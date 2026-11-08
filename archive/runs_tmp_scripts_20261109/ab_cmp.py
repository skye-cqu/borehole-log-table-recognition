# -*- coding: utf-8 -*-
"""一次读图、两档并排量：生产档 vs 变体档（YARD_SRC 指的那批 JSON），差值直接打出来。

尺子只认"图上有没有横线墨、线离它多少 px"，两档用同一张墨迹掩膜，差别只在线本身。
用法: python runs/tmp/ab_cmp.py <变体目录> [1024 1027 ...]     # 无参数=30 张
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
import yardstick as Y                                               # noqa: E402

VAR = Path(sys.argv[1])
PROD = paths.RUNS_DIR / "table_reconstruct"
codes = [a for a in sys.argv[2:] if a.isdigit()] or \
        sorted(p.name.split("图")[1].split("_")[0] for p in PROD.glob("*_行判定.json"))

_load = Y.masks
_hit = {}


def cached(stem):
    return _hit[stem]


Y.masks = cached
KEYS = ("n", "bad", "near", "over", "med", "p90", "noline", "cross")
print(f"{'张':<6}" + "".join(f"{k:>10}" for k in KEYS) + "   (生产→变体)")
acc = {k: [0.0, 0.0] for k in KEYS}
for code in codes:
    stem = f"钻孔柱状图{code}"
    if not (VAR / f"{stem}_行判定.json").exists():
        print(f"{code:<6} 变体缺档")
        continue
    _hit[stem] = _load(stem)
    out = []
    for i, src in enumerate((PROD, VAR)):
        Y.SRC = src
        m = Y.measure(code)
        d = {"n": m["n"], "bad": m["bad_lines"], "near": m["near"],
             "over": m["over"], "med": m["med"], "p90": m["p90"],
             "noline": m["noline"], "cross": m["cross"]}
        out.append(d)
        for k, v in d.items():
            acc[k][i] += v
    _hit.clear()
    print(f"{code:<6}" + "".join(
        f"{out[0][k]:>4.0f}→{out[1][k]:<5.0f}" if k == "n" else
        f"{out[0][k]:>4.1f}→{out[1][k]:<5.1f}" for k in KEYS), flush=True)
print("合计    " + "".join(f"{acc[k][0]:>4.0f}→{acc[k][1]:<5.0f}" if k in ("n", "bad", "near", "noline")
                           else f"{acc[k][0]:>4.1f}→{acc[k][1]:<5.1f}" for k in KEYS))
print("列名: n=层界数 bad=超差>10%的线数 near=超差≤10%的线数 over=平均超差% "
      "med/p90=离墨px noline=过半找不到墨的线数 cross=压字%")
