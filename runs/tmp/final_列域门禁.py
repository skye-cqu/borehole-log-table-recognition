# -*- coding: utf-8 -*-
"""final 列域门禁(用户指令 2026-11-09):部分列只能出现对应内容,越界必错。

30 张终值表逐列形态白名单:
  深度/层厚/采长/真厚  ^\d+(\.\d+)?$ 或空(纯数值)
  倾角                ^\d+(\.\d+)?\s*°?$ 或空
  煤层标志层号        [0-9]{1,3} | 中文数字[上下]? | — | 空
  地质时代            含中文(地层名)或空
  岩性描述            含中文或空
越界=门禁违例,进修正清单。
"""
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(ROOT))
from openpyxl import load_workbook  # noqa: E402
from openpyxl.cell.rich_text import CellRichText  # noqa: E402

SRC = ROOT / "outputs/Excel交付_终版_20261109"
OUT = ROOT / "runs/autoresearch_align/多源定级_20261106/列域门禁_20261109.json"
if len(sys.argv) > 1:                      # 可选:传入目录则只检不覆盖违例清单
    SRC = Path(sys.argv[1])
    OUT = ROOT / "runs/tmp/_列域门禁_重放.json"

NUM = re.compile(r"^\d+(?:\.\d+)?$")
DIP = re.compile(r"^\d+(?:\.\d+)?\s*°?$")
MARK = re.compile(r"^[0-9]{1,3}|[一二三四五六七八九十]+[上下]?$|^—$")


def txt(v):
    if v is None:
        return ""
    if isinstance(v, CellRichText):
        v = str(v)
    return str(v).strip()


def col_of(hdr, names):
    for j, h in enumerate(hdr):
        if h:
            for n in names:
                if n in str(h):
                    return j, str(h)
    return None, None


viol, checked = [], 0
for p in sorted(glob.glob(str(SRC / "*_整合.xlsx"))):
    stem = Path(p).name.split("_")[0].replace("钻孔柱状图", "")
    wb = load_workbook(p, rich_text=True)
    ws = wb.active
    hdr = [c.value for c in ws[1]]
    spec = {}
    for key, names, pat in (
            ("深度", ("深度",), NUM), ("层厚", ("层厚",), NUM),
            ("采长", ("采长",), NUM), ("真厚", ("真厚",), NUM),
            ("倾角", ("倾角",), DIP),
            ("煤层标志层号", ("煤层标志", "标志层号", "层号"), MARK)):
        c, h = col_of(hdr, names)
        if c is not None:
            spec[c] = (key, pat)
    cEra, _ = col_of(hdr, ("地质时代", "时代"))
    cDesc, _ = col_of(hdr, ("岩性描述", "描述"))
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        for c, (key, pat) in spec.items():
            v = txt(row[c]) if c < len(row) else ""
            if not v:
                continue
            checked += 1
            if not pat.match(v):
                viol.append({"图": stem, "xlsx行": i, "列": key, "值": v[:40]})
        for c, key in ((cEra, "地质时代"), (cDesc, "岩性描述")):
            if c is None:
                continue
            v = txt(row[c]) if c < len(row) else ""
            if not v:
                continue
            checked += 1
            if not re.search(r"[\u4e00-\u9fff]", v):
                viol.append({"图": stem, "xlsx行": i, "列": key, "值": v[:40]})

json.dump(viol, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print(f"检查 {checked} 格, 违例 {len(viol)}")
for k, n in Counter((x['列']) for x in viol).most_common():
    print(" ", k, n)
for x in viol[:30]:
    print(" ", x["图"], "行", x["xlsx行"], x["列"], repr(x["值"]))
print("->", OUT)
