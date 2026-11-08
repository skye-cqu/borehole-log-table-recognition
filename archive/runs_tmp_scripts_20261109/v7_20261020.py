
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
p=paths.RUNS_DIR/'全量整合_合订表_v7.xlsx'
wb=load_workbook(p)
ws=wb['1015']
print('1015 dims',ws.max_row,ws.max_column)
print('header',[c.value for c in ws[1]])
merged=len(ws.merged_cells.ranges)
print('merged',merged)
# count red font
red=0
for row in ws.iter_rows():
    for c in row:
        if c.font and c.font.color and isinstance(c.font.color.rgb,str) and c.font.color.rgb.endswith('FF0000'):
            red+=1
print('red cells',red)
