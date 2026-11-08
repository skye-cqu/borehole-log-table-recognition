# -*- coding: utf-8 -*-
"""验证:1042 表头带满高竖笔(0.60) 全列 + 真厚/柱状 真实列界落点。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/"钻孔柱状图1042_表头映射.json").read_text(encoding="utf-8"))
b0, b1 = hm["band"]; bh = b1 - b0
dens = (g[b0:b1, :] < 150).sum(axis=0)
print("表头带 [%d,%d] 满高竖笔 (暗比>=0.60, 全宽):" % (b0, b1))
i, W = 0, g.shape[1]
while i < W:
    if dens[i] >= 0.60 * bh:
        j = i
        while j < W and dens[j] >= 0.60 * bh: j += 1
        if j - i <= 3:
            print("   x=%-6d 宽=%d 暗比=%.2f" % (i + int(np.argmax(dens[i:j])), j-i, dens[i:j].max()/bh))
        i = j
    else: i += 1
print()
print("已采用 sep_x_band:", hm["sep_x_band"])
print("keep 列名/几何:")
for c in hm["keep"]:
    print("   %-8s left_sep=%-3s right_sep=%-3s x=%-22s 宽=%.1f"
          % (c["name"], c["left_sep"], c["right_sep"], str(c["x_in_band"]), c["width"]))
print()
print("警告:", hm["warnings"])
