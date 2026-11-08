# -*- coding: utf-8 -*-
"""1042 决定性取证:分割线真段点数组 + 表头带暗比剖面 + 全高墨迹连续性。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
stem = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
print("图尺寸 H=%d W=%d" % (H, W))
sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_分割线.json").read_text(encoding="utf-8"))
print("\n== _分割线.json 逐线 ==")
for i, ln in enumerate(sp["lines"]):
    pts = ln["pts"]
    ys = [p[1] for p in pts]
    xs = [p[0] for p in pts]
    print("[%d] %-6s idx=%-4s name=%-12s src=%-22s n=%d y=[%.0f,%.0f] x=[%.0f,%.0f]"
          % (i, ln.get("kind"), ln.get("index"), str(ln.get("name")), str(ln.get("src")),
             len(pts), min(ys), max(ys), min(xs), max(xs)))
    print("     头5点 %s" % " ".join("(%.0f,%.0f)" % (p[0], p[1]) for p in pts[:5]))
    print("     尾5点 %s" % " ".join("(%.0f,%.0f)" % (p[0], p[1]) for p in pts[-5:]))

print("\n== 表头带 [750,908] 暗比剖面 (x=440..980, frac>=0.15) ==")
band = g[750:908, :]
d = (band < 140)
fr = d.mean(axis=0)
runs = []
i = 440
while i <= 980:
    if fr[i] >= 0.15:
        j = i
        while j <= 980 and fr[j] >= 0.15: j += 1
        pk = max(range(i, j), key=lambda t: fr[t])
        runs.append((i, j-1, pk, float(fr[pk])))
        i = j
    else:
        i += 1
for a, b, pk, v in runs:
    print("   x=[%3d,%3d] 峰=%3d 暗比=%.2f" % (a, b, pk, v))

print("\n== 全高墨迹连续性 (x=440..980, 每4行采样, 窗±2) ==")
ys = np.arange(2, H-2, 4)
out = []
for x in range(440, 981):
    seg = g[ys[:, None] + np.arange(-2, 3)[None, :], x]
    out.append((x, float((seg.min(axis=1) < 140).mean())))
print("   连续度>=0.30 的 x:")
run = []
for x, v in out:
    if v >= 0.30: run.append((x, v))
    else:
        if run:
            bx = max(run, key=lambda t: t[1])
            print("     x=[%d,%d] 峰=%d 连续度=%.2f" % (run[0][0], run[-1][0], bx[0], bx[1]))
            run = []
if run:
    bx = max(run, key=lambda t: t[1])
    print("     x=[%d,%d] 峰=%d 连续度=%.2f" % (run[0][0], run[-1][0], bx[0], bx[1]))
