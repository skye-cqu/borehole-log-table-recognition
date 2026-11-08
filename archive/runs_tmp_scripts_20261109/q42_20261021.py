
import sys,json; sys.path.insert(0,'.')
import openpyxl
from src.core import paths
D=paths.RUNS_DIR/'table_整合_全量_20261011'
stem='钻孔柱状图1023'
wb=openpyxl.load_workbook(D/f'{stem}_整合.xlsx'); ws=wb.active
hdr=[c.value for c in ws[1]]
ci=[i for i,h in enumerate(hdr) if h and '岩性' in str(h)][0]
for r in (106,107,108):
    print('sheet row',r,[ws.cell(r,c+1).value for c in range(len(hdr))])
print()
# 检查所有 30 张图交付表里 岩性描述 首字符是标点/符号的行
import glob,re
tot=0; bad=[]
for p in sorted(glob.glob(str(D/'*_整合.xlsx'))):
    wb=openpyxl.load_workbook(p); ws=wb.active
    hdr=[c.value for c in ws[1]]
    if not any(h and '岩性' in str(h) for h in hdr): continue
    ci=[i for i,h in enumerate(hdr) if h and '岩性' in str(h)][0]
    for r in range(2,ws.max_row+1):
        v=ws.cell(r,ci+1).value
        if v is None: continue
        tot+=1
        s=str(v).strip()
        if s and not (s[0].isalnum() or '\u4e00'<=s[0]<='\u9fff'):
            bad.append((p.split('\\')[-1].replace('_整合.xlsx',''),r-1,s[:20]))
print('全库 岩性描述 非空 %d 格, 首字符异常 %d 格'%(tot,len(bad)))
for b in bad[:20]: print('  ',b)

