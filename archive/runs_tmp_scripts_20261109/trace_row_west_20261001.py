"""追一行: 阶段4 high 段(x[199,529] y~1042)为什么没进行链。

环节: 候选段 → label 过滤 → clip_to_frame(逐 y 框裁) → build_tracks 建链 → merge_tracks → items。
"""
import json, sys
sys.path.insert(0, ".")
import numpy as np
from src.core import paths
from src.table import track_rows as tr
from src.table import track_group

stem = "钻孔柱状图1015"
cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))

# 1) 目标段原文
targets = [s for s in cj["lines"] if s["id"] in (50131, 49985, 48318, 50129, 48363)]
print("== 候选段原文:")
for s in targets:
    xs = [p[0] for p in s["points"]]; ys = [p[1] for p in s["points"]]
    print(f"  id={s['id']} {s['label']} x[{min(xs)},{max(xs)}] y[{min(ys)},{max(ys)}] n={len(s['points'])}")

# 2) 左框链在 y=1041/1555 处的位置 + y 单调性
fr = tr.table_frame(stem)
L, R = fr
print("== 左框链: n=", len(L), " y 单调?", bool(np.all(np.diff(L[:, 0]) > 0)))
for yq in (732, 1041, 1555, 8437, 11505, 14552, 17767):
    print(f"  L({yq}) = {np.interp(yq, L[:, 0], L[:, 1]):.1f}")
dup = np.flatnonzero(np.diff(L[:, 0]) <= 0)
print("  y 非单调处:", dup[:5], " 共", len(dup))

# 3) clip_to_frame 结果
print("== clip_to_frame 后:")
for s in targets:
    q = tr.clip_to_frame(s["points"], *fr)
    if q is None:
        print(f"  id={s['id']} → 整段被裁掉")
    else:
        print(f"  id={s['id']} → x[{q[0,0]:.0f},{q[-1,0]:.0f}] n={len(q)} (原 n={len(s['points'])})")

# 4) 全链路: load_chains 后这些 id 在不在 items 里
ch = tr.load_chains(stem)
have = {}
for it in ch["items"]:
    for i in it["ids"]:
        have.setdefault(i, []).append((round(it["x"][0]), round(it["x"][1])))
for s in targets:
    print(f"  id={s['id']} 在 items: {have.get(s['id'], '❌ 无')}")

# 5) y≈1042 附近的行为: poly 西端与成员 ids
rows = json.loads((paths.RUNS_DIR/'table_reconstruct'/f'钻孔柱状图{stem}_行判定.json').read_text(encoding='utf-8'))["rows"]
for r in rows:
    if 900 < r["y_at_mid"] < 1250:
        print(f"  行 y={r['y_at_mid']} poly西端={r['poly'][0][0]} x={r['x']} ids n={len(r['segment_ids'])} "
              f"含目标段: {[i for i in r['segment_ids'] if i in (50131,49985,48318)]}")
