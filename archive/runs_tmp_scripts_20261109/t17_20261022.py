
# -*- coding: utf-8 -*-
"""分隔线"换线"检测: 沿 y 追踪每条 sep_polyline 最近的真实竖墨, 检出身份跳变。

判定口径(与 yard_cols 一致, 最近墨迹而非 argmax):
  - 竖墨: 自适应阈值 -> 形态学竖向开运算(1x40) -> 窗口内占比>0.55
  - 对每个采样 y, 取每条分隔线的 poly_x, 找最近墨迹中心
  - 若最近墨迹在相邻采样点之间跳变 >12px, 且新身份其后连续 >=5 个采样点稳定 -> 记为一次"换线"
"""
import sys, json
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

D = paths.RUNS_DIR / 'table_reconstruct'
JUMP = 12.0
STABLE = 5


def ink_centers(vv, y, half=20, thr=0.55):
    r0 = max(0, y - half); r1 = min(vv.shape[0], y + half + 1)
    if r1 <= r0:
        return []
    frac = vv[r0:r1, :].mean(axis=0)
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
    vv = cv2.morphologyEx(bw * 255, cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))) > 0
    del bw, gray
    polys = []
    for s in sp:
        ys = np.asarray(s['ys'], float); xs = np.asarray(s['xs'], float)
        o = np.argsort(ys, kind='stable')
        polys.append((ys[o], xs[o]))
    ytop = int(min(p[0][0] for p in polys)); ybot = int(max(p[0][-1] for p in polys))
    ysmp = list(range(ytop + 30, ybot - 30, step))
    # 收集每条分隔线在每个采样点的 poly_x / 最近墨迹
    recs = []
    for j, (py, px) in enumerate(polys):
        arr = []
        for y in ysmp:
            if py[0] <= y <= py[-1]:
                xq = float(np.interp(y, py, px))
            else:
                xq = None
            arr.append(xq)
        recs.append(arr)
    near = [[None] * len(ysmp) for _ in polys]
    for k, y in enumerate(ysmp):
        cands = ink_centers(vv, y)
        if not cands:
            continue
        arr = np.asarray(cands)
        for j in range(len(polys)):
            xq = recs[j][k]
            if xq is None:
                continue
            near[j][k] = float(arr[np.argmin(np.abs(arr - xq))])
    out = []
    for j in range(len(polys)):
        # 残差统计
        res = []
        for k, y in enumerate(ysmp):
            if recs[j][k] is None or near[j][k] is None:
                continue
            res.append(abs(near[j][k] - recs[j][k]))
        # 身份跳变
        sw = []
        k = 0
        while k < len(ysmp):
            if near[j][k] is None:
                k += 1; continue
            k2 = k
            while k2 + 1 < len(ysmp) and near[j][k2 + 1] is not None and abs(near[j][k2 + 1] - near[j][k2]) <= JUMP:
                k2 += 1
            runlen = k2 - k + 1
            if runlen >= STABLE and k2 + 1 < len(ysmp) and near[j][k2 + 1] is not None:
                d = near[j][k2 + 1] - near[j][k2]
                if abs(d) > JUMP:
                    # 新身份需继续稳定
                    k3 = k2 + 1
                    while k3 + 1 < len(ysmp) and near[j][k3 + 1] is not None and abs(near[j][k3 + 1] - near[j][k3]) <= JUMP:
                        k3 += 1
                    if k3 - (k2 + 1) + 1 >= STABLE:
                        sw.append((ysmp[k2], ysmp[k2 + 1], round(near[j][k2], 1), round(near[j][k2 + 1], 1), round(d, 1)))
                        k = k2 + 1
                        continue
            k = k2 + 1
        med = float(np.median(res)) if res else float('nan')
        p90 = float(np.percentile(res, 90)) if res else float('nan')
        out.append((j, sp[j].get('kind'), sp[j].get('side'), med, p90, len(res), sw))
    return out, len(ysmp)


if __name__ == '__main__':
    codes = sys.argv[1:] or ['1019', '1023', '1031', '1033', '1042']
    for code in codes:
        out, n = analyze(code)
        print('===== {}  (采样 {} 点)'.format(code, n))
        for j, kind, side, med, p90, nr, sw in out:
            flag = '  <<< 换线' if sw else ''
            print('  sep#%-2d %-6s %-6s |残差| 中位 %5.1f p90 %5.1f (n=%d)%s' % (j, kind, side, med, p90, nr, flag))
            for y0, y1, a, b, d in sw:
                print('        y=%d -> %d : 墨迹 %.1f -> %.1f (%+.1f px)' % (y0, y1, a, b, d))
