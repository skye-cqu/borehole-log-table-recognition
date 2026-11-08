# -*- coding: utf-8 -*-
"""残差归因:旧行模型的每个"捆行带"里,到底有没有候选横线?

带 = 现行 行判定.json 相邻两条层界之间的 y 区间(= 交付表一行)。
T  = 该行 深度/层厚 格里的数值个数(几个值就是捆了 T 行)→ 带内应有 T-1 条界线。
P  = v3 缓存里落在带内(离两边 >MARGIN)的线簇数,及其 cov_num 分布。

分类:
  可救 = 带内 P >= T-1 且其中有 cov_num 落在 [LO, 阈值) → 降阈值就能补上
  缺线 = 带内 P < T-1 且没有低于阈值的候选 → 线根本不在链并集里(阶段4/5 召回问题)
输出每类格数与占比,直接决定"继续调阈值"还是"转去查缺线"。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"
NUM = re.compile(r"-?\d+(?:\.\d+)?")
TH = 0.40
LO = 0.15
MARGIN = 18.0


def lines(code):
    d = json.loads((paths.RUNS_DIR / "tmp" / f"行链3_{code}.json").read_text(encoding="utf-8"))
    tab_l, tab_r = d["tab_l"], d["tab_r"]
    b = float(np.clip(d["anchor_x"], tab_l + 60, tab_r - 60))
    out = []
    for y, iv in d["lines"]:
        ca = cb = None
        tot = 0.0
        for a, e in sorted([(max(a, tab_l), min(e, b)) for a, e in iv]):
            if ca is None:
                ca, cb = a, e
            elif a <= cb:
                cb = max(cb, e)
            else:
                tot += cb - ca
                ca, cb = a, e
        tot += cb - ca if ca is not None else 0.0
        out.append((y, tot / max(b - tab_l, 1.0)))
    return out


def main():
    stat = Counter()
    per = []
    for p in sorted((paths.RUNS_DIR / "table_reconstruct").glob("*_行判定.json")):
        code = re.search(r"(\d{4})", p.stem).group(1)
        rm = json.loads(p.read_text(encoding="utf-8"))
        ys = [r["y_at_mid"] for r in rm["rows"]]
        if len(ys) < 2:
            continue
        L = lines(code)
        ws = load_workbook(DELIV / f"{code}_还原.xlsx", read_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        hdr = [str(h or "") for h in rows[0]]
        idx = [i for i, h in enumerate(hdr) if any(k in h for k in ("深度", "层厚"))]
        n_ok = n_low = n_none = n_band = 0
        for j in range(len(ys) - 1):
            if j + 1 >= len(rows) - 1:
                break
            r = rows[j + 1]
            T = max([1] + [len(NUM.findall(str(r[i]))) if isinstance(r[i], str)
                           else (1 if isinstance(r[i], (int, float)) else 0)
                           for i in idx])
            need = T - 1
            if need <= 0:
                continue
            n_band += 1
            inside = [(y, c) for y, c in L if ys[j] + MARGIN < y < ys[j + 1] - MARGIN]
            passed = [c for y, c in inside if c >= TH]
            low = [c for y, c in inside if LO <= c < TH]
            if len(passed) + len(low) >= need and low:
                n_ok += 1                      # 降阈值可救
            elif len(passed) >= need:
                n_ok += 1                      # 已够(旧模型漏在别处)
            elif not inside:
                n_none += 1                    # 带内一条候选都没有
            else:
                n_low += 1                     # 有线但不够,含不足 need
        per.append((code, n_band, n_ok, n_low, n_none))
        if abs(len(ys) - (len(rows) - 1)) > 3:
            print(f"  ! {code}: 行模型 {len(ys)} 条 vs 交付 {len(rows)-1} 行，带↔行映射可能错位")
        stat["band"] += n_band
        stat["ok"] += n_ok
        stat["low"] += n_low
        stat["none"] += n_none
    print(f"{'张':<6}{'捆行带':>7}{'够/可救':>8}{'线不足':>8}{'带内无线':>9}")
    for c, nb, ok, low, none in sorted(per, key=lambda x: -(x[3] + x[4])):
        print(f"{c:<6}{nb:>7}{ok:>8}{low:>8}{none:>9}")
    t = stat["band"]
    print(f"--- 合计 捆行带 {t}: 够/可救 {stat['ok']} ({100*stat['ok']/t:.0f}%), "
          f"线不足 {stat['low']} ({100*stat['low']/t:.0f}%), "
          f"带内无候选 {stat['none']} ({100*stat['none']/t:.0f}%)   "
          f"[阈值 {TH}, 低分候选下限 {LO}]")


if __name__ == "__main__":
    main()
