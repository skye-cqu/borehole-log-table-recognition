# -*- coding: utf-8 -*-
"""手工复刻 tests/test_delivery_gate.py 里 4 个用 tmp_path 的用例
(该 fixture 在本机沙箱下无法建目录 -> PermissionError,是环境问题不是代码问题)。"""
import json, shutil, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from openpyxl import Workbook, load_workbook
from src.table import delivery_gate as dg

T = R/"runs"/"tmp"/"_harness"
shutil.rmtree(T, ignore_errors=True); T.mkdir(parents=True, exist_ok=True)
ok = fail = 0
def chk(name, cond, extra=""):
    global ok, fail
    if cond: ok += 1; print("  PASS %s" % name)
    else: fail += 1; print("  FAIL %s %s" % (name, extra))

def _mk(rows, merged=None, name="t.xlsx"):
    wb = Workbook(); ws = wb.active
    ws.append(["地质时代","煤层/标志层号","深度","层厚","采长","倾角","真厚","岩性描述"])
    for r in rows: ws.append(r)
    for m in (merged or []): ws.merge_cells(m)
    p = T/name; wb.save(p); return load_workbook(p).active

print("== 用例1: 报出各类违规 ==")
ws = _mk([
    ["飞仙关组二至一段","1",12.28,12.28,0,"5°",3,"表土"],
    ["3.7","1",12.83,0.55,3,"。9","MOLO","粉砂质泥岩"],
    ["大隆组","","355.95 357.47",1.52,3,"4°","0.7!","泥岩"],
    ["长兴组","三上",13.0,0.17,"","4°","",""],
])
bad = dg.scan_sheet(ws); got = {(r,c,s) for r,c,s in bad}
chk("(3,1,3.7)", (3,1,"3.7") in got)
chk("(3,6,。9)", (3,6,"。9") in got)
chk("(3,7,MOLO)", (3,7,"MOLO") in got)
chk("(4,3,双数串)", (4,3,"355.95 357.47") in got)
chk("(4,7,0.7!)", (4,7,"0.7!") in got)
chk("合法不报", (2,6,"5°") not in got and (5,2,"三上") not in got)
chk("总数==5", len(bad)==5, "实得 %d" % len(bad))

print("== 用例2: 合并区非首格与空格合法 ==")
ws = _mk([["飞仙关组","1",1,1,1,"5°",1,"x"],[None,None,2,1,1,"5°",1,"y"]], merged=["A2:A3"])
chk("全合法", dg.scan_sheet(ws)==[], str(dg.scan_sheet(ws)))

print("== 用例3: rich_text 值参与判定 ==")
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
wb = Workbook(); ws = wb.active
ws.append(["地质时代","煤层/标志层号","深度","层厚","采长","倾角","真厚","岩性描述"])
ws.append(["第四系","1",1,1,1,"5°",1,""])
c = ws.cell(row=2, column=8)
c.value = CellRichText("泥岩", TextBlock(InlineFont(color="FFFF0000"), "灰"), "岩")
ws.cell(row=3, column=6).value = "。8"
p = T/"r.xlsx"; wb.save(p)
ws2 = load_workbook(p, rich_text=True).active
chk("只有(3,6)违规", [(r,c) for r,c,_ in dg.scan_sheet(ws2)]==[(3,6)],
    str([(r,c) for r,c,_ in dg.scan_sheet(ws2)]))

print("== 用例4: main 违规退出1 / 干净退出0 ==")
_mk([["3.7","1",1,1,1,"。9",1,"x"]], name="钻孔柱状图1015_整合.xlsx")
d1 = T/"run1"; d1.mkdir(exist_ok=True)
shutil.copy(T/"钻孔柱状图1015_整合.xlsx", d1/"钻孔柱状图1015_整合.xlsx")
dg.paths.FINALIZE_FULL_DIR = d1
rc = dg.main([])
chk("退出码1", rc==1, "实得 %d" % rc)
data = json.loads((d1/"交付门禁_报告.json").read_text(encoding="utf-8"))
chk("符号幻读2条", len(data["符号幻读"])==2, str({k:len(v) for k,v in data.items()}))
chk("粘连专项空", data["粘连专项"]==[])
wb = dg.load_workbook(d1/"钻孔柱状图1015_整合.xlsx"); ws2 = wb.active
ws2.cell(row=2,column=1).value="第四系"; ws2.cell(row=2,column=6).value="5°"
wb.save(d1/"钻孔柱状图1015_整合.xlsx")
chk("干净退出0", dg.main([])==0)

print()
print("手工复刻: PASS=%d FAIL=%d" % (ok, fail))
shutil.rmtree(T, ignore_errors=True)
sys.exit(1 if fail else 0)
