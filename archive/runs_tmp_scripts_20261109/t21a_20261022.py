
# -*- coding: utf-8 -*-
"""列线"混线"检测: 每条列分隔线的 segment_ids 是否来自两条不同物理线。

判据: 同一列的竖向候选段按中位 x 聚类, 若出现 |dx| > XCLUST 的第二个簇,
      说明该列的段集合混入了另一条物理线。
"""
import sys, json, collections
sys.path.insert(0, '.')
import numpy as np
from src.core import paths

XCLUST = 20.0
D = paths.RUNS_DIR / 'table_reconstruct'

def seg_info(code):
    stem = '钻孔柱状图' + code
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
    lines = cj['lines']
    cnt = collections.Counter((l.get('direction'), l.get('label')) for l in lines)
    return stem, lines, cnt

for code in ['1023', '1019', '1042']:
    stem, lines, cnt = seg_info(code)
    print('===', code, '候选段组合分布:', dict(cnt))
    print('   段字段样例:', {k: (str(v)[:60]) for k, v in lines[0].items()})
