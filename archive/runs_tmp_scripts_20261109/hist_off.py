# -*- coding: utf-8 -*-
"""每条层界的"离墨采样%"分布：坏线是"少数几条离谱"还是"多数轻微歪"。

用法: python runs/tmp/hist_off.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
import yardstick as Y                                               # noqa: E402

BINS = [0, 1, 5, 10, 25, 50, 75, 100.01]
hist = np.zeros(len(BINS) - 1, int)
nink = np.zeros(len(BINS) - 1, int)
n = 0
for p in sorted(paths.CANDIDATE_COORD_DIR.glob("*.json")):
    rd = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                     f"{p.stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(p.stem)
    W = ruling.shape[1]
    for r in rd["rows"]:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        off = nk = nn = 0
        for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), Y.SAMPLE):
            y = Y.line_y(r, x)
            band = ruling[max(0, int(y) - Y.SEARCH):int(y) + Y.SEARCH, int(x)]
            idx = np.flatnonzero(band)
            nn += 1
            if not len(idx):
                nk += 1
                off += 1
            elif np.abs(idx + max(0, int(y) - Y.SEARCH) - y).min() > 5:
                off += 1
        h = np.histogram([off / nn * 100], bins=BINS)[0]
        hist += h
        nink += np.histogram([nk / nn * 100], bins=BINS)[0]
        n += 1
print(f"每条层界的离墨采样% 分布，共 {n} 条层界")
for i in range(len(BINS) - 1):
    print(f"  {BINS[i]:3.0f}-{BINS[i + 1]:3.0f}% : {hist[i]:5d} 条"
          f"   (同档里\"完全找不到横线墨\"的采样占比也>0 的: {nink[i]:5d})")
print(f">10% 的线: {hist[3:].sum()} 条 ({hist[3:].sum() / n * 100:.0f}%)"
      f"    >50% 的线: {hist[5:].sum()} 条 ({hist[5:].sum() / n * 100:.0f}%)")
