# -*- coding: utf-8 -*-
"""最后两条漏线值不值得放宽 ROW_COV：把覆盖率门槛往下扫，看多出来的线贴不贴墨。

漏线口径（diag_missed）说 1027/1040 各剩 1 条真横线没接住，它们当时的 cov_num 是
0.32 / 0.373，都卡在 ROW_COV=0.40 下面。放宽能不能捞回来、代价是什么，得有数。
标尺只用数值区（层界的定义域就在数值区，描述区的墨是手写长横，量不得）：
  数值区离墨% = 层界在 [表左缘, boundary_x] 上采样，±60px 内找不到横线墨的占比
用法: python runs/tmp/sweep_cov.py 1027 1040
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.table import track_rows as tr                              # noqa: E402
import yardstick as Y                                               # noqa: E402
import diag_missed as M                                             # noqa: E402

COVS = [0.40, 0.37, 0.32, 0.28]


def run(code):
    stem = f"钻孔柱状图{code}"
    ch = tr.load_chains(stem)
    ruling, _ = Y.masks(stem)
    print(f"\n=== {code} 链 {len(ch['items'])} 条 ===")
    print(f"{'ROW_COV':>8}{'层界':>6}{'漏线':>6}{'数值区离墨>30%':>16}{'>10%':>6}{'中位':>7}")
    base = tr.ROW_COV
    for cov in COVS:
        tr.ROW_COV = cov
        o = tr.assemble(ch)
        b = int(np.median([r["boundary_x"] for r in o["rows"]]))
        num = [offink_num(ruling, r, ch["tab_l"], b) for r in o["rows"]]
        print(f"{cov:>8.2f}{len(o['rows']):>6}{len(M.missed(o, ruling)):>6}"
              f"{sum(1 for v in num if v > 30):>16}{sum(1 for v in num if v > 10):>6}"
              f"{np.median(num):>7.1f}")
    tr.ROW_COV = base


def offink_num(ruling, r, a, z, n=40, search=60, over=5.0):
    """层界只量数值区那一段的离墨%。"""
    ds = []
    for x in np.linspace(max(r["x"][0], a) + 5, min(r["x"][1], z) - 5, n):
        y = tr.row_y(r, x)
        band = ruling[max(0, int(y) - search):min(ruling.shape[0], int(y) + search), int(x)]
        i = np.flatnonzero(band)
        ds.append(float(np.abs(i + max(0, int(y) - search) - y).min()) if len(i) else np.nan)
    return float(np.mean([not np.isfinite(v) or v > over for v in ds])) * 100


if __name__ == "__main__":
    for c in [a for a in sys.argv[1:] if a.isdigit()] or ["1027", "1040"]:
        run(c)
