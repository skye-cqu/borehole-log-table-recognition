
# -*- coding: utf-8 -*-
"""横线断口定位格线: 表格横线在格界处断开, 断口中点即格界。
先在 1023(已知真解)上验证, 再用于其它图。
"""
import sys, json
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

def gap_centers(bw, y, half=4, minw=6, maxgap=90):
    a = max(0, y-half); b = min(bw.shape[0], y+half+1)
    if b <= a: return []
    prof = 1.0 - bw[a:b, :].mean(axis=0)     # 1=全白
    gaps = []
    i = 0
    W = len(prof)
    while i < W:
        if prof[i] > 0.35:
            j = i
            while j < W and prof[j] > 0.35:
                j += 1
            w = j - i
            if minw <= w <= maxgap:
                gaps.append((i, j-1, (i+j-1)/2.0, w))
            i = j
        else:
            i += 1
    return gaps

code = sys.argv[1] if len(sys.argv) > 1 else '1023'
stem = '钻孔柱状图' + code
gray = cv2.imread(str(paths.RAW_DIR / (stem + '.JPG')), cv2.IMREAD_GRAYSCALE)
bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                            cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8)
hm = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / (stem + '_表头映射.json'), encoding='utf-8'))
rj = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / (stem + '_行判定.json'), encoding='utf-8'))
print('=== {}  横线断口 vs 画线'.format(code))
for idx in [0, 5, 20, 40, 60, 80, 100]:
    if idx >= len(rj['rows'])-1: break
    p = rj['rows'][idx]['poly']
    ys = [q[1] for q in p]
    y = int(np.median(ys))
    g = gap_centers(bw, y)
    # 该 y 处画线 x
    sx = []
    for s in hm['sep_pts']:
        yy = np.asarray(s['ys'], float); xx = np.asarray(s['xs'], float)
        o = np.argsort(yy, kind='stable')
        if yy[o][0] <= y <= yy[o][-1]:
            sx.append((float(np.interp(y, yy[o], xx[o])), s.get('index'), s.get('kind')))
    sx.sort()
    print('  行%d y=%d:' % (idx, y))
    print('     断口(格界候选): ' + ', '.join('%.1f(w%d)' % (g_[2], g_[3]) for g_ in g[:20]))
    print('     画线x        : ' + ', '.join('%.1f#%s%s' % (a, b, '(edge)' if c=='edge' else '') for a,b,c in sx))
