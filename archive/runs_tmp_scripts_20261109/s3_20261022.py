
# -*- coding: utf-8 -*-
"""Agnes 视觉筛选到底覆盖了图的多大范围?"""
import sys,json; sys.path.insert(0,'.')
import cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
print('图     图高     图的宽   Agnes看的crop高   覆盖比例   未被判定的track')
tot=[]
for p in sorted(D.glob('*_全竖线判定.json')):
    d=json.load(open(p,encoding='utf-8'))
    stem=d['image']; code=stem[-4:]
    g=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=g.shape
    ch=d['crop'][3]
    nt=d['n_tracks']; nv=d['n_visible']
    unj=nt-len(d['merged_by_track'])
    cov=ch/H*100
    tot.append(cov)
    print('%-6s %6d  %6d  %12d  %7.1f%%   %d / %d'%(code,H,W,ch,cov,unj,nt))
print()
import numpy as np
a=np.array(tot)
print('30 张: 覆盖比例 中位 %.1f%%  最小 %.1f%%  最大 %.1f%%'%(np.median(a),a.min(),a.max()))
print('覆盖 <50%% 的图数: %d / %d'%((a<50).sum(),len(a)))

