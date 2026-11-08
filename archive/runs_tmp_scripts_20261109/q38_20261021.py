
# -*- coding: utf-8 -*-
"""判决: 1023 下部, 岩性描述的行线左端点落在 1045 还是 1089?
   用 20px 横核(短段也活), 只在 x 1000..1500 找, 逐条列出横线的左端。
"""
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
for K in (20,40):
    hh=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(K,1)))>0)
    print('=== 横核 %dpx ==='%K)
    rows=[]
    for y in range(9000,11900):
        seg=hh[y,1000:1600]
        idx=np.flatnonzero(seg)
        if len(idx)<K: continue
        # 必须连续延伸到 1500 以上
        if idx[-1] < 500: continue
        rows.append((y,1000+idx[0],1000+idx[-1]))
    grp=[]
    for y,x0,x1 in rows:
        if grp and y-grp[-1][-1][0]<=3: grp[-1].append((y,x0,x1))
        else: grp.append([(y,x0,x1)])
    print('  横线条数 %d'%len(grp))
    for g in grp:
        ym=int(np.mean([a for a,_,_ in g])); xl=int(np.min([b for _,b,_ in g])); xr=int(np.max([c for _,_,c in g]))
        print('    y=%5d  左端 x=%4d  右端 x=%4d   -> %s'%(ym,xl,xr,
            '贴 1045(图案条)' if abs(xl-1045)<8 else ('贴 1089(真边界)' if abs(xl-1089)<8 else '其他')))

