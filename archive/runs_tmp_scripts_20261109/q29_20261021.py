
# -*- coding: utf-8 -*-
"""影响面: 1023 交付表里 y>=8735 的行, 岩性描述 与 柱状 两列长什么样。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_整合_全量_20261011'
stem='钻孔柱状图1023'
rd=json.load(open(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_行判定.json',encoding='utf-8'))
rows=rd['rows']
print('行数',len(rows))
def rowy(rec,x):
    p=np.asarray(rec['poly'],float)
    xs=p[:,0]; ys=p[:,1]
    return float(np.interp(x,np.clip(x,xs[0],xs[-1]),ys))
# 找 y 8735 对应的行
lo=None
for i,r in enumerate(rows):
    y=rowy(r,1200)
    if lo is None and y>=8735: lo=i
print('y>=8735 起始行号:',lo,' 总行数',len(rows))
# 读交付 json
p=D/f'{stem}.json'
print('交付 json 存在?',p.exists())
if not p.exists():
    cands=list(D.glob('*1023*'))
    print('候补:',[c.name for c in cands])

