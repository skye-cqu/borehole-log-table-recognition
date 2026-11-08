# -*- coding: utf-8 -*-
"""rect_struct 单元测试：方案一（矫正系结构还原）的纯函数部分。

2026-09-09 修复轮新增：dev_filter（侧线偏离滤点）、resolve_sems（矫正系 sem 解析，
不读拉直系数据）、分段绘制（无桥接）、方案F 删除边界逐行跟随真实墨迹。"""
import numpy as np

from src.table.rect_struct import (dev_filter, remove_deleted_bands, resolve_sems,
                                   side_intervals, strip_band)

BG, INK = 230, 80


def test_strip_band_masks_outside_curves():
    """带内逐行掩膜：曲线边界以外的墨（含邻列线）必须被剔除。"""
    import cv2
    h, w = 300, 200
    img = np.full((h, w), BG, np.uint8)
    cv2.line(img, (20, 0), (20, h), INK, 3)    # 邻列线（应在带外）
    cv2.line(img, (100, 0), (100, h), INK, 3)  # 带内竖线
    ys = np.arange(h)
    wx = 60 + 10 * np.sin(ys / 40.0)
    ex = 120 + 10 * np.cos(ys / 40.0)
    band_soft, gray_band, x0i = strip_band(img, 0, h, (ys, wx), (ys, ex), inset=3)
    assert x0i >= 0
    col = 100 - x0i
    assert band_soft[:, col].mean() > 0.9
    col2 = 20 - x0i
    if col2 >= 0:
        assert band_soft[:, col2].mean() < 0.05
    assert (gray_band[:, col] == BG).mean() < 0.1


# ---------- dev_filter：侧线贴线爬行锯齿/跳轨点剔除 ----------

def test_dev_filter_drops_jump_track_keeps_smooth_line():
    ys = np.arange(0, 2000, 40.0)
    xs = 63.5 + 1.5 * np.sin(ys / 300.0)
    xs[10:14] += 56.0
    xs[20] += 64.0
    keep = dev_filter(ys, xs, win=8, dev=6.0)
    assert keep.sum() == len(xs) - 5
    assert not keep[10:14].any() and not keep[20]


def test_dev_filter_keeps_genuine_curvature():
    ys = np.arange(0, 3000, 30.0)
    xs = 100 + 40 * np.sin(ys / 1500.0)
    keep = dev_filter(ys, xs, win=8, dev=6.0)
    assert keep.all()


# ---------- resolve_sems：sem 矫正系解析 ----------

def _mids(cols):
    names = sorted(cols, key=cols.get)
    return names, np.array([cols[n] for n in names], float)


def test_resolve_sems_matches_detected_line_in_window():
    W = 2745.0
    names, xs = _mids({'col8': 775.9, 'col9': 2106.4, 'col7': 580.5})
    out = resolve_sems(names, xs, W, snap_fn=lambda x: (x, 0.0))
    assert out[9]['ref'] == 'col9' and out[9]['cut_x'] == 2106.4


def test_resolve_sems_hint_overrides_template_proximity():
    W = 2700.0
    names, xs = _mids({'col6': 593.2, 'col7': 666.2, 'col8': 870.7, 'col9': 2182.5})
    out = resolve_sems(names, xs, W, snap_fn=lambda x: (x, 0.0),
                       hints={7: 'col7', 8: 'col8'})
    assert out[7]['ref'] == 'col7' and out[7]['cut_x'] == 666.2
    assert out[8]['ref'] == 'col8' and out[8]['cut_x'] == 870.7
    assert not out[7]['aux'] and not out[8]['aux']


def test_resolve_sems_hint_ignores_cross_frame_gap():
    """1035 回归：同名 col7 两账差 61px（合法拉直系差）——同源同名对账天然可信，
    不加跨系 px 门槛；切口=落账线 563.1，带宽 208 合模板。"""
    names, xs = _mids({'col7': 563.1, 'col8': 771.1, 'col9': 2104.1})
    out = resolve_sems(names, xs, 2700.0, snap_fn=lambda x: (x, 0.0),
                       hints={7: 'col7', 8: 'col8'})
    assert out[7]['ref'] == 'col7' and out[7]['cut_x'] == 563.1
    assert not out[7].get('band_check_warning')


def test_resolve_sems_rejects_line_outside_window_then_snaps():
    W = 3000.0
    names, xs = _mids({'col7': 563.1, 'col8': 771.1, 'col9': 2104.1})
    out = resolve_sems(names, xs, W, snap_fn=lambda x: (x, 0.0))
    assert out[7]['ref'] == 'col7'
    assert out[8]['source'].startswith('template')
    assert abs(out[8]['cut_x'] - (563.1 + (0.2883 - 0.2109) * W)) <= 1.0


def test_resolve_sems_band_check_warns_without_rewrite():
    W = 2700.0
    names, xs = _mids({'col7': 666.2, 'col8': 870.7, 'col9': 2182.5})
    out = resolve_sems(names, xs, W, snap_fn=lambda x: (x, 0.0),
                       hints={7: 'col7', 8: 'col8'})
    assert out[7]['cut_x'] == 666.2 and out[8]['cut_x'] == 870.7
    assert 'band_check_warning' not in out[7]
    names2, xs2 = _mids({'col7': 666.2, 'col8': 970.7, 'col9': 2182.5})
    out2 = resolve_sems(names2, xs2, W, snap_fn=lambda x: (x, 0.0),
                        hints={7: 'col7', 8: 'col8'})
    assert out2[7]['cut_x'] == 666.2 and out2[8]['cut_x'] == 970.7
    assert 'band_check_warning' in out2[7] and 'band_check_warning' in out2[8]


def test_resolve_sems_snap_moves_aux_to_ink():
    W = 2740.0
    names, xs = _mids({'col7': 529.0, 'col9': 2055.2})
    out = resolve_sems(names, xs, W, snap_fn=lambda x: (763.0, 9999.0))
    assert out[8]['ref'].startswith('aux')
    assert out[8]['cut_x'] == 763.0 and 'snap' in out[8]['source']


# ---------- 分段绘制：天窗真开窗，不桥接 ----------

def test_side_intervals_open_gaps_split_segments():
    ys = np.array([100., 200., 700., 800., 1600.])
    hits = np.array([True, True, True, True, True])
    iv, gaps = side_intervals(ys, hits, max_chain_gap=300)
    assert len(iv) == 3
    assert gaps == [(200, 700), (800, 1600)]


def test_segments_from_gaps_never_bridge():
    from src.table.rect_struct import segments_from_gaps
    ys = np.array([0., 100., 5000., 5100.])
    xs = np.array([12., 13., 20., 21.])
    segs = segments_from_gaps(ys, xs, [(0, 100), (5000, 5100)])
    assert len(segs) == 2
    assert all(np.all(np.diff(s[:, 1]) <= 300) for s in segs)
    assert segs[0][:, 1].max() <= 100 and segs[1][:, 1].min() >= 5000


# ---------- clip_to_kept：绘制层按保留区裁剪 ----------

def test_clip_to_kept_splits_at_deleted_bands():
    from src.table.rect_struct import clip_to_kept
    curves = {7: (np.array([0., 100.]), np.full(2, 100.)),
              8: (np.array([0., 100.]), np.full(2, 200.)),
              9: (np.array([0., 100.]), np.full(2, 300.))}
    pts = np.array([[50., 10.], [150., 30.], [250., 40.],
                    [299., 50.], [305., 60.]])
    segs = clip_to_kept(pts, curves)
    xs_all = np.concatenate([s[:, 0] for s in segs])
    assert 150. not in xs_all and 305. not in xs_all
    assert 250. in xs_all and 299. in xs_all


def test_clip_to_kept_keeps_boundary_lines():
    from src.table.rect_struct import clip_to_kept
    curves = {7: (np.array([0., 100.]), np.full(2, 100.)),
              8: (np.array([0., 100.]), np.full(2, 200.)),
              9: (np.array([0., 100.]), np.full(2, 300.))}
    pts = np.array([[100., 10.], [100.5, 30.], [300., 50.]])
    segs = clip_to_kept(pts, curves)
    xs_all = np.concatenate([s[:, 0] for s in segs])
    assert 100. in xs_all and 300. in xs_all


def test_clip_to_kept_stops_crossing_line_at_c9():
    from src.table.rect_struct import clip_to_kept
    curves = {7: (np.array([0., 100.]), np.full(2, 100.)),
              8: (np.array([0., 100.]), np.full(2, 200.)),
              9: (np.array([0., 100.]), np.full(2, 300.))}
    pts = np.array([[150., 10.], [250., 20.], [299., 30.], [302., 40.], [325., 50.]])
    segs = clip_to_kept(pts, curves)
    xs_all = np.concatenate([s[:, 0] for s in segs])
    assert (xs_all <= 300.5).all()
    assert 325. not in xs_all and 302. not in xs_all


# ---------- 方案F：删除=落账曲线逐行白化（真墨跟踪实测会游移到贴线文字上，废弃） ----------

def test_remove_deleted_bands_follows_curves():
    """删除边界=落账曲线本身（逐行插值）：带内白化、带外一字不动、弯曲跟随。"""
    h, w = 40, 200
    rect = np.full((h, w, 3), 200, np.uint8)
    rect[:, 100] = 0     # 带内 → 白
    rect[:, 60] = 0      # 带西 → 保留
    rect[:, 150] = 0     # 带东 → 保留
    curves = {7: (np.array([0., h // 2 - 1, h // 2, h], float),
                  np.array([90., 90., 110., 110.])),
              8: (np.array([0., h]), np.full(2, 130.)),
              9: (np.array([0., h]), np.full(2, 170.))}
    canvas = remove_deleted_bands(rect, curves)
    assert canvas.shape == rect.shape                       # 全幅
    assert (canvas[: h // 2, 100] == 255).all()             # 上半段带内白
    assert (canvas[h // 2:, 100] == 0).all()                # 下半段曲线到 110，100 在带外 → 保留
    assert (canvas[:, 110] == 255).all()                    # 弯曲跟随
    assert (canvas[:, 60] == 0).all() and (canvas[:, 150] == 0).all()


# ---------- R4：外框整线绘制 + 逐点校验分色（封闭连贯） ----------

def test_dash_segments_cover_whole_polyline():
    """虚线短划覆盖整条折线：首末短划贴合端点，相邻短划净空≈off（连通无缺口）。"""
    import pytest
    from src.table.rect_struct import dash_segments
    ys = np.arange(0, 1000, 10.0)
    pts = np.stack([np.full(len(ys), 50.0), ys], 1)
    pieces = dash_segments(pts, on=26, off=16)
    assert pieces
    assert np.allclose(pieces[0][0], pts[0]) and np.allclose(pieces[-1][-1], pts[-1])
    for a, b in zip(pieces, pieces[1:]):
        gap = float(np.linalg.norm(b[0] - a[-1]))
        assert 13.0 <= gap <= 19.0          # 净空≈off=16
    # 各长度的短路径（含不足一个周期的）：尾短划必须到达终点（R4 实测
    # 1017 底框 40px 连接段曾只画前 26px，在实线段前留裸口）
    for L in (5, 12, 26, 40, 41, 42, 55, 100, 300, 599):
        p2 = np.stack([np.full(L + 1, 50.0), np.arange(0., L + 1., 1.)], 1)
        ps = dash_segments(p2, on=26, off=16)
        assert np.allclose(ps[0][0], p2[0]), L
        assert np.allclose(ps[-1][-1], p2[-1]), L
        for a, b in zip(ps, ps[1:]):
            assert float(np.linalg.norm(b[0] - a[-1])) <= 16 + 2.5, L


def test_draw_frame_polyline_solid_verified_dash_unverified():
    """验证段=现色实线、未验证段=黄虚线；整列无超虚线净空的缺口（封闭连贯）。"""
    import cv2
    from src.table.rect_struct import draw_frame_polyline
    img = np.full((600, 200, 3), 255, np.uint8)
    ys = np.arange(0, 600, 2.0)
    xs = np.full(len(ys), 100.0)
    status = np.ones(len(ys), bool)
    status[100:200] = False                      # y∈[200,398) 未验证
    draw_frame_polyline(img, ys, xs, status, (255, 0, 0))
    col = img[:, 100]
    blue = np.where((col[:, 0] > 200) & (col[:, 1] < 100) & (col[:, 2] < 100))[0]
    yellow = np.where((col[:, 0] < 100) & (col[:, 1] > 200) & (col[:, 2] > 200))[0]
    assert blue.size > 80 and yellow.size > 40
    assert not blue[(blue > 206) & (blue < 394)].size        # 实线不进未验证区
    assert ((yellow >= 194) & (yellow <= 406)).all()         # 虚线只在未验证区（含两端连接点）
    drawn = np.sort(np.concatenate([blue, yellow]))
    assert drawn.min() <= 5 and drawn.max() >= 594           # 首末覆盖
    assert np.diff(drawn).max() <= 30                        # 无超净空缺口
    blue_a, blue_b = blue[blue < 300], blue[blue >= 300]
    assert np.diff(blue_a).max() <= 3 and np.diff(blue_b).max() <= 3   # 实线连续


def test_frame_status_flags_floating_segment():
    """悬浮段（无墨处）判未验证，贴细规则线段判验证——判据与 JSON 账目同参。"""
    import cv2
    from src.table.rect_struct import frame_status
    img = np.full((2000, 200), 230, np.uint8)
    img[:, 98:102] = 60                       # 真细规则线 x=100
    ys = np.arange(0, 2000, 10.0)
    xs = np.full(len(ys), 100.0)
    xs[100:140] = 160.0                       # 悬浮段（该处空白）
    st = frame_status(img, ys, xs, 'v')
    assert st[:100].all() and st[140:].all()
    assert not st[100:140].any()


def test_collect_unverified_labels_only_long_runs():
    from src.table.rect_struct import collect_unverified_labels
    ys = np.arange(0, 1000, 10.0)
    xs = np.full(100, 50.0)
    status = np.ones(100, bool)
    status[20:60] = False                     # 400px 段 → 标注
    lab = collect_unverified_labels(ys, xs, status, min_len=260)
    assert len(lab) == 1 and 290 <= lab[0][1] <= 410 and lab[0][2] == '6e 未验证段'
    status2 = np.ones(100, bool)
    status2[20:30] = False                    # 100px 短段 → 不加字
    assert collect_unverified_labels(ys, xs, status2, min_len=260) == []


def test_collect_unverified_labels_merges_short_verified_islands():
    """单点/短验证岛不画实线（视觉连续黄虚），测长须跨岛合并（1015 底框实测回归：
    0~42px 未验证段与单点岛交替 ≈800px，逐段测长全部低于阈值漏标）。"""
    from src.table.rect_struct import collect_unverified_labels
    ys = np.arange(0, 1000, 10.0)
    xs = np.full(100, 50.0)
    status = np.ones(100, bool)
    status[20:80] = False
    status[40] = True                          # 单点岛：不画实线，视觉仍是连续虚线
    status[43] = True
    lab = collect_unverified_labels(ys, xs, status, min_len=260)
    assert len(lab) == 1 and 190 <= lab[0][1] <= 810
    status2 = np.ones(100, bool)
    status2[20:40] = False                     # 200px | 160px 实线岛 | 240px：
    status2[40:56] = True                      # 岛 >150px 不合并，两段各自 <260 → 无标注
    status2[56:80] = False
    assert collect_unverified_labels(ys, xs, status2, min_len=260) == []


def test_annotate_overlay_draws_labels_and_legend():
    from src.table.rect_struct import _font_path, annotate_overlay
    if _font_path() is None:
        import pytest
        pytest.skip('无中文字体')
    img = np.full((500, 800, 3), 255, np.uint8)
    annotate_overlay(img, [(100, 200, '6e 未验证段')],
                     legend={'x0': 420, 'y0': 60, 'xlim': 790,
                             'entries': [('side', '外框侧线·验证段'),
                                         ('frame', '上下框·验证段'),
                                         ('unver', '6e 未验证段')],
                             'note': '黄虚线=悬浮/跳轨/出界点'})
    ink = (img < 220).any(2)
    assert ink.any()                                # 有笔画
    assert ink[60:260, 300:790].any()               # 图例卡片区域有内容
    yellow = (img[:, :, 0] < 120) & (img[:, :, 1] > 180) & (img[:, :, 2] > 180)
    assert yellow.sum() > 50                        # 黄色标注文字/虚线色样存在
