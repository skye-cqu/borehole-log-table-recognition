# -*- coding: utf-8 -*-
"""诊断：1035/1042 控制线（列线+左右外框）混轨/跳变/交叉检查，全量 30 张结构普查。

只读检查，不修改任何产物。输出文本报告 + 可疑区域高清裁片到 runs/tmp/diag_crop/。
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
CROP_DIR = paths.RUNS_DIR / 'tmp' / 'diag_crop'
CROP_DIR.mkdir(parents=True, exist_ok=True)


def load(stem):
    m = json.load(open(TR_DIR / f'{stem}_矫正映射.json', encoding='utf-8'))
    return m


def profile(pts):
    """折线 → 按 y 排序的 (ys, xs)。"""
    arr = np.asarray(pts, float)
    order = np.argsort(arr[:, 1])
    arr = arr[order]
    return arr[:, 1], arr[:, 0]


def line_stats(name, pts, imgh):
    ys, xs = profile(pts)
    d = np.abs(np.diff(xs))
    dy = np.abs(np.diff(ys))
    top_j = np.argsort(d)[::-1][:3]
    jumps = [(round(float(ys[i]), 0), round(float(xs[i]), 0), round(float(xs[i + 1]), 0)) for i in top_j if d[i] > 8]
    cov = (ys.max() - ys.min()) / imgh
    return {'name': name, 'n': len(ys), 'median_x': float(np.median(xs)),
            'x_lo': float(xs.min()), 'x_hi': float(xs.max()),
            'drift': float(xs.max() - xs.min()), 'cover': round(float(cov), 2),
            'jumps': jumps, 'ys': ys, 'xs': xs}


def ink_support(gray, ys, xs, win=6, thresh=110):
    """沿折线采样，±win px 内存在暗像素的比例。"""
    h, w = gray.shape
    ok = 0
    tot = 0
    for y, x in zip(ys[::2], xs[::2]):
        yi = int(round(y))
        if yi < 0 or yi >= h:
            continue
        xi = int(round(x))
        lo, hi = max(0, xi - win), min(w, xi + win + 1)
        seg = gray[yi, lo:hi]
        tot += 1
        if seg.size and seg.min() < thresh:
            ok += 1
    return ok / max(1, tot)


def cross_count(la, lb, step=2.0):
    """相邻两线在共同 y 范围内 x_a(y) >= x_b(y)-1 的行数与首末 y。"""
    y0 = max(la['ys'].min(), lb['ys'].min())
    y1 = min(la['ys'].max(), lb['ys'].max())
    if y1 <= y0:
        return 0, None, None
    yg = np.arange(y0, y1, step)
    xa = np.interp(yg, la['ys'], la['xs'])
    xb = np.interp(yg, lb['ys'], lb['xs'])
    bad = xa >= xb - 1.0
    if not bad.any():
        return 0, None, None
    idx = np.where(bad)[0]
    return int(bad.sum()), float(yg[idx[0]]), float(yg[idx[-1]])


def diag_stem(stem, do_ink=False, crops=False):
    m = load(stem)
    W, Hh = m['rect_size']
    margin = m['margin']
    imgw, imgh = W + 2 * margin, Hh + 2 * margin
    print(f"===== {stem} (rect {imgw}x{imgh}) =====")
    gray = None
    if do_ink:
        gray = cv2.imread(str(TR_DIR / f'{stem}_表格矫正.png'), cv2.IMREAD_GRAYSCALE)

    lines = []
    for s in ('left', 'right'):
        st = line_stats(f'side_{s}', m['lines_rect']['sides'][s], imgh)
        lines.append(st)
    for c in m['lines_rect']['columns']:
        lines.append(line_stats(f"col{c['index']}", c['pts'], imgh))

    for st in lines:
        sup = ''
        if gray is not None:
            sup = f" 墨迹支撑={ink_support(gray, st['ys'], st['xs']):.2f}"
        print(f"  {st['name']:>9}: n={st['n']:4d} median_x={st['median_x']:7.1f} "
              f"x=[{st['x_lo']:7.1f},{st['x_hi']:7.1f}] 漂移={st['drift']:5.1f} "
              f"y覆盖={st['cover']:.2f}{sup} 跳变={st['jumps']}")
        if crops and st['jumps']:
            crop = cv2.imread(str(TR_DIR / f'{stem}_表格矫正.png'))
            for jy, jx0, jx1 in st['jumps']:
                y0, y1 = int(max(0, jy - 60)), int(min(gray.shape[0] if gray is not None else imgh, jy + 60))
                x0, x1 = int(max(0, min(jx0, jx1) - 120)), int(min(imgw, max(jx0, jx1) + 120))
                if y1 <= y0 or x1 <= x0:
                    print(f"      跳变 y={jy:.0f} 超出图像范围，无法裁片（点在图外）")
                    continue
                piece = crop[y0:y1, x0:x1]
                if piece.size == 0:
                    continue
                out = CROP_DIR / f'{stem}_{st["name"]}_jump_y{int(jy)}.png'
                cv2.imwrite(str(out), piece)
                print(f"      跳变裁片 -> {out.name}")
    # 图外点统计
    for s in ('left', 'right'):
        ys, xs = profile(m['lines_rect']['sides'][s])
        out_n = int(((ys < 0) | (ys > imgh) | (xs < 0) | (xs > imgw)).sum())
        print(f"  side_{s} 图外点数={out_n}/{len(ys)}  y范围=[{ys.min():.0f},{ys.max():.0f}]")

    # 相邻交叉检查（按 median 排序）
    srt = sorted(lines, key=lambda s: s['median_x'])
    print("  相邻交叉检查:")
    for a, b in zip(srt, srt[1:]):
        cnt, y0, y1 = cross_count(a, b)
        flag = ' <-- 交叉!' if cnt else ''
        if cnt:
            print(f"    {a['name']} vs {b['name']}: {cnt} 行交叉, y∈[{y0:.0f},{y1:.0f}]{flag}")
    print("  （未列出的相邻对无交叉）")

    # sides 全高 x 分布（看双轨）
    for s in ('left', 'right'):
        ys, xs = profile(m['lines_rect']['sides'][s])
        qs = np.percentile(xs, [0, 10, 25, 50, 75, 90, 100])
        print(f"  side_{s} x 分位[0,10,25,50,75,90,100]: {[round(float(q),1) for q in qs]}")
    return m


def global_census():
    print("===== 全量 30 张结构普查（跳变>8px 的线数 / 相邻交叉行数） =====")
    stems = sorted('%d' % i for i in range(1015, 1045))
    for n in stems:
        stem = '钻孔柱状图' + n
        m = load(stem)
        W, Hh = m['rect_size']
        imgh = Hh + 50
        lines = []
        for s in ('left', 'right'):
            lines.append(line_stats(f'side_{s}', m['lines_rect']['sides'][s], imgh))
        for c in m['lines_rect']['columns']:
            lines.append(line_stats(f"col{c['index']}", c['pts'], imgh))
        njump = sum(1 for st in lines if st['jumps'])
        srt = sorted(lines, key=lambda s: s['median_x'])
        xcnt = 0
        xdetail = []
        for a, b in zip(srt, srt[1:]):
            cnt, y0, y1 = cross_count(a, b, step=4.0)
            xcnt += cnt
            if cnt:
                xdetail.append(f"{a['name']}|{b['name']}:{cnt}行(y{y0:.0f}~{y1:.0f})")
        print(f"  {n}: 跳变线数={njump} 交叉总行数={xcnt} {'; '.join(xdetail) if xdetail else ''}")


def compare_closure(stem):
    """sides 与 闭合外框.json 的映射一致性 + 闭合外框 left/right 链自身结构。"""
    m = load(stem)
    cf = json.load(open(TR_DIR / f'{stem}_闭合外框.json', encoding='utf-8'))
    H_sr = np.asarray(m['H_src_to_rect'], np.float64)
    print(f"===== {stem} sides 与闭合外框对比 =====")
    for s in ('left', 'right'):
        cfpts = np.asarray(cf[s]['pts'], float).reshape(-1, 1, 2)
        mapped = cv2.perspectiveTransform(cfpts, H_sr).reshape(-1, 2)
        rpts = np.asarray(m['lines_rect']['sides'][s], float)
        n = min(len(mapped), len(rpts))
        diff = np.abs(mapped[:n] - rpts[:n]).max() if n else -1
        print(f"  {s}: 闭合外框点数={len(cf[s]['pts'])} sides点数={len(rpts)} 映射后最大差={diff:.2f}")
        keys = [k for k in cf[s].keys() if k != 'pts']
        print(f"    闭合外框 {s} 字段: {keys}")
        for k in keys:
            v = cf[s][k]
            print(f"      {k} = {json.dumps(v, ensure_ascii=False)[:300]}")


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if mode in ('all', 'census'):
        global_census()
    if mode in ('all', 'two'):
        diag_stem('钻孔柱状图1035', do_ink=True, crops=True)
        diag_stem('钻孔柱状图1042', do_ink=True, crops=True)
    if mode in ('all', 'closure'):
        compare_closure('钻孔柱状图1035')
        compare_closure('钻孔柱状图1042')
