
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
sp=hm['sep_pts'][10]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
print('sep#10 表底以下(y>11947)是否真有墨:')
for y in (11960,12050,12150,12250,12350,12440,12480):
    xp=float(tr.edge_at(a,y))
    lo=max(0,int(xp)-8); hi=min(W,int(xp)+9)
    print('  y=%5d x=%7.1f  窗内有竖墨=%s'%(y,xp,bool(vv[y,lo:hi].any())))
print()
print('sep#10 上端 y<569 (顶框以上):')
for y in (555,560,568):
    xp=float(tr.edge_at(a,y))
    lo=max(0,int(xp)-8); hi=min(W,int(xp)+9)
    print('  y=%5d x=%7.1f  窗内有竖墨=%s'%(y,xp,bool(vv[y,lo:hi].any())))

