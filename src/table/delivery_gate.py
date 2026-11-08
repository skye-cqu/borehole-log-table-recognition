# -*- coding: utf-8 -*-
"""交付级整表门禁:每列领域合法性断言,违规=不可交付(退出码 1)。

根因(2026-10-11 诊断):上游 OCR 幻读/行粘连/列错位未经逐格门禁直达用户,
用户历轮指出的缺陷仅占全列扫描违规的 ~12%(805 格 vs ~90 格)。与
src/tools/audit_deliverable.py(结构计数/哨兵)互补:audit 查"格子数够不够、
哨兵清没清",gate 查"每格值是否在领域合法集内"。只读不改。

用法: python -m src.table.delivery_gate   → 打印分类计数,报告 JSON 落
runs/table_整合_全量_20261011/交付门禁_报告.json;违规>0 退出码 1。

口径修正(2026-10-15):规则曾以**硬编码列号 0-7** 为键,而 1032 只有 6 列、
1042 只有 7 列(扫描左缘裁切,时代/煤层标志层号不在图内),导致两图每格都用错
规则判,违规数虚高(491→54)。现改为**按表头名解析角色**再取规则;表头名无法
映射即报错,不静默跳过;整图豁免(SPECIAL_CHARTS)废止。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock

from src.core import paths

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


def _layer(v):
    return bool(LAYER.fullmatch(re.sub(r"\s", "", str(v))))


def _dip(v):
    return bool(DIP.fullmatch(str(v).strip()))


# 角色 → 断言。**按语义角色取规则**,不按列号。
ROLE_RULES = {
    "era": _era, "layer": _layer, "depth": _num, "thick": _num,
    "length": _num, "dip": _dip, "true_thick": _num, "desc": _desc,
}
NUM_ROLES = ("depth", "thick", "length", "true_thick")

# 表头名 → 角色。别名覆盖各图实际写法(含 '煤层/标志层号' 与 '煤层标志层号')。
COL_ALIASES = {
    "地质时代": "era", "时代": "era", "地层时代": "era",
    "煤层/标志层号": "layer", "煤层标志层号": "layer",
    "煤层标志层": "layer", "标志层号": "layer", "煤层": "layer",
    "深度": "depth", "孔深": "depth",
    "层厚": "thick",
    "采长": "length",
    "倾角": "dip",
    "真厚": "true_thick",
    "柱状": "column", "柱状图": "column",
    "岩性描述": "desc", "岩性": "desc",
}

# 历史口径:8 列固定布局的角色序列(仅作 decide/classify 的向后兼容回退)
COLS = ["地质时代", "煤层/标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]
RULES = {i: ROLE_RULES[r] for i, r in enumerate(
    ["era", "layer", "depth", "thick", "length", "dip", "true_thick", "desc"])}


def header_roles(header):
    """表头行 → {1-based xlsx 列号: 角色}。未知名/空名报错(静默跳过正是本缺陷成因)。"""
    out, unknown = {}, []
    for i, h in enumerate(header or ()):
        key = re.sub(r"[\s\u3000]+", "", str(h if h is not None else ""))
        key = key.replace("（", "(").replace("）", ")")
        key = re.sub(r"\((?:m|米)\)$", "", key)
        r = COL_ALIASES.get(key)
        if r:
            out[i + 1] = r
        elif key:
            unknown.append((i + 1, str(h)))
    if unknown:
        raise ValueError(
            "表头名无法映射到门禁规则,拒绝静默跳过: %s(完整表头=%s)"
            % (unknown, list(header or ())))
    if not out:
        raise ValueError("表头行为空,无法解析列角色: %s" % (list(header or ()),))
    return out


def rules_for(ws):
    """工作表 → {1-based 列号: 断言}。以第 1 行表头为准(1032 六列/1042 七列)。"""
    hdr = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    return {c: ROLE_RULES[r] for c, r in header_roles(hdr).items()}


def cell_text(v):
    """rich text → 纯文本;读盘必须 rich_text=True 否则红字结构静默退化(12.6 教训)。"""
    if isinstance(v, CellRichText):
        return "".join(b.text if isinstance(b, TextBlock) else str(b) for b in v)
    return "" if v is None else str(v)


def scan_sheet(ws, rules=None):
    """返回 [(row, col, 值)] 违规格;MergedCell(合并区非首格)与空格合法。

    规则按**表头名**解析(1032 六列/1042 七列,按列号取规则会串列)。
    表头名无法映射时抛 ValueError —— 静默跳过正是本缺陷的成因。"""
    rules = rules if rules is not None else rules_for(ws)
    out = []
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if c.__class__.__name__ == "MergedCell":
                continue
            fn = rules.get(c.column)
            if fn is None:
                raise ValueError(
                    "第 %d 行第 %d 列无对应规则(表头未映射该列),拒绝静默跳过"
                    % (c.row, c.column))
            s = cell_text(c.value).strip()
            if s and not fn(s):
                out.append((c.row, c.column, s))
    return out


_role_of = {}          # (图名, 1-based 列号) → 角色,供归类用


def scan_dir(d):
    """扫目录 → {图名: 违规格};同时填 _role_of 供 classify 用。"""
    rep = {}
    for p in sorted(Path(d).glob("*_整合.xlsx")):
        stem = p.stem.replace("_整合", "")
        ws = load_workbook(p, rich_text=True).active
        hdr = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
        by_col = header_roles(hdr)                       # {列号: 角色}
        for c, r in by_col.items():
            _role_of[(stem, c)] = r
        rules = {c: ROLE_RULES[r] for c, r in by_col.items()}
        rep[stem] = scan_sheet(ws, rules)
    return rep


# 曾经整图豁免的图(旧版映射/整图列错位)。**豁免已废止**:整图不判会让真实
# 违规混在虚高计数里无法分辨(1032 的 345 条里只有 16 条是真的)。
# 名单保留,但只作为**专项归属标签**(见 specialty_of),不再改变违规判定与归类。
SPECIAL_CHARTS = {1019, 1032, 1042}


def specialty_of(stem):
    """图 → 专项归属标签(无则 None)。仅用于分流,**不影响是否判定违规**。"""
    k = int(re.sub(r"\D", "", stem) or 0)
    return "错位专项" if k in SPECIAL_CHARTS else None
STUCK = re.compile(r"^-?\d+(?:\.\d+)?\s+[\d.]+")   # 数值列双数串(行粘连形态)
# 数值列角色(粘连形态只可能出现在数值列)
STUCK_ROLES = set(NUM_ROLES)


def classify(stem, col, text, role=None):
    """违规**按内容**归类:粘连专项 / 符号幻读。

    注意:不再有"整图豁免"分支 —— 每格都判。过去 1019/1032/1042 的任何违规
    都被整图标成"错位专项",导致 1032 里 329 条假违规与 16 条真违规混为一谈。
    图的专项归属改用 specialty_of(),与内容归类正交。"""
    _LEGACY = ["era", "layer", "depth", "thick", "length", "dip", "true_thick", "desc"]
    r = role if role is not None else (_LEGACY[col - 1] if 1 <= col <= 8 else None)
    if r in STUCK_ROLES and STUCK.match(text):
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


def decide(px, ag, col, rule=None):
    """像素/Agnes 双引擎仲裁(纯函数,TDD):→(动作, 新值, 依据)。
    无墨→清空;像素合法→替换(像素是第一手证据,列语义归一);
    数值列像素读数缺首位('.00'/'.5')或丢小数位('1.')均为 OCR 截断,NUM_RE 判非法
    (打印数值一律带前导0 且点后必有位,1015 r48/1034/1035 像素实证)
    → Agnes 独立读出合法值才替换,否则清空记账;像素非法但 Agnes 合法→替换(记账);
    双非法→清空记账。col=xlsx 列 1-8。"""
    if px is None or not str(px).strip():
        return ("清空", None, "格内无墨")
    # col 是 1-based xlsx 列号;缺省回退历史 8 列布局(RULES 以 0-based 为键)
    rule = rule if rule is not None else RULES.get(col - 1)
    pxn = _normalize(px, col)
    px_ok = rule(pxn)
    agn = _normalize(ag, col) if ag and str(ag).strip() else None
    ag_ok = agn is not None and rule(agn)
    if px_ok:
        return ("替换", pxn, "像素读数合法")
    if ag_ok:
        return ("替换", agn, "像素非法,Agnes读数合法")
    return ("清空", None, "双引擎均非法,清空记账")


def main(argv):
    rep = scan_dir(paths.FINALIZE_FULL_DIR)
    cats = {"符号幻读": [], "粘连专项": [], "错位专项": []}
    for stem, items in rep.items():
        spec = specialty_of(stem)
        for r, c, s in items:
            role = _role_of.get((stem, c))
            entry = {"图": stem, "行": r, "列": role or f"第{c}列", "值": s[:40]}
            if spec:
                entry["专项"] = spec
            cats[classify(stem, c, s, role)].append(entry)
    out = paths.FINALIZE_FULL_DIR / "交付门禁_报告.json"
    out.write_text(json.dumps(cats, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(v) for v in cats.values())
    print("门禁违规:", n, {k: len(v) for k, v in cats.items()})
    print("报告:", out)
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
