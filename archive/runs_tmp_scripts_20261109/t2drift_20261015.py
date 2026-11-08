# -*- coding: utf-8 -*-
"""漂移走廊真值检验:以相邻已核验界(551.9 采长|倾角, 913 柱状|岩性)的实测 x(y)
估计统一漂移 d(y),预测 709 的位置,逐 y 测墨迹;再找该处阶段4 候选段做贴合。"""
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
d = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_分割线.json").read_text(encoding="utf-8"))
def get(idx):
    p = np.asarray(d["lines"][idx]["pts"], float); p = p[np.argsort(p[:,1])]
    return p[:,0], p[:,1]
xL, yL = get(6)   # 采长|倾角  550.7
xR, yR = get(9)   # 柱状|岩性  912.0
y0, y1 = int(max(yL.min(), yR.min())), int(min(yL.max(), yR.max()))
yy = np.arange(y0, y1+1)
# 锚定 y=829 的表头实测界址
A_L, A_R, A_T = 551.9, 913.0, 709.0
dL = np.interp(yy, yL, xL) - A_L
dR = np.interp(yy, yR, xR) - A_R
drift = (dL + dR) / 2.0
pred = A_T + drift
print("漂移 d(y):  y=%d:%.1f  y=%d:%.1f  y=%d:%.1f  y=%d:%.1f" % (
    y0, drift[0], y0+5000, np.interp(y0+5000,yy,drift), y0+10000, np.interp(y0+10000,yy,drift), y1, drift[-1]))
hit6 = np.array([dark[y, max(0,int(round(x))-6):int(round(x))+7].any() for y, x in zip(yy, pred)])
print("预测路径墨迹命中 ±6px = %.4f   ±3px = %.4f" % (
    hit6.mean(),
    np.mean([dark[y, max(0,int(round(x))-3):int(round(x))+4].any() for y, x in zip(yy, pred)])))
runs, s = [], None
for i, v in enumerate(hit6):
    if not v and s is None: s = i
    elif v and s is not None: runs.append((int(yy[s]), int(yy[i-1]), i-s)); s = None
if s is not None: runs.append((int(yy[s]), int(yy[-1]), len(hit6)-s))
print("未命中总长=%d/%d  最长段 top6=%s" % (int((~hit6).sum()), len(hit6),
      sorted(runs, key=lambda r:-r[2])[:6]))
# 阶段4 候选贴合率
cj = json.loads((paths.CANDIDATE_COORD_DIR/f"{STEM}.json").read_text(encoding="utf-8"))
pts = []
for sg in cj["lines"]:
    if sg["direction"] != "vertical" or sg["label"] != "high": continue
    for x, y in sg["points"]:
        if y0-200 <= y <= y1+200: pts.append((float(x), float(y)))
pts = np.array(pts)
print("阶段4 竖/高候选点(在区间内) =", len(pts))
snap = np.array([np.min(np.abs(pts[:,0] - x)) if len(pts) else 1e9 for x in pred])
for tol in (5, 10, 20, 30, 45):
    print("  走廊 ±%dpx 内有候选点的 y 占比 = %.4f" % (tol, (snap <= tol).mean()))
