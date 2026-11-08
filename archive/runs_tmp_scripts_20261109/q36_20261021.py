
# -*- coding: utf-8 -*-
"""根因: bridge_gaps 的 ALIGN_TOL=40 允许了 39px 的横向跳线。全库统计这类"横向跳>30px 的补全"。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
RECON=paths.RUNS_DIR/'table_reconstruct'
tot=0; big=[]
for p in sorted(RECON.glob('*_分割线.json')):
    d=json.load(open(p,encoding='utf-8'))
    stem=p.name.replace('_分割线.json','')
    for ln in d['lines']:
        for fl in ln.get('fills') or []:
            a,b=np.asarray(fl['fill'],float)
            dx=abs(b[0]-a[0])
            tot+=1
            if dx>30:
                big.append((stem,ln['kind'],ln.get('index'),fl['y'],round(dx,1),fl['gap']))
print('全库 fills 总数 %d, 其中横向跳 >30px 的 %d 条 = %.1f%%'%(tot,len(big),100*len(big)/max(1,tot)))
for b in sorted(big,key=lambda t:-t[4])[:20]:
    print('  %-16s %-6s idx=%-3s y=%s  横跳=%.1fpx  缺口=%spx'%(b[0],b[1],b[2],b[3],b[4],b[5]))
print()
from collections import Counter
c=Counter(b[0] for b in big)
print('按图统计:',dict(c))

