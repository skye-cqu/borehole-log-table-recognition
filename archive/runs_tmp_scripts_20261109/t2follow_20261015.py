# -*- coding: utf-8 -*-
"""1042:自表头向下逐点跟踪竖线(小窗口,抗漂移),判定哪些是真列界。
与 1033 修复同法:窗口内墨峰,连续跟踪。"""
import sys, json
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 140).astype(np.uint8)
H, W = g.shape

def frac_at(y, x, dy=7):
    x0, x1 = max(0, x-1), min(W, x+2)
    return float(ink[y:y+dy, x0:x1].max(axis=1).mean())

def track(x0, y0=980, y1=19700, dy=8, win=9, need=0.55):
    prev = float(x0); out = []
    for y in range(y0, y1, dy):
        best, bx = -1.0, prev
        for x in range(int(prev)-win, int(prev)+win+1):
            if x < 1 or x >= W-1: continue
            f = frac_at(y, x, dy)
            if f > best: best, bx = f, float(x)
        if best >= need:
            prev = bx
            out.append((y, prev, best))
        else:
            out.append((y, prev, -best))     # 负号=缺失
    return out

seeds = [553, 633, 665, 709, 745, 790, 912, 950]
print("== 自 y=980 向下跟踪(窗口±9, 需墨>=0.55) ==")
res = {}
for s in seeds:
    t = track(s)
    xs = [p[1] for p in t]; miss = sum(1 for p in t if p[2] < 0)
    # 最长缺失段
    run = best = 0
    for p in t:
        run = run+1 if p[2] < 0 else 0
        best = max(best, run)
    res[s] = t
    print("  seed=%-4d 段数=%-4d 缺失=%-4d(%.0f%%) 最长缺失=%-3d段  x: 顶=%.0f 中=%.0f 底=%.0f 范围=[%.0f,%.0f]" % (
        s, len(t), miss, 100.0*miss/len(t), best, xs[0], xs[len(xs)//2], xs[-1], min(xs), max(xs)))

print()
print("== 各 seed 跟踪曲线采样(y: x) ==")
for s in seeds:
    t = res[s]
    pts = [t[i] for i in range(0, len(t), max(1, len(t)//12))]
    print("  seed=%-4d %s" % (s, "  ".join("%d:%s%.0f" % (p[0], "" if p[2]>=0 else "x", p[1]) for p in pts)))
