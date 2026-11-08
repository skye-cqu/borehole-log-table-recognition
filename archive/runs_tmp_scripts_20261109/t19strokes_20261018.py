# -*- coding: utf-8 -*-
"""1019 表头带满高竖笔普查 + 与既有界比对,查 真厚|柱状 界(~903)是否漏检。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1019"
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_表头映射.json").read_text(encoding="utf-8"))
b0, b1 = hm["band"]; bh = b1 - b0
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
print("band=[%d,%d] bh=%d  图 %dx%d" % (b0, b1, bh, W, H))
dens = (g[b0:b1] < 150).sum(axis=0)
print("\n== 满高竖笔 (占比>=0.60, 宽<=3) ==")
i = 0
while i < W:
    if dens[i] >= 0.60*bh:
        j = i
        while j < W and dens[j] >= 0.60*bh: j += 1
        if j - i <= 3:
            print("  x=%d  占比=%.2f 宽=%d" % (i+int(np.argmax(dens[i:j])), dens[i:j].max()/bh, j-i))
        else:
            print("  [宽块 x=%d..%d 占比=%.2f] 非竖线" % (i, j-1, dens[i:j].max()/bh))
        i = j
    else:
        i += 1
print("\n== 0.40~0.60 之间的弱竖笔 ==")
i = 0
while i < W:
    if dens[i] >= 0.40*bh:
        j = i
        while j < W and dens[j] >= 0.40*bh: j += 1
        v = dens[i:j].max()/bh
        if v < 0.60 and j-i <= 4:
            print("  x=%d  占比=%.2f 宽=%d" % (i+int(np.argmax(dens[i:j])), v, j-i))
        i = j
    else:
        i += 1
print("\n== 现有界 ==", hm.get("sep_x_band"))
