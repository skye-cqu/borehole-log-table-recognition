
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1019','1015','1017']:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    k0=hm['keep'][0]
    print('===',s,'k0',k0['name'],'L',k0['left_sep'],'R',k0['right_sep'],'x_in_band',k0['x_in_band'],'width',k0['width'])
    print('   sep_x_band',[round(x,1) for x in hm['sep_x_band']])
    n=len(hm['sep_pts'])
    for key in ('left_sep','right_sep'):
        i=k0[key]
        if 0<=i<n:
            sp=hm['sep_pts'][i]
            print('   %s#%d npts=%d y=[%d,%d] x=[%.0f,%.0f]'%(key,i,len(sp['ys']),sp['ys'][0],sp['ys'][-1],min(sp['xs']),max(sp['xs'])))
        else:
            print('   %s#%d OUT OF RANGE (n=%d)'%(key,i,n))
