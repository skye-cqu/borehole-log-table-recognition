# -*- coding: utf-8 -*-
"""1042 表头区原始灰度剖查:找那条竖线到底在哪个 x,灰度多少。"""
import sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
print("全图灰度: min=%d max=%d mean=%.1f" % (g.min(), g.max(), g.mean()))

def probe(y0, y1, x0, x1, label, topn=14):
    sub = g[y0:y1, x0:x1]
    dark = (sub < 128).sum(axis=0)          # 每列暗像素数
    order = np.argsort(-dark)[:topn]
    print()
    print("== %s  y=[%d,%d] x=[%d,%d]  带高=%d ==" % (label, y0, y1, x0, x1, y1-y0))
    print("   每列暗像素数 top%d:" % topn)
    for i in sorted(order):
        print("     x=%-5d 暗=%-4d 最小灰度=%d" % (x0+i, dark[i], sub[:, i].min()))

probe(747, 911, 600, 1000, "表头带")
probe(750, 1400, 600, 1000, "表头带+首行")
probe(1000, 3000, 600, 1000, "数据区上段")

print()
print("== 逐列最小灰度(x=650..800, y=[747,911]) ==")
sub = g[747:911, 650:800]
mn = sub.min(axis=0)
for i in range(0, 150, 1):
    if mn[i] < 200:
        print("   x=%-5d min=%d" % (650+i, mn[i]))
