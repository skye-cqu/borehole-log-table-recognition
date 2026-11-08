# -*- coding: utf-8 -*-
"""1042 缺失列界 x~709 的墨迹证据:阶段4候选几何 + 逐行墨迹跟踪折线。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{STEM}.json").read_text(encoding="utf-8"))
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_表头映射.json").read_text(encoding="utf-8"))
print("H,W =", H, W, " band =", hm["band"])

# 1) 阶段4 vertical/high 候选,mean x 距 709 <= 45
print("\n== 阶段4 vertical/high 候选 (|mean_x-709|<=45) ==")
rows = []
for s in cj["lines"]:
    if s["direction"] != "vertical" or s["label"] != "high": continue
    pts = s["points"]; mx = float(np.mean([p[0] for p in pts]))
    if abs(mx - 709) > 45: continue
    ys = [p[1] for p in pts]
    rows.append((min(ys), max(ys), mx, len(pts), s.get("final_score"), s.get("id")))
rows.sort()
print("  段数 =", len(rows))
for a, b, mx, n, sc, i in rows:
    print("   y=[%6d,%6d] n=%-5d meanx=%.1f score=%s id=%s" % (a, b, n, mx, sc, i))
tot = np.zeros(H+2, dtype=bool)
for a, b, mx, n, sc, i in rows:
    tot[max(0,int(a)):min(H,int(b))] = True
print("   合并 y 覆盖 = %.3f * H" % (tot.sum()/H))

# 2) 逐行墨迹跟踪:锚在表头带中线 x=709,每行在 ±WIN 内找暗像素最多处
print("\n== 逐行墨迹跟踪 (锚 709, WIN=18, 阈值<150) ==")
WIN, TH = 18, 150
b0, b1 = hm["band"]
ys_anchor = (b0 + b1)//2
x = 709.0
poly, miss = [], 0
for y in range(int(min(min(s["points"], key=lambda p: p[1])[1] for s in cj["lines"] if s["direction"]=="horizontal" and s["label"]=="high")), H):
    a, b = int(max(0, x-WIN)), int(min(W, x+WIN+1))
    seg = g[y, a:b]
    dark = (seg < TH)
    if dark.sum() < 2:
        miss += 1; continue
    # 加权质心
    idx = np.nonzero(dark)[0]
    xc = a + float(np.average(idx, weights=(TH - seg[idx])))
    poly.append((y, xc))
    x = xc   # 跟随漂移
print("   采样点 =", len(poly), " 无墨行 =", miss)
if poly:
    arr = np.array(poly)
    for frac in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        y = int(arr[0,0] + frac*(arr[-1,0]-arr[0,0]))
        k = np.argmin(np.abs(arr[:,0]-y))
        print("   y=%6d  x=%.1f" % (arr[k,0], arr[k,1]))
    print("   x 范围 = %.1f .. %.1f (漂移 %.1f)" % (arr[:,1].min(), arr[:,1].max(), arr[-1,1]-arr[0,1]))
    np.save(str(R/"runs/tmp/t2_709poly_20261015.npy"), arr)
    print("   折线已存 runs/tmp/t2_709poly_20261015.npy")
