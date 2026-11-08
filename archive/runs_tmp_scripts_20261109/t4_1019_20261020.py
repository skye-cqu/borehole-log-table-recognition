
import sys,json; sys.path.insert(0,'.')
from src.core import paths
p=paths.ERA_CHAR_DIR/'钻孔柱状图1019'/'era_chars.json'
d=json.loads(p.read_text(encoding='utf-8'))
print('keys',list(d.keys()))
print('strip',d.get('strip_y0'),d.get('strip_y1'))
print('preflight',json.dumps(d.get('preflight'),ensure_ascii=False))
print('n_chars',len(d['chars']))
for c in d['chars']:
    print('  char y=%d-%d ocr=%r'%(c['y0'],c['y1'],c.get('ocr')))
print('bands:')
for b in d['bands']:
    print('  ',b)
