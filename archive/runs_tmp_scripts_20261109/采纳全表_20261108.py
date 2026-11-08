# -*- coding: utf-8 -*-
"""寻址验证 + 生成规则引擎采纳全表(98 格,v2)。

语义修正(2026-11-08): 定级的"现值"=候选表值(种子+旧规则)。故:
- A 类(现值对,种子==候选==纸面) 30 格: protect=true,规则不动,禁参考门改写;
- B 类(现值对,种子≠候选,旧规则所采=纸面) 2 格(1024/87、1026/34):
  protect=false 且不采纳——判读实锤旧规则采对,照常由旧规则重建;
- C 类(众读对 13+都不对 53): protect=true+采纳,守卫接受 种子现值 或 现值。
产出: 多源定级_20261106/判读_采纳全表_20261108.json
"""
import json, sys
sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
from src.core import paths
from src.handwriting.normalizers import norm_desc
from src.handwriting import rules as R
from openpyxl import load_workbook

BASE = paths.AUTORESEARCH_DIR / "多源定级_20261106"
OVERRIDE = {"1035_行68": "煤判层", "1041_行49": "煤判层"}
SRC_OVERRIDE = "次读+行带读(引擎读;众读缺'煤'前缀)"

res, disp = {}, {}
for i in range(8):
    for d in json.loads((BASE / f"判读_分派_{i}.json").read_text(encoding="utf-8")):
        disp[d["tag"]] = d
    for r in json.loads((BASE / f"判读_结果_{i}.json").read_text(encoding="utf-8")):
        res[r["tag"]] = r
assert set(res) == set(disp) and len(res) == 98

seed_vals = {}
for p in sorted(paths.AUTORESEARCH_SEED_DIR.glob("*_整合.xlsx")):
    rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
    dcol = R.resolve_roles(rows[0]).get("desc")
    seed_vals[p.stem.replace("_整合", "")] = {
        i + 2: ("" if v is None else str(v)) for i, v in
        [(i, rows[i + 1][dcol]) for i in range(len(rows) - 1)]}

bad, table = [], []
for tag in sorted(res):
    r, d = res[tag], disp[tag]
    stem, row_s = tag.split("_行")
    row = int(row_s)
    seed_v = seed_vals.get("钻孔柱状图" + stem, {}).get(row)
    if seed_v is None:
        bad.append((tag, "种子无此行/无此图"))
        continue
    addr_ok = norm_desc(seed_v) == norm_desc(d["现值"])
    if r["verdict"] == "现值对":
        if addr_ok:
            table.append({"tag": tag, "组": "A", "protect": True, "新值": None,
                          "种子现值": seed_v, "判读现值": d["现值"],
                          "来源": "判读·维持现值(禁参考门改写)", "conf": r["conf"]})
        else:  # B 类:候选值才是被判读确认的,种子是旧值
            table.append({"tag": tag, "组": "B", "protect": False, "新值": None,
                          "种子现值": seed_v, "判读现值": d["现值"],
                          "来源": "判读确认旧规则所采=纸面,照常重建", "conf": r["conf"]})
        continue
    if not addr_ok and norm_desc(seed_v) == norm_desc(r.get("text", "")):
        pass  # C 类种子恰与转写同文亦可(守卫双accept)
    elif not addr_ok:
        # C 类但种子与判读现值都不匹配→只可能是候选被旧规则改过,登记种子值供守卫
        pass
    if r["verdict"] == "众读对":
        new = OVERRIDE.get(tag, d["众读"])
        src = "众读(引擎读)" if tag not in OVERRIDE else SRC_OVERRIDE
    else:
        new, src = r["text"], "纸面转写(助手弱档·用户授权流程)"
    table.append({"tag": tag, "组": "C", "protect": True, "新值": new,
                  "种子现值": seed_v, "判读现值": d["现值"],
                  "来源": src, "conf": r["conf"]})

print(f"98 格寻址: 失败 {len(bad)}")
for t, why in bad:
    print("  FAIL", t, why)
grp = {}
for e in table:
    grp[e["组"]] = grp.get(e["组"], 0) + 1
out = BASE / "判读_采纳全表_20261108.json"
out.write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"采纳全表 {len(table)} 格 组分布 {grp} -> {out.name}")
