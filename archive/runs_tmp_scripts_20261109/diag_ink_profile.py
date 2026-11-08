# -*- coding: utf-8 -*-
"""逐条线的"离墨剖面"：这条线在原图横线上走多远、在哪一段离开墨迹。

为什么量：门禁阈值 A/B 的结论是形状读数(斜率/走偏)分不开好坏——
1027 无门禁 115 条层界里，贴合真行(离墨≤10%)81 条的 ptp 中位 0.28 行高，
离墨>10% 的 34 条 ptp 中位 0.29，两个分布重叠；1040 最歪的那条(8.1 行高)反而
离墨 0.0%，是条真而弯的行线。所以"歪"不是"不存在"的判据，得看墨本身。
按 10 个 x 分箱打每条线的中位离墨距离：一路贴墨后段飘走 = 追踪跳线；
全程无墨 = 凭空画的；只断几格 = 桥接口子，该裁不该删。

用法: python runs/tmp/diag_ink_profile.py 1027 [1040 ...]   # 默认点 1027 最歪的几条
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402
from src.table.track_rows import row_y                              # noqa: E402
import yardstick as Y                                               # noqa: E402

SRC = Path(os.environ.get("SRC", str(ROOT / "runs" / "table_reconstruct")))
N_BIN = 12
SEARCH = 60


def profile(rec, ruling):
    """线 → 每箱的中位离墨距离(px)。找不到墨记 999。"""
    x0, x1 = int(rec["x"][0]), int(rec["x"][1])
    H = ruling.shape[0]
    ds = []
    for x in np.linspace(x0, x1, 240):
        xi = int(x)
        y = row_y(rec, x)
        band = ruling[max(0, int(y) - SEARCH):min(H, int(y) + SEARCH), xi]
        idx = np.flatnonzero(band)
        ds.append(float(np.abs(idx + max(0, int(y) - SEARCH) - y).min())
                  if len(idx) else 999.0)
    ds = np.array(ds)
    return np.array_split(ds, N_BIN)


def main(codes, picks):
    for code in codes:
        stem = f"钻孔柱状图{code}"
        rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
        ruling, _ = Y.masks(stem)
        row_h = max(rd["row_h"], 1.0)
        # ptp 从折线现算：老快照 JSON 里没这个字段，别为了看剖面先重跑一遍生产
        for r in rd["rows"]:
            r["ptp"] = tr.ptp_off(np.asarray(r["poly"], float), rd["slope_med"])
        want = [r for r in rd["rows"] if any(abs(r["y_at_mid"] - p) < 18 for p in picks)] \
            if picks else sorted(rd["rows"], key=lambda r: -r["ptp"])[:6]
        print(f"\n=== {code} 行高 {row_h:.0f}px，层界 {len(rd['rows'])} 条"
              f"（点 {picks or 'ptp 最大的 6 条'}）===")
        for r in want:
            bins = [float(np.median(b)) for b in profile(r, ruling)]
            off = sum(1 for v in bins if v > 5)
            print(f"y={r['y_at_mid']:7.0f} ptp={r['ptp'] / row_h:4.2f}行高 "
                  f"离墨箱{off:>2}/{N_BIN}  " +
                  " ".join("浮" if v >= 999 else (f"{v:3.0f}" if v > 5 else f"{v:2.0f}·")
                           for v in bins))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[:1] or ["1027"], [float(v) for v in a[1:]])
