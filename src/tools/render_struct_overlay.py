# -*- coding: utf-8 -*-
"""结构叠加核验图:现行行界折线+列界真段画回原图,交用户肉眼核验(约束7)。

红=行界折线(行判定 poly,即出表用的层界);蓝=列界真段(_分割线 P10 口径,sep_pts);
黄=P5 已登记的可疑线(单链跨柱状带 ~80px 台阶,待用户裁定是否 rowspan)。
产物(paths.OVERLAY_CHECK_DIR_20260930):{stem}_叠加全图.png(全分辨率)、
{stem}_叠加半分辨率.jpg、局部1比1/{stem}_{标签}.png。

用法: python -u -X utf8 src/tools/render_struct_overlay.py 1015 1027
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402

# P5 可疑线(骨架修正后真歪 5 条,runs/行列线可疑清单.json 同源)
YELLOW = {("钻孔柱状图1020", 10074), ("钻孔柱状图1027", 3142),
          ("钻孔柱状图1027", 11412), ("钻孔柱状图1037", 22128), ("钻孔柱状图1043", 3671)}


def _col_x(hm, name):
    for c in hm.get("keep", []) + hm.get("drop_columns", []):
        if c["name"] == name:
            return c["x_in_band"]
    return None


def render(stem: str):
    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                        encoding="utf-8"))
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                        encoding="utf-8"))
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    x_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_tbl) >= hm["band"][1]]
    # 可疑线就近匹配:清单 y 是外框定宽前旧模型坐标,线会漂 ~60px,死阈值会漏
    suspects = [y for s, y in YELLOW if s == stem]
    ymids = [row_y(r, x_tbl) for r in rows_r]
    yellow = [False] * len(rows_r)
    for y in suspects:
        k = min(range(len(ymids)), key=lambda i: abs(ymids[i] - y))
        if abs(ymids[k] - y) < 150:
            yellow[k] = True
    n_yellow = sum(yellow)
    for r, is_yellow in zip(rows_r, yellow):
        pts = np.asarray(r["poly"], np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], False, (0, 255, 255) if is_yellow else (0, 0, 255), 3)
    for b in hm["sep_pts"]:
        pts = np.asarray(list(zip(b["xs"], b["ys"])), np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], False, (255, 0, 0), 3)

    out = paths.OVERLAY_CHECK_DIR_20260930
    (out / "局部1比1").mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / f"{stem}_叠加全图.png"), img)
    half = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2),
                      interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out / f"{stem}_叠加半分辨率.jpg"), half,
                [cv2.IMWRITE_JPEG_QUALITY, 90])

    # 1:1 裁片:时代列上段 / 柱状带(可疑线优先) / 数值列中部
    crops = []
    era = _col_x(hm, "地质时代")
    if era:
        crops.append(("时代列上段", max(0, era[0] - 140), hm["band"][0] - 80,
                      era[1] + 380, hm["band"][0] + 1700))
    band = _col_x(hm, "柱状")
    ys_yellow = [y for s, y in YELLOW if s == stem]
    y_focus = ys_yellow[0] if ys_yellow else 9000
    if band:
        crops.append(("柱状带" + (f"_可疑线{y_focus}" if ys_yellow else ""),
                      max(0, band[0] - 450), y_focus - 350,
                      min(img.shape[1], band[1] + 450), y_focus + 350))
    num0 = _col_x(hm, "深度")
    num1 = _col_x(hm, "采长")
    if num0 and num1:
        crops.append(("数值列中部", num0[0] - 60, y_focus + 900,
                      num1[1] + 60, y_focus + 1900))
    for label, x0, y0, x1, y1 in crops:
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(img.shape[1], int(x1)), min(img.shape[0], int(y1))
        cv2.imwrite(str(out / "局部1比1" / f"{stem}_{label}.png"), img[y0:y1, x0:x1])
    print(f"{stem}: 行界 {len(rows_r)} 条(黄 {n_yellow}) 列界 {len(hm['sep_pts'])} 条, "
          f"全图+半分辨率+{len(crops)} 裁片 → {out.name}/")


def main():
    stems = sys.argv[1:] or []
    for n in stems:
        render(f"钻孔柱状图{n}" if n.isdigit() else n)


if __name__ == "__main__":
    main()
