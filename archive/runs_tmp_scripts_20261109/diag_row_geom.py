# -*- coding: utf-8 -*-
"""层界几何偏差逐跳定位（只读，不改任何产物）。

一条层界从"原图小线段"到"图上那条红线"要过四跳，逐跳量它各自引入多少 px 偏差：

  跳1 线段→链   阶段3/4/5：链的点列 离它自己引用的原始 high 段 有多远
  跳2 链→簇     阶段6c 聚簇：我把 ±LINE_TOL 内的链并成"一条线"，
                同簇各链在同一 x 处的 y 相互差多少（差得多=并错了，一条簇其实是两条真实线）
  跳3 簇→存值   表示法：JSON 里只存一个 y_at_mid，簇自己的形状在同一 x 处离它多远
  跳4 存值→画   画图：draw_rows 用 (x[0],y)→(x[1],y) 一条直线，
                这条直线走过的 x 上，有多少 x 根本没有墨（画出了一张图上不存在的线）

每跳给 中位/最大 偏差，哪一跳最大，问题就在哪个阶段。
另存证据图：同一窗口叠 原始段(绿点) / 链(蓝线) / 存的平线(红) / 实际画的线(黄)。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_group, track_rows                       # noqa: E402
from src.table.track_columns import merge_tracks                    # noqa: E402

SAMPLE = 40
INK_TOL = 8.0


def chains_of(stem):
    """复现阶段6c 的建链（与 determine_rows 同一套代码），返回 groups + 原始 high 段。"""
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    src = [s for s in cj["lines"] if s["direction"] == "horizontal" and s["label"] == "high"]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    ink = track_group.binarize(gray, track_group.PARAMS).T
    segs = []
    for s in src:
        pts = np.asarray(s["points"], float)
        i_top, i_bot = int(pts[:, 1].argmin()), int(pts[:, 1].argmax())
        adj_t = pts[1] if i_top == 0 else pts[i_top - 1]
        adj_b = pts[-2] if i_bot == len(pts) - 1 else pts[i_bot + 1]
        segs.append({"id": s["id"],
                     "top": pts[i_top][::-1].copy(), "bot": pts[i_bot][::-1].copy(),
                     "v_top": track_rows._dir_down(pts[i_top][::-1], adj_t[::-1]),
                     "v_bot": track_rows._dir_down(pts[i_bot][::-1], adj_b[::-1]),
                     "points": track_rows._swap_points(s["points"]),
                     "length": float(s["length"])})
    tracks, _ = track_group.build_tracks(segs, ink, track_group.PARAMS)
    return merge_tracks(tracks, {s["id"]: s for s in segs}), src


def yshape(pts, xs):
    """点列 (x,y) 在 xs 上的 y；无覆盖返回 nan。pts 已按 x 排序。"""
    if len(pts) < 2:
        return np.full(len(xs), np.nan)
    lo, hi = pts[0, 0], pts[-1, 0]
    out = np.where((xs >= lo) & (xs <= hi), np.interp(xs, pts[:, 0], pts[:, 1]), np.nan)
    return out


def diag(code):
    stem = f"钻孔柱状图{code}"
    groups, src = chains_of(stem)
    seg = {s["id"]: np.asarray(s["points"], float) for s in src}
    rd = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                    .read_text(encoding="utf-8"))
    gid = {}
    for g in groups:
        for i in g["ids"]:
            gid.setdefault(i, []).append(g)
    e1, e2, e3, e4 = [], [], [], []
    for r in rd["rows"]:
        x0, x1 = r["x"]
        xs = np.linspace(x0 + 20, x1 - 20, SAMPLE)
        mem = [g for i in r["segment_ids"] for g in gid.get(i, [])]
        if not mem:
            continue
        # 跳1：链点列 vs 原始段点
        d1 = []
        for g in mem:
            gp = np.asarray(g["pts"], float)
            for s in g["ids"]:
                if s not in seg:
                    continue
                sp = seg[s]
                yy = yshape(gp, sp[:, 0])
                ok = ~np.isnan(yy)
                if ok.sum():
                    d1.append(float(np.abs(yy[ok] - sp[ok, 1]).max()))
        # 跳2：同簇各链在同一 x 的 y 相互差
        shapes = np.array([yshape(np.asarray(g["pts"], float), xs) for g in mem])
        d2 = [float(np.nanmax(s) - np.nanmin(s)) for s in shapes] if len(mem) > 1 else []
        # 跳3：簇形状(逐 x 取各链中位) vs 存的那个 y
        ref = np.nanmedian(shapes, axis=0)
        ok = ~np.isnan(ref)
        d3 = float(np.abs(ref[ok] - r["y_at_mid"]).max()) if ok.sum() else np.nan
        # 跳4：画的直线走过的 x 上，有多少 x 处 12px 内没有任何链/段墨
        allp = np.vstack([np.asarray(g["pts"], float) for g in mem])
        near = np.array([bool(len(allp[(np.abs(allp[:, 0] - x) <= 12)
                                        & (np.abs(allp[:, 1] - r["y_at_mid"]) <= 12)]))
                         for x in xs])
        e1 += d1
        e2 += [d for d in d2 if np.isfinite(d)]
        if np.isfinite(d3):
            e3.append(d3)
        e4.append(1.0 - near.mean())
    f = lambda a: (float(np.median(a)), float(np.max(a))) if len(a) else (0.0, 0.0)
    m1, x1_ = f(e1); m2, x2_ = f(e2); m3, x3_ = f(e3)
    return {"code": code, "n": len(rd["rows"]),
            "跳1_线段→链": (m1, x1_), "跳2_链→簇": (m2, x2_),
            "跳3_簇→存值": (m3, x3_), "跳4_画的线无墨比例": (float(np.median(e4)),
                                                    float(np.max(e4)))}


def main():
    codes = sys.argv[1:] or ["1019", "1026", "1032", "1035"]
    print(f"{'张':<6}{'层界':>5}  " + "".join(f"{k:>22}" for k in
          ("跳1 线段→链", "跳2 链→簇(并错线)", "跳3 簇→存的y", "跳4 画线处无墨")))
    for c in codes:
        d = diag(c)
        cells = [d["跳1_线段→链"], d["跳2_链→簇"], d["跳3_簇→存值"], d["跳4_画的线无墨比例"]]
        print(f"{c:<6}{d['n']:>5}  " + "".join(
            f"{m:>10.0f}/{x:<11.0f}" for m, x in cells))
    print("  (每格 = 中位/最大；跳1~3 单位 px，跳4 单位 比例)")


if __name__ == "__main__":
    main()
