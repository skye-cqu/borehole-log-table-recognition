
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
cases=[('1017','right_sep'),('1020','right_sep'),('1023','left_sep'),('1025','right_sep'),('1028','left_sep'),('1032','left_sep'),('1032','right_sep')]
for s,side in cases:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    y0,y1=min(ys),max(ys)
    sp=hm['sep_pts'][hm['keep'][0][side]]
    sy=np.asarray(sp['ys'],float); sx=np.asarray(sp['xs'],float)
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    print('===',s,side,'data',round(y0),round(y1),'H',H)
    print('  tail pts:',[(round(a),round(b,1)) for a,b in zip(sy[-5:],sx[-5:])])
    # ink columns at last valid y and inside gap
    for yy in [int(sy[-1])-30, int(sy[-1])+20, int((sy[-1]+y1)/2), int(y1)-30]:
        if yy<0 or yy>=H: continue
        b=gray[max(0,yy-25):yy+25,:]
        dark=(b<160).mean(axis=0)
        cols=[i for i in range(1,len(dark)-1) if dark[i]>0.6 and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
        grp=[]
        for c in cols:
            if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
            else: grp.append([c])
        centers=[round(sum(g)/len(g),1) for g in grp if len(g)<=10]
        near=[c for c in centers if abs(c-sx[-1])<120]
        print('   y',yy,'ink near tail x=%.0f:'%sx[-1],near)
