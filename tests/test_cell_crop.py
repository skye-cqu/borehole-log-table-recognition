# -*- coding: utf-8 -*-
"""_crop_cell:单元格四边界各按折线逐像素取格,不再用直线矩形。

斜边界格角上的字必须保留(直线矩形按中心取标量会切掉),界外墨必须置白,
行界折线出窗口取近端点值(禁外推,1035 缺陷守卫)。
"""
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.table.reconstruct_excel import _crop_cell  # noqa: E402


def _cell():
    gray = np.full((200, 200), 255, np.uint8)
    top = {"poly": [[20, 40], [180, 60]]}          # 顶界向右下斜,中心高 y=50
    bot = {"poly": [[20, 160], [180, 140]]}        # 底界向右上斜,中心低 y=150
    bx_l = lambda y: 20.0 + 0.02 * (np.asarray(y, float) - 100)   # 左界微斜
    bx_r = lambda y: 160.0                          # 右界竖直
    # 粗框 = 直线矩形口径(中心标量):x[20,160] y[50,150]
    return gray, top, bot, bx_l, bx_r, (20, 160, 50, 150)


def test_斜边界格角的字保留_界外墨置白():
    gray, top, bot, bx_l, bx_r, (x0, x1, y0, y1) = _cell()
    gray[45:48, 24:30] = 0      # 字A:左上格角,真格内(yt(30)+3=44.25≤45)、直线矩形外(y<50,x<…)
    gray[95:105, 80:120] = 0    # 字B:格中央
    gray[95:105, 8:16] = 0      # 字C:左界(bx_l(100)=20)之外
    gray[144:149, 150:158] = 0  # 字D:右下,底界 yb(150)-3≈140.8 之上之外(邻格墨)
    crop = _crop_cell(gray, top, bot, bx_l, bx_r, x0, x1, y0, y1)
    assert crop is not None
    assert (crop == 0).sum() >= 3 * 6 + 10 * 40        # A、B 完整保留
    assert crop[95 - 10:105 - 10, 8:16].min() == 255   # C 置白(窗口 ya=10)
    assert crop[144 - 10:149 - 10, 150:158].min() == 255   # D 置白


def test_行界折线出窗口取近端不外推():
    gray, top, bot, bx_l, bx_r, (x0, x1, y0, y1) = _cell()
    short = {"poly": [[60, 56], [140, 40]]}            # 斜折线只盖 x∈[60,140]
    gray[59:63, 24:30] = 0                             # x=24 处:近端值 y=56 → 字在界下;
    crop = _crop_cell(gray, short, bot, bx_l, bx_r, x0, x1, y0, y1)
    assert crop is not None                            # 线性外推会推出 y≈63 把字切掉
    assert (crop == 0).sum() >= 4 * 6


def test_空格返回None():
    gray, top, bot, bx_l, bx_r, (x0, x1, y0, y1) = _cell()
    tight_l = lambda y: 160.0                          # 左界=右界 → 无内容空间
    assert _crop_cell(gray, top, bot, tight_l, bx_r, x0, x1, y0, y1) is None
