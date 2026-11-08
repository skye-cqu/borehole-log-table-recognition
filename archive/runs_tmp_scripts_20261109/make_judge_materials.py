# -*- coding: utf-8 -*-
"""为试点/全量验收生成 judge 视觉材料（高清裁片，无预览 JPG）。

每张图输出到 runs/tmp/judge/{stem}/：
  01_清洗总览_半分辨率.png   —— 清洗图 1/2 缩放
  02_切口贴线_矫正系.png     —— 拉直核对图上三个切口 x 三高度的全分辨率合成
  03_拼接缝_清洗系.png       —— 清洗图上 sem8 拼接缝与 sem9 东边界三高度全分辨率合成
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402

TR = paths.RUNS_DIR / 'table_reconstruct'
OUT = paths.RUNS_DIR / 'tmp' / 'judge'

BAND_H = 300   # 裁片半高
CUT_W = 150    # 裁片半宽


def vstack_labeled(pieces, labels):
    seg_h = 22
    total = []
    for p, lb in zip(pieces, labels):
        bar = np.full((seg_h, p.shape[1], 3), 40, np.uint8)
        cv2.putText(bar, lb, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        total += [bar, p]
    return np.vstack(total)


def hstack_labeled(pieces, labels):
    seg_w = 150
    cols = []
    for p, lb in zip(pieces, labels):
        bar = np.full((p.shape[0], seg_w, 3), 40, np.uint8)
        for i, ch in enumerate(lb.split('|')):
            cv2.putText(bar, ch, (4, 24 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 1, cv2.LINE_AA)
        cols.append(np.hstack([bar, p]))
    return np.hstack(cols)


def make(stem):
    # 切口位置从清洗映射取（straight 系）
    cm = json.load(open(TR / f'{stem}_清洗映射.json', encoding='utf-8'))
    seps = cm['separators_straight']
    xs = {k: int(round(v['u_straight'])) for k, v in seps.items()}
    shift = xs['sem8'] - xs['sem7']
    clean_w = cm['clean_size'][0]
    seam_clean, east_clean = xs['sem8'] - shift, xs['sem9'] - shift

    straight = cv2.imread(str(TR / f'{stem}_表格拉直.png'))
    chk = cv2.imread(str(TR / f'{stem}_表格拉直_核对.png'))
    clean = cv2.imread(str(TR / f'{stem}_表格清洗.png'))
    H = straight.shape[0]
    odir = OUT / stem
    odir.mkdir(parents=True, exist_ok=True)

    # 01 清洗总览 半分辨率
    half = cv2.resize(clean, (clean.shape[1] // 2, clean.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(odir / '01_清洗总览_半分辨率.png'), half)

    ys_band = [int(H * f) for f in (0.06, 0.5, 0.94)]
    yl = ['top 6%', 'mid 50%', 'bot 94%']

    def crop_bands(img, xc, half_w=CUT_W):
        pieces = []
        for y in ys_band:
            y0, y1 = max(0, y - BAND_H), min(img.shape[0], y + BAND_H)
            x0, x1 = max(0, xc - half_w), min(img.shape[1], xc + half_w)
            pieces.append(img[y0:y1, x0:x1].copy())
        return pieces

    # 02 三个切口在拉直核对图上的贴线（红竖线=落账目标位置）
    for cut, key in ((xs['sem7'], 'sem7_zhenhou_zhuzhuang'), (xs['sem8'], 'sem8_zhuzhuang_yanxing'),
                     (xs['sem9'], 'sem9_yanxing_shuiwen')):
        cols = hstack_labeled(crop_bands(chk, cut), [f'{key}|{l}' for l in yl])
        cv2.imwrite(str(odir / f'02_切口贴线_{key}.png'), cols)

    # 03 清洗图上的拼接缝（sem8 线）与东边界（sem9 线）
    seam = hstack_labeled(crop_bands(clean, seam_clean), [f'seam(sem8)|{l}' for l in yl])
    east = hstack_labeled(crop_bands(clean, east_clean, half_w=120), [f'east(sem9)|{l}' for l in yl])
    cv2.imwrite(str(odir / '03_拼接缝_清洗系.png'), np.hstack([seam, east]))

    print(stem, '->', odir)


if __name__ == '__main__':
    for n in (sys.argv[1:] or ['1015', '1020', '1042']):
        make('钻孔柱状图' + n)
