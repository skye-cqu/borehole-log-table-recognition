# -*- coding: utf-8 -*-
"""多源全量扫描(RapidOCR 侧,2026-11-06 用户批准):全库 desc 非空格 × 3 读。

读实例:窄窗(复用 reread_desc 既有读,缺则现读)/ 宽窗 / 横排拼字。
出 runs/autoresearch_align/multisource_reads.json:
    {stem: {"行<r>": {"tight": str, "loose": str, "montage": str, "耗时s": f}}}
纪律:确定性(intra_op=1)、证据只增不改、巨行守卫(y1-y0>400 跳)、
并行统一走 src/core/batch.run_batch(3 进程)。
CLI: python src/handwriting/multisource_sweep.py [--only-stems=1015,1020]
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from openpyxl import load_workbook

from src.core import paths
from src.handwriting import rules as R
from src.handwriting.cellcrop import crop_window, read_cell_text
from src.handwriting.normalizers import norm_desc

OUT = paths.AUTORESEARCH_DIR / "multisource_reads.json"
PARTS = paths.AUTORESEARCH_DIR / "multisource_parts"


def montage_read(gray, x0, x1, y0, y1, ocr):
    """横排拼字读:格窗→OTSU 反相→竖投影切字(近缝合并)→等高横排→整读。"""
    import cv2
    win = crop_window(gray, x0, x1, y0, y1, pad_l=8, pad_r=8)
    if win is None:
        return ""
    _, binv = cv2.threshold(win, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    col = (binv > 0).sum(axis=0)
    runs, s = [], None
    for i, v in enumerate(col):
        if v >= 1 and s is None:
            s = i
        elif v < 1 and s is not None:
            runs.append([s, i])
            s = None
    if s is not None:
        runs.append([s, len(col)])
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < 6:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    merged = [ab for ab in merged if ab[1] - ab[0] >= 6]
    tiles = []
    for a, b in merged:
        sub = binv[:, a:b]
        ys = np.where(sub.sum(axis=1) > 0)[0]
        if len(ys) == 0:
            continue
        t = 255 - sub[ys[0]:ys[-1] + 1]
        h0 = 48
        t = cv2.resize(t, (max(6, int(t.shape[1] * h0 / t.shape[0])), h0))
        tiles.append(t)
    if len(tiles) < 2:
        return ""
    h = max(t.shape[0] for t in tiles)
    gap = np.full((h, 6), 255, np.uint8)
    row_img = None
    for t in tiles:
        t = cv2.copyMakeBorder(t, 0, h - t.shape[0], 3, 3,
                               cv2.BORDER_CONSTANT, value=255)
        row_img = t if row_img is None else np.hstack([row_img, gap, t])
    if row_img.shape[0] < 16 or row_img.shape[1] < 32:
        return ""
    try:
        res, _ = ocr(row_img)
    except Exception:                 # noqa: BLE001  极端宽高比触 RapidOCR 缩放边界
        return ""
    return " ".join(str(t) for _, t, _c in (res or [])) if res else ""


def targets_desc_nonempty():
    """全库 desc 非空格清单 {(stem数字, 行)}。"""
    out = set()
    for p in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
        stem = p.name[: -len("_整合.xlsx")]
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        if dcol is None:
            continue
        for i, row in enumerate(rows[1:]):
            if norm_desc(row[dcol] if dcol < len(row) else None):
                out.add((stem[5:], i + 2))
    return out


def worker(payload):
    """单图三读:吃 (stem数字, [行]),证据分片落盘。batch 约定 (stem, ok, info)。"""
    stem, rows_ = payload
    try:
        import cv2
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"钻孔柱状图{stem}_表头映射.json", encoding="utf-8"))
        keep = None
        for k in hm["keep"]:
            if k["name"] == "岩性描述":
                keep = sorted(k["x_in_band"])
        if not keep:
            return stem, False, "无desc列界"
        x0, x1 = keep
        cache = json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
        ivs = {int(k): tuple(float(a) for a in v)
               for k, v in cache[f"钻孔柱状图{stem}"]["ivs"].items()}
        gray = cv2.imread(str(paths.RAW_DIR / f"钻孔柱状图{stem}.JPG"),
                          cv2.IMREAD_GRAYSCALE)
        from src.handwriting.reread import _ocr
        ocr = _ocr()
        old = {}
        od = paths.AUTORESEARCH_DIR / "reread_desc.json"
        if od.exists():
            old = json.loads(od.read_text(encoding="utf-8")).get(
                f"钻孔柱状图{stem}", {})
        ev = {}
        t0 = time.time()
        for r in sorted(rows_):
            if r - 2 not in ivs:
                continue
            y0, y1 = ivs[r - 2]
            if y1 - y0 > 400:
                continue                      # 巨行守卫
            tight = ((old.get(f"行{r}") or {}).get("text") or "").strip()
            if not tight:
                tight = read_cell_text(gray, x0, x1, y0, y1, ocr)
            loose = read_cell_text(gray, x0, x1, y0, y1, ocr,
                                   pad_l=30, pad_r=120,
                                   center_lo=-60, center_hi=150)
            mont = montage_read(gray, x0, x1, y0, y1, ocr)
            ev[f"行{r}"] = {"tight": tight, "loose": loose,
                            "montage": mont}
        PARTS.mkdir(parents=True, exist_ok=True)
        (PARTS / f"{stem}.json").write_text(
            json.dumps(ev, ensure_ascii=False), encoding="utf-8")
        return stem, True, f"读{len(ev)}格 {round(time.time() - t0, 1)}s"
    except Exception as e:  # noqa: BLE001
        return stem, False, f"{type(e).__name__}: {e}"


def main(argv):
    only = None
    for a in argv:
        if a.startswith("--only-stems="):
            only = set(a.split("=", 1)[1].split(","))
    targets = targets_desc_nonempty()
    if only:
        targets = {t for t in targets if t[0] in only}
    have = set()
    if PARTS.exists():
        for pp in PARTS.glob("*.json"):
            have.add(pp.stem)                 # 断点续跑:已分片图跳过
    per = {}
    for stem, r in sorted(targets):
        if stem in have:
            continue
        per.setdefault(stem, []).append(r)
    items = sorted(per.items())
    n_cells = sum(len(v) for _, v in items)
    print(f"待三读 {n_cells} 格 / {len(items)} 图(已有分片 {len(have)} 图跳过)")
    if not items:
        _merge()
        return
    from src.core import batch
    results = batch.run_batch(items, worker, max_workers=3)
    failed = [it for it, (_s, ok, _i) in zip(items, results) if not ok]
    if failed:
        print(f"重试 {len(failed)} 张失败图(单进程)")
        retry = dict((s, (s, ok, info)) for s, ok, info in
                     batch.run_batch(failed, worker, max_workers=1))
        results = [retry.get(s, res) for s, res in
                   zip([it[0] for it in items], results)]
    _merge()
    for stem, ok, info in results:
        if not ok:
            print(f"  {stem} FAIL {info}")


def _merge():
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    n = 0
    for pp in sorted(PARTS.glob("*.json")):
        out[f"钻孔柱状图{pp.stem}"] = json.loads(pp.read_text(encoding="utf-8"))
        n += 1
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    cells = sum(len(v) for v in out.values())
    print(f"合并 {n} 图 / {cells} 格 → multisource_reads.json")


if __name__ == "__main__":
    main(sys.argv[1:])
