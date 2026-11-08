# -*- coding: utf-8 -*-
"""把"扫描左缘截断"登记到 Excel:逐行橙色底 + 批注,数值一格不改。

用法:
  python src/tools/mark_truncation.py 1032            # 写回重出目录的同名 xlsx 副本
  python src/tools/mark_truncation.py 1032 --out DIR  # 指定输出目录

口径(用户 2026-10-20 裁决):1032 深度列左半格被扫描裁掉,前导位不可恢复 →
**登记为不可恢复 + 逐行标注截断**,不用层厚反推补位(那是发明数据)。
标注语义与既有配色不冲突:红字=与参考表分歧,橙底=原图不可恢复。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.table.truncation import (column_frame_present, depth_chain_evidence,
                                  scan_left_cut)

ORANGE = "FFC000"          # 橙底:原图不可恢复(与红字=参考表分歧、浅蓝=Agnes 校正区分)
NOTE = ("扫描左缘截断:深度列左框整条不在图上(该列左半被裁),数字前导位不可恢复。"
        "数值按原图可见部分保留,未用层厚反推补位。")


def _depth_col(header):
    """表头 → 深度列下标;找不到返回 None(1032 无时代列但深度列在)。"""
    for i, v in enumerate(header or []):
        if str(v or "").strip() == "深度":
            return i
    return None


def mark(stem, out_dir=None):
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill
    from openpyxl.comments import Comment

    import json
    import cv2

    src = paths.REEMIT_DIR_20261005B / f"{stem}_还原.xlsx"
    if not src.exists():
        return {"error": f"源表不存在: {src}"}
    wb = load_workbook(src, rich_text=True)
    ws = wb.active
    data = list(ws.iter_rows(values_only=True))
    col = _depth_col(data[0])
    if col is None:
        return {"error": f"表头无深度列: {data[0]}"}

    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                        encoding="utf-8"))
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                        encoding="utf-8"))
    from src.table.track_rows import row_y
    midx = sum(rd["table_x"]) / 2.0
    ys = [row_y(r, midx) for r in rd["rows"] if row_y(r, midx) >= hm["band"][1]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    x1 = int(hm["sep_x_band"][0])
    # 整列级判据:深度列左框是否存在。不存在 = 整列左半被裁,全列逐行都算截断。
    # 逐行数贴边墨会被扫描噪点带偏(1032 实测每行 0~140px,含格线残余),不作主判据。
    col_cut = not column_frame_present(gray, ys, 0)
    rows = scan_left_cut(gray, ys, 0, x1)
    if col_cut:
        for r in rows:
            r["截断"] = True

    chain = depth_chain_evidence(
        [(i + 2, r[col], r[col + 1] if len(r) > col + 1 else None)
         for i, r in enumerate(data[1:]) if isinstance(r[col], (int, float))])
    ev = {e["行"]: e for e in chain}

    fill = PatternFill(start_color=ORANGE, end_color=ORANGE, fill_type="solid")
    marked, ledger = 0, []
    for r in rows:
        if not r["截断"]:
            continue
        xr = r["行"] + 2                      # 表头占第 1 行
        cell = ws.cell(row=xr, column=col + 1)
        if not isinstance(cell.value, (int, float)):
            # 表尾文字行/空行不是深度读数,不标(标了会污染"逐行截断"的口径)
            continue
        cell.fill = fill
        cell.comment = Comment(NOTE, "audit")
        e = ev.get(xr, {})
        marked += 1
        ledger.append({"xlsx行": xr, "y0": r["y0"], "y1": r["y1"],
                       "贴边墨": r["贴边墨"], "读": cell.value,
                       "推算": e.get("推算"), "旁证支持": e.get("支持")})
    out_dir = Path(out_dir) if out_dir else paths.REEMIT_DIR_20261005B
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{stem}_还原.xlsx"
    wb.save(dst)
    return {"stem": stem, "标注行数": marked, "总判行数": len(rows),
            "整列裁切": col_cut, "输出": str(dst), "明细": ledger}


def main(argv):
    import json
    if not argv:
        print(__doc__)
        return 2
    stem = argv[0] if argv[0].startswith("钻孔柱状图") else f"钻孔柱状图{argv[0]}"
    out = None
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    rep = mark(stem, out)
    if "error" in rep:
        print("FAIL", rep["error"])
        return 1
    print(f"{rep['stem']} 标注 {rep['标注行数']}/{rep['总判行数']} 行"
          f"(整列裁切={rep['整列裁切']}) → {rep['输出']}")
    led = paths.TMP_DIR / f"截断登记_{stem}.json"
    led.parent.mkdir(parents=True, exist_ok=True)
    led.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("明细:", led)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))