# -*- coding: utf-8 -*-
"""把"这条行线到底歪不歪"画成能直接看的片：灰底=原图，绿=图上真横线墨，淡蓝=字，红=画的线。

红压绿=线在真横线上；红绿错开=画偏了；红线附近没绿=原图这一段本就断线/没横线。
按 1200px 宽分片、不缩图，笔画看得清。

用法: python runs/tmp/mark_off.py 1020 10073 10240        # 一个 y 出若干片
      python runs/tmp/mark_off.py --list runs/tmp/worst.txt   # 每行 "张 y"
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
import yardstick as Y                                              # noqa: E402
from src.core import paths                                          # noqa: E402

M = 90            # 线上下各留多少像素
TILE = 1200       # 每片宽
_cache = {}


def sheet(code):
    if code not in _cache:
        stem = f"钻孔柱状图{code}"
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        ruling, glyph = Y.masks(stem)
        rd = json.loads((Y.SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
        _cache[code] = (gray, ruling, glyph, rd)
    return _cache[code]


def worst_run(code, y_mid):
    """这条线上"有墨却画偏"最长的连续一段：裁片只裁这一段，一张图就能看出歪在哪。"""
    _, ruling, _, rd = sheet(code)
    r = [u for u in rd["rows"] if abs(u["y_at_mid"] - y_mid) <= 2][0]
    x0, x1 = int(r["x"][0]), int(r["x"][1])
    hit = []
    for x in range(x0, x1 + 1, 4):
        y = Y.line_y(r, x)
        lo = max(0, int(y) - Y.SEARCH)
        idx = np.flatnonzero(ruling[lo:int(y) + Y.SEARCH, x])
        d = float(np.abs(idx + lo - y).min()) if len(idx) else np.inf
        if 5 < d <= Y.SEARCH:
            hit.append(x)
    if not hit:
        return x0, x1
    best = cur = [hit[0], hit[0]]
    for x in hit[1:]:
        if x - cur[-1] <= 120:
            cur[-1] = x
        else:
            cur = [x, x]
        if cur[1] - cur[0] > best[1] - best[0]:
            best = cur
    return max(x0, best[0] - 300), min(x1, best[1] + 300)


def crops(code, y_mid, auto=True):
    gray, ruling, glyph, rd = sheet(code)
    hit = [r for r in rd["rows"] if abs(r["y_at_mid"] - y_mid) <= 2]
    if not hit:
        print(f"  {code} y={y_mid}: 没有这条行线，跳过")
        return []
    r = hit[0]
    x0, x1 = worst_run(code, y_mid) if auto else (int(r["x"][0]), int(r["x"][1]))
    ys = np.array([Y.line_y(r, x) for x in range(x0, x1 + 1)])
    top, bot = max(0, int(ys.min()) - M), min(gray.shape[0], int(ys.max()) + M)
    outs = []
    for t, sx in enumerate(range(x0, x1, TILE)):
        ex = min(sx + TILE, x1)
        sl = (slice(top, bot), slice(sx, ex))
        img = cv2.cvtColor(gray[sl], cv2.COLOR_GRAY2BGR)
        for mask, ch, val, w in ((ruling, 1, 190, 0.8), (glyph, 0, 150, 0.45)):
            g = np.zeros_like(img)
            g[..., ch][mask[sl] > 0] = val
            img = cv2.addWeighted(img, 1.0, g, w, 0)
        pts = np.column_stack([np.arange(sx, ex + 1) - sx,
                               np.round(ys[:ex - sx + 1]).astype(int) - top])
        cv2.polylines(img, [pts.astype(np.int32)], False, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(img, f"{code} y={y_mid} x={sx}-{ex}  green=ruling red=drawn",
                    (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 1)
        out = ROOT / "runs" / "tmp" / f"歪线_{code}_{y_mid}_{t}.png"
        cv2.imwrite(str(out), img, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        outs.append(out)
    return outs


if __name__ == "__main__":
    if sys.argv[1] == "--list":
        jobs = [ln.split() for ln in Path(sys.argv[2]).read_text(encoding="utf-8").split("\n")
                if ln.strip()]
    else:
        jobs = [[sys.argv[1], y] for y in sys.argv[2:]]
    for c, y in jobs:
        for p in crops(c, int(y)):
            print(p)
