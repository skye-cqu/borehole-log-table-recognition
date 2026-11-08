# -*- coding: utf-8 -*-
"""探针2:先按 y 把链聚成"同一横线"(并集覆盖),再判层界——测这套判据的召回。

动机:现行 determine_rows 按"单条链"算覆盖率,一条真行界在数值区被柱状图/污损
断成两三条链时每段覆盖都不到阈值 → 整条界被降级为子行线 → 物理行被捆叠。
本探针把链先聚成线(并集),扫阈值看 1032/1042(已知真值 103/112 行)落在哪。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                    # noqa: E402
from src.table import track_group, track_rows                  # noqa: E402
from src.table.track_columns import merge_tracks               # noqa: E402


def chains(stem):
    hm = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json")
                    .read_text(encoding="utf-8"))
    desc = next((c for c in hm.get("columns", []) if "岩性" in str(c.get("name", ""))), None)
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    segs_src = [s for s in cj["lines"] if s["direction"] == "horizontal" and s["label"] == "high"]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    ink = track_group.binarize(gray, track_group.PARAMS).T
    segs = []
    for s in segs_src:
        pts = np.asarray(s["points"], float)
        i_t, i_b = int(pts[:, 1].argmin()), int(pts[:, 1].argmax())
        adj_t = pts[1] if i_t == 0 else pts[i_t - 1]
        adj_b = pts[-2] if i_b == len(pts) - 1 else pts[i_b + 1]
        segs.append({"id": s["id"], "top": pts[i_t][::-1].copy(), "bot": pts[i_b][::-1].copy(),
                     "v_top": track_rows._dir_down(pts[i_t][::-1], adj_t[::-1]),
                     "v_bot": track_rows._dir_down(pts[i_b][::-1], adj_b[::-1]),
                     "points": track_rows._swap_points(s["points"]), "length": float(s["length"])})
    tracks, _ = track_group.build_tracks(segs, ink, track_group.PARAMS)
    groups = merge_tracks(tracks, {s["id"]: s for s in segs})
    longs = [g for g in groups if g["y1"] - g["y0"] >= 0.5 * cj["width"]]
    tab_l, tab_r = min(g["y0"] for g in longs), max(g["y1"] for g in longs)
    num_x = desc["x_in_band"][0] if desc and desc.get("x_in_band") else tab_r
    return groups, tab_l, tab_r, min(max(num_x, tab_l + 1), tab_r - 1)


def merge_by_y(groups, tab_l, tab_r, num_x, tol):
    """把 y 相距 tol 内的链并成一条"线",覆盖区间取并集;分别量数值区/描述区覆盖率。"""
    items = []
    for g in groups:
        items.append((track_rows.x_at_mid(g), min(max(g["y0"], tab_l), num_x),
                      min(max(g["y1"], tab_l), num_x),
                      min(max(g["y0"], num_x), tab_r), min(max(g["y1"], num_x), tab_r)))
    items.sort()
    lines = []
    for y, nl, nr, dl, dr in items:
        if lines and y - lines[-1]["y_ref"] <= tol:
            L = lines[-1]
            L["num"].append((nl, nr))
            L["desc"].append((dl, dr))
            L["y_ref"] = y
        else:
            lines.append({"y": y, "y_ref": y, "num": [(nl, nr)], "desc": [(dl, dr)]})
    nw, dw = max(num_x - tab_l, 1), max(tab_r - num_x, 1)
    return [{"y": L["y"], "cov_num": _union(L["num"]) / nw, "cov_desc": _union(L["desc"]) / dw}
            for L in lines]


def _union(iv):
    iv = sorted((max(a, 0), b) for a, b in iv if b > a)
    tot, ca, cb = 0.0, None, None
    for a, b in iv:
        if ca is None:
            ca, cb = a, b
        elif a <= cb:
            cb = max(cb, b)
        else:
            tot += cb - ca
            ca, cb = a, b
    return tot + (cb - ca if ca is not None else 0)


TRUTH = {"1032": 103, "1042": 112}
if __name__ == "__main__":
  for code in sys.argv[1:] or list(TRUTH):
    stem = f"钻孔柱状图{code}"
    groups, tab_l, tab_r, num_x = chains(stem)
    print(f"\n== {code} 真值 {TRUTH.get(code)} 行,链 {len(groups)}")
    for tol in (25, 40):
        L = merge_by_y(groups, tab_l, tab_r, num_x, tol)
        for th in (0.6, 0.5, 0.45, 0.4, 0.35, 0.3):
            cand = [x for x in L if x["cov_num"] >= th]
            print(f"   tol={tol} cov_num≥{th:<4} → 线 {len(L)} 层界候选 {len(cand)}")
