
import sys,json; sys.path.insert(0,'.')
import cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
for n in ('_全竖线叠加图.png','_全竖线叠加图_预览.jpg','_agnes验收.json'):
    p=D/('钻孔柱状图1023'+n)
    if p.exists():
        if n.endswith('.json'):
            d=json.load(open(p,encoding='utf-8'))
            print(n,'keys=',list(d.keys())[:12])
        else:
            im=cv2.imread(str(p)); print(n,'尺寸=',im.shape)
    else:
        print(n,'不存在')
print()
print('=== 分片目录 ===')
pd=D/'全竖线分片'
if pd.exists():
    fs=sorted(x.name for x in pd.glob('*1023*'))
    print('分片数',len(fs))
    for f in fs:
        im=cv2.imread(str(pd/f)); print('  ',f,im.shape)

