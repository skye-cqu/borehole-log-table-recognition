# -*- coding: utf-8 -*-
"""1042 逐 y 暗色行程普查(x 100..1250):列出宽度<=10 的行程中心 = 候选列界。
同时给出表头界址 y=829 的实测,作为真值锚。"""
import sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
dark = (g < 150)

def runs_at(y, x0=100, x1=1250, wmax=10):
    row = dark[y, x0:x1]
    out, s = [], None
    for i, v in enumerate(row):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s <= wmax: out.append((x0 + (s + i - 1) / 2.0, i - s))
            s = None
    if s is not None and len(row) - s <= wmax: out.append((x0 + (s + len(row) - 1) / 2.0, len(row) - s))
    return out

print("== 表头带内 y=829 的行程(宽<=10) ==")
print("  " + "  ".join("%.0f(w%d)" % t for t in runs_at(829)))
print("\n== 各 y 的行程中心 ==")
for y in range(1000, min(H, 19900), 1000):
    print("y=%-6d " % y + "  ".join("%.0f" % c for c, w in runs_at(y)))
print("\n== 定点追踪:各 y 处最接近 551.9 / 632.7 / 709 的行程 ==")
for y in range(900, min(H, 19900), 1000):
    rr = runs_at(y)
    if not rr: continue
    cs = np.array([c for c, w in rr])
    ws = [w for c, w in rr]
    line = "y=%-6d " % y
    for tgt in (551.9, 632.7, 709.0):
        k = int(np.argmin(np.abs(cs - tgt)))
        line += "  tgt%.0f->%.1f(w%d,d%+.1f)" % (tgt, cs[k], ws[k], cs[k] - tgt)
    print(line)
