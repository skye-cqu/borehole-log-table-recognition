# -*- coding: utf-8 -*-
"""门禁前后逐张对照（只读 JSON，不碰图）：层界数、台阶线数、剔链数、覆盖率降级数。

台阶按"半行高"这条绝对门量（>tol 的线 = 跨了两行的线，就是 1027 那种图上不存在的线）。
用法: python runs/tmp/ab_gates.py
"""
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import step_of                            # noqa: E402

OLD = Path(os.environ.get("SRC", ROOT / "rollback" / "行判定_门禁前_20260924"))
NEW = paths.RUNS_DIR / "table_reconstruct"


def stat(d, stem):
    rd = json.loads((d / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    tol = rd.get("step_tol", 35.0)
    st = np.array([step_of(np.asarray(r["poly"], float)) for r in rd["rows"]])
    return {"n": len(rd["rows"]), "sub": len(rd["sub_rows"]), "tol": tol,
            "row_h": rd.get("row_h", 0), "rej": rd.get("n_chains_stepped", 0),
            "big": int((st > tol).sum()), "max": float(st.max()) if len(st) else 0.0,
            "y": sorted(r["y_at_mid"] for r in rd["rows"])}


rows = []
for p in sorted(paths.CANDIDATE_COORD_DIR.glob("*.json")):
    stem = p.stem
    code = stem[-4:]
    try:
        a, b = stat(OLD, stem), stat(NEW, stem)
    except FileNotFoundError:
        continue
    rows.append((code, a, b))

print(f"{'张':<6}{'层界 前→后':>14}{'台阶线(>半行高) 前→后':>22}{'最大台阶px 前→后':>18}"
      f"{'子行线 前→后':>13}{'剔链':>6}{'行高':>6}")
for code, a, b in rows:
    print(f"{code:<6}{a['n']:>6}→{b['n']:<7}{a['big']:>10}→{b['big']:<11}"
          f"{a['max']:>8.0f}→{b['max']:<8.0f}{a['sub']:>6}→{b['sub']:<6}"
          f"{b['rej']:>6}{b['row_h']:>6.0f}")
n = lambda k, s: sum(x[k][s] for x in rows)          # noqa: E731
print(f"合计 {len(rows)} 张: 层界 {n('a','n')}→{n('b','n')}  台阶线 {n('a','big')}→{n('b','big')}"
      f"  子行线 {n('a','sub')}→{n('b','sub')}  剔链 {n('b','rej')}")
