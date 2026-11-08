
import sys,json,re; sys.path.insert(0,'.')
import openpyxl
from src.core import paths
D=paths.RUNS_DIR/'table_整合_全量_20261011'
stem='钻孔柱状图1023'
wb=openpyxl.load_workbook(D/f'{stem}_整合.xlsx'); ws=wb.active
hdr=[c.value for c in ws[1]]
ci=[i for i,h in enumerate(hdr) if h and '岩性' in str(h)][0]
print('错线区间行(82..123) 岩性描述 首字符分布:')
bad=0
for r in range(2, ws.max_row+1):
    if r-2 < 82: continue
    v=ws.cell(r,ci+1).value
    if v is None: continue
    head=str(v)[:6]
    junk=bool(re.match(r'^[^一-龥A-Za-z0-9（(]', str(v)))
    if junk: bad+=1
    print('  r%-3d %r'%(r-1, head))
print('首字符非汉字/字母/数字的行数:',bad)

