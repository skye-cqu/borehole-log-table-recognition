# -*- coding: utf-8 -*-
"""嫌疑带几何归因(2026-10-05): 公理违反(I1/I2)+两数同格 → 带内是否躺着 sub_rows/off_grid。
假设: 疑漏行线多被覆盖率门禁降级成 sub_rows(1040 漏线先例)。输出 CSV+汇总。"""
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402

NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
TWO_RE = re.compile(r"^\s*-?\d+(\.\d+)?\s+-?\d+(\.\d+)?\s*$")
NUMCOLS = {"深度", "层厚", "采长", "倾角", "真厚"}


def main():
    from openpyxl import load_workbook
    inv = json.load(open(paths.RUNS_DIR / "tmp" / "公理门禁实测_20261005.json",
                         encoding="utf-8"))
    bad_rows = {}          # (stem, xlsx行) -> 信号集
    for f in sorted((paths.RUNS_DIR / "tmp").glob("公理违反_20261005.csv")):
        for r in list(csv.reader(open(f, encoding="utf-8-sig")))[1:]:
            bad_rows.setdefault((r[0], int(r[1])), set()).add(r[2])
    for f in sorted(paths.REEMIT_DIR_20261005.glob("*_还原.xlsx")):
        stem = f.name.split("钻孔柱状图")[1][:4]
        ws = load_workbook(f).active
        vals = [[c.value for c in row] for row in ws.iter_rows()]
        hdr = vals[0]
        nidx = [i for i, n in enumerate(hdr) if n in NUMCOLS]
        for j in range(1, len(vals)):
            for ci in nidx:
                v = vals[j][ci]
                if isinstance(v, str) and TWO_RE.match(v):
                    bad_rows.setdefault((stem, j + 1), set()).add("两数同格")

    out = []
    stats = {"sub": 0, "off": 0, "none": 0}
    by_stem = {}
    for (stem, xr), sig in sorted(bad_rows.items()):
        rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"钻孔柱状图{stem}_行判定.json", encoding="utf-8"))
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"钻孔柱状图{stem}_表头映射.json", encoding="utf-8"))
        x_tbl = sum(rd["table_x"]) / 2
        rows_r = [r for r in rd["rows"] if row_y(r, x_tbl) >= hm["band"][1]]
        d = xr - 1
        if d < 1 or d >= len(rows_r):
            continue
        top, bot = rows_r[d - 1], rows_r[d]
        y0, y1 = row_y(top, x_tbl), row_y(bot, x_tbl)
        subs, offs = [], []
        for kind, arr in (("sub", rd.get("sub_rows") or []),
                          ("off", rd.get("off_grid") or [])):
            for q in arr:
                p = np.asarray(q["poly"], float)
                ym = float(np.interp(x_tbl, p[:, 0], p[:, 1]))
                if y0 + 3 < ym < y1 - 3:
                    (subs if kind == "sub" else offs).append(round(ym))
        stats["sub" if subs else ("off" if offs else "none")] += 1
        by_stem.setdefault(stem, [0, 0])[0 if (subs or offs) else 1] += 1
        out.append([stem, xr, "+".join(sorted(sig)), int(y0), int(y1),
                    len(subs), subs[:4], len(offs)])

    with open(paths.RUNS_DIR / "tmp" / "疑漏带归因_20261005.csv", "w",
              newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["图号", "xlsx行", "信号", "带y0", "带y1", "带内sub数", "sub y样例", "带内off数"])
        w.writerows(out)
    print(f"嫌疑带 {len(out)} 条(唯一 图×行): 带内有sub {stats['sub']}, 仅off {stats['off']}, "
          f"带内无线 {stats['none']}")
    for s, (n_hit, n_none) in sorted(by_stem.items()):
        print(f"  {s}: 有线 {n_hit} / 无线 {n_none}")


if __name__ == "__main__":
    main()
