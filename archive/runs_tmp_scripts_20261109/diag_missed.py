# -*- coding: utf-8 -*-
"""诊断B（用户提的 1040 漏线）：原图有横线墨、我们没有层界的地方。

做法：数值区（表左缘→层界里记的 boundary_x）内按 y 扫横线墨带——
一行 y 上 ≥40% 的 x 采样有 ruling 墨，且带高 ≤8px，就是一条"图上真实存在的横线"。
再看它 ±TOL 内有没有层界经过；没有 = 漏线。
漏的那条若被降级成了子行线，把它当时的 cov_num 一起打出来 → 直接分辨
"判据过严"还是"上游根本没这条线"。

用法: python runs/tmp/diag_missed.py [1040 1027 ...]     # 无参数=30 张
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import row_y                              # noqa: E402
import yardstick as Y                                               # noqa: E402

SRC = Path(os.environ.get("SRC", ROOT / "runs" / "table_reconstruct"))
TOL = 12          # 层界离真线 ±12px 内算"接住了"
FRAC = 0.40       # 该 y 带上多少比例的 x 有横线墨才算一条真横线


def bands(ruling, x0, x1, hdr_bot):
    """数值区 → 真实横线墨带 [(y中位, 覆盖率)]。"""
    xs = np.linspace(x0 + 30, x1 - 30, 120).astype(int)
    col = ruling[:, xs] > 0
    cov = col.mean(axis=1)
    out, y = [], 0
    while y < len(cov):
        if cov[y] < 0.12:
            y += 1
            continue
        y1 = y
        while y1 + 1 < len(cov) and cov[y1 + 1] >= 0.12:
            y1 += 1
        if y1 - y <= 8 and y > hdr_bot:               # 带高够窄 = 一条线，不是文字堆
            c = cov[y:y1 + 1]
            out.append((float(np.average(np.arange(y, y1 + 1), weights=c)), float(c.max())))
        y = y1 + 1
    return [b for b in out if b[1] >= FRAC]


def missed(rd, ruling):
    """一份 行判定.json + 横线墨迹 → (图上真横线条数, [(y, 墨覆盖, 最近层界差px, 子行线cov)])。

    标尺 sweep_gates 也调它，漏线口径不留两份。
    """
    x0, x1 = int(rd["table_x"][0]), int(rd["table_x"][1])
    b = int(np.median([r["boundary_x"] for r in rd["rows"]]))
    rows = rd["rows"]
    hdr_bot = min(int(r["y_at_mid"]) for r in rows)          # 首条层界≈表头底
    miss = []
    for y, c in bands(ruling, x0, min(b, x1), hdr_bot + 5):
        xs = np.linspace(x0 + 30, min(b, x1) - 30, 40)
        near = min((np.median([abs(row_y(r, x) - y) for x in xs]) for r in rows),
                   default=1e9)
        if near > TOL:
            sub = [r for r in rd["sub_rows"] if abs(r["y_at_mid"] - y) <= 25]
            miss.append((y, c, near, sub[0]["cov_num"] if sub else None))
    return miss


if __name__ == "__main__":
    for code in [a for a in sys.argv[1:] if a.isdigit()] or \
            sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json")):
        stem = f"钻孔柱状图{code}"
        rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
        ruling, _ = Y.masks(stem)
        miss = missed(rd, ruling)
        print(f"{code}: 层界 {len(rd['rows'])} 条,漏 {len(miss)} 条{'' if miss else '  ✓'}")
        for y, c, near, cv in miss[:10]:
            print(f"    y={y:7.0f} 墨覆盖{c * 100:3.0f}%  最近层界差{near:4.0f}px  "
                  f"同位置子行线cov={cv}")
