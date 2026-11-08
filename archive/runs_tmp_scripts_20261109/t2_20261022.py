
import sys,json; sys.path.insert(0,'.')
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
d=json.load(open(D/'回收与分歧报告.json',encoding='utf-8'))
print('图     recoveries  disagreements')
for k in sorted(d):
    v=d[k]
    print('%-6s %3d        %3d'%(k,len(v.get('recoveries') or []),len(v.get('disagreements') or [])))
print()
print('=== 1023 全文 ===')
print(json.dumps(d['1023'],ensure_ascii=False,indent=1))

