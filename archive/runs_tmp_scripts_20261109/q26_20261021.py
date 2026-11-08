
# -*- coding: utf-8 -*-
"""定案图: sep#8 从 y~8660 起跳到"柱状图案内条右边"(绿), 丢弃"柱状格外边界"(蓝)。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'col_crop_20261021'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
def track(x0,y0,y1,tol=4):
    x=float(x0); pts=[]
    for y in range(y0,y1):
        lo=max(0,int(round(x))-tol); hi=min(W,int(round(x))+tol+1)
        idx=np.flatnonzero(vv[y,lo:hi])
        if len(idx): x=float(idx[np.argmin(np.abs(idx+lo-x))]+lo)
        pts.append((y,x))
    return np.array(pts,float)
a7,a8=poly(7),poly(8)
# 两条候选线: 内条右边(153px) 与 格外边界(197px), 各从 sep7 起追
inner=[]; outer=[]
for y in range(8400,11960,1):
    x7=float(tr.edge_at(a7,y))
    inner.append((y,float(tr.edge_at(track(x7+153,y,y+1)[0:1] if False else np.array([[y,x7+153]]),y))))
# 简单点: 直接按 sep7 + 常数偏移取, 再吸附到最近竖墨
def snap(x7,off,y):
    lo=int(x7+off)-8; hi=int(x7+off)+9
    idx=np.flatnonzero(vv[y,lo:hi])
    return float(idx[np.argmin(np.abs(idx+lo-(x7+off)))]+lo) if len(idx) else x7+off
IN=np.array([[y,snap(float(tr.edge_at(a7,y)),153.5,y)] for y in range(8400,11960)])
OU=np.array([[y,snap(float(tr.edge_at(a7,y)),197.0,y)] for y in range(8400,11960)])
x0,x1,y0,y1=980,1160,8500,10050
sub=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
def dp(P,c,th):
    ok=(P[:,1]>=x0)&(P[:,1]<x1)
    cv2.polylines(sub,[np.column_stack([P[ok,1]-x0,P[ok,0]-y0]).astype(np.int32)],False,c,th)
dp(OU,(255,0,0),1)     # 蓝 = 柱状格外边界(应为 sep8)
dp(IN,(0,220,0),1)     # 绿 = 柱状图案内条右边
dp(a8,(0,0,255),2)     # 红 = 现折线
cv2.putText(sub,'BLUE = cell border (correct)',(4,20),cv2.FONT_HERSHEY_SIMPLEX,0.45,(255,0,0),1)
cv2.putText(sub,'GREEN = hatch-bar edge',(4,38),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,150,0),1)
cv2.putText(sub,'RED = current sep#8',(4,56),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,255),1)
cv2.imwrite(str(OUT/'g1_sep8_wrong_line.png'),cv2.resize(sub,None,fx=3,fy=3,interpolation=cv2.INTER_NEAREST))
print('g1 ok',sub.shape)
# 再给一张"正确区"(y 3000..3600) 做对照
y0b,y1b=3000,3600
sub2=cv2.cvtColor(gray[y0b:y1b,x0:x1],cv2.COLOR_GRAY2BGR)
def dp2(P,c,th,sub_,y0_,y1_):
    ok=(P[:,1]>=x0)&(P[:,1]<x1)&(P[:,0]>=y0_)&(P[:,0]<y1_)
    cv2.polylines(sub_,[np.column_stack([P[ok,1]-x0,P[ok,0]-y0_]).astype(np.int32)],False,c,th)
dp2(OU,(255,0,0),1,sub2,y0b,y1b); dp2(IN,(0,220,0),1,sub2,y0b,y1b); dp2(a8,(0,0,255),2,sub2,y0b,y1b)
cv2.imwrite(str(OUT/'g2_sep8_right.png'),cv2.resize(sub2,None,fx=3,fy=3,interpolation=cv2.INTER_NEAREST))
print('g2 ok',sub2.shape)

