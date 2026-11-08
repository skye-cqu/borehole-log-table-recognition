# -*- coding: utf-8 -*-
"""门禁5 的回归检查②：删带有没有把折线的东头截短。

下游 reconstruct_excel.build_cells 在格子里取 row_y 切单元格，折线东头一截短，
靠东那几列的取值就落到上一行去。所以删带之后必须量：每张"折线最大 x"的中位、
以及东伸过 1500px 的层界条数，跟删带前对得住才算没伤。

用法: python runs/tmp/poly_east.py            # 读现行 runs/ 产物
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths  # noqa: E402

tot = n = 0
print(f"{'图':<7}{'层界':>7}{'poly最大x中位':>14}{'东伸>1500':>11}")
for fp in sorted((paths.RUNS_DIR / "table_reconstruct").glob("*_行判定.json")):
    rows = json.load(open(fp, encoding="utf-8"))["rows"]
    east = [max(p[0] for p in r["poly"]) for r in rows]
    tot += len(rows)
    n += sum(e > 1500 for e in east)
    print(f"{fp.stem[5:9]:<7}{len(rows):>7}{int(np.median(east)) if east else 0:>14}{sum(e > 1500 for e in east):>11}")
print(f"合计 层界{tot} 东伸>1500 {n} ({n / tot:.0%})")
