
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.era_chars import era_strip, char_boxes
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1042'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
k0=hm['keep'][0]
sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
midx=sum(rd['table_x'])/2.0
rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
band,ys,x0i=era_strip(gray,sp_l,sp_r,rows)
print('band',band.shape,'x0i',x0i,'ys',ys[0],ys[-1])
print('ink',int(band.sum()))
prof=band.sum(axis=1)
print('prof>2 rows',int((prof>2).sum()))
print('sample prof every 500:',[int(prof[i]) for i in range(0,len(prof),500)])
boxes=char_boxes(band,ys)
print('boxes',boxes[:10],'n',len(boxes))
# what is the width?
print('band width',band.shape[1])
