# -*- coding: utf-8 -*-
"""组装人工验收包：runs/验收包/<图号>/ 每图一夹（叠加图/行线图/Excel/说明.md）。
只复制归档，不改动任何产物。"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.apply_verdict import VERDICT  # noqa: E402

OUT = paths.RUNS_DIR / "验收包"


def pack(stem, dirs):
    n = stem.replace("钻孔柱状图", "")
    copied = []

    def cp(src: Path, dst: Path):
        if src.exists():
            shutil.copy2(src, dst)
            copied.append(dst.name)

    cp(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_验收叠加图.png",
       dirs["叠加图"] / f"{n}_列线验收.png")
    cp(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_验收叠加图_预览.jpg",
       dirs["预览"] / f"{n}_列线验收.jpg")
    cp(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定_预览.jpg",
       dirs["行线"] / f"{n}_行线判定.jpg")
    cp(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_还原.xlsx",
       dirs["Excel"] / f"{n}_还原.xlsx")

    hm = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json"
    names, drops, warns = [], [], []
    if hm.exists():
        r = json.load(open(hm, encoding="utf-8"))
        names = [c["name"] for c in r["keep"]]
        drops = sorted({c["name"] for c in r["drop_columns"]} - {"空窄格"})
        warns = r["warnings"]
    v = VERDICT.get(n, {})
    lines = [
        f"# 钻孔柱状图{n}",
        f"- 保留列（{len(names)}）：{'、'.join(names) if names else '（无，见警告）'}",
        f"- 删除列：{'、'.join(drops) if drops else '无'}",
        f"- 存疑编号：{v.get('unknown', []) or '无'}",
        f"- 程序警告：{'; '.join(warns) if warns else '无'}",
        f"- 逐编号视觉判定详录：`runs/table_reconstruct/视觉验收结论.md`",
    ]
    (dirs["说明"] / f"{n}.md").write_text("\n".join(lines), encoding="utf-8")
    return n, copied


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dirs = {k: OUT / k for k in ("叠加图", "预览", "行线", "Excel", "说明")}
    for d in dirs.values():
        d.mkdir(exist_ok=True)
    stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    guide = [
        "# 验收包使用说明",
        "",
        "按类型平铺，看图软件内用“下一张”连续翻即可：",
        "1. `叠加图/` —— 30 张全图验收叠加（**主验收对象**）：红色编号线=真列分隔线，灰=外框，压暗=剔除的内容线，橙=存疑；",
        "2. `预览/` —— 同内容半分辨率 JPG，快速过图；",
        "3. `行线/` —— 层界行线判定图（26 张）；",
        "4. `Excel/` —— 还原表格，8 列（柱状/水文已删，26 份）；",
        "5. `说明/` —— 每图保留列、删除列、存疑项、程序警告。",
        "",
        "已知特殊情况：1023 表头手绘且层厚/深度顺序相反（已按人工复核纠正）；1032 扫描件左缘裁切（图内 8 列）；",
        "1018/1042 有列边界缺失；1030 未出 Excel（列线污染待修）；1020 两根真线漏标（叠加图中为压暗状态）。",
        "图幅顶部细红色横线为原图红笔标注，非程序所画。",
    ]
    (OUT / "README_验收指南.md").write_text("\n".join(guide), encoding="utf-8")
    for stem in stems:
        n, copied = pack(stem, dirs)
        print(n, len(copied), "个文件")


if __name__ == "__main__":
    main()
