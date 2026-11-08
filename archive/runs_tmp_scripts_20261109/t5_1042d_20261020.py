
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.era_chars import era_strip
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1042'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
k0=hm['keep'][0]
sl=hm['sep_pts'][k0['left_sep']]; sr=hm['sep_pts'][k0['right_sep']]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
midx=sum(rd['table_x'])/2.0
rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
band,ys,x0i=era_strip(gray,sl,sr,rows)
colsum=band.sum(axis=0)
print('x0i',x0i,'width',band.shape[1])
print('col ink (x offset relative to x0i):')
for i,v in enumerate(colsum):
    if v>2000: print('   col %d (abs x=%d) ink=%d'%(i,x0i+i,v))
print('total',int(colsum.sum()))
