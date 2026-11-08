
import sys,json; sys.path.insert(0,'.')
from openpyxl import load_workbook
from src.core import paths
src=paths.REEMIT_DIR_20261005B/'钻孔柱状图1032_还原.xlsx'
out='runs/tmp/t3out_20261020/钻孔柱状图1032_还原.xlsx'
a=list(load_workbook(src).active.iter_rows(values_only=True))
b=list(load_workbook(out,rich_text=True).active.iter_rows(values_only=True))
print('src rows',len(a),'out rows',len(b))
n=min(len(a),len(b))
diff=[i for i in range(n) if a[i]!=b[i]]
print('differing rows:',diff[:10],'count',len(diff))
for i in diff[:5]:
    print('  src',a[i]); print('  out',b[i])
print('trailing src rows beyond out:',a[n:])
