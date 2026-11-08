
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))
# PF3 sanity: for each figure list rows flagged with era=full, check band y spacing using _band_y
from src.table.track_rows import row_y
from src.table.era_chars import _band_y, _extend_era_bounds, _era_ink_span
import cv2
print('stem  n_era_rows  min_gap_band_y  viol(8px)')
for stem in stems:
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    k0=hm['keep'][0]; n=len(hm['sep_pts'])
    if not (0<=k0['left_sep']<n and 0<=k0['right_sep']<n):
        print('%-14s NO ERA'%stem.replace('钻孔柱状图','')); continue
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    hm2=_extend_era_bounds(hm,gray,float(max(row_y(r,midx) for r in rows)))
    sp_l=hm2['sep_pts'][k0['left_sep']]; sp_r=hm2['sep_pts'][k0['right_sep']]
    ys=[row_y(r,midx) for r in rows]
    ink=_era_ink_span(hm2,gray)
    y0,y1=min(ys),max(ys)
    if ink: y0,y1=max(y0,float(ink[0])),min(y1,float(ink[1]))
    xm=(y0+y1)/2
    xl=float(np.interp(xm,sp_l['ys'],sp_l['xs'])); xr=float(np.interp(xm,sp_r['ys'],sp_r['xs']))
    era=[(i,r) for i,r in enumerate(rows) if r.get('era')]
    bz=[(i,_band_y(r,xl,xr)) for i,r in era]
    bz=[(i,b) for i,b in bz if b is not None]
    gaps=[bz[k+1][1]-bz[k][1] for k in range(len(bz)-1)]
    mg=min(gaps) if gaps else 0
    v=sum(1 for g in gaps if g<8.0)
    print('%-14s %5d  %8.1f  %d'%(stem.replace('钻孔柱状图',''),len(era),mg,v))
