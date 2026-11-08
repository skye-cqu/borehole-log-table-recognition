
# -*- coding: utf-8 -*-
"""两处离群的最终判定: (1) sep#10 的 27px 是不是 argmax 平票 (2) sep#8 的 4px 落在哪几个采样点"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)*255
v=cv2.morphologyEx(bw,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))
v=cv2.morphologyEx(v,cv2.MORPH_CLOSE,np.ones((25,1),np.uint8))

def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

print('===== (1) sep#10 y=7998: yard_cols 同款判据的逐列值 =====')
a10=poly(10); xp=float(tr.edge_at(a10,7998))
print('   折线x = %.1f   搜索窗 [%d,%d]'%(xp,int(xp)-60,int(xp)+60))
lo=max(0,int(xp)-60)
idx=np.flatnonzero(v[7998,lo:min(int(xp)+60,W-1)])
print('   窗内全部有墨列:', [int(i+lo) for i in idx])
d=[]
for i in idx:
    xx=i+lo
    d.append((int(xx), abs(int(xx)-xp)))
print('   到折线距离:', d)
print('   >>> 距折线最近的墨列 = %d (差 %.1f)'%(min(d,key=lambda t:t[1])[0], min(t[1] for t in d)))
print('   >>> yard_cols 用 idx.min() 取最近 -> 结果就是这条, 不是 27px 那条')
print()
print('===== (2) sep#8: yard_cols 60 个采样点逐点偏差 =====')
a8=poly(8); y0,y1=a8[0,0],a8[-1,0]
SAMPLE=60
bad=[]
for k,y in enumerate(np.linspace(y0,y1,SAMPLE)):
    yi=int(round(y)); xi=float(tr.edge_at(a8,y))
    lo=max(0,int(xi)-60)
    idx=np.flatnonzero(v[yi,lo:min(int(xi)+60,W-1)])
    if len(idx)==0:
        print('   #%-2d y=%6.0f 折线=%7.1f  窗内无墨'%(k,y,xi)); continue
    j=int(np.argmin(np.abs(idx+lo-xi))); xk=float(idx[j]+lo)
    dd=abs(xk-xi)
    tag='  <<< 超差' if dd>5 else ''
    if dd>5 or k%10==0:
        print('   #%-2d y=%6.0f 折线=%7.1f 最近墨=%7.1f 差=%5.1f%s'%(k,y,xi,xk,dd,tag))
    if dd>5: bad.append((k,y,xi,xk,dd))
print()
print('   超差点数 = %d / %d'%(len(bad),SAMPLE))
for b in bad: print('     #%d y=%.0f 折线=%.1f 墨=%.1f 差=%.1f'%b)

