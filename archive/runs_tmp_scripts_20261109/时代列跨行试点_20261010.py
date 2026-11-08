# -*- coding: utf-8 -*-
"""时代列跨行文字试点:不再按行切格。列带内逐像素掩膜取条带(原图像素,不重采样),
剔行线墨→竖向投影找整字墨块→逐字OCR→按实测空隙分布聚成名字带→映射覆盖行区间(合并区依据)。
试点: 1016 1022 1026 1036 1040。输出 runs/tmp/时代列跨行试点_20261010/
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths
from src.table.track_rows import row_y
from openpyxl import load_workbook

OUT = paths.RUNS_DIR / "tmp" / "时代列跨行试点_20261010"
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
    keep, v3, band = hm["keep"], hm.get("sep_pts"), hm["band"]
    x_tbl = sum(rd["table_x"]) / 2
    rows_r = [q for q in rd["rows"] if row_y(q, x_tbl) >= band[1]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    vals = list(load_workbook(B / f"钻孔柱状图{num}_还原.xlsx", data_only=True)
                .active.iter_rows(values_only=True))

    def bx(i, y, edge):
        if i is None or i < 0:
            return edge
        b = v3[i]
        r = np.interp(y, b["ys"], b["xs"])
        return r if np.ndim(r) else float(r)

    L, R = keep[0]["left_sep"], keep[0]["right_sep"]
    y0, y1 = int(band[1]), int(row_y(rows_r[-1], x_tbl))
    ys = np.arange(y0, y1)
    xls = np.asarray([bx(L, y, 0.0) for y in ys]) + 4
    xrs = np.asarray([bx(R, y, gray.shape[1]) for y in ys]) - 4
    xa, xb = int(np.min(xls)), int(np.max(xrs))
    strip = np.full((len(ys), xb - xa), 255, np.uint8)      # 掩膜取条带,原像素不重采样
    for k, y in enumerate(ys):
        a, b = int(xls[k] - xa), int(xrs[k] - xa)
        if b > a:
            strip[k, a:b] = gray[y, xa:xb][a:b]
    # 行线行:暗像素占比>0.55 → 置白(剔行线墨)
    dark = strip < 170
    line_rows = dark.mean(axis=1) > 0.55
    proj = dark.copy()
    proj[line_rows] = False
    prof = proj.sum(axis=1)
    on = prof > 2
    # 聚墨块:≤12px 断口缝合(行线厚度+pad),块高 15~260px 为字
    runs, s = [], None
    for k, v in enumerate(on):
        if v and s is None:
            s = k
        elif not v and s is not None:
            runs.append([s, k]); s = None
    if s is not None:
        runs.append([s, len(on)])
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] <= 12:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    chars = [(a, b) for a, b in merged if 15 <= b - a <= 260]
    # 逐字 OCR(带 6px 边距)
    texts = []
    for a, b in chars:
        crop = strip[max(0, a - 6):b + 6, :]
        res, _ = ocr(crop)
        texts.append("".join(t[1] for t in (res or [])).replace(" ", ""))
    # 名字分带:空隙 > 2×字高中位 → 分名(阈值由本图实测推导)
    hgt = [b - a for a, b in chars]
    hmed = float(np.median(hgt)) if hgt else 0
    gaps = [chars[k + 1][0] - chars[k][1] for k in range(len(chars) - 1)]
    G = max(2.0 * hmed, 60)
    names, cur = [], None
    for k, (a, b) in enumerate(chars):
        if cur and chars[k][0] - cur[1] > G:
            names.append(cur); cur = [a, b, texts[k]]
        elif cur:
            cur[1] = b; cur[2] += texts[k]
        else:
            cur = [a, b, texts[k]]
    if cur:
        names.append(cur)
    # 映射覆盖 xlsx 行
    ymid_rows = [(row_y(rows_r[k], x_tbl) + row_y(rows_r[k + 1], x_tbl)) / 2 for k in range(len(rows_r) - 1)]

    def cover(a, b):
        ya, yb = ys[a], ys[b]
        return [j + 2 for j, m in enumerate(ymid_rows) if ya - 5 <= m <= yb + 5]

    print(f"=== {num} 字高中位={hmed:.0f}px 名带分隔G={G:.0f}px 字块{len(chars)} 名带{len(names)} ===")
    for a, b, t in names:
        cov = cover(a, b)
        frag = [str(vals[r - 1][0] or "") for r in cov]
        print(f"  y[{ys[a]},{ys[b]}] 字={t!r} 覆盖xlsx行{cov} 现表碎片={frag}")
        rows_csv.append([num, f"y{ys[a]}-{ys[b]}", t, " ".join(map(str, cov)), " ".join(frag)])
    # 可视化:条带+字块框
    viz = cv2.cvtColor(strip, cv2.COLOR_GRAY2BGR)
    for k, (a, b) in enumerate(chars):
        cv2.rectangle(viz, (0, a), (viz.shape[1] - 1, b), (0, 0, 255), 2)
    for a, b, t in names:
        cv2.rectangle(viz, (0, a), (viz.shape[1] - 1, b), (255, 0, 0), 1)
    cv2.imwrite(str(OUT / f"{num}_时代条带.png"), viz)

with open(OUT / "名字带对照.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["图号", "y范围", "拼合名", "覆盖xlsx行", "现表碎片"])
    w.writerows(rows_csv)
print(f"→ {OUT}")
