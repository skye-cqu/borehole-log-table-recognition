# -*- coding: utf-8 -*-
"""第0期只读测量：行线检测参数的实测依据（先验证后实现，不改动任何产物）。

测两件事：
  1. 阶段4 high+horizontal 候选的角度/挠度/长度分布 —— 行线到底有多倾斜/多弯，
     决定 DP 搜索窗与"分块去倾"的必要性；
  2. 拉直图的墨迹灰度统计 —— 背景水平、墨迹浓度，决定 DP 代价函数的标定。
输出 runs/table_reconstruct/行线参数实测.json + 控制台摘要。只读，不写图片。
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

CD = paths.CANDIDATE_COORD_DIR
TR = paths.RUNS_DIR / 'table_reconstruct'
PILOTS = ('1015', '1035', '1017')


def pct(a, ps=(10, 50, 90, 99)):
    return {f'p{p}': round(float(np.percentile(a, p)), 4) for p in ps}


def main():
    out = {}
    for n in PILOTS:
        stem = '钻孔柱状图' + n
        j = json.load(open(CD / f'{stem}.json', encoding='utf-8'))
        hs = [l for l in j['lines']
              if l.get('label') == 'high' and l.get('direction') == 'horizontal']
        rec = {'n_high_horizontal': len(hs)}
        if hs:
            L = np.array([float(l['length']) for l in hs])
            A = np.array([abs(float(l['angle'])) for l in hs])
            P = np.array([abs(float(l['pca_angle'])) for l in hs])
            D = np.array([abs(float(l['deflection'])) for l in hs])
            rec['length'] = pct(L)
            rec['abs_angle'] = pct(A, (50, 90, 99, 100))
            rec['abs_pca_angle'] = pct(P, (50, 90, 99, 100))
            rec['abs_deflection'] = pct(D, (50, 90, 99, 100))
            rec['angle_unit_guess'] = 'rad' if np.median(A) < 0.5 else 'deg'
        g = cv2.imread(str(TR / f'{stem}_表格拉直.png'), cv2.IMREAD_GRAYSCALE)
        rec['straight_gray'] = {
            'size': [int(g.shape[1]), int(g.shape[0])],
            'bg_median': round(float(np.median(g)), 1),
            'bg_p25': round(float(np.percentile(g, 25)), 1),
            'dark_p10_of_ink': round(float(np.percentile(g[g < 150], 10)), 1) if (g < 150).any() else None,
            'frac_below_150': round(float((g < 150).mean()), 4),
            'frac_below_100': round(float((g < 100).mean()), 4),
        }
        out[stem] = rec
    dest = TR / '行线参数实测.json'
    json.dump(out, open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print('->', dest)


if __name__ == '__main__':
    main()
