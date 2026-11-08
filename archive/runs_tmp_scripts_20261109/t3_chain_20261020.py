
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
p=paths.REEMIT_DIR_20261005B/'钻孔柱状图1032_还原.xlsx'
ws=load_workbook(p).active
rows=list(ws.iter_rows(values_only=True))
print('hdr',rows[0])
prev=None
bad=0
for i,r in enumerate(rows[1:],start=2):
    d,thk,caij,ang,zhen,desc=r[0],r[1],r[2],r[3],r[4],r[5]
    if not isinstance(d,(int,float)): continue
    if prev is not None:
        exp=prev+thk if isinstance(thk,(int,float)) else None
        flag='' if (exp is None or abs(d-exp)<0.02) else '  <-- MISMATCH exp=%.2f got=%.2f'%(exp,d)
        if flag: bad+=1
        print('%3d d=%8.2f thk=%7s exp=%s%s'%(i,d,thk,('%.2f'%exp) if exp is not None else '-',flag))
    prev=d
print('mismatch rows',bad,'of',len(rows)-2)
