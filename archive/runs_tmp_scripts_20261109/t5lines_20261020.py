
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1030'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
# column bands from sep_x_band
hm=json.load(open(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_表头映射.json',encoding='utf-8'))
xs=hm['sep_x_band']
print('sep_x_band',xs)
names=[c['name'] for c in hm['keep']]
print('keep',names)
wins=[]
for i,nm in enumerate(names):
    a=int(xs[i])+8; b=int(xs[i+1])-8
    if b-a>20: wins.append((nm,a,b))
print('wins',wins)
print()
print('y     '+' '.join('%-8s'%n[:6] for n,_,_ in wins))
for y in range(4540,4790,1):
    fr=[float((gray[y,a:b]<150).mean()) for _,a,b in wins]
    if max(fr)>0.5:
        print('%5d '%y+' '.join('%-8.2f'%f for f in fr))
