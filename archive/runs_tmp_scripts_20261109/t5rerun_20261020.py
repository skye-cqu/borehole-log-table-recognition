
import sys,json; sys.path.insert(0,'.')
from src.table import era_chars
from src.core import paths
stems=sorted(p.name.split('_')[0] for p in (paths.RUNS_DIR/'table_reconstruct').glob('*_表头映射.json'))
bad=[]
for s in stems:
    r=era_chars.preflight(s)
    tag='OK ' if r['ok'] else 'FAIL'
    print('%-16s %s PF1=%.4f PF2=%.3f PF3=%d %s'%(s.replace('钻孔柱状图',''),tag,r['PF1_列界覆盖率'],r['PF2_时代界行接触率'],len(r.get('PF3_行序违规') or []),r.get('原因','')))
    if not r['ok']: bad.append(s)
print('BAD:',[b.replace('钻孔柱状图','') for b in bad])
