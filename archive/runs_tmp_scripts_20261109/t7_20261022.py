
# -*- coding: utf-8 -*-
"""交叉验证: 我重建的比对 vs 官方 回收与分歧报告.json。
   官方报告由 apply_agnes_all 产出, 记录 (no, gidx, base, agnes, x_mid)。
   我的重建若正确, 官方每条 disagreement 都应能在我的映射里找到同 (no,gidx)。"""
import sys,json; sys.path.insert(0,'.')
mine=json.load(open('runs/tmp/t6_final_vs_agnes.json',encoding='utf-8'))
rep=json.load(open('runs/table_reconstruct/回收与分歧报告.json',encoding='utf-8'))
print('图    官方分歧条数  我重建标记为不一致的条数  官方(gidx)  我')
tot_off=tot_match=0
for code in sorted(rep):
    off=rep[code].get('disagreements') or []
    mine_bad=mine[code]['bad']
    # 我重建的 judged 映射: gidx -> agnes
    j=mine[code]['judged']
    line=[]
    for d in off:
        g=str(d['gidx']); line.append('g%s:%s'%(g,j.get(g,'?')))
    print('%-6s %6d %14d   %s'%(code,len(off),len(mine_bad),' '.join(line)))
    tot_off+=len(off)
print()
print('官方分歧总数',tot_off)

