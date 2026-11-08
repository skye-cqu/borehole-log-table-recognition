# -*- coding: utf-8 -*-
"""项②收尾重跑回归断言: 非 era 行与备份(v9)逐字节一致; era 行 = 备份折线的前置扩展。

备份 = rollback/era_ext_行判定_备份_20261001(西延前的 v9 定稿)。
退出码非 0 = 有回归。"""
import json
import sys

sys.path.insert(0, ".")
from src.core import paths

BAK = paths.PROJECT_ROOT / "rollback" / "era_ext_行判定_备份_20261001"
bad = 0
n_era = 0
n_era_ok_suffix = 0
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
        if "era" not in rn:
            if ro != rn:
                print(f"[FAIL] {stem} 行{i} 非 era 行被改动")
                bad += 1
            continue
        n_era += 1
        po, pn = ro["poly"], rn["poly"]
        k = len(pn) - len(po)
        if k < 0 or pn[k:] != po:
            print(f"[FAIL] {stem} 行{i} era 行东段与备份不一致 (k={k})")
            bad += 1
        else:
            n_era_ok_suffix += 1
        if rn["n_poly"] != len(pn):
            print(f"[FAIL] {stem} 行{i} n_poly 不一致")
            bad += 1
print(f"era 行 {n_era} 条(东段保持 {n_era_ok_suffix}), 非 era 行零改动, 失败 {bad}")
sys.exit(1 if bad else 0)
