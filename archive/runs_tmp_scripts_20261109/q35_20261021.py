
import sys,json; sys.path.insert(0,'.')
from src.core import paths
stem='钻孔柱状图1023'
d=json.load(open(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_分割线.json',encoding='utf-8'))
for ln in d['lines']:
    if ln.get('kind')=='column' and ln.get('index')==8:
        print('line8 keys:',list(ln.keys()))
        print('  src=',ln.get('src'),' n_orig=',len(ln.get('_orig_ids',[])))
        print('  fills=',json.dumps(ln.get('fills'),ensure_ascii=False)[:800])
        print('  extends len=',len(ln.get('extends') or []))
        print('  ext_conn=',json.dumps(ln.get('ext_conn'),ensure_ascii=False)[:300])

