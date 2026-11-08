# -*- coding: utf-8 -*-
"""轨道提取实验：从之字混轨的落账折线中选出真墨迹轨（多数轨 vs 少数轨）。

选择依据（只用已落账点，不拟合）：
  1. 剔除图外点；
  2. 滚动中位数(window=9)求局部趋势，|残差|>15px 的点为"少数轨"候选；
  3. 若少数轨点数>=8 且 y 覆盖>50%：与相邻列线比漂移相关性，相关性高者胜；
  4. 选择后自查：相邻点 |dx|<=15px、无内部交叉。
输出：全部 30 张的检查报告 + 问题线的验证叠加裁片。
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

TR = paths.RUNS_DIR / 'table_reconstruct'
OUT = paths.RUNS_DIR / 'tmp' / 'diag_crop'
DEV = 15.0     # 残差分轨阈值
WIN = 9        # 滚动中位数窗口


def rolling_median(x, win=WIN):
    n = len(x)
    out = np.empty(n)
    r = win // 2
    for i in range(n):
        lo, hi = max(0, i - r), min(n, i + r + 1)
        out[i] = np.median(x[lo:hi])
    return out


def extract_track(pts, imgw, imgh):
    """返回 (主轨ys,xs, 少数轨ys,xs, 报告dict)。主轨=剔除|残差|>DEV 后的内点。"""
    arr = np.asarray(pts, float)
    # 1. 图外点剔除
    inb = (arr[:, 1] >= -2) & (arr[:, 1] <= imgh + 2) & (arr[:, 0] >= -2) & (arr[:, 0] <= imgw + 2)
    n_out = int((~inb).sum())
    arr = arr[inb]
    order = np.argsort(arr[:, 1])
    arr = arr[order]
    ys, xs = arr[:, 1], arr[:, 0]
    # 2. 残差分轨：主轨=内点，少数轨=离群点
    trend = rolling_median(xs)
    r = xs - trend
    minor = np.abs(r) > DEV
    rep = {'n_out': n_out, 'n': len(xs), 'n_minor': int(minor.sum())}
    if minor.sum() >= 8:
        ycov = (ys[minor].max() - ys[minor].min()) / max(1.0, imgh)
        rep['minor_cov'] = round(float(ycov), 2)
        if ycov > 0.5:
            rep['minor_track'] = (ys[minor], xs[minor])
    return (ys[~minor], xs[~minor]), rep.get('minor_track', None), rep


def ink_support(gray, ys, xs, win=8, thresh=150):
    h, w = gray.shape
    ok = 0
    tot = 0
    for y, x in zip(ys, xs):
        yi = int(round(y))
        if yi < 0 or yi >= h:
            continue
        xi = int(round(x))
        lo, hi = max(0, xi - win), min(w, xi + win + 1)
        tot += 1
        if gray[yi, lo:hi].size and gray[yi, lo:hi].min() < thresh:
            ok += 1
    return ok / max(1, tot)


def drift_corr(ys_a, xs_a, ys_b, xs_b):
    """两条折线在共同 y 范围内去均值后的漂移相关性。"""
    y0 = max(ys_a.min(), ys_b.min())
    y1 = min(ys_a.max(), ys_b.max())
    if y1 - y0 < 2000:
        return 0.0
    yg = np.arange(y0 + 50, y1 - 50, 50.0)
    xa = np.interp(yg, ys_a, xs_a)
    xb = np.interp(yg, ys_b, xs_b)
    ra, rb = xa - xa.mean(), xb - xb.mean()
    da = np.linalg.norm(ra)
    db = np.linalg.norm(rb)
    if da < 1e-6 or db < 1e-6:
        return 0.0
    return float((ra * rb).sum() / (da * db))


def smoothness(ys, xs, max_dy=150.0):
    """局部之字度量：仅统计 Δy<=max_dy 的相邻点对的最大 |dx|。"""
    if len(xs) < 3:
        return 0.0
    dy = np.abs(np.diff(ys))
    dx = np.abs(np.diff(xs))
    sel = dy <= max_dy
    return float(dx[sel].max()) if sel.any() else 0.0


def process_stem(n, make_crops=False):
    stem = '钻孔柱状图' + n
    m = json.load(open(TR / f'{stem}_矫正映射.json', encoding='utf-8'))
    W, Hh = m['rect_size']
    imgw, imgh = W + 50, Hh + 50
    gray = cv2.imread(str(TR / f'{stem}_表格矫正.png'), cv2.IMREAD_GRAYSCALE)
    report = []
    keepers = {}   # name -> (ys,xs) 选用轨
    minor_tracks = {}
    for s in ('left', 'right'):
        pts = m['lines_rect']['sides'][s]
        (ys, xs), minor, rep = extract_track(pts, imgw, imgh)
        name = f'side_{s}'
        rec = {'name': name, **rep}
        if minor is not None:
            minor_tracks[name] = minor
        keepers[name] = (ys, xs)
        report.append(rec)
    cols = []
    for c in m['lines_rect']['columns']:
        (ys, xs), minor, rep = extract_track(c['pts'], imgw, imgh)
        name = f"col{c['index']}"
        rec = {'name': name, **rep}
        if minor is not None:
            minor_tracks[name] = minor
        cols.append((name, ys, xs))
        keepers[name] = (ys, xs)
        report.append(rec)

    # 少数轨 vs 主轨：与相邻列线的漂移相关性
    col_sorted = sorted(cols, key=lambda t: np.median(t[2]))
    decisions = {}
    for name, minor in minor_tracks.items():
        mys, mxs = minor
        cands = [t for t in col_sorted]
        if name.startswith('side_'):
            nbr = col_sorted[0] if name == 'side_left' else col_sorted[-1]
        else:
            k = [i for i, t in enumerate(col_sorted) if t[0] == name][0]
            nbr = col_sorted[k - 1] if k > 0 else col_sorted[k + 1] if k + 1 < len(col_sorted) else None
        if nbr is None:
            continue
        c_major = drift_corr(keepers[name][0], keepers[name][1], nbr[1], nbr[2])
        c_minor = drift_corr(mys, mxs, nbr[1], nbr[2])
        s_major = ink_support(gray, *keepers[name])
        s_minor = ink_support(gray, mys, mxs)
        pick_minor = (c_minor > c_major + 0.3) and (s_minor >= s_major - 0.25)
        decisions[name] = {'c_major': round(c_major, 2), 'c_minor': round(c_minor, 2),
                           's_major': round(s_major, 2), 's_minor': round(s_minor, 2),
                           'pick': 'minor' if pick_minor else 'major',
                           'minor_smooth': smoothness(mys, mxs)}
        if pick_minor:
            keepers[name] = (mys, mxs)

    # 选择后平滑与交叉检查
    final = {}
    for name, (ys, xs) in keepers.items():
        final[name] = (ys, xs, smoothness(ys, xs))
    for rec in report:
        name = rec['name']
        ys, xs, sm = final[name]
        rec['picked_smooth'] = round(sm, 1)
        if name in decisions:
            rec.update(decisions[name])
    if make_crops:
        make_overlay(stem, m, final, minor_tracks, decisions, gray)
    return report


def make_overlay(stem, m, final, minor_tracks, decisions, gray):
    img = cv2.imread(str(TR / f'{stem}_表格矫正.png'))
    H_img = img.shape[0]
    bands = [(0, 2600), (2600, 5200), (5200, 7800), (7800, 10400),
             (10400, 13000), (13000, 15600), (15600, H_img)]
    for name in list(decisions.keys()):
        for bi, (y0, y1) in enumerate(bands):
            vis = img[y0:y1].copy()
            ys, xs, _ = final[name]
            sel = (ys >= y0) & (ys < y1)
            if sel.sum() >= 2:
                p = np.stack([xs[sel], ys[sel] - y0], 1).astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(vis, [p], False, (0, 0, 255), 2, cv2.LINE_AA)
            if name in minor_tracks:
                mys, mxs = minor_tracks[name]
                sel = (mys >= y0) & (mys < y1)
                if sel.sum() >= 2:
                    p = np.stack([mxs[sel], mys[sel] - y0], 1).astype(np.int32).reshape(-1, 1, 2)
                    cv2.polylines(vis, [p], False, (0, 255, 0), 2, cv2.LINE_AA)
            out = OUT / f'fix_{stem}_{name}_y{y0}.png'
            piece = np.ascontiguousarray(vis[:, :200])
            if piece.size:
                cv2.imwrite(str(out), piece)
    print(f"  叠加裁片已输出到 {OUT} (fix_{stem}_*)")


if __name__ == '__main__':
    stems = sorted('%d' % i for i in range(1015, 1045))
    crops_for = sys.argv[1].split(',') if len(sys.argv) > 1 else []
    for n in stems:
        rep = process_stem(n, make_crops=(n in crops_for))
        flags = [r for r in rep if r.get('n_minor', 0) >= 8 or r.get('picked_smooth', 0) > 15
                 or r.get('n_out', 0) > 0]
        if flags:
            print(f"== {n} ==")
            for r in flags:
                extra = ''
                for k in ('c_major', 'c_minor', 's_major', 's_minor', 'pick', 'minor_cov', 'minor_smooth'):
                    if k in r:
                        extra += f" {k}={r[k]}"
                print(f"  {r['name']:>9}: n_out={r['n_out']} n_minor={r['n_minor']}"
                      f"{(' minor_cov=' + str(r['minor_cov'])) if 'minor_cov' in r else ''} "
                      f"picked_smooth={r['picked_smooth']}{extra}")
