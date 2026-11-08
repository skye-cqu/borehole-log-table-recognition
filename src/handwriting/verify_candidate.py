# -*- coding: utf-8 -*-
"""候选表正确性门禁(.auto/checks.sh 的执行器)。

查四件事,任一违例退出码 1:
  1. 文件集完整:candidate 与 seed 同为 30 张 *_整合.xlsx,_manifest.json 在;
  2. 结构无损:每表 max_row/max_column 与 seed 相同(规则只许改值,不许增删行列);
  3. 哨兵 0:全表无 "@单"/"@条"/字面 "nan"/"None"(回写链污染哨兵,见 STATUS P0);
  4. 数值列类型:与 seed 不同的数值角色格,规范化后必须可析为 float
     (规则不得往数值列引入非数值文本;seed 本身的杂质格不动则不究)。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.handwriting.normalizers import norm_text, parse_num
from src.handwriting import rules as rules_mod

SENTINELS = ("@单", "@条")
LITERAL_BAD = {"nan", "none", "NaN", "None"}


def _grid(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True)
    ws = wb.active
    g = list(ws.iter_rows(values_only=True))
    dims = (ws.max_row, ws.max_column)
    wb.close()
    return g, dims


def main():
    seed, cand = paths.AUTORESEARCH_SEED_DIR, paths.AUTORESEARCH_CANDIDATE_DIR
    bad = []
    seeds = sorted(seed.glob("*_整合.xlsx"))
    cands = sorted(cand.glob("*_整合.xlsx"))
    if [p.name for p in seeds] != [p.name for p in cands]:
        bad.append(f"文件集不一致 seed={len(seeds)} cand={len(cands)}")
    if not (cand / "_manifest.json").exists():
        bad.append("缺 _manifest.json")
    mf = {}
    if (cand / "_manifest.json").exists():
        mf = json.loads((cand / "_manifest.json").read_text(encoding="utf-8"))
        missing = set(mf.get("rules", [])) ^ {r.name for r in rules_mod.RULES}
        if missing:
            bad.append(f"manifest 规则集与 rules.py 不一致: {sorted(missing)}")
    num_roles = rules_mod.NUMERIC_ROLES
    for sp in seeds:
        cp = cand / sp.name
        if not cp.exists():
            continue
        sg, sdims = _grid(sp)
        cg, cdims = _grid(cp)
        stem = sp.name[:-len("_整合.xlsx")]
        if sdims != cdims:
            bad.append(f"{stem} 维度变 {sdims}->{cdims}")
            continue
        from src.table.finalize_tables import column_roles
        roles = column_roles(sg[0] if sg else [])
        idx_role = {c: r for r, c in roles.items()}
        for i, (sr, cr) in enumerate(zip(sg[1:], cg[1:]), start=2):
            for j, (sv, cv) in enumerate(zip(sr, cr)):
                role = idx_role.get(j)
                if role is None:
                    continue
                s_txt, c_txt = norm_text(sv), norm_text(cv)
                if s_txt in LITERAL_BAD or c_txt in LITERAL_BAD or \
                   any(x in c_txt for x in SENTINELS):
                    bad.append(f"{stem} r{i}c{j + 1} 哨兵/字面: {c_txt[:40]!r}")
                if role in num_roles and s_txt != c_txt and parse_num(cv) is None:
                    bad.append(f"{stem} r{i}c{j + 1} 数值列引入非数值: "
                               f"{s_txt[:20]!r}->{c_txt[:20]!r}")
    n_bad = len(bad)
    print(f"checks: 违例 {n_bad} (规则 {mf.get('rules', [])} "
          f"改动 {mf.get('total_changes', '?')})")
    for b in bad[:20]:
        print("  ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
