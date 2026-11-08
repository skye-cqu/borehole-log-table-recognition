# -*- coding: utf-8 -*-
"""逐行带满高竖笔覆盖:真列界 vs 文字笔画 的判据。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

stem = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
rj = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_行判定.json").read_text(encoding="utf-8"))
rows = rj["rows"]
bands = []
for i in range(len(rows)-1):
    y0 = rows[i]["poly"][-1][1]; y1 = rows[i+1]["poly"][-1][1]
    if y1 - y0 >= 20: bands.append((y0, y1))
print("有效行带数 =", len(bands))

chains = json.loads((R/"runs/tmp/t2chains_20261015.json").read_text(encoding="utf-8"))

def cover(pts, y0, y1):
    ys = np.array([p[0] for p in pts], float); xs = np.array([p[1] for p in pts], float)
    xp = float(np.interp((y0+y1)/2.0, ys, xs))
    xa = max(0, int(round(xp)) - 3); xb = min(W, int(round(xp)) + 5)
    seg = g[int(y0)+2:int(y1)-1, xa:xb]
    if seg.shape[0] < 4: return None, xp
    return float((seg.min(axis=1) < 150).mean()), xp

print()
print("真实墨迹链 逐行带覆盖 (>=0.85 记为命中)")
print("链   y范围            x顶→x底    命中/总行带   比例   定性")
res = []
for n, c in enumerate(chains):
    pts = c["pts"]
    ys = [p[0] for p in pts]; xs = [p[1] for p in pts]
    hit = 0; tot = 0
    for (y0, y1) in bands:
        if y0 < ys[0] - 20 or y1 > ys[-1] + 20: continue
        cv, xp = cover(pts, y0, y1)
        if cv is None: continue
        tot += 1
        if cv >= 0.85: hit += 1
    if tot < 10: continue
    ratio = hit/float(tot)
    kind = "真列界" if ratio >= 0.80 else ("部分(断口多)" if ratio >= 0.40 else "非列界(文字/图案)")
    res.append((ratio, n, ys[0], ys[-1], xs[0], xs[-1], hit, tot, kind))

for ratio, n, y0, y1, x0, x1, hit, tot, kind in sorted(res, reverse=True):
    print("%-3d  %-7.0f..%-7.0f  %-5.0f→%-5.0f  %-6s/%-6d  %.2f   %s"
          % (n, y0, y1, x0, x1, hit, tot, ratio, kind))

print()
print("已采用 sep_pts 各线 同法覆盖:")
sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_分割线.json").read_text(encoding="utf-8"))
for i, ln in enumerate(sp["lines"]):
    pts = [(p[1], p[0]) for p in ln["pts"]]
    ys = [p[0] for p in pts]
    hit = 0; tot = 0
    for (y0, y1) in bands:
        if y0 < ys[0] - 20 or y1 > ys[-1] + 20: continue
        cv, xp = cover(pts, y0, y1)
        if cv is None: continue
        tot += 1
        if cv >= 0.85: hit += 1
    r = hit/float(tot) if tot else 0.0
    print("  [%d] %-14s %-5.0f→%-5.0f  命中 %d/%d = %.2f" %
          (i, str(ln.get("name"))[:13], pts[0][1], pts[-1][1], hit, tot, r))
