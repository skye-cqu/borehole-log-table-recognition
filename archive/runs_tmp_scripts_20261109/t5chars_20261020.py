
import sys,json; sys.path.insert(0,'.')
from src.core import paths
# compare band names before/after for the 5 figures we just re-ran, plus check 1025/1028 invalid
for s in ['1025','1028']:
    p=paths.ERA_CHAR_DIR/f'钻孔柱状图{s}'/'era_chars.json'
    d=json.loads(p.read_text(encoding='utf-8'))
    print('===',s)
    for c in d['chars']:
        print('   y=%5d-%5d ocr=%r'%(c['y0'],c['y1'],c.get('ocr')))
