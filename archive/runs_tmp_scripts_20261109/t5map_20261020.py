
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1017','1020','1023','1025','1028','1032']:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    k0=hm['keep'][0]
    sl=hm['sep_pts'][k0['left_sep']]; sr=hm['sep_pts'][k0['right_sep']]
    print('===',s,'band',[round(x,1) for x in hm['sep_x_band']],'k0',k0['name'],k0['left_sep'],k0['right_sep'])
    print('  L tail',[(round(a),round(b,1)) for a,b in zip(sl['ys'][-3:],sl['xs'][-3:])])
    print('  R tail',[(round(a),round(b,1)) for a,b in zip(sr['ys'][-3:],sr['xs'][-3:])])
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    y0,y1=min(ys),max(ys)
    for yy in np.linspace(max(sr['ys'][-1],y0)+30, y1-30, 4).astype(int):
        lx=float(np.interp(yy,sl['ys'],sl['xs'])); rx=float(np.interp(yy,sr['ys'],sr['xs']))
        b=gray[max(0,yy-25):yy+25,:]
        dark=(b<160).mean(axis=0)
        cols=[i for i in range(1,len(dark)-1) if dark[i]>0.6 and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
        grp=[]
        for c in cols:
            if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
            else: grp.append([c])
        centers=[round(sum(g)/len(g),1) for g in grp if len(g)<=10]
        lo=int(min(lx,rx))-100; hi=int(max(lx,rx))+100
        print('   y',yy,'L=%.0f R=%.0f'%(lx,rx),'ink in [%d,%d]:'%(lo,hi),[c for c in centers if lo<=c<=hi])
