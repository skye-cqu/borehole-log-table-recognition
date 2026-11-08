
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import col_segments as CS
lp=CS.line_parts('钻孔柱状图1019')
gray=cv2.imread(str(paths.RAW_DIR/'钻孔柱状图1019.JPG'),cv2.IMREAD_GRAYSCALE)
for idx in (2,3):
    ln=lp['lines'][idx]
    print('=== line #%d kind=%s index=%s'%(idx,ln['kind'],ln.get('index')))
    for k,(seg,sids) in enumerate(ln['parts']):
        a=np.asarray(seg,float)
        print('  part%d y=[%.0f,%.0f] x=[%.0f,%.0f] npts=%d ids=%s'%(k,a[:,1].min(),a[:,1].max(),a[:,0].min(),a[:,0].max(),len(a),sids))
    for k,(seg,meta) in enumerate(ln.get('bridged',[])):
        a=np.asarray(seg,float)
        print('  bridge%d y=[%.0f,%.0f] x=[%.0f,%.0f] npts=%d meta=%s'%(k,a[:,1].min(),a[:,1].max(),a[:,0].min(),a[:,0].max(),len(a),meta))
