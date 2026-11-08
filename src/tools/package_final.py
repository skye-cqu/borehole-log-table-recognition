# -*- coding: utf-8 -*-
"""终版打包(幂等,可反复跑):runs 补产终版 → outputs/Excel交付_最终_20260915。

- 拷 4 张 {编号}_还原.xlsx
- 重建 README 分级表(含伪差修复列;按"| 图号"表头定位整块替换)
- 同步复核包:点选版 待核清单.html(runs 侧由 agnes4_verify.py review 生成)、
  顶层 回写模板.json(剩余待人审键)、清理 HTML 未引用的裁片 PNG

用法: python src/tools/package_final.py
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from src.core import paths  # noqa: E402

STEMS4 = ["钻孔柱状图1018", "钻孔柱状图1030", "钻孔柱状图1032", "钻孔柱状图1042"]
PKG = PROJECT_ROOT / "outputs" / "Excel交付_最终_20260915"
RUNS = paths.RUNS_DIR / "table_reconstruct"


def main():
    summary = json.loads((RUNS / "对账汇总.json").read_text(encoding="utf-8"))
    rows, tots = [], [0] * 11
    tpl = {}
    for stem in STEMS4:
        code = stem[-4:]
        flags = json.loads((RUNS / f"{stem}_待核清单.json").read_text(encoding="utf-8"))

        def cnt(*prefixes):
            return sum(1 for f in flags
                       if any(str(f["处置"]).startswith(p) for p in prefixes))

        rel = cnt("关系式裁定", "深度差裁定")
        dual = cnt("Agnes双读一致采纳")
        empty = cnt("双引擎读空一致")
        arti = cnt("多引擎一致(小数点伪差修复)")
        human = cnt("用户人审确认")
        visual = cnt("助手视觉判读")
        avv = cnt("助手视觉核验")
        pending = cnt("待人审")
        strict = summary[stem]["格"] - len(flags)
        pair = summary[stem]["QC"]["真厚互证对"]
        shutil.copy2(RUNS / f"{stem}_还原_补产终版.xlsx", PKG / f"{code}_还原.xlsx")
        vals = [summary[stem]["格"], strict, dual, empty, rel, arti, human, visual,
                avv, pending, pair]
        tots = [a + b for a, b in zip(tots, vals)]
        rows.append(f"| [{code}]({code}_还原.xlsx) | " + " | ".join(map(str, vals)) + " |")
        tpl[code] = {f"{f['层']}:{f['列']}": "" for f in flags
                     if f["处置"] == "待人审" and f.get("列")}
        # 复核页同步 + 清理未引用裁片
        src_html = RUNS / f"{stem}_待核复核包" / "待核清单.html"
        sub = PKG / "待核复核包" / f"{stem}_待核复核包"
        if src_html.exists():
            shutil.copy2(src_html, sub / "待核清单.html")
        if (sub / "待核清单.html").exists():
            html = (sub / "待核清单.html").read_text(encoding="utf-8")
            used = set(re.findall(r'src="([^"]+\.png)"', html))
            for png in sub.glob("*.png"):
                if png.name not in used:
                    png.unlink()

    head = ("| 图号 | 总格数 | 多引擎一致(严格) | 双读采纳 | 读空一致 | 关系式裁定 | "
            "伪差修复 | 用户人审确认 | 助手视觉判读 | 助手视觉核验(用户授权) | "
            "**待人审** | 真厚互证对 |")
    sep = "| " + " --- | " * 11 + "--- |"
    total = ("| 合计 | " + " | ".join(map(str, tots)) + " |")
    rd = PKG / "README_必读.md"
    lines = rd.read_text(encoding="utf-8").splitlines()
    out, i, hit = [], 0, False
    while i < len(lines):
        if lines[i].startswith("| 图号") and not hit:
            out += [head, sep] + rows + [total]
            hit = True
            i += 1
            while i < len(lines) and lines[i].startswith("|"):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    assert hit, "README 未找到分级表表头"
    rd.write_text("\n".join(out) + "\n", encoding="utf-8")
    (PKG / "待核复核包" / "回写模板.json").write_text(
        json.dumps(tpl, ensure_ascii=False, indent=1), encoding="utf-8")
    pend = sum(len(v) for v in tpl.values())
    print(f"打包完成: 4 xlsx + README 分级表(伪差修复列) + 复核包同步;待人审合计 {pend}")


if __name__ == "__main__":
    main()
