# -*- coding: utf-8 -*-
"""全30张:表头带真实满高竖笔 vs _表头映射.json 实际采用的 sep_x_band。
判据:真实竖笔(表头带暗占比>=0.45)在 sep_x_band 里找不到(容差6px) → 漏界。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

RECON = paths.RUNS_DIR/"table_reconstruct"
stems = sorted([p.name.replace("_表头映射.json","") for p in RECON.glob("*_表头映射.json")])
print("图数:", len(stems))
print()
print("stem                  src          n_sep 真实满高竖笔(x<1200)          漏界(未在sep_x_band)")
print("-"*118)
tot_miss = 0
rows = []
for stem in stems:
    hm = json.loads((RECON/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
    if not hm.get("band"): 
        print("%-21s %-12s %s" % (stem, hm.get("header_src"), "无band")); continue
    y0, y1 = int(hm["band"][0]), int(hm["band"][1])
    if y1 - y0 < 40: 
        print("%-21s %-12s 带过窄 %d" % (stem, hm.get("header_src"), y1-y0)); continue
    jp = paths.RAW_DIR/f"{stem}.JPG"
    if not jp.exists(): jp = paths.RAW_DIR/f"{stem}.jpg"
    g = cv2.imread(str(jp), cv2.IMREAD_GRAYSCALE)
    if g is None:
        print("%-21s 原图读不到" % stem); continue
    hh = y1-y0
    dark = (g[y0:y1] < 140)
    cand = []
    for x in range(1, min(g.shape[1]-1, 1400)):
        f = float(dark[:, x].mean())
        if f >= 0.45: cand.append((x, f))
    grps = []
    for x, f in cand:
        if grps and x - grps[-1][-1][0] <= 3: grps[-1].append((x, f))
        else: grps.append([(x, f)])
    strokes = [(float(np.mean([a for a,_ in gp])), max(b for _,b in gp)) for gp in grps]
    seps = [v for v in (hm.get("sep_x_band") or []) if v < 1400]
    miss = [(x, f) for x, f in strokes if not any(abs(x-s) <= 6 for s in seps)]
    tot_miss += len(miss)
    rows.append((stem, hm.get("header_src"), len(hm.get("sep_x_band") or []), len(strokes), miss))
    print("%-21s %-12s %-6d %-28s %s" % (
        stem, hm.get("header_src"), len(hm.get("sep_x_band") or []), len(strokes),
        " ".join("%.0f(%.2f)" % m for m in miss) if miss else "-"))
print("-"*118)
print("漏界总数 =", tot_miss)
print()
print("== 只有 1042 吗? 有漏界的图 ==")
for stem, src, ns, nstroke, miss in rows:
    if miss: print("   %-21s src=%-10s 漏 %d 条: %s" % (stem, src, len(miss), " ".join("%.0f(占比%.2f)" % m for m in miss)))
