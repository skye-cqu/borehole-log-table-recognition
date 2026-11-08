
import sys,json; sys.path.insert(0,'.')
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
d=json.loads((D/f'{stem}_全竖线判定.json').read_text(encoding='utf-8'))
print('keys',list(d.keys())[:10])
print(json.dumps(d,ensure_ascii=False)[:1500])
