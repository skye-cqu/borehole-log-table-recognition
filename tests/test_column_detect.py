# -*- coding: utf-8 -*-
"""列优先 + 双层框管线单测：外框检测 / mean-shift 列候选 / RANSAC / 内框 / 列计数。"""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.table.column_fit import (
    merge_fragments, detect_wrap_frame, _column_bandwidth,
    cluster_column_candidates, _fit_ransac_x_of_y, fit_column_lines, _clip_jump,
    detect_body_frame, assign_columns, _global_slope, _body_bottom_estimate,
)


def _mk(seg_id, direction, x0, y0, x1, y1, label="high", length=None):
    """构造一条线段 dict（方向明确、几何可控）。"""
    bbox = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
    if length is None:
        length = float(np.hypot(x1 - x0, y1 - y0))
    return {
        "id": seg_id,
        "label": label,
        "direction": direction,
        "length": length,
        "direct_ratio": 1.0,
        "angle": 90.0 if direction == "vertical" else 0.0,
        "pca_angle": 90.0 if direction == "vertical" else 0.0,
        "bbox": bbox,
        "midx": float((x0 + x1) / 2),
        "midy": float((y0 + y1) / 2),
        "points": [[int(x0), int(y0)], [int(x1), int(y1)]],
    }


def _mk_merged(axis, traj):
    """构造一条合并线 dict（detect_wrap_frame / _column_bandwidth 输入）。"""
    return {"axis": axis, "trajectory": [[float(p[0]), float(p[1])] for p in traj]}


def _mk_merged_v(x, y_max=1000.0, pts=3):
    """构造一条全高竖线合并线（至少 3 个轨迹点，供斜率/带宽估计）。"""
    return _mk_merged("vertical", [[x, y_max * i / (pts - 1)] for i in range(pts)])


def _mk_vline_cluster(x, y0, y1, n, start_id=0, spread=4):
    """构造一簇同列线碎片：midx 集中在 x±spread，y 覆盖 [y0,y1]。"""
    rng = np.random.default_rng(7)
    out = []
    for i in range(n):
        yy0 = y0 + (y1 - y0) * i / n
        yy1 = y0 + (y1 - y0) * (i + 1) / n
        xx = x + rng.uniform(-spread, spread)
        out.append(_mk(start_id + i, "vertical", xx, yy0, xx, yy1,
                       length=(yy1 - yy0) * 2.0))
    return out


# ---------------- 步骤1：外层包裹框 ----------------
def test_wrap_frame_outermost_lines():
    """全宽横线取 y 最小/最大，全长竖线取 x 最小/最大。"""
    merged = [
        _mk_merged("horizontal", [[50, 100], [700, 100]]),    # 顶
        _mk_merged("horizontal", [[50, 5000], [700, 5000]]),  # 底
        _mk_merged("horizontal", [[50, 500], [700, 500]]),    # 内部行线（宽度不足被滤）
        _mk_merged("vertical", [[50, 100], [50, 5000]]),      # 左
        _mk_merged("vertical", [[700, 100], [700, 5000]]),    # 右
        _mk_merged("vertical", [[400, 100], [400, 5000]]),    # 列线（非边缘）
    ]
    frame = detect_wrap_frame(merged)
    assert frame["left"] == 50.0 and frame["top"] == 100.0
    assert frame["right"] == 700.0 and frame["bottom"] == 5000.0


def test_wrap_frame_double_line_merged():
    """粗框双线（相距 <= DOUBLE_LINE_GAP）应并入，取位置中位。"""
    merged = [
        _mk_merged("horizontal", [[0, 100], [900, 100]]),
        _mk_merged("horizontal", [[0, 5000], [900, 5000]]),
        _mk_merged("vertical", [[50, 100], [50, 5000]]),
        _mk_merged("vertical", [[62, 100], [62, 5000]]),   # 左框双线，距 12px
        _mk_merged("vertical", [[900, 100], [900, 5000]]),
    ]
    frame = detect_wrap_frame(merged)
    assert frame["left"] == 56.0   # median(50, 62)


# ---------------- 步骤2：mean-shift 列候选 ----------------
def test_column_bandwidth_adaptive():
    """带宽 = 0.45 × 全高竖线间距中位数（截断到 [25,100]）。"""
    merged = [_mk_merged_v(x) for x in (100, 300, 500)]
    assert _column_bandwidth(merged) == pytest.approx(90.0, abs=0.1)  # 0.45*200=90


def test_cluster_columns_basic_and_span_filter():
    """贯穿全高的列线入选，跨度不足的短簇（图形笔画）被拒。

    存在判据为 y 跨度 >= 90% 表高（贯穿全高），覆盖率只作统计——
    边缘淡线碎片少但贯穿全高，用覆盖率的密度语义会漏掉。
    """
    lines = (_mk_vline_cluster(100, 0, 1000, 30)
             + _mk_vline_cluster(400, 0, 1000, 30)
             + _mk_vline_cluster(700, 0, 1000, 30)
             + _mk_vline_cluster(250, 300, 500, 5))  # 短簇：跨度 200 < 900
    merged = [_mk_merged("vertical", [[x, 0], [x, 1000]]) for x in (100, 400, 700)]
    wrap = {"top": 0.0, "bottom": 1000.0, "height": 1000.0}
    cols = cluster_column_candidates(lines, wrap, merged)
    xs = [round(c["x_ref"]) for c in cols]
    assert xs == [100, 400, 700]
    assert all(c["span_ratio"] >= 0.90 for c in cols)


def test_cluster_columns_excludes_suspect_and_none():
    """suspect 段与 direction==none 段不参与列候选。"""
    good = _mk_vline_cluster(100, 0, 1000, 30)
    suspect = _mk_vline_cluster(400, 0, 1000, 20, start_id=100)
    for ln in suspect:
        ln["label"] = "suspect"
    none_dir = _mk_vline_cluster(700, 0, 1000, 20, start_id=200)
    for ln in none_dir:
        ln["direction"] = "none"
    merged = [_mk_merged("vertical", [[100, 0], [100, 1000]])]
    wrap = {"top": 0.0, "bottom": 1000.0, "height": 1000.0}
    cols = cluster_column_candidates(good + suspect + none_dir, wrap, merged)
    assert [round(c["x_ref"]) for c in cols] == [100]


def test_drift_correction_separates_tilted_lines():
    """两条漂移线（斜率 0.004）碎片 midx 交叠，漂移校正后 x_ref 分离。"""
    a, ref_y, y_max = 0.004, 9000.0, 20000.0
    lines = []
    for i in range(20):
        y0, y1 = i * 1000, (i + 1) * 1000
        lines.append(_mk(i, "vertical", 200 + a * (y0 - ref_y) + 1, y0,
                         200 + a * (y1 - ref_y) + 1, y1))
        lines.append(_mk(100 + i, "vertical", 260 + a * (y0 - ref_y) - 1, y0,
                         260 + a * (y1 - ref_y) - 1, y1))
    merged = [_mk_merged("vertical", [[x + a * (0 - ref_y), 0],
                                      [x + a * (y_max / 2 - ref_y), y_max / 2],
                                      [x + a * (y_max - ref_y), y_max]])
              for x in (200, 260)]
    wrap = {"top": 0.0, "bottom": y_max, "height": y_max}
    cols = cluster_column_candidates(lines, wrap, merged)
    assert len(cols) == 2          # 两条漂移线分离（簇中心允许几 px 偏差）
    assert abs(cols[0]["x_ref"] - 200) <= 6
    assert abs(cols[1]["x_ref"] - 260) <= 6


# ---------------- 步骤3：RANSAC 拟合 ----------------
def test_ransac_tilted_line():
    """倾斜列线（x=0.004y+100）应被拟合出正确参数。"""
    rng = np.random.default_rng(3)
    members = []
    for i in range(20):
        y0, y1 = i * 100, i * 100 + 90
        x0 = 0.004 * y0 + 100 + rng.uniform(-1, 1)
        x1 = 0.004 * y1 + 100 + rng.uniform(-1, 1)
        members.append(_mk(i, "vertical", x0, y0, x1, y1))
    a, b, _, _ = _fit_ransac_x_of_y(members)
    assert a == pytest.approx(0.004, abs=0.0008)
    assert b == pytest.approx(100.0, abs=8.0)


def test_ransac_ignores_parallel_outliers():
    """平行的杂线碎片（体量小）不应带偏拟合（长度加权）。"""
    main = _mk_vline_cluster(300, 0, 2000, 20)          # 主列线 20 段
    junk = _mk_vline_cluster(250, 200, 1800, 5, start_id=100)  # 平行杂线 5 段
    a, b, inl, _ = _fit_ransac_x_of_y(main + junk)
    assert inl >= 0.7
    # 拟合线在中间高度应贴近主列线
    assert abs((a * 1000 + b) - 300) < 15


def test_fit_trajectory_follows_line():
    """轨迹为分箱中位折线，覆盖列线全段（含弯折），不被杂线带偏。"""
    members = (_mk_vline_cluster(200, 0, 1500, 25)
               + _mk_vline_cluster(150, 100, 1400, 5, start_id=100))
    cols = [{
        "x_ref": 200.0, "x": 200.0, "coverage": 1500.0, "coverage_ratio": 0.95,
        "span_ratio": 0.95, "y_top": 0.0, "y_bot": 1500.0, "num_members": 30,
        "member_ids": [m["id"] for m in members], "_members": members,
    }]
    lines = fit_column_lines(cols)
    assert len(lines) == 1
    traj = lines[0]["trajectory"]
    assert traj[0][1] <= 20 and traj[-1][1] >= 1480        # 覆盖全段
    assert abs(np.median([t[0] for t in traj]) - 200) < 12  # 中位 x 贴主列线


def test_clip_jump_removes_tail():
    """跳变到异线的尾段应被裁剪（保留最长连续段）。"""
    traj = [[100 + i * 0.1, i * 20] for i in range(15)] + \
           [[300, 300], [301, 320], [302, 340]]
    out = _clip_jump(traj, 40.0)
    assert out[-1][1] <= 300


# ---------------- 步骤4：内层表体外框 ----------------
def test_body_frame_from_outermost_columns():
    """内框 = 最左/最右列线 × 夹住列线范围的全宽横线。"""
    merged = [
        _mk_merged("horizontal", [[0, 40], [600, 40]]),     # 顶部上方最近全宽线
        _mk_merged("horizontal", [[0, 950], [600, 950]]),   # 底部下方最近全宽线
        _mk_merged("horizontal", [[0, 0], [600, 0]]),       # 更远的外框线
        _mk_merged("horizontal", [[0, 1000], [600, 1000]]),
    ]
    col_lines = [
        {"x_ref": 100.0, "x": 100.0, "y_cluster_top": 50.0, "y_cluster_bot": 900.0},
        {"x_ref": 300.0, "x": 300.0, "y_cluster_top": 40.0, "y_cluster_bot": 910.0},
        {"x_ref": 500.0, "x": 500.0, "y_cluster_top": 55.0, "y_cluster_bot": 905.0},
    ]
    body = detect_body_frame(merged, col_lines)
    assert body["left"] == 100.0 and body["right"] == 500.0
    assert body["top"] == 40.0 and body["bottom"] == 950.0


# ---------------- 步骤5：列计数与归属 ----------------
def _mk_col_line(x_ref, y_top=50.0, y_bot=900.0):
    """构造一条合成列线（assign_columns 输入所需字段）。"""
    return {"x_ref": x_ref, "x": x_ref, "y_top": y_top, "y_bot": y_bot,
            "y_cluster_top": y_top, "y_cluster_bot": y_bot, "role": None}


def test_assign_columns_roles_and_count():
    """3 条列线 → 2 列；最外两条为 frame，中间为 separator；按 x_ref 归属 column_id。"""
    col_lines = [_mk_col_line(100.0), _mk_col_line(300.0), _mk_col_line(500.0)]
    lines = [
        _mk(0, "vertical", 150, 0, 150, 100),    # 列0
        _mk(1, "vertical", 400, 0, 400, 100),    # 列1
        _mk(2, "vertical", 600, 0, 600, 100),    # 越界 → None
        _mk(3, "horizontal", 0, 50, 100, 50),    # 横向不归属
    ]
    suspect = _mk(4, "vertical", 150, 0, 150, 100, label="suspect")
    out, n_columns, bounds = assign_columns(lines + [suspect], col_lines)
    assert n_columns == 2
    assert bounds == [(100.0, 300.0), (300.0, 500.0)]
    assert [c["role"] for c in col_lines] == ["frame", "separator", "frame"]
    by_id = {ln["id"]: ln for ln in out}
    assert by_id[0]["column_id"] == 0
    assert by_id[1]["column_id"] == 1
    assert by_id[2]["column_id"] is None
    assert by_id[3]["column_id"] is None
    assert by_id[4]["column_id"] is None   # suspect 不归属


def test_internal_role_by_bottom():
    """终点低于主体底线的候选为内部线（水曲线大列内部线 2400 型）。"""
    col_lines = [_mk_col_line(100.0, y_bot=960.0),   # 边界线到达底线附近
                 _mk_col_line(200.0, y_bot=850.0),   # 止于 850 < 950-20 → internal
                 _mk_col_line(300.0, y_bot=955.0)]
    lines = [_mk(0, "vertical", 150, 0, 150, 100), _mk(1, "vertical", 250, 0, 250, 100)]
    out, n_columns, bounds = assign_columns(lines, col_lines, body_bottom=950.0)
    assert [c["role"] for c in col_lines] == ["frame", "internal", "frame"]
    assert n_columns == 1          # 内部线不计入边界：仅 [100,300] 一个列区域
    assert bounds == [(100.0, 300.0)]


def test_wrap_role_by_edge():
    """与包裹框缘重合的候选为 wrap（右缘 2940 型），不作列边界。"""
    col_lines = [_mk_col_line(100.0, y_top=10.0), _mk_col_line(300.0, y_top=10.0),
                 _mk_col_line(408.0, y_top=100.0, y_bot=950.0)]  # 距 wrap.right=405 仅 3px
    wrap = {"left": 50.0, "right": 405.0, "top": 0.0, "height": 1000.0}
    lines = [_mk(0, "vertical", 200, 0, 200, 100)]
    out, n_columns, bounds = assign_columns(lines, col_lines, wrap=wrap)
    assert [c["role"] for c in col_lines] == ["frame", "frame", "wrap"]
    assert n_columns == 1          # wrap 线不作列边界：仅 [100,300] 一个列区域
    assert bounds == [(100.0, 300.0)]


# ---------------- 1015 真实数据验收 ----------------
@pytest.fixture(scope="module")
def real_result(sample_data):
    lines = sample_data["lines"]
    merged = merge_fragments(lines)
    wrap = detect_wrap_frame(merged)
    cols = cluster_column_candidates(lines, wrap, merged)
    col_lines = fit_column_lines(cols)
    body_bottom = _body_bottom_estimate(merged, cols)
    ref_y = (wrap["top"] + wrap["bottom"]) / 2.0
    a = _global_slope(merged)
    out_lines, n_columns, bounds = assign_columns(lines, col_lines, wrap, a, ref_y,
                                                  body_bottom)
    boundaries = [c for c in col_lines if c.get("role") in ("frame", "separator")]
    body = detect_body_frame(merged, boundaries)
    return {"wrap": wrap, "body": body, "col_lines": col_lines,
            "n_columns": n_columns, "bounds": bounds, "out_lines": out_lines}


def test_real_1015_ten_columns(real_result):
    """标准答案：1015 共 10 个列区域（左区 224/289 两条找回，水曲线大列 2400 为内部线）。"""
    assert real_result["n_columns"] == 10
    roles = [c["role"] for c in real_result["col_lines"]]
    assert roles.count("frame") == 2 and roles.count("separator") == 9
    assert roles.count("internal") == 1   # 水曲线大列内部线 x≈2400
    assert roles.count("wrap") == 1       # 外框右线 x≈2940


def test_real_1015_full_height_coverage(real_result):
    """每条列线贯穿全高：y 跨度 >= 90% 表格高度。"""
    for c in real_result["col_lines"]:
        assert c["span_ratio"] >= 0.90, f"line {c['x_ref']} span {c['span_ratio']}"


def test_real_1015_frames_sane(real_result):
    """双层框：外框 [154, 1038, 2940, 18464]（顶线四角闭合），内框 = 最左/最右列线。

    注：最右列线（2866）延伸入底部条带，内框底线由全宽横线（y=17765.8）界定。
    """
    w, b, cl = real_result["wrap"], real_result["body"], real_result["col_lines"]
    assert w["top"] == pytest.approx(1037.8, abs=3.0)      # 外框顶 = 四角闭合线（用户鉴定）
    assert w["right"] == pytest.approx(2939.5, abs=3.0)    # 外框右 = 最外侧漂移线
    assert w["bottom"] == pytest.approx(18464.4, abs=3.0)  # 外框底（用户确认正确）
    assert w["left"] < b["left"] <= cl[0]["x_ref"] + 1
    assert b["right"] == pytest.approx(2864.0, abs=8.0)    # 内框右 = 最后一列列线（用户鉴定）
    assert b["top"] == pytest.approx(728.5, abs=3.0)
    mid_bot = float(np.median([c["y_bot"] for c in cl if c.get("role") != "internal"]))
    assert b["bottom"] > 0.9 * mid_bot
    assert b["bottom"] <= w["bottom"]   # 底部条带在外框内
