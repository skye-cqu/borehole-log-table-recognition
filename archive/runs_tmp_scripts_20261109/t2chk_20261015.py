# -*- coding: utf-8 -*-
"""墨迹验证接续:段间桥接须由真实墨迹支撑(AGENTS 数据源神圣:阶段4段+桥接+墨迹外延)。
与扇形墨迹真值(t2_fan709)比对,判定能否复现 709 界全高折线。"""
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
fan = np.load(str(R/"runs/tmp/t2_fan709_20261015.npy")); FY, FX = fan[:,0], fan[:,1]

def ink_chord(p0, p1, tol=4, need=0.90, n=40):
    y0, y1 = float(p0[1]), float(p1[1])
    if y1 <= y0: return False
    ys = np.linspace(y0, y1, n)
    xs = np.linspace(float(p0[0]), float(p1[0]), n)
    h = sum(1 for y, x in zip(ys, xs) if dark[int(y), max(0,int(x)-tol):int(x)+tol+1].any())
    return h / n >= need

def chain(seed_id, tol, gap_max, ink_tol, ink_need):
    cur = segs[[i for i,s in enumerate(segs) if s[0]==seed_id][0]][1].copy()
    used = {seed_id}
    order = sorted(segs, key=lambda s: s[1][:,1].min())
    while True:
        ty, tx = cur[-1,1], cur[-1,0]
        best, bd = None, None
        for sid, p in order:
            if sid in used: continue
            if p[0,1] < ty-20 or p[0,1] > ty+gap_max: continue
            d = float(np.hypot(p[0,0]-tx, p[0,1]-ty))
            if d > tol: continue
            if not ink_chord((tx,ty), (p[0,0],p[0,1]), ink_tol, ink_need): continue
            if bd is None or d < bd: best, bd = (sid,p), d
        if best is None: break
        sid, p = best
        add = p[p[:,1] > cur[-1,1]]
        if len(add): cur = np.vstack([cur, add])
        used.add(sid)
    return cur, used

def report(tag, tr, used):
    m = (tr[:,1] >= FY[0]) & (tr[:,1] <= FY[-1])
    d = np.abs(tr[m,0] - np.interp(tr[m,1], FY, FX))
    ink = np.mean([dark[int(y), max(0,int(round(x))-3):int(round(x))+4].any() for x, y in tr])
    print("  %-28s 段=%3d 点=%4d y=[%.0f,%.0f] 覆盖=%.3f 墨迹=%.3f |差|中位=%.1f P90=%.1f 最大=%.1f"
          % (tag, len(used), len(tr), tr[0,1], tr[-1,1], (tr[-1,1]-tr[0,1])/H, ink,
             np.median(d), np.percentile(d,90), d.max()))

cand = [(p[0,1], sid) for sid, p in segs if abs(p[:,0].mean()-709) <= 8]
seed = min(cand)[1]
print("种子 id =", seed, " 种子点 y=[%.0f,%.0f] x~%.0f" % (
    segs[[i for i,s in enumerate(segs) if s[0]==seed][0]][1][0,1],
    segs[[i for i,s in enumerate(segs) if s[0]==seed][0]][1][-1,1],
    segs[[i for i,s in enumerate(segs) if s[0]==seed][0]][1][:,0].mean()))
print("\n== 无墨迹校验(基线) ==")
report("tol=45 无校验", *chain(seed, 45, 160, 4, 0.0))
print("\n== 墨迹校验接续 ==")
for tol, gm, it, inn in ((45,160,4,0.90),(60,200,4,0.90),(60,200,6,0.85),
                          (90,220,6,0.85),(120,260,8,0.80),(60,200,4,0.70)):
    report("tol=%d gap=%d ink±%d>=%.2f" % (tol,gm,it,inn), *chain(seed, tol, gm, it, inn))
