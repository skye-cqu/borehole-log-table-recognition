
import sys,json; sys.path.insert(0,'.')
from src.core import paths
for s in ['1017','1020','1023','1025','1028']:
    p=paths.ERA_CHAR_DIR/f'钻孔柱状图{s}'/'era_chars.json'
    d=json.loads(p.read_text(encoding='utf-8'))
    pf=d['preflight']
    print('===',s,'strip',d['strip_y0'],d['strip_y1'],'nchar',len(d['chars']))
    print('   PF1',pf['PF1_列界覆盖率'],'PF2',pf['PF2_时代界行接触率'],'PF4',pf['PF4_顶部墨占比'],'PF4_warn',pf.get('PF4_warn'))
    print('   header_strip',d.get('header_strip'))
    for b in d['bands']:
        print('     %-14s y=%d-%d %s'%(b['name'],b['y0'],b['y1'],b['判定']))
