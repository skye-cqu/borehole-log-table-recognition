# -*- coding: utf-8 -*-
"""角点裁片:框边在左上/右上角那一截"甩出去又甩回来"到底是什么形态(原图 1:1 vs 我们的线)。

用法: python runs/tmp/crop_corner.py 1015 [1042 ...]   → runs/tmp/corner_<图号>.png
左边=原图 1:1,右边=同一片上画我们的左右框边(红)、6d 的上下框(蓝)、6e 角点(绿十字)。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import col_segments as cs                            # noqa: E402

R = paths.RUNS_DIR / 'table_reconstruct'
BOX = 700            # 裁片边长(px)


def main():
    for code in sys.argv[1:] or ['1015']:
        stem = f'钻孔柱状图{code}'
        raw = cv2.imread(str(paths.RAW_DIR / f'{stem}.JPG'))
        book = cs.line_parts(stem)
        tj = R / f'{stem}_上下框.json'
        tf = json.load(open(tj, encoding='utf-8')) if tj.exists() else {}
        cor = json.load(open(R / f'{stem}_闭合外框.json', encoding='utf-8'))['corners']
        # 窗口放在表顶偏左:那里同时有左上角、顶框、和左边顶部那一截
        L = next((l for l in book['lines'] if l['kind'] == 'edge' and l['side'] == 'left'), None)
        pts = np.vstack([np.asarray(p, float) for p, _ in L['parts']]) if L and L['parts'] else None
        top = np.asarray(tf.get('top', {}).get('groups', [{'pts': []}])[0]['pts'], float) \
            if tf and tf.get('top', {}).get('groups') else None
        ay = int(min(pts[:, 1].min(), cor['TL'][1]) if pts is not None else cor['TL'][1])
        q = pts[pts[:, 1] <= ay + 300] if pts is not None else np.zeros((0, 2))
        ax = int(q[:, 0].min() if len(q) else cor['TL'][0]) - 40
        y0, y1 = max(0, ay - 80), min(raw.shape[0], ay + BOX)
        x0, x1 = max(0, ax), min(raw.shape[1], ax + BOX)
        a = raw[y0:y1, x0:x1].copy()
        b = a.copy()
        for rec in book['lines']:
            if rec['kind'] != 'edge':
                continue
            col = (0, 0, 255) if rec['side'] == 'left' else (0, 128, 255)
            for p, _ in rec['parts']:
                q = np.asarray(p, float) - [x0, y0]
                cv2.polylines(b, [q[:, :2].astype(np.int32).reshape(-1, 1, 2)], False, col, 2)
        for kind, col in (('top', (255, 0, 0)), ('bottom', (255, 0, 0))):
            for g in tf.get(kind, {}).get('groups', []):
                q = np.asarray(g['pts'], float) - [x0, y0]
                cv2.polylines(b, [q.reshape(-1, 1, 2).astype(np.int32)], False, col, 2)
        for k, v in cor.items():
            if v and x0 <= v[0] < x1 and y0 <= v[1] < y1:
                cv2.drawMarker(b, (int(v[0] - x0), int(v[1] - y0)), (0, 255, 0),
                               cv2.MARKER_TILTED_CROSS, 26, 3)
        cv2.putText(b, 'red=our left edge  orange=right  blue=6d top/bottom  green x=6e corner',
                    (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        out = np.hstack([a, np.full((a.shape[0], 6, 3), 255, np.uint8), b])
        fp = ROOT / 'runs' / 'tmp' / f'corner_{code}.png'
        cv2.imwrite(str(fp), out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        print(f'{fp}  角点窗口 x{x0}~{x1} y{y0}~{y1}')


if __name__ == '__main__':
    main()
