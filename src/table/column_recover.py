# -*- coding: utf-8 -*-
"""阶段5b：纵向主框架恢复：纵向候选粗聚类 + 轨迹图搜索 + DP + 评分 + 平滑

只恢复"主要列边界 + 外部大框架"的纵向骨架，不做行结构/单元格重构。
DBSCAN 仅用于将位置相近的纵向候选划入粗簇；随后根据候选段之间的
y 向间隔、x 向距离、方向差和局部延伸趋势建立有向图，通过动态规划
寻找纵向覆盖范围最大、连接代价最低的连续轨迹。每条轨迹再依据纵向
覆盖率、连续性、方向平滑度和支持线段数量评分。高分长轨迹作为主列
边界，局部短轨迹暂不认定为表格列。恢复轨迹后再用低阶多项式平滑
获得精确列边界坐标。

输入（只读）：
  - data/raw_images/*.JPG（彩色扫描件，用作原图副本与叠加背景）
  - data/表格线候选识别处理/坐标数据/*.json（候选线+标签+特征，阶段4 产物）
输出（data/纵向主框架恢复/）：
  - 原图/             原始扫描件 PNG 无损副本，绝不绘制
  - 叠加可视化图/     原图副本上绘制恢复的纵向轨迹（主要人工核验图）
  - 纯线条可视化图/   白底仅绘制纵向轨迹
  - 坐标数据/         每图 JSON（主列边界采样点 + 轨迹详情 + 评分）
  - 特征统计/         每图 JSON（列数/轨迹数/覆盖率分布，便于调参）

与原图同尺寸同坐标系，可逐像素对照。输入全程只读。

用法：
    python src/table/column_recover.py
"""
import json
import sys
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
    paths.COLUMN_RECOVER_ORIG_DIR,
    paths.COLUMN_RECOVER_OVERLAY_DIR,
    paths.COLUMN_RECOVER_PURE_DIR,
    paths.COLUMN_RECOVER_COORD_DIR,
    paths.COLUMN_RECOVER_STATS_DIR,
)

# ---- DBSCAN 粗聚类参数 ----
DBSCAN_EPS = 8.0       # 一级聚类半径（px）；探查：eps=8 对 1015/1024 干净
DBSCAN_MIN = 3         # 最小成员数
SPLIT_EPS = 4.0        # 二次拆分半径（px）；大簇内更细的子分组
SPLIT_SPAN = 30.0      # 触发二次拆分的簇 x-span 阈值（px）

# ---- 图搜索/DP 边权参数 ----
GAP_HARD = 250.0       # y 间隔超过此值不建边（真断口）；数据：断口中位84、p75=209
GAP_SOFT = 30.0        # y 间隔在此值内为低代价连接
GAP_PENALTY = 5.0      # 每单位 gap 的惩罚（收益中扣除）
GAP_BRIDGE = 350.0     # 跨断口桥接的 y 间隔上限；>此值视为硬断口不可桥接
X_TOL = 20.0           # x 偏移容差，<=此值零惩罚
X_LIN = 0.6            # 超出容差的线性惩罚系数
X_CAP = 50.0           # 单边 x 惩罚上限（60px偏移->0.6×40=24，远低于旧平方180）
X_BRIDGE_MAX = 80.0    # 允许连接/桥接的最大 |Δmidx|；>此值不建边
ANGLE_PENALTY = 0.1    # 每单位 (Δpca)² 的惩罚
MAX_Y_OFFSET = 400.0   # 构建边时 j.y0 相对 i.y0 的最大前向查找窗口（px），限边数

# ---- 轨迹评分阈值 ----
MAIN_SCORE = 0.50      # 主列边界最低综合分
MAIN_COVERAGE = 0.40   # 主列边界最低 y 覆盖率
MIN_TRAJ_SEGS = 2      # 轨迹至少含 2 段才评分

# ---- 平滑采样 ----
SAMPLE_STEP = 50.0     # 列边界沿 y 等间距采样步长（px）
POLY_DEG = 2           # 多项式拟合阶数（允许轻微倾斜）


# ============================================================
# 步骤1：加载纵向候选
# ============================================================
def load_vertical_candidates(data):
    """从候选识别 JSON 提取纵向 high/suspect 段。

    返回 list[dict]，每个含 id,y0,y1,midx,midy,length,pca_angle。
    """
    segs = []
    for l in data["lines"]:
        if l["direction"] != "vertical":
            continue
        if l["label"] not in ("high", "suspect"):
            continue
        x0, y0, x1, y1 = l["bbox"]
        segs.append({
            "id": l["id"],
            "y0": float(y0), "y1": float(y1),
            "midx": float(l["midx"]), "midy": float(l["midy"]),
            "length": float(l["length"]),
            "pca_angle": float(l["pca_angle"]),
            "points": l["points"],
        })
    return segs


# ============================================================
# 步骤2：DBSCAN 粗聚类 + 大簇二次拆分
# ============================================================
def dbscan_cluster(segments):
    """对纵向候选按 midx 一维 DBSCAN 聚类，大簇二次拆分。

    返回 list[list[seg]]，每个子列表为一个列候选组。
    """
    if not segments:
        return []
    X = np.array([[s["midx"]] for s in segments], dtype=np.float64)
    labels = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN).fit_predict(X)

    groups = []
    for lbl in set(labels):
        if lbl == -1:
            # 噪声点单独成组（可能短小孤立段）
            for i in np.where(labels == lbl)[0]:
                groups.append([segments[i]])
            continue
        members = [segments[i] for i in np.where(labels == lbl)[0]]
        xs = np.array([m["midx"] for m in members])
        xspan = float(xs.max() - xs.min())
        if xspan > SPLIT_SPAN and len(members) > DBSCAN_MIN:
            # 二次拆分：更小 eps 再聚
            X2 = np.array([[m["midx"]] for m in members], dtype=np.float64)
            sub_labels = DBSCAN(eps=SPLIT_EPS, min_samples=DBSCAN_MIN).fit_predict(X2)
            for sl in set(sub_labels):
                if sl == -1:
                    for i in np.where(sub_labels == sl)[0]:
                        groups.append([members[i]])
                else:
                    sub = [members[i] for i in np.where(sub_labels == sl)[0]]
                    groups.append(sub)
        else:
            groups.append(members)
    # 按 midx 中位数排序列组
    groups.sort(key=lambda g: float(np.median([s["midx"] for s in g])))
    return groups


# ============================================================
# 步骤3：簇内构建有向图
# ============================================================
def edge_cost(si, sj):
    """计算从段 i 到段 j 的连接代价（惩罚，越小越好）。返回 None 表示不建边。

    DP 将最大化"y 延伸收益 - 此惩罚"。惩罚由 gap、x 偏移、方向差构成。
    - gap：重叠(gap<=0)惩罚0；0<gap<=SOFT 缓增；SOFT<gap<=HARD 陡增；>HARD 不建边
    - x 偏移：分段线性 + cap（真列跨断口偏移 p95≈63px，旧平方惩罚严重过度）
    - 方向：平方惩罚（方向高度一致，权重小）
    """
    gap = sj["y0"] - si["y1"]
    if gap > GAP_HARD:
        return None  # 真断口，不连
    # gap 惩罚：重叠=0，0<gap<=SOFT 缓增，SOFT<gap<=HARD 陡增
    if gap <= 0:
        p_gap = 0.0
    elif gap <= GAP_SOFT:
        p_gap = GAP_PENALTY * gap / GAP_SOFT
    else:
        p_gap = GAP_PENALTY * (1.0 + 3.0 * (gap - GAP_SOFT) / (GAP_HARD - GAP_SOFT))
    # x 对齐惩罚：分段线性 + cap（替代旧平方项）
    dx = abs(sj["midx"] - si["midx"])
    if dx > X_BRIDGE_MAX:
        return None  # 偏移过大，不建边
    p_x = min(X_LIN * max(dx - X_TOL, 0.0), X_CAP)
    # 方向惩罚
    p_a = ANGLE_PENALTY * (sj["pca_angle"] - si["pca_angle"]) ** 2
    return p_gap + p_x + p_a


def build_dag(members):
    """为列候选组建 DAG。

    返回 adj: dict[i] = list of (j, penalty)。节点按 y0 升序索引。
    边 i->j 要求 j.y0 > i.y0 且 j.y0 <= i.y1 + MAX_Y_OFFSET（按 y 下沿延伸窗口限边数，
    而非 y0 绝对差，避免长段因 y0 差大而断边）。
    """
    members = sorted(members, key=lambda s: s["y0"])
    n = len(members)
    adj = {i: [] for i in range(n)}
    for i in range(n):
        # 边窗口：j.y0 在 (i.y0, i.y1 + MAX_Y_OFFSET] 内
        y_limit = members[i]["y1"] + MAX_Y_OFFSET
        for j in range(i + 1, n):
            if members[j]["y0"] > y_limit:
                break  # 超出延伸窗口，后续更远，停止
            if members[j]["y0"] <= members[i]["y0"]:
                continue  # y0 不递增，跳过（排序后一般不会，但安全起见）
            c = edge_cost(members[i], members[j])
            if c is not None:
                adj[i].append((j, c))
    return members, adj


# ============================================================
# 步骤4：动态规划求最优轨迹
# ============================================================
def dp_best_path(members, adj):
    """DP 求覆盖最大、连接代价最低的最优路径。

    目标：最大化累计"y 延伸收益 - 连接惩罚"。
    - 边 i->j 的 y 延伸 = max(j.y1 - i.y1, 0)：段 j 把轨迹下沿推进多少
      （重叠则延伸为 0，避免在重叠区堆叠段白赚收益）
    - 收益 = y_extend - penalty
    - dp[j] = max over pred i of (dp[i] + gain(i,j))，起点 dp=0
    返回路径（成员对象列表）。
    """
    n = len(members)
    if n == 0:
        return []
    dp = [0.0] * n
    prev = [-1] * n
    for j in range(n):
        best = 0.0  # 从虚拟起点 s 直接到 j（无前驱），收益 0
        best_i = -1
        for i in range(j):
            for (k, pen) in adj.get(i, []):
                if k != j:
                    continue
                # y 延伸：段 j 把下沿推进多少（相对段 i 的 y1）
                y_ext = max(members[j]["y1"] - members[i]["y1"], 0.0)
                gain = y_ext - pen
                if dp[i] + gain > best:
                    best = dp[i] + gain
                    best_i = i
        dp[j] = best
        prev[j] = best_i
    # 找终点：累计收益最大（y 覆盖最远 + 代价最低）
    end = int(np.argmax(dp))
    # 回溯
    path = []
    cur = end
    while cur != -1:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return [members[i] for i in path]


def extract_trajectories(members, max_trajs=8, min_segs=MIN_TRAJ_SEGS):
    """从列候选组提取轨迹：断口切分 + 区间独立 DP + 跨断口桥接。

    解决旧"贪心剥离"策略的缺陷：下半部海量重叠段淹没上半部，
    导致上半部真列段被漏掉。

    流程：
    1. 按 y0 排序，在 gap>GAP_BRIDGE 处切分为 y 子区间
       （gap<=GAP_BRIDGE 的断口允许桥接，不切分）
    2. 每个子区间独立跑 build_dag + dp_best_path，得到局部最优轨迹
       -- 子区间内段数少，上半部不会被下半部淹没
    3. 跨断口桥接：相邻子区间的末端轨迹，若 gap<=GAP_BRIDGE 且
       |Δmidx|<=X_BRIDGE_MAX，合并成一条长轨迹
    """
    if len(members) < min_segs:
        return []
    members = sorted(members, key=lambda s: s["y0"])

    # 1. 按硬断口（gap>GAP_BRIDGE）切分 y 子区间
    sub_groups = []
    cur = [members[0]]
    for i in range(1, len(members)):
        gap = members[i]["y0"] - members[i - 1]["y1"]
        if gap > GAP_BRIDGE:
            sub_groups.append(cur)
            cur = [members[i]]
        else:
            cur.append(members[i])
    sub_groups.append(cur)

    # 2. 每个子区间独立 DP（每区间取最优 + 次优轨迹）
    sub_trajs = []
    for sg in sub_groups:
        if len(sg) < min_segs:
            if sg:
                sub_trajs.append([sg[0]])  # 单段也保留
            continue
        mem, adj = build_dag(sg)
        path = dp_best_path(mem, adj)
        if path:
            sub_trajs.append(path)
            # 次优：移除已用段再跑一次（捕捉同区间并列轨迹）
            used = set(s["id"] for s in path)
            remain = [s for s in sg if s["id"] not in used]
            if len(remain) >= min_segs:
                mem2, adj2 = build_dag(remain)
                path2 = dp_best_path(mem2, adj2)
                if path2 and len(path2) >= min_segs:
                    sub_trajs.append(path2)

    # 3. 跨断口桥接：相邻子区间轨迹若 gap<=GAP_BRIDGE 且 |Δmidx|<=X_BRIDGE_MAX 则合并
    if len(sub_trajs) <= 1:
        return sub_trajs
    # 按 y 范围排序子轨迹
    sub_trajs.sort(key=lambda t: min(s["y0"] for s in t))
    merged = [list(sub_trajs[0])]
    for nxt in sub_trajs[1:]:
        prev = merged[-1]
        prev_end = max(s["y1"] for s in prev)
        nxt_start = min(s["y0"] for s in nxt)
        gap = nxt_start - prev_end
        prev_midx = float(np.median([s["midx"] for s in prev]))
        nxt_midx = float(np.median([s["midx"] for s in nxt]))
        dx = abs(nxt_midx - prev_midx)
        if 0 < gap <= GAP_BRIDGE and dx <= X_BRIDGE_MAX:
            # 桥接：合并到上一条轨迹
            merged[-1] = prev + nxt
        else:
            merged.append(list(nxt))
    return merged


# ============================================================
# 步骤5：轨迹评分 + 主列边界筛选
# ============================================================
def score_trajectory(traj, img_h):
    """5 维评分。返回 (score, metrics)。

    维度：y_coverage(覆盖率) + y_span_ratio(跨度连续性) + continuity(平均gap) +
          angle_smooth(方向平滑) + support(段数)。
    新增 y_span_ratio 显式奖励轨迹 y 跨度占图像高度的比例，
    鼓励 DP 覆盖整列高度而非在局部堆叠。
    """
    if len(traj) < MIN_TRAJ_SEGS:
        return 0.0, {}
    ys0 = [s["y0"] for s in traj]
    ys1 = [s["y1"] for s in traj]
    y_min, y_max = min(ys0), max(ys1)
    y_span = y_max - y_min
    y_coverage = min(y_span / img_h, 1.0) if img_h > 0 else 0.0
    y_span_ratio = y_coverage  # 轨迹 y 跨度 / 图像高度

    # 连续性：平均 gap 归一
    gaps = []
    for a, b in zip(traj[:-1], traj[1:]):
        g = b["y0"] - a["y1"]
        gaps.append(max(g, 0.0))  # 重叠记0
    mean_gap = float(np.mean(gaps)) if gaps else 0.0
    continuity = max(0.0, 1.0 - mean_gap / GAP_HARD)

    # 方向平滑度
    angs = [s["pca_angle"] for s in traj]
    ang_std = float(np.std(angs)) if len(angs) > 1 else 0.0
    angle_smooth = max(0.0, 1.0 - ang_std / 5.0)  # 5° 标准差归零

    # 支持线段数
    support = min(len(traj) / 10.0, 1.0)  # 10 段满分

    score = (0.30 * y_coverage + 0.15 * y_span_ratio + 0.20 * continuity
             + 0.20 * angle_smooth + 0.15 * support)
    return round(float(score), 4), {
        "y_coverage": round(float(y_coverage), 4),
        "y_span_ratio": round(float(y_span_ratio), 4),
        "continuity": round(float(continuity), 4),
        "angle_smooth": round(float(angle_smooth), 4),
        "support": round(float(support), 4),
        "y_span": round(float(y_span), 1),
        "seg_count": len(traj),
    }


# ============================================================
# 步骤6：低阶多项式平滑
# ============================================================
def smooth_trajectory(traj, img_h):
    """对轨迹段中点 (midx, midy) 按 y 排序，polyfit 拟合 x(y)。

    返回采样点 [[x,y],...] 沿 y 等间距。
    """
    pts = sorted([(s["midy"], s["midx"]) for s in traj], key=lambda p: p[0])
    ys = np.array([p[0] for p in pts], dtype=np.float64)
    xs = np.array([p[1] for p in pts], dtype=np.float64)
    if len(pts) < POLY_DEG + 1:
        # 点太少，直接用中位 x 作直线
        x_med = float(np.median(xs))
        y0, y1 = float(ys.min()), float(ys.max())
        samples = []
        y = y0
        while y <= y1:
            samples.append([round(x_med, 1), round(y, 1)])
            y += SAMPLE_STEP
        return samples, x_med
    coef = np.polyfit(ys, xs, POLY_DEG)
    poly = np.poly1d(coef)
    y0, y1 = float(ys.min()), float(ys.max())
    samples = []
    y = y0
    while y <= y1:
        x = float(poly(y))
        samples.append([round(x, 1), round(y, 1)])
        y += SAMPLE_STEP
    x_center = float(poly((y0 + y1) / 2.0))
    return samples, x_center


# ============================================================
# 可视化
# ============================================================
def draw_polyline_pts(img, pts, color, thickness):
    n = len(pts)
    if n < 2:
        return
    arr = np.array(pts, dtype=np.int32)
    cv2.polylines(img, [arr], False, color, thickness, cv2.LINE_8)


def draw_overlay(orig, main_trajs, short_trajs, clusters):
    """在原图副本上绘制：主列=绿，短轨迹=黄，簇中心=浅蓝点。"""
    viz = orig.copy()
    # 先画簇中心点（底层）
    for c in clusters:
        cv2.circle(viz, (int(c["midx"]), int(c["midy"])), 2, (255, 200, 100), -1)
    # 短轨迹（黄色细线）
    for t in short_trajs:
        for s in t["segs"]:
            draw_polyline_pts(viz, s["points"], (0, 255, 255), 2)
    # 主列（绿色粗线）
    for t in main_trajs:
        if t.get("samples"):
            draw_polyline_pts(viz, t["samples"], (0, 200, 0), 4)
    return viz


def draw_pure(w, h, main_trajs, short_trajs):
    viz = np.full((h, w, 3), 255, dtype=np.uint8)
    for t in short_trajs:
        for s in t["segs"]:
            draw_polyline_pts(viz, s["points"], (0, 200, 255), 2)
    for t in main_trajs:
        if t.get("samples"):
            draw_polyline_pts(viz, t["samples"], (0, 180, 0), 3)
    return viz


# ============================================================
# 单图处理
# ============================================================
def process_image(jpg_path, json_path):
    """处理一张图：纵向候选 -> 聚类 -> 图搜索DP -> 评分 -> 平滑 -> 输出五件套。

    返回 (stem, ok, info)。
    """
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

        # 步骤2：DBSCAN 粗聚类 + 二次拆分
        groups = dbscan_cluster(segs)

        # 簇中心（用于可视化）
        clusters = []
        for g in groups:
            if len(g) == 0:
                continue
            clusters.append({
                "midx": float(np.median([s["midx"] for s in g])),
                "midy": float(np.median([s["midy"] for s in g])),
            })

        # 步骤3-5：每个列组建图搜索、DP、评分
        all_trajs = []
        # 按组聚合：组内多条轨迹合并算 y 覆盖率，判定该组是否为主列
        group_trajs = {}  # gi -> list of traj dicts
        for gi, g in enumerate(groups):
            if len(g) < MIN_TRAJ_SEGS:
                continue
            trajs = extract_trajectories(g)
            for ti, traj in enumerate(trajs):
                score, metrics = score_trajectory(traj, img_h)
                samples, x_center = smooth_trajectory(traj, img_h)
                td = {
                    "traj_id": f"g{gi}t{ti}",
                    "group_idx": gi,
                    "score": score,
                    "is_main": False,  # 后面按组合并覆盖率判定
                    "x_center": round(x_center, 1),
                    "metrics": metrics,
                    "samples": samples,
                    "segs": [{"id": s["id"], "y0": s["y0"], "y1": s["y1"],
                              "midx": s["midx"], "length": s["length"],
                              "points": s["points"]} for s in traj],
                }
                all_trajs.append(td)
                group_trajs.setdefault(gi, []).append(td)

        # 按组判定主列：组内 score>=阈值的轨迹合并算 y 覆盖率
        # 合并覆盖率达标则该组所有 score>=MAIN_SCORE 的轨迹标记为主列
        for gi, gtrajs in group_trajs.items():
            qual = [t for t in gtrajs if t["score"] >= MAIN_SCORE]
            if not qual:
                continue
            # 合并这些轨迹的所有段，算 UNION y 覆盖率
            all_y0 = [s["y0"] for t in qual for s in t["segs"]]
            all_y1 = [s["y1"] for t in qual for s in t["segs"]]
            merged_cov = (max(all_y1) - min(all_y0)) / img_h if img_h > 0 else 0.0
            if merged_cov >= MAIN_COVERAGE:
                for t in qual:
                    t["is_main"] = True
                    t["metrics"]["merged_coverage"] = round(float(merged_cov), 4)

        main_trajs = [t for t in all_trajs if t["is_main"]]
        short_trajs = [t for t in all_trajs if not t["is_main"]]
        main_trajs.sort(key=lambda t: t["x_center"])

        # ---- 输出1：原图副本（绝不绘制）----
        cv2.imwrite(str(paths.COLUMN_RECOVER_ORIG_DIR / f"{stem}.png"), orig,
                    [cv2.IMWRITE_PNG_COMPRESSION, 0])

        # ---- 输出2：叠加可视化图 ----
        viz = draw_overlay(orig, main_trajs, short_trajs, clusters)
        cv2.imwrite(str(paths.COLUMN_RECOVER_OVERLAY_DIR / f"{stem}.png"), viz,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出3：纯线条可视化图 ----
        viz_pure = draw_pure(img_w, img_h, main_trajs, short_trajs)
        cv2.imwrite(str(paths.COLUMN_RECOVER_PURE_DIR / f"{stem}.png"), viz_pure,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出4：坐标数据 JSON ----
        main_summary = [{
            "traj_id": t["traj_id"], "x_center": t["x_center"],
            "score": t["score"], "y_coverage": t["metrics"].get("y_coverage", 0),
            "y_span": t["metrics"].get("y_span", 0), "seg_count": t["metrics"].get("seg_count", 0),
            "samples": t["samples"],
        } for t in main_trajs]
        coord_out = {
            "image": f"{stem}.png",
            "source_jpg": jpg_path.name,
            "width": img_w, "height": img_h,
            "summary": {
                "main_columns": len(main_trajs),
                "short_trajectories": len(short_trajs),
                "total_trajectories": len(all_trajs),
                "vertical_candidates": len(segs),
                "cluster_groups": len(groups),
            },
            "main_columns": main_summary,
            "all_trajectories": [{
                "traj_id": t["traj_id"], "is_main": t["is_main"],
                "x_center": t["x_center"], "score": t["score"],
                "metrics": t["metrics"], "seg_count": len(t["segs"]),
            } for t in all_trajs],
        }
        with open(paths.COLUMN_RECOVER_COORD_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(coord_out, f, ensure_ascii=False)

        # ---- 输出5：特征统计 JSON ----
        stats = build_stats(all_trajs, main_trajs, groups, segs, img_h)
        with open(paths.COLUMN_RECOVER_STATS_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        return stem, True, (
            f"主列={len(main_trajs)} 短轨迹={len(short_trajs)} "
            f"候选={len(segs)} 簇={len(groups)}"
        )
    except Exception as e:
        return stem, False, f"{type(e).__name__}: {e}"


def build_stats(all_trajs, main_trajs, groups, segs, img_h):
    """构造特征统计 JSON。"""
    def pct(vals, p):
        return round(float(np.percentile(vals, p)), 2) if vals else 0.0

    main_cov = [t["metrics"].get("y_coverage", 0) for t in main_trajs]
    main_score = [t["score"] for t in main_trajs]
    all_score = [t["score"] for t in all_trajs]
    group_sizes = [len(g) for g in groups]

    return {
        "summary": {
            "main_columns": len(main_trajs),
            "short_trajectories": len(all_trajs) - len(main_trajs),
            "total_trajectories": len(all_trajs),
            "vertical_candidates": len(segs),
            "cluster_groups": len(groups),
        },
        "main_columns": {
            "count": len(main_trajs),
            "y_coverage": {"min": min(main_cov) if main_cov else 0,
                           "max": max(main_cov) if main_cov else 0,
                           "p50": pct(main_cov, 50), "p90": pct(main_cov, 90)},
            "score": {"min": min(main_score) if main_score else 0,
                      "max": max(main_score) if main_score else 0,
                      "p50": pct(main_score, 50)},
            "x_centers": [t["x_center"] for t in main_trajs],
        },
        "all_trajectories": {
            "score": {"p50": pct(all_score, 50), "p90": pct(all_score, 90)},
        },
        "cluster_groups": {
            "count": len(groups),
            "size": {"min": min(group_sizes) if group_sizes else 0,
                     "max": max(group_sizes) if group_sizes else 0,
                     "p50": pct(group_sizes, 50)},
        },
    }


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
    print(f"输出目录：{paths.COLUMN_RECOVER_DIR}")
    run_batch(pairs, process_image, starmap=True)


if __name__ == "__main__":
    main()
