# -*- coding: utf-8 -*-
"""1042 决定性:墨迹逐行跟踪列界 vs 阶段4/5已有折线 → 判定能否合规修复。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from src.table import col_segments

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 140).astype(np.uint8)
H, W = g.shape

lp = col_segments.line_parts("钻孔柱状图1042")
lines = []
for ln in lp["lines"]:
    pts = [p for seg, _ in ln["parts"] for p in seg] + [p for seg, _ in ln.get("bridged", []) for p in seg]
    if len(pts) < 2: continue
    a = np.array(sorted(pts, key=lambda p: p[1]), float)
    lines.append({"kind": ln["kind"], "index": ln.get("index"), "src": ln.get("src"),
                  "ys": a[:,1], "xs": a[:,0]})
print("line_parts 折线数:", len(lines))
for L in lines:
    print("  kind=%-7s idx=%-5s src=%-22s n=%-4d x=[%.0f,%.0f] y=[%.0f,%.0f]" % (
        L["kind"], L["index"], str(L["src"]), len(L["xs"]),
        L["xs"].min(), L["xs"].max(), L["ys"].min(), L["ys"].max()))

def track(x_start, y0=1000, y1=19600, step=40, win=26, need=0.55):
    """自 x_start 起,逐 step 向下找墨峰(窗口 win 内),返回 [(y,x)]。"""
    prev = float(x_start); out = []
    for y in range(y0, y1, step):
        band = ink[y-3:y+4, max(0,int(prev-win)):int(prev+win)]
        col = band.sum(axis=0).astype(float)
        if col.max() < 2:
            out.append((y, prev)); continue
        cs = np.convolve(col, np.ones(3)/3.0, mode="same")
        i = int(np.argmax(cs))
        x = max(0,int(prev-win)) + i
        prev = float(x)
        out.append((y, x))
    return out

print()
print("== 墨迹跟踪(自表头位置起步) ==")
cands = {"采长|倾角": 553, "倾角|真厚": 633, "真厚|柱状": 712, "柱状|岩性描述": 912}
tracks = {}
for nm, x0 in cands.items():
    t = track(x0)
    tracks[nm] = t
    ys = [p[0] for p in t]; xs = [p[1] for p in t]
    print("  %-14s x: 顶=%.0f 中=%.0f 底=%.0f  范围=[%.0f,%.0f]" % (
        nm, xs[0], xs[len(xs)//2], xs[-1], min(xs), max(xs)))

print()
print("== 跟踪线与 line_parts 折线的贴合度(逐点最近距离) ==")
for nm, t in tracks.items():
    best = None
    for L in lines:
        if L["kind"] != "column": continue
        d = []
        for y, x in t:
            if L["ys"].min() <= y <= L["ys"].max():
                d.append(abs(x - float(np.interp(y, L["ys"], L["xs"]))))
        if len(d) < 50: continue
        d = np.array(d)
        frac = float((d <= 15).mean())
        med = float(np.median(d))
        if best is None or frac > best[0]:
            best = (frac, med, L["index"], L["src"], len(d))
    if best:
        print("  %-14s → 最佳折线 idx=%-5s src=%-22s 贴合(<=15px)=%.0f%% 中位差=%.1fpx (n=%d)" % (
            nm, best[2], str(best[3]), 100*best[0], best[1], best[4]))
    else:
        print("  %-14s → 无可比折线" % nm)
