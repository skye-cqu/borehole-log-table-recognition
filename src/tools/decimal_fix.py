# -*- coding: utf-8 -*-
"""小数点伪差修复:RapidOCR 丢小数点/前导"0."的待审格,当 Agnes 读数与草案
数字序列全同(仅差小数点)且列值域容许时,采纳带小数点一侧并落账待核清单与终版 xlsx。

判据(四重,额度实测: python src/tools/audit4_pack.py B 段,458 格中 49 格成立):
1. 草案与 Agnes 读均为纯数字串(仅空格/小数点/度百分号);
2. 去非数字、去前导零后两序列全同(小数点永不忽略——采纳值显式带点);
3. 采纳值每个 token 落在该图该列可信(未标记)数值池 [min-0.05, max+0.05];
4. 采纳串中每个不带点的 token 必须在草案空格分词中原样出现(剔除
   "050"→"0 50"类 Agnes 也未读净的歧义格)。
落账:处置="多引擎一致(小数点伪差修复)",采纳值写入 xlsx,修复清单留档
runs/table_reconstruct/伪差修复清单.json。

用法: python src/tools/decimal_fix.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from openpyxl import load_workbook  # noqa: E402

STEMS4 = ["钻孔柱状图1018", "钻孔柱状图1030", "钻孔柱状图1032", "钻孔柱状图1042"]
RUNS = PROJECT_ROOT / "runs" / "table_reconstruct"
TOL = 0.05


def num_toks(s):
    t = str(s if s is not None else "").strip()
    if not t or t == "None" or not re.fullmatch(r"[0-9 .,。°%]+", t):
        return None
    out = []
    for tok in re.split(r"\s+", re.sub(r"[,。°%]", "", t)):
        if not tok:
            continue
        try:
            out.append(float(tok))
        except ValueError:
            return None
    return out or None


def digseq(s):
    d = re.sub(r"\D", "", str(s or ""))
    return d.lstrip("0") or "0"


def fix_chart(stem):
    flags = json.loads((RUNS / f"{stem}_待核清单.json").read_text(encoding="utf-8"))
    xlsx = RUNS / f"{stem}_还原_补产终版.xlsx"
    ws = load_workbook(xlsx).active
    rows = list(ws.iter_rows(values_only=True))
    header, table = list(rows[0]), [list(r) for r in rows[1:]]
    disp = {(f["层"], f["列"]) for f in flags}
    pools = {}
    for j, name in enumerate(header):
        vals = []
        for li, r in enumerate(table, 1):
            if (li, name) in disp:
                continue
            vals += num_toks(r[j]) or []
        pools[name] = (min(vals), max(vals)) if vals else None

    fixed = []
    for f in flags:
        if not str(f["处置"]).startswith("待人审"):
            continue
        if num_toks(f.get("草案")) is None:
            continue
        pool = pools.get(f["列"])
        if pool is None:
            continue
        draft_toks = re.split(r"\s+", str(f.get("草案")).strip())
        for key in ("agnes单格", "agnes条"):
            cnum = num_toks(f.get(key))
            if cnum is None or digseq(f.get("草案")) != digseq(f.get(key)):
                continue
            toks = re.split(r"\s+", str(f.get(key)).strip())
            if not any("." in t for t in toks):
                continue  # 采纳侧须带小数点(伪差修复方向)
            if not all(pool[0] - TOL <= v <= pool[1] + TOL for v in cnum):
                break  # 值域外,弃判
            if any("." not in t and t not in draft_toks for t in toks):
                continue  # 守卫4:采纳串仍有草案没有的无点 token → 歧义
            val = cnum[0] if len(cnum) == 1 else " ".join(toks)
            j = header.index(f["列"])
            table[f["层"] - 1][j] = val
            f["处置"] = "多引擎一致(小数点伪差修复)"
            f["采纳值"] = str(val)
            f["依据"] = f"{key}读数数字序列与草案全同,仅补小数点;列值域内"
            fixed.append({"层": f["层"], "列": f["列"], "原值": f.get("草案"),
                          "采纳": str(val), "来源": key})
            break

    ws2 = load_workbook(xlsx).active
    for rec in fixed:
        ws2.cell(row=rec["层"] + 1,
                 column=header.index(rec["列"]) + 1).value = \
            float(rec["采纳"]) if re.fullmatch(r"-?\d+(\.\d+)?", rec["采纳"]) \
            else rec["采纳"]
    ws2.parent.save(xlsx)
    (RUNS / f"{stem}_待核清单.json").write_text(
        json.dumps(flags, ensure_ascii=False, indent=1), encoding="utf-8")
    pend = sum(1 for f in flags if f["处置"] == "待人审")
    print(f"{stem}: 伪差修复 {len(fixed)} 格,剩余待人审 {pend}")
    return fixed


def main():
    all_fixed = {}
    for stem in STEMS4:
        all_fixed[stem] = fix_chart(stem)
    (RUNS / "伪差修复清单.json").write_text(
        json.dumps(all_fixed, ensure_ascii=False, indent=1), encoding="utf-8")
    print("清单 → runs/table_reconstruct/伪差修复清单.json")


if __name__ == "__main__":
    main()
