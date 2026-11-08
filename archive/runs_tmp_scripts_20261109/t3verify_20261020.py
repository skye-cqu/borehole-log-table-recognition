
import sys,json; sys.path.insert(0,'.')
from openpyxl import load_workbook
p='runs/tmp/t3out_20261020/钻孔柱状图1032_还原.xlsx'
wb=load_workbook(p,rich_text=True)
ws=wb.active
print('dims',ws.max_row,ws.max_column)
orange=0; comments=0
for row in ws.iter_rows():
    for c in row:
        f=c.fill
        rgb=f.start_color.rgb if f and f.start_color else None
        if isinstance(rgb,str) and rgb.endswith('FFC000'):
            orange+=1
            if c.comment: comments+=1
print('orange cells',orange,'with comment',comments)
print('header',[c.value for c in ws[1]])
print('row2',[c.value for c in ws[2]])
print('row3',[c.value for c in ws[3]])
print('last data row',[c.value for c in ws[ws.max_row]])
# confirm values unchanged vs source
from src.core import paths
src=paths.REEMIT_DIR_20261005B/'钻孔柱状图1032_还原.xlsx'
w2=load_workbook(src).active
a=[[c for c in r] for r in w2.iter_rows(values_only=True)]
b=[[c for c in r] for r in ws.iter_rows(values_only=True)]
print('values identical:',a==b)
