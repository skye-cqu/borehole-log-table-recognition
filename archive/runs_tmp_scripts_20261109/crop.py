# -*- coding: utf-8 -*-
"""任意小窗放大对比：左原图 / 右叠层界，2 倍放大，看一条线到底贴不贴真线。

win.py 出的是全表宽的横条，看"某条线在某一格里跳没跳行"要更近的距离，就这个。
用法: python runs/tmp/crop.py <out名> <code> <x0> <x1> <y0> <y1> [json目录]
产物: runs/tmp/<out名>.png
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import row_y                              # noqa: E402


def main(name, code, x0, x1, y0, y1, src=paths.RUNS_DIR / "table_reconstruct"):
    stem = f"钻孔柱状图{code}"
    x0, x1, y0, y1 = map(int, (x0, x1, y0, y1))
    rd = json.loads((Path(src) / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    cut = lambda a: a[y0:y1, x0:x1]                                 # noqa: E731
    raw = cv2.cvtColor(cut(gray), cv2.COLOR_GRAY2BGR)
    ovl = raw.copy()
    for r in rd["rows"]:
        pts = np.array([[x - x0, row_y(r, x) - y0] for x in
                        np.linspace(max(r["x"][0], x0), min(r["x"][1], x1), 400)], np.int32)
        if pts[-1, 0] > pts[0, 0]:
            cv2.polylines(ovl, [pts.reshape(-1, 1, 2)], False, (0, 0, 255), 2, cv2.LINE_AA)
    z = 2
    out = ROOT / "runs" / "tmp" / f"{name}.png"
    cv2.imwrite(str(out), np.hstack([np.kron(raw, np.ones((z, z, 1), np.uint8)),
                                     np.full(((y1 - y0) * z, 8, 3), 128, np.uint8),
                                     np.kron(ovl, np.ones((z, z, 1), np.uint8))]),
                [cv2.IMWRITE_PNG_COMPRESSION, 3])
    print(f"{out} 层界{len(rd['rows'])}条 x={x0}-{x1} y={y0}-{y1} 左原图右叠线{z}倍")


if __name__ == "__main__":
    main(*sys.argv[1:7], sys.argv[7] if len(sys.argv) > 7 else
         str(paths.RUNS_DIR / "table_reconstruct"))
