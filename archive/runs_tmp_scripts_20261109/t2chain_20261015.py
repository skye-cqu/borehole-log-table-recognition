# -*- coding: utf-8 -*-
"""1042 真实列界链:滑动窗测满高竖笔 → 跨窗链接 → 与 sep_pts 对照。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

stem = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
XMAX = 1200
WIN, STEP, THR, TOL = 40, 10, 0.80, 30

obs = []
for y0 in range(700, H-60, STEP):
    win = g[y0:y0+WIN, :XMAX]
    fr = (win < 140).mean(axis=0)
    peaks, i = [], 0
    while i < XMAX:
        if fr[i] >= THR:
            j = i
            while j < XMAX and fr[j] >= THR: j += 1
            seg = fr[i:j]
            peaks.append(float((np.arange(i, j)*seg).sum()/seg.sum()))
            i = j
        else:
            i += 1
    obs.append((y0+WIN/2.0, peaks))

chains = []
for ymid, peaks in obs:
    used = [False]*len(peaks)
    for ch in chains:
        if ymid - ch["last_y"] > 200:
            continue
        best, bd = None, 1e9
        for k, px in enumerate(peaks):
            if used[k]: continue
            d = abs(px-ch["x"])
            if d < bd: bd, best = d, k
        if best is not None and bd <= TOL:
            ch["pts"].append((ymid, peaks[best])); ch["x"] = peaks[best]; ch["last_y"] = ymid
            used[best] = True
    for k, px in enumerate(peaks):
        if not used[k]:
            chains.append({"x": px, "pts": [(ymid, px)], "last_y": ymid})

chains = [c for c in chains if len(c["pts"]) >= 6]
chains.sort(key=lambda c: c["pts"][0][1])
print("真实墨迹链 (>=6 窗, 共 %d 条):" % len(chains))
print("序  y顶    y底    覆盖窗数  x顶    x中    x底    x漂移")
for n, c in enumerate(chains):
    ys = [p[0] for p in c["pts"]]; xs = [p[1] for p in c["pts"]]
    cov = len(c["pts"])
    print("%-3d %-7.0f %-7.0f %-8d %-6.0f %-6.0f %-6.0f %+.0f"
          % (n, ys[0], ys[-1], cov, xs[0], xs[len(xs)//2], xs[-1], xs[-1]-xs[0]))

sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_分割线.json").read_text(encoding="utf-8"))
print()
print("sep_pts 与真实链对照 (在 y=1000/6000/11000/16000/19500 处):")
print("线名          " + "".join("%-10s" % ("y=%d" % y) for y in [1000, 6000, 11000, 16000, 19500]))
for i, ln in enumerate(sp["lines"]):
    pts = sorted(ln["pts"], key=lambda p: p[1])
    ys = np.array([p[1] for p in pts], float); xs = np.array([p[0] for p in pts], float)
    row = "%-13s" % (str(ln.get("name"))[:12])
    for y in [1000, 6000, 11000, 16000, 19500]:
        row += "%-10.0f" % float(np.interp(y, ys, xs))
    print(row)

json.dump([{"pts": c["pts"]} for c in chains],
          open(R/"runs/tmp/t2chains_20261015.json", "w", encoding="utf-8"),
          ensure_ascii=False)
print()
print("链已存 runs/tmp/t2chains_20261015.json")
