
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
from openpyxl import load_workbook
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1017','1020','1025','1028','1023']:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    ys=[row_y(r,midx) for r in rows]
    print('===',s,'n_rows',len(rows),'y0',round(ys[0]),'y1',round(ys[-1]))
    for r,y in list(zip(rows,ys))[-4:]:
        xs=[p[0] for p in r['poly']]
        print('   y=%8.1f  x=[%6.0f,%6.0f]  npts=%d'%(y,min(xs),max(xs),len(r['poly'])))
    p=paths.REEMIT_DIR_20261005B/f'{stem}_还原.xlsx'
    if p.exists():
        ws=load_workbook(p).active
        print('   xlsx rows(含表头)',ws.max_row)
