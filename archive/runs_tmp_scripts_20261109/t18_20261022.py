
# -*- coding: utf-8 -*-
"""分隔线"换线"检测 v2: 只用长竖线(1x200 开运算, 文字笔画无法存活)做身份追踪。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

D = paths.RUNS_DIR / 'table_reconstruct'
JUMP = 12.0
STABLE = 5
KERN = 200


def centers(mask, y, half, thr=0.5):
    r0 = max(0, y - half); r1 = min(mask.shape[0], y + half + 1)
    if r1 <= r0:
        return []
    frac = mask[r0:r1, :].mean(axis=0)
    idxs = np.flatnonzero(frac > thr)
    if idxs.size == 0:
        return []
    grp = []
    for c0 in idxs:
        if grp and c0 - grp[-1][-1] <= 4:
            grp[-1].append(c0)
        else:
            grp.append([c0])
    return [float(np.mean(g)) for g in grp]


def analyze(code, step=10):
    stem = '钻孔柱状图' + code
    hm = json.load(open(D / (stem + '_表头映射.json'), encoding='utf-8'))
    sp = hm['sep_pts']
    gray = cv2.imread(str(paths.RAW_DIR / (stem + '.JPG')), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8)
    vshort = cv2.morphologyEx(bw * 255, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))) > 0
    vlong = cv2.morphologyEx(bw * 255, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (1, KERN))) > 0
    del bw, gray
    polys = []
    for s in sp:
        ys = np.asarray(s['ys'], float); xs = np.asarray(s['xs'], float)
        o = np.argsort(ys, kind='stable')
        polys.append((ys[o], xs[o]))
    ytop = int(min(p[0][0] for p in polys)); ybot = int(max(p[0][-1] for p in polys))
    ysmp = list(range(ytop + 30, ybot - 30, step))
    half = KERN // 2
    near = [[None] * len(ysmp) for _ in polys]
    px = [[None] * len(ysmp) for _ in polys]
    nshort = []; nlong = []
    for k, y in enumerate(ysmp):
        cs_long = centers(vlong, y, half)
        cs_short = centers(vshort, y, 20)
        nlong.append(len(cs_long)); nshort.append(len(cs_short))
        if not cs_long:
            continue
        arr = np.asarray(cs_long)
        for j, (py, pxx) in enumerate(polys):
            if not (py[0] <= y <= py[-1]):
                continue
            xq = float(np.interp(y, py, pxx))
            px[j][k] = xq
            near[j][k] = float(arr[np.argmin(np.abs(arr - xq))])
    res_rows = []
    for j in range(len(polys)):
        res = [abs(near[j][k] - px[j][k]) for k in range(len(ysmp))
               if near[j][k] is not None and px[j][k] is not None]
        on = sum(1 for r in res if r <= 3.0)
        sw = []
        k = 0
        while k < len(ysmp):
            if near[j][k] is None:
                k += 1; continue
            k2 = k
            while k2 + 1 < len(ysmp) and near[j][k2+1] is not None and abs(near[j][k2+1]-near[j][k2]) <= JUMP:
                k2 += 1
            if k2 + 1 < len(ysmp) and near[j][k2+1] is not None and abs(near[j][k2+1]-near[j][k2]) > JUMP:
                k3 = k2 + 1
                while k3 + 1 < len(ysmp) and near[j][k3+1] is not None and abs(near[j][k3+1]-near[j][k3]) <= JUMP:
                    k3 += 1
                if (k3 - k2) >= STABLE:
                    sw.append((ysmp[k2], ysmp[k2+1], near[j][k2], near[j][k2+1], near[j][k2+1]-near[j][k2]))
                    k = k2 + 1
                    continue
            k = k2 + 1
        res_rows.append((j, sp[j].get('kind'), sp[j].get('side'),
                         float(np.median(res)) if res else float('nan'),
                         on, len(res), sw))
    return res_rows, ysmp, float(np.median(nshort)), float(np.median(nlong))


if __name__ == '__main__':
    codes = sys.argv[1:] or ['1019', '1023', '1031', '1033', '1042']
    for code in codes:
        out, ysmp, ms, ml = analyze(code)
        print('===== {}  采样{}点  每行墨线数 中位: 短核{} / 长核{}'.format(code, len(ysmp), ms, ml))
        for j, kind, side, med, on, nr, sw in out:
            print('  sep#%-2d %-6s %-5s |残差|中位%5.1f  贴线率 %5.1f%% (%d/%d)%s' % (
                j, kind, side, med, 100.0*on/max(nr,1), on, nr, '  <<< 换线' if sw else ''))
            for y0, y1, a, b, d in sw:
                print('        y=%d -> %d : 墨迹 %.1f -> %.1f (%+.1f px)' % (y0, y1, a, b, d))
