
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
d=json.loads((D/f'{stem}_全竖线判定.json').read_text(encoding='utf-8'))
cols=d['columns_gidx']
print('LLM columns_gidx',cols,'count',len(cols))
print('表头映射 sep_pts 列数',len([s for s in hm['sep_pts'] if s.get('kind')=='column']))
print()
# LLM 判为 column 的 9 条; sep_pts 里 kind=column 的也是 9 条(不含两条 edge)
print('sep_pts column x@mid:',[round(float(np.interp((np.asarray(s["ys"]).min()+np.asarray(s["ys"]).max())/2,s['ys'],s['xs'])),1) for s in hm['sep_pts'] if s.get('kind')=='column'])
print()
print('FINAL[1023] columns:',[2,3,4,5,6,7,8,9,10],'(9 条)')
print('=> 数量一致: LLM 9 条 column, sep_pts 9 条 column, FINAL 9 条')
print('=> 差别只在"编号体系": LLM 用全部27条track的 gidx, FINAL 用 separators 的序号')
