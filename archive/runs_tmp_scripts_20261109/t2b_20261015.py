# -*- coding: utf-8 -*-
"""构造法对比(以 t2_fan709 = 墨迹拟合真值为裁判):
 B1 走廊内阶段4候选点按y分箱取中位
 B2 走廊内逐y吸附到最近的细墨迹行程
走廊 = 709 + d(y), d(y) = 已核验 _分割线 各线相对其表头位置的偏移中位数。"""
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
fan = np.load(str(R/"runs/tmp/t2_fan709_20261015.npy")); FY, FX = fan[:,0], fan[:,1]
d = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_分割线.json").read_text(encoding="utf-8"))
HDR = {2:196.7, 3:260.2, 4:384.5, 5:468.7, 6:551.9, 8:632.7, 9:912.0}
off = []
for i, hx in HDR.items():
    p = np.asarray(d["lines"][i]["pts"], float); p = p[np.argsort(p[:,1])]
    off.append((p[:,1], p[:,0] - hx))
yy = np.arange(760, 19740)
D = np.vstack([np.interp(yy, o[0], o[1]) for o in off])
dmed = np.median(D, axis=0)
corr = 709.0 + dmed
print("走廊 d(y): y=1000 %.0f  y=6000 %.0f  y=10000 %.0f  y=15000 %.0f  y=19000 %.0f" % tuple(
    np.interp(t, yy, dmed) for t in (1000,6000,10000,15000,19000)))
print("与扇形真值 d 对比: y=1000 %.0f/%.0f  y=6000 %.0f/%.0f  y=10000 %.0f/%.0f  y=19000 %.0f/%.0f" % (
    2, np.interp(1000,yy,dmed), 47, np.interp(6000,yy,dmed), 64, np.interp(10000,yy,dmed),
    128, np.interp(19000,yy,dmed)))

def evalpath(tag, yv, xv):
    m = (yv >= FY[0]) & (yv <= FY[-1])
    dev = np.abs(xv[m] - np.interp(yv[m], FY, FX))
    ink = np.mean([dark[int(y), max(0,int(round(x))-3):int(round(x))+4].any() for x, y in zip(xv, yv)])
    # 覆盖率:插值后逐 y 有值
    print("  %-22s 点=%4d y=[%.0f,%.0f] 覆盖=%.3f 墨迹=%.3f |差|中位=%.1f P90=%.1f 最大=%.1f" % (
        tag, len(yv), yv[0], yv[-1], (yv[-1]-yv[0])/(FY[-1]-FY[0]), ink,
        np.median(dev), np.percentile(dev,90), dev.max()))

# B1
cj = json.loads((paths.CANDIDATE_COORD_DIR/f"{STEM}.json").read_text(encoding="utf-8"))
pts = []
for s in cj["lines"]:
    if s["direction"] != "vertical" or s["label"] != "high": continue
    for x, y in s["points"]: pts.append((float(x), float(y)))
pts = np.array(pts)
print("\n== B1 走廊内阶段4候选分箱 ==")
for Wd in (4, 6, 10, 16, 25, 40):
    sel = pts[np.abs(pts[:,0] - np.interp(pts[:,1], yy, corr)) <= Wd]
    yb = np.arange(760, 19740, 20); xs = []
    for a in yb:
        m = (sel[:,1] >= a) & (sel[:,1] < a+20)
        xs.append(np.median(sel[m,0]) if m.sum() else np.nan)
    xs = np.array(xs); ok = ~np.isnan(xs)
    evalpath("B1 ±%d 点=%d" % (Wd, len(sel)), yb[ok]+10, xs[ok])

# B2
def thin_runs(y, x0=90, x1=1210, wmax=5):
    row = dark[y, x0:x1]; out = []; s = None
    for i, v in enumerate(row):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s <= wmax: out.append(x0 + (s + i - 1) / 2.0)
            s = None
    if s is not None and len(row) - s <= wmax: out.append(x0 + (s + len(row) - 1) / 2.0)
    return np.array(out)
print("\n== B2 逐y吸附细行程 ==")
for Wd in (4, 6, 10, 16, 25):
    yv, xv = [], []
    for y, c in zip(yy, corr):
        rr = thin_runs(int(y))
        if len(rr) == 0: continue
        k = int(np.argmin(np.abs(rr - c)))
        if abs(rr[k] - c) <= Wd: yv.append(y); xv.append(rr[k])
    if len(yv) > 10: evalpath("B2 ±%d" % Wd, np.array(yv), np.array(xv))
