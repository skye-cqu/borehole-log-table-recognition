# -*- coding: utf-8 -*-
"""从真种子链接阶段4候选,得到 1042 表头 x=709 界的真实折线。对照 633 界。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
dark = (g < 150)
cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{STEM}.json").read_text(encoding="utf-8"))
segs = {}
for s in cj["lines"]:
    if s["direction"] != "vertical" or s["label"] != "high": continue
    p = np.asarray(s["points"], float)
    o = np.argsort(p[:,1]); p = p[o]
    segs[s["id"]] = p
print("vertical/high 段 =", len(segs))

def chain_from(seed_id, gap_max=120):
    """从种子段起,y 升序贪心接续(端点 x 差 <= gap_max)。"""
    cur = segs[seed_id].copy()
    used = {seed_id}
    order = sorted(segs.items(), key=lambda kv: kv[1][:,1].min())
    changed = True
    while changed:
        changed = False
        tail_y, tail_x = cur[-1,1], cur[-1,0]
        best, bestd = None, None
        for i, p in order:
            if i in used: continue
            y0, x0 = p[0,1], p[0,0]
            if y0 < tail_y - 20 or y0 > tail_y + gap_max: continue
            d = abs(x0 - tail_x)
            if d <= 45 and (bestd is None or d < bestd):
                best, bestd = i, d
        if best is not None:
            p = segs[best]
            cur = np.vstack([cur, p[p[:,1] > cur[-1,1]]]) if (p[:,1] > cur[-1,1]).any() else cur
            used.add(best); changed = True
    return cur, used

def prof(tr, step=1500):
    out = []
    for y in range(int(tr[0,1]), int(tr[-1,1])+1, step):
        k = np.argmin(np.abs(tr[:,1]-y))
        out.append((int(tr[k,1]), round(float(tr[k,0]),1)))
    return out

def ink_frac(tr):
    hit = 0
    for x, y in tr:
        xi, yi = int(round(x)), int(y)
        if 0 <= yi < H and dark[yi, max(0,xi-3):xi+4].any(): hit += 1
    return hit/len(tr)

for name, seed in (("709", 23397), ("633", None)):
    if seed is None:
        # 633: 找 y 最小且 x 接近 633 的段
        cand = [(p[0,1], i) for i, p in segs.items() if abs(p[0,0]-633) <= 6]
        seed = min(cand)[1]
    tr, used = chain_from(seed)
    print("\n== 链 %s (种子 id=%s) ==" % (name, seed))
    print("   段数=%d 点=%d y=[%.0f,%.0f] 覆盖=%.3f  x=%.0f..%.0f" % (
        len(used), len(tr), tr[0,1], tr[-1,1], (tr[-1,1]-tr[0,1])/H, tr[:,0].min(), tr[:,0].max()))
    print("   墨迹命中率 = %.3f" % ink_frac(tr))
    print("   剖面:", " ".join("y%d:x%.0f" % t for t in prof(tr)))
    np.save(str(R/f"runs/tmp/t2_chain_{name}_20261015.npy"), tr)
