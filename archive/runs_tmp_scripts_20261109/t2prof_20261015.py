# -*- coding: utf-8 -*-
"""表头带竖线剖面:用管线自身的 adaptiveThreshold 口径,对比 gray<150 口径。

判据:真分隔线应在带内近乎满高;文字竖笔只占带高一小部分。
"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
stem = sys.argv[1]
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
b0, b1 = hm["band"]; bh = b1 - b0
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
bw = cv2.adaptiveThreshold(g[b0:b1], 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                           cv2.THRESH_BINARY, 31, 12)
d_ad = (bw == 0).sum(axis=0) / float(bh)
d_g150 = (g[b0:b1] < 150).sum(axis=0) / float(bh)
print("stem=%s band=[%d,%d] bh=%d" % (stem, b0, b1, bh))
print("  x     adap  g<150")
for x in range(120, 1400):
    if max(d_ad[x], d_g150[x]) >= 0.35:
        print("  %-5d %.2f  %.2f" % (x, d_ad[x], d_g150[x]))
