# -*- coding: utf-8 -*-
"""变体实验分析(2026-11-03):按变体出决策表。
dip坏格=纯数值率(越高越好);dip对照=保持v0读数率;
desc坏格=与Agnes读数字符重合率(去标点)≥0.6 计恢复(带级空/残两档);
desc对照=与v0读数重合率≥0.92 计保持。
"""
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

PUN = re.compile(r"[°。，,、．\.\s;；:：()（）\n]+")
NUMRE = re.compile(r"^-?\d+(\.\d+)?°?$")


def norm(s):
    return PUN.sub("", str(s or ""))


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def main():
    d = json.loads((paths.RUNS_DIR / "tmp" / "diag_variant_ocr.json").read_text(encoding="utf-8"))
    variants = [v for v in d["variants"] if v != "v0"]
    cells = d["cells"]
    kinds = ("dip坏", "desc坏带空", "desc坏带残", "desc对照", "dip对照")
    stat = {k: [] for k in kinds}
    for c in cells:
        v0 = str(c["读"].get("v0") or "")
        k = c.get("k")
        if c["type"] == "bad":
            if k == "dip":
                stat["dip坏"].append(c)
            elif len(v0) <= 2:
                stat["desc坏带空"].append(c)
            else:
                stat["desc坏带残"].append(c)
        else:
            stat[f"{k}对照"].append(c)
    hdr = "变体      " + "".join(f"{k:>12}" for k in kinds)
    print(hdr + "   (ok/tot)")
    best = {}
    for v in variants:
        row = []
        for kind in kinds:
            ok = tot = 0
            for c in stat[kind]:
                r0, rv = str(c["读"].get("v0") or ""), str(c["读"].get(v) or "")
                if kind == "dip坏":
                    good = bool(rv) and bool(NUMRE.match(rv))
                elif kind in ("desc坏带空", "desc坏带残"):
                    good = sim(rv, c.get("agnes")) >= 0.6
                else:
                    good = sim(rv, r0) >= 0.92
                tot += 1
                ok += bool(good)
            row.append(f"{ok}/{tot}")
            best.setdefault(kind, []).append((ok, tot, v))
        print(f"{v:>10}" + "".join(f"{r:>12}" for r in row))
    print("\n各档最优变体:")
    for kind, lst in best.items():
        lst.sort(key=lambda t: -t[0])
        print(f"  {kind}: " + ", ".join(f"{v}={ok}/{tot}" for ok, tot, v in lst[:3]))


if __name__ == "__main__":
    main()
