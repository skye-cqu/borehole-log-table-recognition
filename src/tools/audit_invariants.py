# -*- coding: utf-8 -*-
"""领域公理门禁 v2(2026-10-05)。v1 实测后升级:1023 原图表头语义本身对调
(层厚列印累计深度、深度列印层厚,1:1 裁片实拍),故先按**值角色**定列再判公理:
  角色检测: 累计列 = 数值占比高且近严格递增的保留数值列(递增率>0.98);
           层厚列 = 对累计列逐对差中位误差最小的其余数值列。
  H登记: 角色↔表头名错配 = 原图笔误/特殊约定,单独立"登记"不判违反(1032 笔误登记先例)。
  I1 深度单调: 累计角色列相邻行须递增;
  I2 层厚=Δ深度: |层厚角色值 − Δ累计角色值| ≤ tol,H0(相邻差)全局中位误差实测=0.0000,
     tol = max(0.05, med+6×1.4826×MAD);
  I3 层号: 煤层标志层号数值列非递增即违反(diff 间隔分布另报)。
  I4 仅测量: 真厚≈层厚×cos(倾角) 一致率。
  I5 巨带: 相邻行界带高 >2.5×全表中位 = 疑并层——jumble 字符串('408.16 413.78 434.23')
     使 I1/I2 静默跳过(非数值不进算术),带高尺不依赖单元格内容,补此洞(1020/1031/1033/1037 实证)。
用法: python src/tools/audit_invariants.py [xlsx目录] [--strict](I1/I2 有违反退出码1)"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402

NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
NUMCOLS = {"深度", "层厚", "采长", "倾角", "真厚"}
OUT_CSV = paths.RUNS_DIR / "tmp" / "公理违反_20261005.csv"
OUT_JSON = paths.RUNS_DIR / "tmp" / "公理门禁实测_20261005.json"


def _num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str) and NUM_RE.match(v.strip()):
        return float(v.strip())
    return None


def _roles(vals, hdr):
    """(累计列号, 层厚列号, 登记说明)。数据驱动:递增率>0.98 的数值列=累计列;
    其余数值列对 Δ累计 中位误差最小者=层厚列。找不到累计列返回 (None, None, 说明)。"""
    cands = [i for i, n in enumerate(hdr) if n in NUMCOLS]
    seqs = {}
    for i in cands:
        seq = [(j, _num(vals[j][i])) for j in range(1, len(vals))]
        seq = [v for _, v in seq if v is not None]
        if len(seq) >= 10:
            seqs[i] = seq
    depth_i = None
    for i, seq in seqs.items():
        inc = sum(1 for k in range(1, len(seq)) if seq[k] > seq[k - 1])
        if inc / (len(seq) - 1) > 0.98 and (depth_i is None or len(seq) > len(seqs[depth_i])):
            depth_i = i
    if depth_i is None:
        return None, None, "无近严格递增数值列,角色检测失败"
    d = seqs[depth_i]
    best, best_err = None, None
    for i, seq in seqs.items():
        if i == depth_i:
            continue
        by_j = {j: v for j, v in ((j, _num(vals[j][i])) for j in range(1, len(vals)))
                if v is not None}
        dmap = {j: v for j, v in ((j, _num(vals[j][depth_i])) for j in range(1, len(vals)))
                if v is not None}
        errs = [abs(by_j[j] - (dmap[j] - dmap[j - 1])) for j in sorted(by_j)
                if j in dmap and j - 1 in dmap]
        e = float(np.median(errs)) if errs else 1e9
        if best_err is None or e < best_err:
            best, best_err = i, e
    note = ""
    if hdr[depth_i] != "深度" or (best is not None and hdr[best] != "层厚"):
        note = (f"原图表头语义对调: 累计列在『{hdr[depth_i]}』列位、"
                f"层厚列在『{hdr[best] if best is not None else '?'}』列位(登记,忠实原图不改)")
    return depth_i, best, note


def main():
    from openpyxl import load_workbook

    strict = "--strict" in sys.argv
    d_arg = [a for a in sys.argv[1:] if not a.startswith("--")]
    xdir = Path(d_arg[0]) if d_arg else paths.REEMIT_DIR_20261005B

    charts = {}
    for f in sorted(xdir.glob("*_还原.xlsx")):
        stem = f.name.split("钻孔柱状图")[1][:4]
        ws = load_workbook(f).active
        vals = [[c.value for c in row] for row in ws.iter_rows()]
        charts[stem] = {"vals": vals, "hdr": vals[0]}

    # 全局容差: H0 假设(层厚_j = 累计_j − 累计_{j-1})的误差分布
    all_err = []
    for c in charts.values():
        di, ti, _ = _roles(c["vals"], c["hdr"])
        if di is None or ti is None:
            continue
        vals, dser = c["vals"], [(j, _num(c["vals"][j][di])) for j in range(1, len(c["vals"]))]
        dmap = {j: v for j, v in dser if v is not None}
        for j in range(2, len(vals)):
            t = _num(vals[j][ti])
            if j in dmap and j - 1 in dmap and t is not None:
                all_err.append(abs(t - (dmap[j] - dmap[j - 1])))
    med = float(np.median(all_err))
    mad = float(np.median(np.abs(np.asarray(all_err) - med)))
    tol = max(0.05, med + 6 * 1.4826 * mad)

    violations, notes, report = [], [], {}
    for s, c in sorted(charts.items()):
        vals, hdr = c["vals"], c["hdr"]
        zi = hdr.index("煤层标志层号") if "煤层标志层号" in hdr else None
        gi = hdr.index("倾角") if "倾角" in hdr else None
        ri = hdr.index("真厚") if "真厚" in hdr else None
        ti = hdr.index("层厚") if "层厚" in hdr else None
        di, t_role, note = _roles(vals, hdr)
        if note:
            notes.append([s, note])
        i1 = i2 = i3 = i4_ok = i4_n = 0
        if di is not None and t_role is not None:
            dmap = {j: v for j, v in ((j, _num(vals[j][di])) for j in range(1, len(vals)))
                    if v is not None}
            for j in range(2, len(vals)):
                d0, d1 = dmap.get(j - 1), dmap.get(j)
                t = _num(vals[j][t_role])
                if d0 is not None and d1 is not None:
                    if d1 <= d0:
                        i1 += 1
                        violations.append([s, j + 1, "I1累计深度单调", f"{d0}→{d1}"])
                    if t is not None and abs(t - (d1 - d0)) > tol:
                        i2 += 1
                        violations.append([s, j + 1, "I2层厚=Δ深度",
                                           f"层厚{t} Δ={round(d1-d0,3)}"])
        zd = [(j + 1, _num(vals[j][zi])) for j in range(1, len(vals))
              if zi is not None and _num(vals[j][zi]) is not None]
        for k in range(1, len(zd)):
            if zd[k][1] - zd[k - 1][1] <= 0:
                i3 += 1
                violations.append([s, zd[k][0], "I3层号连续", f"{zd[k-1][1]}→{zd[k][1]}"])
        if gi is not None and ri is not None and t_role is not None:
            for j in range(1, len(vals)):
                r, t, g = _num(vals[j][ri]), _num(vals[j][t_role]), _num(vals[j][gi])
                if None not in (r, t, g) and t > 0 and 0 <= g <= 90:
                    i4_n += 1
                    if abs(r - t * math.cos(math.radians(g))) <= max(0.05, 0.05 * t):
                        i4_ok += 1
        report[s] = {"n_rows": len(vals) - 1, "I1": i1, "I2": i2, "I3": i3,
                     "roles": f"{hdr[di] if di is not None else '?'}/{hdr[t_role] if t_role is not None else '?'}",
                     "i4": round(i4_ok / i4_n, 3) if i4_n else None, "i4_n": i4_n}

    # ---- I5 巨带(结构侧信号,不依赖单元格内容)----
    from src.table.track_rows import row_y
    for s in sorted(charts):
        fp = paths.RUNS_DIR / "table_reconstruct" / f"钻孔柱状图{s}_行判定.json"
        hp = paths.RUNS_DIR / "table_reconstruct" / f"钻孔柱状图{s}_表头映射.json"
        if not fp.exists() or not hp.exists():
            continue
        rd = json.load(open(fp, encoding="utf-8"))
        hm = json.load(open(hp, encoding="utf-8"))
        if not rd.get("rows") or not hm.get("band"):
            continue
        x_tbl = sum(rd["table_x"]) / 2
        ys = sorted(row_y(r, x_tbl) for r in rd["rows"] if row_y(r, x_tbl) >= hm["band"][1])
        if len(ys) < 4:
            continue
        med = float(np.median(np.diff(ys)))
        i5 = 0
        for a, b in zip(ys[:-1], ys[1:]):
            if b - a > 2.5 * med:
                i5 += 1
                violations.append([s, "-", "I5巨带",
                                   f"带高{b-a:.0f}px = {(b-a)/med:.1f}×中位行高,疑并层"])
        report[s]["I5"] = i5

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["图号", "xlsx行号", "公理", "详情"])
        w.writerows(violations)
    OUT_JSON.write_text(json.dumps({"tol": round(tol, 4), "per_chart": report,
                                    "notes": notes}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"tol={tol:.3f}  角色列(累计/层厚) 与 I1/I2/I3:")
    for s, r in report.items():
        flag = " ⚠" if (r["I1"] or r["I2"] > 5) else ""
        print(f"{s} {r['roles']:<8} 行{r['n_rows']:4d}  I1={r['I1']:2d} I2={r['I2']:3d} "
              f"I3={r['I3']}  i4={r['i4']}{flag}")
    for s, n in notes:
        print(f"[登记] {s}: {n}")
    print(f"合计 I1={sum(r['I1'] for r in report.values())} "
          f"I2={sum(r['I2'] for r in report.values())} "
          f"I3={sum(r['I3'] for r in report.values())} → {OUT_CSV.name}")
    if strict and any(r["I1"] or r["I2"] for r in report.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
