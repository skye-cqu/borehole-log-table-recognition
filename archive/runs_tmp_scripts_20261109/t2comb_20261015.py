# -*- coding: utf-8 -*-
"""合并规则干跑:①去双描(相邻界<CELL_W_MIN 合并取中) ②命名格过宽(>CELL_W_MAX)且格内有满高表头竖笔 → 劈分。

范围限 岩性描述左界之左;不写文件。
"""
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

def nm_of(cs):
    return [("空窄格" if c[2] is None else c[2]) for c in cs] if cs else None

# ① 去双描
sep = sorted(sx)
dedup, i, merged = [], 0, []
while i < len(sep):
    j = i
    while j + 1 < len(sep) and sep[j+1] - sep[j] < CELL_W_MIN: j += 1
    if j > i:
        m = float(np.mean(sep[i:j+1])); dedup.append(m)
        merged.append({"合并": [round(v,1) for v in sep[i:j+1]], "为": round(m,1)})
    else:
        dedup.append(sep[i])
    i = j + 1

cells0, ia0 = walk(dedup)
g = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
b0, b1 = int(band[0]), int(band[1]); bh = b1 - b0
dens = (g[b0:b1, :] < 150).sum(axis=0)
strokes, i = [], 0
while i < W:
    if dens[i] >= HR_MIN * bh:
        j = i
        while j < W and dens[j] >= HR_MIN * bh: j += 1
        if j - i <= 3: strokes.append(float(i + int(np.argmax(dens[i:j]))))
        i = j
    else: i += 1
del g

# ② 劈分
left_desc = dedup[ia0] if ia0 is not None else float(W)
added = []
if cells0:
    for li, ri, nm in cells0:
        if nm is None: continue
        lx = dedup[li] if li >= 0 else 0.0
        rx = dedup[ri] if ri >= 0 else float(W)
        if rx > left_desc + TOL_SEP: continue
        if rx - lx <= CELL_W_MAX: continue
        for s in strokes:
            if not (lx + CELL_W_MIN <= s <= rx - CELL_W_MIN): continue
            if any(abs(s - v) <= TOL_SEP for v in dedup): continue
            added.append({"格": nm, "宽": round(rx - lx, 1), "新界": round(s, 1)})
for a in added: dedup.append(a["新界"])
dedup.sort()
cells1, _ = walk(dedup)

print(json.dumps({"stem": stem, "去双描": merged, "劈分": added,
                  "列名_前": nm_of(cells0), "列名_后": nm_of(cells1),
                  "变化": (nm_of(cells0) != nm_of(cells1)) or bool(merged)}, ensure_ascii=False))
