# -*- coding: utf-8 -*-
"""行判定里的表宽(table_x) 与 6a4 闭合外框的左右边 对不对得上。"""
import json, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from src.core import paths
from src.table.track_rows import edge_at

print(f"{'张':<6}{'table_x':>16}{'外框左':>8}{'外框右':>8}{'左差':>7}{'右差':>7}")
dl = []; dr = []
for p in sorted(paths.RUNS_DIR.glob('table_reconstruct/*_行判定.json')):
    code = p.stem.split('图')[1].split('_')[0]
    stem = f"钻孔柱状图{code}"
    rd = json.loads(p.read_text(encoding='utf-8')); tl, tr = rd['table_x']
    fr = json.load(open(p.parent / f'{stem}_闭合外框.json', encoding='utf-8'))
    L = np.array([[q[1], q[0]] for q in fr['left']['pts']], float)
    R = np.array([[q[1], q[0]] for q in fr['right']['pts']], float)
    ys = np.linspace(max(L[0, 0], R[0, 0]), min(L[-1, 0], R[-1, 0]), 100)
    l = float(np.median([edge_at(L, y) for y in ys]))
    r = float(np.median([edge_at(R, y) for y in ys]))
    dl.append(tl - l); dr.append(tr - r)
    print(f'{code:<6}{str(tl) + "~" + str(tr):>16}{l:>8.0f}{r:>8.0f}{tl - l:>7.0f}{tr - r:>7.0f}')
print('左差 中位/最小/最大', round(float(np.median(dl))), round(min(dl)), round(max(dl)),
      '| 右差 中位/最小/最大', round(float(np.median(dr))), round(min(dr)), round(max(dr)))
