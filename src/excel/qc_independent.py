# -*- coding: utf-8 -*-
"""独立终检 READ-ONLY。本文件不含 wb.save()。

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

P = str(paths.DELIVERY_XLSX)

EXPECT_HDR = ['地质时代', '煤层/标志层号', '深度(m)', '层厚(m)', '采长(m)', '倾角(°)', '真厚(m)', '岩性描述']
FG = {'飞仙关组', '飞仙关组一段', '飞仙关组二段', '飞仙关组一至二段', '飞仙关组二至一段'}
RANK = {'第四系': 0, '大隆组': 2, '长兴组': 3, '龙潭组上段': 4, '龙潭组中段': 5, '龙潭组下段': 6, '茅口组': 7}
for f in FG:
    RANK[f] = 1
EXEMPT = {'1032'}


def nz(v):
    return v is not None and str(v).strip() != ''


def main():
    wb = openpyxl.load_workbook(P)
    A = []
    B = []
    C = []
    D = []
    E = []
    F = []
    badparse = []
    names = wb.sheetnames

    # ---------- A 结构 ----------
    if len(names) != 30:
        A.append("sheet数=%d 不是30" % len(names))
    want = set(str(i) for i in range(1015, 1045))
    miss = want - set(names)
    extra = set(names) - want
    if miss:
        A.append("缺失孔号:%s" % sorted(miss))
    if extra:
        A.append("多余sheet:%s" % sorted(extra))

    for sn in names:
        ws = wb[sn]
        if ws.max_column != 8:
            A.append("%s: 列数=%s != 8" % (sn, ws.max_column))
        hdr = [ws.cell(1, c).value for c in range(1, 9)]
        if hdr != EXPECT_HDR:
            A.append("%s: 表头不一致 %s" % (sn, hdr))
        for r in range(2, ws.max_row + 1):
            if not any(nz(ws.cell(r, c).value) for c in range(1, 9)):
                A.append("%s r%d: 整行全空" % (sn, r))

    # ---------- B/C ----------
    allblocks = {}
    for sn in names:
        ws = wb[sn]
        mx = ws.max_row
        starts = [r for r in range(2, mx + 1) if nz(ws.cell(r, 1).value)]
        c1m = [m for m in ws.merged_cells.ranges if m.min_col == 1 and m.max_col == 1]

        if sn in EXEMPT:
            if starts or c1m:
                B.append("%s(豁免孔) 预期col1数据区全空且0合并, 实际 非空行=%s 合并数=%d" % (sn, starts, len(c1m)))
            allblocks[sn] = []
            continue

        if not starts:
            B.append("%s: col1 数据区完全为空(非豁免孔)" % sn)
            allblocks[sn] = []
            continue
        if starts[0] != 2:
            B.append("%s: 首块起于 r%d, r2..r%d 无地层覆盖(头部间隙)" % (sn, starts[0], starts[0] - 1))

        blocks = []
        for i, s in enumerate(starts):
            e = starts[i + 1] - 1 if i + 1 < len(starts) else mx
            blocks.append((str(ws.cell(s, 1).value).strip(), s, e))
        allblocks[sn] = blocks

        if blocks[-1][2] != mx:
            B.append("%s: 末块止于 r%d, 未覆盖 max_row=%d" % (sn, blocks[-1][2], mx))

        for lb, s, e in blocks:
            if lb not in RANK:
                B.append("%s r%d: 非标准地层名 '%s'" % (sn, s, lb))

        seq = [(lb, s) for lb, s, e in blocks if lb in RANK]
        for i in range(1, len(seq)):
            if RANK[seq[i][0]] < RANK[seq[i - 1][0]]:
                B.append("%s r%d: 层序倒挂 '%s'(r%d) -> '%s'" % (sn, seq[i][1], seq[i - 1][0], seq[i - 1][1], seq[i][0]))
            elif RANK[seq[i][0]] == RANK[seq[i - 1][0]]:
                B.append("%s r%d: 同级地层重复 '%s' -> '%s' (块被割裂?)" % (sn, seq[i][1], seq[i - 1][0], seq[i][0]))

        covered = {}
        for m in c1m:
            if m.min_row < 2:
                C.append("%s: col1合并 %s 侵入表头" % (sn, m))
            for r in range(m.min_row, m.max_row + 1):
                covered.setdefault(r, []).append(str(m))
        for r in sorted(covered):
            if len(covered[r]) > 1:
                C.append("%s r%d: col1被多个合并区重叠 %s" % (sn, r, covered[r]))

        used = set()
        for lb, s, e in blocks:
            if e == s:
                continue
            exact = [m for m in c1m if m.min_row == s and m.max_row == e]
            if exact:
                used.add(str(exact[0]))
                continue
            part = [str(m) for m in c1m if m.min_row <= e and m.max_row >= s]
            C.append("%s r%d-%d [%s]: 无精确覆盖的col1合并 (相关:%s)" % (sn, s, e, lb, part))
            for r in range(s + 1, e + 1):
                if r not in covered and not nz(ws.cell(r, 1).value):
                    C.append("    -> 孤行 %s r%d (属 %s): 非块首/无合并/自身空" % (sn, r, lb))

        for m in c1m:
            if m.max_row > m.min_row and str(m) not in used:
                if not any(m.min_row == s and m.max_row == e for lb, s, e in blocks):
                    C.append("%s: 错位col1合并 %s 不对应任何地层块" % (sn, m))

    # ---------- D ----------
    tot2 = tot6 = 0
    for sn in names:
        ws = wb[sn]
        mx = ws.max_row
        for col, tag in ((2, 'col2'), (6, 'col6')):
            ms = [m for m in ws.merged_cells.ranges if m.min_col == col and m.max_col == col]
            if col == 2:
                tot2 += len(ms)
            else:
                tot6 += len(ms)
            for m in ms:
                if m.min_row > m.max_row:
                    D.append("%s %s: 起止倒挂 %s" % (sn, tag, m))
                if m.max_row > mx:
                    D.append("%s %s: 合并 %s 超出 max_row=%d" % (sn, tag, m, mx))
                if m.min_row < 2:
                    D.append("%s %s: 合并 %s 侵入表头" % (sn, tag, m))
            cov = {}
            for m in ms:
                for r in range(m.min_row, m.max_row + 1):
                    cov[r] = cov.get(r, 0) + 1
            for r in sorted(cov):
                if cov[r] > 1:
                    D.append("%s %s r%d: 重叠合并" % (sn, tag, r))

    # ---------- E ----------
    for sn in names:
        ws = wb[sn]
        prev = None
        prow = None
        for r in range(2, ws.max_row + 1):
            v = ws.cell(r, 3).value
            if not nz(v):
                badparse.append("%s r%d: col3 为空" % (sn, r))
                continue
            if not isinstance(v, str):
                badparse.append("%s r%d: col3 非字符串型 (%s) 值=%r" % (sn, r, type(v).__name__, v))
            try:
                fv = float(str(v).strip())
            except Exception:
                badparse.append("%s r%d: col3 无法解析 '%s'" % (sn, r, v))
                continue
            if prev is not None and fv < prev:
                E.append("%s r%d: 深度回退 %s -> %s (上一行 r%d)" % (sn, r, prev, fv, prow))
            prev = fv
            prow = r

    # ---------- F ----------
    def lith(ws, r):
        v = ws.cell(r, 8).value
        return str(v).strip() if nz(v) else ""

    for sn in names:
        ws = wb[sn]
        for lb, s, e in allblocks.get(sn, []):
            if lb == '大隆组':
                t = lith(ws, e)
                if '硅质岩' not in t:
                    F.append("%s r%d: 大隆组末行非硅质岩 -> '%s'" % (sn, e, t[:34]))
            elif lb == '茅口组':
                t = lith(ws, s)
                if not re.search(r'灰岩', t):
                    F.append("%s r%d: 茅口组首行非灰岩类 -> '%s'" % (sn, s, t[:34]))
            elif lb == '第四系':
                t = lith(ws, s)
                if not re.search(r'表土|黏土|粘土|坡积|残积|滑坡|土|砂砾', t):
                    F.append("%s r%d: 第四系首行岩性异常 -> '%s'" % (sn, s, t[:34]))
            elif lb == '长兴组':
                for r in range(s, e + 1):
                    t = lith(ws, r)
                    if re.match(r'^煤([：:]|$)', t):
                        F.append("%s r%d: 长兴组内独立煤层 -> '%s'" % (sn, r, t[:34]))

    def dump(tag, lst):
        print("\n===== %s : %d 条 =====" % (tag, len(lst)))
        for x in lst:
            print(" -", x)

    dump("A 结构", A)
    dump("B 块连续性/单调性", B)
    dump("C col1合并覆盖", C)
    dump("D col2/col6合并畸形", D)
    print("    [D] col2合并区总数=%d  col6合并区总数=%d" % (tot2, tot6))
    dump("E 深度回退", E)
    print("    [E] col3 解析/类型/空值 问题 %d 条:" % len(badparse))
    for x in badparse:
        print("     *", x)
    dump("F 岩性交叉矛盾", F)
    print("\n总计: %d" % (len(A) + len(B) + len(C) + len(D) + len(E) + len(badparse) + len(F)))


if __name__ == "__main__":
    main()
