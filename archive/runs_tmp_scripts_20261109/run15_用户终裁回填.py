# -*- coding: utf-8 -*-
"""run15:用户终裁 28 格回填第三表(2026-11-09 验收页裁定_结果.json)。幂等版。

- 24 sug:采纳建议值(页面半角标点→规范化全角,内容不变;码点显式转换)
- 4 custom(1019_19/64/66/68):用户亲核前缀字=火+乚=「煤」俗写,推翻助手
  「灺」判读——入表「煤:无芯。」(补纸面句号,note 存用户原文)
- 1019_59 特判:xnorm 剔标点会吞掉句号差异,强制写值「无芯。」
- 无条目 18 格新增:置空 2(1017_83/1032_104,置空=true)/写值 3
  (1020_118/119、1029_43)/维持 13(protect=1)
- 种子现值一律锚种子表值(SEED_DIR,重建不动点,run13 教训)
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
BASE = ROOT / "runs/autoresearch_align/多源定级_20261106"
TBL = BASE / "判读_采纳_分裂_20261109.json"
USR = Path(r"D:\Skye\Downloads\裁定_结果.json")

sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

# 半角→全角:码点显式(肉眼写全角字符易键值颠倒,run15 首版教训)
_PUNC = {0x2C: 0xFF0C, 0x3A: 0xFF1A, 0x3B: 0xFF1B, 0x21: 0xFF01,
         0x3F: 0xFF1F, 0x28: 0xFF08, 0x29: 0xFF09}


def punct(s):
    return str(s).translate(_PUNC)


usr = {x["tag"]: x for x in json.loads(USR.read_text(encoding="utf-8"))["items"]}
tbl = json.loads(TBL.read_text(encoding="utf-8"))
idx = {e["tag"]: e for e in tbl}

cache = {}


def seed_val(stem0, r):
    stem = "钻孔柱状图" + stem0
    if stem not in cache:
        p = paths.AUTORESEARCH_SEED_DIR / f"{stem}_整合.xlsx"
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        from src.handwriting import rules as R
        dcol = R.resolve_roles(rows[0]).get("desc")
        cache[stem] = (rows, dcol)
    rows, dcol = cache[stem]
    row = rows[int(r) - 1]
    return str(row[dcol] if dcol < len(row) else "")


CUSTOM_FIX = {"1019_行19", "1019_行64", "1019_行66", "1019_行68"}
FORCE_WRITE = {"1019_行59": "无芯。"}   # xnorm 剔标点吞句号差异,强制写值

stats = {"更新": 0, "新增置空": 0, "新增写值": 0, "新增维持": 0, "不动": 0}
for tag, item in usr.items():
    stem0, r = tag.split("_行")
    seedv = seed_val(stem0, int(r))
    choice, raw = item["裁定"], str(item.get("值", ""))
    note_add = "用户终裁(2026-11-09 验收页)"
    if tag in CUSTOM_FIX:
        val, extra = ("煤" + chr(0xFF1A) + "无芯。",
                      f";用户原文={raw!r};用户亲核前缀=火+乚(煤俗写),推翻助手灺判读")
    elif choice == "sug" and raw == "":
        val, extra = "", "(图签不识别,置空)"
    elif tag in FORCE_WRITE:
        val, extra = FORCE_WRITE[tag], ";用户裁定补句号(纸面句号清晰)"
    else:
        pv = punct(raw)
        val, extra = pv, (";标点规范化全角" if pv != raw else "")

    e = idx.get(tag)
    if e is None:
        base = {"tag": tag, "种子现值": seedv, "新值": "",
                "判读现值": seedv, "protect": 0, "note": note_add + extra}
        if val == "" and choice == "sug":
            base["置空"] = True
            stats["新增置空"] += 1
        elif val == "":
            base["protect"] = 1
            stats["新增维持"] += 1
        else:
            base["新值"] = val
            stats["新增写值"] += 1
        tbl.append(base)
        idx[tag] = base
        continue

    # 已有条目(含上一轮已新增格):幂等更新
    if (e.get("protect") and not e.get("新值") and not e.get("置空")
            and tag not in FORCE_WRITE and _xn(val) == _xn(seedv)):
        stats["不动"] += 1
        continue
    if note_add not in str(e.get("note", "")):
        e["note"] = str(e.get("note", "")) + ";" + note_add + extra
    if e.get("protect"):
        e["protect"] = 0
    if e.get("置空"):
        e.pop("置空") if (val or tag not in {"1017_行83", "1032_行104"}) else None
        if val == "" and tag in {"1017_行83", "1032_行104"}:
            e["置空"] = True
    cur = str(e.get("新值", "") or "")
    if val and val != cur:                      # 字符级覆盖(xnorm 会吞标点差异)
        e["新值"] = val
    elif not val and choice == "sug" and not e.get("置空"):
        e["新值"] = ""
        e["置空"] = True
    chain = [x for x in str(e.get("判读现值", "")).split("|") if x]
    for x in [seedv]:
        if x and x not in chain and _xn(x) != _xn(val):
            chain.append(x)
    e["判读现值"] = "|".join(chain)
    stats["更新"] += 1

TBL.write_text(json.dumps(tbl, ensure_ascii=False, indent=1), encoding="utf-8")
print("统计:", stats, "总条目", len(tbl))

miss = []
for e in tbl:
    s0, rr = e["tag"].split("_行")
    sv = seed_val(s0, int(rr))
    chain = ([str(e.get("种子现值", "")), str(e.get("新值", ""))]
             + str(e.get("判读现值", "")).split("|"))
    if _xn(sv) not in (_xn(x) for x in chain if x):
        miss.append(e["tag"])
print("种子表值不在守卫链:", len(miss), miss[:10])

bad_half = []
for tag in usr:
    e = idx[tag]
    v = str(e.get("新值", ""))
    if any(ord(ch) in (0x2C, 0x3A) for ch in v):
        bad_half.append(tag)
print("新值残留半角标点:", bad_half, "(期望空)")
for tag in ["1019_行59", "1020_行173", "1020_行118", "1029_行43"]:
    e = idx[tag]
    print(tag, "| protect=", e.get("protect"), "| 置空=", e.get("置空", False),
          "| 新值=", str(e.get("新值", ""))[:42])
