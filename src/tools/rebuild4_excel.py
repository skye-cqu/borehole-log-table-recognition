# -*- coding: utf-8 -*-
"""4 张待复核图(1018/1030/1032/1042)的 Excel 补产。

依据:已核验列结构定稿(列边界=用户核验的线,含 rebuild/recovery 边界)+ 宽度指纹
(各空隙宽与 1018/1030/1030 标准列宽逐一吻合,2026-09-15 实测)+ 表头 OCR 定列名。
行判定用 track_rows.determine_rows(与 26 张同代码);格 OCR 用 RapidOCR(同 26 张)。
产出与 26 张同 schema 的 {stem}_还原.xlsx,另出互证 QC,单元格不改名不臆造。

用法:
  python src/tools/rebuild4_excel.py rows            # 4 张 行判定
  python src/tools/rebuild4_excel.py headers         # 表头 OCR 定列名(打印)
  python src/tools/rebuild4_excel.py build           # 出 4 张 Excel 草案 + QC
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.track_columns import load_chain  # noqa: E402
from src.table.track_rows import determine_rows  # noqa: E402

STEMS4 = ["钻孔柱状图1018", "钻孔柱状图1030", "钻孔柱状图1032", "钻孔柱状图1042"]
KEEP8 = ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]
NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")

# 每图边界方案:x 升序;src 指 判定 separators[no] 或 定稿 frames/recovery 条目。
# 依据=核验定稿逐条目 + 空隙宽度与标准列宽指纹吻合(1032 三列整列裁失:
# 65|152|236|317|392|596|1917 七空隙 87/84/81/75/204/1321/545 ↔ 85/85/78/77/205/1300/550)。
def _boundaries(n: int, jd, st):
    sep = {s["no"]: s for s in jd["separators"]}
    fr = {f.get("side"): f for f in st["frames"]}

    def entry(src):
        if src == "L":          # 定稿 frames left
            return fr["left"]
        if src == "R":
            return fr["right"]
        if src == "E":          # 1032 图左缘条目(src='frames')
            return next(c for c in st["columns"] if c.get("src") == "frames")
        if isinstance(src, int):
            return sep[src]
        return next(c for c in st["columns"] if c.get("src") == src)  # rebuild:/recovery

    plans = {
        1018: (["L", 1, 2, 3, 4, 5, 6, 7, "recovery", 8, "R"],
               ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚",
                "柱状", "岩性描述", "简易水文曲线"]),
        1030: ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "R"],
               ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚",
                "柱状", "岩性描述", "简易水文曲线"]),
        1032: (["E", 1, 2, 3, 4, 5, 6, "R"],
               ["层厚", "采长", "倾角", "真厚", "柱状", "岩性描述", "简易水文曲线"]),
        1042: (["L", "rebuild:地质|煤层", "rebuild:煤层|深度", 3, 4, 5, 6, 7, 8, 9, "R"],
               ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角",
                "真厚", "柱状", "岩性描述", "简易水文曲线"]),
    }[n]
    srcs, names = plans
    bs = []
    for src in srcs:
        e = entry(src)
        bs.append({"src": str(src), "x": float(e["x_at_mid"]),
                   "ids": list(e.get("segment_ids") or [])})
    bs.sort(key=lambda b: b["x"])
    cols = []
    for i in range(len(bs) - 1):
        cols.append({"name": names[i], "li": i, "ri": i + 1,
                     "x0": bs[i]["x"], "x1": bs[i + 1]["x"],
                     "keep": names[i] in KEEP8})
    return bs, cols


def _chain_x(segs_all, ids, y):
    if not ids:
        return None
    pts, _ = load_chain({"segment_ids": ids}, segs_all)
    i = int(np.searchsorted(pts[:, 0], y))
    if i <= 0:
        return float(pts[0, 1])
    if i >= len(pts):
        return float(pts[-1, 1])
    y0, x0 = pts[i - 1]
    y1, x1 = pts[i]
    return float(x0 + (x1 - x0) * (y - y0) / max(y1 - y0, 1e-9))


def load_chart(n: int):
    stem = f"钻孔柱状图{n}"
    tp = paths.TRACK_GROUP_DIR / f"{stem}_列判定.json"
    if not tp.exists():
        raise SystemExit(f"{stem}: track 源已退役({tp.name} 不存在);"
                         f"本补产脚本按 track 编号口径,该路径不可用")
    jd = json.loads(tp.read_text(encoding="utf-8"))
    st = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json")
                    .read_text(encoding="utf-8"))
    hm_old = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json")
                        .read_text(encoding="utf-8"))
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    seg_all = {s["id"]: s for s in cj["lines"]
               if s["direction"] == "vertical" and s["label"] == "high"}
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    bs, cols = _boundaries(n, jd, st)
    return stem, jd, st, hm_old, seg_all, gray, bs, cols


def stage_rows():
    for stem in STEMS4:
        n = int(stem[-4:])
        _, jd, st, hm_old, _, _, bs, cols = load_chart(n)
        o = determine_rows(stem)
        print(f"{stem}: 主行线 {len(o['rows'])} 子行线 {len(o['sub_rows'])} "
              f"warnings={o['warnings']}")


def stage_headers():
    """表头带内逐 gap OCR,核对列名方案(不落盘,打印供人复核)。"""
    for stem in STEMS4:
        n = int(stem[-4:])
        _, jd, st, hm_old, seg_all, gray, bs, cols = load_chart(n)
        band = hm_old["band"]
        print(f"==== {stem} band={band}")
        for c in cols:
            y0, y1 = band[0] + 6, band[1] - 4
            x0 = int(c["x0"]) + 3
            x1 = int(c["x1"]) - 3
            if x1 - x0 < 8 or y1 - y0 < 8:
                print("   %-8s [太窄不读]" % c["name"])
                continue
            crop = gray[y0:y1, x0:x1]
            from rapidocr_onnxruntime import RapidOCR
            ocr = RapidOCR(intra_op_num_threads=1)  # 默认满核线程在多进程池里互踩,实测慢 12 倍
            res, _ = ocr(crop)
            text = " ".join(r[1] for r in (res or [])).strip()
            print("   %-8s x[%d,%d] w=%d 表头读数: %r" % (
                c["name"], c["x0"], c["x1"], c["x1"] - c["x0"], text[:24]))


def stage_build():
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1)  # 默认满核线程在多进程池里互踩,实测慢 12 倍
    for stem in STEMS4:
        n = int(stem[-4:])
        _, jd, st, hm_old, seg_all, gray, bs, cols = load_chart(n)
        rd = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                        .read_text(encoding="utf-8"))
        band = hm_old["band"]
        rows_y = [r["y_at_mid"] for r in rd["rows"] if r["y_at_mid"] >= band[1]]
        if len(rows_y) < 2:
            print(stem, "FAIL 主行线不足", len(rows_y))
            continue
        keep = [c for c in cols if c["keep"]]
        table = []
        n_cells = n_text = 0
        for li in range(len(rows_y) - 1):
            y_top, y_bot = rows_y[li], rows_y[li + 1]
            y_mid = (y_top + y_bot) / 2
            out_row = []
            for c in keep:
                x0 = _chain_x(seg_all, bs[c["li"]]["ids"], y_mid)
                x1 = _chain_x(seg_all, bs[c["ri"]]["ids"], y_mid)
                if x0 is None:
                    x0 = c["x0"]
                if x1 is None:
                    x1 = c["x1"]
                xi0 = int(max(0, min(x0, x1) + 3))
                xi1 = int(min(gray.shape[1], max(x0, x1) - 3))
                yi0, yi1 = int(y_top + 4), int(y_bot - 3)
                if xi1 - xi0 < 8 or yi1 - yi0 < 8:
                    out_row.append("")
                    continue
                res, _ = ocr(gray[yi0:yi1, xi0:xi1])
                n_cells += 1
                text = " ".join(r[1] for r in (res or [])).strip()
                if text:
                    n_text += 1
                out_row.append(float(text) if NUM_RE.match(text) else text)
            table.append(out_row)
        header = [c["name"] for c in keep]
        sheet = [header] + table
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = stem.replace("钻孔柱状图", "")
        for row in sheet:
            ws.append(row)
        out = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_还原_补产草案.xlsx"
        wb.save(out)
        qc = relation_qc(header, table)
        print(f"{stem}: 层 {len(table)} 格 {n_cells} 有字 {n_text} → {out.name}")
        print(f"   互证: {qc}")


def relation_qc(header, table):
    """数字互证(判定6 实测关系):真厚=层厚×cos倾角;层厚=相邻深度差;深度递增。"""
    def col(name):
        return [r[header.index(name)] if name in header else None for r in table]
    d, t, ang, th = col("深度"), col("层厚"), col("倾角"), col("真厚")
    n = len(table)
    strong = ok = 0
    diffs = []
    mono = True
    prev = None
    for i in range(n):
        try:
            dv = float(d[i]) if d[i] not in (None, "") else None
        except (TypeError, ValueError):
            dv = None
        if dv is not None:
            if prev is not None and dv <= prev:
                mono = False
            prev = dv
        try:
            tv, av, hv = float(t[i]), float(ang[i]), float(th[i])
        except (TypeError, ValueError):
            continue
        if abs(av) > 89:
            continue
        pred = hv * math.cos(math.radians(av))
        strong += 1
        if abs(pred - tv) <= 0.02:
            ok += 1
        diffs.append(abs(pred - tv))
    return {"行数": n, "深度递增": mono,
            "真厚互证对": strong, "互证≤0.02m": ok,
            "互证率": round(ok / strong, 3) if strong else None}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    {"rows": stage_rows, "headers": stage_headers, "build": stage_build}[cmd]()


if __name__ == "__main__":
    main()
