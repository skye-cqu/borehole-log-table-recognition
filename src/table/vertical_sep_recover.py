# -*- coding: utf-8 -*-
# DEPRECATED: 本原型已被 src/table/column_fit.py 取代（column_fit 同时支持纵向+横向、含 noise
# 再召回、采用折线/分段轨迹形式，且产物回挂 column_id）。保留不删以免破坏既有产物。
"""阶段4 原型：纵向主分隔线重建（按固定 y 分层 + 多路径 Non-crossing 联合）

目标：从阶段3/4 产生的竖线证据碎片中，恢复贯穿整张柱状图的、有限条
纵向主分隔线。每条主分隔线表示为随 y 变化的轨迹 x(y)（允许整体小幅
倾斜/弯曲），输出轨迹 + 支撑碎片 id 列表 + Coverage + 总代价 + 可视化叠加图。

与阶段5b column_recover.py 的根本区别：
  - column_recover 按 x 粗聚类 -> 簇内独立 DP，无全局 Non-crossing 约束；
  - 本原型按【固定 y 步长分层】建全局 DAG，再【逐条抽取 + 占用惩罚】
    实现多条路径的联合优化与 Non-crossing 硬约束。

输入（只读）：
  - data/raw_images/*.JPG（彩色扫描件，叠加背景）
  - data/表格线候选识别处理/坐标数据/*.json（候选线，阶段4 产物）
输出（data/纵向主分隔线重建/）：
  - 叠加可视化图/   原图副本上绘制恢复的各列轨迹
  - 纯线条可视化图/ 白底仅绘制各列轨迹
  - 坐标数据/      每图 JSON（列边界轨迹 + 支撑碎片 + coverage + 代价）
  - 特征统计/      每图 JSON（列数/coverage 分布，便于调参）

不做行/单元格/OCR；不重新检测原图线；不把 band_id 当列号；不强制拟合成直线。

用法：
    python src/table/vertical_sep_recover.py
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch
from src.table.column_recover import (
    load_vertical_candidates,
    smooth_trajectory,
    draw_polyline_pts,
)

# ---- 输出目录 ----
OUTPUT_DIRS = (
    paths.VERTICAL_SEP_OVERLAY_DIR,
    paths.VERTICAL_SEP_PURE_DIR,
    paths.VERTICAL_SEP_COORD_DIR,
    paths.VERTICAL_SEP_STATS_DIR,
)

# ============================================================
# 可调参数（初值，后续按真实数据实测调，不锁死）
# ============================================================
Y_STEP = 100.0          # 固定 y 分层步长（px）；图高 18661 -> 约 187 层
W_X = 0.5               # 层间 x 偏移惩罚系数（|Δx| 每 px 的代价）
NODE_GAIN = 60.0       # 经过一个有证据层的基础收益（奖励向下延伸，>0 才愿走）
SCORE_GAIN = 0.0        # 每层置信度的额外收益系数（原型先关，避免 score_sum 量级淹没长路径）
GAP_PENALTY = 14.0      # 每层缺失证据（断裂）的代价；缺口越大代价越高
LONG_GAP_PENALTY = 40.0 # 连续缺失超过此层数的“长期无证据”额外显著代价阈值
OCCUPY_BAND = 25.0      # 已占用列在每层左右各占用的 x 半带宽（px）；同时影响层内候选合并
OCCUPY_PENALTY = 45.0   # 后续路径进入/穿越已占用 (层,x) 的额外代价
MIN_GAIN_RATIO = 0.03   # 首条最优路径 gain 的下限（图高比例，防纯噪声图）
REL_MIN_RATIO = 0.30    # 后续列停止抽取的相对门槛：gain < REL_MIN_RATIO * 首条gain 则停止
MIN_PATH_LAYERS = 30    # 路径至少经过的层数（低于则视为短碎片，不抽取）
MAX_COLUMNS = 30        # 单图最多恢复列数上限（安全闸）
COVERAGE_MIN = 0.20     # coverage 低于此值的列标记为不可靠（仍输出，仅标注）
SAMPLE_STEP = 50.0      # 列边界沿 y 等间距采样步长（px），用于平滑与可视化


# ============================================================
# 步骤1：按固定 y 分层，构建层节点
# ============================================================
def build_layers(segs, img_h, y_step=Y_STEP):
    """把竖线候选按固定 y 步长分层。

    返回：
      layers: list[dict]，每层 k 含
        - k, y0, y1（该层 y 区间）
        - nodes: list[dict] 该层候选列位置节点，每个含
            x（该层候选 x 中位数）、seg_ids（支撑碎片 id）、
            xmin/xmax（该层候选 x 范围）、score_sum（置信度累加）
        - has_evidence: bool
      层索引 k=0..K-1，自上而下，作为 DAG 拓扑序。
    """
    K = int(np.ceil(img_h / y_step)) + 1
    layers = []
    for k in range(K):
        y0 = k * y_step
        y1 = min((k + 1) * y_step, img_h)
        layers.append({
            "k": k, "y0": y0, "y1": y1,
            "nodes": [], "has_evidence": False,
        })

    # 把每个候选按其 midy 归入一层（midy 落在该层 y 区间）
    for s in segs:
        k = int(s["midy"] // y_step)
        if k < 0:
            k = 0
        if k >= K:
            k = K - 1
        # 该候选的 x：取 points 的 x 中位数，比 midx 更稳
        pts = s["points"]
        xs = [p[0] for p in pts]
        xm = float(np.median(xs)) if xs else float(s["midx"])
        layers[k]["nodes"].append({
            "x": xm,
            "seg_id": s["id"],
            "score": float(s.get("length", 0.0)),  # 暂以长度作权重，后续可换 final_score
        })
        layers[k]["has_evidence"] = True

    # 每层聚合为若干候选列位置节点：按 x 接近度（<=OCCUPY_BAND）合并，
    # 取 x 中位数、汇总支撑碎片 id 与置信度
    for ly in layers:
        if not ly["nodes"]:
            continue
        # 按 x 排序后贪心合并相邻（间距<=OCCUPY_BAND）的候选
        ns = sorted(ly["nodes"], key=lambda n: n["x"])
        merged = []
        cur_xs = [ns[0]["x"]]
        cur_ids = [ns[0]["seg_id"]]
        cur_score = ns[0]["score"]
        for n in ns[1:]:
            if n["x"] - max(cur_xs) <= OCCUPY_BAND:
                cur_xs.append(n["x"])
                cur_ids.append(n["seg_id"])
                cur_score += n["score"]
            else:
                merged.append({
                    "x": float(np.median(cur_xs)),
                    "seg_ids": cur_ids,
                    "xmin": float(min(cur_xs)),
                    "xmax": float(max(cur_xs)),
                    "score_sum": cur_score,
                })
                cur_xs = [n["x"]]
                cur_ids = [n["seg_id"]]
                cur_score = n["score"]
        merged.append({
            "x": float(np.median(cur_xs)),
            "seg_ids": cur_ids,
            "xmin": float(min(cur_xs)),
            "xmax": float(max(cur_xs)),
            "score_sum": cur_score,
        })
        ly["nodes"] = merged
        ly["has_evidence"] = True
    return layers


# ============================================================
# 步骤2：全局 DAG + 单条最小代价路径 DP（带占用惩罚）
# ============================================================
def edge_cost(x_from, x_to, gap_layers, occupy_blocked):
    """层间连边代价（越小越好，从收益中扣除）。

    - x 偏移：W_X * |Δx|（接近极低，差距大高）
    - 断裂惩罚：缺口处每层缺失证据付 GAP_PENALTY；长期无证据显著增代价
    - 占用惩罚：若目标 (层, x) 落在已占用列带宽内，付 OCCUPY_PENALTY
    """
    p_x = W_X * abs(x_to - x_from)
    # gap_layers: 从上一层到本层之间“缺失证据的层数”
    p_gap = gap_layers * GAP_PENALTY
    if gap_layers > LONG_GAP_PENALTY / GAP_PENALTY:
        # 长期无证据：额外显著惩罚（阶梯：超出部分再叠加一份）
        over = gap_layers - LONG_GAP_PENALTY / GAP_PENALTY
        p_gap += over * GAP_PENALTY
    p_occ = OCCUPY_PENALTY if occupy_blocked else 0.0
    return p_x + p_gap + p_occ


def dp_best_path(layers, occupy):
    """最大化净收益（覆盖收益 - 代价）的从上往下列轨迹。

    框架（类比 column_recover 的 gain = y_extend - penalty）：
      - 每个有证据节点收益 = NODE_GAIN + SCORE_GAIN * score_sum（奖励向下延伸）
      - 边代价 = edge_cost（x 偏移 + 断裂 + 占用）
      - dp[node] = node_gain + max(0, max_over_pred(dp[pred] - edge_cost))
        即：要么接在前驱后（扣边代价），要么作为新起点（不接前驱，收益仅自身）
      - 终点取 dp 最大者，回溯至无前驱（prev=-1 表示起点，保留）

    occupy: dict[k] -> list[(x_lo, x_hi)]，已占用层-x带宽区间。
    返回 (gain, path)，path 为 list[dict]{k, x, seg_ids, y}。
    """
    K = len(layers)
    dp = [{} for _ in range(K)]
    prev = [{} for _ in range(K)]

    for k in range(K):
        ly = layers[k]
        for ni, node in enumerate(ly["nodes"]):
            x = node["x"]
            blocked = _in_occupy(occupy, k, x)
            node_gain = NODE_GAIN + SCORE_GAIN * node.get("score_sum", 0.0)
            if blocked:
                node_gain -= OCCUPY_PENALTY  # 占用区进入减收益
            best = node_gain           # 作为新起点（无前驱）
            best_prev = (-1, -1)
            if k > 0:
                pk = k - 1
                while pk >= 0:
                    gap_layers = max(k - pk - 1, 0)
                    ply = layers[pk]
                    for pni, pnode in enumerate(ply["nodes"]):
                        key = (pk, pni)
                        if key not in dp[pk]:
                            continue
                        c = edge_cost(pnode["x"], x, gap_layers, blocked)
                        cand = dp[pk][key] + node_gain - c
                        if cand > best:
                            best = cand
                            best_prev = key
                    if ply["has_evidence"]:
                        break  # 局部窗口：仅回溯到最近有证据层，避免全连通 O(K^2)
                    pk -= 1
            dp[k][(k, ni)] = best
            prev[k][(k, ni)] = best_prev

    # 全局最大收益终点
    best_gain = -float("inf")
    best_end = None
    for k in range(K):
        for key, g in dp[k].items():
            if g > best_gain:
                best_gain = g
                best_end = key

    if best_end is None or not np.isfinite(best_gain):
        return -float("inf"), []

    # 回溯（prev=-1 表示起点，仍保留该节点）
    path = []
    cur = best_end
    while cur != (-1, -1):
        k, ni = cur
        node = layers[k]["nodes"][ni]
        path.append({"k": k, "x": node["x"], "seg_ids": node["seg_ids"],
                     "y": (layers[k]["y0"] + layers[k]["y1"]) / 2.0})
        cur = prev[k][cur]
    path.reverse()
    return best_gain, path


def _in_occupy(occupy, k, x):
    for (x_lo, x_hi) in occupy.get(k, []):
        if x_lo <= x <= x_hi:
            return True
    return False


# ============================================================
# 步骤3：多条路径联合抽取（Non-crossing，方案 A）
# ============================================================
def recover_columns(layers, img_h):
    """循环抽取最优轨迹，逐条占用，直到代价过低或达上限。

    返回 list[dict]: 每条列含 traj 点序列、seg_ids、coverage、cost、reliable。
    """
    occupy = {}  # k -> list[(x_lo, x_hi)]
    columns = []
    base_gain = None  # 首条最优路径收益，作为相对门槛基准
    abs_min_gain = max(MIN_GAIN_RATIO * img_h, NODE_GAIN * 5)
    for _ in range(MAX_COLUMNS):
        gain, path = dp_best_path(layers, occupy)
        if not np.isfinite(gain) or gain < abs_min_gain:
            break
        if len(path) < 2:
            break
        # 经过的层数（=有证据节点数）低于硬门槛，视为短碎片：
        # 仍占用其层（避免挡住更长路径），但不计入列、继续抽取
        if len(path) < MIN_PATH_LAYERS:
            for p in path:
                occupy.setdefault(p["k"], []).append(
                    (p["x"] - OCCUPY_BAND, p["x"] + OCCUPY_BAND))
            continue
        # 相对门槛：首条之后，收益低于首条的 REL_MIN_RATIO 则停止
        if base_gain is None:
            base_gain = gain
        elif gain < REL_MIN_RATIO * base_gain:
            break
        # 占用：把该列轨迹经过的每层 x±OCCUPY_BAND 标记为占用
        for p in path:
            k = p["k"]
            lo = p["x"] - OCCUPY_BAND
            hi = p["x"] + OCCUPY_BAND
            occupy.setdefault(k, []).append((lo, hi))
        # coverage：支撑层覆盖的 y 高度 / 图高
        ys = [p["y"] for p in path]
        y_span = (max(ys) - min(ys)) if ys else 0.0
        coverage = y_span / img_h if img_h > 0 else 0.0
        # 收集支撑碎片（去重）
        seg_ids = []
        for p in path:
            for sid in p["seg_ids"]:
                if sid not in seg_ids:
                    seg_ids.append(sid)
        columns.append({
            "traj": [[round(p["x"], 1), round(p["y"], 1)] for p in path],
            "seg_ids": seg_ids,
            "coverage": round(float(coverage), 4),
            "cost": round(float(gain), 2),
            "reliable": coverage >= COVERAGE_MIN,
        })
    # 按平均 x 排序，便于阅读
    columns.sort(key=lambda c: float(np.mean([p[0] for p in c["traj"]])))
    return columns


# ============================================================
# 可视化（复用 column_recover.draw_polyline_pts）
# ============================================================
def draw_overlay(orig, columns):
    viz = orig.copy()
    for ci, c in enumerate(columns):
        color = (0, 200, 0) if c["reliable"] else (0, 180, 220)
        draw_polyline_pts(viz, c["traj"], color, 3)
    return viz


def draw_pure(w, h, columns):
    viz = np.full((h, w, 3), 255, dtype=np.uint8)
    for c in columns:
        color = (0, 170, 0) if c["reliable"] else (0, 150, 200)
        draw_polyline_pts(viz, c["traj"], color, 2)
    return viz


# ============================================================
# 单图处理
# ============================================================
def process_image(jpg_path, json_path):
    stem = jpg_path.stem
    try:
        paths.ensure_dirs(*OUTPUT_DIRS)

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        img_w, img_h = int(data["width"]), int(data["height"])

        orig = cv2.imread(str(jpg_path), cv2.IMREAD_COLOR)
        if orig is None:
            return stem, False, "无法读取原图 JPG"
        if orig.shape[0] != img_h or orig.shape[1] != img_w:
            return stem, False, f"原图尺寸 {orig.shape} 与 JSON {img_w}x{img_h} 不一致"

        # 步骤1：加载纵向候选
        segs = load_vertical_candidates(data)
        if not segs:
            return stem, False, "无纵向候选"

        # 步骤2：按固定 y 分层
        layers = build_layers(segs, img_h, Y_STEP)

        # 步骤3：多路径联合抽取（Non-crossing）
        columns = recover_columns(layers, img_h)

        # 平滑采样（仅用于可视化，保持 x(y) 轨迹表达，不强制直线）
        columns_out = []
        for c in columns:
            # 用原始 traj 点做轻量 polyfit 平滑（deg=2 允许轻微倾斜弯曲）
            pts = sorted(c["traj"], key=lambda p: p[1])
            ys = np.array([p[1] for p in pts], dtype=np.float64)
            xs = np.array([p[0] for p in pts], dtype=np.float64)
            if len(pts) >= 3:
                coef = np.polyfit(ys, xs, 2)
                poly = np.poly1d(coef)
                samples = []
                y = float(ys.min())
                while y <= float(ys.max()):
                    samples.append([round(float(poly(y)), 1), round(y, 1)])
                    y += SAMPLE_STEP
            else:
                samples = [[round(p[0], 1), round(p[1], 1)] for p in pts]
            columns_out.append({
                "traj": c["traj"],
                "samples": samples,
                "seg_ids": c["seg_ids"],
                "coverage": c["coverage"],
                "cost": c["cost"],
                "reliable": c["reliable"],
            })

        # ---- 输出1：叠加可视化图 ----
        viz = draw_overlay(orig, columns_out)
        cv2.imwrite(str(paths.VERTICAL_SEP_OVERLAY_DIR / f"{stem}.png"), viz,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出2：纯线条可视化图 ----
        viz_pure = draw_pure(img_w, img_h, columns_out)
        cv2.imwrite(str(paths.VERTICAL_SEP_PURE_DIR / f"{stem}.png"), viz_pure,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出3：坐标数据 JSON ----
        coord_out = {
            "image": f"{stem}.png",
            "source_jpg": jpg_path.name,
            "width": img_w, "height": img_h,
            "y_step": Y_STEP,
            "summary": {
                "columns": len(columns_out),
                "reliable_columns": sum(1 for c in columns_out if c["reliable"]),
                "vertical_candidates": len(segs),
                "layers": len(layers),
            },
            "columns": [{
                "index": i,
                "reliable": c["reliable"],
                "coverage": c["coverage"],
                "cost": c["cost"],
                "num_segments": len(c["seg_ids"]),
                "seg_ids": c["seg_ids"],
                "traj": c["traj"],        # 原始分层轨迹 x(y)
                "samples": c["samples"],  # 平滑采样点
            } for i, c in enumerate(columns_out)],
        }
        with open(paths.VERTICAL_SEP_COORD_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(coord_out, f, ensure_ascii=False)

        # ---- 输出4：特征统计 JSON ----
        covs = [c["coverage"] for c in columns_out]
        stats = {
            "summary": coord_out["summary"],
            "coverage": {
                "min": min(covs) if covs else 0,
                "max": max(covs) if covs else 0,
                "p50": round(float(np.percentile(covs, 50)), 4) if covs else 0,
            },
            "costs": [c["cost"] for c in columns_out],
        }
        with open(paths.VERTICAL_SEP_STATS_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        return stem, True, (
            f"列={len(columns_out)} 可靠={sum(1 for c in columns_out if c['reliable'])} "
            f"候选={len(segs)} 层={len(layers)}"
        )
    except Exception as e:
        return stem, False, f"{type(e).__name__}: {e}"


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
    print(f"输出目录：{paths.VERTICAL_SEP_DIR}")
    print(f"参数：Y_STEP={Y_STEP} W_X={W_X} GAP_PENALTY={GAP_PENALTY} "
          f"OCCUPY_BAND={OCCUPY_BAND} OCCUPY_PENALTY={OCCUPY_PENALTY} "
          f"MIN_GAIN_RATIO={MIN_GAIN_RATIO} MIN_PATH_LAYERS={MIN_PATH_LAYERS}")
    run_batch(pairs, process_image, starmap=True)


if __name__ == "__main__":
    main()
