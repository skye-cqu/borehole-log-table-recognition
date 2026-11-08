
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
cases=[('1017','right_sep'),('1020','right_sep'),('1023','left_sep'),('1025','right_sep'),('1028','left_sep'),('1032','left_sep'),('1032','right_sep')]
for s,side in cases:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    y0,y1=min(ys),max(ys)
    sp=hm['sep_pts'][hm['keep'][0][side]]
    sy=np.asarray(sp['ys'],float); sx=np.asarray(sp['xs'],float)
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    lo=sy.max(); ya=int(min(lo+2,y1)); yb=int(min(y1,H-1))
    if yb<=ya: print(s,side,'nogap'); continue
    strip=gray[ya:yb+1,:]
    dark=(strip<160).mean(axis=0)   # per-x vertical dark fraction within gap
    # find candidate columns with high dark fraction
    idx=np.argsort(dark)[::-1][:12]
    cands=sorted([(int(i),round(float(dark[i]),3)) for i in idx if dark[i]>0.5])
    # nearest to predicted
    px=float(np.interp(lo,sy,sx))
    print(s,side,'gap',ya,yb,'len',yb-ya,'predx',round(px,1),'inkcols>0.5:',cands[:8])
