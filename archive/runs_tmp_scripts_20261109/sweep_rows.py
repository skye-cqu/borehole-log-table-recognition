# -*- coding: utf-8 -*-
"""阶段B(秒级):读 runs/tmp/行链_*.json 缓存,扫阈值出判据推导表。

对每个候选阈值,逐张报:层界数 / 现行交付行数 / 最小行高px / 巨大间隙数(>3×中位行高)
/ 1032、1042 与已知真值(103/112)的偏差。
选阈标准:①两已知真值偏差最小;②不产生 <40px 的畸形薄行;③巨大间隙数最少(漏界信号)。
"""
import json
import sys
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                    # noqa: E402

TRUTH = {"1032": 103, "1042": 112}
DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"


def union(iv):
    iv = sorted((a, b) for a, b in iv if b > a)
    tot, ca, cb = 0.0, None, None
    for a, b in iv:
        if ca is None:
            ca, cb = a, b
        elif a <= cb:
            cb = max(cb, b)
        else:
            tot += cb - ca
            ca, cb = a, b
    return tot + (cb - ca if ca is not None else 0.0)


def lines_of(code):
    d = json.loads((paths.RUNS_DIR / "tmp" / f"行链_{code}.json").read_text(encoding="utf-8"))
    nw = max(d["num_x"] - d["tab_l"], 1)
    dw = max(d["tab_r"] - d["num_x"], 1)
    return [{"y": y, "cn": union(n) / nw, "cd": union(s) / dw} for y, n, s in d["lines"]]


def delivered_rows(code):
    p = DELIV / f"{code}_还原.xlsx"
    if not p.exists():
        for cand in DELIV.glob(f"{code}*.xlsx"):
            p = cand
    return load_workbook(p, read_only=True).active.max_row - 1


def stats(L, th):
    ys = sorted(x["y"] for x in L if x["cn"] >= th)
    if len(ys) < 3:
        return None
    g = np.diff(ys)
    med = float(np.median(g))
    return {"n": len(ys), "min": float(g.min()), "thin": int((g < 40).sum()),
            "big": int((g > 3 * med).sum()), "med": med}


def main():
    codes = sorted(p.stem.split("_")[1] for p in (paths.RUNS_DIR / "tmp").glob("行链_*.json"))
    deliv = {c: delivered_rows(c) for c in codes}
    print(f"{'阈值':<6}" + "".join(f"{c:>10}" for c in ("1032", "1042"))
          + f"{'总层界':>9}{'薄行<40':>9}{'巨大间隙':>9}{'vs交付':>9}")
    for th in (0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3):
        tot = thin = big = 0
        dsum = 0
        cells = []
        for c in codes:
            s = stats(lines_of(c), th) or {"n": 0, "thin": 0, "big": 0, "med": 0}
            tot += s["n"]
            thin += s["thin"]
            big += s["big"]
            dsum += s["n"] - deliv[c]
            if c in TRUTH:
                cells.append(f"{s['n']}({s['n']-TRUTH[c]:+d})")
        while len(cells) < 2:
            cells.append("-")
        print(f"{th:<6}" + "".join(f"{x:>10}" for x in cells)
              + f"{tot:>9}{thin:>9}{big:>9}{dsum:>+9}")
    print("\n交付行数合计 =", sum(deliv.values()), " 张数 =", len(codes))
    th = float(sys.argv[1]) if len(sys.argv) > 1 else 0.45
    print(f"\n=== 逐张明细 @cov_num>={th} ===")
    print(f"{'张':<6}{'层界':>6}{'交付':>6}{'倍':>6}{'薄行<40':>9}{'巨大间隙':>9}"
          f"{'中位行高':>9}{'最小行高':>9}")
    rows = []
    for c in codes:
        L = lines_of(c)
        s = stats(L, th) or {"n": 0, "thin": 0, "big": 0, "med": 0, "min": 0}
        ys = sorted(x["y"] for x in L if x["cn"] >= th)
        g = np.diff(ys) if len(ys) > 1 else [0]
        rows.append((c, s["n"], deliv[c], s["n"] / max(deliv[c], 1), s["thin"], s["big"],
                     s["med"], float(min(g))))
    for r in sorted(rows, key=lambda x: -x[3]):
        mark = "*" if r[0] in TRUTH else " "
        print(f"{r[0]}{mark:<1}{r[1]:>6}{r[2]:>6}{r[3]:>6.2f}{r[4]:>9}{r[5]:>9}"
              f"{r[6]:>9.0f}{r[7]:>9.0f}")


if __name__ == "__main__":
    main()
