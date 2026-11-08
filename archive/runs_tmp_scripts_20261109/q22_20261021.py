
# -*- coding: utf-8 -*-
"""最终证据图: sep#8 跳线 (红=现折线, 绿=真列线B, 黄=横线左端点) / sep#10 27px 假象。"""
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
hh=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(30,1)))>0)
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

# ---- 图1: sep#8 全程, 每 40px 拼一条, 左右各留 90px ---
a8=poly(8)
B=track(1073,576,11940)
A=track(1032,576,11940)
x0,x1=880,1250
y0,y1=540,12000
sub=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
def drawpoly(P,color,th=2):
    ok=(P[:,1]>=x0)&(P[:,1]<x1)&(P[:,0]>=y0)&(P[:,0]<y1)
    pts=np.column_stack([P[ok,1]-x0,P[ok,0]-y0]).astype(np.int32)
    if len(pts)>1: cv2.polylines(sub,[pts],False,color,th)
drawpoly(A,(0,255,0),1)          # A = 柱状图案右边(绿)
drawpoly(B,(255,0,0),1)          # B = 真列线(蓝)
drawpoly(a8,(0,0,255),2)         # 现折线(红)
# 横线左端点(黄点)
for y in range(y0,y1):
    idx=np.flatnonzero(hh[y,900:1300])
    if len(idx)>60:
        xl=900+idx[0]
        if x0<=xl<x1: sub[y-y0,xl-x0]=(0,255,255)
# 标注跳线区
cv2.rectangle(sub,(0,8659-y0),(x1-x0-1,9010-y0),(255,0,255),2)
cv2.putText(sub,'fill 8659->9010 (jump to wrong line)',(6,8700-y0),cv2.FONT_HERSHEY_SIMPLEX,0.9,(255,0,255),2)
cv2.imwrite(str(OUT/'e1_sep8_full.png'),sub); print('e1',sub.shape)
# 上半 + 下半各放大 2x
for nm,ya,yb in (('e2_sep8_up.png',560,6200),('e3_sep8_dn.png',6100,11960)):
    s2=sub[ya-y0:yb-y0].copy()
    cv2.imwrite(str(OUT/nm),cv2.resize(s2,None,fx=2,fy=2,interpolation=cv2.INTER_AREA))
    print(nm,(yb-ya)*2,(x1-x0)*2)

