
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
from src.table.era_chars import _band_y, _era_ink_span, _extend_era_bounds
import cv2
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1030'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
midx=sum(rd['table_x'])/2.0
rd['rows']=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
hm2=_extend_era_bounds(hm,gray,float(max(row_y(r,midx) for r in rd['rows'])))
sp_l=hm2['sep_pts'][hm2['keep'][0]['left_sep']]; sp_r=hm2['sep_pts'][hm2['keep'][0]['right_sep']]
ys=[row_y(r,midx) for r in rd['rows']]
y0,y1=min(ys),max(ys)
ink=_era_ink_span(hm2,gray)
print('ink span',ink,'data',y0,y1)
lo=max(y0,float(ink[0])); hi=min(y1,float(ink[1]))
xm=(lo+hi)/2
xl=float(np.interp(xm,sp_l['ys'],sp_l['xs'])); xr=float(np.interp(xm,sp_r['ys'],sp_r['xs']))
print('band',xl,xr,'at y',xm)
prev=None
for i,r in enumerate(rd['rows']):
    yb=_band_y(r,xl,xr)
    if yb is None: continue
    if prev is not None and yb-prev<8.0:
        print('VIOL row%d yb=%.1f prev=%.1f gap=%.1f'%(i,yb,prev,yb-prev))
    prev=yb
