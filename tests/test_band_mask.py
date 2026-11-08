# -*- coding: utf-8 -*-
"""带掩膜单测：all_in_band / band_split_item / _in_band_mask / continue_below 远锚分支。

坐标约定与生产一致：段与条目点列 = [x, y]（第一坐标=原图 x）；带缘链 = (y, x)。
条目切带语义（band_split_item）：带内点剔除、条目沿带切成碎片；水文带只还东端贴切线
（≤HYDRO_RESTORE）的终端尾巴（岩性行线的 T 接行尾是行界证据）；单点碎片贴邻居趋势才留
（离趋势远的是骑带缘台阶点），全孤点条目共线即留；穿到右框的表框线豁免水文带切分。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.table.track_rows import (BAND_PAD, HYDRO_RESTORE, _in_band_mask,
                                  all_in_band, band_split_item, continue_below)


def _band(w_x, e_x, y0=0.0, y1=1000.0):
    """竖直的假带缘链 (y,x)。"""
    return np.array([[y0, w_x], [y1, e_x]], float)


WEST = _band(100.0, 100.0)                # 柱状带西缘 x=100，净内区 [100+PAD, 300-PAD]
EAST = _band(300.0, 300.0)                # 柱状带东缘
HYDRO = _band(500.0, 500.0)               # 水文带只有西缘
BANDS = [(WEST, EAST), (HYDRO, None)]


def test_all_in_band_整段在带内为真():
    pts = [[150, 500], [200, 500], [250, 500]]
    assert all_in_band(pts, BANDS)


def test_all_in_band_骑缘与出带为假():
    assert not all_in_band([[90, 500], [200, 500]], BANDS)      # 骑西缘
    assert not all_in_band([[450, 500], [550, 500]], BANDS)     # 穿水文带西缘
    assert not all_in_band([[400, 500], [450, 500]], BANDS)     # 两带之间=内容区


def test_in_band_mask_水文带西缘以右全算():
    m = _in_band_mask([450.0, 520.0, 700.0], [500.0] * 3, [(HYDRO, None)])
    assert list(m) == [False, True, True]


def test_band_split_穿带条目切开_终端尾巴贴线还回():
    # 点列 50~690 步 10：柱状带 [106,294] 切去中段；水文带切线 x≥506，终端恢复还回
    # 贴线 ≤506+20 的 510/520 两点，530 以深不还
    it = {"pts": [[float(x), 500.0] for x in range(50, 700, 10)],
          "ids": [7, 8], "res": 0.5, "y": 505.0}
    pieces = band_split_item(it, BANDS, tab_l=0.0, tab_r=2000.0)
    pts = np.vstack([p["pts"] for p in pieces])
    xs = pts[:, 0]
    inside_c = _in_band_mask(xs, pts[:, 1], [(WEST, EAST)])
    assert not inside_c.any()                     # 柱状带内一个点不剩
    assert xs.max() == 520.0                      # 终端恢复到切线+20 为止
    assert xs.min() == 50.0
    assert all(p["ids"] == [7, 8] for p in pieces)    # 出处原样保留
    assert all(p["y"] == 505.0 for p in pieces)       # 原链 y 键不随碎片重算（load_chains 重并用）


def test_band_split_全带内条目丢弃_带外条目原样():
    inside = {"pts": [[160.0, 500.0], [260.0, 500.0]], "ids": [3], "y": 500.0}
    assert band_split_item(inside, BANDS, 0.0, 2000.0) == []
    west_only = {"pts": [[20.0, 500.0], [90.0, 500.0]], "ids": [4], "y": 500.0}
    got = band_split_item(west_only, BANDS, 0.0, 2000.0)
    assert len(got) == 1 and got[0]["ids"] == [4]


def test_band_split_全孤点条目共线保留():
    # 带内点两侧各剩 1 点 → 两个单点碎片；追踪既然并成一条链，切带不比不切严，共线即留
    it = {"pts": [[50.0, 500.0], [200.0, 500.0], [490.0, 500.0]], "ids": [9], "y": 500.0}
    got = band_split_item(it, BANDS, 0.0, 2000.0)
    assert len(got) == 2
    assert sorted(p["pts"][0][0] for p in got) == [50.0, 490.0]


def test_band_split_孤点碎片贴趋势留_离趋势剔():
    # 西侧 5 点真行 + 带内 1 点(切掉) + 带东孤点：贴趋势（T 接行尾/带缘骑点）留
    it = {"pts": [[float(x), 500.0] for x in range(50, 100, 10)]
          + [[200.0, 500.0], [300.0, 502.0]],
          "ids": [11], "y": 500.0}
    got = band_split_item(it, BANDS, 0.0, 2000.0)
    assert len(got) == 2 and got[-1]["pts"][0][0] == 300.0
    # 离趋势 60px（>SINGLETON_FIT_TOL=25）的是骑带缘台阶点，剔
    it2 = {"pts": [[float(x), 500.0] for x in range(50, 100, 10)]
           + [[200.0, 500.0], [300.0, 560.0]],
           "ids": [12], "y": 500.0}
    got2 = band_split_item(it2, BANDS, 0.0, 2000.0)
    assert len(got2) == 1 and got2[0]["x"] == (50.0, 90.0)


def test_band_split_水文带深入带内的终端不还():
    # 行尾扎进水文带 200px（真墨迹但用户口径=带内不许有）：只还贴线 20px，深的不还
    it = {"pts": [[float(x), 500.0] for x in range(50, 460, 10)]
          + [[510.0, 500.0], [700.0, 500.0]],
          "ids": [13], "y": 500.0}
    got = band_split_item(it, BANDS, 0.0, 2000.0)
    xs = np.vstack([p["pts"] for p in got])[:, 0]
    assert xs.max() == 510.0                      # 510 贴线(506)还回，700 不还


def test_band_split_行界窗口裁剪仍生效():
    it = {"pts": [[float(x), 500.0] for x in range(50, 700, 10)], "ids": [1], "y": 500.0}
    pieces = band_split_item(it, BANDS, tab_l=60.0, tab_r=600.0)
    assert min(p["x"][0] for p in pieces) == 60.0     # 左界收到窗口
    assert all(p["x"][1] <= 600.0 for p in pieces)


def test_band_split_穿到右框的框线豁免水文带():
    # 表框线（顶/底边）真墨迹贯穿水文带：条目右端到 tab_r 不足 HYDRO_FRAME_KEEP 即豁免，
    # 水文带点保留；柱状带照切（图案污染不分框线不框线）
    it = {"pts": [[float(x), 500.0] for x in range(50, 1991, 10)], "ids": [5], "y": 500.0}
    pieces = band_split_item(it, BANDS, tab_l=0.0, tab_r=2000.0)
    assert len(pieces) == 2                       # 只剩柱状带一个口子
    tail = np.asarray(pieces[1]["pts"])[:, 0]
    assert (tail >= 520.0).any()                  # 水文带西缘以右的点还在
    inside_c = _in_band_mask(tail, np.asarray(pieces[1]["pts"])[:, 1], [(WEST, EAST)])
    assert not inside_c.any()                     # 柱状带内一个点不剩
    assert pieces[1]["x"][1] == 1990.0
    # 普通行（右端离右框远）：止步水文带切线+恢复深度
    it2 = {"pts": [[float(x), 500.0] for x in range(50, 700, 10)], "ids": [6], "y": 500.0}
    pieces2 = band_split_item(it2, BANDS, tab_l=0.0, tab_r=2000.0)
    assert np.asarray(pieces2[-1]["pts"])[:, 0].max() <= HYDRO[0, 1] + BAND_PAD + HYDRO_RESTORE


def test_continue_below_近锚抄形_远锚按右框平移():
    # 近锚（断口处间距 98 ≤ 0.5×wide）：照抄锚形 + 断口平移
    chain = np.array([[0.0, 1000.0], [100.0, 1000.0]], float)
    near = np.array([[0.0, 900.0], [2000.0, 940.0]], float)
    fr = (None, np.array([[0.0, 2000.0], [2000.0, 2000.0]], float))
    got = continue_below(chain, [near], 2000.0, fr, wide=2000.0)
    assert got[-1][0] == 2000.0 and got[-1][1] == 1038.0      # 锚形 940 + 平移 98
    # 远锚（断口处间距 1200 > 0.5×wide）：不抄形，按右框 − 实测段"到框间距"中位数续
    far = np.array([[0.0, 2200.0], [2000.0, 2200.0]], float)
    got2 = continue_below(chain, [far], 2000.0, fr, wide=2000.0)
    # 实测段到右框间距 = 1000，尾段 x = 右框(y) − 1000（右框此例竖直 x=2000）
    assert got2[-1][0] == 2000.0 and got2[-1][1] == 1000.0
    # 无右框退回旧抄法（锚形平移：2200 − 1200 = 1000，接续本链）
    got3 = continue_below(chain, [far], 2000.0, None, wide=2000.0)
    assert got3[-1][0] == 2000.0 and got3[-1][1] == 1000.0
