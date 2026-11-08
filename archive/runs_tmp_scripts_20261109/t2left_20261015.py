# -*- coding: utf-8 -*-
"""1042 x=137 定性 + 全30张"内容未检出"普查。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
RECON = paths.RUNS_DIR/"table_reconstruct"

print("== 全30张 _表头映射.json 的 warnings 普查 ==")
for p in sorted(RECON.glob("*_表头映射.json")):
    hm = json.loads(p.read_text(encoding="utf-8"))
    ws = hm.get("warnings") or []
    key = [w for w in ws if ("未检出" in w or "超出预期" in w or "落在所有格之外" in w or "重复列名" in w)]
    if key:
        print("  %-21s src=%-11s ok=%-5s %s" % (p.name.replace("_表头映射.json",""), hm.get("header_src"), hm.get("ok"), key))

print()
print("== 1042 x=137 的墨迹覆盖(全表/表头带/数据带) ==")
g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
hm = json.loads((RECON/"钻孔柱状图1042_表头映射.json").read_text(encoding="utf-8"))
y0, y1 = hm["band"]
for lo, hi, nm in [(0, H, "全图"), (y0, y1, "表头带"), (1000, 4000, "表头下方"), (4000, 12000, "中段"), (12000, 19700, "下段")]:
    d = (g[int(lo):int(hi)] < 140)
    print("  %s y=[%d,%d]: x=135:%.2f x=136:%.2f x=137:%.2f x=138:%.2f x=139:%.2f" % (
        nm, lo, hi, *[float(d[:, x].mean()) for x in (135,136,137,138,139)]))
print("  邻域最大覆盖 x∈[125,205]:")
d = (g < 140)
best = [(x, float(d[:, x].mean())) for x in range(125, 206)]
best.sort(key=lambda t: -t[1])
print("    " + "  ".join("x=%d:%.2f" % b for b in best[:10]))

# 裁片
outs = []
for xa, xb, ya, yb, sc, lb in [(40, 320, 700, 1010, 5, "表头左区 y=[700,1010]"),
                               (40, 320, 4000, 4400, 5, "数据行左区 y=[4000,4400]")]:
    sub = g[ya:yb, xa:xb]
    c = cv2.resize(cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR), ((xb-xa)*sc, (yb-ya)*sc), interpolation=cv2.INTER_NEAREST)
    outs.append([c, xa, xb, ya, yb, sc, lb])
Wt = max(o[0].shape[1] for o in outs) + 70
Ht = sum(o[0].shape[0] for o in outs) + 70*len(outs) + 30
canvas = np.full((Ht, Wt, 3), 255, np.uint8)
yy = 30
for c, xa, xb, ya, yb, sc, lb in outs:
    canvas[yy:yy+c.shape[0], 70:70+c.shape[1]] = c; yy += c.shape[0] + 70
img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
d2 = ImageDraw.Draw(img)
yy = 30
for c, xa, xb, ya, yb, sc, lb in outs:
    h = c.shape[0]
    for x in range(xa, xb, 10):
        px = 70 + (x-xa)*sc
        maj = (x % 50 == 0)
        d2.line([(px, yy-14 if maj else yy-8), (px, yy+h)], fill=(230,0,0) if maj else (150,200,255), width=1)
        if maj: d2.text((px+2, yy-26), str(x), fill=(200,0,0))
    d2.text((2, yy+h+4), lb, fill=(0,0,180))
    yy += h + 70
p = R/"runs/tmp/t2_left_20261015.png"
img.save(p); print(); print("saved", p, img.size)
