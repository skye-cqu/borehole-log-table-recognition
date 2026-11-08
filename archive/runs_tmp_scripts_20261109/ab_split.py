# -*- coding: utf-8 -*-
"""门禁档位对跑：同一批链、同一把标尺（原图横线墨 + 漏线带），外加一把不靠墨的行距尺。

为什么加行距尺：离墨读数受标尺自身边界影响（淡线被开运算抹掉→只能当下限），而"相邻层界
间距落在 0.8~1.2 行高"和"两线挤在同一行里(<0.6 行高)"只看线自己排出来的格，拼错的线一定会
在这里露出来——1027 挤线 14→6、1040 3→0（切分后）。

用法: python runs/tmp/ab_split.py [1027 1040]   # 7 档细跑，逐档 vs 只形状闸
      python runs/tmp/ab_split.py brief          # 3 档粗跑，全量 30 张一行一张 + 合计
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402
import yardstick as Y                                               # noqa: E402
import diag_missed as M                                             # noqa: E402
from sweep_gates import offink                                      # noqa: E402

# (档名, skew, split)；None = 用模块默认，0 = 关掉这一道
VARIANTS = [("无门禁", 9.0, 0.0), ("只形状闸", None, 0.0)] + \
           [(f"切分{f:.1f}", None, f) for f in (0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.5)]
BRIEF = [("门禁前", 9.0, 0.0), ("形状闸", None, 0.0), ("定稿", None, None)]
BASE = "只形状闸"


def load(code):
    stem = f"钻孔柱状图{code}"
    return tr.load_chains(stem), Y.masks(stem)[0]


def spacing(o):
    """(行距落在 0.8~1.2 行高的占比%, 挤在一起 <0.6 行高处数, 大缝 >1.3 行高处数)。"""
    h = o["row_h"]
    d = np.diff(sorted(r["y_at_mid"] for r in o["rows"]))
    if not len(d):
        return 0.0, 0, 0
    return (float(np.mean((d > 0.8 * h) & (d < 1.2 * h)) * 100),
            int((d < 0.6 * h).sum()), int((d > 1.3 * h).sum()))


def measure(ch, ruling, sk, sp):
    """一档门禁的全部读数。被形状闸剔掉的线也拿同一把尺子量：剔的若是贴在墨上的真行
    = 阈值过紧（'rej10' 这一列），30 张里 1020/1035 就是这个形态。"""
    o = tr.assemble(ch, sk, sp)
    oi = offink(ruling, o["rows"])
    rej = offink(ruling, o["off_grid"])
    reg, tight, wide = spacing(o)
    return dict(o=o, n=len(o["rows"]), miss=len(M.missed(o, ruling)),
                o30=sum(1 for v in oi if v > 30), o10=sum(1 for v in oi if v > 10),
                med=float(np.median(oi)) if oi else 0.0, off=len(o["off_grid"]),
                rej10=sum(1 for v in rej if v <= 10),
                cut=o["n_chains_split"], pieces=o["n_pieces"], reg=reg, tight=tight,
                wide=wide)


HEAD = (f"{'档位':<9}{'层界':>5}{'漏线':>5}{'离墨>30%':>9}{'离墨>10%':>9}{'中位离墨':>9}"
        f"{'剔线':>5}{'剔且贴墨':>9}{'切开链':>7}{'段数':>5}{'行距规整%':>10}{'挤<0.6h':>8}{'大缝':>5}")


def line(tag, m):
    return (f"{tag:<9}{m['n']:>5}{m['miss']:>5}{m['o30']:>9}{m['o10']:>9}{m['med']:>9.1f}"
            f"{m['off']:>5}{m['rej10']:>9}{m['cut']:>7}{m['pieces']:>5}{m['reg']:>10.0f}"
            f"{m['tight']:>8}{m['wide']:>5}")


def detail(code, ch, ruling):
    print(f"\n=== {code}  链 {len(ch['items'])} 条  全表中位斜率 {ch['s0']:+.4f} ===")
    print(HEAD)
    got = {}
    for tag, sk, sp in VARIANTS:
        got[tag] = m = measure(ch, ruling, sk, sp)
        print(line(tag, m))
    base = got[BASE]
    bad = [f'{r["y_at_mid"]:.0f}:{v:.0f}'
           for r, v in zip(base["o"]["rows"], offink(ruling, base["o"]["rows"])) if v > 30]
    print(f"  行高 {base['o']['row_h']}px；{BASE} 的漏线 "
          f"{[f'{t[0]:.0f}' for t in M.missed(base['o'], ruling)]}  离墨>30% 的线 {bad}")
    ys_b = sorted(round(r["y_at_mid"]) for r in base["o"]["rows"])
    for tag, *_ in VARIANTS[2:]:
        o = got[tag]["o"]
        ys_n = sorted(round(r["y_at_mid"]) for r in o["rows"])
        # 同一条线被挪几 px ≠ 多/少一条线：先按 ±15px 配对，再报配不上对的
        moved = [(y, min((v for v in ys_b if abs(v - y) <= 15), key=lambda v: abs(v - y),
                         default=None)) for y in ys_n]
        shift = [(y, v) for y, v in moved if v is not None and y != v]
        print(f"  {tag} vs {BASE}：切分限 {o['split_lim']:.0f}px  切开 "
              f"{got[tag]['cut']} 条链→{got[tag]['pieces']} 段  漏线 "
              f"{[f'{t[0]:.0f}' for t in M.missed(o, ruling)]}")
        print(f"    平移 {len(shift)} 条（最大 {max((abs(y - v) for y, v in shift), default=0)}px）"
              f" 真新增 {[y for y, v in moved if v is None]}"
              f" 真失去 {[v for v in ys_b if v not in [u for _, u in moved if u is not None]]}")


def brief(codes):
    """30 张一张一行，三档并排：只看"层界/漏线/离墨>10/剔线/切开/挤线"，末行合计。"""
    cols = "层界 漏 >10 剔 剔墨 切 挤"
    print(f"{'图':<6}" + "".join(f"{f'{t}({cols})':>30}" for t, *_ in BRIEF))
    acc = {t: [] for t, *_ in BRIEF}
    for code in codes:
        ch, ruling = load(code)
        cells = []
        for tag, sk, sp in BRIEF:
            m = measure(ch, ruling, sk, sp)
            acc[tag].append(m)
            cells.append(f"{m['n']:>6}{m['miss']:>3}{m['o10']:>4}{m['off']:>4}"
                         f"{m['rej10']:>5}{m['cut']:>3}{m['tight']:>4}")
        print(f"{code:<6}" + "".join(cells))
    for tag, *_ in BRIEF:
        ms = acc[tag]
        print(f"合计 {tag:<6}"
              f"{sum(m['n'] for m in ms):>5} 漏{sum(m['miss'] for m in ms):>3} "
              f">10 {sum(m['o10'] for m in ms):>4} 剔{sum(m['off'] for m in ms):>4} "
              f"剔墨{sum(m['rej10'] for m in ms):>4} 切{sum(m['cut'] for m in ms):>4} "
              f"挤{sum(m['tight'] for m in ms):>4} "
              f"行距规整{np.mean([m['reg'] for m in ms]):>5.0f}% 中位离墨"
              f"{np.mean([m['med'] for m in ms]):>5.1f}")


if __name__ == "__main__":
    codes = [a for a in sys.argv[1:] if a.isdigit()] or ["1027", "1040"]
    if "brief" in sys.argv[1:]:
        codes = sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
        brief(codes)
    else:
        for c in codes:
            ch, ruling = load(c)
            detail(c, ch, ruling)
