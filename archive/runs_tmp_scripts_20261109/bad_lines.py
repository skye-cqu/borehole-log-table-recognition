# -*- coding: utf-8 -*-
"""把标尺落到"哪几条线"：列出超差采样 >10% 的层界，给肉眼核验用。

用法: python runs/tmp/bad_lines.py 1027 1040     # 无参数=30 张
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
sys.path.insert(0, str(ROOT))
import yardstick as Y                                              # noqa: E402


def lines_of(code):
    import json
    stem = f"钻孔柱状图{code}"
    rd = json.loads((Y.SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, glyph = Y.masks(stem)
    W = ruling.shape[1]
    out = []
    for r in rd["rows"]:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        off, cross, n = 0, 0, 0
        for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), Y.SAMPLE):
            xi = int(x)
            y = Y.line_y(r, x)
            band = ruling[max(0, int(y) - Y.SEARCH):int(y) + Y.SEARCH, xi]
            idx = np.flatnonzero(band)
            n += 1
            if not len(idx) or np.abs(idx + max(0, int(y) - Y.SEARCH) - y).min() > 5:
                off += 1
            if glyph[int(y) - 2:int(y) + 3, xi].any():
                cross += 1
        if off / n > 0.10 or cross / n > 0.30:
            out.append((round(r["y_at_mid"]), r["x"], round(off / n * 100),
                        round(cross / n * 100), r["n_chains"]))
    return out


for code in [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in Y.paths.CANDIDATE_COORD_DIR.glob("*.json")):
    ls = lines_of(code)
    print(f"{code}: 超差/压字线 {len(ls)} 条  (y, x跨度, 离墨%, 压字%, 链数)")
    for t in sorted(ls, key=lambda v: -(v[2] + v[3]))[:8]:
        print(f"    y={t[0]:<6} x={t[1][0]}-{t[1][1]:<6} 离墨{t[2]:>3}% 压字{t[3]:>3}% "
              f"链{t[4]}")
