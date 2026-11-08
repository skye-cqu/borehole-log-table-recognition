# -*- coding: utf-8 -*-
"""A/B：把层界折线按"图上到底有没有这条横线墨"裁短——墨断的地方线也不画。

歪线裁片实测（1037 y=22133、1027 y=11412）：数值区那一段贴着真行界，往东进了描述栏就
爬到上下两行之间——那里图上本来没有这条横线（描述栏一行顶数值栏几行 = rowspan）。
链把这段没墨的地方也连上了，画出来就是一条穿过文字的假线，正是用户禁止的那一类。

这一档只做减法：从线的中点往两边扩，遇到 >GAP px 的无墨断口就停，poly 和 x 一起裁短。
不新增点、不外插、不改判界，剩下的部分每一段都有横线墨。
产物 runs/tmp/ab/裁墨/。用法: python runs/tmp/ab_trim.py [1037 1027]   # 无参数=30 张
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
import yardstick as Y                                               # noqa: E402
from src.core import paths                                          # noqa: E402

OUT = ROOT / "runs" / "tmp" / "ab" / "裁墨"
N = 200            # 一条线采多少个 x 判有无墨
GAP = 40.0         # 连续无墨超过这么长 px 就在此裁断（横线被竖线打断远短于此）
MIN_KEEP = 0.30    # 裁完不足原跨度这个比例：宁可保留原线，不裁成一条小尾巴


def ink_ok(ruling, r, xs):
    """这些 x 处，线离最近的横线墨有多少 px（±SEARCH 内找不到 = inf）。"""
    H, W = ruling.shape
    out = []
    for x in xs:
        y = Y.line_y(r, x)
        xi = int(np.clip(x, 0, W - 2))
        lo, hi = max(0, int(y) - Y.SEARCH), min(H, int(y) + Y.SEARCH)
        idx = np.flatnonzero(ruling[lo:hi, xi])
        out.append(float(np.abs(idx + lo - y).min()) if len(idx) else np.inf)
    return np.array(out)


def keep_span(xs, ok):
    """把每个 >GAP 的无墨游程中点当刀口，取中点所在的那一段 → (左界, 右界)。

    短的无墨段（竖线压过、扫描断口）不下刀，避免把一条真线切成小尾巴。
    """
    cuts = []
    i = 0
    while i < len(ok):
        if ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(ok) and not ok[j + 1]:
            j += 1
        if xs[j] - xs[i] > GAP:
            cuts.append((xs[i] + xs[j]) / 2)
        i = j + 1
    edges = [xs[0]] + sorted(cuts) + [xs[-1]]
    mid = xs[len(xs) // 2]
    seg = [(edges[k], edges[k + 1]) for k in range(len(edges) - 1)]
    return max((s for s in seg if s[0] <= mid <= s[1]), key=lambda s: s[1] - s[0],
               default=(xs[0], xs[-1]))


def trim(code):
    stem = f"钻孔柱状图{code}"
    src = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                      f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(stem)
    n_cut = n_keep = 0
    for r in src["rows"]:
        x0, x1 = float(r["x"][0]), float(r["x"][1])
        xs = np.linspace(x0, x1, N)
        ok = ink_ok(ruling, r, xs) <= Y.POLY_TOL
        if ok.all():
            n_keep += 1
            continue
        a, b = keep_span(xs, ok)
        if b - a < MIN_KEEP * (x1 - x0):
            n_keep += 1
            continue
        pl = np.asarray(r["poly"], float)
        keep = pl[(pl[:, 0] >= a) & (pl[:, 0] <= b)]
        if len(keep) < 2:
            n_keep += 1
            continue
        r["poly"] = [[round(float(u), 1), round(float(v), 1)] for u, v in keep]
        r["x"] = [int(keep[0, 0]), int(keep[-1, 0])]
        r["y_at_mid"] = round(float(np.median(keep[:, 1])), 1)
        r["n_trimmed"] = round(1 - (b - a) / (x1 - x0), 3)
        n_cut += 1
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stem}_行判定.json").write_text(json.dumps(src, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    return code, len(src["rows"]), n_cut, n_keep


if __name__ == "__main__":
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
            sorted(p.name.split("图")[1].split("_")[0]
                   for p in (paths.RUNS_DIR / "table_reconstruct").glob("*_行判定.json"))
    tot = [0, 0, 0]
    for c in codes:
        code, n, cut, keep = trim(c)
        tot = [tot[0] + n, tot[1] + cut, tot[2] + keep]
        print(f"{code}: 层界 {n}  裁短 {cut}  未动 {keep}", flush=True)
    print(f"合计: 层界 {tot[0]}  裁短 {tot[1]}  未动 {tot[2]}")
