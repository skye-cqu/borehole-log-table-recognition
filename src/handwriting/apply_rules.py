# -*- coding: utf-8 -*-
"""规则引擎执行器:重置候选区→应用规则→写清单与账目。

吃 paths.AUTORESEARCH_SEED_DIR 的 30 张定稿整合表(冻结基线快照),
产出 paths.AUTORESEARCH_CANDIDATE_DIR 的候选表 + _manifest.json + _账目.json。
每次运行全量重置重建——candidate 只是规则的纯函数,无残留状态。

CLI: python src/handwriting/apply_rules.py [--only 规则名,规则名]
"""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.handwriting.engine import apply_to_workbook
from src.handwriting import rules as rules_mod


def main(argv):
    only = None
    if argv and argv[0] == "--only":
        only = set(argv[1].split(",")) if len(argv) > 1 else set()
    seed, cand = paths.AUTORESEARCH_SEED_DIR, paths.AUTORESEARCH_CANDIDATE_DIR
    seeds = sorted(seed.glob("*_整合.xlsx"))
    if not seeds:
        print("FAIL 无种子表:", seed)
        return 2
    if cand.exists():
        shutil.rmtree(cand)                     # 错误产出即清:候选区整体重建
    cand.mkdir(parents=True)
    for p in seeds:
        shutil.copy2(p, cand / p.name)
    use = [r for r in rules_mod.RULES if only is None or r.name in only]
    names = [r.name for r in use]
    missing = (only or set()) - set(names)
    if missing:
        print("FAIL 未知规则:", sorted(missing))
        return 2
    t0, ledger = time.time(), []
    for p in sorted(cand.glob("*_整合.xlsx")):
        ledger += apply_to_workbook(p, use, rules_mod.resolve_roles,
                                    stem=p.name[:-len("_整合.xlsx")])
    per_rule, per_chart = {}, {}
    for e in ledger:
        per_rule[e["规则"]] = per_rule.get(e["规则"], 0) + 1
        per_chart[e["图"]] = per_chart.get(e["图"], 0) + 1
    manifest = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "seed": str(seed), "rules": names,
                "total_changes": len(ledger), "per_rule": per_rule,
                "per_chart": per_chart, "耗时s": round(time.time() - t0, 1)}
    (cand / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(cand / "_账目.json", "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)
    print("规则", names, "改动", len(ledger), "图", len(per_chart),
          f"{manifest['耗时s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
