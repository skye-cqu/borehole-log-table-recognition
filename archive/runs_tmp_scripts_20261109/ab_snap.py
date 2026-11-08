# -*- coding: utf-8 -*-
"""A/B：把已定稿的层界折线逐点吸到就近的"横线墨"上，看能不能修掉那 14 条真歪的线。

歪的形态（裁片实测）：线在表左半贴着真行界，右半爬进相邻一行 → 画出来的线穿过文字。
这一档只做一件事：折线每个顶点在它 ±min(25px, 0.30×行高) 内找横线墨（自适应二值→40×1 横条
开运算→25px 闭运算，和尺子同一套墨定义），找到就把点挪到墨的均值上，找不到原地不动。
半径压在 0.30×行高以内 = 不可能把点挪到上/下相邻那条线上。

产物 runs/tmp/ab/吸墨/，生产目录不动。用法: python runs/tmp/ab_snap.py [1037 1027]  # 无参数=30 张
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
import yardstick as Y                                               # noqa: E402
from src.core import paths                                          # noqa: E402

OUT = ROOT / "runs" / "tmp" / "ab" / "吸墨"
RAD_FRAC = 0.30         # 吸附半径上限 = 行高的这个比例（半行高以内才不可能跳到邻行）
RAD_MAX = 25.0


def snap(code):
    stem = f"钻孔柱状图{code}"
    src = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                      f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(stem)
    H = ruling.shape[0]
    rad = min(RAD_MAX, RAD_FRAC * src.get("row_h", 80))
    moved = tot = 0
    for key in ("rows", "sub_rows"):
        for r in src[key]:
            pl = np.asarray(r["poly"], float)
            for k in range(len(pl)):
                x = int(np.clip(pl[k, 0], 0, pl[-1, 0]))
                y = int(round(pl[k, 1]))
                lo, hi = max(0, y - int(rad)), min(H, y + int(rad) + 1)
                idx = np.flatnonzero(ruling[lo:hi, x])
                if len(idx):
                    tot += 1
                    # 只吸"离它最近的那一横条墨"：±半径里同时有上下两条线时，
                    # 取全部墨点的均值会落在两条线中间的空纸上（实测越吸越偏）。
                    grp = np.split(idx, np.flatnonzero(np.diff(idx) > 2) + 1)
                    near = min(grp, key=lambda g: abs(g.mean() + lo - y))
                    ny = float(near.mean() + lo)
                    if abs(ny - pl[k, 1]) > 0.5:
                        moved += 1
                    pl[k, 1] = ny
            r["poly"] = [[round(float(a), 1), round(float(b), 1)] for a, b in pl]
            r["y_at_mid"] = round(float(np.median(pl[:, 1])), 1)
            r["x"] = [int(pl[0, 0]), int(pl[-1, 0])]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stem}_行判定.json").write_text(json.dumps(src, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    return code, tot, moved, round(rad, 1)


if __name__ == "__main__":
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
            sorted(p.name.split("图")[1].split("_")[0]
                   for p in (paths.RUNS_DIR / "table_reconstruct").glob("*_行判定.json"))
    for c in codes:
        print("{}  顶点 {} 个 挪动 {} 个  半径 {}px".format(*snap(c)), flush=True)
