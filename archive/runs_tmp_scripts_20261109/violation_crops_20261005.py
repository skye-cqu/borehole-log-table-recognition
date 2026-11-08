# -*- coding: utf-8 -*-
"""公理违反清单 → 原图裁片包:对复测出的每条 I1/I2/I3/I5 违反渲染所在行带数值区裁片。

I1/I2/I3 按 xlsx行号映射行带 (ys[r-2], ys[r-1]);I5 重算巨带区间。
裁片 x=[tab_l−15, tab_l+900](数值四列+层号), y=带±25, 2×。
输出 runs/tmp/违反裁片_20261005/ + 索引.csv;同带多条违反只出一张裁片。

用法: python runs/tmp/violation_crops_20261005.py [违反csv路径] [xlsx目录]
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

VIOL_CSV = paths.RUNS_DIR / "tmp" / "公理违反_20261005.csv"
XLSX_DIR = paths.REEMIT_DIR_20261005B
OUT = paths.RUNS_DIR / "tmp" / "违反裁片_20261005"
NUM_W = 900  # 数值区裁宽(层号+深度+层厚+采长+真厚 ≈ [tab_l, tab_l+900])

if len(sys.argv) > 1:
    VIOL_CSV = Path(sys.argv[1])
if len(sys.argv) > 2:
    XLSX_DIR = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

from openpyxl import load_workbook

viols = list(csv.reader(open(VIOL_CSV, encoding="utf-8-sig")))[1:]
by_chart = {}
for v in viols:
    by_chart.setdefault(v[0], []).append(v[1:])

stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
index, missing = [], []
for stem in stems:
    s = stem.replace("钻孔柱状图", "")
    if s not in by_chart:
        continue
    xlsx = XLSX_DIR / f"{stem}_还原.xlsx"
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json"
    hp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json"
    if not xlsx.exists() or not fp.exists() or not hp.exists():
        missing.append(s)
        continue
    rd = json.load(open(fp, encoding="utf-8"))
    hm = json.load(open(hp, encoding="utf-8"))
    if not rd.get("rows") or not hm.get("band"):
        missing.append(s)
        continue
    tab_l, tab_r = rd["table_x"]
    x_tbl = (tab_l + tab_r) / 2
    ys = sorted(row_y(r, x_tbl) for r in rd["rows"] if row_y(r, x_tbl) >= hm["band"][1])
    ws = load_workbook(xlsx).active
    vals = list(ws.iter_rows(values_only=True))
    n_tab = len(vals) - 1
    if n_tab != len(ys) - 1:
        print(f"[!] {s}: xlsx数据行{n_tab} ≠ 行带数{len(ys)-1},该图跳过(需人工对位)")
        missing.append(s + "(对位失败)")
        continue
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)

    def crop(y0, y1, tag):
        y0, y1 = max(0, int(y0) - 25), min(gray.shape[0], int(y1) + 25)
        x0 = max(0, tab_l - 15)
        x1 = min(gray.shape[1], tab_l + NUM_W)
        viz = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
        viz = cv2.resize(viz, (viz.shape[1] * 2, viz.shape[0] * 2),
                         interpolation=cv2.INTER_NEAREST)
        name = f"{s}_{tag}.png"
        cv2.imwrite(str(OUT / name), viz)
        return name

    done_bands = {}
    for axrow, ax, detail in by_chart[s]:
        row_idx = None                      # xlsx 行号(1基);I5 无
        if axrow == "-":                    # I5: 重算巨带(行号列为'-')
            if len(ys) < 4:
                continue
            med = float(np.median(np.diff(ys)))
            bands = [(a, b) for a, b in zip(ys[:-1], ys[1:]) if b - a > 2.5 * med]
        else:                               # I1/I2/I3: xlsx行号→带
            r = int(axrow)
            row_idx = r
            if not (2 <= r < len(vals)):
                continue
            k = r - 2                       # 数据行序号(0基)
            bands = [(ys[k], ys[k + 1])]
        for bi, (a, b) in enumerate(bands):
            key = (round(a), round(b))
            if key in done_bands:
                index.append([s, axrow, ax, detail, f"{a:.0f}-{b:.0f}", done_bands[key]])
                continue
            name = crop(a, b, f"{ax.replace('I','').replace('=','_')}_r{axrow}_y{int(a)}")
            done_bands[key] = name
            row_vals = [str(v)[:22] if v is not None else "" for v in vals[row_idx - 1]] if row_idx else []
            index.append([s, axrow, ax, detail, f"{a:.0f}-{b:.0f}", name] + (["|".join(row_vals)] if row_vals else [""]))

with open(OUT / "索引.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["图号", "xlsx行号", "公理", "详情", "带y", "文件", "该行值"])
    w.writerows(index)
print(f"裁片 {len(set(r[5] for r in index))} 张(违反{len(index)}条) → {OUT}")
if missing:
    print("未出图:", missing)
