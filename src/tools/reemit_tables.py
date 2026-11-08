# -*- coding: utf-8 -*-
"""用现行行界重出还原表：无参数=全量 30 张（约束6）。

行判定吃 runs/table_reconstruct/{stem}_行判定.json（现行＝漏行判据重建＋折线表征＋门禁1~5）；
列界吃 {stem}_表头映射.json（select_map 单一真源 line_parts 真段，表头内容锚定），
格几何沿用 reconstruct_excel，与旧交付表同一套代码，唯一变量是行界与列界源。

产物写 paths.REEMIT_DIR_20261023，跑完落 清单.json + README_必读.md。
正式表 runs/table_reconstruct/*_还原.xlsx 里存着已回写的人审判读，重跑一次抹一次，故一律不覆盖。

值口径（重要）：本目录的表是 **RapidOCR 裸识别草案**——判读挂在旧行号上，
行界定稿（决策队列 D01）后按 P0 口径统一重推，本轮重放会静默错位，故不做。

用法:
  python -u -X utf8 src/tools/reemit_tables.py            # 全量 30 张
  python -u -X utf8 src/tools/reemit_tables.py 1032 1042   # 指定编号
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import batch, paths                  # noqa: E402
from src.table import reconstruct_excel            # noqa: E402

OUT_DIR = paths.REEMIT_DIR_20261023  # 2026-10-23 列线修复(数据区墨迹重描+质量门)后的 8 图重出
# 上一轮(重出_20261005_项④)保留不覆盖;列界源已变,另开新目录(约束6)


def bad_header(stem):
    """这张的表头映射坏在哪，返回一句人话；能用就返回 None。"""
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json"
    if not fp.exists():
        return "没有表头映射文件"
    hm = json.load(open(fp, encoding="utf-8"))
    keep, band = hm.get("keep") or [], hm.get("band")
    if not band:
        return f"表头映射坏：keep {len(keep)} 列、表头底界 band 为空"
    if len(keep) < 2:
        return f"表头映射坏：keep 只剩 {len(keep)} 列"
    return None


def worker(stem):
    why = bad_header(stem)
    if why:
        return stem, False, f"{why}（堵点同 STATUS 下一步：表头映射改吃 6a 列结构定稿）"
    try:
        sheet, meta = reconstruct_excel.build_cells(stem)
        if sheet is None:
            return stem, False, str(meta)
        p = reconstruct_excel.to_excel(stem, sheet, OUT_DIR)
        return stem, True, (f"{len(sheet[0])}列 层{meta['n_layers']} "
                            f"有字格{meta['n_text_cells']} → {p.parent.name}/{p.name}")
    except Exception as e:                          # noqa: BLE001
        return stem, False, f"{type(e).__name__}: {e}"


def summarize(out_dir):
    """行数对照:出表数据行数 vs 行判定层界数,落 清单.json + README_必读.md(约束12)。"""
    from openpyxl import load_workbook
    rows_acc = []
    for fp in sorted(out_dir.glob("*_还原.xlsx")):
        stem = fp.stem.replace("_还原", "")
        ws = load_workbook(fp, read_only=True, data_only=True).active
        n_data = sum(1 for row in ws.iter_rows(min_row=2, values_only=True)
                     if any(v not in (None, "") for v in row))
        rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                            encoding="utf-8"))
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                            encoding="utf-8"))
        rows_acc.append({"image": stem, "数据行": n_data,
                         "行判定行线": len(rd.get("rows", [])),
                         "表头源": hm.get("header_src"),
                         "表头核验": len(hm.get("label_verify") or {}),
                         "表头警告": hm.get("warnings", [])})
    json.dump({"n_images": len(rows_acc), "images": rows_acc},
              open(out_dir / "清单.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    (out_dir / "README_必读.md").write_text(
        "# 重出表（草案级,供行界核验,非定稿）\n\n"
        "- 行界:现行 `*_行判定.json`（漏行判据重建+折线表征+门禁1~5+外框定宽,分支 stage-rows-gates）;\n"
        "- 列界:`表头映射` select_map 单一真源（line_parts 真段）,\n"
        "  表头标签经内容锚定(每格 OCR 关键词核验,`表头映射.json` 的 label_verify 逐格留痕);\n"
        "- **值 = RapidOCR 裸识别草案**,未叠加 Agnes/人审判读——判读挂在旧行号上,\n"
        "  行界定稿（决策队列 D01）后按 P0 口径统一重推,本轮重放会静默错位,故不做;\n"
        "- 哨兵不可能出现（草案链无哨兵）;audit_deliverable S1 应为 0;\n"
        "- 个别表含整行无字的层（如 1015 第 75 层）:行线对之间无任何 OCR 命中,\n"
        "  成因（漏识或非内容层隙）留待行界核验,清单.json 的 数据行(有值) 与审计 物理行 数差即空层数;\n"
        "- 1032/1042 的内容权威仍是 `还原_补产终版.xlsx`（手工重建 103/112 行）;\n"
        "- 结构正确性以全分辨率叠加图+用户肉眼核验为准（约束7）,本表不得称定稿。\n",
        encoding="utf-8")
    print(f"清单+README → {out_dir}")


def main():
    stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    if len(sys.argv) > 1:
        stems = [f"钻孔柱状图{c}" for c in sys.argv[1:]]
    batch.run_batch(stems, worker, max_workers=6)
    summarize(OUT_DIR)


if __name__ == "__main__":
    main()
