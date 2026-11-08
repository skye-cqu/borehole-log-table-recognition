
import sys,json; sys.path.insert(0,'.')
from src.core import paths
# v7 workbook sheet count
from openpyxl import load_workbook
p=paths.RUNS_DIR/'全量整合_合订表_v7.xlsx'
wb=load_workbook(p,read_only=True)
print('v7 sheets',len(wb.sheetnames), wb.sheetnames[:5],'...',wb.sheetnames[-3:])
wb.close()
# table_reconstruct counts
D=paths.RUNS_DIR/'table_reconstruct'
print('表头映射',len(list(D.glob('*_表头映射.json'))))
print('行判定',len(list(D.glob('*_行判定.json'))))
print('列结构定稿',len(list(D.glob('*_列结构定稿.json'))))
print('era_chars dirs',len([d for d in paths.ERA_CHAR_DIR.iterdir() if d.is_dir()]))
