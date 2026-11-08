# -*- coding: utf-8 -*-
"""新旧重出表对比(2026-10-25):20261023(列线修复后) vs 20261005B(项④,上一版)。

只读对比,逐图逐格:行数、每格值(float 按数值比,字符串去空格比)。
预期:8 张修复名单图有差(列界动过→切格变→OCR 读数可能变),其余 22 张应零差。
输出:逐图差异数 + 差异格明细(前若干条),汇总打印。
"""
import json
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "runs/table_reconstruct_重出_20261005_项④行线补全"
NEW = ROOT / "runs/table_reconstruct_重出_20261023_列线修复"
REPAIRED = {"1019", "1023", "1024", "1030", "1031", "1033", "1035", "1042"}

MAX_SHOW = 6


def load(p):
    ws = load_workbook(p).active
    return [list(r) for r in ws.iter_rows(values_only=True)]


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    sa = str(a or "").replace(" ", "")
    sb = str(b or "").replace(" ", "")
    return sa == sb


def main():
    olds = {p.name: p for p in OLD.glob("*_还原.xlsx")}
    news = {p.name: p for p in NEW.glob("*_还原.xlsx")}
    miss = sorted(set(olds) ^ set(news))
    if miss:
        print("!! 文件清单不对称:", miss)
    total_diff = 0
    detail = {}
    for name in sorted(set(olds) & set(news)):
        stem = name.split("钻孔柱状图")[1][:4]
        o, n = load(olds[name]), load(news[name])
        diffs = []
        if len(o) != len(n):
            diffs.append(("行数", f"{len(o)-1}", f"{len(n)-1}"))
        hdr = n[0] if n else []
        for ri in range(min(len(o), len(n))):
            ro, rn = o[ri] or [], n[ri] or []
            for ci in range(max(len(ro), len(rn))):
                vo = ro[ci] if ci < len(ro) else None
                vn = rn[ci] if ci < len(rn) else None
                if not same(vo, vn):
                    col = str(hdr[ci]) if ci < len(hdr) else f"col{ci}"
                    diffs.append((f"行{ri} {col}", vo, vn))
        total_diff += len(diffs)
        tag = "修复图" if stem in REPAIRED else ""
        if diffs:
            detail[name] = (tag, diffs)
        print(f"{stem} {tag}: 行 {len(o)-1}→{len(n)-1}, 差异格 {len(diffs)}")
    print(f"\n合计差异格 {total_diff}")
    print("=== 非修复图的差异(应为空) ===")
    any_bad = False
    for name, (tag, diffs) in detail.items():
        if tag:
            continue
        any_bad = True
        print(name, diffs[:MAX_SHOW])
    if not any_bad:
        print("(无)")
    print("=== 修复图差异明细(每图前 6 条) ===")
    for name, (tag, diffs) in detail.items():
        if not tag:
            continue
        print(name)
        for d in diffs[:MAX_SHOW]:
            print("  ", d)
    (ROOT / "runs/tmp/对比_新旧重出_20261025.json").write_text(
        json.dumps({k: {"tag": v[0], "diffs": v[1]} for k, v in detail.items()},
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("明细已落 runs/tmp/对比_新旧重出_20261025.json")


if __name__ == "__main__":
    main()
