
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1042'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
k0=hm['keep'][0]
sl=hm['sep_pts'][k0['left_sep']]; sr=hm['sep_pts'][k0['right_sep']]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
for y in [1000,3000,6000,9000,12000,15000,18000,19500]:
    L=float(np.interp(y,sl['ys'],sl['xs'])); R=float(np.interp(y,sr['ys'],sr['xs']))
    seg=gray[y-30:y+30, :int(R)+60]
    dark=(seg<160).mean(axis=0)
    idx=[i for i in range(1,len(dark)-1) if dark[i]>0.6 and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
    grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=4: grp[-1].append(c)
        else: grp.append([c])
    cen=[round(sum(g)/len(g),1) for g in grp if len(g)<=16]
    print('y=%5d L=%6.1f R=%6.1f  ink: %s'%(y,L,R,cen))
