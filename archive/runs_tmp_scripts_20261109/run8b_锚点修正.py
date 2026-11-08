# -*- coding: utf-8 -*-
"""run8b:第三表种子现值锚点修正——分派 json"现值"字段截断(60字)致守卫 xnorm
全等失败,64/477 条判读成果在 converge_score 未吃到定谳 1.0。

修法:守卫未命中条目,种子现值 ← xlsx 当前全文(判读员对照的候选值锚点),
判读现值链保留(含分派截断版,向后兼容)。note 补记。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TBL = ROOT / "runs/autoresearch_align/多源定级_20261106/判读_采纳_分裂_20261109.json"
MISS = ROOT / "runs/tmp/r8_guard_miss.json"

sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

miss = {m["tag"] for m in json.loads(MISS.read_text(encoding="utf-8"))}
tbl = json.loads(TBL.read_text(encoding="utf-8"))
cache = {}
fixed = 0
for e in tbl:
    if e["tag"] not in miss:
        continue
    stem0, r = e["tag"].split("_行")
    stem = "钻孔柱状图" + stem0
    if stem not in cache:
        p = paths.AUTORESEARCH_CANDIDATE_DIR / f"{stem}_整合.xlsx"
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        cache[stem] = (rows, dcol)
    rows, dcol = cache[stem]
    cur = str(rows[int(r) - 1][dcol] if dcol < len(rows[int(r) - 1]) else "")
    old_seed = str(e.get("种子现值", ""))
    e["种子现值"] = cur
    if _xn(old_seed) != _xn(cur):
        # 链中保留旧种子,守卫列表语义不变
        chain = [x for x in str(e.get("判读现值", "")).split("|") if x]
        if old_seed and old_seed not in chain:
            chain.append(old_seed)
        e["判读现值"] = "|".join(chain)
        e["note"] = str(e.get("note", "")) + ";run8b种子现值锚点修正(分派现值截断缺陷)"
        fixed += 1

TBL.write_text(json.dumps(tbl, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"锚点修正 {fixed} 条(共 {len(miss)} 未命中)")
# 回读:守卫命中复查
chk = json.loads(TBL.read_text(encoding="utf-8"))
assert len(chk) == len(tbl)
cache2 = {}
still = 0
for e in chk:
    stem0, r = e["tag"].split("_行")
    stem = "钻孔柱状图" + stem0
    if stem not in cache2:
        p = paths.AUTORESEARCH_CANDIDATE_DIR / f"{stem}_整合.xlsx"
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        cache2[stem] = (rows, dcol)
    rows, dcol = cache2[stem]
    cur = str(rows[int(r) - 1][dcol] if dcol < len(rows[int(r) - 1]) else "")
    seeds = ([str(e.get("种子现值", "")), str(e.get("新值", ""))]
             + str(e.get("判读现值", "")).split("|"))
    if _xn(cur) not in (_xn(x) for x in seeds if x):
        still += 1
print(f"回读校验: 守卫仍未命中 {still} 条(期望 0)")
