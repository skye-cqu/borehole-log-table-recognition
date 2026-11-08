# -*- coding: utf-8 -*-
"""干跑:界去双描(间距<CELL_W_MIN 合并) + 超宽命名列按表头墨迹竖笔劈分,再走算术命名。

不写任何文件;输出修复前后的列名序列,用于判定规则是否只影响 1042。
"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

NUMERIC_NAMES = ["真厚", "倾角", "采长", "层厚", "深度", "煤层标志层号", "地质时代"]
DROP_NAMES = {"柱状", "简易水文曲线"}
CELL_W_MIN, CELL_W_MAX = 30.0, 180.0
HR_MIN, TOL_SEP, COV_MIN = 0.60, 12, 0.15
stem = sys.argv[1]

hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
band = hm.get("band"); sx = hm.get("sep_x_band") or []
if not band or len(sx) < 2:
    print(json.dumps({"stem": stem, "skip": True}, ensure_ascii=False)); sys.exit(0)

def walk(xs):
    """照抄 header_assign 的算术命名,返回 (列名序列, 警告)"""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    xs_s = [xs[i] for i in order]
    gaps = [(b - a, k) for k, (a, b) in enumerate(zip(xs_s, xs_s[1:]))]
    wid, k_desc = max(gaps)
    if wid < 400: return None, ["未找到岩性描述锚"]
    ia, ib = order[k_desc], order[k_desc + 1]
    warns, cells = [], [(ia, ib, "岩性描述")]
    if ia - 1 >= 0:
        cells.append((ia - 1, ia, "柱状"))
        for j, nm in enumerate(NUMERIC_NAMES):
            ri = ia - 1 - j
            cells.append((ri - 1, ri, nm))
            if ri - 1 < -1:
                warns.append("数值列超出图左缘"); cells.pop(); break
    else:
        warns.append("岩性描述左界缺失")
    lm = cells[-1][0]
    for li in range(lm - 1, -1, -1):
        cells.append((li - 1, li, None))
    if ib + 1 < len(xs):
        cells.append((ib, ib + 1, "简易水文曲线"))
        for ri in range(ib + 1, len(xs)):
            cells.append((ri, ri + 1 if ri + 1 < len(xs) else -1, "简易水文曲线"))
    else:
        cells.append((ib, -1, "简易水文曲线"))
    out = []
    for li, ri, nm in cells:
        if nm is None: nm = "空窄格"
        out.append((nm, (li, ri)))
    return out, warns

# ---------- 修复前 ----------
before, _ = walk(list(sx))

# ---------- 修复 ----------
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
cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
def cov(x, tol=8):
    c = np.zeros(H + 2, dtype=bool); n = 0
    for s in cj["lines"]:
        if s["direction"] != "vertical" or s["label"] != "high": continue
        pts = s["points"]
        if abs(float(np.mean([p[0] for p in pts])) - x) > tol: continue
        ys = [p[1] for p in pts]
        a, b = max(0, int(min(ys))), min(H, int(max(ys)))
        if b > a: c[a:b] = True; n += 1
    return float(c.sum())/H, n

sep = sorted(sx)
# 1) 去双描:相邻间距 < CELL_W_MIN → 合并取中
dedup, i = [], 0
merged_log = []
while i < len(sep):
    j = i
    while j + 1 < len(sep) and sep[j+1] - sep[j] < CELL_W_MIN: j += 1
    if j > i:
        m = float(np.mean(sep[i:j+1])); dedup.append(m)
        merged_log.append({"合并": [round(v,1) for v in sep[i:j+1]], "为": round(m,1)})
    else:
        dedup.append(sep[i])
    i = j + 1
# 2) 超宽命名列按表头墨迹竖笔劈分
cells_now, _ = walk(dedup)
added = []
if cells_now:
    for nm, (li, ri) in cells_now:
        if nm in ("岩性描述", "地质时代", "空窄格"): continue
        lx = dedup[li] if li >= 0 else 0.0
        rx = dedup[ri] if ri >= 0 else float(W)
        if rx - lx <= CELL_W_MAX: continue
        for s in strokes:
            if not (lx + CELL_W_MIN <= s <= rx - CELL_W_MIN): continue
            if any(abs(s - v) <= TOL_SEP for v in dedup): continue
            frac, n = cov(s)
            if frac >= COV_MIN:
                added.append({"格": nm, "宽": round(rx-lx,1), "新界x": round(s,1),
                              "候选覆盖": round(frac,3), "段数": n})
    for a in added:
        dedup.append(a["新界x"])
    dedup.sort()
after, _ = walk(dedup)

def names(cs):
    return [n for n, _ in cs] if cs else None
print(json.dumps({"stem": stem,
                  "去双描": merged_log, "劈分": added,
                  "修复前列名": names(before), "修复后列名": names(after),
                  "变化": names(before) != names(after)}, ensure_ascii=False))
