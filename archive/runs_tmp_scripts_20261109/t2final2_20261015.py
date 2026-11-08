# -*- coding: utf-8 -*-
"""1042 定案:(a)表头字形簇+逐簇OCR (b)阶段4 high 链在 x=137/709 的 y 覆盖。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
sys.path.insert(0, str(R/"src"))
from src.table.header_assign import _get_ocr, _cell_text, match_name

stem = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
y0, y1 = int(hm["band"][0]), int(hm["band"][1])
band = (y0, y1)
dark = (g[y0:y1] < 140)
cov = dark.mean(axis=0)

print("== (a) 表头带 y=[%d,%d] 字形簇 (剔除 cov>=0.35 的线列) ==" % (y0, y1))
linecols = cov >= 0.35
glyph = dark.copy(); glyph[:, linecols] = False
prof = glyph.sum(axis=0)
cl, i = [], 0
while i < W:
    if prof[i] > 0:
        j = i
        while j < W and prof[j] > 0: j += 1
        if j - i >= 5: cl.append((i, j))
        i = j
    else: i += 1
ocr = _get_ocr()
print("字形簇 %d 个(仅列 x<1300):" % len(cl))
for a, b in cl:
    if a >= 1300: continue
    t = _cell_text(ocr, g, band, float(a), float(b))
    print("   x=[%4d,%4d] 宽=%-4d OCR=%-24r match=%s" % (a, b, b-a, t, match_name(t)))

print()
print("== (b) 阶段4 high 链在 x=137 / 709 附近的 y 覆盖 ==")
cj = json.loads((paths.CANDIDATE_COORD_DIR/f"{stem}.json").read_text(encoding="utf-8"))
vs = [s for s in cj["lines"] if s.get("direction")=="vertical" and s.get("label")=="high"]
rj = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_行判定.json").read_text(encoding="utf-8"))
rys = [r["poly"][-1][1] for r in rj["rows"]]
top, bot = min(rys), max(rys)
print("表格 y 范围 = [%.0f,%.0f]" % (top, bot))
for lo, hi, nm in [(125,200,"x≈137(→173数据行)"), (695,735,"x≈709(→745数据行)"), (540,570,"x≈550/553")]:
    segs = []
    for s in vs:
        pts = np.array(s.get("points") or [], float)
        if len(pts) < 2: continue
        xm = float(np.median(pts[:,0]))
        if lo <= xm <= hi:
            segs.append((float(pts[:,1].min()), float(pts[:,1].max()), xm, s.get("id")))
    segs.sort()
    if not segs:
        print("  %s: 无候选" % nm); continue
    # 合并 y 区间
    merged = []
    for a, b, xm, sid in segs:
        if merged and a <= merged[-1][1] + 40: merged[-1][1] = max(merged[-1][1], b); merged[-1][2] += 1
        else: merged.append([a, b, 1])
    tot = sum(b-a for a, b, _ in merged)
    print("  %s: 候选 %d 条 → 合并 %d 段, y 覆盖 %.0f/%.0f = %.1f%%" % (
        nm, len(segs), len(merged), tot, bot-top, 100.0*tot/(bot-top)))
    for a, b, n in merged[:8]:
        print("       y=[%6.0f,%6.0f] (%d条)" % (a, b, n))
    if len(merged) > 8: print("       ... 共 %d 段" % len(merged))
