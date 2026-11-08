# -*- coding: utf-8 -*-
"""按 seg 溯源分析问题线：闭合外框 sides 的 segs、分割线 columns 的来源折线。

对每段输出：prov、n、src y 跨度、src x 范围、映射后 rect x 范围。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402

TR_DIR = paths.RUNS_DIR / 'table_reconstruct'


def map_pts(H, pts):
    arr = np.asarray(pts, np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(arr, H).reshape(-1, 2)


def seg_report(name, segs, H, imgh):
    print(f"  --- {name} 共 {len(segs)} 段 ---")
    for i, sg in enumerate(segs):
        pts = sg.get('pts', [])
        prov = sg.get('prov', '?')
        n = sg.get('n', len(pts))
        if not pts:
            print(f"    seg{i:02d} {prov:<12} n={n} (无点，gap={sg.get('gap')})")
            continue
        arr = np.asarray(pts, float)
        mp = map_pts(H, arr) if H is not None else arr
        print(f"    seg{i:02d} {prov:<12} n={n:3d} src_y=[{arr[:,1].min():6.0f},{arr[:,1].max():6.0f}] "
              f"src_x=[{arr[:,0].min():6.0f},{arr[:,0].max():6.0f}] "
              f"rect_x=[{mp[:,0].min():7.1f},{mp[:,0].max():7.1f}] rect_y=[{mp[:,1].min():6.0f},{mp[:,1].max():6.0f}]")


def main():
    stem = sys.argv[1]           # 如 钻孔柱状图1042
    which = sys.argv[2] if len(sys.argv) > 2 else 'sides'
    m = json.load(open(TR_DIR / f'{stem}_矫正映射.json', encoding='utf-8'))
    H_sr = np.asarray(m['H_src_to_rect'], np.float64)
    imgh = m['rect_size'][1] + 50

    if which in ('sides', 'all'):
        cf = json.load(open(TR_DIR / f'{stem}_闭合外框.json', encoding='utf-8'))
        for s in ('left', 'right'):
            seg_report(f'闭合外框.{s}', cf[s]['segs'], H_sr, imgh)
    if which in ('cols', 'all'):
        d = json.load(open(TR_DIR / f'{stem}_分割线.json', encoding='utf-8'))
        idxs = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
        print(f"  分割线.json 顶层键: {list(d.keys())}")
        for c in d['lines']:
            if c.get('kind') != 'column':
                continue
            if idxs and c.get('index') not in idxs:
                continue
            extra = {k: v for k, v in c.items() if k not in ('pts', 'kind', 'index', 'n')}
            print(f"  --- col{c.get('index')} 字段: {list(c.keys())} ---")
            if extra:
                print(f"      附加: {json.dumps(extra, ensure_ascii=False)[:400]}")
            segs = c.get('segs')
            if segs:
                seg_report(f"分割线 col{c.get('index')}", segs, H_sr, imgh)
            else:
                pts = np.asarray(c['pts'], float)
                mp = map_pts(H_sr, pts)
                print(f"    整线 n={len(pts)} src_x=[{pts[:,0].min():.0f},{pts[:,0].max():.0f}] "
                      f"src_y=[{pts[:,1].min():.0f},{pts[:,1].max():.0f}] rect_x=[{mp[:,0].min():.1f},{mp[:,0].max():.1f}]")


if __name__ == '__main__':
    main()
