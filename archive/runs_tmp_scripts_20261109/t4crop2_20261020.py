
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
stem='钻孔柱状图1019'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
k0=hm['keep'][0]
sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
for tag,ya,yb in [('top',1200,2600),('mid',3400,5600)]:
    x0,x1=150,650
    crop=cv2.cvtColor(gray[ya:yb,x0:x1],cv2.COLOR_GRAY2BGR)
    for sp,c in ((sp_l,(0,0,255)),(sp_r,(0,180,0))):
        pts=[(int(x-x0),int(y-ya)) for x,y in zip(sp['xs'],sp['ys']) if ya<=y<=yb and x0<=x<=x1]
        if len(pts)>=2: cv2.polylines(crop,[np.asarray(pts,np.int32)],False,c,2)
    cv2.imwrite(str(OUT/f'1019_{tag}.png'),crop)
    print(tag,crop.shape)
