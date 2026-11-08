# -*- coding: utf-8 -*-
"""行线的左右端点有没有伸出表格外框：伸出去的那一段是框外的注记/刻度，不是表格的行线。

外框取 6a4 闭合外框的左右两条边（按该线的高度取值）。超出 >10px 记一条，按张统计并点名。
用法: python runs/tmp/diag_span.py [1018 1034]   # 无参数=30 张
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import edge_at                     # noqa: E402

TOL = 10
SRC = Path(os.environ.get("SPAN_SRC", paths.RUNS_DIR / "table_reconstruct"))


def sheet(code):
    stem = f"钻孔柱状图{code}"
    fr = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_闭合外框.json",
                        encoding="utf-8"))
    L = np.array([[p[1], p[0]] for p in fr["left"]["pts"]], float)
    R = np.array([[p[1], p[0]] for p in fr["right"]["pts"]], float)
    rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    out = []
    for r in rd["rows"]:
        y = r["y_at_mid"]
        lo, hi = edge_at(L, y), edge_at(R, y)
        e0, e1 = lo - int(r["x"][0]), int(r["x"][1]) - hi
        if e0 > TOL or e1 > TOL:
            out.append((round(y), int(r["x"][0]), int(r["x"][1]),
                        round(lo), round(hi), round(max(e0, e1)), r["n_chains"]))
    return len(rd["rows"]), out


tot = tot_n = 0
for code in [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json")):
    n, out = sheet(code)
    tot += len(out)
    tot_n += n
    print(f"{code}: 行线{n:>4}  端点出框{len(out):>4}" +
          "".join(f"\n      y={t[0]:<6} 画的 x={t[1]}-{t[2]}  框 {t[3]}~{t[4]}  出 {t[5]}px 链{t[6]}"
                  for t in sorted(out, key=lambda t: -t[5])[:4]))
print(f"合计: 行线{tot_n}  端点出框{tot}")
