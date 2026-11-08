# -*- coding: utf-8 -*-
"""Agnes 重读一致性核对(用户 2026-10-29:同配置再做一次,看结果是否与第一次相同)。

第一次答案备份在 AGNES_REPEAT_DIR_20261029(*.第1次.json),第二次为
AGNES_REREAD_DIR_20261028 内现行 *.答.json。逐块逐行逐字段比对:
先各自过 _spread(列挤占分摊)+_norm 折平,再按 块行数/解析成败 分档统计。

用法: python src/tools/agnes_repeat_check.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths
from src.table.agnes_era_blocks import _norm, _spread

ROLES = ("era", "layer", "depth", "thick", "length", "dip", "true_thick", "desc")


def main():
    rep_dir = paths.AGNES_REPEAT_DIR_20261029
    out = {"块": 0, "两次皆解析": 0, "行数同": 0, "行数异": 0,
           "字段比": 0, "字段同": 0, "字段异": 0}
    by_role = {r: [0, 0] for r in ROLES}          # [同, 异]
    diffs = []
    for first in sorted(rep_dir.glob("*/*.第1次.json")):
        out["块"] += 1
        cur = Path(str(first).replace(str(rep_dir), str(paths.AGNES_REREAD_DIR_20261028))) \
            .with_name(first.name.replace(".第1次.json", ".json"))
        j1 = json.loads(first.read_text(encoding="utf-8"))
        j2 = json.loads(cur.read_text(encoding="utf-8"))
        r1, r2 = j1.get("rows"), j2.get("rows")
        if not r1 or not r2:
            continue
        out["两次皆解析"] += 1
        if len(r1) != len(r2):
            out["行数异"] += 1
            diffs.append({"块": str(cur.parent.name) + "/" + cur.name[:4],
                          "类": f"行数 {len(r1)}→{len(r2)}"})
            continue
        out["行数同"] += 1
        账f = cur.parent / "块账.json"
        roles = json.loads(账f.read_text(encoding="utf-8"))["roles"]
        for a, b in zip(r1, r2):
            _spread(a, roles)
            _spread(b, roles)
            for k in ROLES:
                if k not in roles:
                    continue
                _, v1 = _norm(k, a.get(k, ""))
                _, v2 = _norm(k, b.get(k, ""))
                out["字段比"] += 1
                if v1 == v2:
                    out["字段同"] += 1
                    by_role[k][0] += 1
                else:
                    out["字段异"] += 1
                    by_role[k][1] += 1
                    if len(diffs) < 40:
                        diffs.append({"块": cur.parent.name[5:] + "/" + cur.name[1:3],
                                      "r": a.get("r"), "列": k,
                                      "第1次": str(v1)[:40], "第2次": str(v2)[:40]})
    rate = out["字段同"] / max(1, out["字段比"]) * 100
    print(json.dumps(out, ensure_ascii=False))
    print(f"字段级一致率: {out['字段同']}/{out['字段比']} = {rate:.3f}%")
    for k, (s, d) in by_role.items():
        if s + d:
            print(f"  {k}: {s}/{s + d} = {s / (s + d) * 100:.3f}%  异 {d}")
    odd = (rep_dir / "两次差异样例.json")
    odd.write_text(json.dumps(diffs, ensure_ascii=False, indent=1), encoding="utf-8")
    print("差异样例:", odd, f"({len(diffs)} 条)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
