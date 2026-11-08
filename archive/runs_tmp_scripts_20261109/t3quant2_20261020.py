
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
p=paths.REEMIT_DIR_20261005B/'钻孔柱状图1032_还原.xlsx'
ws=load_workbook(p).active
rows=list(ws.iter_rows(values_only=True))
prev=None
suf=0; tot=0; other=[]
for i,r in enumerate(rows[1:],start=2):
    d,thk=r[0],r[1]
    if not isinstance(d,(int,float)) or not isinstance(thk,(int,float)): continue
    if prev is not None:
        exp=round(prev+thk,2)
        sd=('%.2f'%d).rstrip('0').rstrip('.') if d else '0'
        se=('%.2f'%exp).rstrip('0').rstrip('.')
        tot+=1
        if se.endswith(sd) and sd!=se:
            suf+=1
        elif abs(exp-d)>=0.02:
            other.append((i,d,thk,exp,sd,se))
    prev=d
print('total',tot,'suffix-of-expected',suf,'other',len(other))
print()
for o in other[:25]: print('  row%-4d read=%-8s thk=%-7s exp=%-8s  %s vs %s'%o)
