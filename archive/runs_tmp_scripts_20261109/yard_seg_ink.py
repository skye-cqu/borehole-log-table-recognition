# -*- coding: utf-8 -*-
"""交付线段级标尺:逐段量"这段列线/外框边贴不贴原图真竖墨"——约束2 的可执行检查。

沿用 runs/tmp/yard_cols.py 的竖墨口径(自适应二值 → 1×40 竖条开运算 → 25px 竖向闭运算),
但对的是 **交付数据里的每一段**(backing=frag/fill/extend),不再是整条定稿链:
  贴墨率 = 段内纵向 20 个采样里,±5px 内有竖墨的比例。
  ≥0.8 贴墨 / <0.2 = 悬空(这段在原图里没有对应的竖线,该剔) / 中间 = 部分贴墨。
补全段(fill/extend)单独一档:它们是 6a2 登记过的断口桥,悬空就要命。

用法: python runs/tmp/yard_seg_ink.py [交付目录] [1024 1042]   # 无图号=该目录全部
"""
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.table import track_rows as tr  # noqa: E402

VLEN, CLOSE, TOL, N = 40, 25, 5.0, 20


def vmask(stem):
    g = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8) * 255
    del g
    v = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (1, VLEN)))
    del bw
    return cv2.morphologyEx(v, cv2.MORPH_CLOSE, np.ones((CLOSE, 1), np.uint8))


def sheet(d, stem):
    v = vmask(stem)
    W = v.shape[1]
    j = json.load(open(d / '每张' / f'{stem}.json', encoding='utf-8'))
    st, bad = Counter(), []
    for ln in j['lines']:
        if ln['kind'] == 'row':
            continue
        P = np.asarray(ln['points'], float)
        if ln['backing'] == 'extend':                     # 外延是从端点往外探墨,采样它的每一段沿程
            ys = np.linspace(P[:, 1].min(), P[:, 1].max(), N)
            xs = np.interp(ys, P[:, 1], P[:, 0])
        else:
            ys, xs = P[:, 1], P[:, 0]
        hit = []
        for y, x in zip(ys, xs):
            yi, xi = int(round(y)), int(round(x))
            if not 0 <= yi < v.shape[0]:
                continue
            idx = np.flatnonzero(v[yi, max(0, xi - 30):min(W, xi + 31)])
            hit.append(bool(len(idx)) and float(np.abs(idx + max(0, xi - 30) - xi).min()) <= TOL)
        frac = np.mean(hit) if hit else 0.0
        st[ln['backing']] += 1
        st[f'{ln["backing"]}贴墨'] += int(frac >= 0.8)
        st[f'{ln["backing"]}悬空'] += int(frac < 0.2)
        if frac < 0.2:
            bad.append((stem[-4:], ln['line_id'], ln['kind'], ln['col_index'], ln['backing'],
                        ln['n_pts'], round(frac, 2),
                        [round(u, 1) for u in (ln['x0'], ln['y0'], ln['x1'], ln['y1'])]))
    return st, bad


def main():
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        paths.OUTPUTS_DIR / '行列线数据集_列线分段_20260927'
    codes = [a for a in sys.argv[2:] if a.isdigit()]
    stems = [f'钻孔柱状图{c}' for c in codes] if codes else \
        sorted(p.name[:-5] for p in (d / '每张').glob('*.json'))
    tot, allbad = Counter(), []
    for stem in stems:
        st, bad = sheet(d, stem)
        tot.update(st)
        allbad += bad
        print(f"{stem[-4:]}: 真段 {st['frag']} 贴墨{st['frag贴墨']} 悬空{st['frag悬空']}｜"
              f"桥接段 {st['fill']} 贴墨{st['fill贴墨']} 悬空{st['fill悬空']}｜"
              f"外延段 {st['extend']} 贴墨{st['extend贴墨']} 悬空{st['extend悬空']}", flush=True)
    seg = tot['frag'] + tot['fill'] + tot['extend']
    off = tot['frag悬空'] + tot['fill悬空'] + tot['extend悬空']
    print(f"\n合计 {len(stems)} 张 {seg} 段: 贴墨 {seg - off} ({(seg - off) / max(seg, 1) * 100:.1f}%)"
          f"  悬空 {off} ({off / max(seg, 1) * 100:.1f}%)"
          f"  [真段 悬空{tot['frag悬空']}/{tot['frag']} 桥接 悬空{tot['fill悬空']}/{tot['fill']}"
          f" 外延 悬空{tot['extend悬空']}/{tot['extend']}]")
    for b in sorted(allbad, key=lambda t: t[6])[:20]:
        print('  悬空段', b)


if __name__ == '__main__':
    main()
