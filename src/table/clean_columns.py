# -*- coding: utf-8 -*-
"""阶段6g：图片裁剪与数据清洗（用户 2026-09-05 指示：删除"柱状"和"简易水文曲线"两列）。

在 {stem}_表格矫正.png 上定三个边界（矫正系，含 25px margin）：
  sem7 = 真厚|柱状、sem8 = 柱状|岩性、sem9 = 岩性|水文。
删除区间 = [sem7, sem8)（柱状条带）与 (sem9, 末尾]（水文列），拼接结果只含 8 个保留列：
  clean = hstack(rect[:, :x7], rect[:, x8:x9+1])   （保留 sem8 线作为拼接缝、sem9 线作为东边界）

边界来源与可靠性分级：
  ① detected：本图 lines_rect.columns 中距模板相对位置最近、且在合理区间内的检出线；
  ② band 几何：sem7/sem8 用"柱状带宽=模板值"互检，超差一侧按另一侧+模板带宽推算；
  ③ snap：推算边界在 ±40px 内吸附矫正图墨迹最强竖线（中段 60% 行的暗度列剖面），
     无显著峰则保留推算值并落账 warned。
坐标换算（{stem}_清洗映射.json）：分段规则
  u_rect = u_clean (u_clean <= x7)；= u_clean + (x8 - x7) (u_clean >= x7)；v 相同；
  再经 H_rect_to_src 回原图。并给出左右两片的合成矩阵 H_clean_to_src_L/R。
输出 {stem}_表格清洗.png、{stem}_表格清洗_预览.jpg、{stem}_清洗映射.json、清洗映射汇总.json。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

MARGIN = 25
# 模板相对位置（30 张同版印张，来自全量矫正映射统计；sem 只用 7/8/9）
T = {7: 0.2109, 8: 0.2883, 9: 0.7864}
BAND_W = T[8] - T[7]          # 柱状带宽（相对）
SANITY = {7: (0.15, 0.26), 8: (0.25, 0.33), 9: (0.74, 0.82)}
SNAP_WIN = 40.0
BAND_TOL = 60.0               # 柱状带宽互检容差（px）
PREVIEW_SCALE = 2


def snap_to_ink(rect_gray, x_est, H_img):
    """在 ±SNAP_WIN 内吸附最强墨迹竖线（中段 60% 行暗度列剖面）。"""
    h = rect_gray.shape[0]
    band = rect_gray[int(h * 0.2):int(h * 0.8), :].astype(float)
    strength = (255.0 - band).sum(axis=0)
    lo = max(0, int(x_est - SNAP_WIN))
    hi = min(len(strength) - 1, int(x_est + SNAP_WIN))
    if hi <= lo:
        return x_est, 0.0
    seg = strength[lo:hi + 1]
    base = float(np.median(strength))
    pk = int(np.argmax(seg))
    peak = float(seg[pk])
    if peak - base < 0.10 * (hi - lo) * 255:
        return x_est, peak - base
    return lo + pk, peak - base


def process(stem):
    m = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_矫正映射.json', encoding='utf-8'))
    W, Hh = m['rect_size']
    img_w = W + 2 * MARGIN
    rect = cv2.imread(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_表格矫正.png'),
                      cv2.IMREAD_COLOR)
    rect_gray = cv2.imread(str(paths.RAW_DIR / f'{stem}.JPG'), cv2.IMREAD_GRAYSCALE)
    H_rs = np.asarray(m['H_rect_to_src'], np.float64)
    H_sr = np.asarray(m['H_src_to_rect'], np.float64)
    # 矫正图的灰度（用于吸附）直接由矫正图取，省一次重投影
    rect_gray = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY)

    cols = sorted(m['lines_rect']['columns'],
                  key=lambda c: float(np.median([p[0] for p in c['pts']])))
    mids = [float(np.median([p[0] for p in c['pts']])) for c in cols]

    x = {}
    src = {}
    for sid, lo_hi in SANITY.items():
        lo, hi = lo_hi[0] * W + MARGIN, lo_hi[1] * W + MARGIN
        cands = [u for u in mids if lo <= u <= hi]
        if cands:
            t_abs = T[sid] * W + MARGIN
            x[sid] = min(cands, key=lambda u: abs(u - t_abs))
            src[sid] = 'detected'
        else:
            src[sid] = 'missing'
    # band 几何互检/补齐
    if 8 in x and 7 in x and abs(x[8] - x[7] - BAND_W * W) > BAND_TOL:
        bad = 7 if abs(x[7] - (T[7] * W + MARGIN)) > abs(x[8] - (T[8] * W + MARGIN)) else 8
        src[bad] = 'band_fix'
        x[bad] = (x[8] - BAND_W * W) if bad == 7 else (x[7] + BAND_W * W)
    if 9 in x and 8 in x and abs((x[9] - x[8]) - (T[9] - T[8]) * W) > 3 * BAND_TOL:
        pass  # 岩性区宽度过大不作硬检（1042 等版式漂移）
    if src.get(8) == 'missing':
        # 优先近邻推算（sem7+带宽），次选 sem9-模板跨度；1032 实证 sem9 跨度会偏
        if 7 in x:
            x[8] = x[7] + BAND_W * W
        elif 9 in x:
            x[8] = x[9] - (T[9] - T[8]) * W
        src[8] = 'template'
    if src.get(7) in ('missing', 'band_fix'):
        x[7] = x[8] - BAND_W * W
        src[7] = 'template' if src[7] == 'missing' else 'band_fix'
    if src.get(9) == 'missing' and 8 in x:
        x[9] = x[8] + (T[9] - T[8]) * W
        src[9] = 'template'

    # 推算/超差边界吸附墨迹
    for sid in (7, 8, 9):
        if sid in x and src[sid] in ('missing', 'template', 'band_fix'):
            xs, strength = snap_to_ink(rect_gray, x[sid], Hh)
            if strength > 0:
                x[sid] = float(xs)
                src[sid] += '+snapped'
            else:
                src[sid] += '+no_peak'

    x7, x8, x9 = int(round(x[7])), int(round(x[8])), int(round(x[9]))
    x7 = min(max(x7, 1), x8 - 2)
    x8 = min(max(x8, x7 + 2), x9 - 2)
    x9 = min(max(x9, x8 + 2), img_w - 1)

    clean = np.hstack([rect[:, :x7], rect[:, x8:x9 + 1]])
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_表格清洗.png'),
                clean, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    pv = cv2.resize(clean, (clean.shape[1] // PREVIEW_SCALE, clean.shape[0] // PREVIEW_SCALE),
                    interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_表格清洗_预览.jpg'),
                pv, [cv2.IMWRITE_JPEG_QUALITY, 85])

    shift = x8 - x7
    # 分片合成矩阵：clean → src
    T_R = np.array([[1, 0, float(shift)], [0, 1, 0], [0, 0, 1]], np.float64)
    H_clean_src_L = H_rs
    H_clean_src_R = T_R @ H_rs

    mapping = {
        'image': stem,
        'clean_size': [int(clean.shape[1]), int(clean.shape[0])],
        'rect_size': [W, Hh], 'margin': MARGIN,
        'separators_rect': {f'sem{sid}': {'u_rect': round(x[sid], 1), 'source': src.get(sid)}
                            for sid in (7, 8, 9)},
        'removed_bands_rect': [[x7, x8], [x9 + 1, img_w - 1]],
        'rule': 'u_rect = u_clean (u_clean <= %d)；= u_clean + %d (u_clean >= %d)；v 相同；'
                'src = H_rect_to_src·[u_rect,v,1]' % (x7, shift, x7),
        'H_rect_to_src': np.round(H_rs, 8).tolist(),
        'H_clean_to_src_L': np.round(H_clean_src_L, 8).tolist(),
        'H_clean_to_src_R': np.round(H_clean_src_R, 8).tolist(),
        'boundary_switch_u_clean': x7,
        'retained_separators_clean': {
            'west_edge': 0,
            'sem1..sem6': 'u_clean = u_rect（未动）',
            'sem8(柱状|岩性→新缝)': x7,
            'sem9(岩性|水文→东界)': x9 - shift,
        },
    }
    json.dump(mapping, open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_清洗映射.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)
    return {'x7': x7, 'x8': x8, 'x9': x9, 'src': {k: src.get(k) for k in (7, 8, 9)},
            'clean_w': int(clean.shape[1])}


def main():
    only = sys.argv[1:] or sorted('%d' % i for i in range(1015, 1045))
    summary = {}
    for n in only:
        stem = '钻孔柱状图' + n
        r = process(stem)
        print(n, 'x7=%d x8=%d x9=%d clean_w=%d src=%s' % (r['x7'], r['x8'], r['x9'],
                                                          r['clean_w'], r['src']), flush=True)
        summary[n] = r
    json.dump(summary, open(paths.RUNS_DIR / 'table_reconstruct' / '清洗映射汇总.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
