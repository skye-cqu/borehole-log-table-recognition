# -*- coding: utf-8 -*-
"""final:终版交付包(2026-11-09)——candidate 终值 30 张 → 字级标红 vs 用户参考包。

1. outputs/Excel交付_终版_20261109/ ← candidate 30 张整合表(纯终值)
2. compare_ref.compare_chart 逐图:与 runs/参考表_1015-1044_20261011(用户提供的
   1015-1044(1).zip 解包)字级对比,差异文字红色字体(RICH_COLS 长文本列只标
   差异字符,数值/短文本整格红),+对比账 csv+对比汇总.json
3. 血统切换:旧种子表备份 rollback/,candidate 终值 30 张覆盖种子表(新基线)
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(ROOT))

from src.core import paths  # noqa: E402
from src.table.compare_ref import compare_chart  # noqa: E402

OUT = paths.OUTPUTS_DIR / "Excel交付_终版_20261109"
REF = paths.REF_XLSX_DIR_20261011 / "1015-1044"
t0 = time.time()

# 1) 复制终值
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
stems = sorted(p.name[:-len("_整合.xlsx")]
               for p in paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx"))
assert len(stems) == 30, f"candidate 应 30 张,实 {len(stems)}"
for s in stems:
    shutil.copy2(paths.AUTORESEARCH_CANDIDATE_DIR / f"{s}_整合.xlsx",
                 OUT / f"{s}_整合.xlsx")
print("① 终值复制 30 张 ->", OUT.name)

# 2) 字级标红
summary = []
for s in stems:
    rep = compare_chart(s, OUT, REF)
    summary.append(rep)
    if "error" in rep:
        print(s, "FAIL", rep["error"])
    else:
        print(s, f"配对{rep['配对行']} diff{rep['diff']} 我空{rep['ours_empty']} "
                 f"参空{rep['theirs_empty']}")
(OUT / "对比汇总.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
ok = [r for r in summary if "比对格" in r]
if ok:
    tg, te = sum(r["比对格"] for r in ok), sum(r["equal"] for r in ok)
    print(f"② 整体一致率 {te}/{tg} = {te / tg:.4f}")
bad = [r["图"] for r in summary if "error" in r]
print("   失败:", bad or "无")

# 3) 血统切换
bk = ROOT / "rollback/seed_20261109_切换前"
if not bk.exists():
    bk.mkdir(parents=True)
    for p in paths.AUTORESEARCH_SEED_DIR.glob("*_整合.xlsx"):
        shutil.copy2(p, bk / p.name)
    print("③ 旧种子表备份 -> rollback/seed_20261109_切换前")
for p in paths.AUTORESEARCH_SEED_DIR.glob("*_整合.xlsx"):
    p.unlink()
for s in stems:
    shutil.copy2(OUT / f"{s}_整合.xlsx",
                 paths.AUTORESEARCH_SEED_DIR / f"{s}_整合.xlsx")
print("④ 血统切换:种子表 <- 终值 30 张", f"{time.time() - t0:.0f}s")
