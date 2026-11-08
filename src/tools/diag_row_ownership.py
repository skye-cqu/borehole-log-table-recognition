# -*- coding: utf-8 -*-
"""行界归属量化诊断:待核格裁片里"数字到底落在哪个行区间",用墨迹段实测判定,
不靠肉眼争论。

对指定图的指定列:逐行区间 [rows_y[i], rows_y[i+1]] 统计列带内暗像素,提取墨迹
连通段(=手写的数字/文字行),报告每段中心相对所在行区间的位置(0=区间上沿,
1=区间下沿,>1=写到区间外下方)。用于判定 rows_y 是否存在系统性偏移。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.agnes4_verify import chart_geometry  # noqa: E402
from src.tools.rebuild4_excel import _chain_x  # noqa: E402

INK = 128          # 暗像素阈
MIN_RUN = 4        # 墨迹段最小连续行高(px),滤掉线宽


def col_x(g, name, y_mid):
    c = next((c for c in g["keep"] if c["name"] == name), None)
    if c is None:
        return None
    xa = _chain_x(g["seg_all"], g["bs"][c["li"]]["ids"], y_mid)
    xb = _chain_x(g["seg_all"], g["bs"][c["ri"]]["ids"], y_mid)
    return (xa if xa is not None else c["x0"], xb if xb is not None else c["x1"])


def ink_runs(col_band):
    """列带(1D 暗像素计数)→ 墨迹段 [(起,止)]。"""
    dark = col_band > 0
    runs, s = [], None
    for i, d in enumerate(dark):
        if d and s is None:
            s = i
        elif not d and s is not None:
            if i - s >= MIN_RUN:
                runs.append((s, i))
            s = None
    if s is not None and len(dark) - s >= MIN_RUN:
        runs.append((s, len(dark)))
    return runs


def main(n, names, layers):
    g = chart_geometry(n)
    gray = g["gray"]
    rows_y = g["rows_y"]
    for name in names:
        print(f"\n=== 钻孔柱状图{n} 列「{name}」 ===")
        pos_all = []
        for li in layers:
            y0, y1 = int(rows_y[li]), int(rows_y[li + 1])
            xa, xb = col_x(g, name, (rows_y[li] + rows_y[li + 1]) / 2)
            x0, x1 = int(min(xa, xb)), int(max(xa, xb))
            # 上下各多看 60px,捕捉写到区间外的墨迹
            Y0, Y1 = max(0, y0 - 60), min(gray.shape[0], y1 + 60)
            band = (gray[Y0:Y1, x0 + 3:x1 - 3] < INK).sum(axis=1)
            runs = ink_runs(band)
            desc = []
            for s, e in runs:
                gy0, gy1 = Y0 + s, Y0 + e
                center = (gy0 + gy1) / 2
                # 归属:中心落在哪个行区间
                owner = None
                for k in range(len(rows_y) - 1):
                    if rows_y[k] <= center < rows_y[k + 1]:
                        owner = k + 1
                        break
                frac = (center - y0) / max(y1 - y0, 1)
                desc.append(f"墨段y[{gy0},{gy1}]→第{owner}层(区间内位置{frac:+.2f})")
                if owner == li + 1:
                    pos_all.append(frac)
            print(f"  第{li+1}层 行界[{y0},{y1}] 高{y1-y0}px : " + ("; ".join(desc) or "无墨"))
        if pos_all:
            a = np.array(pos_all)
            print(f"  >> 本格墨迹中心在行区间内的相对位置: 中位 {np.median(a):+.2f} "
                  f"均值 {a.mean():+.2f}  p10 {np.percentile(a,10):+.2f} "
                  f"p90 {np.percentile(a,90):+.2f}  (0=上沿 1=下沿,>0.75 即偏下压线)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1032
    names = (sys.argv[2] if len(sys.argv) > 2 else "层厚,采长,真厚").split(",")
    lo = int(sys.argv[3]) if len(sys.argv) > 3 else 29
    hi = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    main(n, names, list(range(lo - 1, hi)))
