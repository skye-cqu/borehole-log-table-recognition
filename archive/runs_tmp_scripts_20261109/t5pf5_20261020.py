
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
from src.table.era_chars import _extend_era_bounds
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))
print('stem         w_p10  w_p50  w_p90  ratio  jump_max  verdict')
for stem in stems:
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    k0=hm['keep'][0]; n=len(hm['sep_pts'])
    if not (0<=k0['left_sep']<n and 0<=k0['right_sep']<n):
        print('%-12s NO ERA COLUMN'%stem.replace('钻孔柱状图','')); continue
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    h2=_extend_era_bounds(hm,gray,float(max(row_y(r,midx) for r in rows)))
    sp_l=h2['sep_pts'][k0['left_sep']]; sp_r=h2['sep_pts'][k0['right_sep']]
    y0=max(sp_l['ys'][0],sp_r['ys'][0]); y1=min(sp_l['ys'][-1],sp_r['ys'][-1])
    ys=np.arange(y0,y1,5.0)
    w=np.array([float(np.interp(y,sp_r['ys'],sp_r['xs']))-float(np.interp(y,sp_l['ys'],sp_l['xs'])) for y in ys])
    p10,p50,p90=np.percentile(w,10),np.median(w),np.percentile(w,90)
    ratio=p90/max(1e-6,p10)
    d=np.abs(np.diff(w)); jm=float(d.max()) if len(d) else 0.0
    print('%-12s %5.1f %5.1f %5.1f %6.2f %8.1f  %s'%(stem.replace('钻孔柱状图',''),p10,p50,p90,ratio,jm,'FAIL' if ratio>1.3 else 'ok'))
