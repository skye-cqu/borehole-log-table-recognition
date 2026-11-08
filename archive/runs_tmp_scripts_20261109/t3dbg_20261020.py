
import sys,json; sys.path.insert(0,'.')
from src.core import paths
d=json.loads((paths.TMP_DIR/'截断登记_钻孔柱状图1032.json').read_text(encoding='utf-8'))
print('标注',d['标注行数'],'/',d['总判行数'])
import collections
c=collections.Counter(x['贴边墨'] for x in d['明细'])
print('贴边墨分布',sorted(c.items())[:20])
for x in d['明细'][:12]:
    print('  行%-4d y=%5d-%5d 贴边墨=%3d 读=%s 推算=%s 旁证=%s'%(x['xlsx行'],x['y0'],x['y1'],x['贴边墨'],x['读'],x['推算'],x['旁证支持']))
