
# -*- coding: utf-8 -*-
"""终判: 异常段内, 右线偏离处是否真实存在"另一条平行竖墨"(= 画到了旁边那条线)。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

D = paths.RUNS_DIR / 'table_reconstruct'
cases = [
    ('1019', 3, 8860, 14330),
    ('1023', 8, 8860, 11040),
    ('1031', 7, 9880, 13440),
    ('1042', 8, 10790, 16690),
    ('1033', 6, 10030, 18250),
]
for code, ridx, y0, y1 in cases:
    stem = '钻孔柱状图' + code
    cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
    seg = {s['id']: np.asarray(s['points'], float)
           for s in cj['lines']
           if s.get('direction') == 'vertical' and s.get('label') == 'high'}
    gray = cv2.imread(str(paths.RAW_DIR / (stem + '.JPG')), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8)
    vv = cv2.morphologyEx(bw * 255, cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))) > 0
    cols = [c for c in cs['columns'] if c.get('index') == ridx]
    if not cols:
        print(code, '列', ridx, '不存在, 跳过')
        continue
    c = cols[0]
    fr = []
    for i in (c.get('segment_ids') or []):
        if i not in seg:
            continue
        p = seg[i]
        fr.append((float(np.median(p[:, 1])), float(np.median(p[:, 0]))))
    fr.sort()
    fy = np.array([a for a, _ in fr]); fx = np.array([b for _, b in fr])
    offs = []
    ys = list(range(y0 + 100, y1 - 100, 60))
    for y in ys:
        if fy.size == 0 or not (fy.min() <= y <= fy.max()):
            continue
        xr = float(np.interp(y, fy, fx))
        row = vv[max(0, y - 12):y + 13, :]
        col = row.mean(axis=0)
        idxs = np.flatnonzero(col > 0.55)
        grp = []
        for c0 in idxs:
            if grp and c0 - grp[-1][-1] <= 4:
                grp[-1].append(c0)
            else:
                grp.append([c0])
        inks = sorted(float(np.mean(g)) for g in grp)
        cand = [u for u in inks if 25 < (u - xr) < 70]
        if cand:
            offs.append(min(cand, key=lambda u: u - xr))
    if offs:
        med = float(np.median(offs))
        print('{} 列{} 异常段: 右线右侧另有竖墨, 中位距离 {:+.1f}px; 采样 {}/{} 点有平行线'.format(
            code, ridx, med, len(offs), len(ys)))
    else:
        print('{} 列{} 异常段: 右侧未找到平行竖墨 (不是换线)'.format(code, ridx))
