# -*- coding: utf-8 -*-
"""无墨断口到底有多长：按游程长度分档计数，用来定"多长的断口才该把线裁断"。

只读原图 + 生产档行判定，不改任何线。用法: python runs/tmp/diag_gaps.py 1037 1027
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
import yardstick as Y                                               # noqa: E402
import ab_trim as T                                                 # noqa: E402
from src.core import paths                                          # noqa: E402

BINS = [0, 20, 40, 60, 80, 120, 200, 400, 1e9]
hist, per = Counter(), Counter()
for code in [a for a in sys.argv[1:] if a.isdigit()] or ["1037"]:
    stem = f"钻孔柱状图{code}"
    rd = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                     f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(stem)
    for r in rd["rows"]:
        xs = np.linspace(r["x"][0], r["x"][1], T.N)
        ok = T.ink_ok(ruling, r, xs) <= Y.POLY_TOL
        if ok.all():
            per["整条有墨"] += 1
            continue
        i = 0
        while i < len(ok):
            if ok[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(ok) and not ok[j + 1]:
                j += 1
            L = xs[j] - xs[i] + (xs[1] - xs[0])
            hist[next(b for b in range(len(BINS) - 1) if BINS[b] <= L < BINS[b + 1])] += 1
            i = j + 1
print("断口长度分布(px):")
for k, c in sorted(hist.items()):
    print(f"  {BINS[k]:>6.0f}~{BINS[k+1]:<6.0f}  {c}")
print("按线计:", dict(per), " 有断口的线", sum(hist.values()) and len(hist))
