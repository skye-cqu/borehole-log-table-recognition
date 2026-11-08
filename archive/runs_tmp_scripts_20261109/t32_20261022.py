
# -*- coding: utf-8 -*-
"""混线列证据图: 1比1 原图局部 + 主轨(绿) + 混入轨(红) + 实际画线(蓝)。"""
import sys, json, os
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

TOL = 30.0
D = paths.RUNS_DIR / 'table_reconstruct'
OUT = paths.RUNS_DIR / 'tmp' / 'mixline_20261022'
os.makedirs(str(OUT), exist_ok=True)
codes = ['1019', '1023', '1024', '1030', '1031', '1033', '1035', '1042']
GREEN = (0, 200, 0); RED = (0, 0, 255); BLUE = (255, 120, 0); YEL = (0, 220, 255)
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
    seps = []
    for j, s in enumerate(hm['sep_pts']):
        ys = np.asarray(s['ys'], float); xs = np.asarray(s['xs'], float)
        o = np.argsort(ys, kind='stable')
        seps.append((j, ys[o], xs[o]))
    gray = cv2.imread(str(paths.RAW_DIR / (stem + '.JPG')), cv2.IMREAD_GRAYSCALE)
    H, W = gray.shape
    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    coltr = []
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
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
            info.append({'n': len(g), 'x': float(np.median([q[0] for q in g])),
                         'y0': int(min(q[1] for q in g)), 'y1': int(max(q[2] for q in g)),
                         'pts': [(q[0], 0.5*(q[1]+q[2])) for q in g]})
        info.sort(key=lambda d: -d['n'])
        coltr.append({'index': c['index'], 'src': c.get('src'), 'tracks': info})
    for col in coltr:
        if len(col['tracks']) < 2:
            continue
        main = col['tracks'][0]
        # 找该列对应的 sep 折线(与主轨最贴合者)
        bestsep = None; bestd = None
        for (j, py, px) in seps:
            ds = []
            for (fx, fy) in main['pts']:
                if py[0] <= fy <= py[-1]:
                    ds.append(abs(float(np.interp(fy, py, px)) - fx))
            if not ds:
                continue
            md = float(np.median(ds))
            if bestd is None or md < bestd:
                bestd = md; bestsep = (j, py, px)
        for si, sec in enumerate(col['tracks'][1:], start=1):
            if sec['n'] < 2:
                continue
            # 画: 主轨绿, 混入红, 实际画线蓝
            for (fx, fy) in main['pts']:
                if 0 <= int(fy) < H and 0 <= int(fx) < W:
                    cv2.circle(bgr, (int(fx), int(fy)), 4, GREEN, -1)
            for (fx, fy) in sec['pts']:
                if 0 <= int(fy) < H and 0 <= int(fx) < W:
                    cv2.circle(bgr, (int(fx), int(fy)), 4, RED, -1)
            if bestsep:
                j, py, px = bestsep
                pts = np.stack([px, py], axis=1).astype(np.int32)
                cv2.polylines(bgr, [pts], False, BLUE, 2)
            # 切 1比1 局部
            ys_all = [p[1] for p in main['pts']] + [p[1] for p in sec['pts']]
            xs_all = [p[0] for p in main['pts']] + [p[0] for p in sec['pts']]
            x0 = int(max(0, min(xs_all)-70)); x1 = int(min(W, max(xs_all)+70))
            y0 = int(max(0, min(ys_all)-50)); y1 = int(min(H, max(ys_all)+50))
            MAXH = 2200
            nslice = max(1, (y1-y0)//MAXH)
            for k in range(nslice):
                ya = y0 + k*MAXH; yb = min(y1, ya+MAXH)
                crop = bgr[ya:yb, x0:x1].copy()
                sc = max(1, (crop.shape[0])//900)
                if sc > 1:
                    crop = cv2.resize(crop, None, fx=1.0/sc, fy=1.0/sc)
                    ys_off = ya
                else:
                    ys_off = ya
                fn = os.path.join(str(OUT), '%s_列%d轨%d_局部%d_%dy%d.png' % (code, col['index'], si, k, ya, yb))
                cv2.imwrite(fn, crop)
                made.append(fn)
                print('写出', os.path.basename(fn))
json.dump(made, open('runs/tmp/t32_evidence_files.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
