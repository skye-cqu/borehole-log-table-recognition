# -*- coding: utf-8 -*-
"""第一性原理:1.3px/2.3px 到底是"两条线"还是"同一条线被检出两次"?
在表头带内打印该邻域的暗色占比剖面:一条印刷线 = 单峰;两条线 = 双峰且中间有谷。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
RECON = paths.RUNS_DIR / "table_reconstruct"
CASES = [("钻孔柱状图1019", 385.0, 386.3), ("钻孔柱状图1042", 550.7, 553.0)]
for stem, xa, xb in CASES:
    hm = json.loads((RECON/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
    b0, b1 = hm["band"]; bh = b1-b0
    g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    bw = cv2.adaptiveThreshold(g[b0:b1], 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12)
    d_ad = (bw == 0).sum(axis=0)/float(bh)
    d_g  = (g[b0:b1] < 150).sum(axis=0)/float(bh)
    lo, hi = int(min(xa, xb))-8, int(max(xa, xb))+9
    print("\n=== %s  band=[%d,%d] bh=%d ===" % (stem, b0, b1, bh))
    print("  两条 _分割线 的 x@ymid = %.1f / %.1f  (差 %.1f)" % (xa, xb, abs(xb-xa)))
    print("  x     adap   g<150")
    for x in range(lo, hi):
        mark = ""
        if abs(x-xa) < 0.6 or abs(x-xb) < 0.6: mark = "  <== 分割线位置"
        print("  %-5d %.2f   %.2f%s" % (x, d_ad[x], d_g[x], mark))
    seg = d_ad[lo:hi]
    peaks = [lo+i for i in range(1, len(seg)-1) if seg[i] >= seg[i-1] and seg[i] >= seg[i+1] and seg[i] >= 0.5]
    print("  该邻域 adap>=0.5 的局部峰 x =", peaks, " 峰数 =", len(peaks))
    # 中间是否有谷
    mid = (lo+hi)//2
    print("  中点 x=%d 的 adap 占比 = %.2f  (若明显低于两侧峰 → 双峰/两条线)" % (mid, d_ad[mid]))
