
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
from src.table.era_chars import era_strip, _extend_era_bounds
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))
print('stem         bandW  rows_ink_frac  max_col_frac  verdict')
for stem in stems:
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    k0=hm['keep'][0]; n=len(hm['sep_pts'])
    if not (0<=k0['left_sep']<n and 0<=k0['right_sep']<n):
        print('%-12s N/A'%stem.replace('钻孔柱状图','')); continue
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    h2=_extend_era_bounds(hm,gray,float(max(row_y(r,midx) for r in rows)))
    sl=h2['sep_pts'][k0['left_sep']]; sr=h2['sep_pts'][k0['right_sep']]
    band,ys,x0i=era_strip(gray,sl,sr,rows)
    if band.size==0:
        print('%-12s EMPTY'%stem.replace('钻孔柱状图','')); continue
    rf=float((band.sum(axis=1)>2).mean())
    cf=float(band.sum(axis=0).max()/band.shape[0])
    print('%-12s %5d  %8.3f  %8.3f  %s'%(stem.replace('钻孔柱状图',''),band.shape[1],rf,cf,'FAIL' if rf>0.85 else 'ok'))
