# -*- coding: utf-8 -*-
"""阶段4：表格线候选识别：polyline -> RDP -> 几何特征 -> 三级分类 -> DBSCAN聚类 -> 结构复核

借鉴 TSRFormer / RobusTabNet 的分割-合并思想，但当前只做"候选识别"，
不进入结构合并或移除阶段。所有线都保留，仅打标签 {high, suspect, noise}。

输入（只读）：
  - data/raw_images/*.JPG（彩色扫描件，用作原图副本与叠加背景）
  - data/LingDong-skeleton-tracing处理/坐标数据/*.json（polyline 坐标）
输出（data/表格线候选识别处理/，每图五件套）：
  - 原图/             原始扫描件 PNG 无损副本，绝不绘制（用于人工对照）
  - 叠加可视化图/     原图副本上绘制候选线（主要人工核验图）
  - 纯线条可视化图/   白底仅绘制 polyline（方便单独观察算法判断）
  - 坐标数据/         每图一个 JSON（所有线 + 标签/特征/分数）
  - 特征统计/         每图一个 JSON（各类数量与分布，便于调参）

原图与所有可视化图宽高完全相同、坐标系一致，可逐像素对照。
输入目录全程只读，绝不原地保存或覆盖。

用法：
    python src/table/table_line_detect.py
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from collections import Counter
from sklearn.cluster import DBSCAN

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths
from src.core.batch import run_batch

# ---- 输出目录（五件套）----
OUTPUT_DIRS = (
    paths.CANDIDATE_ORIG_DIR,
    paths.CANDIDATE_OVERLAY_DIR,
    paths.CANDIDATE_PURE_DIR,
    paths.CANDIDATE_COORD_DIR,
    paths.CANDIDATE_STATS_DIR,
)

# ---- 算法参数 ----
RDP_EPS = 2.0           # RDP 简化阈值（px），消除骨架锯齿，保真主方向
MIN_LEN_HIGH = 100.0    # 高可能候选最小长度（px）；探查：L>=100 时纯度 99%+
MIN_LEN_SUSPECT = 50.0  # 可疑最小长度（px）；L<50 基本是文字笔画（94~95%）
DIR_TOL = 5.0           # 方向容差（度），水平±5° 或垂直 90±5°
DIRECT_MAX = 1.1        # 直达比上限，框线应接近 1.0；文字笔画 med 1.05 p90 1.5
DEFLECT_MAX = 5.0       # 局部偏折角上限（度），长框线 98%+ <5°
W_OVER_H_HORIZ = 3.0    # 水平线包围盒宽高比下限
W_OVER_H_VERT = 0.33    # 垂直线包围盒宽高比上限
DBSCAN_EPS = 15.0       # 线带聚类半径（px），同一表格线不同段 y/x 应接近
DBSCAN_MIN = 2          # 聚类最小样本数


# ============================================================
# 阶段A：RDP 简化
# ============================================================
def rdp(points, eps):
    """Ramer-Douglas-Peucker 折线简化。

    points: (N,2) float64 数组。返回简化后的 (M,2) 数组。
    自写以避免引入 rdp 包（numpy 2.x 兼容性更稳妥）。
    """
    if len(points) < 3:
        return points.copy()

    # 递归：找垂直距离最远的点，超过 eps 则保留并递归两侧
    start, end = points[0], points[-1]
    seg = end - start
    seg_len_sq = float(seg @ seg)
    if seg_len_sq < 1e-12:
        # 退化（首尾重合），保留首个点
        return points[:1].copy()
    # 点到直线的垂直距离 = |cross(seg, p-start)| / |seg|
    diff = points - start
    cross = diff[:, 0] * seg[1] - diff[:, 1] * seg[0]
    dist = np.abs(cross) / np.sqrt(seg_len_sq)
    idx = int(np.argmax(dist))
    max_d = float(dist[idx])

    if max_d < eps:
        return np.array([start, end])
    # 递归两侧
    left = rdp(points[: idx + 1], eps)
    right = rdp(points[idx:], eps)
    # 拼接，去掉重复的连接点
    return np.vstack([left[:-1], right])


# ============================================================
# 阶段A：几何特征
# ============================================================
def poly_length(pts):
    """折线累计长度。"""
    if len(pts) < 2:
        return 0.0
    d = np.diff(pts, axis=0)
    return float(np.hypot(d[:, 0], d[:, 1]).sum())


def compute_features(poly_rdp):
    """计算 6 维几何特征。

    返回 dict: length, direct_ratio, angle, w, h, w_over_h, bbox, midx, midy
    """
    if len(poly_rdp) < 2:
        return None
    length = poly_length(poly_rdp)
    start, end = poly_rdp[0], poly_rdp[-1]
    chord = float(np.hypot(end[0] - start[0], end[1] - start[1]))
    direct_ratio = length / chord if chord > 1e-6 else 1.0
    # 首尾连线角度，折算到 0~180°
    ang = np.degrees(np.arctan2(end[1] - start[1], end[0] - start[0])) % 180.0
    x0, y0 = poly_rdp[:, 0].min(), poly_rdp[:, 1].min()
    x1, y1 = poly_rdp[:, 0].max(), poly_rdp[:, 1].max()
    w = float(x1 - x0)
    h = float(y1 - y0)
    w_over_h = (w / h) if h > 1e-6 else float("inf")
    return {
        "length": length,
        "direct_ratio": direct_ratio,
        "angle": float(ang),
        "w": w,
        "h": h,
        "w_over_h": float(w_over_h),
        "bbox": [float(x0), float(y0), float(x1), float(y1)],
        "midx": float((x0 + x1) / 2.0),
        "midy": float((y0 + y1) / 2.0),
    }


# ============================================================
# 阶段A：PCA 主方向
# ============================================================
def pca_angle(points):
    """用 SVD 求点集第一主成分方向角（0~180°）。

    对中心化后的点集做 SVD，右奇异向量第一列即主方向。
    """
    if len(points) < 2:
        return 0.0
    c = points - points.mean(axis=0)
    # cov = c^T c，特征向量即右奇异向量
    _, _, vh = np.linalg.svd(c, full_matrices=False)
    v = vh[0]
    ang = np.degrees(np.arctan2(v[1], v[0])) % 180.0
    return float(ang)


def deflection_std(rdp_pts):
    """局部方向稳定性：相邻段夹角的标准差（度）。

    段数<=2 记 0（无中间转折）。段数>2 时计算相邻段方向角差，
    取与 180° 的最小夹角（忽略 0/180 等价的翻转）。
    """
    n = len(rdp_pts)
    if n < 3:
        return 0.0
    d = np.diff(rdp_pts, axis=0)  # (n-1, 2)
    angs = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
    # 相邻段方向差，折叠到 [0,90]（线段方向无朝向，>90 等价于 180-差）
    diffs = np.abs(np.diff(angs))
    diffs = np.minimum(diffs, 180.0 - diffs)
    return float(diffs.std())


# ============================================================
# 阶段A：主方向判定
# ============================================================
def angle_diff(a, b):
    """两个角度（0~180°）的最小差，考虑 0/180 等价。返回度。"""
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def classify_direction(feat, pca_ang):
    """判定主方向：horizontal / vertical / none。

    PCA 方向 + 包围盒宽高比双重确认，避免短笔画碰巧水平/垂直。
    """
    wo = feat["w_over_h"]
    if angle_diff(pca_ang, 0.0) <= DIR_TOL and wo > W_OVER_H_HORIZ:
        return "horizontal"
    if angle_diff(pca_ang, 90.0) <= DIR_TOL and wo < W_OVER_H_VERT:
        return "vertical"
    return "none"


# ============================================================
# 阶段B：三级初分（宽松策略，保留所有线）
# ============================================================
def initial_label(feat, direction):
    """根据几何特征与方向做三级初分。

    high:    长线 + 方向正 + 直达 + 稳定
    suspect: 中等长度或方向正但有某项不达标
    noise:   短且方向不正
    """
    L = feat["length"]
    dr = feat["direct_ratio"]
    if L >= MIN_LEN_HIGH and direction != "none" and dr <= DIRECT_MAX:
        return "high"
    # suspect：方向正但长度中等；或长线但直达比偏高（可能被骨架串连的文字行）；
    #          或超长但方向不定（可能是斜向合并线，留待结构复核）
    if (MIN_LEN_SUSPECT <= L < MIN_LEN_HIGH and direction != "none") or \
       (L >= MIN_LEN_HIGH and dr > DIRECT_MAX) or \
       (L >= 150.0 and direction == "none"):
        return "suspect"
    return "noise"


# ============================================================
# 阶段C：DBSCAN 聚类找线带
# ============================================================
def cluster_bands(candidates, axis):
    """对候选线按指定轴（'y' 横线带 / 'x' 纵线带）做一维 DBSCAN 聚类。

    candidates: list of dict（含 midx/midy）。
    返回 band_id 列表（-1 表示噪声/孤立点，即无同向邻居）。
    """
    if not candidates:
        return []
    key = "midy" if axis == "y" else "midx"
    X = np.array([[c[key]] for c in candidates], dtype=np.float64)
    labels = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN).fit_predict(X)
    return labels.tolist()


# ============================================================
# 阶段C：线段相交（numpy 叉积法）
# ============================================================
def segments_intersect(p1, p2, p3, p4):
    """判断线段 p1p2 与 p3p4 是否相交（含端点）。"""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return False


def count_crossings(line, perpendicular_lines):
    """统计 line（首尾段近似）与垂直方向候选线的交点数。

    用每条候选的首尾段近似（RDP 后长框线接近直线，误差可接受），
    避免对每条 polyline 全段比较的高成本。
    """
    p1 = (line["bbox"][0], line["bbox"][1])
    p2 = (line["bbox"][2], line["bbox"][3])
    cnt = 0
    for ol in perpendicular_lines:
        p3 = (ol["bbox"][0], ol["bbox"][1])
        p4 = (ol["bbox"][2], ol["bbox"][3])
        if segments_intersect(p1, p2, p3, p4):
            cnt += 1
    return cnt


# ============================================================
# 阶段C：结构支持打分
# ============================================================
def compute_struct_scores(lines, img_w, img_h):
    """对 high+suspect 候选计算结构支持分并复核标签。

    band_support:   同一线带的候选数（归一化）
    span_coverage:  候选长度 / 主跨度（横线取 img_w，纵线取 img_h）
    crossing_count: 与垂直方向候选的交点数
    struct_score:   上述三项加权
    final_score:    geo_score*0.6 + struct_score*0.4
    复核：struct_score 高的 suspect -> high；孤立无支持的 high -> suspect
    """
    cand_idx = [i for i, l in enumerate(lines) if l["label"] in ("high", "suspect")]
    if not cand_idx:
        return
    cands = [lines[i] for i in cand_idx]

    # 分别对横/纵候选聚类
    h_idx = [k for k, c in enumerate(cands) if c["direction"] == "horizontal"]
    v_idx = [k for k, c in enumerate(cands) if c["direction"] == "vertical"]

    h_band = cluster_bands([cands[k] for k in h_idx], "y") if h_idx else []
    v_band = cluster_bands([cands[k] for k in v_idx], "x") if v_idx else []

    # 统计每个 band 的成员数
    h_count = Counter(h_band)
    v_count = Counter(v_band)

    # 主跨度：所有横候选长度的 p75，作为 span_coverage 的分母
    h_lens = [cands[k]["length"] for k in h_idx]
    v_lens = [cands[k]["length"] for k in v_idx]
    h_span = float(np.percentile(h_lens, 75)) if h_lens else float(img_w)
    v_span = float(np.percentile(v_lens, 75)) if v_lens else float(img_h)

    # 垂直方向候选集合（用于求交）
    h_cands = [cands[k] for k in h_idx]
    v_cands = [cands[k] for k in v_idx]

    for k, c in enumerate(cands):
        if c["direction"] == "horizontal":
            bi = h_idx.index(k)
            band_id = int(h_band[bi])
            band_size = h_count.get(band_id, 0)
            span = h_span
            cross = count_crossings(c, v_cands)
        elif c["direction"] == "vertical":
            bi = v_idx.index(k)
            band_id = int(v_band[bi])
            band_size = v_count.get(band_id, 0)
            span = v_span
            cross = count_crossings(c, h_cands)
        else:
            band_id, band_size, span, cross = -1, 0, 1.0, 0

        band_support = min(band_size / 5.0, 1.0)  # 5条同向即满分
        span_coverage = min(c["length"] / span, 1.0) if span > 0 else 0.0
        crossing_support = min(cross / 3.0, 1.0)  # 3个交点即满分
        struct_score = band_support * 0.4 + span_coverage * 0.3 + crossing_support * 0.3
        c["band_id"] = band_id
        c["band_size"] = int(band_size)
        c["crossing_count"] = int(cross)
        c["span_coverage"] = round(float(span_coverage), 4)
        c["struct_score"] = round(float(struct_score), 4)
        # geo_score：由几何特征离线化（length/direct/deflect 归一）
        geo = min(c["length"] / 300.0, 1.0) * 0.5 \
              + max(0, 1 - abs(c["direct_ratio"] - 1.0)) * 0.3 \
              + max(0, 1 - c["deflection"] / DEFLECT_MAX) * 0.2
        c["geo_score"] = round(float(geo), 4)
        c["final_score"] = round(float(geo * 0.6 + struct_score * 0.4), 4)

    # 复核：struct 强者 suspect->high；孤立无支持的 high->suspect
    for c in cands:
        if c["label"] == "suspect" and c["struct_score"] >= 0.5:
            c["label"] = "high"
        elif c["label"] == "high" and c["struct_score"] < 0.1 and c["band_size"] <= 1:
            c["label"] = "suspect"


# ============================================================
# 可视化
# ============================================================
# 颜色 (BGR)：high-横向红/纵向蓝，suspect-黄/橙，noise-浅灰
COLORS = {
    ("high", "horizontal"): (0, 0, 255),
    ("high", "vertical"): (255, 0, 0),
    ("high", "none"): (0, 0, 200),
    ("suspect", "horizontal"): (0, 200, 255),
    ("suspect", "vertical"): (255, 150, 0),
    ("suspect", "none"): (0, 180, 180),
    ("noise", "horizontal"): (200, 200, 200),
    ("noise", "vertical"): (200, 200, 200),
    ("noise", "none"): (220, 220, 220),
}


def line_color(label, direction):
    return COLORS.get((label, direction), (180, 180, 180))


def draw_polyline(img, pts, color, thickness):
    """在 img 上绘制一条 polyline。"""
    n = len(pts)
    if n < 2:
        if n == 1:
            cv2.circle(img, (int(pts[0][0]), int(pts[0][1])), 1, color, -1)
        return
    # 性能：长线用 polylines，短线用循环（避免 numpy 转换开销）
    if n >= 8:
        cv2.polylines(img, [np.array(pts, dtype=np.int32)], False, color, thickness, cv2.LINE_8)
    else:
        for i in range(n - 1):
            cv2.line(img,
                     (int(pts[i][0]), int(pts[i][1])),
                     (int(pts[i + 1][0]), int(pts[i + 1][1])),
                     color, thickness, cv2.LINE_8)


def draw_overlay(orig_bgr, lines):
    """在原图副本上叠加绘制候选线。返回新图像，不修改输入。"""
    viz = orig_bgr.copy()
    # noise 用最细线，suspect 中等，high 最粗
    for l in lines:
        c = line_color(l["label"], l["direction"])
        t = 1 if l["label"] == "noise" else (2 if l["label"] == "suspect" else 3)
        draw_polyline(viz, l["points"], c, t)
    return viz


def draw_pure(w, h, lines):
    """白底仅绘制 polyline。"""
    viz = np.full((h, w, 3), 255, dtype=np.uint8)
    for l in lines:
        c = line_color(l["label"], l["direction"])
        t = 1 if l["label"] == "noise" else (2 if l["label"] == "suspect" else 3)
        draw_polyline(viz, l["points"], c, t)
    return viz


# ============================================================
# 单图处理
# ============================================================
def process_image(jpg_path, json_path):
    """处理一张图：读取 polyline + 原图 -> 特征 -> 分类 -> 聚类复核 -> 输出五件套。

    返回 (stem, ok, info)。
    """
    stem = jpg_path.stem
    try:
        paths.ensure_dirs(*OUTPUT_DIRS)

        # ---- 读取 polyline 坐标（只读）----
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        img_w = int(data["width"])
        img_h = int(data["height"])
        polylines = data["polylines"]

        # ---- 读取原图（彩色，只读；cv2 默认应用 EXIF，与坐标系一致）----
        orig = cv2.imread(str(jpg_path), cv2.IMREAD_COLOR)
        if orig is None:
            return stem, False, "无法读取原图 JPG"
        if orig.shape[0] != img_h or orig.shape[1] != img_w:
            return stem, False, f"原图尺寸 {orig.shape} 与 JSON {img_w}x{img_h} 不一致"

        # ---- 阶段A：RDP + 特征 + 方向 ----
        lines = []
        for pid, poly in enumerate(polylines):
            pts = np.array(poly, dtype=np.float64)
            if len(pts) < 2:
                continue
            simp = rdp(pts, RDP_EPS)
            feat = compute_features(simp)
            if feat is None:
                continue
            pca_ang = pca_angle(simp)
            deflect = deflection_std(simp)
            direction = classify_direction(feat, pca_ang)
            label = initial_label(feat, direction)
            lines.append({
                "id": pid,
                "label": label,
                "direction": direction,
                "length": round(feat["length"], 2),
                "direct_ratio": round(feat["direct_ratio"], 4),
                "angle": round(feat["angle"], 2),
                "pca_angle": round(pca_ang, 2),
                "deflection": round(deflect, 2),
                "w_over_h": round(feat["w_over_h"], 4),
                "bbox": [round(v, 1) for v in feat["bbox"]],
                "midx": feat["midx"],
                "midy": feat["midy"],
                "band_id": -1,
                "band_size": 0,
                "crossing_count": 0,
                "span_coverage": 0.0,
                "geo_score": 0.0,
                "struct_score": 0.0,
                "final_score": 0.0,
                "points": simp.astype(int).tolist(),
            })

        # ---- 阶段C：DBSCAN 聚类 + 结构复核 ----
        compute_struct_scores(lines, img_w, img_h)

        # ---- 汇总统计 ----
        label_cnt = Counter(l["label"] for l in lines)
        dir_cnt = Counter(l["direction"] for l in lines)
        summary = {
            "high": label_cnt.get("high", 0),
            "suspect": label_cnt.get("suspect", 0),
            "noise": label_cnt.get("noise", 0),
            "total": len(lines),
            "horizontal": dir_cnt.get("horizontal", 0),
            "vertical": dir_cnt.get("vertical", 0),
        }

        # ---- 输出1：原图副本（绝不绘制，PNG 无损）----
        cv2.imwrite(str(paths.CANDIDATE_ORIG_DIR / f"{stem}.png"), orig,
                    [cv2.IMWRITE_PNG_COMPRESSION, 0])

        # ---- 输出2：叠加可视化图（在副本上绘制）----
        viz_overlay = draw_overlay(orig, lines)
        cv2.imwrite(str(paths.CANDIDATE_OVERLAY_DIR / f"{stem}.png"), viz_overlay,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出3：纯线条可视化图（白底）----
        viz_pure = draw_pure(img_w, img_h, lines)
        cv2.imwrite(str(paths.CANDIDATE_PURE_DIR / f"{stem}.png"), viz_pure,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # ---- 输出4：坐标数据 JSON ----
        coord_out = {
            "image": f"{stem}.png",
            "source_jpg": jpg_path.name,
            "width": img_w,
            "height": img_h,
            "summary": summary,
            "lines": lines,
        }
        with open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(coord_out, f, ensure_ascii=False)

        # ---- 输出5：特征统计 JSON ----
        stats = build_stats(lines, summary, img_w, img_h)
        with open(paths.CANDIDATE_STATS_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        return stem, True, (
            f"H={summary['high']} S={summary['suspect']} N={summary['noise']} "
            f"horz={summary['horizontal']} vert={summary['vertical']}"
        )
    except Exception as e:
        return stem, False, f"{type(e).__name__}: {e}"


def build_stats(lines, summary, img_w, img_h):
    """构造特征统计 JSON，便于调参。"""
    def pct(vals, p):
        return round(float(np.percentile(vals, p)), 2) if vals else 0.0

    high = [l for l in lines if l["label"] == "high"]
    suspect = [l for l in lines if l["label"] == "suspect"]
    noise = [l for l in lines if l["label"] == "noise"]

    def len_stats(subset):
        vals = [l["length"] for l in subset]
        return {"count": len(vals), "min": min(vals) if vals else 0,
                "max": max(vals) if vals else 0,
                "p50": pct(vals, 50), "p90": pct(vals, 90)}

    return {
        "image_size": {"width": img_w, "height": img_h},
        "summary": summary,
        "length_by_label": {
            "high": len_stats(high),
            "suspect": len_stats(suspect),
            "noise": len_stats(noise),
        },
        "direction_by_label": {
            "high_horz": sum(1 for l in high if l["direction"] == "horizontal"),
            "high_vert": sum(1 for l in high if l["direction"] == "vertical"),
            "suspect_horz": sum(1 for l in suspect if l["direction"] == "horizontal"),
            "suspect_vert": sum(1 for l in suspect if l["direction"] == "vertical"),
        },
        "bands": {
            "horizontal_bands": len(set(l["band_id"] for l in high + suspect
                                        if l["direction"] == "horizontal" and l["band_id"] >= 0)),
            "vertical_bands": len(set(l["band_id"] for l in high + suspect
                                      if l["direction"] == "vertical" and l["band_id"] >= 0)),
        },
    }


# ============================================================
# 主入口
# ============================================================
def main():
    paths.ensure_dirs(*OUTPUT_DIRS)
    pairs = paths.pair_jpg_json(paths.SKELETON_COORD_DIR)
    if not pairs:
        print(f"未找到配对的 JPG/JSON。RAW_DIR={paths.RAW_DIR} "
              f"JSON_DIR={paths.SKELETON_COORD_DIR}")
        return
    print(f"输出目录：{paths.CANDIDATE_DIR}")
    # 大图(3000x20000)阶段4 单图峰值内存高,8 并行在 16GB 机器 MemoryError
    # (2026-10-25 实测 1024/1035 失败),压到 4 并行
    run_batch(pairs, process_image, starmap=True, max_workers=4)


if __name__ == "__main__":
    main()
