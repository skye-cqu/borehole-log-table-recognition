# -*- coding: utf-8 -*-
"""框边"突然大跳转"的形态分账(用户 2026-09-27 标准③:边上不许有突然大跳转)。

判据本身在 `src/table/col_segments.py:line_jumps`(出图要按它剔离群点,尺子与交付共用一把刀,不会两头漂)。
本脚本只负责全量跑一遍并分类汇总:尖点(离群点,该剔) / 端点(线两端,角上直角弯) / 台阶(真折了,交人看)。

用法: python runs/tmp/diag_hook.py [图号...]   默认全量 30 张
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import col_segments as cs                            # noqa: E402


def scan(stem):
    """→ [(线名, 形态, 跳距, 碎片id, 沿线%, 前点, 后点)] 竖边(列线/左右框)+横框(顶/底)。"""
    seg, fh = cs.frag_points(stem), cs.frag_points(stem, "horizontal")
    rows = [(f"{ln['kind']}{ln['index'] if ln['kind'] == 'column' else ln['side']}",
             ln['parts'], seg, 1) for ln in cs.line_parts(stem)['lines']]
    rows += [(f"{ln['kind']}框{ln['index']}", ln['parts'], fh, 0)
             for ln in cs.frame_parts(stem)['lines']]
    return [(name,) + r for name, parts, src, ax in rows
            for r in cs.line_jumps([(np.asarray(p, float), i) for p, i in parts], src, ax)[0]]


if __name__ == '__main__':
    codes = sys.argv[1:] or [p.stem[-4:] for p in sorted(paths.RAW_DIR.glob('钻孔柱状图*.JPG'))]
    tot, sheets = Counter(), {}
    for code in codes:
        rows = scan(f'钻孔柱状图{code}')
        if rows:
            sheets[code] = rows
            tot.update(r[1] for r in rows)
        for r in sorted(rows, key=lambda t: (t[0], -t[2])):
            print(f'  {code} {r[0]:12} {r[1]:4} {r[2]:4}px 碎片{r[3]} 沿线{r[4]:>3}% {r[5]}→{r[6]}')
    edge = [r for v in sheets.values() for r in v if r[0].startswith(('edge', 'top', 'bottom'))]
    print(f'\n合计 {len(codes)} 张: ' + '  '.join(f'{k} {v}' for k, v in tot.most_common()))
    print(f'框边(左右+上下)上的跳 {len(edge)}: 角上(沿线<10% 或 >90%) '
          f'{sum(1 for r in edge if r[4] < 10 or r[4] > 90)}  边中段 '
          f'{sum(1 for r in edge if 10 <= r[4] <= 90)}')
    print('有跳的张数', len(sheets), ' 只有尖点的张数',
          sum(1 for v in sheets.values() if {r[1] for r in v} == {'尖点'}),
          ' 尖点涉及碎片', len({(c, r[3]) for c, v in sheets.items() for r in v if r[1] == '尖点'}))
