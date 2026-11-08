# -*- coding: utf-8 -*-
"""最终规则干跑:界漏检检测(表头满高竖笔 + 阶段4竖向候选墨迹佐证),限定在岩性描述左界之左。

只报告 keep 列名变化,不写文件。
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
HR_MIN, TOL_SEP, COV_MIN = 0.60, 12, 0.20
stem = sys.argv[1]

hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
band = hm.get("band"); sx = hm.get("sep_x_band") or []
if not band or len(sx) < 2:
    print(json.dumps({"stem": stem, "skip": True}, ensure_ascii=False)); sys.exit(0)

def walk(xs):
    if len(xs) < 2: return None, None
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

before_cells, ia0 = walk(list(sx))
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

sep = list(sx)
left_desc = sep[ia0] if ia0 is not None and ia0 < len(sep) else float(W)
added = []
for s in strokes:
    if s >= left_desc - TOL_SEP: continue
    if any(abs(s - v) <= TOL_SEP for v in sep): continue
    frac, n = cov(s)
    if frac >= COV_MIN:
        added.append({"x": round(s, 1), "cov": round(frac, 3), "段": n})
for a in added: sep.append(a["x"])
sep.sort()

def final_names(cells):
    """复刻 _relabel_by_content 的净效果(仅用几何+已知内容名,不跑 OCR):
    这里只报告几何列名,内容重贴由 OCR 决定,另行实测。"""
    if not cells: return None
    out = []
    for li, ri, nm in cells:
        if nm is None: nm = "空窄格"
        out.append(nm)
    return out

print(json.dumps({"stem": stem, "岩性描述左界": round(left_desc),
                  "新增界": added,
                  "几何列名_前": final_names(before_cells),
                  "几何列名_后": final_names(walk(sep)[0]),
                  "变化": added != []}, ensure_ascii=False))
