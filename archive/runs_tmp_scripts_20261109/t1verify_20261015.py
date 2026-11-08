# -*- coding: utf-8 -*-
"""T1 验收:表头无法映射必须报错(反例演示);28张8列表零变化已在上一步证明。"""
import sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from openpyxl import Workbook, load_workbook
from src.table import delivery_gate as dg

print("##### 反例1:表头有无法识别的列名 -> 必须报错")
wb = Workbook(); ws = wb.active
ws.append(["地质时代","煤层标志层号","深度","层厚","采长","倾角","真厚","莫名其妙列"])
ws.append(["第四系","1",1,1,1,"5°",1,"x"])
try:
    dg.scan_sheet(ws)
    print("  失败!静默跳过了")
except ValueError as e:
    print("  OK 报错: %s" % str(e)[:110])

print()
print("##### 反例2:扫描时遇到表头未映射的列 -> 必须报错")
wb2 = Workbook(); ws2 = wb2.active
ws2.append(["深度","层厚"])          # 只声明2列
ws2.cell(row=2, column=3, value="999")   # 第3列有值但表头没有
try:
    dg.scan_sheet(ws2)
    print("  失败!静默跳过了")
except ValueError as e:
    print("  OK 报错: %s" % str(e)[:110])

print()
print("##### 反例3:表头全空 -> 必须报错")
wb3 = Workbook(); ws3 = wb3.active
ws3.append([None, None])
try:
    dg.scan_sheet(ws3)
    print("  失败!")
except ValueError as e:
    print("  OK 报错: %s" % str(e)[:110])

print()
print("##### 正常路径:三张特殊图各自的角色映射")
D = R/"runs"/"table_整合_全量_20261011"
for k in (1032, 1042, 1019, 1023):
    ws = load_workbook(D/f"钻孔柱状图{k}_整合.xlsx", rich_text=True).active
    hdr = [ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)]
    print("  %-5d %s" % (k, dg.header_roles(hdr)))

print()
print("##### classify 不再整图豁免(1032/1042 的真实违规要能归类)")
print("  1032 深度列双数串:", dg.classify("钻孔柱状图1032", 1, "355.95 357.47", "depth"))
print("  1042 倾角幻读:", dg.classify("钻孔柱状图1042", 6, "。9", "dip"))
print("  1019 时代列:", dg.classify("钻孔柱状图1019", 1, "3.7", "era"))
