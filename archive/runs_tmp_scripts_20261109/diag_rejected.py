# -*- coding: utf-8 -*-
"""门禁2 剔掉的链，台阶到底出在哪一跳：阶段4 的候选段自己就跨行，还是建链时接错了段。

对每条被剔的链：按段切开它的点列，看最大台阶落在
  ①单个候选段内部 → 阶段4 检出的段本身就跨了两行（识别错）
  ②段与段的接缝   → 阶段6c 建链/同线合并把两行的段接成一条（拼接错）
并打出接缝两侧的段 id、段各自的中位 y，方便直接去阶段4 叠加图上找。

用法: python runs/tmp/diag_rejected.py [1027 1040 ...]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import step_of                            # noqa: E402


def main(codes):
    tot = defaultdict(int)
    for code in codes:
        stem = f"钻孔柱状图{code}"
        rd = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                         f"{stem}_行判定.json").read_text(encoding="utf-8"))
        cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
        seg = {s["id"]: np.asarray(s["points"], float) for s in cj["lines"]
               if s["direction"] == "horizontal" and s["label"] == "high"}
        print(f"\n{code}: 门禁2 剔链 {rd['n_chains_stepped']} 条 (容差 {rd['step_tol']:.0f}px,"
              f"行高 {rd['row_h']:.0f}px)")
        for r in sorted(rd["rejected"], key=lambda q: -q["step"])[:8]:
            runs = []                                   # [(段id, 该段点列)] 按链内顺序
            for i in r["segment_ids"]:
                if i in seg:
                    p = seg[i]
                    runs.append((i, np.column_stack([p[:, 1], p[:, 0]])))   # →(x,y)
            inner = max([step_of(p) for _, p in runs], default=0.0)
            seam = 0.0
            at = ""
            for (ia, pa), (ib, pb) in zip(runs, runs[1:]):
                d = abs(float(np.median(pa[-5:, 1])) - float(np.median(pb[:5, 1])))
                if d > seam:
                    seam, at = d, f"{ia}→{ib}"
            who = "段内(阶段4)" if inner >= seam else f"段间接缝(建链 {at})"
            tot["段内" if inner >= seam else "接缝"] += 1
            print(f"    y={r['y']:<9} x={r['x'][0]}-{r['x'][1]:<6} 段{len(runs)} "
                  f"台阶 段内{inner:5.0f} / 接缝{seam:5.0f} → {who}")
    print(f"\n30 张合计口径: 段内 {tot['段内']} 条, 段间接缝 {tot['接缝']} 条")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if a.isdigit()] or
         sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json")))
