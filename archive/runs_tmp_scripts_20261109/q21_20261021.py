
# -*- coding: utf-8 -*-
"""定位到管线阶段: sep#8 的碎片构成(_分割线 line8 的 _orig_ids)在 y 8660..9010 断口两侧分别是谁。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table import col_segments as cs
from src.table import track_rows as tr
stem='钻孔柱状图1023'
lp=cs.line_parts(stem)
seg=cs.frag_points(stem)
print('band_src=',lp['band_src'],' warnings=',lp['warnings'])
for ln in lp['lines']:
    if ln['kind']=='column' and ln['index']==8:
        print()
        print('line8: parts=%d bridged=%d gaps=%s dropped=%d'%(len(ln['parts']),len(ln['bridged']),ln['gaps'],len(ln['dropped'])))
        for k,(p,ids) in enumerate(ln['parts']):
            a=np.asarray(p,float)
            print('  part%-2d  点数%-4d  y[%7.1f,%7.1f]  x[%7.1f,%7.1f]  碎片%s'%(
                k,len(a),a[:,1].min(),a[:,1].max(),a[:,0].min(),a[:,0].max(),ids[:6]))
        for p,kd in ln['bridged']:
            a=np.asarray(p,float); print('  bridged-%s y[%.1f,%.1f] x[%.1f,%.1f]'%(kd,a[:,1].min(),a[:,1].max(),a[:,0].min(),a[:,0].max()))
        print()
        print('  断口处各碎片的原始 y 覆盖:')
        for k,(p,ids) in enumerate(ln['parts']):
            a=np.asarray(p,float)
            if a[:,1].max()>8400 and a[:,1].min()<9200:
                print('    part%d y[%.0f,%.0f] x[%.1f,%.1f]'%(k,a[:,1].min(),a[:,1].max(),a[:,0].min(),a[:,0].max()))

