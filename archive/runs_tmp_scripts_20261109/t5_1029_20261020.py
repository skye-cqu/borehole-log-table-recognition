
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1029'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
k0=hm['keep'][0]; print('k0',k0['name'],k0['left_sep'],k0['right_sep'])
sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
print('L tail',sp_l['ys'][-3:],sp_l['xs'][-3:])
print('R tail',sp_r['ys'][-3:],sp_r['xs'][-3:])
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
for y in range(20340,20500,10):
    b=gray[y-2:y+3,150:420]
    dark=(b<160).any(axis=0)
    runs=[];s=None
    for i,v in enumerate(dark):
        if v and s is None: s=i
        elif not v and s is not None: runs.append((150+s,150+i-1)); s=None
    if s is not None: runs.append((150+s,150+len(dark)-1))
    print(' y',y,runs)
