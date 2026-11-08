
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1025','1028']:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    print('===',s,'sep_x_band',[round(x,1) for x in hm['sep_x_band']])
    print(' keep:',[(i,c['name'],c['left_sep'],c['right_sep']) for i,c in enumerate(hm['keep'][:3])])
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    for y in [11000,13000,15000,16500]:
        band=gray[y-40:y+40,:]
        dark=(band<160).mean(axis=0)
        cols=[int(i) for i in range(1,len(dark)-1) if dark[i]>0.6 and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
        # group
        grp=[]
        for c in cols:
            if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
            else: grp.append([c])
        centers=[round(sum(g)/len(g),1) for g in grp if len(g)<=8]
        print('  y',y,'ink cols<600:',[c for c in centers if c<600])
    for side in ('left_sep','right_sep'):
        sp=hm['sep_pts'][hm['keep'][0][side]]
        for y in [11000,13000,15000,16500]:
            print('  ',side,'y',y,'x',round(float(np.interp(y,sp['ys'],sp['xs'])),1))
