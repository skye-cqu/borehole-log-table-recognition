
import sys,json,re; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G
d=paths.RUNS_DIR/'table_整合_全量_20261011'
ws=load_workbook(d/'钻孔柱状图1023_整合.xlsx',rich_text=True).active
rows=list(ws.iter_rows(values_only=True))
print('header',rows[0])
for r in rows[1:8]: print(r)
