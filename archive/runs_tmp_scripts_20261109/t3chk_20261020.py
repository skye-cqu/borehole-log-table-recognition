
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
from src.table.truncation import scan_left_cut
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1032'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
midx=sum(rd['table_x'])/2.0
rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
ys=[row_y(r,midx) for r in rows]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
x1=int(hm['sep_x_band'][0])
res=scan_left_cut(gray,ys,0,x1)
cut=[r for r in res if r['截断']]
print('judged',len(res),'cut',len(cut))
print('ink distribution:',sorted(r['贴边墨'] for r in res)[:15],'...',sorted(r['贴边墨'] for r in res)[-8:])
for r in res[:15]:
    print('  行%-3d y=%5d-%5d 贴边墨=%3d %s'%(r['行'],r['y0'],r['y1'],r['贴边墨'],'CUT' if r['截断'] else ''))
