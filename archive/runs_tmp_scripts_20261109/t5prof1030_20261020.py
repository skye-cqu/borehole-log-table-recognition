
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as T
stem='钻孔柱状图1030'
rd=json.load(open(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_行判定.json',encoding='utf-8'))
fr=T.table_frame(stem)
Lys,Lxs=T._era_frame_left(fr)
L_raw=np.array(sorted(np.asarray(fr[0],float).tolist()))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
lw=T._era_line_width(rd['rows'], T.track_group.binarize(gray,T.track_group.PARAMS).T)
cols=json.loads((paths.RUNS_DIR/'table_reconstruct'/f'{stem}_列结构定稿.json').read_text(encoding='utf-8'))['columns']
c0=float(cols[0]['x_at_mid'])
print('c0',c0,'lw',lw)
sel=[]
for r in rd['rows']:
    p=np.asarray(r['poly'],float)
    x_hi=min(p[0,0]-1, c0-25); ok=tot=0; x=int(x_hi)
    while x>100:
        y=float(T._era_row_ys(p,[x])[0])
        Ly=float(np.interp(y,L_raw[:,0],L_raw[:,1]))
        if x<Ly+15: break
        tot+=1
        if gray[max(int(y-8),0):int(y+9),x].min()<210: ok+=1
        x-=1
    if tot<15 or ok/tot<0.5: continue
    x_e=p[0,0]-2
    x_w=float(np.interp(float(T._era_row_ys(p,[p[0,0]])[0]),Lys,Lxs))+3
    pts,_=T._era_walk(gray,p,x_e,x_w,lw,Lys,Lxs)
    sel.append((r,p,x_e,pts))
prof=T._era_profile([(p,pts) for r,p,_,pts in sel if not r.get('complete_from_sub')])
print('n_sel',len(sel))
if prof is not None:
    for c,m in zip(prof[0],prof[1]):
        print('  x=%7.1f  prof=%+7.1f'%(c,m))
