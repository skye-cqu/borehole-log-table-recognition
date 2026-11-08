# -*- coding: utf-8 -*-
"""漏定的竖墨落在柱状带里还是带外：带内=图案自己的边框（不能当列线），带外=要人看。

只读 runs/tmp/yard_cols_30.log 的判定结果 + 6a 定稿列线，不再碰图。
用法: python runs/tmp/triage_misscols.py
"""
import re
import sys
from pathlib import Path

import numpy as np

ROOT = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + "/runs/tmp")
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402
from src.table.track_rows import x_at                               # noqa: E402

cur = None
for ln in open(ROOT + "/runs/tmp/yard_cols_30.log", encoding="utf-8").read().split("\n"):
    m = re.match(r"^(1\d{3}): 列线", ln)
    if m:
        cur = m.group(1)
    m = re.search(r"漏: x=(\d+)\s+竖墨占表高 (\d+)%", ln)
    if not (m and cur):
        continue
    x, pct = float(m.group(1)), int(m.group(2))
    w, e, _ = tr.content_band(f"钻孔柱状图{cur}")
    if w is None:
        print(f"{cur} x={x:.0f} 竖墨{pct}%  该张无柱状带")
        continue
    ys = np.linspace(1000, 16000, 31)
    win, ein = [x_at(w, y) for y in ys], [x_at(e, y) for y in ys]
    inn = sum(a <= x <= b for a, b in zip(win, ein)) >= 16      # 过半高度落在带内
    tag = "带内=柱状图案边框" if inn else "带外=需人看"
    print(f"{cur} x={x:5.0f} 竖墨{pct:2d}%  带 {np.median(win):.0f}~{np.median(ein):.0f}  {tag}")
