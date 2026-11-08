# -*- coding: utf-8 -*-
"""管线实裁复核:用 build_cells 同一代码路径(_crop_cell+_bound_x)渲染前两列每格裁片,
逐格跑 RapidOCR,输出 裁片montage + OCR/表值对照CSV。验证"切格窗口错位→识别错"是否成立。
输出 runs/tmp/前两列_管线实裁_20261010/
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths
from src.table.reconstruct_excel import _crop_cell
from src.table.track_rows import row_y
from openpyxl import load_workbook

OUT = paths.RUNS_DIR / "tmp" / "前两列_管线实裁_20261010"
OUT.mkdir(parents=True, exist_ok=True)
B = paths.REEMIT_DIR_20261005B
NUMS = ["1016", "1022", "1026", "1036", "1040"]

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

rows_csv = []
for num in NUMS:
    stem = f"钻孔柱状图{num}"
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json", encoding="utf-8"))
    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json", encoding="utf-8"))
    keep, v3 = hm["keep"], hm.get("sep_pts")
    x_tbl = sum(rd["table_x"]) / 2
    rows_r = [q for q in rd["rows"] if row_y(q, x_tbl) >= hm["band"][1]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    vals = list(load_workbook(B / f"钻孔柱状图{num}_还原.xlsx", data_only=True)
                .active.iter_rows(values_only=True))

    def _bound_x(i, y, edge):
        if i is None or i < 0:
            return edge
        b = v3[i]
        r = np.interp(y, b["ys"], b["xs"])
        return r if np.ndim(r) else float(r)

    for ci in (0, 1):
        c = keep[ci]
        crops = []
        for r in range(2, 12):                      # r2..r11,与粗裁片同带
            top, bot = rows_r[r - 2], rows_r[r - 1]
            y_mid = (row_y(top, x_tbl) + row_y(bot, x_tbl)) / 2
            x0 = _bound_x(c["left_sep"], y_mid, 0.0)
            x1 = min(_bound_x(c["right_sep"], y_mid, float(gray.shape[1])), gray.shape[1])
            xc = (x0 + x1) / 2
            y0c, y1c = row_y(top, xc), row_y(bot, xc)
            crop = _crop_cell(gray, top, bot,
                              lambda y, i=c["left_sep"]: _bound_x(i, y, 0.0),
                              lambda y, i=c["right_sep"]: _bound_x(i, y, float(gray.shape[1])),
                              x0, x1, y0c, y1c)
            txt, tab = "", vals[r - 1][ci] if r - 1 < len(vals) else ""
            if crop is not None:
                res, _ = ocr(crop)
                txt = " ".join(t[1] for t in (res or [])).strip()
                g = cv2.resize(crop, (crop.shape[1] * 2, crop.shape[0] * 2),
                               interpolation=cv2.INTER_NEAREST)
            else:
                g = np.full((40, 160), 255, np.uint8)
            crops.append((r, g))
            rows_csv.append([num, r, c["name"], f"crop={'None' if crop is None else crop.shape}",
                             txt, tab])
        # montage: 左侧白条写行号,黑白分隔
        H = sum(g.shape[0] + 6 for _, g in crops)
        W = max(g.shape[1] for _, g in crops) + 56
        mont = np.full((H, W), 255, np.uint8)
        y = 0
        for r, g in crops:
            mont[y:y + g.shape[0], 56:56 + g.shape[1]] = g
            cv2.putText(mont, f"r{r}", (4, y + g.shape[0] // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
            y += g.shape[0] + 6
            if y < H:
                mont[y - 3:y + 3, :] = 128
        p = OUT / f"{num}_c{ci}_{c['name']}_实裁.png"
        cv2.imwrite(str(p), mont)
        print(p)

with open(OUT / "实裁OCR对照.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["图号", "xlsx行", "列", "crop尺寸", "OCR读出", "表值"])
    w.writerows(rows_csv)
print(f"{len(rows_csv)} 格 → {OUT}")
