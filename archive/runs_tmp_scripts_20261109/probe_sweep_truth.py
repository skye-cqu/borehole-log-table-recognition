# -*- coding: utf-8 -*-
"""阶段B+:用两张已重建真值(1032=103行 / 1042=112行)校阈值。

思路:柱状图的行高与层厚成正比(深度线性轴),故真值 层厚 累加归一后 ×[首末线像素跨度]
应落在检测到的层界 y 上。逐阈值量三件事:
  漏(真值界无检测匹配)/ 多(检测界无真值匹配)/ 匹配残差中位数(px),匹配半径=25px(聚簇容差)。
残差小说明"线性深度轴"模型成立,该指标才可用作选阈依据。
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                        # noqa: E402

TRUTH_XLSX = {"1032": "钻孔柱状图1032_还原_补产终版.xlsx",
              "1042": "钻孔柱状图1042_还原_补产终版.xlsx"}
NUM = re.compile(r"\d+(?:\.\d+)?")
R = 25.0


def truth_bounds(code):
    ws = load_workbook(paths.RUNS_DIR / "table_reconstruct" / TRUTH_XLSX[code],
                       read_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h or "") for h in rows[0]]
    ci = next(i for i, h in enumerate(hdr) if "层厚" in h)
    th = []
    multi = 0
    for r in rows[1:]:
        v = str(r[ci] if r[ci] is not None else "")
        ns = NUM.findall(v)
        if len(ns) > 1:
            multi += 1
        th.append(sum(float(n) for n in ns))
    c = np.cumsum([0.0] + th)
    return c / c[-1], multi


def detected(code, th):
    d = json.loads((paths.RUNS_DIR / "tmp" / f"行链_{code}.json").read_text(encoding="utf-8"))
    nw = max(d["num_x"] - d["tab_l"], 1)
    ys = sorted(y for y, n, s in d["lines"]
                if sum_iv(n) / nw >= th)
    return ys, (d["tab_l"], d["tab_r"])


def sum_iv(iv):
    iv = sorted((a, b) for a, b in iv if b > a)
    tot, ca, cb = 0.0, None, None
    for a, b in iv:
        if ca is None:
            ca, cb = a, b
        elif a <= cb:
            cb = max(cb, b)
        else:
            tot += cb - ca
            ca, cb = a, b
    return tot + (cb - ca if ca is not None else 0.0)


def score(code, frac, th):
    ys, (y0, y1) = detected(code, th)
    if len(ys) < 3:
        return None
    det = np.asarray(ys, float)
    tr = y0 + frac * (y1 - y0)                      # 真值层界 → 像素
    dm = np.abs(det[:, None] - tr[None, :])
    t2d = np.min(dm, axis=0)                        # 每条真值界到最近检测界
    d2t = np.min(dm, axis=1)                        # 每条检测界到最近真值界
    ok_t = t2d <= R
    ok_d = d2t <= R
    return {"n": len(det), "漏": int((~ok_t).sum()), "多": int((~ok_d).sum()),
            "res": float(np.median(t2d[ok_t])) if ok_t.any() else float("nan")}


def main():
    fr = {c: truth_bounds(c) for c in TRUTH_XLSX}
    for c, (f, m) in fr.items():
        print(f"真值 {c}: {len(f)-1} 行, 多值层厚格 {m} 个")
    print(f"{'阈值':<6}" + "".join(f"{c+'漏/多/残差':>18}" for c in fr) + f"{'合计漏':>8}{'合计多':>8}")
    for th in (0.6, 0.55, 0.5, 0.48, 0.45, 0.4, 0.35, 0.3):
        cells, ml, md = [], 0, 0
        for c in fr:
            s = score(c, fr[c][0], th)
            cells.append(f"{s['漏']}/{s['多']}/{s['res']:.0f}")
            ml += s["漏"]; md += s["多"]
        print(f"{th:<6}" + "".join(f"{x:>18}" for x in cells) + f"{ml:>8}{md:>8}")


if __name__ == "__main__":
    main()
