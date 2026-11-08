# -*- coding: utf-8 -*-
"""run11 收官:血统分叉未判读 323 格汇总 → 入第三表。

三向比对:候选表值(xlsx)/deliv(交付包)/cmp(对比包)。
- deliv对:纸面=deliv。候选若=deliv→protect 定谳;否则写值(deliv 全文)。
- cmp对:纸面=cmp→写值(cmp 全文)。
- 都不对:写值(agent text)。
主会话修正:1018_123(皮,agent 误及)→cmp对;1035_129/160(半富先例)→deliv对;
1020_118/119(行带歧义)保持 hold 不入表。
种子现值=xlsx 候选全文(run8b 教训);判读现值链记 deliv/cmp 两说。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
PKG = ROOT / "runs/autoresearch_align/多源定级_20261106/血统分叉判读包_r11"
TBL = ROOT / "runs/autoresearch_align/多源定级_20261106/判读_采纳_分裂_20261109.json"

sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

FIX = {  # 主会话终裁修正
    "1018_行123": ("cmp对", None),
    "1035_行129": ("deliv对", None),
    "1035_行160": ("deliv对", None),
}
HOLD = {"1020_行118", "1020_行119"}

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
for b in range(22):
    for e in json.loads((PKG / f"分派_血统_r11_{b}.json").read_text(encoding="utf-8")):
        dsp[e["tag"]] = e

rows = json.loads(TBL.read_text(encoding="utf-8"))
by_key = {}
for e in rows:
    stem, r = e["tag"].split("_行")
    by_key[("钻孔柱状图" + stem, int(r))] = e

from collections import Counter
stats = Counter()
write_rows = []
hold_rows = []
for b in range(22):
    res = json.loads((PKG / f"判读_结果_r11_{b}.json").read_text(encoding="utf-8"))
    for e in res:
        tag = e["tag"]
        d = dsp[tag]
        stem0, r = tag.split("_行")
        r = int(r)
        cur = xlsx_val(stem0, r)
        deliv, cmp = d["deliv"], d["cmp"]
        v = e.get("verdict", "")
        text = str(e.get("text", "") or "").strip()
        if tag in FIX:
            v = FIX[tag][0]
        if tag in HOLD:
            hold_rows.append({"tag": tag, "候选": cur, "deliv": deliv, "cmp": cmp,
                              "agent": e, "登记": "行带归属歧义(r8 已登记),待结构复核"})
            stats["hold"] += 1
            continue
        key = ("钻孔柱状图" + stem0, r)
        note = f"r11血统分叉判读({v},conf {e.get('conf', '中')})"
        chain = "|".join([x for x in [deliv, cmp] if x])
        if v == "deliv对":
            if _xn(cur) == _xn(deliv):
                old = by_key.get(key)
                if old is not None:
                    old["protect"] = 1
                    old["来源"] = old.get("来源", "") + "|r11护"
                    stats["protect_dup"] += 1
                else:
                    write_rows.append({"tag": tag, "组S": "", "protect": 1, "新值": "",
                                       "种子现值": cur, "判读现值": chain, "来源": "r11",
                                       "conf": e.get("conf", "中"), "note": note})
                stats["deliv_protect"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 0, "新值": deliv,
                                   "种子现值": cur, "判读现值": chain, "来源": "r11",
                                   "conf": e.get("conf", "中"), "note": note})
                stats["deliv_write"] += 1
        elif v == "cmp对":
            write_rows.append({"tag": tag, "组S": "", "protect": 0, "新值": cmp,
                               "种子现值": cur, "判读现值": chain, "来源": "r11",
                               "conf": e.get("conf", "中"), "note": note})
            stats["cmp_write"] += 1
        else:
            if not text:
                hold_rows.append({"tag": tag, "候选": cur, "deliv": deliv, "cmp": cmp,
                                  "agent": e, "登记": "都不对但无text"})
                stats["hold"] += 1
                continue
            write_rows.append({"tag": tag, "组S": "", "protect": 0, "新值": text,
                               "种子现值": cur, "判读现值": chain, "来源": "r11",
                               "conf": e.get("conf", "中"), "note": note})
            stats["neither_write"] += 1

rows.extend(write_rows)
TBL.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
hp = ROOT / "runs/autoresearch_align/多源定级_20261106/血统分叉_r11_待用户.json"
hp.write_text(json.dumps(hold_rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("统计:", dict(stats))
print(f"第三表 -> {len(rows)} 条(新增 {len(write_rows)})")
chk = json.loads(TBL.read_text(encoding="utf-8"))
assert len(chk) == len(rows)
bad = [e for e in chk if not e.get("tag") or "_行" not in e["tag"]]
assert not bad
print("回读校验通过; hold ->", hp.name)
