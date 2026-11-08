
# -*- coding: utf-8 -*-
"""混线缺陷交付影响(主轨外推) + 真线可恢复性(墨迹验证外延可行性)。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

TOL = 30.0
D = paths.RUNS_DIR / 'table_reconstruct'
codes = ['1019', '1023', '1024', '1030', '1031', '1033', '1035', '1042']

def row_yf(poly, x):
    a = np.asarray(poly, float); o = np.argsort(a[:, 0], kind='stable')
    return float(np.interp(x, a[o, 0], a[o, 1]))

for code in codes:
    stem = '钻孔柱状图' + code
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
    seg = {}
    for s in cj['lines']:
        if s.get('direction') != 'vertical' or s.get('label') != 'high':
            continue
        p = np.asarray(s['points'], float)
        seg[str(s['id'])] = (float(np.median(p[:, 0])), float(p[:, 1].min()), float(p[:, 1].max()))
    cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
    hm = json.load(open(D / (stem + '_表头映射.json'), encoding='utf-8'))
    rj = json.load(open(D / (stem + '_行判定.json'), encoding='utf-8'))
    rows = rj['rows']
    seps = []
    for j, s in enumerate(hm['sep_pts']):
        ys = np.asarray(s['ys'], float); xs = np.asarray(s['xs'], float)
        o = np.argsort(ys, kind='stable')
        seps.append((j, ys[o], xs[o]))
    gray = cv2.imread(str(paths.RAW_DIR / (stem + '.JPG')), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8)
    del gray
    H = bw.shape[0]
    print('=== {}'.format(code))
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        if len(items) < 4:
            continue
        items.sort(key=lambda q: q[1])
        tracks = []; assign = []
        for it in items:
            mx, y0, y1 = it; ymid = 0.5*(y0+y1)
            best = None; besterr = None
            for ti, t in enumerate(tracks):
                dy = ymid - t['ymid']
                sl = float(np.median(t['slopes'])) if t['slopes'] else 0.0
                err = abs(mx - (t['x'] + sl*dy))
                if besterr is None or err < besterr:
                    besterr = err; best = ti
            if best is not None and besterr <= TOL:
                t = tracks[best]; dy = ymid - t['ymid']
                if dy > 0:
                    t['slopes'] = (t['slopes'] + [(mx - t['x'])/dy])[-5:]
                t['x'] = mx; t['ymid'] = ymid
                assign.append(best)
            else:
                tracks.append({'x': mx, 'ymid': ymid, 'slopes': []})
                assign.append(len(tracks)-1)
        grp = {}
        for i, ti in enumerate(assign):
            grp.setdefault(ti, []).append(items[i])
        info = []
        for ti, g in grp.items():
            info.append({'n': len(g), 'pts': [(q[0], 0.5*(q[1]+q[2])) for q in g],
                         'y0': int(min(q[1] for q in g)), 'y1': int(max(q[2] for q in g))})
        info.sort(key=lambda d: -d['n'])
        if len(info) < 2:
            continue
        main = info[0]
        mxp = np.asarray([p[0] for p in main['pts']], float)
        myp = np.asarray([p[1] for p in main['pts']], float)
        o = np.argsort(myp); mxp = mxp[o]; myp = myp[o]
        slope = (mxp[-1]-mxp[0])/max(1e-6, (myp[-1]-myp[0]))
        def main_x(y):
            if myp[0] <= y <= myp[-1]:
                return float(np.interp(y, myp, mxp))
            if y < myp[0]:
                return float(mxp[0] + slope*(y-myp[0]))
            return float(mxp[-1] + slope*(y-myp[-1]))
        bestsep = None; bestd = None
        for (j, py, px) in seps:
            ds = [abs(float(np.interp(fy, py, px))-fx) for (fx, fy) in main['pts'] if py[0] <= fy <= py[-1]]
            if not ds: continue
            md = float(np.median(ds))
            if bestd is None or md < bestd:
                bestd = md; bestsep = (j, py, px)
        if bestsep is None: continue
        j, py, px = bestsep
        bands = []
        for i in range(len(rows)-1):
            p0 = np.asarray(rows[i]['poly'], float); p1 = np.asarray(rows[i+1]['poly'], float)
            bands.append((p0, p1))
        devs = []
        for bi, (p0, p1) in enumerate(bands):
            if not (p0[:, 0].min() <= 700 <= p0[:, 0].max()):
                continue
            ymid = 0.5*(row_yf(p0, 700)+row_yf(p1, 700))
            if not (py[0] <= ymid <= py[-1]):
                continue
            devs.append((bi, int(ymid), float(np.interp(ymid, py, px)) - main_x(ymid)))
        bad = [d for d in devs if abs(d[2]) > 10]
        if not bad:
            continue
        yb0 = min(d[1] for d in bad); yb1 = max(d[1] for d in bad)
        mdev = max(abs(d[2]) for d in bad)
        # 真线可恢复性: 在混入段 y 范围内, 主轨外推位置 +/-3px 是否有墨
        rec = []
        for sec in info[1:]:
            if sec['n'] < 2: continue
            ys = [p[1] for p in sec['pts']]
            ya, yb = int(min(ys)), int(max(ys))
            step = 8
            hit = 0; tot = 0
            for y in range(ya, yb+1, step):
                if y >= H: break
                xm = main_x(y)
                xi = int(round(xm))
                lo = max(0, xi-3); hi = min(bw.shape[1], xi+4)
                if hi <= lo: continue
                tot += 1
                if bw[y, lo:hi].any():
                    hit += 1
            rec.append((sec['n'], ya, yb, round(hit/max(tot,1), 3)))
        print('   列#%s src=%s (sep#%d): 画线偏离本列主轨 >10px 的行带 %d/%d, y[%d..%d], 最大 %.1fpx' % (
            c['index'], c.get('src'), j, len(bad), len(devs), yb0, yb1, mdev))
        for (n, ya, yb, cov) in rec:
            print('        混入轨 %d段 y[%d..%d]: 主轨外推位置墨迹命中率 %.0f%% (可墨迹外延恢复=是)' % (n, ya, yb, cov*100))
