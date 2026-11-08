# -*- coding: utf-8 -*-
"""组装时代列整合试点包(outputs):整合 xlsx + 校正账 + 验收 JSON + 汇总 md。
数字全部现读产物 JSON,不手抄。用法: python runs/tmp/组装时代列整合包_20261010.py
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402

STEMS = ["钻孔柱状图1016", "钻孔柱状图1022", "钻孔柱状图1026", "钻孔柱状图1036", "钻孔柱状图1040"]


def main():
    dst = paths.FINALIZE_PACKAGE_DIR
    dst.mkdir(parents=True, exist_ok=True)
    lines = ["# 时代列整合试点包(5 图,2026-10-10)", "",
             "整合 = 时代列合并单元格(rowspan)+ OCR 语义校正 + 数据合理性门禁。",
             "源产物:`runs/table_整合_20261010/`;判读口径:助手视觉判读/程序规则(弱档),终验归用户。", "",
             "## 怎么看", "",
             "- `{图号}_整合.xlsx`:时代列已按名带纵向合并;描述列**黄色底**=Agnes 语义校正过的格子;",
             "- `{图号}_校正账.csv`:每一条改动/建议(应用=1 已写入,应用=0 仅记账);",
             "- `{图号}_验收.json`:名带清单、合并组、门禁问题全账。", "",
             "## 逐图汇总", "",
             "| 图 | 时代名带 | 合并组 | 门禁问题 | 账(应用/未应用) |", "| --- | --- | --- | --- | --- |"]
    for stem in STEMS:
        rep = json.loads((paths.FINALIZE_DIR / f"{stem}_验收.json").read_text(encoding="utf-8"))
        ledger_n = rep.get("账条数", 0)
        fixes = rep.get("跨图修复", [])
        lines.append(f"| {stem[5:]} | {'、'.join(rep['名带'])} | {len(rep['合并组'])} "
                     f"| {len(rep['门禁问题'])} | {ledger_n} |")
        if fixes:
            lines.append(f"  - 跨图修复: {[(f['原'], f['新']) for f in fixes]}")
    lines += ["", "## 时代列改动与推定依据(全账)", ""]
    for stem in STEMS:
        csvp = paths.FINALIZE_DIR / f"{stem}_校正账.csv"
        if not csvp.exists():
            continue
        import csv
        rows = list(csv.DictReader(open(csvp, encoding="utf-8-sig")))
        era = [r for r in rows if r["列"] == "地质时代"]
        if era:
            lines.append(f"### {stem[5:]}(时代列 {len(era)} 条)")
            lines.append("")
            lines.append("| 原 | 新 | 依据 | 应用 |")
            lines.append("| --- | --- | --- | --- |")
            for r in era:
                lines.append(f"| {r['原'][:60].replace('|', '/')} | {r['新'][:60]} | "
                             f"{r['依据'].replace('|', '/')} | {r['应用']} |")
            lines.append("")
    lines += ["## 已知未决(登记不阻塞,待用户裁决)", "",
              "- ~~1022 首带 萧系~~ **已裁(2026-10-11)**:用户确认直接是第四系,已按用户裁决落表(账来源=用户裁决);",
              "- ~~飞仙关段序 二至一 vs 一至二~~ **已裁(2026-10-11)**:用户确认两种印法都正常,保留各图原读,单杠推定\"一\"正确;",
              "- 1016:名带为 第四系→龙潭组上/中/下段→茅口组,第四系与龙潭组上段之间 194px 零墨迹字块"
              "(era_chars 字块账),大概率图面本就如此——见包内 `1016_时代列顶部裁片.png` 供眼验;",
              "- 数值门禁 flag(1016 层厚×4、1026 深度逆序×1+层厚×5、1040 层厚×2)只记未改数,见各图 _验收.json;",
              "- 繁体/死字专项:试点 5 图未遇到,全量阶段再查。", ""]
    (dst / "汇总.md").write_text("\n".join(lines), encoding="utf-8")
    for stem in STEMS:
        for suf in ("_整合.xlsx", "_校正账.csv", "_验收.json"):
            p = paths.FINALIZE_DIR / f"{stem}{suf}"
            if p.exists():
                shutil.copy2(p, dst / p.name)
    # 1016 时代列顶部裁片(第四系→龙潭组上段 之间零墨迹的眼验证据)
    import cv2
    from src.table.era_chars import _load_inputs
    hm, rd = _load_inputs("钻孔柱状图1016")
    sp_l = hm["sep_pts"][hm["keep"][0]["left_sep"]]
    sp_r = hm["sep_pts"][hm["keep"][0]["right_sep"]]
    gray = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1016.JPG"), cv2.IMREAD_GRAYSCALE)
    x0 = int(min(min(sp_l["xs"]), min(sp_r["xs"]))) - 40
    x1 = int(max(max(sp_l["xs"]), max(sp_r["xs"]))) + 40
    crop = gray[700:2600, max(0, x0):x1]
    cv2.imwrite(str(dst / "1016_时代列顶部裁片.png"), crop)
    print("包已出:", dst)
    print("文件:", sorted(p.name for p in dst.iterdir()))


if __name__ == "__main__":
    main()
