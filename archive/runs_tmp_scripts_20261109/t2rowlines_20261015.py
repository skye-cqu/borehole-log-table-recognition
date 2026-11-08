# -*- coding: utf-8 -*-
"""1042: 逐行带内满高竖笔 —— 列结构的唯一客观真值。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

rj = json.loads((paths.RUNS_DIR/"table_reconstruct"/"钻孔柱状图1042_行判定.json").read_text(encoding="utf-8"))
rows = rj["rows"]
print("行数 =", len(rows))
print("rows[0] 键 =", list(rows[0].keys()))
g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)

def band_strokes(y0, y1, x0=450, x1=1000, th=0.45):
    y0, y1 = int(y0)+2, int(y1)-2
    if y1 - y0 < 6: return []
    dark = (g[y0:y1, x0:x1] < 140)
    cand = [(x0+i, float(dark[:, i].mean())) for i in range(dark.shape[1])]
    cand = [(x, f) for x, f in cand if f >= th]
    grps = []
    for x, f in cand:
        if grps and x - grps[-1][-1][0] <= 3: grps[-1].append((x, f))
        else: grps.append([(x, f)])
    return [(float(np.mean([a for a,_ in gp])), max(b for _,b in gp)) for gp in grps]

print()
print("== 前 12 行带内满高竖笔 ==")
for i in range(min(12, len(rows)-1)):
    y0 = rows[i]["poly"][-1][1] if isinstance(rows[i]["poly"][-1], list) else rows[i]["poly"][-1]
    y1 = rows[i+1]["poly"][-1][1] if isinstance(rows[i+1]["poly"][-1], list) else rows[i+1]["poly"][-1]
    st = band_strokes(y0, y1)
    print("  r%-3d y=[%6.0f,%6.0f] h=%-4.0f  %s" % (i, y0, y1, y1-y0,
          " ".join("%.0f(%.2f)" % s for s in st)))

print()
print("== 关键竖笔 709 在全部行带中的出现率 ==")
cnt = tot = 0
missing = []
for i in range(len(rows)-1):
    a = rows[i]["poly"][-1]; b = rows[i+1]["poly"][-1]
    y0 = a[1] if isinstance(a, list) else a
    y1 = b[1] if isinstance(b, list) else b
    if y1 - y0 < 10: continue
    tot += 1
    st = band_strokes(y0, y1)
    if any(abs(x-709) <= 6 for x, _ in st): cnt += 1
    else: missing.append((i, y0, y1))
print("  709 界: %d/%d 行带命中 (%.0f%%)" % (cnt, tot, 100.0*cnt/max(tot,1)))
print("  缺失行:", missing[:20], "..." if len(missing) > 20 else "")

print()
print("== 各候选界的出现率(全表统计) ==")
cand = [469, 550, 553, 633, 660, 709, 745, 790, 913]
stat = {c: 0 for c in cand}
n = 0
for i in range(len(rows)-1):
    a = rows[i]["poly"][-1]; b = rows[i+1]["poly"][-1]
    y0 = a[1] if isinstance(a, list) else a
    y1 = b[1] if isinstance(b, list) else b
    if y1 - y0 < 10: continue
    n += 1
    st = band_strokes(y0, y1)
    for c in cand:
        if any(abs(x-c) <= 6 for x, _ in st): stat[c] += 1
for c in cand:
    print("  x=%-5d 命中 %d/%d (%.0f%%)" % (c, stat[c], n, 100.0*stat[c]/max(n,1)))
