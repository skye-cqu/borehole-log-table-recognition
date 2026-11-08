
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))
def thick(gray,x,y,half=12):
    col=gray[max(0,y-half):y+half+1, max(0,x)]
    dark=col<160
    # run containing center
    c=min(half,len(col)-1)
    if not dark[c]: return 0
    lo=hi=c
    while lo-1>=0 and dark[lo-1]: lo-=1
    while hi+1<len(col) and dark[hi+1]: hi+=1
    return hi-lo+1
print('stem   left_thick  right_thick   (median over 9 samples)')
for stem in stems:
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    k0=hm['keep'][0]; n=len(hm['sep_pts'])
    if not (0<=k0['left_sep']<n and 0<=k0['right_sep']<n):
        print('%-12s N/A'%stem.replace('钻孔柱状图','')); continue
    sl=hm['sep_pts'][k0['left_sep']]; sr=hm['sep_pts'][k0['right_sep']]
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    y0=max(sl['ys'][0],sr['ys'][0]); y1=min(sl['ys'][-1],sr['ys'][-1])
    tl=[];tr=[]
    for y in np.linspace(y0+200,y1-200,9):
        xl=int(np.interp(y,sl['ys'],sl['xs'])); xr=int(np.interp(y,sr['ys'],sr['xs']))
        tl.append(thick(gray,xl,int(y))); tr.append(thick(gray,xr,int(y)))
    print('%-12s %6.1f %10.1f'%(stem.replace('钻孔柱状图',''),np.median(tl),np.median(tr)))
