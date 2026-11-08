
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261021'; OUT.mkdir(parents=True,exist_ok=True)
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
b=hm['band']
y0=int(b[0])-40; y1=int(b[1])+60
x0=150; x1=1050
crop=gray[y0:y1, x0:x1]
crop=cv2.resize(crop,((x1-x0)*2,(y1-y0)*2),interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/'1023_header_2x.png'),crop)
print('header crop',crop.shape,'y',y0,y1,'x',x0,x1)
# also a data region with numbers
y2,y3=800,1500
c2=gray[y2:y3, x0:x1]
c2=cv2.resize(c2,((x1-x0)*2,(y3-y2)*2),interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/'1023_data_2x.png'),c2)
print('data crop',c2.shape)
