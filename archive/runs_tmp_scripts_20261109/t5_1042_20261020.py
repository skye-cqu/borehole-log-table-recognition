
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1042'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
print('sep_x_band',[round(x,1) for x in hm['sep_x_band']])
print('keep',[(i,c['name'],c['left_sep'],c['right_sep'],c['x_in_band']) for i,c in enumerate(hm['keep'][:2])])
for i,sp in enumerate(hm['sep_pts'][:4]):
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    print('#%d kind=%s side=%s npts=%d y=[%.0f,%.0f] x=[%.0f,%.0f]'%(i,sp.get('kind'),sp.get('side'),len(ys),ys.min(),ys.max(),xs.min(),xs.max()))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
crop=gray[780:1400, 60:700]
cv2.imwrite(str(OUT/'1042_hdr.png'),crop)
print('crop',crop.shape)
