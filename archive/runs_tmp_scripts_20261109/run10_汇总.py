# -*- coding: utf-8 -*-
"""run10 收官:尾池(读数不足 46+读截断 8)判读汇总 → 入第三表。

主会话终裁覆盖(agent 判定被大窗亲核推翻/升信):
- 1019_19:批0 判现值对(前缀"灿"),大窗实证纸面"灺:无芯。"→写值
- 1019_62/80/86:批0 判都不对(前缀无依据),大窗实证"灺:"在列内→写值
- 1019_64/66/68:r8 hold 出库,大窗同形实证→写值
1033_63:agent 加高窗核验现值对(protect),行框 8px 窄条异常登记结构侧。
种子现值=xlsx 全文(run8b 教训)。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
PKG = ROOT / "runs/autoresearch_align/多源定级_20261106/尾池判读包_r10"
TBL = ROOT / "runs/autoresearch_align/多源定级_20261106/判读_采纳_分裂_20261109.json"
HOLD8 = ROOT / "runs/autoresearch_align/多源定级_20261106/矛盾池_r8_待用户.json"
HOLD9 = ROOT / "runs/autoresearch_align/多源定级_20261106/同族池_r9_待用户.json"

sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

# 主会话终裁(大窗亲核):1019 前缀"灺:"七格写值
FINAL = {
    "1019_行19": "灺：无芯。",
    "1019_行62": "灺：无芯。",
    "1019_行64": "灺：无芯。",
    "1019_行66": "灺：无芯。",
    "1019_行68": "灺：无芯。",
    "1019_行80": "灺：判层。",
    "1019_行86": "灺：判层。",
}
FINAL_NOTE = ("主会话大窗终裁:1019 图判层语前缀=灺(火旁+乜),七格同形实证"
              "(19/62/64/66/68/80/86),现值前缀灿/此/炕/灯系引擎异读")

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

stats = {"现值对": 0, "写值": 0, "终裁写值": 0, "dup": 0}
write_rows = []
seen = set()
for b in range(4):
    res = json.loads((PKG / f"判读_结果_r10_{b}.json").read_text(encoding="utf-8"))
    for e in res:
        tag = e["tag"]
        if tag in seen:
            continue
        seen.add(tag)
        stem0, r = tag.split("_行")
        cur = xlsx_val(stem0, int(r))
        text = str(e.get("text", "") or "").strip()
        v = e.get("verdict", "")
        if tag in FINAL:
            # 主会话终裁:一律写值(前缀字形异读,纸面=灺:)
            old = by_key.get(("钻孔柱状图" + stem0, int(r)))
            if old is not None:
                inh = [str(old.get("种子现值", ""))] + \
                      [x for x in str(old.get("判读现值", "")).split("|") if x]
                old["protect"] = 0
                old["新值"] = FINAL[tag]
                old["判读现值"] = "|".join([x for x in [cur] + inh
                                            if x and x != FINAL[tag]])
                old["来源"] = old.get("来源", "") + "|r10终裁"
                old["note"] = FINAL_NOTE
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 0,
                                   "新值": FINAL[tag], "种子现值": cur,
                                   "判读现值": "", "来源": "r10终裁",
                                   "conf": "高", "note": FINAL_NOTE})
            stats["终裁写值"] += 1
            continue
        key = ("钻孔柱状图" + stem0, int(r))
        if v == "现值对":
            old = by_key.get(key)
            note = f"r10尾池判读现值对(conf {e.get('conf', '中')})"
            if old is not None:
                old["protect"] = 1
                old["来源"] = old.get("来源", "") + "|r10护"
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 1, "新值": "",
                                   "种子现值": cur, "判读现值": "", "来源": "r10",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["现值对"] += 1
        else:
            if not text:
                continue
            old = by_key.get(key)
            note = (f"r10尾池判读翻案:现值误,text=纸面忠实转写"
                    f"(conf {e.get('conf', '中')};{e.get('type', '')})")
            if old is not None:
                inh = [str(old.get("种子现值", ""))] + \
                      [x for x in str(old.get("判读现值", "")).split("|") if x]
                old["protect"] = 0
                old["新值"] = text
                old["判读现值"] = "|".join([x for x in [cur] + inh if x and x != text])
                old["来源"] = old.get("来源", "") + "|r10翻"
                old["note"] = note
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 0, "新值": text,
                                   "种子现值": cur, "判读现值": "", "来源": "r10",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["写值"] += 1

rows.extend(write_rows)
TBL.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
# hold 登记表更新:64/66/68/19 已终裁出库
for hp in (HOLD8, HOLD9):
    if not hp.exists():
        continue
    hs = json.loads(hp.read_text(encoding="utf-8"))
    for h in hs:
        if h.get("tag") in FINAL:
            h["已终裁"] = "r10 大窗实证灺:前缀,写值入第三表"
    hp.write_text(json.dumps(hs, ensure_ascii=False, indent=1), encoding="utf-8")
print("统计:", stats)
print(f"第三表 -> {len(rows)} 条(新增 {len(write_rows)})")
chk = json.loads(TBL.read_text(encoding="utf-8"))
assert len(chk) == len(rows)
print("回读校验通过")
# 1033_63 结构异常登记
abn = ROOT / "runs/autoresearch_align/多源定级_20261106/结构异常登记_r10.json"
abn.write_text(json.dumps([
    {"tag": "1033_行63", "问题": "行框重建切分异常:ivs 带高仅 8px(y17012-17020),"
     "v2 cell/strip 成窄条不可读;判读员用同管线加高窗核验纸面=现值",
     "处置": "判读 protect 已入表;行框来源待结构侧排查 table_reconstruct 该行 ivs"}],
    ensure_ascii=False, indent=1), encoding="utf-8")
print("结构异常登记 ->", abn.name)
