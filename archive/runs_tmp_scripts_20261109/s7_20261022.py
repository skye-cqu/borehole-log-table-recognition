
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
stem='钻孔柱状图1023'
cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
seg={s['id']:s for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
tp=paths.TRACK_GROUP_DIR/f'{stem}_列判定.json'
print('track 源存在?',tp.exists())

