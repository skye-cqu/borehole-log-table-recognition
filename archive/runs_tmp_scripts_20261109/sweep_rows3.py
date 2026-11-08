# -*- coding: utf-8 -*-
"""扫描 v3:三种"数值区右界"取法 × 阈值,一次比完(读 runs/tmp/行链3_*.json,秒级)。

A 常数     xb = 定稿 x_at_mid
B 逐条插值 xb = 锚线折线在该 y 处的 x
C 邻域中位 xb = 锚线上 |y'-y|<=WIN 的点取中位数(抗碎片串线,1035 的病)
标尺:1032=103 / 1042=112 两张真值偏差;另报 30 张层界合计与薄行数、交付多值格率(独立信号)。
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
from src.table.track_columns import load_chain                      # noqa: E402

TRUTH = {"1032": 103, "1042": 112}
DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"
NUM = re.compile(r"\d+\.\d+")
NUMHDR = ("深度", "层厚", "采长", "真厚")
WIN = 400.0


def uv(iv):
    ca = cb = None
    tot = 0.0
    for a, b in sorted(iv):
        if ca is None:
            ca, cb = a, b
        elif a <= cb:
            cb = max(cb, b)
        else:
            tot += cb - ca
            ca, cb = a, b
    return tot + (cb - ca if ca is not None else 0.0)


def anchor_pts(code, ax):
    """锚定列线(定稿里 x_at_mid==ax 那条)的全分辨率 (y,x) 点列——现取,不进缓存。"""
    stem = f"钻孔柱状图{code}"
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"}
    st = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json")
                    .read_text(encoding="utf-8"))
    c = min(st["columns"], key=lambda c: abs(c["x_at_mid"] - ax))
    pts, _ = load_chain({"segment_ids": c["segment_ids"]}, seg)
    return np.asarray(pts, float)


def load(code):
    d = json.loads((paths.RUNS_DIR / "tmp" / f"行链3_{code}.json").read_text(encoding="utf-8"))
    ap = anchor_pts(code, d["anchor_x"])                   # (y, x) 按 y 升序
    out = []
    for y, iv in d["lines"]:
        w = ap[np.abs(ap[:, 0] - y) <= WIN]
        b = {"A": d["anchor_x"],
             "B": float(np.interp(y, ap[:, 0], ap[:, 1])),
             "C": float(np.median(w[:, 1])) if len(w) else d["anchor_x"]}
        b = {k: float(np.clip(v, d["tab_l"] + 60, d["tab_r"] - 60)) for k, v in b.items()}
        cn = {k: uv([(max(a, d["tab_l"]), min(bb, v)) for a, bb in iv])
              / max(v - d["tab_l"], 1) for k, v in b.items()}
        out.append({"y": y, "b": b, "cn": cn})
    return out, d


def delivered(code):
    p = DELIV / f"{code}_还原.xlsx"
    if not p.exists():
        return 0, 0
    ws = load_workbook(p, read_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h or "") for h in rows[0]]
    idx = [i for i, h in enumerate(hdr) if any(k in h for k in NUMHDR)]
    multi = sum(1 for r in rows[1:] for i in idx
                if isinstance(r[i], str) and len(NUM.findall(r[i])) > 1)
    return len(rows) - 1, multi


def main():
    codes = sorted(p.stem[4:] for p in (paths.RUNS_DIR / "tmp").glob("行链3_*.json"))
    L = {c: load(c)[0] for c in codes}
    dv = {c: delivered(c) for c in codes}
    print(f"缓存 {len(codes)} 张")
    print(f"{'取界':<4}{'阈值':<7}{'1032':>10}{'1042':>10}{'总层界':>9}{'薄行<40':>9}")
    for rule in "ABC":
        for th in (0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3):
            tot = thin = 0
            cells = []
            for c in ("1032", "1042"):
                if c not in L:
                    cells.append("-")
                    continue
                n = sum(1 for x in L[c] if x["cn"][rule] >= th)
                cells.append(f"{n}({n-TRUTH[c]:+d})")
            for c in codes:
                ys = sorted(x["y"] for x in L[c] if x["cn"][rule] >= th)
                tot += len(ys)
                if len(ys) > 1:
                    thin += int((np.diff(ys) < 40).sum())
            print(f"{rule:<4}{th:<7}" + "".join(f"{x:>10}" for x in cells)
                  + f"{tot:>9}{thin:>9}")

    if len(sys.argv) < 3:
        return
    rule, th = sys.argv[1], float(sys.argv[2])
    print(f"\n=== 逐张 取界{rule} @cov_num>={th} ===")
    print(f"{'张':<6}{'层界':>6}{'交付':>6}{'倍':>6}{'薄行':>6}{'最小行高':>9}"
          f"{'定稿锚x':>9}{'本张右界范围':>13}{'交付多值格':>11}")
    rows = []
    for c in codes:
        lines = L[c]
        ys = sorted(x["y"] for x in lines if x["cn"][rule] >= th)
        g = np.diff(ys) if len(ys) > 1 else np.array([0.0])
        bs = [x["b"][rule] for x in lines]
        n, m = dv[c]
        rows.append((c, len(ys), n, len(ys) / max(n, 1), int((g < 40).sum()), float(g.min()),
                     min(bs), max(bs), m))
    for r in sorted(rows, key=lambda x: -x[3]):
        mk = "*" if r[0] in TRUTH else " "
        print(f"{r[0]}{mk:<1}{r[1]:>6}{r[2]:>6}{r[3]:>6.2f}{r[4]:>6}{r[5]:>9.0f}"
              f"{'':>9}{r[6]:>6.0f}-{r[7]:<6.0f}{r[8]:>11}")


if __name__ == "__main__":
    main()
