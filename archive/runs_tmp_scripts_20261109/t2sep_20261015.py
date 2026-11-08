# -*- coding: utf-8 -*-
"""1042:抗漂移判定 [632.7,912.0] 区间到底是几列。
方法:用 sep_pts 折线沿 y 插值出左右界,再在**随 y 移动的窗口**内测墨,
     统计内部竖线的持续长度。固定 x 窗口会因原图倾斜而漏检。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

hm = json.loads((R/"runs"/"table_reconstruct"/"钻孔柱状图1042_表头映射.json").read_text(encoding="utf-8"))
sps = hm["sep_pts"]
print("sep_pts 条数:", len(sps))
for s in sps:
    print("  kind=%-7s index=%-5s n=%d y=[%.0f,%.0f] x=[%.1f,%.1f]" % (
        s["kind"], s["index"], len(s["xs"]),
        min(s["ys"]), max(s["ys"]), min(s["xs"]), max(s["xs"])))

# 找 index 7 与 8 的折线(即 632.7 与 912.0 两条界)
def get(idx):
    for s in sps:
        if s["index"] == idx: return s
    return None
for idx in (5,6,7,8,9):
    s = get(idx)
    if s:
        print()
        print("index=%d  y跨度=[%.0f,%.0f]  x范围=[%.1f,%.1f]" % (idx, min(s["ys"]), max(s["ys"]), min(s["xs"]), max(s["xs"])))
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            yq = min(s["ys"]) + frac*(max(s["ys"])-min(s["ys"]))
            xs = np.array(s["xs"], float); ys = np.array(s["ys"], float)
            o = np.argsort(ys)
            print("    y=%-8.0f x=%.1f" % (yq, np.interp(yq, ys[o], xs[o])))
