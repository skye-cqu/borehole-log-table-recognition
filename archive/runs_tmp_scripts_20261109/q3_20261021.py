
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
for k in ('frames','content','others','missing'):
    print(k, json.dumps(cs.get(k), ensure_ascii=False)[:600])
print()
fp=D/f'{stem}_闭合外框.json'
print('闭合外框 exists', fp.exists())
if fp.exists():
    d=json.load(open(fp,encoding='utf-8'))
    print('keys', list(d.keys()))
    for k,v in d.items():
        pts=v.get('pts') if isinstance(v,dict) else None
        if pts:
            a=np.array(pts,float)
            print('  %-6s n=%-4d y[%.0f,%.0f] x[%.1f,%.1f] x@mid=%.1f'%(k,len(a),a[:,0].min(),a[:,0].max(),a[:,1].min(),a[:,1].max(),
                  float(np.interp((a[:,0].min()+a[:,0].max())/2, a[:,0], a[:,1]))))
        else:
            print('  ',k,str(v)[:200])

