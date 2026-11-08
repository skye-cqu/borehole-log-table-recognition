# -*- coding: utf-8 -*-
"""项③重跑回归断言(对比 rollback/era_ext_行判定_备份_20261001 = v9 西延前定稿)。

项③有意改动 rows 的 poly(无墨区锚定+桥),所以断言分两层:
- 身份字段全等(所有行):x/segment_ids/y_at_mid/cov_num/n_chains/boundary_x;
- 未动笔行(chord_n_anchor 不存在)且非 era 行:整条记录逐字节一致;
- era 行门复验:30 张合计 full=205、partial=0(项②收尾口径)。
退出码非 0 = 有回归。"""
import json
import sys

sys.path.insert(0, ".")
from src.core import paths

BAK = paths.PROJECT_ROOT / "rollback" / "era_ext_行判定_备份_20261001"
ID_KEYS = ["x", "segment_ids", "y_at_mid", "cov_num", "n_chains", "boundary_x"]
bad = 0
n_untouched_chk = 0
n_era = n_full = n_part = 0
for f in sorted(BAK.glob("钻孔柱状图*_行判定.json")):
    stem = f.name[:-9]
    old = json.loads(f.read_text(encoding="utf-8"))
    new = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                     .read_text(encoding="utf-8"))
    if len(old["rows"]) != len(new["rows"]):
        print(f"[FAIL] {stem} 行数 {len(old['rows'])} -> {len(new['rows'])}")
        bad += 1
        continue
    for i, (ro, rn) in enumerate(zip(old["rows"], new["rows"])):
        for k in ID_KEYS:
            if k == "x" and "era" in rn:
                # era 行西端由西延合法西移(备份=西延前 v9),只验东端
                if ro["x"][1] != rn["x"][1]:
                    print(f"[FAIL] {stem} 行{i} era 行 x[1] 被改动")
                    bad += 1
            elif ro.get(k) != rn.get(k):
                print(f"[FAIL] {stem} 行{i} 身份字段 {k} 被改动: {ro.get(k)} -> {rn.get(k)}")
                bad += 1
        if "era" not in rn and "chord_n_anchor" not in rn:
            n_untouched_chk += 1
            if ro != rn:
                print(f"[FAIL] {stem} 行{i} 未动笔行被改动")
                bad += 1
        if "era" in rn:
            n_era += 1
            n_full += rn["era"] == "full"
            n_part += rn["era"] == "partial"
print(f"未动笔行核验 {n_untouched_chk} 条, era 行 {n_era} (full {n_full} / partial {n_part}), 失败 {bad}")
if n_part != 0 or n_era < 205 or n_full != n_era:
    print("[FAIL] era 接触门不复验(应全部接触,≥205 行)")
    bad += 1
sys.exit(1 if bad else 0)
