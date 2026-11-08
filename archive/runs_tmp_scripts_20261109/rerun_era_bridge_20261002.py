# -*- coding: utf-8 -*-
"""项②收尾(曲率桥+强制接触左框) 30 张全量重跑:单进程,逐张报接触/桥接统计。"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from src.core import paths
from src.table.track_rows import determine_rows

stems = sorted(p.stem for p in paths.RAW_DIR.glob("钻孔柱状图*.JPG"))
print(f"共 {len(stems)} 张")
tot = {"n": 0, "full": 0, "part": 0, "brig": 0, "bpx": []}
t_all = time.time()
for i, stem in enumerate(stems, 1):
    t = time.time()
    out = determine_rows(stem)
    era = [r for r in out["rows"] if r.get("era")]
    brig = [r for r in era if r.get("era_bridge_px")]
    w = [x for x in out["warnings"] if "时代" in x]
    print(f"[{i:2d}/{len(stems)}] {stem} {time.time()-t:5.1f}s era={len(era):3d} "
          f"full={out['n_era_full']:3d} part={out['n_era_partial']} brig={len(brig):3d} "
          f"bpx_max={max((r['era_bridge_px'] for r in brig), default=0):4d} {w}")
    tot["n"] += len(era)
    tot["full"] += out["n_era_full"]
    tot["part"] += out["n_era_partial"]
    tot["brig"] += len(brig)
    tot["bpx"] += [r["era_bridge_px"] for r in brig]
import numpy as np
print(f"\n合计 {time.time()-t_all:.0f}s: era 行 {tot['n']}, 接触 {tot['full']}, 未接触 {tot['part']}, "
      f"含桥接 {tot['brig']} 行, 桥长中位 {int(np.median(tot['bpx'])) if tot['bpx'] else 0}px, "
      f"最长 {max(tot['bpx']) if tot['bpx'] else 0}px")
