
# -*- coding: utf-8 -*-
"""分隔线"换线"终判 v3 —— 行带内可跨越的竖规则 + 全表覆盖长度排序。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

SPAN_MIN = 0.80
MARGIN = 4
SEARCH = 170


def row_yf(poly, x):
    a = np.asarray(poly, float)
    o = np.argsort(a[:, 0], kind='stable')
    xs = a[o, 0]; ys = a[o, 1]
    return float(np.interp(x, xs, ys))


def analyze(code):
    stem = '钻孔柱状图' + code
    Dd = paths.RUNS_DIR / 'table_reconstruct'
    hm = json.load(open(Dd / (stem + '_表头映射.json'), encoding='utf-8'))
    rj = json.load(open(Dd / (stem + '_行判定.json'), encoding='utf-8'))
    sp = hm['sep_pts']
    rows = rj['rows']
    gray = cv2.imread(str(paths.RAW_DIR / (stem + '.JPG')), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8)
    del gray
    polys = []
    for s in sp:
        ys = np.asarray(s['ys'], float); xs = np.asarray(s['xs'], float)
        o = np.argsort(ys, kind='stable')
        polys.append((ys[o], xs[o]))
    ytop = int(min(min(p[1] for p in r['poly']) for r in rows))
    ybot = int(max(max(p[1] for p in r['poly']) for r in rows))
    H = bw.shape[0]
    ytop = max(0, ytop); ybot = min(H, ybot)
    vprof = bw[ytop:ybot, :].sum(axis=0).astype(float) / float(max(1, ybot - ytop))
    bands = [(np.asarray(rows[i]['poly'], float), np.asarray(rows[i+1]['poly'], float))
             for i in range(len(rows) - 1)]
    out = []
    for j, (py, px) in enumerate(polys):
        rec = []
        for bi, (p0, p1) in enumerate(bands):
            x = float(px[0])
            for _ in range(3):
                if not (p0[:, 0].min() <= x <= p0[:, 0].max()):
                    break
                y_lo = row_yf(p0, x); y_hi = row_yf(p1, x)
                if not (y_hi - y_lo > 12):
                    break
                mid = 0.5 * (y_lo + y_hi)
                if not (py[0] <= mid <= py[-1]):
                    break
                x = float(np.interp(mid, py, px))
            if not (p0[:, 0].min() <= x <= p0[:, 0].max()):
                continue
            y_lo = row_yf(p0, x); y_hi = row_yf(p1, x)
            if not (y_hi - y_lo > 12):
                continue
            a = int(max(0, y_lo + MARGIN)); b = int(min(H, y_hi - MARGIN))
            if b - a < 6:
                continue
            x0 = int(max(0, x - SEARCH)); x1 = int(min(bw.shape[1], x + SEARCH))
            if x1 - x0 < 8:
                continue
            prof = bw[a:b, x0:x1].mean(axis=0)
            idxs = np.flatnonzero(prof > SPAN_MIN)
            if idxs.size == 0:
                rec.append((bi, int(y_lo), int(y_hi), x, None, 0.0, 0.0, None))
                continue
            grp = []
            for c0 in idxs:
                if grp and c0 - grp[-1][-1] <= 4:
                    grp[-1].append(c0)
                else:
                    grp.append([c0])
            rules = [(x0 + float(np.mean(g)), float(vprof[x0 + int(np.mean(g))])) for g in grp]
            near = min(rules, key=lambda r: abs(r[0] - x))
            best = max(rules, key=lambda r: r[1])
            rec.append((bi, int(y_lo), int(y_hi), x, near[0], near[1], best[1], best[0]))
        out.append((j, sp[j].get('kind'), rec))
    return out, len(bands)


if __name__ == '__main__':
    codes = sys.argv[1:] or ['1023', '1019', '1031', '1033', '1042']
    for code in codes:
        out, nb = analyze(code)
        print('===== {}  行带 {} 个'.format(code, nb))
        for j, kind, rec in out:
            bad = []
            for (bi, ylo, yhi, x, nx, ncov, bcov, bx) in rec:
                if nx is None:
                    bad.append((bi, ylo, yhi, x, None, 0.0, 0.0, None, '带内无跨带竖规则'))
                elif abs(nx - x) > 3.0:
                    bad.append((bi, ylo, yhi, x, nx, ncov, bcov, bx, '线上无墨(偏 %+.1fpx)' % (nx - x)))
                elif ncov < 0.85 * bcov and bcov - ncov > 0.25:
                    bad.append((bi, ylo, yhi, x, nx, ncov, bcov, bx,
                                '换短命线(本线覆盖%.0f%% < 同带长线%.0f%%, 相距%.0fpx)' % (100*ncov, 100*bcov, bx-nx)))
            if bad:
                print('  sep#%d (%s): %d/%d 行带异常' % (j, kind, len(bad), len(rec)))
                for b in bad[:6]:
                    print('      band%-4d y[%d,%d] 画在x=%.1f 规则x=%s 覆盖%.2f/%.2f 备选x=%s | %s' % (
                        b[0], b[1], b[2], b[3], ('%.1f' % b[4]) if b[4] is not None else 'None',
                        b[5], b[6], ('%.1f' % b[7]) if b[7] is not None else 'None', b[8]))
                if len(bad) > 6:
                    print('      ... 其余 %d 条同类' % (len(bad)-6))
