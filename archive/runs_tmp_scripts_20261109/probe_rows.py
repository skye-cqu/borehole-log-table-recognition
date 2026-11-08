# -*- coding: utf-8 -*-
"""探针:1032/1042 行链分桶实测,定位"物理行数少于真值"的丢失环节。

复用 track_rows.determine_rows 的建链路径(build_tracks+merge_tracks),
但把每条链的 数值区覆盖 ov_num / 表宽占比 / 与最近已判层界的 y 距离 都打出来,
看漏掉的界是落在 sub 桶、other 桶,还是被 40px 去重吃掉。
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

CODES = sys.argv[1:] or ["1032", "1042"]
for code in CODES:
    stem = f"钻孔柱状图{code}"
    hm = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json")
                    .read_text(encoding="utf-8"))
    desc = next(c for c in hm["columns"] if c["name"] == "岩性描述")
    num_right_x = desc["x_in_band"][0]
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    segs_src = [s for s in cj["lines"] if s["direction"] == "horizontal" and s["label"] == "high"]
    img_w = cj["width"]
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

    longs = [g for g in groups if g["y1"] - g["y0"] >= 0.5 * img_w]
    tab_l, tab_r = min(g["y0"] for g in longs), max(g["y1"] for g in longs)
    tab_w, num_w = tab_r - tab_l, num_right_x - tab_l
    rows_all = sorted(({"y": track_rows.x_at_mid(g), "g": g} for g in groups),
                      key=lambda r: r["y"])
    # 现行判据先跑一遍,标出被判为层界的
    cur = []
    for r in rows_all:
        g = r["g"]
        span = g["y1"] - g["y0"]
        ov_num = min(g["y1"], num_right_x) - max(g["y0"], tab_l)
        r["span_f"] = span / tab_w
        r["ovnum_f"] = max(ov_num, 0) / num_w
        r["is_row"] = r["span_f"] >= 0.75 or r["ovnum_f"] >= 0.6
        if r["is_row"] and (not cur or r["y"] - cur[-1]["y"] >= 40):
            cur.append(r)
    n_row, n_sub = len(cur), sum(1 for r in rows_all if r["span_f"] >= 0.28 and not r["is_row"])
    print(f"\n== {code}: 链 {len(groups)} 表宽 {tab_w:.0f} 数值区宽 {num_w:.0f}")
    print(f"   现行层界 {len(cur)}  (含 40px 去重前 {sum(1 for r in rows_all if r['is_row'])})"
          f"  子行线 {n_sub}  其余 {sum(1 for r in rows_all if not r['is_row'] and r['span_f'] < 0.28)}")
    # 相邻层界之间是否藏着"次级线"——它们就是被漏掉的物理界
    hidden = 0
    for a, b in zip(cur, cur[1:]):
        mid = [r for r in rows_all if a["y"] + 40 < r["y"] < b["y"] - 40
               and (r["ovnum_f"] >= 0.45 or r["span_f"] >= 0.5)]
        hidden += len(mid)
    print(f"   层界间隙内≥0.45数值区覆盖的次级线: {hidden} 条 → 层界+次级 = {len(cur)+hidden}")
    # 层界间隙高度分布,找"过薄行"=漏界信号
    gaps = np.diff([r["y"] for r in cur])
    print(f"   层界间距 px: 中位 {np.median(gaps):.0f} p10 {np.percentile(gaps,10):.0f} "
          f"最小 {gaps.min():.0f} 最大 {gaps.max():.0f}")
