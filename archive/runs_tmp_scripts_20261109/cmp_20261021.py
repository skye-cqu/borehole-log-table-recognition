
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from src.table.finalize_columns import FINAL
D=paths.RUNS_DIR/'table_reconstruct'
agree=0; total=0
detail=[]
for code,spec in sorted(FINAL.items()):
    stem=f'钻孔柱状图{code}'
    p=D/f'{stem}_全竖线判定.json'
    if not p.exists(): continue
    d=json.loads(p.read_text(encoding='utf-8'))
    ag=set(d.get('columns_gidx') or [])
    fin=set(spec.get('columns') or [])
    total+=1
    if ag==fin: agree+=1
    else:
        detail.append((code,sorted(ag),sorted(fin)))
print('figures',total,'LLM==FINAL',agree)
print()
for c,a,f in detail:
    print('%-5s LLM=%s  FINAL=%s'%(c,a,f))
