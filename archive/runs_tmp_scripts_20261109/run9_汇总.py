# -*- coding: utf-8 -*-
"""run9 收官:同族多数池 94 格判读汇总 → 入第三表。

run8b 教训落地:种子现值直接取 xlsx 全文(不用分派现值)。
hold:1020_118/119(行带归属歧义,r8 已登记)、1029_43(行42/43 边界重叠,
主会话亲核窗全空白,现值"岩性向上"串行嫌疑)、1032_104(图签行)、
1019_19(前缀"灿:"无窗内依据,与 64/66/68 同款存疑)。
"""
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
PKG = ROOT / "runs/autoresearch_align/多源定级_20261106/同族判读包_r9"
TBL = ROOT / "runs/autoresearch_align/多源定级_20261106/判读_采纳_分裂_20261109.json"

sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

HOLD = {
    "1020_行118": "行带归属歧义(r8 已登记),119 分行待结构复核",
    "1020_行119": "行带归属歧义(r8 已登记),118 分行待结构复核",
    "1029_行43": "主会话亲核:行带窗全空白,现值'岩性向上'非短判层语且非纸面;"
                 "行42/43 折线边界重叠,字归属待结构复核",
    "1032_行104": "图签行(r8 已登记),图签处置待用户",
    "1019_行19": "前缀'灿:'窗内无字形依据(与 64/66/68 同款),留用户终裁",
}

xlsx_cache = {}


def xlsx_val(stem0, r):
    stem = "钻孔柱状图" + stem0
    if stem not in xlsx_cache:
        p = paths.AUTORESEARCH_CANDIDATE_DIR / f"{stem}_整合.xlsx"
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        xlsx_cache[stem] = (rows, dcol)
    rows, dcol = xlsx_cache[stem]
    return str(rows[r - 1][dcol] if dcol < len(rows[r - 1]) else "")


rows = json.loads(TBL.read_text(encoding="utf-8"))
by_key = {}
for e in rows:
    stem, r = e["tag"].split("_行")
    by_key[("钻孔柱状图" + stem, int(r))] = e

stats = {"现值对": 0, "写值": 0, "hold": 0, "dup": 0, "兜底改判": 0}
write_rows, hold_rows = [], []
for b in range(7):
    res = json.loads((PKG / f"判读_结果_r9_{b}.json").read_text(encoding="utf-8"))
    for e in res:
        tag = e["tag"]
        stem0, r = tag.split("_行")
        cur = xlsx_val(stem0, int(r))
        text = str(e.get("text", "") or "").strip()
        v = e.get("verdict", "")
        if v == "现值对" and text and _xn(text) != _xn(cur) \
                and SequenceMatcher(None, _xn(text), _xn(cur)).ratio() < 0.85:
            v = "都不对"
            stats["兜底改判"] += 1
        if tag in HOLD:
            hold_rows.append({"tag": tag, "现值": cur, "agent_text": text,
                              "verdict": v, "登记": HOLD[tag]})
            stats["hold"] += 1
            continue
        key = ("钻孔柱状图" + stem0, int(r))
        if v == "现值对":
            old = by_key.get(key)
            note = f"r9同族池判读现值对(conf {e.get('conf', '中')})"
            if old is not None:
                old["protect"] = 1
                old["来源"] = old.get("来源", "") + "|r9护"
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 1, "新值": "",
                                   "种子现值": cur, "判读现值": "", "来源": "r9",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["现值对"] += 1
        else:
            if not text:
                hold_rows.append({"tag": tag, "现值": cur, "agent_text": "",
                                  "verdict": v, "登记": "都不对但无text"})
                stats["hold"] += 1
                continue
            old = by_key.get(key)
            note = (f"r9同族池判读翻案:现值误,text=纸面忠实转写"
                    f"(conf {e.get('conf', '中')};{e.get('type', '')})")
            if old is not None:
                inh = [str(old.get("种子现值", ""))] + \
                      [x for x in str(old.get("判读现值", "")).split("|") if x]
                old["protect"] = 0
                old["新值"] = text
                old["判读现值"] = "|".join([x for x in [cur] + inh if x and x != text])
                old["来源"] = old.get("来源", "") + "|r9翻"
                old["note"] = note
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 0, "新值": text,
                                   "种子现值": cur, "判读现值": "", "来源": "r9",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["写值"] += 1

rows.extend(write_rows)
TBL.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
hp = ROOT / "runs/autoresearch_align/多源定级_20261106/同族池_r9_待用户.json"
hp.write_text(json.dumps(hold_rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("统计:", stats)
print(f"第三表 -> {len(rows)} 条(新增 {len(write_rows)})")
chk = json.loads(TBL.read_text(encoding="utf-8"))
assert len(chk) == len(rows)
bad = [e for e in chk if not e.get("tag") or "_行" not in e["tag"]]
assert not bad, bad
print("回读校验通过; 待用户登记 ->", hp.name)
