# -*- coding: utf-8 -*-
"""1042:各 y 处真实满高竖笔 vs sep_pts 插值 x —— 一一对应关系。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

stem = "钻孔柱状图1042"
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
rj = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_行判定.json").read_text(encoding="utf-8"))
rows = rj["rows"]

def strokes(y0, y1, th=0.75, x0=0, x1=None):
    x1 = x1 or g.shape[1]
    d = (g[int(y0)+3:int(y1)-3, x0:x1] < 140)
    if d.shape[0] < 4: return []
    cf = d.mean(axis=0); out, i = [], 0
    while i < len(cf):
        if cf[i] >= th:
            j = i
            while j < len(cf) and cf[j] >= th: j += 1
            out.append((x0+(i+j-1)/2.0, float(cf[i:j].max()))); i = j
        else: i += 1
    return out

seps = hm["sep_pts"]
print("== sep_pts 在指定 y 的插值 x ==")
ys_test = [829, 4070, 4230, 4540, 6000, 10000, 15000, 19000]
hdr = "y      " + "".join("%-9s" % ("sp%d" % i) for i in range(len(seps)))
print(hdr)
for y in ys_test:
    line = "%-7d" % y
    for sp in seps:
        ys = np.array(sp["ys"], float); xs = np.array(sp["xs"], float)
        o = np.argsort(ys)
        v = float(np.interp(y, ys[o], xs[o]))
        line += "%-9.0f" % v
    print(line)
print("名称  " + "".join("%-9s" % (sp["kind"][:4] + str(sp["index"])) for sp in seps))

print()
print("== 各行带内真实满高竖笔 vs sep_pts 插值(只看 x<1100) ==")
for idx in [5, 7, 10, 30, 60, 100]:
    if idx+1 >= len(rows): continue
    y0 = rows[idx]["poly"][-1][1]; y1 = rows[idx+1]["poly"][-1][1]
    if y1-y0 < 25: continue
    st = [s for s, _ in strokes(y0, y1) if s < 1100]
    ymid = (y0+y1)/2
    sv = []
    for sp in seps:
        ys = np.array(sp["ys"], float); xs = np.array(sp["xs"], float)
        o = np.argsort(ys)
        sv.append(round(float(np.interp(ymid, ys[o], xs[o]))))
    print("  r%-3d y=[%6.0f,%6.0f]" % (idx, y0, y1))
    print("       实测竖笔: %s" % " ".join("%.0f" % s for s in st))
    print("       sep_pts : %s" % " ".join("%d" % s for s in sv))
    # 实测竖笔中无对应 sep 的
    miss = [s for s in st if not any(abs(s-v) <= 8 for v in sv)]
    print("       实测有/sep无: %s" % (" ".join("%.0f" % m for m in miss) or "-"))
