# -*- coding: utf-8 -*-
"""几何感知干跑:比较修复前后每个命名格的 (名, x0, x1),而非仅列名序列。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
NUMERIC_NAMES = ["真厚", "倾角", "采长", "层厚", "深度", "煤层标志层号", "地质时代"]
CELL_W_MIN, CELL_W_MAX = 30.0, 180.0
HR_MIN, TOL_SEP = 0.60, 12
stem = sys.argv[1]
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
band = hm.get("band"); sx = hm.get("sep_x_band") or []
if not band or len(sx) < 2:
    print(json.dumps({"stem": stem, "skip": True}, ensure_ascii=False)); sys.exit(0)

def walk(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    xs_s = [xs[i] for i in order]
    gaps = [(b - a, k) for k, (a, b) in enumerate(zip(xs_s, xs_s[1:]))]
    wid, k_desc = max(gaps)
    if wid < 400: return None, None
    ia, ib = order[k_desc], order[k_desc + 1]
    cells = [(ia, ib, "岩性描述")]
    if ia - 1 >= 0:
        cells.append((ia - 1, ia, "柱状"))
        for j, nm in enumerate(NUMERIC_NAMES):
            ri = ia - 1 - j
            if ri - 1 < -1: break
            cells.append((ri - 1, ri, nm))
    lm = cells[-1][0]
    for li in range(lm - 1, -1, -1):
        cells.append((li - 1, li, None))
    return cells, ia

def geo(cs, xs):
    if not cs: return None
    out = []
    for li, ri, nm in cs:
        lx = 0.0 if li < 0 else xs[li]
        rx = float(W) if ri < 0 else xs[ri]
        out.append([("空窄格" if nm is None else nm), round(lx,1), round(rx,1)])
    return out

# 修复前
g0 = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g0.shape
c0, _ = walk(list(sx))
geo0 = geo(c0, sx)

# ① 去双描
sep = sorted(sx); dedup = []; i = 0; merged = []
while i < len(sep):
    j = i
    while j+1 < len(sep) and sep[j+1]-sep[j] < CELL_W_MIN: j += 1
    if j > i:
        m = float(np.mean(sep[i:j+1])); dedup.append(m); merged.append([round(v,1) for v in sep[i:j+1]])
    else: dedup.append(sep[i])
    i = j + 1
# ② 满高竖笔
b0, b1 = int(band[0]), int(band[1]); bh = b1 - b0
dens = (g0[b0:b1, :] < 150).sum(axis=0)
strokes = []; i = 0
while i < W:
    if dens[i] >= HR_MIN*bh:
        j = i
        while j < W and dens[j] >= HR_MIN*bh: j += 1
        if j-i <= 3: strokes.append(float(i+int(np.argmax(dens[i:j]))))
        i = j
    else: i += 1
del g0
# ③ 劈分
cd, iad = walk(dedup)
left_desc = dedup[iad] if iad is not None else float(W)
added = []
if cd:
    for li, ri, nm in cd:
        if nm is None: continue
        lx = dedup[li] if li >= 0 else 0.0
        rx = dedup[ri] if ri >= 0 else float(W)
        if rx > left_desc + TOL_SEP: continue
        if rx - lx <= CELL_W_MAX: continue
        for s in strokes:
            if not (lx + CELL_W_MIN <= s <= rx - CELL_W_MIN): continue
            if any(abs(s-v) <= TOL_SEP for v in dedup): continue
            added.append([nm, round(rx-lx,1), round(s,1)])
for a in added: dedup.append(a[2])
dedup.sort()
c1, _ = walk(dedup)
geo1 = geo(c1, dedup)
print(json.dumps({"stem": stem, "去双描": merged, "劈分": added,
                  "几何前": geo0, "几何后": geo1,
                  "变化": geo0 != geo1}, ensure_ascii=False))
