# -*- coding: utf-8 -*-
"""98 格合并预览(只读):交付包现值 vs 种子值 vs 定谳值(候选)逐格对账。

产出(新目录,不动交付包):
  runs/autoresearch_align/多源定级_20261106/合并预览_20261108/
    合并预览.csv   98 行逐格(图/行/组/交付包现值/种子值/定谳值/来源/conf)
    合并预览.md    摘要(将变更格数/按图分布/一致性校验/合并实施要点)
"""
import csv, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
from src.core import paths
from src.handwriting.normalizers import norm_desc
from src.handwriting import rules as R
from openpyxl import load_workbook

BASE = paths.AUTORESEARCH_DIR / "多源定级_20261106"
OUT = BASE / "合并预览_20261108"
OUT.mkdir(exist_ok=True)
DELIV = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活\outputs\Excel交付_最终_20261028")

tab = json.loads((BASE / "判读_采纳全表_20261108.json").read_text(encoding="utf-8"))

def desc_col(rows):
    return R.resolve_roles(rows[0]).get("desc")

cand, seed, deliv = {}, {}, {}
for p in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
    stem = p.stem.replace("_整合", "")
    rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
    d = desc_col(rows)
    cand[stem] = {i + 2: rows[i + 1][d] for i in range(len(rows) - 1)}
for p in sorted(paths.AUTORESEARCH_SEED_DIR.glob("*_整合.xlsx")):
    stem = p.stem.replace("_整合", "")
    rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
    d = desc_col(rows)
    seed[stem] = {i + 2: rows[i + 1][d] for i in range(len(rows) - 1)}
for p in sorted(DELIV.glob("*_整合.xlsx")):
    stem = p.stem.replace("_整合", "")
    rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
    d = desc_col(rows)
    deliv[stem] = {i + 2: rows[i + 1][d] for i in range(len(rows) - 1)}

rows_out, warn = [], []
for e in tab:
    stem, row_s = e["tag"].split("_行")
    row = int(row_s)
    full = "钻孔柱状图" + stem
    dv = deliv.get(full, {}).get(row)
    sv = seed.get(full, {}).get(row)
    cv = cand.get(full, {}).get(row)
    if dv is None:
        warn.append(f"{e['tag']}: 交付包无此行/无此图")
        continue
    # 一致性:交付包 desc 应与种子全等(交付包由整合链产出,desc 无独立补丁)
    if norm_desc(dv) != norm_desc(sv):
        warn.append(f"{e['tag']}: 交付包≠种子(交付包={str(dv)[:24]!r} 种子={str(sv)[:24]!r})")
    target = e["新值"] if e["组"] == "C" else (e["判读现值"] if e["组"] == "B" else e["种子现值"])
    changed = norm_desc(dv) != norm_desc(target)
    rows_out.append({
        "tag": e["tag"], "组": e["组"], "verdict_来源": e["来源"],
        "交付包现值": "" if dv is None else str(dv),
        "种子值": "" if sv is None else str(sv),
        "定谳值": "" if target is None else str(target),
        "将变更": "是" if changed else "否",
        "conf": e.get("conf", ""),
    })

n_change = sum(1 for r in rows_out if r["将变更"] == "是")
by_change = Counter()
for r in rows_out:
    if r["将变更"] == "是":
        by_change[r["tag"].split("_行")[0]] += 1

with open(OUT / "合并预览.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
    w.writeheader()
    w.writerows(rows_out)

md = ["# 98 格定谳值合并预览(2026-11-08,只读对账)", "",
      f"- 交付包基准: `outputs/Excel交付_最终_20261028/`(30 图,只读未动)", "",
      "| 项 | 数 |", "|---|---|"]
md += [f"| 预览格数 | {len(rows_out)} |",
       f"| 合并将变更 | {n_change} |",
       f"| 维持不变(判读=现值) | {len(rows_out) - n_change} |",
       f"| 变更按图分布 | {dict(sorted(by_change.items()))} |", "",
      f"一致性警告 {len(warn)} 条:" if warn else "一致性校验: 交付包 desc 与种子逐格全等,无漂移。"]
md += [f"- {w}" for w in warn]
md += ["", "## 合并实施要点(获批后执行)",
       "- 目标=交付包 30 图 desc 格(66 格写定谳值);**必须 rich_text=True 载入**(10-11 教训:否则红字 rich text 被打回纯文本)",
       "- 红字语义:与参考分歧标红——写定谳值后须同步重算该格红字(定谳值来自原图判读,与参考的关系重判)",
       "- 校正账逐格入账(来源=判读采纳,A/B/C 组+conf),账幂等(同格旧条目先清再追加)",
       "- 落地后跑 audit_deliverable(哨兵残留)+重出对比标注;种子表与候选区不动",
       "- 署名: 53 格纸面转写=助手视觉判读(用户授权),弱档"]
(OUT / "合并预览.md").write_text("\n".join(md), encoding="utf-8")
print(f"预览 {len(rows_out)} 格,将变更 {n_change},警告 {len(warn)}")
for w in warn:
    print("  WARN", w)
print(f"-> {OUT}")
