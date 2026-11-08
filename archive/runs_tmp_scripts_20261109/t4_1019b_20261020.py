
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1019'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
k0=hm['keep'][0]
sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
print('left poly pts:',[(round(a),round(b)) for a,b in zip(sp_l['ys'],sp_l['xs'])])
print('right npts',len(sp_r['ys']))
for y in [1100,2000,4000,8000,12000,16000,17500]:
    xl=float(np.interp(y,sp_l['ys'],sp_l['xs'])); xr=float(np.interp(y,sp_r['ys'],sp_r['xs']))
    b=gray[y-25:y+25,:]
    dark=(b<160).mean(axis=0)
    cols=[i for i in range(1,len(dark)-1) if dark[i]>0.6 and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
    grp=[]
    for c in cols:
        if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
        else: grp.append([c])
    centers=[round(sum(g)/len(g),1) for g in grp if len(g)<=10]
    print('y=%5d L=%.0f R=%.0f  ink<600: %s'%(y,xl,xr,[c for c in centers if c<600]))
