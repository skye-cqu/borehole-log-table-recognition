# -*- coding: utf-8 -*-
"""柱状带（真厚|柱状 → 柱状|岩性）该不该参与 6c：三档对跑，同一把尺子。

用户的做法（阶段6g `clean_columns.py` 已按此把"柱状""简易水文曲线"两列裁掉）：带里画的是岩性
图案，不是表格线，不该当结构证据。本轮量三件事：
  1 刀口落在哪：门禁4 切出来的台阶有多少就在带里。带宽 ~205px 而窗宽 WIN_DX=300px，
    带内的台阶两侧凑不满两个整半窗 → 切分闸和形状闸在带里都是盲区，线可以在带里跳一整行
    而两道闸读数都是 0；
  2 只收窗口：数值区右界从带东缘挪到带西缘（带内墨不再算覆盖）；
  3 删带+收窗口：整条落在带里的阶段4 段丢掉（= 用户"删列"），链在带处自然断开，窗口同步收到带西缘。

只删输入段，不造新点（约束2）。骑在带缘上的段保留（那是真行线伸到带缘的部分，删了会把真行截短）。

用法: python runs/tmp/ab_bandmask.py [code...]     # 无参数=30 张
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr, track_group                 # noqa: E402
from src.table.track_columns import x_at                            # noqa: E402
import yardstick as Y                                               # noqa: E402
import diag_missed as M                                             # noqa: E402
from sweep_gates import offink, SAMPLE, SEARCH, OVER                 # noqa: E402
from ab_split import spacing                                        # noqa: E402
from diag_band import band_edges                                    # noqa: E402

BAND_PAD = 6.0          # 判"段整条落在带里"时给带缘留的余量(px)
ARMS = ("现状", "只收窗口", "删带+收窗口")


def _build(stem, segs_src, cj):
    """track_rows.load_chains 的后半段（建链→合并→点列），输入段换成给定的那批。"""
    img_w = int(cj["width"])
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    ink = track_group.binarize(gray, track_group.PARAMS).T
    segs = []
    for s in segs_src:
        pts = np.asarray(s["points"], float)
        i_top, i_bot = int(pts[:, 1].argmin()), int(pts[:, 1].argmax())
        adj_t = pts[1] if i_top == 0 else pts[i_top - 1]
        adj_b = pts[-2] if i_bot == len(pts) - 1 else pts[i_bot + 1]
        segs.append({"id": s["id"], "top": pts[i_top][::-1].copy(),
                     "bot": pts[i_bot][::-1].copy(),
                     "v_top": tr._dir_down(pts[i_top][::-1], adj_t[::-1]),
                     "v_bot": tr._dir_down(pts[i_bot][::-1], adj_b[::-1]),
                     "points": tr._swap_points(s["points"]), "length": float(s["length"])})
    tracks, _ = track_group.build_tracks(segs, ink, track_group.PARAMS)
    groups = tr.merge_tracks(tracks, {s["id"]: s for s in segs})
    longs = [g for g in groups if g["y1"] - g["y0"] >= 0.5 * img_w]
    if not longs:
        return None
    tab_l = min(g["y0"] for g in longs)
    tab_r = max(g["y1"] for g in longs)
    items = []
    for g in groups:
        x0, x1 = max(g["y0"], tab_l), min(g["y1"], tab_r)
        if x1 - x0 <= 0:
            continue
        items.append({"y": tr.x_at_mid(g), "x": (x0, x1), "res": g["res"],
                      "step": tr.step_of(g["pts"]), "slope": tr.slope_of(g["pts"]),
                      "pts": g["pts"], "ids": list(g["ids"])})
    items.sort(key=lambda it: it["y"])
    s0 = float(np.median([it["slope"] for it in items]))
    for it in items:
        it["ptp"] = tr.ptp_off(it["pts"], s0)
    return {"stem": stem, "items": items, "s0": s0, "tab_l": tab_l, "tab_r": tab_r,
            "tab_w": max(tab_r - tab_l, 1.0), "col": tr.column_anchor(stem),
            "n_segs": len(segs_src), "n_chains": len(groups), "warns": []}


def load_chains_masked(stem, west, east):
    """load_chains 的删带版：整条落在柱状带里的横段丢掉，链在带处自然断开。"""
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    segs_src = [s for s in cj["lines"]
                if s["direction"] == "horizontal" and s["label"] == "high"]
    kept = []
    for s in segs_src:
        p = np.asarray(s["points"], float)
        x0, x1 = p[:, 0].min(), p[:, 0].max()
        ym = float(np.median(p[:, 1]))
        if x_at(west, ym) + BAND_PAD <= x0 and x1 <= x_at(east, ym) - BAND_PAD:
            continue                                        # 整段在带里 = 图案边线
        kept.append(s)
    return _build(stem, kept, cj), len(segs_src) - len(kept)


def offink_out(ruling, rows, band):
    """sweep_gates.offink 的"带外采样"版：柱状带里的采样丢掉再算离墨%。

    为什么要这一把：带里的图案边线（煤块上下缘、灰岩砖缝）本身就被 adaptiveThreshold+40×1
    开运算当成"横线墨"，所以一条被图案拽偏的线在标尺眼里仍是贴墨的——标尺和两道闸
    （窗 300px > 带宽 205px）在同一条带上是同一个盲区。
    """
    H, W = ruling.shape
    wl, er = band
    out = []
    for r in rows:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        ds = []
        for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), SAMPLE):
            if wl <= x <= er:
                continue
            y = tr.row_y(r, x)
            lo = max(0, int(y) - SEARCH)
            seg = ruling[lo:min(H, int(y) + SEARCH), int(x)]
            idx = np.flatnonzero(seg)
            ds.append(float(np.abs(idx + lo - y).min()) if len(idx) else np.nan)
        out.append(float(np.mean([not np.isfinite(v) or v > OVER for v in ds])) * 100 if ds else 0.0)
    return out


def drag(rows, west, band, row_h, s0):
    """带内被拽偏的层界条数：这条线在带里的中位高度 减 它在带外的中位高度（扣全表斜率）。"""
    n = 0
    worst = []
    for r in rows:
        p = np.asarray(r["poly"], float)
        if len(p) < 3:
            continue
        ym = float(np.median(p[:, 1]))
        wl, er = x_at(west, ym), band[1]
        inb = (p[:, 0] >= wl) & (p[:, 0] <= er)
        if inb.sum() < 3 or (~inb).sum() < 3:
            continue
        q = p[:, 1] - s0 * p[:, 0]
        d = float(np.median(q[inb]) - np.median(q[~inb]))
        if abs(d) > 0.35 * row_h:
            n += 1
            worst.append((round(abs(d) / row_h, 2), int(r["y_at_mid"])))
    return n, sorted(worst, reverse=True)[:3]


def measure(ch, ruling, band, west, col=None):
    o = tr.assemble(dict(ch, col=col) if col is not None else ch)
    oi = offink(ruling, o["rows"])
    oo = offink_out(ruling, o["rows"], band)
    dr, worst = drag(o["rows"], west, band, o["row_h"], ch["s0"])
    reg, tight = spacing(o)[0], spacing(o)[1]
    return o, dict(n=len(o["rows"]), miss=len(M.missed(o, ruling)),
                   o10=sum(1 for v in oi if v > 10), o10out=sum(1 for v in oo if v > 10),
                   o30=sum(1 for v in oi if v > 30), drag=dr, worst=worst,
                   med=float(np.median(oi)) if oi else 0.0, off=len(o["off_grid"]),
                   reg=reg, tight=tight, row_h=o["row_h"])


def cut_where(ch, band, row_h):
    """门禁4 的刀口 x 落在带里 / 带外 的计数。"""
    jump = tr.SPLIT_FRAC * row_h
    wl, er = band
    n_in = n_out = 0
    for it in ch["items"]:
        pieces = tr.split_pts(it["pts"], ch["s0"], jump)
        for a, b in zip(pieces, pieces[1:]):
            if wl <= (a[-1, 0] + b[0, 0]) / 2 <= er:
                n_in += 1
            else:
                n_out += 1
    return n_in, n_out


def churn(ya, yb, tol):
    """两档层界集合按 y 就近配对（容差 tol px）→ (丢, 补)。"""
    return (sum(1 for y in ya if not any(abs(y - v) <= tol for v in yb)),
            sum(1 for y in yb if not any(abs(y - v) <= tol for v in ya)))


def main(codes):
    acc = {t: [] for t in ARMS}
    cin = cout = nsh = 0
    for code in codes:
        stem = f"钻孔柱状图{code}"
        east, west, bw, ex = band_edges(stem)
        if west is None:
            print(f"{code}: 锚线 x={ex:.0f} 左邻间距不像柱状带（1020 型：锚线本身就是带西缘）— 跳过")
            continue
        ch_now = tr.load_chains(stem)
        if ch_now is None:
            continue
        ruling = Y.masks(stem)[0]
        ch_cut, n_drop = load_chains_masked(stem, west, east)
        ym = float(np.median([it["y"] for it in ch_now["items"]]))
        band = (x_at(west, ym), x_at(east, ym))
        o0, m0 = measure(ch_now, ruling, band, west)
        o1, m1 = measure(ch_now, ruling, band, west, col=west)
        o2, m2 = measure(ch_cut, ruling, band, west, col=west)
        i, j = cut_where(ch_now, band, m0["row_h"])
        lost, gain = churn([r["y_at_mid"] for r in o0["rows"]],
                           [r["y_at_mid"] for r in o2["rows"]], 0.3 * m0["row_h"])
        nsh += 1
        cin += i
        cout += j
        print(f"{code}: 带[{band[0]:.0f},{band[1]:.0f}]宽{band[1]-band[0]:.0f} 丢带内段{n_drop} "
              f"刀口在带内{i}/带外{j}  "
              + "  ".join(f"{t} 层界{m['n']:>3} 拽偏{m['drag']:>3} 漏{m['miss']:>2} "
                          f">10%{m['o10']:>4}/{m['o10out']:>4} 挤{m['tight']:>3} "
                          f"规整{m['reg']:>3.0f}% 剔{m['off']:>3}"
                          for t, m in zip(ARMS, (m0, m1, m2)))
              + f"  删带后层界 -{lost} +{gain}")
        for t, m in zip(ARMS, (m0, m1, m2)):
            acc[t].append(m)
    for t in ARMS:
        v = acc[t]
        print(f"合计({len(v)}张) {t}: 层界{sum(x['n'] for x in v)} 带内拽偏{sum(x['drag'] for x in v)} "
              f"漏{sum(x['miss'] for x in v)} 离墨>10%(全采样/带外采样)"
              f"{sum(x['o10'] for x in v)}/{sum(x['o10out'] for x in v)} >30%{sum(x['o30'] for x in v)} "
              f"挤{sum(x['tight'] for x in v)} 剔{sum(x['off'] for x in v)} "
              f"规整{np.mean([x['reg'] for x in v]):.0f}% 中位离墨{np.mean([x['med'] for x in v]):.1f}")
    print(f"门禁4 刀口位置合计: 柱状带内 {cin} / 带外 {cout}")


if __name__ == "__main__":
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    main(codes)
