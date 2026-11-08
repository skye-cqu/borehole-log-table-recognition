# -*- coding: utf-8 -*-
"""选法实验:用阶段4 竖/高候选点构造 709 界折线。
A) 种子接续,扫容差;  B) 扇形走廊内候选点按 y 分箱取中位。
一律与扇形墨迹真值(t2_fan709)比对,并测墨迹命中。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
dark = (g < 150)
cj = json.loads((paths.CANDIDATE_COORD_DIR/f"{STEM}.json").read_text(encoding="utf-8"))
segs = []
for s in cj["lines"]:
    if s["direction"] != "vertical" or s["label"] != "high": continue
    p = np.asarray(s["points"], float); p = p[np.argsort(p[:,1])]
    if len(p) >= 2: segs.append((s["id"], p))
print("vertical/high 段 =", len(segs))
fan = np.load(str(R/"runs/tmp/t2_fan709_20261015.npy"))   # [[y, x_true],...]
FY, FX = fan[:,0], fan[:,1]
def fanx(y): return float(np.interp(y, FY, FX))
def dev(tr):
    m = (tr[:,1] >= FY[0]) & (tr[:,1] <= FY[-1])
    if m.sum() == 0: return None
    return np.abs(tr[m,0] - np.interp(tr[m,1], FY, FX))
def ink(tr):
    return float(np.mean([dark[int(y), max(0,int(round(x))-3):int(round(x))+4].any() for x, y in tr]))
def chain(seed_id, tol):
    cur = segs[[i for i,s in enumerate(segs) if s[0]==seed_id][0]][1].copy()
    used = {seed_id}
    order = sorted(segs, key=lambda s: s[1][:,1].min())
    ch = True
    while ch:
        ch = False
        ty, tx = cur[-1,1], cur[-1,0]
        best, bd = None, None
        for sid, p in order:
            if sid in used: continue
            if p[0,1] < ty-20 or p[0,1] > ty+160: continue
            d = abs(p[0,0]-tx)
            if d <= tol and (bd is None or d < bd): best, bd = (sid,p), d
        if best is not None:
            sid, p = best
            add = p[p[:,1] > cur[-1,1]]
            if len(add): cur = np.vstack([cur, add])
            used.add(sid); ch = True
    return cur, used
# 种子:y 最小且 meanx 近 709
cand = [(p[0,1], sid) for sid, p in segs if abs(p[:,0].mean()-709) <= 8]
seed = min(cand)[1]
print("种子 id =", seed)
print("\n== A) 种子接续 ==")
for tol in (10, 14, 18, 22, 30, 45):
    tr, used = chain(seed, tol)
    d = dev(tr)
    print("  tol=%-3d 段=%3d 点=%4d y=[%.0f,%.0f] 覆盖=%.3f 墨迹=%.3f  |差|中位=%.1f P90=%.1f 最大=%.1f"
          % (tol, len(used), len(tr), tr[0,1], tr[-1,1], (tr[-1,1]-tr[0,1])/H, ink(tr),
             np.median(d), np.percentile(d,90), d.max()))
print("\n== B) 走廊分箱 ==")
allpts = np.vstack([p for _, p in segs])
for Wd in (6, 10, 16, 25):
    sel = allpts[np.abs(allpts[:,0] - np.array([fanx(y) for y in allpts[:,1]])) <= Wd]
    if len(sel) == 0: print("  ±%-3d 无点" % Wd); continue
    ymin, ymax = sel[:,1].min(), sel[:,1].max()
    yb = np.arange(int(ymin), int(ymax)+1, 20)
    xs = []
    for a in yb:
        m = (sel[:,1] >= a) & (sel[:,1] < a+20)
        xs.append(np.median(sel[m,0]) if m.sum() else np.nan)
    xs = np.array(xs); ok = ~np.isnan(xs)
    tr = np.vstack([xs[ok], yb[ok]+10]).T
    d = dev(tr)
    print("  ±%-3d 点=%5d y=[%.0f,%.0f] 覆盖=%.3f 墨迹=%.3f |差|中位=%.1f P90=%.1f 最大=%.1f"
          % (Wd, len(sel), ymin, ymax, (ymax-ymin)/H, ink(tr), np.median(d), np.percentile(d,90), d.max()))
