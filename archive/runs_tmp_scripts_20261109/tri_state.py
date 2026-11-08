# -*- coding: utf-8 -*-
"""真歪行线逐条出三态裁片：原图 / 我们画的线 / 图上真横线墨。

三态同幅同比例，肉眼一比就能定性：是"该处本无横线"(rowspan)、"链跟错了行"、还是"线只是偏几像素"。
横线和字的判据沿用标尺那一套(runs/tmp/yardstick.py 的 masks)：自适应二值 → 40px 横条开运算 → 闭运算接断口。

用法: python runs/tmp/tri_state.py                # 默认量 off_lines_frame.json 里真歪那几条
      python runs/tmp/tri_state.py 1020:10074     # 也可点名 code:y
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
import yardstick as Y                                               # noqa: E402

OFF = next((Path(a) for a in sys.argv[1:] if ":" not in a),
           Path(__file__).resolve().parent / "off_lines_frame.json")
DEV = 6            # ≥6 个采样"有墨却偏" 才算真歪（与 diag_off 同一口径）
PAD = 130          # 裁片上下各留多少 px
TILE = 1200        # 一张多宽


def rows_of(code):
    rd = json.loads((Y.SRC / f"钻孔柱状图{code}_行判定.json").read_text(encoding="utf-8"))
    return rd["rows"]


def panel(gray, ruling, poly, x0, x1, ylo, yhi, draw):
    c = cv2.cvtColor(gray[ylo:yhi, x0:x1], cv2.COLOR_GRAY2BGR)
    if draw & 1:                                   # 我们画的线 = 红
        p = (np.asarray(poly, np.int32) - [x0, ylo]).reshape(-1, 1, 2)
        cv2.polylines(c, [p], False, (0, 0, 255), 2, cv2.LINE_AA)
    if draw & 2:                                   # 图上真横线墨 = 绿
        m = ruling[ylo:yhi, x0:x1] > 0
        c[m] = (0, 200, 0)
    return c


def main():
    targets = [(c, int(y), -1) for c, y in
               (a.split(":") for a in sys.argv[1:] if ":" in a)] or \
              [(r["code"], r["y"], r["dev_o"]) for r in json.load(open(OFF, encoding="utf-8"))
               if r["dev_o"] >= DEV]
    by_sheet = {}
    for code, y, dev in targets:
        by_sheet.setdefault(code, []).append((y, dev))
    for code, ys in sorted(by_sheet.items()):
        stem = f"钻孔柱状图{code}"
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        ruling, _ = Y.masks(stem)
        rows = rows_of(code)
        for y, dev in ys:
            r = min(rows, key=lambda r: abs(r["y_at_mid"] - y))
            pl = np.asarray(r["poly"], float)
            ylo = max(0, int(pl[:, 1].min()) - PAD)
            yhi = min(gray.shape[0], int(pl[:, 1].max()) + PAD)
            for n, x0 in enumerate(range(int(pl[:, 0].min()), int(pl[:, 0].max()), TILE)):
                x1 = min(x0 + TILE, gray.shape[1])
                strip = np.vstack([panel(gray, ruling, r["poly"], x0, x1, ylo, yhi, d)
                                   for d in (0, 1, 2)] +
                                  [np.full((6, x1 - x0, 3), 40, np.uint8)])
                for i, t in enumerate(("原图", "画的线(红)", "真横线墨(绿)")):
                    cv2.putText(strip, t, (8, 24 + i * (yhi - ylo + 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                out = Y.ROOT / "runs/tmp" / f"三态_{code}_{y}_{n}.png"
                cv2.imwrite(str(out), strip)
            print(f"{code} y={y} 真偏{dev}/60 x{int(pl[:, 0].min())}~{int(pl[:, 0].max())} "
                  f"→ runs/tmp/三态_{code}_{y}_*.png")
        del gray, ruling


if __name__ == "__main__":
    main()
