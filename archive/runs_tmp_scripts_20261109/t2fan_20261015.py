# -*- coding: utf-8 -*-
"""扇形模型真值:x_true(y) = A + d(x,y), d 在表头界址间线性插值(dL..dR)。
用 8 条表头界址做最小二乘拟合,逐 y 检验墨迹;再与种子链 709 比对。"""
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
def get(i):
    p = np.asarray(d["lines"][i]["pts"], float); p = p[np.argsort(p[:,1])]
    return p[:,0], p[:,1]
xL, yL = get(6); xR, yR = get(9)
A = np.array([196.7, 260.2, 384.5, 468.7, 551.9, 632.7, 709.0, 913.0])
y0, y1 = int(max(yL.min(), yR.min())), int(min(yL.max(), yR.max()))
yy = np.arange(y0, y1+1)
dL = np.interp(yy, yL, xL) - 551.9
dR = np.interp(yy, yR, xR) - 913.0
def pred_at(y_arr, a):
    """扇形插值:界址 a 在 y 处的预测 x。"""
    t = (a - 551.9) / (913.0 - 551.9)
    return a + (dL + (dR - dL) * t)

def thin_runs(y, x0=90, x1=1200, wmax=4):
    row = dark[y, x0:x1]; out = []; s = None
    for i, v in enumerate(row):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s <= wmax: out.append(x0 + (s + i - 1) / 2.0)
            s = None
    if s is not None and len(row) - s <= wmax: out.append(x0 + (s + len(row) - 1) / 2.0)
    return np.array(out)

# 8 界逐一验墨
print("扇形模型:各表头界在各 y 的墨迹命中率(±4px 内存在细行程)")
for k, a in enumerate(A):
    p = pred_at(yy, a)
    hit = []
    for y, x in zip(yy, p):
        rr = thin_runs(int(y))
        hit.append(bool(len(rr) and np.min(np.abs(rr - x)) <= 4))
    print("  %6.1f 命中 %.4f" % (a, np.mean(hit)))

# 与种子链 709 比对
tr = np.load(str(R/"runs/tmp/t2_chain_709_20261015.npy"))
tr = tr[np.argsort(tr[:,1])]
ty = tr[:,1]; tx = tr[:,0]
m = (ty >= yy[0]) & (ty <= yy[-1])
pv = pred_at(ty[m], 709.0)
print("\n种子链 709 vs 扇形真值: 中位偏差 %.1f px  最大 %.1f  点=%d" % (
    np.median(np.abs(tx[m]-pv)), np.abs(tx[m]-pv).max(), m.sum()))
for y in range(1000, 19000, 2000):
    k = int(np.argmin(np.abs(ty-y)))
    print("   y=%-6d 链=%.0f  扇形真值=%.0f  差=%+.0f" % (y, tx[k], pred_at(np.array([ty[k]]),709.0)[0], tx[k]-pred_at(np.array([ty[k]]),709.0)[0]))
np.save(str(R/"runs/tmp/t2_fan_20261015.npy"), np.vstack([yy, pred_at(yy, 709.0)]).T)
