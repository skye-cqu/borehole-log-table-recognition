# -*- coding: utf-8 -*-
"""形状门禁阈值扫描：建链一次，用原图横线墨迹当标尺，把所有档位在同一批线上跑完。

为什么要它：上一版按"斜率>3%"逐链剔除，1027 层界从 115 掉到 92——肉眼看到的是"线画歪了"，
数字看到的是"13 条平直真行被连带杀掉"。阈值不能靠猜，也不能靠人眼，得有客观读数。
标尺是原图自己的墨（yardstick 同一套 mask），跟门禁参数无关：
  离墨%   = 这条层界的采样点里，±60px 内找不到横线墨或距离>5px 的占比 → 高 = 线上不存在
  漏线    = 图上有横线墨带、±12px 内没有层界（diag_missed 同一口径）
一张表同时报"消掉的坏线"和"误杀的真行"，才挑得出阈值。

注意标尺自己的边界：横线墨 = 40×1 开运算，手写汉字的长横笔也会被留下，
所以离墨只在数值区可信，描述区里"贴墨"不等于"是行线"（1027 y=10886 就是这条：
它在描述区一路压着字的横笔，剖面读数 0~3px，肉眼却是斜穿三行字）。

用法: python runs/tmp/sweep_gates.py 1027 1040
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.table import track_rows as tr                              # noqa: E402
import yardstick as Y                                               # noqa: E402
import diag_missed as M                                             # noqa: E402

SAMPLE, SEARCH, OVER = 60, 60, 5.0
# 无门禁 = 阈值放到 900%；2% 已部署，3%/5% = 用户给的区间
VARIANTS = [("无门禁", 9.0), ("窗斜率2%部署", 0.02), ("窗斜率3%", 0.03), ("窗斜率5%", 0.05)]


def offink(ruling, rows):
    """每条层界的离墨采样%(>5px 或找不到墨)。0 = 60 个采样全贴在横线墨上。"""
    H, W = ruling.shape                                           # numpy 是 (行, 列)
    out = []
    for r in rows:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        ds = []
        for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), SAMPLE):
            xi = int(x)
            y = tr.row_y(r, x)
            band = ruling[max(0, int(y) - SEARCH):min(H, int(y) + SEARCH), xi]
            idx = np.flatnonzero(band)
            ds.append(float(np.abs(idx + max(0, int(y) - SEARCH) - y).min())
                      if len(idx) else np.nan)
        out.append(float(np.mean([not np.isfinite(v) or v > OVER for v in ds])) * 100)
    return out


def run(code):
    stem = f"钻孔柱状图{code}"
    ch = tr.load_chains(stem)
    ruling, _ = Y.masks(stem)
    print(f"\n=== {code}  链 {len(ch['items'])} 条，全表中位斜率 {ch['s0']:+.4f} ===")
    print(f"{'档位':<10}{'层界':>5}{'漏线':>5}{'离墨>30%':>9}{'离墨>10%':>9}{'中位离墨':>9}"
          f"{'剔线':>5}{'最大窗斜率':>9}")
    for tag, skew in VARIANTS:
        o = tr.assemble(ch, skew)
        oi = offink(ruling, o["rows"])
        ms = M.missed(o, ruling)
        print(f"{tag:<10}{len(o['rows']):>5}{len(ms):>5}"
              f"{sum(1 for v in oi if v > 30):>9}{sum(1 for v in oi if v > 10):>9}"
              f"{np.median(oi) if oi else 0:>9.1f}{len(o['off_grid']):>5}"
              f"{max((abs(r['win']) for r in o['rows']), default=0):>9.1%}")
        for r in o["off_grid"]:
            print(f"          剔 y={r['y_at_mid']:.0f} 窗斜率{r['win']:+.1%} "
                  f"跨{r['span']}px 链{r['n_chains']}条 cov_num={r['cov_num']:.2f}")
    # 相关性：无门禁的层界按窗斜率排开，逐条看它离墨多远——窗斜率真能预言"线上不存在"吗
    o = tr.assemble(ch, 9.0)
    oi = offink(ruling, o["rows"])
    z = sorted(zip(o["rows"], oi), key=lambda t: -abs(t[0]["win"]))
    print("  无门禁层界按窗斜率偏离排序（窗斜率｜离墨%｜跨度｜链数）")
    for r, v in z[:8]:
        print(f"    y={r['y_at_mid']:7.0f} 窗斜率{r['win']:+6.1%} 离墨{v:5.1f}% "
              f"跨{r['span']:5d}px 链{r['n_chains']}条 cov_num={r['cov_num']:.2f}")
    lo = [abs(r["win"]) for r, v in z if v <= 10]
    hi = [abs(r["win"]) for r, v in z if v > 10]
    print(f"    贴合真行(离墨≤10%) {len(lo)} 条：|窗斜率偏离| 中位 {np.median(lo):.1%} "
          f"最大 {max(lo):.1%}")
    print(f"    离墨>10%      {len(hi)} 条：|窗斜率偏离| 中位 {np.median(hi):.1%} "
          f"最大 {max(hi):.1%}")


if __name__ == "__main__":
    for c in [a for a in sys.argv[1:] if a.isdigit()] or ["1027", "1040"]:
        run(c)
