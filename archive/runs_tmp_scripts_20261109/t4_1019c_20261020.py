
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1019'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
k0=hm['keep'][0]
sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
sy=np.asarray(sp_r['ys'],float); sx=np.asarray(sp_r['xs'],float)
print('right_sep npts',len(sy),'y',sy.min(),sy.max(),'x',sx.min(),sx.max())
# sample every 500 y: compare polyline x with nearest ink column
for y in range(1200,17600,800):
    xr=float(np.interp(y,sy,sx)); xl=float(np.interp(y,sp_l['ys'],sp_l['xs']))
    b=gray[y-20:y+20,:]
    dark=(b<160).mean(axis=0)
    cols=[i for i in range(1,len(dark)-1) if dark[i]>0.6 and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
    grp=[]
    for c in cols:
        if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
        else: grp.append([c])
    cen=[round(sum(g)/len(g),1) for g in grp if len(g)<=10 and sum(g)/len(g)<700]
    near=[c for c in cen if abs(c-xr)<=60]
    width=xr-xl
    print('y=%5d L=%6.1f R=%6.1f width=%5.1f nearR=%s'%(y,xl,xr,width,near))
