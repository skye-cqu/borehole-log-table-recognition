# -*- coding: utf-8 -*-
"""阶段6f：表格主体提取与矫正（用户 2026-09-05 指示：按闭合外框提取表格主体，
歪斜的旋转变直、不规则补成规则矩形，坐标与原始之间的换算必须保留）。

方法 = 四角透视变换（homography）：{stem}_闭合外框.json 的四角映射到
(margin, margin) 起的规则矩形，宽高取四边实测均值（保持原始像素比例，不缩放）。
透视变换在四角近似矩形的情形下即"旋转+微量剪切校正"；边线中段残余弯曲
（每边 ≤数十 px）按用户指示后续需要可再加网格 unwarp。

坐标换算（存入 {stem}_矫正映射.json，后续一切结构处理都经它回到原图）：
  rect = H_src_to_rect · [x,y,1]^T （齐次，除以 w）
  src  = H_rect_to_src · [u,v,1]^T
同时把闭合外框四边与全部列线（分割线.json）映射到矫正坐标系一并落账，
后续行线/单元格在矫正系里做，端点经 H_rect_to_src 回原图核对。

输出 {stem}_表格矫正.png（纯净图，供 OCR）、{stem}_表格矫正_核对.png
（叠加映射线供人工核验）、{stem}_矫正映射.json、矫正映射汇总.json。"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

MARGIN = 25          # 矫正图四周留白（px），边界线不贴边
CHECK_DOWNSCALE = 2  # 核对图预览缩放


def fit_angle(gp, axis):
    """边线走向角（相对轴线的弧度）。axis=0 横边（相对水平），axis=1 竖边（相对竖直）。"""
    a = gp[:, axis].astype(float)
    c = gp[:, 1 - axis].astype(float)
    k, _ = np.polyfit(a, c, 1)
    return math.atan(k)


def map_pts(H, pts):
    """齐次映射点列 (N,2) → (N,2)。"""
    arr = np.asarray(pts, np.float64).reshape(-1, 1, 2)
    out = cv2.perspectiveTransform(arr, H).reshape(-1, 2)
    return out


def process(stem):
    cf = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_闭合外框.json', encoding='utf-8'))
    d = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_分割线.json', encoding='utf-8'))
    corners = {k: np.asarray(v, np.float64) for k, v in cf['corners'].items()}
    for k in ('TL', 'TR', 'BR', 'BL'):
        if corners.get(k) is None:
            raise ValueError(f'{stem} 角点 {k} 缺失，无法闭合提取')

    # 矫正后尺寸：四边实测均值（保持原始比例）
    w_top = float(np.linalg.norm(corners['TR'] - corners['TL']))
    w_bot = float(np.linalg.norm(corners['BR'] - corners['BL']))
    h_l = float(np.linalg.norm(corners['BL'] - corners['TL']))
    h_r = float(np.linalg.norm(corners['BR'] - corners['TR']))
    W = int(round((w_top + w_bot) / 2))
    Hh = int(round((h_l + h_r) / 2))

    src = np.array([corners['TL'], corners['TR'], corners['BR'], corners['BL']], np.float32)
    dst = np.array([[MARGIN, MARGIN], [MARGIN + W, MARGIN], [MARGIN + W, MARGIN + Hh],
                    [MARGIN, MARGIN + Hh]], np.float32)
    H_sr = cv2.getPerspectiveTransform(src, dst)          # 原图 → 矫正
    H_rs = cv2.getPerspectiveTransform(dst, src)          # 矫正 → 原图

    # 旋转角报告：四边走向角均值（度）
    ang = [fit_angle(np.asarray(cf['top']['pts'], float), 0),
           fit_angle(np.asarray(cf['bottom']['pts'], float), 0),
           fit_angle(np.asarray(cf['left']['pts'], float), 1),
           fit_angle(np.asarray(cf['right']['pts'], float), 1)]
    rot_deg = round(math.degrees(sum(ang) / len(ang)), 3)

    # 提取 + 矫正
    img = cv2.imread(str(paths.RAW_DIR / f'{stem}.JPG'), cv2.IMREAD_COLOR)
    rect = cv2.warpPerspective(img, H_sr, (MARGIN * 2 + W, MARGIN * 2 + Hh),
                               flags=cv2.INTER_LINEAR)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_表格矫正.png'),
                rect, [cv2.IMWRITE_PNG_COMPRESSION, 3])

    # 映射线：闭合外框四边 + 全部列线
    lines_rect = {'sides': {}, 'columns': []}
    for name in ('left', 'right', 'top', 'bottom'):
        lines_rect['sides'][name] = np.round(map_pts(H_sr, cf[name]['pts']), 1).tolist()
    for c in d['lines']:
        if c['kind'] != 'column' or not c.get('pts'):
            continue
        mp = map_pts(H_sr, c['pts'])
        lines_rect['columns'].append({'index': c.get('index'), 'n': len(mp),
                                      'pts': np.round(mp, 1).tolist()})

    # 核对图：映射线叠回矫正图
    chk = rect.copy()
    for name in ('left', 'right', 'top', 'bottom'):
        cv2.polylines(chk, [np.asarray(lines_rect['sides'][name], np.int32).reshape(-1, 1, 2)],
                      False, (255, 0, 0), 5, cv2.LINE_AA)
    for c in lines_rect['columns']:
        cv2.polylines(chk, [np.asarray(c['pts'], np.int32).reshape(-1, 1, 2)],
                      False, (0, 0, 255), 2, cv2.LINE_AA)
    for k, (ux, uy) in (('TL', (MARGIN, MARGIN)), ('TR', (MARGIN + W, MARGIN)),
                        ('BR', (MARGIN + W, MARGIN + Hh)), ('BL', (MARGIN, MARGIN + Hh))):
        cv2.circle(chk, (int(ux), int(uy)), 16, (255, 255, 255), 4, cv2.LINE_AA)
    txt = "rectified: blue=frame  red=columns  white=corners  (u,v)->src via H_rect_to_src"
    cv2.putText(chk, txt, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 6, cv2.LINE_AA)
    cv2.putText(chk, txt, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_表格矫正_核对.png'),
                chk, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    pv = cv2.resize(chk, (chk.shape[1] // CHECK_DOWNSCALE, chk.shape[0] // CHECK_DOWNSCALE),
                    interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_表格矫正_核对_预览.jpg'),
                pv, [cv2.IMWRITE_JPEG_QUALITY, 85])

    mapping = {
        'image': stem,
        'note': 'rect = H_src_to_rect·[x,y,1]（齐次除 w）；src = H_rect_to_src·[u,v,1]；'
                '列线/边线已在 lines_rect 给出矫正系坐标',
        'rect_size': [W, Hh], 'margin': MARGIN, 'rotation_deg': rot_deg,
        'H_src_to_rect': np.round(H_sr, 8).tolist(),
        'H_rect_to_src': np.round(H_rs, 8).tolist(),
        'corners_src': {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in corners.items()},
        'corners_rect': {'TL': [MARGIN, MARGIN], 'TR': [MARGIN + W, MARGIN],
                         'BR': [MARGIN + W, MARGIN + Hh], 'BL': [MARGIN, MARGIN + Hh]},
        'lines_rect': lines_rect,
    }
    json.dump(mapping, open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_矫正映射.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)
    return {'W': W, 'H': Hh, 'rot': rot_deg}


def main():
    only = sys.argv[1:] or sorted('%d' % i for i in range(1015, 1045))
    summary = {}
    for n in only:
        stem = '钻孔柱状图' + n
        r = process(stem)
        print(n, 'rect=%dx%d rot=%+.3f°' % (r['W'], r['H'], r['rot']), flush=True)
        summary[n] = r
    json.dump(summary, open(paths.RUNS_DIR / 'table_reconstruct' / '矫正映射汇总.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
