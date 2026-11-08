# -*- coding: utf-8 -*-
"""判据:交付表每格里"几个数值"直接说明该格捆了几行 → 每张应有行数 R。

R = 交付行数 + Σ每行(格内数值个数-1)。多值格是"该捆未捆"的直接读数,
不需要 OCR 重跑,不需要肉眼。1032/1042 已修好,应给出 R=103/112(真值)——先自校。
再用 R 去卡 v3 扫描的层界数:哪个阈值让 30 张的 层界数 ≈ R,哪个就是对的。
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"
NUM = re.compile(r"-?\d+(?:\.\d+)?")
NUMHDR = ("深度", "层厚", "采长", "真厚")
TRUTH = {"1032": 103, "1042": 112}


def required_rows(code):
    p = DELIV / f"{code}_还原.xlsx"
    if not p.exists():
        return None
    ws = load_workbook(p, read_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h or "") for h in rows[0]]
    idx = [i for i, h in enumerate(hdr) if any(k in h for k in NUMHDR)]
    r = len(rows) - 1
    for row in rows[1:]:
        r += max([0] + [max(0, len(NUM.findall(str(row[i]))) - 1)
                        for i in idx if isinstance(row[i], str)])
    return r


def main():
    codes = sorted(p.stem[4:] for p in (paths.RUNS_DIR / "tmp").glob("行链3_*.json"))
    # 覆盖区间 → cov_num(取界 C 已由 sweep 证与 A/B 同结果,这里用 定稿常数界)
    cov = {}
    for c in codes:
        d = json.loads((paths.RUNS_DIR / "tmp" / f"行链3_{c}.json")
                       .read_text(encoding="utf-8"))
        tab_l, tab_r, b = d["tab_l"], d["tab_r"], d["anchor_x"]
        out = []
        for y, iv in d["lines"]:
            bb = float(np.clip(b, tab_l + 60, tab_r - 60))
            tot = 0.0
            ca = cb = None
            for a, e in sorted([(max(a, tab_l), min(e, bb)) for a, e in iv]):
                if ca is None:
                    ca, cb = a, e
                elif a <= cb:
                    cb = max(cb, e)
                else:
                    tot += cb - ca
                    ca, cb = a, e
            tot += cb - ca if ca is not None else 0.0
            out.append((y, tot / max(bb - tab_l, 1.0)))
        cov[c] = out

    print(f"{'张':<6}{'应有R':>7}{'交付行':>7}" + "".join(f"{t:>8}" for t in
          ("0.50", "0.45", "0.40", "0.35", "0.30")) + "   最佳阈值")
    tot_err = defaultdict(int)
    for c in codes:
        R = required_rows(c)
        ws = load_workbook(DELIV / f"{c}_还原.xlsx", read_only=True).active
        ndel = ws.max_row - 1
        ns = [sum(1 for _, v in cov[c] if v >= t) for t in (.5, .45, .4, .35, .3)]
        best = min(zip(ns, (.5, .45, .4, .35, .3)), key=lambda x: abs(x[0] - R))
        for n, t in zip(ns, (.5, .45, .4, .35, .3)):
            tot_err[t] += abs(n - R)
        mark = "*" if c in TRUTH else " "
        print(f"{c}{mark:<1}{R:>7}{ndel:>7}" + "".join(f"{n-R:+8d}" for n in ns)
              + f"   {best[1]:.2f}({abs(best[0]-R)})")
    print("合计|偏差|: " + "  ".join(f"{t:.2f}={e}" for t, e in sorted(tot_err.items())))


if __name__ == "__main__":
    main()
