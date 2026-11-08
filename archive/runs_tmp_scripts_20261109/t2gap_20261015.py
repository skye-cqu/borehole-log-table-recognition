# -*- coding: utf-8 -*-
"""第一性原理:正确列界必落在"字间空隙"上,不得穿过字。
做法:表头带内把竖线像素剔除,剩下的就是字墨;求字墨投影的零墨间隙。
"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

RECON = paths.RUNS_DIR/"table_reconstruct"
stem = "钻孔柱状图1042"
hm = json.loads((RECON/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
y0, y1 = int(hm["band"][0]), int(hm["band"][1])
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
sub = g[y0:y1]
dark = (sub < 140)

# 剔竖线:某列在带内暗占比 >=0.45 视为线,连同 ±1 邻列一并剔除
colfrac = dark.mean(axis=0)
isline = colfrac >= 0.45
linecols = np.zeros_like(isline)
for x in np.where(isline)[0]:
    linecols[max(0,x-1):x+2] = True
glyph = dark.copy()
glyph[:, linecols] = False
print("== 表头带 y=[%d,%d] 高=%d ==" % (y0, y1, y1-y0))
print("剔除的线列数 =", int(linecols.sum()))
prof = glyph.sum(axis=0)
print("字墨总量 =", int(prof.sum()))
print()
# 零墨间隙
gaps = []
i = 0
W = len(prof)
while i < W:
    if prof[i] == 0:
        j = i
        while j < W and prof[j] == 0: j += 1
        if j - i >= 8: gaps.append((i, j, (i+j)//2, j-i))
        i = j
    else: i += 1
print("== 零墨间隙(宽>=8px) 共 %d 个 ==" % len(gaps))
seps = sorted(hm["sep_x_band"])
for a, b, c, w in gaps:
    if c > 1100: continue
    near = [s for s in seps if a-4 <= s <= b+4]
    print("   x=[%4d,%4d] 中心=%-5d 宽=%-3d  %s" % (a, b, c, w,
          ("<- sep_x_band 命中 %.1f" % near[0]) if near else "<- sep_x_band 无"))
print()
print("== sep_x_band 每条落在间隙里还是穿过字? ==")
for s in seps:
    if s > 1100: continue
    sx = int(round(s))
    # 该 x 附近字墨量(±2)
    lo, hi = max(0, sx-2), min(W, sx+3)
    ink = int(prof[lo:hi].sum())
    gap = [gg for gg in gaps if gg[0]-2 <= sx <= gg[1]+2]
    print("   sep=%-8.1f 附近字墨=%-6d %s" % (s, ink,
          ("落在间隙 x=[%d,%d]" % (gap[0][0], gap[0][1])) if gap else "**穿过字墨**"))
