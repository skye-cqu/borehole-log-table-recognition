
import sys,json; sys.path.insert(0,'.')
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
p=D/'钻孔柱状图1023_全竖线判定.json'
d=json.load(open(p,encoding='utf-8'))
print('顶层 keys:',list(d.keys()))
for k,v in d.items():
    if isinstance(v,(list,dict)):
        print('  %-18s %s len=%d'%(k,type(v).__name__,len(v)))
    else:
        print('  %-18s %r'%(k,v))

