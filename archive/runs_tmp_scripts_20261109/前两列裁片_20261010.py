# -*- coding: utf-8 -*-
"""前两列竖条裁片:随机 5 图,各裁时代+层号两列 × 10 行的竖条(连行界),供用户分析切碎模式。
列 x 界与 build_cells 同源(keep + sep_pts 插值)。输出 runs/tmp/前两列裁片_20261010/ + 对照CSV。
"""
import csv
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths
from src.table.track_rows import row_y
from openpyxl import load_workbook

OUT = paths.RUNS_DIR / "tmp" / "前两列裁片_20261010"
OUT.mkdir(parents=True, exist_ok=True)
B = paths.REEMIT_DIR_20261005B

stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
random.seed(20261010)
picks = random.sample(stems, 5)

rows_csv = []
for stem in picks:
    num = stem.replace("钻孔柱状图", "")
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json", encoding="utf-8"))
    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json", encoding="utf-8"))
    v3 = hm.get("sep_pts")
    if not v3:
        print(f"[跳] {num} 无 sep_pts")
        continue
    keep = hm["keep"]
    x_tbl = sum(rd["table_x"]) / 2
    rows_r = [q for q in rd["rows"] if row_y(q, x_tbl) >= hm["band"][1]]

    vals = list(load_workbook(B / f"钻孔柱状图{num}_还原.xlsx", data_only=True)
                .active.iter_rows(values_only=True))

    def bx(i, y, edge):
        if i is None or i < 0:
            return edge
        b = v3[i]
        v = np.interp(y, b["ys"], b["xs"])
        return v if np.ndim(v) else float(v)

    # 取第0列有字的行为中心的 10 行带;找不到就取表中段
    center = next((j for j in range(1, len(vals))
                   if str(vals[j][0] or "").strip() not in ("", "None")), len(vals) // 2)
    j0 = max(2, center - 4)
    j1 = min(len(vals) - 1, j0 + 9)          # xlsx 行 j ↔ 带 [rows_r[j-2], rows_r[j-1]]
    top_poly, bot_poly = rows_r[j0 - 2], rows_r[j1 - 1]
    y_mid_all = np.linspace(row_y(top_poly, x_tbl), row_y(bot_poly, x_tbl), 40)
    x0 = min(bx(keep[0]["left_sep"], y, 0.0) for y in y_mid_all) - 15
    x1 = max(bx(keep[1]["right_sep"], y, 1e14) for y in y_mid_all) + 15
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    x0, x1 = max(0, int(x0)), min(gray.shape[1], int(x1))
    xc = (x0 + x1) / 2
    y0 = max(0, int(row_y(top_poly, xc)) - 10)
    y1 = min(gray.shape[0], int(row_y(bot_poly, xc)) + 10)
    viz = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    viz = cv2.resize(viz, (viz.shape[1] * 2, viz.shape[0] * 2), interpolation=cv2.INTER_NEAREST)
    p = OUT / f"{num}_前两列_r{j0}-r{j1}.png"
    cv2.imwrite(str(p), viz)
    print(p, f"y[{y0},{y1}] x[{x0},{x1}]")
    for j in range(j0, j1 + 1):
        c0 = vals[j][0] if j - 1 < len(vals) and len(vals[j]) > 0 else None
        c1 = vals[j][1] if j - 1 < len(vals) and len(vals[j]) > 1 else None
        rows_csv.append([num, j, keep[0]["name"], c0, keep[1]["name"], c1])

with open(OUT / "对照表_墨面在下图_表值在此.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["图号", "xlsx行", "第0列名", "第0列表值", "第1列名", "第1列表值"])
    w.writerows(rows_csv)
print(f"{len(picks)} 图 → {OUT}")
