# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.table import era_chars as E
import numpy as np

print("图    行y范围       时代列左sep y跨度      右sep y跨度      左cov   右cov   PF1")
for k in ["1017","1020","1023","1025","1028","1030","1042"]:
    stem = f"钻孔柱状图{k}"
    hm, rd = E._load_inputs(stem)
    midx = sum(rd["table_x"])/2.0
    ys = [E.row_y(r, midx) for r in rd["rows"]]
    y0, y1 = min(ys), max(ys); span = y1-y0
    sp_l = hm["sep_pts"][hm["keep"][0]["left_sep"]]
    sp_r = hm["sep_pts"][hm["keep"][0]["right_sep"]]
    def cov(sp):
        lo, hi = min(sp["ys"]), max(sp["ys"])
        return max(0.0, min(hi,y1)-max(lo,y0))/span, lo, hi
    cl, lol, hil = cov(sp_l); cr, lor, hir = cov(sp_r)
    print("%-5s [%6.0f,%6.0f] [%6.0f,%6.0f] %.3f  [%6.0f,%6.0f] %.3f  %.4f" % (
        k, y0, y1, lol, hil, cl, lor, hir, cr, min(cl,cr)))
print()
print("→ 若某侧 y 跨度明显短于行范围,说明该列界折线本身没铺满表高(PF1 低的真因)")
