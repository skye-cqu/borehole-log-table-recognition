
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
# use EXACTLY yard_cols.py's method but on sep_pts
SAMPLE=60; VLEN=40; CLOSE=25; SEARCH=60; TOL=5.0
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)*255
v=cv2.morphologyEx(bw,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,VLEN)))
v=cv2.morphologyEx(v,cv2.MORPH_CLOSE,np.ones((CLOSE,1),np.uint8))
H,W=v.shape
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
print('sep  kind   y0     y1     dev%  gap%  (yard_cols 同款算法, 量 sep_pts)')
for i,sp in enumerate(hm['sep_pts']):
    a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
    y0,y1=a[0,0],a[-1,0]
    dev=gap=0
    for y in np.linspace(y0,y1,SAMPLE):
        xi,yi=int(round(tr.edge_at(a,y))),int(round(y))
        if yi<0 or yi>=H: continue
        lo=max(0,xi-SEARCH)
        idx=np.flatnonzero(v[yi,lo:min(xi+SEARCH,W-1)])
        d=float(np.abs(idx+lo-xi).min()) if len(idx) else np.inf
        dev+=TOL<d<=SEARCH
        gap+=d>SEARCH
    print(' #%-3d %-6s %6.0f %6.0f  %5.1f %5.1f'%(i,sp.get('kind'),y0,y1,dev/SAMPLE*100,gap/SAMPLE*100))
