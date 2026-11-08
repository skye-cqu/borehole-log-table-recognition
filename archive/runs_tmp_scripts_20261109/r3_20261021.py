
# -*- coding: utf-8 -*-
"""决定性检验: 同一行岩性描述, 用"现折线"和"真边界"各裁一次, OCR 比对。
   相同 -> 数据没错(用户对); 不同 -> 数据错了。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
from src.table.reconstruct_excel import _crop_cell, row_y
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
v3=hm['sep_pts']
keep=hm['keep']
desc=[c for c in keep if c['name']=='岩性描述'][0]
def bx(i,y,edge=0.0):
    if i is None or i<0: return edge
    b=v3[i]
    return float(np.interp(y,b['ys'],b['xs']))
x_tbl=sum(rd['table_x'])/2
rows_r=[r for r in rd['rows'] if row_y(r,x_tbl)>=hm['band'][1]]
from rapidocr_onnxruntime import RapidOCR
ocr=RapidOCR()
# 真边界: sep8 修正为 sep7+197.8
a7=np.column_stack([np.asarray(v3[7]['ys'],float),np.asarray(v3[7]['xs'],float)])
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]
def bx_fix(i,y):
    if i==desc['left_sep']:
        return float(tr.edge_at(a7,y))+WID
    return bx(i,y)
out=[]
n=0
for li in range(len(rows_r)-1):
    top,bot=rows_r[li],rows_r[li+1]
    y_mid=(row_y(top,x_tbl)+row_y(bot,x_tbl))/2
    if y_mid<8735: continue
    n+=1
    x1=bx(desc['right_sep'],y_mid,float(gray.shape[1]))
    xc=(bx(desc['left_sep'],y_mid)+x1)/2
    y0c,y1c=row_y(top,xc),row_y(bot,xc)
    if y1c-y0c<8: continue
    c1=_crop_cell(gray,top,bot,lambda y: bx(desc['left_sep'],y),lambda y: bx(desc['right_sep'],y,float(gray.shape[1])))
    c2=_crop_cell(gray,top,bot,lambda y: bx_fix(desc['left_sep'],y),lambda y: bx(desc['right_sep'],y,float(gray.shape[1])))
    r1,_=ocr(c1); r2,_=ocr(c2)
    t1=''.join(x[1] for x in (r1 or [])).strip()
    t2=''.join(x[1] for x in (r2 or [])).strip()
    out.append((li,y_mid,t1,t2,t1==t2))
same=sum(1 for o in out if o[4])
print('下段行数 %d, 两种裁法 OCR 完全相同的 %d 行 = %.0f%%'%(len(out),same,100*same/max(1,len(out))))
print()
for o in out:
    if not o[4]:
        print('  行%d y=%.0f'%(o[0],o[1]))
        print('    现折线: %r'%o[2][:90])
        print('    真边界: %r'%o[3][:90])

