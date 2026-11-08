# -*- coding: utf-8 -*-
"""阶段4：主分隔线拟合（纵向 + 横向），含 noise 再召回。

从阶段4 表格线候选识别产物（data/表格线候选识别处理/坐标数据/*.json）中：
  Step 0  noise 再召回：把"伪 noise、真框线"的候选段从 label==noise 升级为 high；
  Step 1  主分隔线拟合：把 high 候选段按方向聚成有限条主分隔线，
          每条用沿主轴等距采样 + 成员 points 中位偏移生成的折线轨迹表示
          （允许倾斜/弯曲，绝不强制笔直），并把原始候选段回挂 column_id。

设计原则（与 AGENTS.md 阶段04 约束一致）：
  - 不重新检测原图像素级的线；
  - 不把 band_id 直接当列；不全局 midx/midy 硬聚类；
  - 不强制拟合成笔直直线；
  - 不因拟合失败删除任何原始候选；
  - 不处理行 / 单元格 / OCR；
  - suspect 段原样保留、不参与拟合、不改 label、column_id=null。

坐标：points 为 [[x, y], ...] 整数像素，图像坐标系（原点左上，x 右、y 下）。

纯函数（recall_noise / fit_main_lines）与 I/O（process_image / main）解耦，便于 pytest。
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import cv2
from sklearn.cluster import MeanShift

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch


# ============================================================
# 参数
# ============================================================
# ---- Step 0 noise 再召回 ----
RECALL_DIRS = ("vertical", "horizontal")   # 仅方向明确者参与召回
RECALL_MIN_LEN = 40.0                      # 长度下限（参考 high p50≈85）
RECALL_MIN_DIR_RATIO = 0.7                 # 几何纯正度下限
RECALL_TOL = 12.0                          # 贴近 high 轨迹的容差带（px），参考 band_size/相邻间距
RECALL_MIN_SIGNALS = 2                     # 命中判据数阈值（方向+长度已占2，另需位置/结构其一）

# ---- Step 1 主分隔线拟合 ----
X_BIN = 40.0                              # 垂直方向(x/midx 或 y/midy)容差（px）：区分相邻平行列线，容错单线漂移
Y_GAP = 300.0                             # 主轴(y/x)方向真断口阈值（px）：>此值切分独立轨道（数据断口 p75≈209）
TRAJ_STEP = 20.0                           # 轨迹沿主轴采样步长（px）
TILT_MAX = 0.15                           # 段自身斜率上限（纵向|dx/dy|/横向|dy/dx|）；超限段方向标错或过度倾斜，剔除出该轴轨道（真实列线 p99≈0.074）
TOP_BOTTOM_PAD = 0.0                       # 端点延伸（保持原段范围，不强行拉长）

# ---- Step 0b 碎片拼接（先拼后拟）----
# 竞争性匹配：每段找主轴方向上"顺序后继"中偏移最小的连接（自适应，不用固定阈值）。
# 固定阈值的问题：列间距不一（40-130px），手画线摆动幅度不一（20-60px），
# 单一阈值总会在某处误判——阈值太小漏连（摆动线断），太大误并（相邻列线连上）。
MERGE_MAIN_GAP = 60.0     # 主轴连接窗口（px）：后继段起点在 (本段终点, +窗口] 内才参与竞争
MERGE_PERP_CAP = 30.0     # 垂直偏移上限（px）：只拼同一条线，不拼相邻平行线。
                            # 依据：同线相邻段 midx 差 p75<=20px，但含真实弯折（1015 外框左线
                            # x 151->177.5 差 26.5px），故取 30px 覆盖；相邻列间距 40~130px，
                            # 30px 不会跨列；允许整体一致倾斜 ~16.7°@gap100px。


# ============================================================
# Step 0b：碎片拼接（端点连通 + 共线判断 + 并查集）
# ============================================================
class _UnionFind:
    """极简并查集（路径压缩）。"""
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _seg_main_axis(s, direction):
    """段的主轴范围与垂直偏移：纵向 (y0,y1,midx)，横向 (x0,x1,midy)。"""
    bb = s.get("bbox") or [0, 0, 0, 0]
    if direction == "vertical":
        return float(bb[1]), float(bb[3]), float(s.get("midx", 0.0))
    return float(bb[0]), float(bb[2]), float(s.get("midy", 0.0))


def _line_self_slope(ln, direction):
    """段自身沿主轴方向的斜率（纵向 |dx/dy|，横向 |dy/dx|）；用于漂移补偿与斜率一致性。"""
    p = ln.get("points") or []
    if len(p) < 2:
        return 0.0
    dx = abs(float(p[-1][0]) - float(p[0][0]))
    dy = abs(float(p[-1][1]) - float(p[0][1]))
    if direction == "vertical":
        return dx / dy if dy != 0 else 0.0
    return dy / dx if dx != 0 else 0.0


def _merge_direction(segs, direction):
    """对一个方向的所有段做竞争性匹配拼接，返回合并线列表。

    竞争性匹配（自适应，无固定垂直阈值）：
      ① 按主轴起点排序；
      ② 每段找"顺序后继"——起点落在 (本段终点, 本段终点+窗口] 内的段，
         其中垂直偏移最小者为其候选后继；
      ③ 冲突裁决：若候选后继已被更近的前驱占用，则偏移更小者胜出，
         败者失去该后继（其链条在此断开，保守处理）；
      ④ 用并查集按最终匹配结果连通。
    这样"列间距不同、摆动幅度不同"都由数据本身决定，不依赖单一阈值。
    """
    if not segs:
        return []
    n = len(segs)
    segs = sorted(segs, key=lambda s: _seg_main_axis(s, direction)[0])
    idx_of = {s["id"]: i for i, s in enumerate(segs)}

    # 阶段1：竞争性匹配，每段至多一个后继
    succ_of = {}   # 前驱 i -> 后继 j
    owner = {}     # 后继 j -> 前驱 i
    for i, a in enumerate(segs):
        a0, a1, a_off = _seg_main_axis(a, direction)
        slope_a = _line_self_slope(a, direction)
        best_j, best_off = None, None
        for j in range(i + 1, n):
            b0, b1, b_off = _seg_main_axis(segs[j], direction)
            gap = b0 - a1
            if gap > MERGE_MAIN_GAP:
                break  # 已按起点排序，后续 gap 更大
            if gap < 0:
                continue  # 主轴重叠/反向，不算顺序后继（平行线段不应连接）
            # 漂移补偿：把 a 段自身倾斜外推到断口处再比较偏移（消除整体倾斜偏差）
            pred_off = a_off + slope_a * gap
            # 斜率一致性：连接处偏移不超过 a/b 段自身斜率外推 + 固定容差
            slope_b = _line_self_slope(segs[j], direction)
            raw_off = abs(b_off - a_off)
            if raw_off > max(MERGE_PERP_CAP, (slope_a + slope_b) * gap + 5.0):
                continue
            off = abs(b_off - pred_off)
            if best_off is None or off < best_off:
                best_off, best_j = off, j
        if best_j is None:
            continue
        if best_j in owner:
            k = owner[best_j]
            kb0, _, kb_off = _seg_main_axis(segs[best_j], direction)
            k_off = abs(kb_off
                        - (_seg_main_axis(segs[k], direction)[2]
                           + _line_self_slope(segs[k], direction) * (kb0 - _seg_main_axis(segs[k], direction)[1])))
            if k_off <= best_off:
                continue  # 已有更近前驱，本段输掉竞争
            del succ_of[k]  # 前驱 k 失去后继（其链在此断开）
        owner[best_j] = i
        succ_of[i] = best_j

    # 阶段2：并查集连通
    uf = _UnionFind(n)
    for i, j in succ_of.items():
        uf.union(i, j)

    # 收集连通分量
    groups = {}
    for i, s in enumerate(segs):
        groups.setdefault(uf.find(i), []).append(s)
    merged = []
    for mid, members in enumerate(sorted(groups.values(), key=lambda g: -len(g))):
        ml = _build_merged_line(members, direction, mid)
        if ml:
            merged.append(ml)
    return merged


def _build_merged_line(members, direction, mid):
    """把一组连通碎片合并为一条逻辑线：轨迹 = 段拼接（复用 _stitch_segments）。

    段拼接沿主轴把同一条线的段直接连成折线（保留每段直度），仅在断口处线性桥接；
    取代分箱中位重采样——分箱中位在 bin 内混入平行碎片会使中位带偏产生折线伪影。
    """
    segs = [_as_seg(m) for m in members if m.get("points")]
    if not segs:
        return None
    traj = _stitch_segments(segs, direction)
    if not traj:
        return None
    bbs = [m.get("bbox") or [0, 0, 0, 0] for m in members]
    bbox = [min(b[0] for b in bbs), min(b[1] for b in bbs),
            max(b[2] for b in bbs), max(b[3] for b in bbs)]
    if direction == "vertical":
        y_span = bbox[3] - bbox[1]
        off = float(np.median([float(m.get("midx", 0.0)) for m in members]))
        top, bottom = [bbox[1], off], [bbox[3], off]
    else:
        y_span = bbox[2] - bbox[0]
        off = float(np.median([float(m.get("midy", 0.0)) for m in members]))
        top, bottom = [bbox[0], off], [bbox[2], off]
    return {
        "id": mid,
        "axis": direction,
        "trajectory": traj,
        "bbox": [float(v) for v in bbox],
        "member_ids": [m["id"] for m in members],
        "num_members": len(members),
        "y_span": float(y_span),
        "top": top,
        "bottom": bottom,
    }


def merge_fragments(lines):
    """碎片端点连通拼接：把属于同一条线的小碎片合并成长线。

    输入：所有候选段（high + noise，suspect 与 direction==none 不参与）。
    输出：合并线列表，每条含 trajectory/bbox/member_ids/axis 等。
    """
    usable = [l for l in lines
              if l.get("direction") in ("vertical", "horizontal")
              and l.get("label") != "suspect"]
    by_dir = {"vertical": [], "horizontal": []}
    for l in usable:
        by_dir[l["direction"]].append(l)
    merged = []
    for direction in ("vertical", "horizontal"):
        merged.extend(_merge_direction(by_dir[direction], direction))
    merged.sort(key=lambda ml: ml["axis"])
    return merged


# ============================================================
# 阶段04 新管线：列优先 + 双层框（先拼后拟）
#   步骤1 外层包裹框 -> 步骤2 mean-shift 列候选 -> 步骤3 全高覆盖验证 + RANSAC
#   -> 步骤4 内层表体外框 -> 步骤5 列计数/角色/归属 -> 步骤6 产物 + 分层叠加图
# ============================================================
COLUMN_MIN_LEN = 50.0              # 参与列聚类的垂直碎片长度下限（px）
SPAN_MIN_RATIO = 0.90              # 列线存在判据：y 跨度 >= 90% 表格高度（贯穿全高）
LANE_SPAN_MIN = 0.25             # 段拼接 lane 保留判据：轨迹 y 跨度 >= 25% 表格高度（过滤短碎片）
FRAME_SPAN_RATIO = 0.60            # 全宽/全长线判定：轨迹跨度 >= 60% 最大值
DOUBLE_LINE_GAP = 30.0             # 双线合并间距（px）：与选中边相距 <= 此值视为粗框双线
WRAP_EDGE_TOL = 10.0               # 候选与包裹框左/右缘的距离容差：视为框线不作列边界
INTERNAL_TOP_TOL = 20.0            # 候选起点低于包裹框顶此容差（px）→ 内部线
INTERNAL_BOT_TOL = 20.0            # 候选终点低于主体底线此容差（px）→ 内部线（子分隔线不达底线）
COVERAGE_GAP_MERGE = 5.0           # 覆盖统计中 y 区间合并间隙（px）
RANSAC_ITER = 100                  # RANSAC 迭代次数
RANSAC_TOL = 5.0                   # RANSAC 内点容差（px）
DE_CONTAM_THRESHOLD = 0.05         # 轨迹被 _clip_jump 删除比例超此值时启用簇内去污染（防误删）
DE_CONTAM_SPAN_RATIO = 0.90        # 去污染保留判据：成员/子组 y 跨度 >= 此比例表高才视为真实列线
SPLIT_MIN_GAP = 25.0               # 簇内峰分离：成员级 x_ref 排序后的最小空档（px）才算独立峰
SPLIT_MIN_COV = 0.30               # 簇内峰分离：分裂两侧子组各自 y 覆盖率（表高比例）的下限
SPLIT_LONG_RATIO = 0.30            # 峰分离：至少一侧子组须有单条 y 跨度 >= 此比例表高的长线成员
                                    # （区别真双线：1035 右区 2875 单长线 0.54H；1015 col7 两侧均为
                                    #  短碎片，最大单成员仅 0.12H，属单线弯折/平行碎片，不得分裂）

# ---- 段拼接（替代分箱中位，忠实第四步候选段）----
# 第四步 high 段几乎全是 2 点近垂直直线（direct_ratio p50=p90=1.0、自身 |dx| p90<=3px），
# 段中位 x 是稳定代表值。沿主轴排序连接段中位 x 即得忠实轨迹，仅在真实断口处线性桥接，
# 不再分箱重采样（分箱中位在 bin 内混入平行碎片会使中位带偏 → 折线/伪跳变，如 1035 col0
# 的 131px 漂移 / 145 跳变，而源段本身笔直）。
STITCH_STRAIGHT_TOL = 5.0    # 段自身 |dx|（纵向）<= 此值视为笔直，只发一个中位顶点
BRIDGE_MAX_GAP = 500.0       # 断口 y（主轴）gap 超过此值不桥接（同线真实断口 p75<=44，1015 col7 最大 457px）
BRIDGE_PERP_TOL = 100.0      # 桥接/lane 归并容差（px）：|off 差| 在此内视为同一条线（允许整体渐倾 + 局部弯折）
                             # 实测调参：tol=50 时 1035 过度拆分（18列/recall0.48）、1015 正常；
                             # tol=100 最优（1015 稳定 10列/0.877/0.915、1035 9列/0.776、1027 8列/0.863）；
                             # 过大（120-200）会让 1035 recall 略降（0.772）且不改善 1015。
SLOPE_TOL = 0.01             # 同一条渐倾线的段间斜率差容差（约0.57°），用于跨断口 run 归并
STITCH_MAX_LANES = 6         # 单簇最多输出几条候选线（安全闸，防病态簇爆炸）


def _traj_span_off(m):
    """合并线的轨迹跨度与垂直偏移：横向返回 (x-span, 中位 y)，纵向返回 (y-span, 中位 x)。"""
    t = np.array(m["trajectory"], dtype=np.float64)
    if m["axis"] == "horizontal":
        return float(t[:, 0].max() - t[:, 0].min()), float(np.median(t[:, 1]))
    return float(t[:, 1].max() - t[:, 1].min()), float(np.median(t[:, 0]))


def _y_union_coverage(members):
    """成员碎片 bbox y 区间并集长度（间隙 <= COVERAGE_GAP_MERGE 视为连续）。"""
    iv = sorted((float(m["bbox"][1]), float(m["bbox"][3])) for m in members)
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1] + COVERAGE_GAP_MERGE:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return sum(b - a for a, b in merged), merged


def detect_wrap_frame(merged):
    """步骤1：外层包裹框检测。

    顶/底：全宽横线（轨迹 x 跨度 >= 60% 最大跨度）按 y 分上下两半，
      各半取跨度最大者——包裹框顶/底比主体顶/底线更宽（1015：外框顶 y≈1038
      跨度 2637 > 主体顶 y≈729 跨度 2578），且四角与外缘竖线相接；
    左/右：全长竖线（轨迹 y 跨度 >= 60% 最大跨度）中 x 最小/最大者；
    双线合并：与选中边相距 <= DOUBLE_LINE_GAP 的近邻线并入，取位置中位。
    返回 frame 及四边所用合并线引用（_lines，供沿真实线绘制）。
    """
    h_stats = [_traj_span_off(m) + (m,) for m in merged if m["axis"] == "horizontal"]
    v_stats = [_traj_span_off(m) + (m,) for m in merged if m["axis"] == "vertical"]
    if not h_stats or not v_stats:
        return None
    h_max = max(s[0] for s in h_stats)
    v_max = max(s[0] for s in v_stats)
    h_full = [s for s in h_stats if s[0] >= FRAME_SPAN_RATIO * h_max]
    v_full = [s for s in v_stats if s[0] >= FRAME_SPAN_RATIO * v_max]
    if not h_full or not v_full:
        return None

    # 顶/底：上下两半各自跨度最大者（跨度相同取更靠外者）
    ordered = sorted(h_full, key=lambda s: s[1])
    half = (len(ordered) + 1) // 2
    top_group, bot_group = ordered[:half], ordered[half:]
    top_line = max(top_group, key=lambda s: (s[0], -s[1]))
    bot_line = max(bot_group, key=lambda s: (s[0], s[1]))

    def merge_near(stats, chosen_y, chosen_span):
        near = [s[1] for s in stats if abs(s[1] - chosen_y) <= DOUBLE_LINE_GAP
                and s[0] >= 0.5 * chosen_span]
        return float(np.median(near)) if near else chosen_y

    def pick_side(stats, key, pick):
        chosen = pick(stats, key=key)
        near = [s[1] for s in stats if abs(s[1] - chosen[1]) <= DOUBLE_LINE_GAP
                and s[0] >= 0.5 * chosen[0]]
        return float(np.median(near)) if near else chosen[1]

    left_line = min(v_full, key=lambda s: s[1])
    right_line = max(v_full, key=lambda s: s[1])
    top = merge_near(top_group, top_line[1], top_line[0])   # 顶线位置（双线合并后）
    bottom = merge_near(bot_group, bot_line[1], bot_line[0])
    left = pick_side(v_full, lambda s: s[1], min)        # x 最小 = 最靠左
    right = pick_side(v_full, lambda s: s[1], max)       # x 最大 = 最靠右
    frame = {"left": left, "top": top, "right": right, "bottom": bottom}
    frame["width"] = frame["right"] - frame["left"]
    frame["height"] = frame["bottom"] - frame["top"]
    frame["_lines"] = {
        "top": top_line[2], "bottom": bot_line[2],
        "left": left_line[2], "right": right_line[2],
    }
    frame["_h_full"] = [{"y": round(s[1], 1), "span": round(s[0], 1)} for s in h_full]
    frame["_v_full"] = [{"x": round(s[1], 1), "span": round(s[0], 1)} for s in v_full]
    return frame


def _global_slope(merged):
    """整表倾斜斜率：全高合并竖线轨迹斜率的中位数（表格整体旋转/手画倾斜）。

    各列线斜率近似一致（1015 约 0.003~0.004），用中位数作全局漂移率，
    把碎片 midx 校正到参考高度，使同一列线的碎片聚回同一位置。
    """
    slopes = []
    for m in merged:
        if m["axis"] != "vertical":
            continue
        t = np.array(m["trajectory"], dtype=np.float64)
        if len(t) >= 3 and t[:, 1].max() - t[:, 1].min() > 5000:
            slopes.append(float(np.polyfit(t[:, 1], t[:, 0], 1)[0]))
    return float(np.median(slopes)) if slopes else 0.0


def _drift_correct_x(fragments, a, ref_y):
    """漂移校正：把碎片 midx 投影到参考高度 ref_y 处的 x（消除整表倾斜）。

    x_ref = midx - a·(midy - ref_y)。同一列线的碎片（含倾斜漂移）校正后
    聚集到同一 x_ref，相邻列线（间距 60-90px）不再因漂移交叠而互相吞噬。
    """
    return np.array([float(l.get("midx", 0.0)) - a * (float(l.get("midy", 0.0)) - ref_y)
                     for l in fragments], dtype=np.float64)


def _column_bandwidth(merged, a=0.0, ref_y=0.0):
    """自适应 mean-shift 带宽：0.45 × 全高合并竖线漂移校正后间距中位数，截断到 [25,100]。

    带宽须匹配列间距（60-130px 不一），用合并后的全高竖线（同一列线的碎片已拼成
    一条，间距即列间距）在参考高度的位置估计。系数取 0.45：0.6× 在 1015 上
    会吞并左区 224/288 两线（漂移校正后仍相触 31px，带宽 48~52 之间合并），
    0.45×（≈39）稳定分离；用碎片级 midx 间距会被同线碎片间距（5-20px）主导。
    宽列（>500px）为表格内大列间隙，不参与中位数，避免拉高带宽导致左区列线合并。
    """
    v_stats = []
    for m in merged:
        if m["axis"] != "vertical":
            continue
        t = np.array(m["trajectory"], dtype=np.float64)
        if len(t) < 3:
            continue
        span = float(t[:, 1].max() - t[:, 1].min())
        off = float(np.median(t[:, 0]))
        mid = float(np.median(t[:, 1]))
        v_stats.append((span, off - a * (mid - ref_y)))
    if len(v_stats) < 3:
        return 50.0
    v_max = max(s[0] for s in v_stats)
    xs = sorted(s[1] for s in v_stats if s[0] >= FRAME_SPAN_RATIO * v_max)
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    if not gaps:
        return 50.0
    # 排除宽列间隙（>500px），否则单次大间隔会抬高带宽，导致左区邻列被错误合并
    small_gaps = [g for g in gaps if g < 500.0]
    use_gaps = small_gaps if small_gaps else gaps
    return float(np.clip(0.45 * float(np.median(use_gaps)), 25.0, 100.0))


def _split_cluster_peaks(members, a, ref_y, table_h, min_gap=SPLIT_MIN_GAP,
                         min_cov=SPLIT_MIN_COV):
    """簇内 1D 峰分离（oracle 方向一）：按成员级 x_ref 的显著空档分裂多峰簇。

    mean-shift 带宽有限，可能把两条真实列线并入同一簇（如 1035 右区
    x≈2875 的宽列内长线与 x≈2909~3004 的右 frame 线，间距约 29px），
    或把真线 + 平行碎片并入（wrap 左框碎片）。本函数对簇内成员按漂移校正
    x_ref 排序，在"成员级空档 >= min_gap 且两侧子组 y 覆盖率都 >= min_cov×表高"
    处分裂为独立子簇，每个子簇继续走 fit_column_lines/assign_columns。

    防误分裂关键：同一条弯曲列线的连续漂移（1015 col7 的 795/837 双峰）
    成员 x_ref 连续铺满、无显著空档；即使出现小空档（<25px）也不触发。
    1015 col10 内部线（x_ref≈2401）与邻线的 39.8px 空档虽然 >25px，但
    一侧子组覆盖率仅 0.01H，不满足 min_cov，故不会误分裂。
    1015 col7（x_ref≈801）在 26px 空档两侧覆盖率都 >=0.3H 但两侧均为短
    碎片（最大单成员仅 0.11H），属同一条列线的平行碎片/弯折，不满足
    min_long（至少一侧须有单条贯穿相当高度的长线）→ 不分裂。

    返回分裂后的子簇成员列表（每项为一个成员列表）。
    """
    if len(members) < 4:
        return [members]
    xrs = _drift_correct_x(members, a, ref_y)
    order = np.argsort(xrs)
    xs = xrs[order]
    mems = [members[i] for i in order]
    gaps = np.diff(xs)

    def _max_single_span(g):
        return max([float(m["bbox"][3]) - float(m["bbox"][1]) for m in g] or [0.0])

    # 找满足条件的最大空档（候选分裂点）：空档 >= min_gap 且两侧覆盖都达标，
    # 且至少一侧有单条贯穿相当高度的长线（真双线的信号，防单线弯折误分裂）
    best_i, best_gap = -1, 0.0
    for i, g in enumerate(gaps):
        if g < min_gap:
            continue
        left = mems[:i + 1]
        right = mems[i + 1:]
        cl, _ = _y_union_coverage(left)
        cr, _ = _y_union_coverage(right)
        long_ok = (_max_single_span(left) >= SPLIT_LONG_RATIO * table_h
                   or _max_single_span(right) >= SPLIT_LONG_RATIO * table_h)
        if cl >= min_cov * table_h and cr >= min_cov * table_h and long_ok \
                and g > best_gap:
            best_i, best_gap = i, g
    if best_i < 0:
        return [members]
    left = _split_cluster_peaks(mems[:best_i + 1], a, ref_y, table_h, min_gap, min_cov)
    right = _split_cluster_peaks(mems[best_i + 1:], a, ref_y, table_h, min_gap, min_cov)
    return left + right


def cluster_column_candidates(lines, wrap, merged):
    """步骤2：漂移校正 mean-shift 聚类列候选 + 贯穿全高验证。

    取方向=vertical 且非 suspect 的碎片（length >= COLUMN_MIN_LEN），
    先按整表倾斜把 midx 校正到参考高度（x_ref，消除漂移导致的分布交叠），
    再做 mean-shift（自适应带宽）。每簇 y 跨度（min~max）>= 90% 表高者
    为真实列线——覆盖率的密度语义会系统性歧视边缘淡线（1015 左区 x≈198~228
    与 x≈275~320 两条真线碎片少但贯穿全高），跨度判据衡量的是"线是否存在"。

    聚类后对每簇做成员级 1D 峰分离（_split_cluster_peaks）：mean-shift 带宽
    无法分离的近距双线（如 1035 右区 2875/2909）被拆成独立子簇，每子簇
    各自验证贯穿全高并作为独立列候选。
    """
    vsegs = [l for l in lines
             if l.get("direction") == "vertical" and l.get("label") != "suspect"
             and (l.get("length") or 0) >= COLUMN_MIN_LEN]
    if not vsegs:
        return []
    ref_y = (wrap["top"] + wrap["bottom"]) / 2.0 if wrap else 0.0
    a = _global_slope(merged)
    bw = _column_bandwidth(merged, a, ref_y)
    X = _drift_correct_x(vsegs, a, ref_y).reshape(-1, 1)
    labels = MeanShift(bandwidth=bw).fit_predict(X)
    table_h = max(float(wrap["height"]), 1.0) if wrap else 1.0
    cols = []
    for lab in sorted(set(labels)):
        members = [vsegs[i] for i, l in enumerate(labels) if l == lab]
        for sub in _split_cluster_peaks(members, a, ref_y, table_h):
            if len(sub) < 2:
                continue
            y_top = min(float(m["bbox"][1]) for m in sub)
            y_bot = max(float(m["bbox"][3]) for m in sub)
            span = y_bot - y_top
            if span < SPAN_MIN_RATIO * table_h:
                continue
            coverage, _ = _y_union_coverage(sub)
            x_ref = float(np.median([float(m["midx"]) - a * (float(m["midy"]) - ref_y)
                                     for m in sub]))
            cols.append({
                "x_ref": x_ref,          # 参考高度处的线位置（排序/列边界用）
                "x": float(np.median([m["midx"] for m in sub])),
                "span": float(span),
                "span_ratio": round(span / table_h, 4),
                "coverage": coverage,
                "coverage_ratio": round(coverage / table_h, 4),
                "y_top": y_top,
                "y_bot": y_bot,
                "num_members": len(sub),
                "member_ids": [m["id"] for m in sub],
                "_members": sub,
            })
    cols.sort(key=lambda c: c["x_ref"])
    return cols


def _fit_ransac_x_of_y(members):
    """RANSAC 拟合 x = a·y + b（纵向列线），返回 (a, b, inlier_frac, inliers)。

    随机两碎片各取一点求线；碎片内 >= 60% 点落在 RANSAC_TOL 内视为内点碎片，
    以内点碎片总长度计分（长度加权：长碎片更可信，避免短而多的杂线夺权）；
    取分最高模型后对全部内点碎片最小二乘精修。
    inliers 返回内点碎片列表，供轨迹分箱中位采样使用。
    """
    frags = []
    for m in members:
        pts = [(float(p[0]), float(p[1])) for p in m.get("points", [])]
        if len(pts) >= 2:
            frags.append((np.array(pts, dtype=np.float64),
                          float(m.get("length", 0.0) or 0.0)))
    if not frags or sum(ln for _, ln in frags) <= 0:
        return None
    rng = np.random.default_rng(42)
    best_score, best_inl_idx = -1.0, None
    for _ in range(RANSAC_ITER):
        i, j = rng.choice(len(frags), 2, replace=False)
        pi = frags[i][0][rng.integers(len(frags[i][0]))]
        pj = frags[j][0][rng.integers(len(frags[j][0]))]
        if abs(pi[1] - pj[1]) < 1e-6:
            continue
        a = (pi[0] - pj[0]) / (pi[1] - pj[1])
        b = pi[0] - a * pi[1]
        score, inl_idx = 0.0, []
        for k, (pts, ln) in enumerate(frags):
            resid = np.abs(pts[:, 0] - (a * pts[:, 1] + b))
            if resid[resid <= RANSAC_TOL].size >= 0.6 * len(pts):
                score += ln
                inl_idx.append(k)
        if score > best_score:
            best_score, best_inl_idx = score, inl_idx
    if not best_inl_idx:
        return None
    best_inl = [members[k] for k in best_inl_idx]
    P = np.vstack([np.array(m["points"], dtype=np.float64) for m in best_inl])
    a, b = np.polyfit(P[:, 1], P[:, 0], 1)
    n_pts_all = sum(len(m.get("points", [])) for m in members)
    inlier_frac = float(sum(len(m.get("points", [])) for m in best_inl)) / \
        float(n_pts_all) if n_pts_all else 0.0
    return float(a), float(b), round(inlier_frac, 4), best_inl


def _clip_jump(traj, threshold):
    """裁剪轨迹中跳变到异线的段（如并入簇的包裹框线在主体线结束后仍延伸）。

    真实列线相邻采样点（TRAJ_STEP=20px）间 x 漂移远小于 2px；相邻点 x 突跳
    超过阈值说明轨迹已离开主体线。保留最长的连续段（主体线）。
    阈值取 80px：手画线表头弯折可达 60-100px（如1035左区列线在 y≈800 处 x 偏移
    80-120px），若阈值过小（40px）会把真实弯折误判为跳变而截掉表头。
    异线跳变通常 >120px（相邻列间距 60-130），80px 仍可有效分离。
    """
    if len(traj) <= 2:
        return traj
    pts = np.array(traj, dtype=np.float64)
    dx = np.abs(np.diff(pts[:, 0]))
    segs, cur = [], [0]
    for i, d in enumerate(dx):
        if d > threshold:
            segs.append(cur)
            cur = [i + 1]
        else:
            cur.append(i + 1)
    segs.append(cur)
    seg = max(segs, key=len)
    return [traj[i] for i in seg]


def _seg_axis_bounds(ln, direction):
    """段的主轴范围 [a0,a1] 与垂直偏移（纵向 a=y/off=x，横向 a=x/off=y）。"""
    bb = ln.get("bbox") or [0, 0, 0, 0]
    if direction == "vertical":
        return float(bb[1]), float(bb[3]), float(ln.get("midx", (bb[0] + bb[2]) / 2.0))
    return float(bb[0]), float(bb[2]), float(ln.get("midy", (bb[1] + bb[3]) / 2.0))


def _lane_slope(segs, direction):
    """lane 内段沿主轴方向的一致斜率（纵向 off~y 线性拟合斜率，横向 off~x）。

    用于跨断口 run 归并：同一条渐倾列线的相邻 run 应共享一致斜率（允许弯曲
    但趋势一致）；斜率为 0 表示垂直（x 恒定），斜率越大右倾越明显。
    """
    if len(segs) < 2:
        return 0.0
    if direction == "vertical":
        ys = np.array([(s[0] + s[1]) / 2.0 for s in segs])
        xs = np.array([s[2] for s in segs])
    else:
        xs = np.array([(s[0] + s[1]) / 2.0 for s in segs])
        ys = np.array([s[2] for s in segs])
    if ys.std() < 1.0:
        return 0.0
    A = np.vstack([ys, np.ones(len(ys))]).T
    k, _ = np.linalg.lstsq(A, xs, rcond=None)[0]
    return float(k)


def _stitch_lines(members, direction):
    """段拼接生成所有候选列线轨迹（方案 A 核心）。

    取代分箱中位重采样：第四步段几乎全是 2 点近垂直直线，段中位 x 是稳定代表值。
    步骤：
      1. 取可用成员（非 suspect、方向匹配、含 points），按主轴 y 排序；
      2. 贪心分配到 lane：新段若偏移接近该 lane 的趋势外推值（允许整体一致倾斜，
         BRIDGE_PERP_TOL + 斜率*缺口），无论主轴是否重叠（y 重叠也允许）都并入该
         lane；只有偏移差明显超容差（真正平行双线）才开新 lane；
      3. 每个 lane 沿主轴逐段展开顶点（笔直段发两端点、弯折段发全部 points），
         断口处线性桥接（插点步长 TRAJ_STEP），端点闭合到成员 bbox 主轴范围；
      4. 返回所有 lane 轨迹（不再只取最长一条），并受 STITCH_MAX_LANES 安全闸限制。

    与上一版（只取最长轨道）的区别：跨断口的同一条渐倾列线（如 1035 右区
    x≈2542 的 9 段 run、1015 各列）会被正确缝合为一条贯穿全高的轨迹；真正平行
    双线（y 重叠但 x 明显不同）因偏移差超容差而被拆成独立 lane。
    """
    if not members:
        return []
    segs = []   # (a0, a1, off, 是否笔直, line_dict)
    for m in members:
        ln = m.get("line") if isinstance(m, dict) else None
        if not ln or ln.get("label") == "suspect":
            continue
        if ln.get("direction") != direction:
            continue
        pts = ln.get("points") or []
        if len(pts) < 2:
            continue
        a0, a1, off = _seg_axis_bounds(ln, direction)
        p0, p1 = pts[0], pts[-1]
        if direction == "vertical":
            straight = abs(float(p1[0]) - float(p0[0])) <= STITCH_STRAIGHT_TOL
        else:
            straight = abs(float(p1[1]) - float(p0[1])) <= STITCH_STRAIGHT_TOL
        segs.append((a0, a1, float(off), straight, ln))
    if not segs:
        return []
    segs = sorted(segs, key=lambda s: s[0])

    # ---- 贪心 lane 分配：偏移接近 lane 趋势（含 y 重叠）=> 同一条线 ----
    # 判据要点：不再用「主轴必须不重叠（gap>=0）才合并」的硬规则——同一条渐倾列线的
    # 相邻碎片段常有轻微 y 重叠（如 1015 x_ref=801 簇 off 771->879 连续渐变 108px），
    # 若一律把 y 重叠段拆成新 lane 会产生假列线（1015 10->13 列回归）。改为：无论 gap
    # 正负，只要新段偏移接近 lane 的趋势外推/中位（考虑 lane 渐倾斜率 + 缺口补偿）就
    # 并入同一 lane；只有偏移差明显超容差（真正平行双线）才开新 lane。
    lanes = []   # [{end, segs:[...]}]
    for s in segs:
        a0, a1, off, straight, ln = s
        best, best_score = None, None
        for li, lane in enumerate(lanes):
            gap = a0 - lane["end"]
            k = _lane_slope(lane["segs"], direction)
            last_off = lane["segs"][-1][2]
            # 趋势外推：gap>=0（主轴有缺口）用斜率外推；gap<0（y 重叠）不外推，
            # 直接用 lane 最近 off 参考，重叠量计入容差补偿。
            extrap = last_off + k * max(gap, 0.0)
            tol = BRIDGE_PERP_TOL + abs(k) * (max(gap, 0.0) + max(-gap, 0.0))
            med_off = float(np.median([x[2] for x in lane["segs"]]))
            score = min(abs(off - extrap), abs(off - med_off))
            if score <= tol and (best is None or score < best_score):
                best, best_score = li, score
        if best is None:
            lanes.append({"end": a1, "segs": [s]})
        else:
            lanes[best]["segs"].append(s)
            lanes[best]["end"] = max(lanes[best]["end"], a1)

    # 安全闸：限制单簇输出条数（按主轴跨度从大到小保留）
    lanes.sort(key=lambda lane: (max(s[1] for s in lane["segs"]) - min(s[0] for s in lane["segs"]),
                                 len(lane["segs"])), reverse=True)
    lanes = lanes[:STITCH_MAX_LANES]

    # ---- 每个 lane 生成轨迹 ----
    outs = []
    for lane in lanes:
        verts = []
        for a0, a1, off, straight, ln in lane["segs"]:
            if straight:
                verts.append((a0, off))
                verts.append((a1, off))
            else:
                for p in ln.get("points") or []:
                    if direction == "vertical":
                        verts.append((float(p[1]), float(p[0])))
                    else:
                        verts.append((float(p[0]), float(p[1])))
        if not verts:
            continue
        verts = sorted(verts, key=lambda v: v[0])
        uniq = []
        for v in verts:
            if uniq and abs(v[0] - uniq[-1][0]) < 1e-6 and abs(v[1] - uniq[-1][1]) < 1e-6:
                continue
            uniq.append(v)
        verts = uniq
        if len(verts) < 2:
            a, off = verts[0]
            outs.append([[round(float(off), 1), round(float(a), 1)]
                         if direction == "vertical"
                         else [round(float(a), 1), round(float(off), 1)]])
            continue

        traj = []
        for i in range(len(verts) - 1):
            a0, off0 = verts[i]
            a1, off1 = verts[i + 1]
            gap = a1 - a0
            if direction == "vertical":
                traj.append([round(float(off0), 1), round(float(a0), 1)])
            else:
                traj.append([round(float(a0), 1), round(float(off0), 1)])
            if gap > TRAJ_STEP + 1e-6:
                n = int(math.floor(gap / TRAJ_STEP))
                for kk in range(1, n + 1):
                    frac = kk * TRAJ_STEP / gap
                    a = a0 + frac * (a1 - a0)
                    off = off0 + frac * (off1 - off0)
                    if direction == "vertical":
                        traj.append([round(float(off), 1), round(float(a), 1)])
                    else:
                        traj.append([round(float(a), 1), round(float(off), 1)])
        a_last, off_last = verts[-1]
        if direction == "vertical":
            traj.append([round(float(off_last), 1), round(float(a_last), 1)])
        else:
            traj.append([round(float(a_last), 1), round(float(off_last), 1)])

        # 端点闭合到该 lane 段 bbox 主轴范围（防止轨迹缩水）
        a_min = min(s[0] for s in lane["segs"])
        a_max = max(s[1] for s in lane["segs"])
        if direction == "vertical":
            if traj[0][1] > a_min + 1e-6:
                traj[0] = [traj[0][0], round(float(a_min), 1)]
            if traj[-1][1] < a_max - 1e-6:
                traj[-1] = [traj[-1][0], round(float(a_max), 1)]
        else:
            if traj[0][0] > a_min + 1e-6:
                traj[0] = [round(float(a_min), 1), traj[0][1]]
            if traj[-1][0] < a_max - 1e-6:
                traj[-1] = [round(float(a_max), 1), traj[-1][1]]
        outs.append(traj)
    return outs


def _stitch_segments(members, direction):
    """段拼接生成单条轨迹（最长候选线），供 _build_merged_line / 旧调用方使用。

    完整段拼接见 _stitch_lines（返回所有候选线）；本函数取其主轴跨度最长的一条，
    以兼容需要单条合并线轨迹（wrap/merge 线）的调用方。
    """
    lines = _stitch_lines(members, direction)
    if not lines:
        return []
    return max(lines, key=lambda tr: (tr[-1][1] - tr[0][1] if direction == "vertical"
                                      else tr[-1][0] - tr[0][0], len(tr)))


def _on_line_fragments(members, a, b, tol_mult=3.0):
    """返回与拟合线一致的碎片（>=60% 点落在 tol_mult×RANSAC_TOL 内）。

    簇可能并入平行线/内部笔画（如左缘 198-228/260-265 线、岩层图内部竖线），
    它们距主体列线 30-100px；按拟合线带过滤后只保留主体列线自己的碎片，
    轨迹才能贴合主体线全段（含表头弯折），不被平行线在缺口处带偏。
    """
    band = tol_mult * RANSAC_TOL
    out = []
    for m in members:
        pts = np.array(m.get("points", []), dtype=np.float64)
        if len(pts) < 2:
            continue
        resid = np.abs(pts[:, 0] - (a * pts[:, 1] + b))
        if resid[resid <= band].size >= 0.6 * len(pts):
            out.append(m)
    return out


def _members_outband_remove(members, a, ref_y, bw, table_h,
                            hist_bin=5.0, peak_ratio=0.15):
    """去污染（步骤1）：剔除簇内漂移校正 x_ref 主峰带外的短碎片。

    手画列线自身可有倾斜/局部漂移（如1015 col7 的 795/837 双峰），其带外
    碎片仍贯穿全高（span>=0.9H），必须保留；真正的污染（如1035 col0 的
    wrap 左框碎片 x_ref≈225-305）带外且不贯穿全高，剔除后轨迹不再被
    平行线在缺口处带偏。
    """
    if len(members) < 6:
        return members
    xrs = _drift_correct_x(members, a, ref_y)
    lo = float(np.floor(xrs.min() / hist_bin) * hist_bin)
    hi = float(np.ceil(xrs.max() / hist_bin) * hist_bin)
    nb = max(1, int(round((hi - lo) / hist_bin)) or 1)
    counts, edges = np.histogram(xrs, bins=nb, range=(lo, hi))
    imax = int(np.argmax(counts))
    peak = counts[imax]
    band_lo, band_hi = imax, imax
    while band_lo > 0 and counts[band_lo - 1] >= peak_ratio * peak:
        band_lo -= 1
    while band_hi < nb - 1 and counts[band_hi + 1] >= peak_ratio * peak:
        band_hi += 1
    blo, bhi = float(edges[band_lo]), float(edges[band_hi + 1])
    keep = []
    for m, x in zip(members, xrs):
        if blo <= x <= bhi:
            keep.append(m)
            continue
        # 带外：仅当不贯穿全高才剔除（贯穿的可能是同一条列线的倾斜段）
        ys = [float(p[1]) for p in m.get("points", [])]
        if ys and (max(ys) - min(ys)) >= 0.9 * table_h:
            keep.append(m)
    return keep if keep else members


def _members_span_filter(members, a, ref_y, bw, table_h, split_frac=0.5):
    """去污染（步骤2）：簇内二次 mean-shift，仅保留贯穿全高的子组。

    处理 x_ref 与主线几乎重合的污染（如1035 col4 上部 x≈644 碎片：漂移校正后
    与主线 x_ref 重叠，主峰带无法分离），按成员 x_ref 二次聚类后，把不贯穿
    全高的子组（污染/内部短线）剔除，只保留贯穿全高的真实列线。
    """
    if len(members) < 6:
        return members
    xrs = _drift_correct_x(members, a, ref_y)
    if float(np.ptp(xrs)) <= bw:
        return members
    lab = MeanShift(bandwidth=split_frac * bw).fit_predict(xrs.reshape(-1, 1))
    groups = []
    for u in sorted(set(lab)):
        g = [members[i] for i, l in enumerate(lab) if l == u]
        ys = [float(m["bbox"][1]) for m in g] + [float(m["bbox"][3]) for m in g]
        span = max(ys) - min(ys)
        groups.append((g, span))
    full = [g for g, s in groups if s >= 0.9 * table_h]
    if not full:
        return members
    keep = []
    for g in full:
        keep.extend(g)
    seen, res = set(), []
    for m in keep:
        if id(m) not in seen:
            seen.add(id(m))
            res.append(m)
    return res if res else members


def fit_column_lines(cols, jump_threshold=None, a=0.0, ref_y=0.0, bw=None,
                     table_h=1.0, decontaminate=False):
    """步骤3：对每条列候选拟合列线。

    RANSAC（长度加权）给出直线参数 (a,b)（JSON 记录用，仅作参考，不用于过滤）；
    轨迹 = 段拼接（沿主轴把同一条线的段直接连成折线，保留每段直度，仅在断口处
    线性桥接），不再用分箱中位重采样、不再用 _clip_jump 裁剪。

    重要修正：不再用 on_line 过滤后再采样——手画列线在表头常有 60-120px 弯折
    （如1035左区列线 y≈800 处），RANSAC 直线会把弯折段判为外点而丢弃，
    导致轨迹顶端被截掉 3000-8000px，进而 internal 误判为全 internal。
    段拼接直接对全部成员取段中位 x 连接，保留真实弯折，且不被平行线带偏。

    每个簇可能含多条候选线（跨断口的渐倾线/真正平行双线），_stitch_lines 返回
    所有 lane，每条 lane 生成一条 column line 记录（role=None 交给 assign_columns）。
    旧的 decontaminate（_members_outband_remove/_members_span_filter）是分箱中位
    时代的补丁：段拼接天然抗平行线，预删成员反而会误删真实弯折段（实测 outband
    误删 1035 左 frame 22 个真实段），因此默认关闭。
    """
    out = []
    if jump_threshold is None:
        jump_threshold = 4.0 * TRAJ_STEP  # 80px，见 _clip_jump 说明
    for i, c in enumerate(cols):
        fit = _fit_ransac_x_of_y(c["_members"])
        if fit is None:
            fa, fb, inlier_frac = 0.0, 0.0, 0.0
        else:
            fa, fb, inlier_frac, _ = fit
        members = c["_members"]
        if decontaminate and bw is not None and bw > 0:
            # 先看全成员采样是否被 _clip_jump 大量误删（混入平行线的信号）
            probe = _sample_trajectory([{"line": m} for m in members], "vertical")
            probe_clip = _clip_jump(probe, jump_threshold)
            if probe and len(probe_clip) <= (1.0 - DE_CONTAM_THRESHOLD) * len(probe):
                members = _members_outband_remove(members, a, ref_y, bw, table_h)
                members = _members_span_filter(members, a, ref_y, bw, table_h)
        # 轨迹 = 段拼接（忠实第四步段，保留每段直度，仅断口桥接）；
        # RANSAC 仅提供拟合参数记录，不参与轨迹几何；不再用 _clip_jump 裁剪
        trajs = _stitch_lines([{"line": m} for m in members], "vertical")
        # 过滤短碎片 lane：只保留主轴跨度 >= LANE_SPAN_MIN * 表高的候选线
        # （簇内短平行碎片/单点段会开出多余 lane，旧版只取最长轨道天然滤掉；
        #   方案 A 返回所有 lane 后需显式滤除，防止 assign_columns 误计数）
        span_keep = []
        for traj in trajs:
            if not traj:
                continue
            span = (traj[-1][1] - traj[0][1]) if traj else 0.0
            if table_h > 0 and span >= LANE_SPAN_MIN * table_h:
                span_keep.append(traj)
        trajs = span_keep
        for traj in trajs:
            if not traj:
                continue
            out.append({
                "id": i,
                "axis": "vertical",
                "role": None,  # assign_columns 填 wrap/internal/frame/separator
                "x_ref": c["x_ref"],
                "x": round(float(np.median([t[0] for t in traj])), 1),
                "fit": {"a": round(fa, 6), "b": round(fb, 2), "inlier_frac": inlier_frac},
                "trajectory": traj,
                "coverage": c["coverage"],
                "coverage_ratio": c["coverage_ratio"],
                "span_ratio": c["span_ratio"],
                "y_top": traj[0][1],
                "y_bot": traj[-1][1],
                "y_cluster_top": c["y_top"],   # 簇成员整体范围（用于内框/内部判定）
                "y_cluster_bot": c["y_bot"],
                "num_members": len(members),
                "member_ids": [m["id"] for m in members],
                "inlier_ids": [m["id"] for m in c["_members"]],
            })
    return out


def detect_body_frame(merged, col_lines):
    """步骤4：内层表体外框 = 最左/最右列线（表格主体自身的外框）夹住的全宽横线。

    左右 = col_lines[0] / col_lines[-1] 的 x_ref（"最左侧和最右侧的列"）；
    顶/底 = 全宽横线中，位于列线簇范围起始/终止 y 中位数外侧最近者
    （个别列线断头不干扰，用簇范围而非轨迹范围）。
    """
    if len(col_lines) < 2:
        return None
    c_top = float(np.median([c["y_cluster_top"] for c in col_lines]))
    c_bot = float(np.median([c["y_cluster_bot"] for c in col_lines]))
    h_stats = [_traj_span_off(m) + (m,) for m in merged if m["axis"] == "horizontal"]
    if not h_stats:
        return None
    h_max = max(s[0] for s in h_stats)
    h_full = [s for s in h_stats if s[0] >= FRAME_SPAN_RATIO * h_max]
    above = [s for s in h_full if s[1] <= c_top + 50.0]
    below = [s for s in h_full if s[1] >= c_bot - 50.0]
    if not above or not below:
        return None
    top_line = max(above, key=lambda s: s[1])     # 列线顶部上方最近的全宽横线
    bot_line = min(below, key=lambda s: s[1])     # 列线底部下方最近的全宽横线
    frame = {
        "left": col_lines[0]["x_ref"], "top": float(top_line[1]),
        "right": col_lines[-1]["x_ref"], "bottom": float(bot_line[1]),
    }
    frame["width"] = frame["right"] - frame["left"]
    frame["height"] = frame["bottom"] - frame["top"]
    # 框线引用：顶/底为全宽横线本身；左/右即最左/最右列线的轨迹
    frame["_lines"] = {
        "top": top_line[2], "bottom": bot_line[2],
        "left": col_lines[0], "right": col_lines[-1],
    }
    return frame


def _body_bottom_estimate(merged, candidates):
    """内框底线估计：全宽横线中，位于候选列线 y_bot 中位数下方最近者。

    供 internal 角色判定使用（内部线终点低于主体底线 INTERNAL_BOT_TOL 以上，
    如 1015 水曲线大列的内部线 x≈2400 止于 y≈17708，边界线都到达底线）。
    """
    if not candidates:
        return None
    c_bot = float(np.median([c["y_bot"] for c in candidates]))
    h_stats = [_traj_span_off(m) + (m,) for m in merged if m["axis"] == "horizontal"]
    if not h_stats:
        return None
    h_max = max(s[0] for s in h_stats)
    h_full = [s for s in h_stats if s[0] >= FRAME_SPAN_RATIO * h_max]
    below = [s for s in h_full if s[1] >= c_bot - 50.0]
    return min(below, key=lambda s: s[1])[1] if below else None


def assign_columns(lines, col_lines, wrap=None, a=0.0, ref_y=0.0, body_bottom=None):
    """步骤5：列线角色（wrap/internal/frame/separator）与列计数。

    - wrap：与包裹框左/右缘重合的候选（|x_ref - 框缘| <= WRAP_EDGE_TOL）——
      包裹框线，不作列边界（1015：右缘 x≈2940 属外框）；
    - internal：起点低于包裹框顶（y_top >= wrap.top - INTERNAL_TOP_TOL）
      或终点低于主体底线（y_bot <= body_bottom - INTERNAL_BOT_TOL）的候选——
      大列内部竖线（1015：水曲线大列 [2323,2864] 内的 x≈2400 止于 y≈17708），
      保留标注不作边界；
    - 其余：最左/最右两条 = 内框 frame，中间 = 分隔线 separator；
      列区域 = 全部 frame+separator 边界划分（n = 边界数 - 1）。

    返回 (out_lines, n_columns, bounds)：
      out_lines：原段副本，新增 column_id（漂移校正后落入的列区域号，
        未归属/suspect/方向不明 = null）；
      bounds：[(left, right), ...] 共 n_columns 个列区域（参考高度处位置）。
    """
    boundaries = []
    for c in col_lines:
        cx = c.get("x_ref", c["x"])
        if wrap is not None and (abs(cx - wrap["left"]) <= WRAP_EDGE_TOL
                                 or abs(cx - wrap["right"]) <= WRAP_EDGE_TOL):
            c["role"] = "wrap"
        elif ((wrap is not None and wrap["height"] > 0
               and c["y_cluster_top"] >= wrap["top"] + 0.06 * wrap["height"])
              or (body_bottom is not None
                  and c["y_cluster_bot"] <= body_bottom - INTERNAL_BOT_TOL)):
            c["role"] = "internal"
        else:
            boundaries.append(c)
    if len(boundaries) >= 2:
        boundaries[0]["role"] = "frame"
        boundaries[-1]["role"] = "frame"
        for c in boundaries[1:-1]:
            c["role"] = "separator"
    bounds = [(boundaries[i]["x_ref"], boundaries[i + 1]["x_ref"])
              for i in range(len(boundaries) - 1)]
    n_columns = len(bounds)

    def col_of(x_ref):
        for i, (lo, hi) in enumerate(bounds):
            if lo <= x_ref <= hi:
                return i
        return None

    out = []
    for ln in lines:
        o = dict(ln)
        o["column_id"] = None
        if (ln.get("label") != "suspect" and ln.get("direction") == "vertical"
                and n_columns > 0):
            x_ref = float(ln.get("midx", float("nan"))) \
                - a * (float(ln.get("midy", 0.0)) - ref_y)
            o["column_id"] = col_of(x_ref)
        out.append(o)
    return out, n_columns, bounds


# ============================================================
# Step 0：noise 再召回
# ============================================================
def _coord_of(line):
    """返回段的主轴坐标：纵向用 midx，横向用 midy；none 返回 None。"""
    if line.get("direction") == "vertical":
        return float(line.get("midx", 0.0))
    if line.get("direction") == "horizontal":
        return float(line.get("midy", 0.0))
    return None


def recall_noise(lines):
    """从 label==noise 的段中召回"伪 noise、真框线"者，升级为 high。

    返回 (new_lines, stats)：
      new_lines 为副本列表（被召回者 label 改为 "high"，其余原样，geometry 不动）；
      stats 为召回统计 dict，含 recall_count / remain_noise / misabsorb_none。
    """
    # 先把现有 high 段的主轴轨迹范围收集为容差带（按方向分组）
    bands = {"vertical": [], "horizontal": []}
    for ln in lines:
        if ln.get("label") == "high" and ln.get("direction") in bands:
            c = _coord_of(ln)
            if c is not None:
                bands[ln["direction"]].append(c)

    def near_high_trajectory(direction, coord):
        if coord is None:
            return False
        arr = bands.get(direction)
        if not arr:
            return False
        a = np.array(arr, dtype=np.float64)
        return bool(np.min(np.abs(a - coord)) <= RECALL_TOL)

    new_lines = []
    recall_count = 0
    misabsorb_none = 0
    for ln in lines:
        if ln.get("label") != "noise":
            new_lines.append(dict(ln))
            continue
        direction = ln.get("direction")
        if direction not in RECALL_DIRS:
            # 方向不明确（none）的 noise 保持，且不可被召回（误吸检查）
            new_lines.append(dict(ln))
            continue
        length = float(ln.get("length", 0.0) or 0.0)
        dr = float(ln.get("direct_ratio", 0.0) or 0.0)
        coord = _coord_of(ln)
        signals = 0
        # 方向明确（已隐含命中）
        signals += 1
        len_ok = length >= RECALL_MIN_LEN
        if len_ok:
            signals += 1
        dr_ok = dr >= RECALL_MIN_DIR_RATIO
        if dr_ok:
            signals += 1
        pos_ok = near_high_trajectory(direction, coord)
        if pos_ok:
            signals += 1
        cross = int(ln.get("crossing_count", 0) or 0)
        struct_ok = cross > 0
        if struct_ok:
            signals += 1
        # 方向+长度+几何纯正为底线，外加位置或结构其一
        if signals >= RECALL_MIN_SIGNALS and (len_ok and dr_ok) and (pos_ok or struct_ok):
            up = dict(ln)
            up["label"] = "high"
            new_lines.append(up)
            recall_count += 1
            if direction == "none":
                misabsorb_none += 1  # 理论上不会触发（前面已拦截）
        else:
            new_lines.append(dict(ln))

    remain_noise = sum(1 for ln in new_lines if ln.get("label") == "noise")
    stats = {
        "recall_count": recall_count,
        "remain_noise": remain_noise,
        "misabsorb_none": misabsorb_none,
    }
    return new_lines, stats


# ============================================================
# Step 1：主分隔线拟合
# ============================================================
def _as_seg(line):
    """把 line 转成聚类/拟合用的内部 seg（含派生 bbox 端点）。"""
    bbox = line.get("bbox") or [0, 0, 0, 0]
    x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]
    if line.get("direction") == "vertical":
        # 主轴 = y；垂直偏移 = x
        a0, a1 = y0, y1
        off = float(line.get("midx", (x0 + x1) / 2.0))
    else:
        # 横向：主轴 = x；垂直偏移 = y
        a0, a1 = x0, x1
        off = float(line.get("midy", (y0 + y1) / 2.0))
    return {
        "id": line["id"],
        "direction": line["direction"],
        "axis_coord": float((a0 + a1) / 2.0),   # 主轴中点
        "a0": float(min(a0, a1)),
        "a1": float(max(a0, a1)),
        "off": off,
        "line": line,
    }


def _split_by_gap(members, key, gap):
    """对成员按 key 排序后，相邻 key 间隙 > gap 即切分为多个子组（主轴连续性切分）。"""
    if len(members) <= 1:
        return [members]
    ordered = sorted(members, key=lambda s: s[key])
    subs = []
    cur = [ordered[0]]
    for prev, nxt in zip(ordered, ordered[1:]):
        if nxt[key] - prev[key] > gap:
            subs.append(cur)
            cur = [nxt]
        else:
            cur.append(nxt)
    subs.append(cur)
    return subs


def _cluster_columns(segs, direction):
    """二维语义聚类：把同方向 high 段聚成有限条主分隔线。

    一条主分隔线 = 在垂直方向(x/midx 或 y/midy)稳定、主轴方向(y/x)贯穿的轨道。
    做法：
      ① 按垂直坐标软分箱（X_BIN）隔离相邻平行列线（列间距通常 > X_BIN）；
      ② 箱内按主轴连续性（Y_GAP 断口）切分独立轨道；
      ③ 合并相邻箱（x 相差 1 个 bin）且在 y 上连续重叠的轨道，
         以容纳单条线沿主轴倾斜/弯曲（x 缓漂跨 bin 边界）而不被误拆。
    不把 band_id 当列、不全局硬聚类、不强制笔直；孤立段自成轨道（不丢段）。
    """
    if not segs:
        return []
    vkey = "off"        # 垂直坐标：midx(纵) / midy(横)
    akey = "axis_coord" # 主轴坐标：y(纵) / x(横)
    # ① 软分箱
    bins = {}
    for s in segs:
        b = int(round(s[vkey] / X_BIN))
        bins.setdefault(b, []).append(s)
    tracks = []
    for b in sorted(bins.keys()):
        subs = _split_by_gap(bins[b], akey, Y_GAP)
        for sub in subs:
            tracks.append(sub)
    # ③ 合并相邻箱且 y 连续重叠的轨道（处理弯曲跨箱）
    merged = _merge_adjacent_tracks(tracks, vkey, akey)
    # ④ 纠正过度合并：若轨道 x 跨度 > X_BIN，按 x 间隙二次拆分（分离被误合的平行列线）
    final = []
    for g in merged:
        xs = np.array([s[vkey] for s in g], dtype=np.float64)
        if xs.max() - xs.min() > X_BIN and len(g) > 1:
            final.extend(_split_by_gap(g, vkey, X_BIN / 2.0))
        else:
            final.append(g)
    final.sort(key=lambda g: float(np.median([s[vkey] for s in g])))
    return final


def _y_overlap(s1, s2, akey, tol=1.0):
    """两段在主轴方向是否连续重叠（间隙 <= tol 视为相接）。"""
    lo = max(s1["a0"], s2["a0"])
    hi = min(s1["a1"], s2["a1"])
    return hi - lo >= -tol


def _merge_adjacent_tracks(tracks, vkey, akey):
    """合并相邻箱（x 相差 <= X_BIN）且在 y 上连续重叠的轨道。"""
    if len(tracks) <= 1:
        return tracks
    # 按垂直坐标排序后贪心合并
    ordered = sorted(tracks, key=lambda g: (float(np.median([s[vkey] for s in g])),
                                             min(s["a0"] for s in g)))
    result = [ordered[0]]
    for nxt in ordered[1:]:
        cur = result[-1]
        cur_x = float(np.median([s[vkey] for s in cur]))
        nxt_x = float(np.median([s[vkey] for s in nxt]))
        # 仅在垂直坐标非常接近（<= X_BIN/2）时合并，区分"单线弯曲跨箱"与"两条相邻列线"
        x_close = abs(nxt_x - cur_x) <= X_BIN / 2.0
        y_cont = any(_y_overlap(m, n, akey) for m in cur for n in nxt)
        if x_close and y_cont:
            result[-1] = cur + nxt
        else:
            result.append(nxt)
    return result


def _seg_self_slope(seg, direction):
    """段自身斜率：纵向 |dx/dy|，横向 |dy/dx|。用于过滤方向标错/过度倾斜的段。"""
    p = np.array(seg["line"].get("points", []), dtype=np.float64)
    if len(p) < 2:
        return 0.0
    dx = p[-1][0] - p[0][0]
    dy = p[-1][1] - p[0][1]
    if direction == "vertical":
        return abs(dx / dy) if dy != 0 else 999.0
    return abs(dy / dx) if dx != 0 else 999.0


def _sample_trajectory(members, direction):
    """沿主轴等距分箱，取箱内成员 points 的垂直偏移中位，生成折线轨迹。

    [DEPRECATED] 列线轨迹已改用 _stitch_segments（段拼接，忠实第四步候选段，
    不产生分箱中位混入平行碎片的折线伪影）。本函数仅保留供旧基线 fit_main_lines
    （横向全宽框线等）与历史测试使用。

    这是 TSRFormer/DQ-DETR 用「沿主轴采样点序列」表示分隔线的思想在本
    数据上的落地：轨迹允许倾斜、允许弯曲，绝不强制成一根全局直线。
    主轴覆盖范围严格取成员真实范围（断口处用相邻已知箱线性插值，不强行拉长）。
    """
    if not members:
        return []
    pts = []
    for m in members:
        for p in m["line"].get("points", []):
            pts.append((float(p[0]), float(p[1])))
    if not pts:
        return []
    pts = np.array(pts, dtype=np.float64)

    if direction == "vertical":
        axis = pts[:, 1]   # 主轴 y
        offs = pts[:, 0]   # 垂直偏移 x
        a0, a1 = float(axis.min()), float(axis.max())
    else:
        axis = pts[:, 0]   # 主轴 x
        offs = pts[:, 1]   # 垂直偏移 y
        a0, a1 = float(axis.min()), float(axis.max())

    if a1 - a0 <= 1e-9:
        return [[round(float(offs[0]), 1), round(a0, 1)] if direction == "vertical"
                else [round(a0, 1), round(float(offs[0]), 1)]]

    # 主轴以 TRAJ_STEP 等距分箱，箱内取偏移中位（对离群段鲁棒）
    n_bins = max(2, int(math.ceil((a1 - a0) / TRAJ_STEP)))
    edges = np.linspace(a0, a1, n_bins + 1)
    # 逐箱统计：非空箱记自身中位偏移，空箱留待插值（不引入插值平滑）
    bin_has = [False] * n_bins
    bin_off = [0.0] * n_bins
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if i == n_bins - 1:
            hi = a1 + 1e-6  # 最后一箱闭口，纳入 a1
        mask = (axis >= lo) & (axis <= hi)
        if mask.any():
            bin_has[i] = True
            bin_off[i] = float(np.median(offs[mask]))
    n_nonempty = sum(bin_has)
    if n_nonempty == 0:
        return []
    if n_nonempty == 1:
        # 仅一个有效箱（整条极短或只在端点），用单点
        i0 = bin_has.index(True)
        center = a1 if i0 == n_bins - 1 else float(0.5 * (edges[i0] + edges[i0 + 1]))
        return [[round(bin_off[i0], 1), round(center, 1)] if direction == "vertical"
                else [round(center, 1), round(bin_off[i0], 1)]]

    # 轨迹轴坐标 = 各箱中心（最后一箱取 a1 闭合端点）
    full_axis = []
    for i in range(n_bins):
        center = float(0.5 * (edges[i] + edges[i + 1]))
        if i == n_bins - 1:
            center = a1
        full_axis.append(center)
    # 偏移：非空箱用自身中位（精确贴合，不插值平滑），空箱在相邻已知箱间线性插值
    ne_axis = [full_axis[i] for i in range(n_bins) if bin_has[i]]
    ne_off = [bin_off[i] for i in range(n_bins) if bin_has[i]]
    full_off = []
    for i in range(n_bins):
        if bin_has[i]:
            full_off.append(bin_off[i])
        else:
            full_off.append(float(np.interp(full_axis[i], ne_axis, ne_off)))

    traj = []
    for ax, off in zip(full_axis, full_off):
        if direction == "vertical":
            traj.append([round(float(off), 1), round(float(ax), 1)])
        else:
            traj.append([round(float(ax), 1), round(float(off), 1)])
    # 端点强制闭合到成员主轴真实范围
    if direction == "vertical":
        traj[0] = [round(float(full_off[0]), 1), round(a0, 1)]
        traj[-1] = [round(float(full_off[-1]), 1), round(a1, 1)]
    else:
        traj[0] = [round(a0, 1), round(float(full_off[0]), 1)]
        traj[-1] = [round(a1, 1), round(float(full_off[-1]), 1)]
    return traj


def _filter_by_tilt(segs, direction):
    """过滤自身斜率超限的段（方向标错或过度倾斜，不该并入该轴轨道）。"""
    return [s for s in segs if _seg_self_slope(s, direction) <= TILT_MAX]


def fit_main_lines(lines):
    """对 high 段拟合主分隔线，返回 (fitted_lines, column_id_map)。

    fitted_lines: list[dict]，每条含
      id, axis(vertical|horizontal), trajectory([[x,y],...]),
      member_line_ids, top, bottom, score。
    column_id_map: {line_id: column_id or None}，对所有输入 line 给出归属。
    """
    # 仅 high 参与；按方向分流；过滤自身斜率超限的段（方向标错/过度倾斜）
    segs_v = [_as_seg(l) for l in lines if l.get("label") == "high" and l.get("direction") == "vertical"]
    segs_h = [_as_seg(l) for l in lines if l.get("label") == "high" and l.get("direction") == "horizontal"]
    segs_v = _filter_by_tilt(segs_v, "vertical")
    segs_h = _filter_by_tilt(segs_h, "horizontal")

    fitted = []
    col_of_line = {}

    def build_axis(groups, direction):
        for g in groups:
            g_sorted = sorted(g, key=lambda s: s["axis_coord"])
            traj = _sample_trajectory(g_sorted, direction)
            if not traj:
                continue
            member_ids = [s["id"] for s in g_sorted]
            if direction == "vertical":
                a_vals = [p[1] for p in traj]
            else:
                a_vals = [p[0] for p in traj]
            top = (min(a_vals) if a_vals else 0.0, traj[0][0] if direction == "vertical" else traj[0][1])
            bottom = (max(a_vals) if a_vals else 0.0, traj[-1][0] if direction == "vertical" else traj[-1][1])
            span = (max(a_vals) - min(a_vals)) if a_vals else 0.0
            # score：覆盖率（span 越长越像主分隔线）× 支撑段数
            score = round(min(span / 1000.0, 1.0) * 0.6 + min(len(member_ids) / 10.0, 1.0) * 0.4, 4)
            cid = len(fitted)
            fitted.append({
                "id": cid,
                "axis": direction,
                "trajectory": traj,
                "member_line_ids": member_ids,
                "top": top,
                "bottom": bottom,
                "score": score,
            })
            for mid in member_ids:
                col_of_line[mid] = cid

    build_axis(_cluster_columns(segs_v, "vertical"), "vertical")
    build_axis(_cluster_columns(segs_h, "horizontal"), "horizontal")

    # 所有输入 line 的 column_id（未参与/非 high 为 None）
    for l in lines:
        col_of_line.setdefault(l["id"], None)

    return fitted, col_of_line


# ============================================================
# 验收指标（可计算，替代模糊"相似率"）
# ============================================================
def _raster_lines(trajectories, width, height, thickness=3):
    """把折线轨迹栅格化为二值掩码（白底线=1）。trajectories: list[list[[x,y]]]。"""
    mask = np.zeros((height, width), dtype=np.uint8)
    for traj in trajectories:
        for i in range(len(traj) - 1):
            p0 = (int(round(traj[i][0])), int(round(traj[i][1])))
            p1 = (int(round(traj[i + 1][0])), int(round(traj[i + 1][1])))
            cv2_line(mask, p0, p1, thickness)
    return mask


def cv2_line(mask, p0, p1, thickness):
    import cv2
    cv2.line(mask, p0, p1, 1, thickness=thickness)


def verify_acceptance(data, tol=8):
    """比较"基准(high 段 points 重画)"与"处理(fitted trajectory 重画)"。

    仅用 high（含 Step0 升级）段；剔除未召回 noise。返回指标 dict。
    """
    import cv2
    width, height = int(data["width"]), int(data["height"])
    lines = data["lines"]
    highs = [l for l in lines if l.get("label") == "high"]

    # 基准图：high 段 points
    base_trajs = [l["points"] for l in highs if l.get("points")]
    # 处理图：fitted trajectory（来自 fitted_lines）
    proc_trajs = [fl["trajectory"] for fl in data.get("fitted_lines", []) if fl.get("trajectory")]

    if not base_trajs:
        return {"recall": None, "precision": None, "iou": None, "note": "no high lines"}

    # 厚度取 7：扫描框线本身有 ~3-5px 宽度，栅格化略宽于理想 1px 数学线更能代表"真实线"
    base_mask = _raster_lines(base_trajs, width, height, thickness=7)
    proc_mask = _raster_lines(proc_trajs, width, height, thickness=7)

    base_pos = base_mask > 0
    proc_pos = proc_mask > 0
    if base_pos.sum() == 0:
        return {"recall": None, "precision": None, "iou": None, "note": "empty base"}
    # 容差带：以对方膨胀 tol 像素为"足够接近"判据，recall/precision 对称
    kernel = np.ones((2 * tol + 1, 2 * tol + 1), np.uint8)
    proc_dil = cv2.dilate(proc_mask, kernel) > 0   # 处理图容差带
    base_dil = cv2.dilate(base_mask, kernel) > 0   # 基准图容差带
    # 召回率：基准像素是否落在处理图容差带内（真实框线被某条主分隔线足够覆盖）
    if base_pos.sum() == 0:
        recall = 0.0
    else:
        recall = float((base_pos & proc_dil).sum()) / float(base_pos.sum())
    # 精度：处理像素是否落在基准容差带内（处理线足够贴近真实框线）
    if proc_pos.sum() == 0:
        precision = 0.0
    else:
        precision = float((proc_pos & base_dil).sum()) / float(proc_pos.sum())
    # IoU（严格像素重叠，仅作参考不卡死）
    union = (base_pos | proc_pos).sum()
    iou = float((base_pos & proc_pos).sum()) / float(union) if union > 0 else 0.0
    return {"recall": round(recall, 4), "precision": round(precision, 4),
            "iou": round(iou, 4), "note": ""}


# ============================================================
# 可视化（叠加图 / 纯线条图）
# ============================================================
def draw_polyline_pts(img, pts, color, thickness):
    """把折线点序列画到 img 上（np.int32 顶点，LINE_8）。"""
    if len(pts) < 2:
        return
    arr = np.array(pts, dtype=np.int32)
    cv2.polylines(img, [arr], False, color, thickness, cv2.LINE_8)


# 分层叠加图配色：外层包裹框=红，内层表体外框=橙，列分隔线=青蓝，内部线=品红
COLOR_WRAP = (0, 0, 255)
COLOR_BODY = (0, 165, 255)
COLOR_SEP = (255, 255, 0)
COLOR_INTERNAL = (255, 0, 255)


def _draw_frame_edges(viz, frame, color):
    """沿框的真实线轨迹绘制四边（消除轴对齐矩形与漂移线的幻影偏差）。"""
    if not frame:
        return
    lines = frame.get("_lines") or {}
    for side in ("top", "bottom", "left", "right"):
        ln = lines.get(side)
        if ln is not None and ln.get("trajectory"):
            draw_polyline_pts(viz, ln["trajectory"], color, 2)
        else:  # 兜底：无轨迹引用时画轴对齐边
            if side == "top":
                cv2.line(viz, (int(round(frame["left"])), int(round(frame["top"]))),
                         (int(round(frame["right"])), int(round(frame["top"]))), color, 2)
            elif side == "bottom":
                cv2.line(viz, (int(round(frame["left"])), int(round(frame["bottom"]))),
                         (int(round(frame["right"])), int(round(frame["bottom"]))), color, 2)
            elif side == "left":
                cv2.line(viz, (int(round(frame["left"])), int(round(frame["top"]))),
                         (int(round(frame["left"])), int(round(frame["bottom"]))), color, 2)
            else:
                cv2.line(viz, (int(round(frame["right"])), int(round(frame["top"]))),
                         (int(round(frame["right"])), int(round(frame["bottom"]))), color, 2)


_ROLE_COLOR = {"frame": COLOR_BODY, "separator": COLOR_SEP,
               "internal": COLOR_INTERNAL, "wrap": COLOR_WRAP}


def draw_column_overlay(orig, wrap, body, col_lines):
    """步骤6：在原图副本上绘制分层叠加图（框沿真实线，列线按角色着色）。"""
    viz = orig.copy()
    _draw_frame_edges(viz, wrap, COLOR_WRAP)
    _draw_frame_edges(viz, body, COLOR_BODY)
    for c in col_lines:
        color = _ROLE_COLOR.get(c.get("role"), COLOR_SEP)
        draw_polyline_pts(viz, c["trajectory"], color, 3)
    return viz


def draw_column_pure(w, h, wrap, body, col_lines):
    """步骤6：白底仅绘制框与列线（配色同叠加图）。"""
    viz = np.full((h, w, 3), 255, dtype=np.uint8)
    _draw_frame_edges(viz, wrap, COLOR_WRAP)
    _draw_frame_edges(viz, body, COLOR_BODY)
    for c in col_lines:
        color = _ROLE_COLOR.get(c.get("role"), COLOR_SEP)
        draw_polyline_pts(viz, c["trajectory"], color, 2)
    return viz


def verify_columns(data, tol=8):
    """步骤6 验收：列线栅格化与成员/线自身碎片像素对比（对称容差带 recall/precision）。

    recall  vs 全簇成员：诚实反映簇内多线（刻意并入的平行线/内部笔画不参与匹配）；
    recall_line vs 线自身碎片（inlier_ids）：拟合质量——轨迹应覆盖其代表的那条线。
    主验收判据：n_columns（1015 目标 10）、coverage_ratio>=70%（全高覆盖）。
    """
    import cv2
    width, height = int(data["width"]), int(data["height"])
    col_lines = data.get("column_lines", [])
    if not col_lines:
        return {"note": "no column lines"}
    kernel = np.ones((2 * tol + 1, 2 * tol + 1), np.uint8)
    by_id = {ln["id"]: ln for ln in data["lines"]}
    per_line = []
    for c in col_lines:
        base_all = _raster_lines([[p for p in by_id[mid]["points"]]
                                  for mid in c.get("member_ids", []) if mid in by_id],
                                 width, height, thickness=3)
        base_line = _raster_lines([[p for p in by_id[mid]["points"]]
                                   for mid in c.get("inlier_ids", []) if mid in by_id],
                                  width, height, thickness=3)
        proc = _raster_lines([c["trajectory"]], width, height, thickness=3)
        pp = proc > 0
        proc_dil = cv2.dilate(proc, kernel) > 0
        rec = rec_line = prec = None
        bp = base_all > 0
        if bp.sum() and pp.sum():
            rec = float((bp & proc_dil).sum()) / float(bp.sum())
        bp_l = base_line > 0
        if bp_l.sum() and pp.sum():
            rec_line = float((bp_l & proc_dil).sum()) / float(bp_l.sum())
        if pp.sum() and (bp.sum() or bp_l.sum()):
            base_dil = cv2.dilate(base_all, kernel) > 0
            prec = float((pp & base_dil).sum()) / float(pp.sum())
        per_line.append({"id": c["id"], "recall": rec,
                         "recall_line": rec_line, "precision": prec})
    def mean_of(key):
        vals = [p[key] for p in per_line if p[key] is not None]
        return round(float(np.mean(vals)), 4) if vals else None
    return {
        "n_columns": data.get("n_columns"),
        "n_column_lines": len(col_lines),
        "coverage_min": round(min(c["coverage_ratio"] for c in col_lines), 4),
        "line_fit": per_line,
        "mean_recall": mean_of("recall"),
        "mean_recall_line": mean_of("recall_line"),
        "mean_precision": mean_of("precision"),
        "note": "",
    }


# ============================================================
# I/O
# ============================================================
def process_image(json_path):
    """处理单张图：读候选 JSON → 碎片拼接 → 外框 → 列聚类/拟合 → 产物。

    输入目录只读，产物写到 paths.COLUMN_FIT_COORD_DIR。
    返回 (stem, ok, info)。
    """
    json_path = Path(json_path)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        lines = data.get("lines", [])

        # 新管线：先拼后拟（列优先 + 双层框，漂移校正聚类）
        merged = merge_fragments(lines)
        wrap = detect_wrap_frame(merged)
        cols = cluster_column_candidates(lines, wrap, merged)
        a = _global_slope(merged)
        ref_y = (wrap["top"] + wrap["bottom"]) / 2.0 if wrap else 0.0
        bw = _column_bandwidth(merged, a, ref_y)
        table_h = max(float(wrap["height"]), 1.0) if wrap else 1.0
        col_lines = fit_column_lines(cols, a=a, ref_y=ref_y, bw=bw, table_h=table_h)
        body_bottom = _body_bottom_estimate(merged, cols)
        out_lines, n_columns, bounds = assign_columns(lines, col_lines, wrap, a, ref_y,
                                                      body_bottom)
        boundaries = [c for c in col_lines if c.get("role") in ("frame", "separator")]
        body = detect_body_frame(merged, boundaries)

        out = {
            "image": data.get("image"),
            "width": data.get("width"),
            "height": data.get("height"),
            "summary": data.get("summary"),
            "pipeline": "merge_fragments -> wrap_frame -> mean_shift_columns -> ransac -> body_frame",
            "frame": {"wrap": wrap, "body": body},
            "column_lines": col_lines,
            "columns": [{"index": i, "left": round(lo, 1), "right": round(hi, 1),
                         "width": round(hi - lo, 1)} for i, (lo, hi) in enumerate(bounds)],
            "n_columns": n_columns,
            "merged_lines": merged,
            "lines": out_lines,
        }
        out["acceptance"] = verify_columns(out)

        out_path = paths.COLUMN_FIT_COORD_DIR / f"{json_path.stem}_column_fit.json"
        paths.ensure_dirs(
            paths.COLUMN_FIT_COORD_DIR, paths.COLUMN_FIT_ORIG_DIR,
            paths.COLUMN_FIT_OVERLAY_DIR, paths.COLUMN_FIT_PURE_DIR,
        )
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)

        # ---- 可视化：原图副本 + 分层叠加图 + 纯线条图 ----
        w, h = int(data["width"]), int(data["height"])
        jpg = paths.RAW_DIR / f"{json_path.stem}.JPG"
        if not jpg.exists():
            jpg = paths.RAW_DIR / f"{json_path.stem}.jpg"
        if jpg.exists():
            orig = cv2.imread(str(jpg))
            if orig is not None:
                # 原图无损副本（绝不绘制）
                cv2.imwrite(str(paths.COLUMN_FIT_ORIG_DIR / f"{json_path.stem}.png"), orig)
                # 分层叠加图（外框红 / 内框橙 / 分隔线青蓝）
                overlay = draw_column_overlay(orig, wrap, body, col_lines)
                cv2.imwrite(str(paths.COLUMN_FIT_OVERLAY_DIR / f"{json_path.stem}.png"), overlay)
        # 纯线条图（白底，独立于原图）
        pure = draw_column_pure(w, h, wrap, body, col_lines)
        cv2.imwrite(str(paths.COLUMN_FIT_PURE_DIR / f"{json_path.stem}.png"), pure)

        info = {
            "n_columns": n_columns,
            "column_lines": len(col_lines),
            "merged_lines": len(merged),
            "frame": {"wrap": wrap, "body": body},
            "acceptance": out["acceptance"],
            "out": str(out_path),
        }
        return json_path.stem, True, info
    except Exception as e:  # 失败不中断批次
        return json_path.stem, False, {"error": str(e)}


def main():
    paths.ensure_dirs(
        paths.COLUMN_FIT_ORIG_DIR, paths.COLUMN_FIT_OVERLAY_DIR,
        paths.COLUMN_FIT_PURE_DIR, paths.COLUMN_FIT_COORD_DIR, paths.COLUMN_FIT_STATS_DIR,
    )
    pairs = [(jf,) for (_, jf) in paths.pair_jpg_json(paths.CANDIDATE_COORD_DIR)]
    if not pairs:
        print("未找到候选 JSON 配对，退出。")
        return
    results = run_batch(pairs, process_image, starmap=True)
    ok = sum(1 for _, s, _ in results if s)
    print(f"完成 {ok}/{len(results)} 张；产物目录：{paths.COLUMN_FIT_COORD_DIR}")


if __name__ == "__main__":
    main()
