
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
for s,y0,y1 in [('1029',20280,20500),('1032',21120,21860),('1017',9200,9400)]:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    dy1=int(max(ys))
    k0=hm['keep'][0]; li,ri=k0['left_sep'],k0['right_sep']
    n=len(hm['sep_pts'])
    sp_l=hm['sep_pts'][li] if 0<=li<n else None
    sp_r=hm['sep_pts'][ri] if 0<=ri<n else None
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    print('===',s,'data_y1',dy1)
    for y in range(y0,min(y1,H-1),10):
        xl=float(np.interp(y,sp_l['ys'],sp_l['xs'])) if sp_l else 0.0
        xr=float(np.interp(y,sp_r['ys'],sp_r['xs'])) if sp_r else float(W)
        a,b=int(xl)+12,int(xr)-12
        dk=np.where(gray[y,a:b]<150)[0] if b>a else []
        if len(dk): print('   y=%d w=%d dark=%d xs=%s'%(y,b-a,len(dk),[a+int(k) for k in dk[:10]]))
