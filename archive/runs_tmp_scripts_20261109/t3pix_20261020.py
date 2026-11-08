
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1032'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
print('sep_x_band',[round(x,1) for x in hm['sep_x_band']])
print('keep',[(c['name'],c['left_sep'],c['right_sep'],c['x_in_band']) for c in hm['keep']])
midx=sum(rd['table_x'])/2.0
rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
ys=[row_y(r,midx) for r in rows]
print('n_rows',len(rows),'y',round(ys[0]),round(ys[-1]))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
# depth column = left_sep(-1 → x=0) .. right_sep(0 → sep_x_band[0])
xr=int(hm['sep_x_band'][0])
print('depth col x range 0..%d'%xr)
touch=0
for i in range(len(rows)-1):
    a,b=int(ys[i]),int(ys[i+1])
    if b-a<4: continue
    sub=gray[a+2:b-2, 0:xr-4]
    if sub.size==0: continue
    dark=(sub<150)
    leftmost=np.where(dark.any(axis=0))[0]
    if len(leftmost)==0:
        print('row%3d y=%5d-%5d  EMPTY'%(i,a,b)); continue
    lm=int(leftmost[0])
    if lm<=2:
        touch+=1
        print('row%3d y=%5d-%5d  leftmost=%d  TOUCHES EDGE'%(i,a,b,lm))
print('rows touching left edge:',touch)
