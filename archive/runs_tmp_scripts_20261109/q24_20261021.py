
# -*- coding: utf-8 -*-
"""sep#10 右侧: 到底哪条是表格右外框? 列 x2700..3248 内所有长竖线。"""
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
a10=poly(10)
print('  y     sep10折线 | x2700..3248 内的竖墨列')
for y in (580,600,1000,3000,6000,7998,10000,12000,12440):
    b=vv[max(0,y-12):y+13,2700:3248].mean(axis=0)
    idx=np.flatnonzero(b>0.55); grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=4: grp[-1].append(c)
        else: grp.append([c])
    ics=[round(2700+sum(g)/len(g),1) for g in grp]
    print('%6d %9.1f | %s'%(y,float(tr.edge_at(a10,y)),ics))
print()
print('=== 顶框/底框的右端点 ===')
for nm in ('top','bottom'):
    pass
fr=json.load(open(D/f'{stem}_闭合外框.json',encoding='utf-8'))
print('corners',fr['corners'])
for k in ('top','bottom','right','left'):
    pts=np.asarray(fr[k]['pts'],float)
    if k in ('top','bottom'):
        print('  %-6s x[%.0f,%.0f] y[%.0f,%.0f]  右端点 x=%.0f'%(k,pts[:,0].min(),pts[:,0].max(),pts[:,1].min(),pts[:,1].max(),pts[np.argmax(pts[:,0])][0]))
    else:
        print('  %-6s y[%.0f,%.0f] x[%.0f,%.0f]'%(k,pts[:,0].min(),pts[:,0].max(),pts[:,1].min(),pts[:,1].max()))
print()
# 证据图: 右侧三线
x0,x1,y0,y1=2760,3120,520,12600
sub=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
ys=np.linspace(y0,y1-1,600); xs=np.array([tr.edge_at(a10,y) for y in ys])
cv2.polylines(sub,[np.column_stack([xs-x0,ys-y0]).astype(np.int32)],False,(0,0,255),2)
for (yy,xx,cc) in [(7998,2929,(0,255,0)),(7998,2957,(255,0,0))]:
    cv2.circle(sub,(int(xx-x0),int(yy-y0)),12,cc,3)
cv2.imwrite(str(OUT/'f1_sep10_lines.png'),cv2.resize(sub,None,fx=1,fy=1))
print('f1',sub.shape)

