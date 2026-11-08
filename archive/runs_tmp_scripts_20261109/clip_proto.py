# -*- coding: utf-8 -*-
"""列分带裁剪原型：行线只保留 数值区 与 岩性描述，删掉 柱状带 与 简易水文曲线。
先在 runs/tmp 里量清楚裁得对不对，再往交付脚本里合。"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                        # noqa: E402
from src.table import track_rows as tr                            # noqa: E402
from src.table.track_columns import load_chain                    # noqa: E402

RECON = paths.RUNS_DIR / "table_reconstruct"
NEG, POS = -1e9, 1e9


def bounds(stem):
    """柱状带西/东缘 + 岩性|水文 分隔线，三条 (y,x) 链都续到表底 → 三个 x(y)  callable。"""
    w, e, _ = tr.content_band(stem)
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]}
    cols = sorted(json.load(open(RECON / f"{stem}_列结构定稿.json", encoding="utf-8"))["columns"],
                  key=lambda c: c["x_at_mid"])
    chains = [load_chain(c, seg)[0] for c in cols]
    y_end = float(cj["height"])
    last = tr.continue_below(chains[-1], chains[:-1], y_end)
    zw = (lambda y, c=w: tr.edge_at(c, y)) if w is not None else (lambda y: NEG)
    ze = (lambda y, c=e: tr.edge_at(c, y)) if e is not None else (lambda y: NEG)
    sw = (lambda y, c=last: tr.edge_at(c, y)) if last is not None else (lambda y: POS)
    return zw, ze, sw


def clip_poly(poly, zw, ze, sw):
    """把行线折线沿 x 走一遍，只吐 数值区(x<zw) 与 岩性(ze<=x<sw) 两段，切点在带缘上。"""
    P = np.asarray(poly, float)
    if len(P) < 2:
        return [] if not _keep(P[0, 0], P[0, 1], zw, ze, sw) else [P.tolist()]

    def region(x, y):
        if x < zw(y):
            return 0                       # 数值区 keep
        if x < ze(y):
            return 1                       # 柱状带 drop
        if x < sw(y):
            return 2                       # 岩性描述 keep
        return 3                           # 水文 drop

    pieces, cur, cur_r = [], [], None
    for (ax, ay), (bx, by) in zip(P, P[1:]):
        ts = []
        for f in (zw, ze, sw):
            ga, gb = ax - f(ay), bx - f(by)
            if (ga < 0) != (gb < 0) and ga != gb:
                ts.append(ga / (ga - gb))
        ts = sorted(t for t in ts if 0 < t < 1)
        marks = [0.0] + ts + [1.0]
        for t0, t1 in zip(marks, marks[1:]):
            tm = 0.5 * (t0 + t1)
            r = region(ax + (bx - ax) * tm, ay + (by - ay) * tm)
            s0 = (ax + (bx - ax) * t0, ay + (by - ay) * t0)
            s1 = (ax + (bx - ax) * t1, ay + (by - ay) * t1)
            if r in (0, 2):
                if cur_r != r:
                    if len(cur) >= 2:
                        pieces.append(cur)
                    cur = [s0]
                    cur_r = r
                cur.append(s1)
            elif cur_r is not None:
                if len(cur) >= 2:
                    pieces.append(cur)
                cur, cur_r = [], None
    if len(cur) >= 2:
        pieces.append(cur)
    return pieces


def _keep(x, y, zw, ze, sw):
    return x < zw(y) or ze(y) <= x < sw(y)


def max_slope(piece):
    """窗口斜率绝对值中位的最大者——近水平的行线该≈0，爬/歪的会大。"""
    p = np.asarray(piece, float)
    if len(p) < 3:
        return 0.0
    dx = np.diff(p[:, 0]); dy = np.diff(p[:, 1])
    s = np.abs(dy / np.where(np.abs(dx) < 1, np.nan, dx))
    s = s[~np.isnan(s)]
    return float(np.median(s)) if len(s) else 0.0


if __name__ == "__main__":
    sus = json.load(open(paths.LINE_SUSPECTS, encoding="utf-8")) if paths.LINE_SUSPECTS.exists() else []
    print("== 5 条待核线裁剪前后：段数 / 每段窗斜率中位 ==")
    for s in sus:
        stem = s["image"]; y = s["y"]
        rd = json.load(open(RECON / f"{stem}_行判定.json", encoding="utf-8"))
        row = min(rd["rows"], key=lambda r: abs(r["y_at_mid"] - y))
        zw, ze, sw = bounds(stem)
        pcs = clip_poly(row["poly"], zw, ze, sw)
        b = max_slope(row["poly"])
        a = [round(max_slope(p), 4) for p in pcs]
        print(f"{stem[-4:]} y{y}: 原斜率{b:.3f} → {len(pcs)}段 {a}")

    print("\n== 全 30 张：行数 vs 裁后段数 ==")
    stems = sorted(p.name[:-len("_行判定.json")] for p in RECON.glob("*_行判定.json"))
    tot_r = tot_p = 0
    for stem in stems:
        rd = json.load(open(RECON / f"{stem}_行判定.json", encoding="utf-8"))
        zw, ze, sw = bounds(stem)
        n_r = len(rd["rows"])
        n_p = sum(max(1, len(clip_poly(r["poly"], zw, ze, sw))) for r in rd["rows"])
        tot_r += n_r; tot_p += n_p
        print(f"{stem[-4:]}: 行 {n_r} → 段 {n_p}")
    print(f"合计: 行 {tot_r} → 段 {tot_p}")
