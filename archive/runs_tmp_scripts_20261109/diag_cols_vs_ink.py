# -*- coding: utf-8 -*-
"""6a 定稿的每一条列线，在若干高度上和"原图真竖线"对一遍。

真竖线 = 阶段4 竖向 high 段在该 y 处横跨、且这一段在原图里连得上足够多黑像素。
用法: python runs/tmp/diag_cols_vs_ink.py 1034 6000 16800 2400
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402

code, y0, y1, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
stem = f"钻孔柱状图{code}"
gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
bw = (gray < 160).astype(np.uint8)
run = np.zeros_like(bw)
for y in range(bw.shape[0]):
    run[y] = (run[y - 1] + 1) * bw[y] if y else bw[y] * 0

cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
segs = [s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"]
fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
cols = sorted(json.load(open(fp, encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
segd = {s["id"]: s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"}
chains = [tr.load_chain({"segment_ids": c["segment_ids"]}, segd)[0] for c in cols]
print(f"{code} 表高 {gray.shape[0]}  定稿列线 {len(cols)} 条")
print("列线 x@中点 / 点列覆盖 y / 列高像素数:")
for c, ch in zip(cols, chains):
    a = np.asarray(ch, float)
    print(f"  {c['x_at_mid']:7.0f}  y {a[0,0]:6.0f}~{a[-1,0]:6.0f}  n={len(a)}")

for y in range(y0, y1 + 1, step):
    ink = [int(x) for x in range(gray.shape[1]) if run[y, x] >= 200]
    grp = []
    for x in ink:
        if grp and x - grp[-1][-1] <= 4:
            grp[-1].append(x)
        else:
            grp.append([x])
    near = [int(np.mean(g)) for g in grp]
    line = []
    for c, ch in zip(cols, chains):
        a = np.asarray(ch, float)
        cov = "·" if a[0, 0] <= y <= a[-1, 0] else "断"
        line.append(f"{tr.edge_at(ch, y):.0f}{cov}")
    print(f"\ny={y}")
    print("  定稿列线取值: " + " ".join(line))
    print("  原图≥200px实竖线: " + " ".join(str(v) for v in near))
