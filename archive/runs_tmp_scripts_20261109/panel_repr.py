# -*- coding: utf-8 -*-
"""表征对比片：同一块区域 = 原图 | 一条水平线 | 折线（成员链原点拼出来的）。

自动选窗：窗内"折线偏离水平线最多"的那一段（表最斜、旧表征误差最扎眼的地方）。
用法: python runs/tmp/panel_repr.py 1019 1035
产物 runs/tmp/表征对比_<code>.png
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

WIN = 700
M = 40


def load(code):
    p = paths.RUNS_DIR / "table_reconstruct" / f"钻孔柱状图{code}_行判定.json"
    return json.loads(p.read_text(encoding="utf-8"))


def dev(r, xs):
    """这条线在 xs 上折线高度与水平线高度的最大偏离。"""
    return max(abs(row_y(r, x) - r["y_at_mid"]) for x in xs)


for code in sys.argv[1:] or ["1019"]:
    rd = load(code)
    stem = f"钻孔柱状图{code}"
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    x0, x1 = int(rd["table_x"][0]), int(rd["table_x"][1])
    lo, hi = int(gray.shape[0] * 0.18), int(gray.shape[0] * 0.92)
    best = (0, lo)
    for y in range(lo, hi - WIN, 50):                       # 滑窗挑偏离最大处
        xs = np.linspace(x0 + 20, x1 - 20, 40)
        s = sum(dev(r, xs) for r in rd["rows"] if y <= r["y_at_mid"] < y + WIN)
        if s > best[0]:
            best = (s, y)
    y0, y1 = int(best[1]), int(best[1] + WIN)
    xa = int(x0 + (x1 - x0) * 0.42)          # 只取表宽中段 700px：原尺寸看，不缩糊
    xb = min(xa + WIN, x1)
    base = cv2.cvtColor(gray[y0 - M:y1 + M, xa:xb], cv2.COLOR_GRAY2BGR)
    panels = [base.copy()]
    for how in ("flat", "poly"):
        im = base.copy()
        for r in rd["rows"]:
            if how == "flat":
                cv2.line(im, (int(r["x"][0] - xa), int(r["y_at_mid"] - y0 + M)),
                         (int(r["x"][1] - xa), int(r["y_at_mid"] - y0 + M)), (0, 0, 255), 2,
                         cv2.LINE_AA)
            else:
                pts = np.asarray([[px - xa, py - y0 + M] for px, py in r["poly"]], np.int32)
                cv2.polylines(im, [pts.reshape(-1, 1, 2)], False, (0, 0, 255), 2, cv2.LINE_AA)
        panels.append(im)
    gap = np.full((panels[0].shape[0], 10, 3), 40, np.uint8)
    img = np.hstack([panels[0], gap, panels[1], gap, panels[2]])
    top = np.full((46, img.shape[1], 3), 255, np.uint8)
    img = np.vstack([top, img])
    for i, t in enumerate(("原图", "旧表征:一条水平线", "新表征:成员链折线")):
        cv2.putText(img, t, (i * (panels[0].shape[1] + 10) + 6, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    out = paths.RUNS_DIR / "tmp" / f"表征对比_{code}.png"
    cv2.imwrite(str(out), img, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    print(f"{code}: 窗口 x={xa}-{xb} y={y0}-{y1} 窗内折线vs水平线累计偏离 "
          f"{best[0]:.0f}px → {out.name}")
