
# -*- coding: utf-8 -*-
"""真 1:1 关键裁片: 取每图偏离最大处, 不缩放。绿=主轨段 红=混入段 蓝=实际画线 黄=真线外推位。"""
import sys, json, os
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

TOL = 30.0
D = paths.RUNS_DIR / 'table_reconstruct'
OUT = paths.RUNS_DIR / 'tmp' / 'mixline_20261022'
os.makedirs(str(OUT), exist_ok=True)
codes = ['1019', '1023', '1024', '1030', '1031', '1033', '1035', '1042']
def row_yf(poly, x):
    a = np.asarray(poly, float); o = np.argsort(a[:, 0], kind='stable')
    return float(np.interp(x, a[o, 0], a[o, 1]))
made = []
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
    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    H, W = gray.shape
    best = None
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        if len(items) < 4: continue
        items.sort(key=lambda q: q[1])
        tracks = []; assign = []
        for it in items:
            mx, y0, y1 = it; ymid = 0.5*(y0+y1)
            b = None; be = None
            for ti, t in enumerate(tracks):
                dy = ymid - t['ymid']
                sl = float(np.median(t['slopes'])) if t['slopes'] else 0.0
                e = abs(mx - (t['x']+sl*dy))
                if be is None or e < be: be = e; b = ti
            if b is not None and be <= TOL:
                t = tracks[b]; dy = ymid - t['ymid']
                if dy > 0: t['slopes'] = (t['slopes'] + [(mx-t['x'])/dy])[-5:]
                t['x'] = mx; t['ymid'] = ymid; assign.append(b)
            else:
                tracks.append({'x': mx, 'ymid': ymid, 'slopes': []}); assign.append(len(tracks)-1)
        grp = {}
        for i, ti in enumerate(assign): grp.setdefault(ti, []).append(items[i])
        info = []
        for ti, g in grp.items():
            info.append({'n': len(g), 'pts': [(q[0], 0.5*(q[1]+q[2])) for q in g],
                         'y0': int(min(q[1] for q in g)), 'y1': int(max(q[2] for q in g))})
        info.sort(key=lambda d: -d['n'])
        if len(info) < 2: continue
        main = info[0]
        mxp = np.asarray([p[0] for p in main['pts']], float)
        myp = np.asarray([p[1] for p in main['pts']], float)
        o = np.argsort(myp); mxp = mxp[o]; myp = myp[o]
        slope = (mxp[-1]-mxp[0])/max(1e-6, (myp[-1]-myp[0]))
        def main_x(y):
            if myp[0] <= y <= myp[-1]: return float(np.interp(y, myp, mxp))
            return float(mxp[0]+slope*(y-myp[0]) if y < myp[0] else mxp[-1]+slope*(y-myp[-1]))
        bestsep = None; bestd = None
        for (j, py, px) in seps:
            ds = [abs(float(np.interp(fy, py, px))-fx) for (fx, fy) in main['pts'] if py[0] <= fy <= py[-1]]
            if not ds: continue
            md = float(np.median(ds))
            if bestd is None or md < bestd: bestd = md; bestsep = (j, py, px)
        if bestsep is None: continue
        j, py, px = bestsep
        for bi in range(len(rows)-1):
            p0 = np.asarray(rows[bi]['poly'], float); p1 = np.asarray(rows[bi+1]['poly'], float)
            if not (p0[:, 0].min() <= 700 <= p0[:, 0].max()): continue
            ym = 0.5*(row_yf(p0, 700)+row_yf(p1, 700))
            if not (py[0] <= ym <= py[-1]): continue
            d = float(np.interp(ym, py, px)) - main_x(ym)
            if abs(d) > 10 and (best is None or abs(d) > abs(best[4])):
                best = (c['index'], c.get('src'), j, int(ym), d, main, info[1:], mxp, myp, slope, py, px)
    if best is None:
        print('{}: 无 >10px 偏离'.format(code)); continue
    ci, src, j, ym, d, main, secs, mxp, myp, slope, py, px = best
    def main_x(y):
        if myp[0] <= y <= myp[-1]: return float(np.interp(y, myp, mxp))
        return float(mxp[0]+slope*(y-myp[0]) if y < myp[0] else mxp[-1]+slope*(y-myp[-1]))
    vis = bgr.copy()
    for (fx, fy) in main['pts']:
        if 0 <= int(fy) < H and 0 <= int(fx) < W: cv2.circle(vis, (int(fx), int(fy)), 5, (0,200,0), -1)
    for sec in secs:
        for (fx, fy) in sec['pts']:
            if 0 <= int(fy) < H and 0 <= int(fx) < W: cv2.circle(vis, (int(fx), int(fy)), 5, (0,0,255), -1)
    pts = np.stack([px, py], axis=1).astype(np.int32)
    cv2.polylines(vis, [pts], False, (255,120,0), 2)
    # 真线外推位(黄)
    for y in range(max(0, ym-400), min(H, ym+400), 6):
        xm = main_x(y)
        if 0 <= int(xm) < W: cv2.circle(vis, (int(xm), y), 2, (0,220,255), -1)
    cx = int(np.interp(ym, py, px))
    x0 = max(0, min(int(mxp[0]), int(mxp[-1]), cx) - 150); x1 = min(W, max(int(mxp[0]), int(mxp[-1]), cx) + 150)
    y0 = max(0, ym-600); y1 = min(H, ym+600)
    crop = vis[y0:y1, x0:x1]
    fn = os.path.join(str(OUT), '%s_关键1比1_y%d.png' % (code, ym))
    cv2.imwrite(fn, crop)
    made.append(fn)
    print('%s 列#%s src=%s sep#%d  y=%d 偏离%+.1fpx -> %s (%dx%d)' % (code, ci, src, j, ym, d, os.path.basename(fn), crop.shape[1], crop.shape[0]))
json.dump(made, open('runs/tmp/t36_key1to1.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
