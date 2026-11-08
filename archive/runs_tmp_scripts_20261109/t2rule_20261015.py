# -*- coding: utf-8 -*-
"""窄规则试跑:表头带满高竖笔 + 阶段4竖向候选墨迹佐证 → 判定"被漏掉的真列界"。

判据(两条同时成立,均在命名列跨度内、非既有界、非外框):
  R1 表头带内存在 1-3px 宽、暗比>=0.60*带高 的竖笔;
  R2 阶段4 vertical/high 候选段(中心 x 距该处 <=8px)合并后的 y 覆盖 >= 表高的 20%。
"""
import json, sys, gc
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

TOL_SEP, TOL_FRAME, COV_MIN, HR_MIN = 12, 40, 0.20, 0.60

def header_strokes(gray, band):
    b0, b1 = int(band[0]), int(band[1]); bh = b1 - b0
    if bh < 20: return []
    dens = (gray[b0:b1, :] < 150).sum(axis=0)
    out, i, W = [], 0, gray.shape[1]
    while i < W:
        if dens[i] >= HR_MIN * bh:
            j = i
            while j < W and dens[j] >= HR_MIN * bh: j += 1
            if j - i <= 3: out.append(float(i + int(np.argmax(dens[i:j]))))
            i = j
        else:
            i += 1
    return out

def cand_cover(cj, x, H, tol=8):
    cov = np.zeros(H + 2, dtype=bool)
    n = 0
    for s in cj["lines"]:
        if s["direction"] != "vertical" or s["label"] != "high": continue
        pts = s["points"]
        xm = float(np.mean([p[0] for p in pts]))
        if abs(xm - x) > tol: continue
        ys = [p[1] for p in pts]
        a, b = max(0, int(min(ys))), min(H, int(max(ys)))
        if b > a: cov[a:b] = True; n += 1
    return int(cov.sum()), n

print("%-16s %-8s %s" % ("图", "带高", "判定为被漏掉的真列界(x, 表头暗比, 候选覆盖, 段数)"))
hits = {}
for p in sorted((paths.RUNS_DIR/"table_reconstruct").glob("*_表头映射.json")):
    stem = p.stem.replace("_表头映射", "")
    hm = json.loads(p.read_text(encoding="utf-8"))
    band = hm.get("band"); sx = hm.get("sep_x_band") or []
    if not band or not sx: continue
    g = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    if g is None:
        print("%-16s 读取失败" % stem); continue
    H, W = g.shape
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    strokes = header_strokes(g, band)
    # 命名列跨度:第一个严格在左框右侧的界 .. 岩性描述右界(最大间距的左端)
    sxs = sorted(sx)
    gaps = [(b - a, i) for i, (a, b) in enumerate(zip(sxs, sxs[1:]))]
    wid, kd = max(gaps)
    lo_x, hi_x = sxs[0], sxs[kd + 1] if kd + 1 < len(sxs) else sxs[-1]
    bh = int(band[1]) - int(band[0])
    found = []
    for s in strokes:
        if s <= lo_x + TOL_FRAME or s >= hi_x - TOL_SEP: continue
        if any(abs(s - v) <= TOL_SEP for v in sx): continue
        cov, n = cand_cover(cj, s, H)
        frac = cov / float(H)
        if frac >= COV_MIN:
            found.append((round(s, 1), round(frac, 3), n))
    if found: hits[stem] = found
    print("%-16s %-8d %s" % (stem, bh, found if found else "-"))
    del g; gc.collect()

print()
print("=== 汇总:被判定为漏掉的真列界 ===")
for k, v in hits.items(): print("  %-16s %s" % (k, v))
if not hits: print("  无")
