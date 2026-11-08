
# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, '.')
from src.core import paths
D = paths.RUNS_DIR / 'table_reconstruct'
stem = '钻孔柱状图1023'
rj = json.load(open(D / (stem + '_行判定.json'), encoding='utf-8'))
print('top keys:', list(rj.keys()))
for k, v in rj.items():
    if isinstance(v, list):
        print('  %s: list[%d]' % (k, len(v)))
    else:
        print('  %s: %s' % (k, str(v)[:120]))
rows = rj.get('rows') or []
if rows:
    print('row0 keys:', list(rows[0].keys()))
    print('row0 sample:', json.dumps(rows[0], ensure_ascii=False)[:600])
    print('rowN sample:', json.dumps(rows[-1], ensure_ascii=False)[:600])
