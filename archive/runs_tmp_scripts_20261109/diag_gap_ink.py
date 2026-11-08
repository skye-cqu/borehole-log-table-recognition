# -*- coding: utf-8 -*-
"""断口处到底有没有墨:把 P10 交付数据里的列线真断口拿到原图竖墨标尺下量一遍。

为什么量:去掉 1921 根无账弦之后,原先被弦填平的地方会真的断开。用户要的是"完全准确的列线",
所以每个断口必须能回答两问 —— 图上这儿本来就没有线(如实断开正确),还是阶段4/6a 漏检了(数据欠一段)。
标尺沿用 runs/tmp/yard_cols.py 的竖墨口径:自适应二值 → 1×40 竖条开运算 → 25px 竖向闭运算。

用法: python runs/tmp/diag_gap_ink.py [交付目录] [1024 1042]   # 无图号=该目录里全部
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

VLEN, CLOSE, SEARCH = 40, 25, 60      # 与 yard_cols 同一口径
MIN_GAP = 50.0                        # 只量 ≥50px 的断口(<此值肉眼看不出,也不影响用线)


def vmask(stem):
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8) * 255
    del gray
    v = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (1, VLEN)))
    del bw
    return cv2.morphologyEx(v, cv2.MORPH_CLOSE, np.ones((CLOSE, 1), np.uint8))


def unassigned(stem):
    """阶段4 里 label=high 的竖段中,没被任何列线认领的部分 —— 断口能不能就地用它填上。"""
    dd = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_分割线.json',
                        encoding='utf-8'))['lines']
    used = {i for l in dd for i in l.get('_orig_ids', [])}
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f'{stem}.json', encoding='utf-8'))
    return [np.asarray(s['points'], float) for s in cj['lines']
            if s['direction'] == 'vertical' and s['label'] == 'high' and s['id'] not in used]


def sheet(d, stem):
    v = vmask(stem)
    W = v.shape[1]
    j = json.load(open(d / '每张' / f'{stem}.json', encoding='utf-8'))
    free = unassigned(stem)
    st = Counter()
    worst = []
    for b in j['col_gaps']:
        for g in b['gaps']:
            a, z, x0, x1 = g['y0'], g['y1'], g['x0'], g['x1']
            if z - a < MIN_GAP:
                st['短断口'] += 1
                continue
            ys = np.arange(a, z)
            xs = x0 + (x1 - x0) * (ys - a) / (z - a)
            hit = np.zeros(len(ys), bool)
            for p in free:
                m = (p[:, 1] >= a) & (p[:, 1] <= z)
                if m.any():
                    d0 = np.abs(p[m][:, 0] - np.interp(p[m][:, 1], ys, xs))
                    if (d0 <= 12).any():
                        lo = int((p[m][d0 <= 12][:, 1] - a).min())
                        hi = int((p[m][d0 <= 12][:, 1] - a).max())
                        hit[max(0, lo):min(len(ys), hi + 1)] = True
            st['现成候选段可填px'] += int(hit.sum())
            hit2 = []
            for y in np.linspace(a, z, 25):
                yi = int(round(y))
                xi = x0 + (x1 - x0) * (y - a) / (z - a)
                lo, hi = max(0, int(xi) - SEARCH), min(W, int(xi) + SEARCH + 1)
                idx = np.flatnonzero(v[yi, lo:hi])
                hit2.append(float(np.abs(idx + lo - xi).min()) if len(idx) else np.inf)
            h = np.array(hit2)
            inked = (h <= 5.0).mean()
            cls = ('图上有线·我们漏了' if inked >= 0.8 else
                   '图上没线·断开属实' if (h > SEARCH).mean() >= 0.5 else '部分有墨(线走了别处)')
            st[cls] += 1
            st['墨占比合计'] += round(inked * 100)
            st['断口px'] += round(z - a)
            worst.append((stem[-4:], f"{b['kind']}:{b['col_name'] or b['col_index']}",
                          round(a), round(z), round(z - a), round(inked * 100), cls,
                          int(hit.sum())))
    return st, worst


CLS = ('图上有线·我们漏了', '图上没线·断开属实', '部分有墨(线走了别处)')


def main():
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        paths.OUTPUTS_DIR / '行列线数据集_列线分段_20260927'
    codes = [a for a in sys.argv[2:] if a.isdigit()]
    stems = [f'钻孔柱状图{c}' for c in codes] if codes else \
        sorted(p.name[:-5] for p in (d / '每张').glob('*.json'))
    tot, allw = Counter(), []
    for stem in stems:
        st, w = sheet(d, stem)
        tot.update(st)
        allw += w
        n = sum(st[c] for c in CLS)
        print(f"{stem[-4:]}: ≥50px 断口 {n} 处 {st['断口px']}px"
              f"｜漏检 {st['图上有线·我们漏了']}｜属实 {st['图上没线·断开属实']}"
              f"｜部分 {st['部分有墨(线走了别处)']}"
              f"｜现成候选段可填 {st['现成候选段可填px']}px({st['现成候选段可填px'] / max(st['断口px'], 1) * 100:.0f}%)"
              f"｜<50px 短断口 {st['短断口']}", flush=True)
    n = sum(tot[c] for c in CLS)
    print(f"\n合计 {len(stems)} 张 ≥50px 断口 {n} 处 {tot['断口px'] / 1000:.1f}k px: "
          f"漏检 {tot['图上有线·我们漏了']} 属实 {tot['图上没线·断开属实']} "
          f"部分 {tot['部分有墨(线走了别处)']}；平均墨覆盖率 {tot['墨占比合计'] / max(n, 1):.0f}%"
          f"；现成候选段只能填 {tot['现成候选段可填px'] / max(tot['断口px'], 1) * 100:.0f}%"
          f"；<50px 短断口 {tot['短断口']} 处")
    print('最长的 15 处:')
    for r in sorted(allw, key=lambda t: -t[4])[:15]:
        print('  ', r)


if __name__ == '__main__':
    main()
