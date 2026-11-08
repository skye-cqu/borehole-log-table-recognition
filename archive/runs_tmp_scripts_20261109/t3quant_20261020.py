
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
p=paths.REEMIT_DIR_20261005B/'钻孔柱状图1032_还原.xlsx'
ws=load_workbook(p).active
rows=list(ws.iter_rows(values_only=True))
prev=None; n=0; ok=0
rec=[]
for i,r in enumerate(rows[1:],start=2):
    d,thk=r[0],r[1]
    if not isinstance(d,(int,float)) or not isinstance(thk,(int,float)): continue
    if prev is not None:
        exp=prev+thk
        # try prefix restoration: does exp end with the read digits?
        sd=('%.2f'%d); se=('%.2f'%exp)
        restored = se.endswith(sd) or abs(exp-d)<0.02
        n+=1
        if restored: ok+=1
        rec.append((i,d,thk,round(exp,2),sd,se,restored))
    prev=d
print('checked',n,'chain-consistent-after-prefix',ok)
print()
print('行 读到深度 层厚 推算深度 读串 推串 前缀可补')
bad=0
for i,d,thk,exp,sd,se,rr in rec:
    if not rr:
        bad+=1
        if bad<=15: print('%3d %9.2f %7.2f %9.2f  %-8s %-8s  %s'%(i,d,thk,exp,sd,se,'PREFIX?' ))
print('...')
print('不可闭合行数',bad,'/',n)
