
import sys,json; sys.path.insert(0,'.')
from src.core import paths
d=json.loads((paths.TMP_DIR/'时代列门禁_20261010.json').read_text(encoding='utf-8'))
figs=[r['图号'].replace('钻孔柱状图','') for r in d['逐图']]
print('n',len(figs))
print(sorted(figs))
for r in d['逐图']:
    s=r['图号'].replace('钻孔柱状图','')
    if s in ('1017','1019','1020','1023','1025','1028','1030','1042'):
        print('%-6s 残墨率=%s G2=%s G3=%d G1b=%d'%(s,r.get('残墨率'),r.get('G2valid'),len(r.get('G3明细') or []),len(r.get('G1b明细') or [])))
