
# -*- coding: utf-8 -*-
"""错线的实际后果: 岩性描述 裁片左界落在 1045, 而真边界 1089 —— 1089 那条竖线被裁进描述格里。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'col_crop_20261021'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a8=poly(8)
# 取一行: y=9500 附近, 裁 [sep8, sep8+400]
y=9500
x8=float(tr.edge_at(a8,y))
print('y=%d  sep8 折线=%.1f  真边界=1089  错线把它裁在 1045'%(y,x8))
sub=cv2.cvtColor(gray[y-40:y+40, 1020:1500],cv2.COLOR_GRAY2BGR)
cv2.line(sub,(int(x8)-1020,0),(int(x8)-1020,80),(0,0,255),2)      # 红=现在裁的左界
cv2.line(sub,(1089-1020,0),(1089-1020,80),(255,0,0),2)             # 蓝=真边界
cv2.line(sub,(1045-1020,0),(1045-1020,80),(0,255,0),2)             # 绿=图案条右边
cv2.imwrite(str(OUT/'h1_crop_effect.png'),cv2.resize(sub,None,fx=3,fy=3,interpolation=cv2.INTER_NEAREST))
print('h1 saved')
# 统计: 错线区间内, 有多少行的裁片里含那条 1089 竖线
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
rows=rd['rows']
def ymid(r):
    p=np.asarray(r['poly'],float)
    return float(np.interp(1200,p[:,0],p[:,1]))
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
n=0; hit=0
for r in rows:
    y=ymid(r)
    if y<8735: continue
    n+=1
    lo=int(float(tr.edge_at(a8,y)))+2
    # 真边界位置(sep7+197.8)
    a7=poly(7); true_x=float(tr.edge_at(a7,y))+197.8
    if vv[int(y), int(true_x)-2:int(true_x)+3].any(): hit+=1
print('错线区间行数 %d, 其中裁片内含真边界竖线的 %d 行 = %.0f%%'%(n,hit,100*hit/max(1,n)))

