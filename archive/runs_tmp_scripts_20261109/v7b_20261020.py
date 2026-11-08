
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
p=paths.RUNS_DIR/'全量整合_合订表_v7.xlsx'
wb=load_workbook(p)
tot_rows=0; tot_red=0; tot_merged=0
for name in wb.sheetnames:
    ws=wb[name]
    tot_rows+=ws.max_row-1
    tot_merged+=len(ws.merged_cells.ranges)
    for row in ws.iter_rows():
        for c in row:
            f=c.font
            if f and f.color and isinstance(f.color.rgb,str) and f.color.rgb.endswith('FF0000'):
                tot_red+=1
print('sheets',len(wb.sheetnames))
print('data rows total',tot_rows)
print('merged total',tot_merged)
print('red cells total',tot_red)
# per-sheet merged count -> era merge status
nom=[]
for name in wb.sheetnames:
    ws=wb[name]
    m=len(ws.merged_cells.ranges)
    if m==0: nom.append(name)
print('sheets with 0 merged:',nom)
