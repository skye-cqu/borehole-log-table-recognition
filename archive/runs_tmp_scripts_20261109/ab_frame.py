# -*- coding: utf-8 -*-
"""A/B：把行线的左右界从"最长链自己撑出来的范围"换成"6a4 闭合外框"，看尺子怎么说。

现状问题（实测 30 张）：链自己定的表宽比真外框左多 61px、右多 100px（最坏 327/285px），
框外的深度刻度、边注被拼进了行线 → 75 条行线端点出框。
这一档：每条阶段4 横段先裁到外框以内（只留框内连续的一段），再建链、再判界；
表的左右界直接取外框。产物落 runs/tmp/ab/框内/，生产目录不动。

用法: python runs/tmp/ab_frame.py [1020 1034 ...]     # 无参数=30 张
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.core.batch import run_batch                                # noqa: E402
from src.table import track_group, track_rows as tr                 # noqa: E402
from src.table.track_rows import in_band                   # noqa: E402

OUT = ROOT / "runs" / "tmp" / "ab" / "框内"
PAD = 8.0            # 离外框多少像素以内算框外


def frame(stem):
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_闭合外框.json"
    if not fp.exists():
        return None
    d = json.load(open(fp, encoding="utf-8"))
    if "left" not in d or "right" not in d:
        return None
    L = np.array([[p[1], p[0]] for p in d["left"]["pts"]], float)
    R = np.array([[p[1], p[0]] for p in d["right"]["pts"]], float)
    w = int(json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json",
                           encoding="utf-8"))["width"])
    lo, hi = float(np.median(L[:, 1])), float(np.median(R[:, 1]))
    if not (0.02 * w < lo < hi < 0.98 * w) or hi - lo < 0.5 * w:
        return None                                   # 外框本身不可信：这一档不动这张图
    return L, R


def clip(p, L, R):
    """点列裁到外框内：只留框内最长的一段连续点（框外部分不是表格的行线）。"""
    ok = (p[:, 0] > np.interp(p[:, 1], L[:, 0], L[:, 1]) + PAD) & \
         (p[:, 0] < np.interp(p[:, 1], R[:, 0], R[:, 1]) - PAD)
    best = cur = None
    for i, v in enumerate(ok):
        if v:
            cur = [i, i] if cur is None else [cur[0], i]
        elif cur:
            best = cur if best is None or cur[1] - cur[0] > best[1] - best[0] else best
            cur = None
    if cur:
        best = cur if best is None or cur[1] - cur[0] > best[1] - best[0] else best
    # 数值区里全是 2 点短段（一段 50~90px），只留 ≥3 点会把整个数值区丢掉
    return None if best is None or best[1] - best[0] < 1 else p[best[0]:best[1] + 1]


def build(stem, segs_src, cj, L, R):
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    ink = track_group.binarize(gray, track_group.PARAMS).T
    del gray                                    # 56MB 一张：内存上限 4GB，用完整张就放手
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
    del ink
    groups = tr.merge_tracks(tracks, {s["id"]: s for s in segs})
    img_w = int(cj["width"])
    longs = [g for g in groups if g["y1"] - g["y0"] >= 0.5 * img_w]
    if not longs:
        return None
    tab_l = float(L[:, 1].max()) + PAD     # 取内缩最多的那一处，保证窗口整条都在框里
    tab_r = float(R[:, 1].min()) - PAD
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
    west, east, _ = tr.content_band(stem)
    return {"stem": stem, "items": items, "s0": s0, "tab_l": tab_l, "tab_r": tab_r,
            "tab_w": max(tab_r - tab_l, 1.0),
            "col": west if west is not None else tr.column_anchor(stem),
            "n_segs": len(segs_src), "n_chains": len(groups), "warns": []}


def write(stem, o):
    (OUT / f"{stem}_行判定.json").write_text(json.dumps(o, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    return (stem[-4:], len(o["rows"]) > 0,
            f"层界 {len(o['rows'])} 子行 {len(o['sub_rows'])} 行高 {o['row_h']:.0f} "
            f"表宽 {o['table_x']}")


def one(stem):
    """一张：段裁到框内 → 建链 → 判界 → 写 runs/tmp/ab/框内/。

    外框本身不可信的张（6a4 左右边中位落在图外）退回生产档那套链定宽，并记 frame_fallback，
    对比时把这几张单列出来，免得拿"没改的"混进"改了没用"。
    """
    fr = frame(stem)
    if fr is None:
        ch = tr.load_chains(stem)
        if ch is None:
            return stem[-4:], False, "外框不可信且无长横链"
        o = tr.assemble(ch)
        o["frame_fallback"] = True
        return write(stem, o)
    L, R = fr
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    src = [s for s in cj["lines"]
           if s["direction"] == "horizontal" and s["label"] == "high"]
    west, east, _ = tr.content_band(stem)
    band = (west, east) if west is not None else None
    kept, n_drop = [], 0
    for s in src:
        p = np.asarray(s["points"], float)
        q = None if (band is not None and in_band(p, band)) else clip(p, L, R)
        if q is None:
            n_drop += 1
            continue
        s = dict(s)
        s["points"] = q.tolist()
        s["length"] = float(q[-1, 0] - q[0, 0])
        kept.append(s)
    ch = build(stem, kept, cj, L, R)
    if ch is None:
        return stem[-4:], False, "无长横链"
    o = tr.assemble(ch)
    o["n_band_segments"] = o.get("n_band_segments", 0) + n_drop
    o["n_clip"] = n_drop
    return write(stem, o)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    stems = [f"钻孔柱状图{a}" if a.isdigit() else a for a in sys.argv[1:]] or \
            sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    # 一进程约 0.5GB（3000×17000 的墨迹掩膜），3 并发 + Qoder 本体压在 4GB 以内
    run_batch(stems, one, max_workers=3)
