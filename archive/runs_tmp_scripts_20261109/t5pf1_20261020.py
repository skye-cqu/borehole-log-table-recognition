
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
    # predicted x by linear fit of last 8 points
    k=min(8,len(sy)); A=np.polyfit(sy[-k:],sx[-k:],1)
    hi=sy.max()
    ylo=int(min(hi+1,y1)); yhi=int(min(y1,H-1))
    if yhi<=ylo:
        print(s,side,'no gap'); continue
    hits=[];preds=[]
    for y in range(ylo,yhi+1,5):
        px=float(np.polyval(A,y)); preds.append(px)
        xi=int(round(px)); a=max(0,xi-15); b=min(W,xi+16)
        seg=gray[y,a:b]
        hits.append(int(seg.min())<160)
    # also: what's the x of nearest dark column in the gap, ignoring prediction
    print(s,side,'gap_y',ylo,yhi,'len',yhi-ylo,'predx',round(float(np.mean(preds))),'inkhit',round(sum(hits)/max(1,len(hits)),3),'H',H,'W',W)
