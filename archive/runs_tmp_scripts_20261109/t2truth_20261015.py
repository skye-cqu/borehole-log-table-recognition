# -*- coding: utf-8 -*-
"""1042: (a)表头文字簇中心 (b)709 链碎片归属 (c)带标尺表头大图。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/"钻孔柱状图1042_表头映射.json").read_text(encoding="utf-8"))
sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/"钻孔柱状图1042_分割线.json").read_text(encoding="utf-8"))
g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)

band = hm["band"]; y0, y1 = band
bw = cv2.adaptiveThreshold(g[y0:y1], 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12)
dens = (bw == 0).sum(axis=0); bh = y1-y0
txt = (dens >= 3) & (dens < 0.65*bh)
clusters = []
for i, v in enumerate(txt):
    if v and clusters and i - clusters[-1][-1] <= 14: clusters[-1].append(i)
    elif v: clusters.append([i])
centers = [(gr[0], gr[-1], (gr[0]+gr[-1])/2) for gr in clusters if len(gr) >= 8]
print("== 表头文字簇(宽度>=8) ==")
for a, b, c in centers:
    print("   x=[%-5d,%-5d] 宽=%-4d 中心=%.0f" % (a, b, b-a, c))
print()
print("== 满高竖笔(占比>=0.40) ==")
hh = y1-y0
lines_found = []
for x in range(1, g.shape[1]-1):
    f = float((g[y0:y1, x] < 140).mean())
    if f >= 0.40: lines_found.append(x)
grps = []
for x in lines_found:
    if grps and x - grps[-1][-1] <= 3: grps[-1].append(x)
    else: grps.append([x])
for gp in grps:
    if gp[0] < 1100:
        print("   x=%-5.0f 宽=%d" % (np.mean(gp), len(gp)))

print()
print("== 709 链碎片 id 是否已被 _分割线.json 收录 ==")
targets = {23397, 22527, 22528, 25820, 37989, 6275, 6249, 6261, 6236, 28613}
for i, ln in enumerate(sp["lines"]):
    ids = set(ln.get("_orig_ids") or [])
    hit = ids & targets
    if hit:
        print("   [%2d] name=%-11s 命中 %s" % (i, str(ln.get("name")), sorted(hit)))
print("   (若某 id 未出现在任何行 → 该碎片在阶段5/6 被丢)")
allids = set()
for ln in sp["lines"]: allids |= set(ln.get("_orig_ids") or [])
print("   _分割线 全部 orig_ids 数 =", len(allids))
for t in sorted(targets):
    print("     id=%-7d %s" % (t, "已收录" if t in allids else "**未收录**"))

# 大图
x0, x1 = 60, 980
sc = 3
sub = g[735:930, x0:x1]
c = cv2.resize(cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR), ((x1-x0)*sc, (930-735)*sc), interpolation=cv2.INTER_NEAREST)
img = Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img)
for x in range(x0, x1, 10):
    px = (x-x0)*sc
    maj = (x % 50 == 0)
    d.line([(px, 0), (px, 30 if maj else 14)], fill=(255,0,0) if maj else (0,160,255), width=1)
    d.line([(px, c.shape[0]-30 if maj else c.shape[0]-14), (px, c.shape[0])], fill=(255,0,0) if maj else (0,160,255), width=1)
    if maj: d.text((px+2, 32), str(x), fill=(220,0,0))
    if maj: d.text((px+2, c.shape[0]-46), str(x), fill=(220,0,0))
p = R/"runs/tmp/t2_hdrwide_20261015.png"
img.save(p); print(); print("saved", p, img.size)
