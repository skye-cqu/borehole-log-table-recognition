
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1019','1015','1017']:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    ymid=(hm['band'][0]+hm['band'][1])/2
    print('===',s,'band',hm['band'],'ymid',ymid)
    print('   sep_x_band(sorted x_mid)',[round(x,1) for x in hm['sep_x_band']])
    calc=[]
    for i,sp in enumerate(hm['sep_pts']):
        ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
        xm=float(np.interp(ymid,ys,xs))
        calc.append(xm)
        print('   #%d kind=%-6s index=%-4s side=%-5s x_mid=%7.1f  y=[%.0f,%.0f]'%(i,sp.get('kind'),sp.get('index'),sp.get('side'),xm,ys.min(),ys.max()))
    print('   computed sorted',[round(x,1) for x in sorted(calc)])
    print('   MATCH' if [round(x,1) for x in sorted(calc)]==[round(x,1) for x in hm['sep_x_band']] else '   *** MISMATCH ***')
