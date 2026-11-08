
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table import track_rows as tr
import openpyxl
D=paths.RUNS_DIR/'table_整合_全量_20261011'
stem='钻孔柱状图1023'
wb=openpyxl.load_workbook(D/f'{stem}_整合.xlsx')
ws=wb.active
hdr=[c.value for c in ws[1]]
print('表头:',hdr)
print('行数:',ws.max_row)
idx={h:i for i,h in enumerate(hdr)}
# 找 岩性描述 列
di=[i for i,h in enumerate(hdr) if h and '岩性' in str(h)]
print('岩性描述列号:',di)
col=di[0] if di else None
for r in range(2, ws.max_row+1):
    if r-2 < 80: continue
    vals=[ws.cell(r,c+1).value for c in range(len(hdr))]
    print(r, vals)
    if r>95: break

