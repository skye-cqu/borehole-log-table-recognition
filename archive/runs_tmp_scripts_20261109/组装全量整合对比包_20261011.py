# -*- coding: utf-8 -*-
"""组装全量整合对比包(outputs):30 张整合 xlsx + 校正账 + 对比账 + 验收 + 汇总 md。
先跑 finalize 全量、再跑 compare_ref(main 会落 对比汇总.json),最后跑本脚本。
用法: python runs/tmp/组装全量整合对比包_20261011.py
"""
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths  # noqa: E402

STEMS = [f"钻孔柱状图{n}" for n in range(1015, 1045)]


def main():
    dst = paths.PROJECT_ROOT / "outputs/全量整合对比包_20261012"
    dst.mkdir(parents=True, exist_ok=True)
    summ = {}
    sj = paths.FINALIZE_FULL_DIR / "对比汇总.json"
    if sj.exists():
        summ = {r["图"]: r for r in json.loads(sj.read_text(encoding="utf-8"))}
    lines = ["# 全量整合对比包(30 图,2026-10-12)", "",
             "整合 = 时代列合并单元格(rowspan)+ OCR 语义校正 + 数据合理性门禁 + **参考表对比标黄**。",
             "源产物:`runs/table_整合_全量_20261011/`;判读口径:程序规则/助手视觉判读(弱档),终验归用户。", "",
             "## 颜色与文件说明", "",
             "- `{图号}_整合.xlsx`:时代列已按名带纵向合并;",
             "- **黄色字体 = 我方与原版参考表(1015-1044(1).zip 的 *_llm_corrected)不一致的字**——"
             "我方是给原版纠错的版本(原版错得多),黄字即我方纠错点,方便快速看改了哪;",
             "- `{图号}_对比账.csv`:每条不一致(我方值/参考值/判定/处置);",
             "- `{图号}_校正账.csv`、`{图号}_验收.json`:整合侧改动与门禁全账;", "",
             "## 对比对齐口径", "",
             "两表同源一张扫描图:按行像素区间互相重叠 1:1 配对(双侧覆盖率 ≥60%),切分粗细不同不硬配;",
             "仅同语义列双方非空且不等才标黄,单方空缺仅记账;数字容差 0.005(仅舍入),°/全角/空白差异不算不同;", "",
             "## 逐图汇总", "",
             "| 图 | 合并组 | 名带 | 门禁 | 整合账 | 配对行 | diff/标黄 | 单方空缺(我/参) | 未配对(我/参) |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    era_refused = []
    for stem in STEMS:
        jf = paths.FINALIZE_FULL_DIR / f"{stem}_验收.json"
        if not jf.exists():
            lines.append(f"| {stem[5:]} | - | FAIL 无整合表 | | | | | | |")
            continue
        rep = json.loads(jf.read_text(encoding="utf-8"))
        if "error" in rep:
            lines.append(f"| {stem[5:]} | - | FAIL {rep['error'][:40]} | | | | | | |")
            continue
        if rep["名带"]:
            eras = "、".join(rep["名带"])
        else:
            eras = "(拒裁未合并)"
            era_refused.append(stem[5:])
        r = summ.get(stem, {})
        if "error" in r or not r:
            cmp_cells = ["-", "-", "-", "-"]
        else:
            cmp_cells = [str(r["配对行"]), f"{r['diff']}/{r['标黄']}",
                         f"{r['ours_empty']}/{r['theirs_empty']}",
                         f"{r['未配对我方行']}/{r['未配对参考行']}"]
        lines.append(f"| {stem[5:]} | {len(rep['合并组'])} | {eras[:44]} | {len(rep['门禁问题'])} "
                     f"| {rep['账条数']} | {cmp_cells[0]} | {cmp_cells[1]} | {cmp_cells[2]} | {cmp_cells[3]} |")
    if era_refused:
        lines += ["", f"**时代列未合并({len(era_refused)} 图)**:{'、'.join(era_refused)}"
                  "——上游拒裁(1017/1020/1023/1025/1028/1032 列界折线覆盖不足;1030/1042 疑带内行序;"
                  "1019 旧版映射无折线),时代列保持原样,其余列照常整合与对比。"]
    # 交付级门禁余量 + 降级图清单(用户 2026-10-11 批准的交付 gate 口径)
    gate_p = paths.FINALIZE_FULL_DIR / "交付门禁_报告.json"
    if gate_p.exists():
        cats = json.loads(gate_p.read_text(encoding="utf-8"))
        cnt = {k: len(v) for k, v in cats.items()}
        lines += ["", "## 交付门禁余量(2026-10-12 复扫)", "",
                  f"符号幻读 {cnt.get('符号幻读', 0)} 条;粘连专项 {cnt.get('粘连专项', 0)} 条;"
                  f"错位专项 {cnt.get('错位专项', 0)} 条(见下降级清单,不阻塞)。"]
        for cat in ("符号幻读", "粘连专项"):
            for it in cats.get(cat, []):
                lines.append(f"- [{cat}] {it['图']} 行{it['行']} {it['列']}={it['值'][:24]}")
        if cnt.get("错位专项"):
            charts = sorted({it["图"] for it in cats["错位专项"]})
            lines.append(f"- [错位专项] 涉及图:{'、'.join(charts)}(整图降级,数值不承诺)")
    lines += ["", "## 降级图清单(登记不阻塞,数值不承诺)", "",
              "- **1019**:旧版行切分映射,列对应不可靠,整图降级;",
              "- **1032**:整图 B 目录列错位,数值列全部不可信,整图降级;",
              "- **1042**:整图错位 + 倾角|真厚列界折线与 1033 同病(89/113 行带宽异常),整图降级;",
              "- 时代列拒裁回退图:时代列未合并,其余列正常(见上节);",
              "- **1033**:倾角|真厚列界折线中段跳线(56/80 行带宽异常)已按墨迹重提修复"
              "(逐行竖线检测+RapidOCR/Agnes 双引擎+校正账;行界双检线假行已删,深度链闭合验证);"
              "其中 RapidOCR/Agnes 分歧格以复核裁片补写,账内标[助手视觉判读]者终验归用户。"]
    lines += ["", "## 待用户关注(登记不阻塞)", "",
              "- 黄字 = 我方纠错点(我方为准的口径);若个别黄字处怀疑我方,看对比账双方值裁决;",
              "- 数值门禁 flag(深度逆序/层厚≠深度差)只记未改数,见各图 _验收.json;", ""]
    (dst / "交付说明.md").write_text("\n".join(lines), encoding="utf-8")
    n = 0
    for stem in STEMS:
        for suf in ("_整合.xlsx", "_校正账.csv", "_验收.json", "_对比账.csv"):
            p = paths.FINALIZE_FULL_DIR / f"{stem}{suf}"
            if p.exists():
                shutil.copy2(p, dst / p.name)
                n += 1
    for extra in ("对比汇总.json", "交付门禁_报告.json"):
        p = paths.FINALIZE_FULL_DIR / extra
        if p.exists():
            shutil.copy2(p, dst / p.name)
    print("包已出:", dst, f"{n} 个产物文件")


if __name__ == "__main__":
    main()
