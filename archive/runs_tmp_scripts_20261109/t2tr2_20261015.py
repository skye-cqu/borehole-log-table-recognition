# -*- coding: utf-8 -*-
"""1042 线[5][6][7][8] 轨迹逐段打印 + 表头带内满高竖笔精确位置。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

stem = "钻孔柱状图1042"
sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_分割线.json").read_text(encoding="utf-8"))
for i in [5, 6, 7, 8]:
    ln = sp["lines"][i]
    pts = sorted(ln["pts"], key=lambda p: p[1])
    ys = np.array([p[1] for p in pts], float); xs = np.array([p[0] for p in pts], float)
    print("=== 线[%d] %s src=%s n=%d ===" % (i, ln.get("name"), ln.get("src"), len(pts)))
    print("   _orig_ids:", ln.get("_orig_ids"))
    for y in range(800, 20600, 1500):
        print("      y=%6d x=%.0f" % (y, float(np.interp(y, ys, xs))))

g = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
b0, b1 = hm["band"]; bh = b1 - b0
print()
print("=== 表头带 [%d,%d] 逐列暗比>=0.60bh 的竖笔 (x=600..960) ===" % (b0, b1))
d = (g[b0:b1, :] < 150)
dens = d.sum(axis=0)
i = 600
while i < 960:
    if dens[i] >= 0.60 * bh:
        j = i
        while j < 960 and dens[j] >= 0.60 * bh: j += 1
        seg = dens[i:j]
        print("   x=[%d,%d] 宽=%d 最大暗比=%.2f 中心=%.1f" % (i, j-1, j-i, seg.max()/bh, i+(j-1-i)/2.0))
        i = j
    else:
        i += 1
print()
print("=== 同一剖面用 0.35bh 阈值 ===")
i = 600
while i < 960:
    if dens[i] >= 0.35 * bh:
        j = i
        while j < 960 and dens[j] >= 0.35 * bh: j += 1
        print("   x=[%d,%d] 宽=%d 最大暗比=%.2f" % (i, j-1, j-i, dens[i:j].max()/bh))
        i = j
    else:
        i += 1
