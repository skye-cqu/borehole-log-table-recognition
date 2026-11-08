
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1019'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
k0=hm['keep'][0]
sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
x0=int(min(sp_l['xs']))-10; x1=int(max(sp_r['xs']))+10
crop=gray[1000:17800, x0:x1]
h,w=crop.shape
sc=2000.0/h
crop=cv2.resize(crop,(max(1,int(w*sc)),2000),interpolation=cv2.INTER_AREA)
out=paths.RUNS_DIR/'tmp'/'t5crop_20261020'/'1019_era_full.png'
cv2.imwrite(str(out),crop)
print(out,crop.shape,'x',x0,x1)
