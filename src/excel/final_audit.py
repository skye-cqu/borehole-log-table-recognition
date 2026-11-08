# -*- coding: utf-8 -*-
"""交付 Excel 终审（只读）：col1 层序/乱码/居中/合并完整性 + col8 页脚垃圾扫描。

输入：paths.DELIVERY_XLSX（桌面交付文件，运行前确认存在）。
"""
import re
import sys
from pathlib import Path

import openpyxl

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths

F = str(paths.DELIVERY_XLSX)

# ---- 区域标准层序 (young -> old)，经 WebSearch 核实 (织金矿区) ----
ORDER = ["第四系","飞仙关组","飞仙关组一段","飞仙关组二段","飞仙关组一至二段","飞仙关组二至一段",
         "大隆组","长兴组","龙潭组上段","龙潭组中段","龙潭组下段","茅口组"]
RANK = {n: i for i, n in enumerate(ORDER)}
# 标准列名集合：标准层序 + 表头“地质时代”
REAL = set(ORDER) | {"地质时代"}

# OCR 乱码正则：已移除误报项 `潭组下`/`龙潭组下组` 中对“龙潭组下段”的误命中
GARBLED = re.compile(r'茅日|矛口|猫口|茆口|龙潭组0|龙组上|龙组中|龙组下|龙潭组下组|至段|飞仙关组二至段|茅口组茅|龙潭$')

# 页脚/图签垃圾关键词（col8 岩性描述里不该出现）
KW = re.compile(r'总工程师|队长|制图|清绘|审核|贵州省煤|省煤|贵州|织金|矿区|勘探|编制|测量|地质|报告|有限公司|研究院|队')


def main():
    wb = openpyxl.load_workbook(F)
    problems = []
    footer = []
    garbled_names = []
    uncentered = []
    merge_issues = []
    distinct_names = set()

    for ws in wb.worksheets:
        name = ws.title
        # 1) col1 全扫描：乱码 + 非标准名 + 未居中
        for r in range(1, ws.max_row + 1):
            c1 = ws.cell(r, 1).value
            if c1 not in (None, ""):
                distinct_names.add(c1)
                s = str(c1)
                if GARBLED.search(s):
                    garbled_names.append((name, r, c1))
                if c1 not in REAL:
                    problems.append((name, "非标准名", r, c1))
                al = ws.cell(r, 1).alignment
                if not (al.horizontal == "center" and al.vertical == "center"):
                    uncentered.append((name, r, c1, al.horizontal, al.vertical))
        # 2) col8 页脚垃圾
        for r in range(1, ws.max_row + 1):
            c8 = ws.cell(r, 8).value
            if c8 not in (None, ""):
                if KW.search(str(c8)):
                    footer.append((name, r, str(c8)[:30]))
        # 3) 层序单调性 (col1 块，上->下)
        blocks = []
        cur = None
        r0 = None
        for r in range(1, ws.max_row + 1):
            v = ws.cell(r, 1).value
            if v not in (None, ""):
                if v != cur:
                    if cur is not None:
                        blocks.append((cur, r0, r - 1))
                    cur = v
                    r0 = r
        if cur is not None:
            blocks.append((cur, r0, ws.max_row))
        # 已知 F24 逆断层造成地层重复(真实地质现象)，允许 1042 发生一次层序倒挂复位：
        #   龙潭组下段(62-105) > 茅口组(106) > 龙潭组下段(107-111) > 茅口组(112)
        # 这是用户原图口径 + 逆冲重复，非错误，故单次复位豁免。
        fault_resets = {"1042": 1}
        resets_left = fault_resets.get(name, 0)
        prev_rank = -1
        for (lab, a, b) in blocks:
            if lab in RANK:
                rk = RANK[lab]
                if rk < prev_rank:
                    if resets_left > 0:
                        resets_left -= 1
                        prev_rank = rk   # 断层复位后，以下盘层序继续单调检查
                    else:
                        problems.append((name, "层序倒序", f"{lab} r{a}-{b} 出现于更老地层之下"))
                else:
                    prev_rank = max(prev_rank, rk)
        # 4) col1 合并完整性：顶格非空 + 区间内除顶格外无值 + 无重叠
        col1_merges = [m for m in ws.merged_cells.ranges if m.min_col == 1 and m.max_col == 1]
        # 重叠检测
        for i in range(len(col1_merges)):
            for j in range(i + 1, len(col1_merges)):
                mi, mj = col1_merges[i], col1_merges[j]
                if not (mi.max_row < mj.min_row or mj.max_row < mi.min_row):
                    merge_issues.append((name, "合并重叠", str(mi), str(mj)))
        for m in col1_merges:
            top = ws.cell(m.min_row, 1).value
            if top in (None, ""):
                merge_issues.append((name, "合并顶格为空", str(m)))
            for rr in range(m.min_row + 1, m.max_row + 1):
                if ws.cell(rr, 1).value not in (None, ""):
                    merge_issues.append((name, "合并内非顶格有值", str(m), rr, ws.cell(rr, 1).value))

    print("非标准名/问题:", len(problems), problems[:20])
    print("残留乱码:", len(garbled_names), garbled_names[:10])
    print("未居中(col1):", len(uncentered), uncentered[:10])
    print("页脚残留(col8):", len(footer), footer[:10])
    print("合并问题:", len(merge_issues), merge_issues[:20])
    print("\n=== 交付文件 col1 全部出现的不同文本 ===")
    for n in sorted(distinct_names):
        print("   ", repr(n))
    print("\n=== sheet 数:", len(wb.worksheets), "===")
    print("\n=== 若 非标准名=0 / 残留乱码=0 / 未居中=0 / 页脚=0 / 合并问题=0 则结构通过 ===")


if __name__ == "__main__":
    main()
