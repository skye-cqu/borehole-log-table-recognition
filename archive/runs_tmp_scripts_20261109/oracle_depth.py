# -*- coding: utf-8 -*-
"""行数真值:一张表有几个"深度"值,就有几个物理行(每层一个底深度)。

不必假设"格内多值=捆行"(采长一格两值是合法的),直接数每列的数值总个数:
  N_depth = 该表 深度 列全部数值 token 数
  应有层界 ≈ N_depth + 1(顶框到地面前每层一条下界线,近似)
对照 v3 层界数 → 缺多少条线，一目了然。同时给 层厚/采长/真厚 三列 token 数作旁证。
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"
NUM = re.compile(r"-?\d+(?:\.\d+)?")
TH = (0.5, 0.45, 0.4, 0.35, 0.3)


def covs(code):
    d = json.loads((paths.RUNS_DIR / "tmp" / f"行链3_{code}.json").read_text(encoding="utf-8"))
    tab_l, tab_r, b = d["tab_l"], d["tab_r"], float(np.clip(d["anchor_x"],
                                                            d["tab_l"] + 60, d["tab_r"] - 60))
    out = []
    for y, iv in d["lines"]:
        ca = cb = None
        tot = 0.0
        for a, e in sorted([(max(a, tab_l), min(e, b)) for a, e in iv]):
            if ca is None:
                ca, cb = a, e
            elif a <= cb:
                cb = max(cb, e)
            else:
                tot += cb - ca
                ca, cb = a, e
        tot += cb - ca if ca is not None else 0.0
        out.append(tot / max(b - tab_l, 1.0))
    return out


def main():
    codes = sorted(p.stem[4:] for p in (paths.RUNS_DIR / "tmp").glob("行链3_*.json"))
    print(f"{'张':<6}{'交付行':>7}{'层厚数':>7}{'真厚数':>7}{'深度数':>7}" +
          "".join(f"{t:>8.2f}" for t in TH))
    tot = [0] * 5
    for c in codes:
        ws = load_workbook(DELIV / f"{c}_还原.xlsx", read_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        hdr = [str(h or "") for h in rows[0]]
        cnt = {}
        for key in ("深度", "层厚", "真厚", "采长"):
            idx = [i for i, h in enumerate(hdr) if key in h]
            cnt[key] = sum(len(NUM.findall(str(r[i]))) if isinstance(r[i], str)
                           else (1 if isinstance(r[i], (int, float)) else 0)
                           for r in rows[1:] for i in idx)
        cv = covs(c)
        ns = [sum(1 for v in cv if v >= t) for t in TH]
        nd = max(cnt["层厚"], cnt["真厚"])          # 行数真值：每层一个层厚/真厚
        print(f"{c:<6}{len(rows)-1:>7}{cnt['层厚']:>7}{cnt['真厚']:>7}{cnt['深度']:>7}" +
              "".join(f"{n-nd:>8d}" for n in ns))
        for i, n in enumerate(ns):
            tot[i] += n - nd
    print("合计(层界-应有行数): " + "  ".join(f"{t:.2f}={e:+d}" for t, e in zip(TH, tot)))


if __name__ == "__main__":
    main()
