# -*- coding: utf-8 -*-
"""run13:重建不动点锚定——第三表种子现值重锚种子表值(SEED_DIR)。

根因:apply_rules 每次全量重置重建 candidate(种子表的纯函数),第三表条目
的"种子现值"若锚 candidate 判读时值,第三表一变重建产物回退种子表值→守卫
xnorm 全等失败→判读成果掉分(run12 尾 7 格低档的根因)。

修法(全 944 条):
- seedv = 种子表值(重建不动点);
- 种子现值 ← seedv;判读现值链 ∪ {判读时candidate值, 新值, 旧链, seedv};
- protect=1 且判读时candidate值≠seedv:candidate 会回退→protect 保护不了
  纸面值→改写值(新值=判读时candidate值=判读确认的纸面,种子现值=seedv),
  重建后 cur=seedv∈守卫→判读采纳写新值→converge 定谳。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TBL = ROOT / "runs/autoresearch_align/多源定级_20261106/判读_采纳_分裂_20261109.json"

sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting.rules import _xn  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

tbl = json.loads(TBL.read_text(encoding="utf-8"))
cache = {}


def seed_val(stem0, r):
    stem = "钻孔柱状图" + stem0
    if stem not in cache:
        p = paths.AUTORESEARCH_SEED_DIR / f"{stem}_整合.xlsx"
        rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
        dcol = R.resolve_roles(rows[0]).get("desc")
        cache[stem] = (rows, dcol)
    rows, dcol = cache[stem]
    return str(rows[int(r) - 1][dcol] if dcol < len(rows[int(r) - 1]) else "")


from collections import Counter
stats = Counter()
for e in tbl:
    stem0, r = e["tag"].split("_行")
    seedv = seed_val(stem0, int(r))
    old_seed = str(e.get("种子现值", ""))
    chain = [x for x in str(e.get("判读现值", "")).split("|") if x]
    newv = str(e.get("新值", "") or "")
    # 链补全:判读时candidate(旧种子)+种子表值
    for x in ([old_seed] if old_seed else []) + [seedv]:
        if x and x not in chain and _xn(x) != _xn(newv):
            chain.append(x)
    e["判读现值"] = "|".join(chain)
    if _xn(old_seed) != _xn(seedv):
        e["种子现值"] = seedv
        e["note"] = str(e.get("note", "")) + ";run13不动点锚定(种子现值←种子表值)"
        if e.get("protect") and _xn(old_seed) != _xn(newv) and old_seed:
            # candidate 回退后 protect 失锚:改写值,新值=判读确认的纸面(旧种子)
            e["protect"] = 0
            e["新值"] = old_seed
            stats["protect转写值"] += 1
        stats["重锚"] += 1
    else:
        stats["已锚"] += 1

TBL.write_text(json.dumps(tbl, ensure_ascii=False, indent=1), encoding="utf-8")
print("统计:", dict(stats), "总数", len(tbl))
# 回读:全表守卫对"种子表值"命中
miss = 0
for e in tbl:
    stem0, r = e["tag"].split("_行")
    seedv = seed_val(stem0, int(r))
    seeds = ([str(e.get("种子现值", "")), str(e.get("新值", ""))]
             + str(e.get("判读现值", "")).split("|"))
    if _xn(seedv) not in (_xn(x) for x in seeds if x):
        miss += 1
print("种子表值不在守卫链:", miss, "(期望 0)")
