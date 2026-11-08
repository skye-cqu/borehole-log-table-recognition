# -*- coding: utf-8 -*-
"""1042 决定性:表头带全宽真实满高竖笔 vs 实际使用的 sep_x_band 11 条。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/"钻孔柱状图1042_表头映射.json").read_text(encoding="utf-8"))
print("== _表头映射.json ==")
print("band =", hm["band"], " header_src =", hm["header_src"])
print("sep_x_band =", [round(v,1) for v in hm["sep_x_band"]])
print("label_verify =", json.dumps(hm.get("label_verify"), ensure_ascii=False))
print("warnings =", json.dumps(hm.get("warnings"), ensure_ascii=False)[:400])
print()
print("== sep_pts 明细 ==")
for i, sp in enumerate(hm["sep_pts"]):
    ys = np.array(sp["ys"], float); xs = np.array(sp["xs"], float)
    print("  [%2d] kind=%-8s index=%-3s side=%-4s n=%-4d y=[%.0f,%.0f] x@顶=%.0f x@中=%.0f x@底=%.0f x范围=[%.0f,%.0f]" % (
        i, sp["kind"], sp["index"], sp["side"], len(ys), ys.min(), ys.max(),
        xs[0], xs[len(xs)//2], xs[-1], xs.min(), xs.max()))

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 140).astype(np.uint8)
H, W = g.shape
y0, y1 = int(hm["band"][0]), int(hm["band"][1])
print()
print("== 表头带 y=[%d,%d] 全宽满高竖笔(暗像素占比>=40%%) ==" % (y0, y1))
hh = y1 - y0
found = []
for x in range(1, W-1):
    frac = float(ink[y0:y1, x].mean())
    if frac >= 0.40:
        found.append((x, frac))
# 合并相邻
groups = []
for x, f in found:
    if groups and x - groups[-1][-1][0] <= 3: groups[-1].append((x, f))
    else: groups.append([(x, f)])
print("满高竖笔 %d 组:" % len(groups))
for gp in groups:
    xs = [a for a, _ in gp]; fs = [b for _, b in gp]
    print("   x=%-6.0f (宽%d, 占比%.2f) %s" % (np.mean(xs), len(gp), max(fs),
          "  <-- sep_x_band 有" if any(abs(np.mean(xs)-v) <= 4 for v in hm["sep_x_band"]) else "  <-- sep_x_band 无!"))
print()
print("== sep_x_band 每条能否在满高竖笔里找到(容差4px) ==")
for v in hm["sep_x_band"]:
    hit = [np.mean([a for a,_ in gp]) for gp in groups if abs(np.mean([a for a,_ in gp]) - v) <= 4]
    print("   sep %-8.1f -> %s" % (v, ("命中 x=%.0f" % hit[0]) if hit else "**无对应满高竖笔**"))
