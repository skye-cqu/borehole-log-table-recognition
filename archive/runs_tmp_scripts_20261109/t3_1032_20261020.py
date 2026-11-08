
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
p=paths.REEMIT_DIR_20261005B/'钻孔柱状图1032_还原.xlsx'
print('exists',p.exists(),p)
ws=load_workbook(p).active
print('dims',ws.max_row,ws.max_column)
for i,row in enumerate(ws.iter_rows(values_only=True)):
    if i<8 or i>ws.max_row-6:
        print(i+1,row)
