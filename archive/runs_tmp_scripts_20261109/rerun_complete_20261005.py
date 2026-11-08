# -*- coding: utf-8 -*-
"""项④(行线补全) 30 张全量重跑:单进程,逐张断言回归,任何断言失败即停并报图号。

回归断言(对照 rollback/行判定_项④前_20261005/ 的交付态 JSON):
  1 旧 rows 逐条字节等价(json sort_keys 序列化)存在于新 rows;
  2 新增 rows 恰为补全行(complete_from_sub=True),条数=补全数;
  3 sub_rows 字节等价(多重集);
  4 era 接触数不低于旧值(补全行可能新增 era 行);
  5 off_grid 字节等价。
"""
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
from src.core import paths
from src.table.track_rows import determine_rows

BK = paths.PROJECT_ROOT / "rollback" / "行判定_项④前_20261005"
BK.mkdir(parents=True, exist_ok=True)

stems = sorted(p.stem for p in paths.RAW_DIR.glob("钻孔柱状图*.JPG"))
print(f"共 {len(stems)} 张;备份目录 {BK}")


def canon(rec):
    return json.dumps(rec, sort_keys=True, ensure_ascii=False)


tot = {"n_comp": 0, "n_try": 0, "era_old": 0, "era_new": 0, "full_old": 0, "full_new": 0}
fails = []
t_all = time.time()
for i, stem in enumerate(stems, 1):
    t = time.time()
    src = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json"
    bak = BK / f"{stem}_行判定.json"
    if not bak.exists():
        shutil.copy2(src, bak)
    old = json.loads(bak.read_text(encoding="utf-8"))
    out = determine_rows(stem)
    # -- 断言 --
    old_rows = {canon(r) for r in old["rows"]}
    new_rows = [canon(r) for r in out["rows"]]
    new_set = set(new_rows)
    miss = old_rows - new_set
    added = [r for r in out["rows"] if canon(r) not in old_rows]
    bad_added = [r for r in added if not r.get("complete_from_sub")]
    old_subs = sorted(canon(r) for r in old["sub_rows"])
    new_subs = sorted(canon(r) for r in out["sub_rows"])
    old_off = sorted(canon(r) for r in old.get("off_grid", []))
    new_off = sorted(canon(r) for r in out.get("off_grid", []))
    era_old = sum(1 for r in old["rows"] if r.get("era") == "full")
    era_new = sum(1 for r in out["rows"] if r.get("era") == "full")
    n_comp = sum(1 for r in added if r.get("complete_from_sub"))
    problems = []
    if miss:
        problems.append(f"旧行丢失{len(miss)}条")
    if bad_added:
        problems.append(f"新增非补全行{len(bad_added)}条")
    if len(added) != out.get("n_complete", n_comp):
        problems.append(f"新增{len(added)}≠补全{n_comp}")
    if old_subs != new_subs:
        problems.append("sub_rows 变动")
    if old_off != new_off:
        problems.append("off_grid 变动")
    if era_new < era_old:
        problems.append(f"era 接触 {era_old}→{era_new}")
    if problems:
        fails.append((stem, problems))
        print(f"[{i:2d}/{len(stems)}] {stem} ✗ {'; '.join(problems)}")
        continue
    tot["n_comp"] += n_comp
    tot["n_try"] += out.get("n_complete_try", 0)
    tot["era_old"] += era_old
    tot["era_new"] += era_new
    w = [x for x in out["warnings"] if "项④" in x]
    print(f"[{i:2d}/{len(stems)}] {stem} {time.time()-t:5.1f}s 行 {len(old['rows'])}→{len(out['rows'])} "
          f"补全 {n_comp}/{out.get('n_complete_try', 0)} era接触 {era_old}→{era_new} {w}")

print(f"\n合计 {time.time()-t_all:.0f}s: 补全 {tot['n_comp']}/{tot['n_try']} 条, "
      f"era 接触 {tot['era_old']}→{tot['era_new']}")
if fails:
    print(f"回归断言失败 {len(fails)} 张:")
    for stem, p in fails:
        print(" ", stem, "; ".join(p))
    sys.exit(1)
print("回归断言全部通过")
