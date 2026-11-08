
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
p=paths.REEMIT_DIR_20261005B/'钻孔柱状图1032_还原.xlsx'
ws=load_workbook(p).active
rows=list(ws.iter_rows(values_only=True))
prev=None
out=[]
for i,r in enumerate(rows[1:],start=2):
    d,thk=r[0],r[1]
    if not isinstance(d,(int,float)): continue
    if prev is not None and isinstance(thk,(int,float)):
        exp=round(prev+thk,2)
        sd=('%.2f'%d)
        se=('%.2f'%exp)
        # truncated if read value's decimal part matches expected but integer part lost
        dd=sd.split('.')[-1]; de=se.split('.')[-1]
        if abs(exp-d)>=0.02 and dd==de:
            out.append((i,d,thk,exp,sd,se))
    prev=d
print('candidates (decimal part matches, integer part differs):',len(out))
for o in out: print('  row%-4d read=%-8s thk=%-7s exp=%-8s'%(o[0],o[3] and o[1] or o[1],o[2],o[3]))
