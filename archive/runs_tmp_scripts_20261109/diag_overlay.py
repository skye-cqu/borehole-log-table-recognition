# -*- coding: utf-8 -*-
"""可视化诊断：把问题控制线画回矫正图的高清裁片，供肉眼判断哪条轨是真线。

用法: python diag_overlay.py <stem数字> <区域> [y起点]
区域: west(左缘0-170) east(右缘) col7 (1042专用 x 240-560)
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
OUT = paths.RUNS_DIR / 'tmp' / 'diag_crop'
OUT.mkdir(parents=True, exist_ok=True)

n = sys.argv[1]
region = sys.argv[2]
y0_arg = int(sys.argv[3]) if len(sys.argv) > 3 else None
stem = '钻孔柱状图' + n
m = json.load(open(TR / f'{stem}_矫正映射.json', encoding='utf-8'))
img = cv2.imread(str(TR / f'{stem}_表格矫正.png'))
H_img, W_img = img.shape[:2]

bands = [(0, 2600), (2600, 5200), (5200, 7800), (7800, 10400),
         (10400, 13000), (13000, 15600), (15600, H_img)]
if y0_arg is not None:
    bands = [(y0_arg, min(H_img, y0_arg + 2600))]

for bi, (y0, y1) in enumerate(bands):
    vis = img[y0:y1].copy()
    if region == 'west':
        x0, x1 = 0, 170
        poly = m['lines_rect']['sides']['left']
        cols = [c for c in m['lines_rect']['columns'] if np.median([p[0] for p in c['pts']]) < 600]
        colors = {c['index']: (0, 165, 255) for c in cols}
    elif region == 'east':
        x0, x1 = W_img - 170, W_img
        poly = m['lines_rect']['sides']['right']
        cols = []
    else:  # col7 区
        x0, x1 = 240, 580
        poly = None
        cols = [c for c in m['lines_rect']['columns'] if 5 <= c['index'] <= 8]
        colors = {c['index']: (0, 165, 255) for c in cols}
    piece = vis[:, x0:x1].copy()
    if poly is not None:
        pts = np.asarray(poly, np.int32).reshape(-1, 1, 2)
        cv2.polylines(piece, [pts], False, (0, 0, 255), 2, cv2.LINE_AA)
    for c in cols:
        pts = np.asarray(c['pts'], np.int32).reshape(-1, 1, 2)
        cv2.polylines(piece, [pts], False, colors.get(c['index'], (0, 255, 0)), 2, cv2.LINE_AA)
    # 每隔 200px 画 y 参考线
    for yy in range(0, piece.shape[0], 200):
        cv2.line(piece, (0, yy), (40, yy), (255, 0, 255), 1)
        cv2.putText(piece, str(y0 + yy), (2, yy + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    scale = 1 if piece.shape[1] <= 700 else 700 / piece.shape[1]
    if scale != 1:
        piece = cv2.resize(piece, (int(piece.shape[1] * scale), int(piece.shape[0] * scale)),
                           interpolation=cv2.INTER_NEAREST)
    out = OUT / f'ov_{stem}_{region}_y{y0}.png'
    cv2.imwrite(str(out), piece)
    print(out)
