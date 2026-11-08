# -*- coding: utf-8 -*-
"""框边上的"突然大跳转"定位 + 矩形度(用户 2026-09-27 定的口径:外框要连起来、近似矩形、边上不许突跳)。

`yard_frame.py` 量出 30 张 60 条框边里 57 条有 >12px 的单跳,其中 58~67px 那一档在二十几张上齐刷刷出现
→ 不像扫描噪声,像同一个成因。本脚本把每一跳落到**具体 y、前后 x、两端点所属阶段4 碎片 id、同碎片还是跨碎片**,
并量每条框边偏离"该边两角点连线"的最大距离(矩形度,角点取 6e `_闭合外框.json`)。

坐标约定:点列是 (x,y)。竖边(left/right)沿 y 前进、跳转看 x;横边(top/bottom)沿 x 前进、跳转看 y。
只读。用法: python runs/tmp/diag_edge_steps.py [1015 1042]
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import col_segments as cs                            # noqa: E402

STEP = 40.0                                  # 单跳阈值(px)
R = paths.RUNS_DIR / 'table_reconstruct'


def frag_of(stem):
    """(x,y) → 拥有该点的阶段4 碎片 id 列表。"""
    fp = {}
    for pid, a in cs.frag_points(stem).items():
        for p in a:
            fp.setdefault((round(float(p[0])), round(float(p[1]))), []).append(pid)
    return fp


def jumps(items, vert, fp):
    """[(点列, _)] → 单跳 [(沿线坐标, 前值, 后值, 同碎片?, [碎片id])]。竖边看 x 跳、横边看 y 跳。"""
    i_pos, i_val = (1, 0) if vert else (0, 1)
    out = []
    for pts, _ in items:
        a = np.asarray(pts, float)
        for k in range(len(a) - 1):
            v0, v1 = a[k, i_val], a[k + 1, i_val]
            if abs(v1 - v0) < STEP:
                continue
            k0 = (round(a[k, 0]), round(a[k, 1]))
            k1 = (round(a[k + 1, 0]), round(a[k + 1, 1]))
            s0, s1 = set(fp.get(k0, [])), set(fp.get(k1, []))
            out.append((float(a[k, i_pos]), float(v0), float(v1), bool(s0 & s1),
                        sorted(s0 | s1)))
    return out


def rect_dev(pts, c0, c1, vert):
    """边点列相对"该边两角点直线"的最大偏离(px);角点缺失或退化 → None。"""
    if not (c0 and c1):
        return None
    ia, ib = (1, 0) if vert else (0, 1)          # 沿边方向 / 偏离方向
    if abs(float(c1[ia]) - float(c0[ia])) < 50:
        return None
    a = np.vstack([np.asarray(p, float) for p in pts])
    ref = np.interp(a[:, ia], [c0[ia], c1[ia]], [c0[ib], c1[ib]])
    return float(np.abs(a[:, ib] - ref).max())


def sheet(stem, show):
    book = cs.line_parts(stem)
    fp = frag_of(stem)
    cf = R / f'{stem}_闭合外框.json'
    cor = json.load(open(cf, encoding='utf-8'))['corners'] if cf.exists() else {}
    cols = [l for l in book['lines'] if l['kind'] == 'column']
    yv = np.array([p[1] for l in cols for pts, _ in l['parts'] for p in pts])
    out = []
    for side in ('left', 'right'):
        rec = next((l for l in book['lines'] if l['kind'] == 'edge' and l['side'] == side), None)
        if not rec or not rec['parts']:
            out.append((f'{side}边', '缺档', None, []))
            continue
        pts = [(np.asarray(p, float), i) for p, i in rec['parts']]
        dv = rect_dev([p for p, _ in pts], cor.get('TL' if side == 'left' else 'TR'),
                      cor.get('BL' if side == 'left' else 'BR'), True)
        jm = jumps(pts, True, fp)
        out.append((f'{side}边', len(jm), dv, jm[:show]))
    tj = R / f'{stem}_上下框.json'
    tf = json.load(open(tj, encoding='utf-8')) if tj.exists() else {}
    for kind, k0, k1 in (('top框', 'TL', 'TR'), ('bottom框', 'BL', 'BR')):
        gs = [(np.asarray(g['pts'], float), g) for g in tf.get(kind[:-1], {}).get('groups', [])
              if g.get('pts')]
        if not gs:
            out.append((kind, '无组', None, []))
            continue
        dv = rect_dev([p for p, _ in gs], cor.get(k0), cor.get(k1), False)
        jm = jumps(gs, False, fp)
        span = float(np.ptp(np.vstack([p for p, _ in gs])[:, 0]))
        out.append((kind, f'{len(jm)}跳 跨{span:.0f}px', dv, jm[:show]))
    return stem[-4:], out, (round(float(yv.min())), round(float(yv.max())))


def main():
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
            sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob('*.json'))
    show = 999
    cnt, devs, cross = Counter(), [], Counter()
    for c in codes:
        code, rows, yr = sheet(f'钻孔柱状图{c}', show)
        print(f"== {code} 表y{yr[0]}~{yr[1]}")
        for nm, n, dv, jm in rows:
            print(f"   {nm:<7} 单跳≥{STEP:.0f}px {n} 处  离两角点连线最大偏 "
                  f"{'—' if dv is None else format(dv, '.0f')}px")
            for pos, v0, v1, same, ids in jm:
                ax = 'y' if nm.endswith('边') else 'x'
                cross['同碎片内' if same else '跨碎片'] += 1
                print(f"      {ax}={pos:.0f} 跳 {v0:.0f}→{v1:.0f} ({v1 - v0:+.0f}px) "
                      f"{'同碎片内' if same else '跨碎片'} 碎片{ids[:2]}")
            if isinstance(n, int):
                cnt[nm[:4]] += n
            if dv is not None:
                devs.append((code, nm, dv))
    print(f"\n合计 {len(codes)} 张: 抽打的跳因分布 {dict(cross)}")
    print('离角点连线最偏 12 条:', [(c, nm, round(d)) for c, nm, d in sorted(devs, key=lambda t: -t[2])[:12]])
    if devs:
        print(f"离角点连线 ≤25px 的边: {sum(1 for _, _, d in devs if d <= 25)}/{len(devs)}")


if __name__ == '__main__':
    main()
