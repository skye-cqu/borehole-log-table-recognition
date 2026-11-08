# -*- coding: utf-8 -*-
"""左框候选定性片:尺子发现某张图"表高范围内 ≥45% 高度上有真竖墨"的簇落在我们左边的**西侧**几十到上百 px,
本脚本把那片原图按 1:1 裁出来(左=纯原图,右=同片上画我们的左边+那个墨簇的 x),交肉眼判"那根墨是不是表的外框"。

用法: python runs/tmp/crop_left.py 1022 1024 ...      → runs/tmp/left_<图号>.png
窗口 x 从 0 到 我们左边顶部 x+220,y 取表高中段(避开上下框与角点)。
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import col_segments as cs                            # noqa: E402

sys.path.insert(0, str(ROOT / 'runs' / 'tmp'))
from yard_frame import sheet                                        # noqa: E402

BOX_W, BOX_H = 1500, 900


def main():
    for code in sys.argv[1:] or ['1022']:
        stem = f'钻孔柱状图{code}'
        raw = cv2.imread(str(paths.RAW_DIR / f'{stem}.JPG'))
        book = cs.line_parts(stem)
        L = next((l for l in book['lines'] if l['kind'] == 'edge' and l['side'] == 'left'), None)
        r = sheet(stem)
        y0, y1 = r['y']
        cy = int((y0 + y1) / 2)
        lx = float(np.asarray(L['parts'][0][0], float)[0, 0]) if L and L['parts'] else 300.0
        west = [c for c in r['vcl'] if c < lx - 20]
        x0 = max(0, int(min(west) - 60) if west else int(lx) - 260)
        x1 = min(raw.shape[1], x0 + BOX_W)
        yy0, yy1 = max(0, cy - BOX_H // 2), min(raw.shape[0], cy + BOX_H // 2)
        a = raw[yy0:yy1, x0:x1].copy()
        b = a.copy()
        for rec in book['lines']:
            if rec['kind'] != 'edge':
                continue
            col = (0, 0, 255) if rec['side'] == 'left' else (0, 128, 255)
            for p, _ in rec['parts']:
                q = np.asarray(p, float) - [x0, yy0]
                cv2.polylines(b, [q[:, :2].astype(np.int32).reshape(-1, 1, 2)], False, col, 2)
        for c in west:
            cv2.line(b, (c - x0, 0), (c - x0, b.shape[0]), (0, 255, 0), 1)
        cv2.putText(b, f'red=our left edge  green=ink cluster w/ >=45% v-ink  x0={x0} y{yy0}~{yy1}',
                    (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
        out = np.hstack([a, np.full((a.shape[0], 6, 3), 255, np.uint8), b])
        fp = ROOT / 'runs' / 'tmp' / f'left_{code}.png'
        cv2.imwrite(str(fp), out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        print(f'{fp}  我们左边x≈{lx:.0f} 西侧墨簇{west} 窗口 x{x0}~{x1} y{yy0}~{yy1}')
        del raw, a, b, out


if __name__ == '__main__':
    main()
