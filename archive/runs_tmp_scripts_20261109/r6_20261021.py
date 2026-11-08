
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.reconstruct_excel import _crop_cell, row_y
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
v3=hm['sep_pts']; keep=hm['keep']
desc=[c for c in keep if c['name']=='岩性描述'][0]
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]
a7y=np.asarray(v3[7]['ys'],float); a7x=np.asarray(v3[7]['xs'],float)
def bx(i,y,edge=0.0):
    if i is None or i<0: return edge
    b=v3[i]; r=np.interp(y,b['ys'],b['xs'])
    return r if np.ndim(r) else float(r)
def bx_fix(i,y):
    if i==desc['left_sep']:
        y=np.asarray(y,float)
        r=np.interp(np.clip(y,a7y[0],a7y[-1]),a7y,a7x)+WID
        return r if np.ndim(r) else float(r)
    return bx(i,y)
x_tbl=sum(rd['table_x'])/2
rows_r=[r for r in rd['rows'] if row_y(r,x_tbl)>=hm['band'][1]]
from rapidocr_onnxruntime import RapidOCR
ocr=RapidOCR()
def cell(li,bxl):
    top,bot=rows_r[li],rows_r[li+1]
    y_mid=(row_y(top,x_tbl)+row_y(bot,x_tbl))/2
    x0=float(np.atleast_1d(bxl(desc['left_sep'],y_mid))[0])
    x1=float(np.atleast_1d(bx(desc['right_sep'],y_mid,float(gray.shape[1])))[0])
    xc=(x0+x1)/2; y0c,y1c=row_y(top,xc),row_y(bot,xc)
    c=_crop_cell(gray,top,bot,lambda y: bxl(desc['left_sep'],y),
                 lambda y: bx(desc['right_sep'],y,float(gray.shape[1])),x0,x1,y0c,y1c)
    if c is None: return ''
    r,_=ocr(c); return ''.join(x[1] for x in (r or [])).strip()
out=[]
for li in range(len(rows_r)-1):
    y_mid=(row_y(rows_r[li],x_tbl)+row_y(rows_r[li+1],x_tbl))/2
    if y_mid<8735: continue
    out.append((li,y_mid,cell(li,bx),cell(li,bx_fix)))
same=sum(1 for o in out if o[2]==o[3])
print('下段行数 %d, 两种裁法 OCR 完全相同 %d 行 = %.0f%%'%(len(out),same,100*same/max(1,len(out))))
for o in out:
    if o[2]!=o[3]:
        print('  行%d y=%.0f'%(o[0],o[1]))
        print('    现折线: %r'%o[2][:110])
        print('    真边界: %r'%o[3][:110])

