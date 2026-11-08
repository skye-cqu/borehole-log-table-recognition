# -*- coding: utf-8 -*-
"""阶段5：Track → 真列线（分隔线）合并与列数判定。

输入 track_group 的归组结果（冻结不变），只新增两类派生关系：
  1. 同一物理线的 Track 合并（跨小断口 / 平行双描）；
  2. 分隔线 / 外框 / 内容线（柱状图案边、曲线、文字笔画）分类。

合并护栏（防串线，先量化验证后定）：
  - 上下相邻（y 缝 ≤60px）：接缝横向对齐 ≤20px 且两侧直线度 res90 ≤15px；
    —— 曲线（如水位线 res90≈23）被此条挡住，不与相邻直尺线并;
  - y 重叠 >100px（同线双描）：重叠区平均横向差 ≤10px。
不对任何原始线段或 Track 做删改；分类只是加标签。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

GAP_MAX_MERGE = 60.0      # 上下缝上限
JUNC_TOL = 20.0           # 接缝横向对齐容差
RES90_MAX = 15.0          # 可合并链的直线度上限（挡曲线）
OVL_MIN = 100.0           # 重叠合并的最小重叠高度
OVL_TOL = 10.0            # 重叠区平均横向差容差
SPAN_FRAC = 0.55          # 分隔线跨度比例（表头墨迹支撑是主闸门；0.8 会杀掉断口多的真线）
LEG_MAX = 150.0           # 横向腿上限：绕框/顺横线的噪声链（聚簇即滤噪）
COV_MIN = 0.40            # 墨迹覆盖率下限（数字笔画/折痕链）
BAND_TOP_PAD = 10         # 表头支撑带：顶框线下方
BAND_H = 70.0             # 表头支撑带高度
FRAME_PAR_TOL = 150.0     # 双线框：伴线横向距离
FRAME_PAR_SPAN = 0.60     # 伴线跨度比例


def header_band(cands, hline_y):
    """自适应表头支撑带 [top_frame+10, top_frame+80]。
    c_top = 跨度前 8 名候选链 y0 的中位数（孤立标题笔画/装订线不会带偏中位数）；
    top_frame = 距 c_top 最近的横线。薄带即可：真分隔线从顶框就有墨。"""
    top8 = sorted(cands, key=lambda g: -g["span"])[:8]
    c_top = float(np.median([g["y0"] for g in top8]))
    near = [y for y in hline_y if abs(y - c_top) <= 120]
    frame_y = float(min(near, key=lambda y: abs(y - c_top))) if near else c_top
    return frame_y + BAND_TOP_PAD, frame_y + BAND_TOP_PAD + BAND_H, c_top


def header_support(pts, gray, y0, y1, k_glob, dist_max=500.0):
    """链条在表头带是否有墨支撑。
    外推 = 顶点 x + 全局剪切斜率 k_glob ×（带中点 − 顶点 y）：短距离外推下
    误差≈斜率误差×距离，远小于弯线顶端腿拟合的漂移。顶端距带 >dist_max 直接无支撑。"""
    ymid = (y0 + y1) / 2
    if pts[0, 0] - ymid > dist_max:
        return False, float(pts[0, 1])
    x = float(pts[0, 1] + k_glob * (ymid - pts[0, 0]))
    return _ink_at(gray, x, y0, y1), x


def load_chain(track, seg):
    """Track → 按 y 排序的 (y, x) 折线 + 墨迹总长。"""
    pts = []
    ink = 0.0
    for i in track["segment_ids"]:
        p = np.asarray(seg[i]["points"], float)
        ink += float(seg[i]["length"])
        for pt in p:
            pts.append((pt[1], pt[0]))
    pts = np.array(sorted(pts))
    return pts, ink


def res90(pts):
    if len(pts) < 3:
        return 0.0
    k, b = np.polyfit(pts[:, 0], pts[:, 1], 1)
    return float(np.percentile(np.abs(np.polyval((k, b), pts[:, 0]) - pts[:, 1]), 90))


def x_at(pts, y):
    """y 处的 x（线性插值；y 恰为端点时返回端点 x）。"""
    n = len(pts)
    i = int(np.searchsorted(pts[:, 0], y))
    if n == 1:
        return float(pts[0, 1])
    i0, i1 = min(max(i - 1, 0), n - 2), min(max(i, 1), n - 1)
    y0, x0 = pts[i0]
    y1, x1 = pts[i1]
    if y1 == y0:
        return float(x0)
    return float(x0 + (x1 - x0) * (y - y0) / (y1 - y0))


def merge_tracks(tracks, seg):
    """同线 Track 合并。返回 groups: List[dict(ids, pts, ink)]（保序）。"""
    items = []
    for t in tracks:
        pts, ink = load_chain(t, seg)
        items.append({"id": t["track_id"], "ids": list(t["segment_ids"]),
                      "pts": pts, "ink": ink, "res": res90(pts),
                      "y0": float(pts[0, 0]), "y1": float(pts[-1, 0])})
    items.sort(key=lambda a: (a["y0"], a["y1"]))
    used = [False] * len(items)
    groups = []

    def put(g, it):
        g["ids"].extend(it["ids"])
        g["ink"] += it["ink"]
        g["pts"] = np.vstack([g["pts"], it["pts"]])
        g["pts"] = g["pts"][np.lexsort((g["pts"][:, 1], g["pts"][:, 0]))]
        g["y0"], g["y1"] = float(g["pts"][0, 0]), float(g["pts"][-1, 0])
        g["res"] = res90(g["pts"])

    for i, it in enumerate(items):
        if used[i]:
            continue
        g = {"ids": list(it["ids"]), "pts": it["pts"], "ink": it["ink"],
             "y0": it["y0"], "y1": it["y1"], "res": it["res"]}
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, o in enumerate(items):
                if used[j]:
                    continue
                join = None
                if 0 <= o["y0"] - g["y1"] <= GAP_MAX_MERGE:      # 上→下相邻
                    xa = x_at(g["pts"], g["y1"])
                    xb = x_at(o["pts"], o["y0"])
                    if xa is not None and xb is not None and abs(xb - xa) <= JUNC_TOL \
                            and max(g["res"], o["res"]) <= RES90_MAX:
                        join = "gap"
                elif o["y0"] <= g["y1"] and o["y1"] >= g["y0"]:   # y 重叠（同线双描）
                    ys = np.linspace(max(o["y0"], g["y0"]) + 5,
                                     min(o["y1"], g["y1"]) - 5, 25)
                    ds = [abs(x_at(o["pts"], y) - x_at(g["pts"], y))
                          for y in ys if x_at(o["pts"], y) and x_at(g["pts"], y)]
                    if len(ds) >= 5 and float(np.mean(ds)) <= OVL_TOL:
                        join = "overlap"
                if join:
                    put(g, o)
                    used[j] = True
                    changed = True
        groups.append(g)
    return groups


def classify(groups, img_h, gray, hline_y):
    """分隔线 / 外框 / 内容线。
    表格范围 = 长链(≥0.5·img_h)的 [min y0, max y1]（图像含装订边/页边，不能用 img_h）。
    分隔线 = 跨表 ≥SPAN_FRAC·表范围 且 表头支撑带有墨；
    表头支撑：链自身伸进表头带用实际轨迹 x，顶端在带下方才外推；
    外框 = 最左侧线(x@mid < 6%·图宽) 或 右侧 150px 内有平行伴线（双线框）。"""
    for g in groups:
        g["span"] = g["y1"] - g["y0"]
        g["ink_cov"] = g["ink"] / max(g["span"], 1e-9)
        # 聚簇即滤噪：真列线首尾位移≈横向范围；横向腿大 = 绕框/顺横线的噪声链
        xs_ = g["pts"][:, 1]
        g["leg"] = float(xs_.max() - xs_.min() - abs(xs_[-1] - xs_[0]))
    longs = [g for g in groups if g["span"] >= 0.5 * img_h]
    if not longs:
        return [], [], list(groups)
    table_top = min(g["y0"] for g in longs)
    # 表格底界用横线最大 y（底框线）：弯链可能伸到页脚，会把表范围撑大；
    # 再从后往前剔除间距异常的尾部杂线（页缘线/页脚线，距前行线远超行距中位数）
    hl = sorted(y for y in hline_y if y >= table_top)
    if hl:
        gaps = np.diff(hl)
        med = float(np.median(gaps)) if len(gaps) else 0.0
        bot = hl[-1]
        for i in range(len(hl) - 1, 0, -1):
            if hl[i] - hl[i - 1] > max(3 * med, 800):
                bot = hl[i - 1]
            else:
                break
        table_bot = bot
    else:
        table_bot = max(g["y1"] for g in longs)
    table_h = max(table_bot - table_top, 1.0)
    cands = [g for g in groups if g["span"] >= SPAN_FRAC * table_h
             and g["leg"] <= LEG_MAX and g["ink_cov"] >= COV_MIN]
    if not cands:
        return [], [], list(groups)
    y0, y1, c_top = header_band(cands, hline_y)
    W = gray.shape[1]
    # 全局剪切斜率：长链弦斜率中位数（弓弯在整线上平均掉）
    k_glob = float(np.median([
        (g["pts"][-1, 1] - g["pts"][0, 1]) / max(g["pts"][-1, 0] - g["pts"][0, 0], 1e-9)
        for g in longs]))
    for g in cands:
        if g["y0"] <= y1:                          # 链顶伸进表头带：用实际轨迹
            x = x_at(g["pts"], (y0 + y1) / 2)
            sup = _ink_at(gray, x, max(y0, g["y0"]), y1)
        else:                                      # 顶端在带下方：顶点+全局斜率外推
            sup, x = header_support(g["pts"], gray, y0, y1, k_glob)
        g["header_sup"], g["x_header"] = sup, x
    cands = [g for g in cands if g["header_sup"]]
    cands.sort(key=lambda g: float(np.median(g["pts"][:, 1])))
    frames = []
    if cands:
        if float(np.median(cands[0]["pts"][:, 1])) < 0.06 * W:
            frames.append(cands[0])                # 最左贴边 → 左框
        right = cands[-1]
        for g in groups:
            if g is right or g["span"] < FRAME_PAR_SPAN * right["span"]:
                continue
            ys = np.linspace(max(g["y0"], right["y0"]) + 5,
                             min(g["y1"], right["y1"]) - 5, 25)
            ds = [abs(x_at(g["pts"], y) - x_at(right["pts"], y))
                  for y in ys if x_at(g["pts"], y) and x_at(right["pts"], y)]
            if len(ds) >= 5 and float(np.mean(ds)) <= FRAME_PAR_TOL:
                if right not in frames:
                    frames.append(right)
                break
    seps = [g for g in cands if g not in frames]
    others = [g for g in groups if g not in cands]
    return seps, frames, others


def _ink_at(gray, x, y0, y1):
    """表头支撑带内 |x|±10 列的逐行最暗值中位数 < 180 → 有墨。"""
    h, w = gray.shape
    if not np.isfinite(x) or x < -50 or x > w + 50:
        return False
    xs = slice(max(0, int(x) - 10), min(w, int(x) + 11))
    band = gray[int(y0):max(int(y0) + 1, int(y1)), xs].astype(int)
    if band.size == 0:
        return False
    return bool(np.median(band.min(axis=1)) < 180)


def draw(viz, seps, frames, others):
    """分隔线加粗+编号；外框灰；其余内容线压暗。"""
    dim = (viz.astype(float) * 0.45).astype(np.uint8)
    mask = np.zeros(viz.shape[:2], bool)
    for g in others:
        arr = g["pts"].astype(int).reshape(-1, 1, 2)
        cv2.polylines(mask, [arr], False, True, 3)
    viz[mask] = dim[mask]
    for g in frames:
        arr = g["pts"].astype(int).reshape(-1, 1, 2)
        cv2.polylines(viz, [arr], False, (128, 128, 128), 3, cv2.LINE_AA)
    for n, g in enumerate(seps, 1):
        arr = g["pts"].astype(int).reshape(-1, 1, 2)
        cv2.polylines(viz, [arr], False, (0, 0, 255), 5, cv2.LINE_AA)
        for y in (g["y0"] + 260, (g["y0"] + g["y1"]) / 2, g["y1"] - 260):
            x = x_at(g["pts"], y)
            if x is None:
                continue
            cv2.circle(viz, (int(x), int(y)), 16, (0, 0, 255), 3, cv2.LINE_AA)
            cv2.putText(viz, str(n), (int(x) - 11, int(y) + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3, cv2.LINE_AA)
    return viz


def main():
    ap = argparse.ArgumentParser(description="Track→列线合并与列数判定")
    ap.add_argument("stem", help="图名，如 钻孔柱状图1019")
    ap.add_argument("--source", choices=["cluster", "track_group"], default="cluster",
                    help="聚簇来源：cluster=集合式零拟合聚簇（新路径），track_group=墨迹追踪")
    args = ap.parse_args()
    stem = args.stem

    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    img_h = int(cj["height"])

    if args.source == "cluster":
        from src.table import cluster_lines as clp
        frags = clp.load_frags(stem)
        p = clp.calibrate(stem, frags)
        cols, _noise, _ = clp.cluster(stem, ang_tol=p["ANG_TOL"], gap_max=p["GAP_MAX"],
                                      align_tol=p["ALIGN_TOL"])
        cols = clp.merge_sets(cols, p["ANG_TOL"], p["GAP_MAX"], p["ALIGN_TOL"])
        groups = clp.to_groups(cols, frags)
    else:
        tj = json.load(open(paths.TRACK_GROUP_COORD_DIR / f"{stem}.json", encoding="utf-8"))
        groups = merge_tracks(tj["tracks"], seg)
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    hline_y = [s["midy"] for s in cj["lines"]
               if s["direction"] == "horizontal" and s["label"] == "high"]
    seps, frames, others = classify(groups, img_h, gray, hline_y)

    paths.ensure_dirs(paths.TRACK_GROUP_DIR)
    report = {
        "image": stem,
        "n_tracks_in": len(groups),
        "n_lines_after_merge": len(groups),
        "n_separators": len(seps),
        "n_frames": len(frames),
        "columns": len(seps) + 1,
        "separators": [{"no": n, "segment_ids": g["ids"],
                        "y": [round(g["y0"]), round(g["y1"])],
                        "span": round(g["span"]), "res90": round(g["res"], 1),
                        "ink_cov": round(g["ink_cov"], 2),
                        "x_at_mid": round(x_at(g["pts"], (g["y0"] + g["y1"]) / 2), 1)}
                       for n, g in enumerate(seps, 1)],
        "frames": [{"segment_ids": g["ids"], "y": [round(g["y0"]), round(g["y1"])],
                    "x_at_mid": round(x_at(g["pts"], (g["y0"] + g["y1"]) / 2), 1)}
                   for g in frames],
        "others": [{"track_ids": g["ids"], "y": [round(g["y0"]), round(g["y1"])],
                    "span": round(g["span"]), "res90": round(g["res"], 1),
                    "ink_cov": round(g["ink_cov"], 2)}
                   for g in sorted(others, key=lambda g: -g["span"])[:15]],
    }
    with open(paths.TRACK_GROUP_DIR / f"{stem}_列判定.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    viz = cv2.imread(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}.png"))
    viz = draw(viz, seps, frames, others)
    cv2.imwrite(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}_列判定.png"), viz,
                [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2),
                      interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}_列判定_预览_半分辨率.jpg"),
                half, [cv2.IMWRITE_JPEG_QUALITY, 88])

    print(f"{stem}: tracks {report['n_tracks_in']} → 合并后线 {report['n_lines_after_merge']}，"
          f"真分隔线 {report['n_separators']} 根 → 列数(格) {report['columns']}")
    for s in report["separators"]:
        ids = s["segment_ids"]
        print("  S%-2d x@mid=%7.1f y %6d~%6d res90=%4.1f cov=%.2f segs=%s" %
              (s["no"], s["x_at_mid"], s["y"][0], s["y"][1], s["res90"], s["ink_cov"],
               ids if len(ids) <= 6 else ids[:6] + ["..."]))


if __name__ == "__main__":
    main()
