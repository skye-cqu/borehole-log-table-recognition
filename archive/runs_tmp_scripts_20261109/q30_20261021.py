
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table import track_rows as tr
D=paths.RUNS_DIR/'table_整合_全量_20261011'
stem='钻孔柱状图1023'
rd=json.load(open(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_行判定.json',encoding='utf-8'))
rows=rd['rows']
print('行数',len(rows),' keys',list(rows[0].keys()))
print('poly 样例:',str(rows[0]['poly'])[:200])
lo=None
for i,r in enumerate(rows):
    y=tr.row_y(r,1200)
    if lo is None and y>=8735: lo=i
print('y>=8735 起始行号:',lo)
p=D/f'{stem}.json'
print('交付 json:',p.exists())
if not p.exists():
    print([c.name for c in D.glob('*1023*')])

