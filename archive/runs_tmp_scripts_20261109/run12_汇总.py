# -*- coding: utf-8 -*-
"""run12 收官:尾池2(单族双几何42+无收敛7+同族5)54格汇总 → 入第三表。

hold:1017_83/1032_104(图签行)、1020_118/119(行带歧义三轮 hold)、
1029_43(行42/43 边界重叠,多数票非图证)。
1030_10:裁片 3px 塌缩,3/4 票逐字一致现值对→protect+登记结构异常。
种子现值=xlsx 全文。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
PKG = ROOT / "runs/autoresearch_align/多源定级_20261106/尾池判读包_r12"
TBL = ROOT / "runs/autoresearch_align/多源定级_20261106/判读_采纳_分裂_20261109.json"

sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

HOLD = {
    "1017_行83": "图签行(图签处置待用户)",
    "1032_行104": "图签行(图签处置待用户)",
    "1020_行118": "行带归属歧义(r8/r9/r11 三轮 hold),待结构复核",
    "1020_行119": "行带归属歧义(同上)",
    "1029_行43": "行42/43 边界重叠,r9 亲核窗空白;多数票非图证,待用户",
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


dsp = {}
for b in range(4):
    for e in json.loads((PKG / f"分派_尾池_r12_{b}.json").read_text(encoding="utf-8")):
        dsp[e["tag"]] = e["现值"]

rows = json.loads(TBL.read_text(encoding="utf-8"))
by_key = {}
for e in rows:
    stem, r = e["tag"].split("_行")
    by_key[("钻孔柱状图" + stem, int(r))] = e

from collections import Counter
stats = Counter()
write_rows, hold_rows = [], []
for b in range(4):
    res = json.loads((PKG / f"判读_结果_r12_{b}.json").read_text(encoding="utf-8"))
    for e in res:
        tag = e["tag"]
        stem0, r = tag.split("_行")
        r = int(r)
        cur = xlsx_val(stem0, r)
        text = str(e.get("text", "") or "").strip()
        v = e.get("verdict", "")
        if tag in HOLD:
            hold_rows.append({"tag": tag, "候选": cur, "agent_text": text,
                              "verdict": v, "登记": HOLD[tag]})
            stats["hold"] += 1
            continue
        key = ("钻孔柱状图" + stem0, r)
        if v == "现值对":
            old = by_key.get(key)
            note = f"r12尾池2判读现值对(conf {e.get('conf', '中')})"
            if old is not None:
                old["protect"] = 1
                old["来源"] = old.get("来源", "") + "|r12护"
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 1, "新值": "",
                                   "种子现值": cur, "判读现值": "", "来源": "r12",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["protect"] += 1
        else:
            if not text:
                hold_rows.append({"tag": tag, "候选": cur, "agent_text": "",
                                  "verdict": v, "登记": "都不对但无text"})
                stats["hold"] += 1
                continue
            old = by_key.get(key)
            note = (f"r12尾池2判读翻案:现值误,text=纸面忠实转写"
                    f"(conf {e.get('conf', '中')};{e.get('type', '')})")
            if old is not None:
                inh = [str(old.get("种子现值", ""))] + \
                      [x for x in str(old.get("判读现值", "")).split("|") if x]
                old["protect"] = 0
                old["新值"] = text
                old["判读现值"] = "|".join([x for x in [cur] + inh if x and x != text])
                old["来源"] = old.get("来源", "") + "|r12翻"
                old["note"] = note
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 0, "新值": text,
                                   "种子现值": cur, "判读现值": "", "来源": "r12",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["write"] += 1

rows.extend(write_rows)
TBL.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
hp = ROOT / "runs/autoresearch_align/多源定级_20261106/尾池2_r12_待用户.json"
hp.write_text(json.dumps(hold_rows, ensure_ascii=False, indent=1), encoding="utf-8")
# 结构异常登记追加(1030_10 行框塌缩)
abn = ROOT / "runs/autoresearch_align/多源定级_20261106/结构异常登记_r10.json"
lst = json.loads(abn.read_text(encoding="utf-8")) if abn.exists() else []
lst.append({"tag": "1030_行10", "问题": "行框塌缩:cell 仅 3px 高/strip 13px,文字压带状不可辨",
            "处置": "3/4 引擎票逐字一致+判读低conf放行 protect;行多边形来源待结构侧排查"})
abn.write_text(json.dumps(lst, ensure_ascii=False, indent=1), encoding="utf-8")
print("统计:", dict(stats))
print(f"第三表 -> {len(rows)} 条(新增 {len(write_rows)})")
chk = json.loads(TBL.read_text(encoding="utf-8"))
assert len(chk) == len(rows)
print("回读校验通过; hold ->", hp.name)
