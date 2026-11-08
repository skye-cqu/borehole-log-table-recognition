# -*- coding: utf-8 -*-
"""抗漂移墨迹跟踪 + 全30图双描界普查。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

def trace(g, y0, y1, x0, win=6, thr=150, maxslope=0.3, step=1):
    x = float(x0); hits = 0; n = 0; gap = 0; maxgap = 0; xs = []
    W = g.shape[1]
    for y in range(int(y0), int(y1), step):
        lo = max(0, int(round(x)) - win); hi = min(W, int(round(x)) + win + 1)
        row = g[y, lo:hi]
        k = int(np.argmin(row)); v = int(row[k])
        n += 1
        if v < thr:
            hits += 1; gap = 0
            nx = lo + k
            d = nx - x
            if abs(d) > maxslope: nx = x + maxslope * (1 if d > 0 else -1)
            x = nx
        else:
            gap += 1
            if gap > maxgap: maxgap = gap
        xs.append(x)
    return hits / max(n, 1), maxgap, xs

stem = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
band = hm["band"]
print("=== %s band=%s 图高=%d ===" % (stem, band, g.shape[0]))
cands = [137, 199, 259, 383, 469, 550, 553, 633, 660, 690, 709, 730, 790, 913, 1000]
print("x0     表头暗比  全高命中率  最大缺口  终点x    定性")
for x0 in cands:
    b = g[band[0]:band[1], max(0, x0-1):x0+2]
    hf = float((b < 150).mean())
    r, mg, xs = trace(g, band[0], g.shape[0]-2, x0)
    kind = "真列界" if (r >= 0.60 and mg <= 400) else ("文字笔画(仅表头)" if hf > 0.5 and r < 0.35 else "存疑")
    print("%-7d %-9.2f %-11.3f %-9d %-8.0f %s" % (x0, hf, r, mg, xs[-1], kind))
print()
print("已采用 sep_x_band:", [round(v) for v in hm["sep_x_band"]])
r, mg, xs = trace(g, band[0], g.shape[0]-2, 709)
print("709 跟踪轨迹抽样:")
for i in range(0, len(xs), max(1, len(xs)//12)):
    print("    y=%6d x=%.0f" % (band[0]+i, xs[i]))

print()
print("=== 全 30 图:相邻分隔线间距 < 20px 的双描普查 ===")
n_dup = 0
for p in sorted((paths.RUNS_DIR/"table_reconstruct").glob("*_表头映射.json")):
    s = p.stem.replace("_表头映射", "")
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    sx = d.get("sep_x_band") or []
    bad = [(round(a,1), round(b,1), round(b-a,1)) for a, b in zip(sx, sx[1:]) if b - a < 20]
    if bad:
        n_dup += 1
        print("  %-16s %s" % (s, bad))
print("  双描图数 = %d" % n_dup)
