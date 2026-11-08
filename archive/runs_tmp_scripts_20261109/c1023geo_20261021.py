
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
print('band',hm['band'])
print('sep_x_band',[round(x,1) for x in hm['sep_x_band']])
print('keep:',[(c['name'],c['left_sep'],c['right_sep'],c['x_in_band']) for c in hm['keep']])
print('notes',hm.get('notes'))
print('warnings',hm.get('warnings'))
