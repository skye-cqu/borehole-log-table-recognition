# -*- coding: utf-8 -*-
"""交付 Excel 打包：把 v4 模板（桌面 1015-1044.xlsx）的 8 列有效值套入
outputs/钻孔柱状图{id}_final_dynamic_llm/ 的 LLM 校正文件，重新合并后输出到桌面。

注意：本组脚本（src/excel/）的操作对象是【桌面外部交付文件】，不属于本项目，
运行前请确认 paths.py 中 EXTERNAL_DESKTOP 下相应文件存在。
"""
import os
import shutil
import sys
import zipfile
from pathlib import Path

import openpyxl

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths

V4 = str(paths.V4_TEMPLATE_XLSX)  # 模板（v4，表头 8 列）
OUT = str(paths.OUTPUTS_DIR)      # 项目交付输出目录
DEST = str(paths.PACKED_DIR)      # 桌面打包目录
ZIP = str(paths.PACKED_ZIP)       # 桌面打包 zip

# v4 列(A-H,1-8) -> 原始列(5,6,7,8,9,10,11,13)
MAP = {1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10, 7: 11, 8: 13}
# v4 中通常纵向合并、需向下填充的列
CARRY = {1, 2, 6}   # A地质时代 B煤层号 F倾角
MERGE_ORIG = [5, 6, 10]  # 写完后按连续相同值重新合并

wbv = None  # main() 内加载（模板文件在桌面，import 时不应加载）


def eff_col(ws, col, maxr):
    out, last = [], None
    for r in range(2, maxr + 1):
        v = ws.cell(row=r, column=col).value
        if v not in (None, ''):
            last = v
        out.append(last)
    return out


def main():
    global wbv
    wbv = openpyxl.load_workbook(V4)  # 模板（v4）
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    os.makedirs(DEST, exist_ok=True)

    for n in range(1015, 1045):
        s = str(n)
        op = os.path.join(OUT, f'钻孔柱状图{s}_final_dynamic_llm', f'钻孔柱状图{s}_llm_corrected.xlsx')
        if not os.path.exists(op):
            print(f'{s}: 原始文件缺失，跳过')
            continue
        wbo = openpyxl.load_workbook(op)
        wso = wbo.active
        wsv = wbv[s]
        vmax = wsv.max_row          # 含表头
        vrows = vmax - 1
        # 读 v4 各列有效值
        vdata = {c: eff_col(wsv, c, vmax) for c in MAP}
        # 原始数据行数
        omax = wso.max_row
        # 拆目标列合并
        for rng in list(wso.merged_cells.ranges):
            if rng.min_col in MAP.values() and rng.min_row >= 2:
                wso.unmerge_cells(str(rng))
        # 写值：v4 行 -> 原始同行(位置1:1)
        for i in range(vrows):
            r = i + 2
            for vc, oc in MAP.items():
                wso.cell(row=r, column=oc).value = vdata[vc][i]
        # 原始多出的行：清空数据列，避免残留旧垃圾
        for r in range(vrows + 2, omax + 1):
            for oc in MAP.values():
                wso.cell(row=r, column=oc).value = None
        # 按连续相同值重新合并 地质时代/煤层号/倾角
        for oc in MERGE_ORIG:
            runs = []
            start = None
            cur = None
            for r in range(2, vrows + 2):
                v = wso.cell(row=r, column=oc).value
                if v != cur:
                    if start is not None and r - 1 > start:
                        runs.append((start, r - 1))
                    start = r
                    cur = v
            if start is not None and (vrows + 1) > start:
                runs.append((start, vrows + 1))
            for a, b in runs:
                wso.merge_cells(start_row=a, start_column=oc, end_row=b, end_column=oc)
        outp = os.path.join(DEST, f'{s}.xlsx')
        wbo.save(outp)
        print(f'{s}: 已写入 {outp} (v4行={vrows}, 原始行={omax})')

    # 打包
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(DEST)):
            if f.endswith('.xlsx'):
                z.write(os.path.join(DEST, f), arcname=f)
    print(f'\n打包完成: {ZIP}')
    print('包含文件:', sorted(os.listdir(DEST)))


if __name__ == "__main__":
    main()
