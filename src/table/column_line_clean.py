# -*- coding: utf-8 -*-
"""阶段5a：表格列线清洗与结构识别：候选竖线 -> 拼接 -> 大框架识别 -> 贯穿判定 -> 结构输出

核心准则（用户明确要求）：
  真列线 = 拼接后的列线，其顶部端点触及表格最上方框线、底部端点触及表格最下方框线。
  不接受"长度比例达80%"判定——很多内部线长度达80%但仍属列内部线条。
  因此先识别大框架（定上下边界）-> 再判定拼接列是否触及上下边界。

输入（只读）：
  - data/表格线候选识别处理/坐标数据/*.json（候选线，阶段4 产物）
  - data/raw_images/*.JPG（彩色扫描件，用作原图副本与叠加背景）
输出（data/列线清洗与结构识别/）：
  - 原图/             原始扫描件 PNG 无损副本，绝不绘制
  - 叠加可视化图/     原图副本上绘制结构识别结果（主要人工核验图）
  - 纯结构图/         白底仅绘制结构线
  - 坐标数据/         每图一个 JSON（大框架/主体/小表格/真列线/内部线）

原图与可视化图宽高完全相同、坐标系一致，可逐像素对照。
输入目录全程只读，绝不原地保存或覆盖。

用法：
    python src/table/column_line_clean.py
"""
import json
import sys
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import DBSCAN

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch

# ---- 输出目录 ----
OUTPUT_DIRS = (
    paths.COLUMN_CLEAN_ORIG_DIR,
    paths.COLUMN_CLEAN_OVERLAY_DIR,
    paths.COLUMN_CLEAN_PURE_DIR,
    paths.COLUMN_CLEAN_COORD_DIR,
)

# ---- 算法参数 ----
# 阶段1：竖线拼接
STITCH_MIDX_EPS = 15.0   # 竖线 midx 聚类半径（px），同列线段 x 应接近
STITCH_GAP = 60.0        # 端点拼接间隙阈值（px），相邻段 gap<=此值则合并

# 阶段2：大框架识别
FRAME_Y_EPS = 15.0       # 横线 midy 聚类半径（px），找顶/底框边
FRAME_X_UNION = 30.0     # x 区间 union 合并阈值（px），相邻或重叠则合并
FRAME_MIN_COVERAGE = 0.5 # 候选框边的 x 覆盖率下限（占图片宽度）

# 阶段4：右下角小表格
SUBTABLE_MIN_DENSITY = 5  # 小表格区域最小线密度（线/万px²）
SUBTABLE_MAX_H_RATIO = 0.03  # 小表格高度上限（占图高比例，~240px/8000px）

# 阶段5：真列线判定（核心）
# 触及容差：表格高度越高，骨架追踪在框线附近断裂的间隙越大，
# 故容差取表格高度的固定比例而非绝对像素，更贴合"语义贯穿"的判定。
TOUCH_TOL_RATIO = 0.06    # 列线触及框线的容差（占 frame.height 比例，6%≈1080px/18000px）
# 注：骨架追踪在框线附近常断裂数百px，容差需覆盖此断裂。仍判定"贯穿"
# 语义（非长度比例判定）：列线必须从顶框延伸到底框附近，而非仅在中间某段很长。
TOUCH_TOL_MIN = 50.0      # 容差下限（px），保证小表格也能用


# ============================================================
# 阶段1：竖线拼接（stitching）
# ============================================================
def union_intervals(intervals, gap):
    """合并重叠或相邻(<=gap)的区间。intervals: list of (start,end)。"""
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def stitch_vertical_lines(vlines):
    """对竖线候选做同 x 位置的端点拼接。

    vlines: list of dict，每条含 midx, bbox[x0,y0,x1,y1], length, id, points
    返回拼接后的列线列表，每条含 x, y_top, y_bot, total_length, segment_ids
    """
    if not vlines:
        return []
    # 1. 按 midx 用 DBSCAN 聚类成 x 簇
    X = np.array([[v["midx"]] for v in vlines], dtype=np.float64)
    labels = DBSCAN(eps=STITCH_MIDX_EPS, min_samples=1).fit_predict(X)

    stitched = []
    for lab in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == lab]
        grp = [vlines[i] for i in idx]
        # 2. 簇内按 y0 排序，相邻段 gap<=STITCH_GAP 则合并
        grp.sort(key=lambda v: v["bbox"][1])
        cur_segs = [grp[0]]
        for v in grp[1:]:
            prev_bot = cur_segs[-1]["bbox"][3]
            cur_top = v["bbox"][1]
            if cur_top - prev_bot <= STITCH_GAP:
                cur_segs.append(v)
            else:
                stitched.append(_merge_segments(cur_segs))
                cur_segs = [v]
        stitched.append(_merge_segments(cur_segs))
    return stitched


def _merge_segments(segs):
    """合并一组同 x 的竖线段为一条逻辑列线。"""
    y_top = min(s["bbox"][1] for s in segs)
    y_bot = max(s["bbox"][3] for s in segs)
    # x 位置取所有段的 midx 中位数（更稳健）
    x = float(np.median([s["midx"] for s in segs]))
    total_len = sum(s["length"] for s in segs)
    seg_ids = [s["id"] for s in segs]
    return {
        "x": x,
        "y_top": float(y_top),
        "y_bot": float(y_bot),
        "y_span": float(y_bot - y_top),
        "total_length": float(total_len),
        "num_segments": len(segs),
        "segment_ids": seg_ids,
    }


# ============================================================
# 阶段2：大框架识别
# ============================================================
def detect_frame(hlines, stitched_vlines, W, H):
    """识别表格大框架四至 [left, top, right, bottom]。

    顶/底框：横线按 midy 聚类，每簇做 x 区间 union，取 x 覆盖率最高且最靠上/下的簇。
    左/右框：拼接竖线中 y 跨度最大者，取 midx 最小/大。
    """
    if not hlines:
        return None
    # 1. 横线按 midy 聚类
    Y = np.array([[h["midy"]] for h in hlines], dtype=np.float64)
    labels = DBSCAN(eps=FRAME_Y_EPS, min_samples=1).fit_predict(Y)

    # 2. 每簇做 x union，算覆盖率
    bands = []
    for lab in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == lab]
        grp = [hlines[i] for i in idx]
        midy = float(np.median([h["midy"] for h in grp]))
        intervals = [(h["bbox"][0], h["bbox"][2]) for h in grp]
        merged = union_intervals(intervals, FRAME_X_UNION)
        total_cov = sum(e - s for s, e in merged)
        coverage = total_cov / W
        # 最宽单段宽度（用于判断是否全宽边框）
        max_span = max((e - s) for s, e in merged) if merged else 0
        bands.append({
            "midy": midy,
            "coverage": coverage,
            "max_span": float(max_span),
            "num_lines": len(grp),
            "merged_intervals": merged,
        })

    # 3. 顶/底框：max_span 大（覆盖表格大部分宽度）的簇中取 midy 最小/大者
    #    顶/底框的横线覆盖表格全宽，max_span 应远大于主体行线 span（≈1320）。
    #    用 max_span 而非 coverage，避免底框断裂成多段导致 coverage 偏低被漏选。
    if not bands:
        return None
    span_pool = []
    for ratio in (0.5, 0.4, 0.3):
        span_pool = [b for b in bands if b["max_span"] >= W * ratio]
        if len(span_pool) >= 3:
            break
    if not span_pool:
        span_pool = bands  # 最终退化：全部
    top_y = min(b["midy"] for b in span_pool)
    bot_y = max(b["midy"] for b in span_pool)
    # top_pool 用于后续左右框识别，取 span 最大的前几个簇
    span_pool_sorted = sorted(span_pool, key=lambda b: -b["max_span"])
    top_pool = span_pool_sorted[:min(3, len(span_pool_sorted))]
    # 诊断用
    pool_sorted = sorted(bands, key=lambda b: -b["coverage"])

    # 4. 左/右框：综合拼接竖线 y_span 与横线 x 覆盖范围
    #    拼接竖线取 y_span 最大的前 30%（扩大范围避免漏掉短竖框）
    vleft, vright = float("inf"), 0.0
    if stitched_vlines:
        sv = sorted(stitched_vlines, key=lambda v: -v["y_span"])
        top_sv = sv[: max(2, len(sv) * 3 // 10)]
        vleft = min(v["x"] for v in top_sv)
        vright = max(v["x"] for v in top_sv)
    # 横线 x 覆盖：顶/底框簇的 merged intervals 最宽单段的左右端
    #    （用最宽单段而非所有区间并集，避免零散短线把边界拉到0）
    hleft, hright = float("inf"), 0.0
    for b in top_pool:
        if b["merged_intervals"]:
            # 取该簇中最宽的单段
            widest = max(b["merged_intervals"], key=lambda iv: iv[1] - iv[0])
            hleft = min(hleft, widest[0])
            hright = max(hright, widest[1])
    # 左/右边界取竖线与横线的交集范围（二者都有的更可靠）
    if hleft < float("inf") and vleft < float("inf"):
        left_x = max(vleft, hleft - 50)   # 横线可能比竖框稍宽，允许50px容差
        right_x = min(vright, hright + 50) if vright < float("inf") else hright
    elif vleft < float("inf"):
        left_x, right_x = vleft, vright
    else:
        left_x, right_x = hleft, hright

    frame = {
        "left": float(left_x),
        "top": float(top_y),
        "right": float(right_x),
        "bottom": float(bot_y),
    }
    frame["width"] = frame["right"] - frame["left"]
    frame["height"] = frame["bottom"] - frame["top"]
    # 附加诊断信息
    frame["_bands"] = [{"midy": b["midy"], "coverage": round(b["coverage"], 3),
                        "max_span": round(b["max_span"], 1), "num_lines": b["num_lines"]}
                       for b in pool_sorted[:10]]
    return frame


# ============================================================
# 阶段3：表格主体识别
# ============================================================
def detect_main_body(hlines, frame):
    """识别表格主体范围（横线 span 重复最多的区段）。

    主体列区的行线有稳定一致的 span（≈1315px，x0≈1008, x1≈2324），
    重复出现近百次。用 span 众数找到这些行线，取 x0/x1 中位数确定主体边界。
    """
    if not hlines:
        return {"left": frame["left"], "top": frame["top"],
                "right": frame["right"], "bottom": frame["bottom"],
                "width": frame["width"], "height": frame["height"]}
    spans = np.array([h["bbox"][2] - h["bbox"][0] for h in hlines])
    # span 直方图找众数（bin=50px），排除极短噪声线
    valid = spans[spans > 200]
    if len(valid) < 5:
        return {"left": frame["left"], "top": frame["top"],
                "right": frame["right"], "bottom": frame["bottom"],
                "width": frame["width"], "height": frame["height"]}
    hist, edges = np.histogram(valid, bins=np.arange(0, spans.max() + 100, 50))
    peak_bin = int(np.argmax(hist))
    peak_span_lo = edges[peak_bin]
    peak_span_hi = edges[peak_bin + 1]
    # 取 span 落在众数 bin 的横线
    main_h = [h for h in hlines
              if peak_span_lo <= (h["bbox"][2] - h["bbox"][0]) < peak_span_hi + 50]
    if len(main_h) < 3:
        # 退化：取 span 最长的前 20% 的中位数
        main_h = sorted(hlines, key=lambda h: -(h["bbox"][2] - h["bbox"][0]))[:max(3, len(hlines) // 5)]
    x0_med = float(np.median([h["bbox"][0] for h in main_h]))
    x1_med = float(np.median([h["bbox"][2] for h in main_h]))
    return {
        "left": x0_med,
        "right": x1_med,
        "top": frame["top"],
        "bottom": frame["bottom"],
        "width": x1_med - x0_med,
        "height": frame["height"],
        "num_main_hlines": len(main_h),
    }


# ============================================================
# 阶段4：右下角小表格识别
# ============================================================
def detect_subtable(hlines, vlines, frame, main_body):
    """识别右下角小表格（图签/责任表）。

    特征：x>主体右框、y>主体底部附近，宽≈780px、高100-240px，
    含 span≈196 的密集小方格线。
    """
    W = frame["right"]
    H = frame["bottom"]
    # 候选区域：右下角，x>主体右框-100, y>frame.bottom-1500
    sub_x_min = main_body["right"] - 100
    sub_y_min = frame["bottom"] - 1500
    sub_x_max = frame["right"] + 50
    sub_y_max = frame["bottom"] + 50

    # 收集区域内横线，排除主体行线（span>400px 的是主体列区行线，非小表格）
    sub_hlines = [h for h in hlines
                  if h["bbox"][2] > sub_x_min and h["bbox"][0] < sub_x_max
                  and h["midy"] > sub_y_min and h["midy"] < sub_y_max
                  and (h["bbox"][2] - h["bbox"][0]) < 400]
    if len(sub_hlines) < 3:
        return {"exists": False}

    # 按 midy 聚类找小表格的行线
    Y = np.array([[h["midy"]] for h in sub_hlines], dtype=np.float64)
    labels = DBSCAN(eps=15.0, min_samples=1).fit_predict(Y)
    rows = []
    for lab in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == lab]
        grp = [sub_hlines[i] for i in idx]
        midy = float(np.median([h["midy"] for h in grp]))
        x0 = min(h["bbox"][0] for h in grp)
        x1 = max(h["bbox"][2] for h in grp)
        rows.append({"midy": midy, "x0": x0, "x1": x1, "count": len(grp)})
    rows.sort(key=lambda r: r["midy"])
    if len(rows) < 2:
        return {"exists": False}

    # 小表格特征：多条密集横线（行间距小）、x 范围相近（≈780px）
    # 找最密集的连续行组（相邻 midy 差 < 150px）
    best_group = []
    cur = [rows[0]]
    for r in rows[1:]:
        if r["midy"] - cur[-1]["midy"] < 150:
            cur.append(r)
        else:
            if len(cur) > len(best_group):
                best_group = cur
            cur = [r]
    if len(cur) > len(best_group):
        best_group = cur
    if len(best_group) < 3:
        return {"exists": False}

    sub_x0 = min(r["x0"] for r in best_group)
    sub_x1 = max(r["x1"] for r in best_group)
    sub_y0 = min(r["midy"] for r in best_group)
    sub_y1 = max(r["midy"] for r in best_group)
    sub_w = sub_x1 - sub_x0
    sub_h = sub_y1 - sub_y0
    # 验证：宽 300-1300px、高 30-600px、至少3行
    if not (300 < sub_w < 1300 and 30 < sub_h < 600):
        return {"exists": False}

    return {
        "exists": True,
        "left": float(sub_x0), "top": float(sub_y0),
        "right": float(sub_x1), "bottom": float(sub_y1),
        "width": float(sub_w), "height": float(sub_h),
        "num_rows": len(best_group),
    }


# ============================================================
# 阶段5：真列线判定（核心，按用户准则）
# ============================================================
def classify_columns(stitched, frame):
    """判定拼接列线是否为真列线（贯穿：顶触上框 ∧ 底触下框）。

    触及容差取表格高度的固定比例（TOUCH_TOL_RATIO），因为骨架追踪在
    框线附近常断裂数百px，绝对容差无法适配不同尺寸的表格。
    真列线：y_top 在容差内触及 frame.top，且 y_bot 在容差内触及 frame.bottom。
    其余为内部线（即使很长也只属列内部）。
    """
    tol = max(TOUCH_TOL_MIN, frame["height"] * TOUCH_TOL_RATIO)
    real_cols = []
    internal = []
    for sv in stitched:
        d_top = sv["y_top"] - frame["top"]        # 正=列线顶在框下方
        d_bot = frame["bottom"] - sv["y_bot"]     # 正=列线底在框上方
        touches_top = d_top <= tol                # 顶在框上方或容差内
        touches_bot = d_bot <= tol                # 底在框下方或容差内
        sv["d_top"] = float(d_top)
        sv["d_bot"] = float(d_bot)
        sv["touches_top"] = bool(touches_top)
        sv["touches_bottom"] = bool(touches_bot)
        if touches_top and touches_bot:
            sv["label"] = "real_column"
            real_cols.append(sv)
        else:
            sv["label"] = "internal"
            internal.append(sv)
    # 按 x 排序，分配列号
    real_cols.sort(key=lambda c: c["x"])
    for i, c in enumerate(real_cols):
        c["col_id"] = i + 1
    return real_cols, internal


# ============================================================
# 阶段6：列连续性分析
# ============================================================
def analyze_column_continuity(real_cols):
    """分析列连续性：缺失只会缺失两侧，内部列总是连续的。"""
    if not real_cols:
        return {"num_real_columns": 0, "missing_side": "all", "is_continuous": False}
    # 相邻列间距，判断是否有异常大间距（内部缺失）
    gaps = []
    for i in range(1, len(real_cols)):
        gaps.append(real_cols[i]["x"] - real_cols[i - 1]["x"])
    if not gaps:
        return {"num_real_columns": len(real_cols), "missing_side": "none",
                "is_continuous": True, "gaps": []}
    median_gap = float(np.median(gaps))
    # 内部不应有超过 1.5x 中位间距的 gap
    internal_continuous = all(g <= median_gap * 1.8 for g in gaps)
    return {
        "num_real_columns": len(real_cols),
        "is_continuous": bool(internal_continuous),
        "missing_side": "none",  # 两侧缺失由人工复核，此处仅标注内部连续性
        "median_gap": round(median_gap, 1),
        "gaps": [round(g, 1) for g in gaps],
    }


# ============================================================
# 可视化
# ============================================================
def draw_overlay(orig, frame, body, subtable, real_cols, internal_vlines, all_vlines):
    """在原图副本上绘制结构识别结果。"""
    viz = orig.copy()
    # 原始竖线候选：浅灰细线（参考）
    for v in all_vlines:
        pts = v.get("points", [])
        if len(pts) >= 2:
            for i in range(len(pts) - 1):
                cv2.line(viz,
                         (int(pts[i][0]), int(pts[i][1])),
                         (int(pts[i + 1][0]), int(pts[i + 1][1])),
                         (200, 200, 200), 1, cv2.LINE_8)

    # 内部拼接线：黄色细线
    for c in internal_vlines:
        cv2.line(viz, (int(c["x"]), int(c["y_top"])), (int(c["x"]), int(c["y_bot"])),
                 (0, 220, 255), 2, cv2.LINE_8)

    # 真列线：红色粗线
    for c in real_cols:
        cv2.line(viz, (int(c["x"]), int(c["y_top"])), (int(c["x"]), int(c["y_bot"])),
                 (0, 0, 255), 3, cv2.LINE_8)
        # 标注列号
        cv2.putText(viz, str(c["col_id"]),
                    (int(c["x"]) + 5, int(c["y_top"]) + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # 大框架：绿色矩形
    if frame:
        p1 = (int(frame["left"]), int(frame["top"]))
        p2 = (int(frame["right"]), int(frame["bottom"]))
        cv2.rectangle(viz, p1, p2, (0, 200, 0), 3)

    # 表格主体：青色虚线矩形
    if body:
        p1 = (int(body["left"]), int(body["top"]))
        p2 = (int(body["right"]), int(body["bottom"]))
        _draw_dashed_rect(viz, p1, p2, (200, 200, 0), 2, 20)

    # 右下小表格：紫色矩形
    if subtable and subtable.get("exists"):
        p1 = (int(subtable["left"]), int(subtable["top"]))
        p2 = (int(subtable["right"]), int(subtable["bottom"]))
        cv2.rectangle(viz, p1, p2, (200, 0, 200), 3)

    return viz


def draw_pure(W, H, frame, body, subtable, real_cols, internal_vlines):
    """白底仅绘制结构线。"""
    viz = np.full((H, W, 3), 255, dtype=np.uint8)
    # 内部拼接线：黄色
    for c in internal_vlines:
        cv2.line(viz, (int(c["x"]), int(c["y_top"])), (int(c["x"]), int(c["y_bot"])),
                 (0, 220, 255), 2, cv2.LINE_8)
    # 真列线：红色
    for c in real_cols:
        cv2.line(viz, (int(c["x"]), int(c["y_top"])), (int(c["x"]), int(c["y_bot"])),
                 (0, 0, 255), 3, cv2.LINE_8)
        cv2.putText(viz, str(c["col_id"]),
                    (int(c["x"]) + 5, int(c["y_top"]) + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 2)
    # 大框架：绿色
    if frame:
        cv2.rectangle(viz, (int(frame["left"]), int(frame["top"])),
                       (int(frame["right"]), int(frame["bottom"])), (0, 200, 0), 3)
    # 主体：青色虚线
    if body:
        _draw_dashed_rect(viz, (int(body["left"]), int(body["top"])),
                          (int(body["right"]), int(body["bottom"])), (200, 200, 0), 2, 20)
    # 小表格：紫色
    if subtable and subtable.get("exists"):
        cv2.rectangle(viz, (int(subtable["left"]), int(subtable["top"])),
                       (int(subtable["right"]), int(subtable["bottom"])), (200, 0, 200), 3)
    return viz


def _draw_dashed_rect(img, p1, p2, color, thickness, dash_len):
    """绘制虚线矩形。"""
    x1, y1 = p1
    x2, y2 = p2
    for x in range(x1, x2, dash_len * 2):
        cv2.line(img, (x, y1), (min(x + dash_len, x2), y1), color, thickness)
        cv2.line(img, (x, y2), (min(x + dash_len, x2), y2), color, thickness)
    for y in range(y1, y2, dash_len * 2):
        cv2.line(img, (x1, y), (x1, min(y + dash_len, y2)), color, thickness)
        cv2.line(img, (x2, y), (x2, min(y + dash_len, y2)), color, thickness)


# ============================================================
# 单图处理
# ============================================================
def process_image(jpg_path, json_path):
    """处理一张图：候选线 -> 拼接 -> 框架 -> 主体 -> 小表格 -> 贯穿判定 -> 输出。

    返回 (stem, ok, info)。
    """
    stem = jpg_path.stem
    try:
        paths.ensure_dirs(*OUTPUT_DIRS)

        # ---- 读取候选数据（只读）----
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        img_w, img_h = int(data["width"]), int(data["height"])
        all_lines = data["lines"]

        # 筛选竖线/横线候选（high+suspect）
        vlines = [l for l in all_lines
                  if l["direction"] == "vertical" and l["label"] in ("high", "suspect")]
        hlines = [l for l in all_lines
                  if l["direction"] == "horizontal" and l["label"] in ("high", "suspect")]

        # ---- 阶段1：竖线拼接 ----
        stitched = stitch_vertical_lines(vlines)

        # ---- 阶段2：大框架 ----
        frame = detect_frame(hlines, stitched, img_w, img_h)
        if frame is None:
            return stem, False, "无法识别大框架"

        # ---- 阶段3：表格主体 ----
        body = detect_main_body(hlines, frame)

        # ---- 阶段4：右下小表格 ----
        subtable = detect_subtable(hlines, vlines, frame, body)

        # ---- 阶段5：真列线判定 ----
        real_cols, internal = classify_columns(stitched, frame)

        # ---- 阶段6：列连续性 ----
        cont = analyze_column_continuity(real_cols)

        # ---- 读取原图（彩色，只读）----
        orig = cv2.imread(str(jpg_path), cv2.IMREAD_COLOR)
        if orig is None:
            return stem, False, "无法读取原图 JPG"

        # ---- 输出1：原图副本（绝不绘制）----
        cv2.imwrite(str(paths.COLUMN_CLEAN_ORIG_DIR / f"{stem}.png"), orig,
                    [cv2.IMWRITE_PNG_COMPRESSION, 0])

        # ---- 输出2：叠加可视化图 ----
        viz = draw_overlay(orig, frame, body, subtable, real_cols, internal, vlines)
        cv2.imwrite(str(paths.COLUMN_CLEAN_OVERLAY_DIR / f"{stem}.png"), viz,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出3：纯结构图 ----
        pure = draw_pure(img_w, img_h, frame, body, subtable, real_cols, internal)
        cv2.imwrite(str(paths.COLUMN_CLEAN_PURE_DIR / f"{stem}.png"), pure,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出4：坐标数据 JSON ----
        # 清理 frame 诊断字段
        frame_out = {k: round(v, 1) if isinstance(v, (int, float)) else v
                     for k, v in frame.items() if not k.startswith("_")}
        frame_out["_diag_bands"] = frame.get("_bands", [])

        body_out = {k: round(v, 1) for k, v in body.items()}
        sub_out = {k: (round(v, 1) if isinstance(v, (int, float)) else v)
                   for k, v in subtable.items()}

        coord_out = {
            "image": f"{stem}.png",
            "source_jpg": jpg_path.name,
            "width": img_w, "height": img_h,
            "frame": frame_out,
            "main_body": body_out,
            "subtable_br": sub_out,
            "column_lines": [
                {"col_id": c["col_id"], "x": round(c["x"], 1),
                 "y_top": round(c["y_top"], 1), "y_bot": round(c["y_bot"], 1),
                 "y_span": round(c["y_span"], 1), "total_length": round(c["total_length"], 1),
                 "num_segments": c["num_segments"], "segment_ids": c["segment_ids"],
                 "touches_top": c["touches_top"], "touches_bottom": c["touches_bottom"],
                 "d_top": round(c["d_top"], 1), "d_bot": round(c["d_bot"], 1),
                 "label": "real_column"}
                for c in real_cols
            ],
            "internal_vlines": [
                {"x": round(c["x"], 1), "y_top": round(c["y_top"], 1),
                 "y_bot": round(c["y_bot"], 1), "y_span": round(c["y_span"], 1),
                 "total_length": round(c["total_length"], 1),
                 "num_segments": c["num_segments"],
                 "touches_top": c["touches_top"], "touches_bottom": c["touches_bottom"],
                 "d_top": round(c["d_top"], 1), "d_bot": round(c["d_bot"], 1),
                 "label": "internal"}
                for c in internal
            ],
            "summary": {
                "num_real_columns": cont["num_real_columns"],
                "num_internal_vlines": len(internal),
                "is_continuous": cont["is_continuous"],
                "missing_side": cont["missing_side"],
                "median_gap": cont.get("median_gap", 0),
            },
        }
        with open(paths.COLUMN_CLEAN_COORD_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(coord_out, f, ensure_ascii=False, indent=2)

        return stem, True, (
            f"cols={cont['num_real_columns']} internal={len(internal)} "
            f"frame=[{frame['left']:.0f},{frame['top']:.0f},{frame['right']:.0f},{frame['bottom']:.0f}] "
            f"sub={'Y' if subtable.get('exists') else 'N'}"
        )
    except Exception as e:
        return stem, False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


# ============================================================
# 主入口
# ============================================================
def main():
    paths.ensure_dirs(*OUTPUT_DIRS)
    pairs = paths.pair_jpg_json(paths.CANDIDATE_COORD_DIR)
    if not pairs:
        print(f"未找到配对的 JPG/JSON。RAW_DIR={paths.RAW_DIR} "
              f"JSON_DIR={paths.CANDIDATE_COORD_DIR}")
        return
    print(f"输出目录：{paths.COLUMN_CLEAN_DIR}")
    run_batch(pairs, process_image, starmap=True)


if __name__ == "__main__":
    main()
