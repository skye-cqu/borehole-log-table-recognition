# -*- coding: utf-8 -*-
"""诊断D：被判据降级成子行线的临界档（cov_num ∈ [0.30,0.40)）到底是不是真层界。

两问：
  1) 它踩在横线墨上吗（离墨%，yardstick 同口径）——踩得住说明线是真的；
  2) 它的分母对不对——cov_num = 数值区被覆盖长度 / (boundary_x − 表左缘)。
     若 boundary_x 比真数值区右界偏右，分母虚高，真层界也会被压到阈值下（判据实现问题，
     不是阈值大小问题）。用该线自己的 poly 与 6a 定稿锚线重新求交，核对存的 boundary_x。

用法: python runs/tmp/diag_cov.py [1040 ...]      # 无参数=30 张
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table.track_columns import x_at                            # noqa: E402
from src.table import track_rows                                    # noqa: E402
import yardstick as Y                                               # noqa: E402

LO, HI = 0.30, 0.40


def off_ink(rec, ruling, x0, x1):
    n = o = 0
    for x in np.linspace(x0 + 10, x1 - 10, Y.SAMPLE):
        y = Y.line_y(rec, x)
        band = ruling[max(0, int(y) - Y.SEARCH):int(y) + Y.SEARCH, int(x)]
        idx = np.flatnonzero(band)
        n += 1
        if not len(idx) or np.abs(idx + max(0, int(y) - Y.SEARCH) - y).min() > 5:
            o += 1
    return o / max(n, 1) * 100


tot = {"n": 0, "onink": 0}
for code in [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json")):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                     f"{stem}_行判定.json").read_text(encoding="utf-8"))
    cand = [r for r in rd["sub_rows"] if LO <= r["cov_num"] < HI]
    if not cand:
        continue
    ruling, _ = Y.masks(stem)
    col = track_rows.column_anchor(stem)
    x0, x1 = int(rd["table_x"][0]), int(rd["table_x"][1])
    print(f"{code}: 临界档子行线 {len(cand)} 条")
    for r in cand:
        p = np.asarray(r["poly"], float)
        # 用线自己的折线与锚线重求交：锚线在这条线高度上的 x
        ys = p[:, 1]
        bx = float(np.median([x_at(col, y) for y in ys
                              if col[0, 0] <= y <= col[-1, 0]])) if col is not None else np.nan
        cov = r["cov_num"]
        o = off_ink(r, ruling, r["x"][0], r["x"][1])
        on = o < 10
        tot["n"] += 1
        tot["onink"] += on
        print(f"    y={r['y_at_mid']:<8} x={r['x'][0]}-{r['x'][1]:<6} cov={cov}"
              f" 离墨{o:3.0f}% {'←踩得住' if on else ''}  "
              f"存的boundary={r['boundary_x']} 锚线重算={bx:.0f}"
              f"{'  分母虚高' if col is not None and r['boundary_x'] - bx > 60 else ''}")
print(f"合计: 临界档 {tot['n']} 条,踩得住横线墨的 {tot['onink']} 条")
