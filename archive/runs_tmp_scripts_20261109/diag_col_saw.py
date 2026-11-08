# -*- coding: utf-8 -*-
"""P10 锯齿定性:把 6d `_外框叠加图.png` 上画出来的斜穿按成因分账。不修任何东西。

实测前提(2026-09-27,30 张):`_分割线.json` 的 `lines[].pts` **与 `_orig_ids` 各阶段4
碎片的点集逐点全等**,只是被按 y 全局排过序;`frame_topbottom.py:302-305` 又把这串排序后的
点当**一条**折线画 → 每处碎片间断口都连成一根直线弦。数据无罪,是画法。

分账口径:相邻两点 p_i→p_{i+1}(纵向 ≥2px 且横向漂移 ≥3px)是一段落笔。
  A 跨碎片弦  没有任何一条碎片同时含 p_i 与 p_{i+1} → 改逐碎片画即可消(零数据改动)
  B 碎片内爬行  某条碎片同时含两端 → 阶段4 碎片自己就斜,需逐点验真才治得了
另单量柱状带污染:整段落在 content_band 里的碎片(= 图案边线被并进了列线)。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import paths  # noqa: E402
from src.table import track_rows  # noqa: E402

MIN_DY, MIN_DX = 2.0, 3.0


def load(stem):
    lines = json.load(open(paths.RUNS_DIR / 'table_reconstruct' /
                           f'{stem}_分割线.json', encoding='utf-8'))['lines']
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f'{stem}.json', encoding='utf-8'))
    seg = {s['id']: np.asarray(s['points'], float)
           for s in cj['lines'] if s['direction'] == 'vertical'}
    return lines, seg


def classify(pts, frags):
    """返回 (A跨碎片弦, B碎片内爬行, 最长弦长度)。"""
    keys = [{tuple(p) for p in f} for f in frags]
    pset = {tuple(p): i for i, p in enumerate(pts)}
    owners = [set() for _ in pts]
    for k, fk in enumerate(keys):
        for pt in fk:
            i = pset.get(pt)
            if i is not None:
                owners[i].add(k)
    a = b = 0
    worst = 0.0
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if abs(q[1] - p[1]) < MIN_DY or abs(q[0] - p[0]) < MIN_DX:
            continue
        span = float(np.hypot(q[0] - p[0], q[1] - p[1]))
        if owners[i] & owners[i + 1]:
            b += 1
        else:
            a += 1
            worst = max(worst, span)
    return a, b, worst


def band_count(frags, band):
    return sum(1 for f in frags if track_rows.in_band(f, band))


def measure_delivery(stems, d):
    """同口径复检交付数据:把 每张/*.json 里每条列线/外框**段**的落笔斜穿分账。
    A 跨碎片弦应当为 0(段内相邻点必出自同一碎片);B 碎片内爬行 = 阶段4 自己的歪,P10 不动它。"""
    tot = Counter()
    worst = 0.0
    for stem in stems:
        seg = {i: f for i, f in _frags(stem).items()}
        dd = json.load(open(d / '每张' / f'{stem}.json', encoding='utf-8'))
        for ln in dd['lines']:
            if ln['kind'] == 'row' or ln['backing'] != 'frag':
                continue
            pts = np.asarray(ln['points'], float)
            frags = [seg[i] for i in ln['segment_ids'] if i in seg]
            a, b, w = classify(pts, frags)
            tot['A'] += a
            tot['B'] += b
            tot['pts'] += len(pts)
            tot['段'] += 1
            worst = max(worst, w)
    print(f"复检交付数据 {d.name}: {len(stems)} 张 {tot['段']} 段 {tot['pts']} 点 → "
          f"A 跨碎片弦 {tot['A']}  B 碎片内爬行 {tot['B']}  最长斜穿 {worst:.0f}px")


def _frags(stem):
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f'{stem}.json', encoding='utf-8'))
    return {s['id']: np.asarray(s['points'], float)
            for s in cj['lines'] if s['direction'] == 'vertical'}


def main():
    if sys.argv[1:2] == ['--delivery']:
        d = Path(sys.argv[2])
        stems = sorted(p.name[:-5] for p in (d / '每张').glob('*.json'))
        measure_delivery(stems, d)
        return
    stems = sys.argv[1:] or [f'钻孔柱状图{n}' for n in range(1015, 1045)]
    tot, rows = Counter(), []
    for stem in stems:
        lines, seg = load(stem)
        w, e, src = track_rows.content_band(stem)
        band = (w, e) if w is not None else None
        for ln in lines:
            frags = [seg[i] for i in ln.get('_orig_ids', []) if i in seg]
            pts = np.asarray(ln['pts'], float)
            a, b, worst = classify(pts, frags)
            nb = band_count(frags, band) if band else 0
            tot['A'] += a
            tot['B'] += b
            tot['pts'] += len(pts)
            tot['弦最长'] = max(tot['弦最长'], worst)
            if a or b:
                rows.append((stem[-4:], f"{ln['kind']}{ln.get('index', '')}",
                             a, b, worst, nb, len(frags)))
    print(f"落笔斜穿合计: A 跨碎片弦 {tot['A']}  B 碎片内爬行 {tot['B']}  "
          f"(全 30 张 {tot['pts']} 个点, 最长弦 {tot['弦最长']:.0f}px)")
    rows.sort(key=lambda r: -(r[2] + r[3]))
    print('\nTop15 线 (A=改画法即消, B=需逐点验真, 带内=图案边线条数/该线碎片总数):')
    print(f"{'图':>5} {'线':>10} {'A':>4} {'B':>4} {'最长弦':>6} {'带内':>8}")
    for n, tag, a, b, w, nb, m in rows[:15]:
        print(f'{n:>5} {tag:>10} {a:>4} {b:>4} {w:>6.0f} {nb:>4}/{m:<3}')
    print('\n带内碎片非零的列线 (图案边线被并进列线):')
    for n, tag, a, b, w, nb, m in sorted(rows):
        if nb:
            print(f'  {n} {tag:>9} 带内碎片 {nb}/{m}  A{a} B{b}')
    print(f"\n受影响面: A>0 的线 {sum(1 for r in rows if r[2])} 条 / "
          f"B>0 的线 {sum(1 for r in rows if r[3])} 条 / 总线数 {sum(1 for s in stems for l in load(s)[0])}")


if __name__ == '__main__':
    main()
