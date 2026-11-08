# -*- coding: utf-8 -*-
"""行界门禁的最小自检（合成点列，不读图）。

形状门禁（用户口径）：拼成线之后，逐窗斜率的中位数离参照斜率 >SKEW(2%) = 歪。
参照默认是"这条线上下 1 行高内邻居的窗斜率中位"（SKEW_BAND），全表中位斜率只兜底——
整张纸在弯时，全表参照会把转得最多的真行当歪线杀掉（1020 实测，见 line_ref）。
只判线级、不判链级——链级实测误杀真行，见 track_rows 模块头与 runs/tmp/sweep_gates.py。
门禁1 完全链接 + 簇直径容差：竖向差 > 容差的两条链不能并成一条线。
门禁3 数值区右界：整簇一次求交，不再 clip 到单条链自己的跨度；覆盖率按窗口裁段，
     整条落在窗口外的链不倒扣（1040 两条真层界因此被降级 = 用户说的"漏线"）。
门禁4 切分：一条链把两行拼在一起（300px 窗两侧中位差 >0.6 行高）时在台阶处下刀，
     两半各归各行的簇；抖和弯都不下刀（rise_of/ptp 会误切，实测见 split_pts 注释）。
     剪枝(trim_pts)试过并废掉：它让 1027 离墨>30% 的层界 1→10 条、漏线 1→2，已删。
门禁5 内容列排除：柱状列（岩性描述左边那一格，实测带宽 162~323px）里画的是图案边线，
     中点落在带内的阶段4 段不作结构证据，数值区右界同时收到带西缘（见 content_band）。
"""
import json

import numpy as np

from src.table import track_rows as tr


def chain(x0, x1, y, k=0.0, ids=("s",), step=0.0):
    """一条链：x 从 x0 到 x1，高度 y + k·(x-x0)（k=斜率）。"""
    xs = np.arange(x0, x1 + 1, 20.0)
    pts = np.column_stack([xs, y + k * (xs - x0)])
    return {"y": float(np.median(pts[:, 1])), "x": (float(x0), float(x1)), "res": 0.0,
            "step": step, "slope": tr.slope_of(pts), "pts": pts, "ids": list(ids)}


def test_形状门禁_缓坡爬行的线判歪():
    # 1027 y=10886 那条：2000px 里爬 130px = 6.5% 斜率，台阶口径读数 0px
    ramp = chain(0, 2000, 10000.0, k=0.065)
    flat = chain(0, 2000, 10000.0)
    assert tr.step_of(ramp["pts"]) < 60                     # 台阶量尺看不见缓坡
    assert tr.skewed(ramp["pts"], 0.0)
    assert not tr.skewed(flat["pts"], 0.0)


def test_形状门禁_整条表都斜时不误伤():
    tilt = chain(0, 2000, 10000.0, k=0.02)                  # 表本身斜 2%
    assert not tr.skewed(tilt["pts"], 0.02)                 # 相对全表中位斜率才算歪


def test_形状门禁_弯但不爬的线不判歪():
    # 1040 实测反例：ptp 8.1 行高的那条线离墨 0.0%，是真而弯的行线。
    # 走偏量/局部爬升当判据就会杀它，所以那两把尺子只登记不判定。
    xs = np.arange(0, 2001, 20.0)
    pts = np.column_stack([xs, 10000.0 + 120.0 * np.sin(xs / 2000.0 * np.pi)])
    assert tr.ptp_off(pts, 0.0) > 100                       # 走偏量很大
    assert not tr.skewed(pts, 0.0)                          # 但两端同高、不是爬去别行


def test_门禁1_半行高内的链才并():
    near = [chain(0, 1000, 3000.0), chain(1000, 2000, 3020.0)]     # 接缝差 20px
    far = [chain(0, 1000, 3000.0), chain(1000, 2000, 3060.0)]      # 接缝差 60px
    assert len(tr.cluster(near, 35.0)) == 1
    assert len(tr.cluster(far, 35.0)) == 2


def test_门禁1_逐级爬行的链被钉在容差内():
    # 单链接能把 20px 一级的小台阶一路串到 100px 之外；完全链接按簇直径拦下来
    items = [chain(200 * i, 200 * i + 200, 3000.0 + 20 * i) for i in range(5)]
    cl = tr.cluster(items, 35.0)
    assert [len(c["mem"]) for c in cl] == [2, 2, 1]
    assert all(max(m["y"] for m in c["mem"]) - min(m["y"] for m in c["mem"]) <= 35
               for c in cl)


def test_门禁3_右界按整簇求交_not_clip到单链():
    it = chain(0, 500, 3000.0)                              # 链只铺到 x=500
    col = np.array([[2900.0, 1000.0], [3100.0, 1000.0]])    # 锚线在 x=1000
    rows, _, _, off = tr.lines_from(tr.cluster([it], 35.0), 0, 3000, 3000, col,
                                    ref=(0.0, 0.02))
    assert not off
    assert rows[0]["boundary_x"] == 1000                    # 旧代码会 clip 成 500
    assert abs(rows[0]["cov_num"] - 0.5) < 1e-3             # 分母 = 1000，不是 500


def test_覆盖率不给窗口外的链倒扣():
    # 1040 y=5101 实测形态：数值区被 381→1034 的链横断 85%，同簇还挂着一条纯描述区链
    num = chain(381, 1034, 5101.0, ids=("a",))
    desc = chain(2357, 3069, 5101.0, ids=("b",))
    assert tr.cover([num], 269, 1034) > 0.85                 # 单看横断数值区的那条
    assert tr.cover([desc], 269, 1034) == 0.0                # 整条在窗口外 = 0，不是负
    assert tr.cover([num, desc], 269, 1034) > 0.8            # 旧算法这里读数 -1.70
    rows, subs, _, off = tr.lines_from(tr.cluster([num, desc], 35.0), 269, 3069, 2800,
                                       np.array([[4900.0, 1034.0], [5300.0, 1034.0]]),
                                       ref=(0.0, 0.02))
    assert not off and not subs and len(rows) == 1           # 真层界不再被降级 = 1040 漏线


def test_形状门禁_拼出来歪的线不落层界():
    it = chain(0, 2000, 3000.0, k=0.065)                    # 一条爬 130px 的"线"
    col = np.array([[2900.0, 2500.0], [3100.0, 2500.0]])
    rows, _, _, off = tr.lines_from(tr.cluster([it], 35.0), 0, 3000, 3000, col,
                                    ref=(0.0, 0.02))
    assert not rows and len(off) == 1                       # 图上没这条线，别当层界


def test_切分_斜撑顶起来的鼓包被切下来():
    # 1027 x≈760~990 那两条斜撑带：线在本行 3000 上走，中间被顶到 2920（1.1 行高）再落回来。
    # 切分把鼓包摘成独立一段，本行的两段还留在 3000 上，拼出来的线不跳行。
    # 台阶读数在中位多数派没换的一整段缝隙上都是满额（平台），刀口取平台正中；鼓包宽 360px
    # 只比窗 300 宽一点，平台略偏，所以判各段中位数、不判刀口的确切 x。
    xs = np.arange(0, 2001, 20.0)
    pts = np.column_stack([xs, np.where((xs > 800) & (xs < 1200), 2920.0, 3000.0)])
    seg = tr.split_pts(pts, 0.0, 41.0)
    assert len(seg) == 3
    assert [round(np.median(s[:, 1])) for s in seg] == [3000.0, 2920.0, 3000.0]
    assert sum(int((np.abs(s[:, 1] - np.median(s[:, 1])) > 1).sum()) for s in seg) <= 6
    for s in seg:                                       # 切完不再从刀口一路削成碎点
        assert max(tr.step_score(s, s[:, 1], 300.0)) <= 41.0


def test_切分_拼两行的链在台阶处下刀():
    # 1027 y=4446 的实测形态：左半贴着 4447，x765→968 一道 69px 的斜撑台阶，右半贴着 4379。
    # 剪枝对它没用（中位落在两行正中间，两段都不越限），只能下刀。
    xs = np.arange(248, 2296, 20.0)
    ys = np.where(xs < 765, 4447.0,
                  np.where(xs > 968, 4379.0, 4447.0 - (xs - 765) * 0.39))
    pts = np.column_stack([xs, ys])
    seg = tr.split_pts(pts, 0.0, 41.0)                      # 0.6 行高（1027 行高 68px）
    assert len(seg) == 2
    assert np.median(seg[0][:, 1]) > 4440 and np.median(seg[1][:, 1]) < 4390
    for s in seg:                                           # 两半里都不再残留"持久台阶"
        assert max(tr.step_score(s, s[:, 1], 300)) <= 41.0
    raw = {tuple(p) for p in pts}
    assert all(tuple(p) in raw for s in seg for p in s)     # 只下刀，不插值造点（约束2）


def test_切分_抖和弯都不下刀():
    # 来回抖：左右两半中位都是中线，峰谷差却很大（这就是换掉 rise_of 的原因）
    xs = np.arange(0, 2001, 20.0)
    wig = np.column_stack([xs, 3000.0 + 30.0 * np.sin(xs / 200.0 * 2 * np.pi)])
    assert tr.rise_of(wig, 300) > 41
    assert len(tr.split_pts(wig, 0.0, 41.0)) == 1
    # 真而弯（1040 y=20654 那类，整体走偏 8 行高、离墨 0%）：缓坡两侧中位只差十几个 px
    arc = np.column_stack([xs, 10000.0 + 120.0 * np.sin(xs / 2000.0 * np.pi)])
    assert tr.ptp_off(arc, 0.0) > 100
    assert len(tr.split_pts(arc, 0.0, 41.0)) == 1


def test_切分后两半各归各行的簇():
    # 两行各有一条全宽链，再混进一条"左半贴上行、右半贴下行"的拼接链
    a = chain(0, 2000, 4400.0, ids=("a",))
    b = chain(0, 2000, 4470.0, ids=("b",))
    xs = np.arange(0, 2001, 20.0)
    splice = {"y": 4435.0, "x": (0.0, 2000.0), "res": 0.0, "step": 0.0, "slope": 0.0,
              "pts": np.column_stack([xs, np.where(xs < 900, 4400.0, 4470.0)]),
              "ids": ["c"]}
    items = [a, b, splice]
    cl = tr.cluster(tr.split_items(items, 0.0, 41.0)[0], 35.0)
    assert len(cl) == 2
    for c in cl:
        assert max(c["poly"][:, 1]) - min(c["poly"][:, 1]) < 1     # 两条线都是平的
        assert c["x"] == (0.0, 2000.0)                             # 都横贯全宽
    # 不切：拼接链自己成一条"线"，从上行爬到下行 —— 画出来就是切坏格子的斜线
    bad = tr.cluster(items, 35.0)
    assert max(max(c["poly"][:, 1]) - min(c["poly"][:, 1]) for c in bad) > 41


def bend_sheet(n=11, span=2000.0):
    """一张"整幅慢慢转"的合成表：n 条行线，行距 80px，斜率从 -5% 线性转到 +5%。

    1020 的形态：全表中位斜率 2.10%，任何一行的参照都不该是它——取全表当参照时，转得最多
    的那几行被形状闸剔掉，而它们离墨 ≤10%（就在真横线上）。
    """
    col = np.array([[900.0, 1000.0], [2000.0, 1000.0]])          # 数值区右界 x=1000
    its = [chain(0, span, 1000.0 + 80.0 * i, k=-0.05 + 0.01 * i, ids=(f"r{i}",))
           for i in range(n)]
    return its, col


def test_形状闸参照_全表中位斜率会杀掉弯表的真行():
    its, col = bend_sheet()
    cl = tr.cluster(its, 35.0)
    assert len(cl) == len(its)                                   # 一行一簇，没串到隔壁
    rows, _, _, off = tr.lines_from(cl, 0, 3000, 3000, col, ref=(0.0, 0.02, None))
    assert (len(rows), len(off)) == (5, 6)                        # 转得最多的两端 6 行被剔
    assert sorted(round(r["win"], 2) for r in off) == [-0.05, -0.04, -0.03, 0.03, 0.04, 0.05]


def test_形状闸参照_换成上下邻居后弯表不剔而爬行的线照剔():
    its, col = bend_sheet()
    # 一条孤零零的爬行链：离最近的真行 380px（>参照带），是"拼歪出来的假线"的形态
    its = its + [chain(0, 2000, 2280.0, k=0.10, ids=("crawl",))]
    cl = tr.cluster(its, 35.0)
    rows, _, _, off = tr.lines_from(cl, 0, 3000, 3000, col, ref=(0.0, 0.02, 90.0))
    assert (len(rows), len(off)) == (11, 1)                       # 真行一条不剔
    assert off[0]["segment_ids"] == ["crawl"]                     # 邻居凑不满 → 退回全表 → 照剔


def test_形状闸参照_带宽为0是全表参照不是自我参照():
    its, col = bend_sheet()
    cl = tr.cluster(its, 35.0)
    pl = [c["poly"] for c in cl]
    ys = [float(np.median(p[:, 1])) for p in pl]
    ws = [tr.win_list(p) for p in pl]
    refs = tr.line_ref(ys, ws, 0.0, 0.0)
    assert refs == [0.0] * len(cl)                               # 0 → 退回全表，不能只配到自己
    assert tr.line_ref(ys, ws, 0.0, None) == [0.0] * len(cl)


def seg(x0, x1, y=500.0):
    """阶段4 的一条横向候选段：点列是 (x, y)，从 x0 拉到 x1。"""
    return [[x0, y], [(x0 + x1) / 2, y], [x1, y]]


def band(west_x, east_x, tilt=0.0):
    """一条带（6a 定稿列线对）：西缘 west_x、东缘 east_x，整体随表 tilt 慢慢右移。"""
    a = np.array([[0.0, west_x], [1000.0, west_x + 1000 * tilt]])
    b = np.array([[0.0, east_x], [1000.0, east_x + 1000 * tilt]])
    return a, b


def test_门禁5_带内的段不算结构证据():
    bl = band(800.0, 1000.0)
    assert tr.in_band(seg(820, 980), bl)                       # 带正中：柱状图案的边线
    assert tr.in_band(seg(806, 999), bl)                       # 中点 902.5，仍在带内
    assert not tr.in_band(seg(700, 806), bl)                   # 中点 753：数值列的真行线
    assert not tr.in_band(seg(1000, 1300), bl)                 # 中点 1150：岩性描述那边
    assert not tr.in_band(seg(800, 810), bl)                   # 骑在带缘 → 保留（BAND_PAD）


def test_门禁5_带跟着表歪不是常数x界():
    bl = band(800.0, 1000.0, tilt=0.1)                         # y=1000 处带整体右移 100px
    assert tr.in_band(seg(950, 1050, y=1000.0), bl)            # 中点 1000 ∈ [900, 1100]
    assert not tr.in_band(seg(950, 1050, y=0.0), bl)           # 同一条线在 y=0 时中点在带外


def test_门禁5_列线中断处带不随外插滑走():
    # 1035 型：两条缘平行右倾、都在 y=500 处断掉，表一直画到 1000+。
    # 裸 x_at 在 y=1000 处把带滑成 [1300,1500]：真带里的段一条没排掉，反倒去删描述列的段。
    west = np.array([[0.0, 800.0], [500.0, 1050.0]])
    east = np.array([[0.0, 1000.0], [500.0, 1250.0]])
    assert tr.in_band(seg(1100, 1200, y=1000.0), (west, east))      # 延接后带 = [1050,1250]
    assert not tr.in_band(seg(1350, 1450, y=1000.0), (west, east))  # 外插才会把它算进"带内"
    assert tr.in_band(seg(1050, 1150, y=400.0), (west, east))       # 覆盖内照旧：带 = [1000,1200]


def sheet(tmp, monkeypatch, xs, height=1000.0):
    """写一张假的 6a 定稿（列线在 xs 上）+ 阶段4 候选坐标，供 content_band 读。

    xs 元素三种写法：x（直上直下、画到底）、(x, 断口 y)、(下 x, 上 x, 断口 y)（斜线）。
    """
    coord, runs = tmp / "坐标数据", tmp / "table_reconstruct"
    coord.mkdir(parents=True), runs.mkdir(parents=True)
    lines, cols = [], []
    for i, x in enumerate(xs):
        x0, x1, ye = (x, x, height) if isinstance(x, (int, float)) else \
            (x[0], x[0], x[1]) if len(x) == 2 else x
        lines.append({"id": f"v{i}", "direction": "vertical", "label": "high",
                      "length": ye, "points": [[x0, 0.0], [x1, ye]]})
        cols.append({"x_at_mid": (x0 + x1) / 2, "segment_ids": [f"v{i}"]})
    (coord / "T.json").write_text(json.dumps({"lines": lines, "height": height}), encoding="utf-8")
    (runs / "T_列结构定稿.json").write_text(json.dumps({"columns": cols}), encoding="utf-8")
    monkeypatch.setattr(tr.paths, "CANDIDATE_COORD_DIR", coord)
    monkeypatch.setattr(tr.paths, "RUNS_DIR", tmp)


def test_门禁5_带认得出时锚线收到带西缘(tmp_path, monkeypatch):
    # 数值格 100、柱状 202、岩性描述 1298 —— 28 张实测的形状
    sheet(tmp_path, monkeypatch, [0, 100, 200, 300, 400, 500, 600, 802, 2100, 2600])
    west, east, src = tr.content_band("T")
    assert src == "line"
    assert (tr.x_at(west, 500), tr.x_at(east, 500)) == (600, 802)


def test_门禁5_东缘漏检按实测带宽推(tmp_path, monkeypatch):
    # 1020 型：柱状|岩性那条线没检出 → 最宽缝是"柱状+岩性"，锚线本身就是带西缘
    sheet(tmp_path, monkeypatch, [0, 100, 200, 300, 400, 500, 600, 679, 1977, 2477])
    west, east, src = tr.content_band("T")
    assert src == "template"
    assert (tr.x_at(west, 500), tr.x_at(east, 500)) == (679, 679 + tr.BAND_W_MED)


def test_门禁5_列线断口以下带跟着邻线走(tmp_path, monkeypatch):
    # 1035 型：两条缘都只画到 y=400，左边那条数值列线画到底、而且一路往右偏
    # （500@y0 → 560@y1000）。表整体在下半张右移，带冻在断口处就会离真柱状列越甩越远。
    xs = [0, 100, 200, 300, 400, (500, 560, 1000.0), (700, 748, 400.0), (902, 950, 400.0),
          2200, 2700]
    sheet(tmp_path, monkeypatch, xs)
    west, east, src = tr.content_band("T")
    assert src == "line"
    assert abs(tr.edge_at(west, 300) - 736) < 1e-6        # 覆盖内照旧：700 + 0.75×48
    assert abs(tr.edge_at(east, 300) - 938) < 1e-6
    # 断口以下：邻线在 y=900 处是 554，带西缘断口处离它 748-524=224 → 554+224
    assert abs(tr.edge_at(west, 900) - 778) < 1e-6
    assert abs(tr.edge_at(east, 900) - 980) < 1e-6        # 950-524=426 → 554+426
    assert abs(tr.edge_at(east, 900) - tr.edge_at(west, 900) - 202) < 1e-6   # 带宽一格不变


def test_门禁5_断口以下没有邻线可跟时保持原位(tmp_path, monkeypatch):
    # 所有列线都在 y=400 断掉 → 没有"当时还活着"的锚线，宁可冻在断口，不把带挪到没量过的地方
    xs = [0, 100, 200, 300, 400, (500, 548, 400.0), (700, 748, 400.0), (902, 950, 400.0),
          (2200, 2248, 400.0), (2700, 2748, 400.0)]
    sheet(tmp_path, monkeypatch, xs)
    west, east, src = tr.content_band("T")
    assert src == "line"
    assert abs(tr.edge_at(west, 900) - 748) < 1e-6
    assert abs(tr.edge_at(east, 900) - 950) < 1e-6


def test_门禁5_认不出带时一段都不删(tmp_path, monkeypatch):
    # 带位上只有 79px（数值列自己的格宽）且列数不够 → 三条件不满足，宁可留着图案边线，
    # 也不能把真数值列的证据抹掉。
    sheet(tmp_path, monkeypatch, [0, 300, 600, 900, 1200, 1279, 2600])
    assert tr.content_band("T") == (None, None, None)
    assert tr.content_band("没有这张图") == (None, None, None)
