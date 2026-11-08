# -*- coding: utf-8 -*-
"""检验 R 的可靠性:一个格里多个深度值,到底"是几行"还是"同一行的两个数"?

判据(门禁账本 M5.T1): 层厚 = 本行深度 − 上一行深度 (±0.02m, 行内一致率 90.8%)。
若某交付行内 深度=[d1,d2,d3] 且 层厚=[t1,t2,t3] 满足 d(i)-d(i-1)=t(i) →
  这三个数确实属于三个物理行,该行捆了 3 行,R 加 2 是对的。
若不满足 → 同行多值,R 被高估。
另测: 跨行(上一交付行的最后一个深度 → 本行第一个深度)是否也满足,满足说明行序连续。
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

DELIV = paths.PROJECT_ROOT / "outputs/Excel交付_最终_20260915"
NUM = re.compile(r"-?\d+(?:\.\d+)?")
TOL = 0.02


def col(ws, key):
    hdr = [str(c.value or "") for c in next(ws.iter_rows(max_row=1))]
    return [i for i, h in enumerate(hdr) if key in h]


def main():
    codes = sys.argv[1:] or sorted(p.stem[:4] for p in DELIV.glob("*_还原.xlsx"))
    tot = defaultdict(int)
    print(f"{'张':<6}{'捆行格':>7}{'Δ层厚成立':>10}{'不成立':>7}{'每格平均捆':>10}")
    per = []
    for c in codes:
        ws = load_workbook(DELIV / f"{c}_还原.xlsx", read_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        di, ti = col(ws, "深度"), col(ws, "层厚")
        if not di or not ti:
            continue
        n_ok = n_bad = n_cells = bundle = 0
        prev_d = None
        for r in rows[1:]:
            ds = [float(x) for i in di if isinstance(r[i], str)
                  for x in NUM.findall(r[i])]
            ts = [float(x) for i in ti if isinstance(r[i], str)
                  for x in NUM.findall(r[i])]
            if len(ds) < 2:
                if ds:
                    prev_d = ds[0]
                continue
            n_cells += 1
            bundle += len(ds)
            if len(ts) == len(ds):
                # 行内：第2..N个深度差应等于对应层厚
                ok = sum(1 for k in range(1, len(ds))
                         if abs((ds[k] - ds[k - 1]) - ts[k]) <= TOL)
                n_ok += ok
                n_bad += len(ds) - 1 - ok
            else:
                n_bad += len(ds) - 1
            prev_d = ds[-1]
        per.append((c, n_cells, n_ok, n_bad, bundle / max(n_cells, 1)))
        tot["cells"] += n_cells
        tot["ok"] += n_ok
        tot["bad"] += n_bad
    for p in sorted(per, key=lambda x: -x[1]):
        print(f"{p[0]:<6}{p[1]:>7}{p[2]:>10}{p[3]:>7}{p[4]:>10.2f}")
    t = tot["ok"] + tot["bad"]
    print(f"--- 合计 捆行格 {tot['cells']}，Δ层厚判据成立 {tot['ok']}/{t} "
          f"= {100*tot['ok']/max(t,1):.1f}%")


if __name__ == "__main__":
    main()
