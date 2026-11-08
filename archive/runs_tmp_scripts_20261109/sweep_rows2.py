# -*- coding: utf-8 -*-
"""阈值扫描 v2:数值区右界改用 6a 列结构定稿(编号线),逐条线插值。

对每个候选阈值报:两张已知真值(1032=103 / 1042=112)偏差、30 张层界合计、薄行<40px 数。
命令行给阈值时另出逐张明细(层界/交付/倍数/最小行高/定稿锚点 vs 6b 右界)。
"""
import json
import sys
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

TRUTH = {"1032": 103, "1042": 112}
DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"


def uv(iv):
    ca = cb = None
    tot = 0.0
    for a, b in sorted((a, b) for a, b in iv if b > a):
        if ca is None:
            ca, cb = a, b
        elif a <= cb:
            cb = max(cb, b)
        else:
            tot += cb - ca
            ca, cb = a, b
    return tot + (cb - ca if ca is not None else 0.0)


def load(code):
    d = json.loads((paths.RUNS_DIR / "tmp" / f"行链2_{code}.json").read_text(encoding="utf-8"))
    out = []
    for y, xb, n, s in d["lines"]:
        nw = max(xb - d["tab_l"], 1)
        dw = max(d["tab_r"] - xb, 1)
        out.append({"y": y, "cn": uv(n) / nw, "cd": uv(s) / dw})
    return out, d


def delivered(code):
    p = DELIV / f"{code}_还原.xlsx"
    if not p.exists():
        p = next(DELIV.glob(f"{code}*.xlsx"), None)
    return load_workbook(p, read_only=True).active.max_row - 1 if p else 0


def main():
    codes = sorted(p.stem[4:] for p in (paths.RUNS_DIR / "tmp").glob("行链2_*.json"))
    L = {c: load(c) for c in codes}
    deliv = {c: delivered(c) for c in codes}
    print(f"缓存 {len(codes)} 张")
    print(f"{'阈值':<7}{'1032':>12}{'1042':>12}{'总层界':>9}{'薄行<40':>9}")
    for th in (0.6, 0.55, 0.5, 0.48, 0.45, 0.42, 0.4, 0.35, 0.3):
        tot = thin = 0
        cells = []
        for c in ("1032", "1042"):
            ys = [x["y"] for x in L[c][0] if x["cn"] >= th]
            cells.append(f"{len(ys)}({len(ys)-TRUTH[c]:+d})")
        for c in codes:
            ys = sorted(x["y"] for x in L[c][0] if x["cn"] >= th)
            tot += len(ys)
            if len(ys) > 1:
                thin += int((np.diff(ys) < 40).sum())
        print(f"{th:<7}" + "".join(f"{x:>12}" for x in cells) + f"{tot:>9}{thin:>9}")

    if len(sys.argv) < 2:
        return
    th = float(sys.argv[1])
    print(f"\n=== 逐张 @cov_num>={th} ===")
    print(f"{'张':<6}{'层界':>6}{'交付':>6}{'倍':>6}{'薄行':>6}{'最小行高':>9}"
          f"{'定稿锚点x':>10}{'锚格宽':>8}{'6b右界':>8}")
    rows = []
    for c in codes:
        lines, d = L[c]
        ys = sorted(x["y"] for x in lines if x["cn"] >= th)
        g = np.diff(ys) if len(ys) > 1 else np.array([0.0])
        hm = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"钻孔柱状图{c}_表头映射.json")
                        .read_text(encoding="utf-8"))
        desc = next((x for x in hm.get("columns", []) if "岩性" in str(x.get("name", ""))), None)
        b6 = desc["x_in_band"][0] if desc else None
        rows.append((c, len(ys), deliv[c], len(ys) / max(deliv[c], 1),
                     int((g < 40).sum()), float(g.min()), d["anchor_x"], d["anchor_w"], b6))
    for r in sorted(rows, key=lambda x: -x[3]):
        m = "*" if r[0] in TRUTH else " "
        print(f"{r[0]}{m:<1}{r[1]:>6}{r[2]:>6}{r[3]:>6.2f}{r[4]:>6}{r[5]:>9.0f}"
              f"{r[6]:>10.0f}{r[7]:>8.0f}{str(r[8]):>8}")


if __name__ == "__main__":
    main()
