
import sys,json; sys.path.insert(0,'.')
from src.core import paths
p=paths.RUNS_DIR/'table_reconstruct'/'回收与分歧报告.json'
d=json.load(open(p,encoding='utf-8'))
print('type',type(d).__name__)
if isinstance(d,dict):
    print('keys',list(d.keys())[:20])
    k=list(d.keys())[0]
    print()
    print('=== 样例:',k,'===')
    print(json.dumps(d[k],ensure_ascii=False,indent=1)[:1500])
elif isinstance(d,list):
    print('len',len(d))
    print(json.dumps(d[0],ensure_ascii=False,indent=1)[:1500])

