# -*- coding: utf-8 -*-
"""单图:表头带满高竖笔中,哪些是"被漏掉的真列界"(命名列跨度内 + 阶段4候选墨迹佐证)。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

TOL_SEP, TOL_FRAME, COV_MIN, HR_MIN = 12, 40, 0.20, 0.60
stem = sys.argv[1]
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
band = hm.get("band"); sx = hm.get("sep_x_band") or []
if not band or not sx:
    print(json.dumps({"stem": stem, "skip": "无 band/sep"})); sys.exit(0)
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

sxs = sorted(sx)
gaps = [(b - a, k) for k, (a, b) in enumerate(zip(sxs, sxs[1:]))]
wid, kd = max(gaps)
lo_x = sxs[0]
hi_x = sxs[kd + 1] if kd + 1 < len(sxs) else sxs[-1]

cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
def cover(x, tol=8):
    cov = np.zeros(H + 2, dtype=bool); n = 0
    for s in cj["lines"]:
        if s["direction"] != "vertical" or s["label"] != "high": continue
        pts = s["points"]
        if abs(float(np.mean([p[0] for p in pts])) - x) > tol: continue
        ys = [p[1] for p in pts]
        a, b = max(0, int(min(ys))), min(H, int(max(ys)))
        if b > a: cov[a:b] = True; n += 1
    return float(cov.sum())/H, n

dups = [(round(a,1), round(b,1), round(b-a,1)) for a, b in zip(sxs, sxs[1:]) if b - a < 20]
found = []
for s in strokes:
    if s <= lo_x + TOL_FRAME or s >= hi_x - TOL_SEP: continue
    if any(abs(s - v) <= TOL_SEP for v in sx): continue
    frac, n = cover(s)
    if frac >= COV_MIN:
        found.append({"x": round(s,1), "候选覆盖": round(frac,3), "段数": n})
print(json.dumps({"stem": stem, "带高": bh, "命名列跨度": [round(lo_x), round(hi_x)],
                  "漏界": found, "双描": dups}, ensure_ascii=False))
