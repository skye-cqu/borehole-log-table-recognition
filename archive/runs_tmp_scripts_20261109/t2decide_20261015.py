# -*- coding: utf-8 -*-
"""1042:判定 x~711 那条线是不是贯穿表高的真列界。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 128).astype(np.uint8)

print("== 候选 x 的纵向连续性(y=740..19850) ==")
print("x      总暗数  最长连续段  连续段数   覆盖率")
for x in range(700, 725):
    col = ink[740:19850, x]
    n = int(col.sum())
    # 最长连续段
    best = cur = 0
    for v in col:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    segs = 0; prev = 0
    for v in col:
        if v and not prev: segs += 1
        prev = v
    print("%-6d %-7d %-11d %-10d %.1f%%" % (x, n, best, segs, 100.0*n/len(col)))

print()
print("== 对照:已知真列界 idx8(~912) 与 idx1(~196) ==")
for x in (196, 197, 911, 912, 913):
    col = ink[740:19850, x]
    n = int(col.sum()); best = cur = 0
    for v in col:
        cur = cur + 1 if v else 0; best = max(best, cur)
    print("%-6d %-7d %-11d %.1f%%" % (x, n, best, 100.0*n/len(col)))

print()
print("== 阶段4/5 已有产物里的候选竖线(数据源神圣:只能用已有候选段) ==")
for fn in ["钻孔柱状图1042_全竖线判定.json", "钻孔柱状图1042_列结构定稿.json"]:
    p = R/"runs"/"table_reconstruct"/fn
    if not p.exists(): print("  缺:", fn); continue
    d = json.loads(p.read_text(encoding="utf-8"))
    print("  -- %s  顶层键=%s" % (fn, list(d.keys())[:12]))
    s = json.dumps(d, ensure_ascii=False)
    import re
    # 找 x 在 690..740 的数
    hits = set()
    for m in re.finditer(r"[-0-9.]+", s):
        try: v = float(m.group())
        except: continue
        if 690 <= v <= 740: hits.add(round(v, 1))
    print("     其中落在 [690,740] 的数值:", sorted(hits)[:40])
