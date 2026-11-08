# -*- coding: utf-8 -*-
"""交付级整表门禁:每列领域合法性断言,违规=不可交付(退出码 1)。

根因(2026-10-11 诊断):上游 OCR 幻读/行粘连/列错位未经逐格门禁直达用户,
用户历轮指出的缺陷仅占全列扫描违规的 ~12%(805 格 vs ~90 格)。与
src/tools/audit_deliverable.py(结构计数/哨兵)互补:audit 查"格子数够不够、
哨兵清没清",gate 查"每格值是否在领域合法集内"。只读不改。

用法: python -m src.table.delivery_gate   → 打印分类计数,报告 JSON 落
runs/table_整合_全量_20261011/交付门禁_报告.json;违规>0 退出码 1。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock

from src.core import paths

COLS = ["地质时代", "煤层/标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]
LAYER = re.compile(r"^[0-9]+$|^[一二三四五六七八九十]+$|^[一二三四五六七八九十]\s*[上下]$"
                   r"|^十[一二三四五]$|^[0-9]+[上下]$")
DIP = re.compile(r"^\d+(\.\d+)?°$")


NUM_RE = re.compile(r"\d+(?:\.\d+)?")   # 整数/小数;'1.'/'.5' 是 OCR 截断数,拦(1034/1035 实锤)


def _num(v):
    return bool(NUM_RE.fullmatch(str(v).strip()))


def _era(v):
    s = re.sub(r"\s+", "", str(v))
    return bool(s) and not re.search(r"[A-Za-z]", s) and bool(re.search(r"[\u4e00-\u9fff]", s))


def _desc(v):
    s = str(v).strip()
    return not s or not re.match(r"^[。.,;:、]", s)


RULES = {0: _era, 1: lambda v: bool(LAYER.fullmatch(re.sub(r"\s", "", str(v)))),
         2: _num, 3: _num, 4: _num, 5: lambda v: bool(DIP.fullmatch(str(v).strip())),
         6: _num, 7: _desc}


def cell_text(v):
    """rich text → 纯文本;读盘必须 rich_text=True 否则红字结构静默退化(12.6 教训)。"""
    if isinstance(v, CellRichText):
        return "".join(b.text if isinstance(b, TextBlock) else str(b) for b in v)
    return "" if v is None else str(v)


def scan_sheet(ws):
    """返回 [(row, col, 值)] 违规格;MergedCell(合并区非首格)与空格合法。"""
    out = []
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if c.__class__.__name__ == "MergedCell":
                continue
            s = cell_text(c.value).strip()
            if s and not RULES[c.column - 1](s):
                out.append((c.row, c.column, s))
    return out


def scan_dir(d):
    rep = {}
    for p in sorted(Path(d).glob("*_整合.xlsx")):
        rep[p.stem.replace("_整合", "")] = scan_sheet(load_workbook(p, rich_text=True).active)
    return rep


SPECIAL_CHARTS = {1019, 1032, 1042}   # 旧版映射/整图列错位:违规不逐格修,整图降级专项
STUCK = re.compile(r"^-?\d+(?:\.\d+)?\s+[\d.]+")   # 数值列双数串(行粘连形态)


def classify(stem, col, text):
    k = int(re.sub(r"\D", "", stem))
    if k in SPECIAL_CHARTS:
        return "错位专项"
    if col in (3, 4, 5, 7, 8) and STUCK.match(text):
        return "粘连专项"
    return "符号幻读"


def _normalize(v, col):
    """列语义归一:倾角裸数字补°(像素实证 1015 r3 '5°',OCR 丢符号),其余去首尾空。"""
    s = re.sub(r"\s+", "", str(v))
    if col == 6:
        bare = s[:-1] if s.endswith("°") else s
        if re.fullmatch(r"\d+(\.\d+)?", bare):
            return bare + "°"
    return str(v).strip()


def decide(px, ag, col):
    """像素/Agnes 双引擎仲裁(纯函数,TDD):→(动作, 新值, 依据)。
    无墨→清空;像素合法→替换(像素是第一手证据,列语义归一);
    数值列像素读数缺首位('.00'/'.5')或丢小数位('1.')均为 OCR 截断,NUM_RE 判非法
    (打印数值一律带前导0 且点后必有位,1015 r48/1034/1035 像素实证)
    → Agnes 独立读出合法值才替换,否则清空记账;像素非法但 Agnes 合法→替换(记账);
    双非法→清空记账。col=xlsx 列 1-8。"""
    if px is None or not str(px).strip():
        return ("清空", None, "格内无墨")
    pxn = _normalize(px, col)
    px_ok = RULES[col - 1](pxn)
    agn = _normalize(ag, col) if ag and str(ag).strip() else None
    ag_ok = agn is not None and RULES[col - 1](agn)
    if px_ok:
        return ("替换", pxn, "像素读数合法")
    if ag_ok:
        return ("替换", agn, "像素非法,Agnes读数合法")
    return ("清空", None, "双引擎均非法,清空记账")


def main(argv):
    rep = scan_dir(paths.FINALIZE_FULL_DIR)
    cats = {"符号幻读": [], "粘连专项": [], "错位专项": []}
    for stem, items in rep.items():
        for r, c, s in items:
            cats[classify(stem, c, s)].append(
                {"图": stem, "行": r, "列": COLS[c - 1], "值": s[:40]})
    out = paths.FINALIZE_FULL_DIR / "交付门禁_报告.json"
    out.write_text(json.dumps(cats, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(v) for v in cats.values())
    print("门禁违规:", n, {k: len(v) for k, v in cats.items()})
    print("报告:", out)
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
