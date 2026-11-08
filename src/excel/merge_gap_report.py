# -*- coding: utf-8 -*-
"""诊断: col1 合并区间是否完整覆盖每个地层块的全部延续行。
数据语义(delivery_blocks 按'空即延续'解析)是对的, 但若合并区没跟上,
视觉上就会出现断裂的空白行。这里只报告, 不改文件。

输入：paths.DELIVERY_XLSX（桌面交付文件，运行前确认存在）。
"""
import sys
from pathlib import Path

import openpyxl

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths

from src.excel import reconstruct_all as R

F = str(paths.DELIVERY_XLSX)


def main():
    wb = openpyxl.load_workbook(F)
    total_gap = 0
    holes = []
    for h in wb.sheetnames:
        ws = wb[h]
        if h == '1032':          # 原图无地质时代列, 豁免
            continue
        blocks = R.delivery_blocks(ws)
        merged = {}
        for m in ws.merged_cells.ranges:
            if m.min_col == 1 and m.max_col == 1:
                merged[m.min_row] = m.max_row
        gaps = []
        for lab, r0, r1 in blocks:
            cur_end = merged.get(r0, r0)      # 未合并则只覆盖自身
            if cur_end < r1:
                gaps.append((lab, r0, cur_end, r1, r1 - cur_end))
        if gaps:
            holes.append(h)
            print('=== %s (数据行%d) ===' % (h, ws.max_row - 1))
            for lab, r0, cur_end, r1, n in gaps:
                print('    %-10s 块=r%d-r%d  但合并只到 r%d  -> %d 行显示为空白'
                      % (lab, r0, r1, cur_end, n))
                total_gap += n

    print()
    print('受影响孔数: %d  /  合计空白行: %d' % (len(holes), total_gap))
    print('孔号:', ' '.join(holes))


if __name__ == "__main__":
    main()
