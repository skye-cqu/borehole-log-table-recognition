
import sys,json; sys.path.insert(0,'.')
from src.core import paths
d=json.loads((paths.TMP_DIR/'时代列门禁_20261010.json').read_text(encoding='utf-8'))
for r in d['逐图']:
    print('%-14s 残墨率=%s G2valid=%s G3=%d G1b=%d'%(r['图号'].replace('钻孔柱状图',''),r.get('残墨率'),r.get('G2valid'),len(r.get('G3明细') or []),len(r.get('G1b明细') or [])))
