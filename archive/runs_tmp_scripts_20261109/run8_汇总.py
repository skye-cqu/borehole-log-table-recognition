# -*- coding: utf-8 -*-
"""run8 收官:矛盾/无收敛池 249 格判读汇总 → 入第三表(判读_采纳_分裂_20261109.json)。

口径(与 r5-r7 一致):
- xnorm 重算 verdict 兜底(agent 口径漂移教训):verdict=现值对 但 text 与现值 xnorm
  不等→按都不对处理;text 非空且≠现值→写值。
- 图签行(纸面=图签字)与结构歧义格不写值,单列登记待用户。
- 现值对→protect(定谳,防未来规则误改);都不对且 text 可信→写值(纸面忠实转写)。
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
PKG = ROOT / "runs/autoresearch_align/多源定级_20261106/分裂判读包_20261109_v2"
TBL = ROOT / "runs/autoresearch_align/多源定级_20261106/判读_采纳_分裂_20261109.json"

sys.path.insert(0, str(ROOT))
from src.handwriting.rules import _xn  # noqa: E402

# 图签行/结构歧义/前缀存疑:不入表,登记待用户
HOLD = {
    "1017_行83": "图签行:现值=图签文字误入,纸面空白;图签处置待用户",
    "1020_行173": "图签行:现值列序错乱;图签处置待用户",
    "1032_行104": "图签行:现值串图签('买'应为'审');图签处置待用户",
    "1020_行118": "行带归属歧义:窗含两行墨迹,118/119 分行待结构复核",
    "1020_行119": "行带归属歧义:窗近乎空白,118/119 分行待结构复核",
    "1019_行64": "前缀存疑:炕/灯:无芯,留用户终裁",
    "1019_行66": "前缀存疑:炕/灯:无芯,留用户终裁",
    "1019_行68": "前缀存疑:炕/灯:无芯,留用户终裁",
}
SRC_NOTE = {
    "1017_行83": None, "1020_行118": None, "1020_行119": None,
    "1019_行64": None, "1019_行66": None, "1019_行68": None,
    "1020_行173": None, "1032_行104": None,
}

rows = json.loads(TBL.read_text(encoding="utf-8"))
by_key = {}
for e in rows:
    stem, r = e["tag"].split("_行")
    by_key[("钻孔柱状图" + stem, int(r))] = e

stats = {"现值对": 0, "写值": 0, "hold": 0, "兜底改判": 0, "dup": 0}
write_rows, hold_rows = [], []
for b in list(range(12)) + ["无收敛"]:
    res = json.loads((PKG / f"判读_结果_r8_{b}.json").read_text(encoding="utf-8"))
    dsp = json.loads((PKG / f"分派_矛盾_r8_{b}.json" if b != "无收敛"
                      else PKG / "分派_矛盾_r8_无收敛.json").read_text(encoding="utf-8"))
    cur = {d["tag"]: d["现值"] for d in dsp}
    for e in res:
        tag = e["tag"]
        cur_v = cur[tag]
        text = str(e.get("text", "") or "").strip()
        v = e.get("verdict", "")
        # xnorm 兜底:判"现值对"但 text 与现值 xnorm 不等 → 都不对
        if v == "现值对" and text and _xn(text) != _xn(cur_v) \
                and SequenceMatcher(None, _xn(text), _xn(cur_v)).ratio() < 0.85:
            v = "都不对"
            stats["兜底改判"] += 1
        if tag in HOLD:
            hold_rows.append({"tag": tag, "现值": cur_v, "agent_text": text,
                              "verdict": v, "登记": HOLD[tag]})
            stats["hold"] += 1
            continue
        stem, r = tag.split("_行")
        key = ("钻孔柱状图" + stem, int(r))
        if v == "现值对":
            # 定谳保护:候选=现值即正确,防未来规则误改
            old = by_key.get(key)
            note = f"r8矛盾池判读现值对(conf {e.get('conf', '中')},{e.get('type', '')})"
            if old is not None:
                old["protect"] = 1
                old["来源"] = old.get("来源", "") + "|r8护"
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 1, "新值": "",
                                   "种子现值": cur_v, "判读现值": "", "来源": "r8",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["现值对"] += 1
        else:
            # 都不对:agent 忠实转写 → 写值(纸面)
            if not text:
                hold_rows.append({"tag": tag, "现值": cur_v, "agent_text": "",
                                  "verdict": v, "登记": "都不对但无text,不入表"})
                stats["hold"] += 1
                continue
            old = by_key.get(key)
            note = (f"r8矛盾池判读翻案:现值误,text=纸面忠实转写"
                    f"(conf {e.get('conf', '中')};{e.get('type', '')})")
            if old is not None:
                # 前表已有条目(现值对保护):翻案覆盖写值,继承种子链
                inh = [str(old.get("种子现值", ""))] + \
                      [x for x in str(old.get("判读现值", "")).split("|") if x]
                old["protect"] = 0
                old["新值"] = text
                old["判读现值"] = "|".join([x for x in [cur_v] + inh
                                            if x and x != text])
                old["来源"] = old.get("来源", "") + "|r8翻"
                old["note"] = note
                stats["dup"] += 1
            else:
                write_rows.append({"tag": tag, "组S": "", "protect": 0, "新值": text,
                                   "种子现值": cur_v, "判读现值": "", "来源": "r8",
                                   "conf": e.get("conf", "中"), "note": note})
            stats["写值"] += 1

rows.extend(write_rows)
TBL.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
(ROOT / "runs/autoresearch_align/多源定级_20261106/矛盾池_r8_待用户.json").write_text(
    json.dumps(hold_rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("统计:", stats)
print(f"第三表 {len(rows) - len(write_rows)} -> {len(rows)} 条(新增 {len(write_rows)})")
print(f"待用户登记 {len(hold_rows)} 格")
# 回读校验
chk = json.loads(TBL.read_text(encoding="utf-8"))
assert len(chk) == len(rows)
bad = [e for e in chk if not e.get("tag") or "_行" not in e["tag"]]
assert not bad, bad
print("回读校验通过")
