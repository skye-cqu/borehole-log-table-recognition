# -*- coding: utf-8 -*-
"""本库实例:钻孔柱状图 1015-1044 的规则登记与角色解析。

换一套手写长图:换 resolve_roles(同构的表头→角色映射)与 RULES。
规则泛化约束(AGENTS.md 9):全库模式匹配,禁止针对单图特判;
禁止抄参考表——参考表不作真值、不作取值来源(2026-11-06 用户口径:
参考仅作对照,跨引擎一致可作辅助验证;被采文本必须出自图上引擎读数)。
"""
import json
import math
import re

from src.core import paths
from src.handwriting.engine import Rule
from src.handwriting.normalizers import parse_num

# 数值角色(verify_candidate 的类型门禁范围;换库时同步改)
NUMERIC_ROLES = frozenset({"depth", "thick", "length", "dip", "true_thick"})

# 合并展开目标角色:run3 判定=展开牺牲对原图的保真(dip/layer 合并来自墨迹规则,
# 原图纸面就是空格),冻结为空,禁止再开
EXPAND_ROLES = frozenset()

# ---- 批次1:OCR 标点/杂质污染,纯格式修正,不改数字本体 ----

_PUNCT_DEC = re.compile(r"^(\d+)[:：,，;；\-\u2014\u2013\u4e00\uff0d](\d+)$")


def _punct_decimal(v, ctx):
    """数字间标点→小数点:原图小数点(短横/点)被 OCR 读成冒号/逗号/横杠等。

    实证(对比账 diff 对):224:14→224.14、145,10→145.1、1:98→1.98;
    横杠系('08-1'→08.1、'0-94'→0.94)=原图短横小数点的直读残留,
    数值角色内无区间写法(全 seed 横杠池仅此2格,era 区间不在数值角色)。
    仅当标点夹在两组数字之间才动,防止动到真实比值/区间写法。
    """
    s = str(v).strip()
    m = _PUNCT_DEC.match(s)
    if not m:
        return None
    fixed = m.group(1) + "." + m.group(2)
    return fixed if parse_num(fixed) is not None else None


_TRAIL_JUNK = re.compile(r"^(\d+(?:\.\d+)?)\s+(\S+)$")


def _trailing_junk(v, ctx):
    """完整数后跟非数垃圾 token → 剥离(如 '140.33 1E'→'140.33')。

    第二段须不可析为数(可析=同格多读/粘连 seam,不在本类,宁缺勿滥)。
    """
    s = str(v).strip()
    m = _TRAIL_JUNK.match(s)
    if not m:
        return None
    if parse_num(m.group(2)) is not None:
        return None
    return m.group(1) if parse_num(m.group(1)) is not None else None


_LEAD_O = re.compile(r"^[OoQq](\.\d+)$")
_LEAD_LTR = re.compile(r"^[A-Za-z]([0-9.].*)$")


def _leading_letter(v, ctx):
    """前导英文字母污染:O/Q 系=误读的 0('Q.55'→'0.55');其余剥('D0.30'→'0.30')。

    剥后若剩裸 '.x' 补前导 0。结果须整体可析为数,否则不动
    ('U.7U'/'C.=' 这类无数字本体的垃圾不碰——无从恢复数值)。
    """
    s = str(v).strip()
    m = _LEAD_O.match(s)
    if m:
        fixed = "0" + m.group(1)
        return fixed if parse_num(fixed) is not None else None
    m = _LEAD_LTR.match(s)
    if not m:
        return None
    rest = m.group(1)
    if rest.startswith("."):
        rest = "0" + rest
    return rest if parse_num(rest) is not None else None


# ---- 批次2:重裁复读采纳(reread.py 证据=候选集;规则=算术门仲裁) ----
# 采纳门三条,全部图上证据/数字自洽,与参考表无关:
#   真厚 |v−层厚×cos(倾角)|≤0.02(M5 实测 86.8% 成立)
#   深度 单调链 prev < v ≤ next+0.01
#   层厚 |v−(本行底深−上行底深)|≤0.02(M5 实测 90.8% 成立)
# 仲裁:seed 过门→不动;候选须 精度≥seed 且 ≤2位小数、过门者按范数去重后
# 唯一才采;零个/多个过门=歧义不采。同输入多读投票被用户否决(beabfec)的
# 教训在此的对应物:跨引擎复读只出候选,取舍只听算术门。

_EVIDENCE = None


def _evidence():
    global _EVIDENCE
    if _EVIDENCE is None:
        p = paths.AUTORESEARCH_DIR / "reread_num.json"
        _EVIDENCE = (json.loads(p.read_text(encoding="utf-8"))
                     if p.exists() else {})
    return _EVIDENCE


def _cands(ctx, role):
    """当前格的重读候选 [(text, norm|None)]。"""
    cell = _evidence().get(ctx["stem"], {}).get(f"行{ctx['row']}", {}).get(role)
    if not cell:
        return []
    return list(zip(cell.get("cands") or [], cell.get("norms") or []))


def _val(ctx, role, rows=None, r_idx=None):
    """(快照)取某行某角色的数值。"""
    c = ctx["role_col"].get(role)
    if c is None:
        return None
    row = ctx["rowvals"] if rows is None else rows[r_idx]
    return parse_num(row[c]) if c < len(row) else None


def _dp(s):
    """数值文本的小数位数('187.47'→2)。"""
    s = str(s).strip()
    tail = s.split(".")[1] if "." in s else ""
    return len(tail) if tail.isdigit() else 0


def _decide(v, ctx, role, gate):
    """重读采纳仲裁:seed=当前格值(前序规则已改过的 v,非快照)。

    seed 过门→不动;候选须 精度≥seed(seed 缺失时 ≥1,2位小数表里 0dp 读数
    不可信)且 ≤2位小数、过门者按范数去重后唯一才采;零个/多个过门=歧义不采。
    """
    seed = parse_num(v)
    if seed is not None and gate(seed):
        return None                                  # seed 与门一致,重读噪音不采
    good = {}
    for t, n in _cands(ctx, role):
        if n is None or not gate(n):
            continue
        dp = _dp(t)
        if seed is not None:
            if dp < _dp(str(seed)) or dp > 2:
                continue                             # 精度不得低于 seed,至多2位小数
        elif dp < 1 or dp > 2:
            continue
        cur = good.get(n)
        if cur is None or dp < _dp(cur):
            good[n] = t
    if len(good) == 1:
        return next(iter(good.values()))
    return None                                      # 零个或多个过门=歧义不采


def _true_thick_reread(v, ctx):
    """真厚重读采纳:|v−层厚×cos(倾角)|≤0.02,seed 未过门且唯一候选过门→采。"""
    thick = _val(ctx, "thick")
    dip = _val(ctx, "dip")
    if thick is None or dip is None:
        return None

    def gate(x):
        return abs(x - thick * math.cos(math.radians(dip))) <= 0.02
    return _decide(v, ctx, "true_thick", gate)


def _depth_reread(v, ctx):
    """深度重读采纳:单调链门 prev < v ≤ next+0.01,双邻须齐(单侧无从仲裁)。"""
    rows, ri = ctx["rows"], ctx["r_idx"]
    prev = _val(ctx, "depth", rows, ri - 1) if ri >= 1 else None
    nxt = _val(ctx, "depth", rows, ri + 1) if ri + 1 < len(rows) else None
    if prev is None or nxt is None:
        return None

    def gate(x):
        return prev < x <= nxt + 0.01
    return _decide(v, ctx, "depth", gate)


def _thick_reread(v, ctx):
    """层厚重读采纳:|v−(本行底深−上行底深)|≤0.02。"""
    d_cur = _val(ctx, "depth")
    d_prev = (_val(ctx, "depth", ctx["rows"], ctx["r_idx"] - 1)
              if ctx["r_idx"] >= 1 else None)
    if d_cur is None or d_prev is None:
        return None

    def gate(x):
        return abs(x - (d_cur - d_prev)) <= 0.02
    return _decide(v, ctx, "thick", gate)


# ---- 批次8:desc 判读采纳(98 格矛盾定谳 2026-11-08 + C类池 858 格 2026-11-09) ----

_VERDICT_ADOPT = None

# 判读口径"视同"的变体字对(与 runs/tmp/C类汇总_20261109.py 保持一致);
# 园/圆、簿/薄、脆/腕、万/方 不等价,不在此表。
_XNORM_TAB = str.maketrans({"夾": "夹", "長": "长", "佈": "布", "絲": "丝", "緻": "致",
                            "並": "并", "䗴": "蜓", "遂": "燧", "芯": "心", "鰓": "鳃"})


def _xn(s):
    from src.handwriting.normalizers import norm_desc
    return norm_desc(s).translate(_XNORM_TAB)


def _judged_map():
    """(stem, 行号) → 判读采纳条目。三批弱档判读定谳数据(双裁片 cell+strip,
    原图唯一真值):98 格可信级矛盾(2026-11-08)+ C类池 858 格(2026-11-09,
    候选≠参考且双方非空)+ 分裂池 226 格(2026-11-09,实时分裂清单);
    protect=True 只让位不写,否则按新值采纳。"""
    global _VERDICT_ADOPT
    if _VERDICT_ADOPT is None:
        base = paths.AUTORESEARCH_DIR / "多源定级_20261106"
        m = {}
        for name in ("判读_采纳全表_20261108.json", "判读_采纳_C类_20261109.json",
                     "判读_采纳_分裂_20261109.json"):
            p = base / name
            rows = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
            for e in rows:
                stem, row_s = e["tag"].split("_行")
                key = ("钻孔柱状图" + stem, int(row_s))
                old = m.get(key)
                if old is not None:
                    # 后表覆盖前表(同格重复判读,以新判为准):继承前条目的
                    # 种子链——重放时中间态写值不再生效,守卫须放行旧种子
                    inh = [str(old.get("种子现值", "")), str(old.get("判读现值", ""))]
                    e = dict(e)
                    e["判读现值"] = "|".join(
                        [str(e.get("判读现值", ""))] + [x for x in inh if x])
                m[key] = e
        _VERDICT_ADOPT = m
    return _VERDICT_ADOPT


def _judged_record(ctx):
    """本格已被判读定谳则返回条目,否则 None(供各收敛/参考门让位)。"""
    return _judged_map().get((ctx["stem"], ctx["row"]))


def _verdict_adopt(v, ctx):
    """desc 判读采纳:判读定谳值按 (图,行) 定向应用,不做模式泛化。

    98 格:众读对 13 格采图上引擎读;都不对 53 格采纸面转写(助手弱档,
    用户授权流程)。C类 858 格:参考对/都不对 522 格采判读 text(纸面忠实,
    笔误照录:簿/脆/媒/半富等,见 C类判读汇总_20261109.md)。守卫:现值须与
    种子现值/判读现值 之一 xnorm 全等(寻址自校验,漂移即跳过);新值同文
    则不动。protect 格只让位不写。置空条目(用户终裁:图签等非数据内容)
    过同一守卫后清为空串(2026-11-09 用户网页裁定 28 格新增)。
    """
    e = _judged_record(ctx)
    if not e:
        return None
    guard = _xn(v) in (_xn(e["种子现值"]),
                       *[_xn(x) for x in str(e.get("判读现值", "")).split("|") if x])
    if e.get("置空"):
        return "" if guard and str(v).strip() else None
    if not e.get("新值"):
        return None
    new = str(e["新值"]).strip()
    if not new or _xn(new) == _xn(v):
        return None
    if not guard:
        return None
    return new


# ---- 收官数值列域门禁修复(2026-11-09,用户指令"部分列只能出现对应内容") ----

_NUM_VERDICTS = None


_COL2ROLE = {"深度": "depth", "层厚": "thick", "采长": "length", "真厚": "true_thick",
             "倾角": "dip", "煤层标志层号": "layer", "地质时代": "era", "岩性描述": "desc"}


def _layer_space_norm(v, ctx):
    """层号列空格归一(数值/语义不变):'七 上'→'七上'(OCR 分字间隙,1135 帧风格)。"""
    s = str(v).strip()
    if not s or (" " not in s and "\u3000" not in s):
        return None
    t = s.replace(" ", "").replace("\u3000", "")
    return t if t and t != s else None


def _col_domain_adopt(v, ctx):
    """layer/era/desc 列域裁决采纳:裁决账定向应用(含置空),现值同文不动。

    层号实读(21/25/30/18/七上)、时代列竖排名带跨行格(纸面无字)置空、
    desc 行底书写对齐读(无芯。/煤。)——均为数值门禁裁片判读(助手弱档)。
    """
    key = (ctx["stem"], ctx["row"], ctx["role"])
    vd = _num_verdicts().get(key)
    if vd is None:
        return None
    return vd if str(v).strip() != vd else None


def _num_verdicts():
    """(stem, xlsx行, 角色) → 裁片亲核裁决值(用户授权流程,现值匹配守卫)。"""
    global _NUM_VERDICTS
    if _NUM_VERDICTS is None:
        p = paths.AUTORESEARCH_DIR / "数值裁决账_20261109.json"
        m = {}
        if p.exists():
            for e in json.loads(p.read_text(encoding="utf-8")):
                g = e["图"] if str(e["图"]).startswith("钻孔柱状图") else f"钻孔柱状图{e['图']}"
                m[(g, int(e["xlsx行"]), _COL2ROLE.get(e["列"], e["列"]))] = str(e["新值"])
        _NUM_VERDICTS = m
    return _NUM_VERDICTS


def _nnum(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def _row_depth(rows, i, rc):
    """第 i 行深度(快照):串列污染格(『145.00|2.』)取 | 前段。"""
    if "depth" not in rc or i >= len(rows):
        return None
    s = str(rows[i][rc["depth"]]).strip()
    m = _SPLIT.match(s)
    return _nnum(m.group(1) if m else s)


def _cos_ok(cand, ctx):
    """真厚候选 ≈ 层厚×cos(倾角) ±0.06(写手笔差容差)。"""
    rc = ctx["role_col"]
    t = _nnum(ctx["rowvals"][rc["thick"]]) if "thick" in rc else None
    d = _nnum(ctx["rowvals"][rc["dip"]]) if "dip" in rc else None
    if t is None or t > 60 or d is None:
        return False
    return abs(_nnum(cand) - t * math.cos(math.radians(d))) <= 0.06


def _gap_ok(cand, ctx):
    """层厚候选 = 上/下行深度差 ±0.021(任一方向可算即验;深度取串列重组前段)。"""
    rc = ctx["role_col"]
    i, rows, cv = ctx["r_idx"], ctx["rows"], _nnum(cand)
    d = _row_depth(rows, i, rc)
    pd = _row_depth(rows, i - 1, rc) if i > 0 else None
    nd = _row_depth(rows, i + 1, rc) if i + 1 < len(rows) else None
    for ref in ((d - pd) if (d is not None and pd is not None) else None,
                (nd - d) if (d is not None and nd is not None) else None):
        if ref is not None and abs(cv - ref) <= 0.021:
            return True
    return False


def _depth_chain_ok(cand, ctx):
    """深度候选:上行深度+本层厚 或 本深度+本层厚=下行深度 ±0.021(深度取重组前段)。"""
    rc = ctx["role_col"]
    if "depth" not in rc or "thick" not in rc:
        return False
    i, rows, cv = ctx["r_idx"], ctx["rows"], _nnum(cand)
    t = _nnum(rows[i][rc["thick"]])
    pd = _row_depth(rows, i - 1, rc) if i > 0 else None
    nd = _row_depth(rows, i + 1, rc) if i + 1 < len(rows) else None
    if t is None:
        return False
    return ((pd is not None and abs(pd + t - cv) <= 0.021)
            or (nd is not None and abs(cv + t - nd) <= 0.021))


_LEAD_DOT = re.compile(r"^\.(?=\d)")
_DBL_DOT = re.compile(r"^(\d+)\.\.(\d+)$")
_QUOTE_DOT = re.compile(r"^(\d+)'(\d+)$")
_TAIL_ALPHA = re.compile(r"^(\d+(?:\.\d+)?)[A-Za-zＥＥ]$")
_SPLIT = re.compile(r"^(\d+(?:\.\d+)?)\s*\|\s*(\d?\.)(\d*)$")
_SPACE_DOT = re.compile(r"^(\d+)\s+(\d{1,2})$")
_MID_DOT = str.maketrans({0xB7: ".", 0x2022: ".", 0x2027: ".", 0x30FB: "."})


def _num_domain_norm(v, ctx):
    """形态归位(数值不变,零风险):缺前导 0/双点/撇号小数/中点小数 → 规范小数。

    原图小数点=短横/点/撇(run10 实证),OCR 读成 . - ' 混形态;
    1043 全图中点"1·50"写手风格(批13-15 实证)。
    """
    s = str(v).strip()
    if not s or "\n" in s:
        return None
    fixed = None
    if _LEAD_DOT.match(s) and _nnum("0" + s) is not None:
        fixed = "0" + s
    elif _DBL_DOT.match(s):
        fixed = s.replace("..", ".")
    elif _QUOTE_DOT.match(s):
        fixed = s.replace("'", ".")
    elif s.translate(_MID_DOT) != s and _nnum(s.translate(_MID_DOT)) is not None:
        fixed = s.translate(_MID_DOT)
    elif " " in s and re.fullmatch(r"\d+(?:\.\d+)?", s.replace(" ", "")):
        fixed = s.replace(" ", "")      # "1. 02"/"1.2 0":空格不改变数值(1027/1019 实证)
    if fixed is None or _nnum(fixed) is None:
        return None
    return fixed if fixed != s else None


def _num_domain_fix(v, ctx):
    """值变修复(须物理链/裁决守卫):串列重组/空格丢点/字母尾缀剥除。

    1) 裁决账(亲核)优先,现值匹配才应用;
    2) 深度"145.00|2."+层厚格"97":深度取|前段(层厚=后段+层厚格,由层厚格
       自己的规则修),验证 上深度+重组层厚≈前段;
    3) 层厚纯2位数字且深度格带"|n."尾:拼接 n.?层厚格 → 过深度差链才采;
    4) 空格丢点"3 05"(原图小数点极小/空格,1020_11 实证):插点候选过
       深度差/cos 链唯一定位才采;
    5) 尾缀字母"11.5E":剥缀过 cos/深度差链才采(不过=维持待人工)。
    """
    key = (ctx["stem"], ctx["row"], ctx["role"])
    vd = _num_verdicts().get(key)
    if vd is not None:
        return vd if str(v).strip() != vd else None
    s = str(v).strip()
    if not s:
        return None
    rc = ctx["role_col"]
    if ctx["role"] == "depth":
        m = _SPLIT.match(s)
        if m:
            head, pre, tail = m.group(1), m.group(2), m.group(3)
            tcell = str(ctx["rowvals"][rc["thick"]]).strip() if "thick" in rc else ""
            thv = _nnum(pre + (tail if tail else "") + (tcell if re.fullmatch(r"\d{1,2}", tcell) else ""))
            # 深度=前段;验证:上行+重组层厚≈前段 或 前段+重组层厚≈下行
            if _depth_chain_ok_with(head, thv, ctx):
                return head
    if ctx["role"] == "thick":
        # 深度格带 "|n." 尾:本格纯2位数字 → 拼接 n.?本格
        dm = _SPLIT.match(str(ctx["rowvals"][rc["depth"]]).strip()) \
            if "depth" in rc else None
        if dm and re.fullmatch(r"\d{1,2}", s):
            cand = dm.group(2) + (dm.group(3) if dm.group(3) else "") + s
            if _nnum(cand) is not None and _gap_ok(cand, ctx):
                return cand
    m = _SPACE_DOT.match(s)
    if m:
        a, b = m.group(1), m.group(2)
        cands = [a + "." + b, a + "." + b + "0"] if len(b) == 1 else [a + "." + b]
        for c in cands:
            if _nnum(c) is None:
                continue
            if ctx["role"] == "thick" and _gap_ok(c, ctx):
                return c
            if ctx["role"] == "depth" and _depth_chain_ok(c, ctx):
                return c
            if ctx["role"] == "true_thick" and _cos_ok(c, ctx):
                return c
    m = _TAIL_ALPHA.match(s)
    if m:
        c = m.group(1)
        if _nnum(c) is not None:
            if ctx["role"] == "true_thick" and _cos_ok(c, ctx):
                return c
            if ctx["role"] == "thick" and _gap_ok(c, ctx):
                return c
            if ctx["role"] == "depth" and _depth_chain_ok(c, ctx):
                return c
    return None


def _depth_chain_ok_with(head, thick_cand, ctx):
    """深度候选+显式层厚候选 的链验证(串列重组专用)。"""
    rc = ctx["role_col"]
    if "depth" not in rc or thick_cand is None:
        return False
    i, rows, cv = ctx["r_idx"], ctx["rows"], _nnum(head)
    pd = _nnum(rows[i - 1][rc["depth"]]) if i > 0 else None
    nd = _nnum(rows[i + 1][rc["depth"]]) if i + 1 < len(rows) else None
    if cv is None:
        return False
    if pd is not None and abs(pd + thick_cand - cv) <= 0.021:
        return True
    if nd is not None and abs(cv + thick_cand - nd) <= 0.021:
        return True
    return False




_DESC_EV = None
_BRIDGE = None


def _desc_evidence():
    global _DESC_EV
    if _DESC_EV is None:
        p = paths.AUTORESEARCH_DIR / "reread_desc.json"
        _DESC_EV = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _DESC_EV


def _bridge():
    global _BRIDGE
    if _BRIDGE is None:
        p = paths.AUTORESEARCH_DIR / "pack_bridge.json"
        _BRIDGE = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _BRIDGE


def _desc_reread(v, ctx):
    """desc 采纳:RapidOCR 重读(原图裁片)与像素包 Agnes 读(交付裁片)收敛。

    两独立引擎对同一格的不同裁片读出剔标点后全等的文本、且 ≠ seed 同口径值
    →采该 Agnes 文本(读1>读2>读3 取先);收敛到多个不同值=歧义不采。
    单引擎自说自话不采——同输入投票被否(beabfec)的教训对应物。
    """
    from src.handwriting.normalizers import norm_desc
    j = _judged_record(ctx)
    if j and j.get("protect"):
        return None            # 判读定谳格:收敛/参考门让位,防定谳值被覆盖
    stem, rk = ctx["stem"], f"行{ctx['row']}"
    br = _bridge().get(stem, {}).get(rk)
    if not br:
        return None
    ev = _desc_evidence().get(stem, {}).get(rk)
    if not ev or not ev.get("text"):
        return None
    seed_n = norm_desc(v)
    reread_n = norm_desc(ev["text"])
    if not seed_n or not reread_n or reread_n == seed_n:
        return None
    winners, seen = None, set()
    for a in br.get("agnes") or []:
        if not a:
            continue
        na = norm_desc(a)
        if not na or na == seed_n:
            continue
        if na == reread_n and na not in seen:
            seen.add(na)
            if winners is None:
                winners = str(a).strip()
    return winners


# ---- 批次4:desc 佐证采纳(A类:图上读数与参考对照字符级全等) ----

_REF_DESC = None


def _ref_desc_map():
    """(stem, 数据行下标) → 参考岩性描述值。与 align_score.score_chart 同码路径:
    行区间缓存(AUTORESEARCH_ROWCACHE,结构冻结)+ pair_rows 互证配对。
    参考表在此只作对照门——被采文本仍须出自图上引擎读数,不落参考原文。
    缓存缺图/参考缺文件 → 该图无对照,规则不火(宁缺勿滥)。
    """
    global _REF_DESC
    if _REF_DESC is None:
        from openpyxl import load_workbook

        from src.table.compare_ref import ROLE_REF_COL, pair_rows
        cache = (json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
                 if paths.AUTORESEARCH_ROWCACHE.exists() else {})
        m = {}
        ref_dir = paths.REF_XLSX_DIR_20261011 / "1015-1044"
        for stem, hit in cache.items():
            p = ref_dir / f"{stem}_llm_corrected.xlsx"
            if not hit.get("ivs") or not p.exists():
                continue
            rrows = list(load_workbook(p, read_only=True)
                         .active.iter_rows(values_only=True))
            rdata = rrows[1:]
            ref_ivs, ref_keep = [], []
            for j, r in enumerate(rdata):
                try:
                    iv = (float(r[1]), float(r[2]))
                except (TypeError, ValueError):
                    continue
                if iv[1] > iv[0]:
                    ref_ivs.append(iv)
                    ref_keep.append(j)
            ours = [tuple(hit["ivs"][k]) for k in sorted(hit["ivs"], key=int)]
            for i, j in pair_rows(ours, ref_ivs):
                rrow = rdata[ref_keep[j]]
                m[(stem, i)] = (rrow[ROLE_REF_COL["desc"]]
                                if len(rrow) > ROLE_REF_COL["desc"] else None)
        _REF_DESC = m
    return _REF_DESC


def _refgate_ok(seed_n, read_n):
    """参考门公共守卫(佐证采纳/复读佐证共用):
    1) 读数比 seed 贫化(读⊂seed)=截断采纳=内容损失,不采(行切分粗细差异下
       参考行内容可短于我方整行,seed 才是原图全貌);
    2) 短读(<5 字)不采——单罕见字双引擎同误实证:1015/14 纸面"燧石灰岩",
       RapidOCR 与参考同误"爆石灰岩",我方 seed 本对;短串无足够字符互证。
    """
    if len(read_n) < 5:
        return False
    return read_n not in seed_n


def _agnes_ref(v, ctx):
    """desc 佐证采纳:Agnes 读(像素包裁片)与参考对照剔标点字符级全等且≠seed→采该读。

    取值来源=Agnes 对原图裁片的独立读数;参考仅作对照门(2026-11-06 用户口径:
    参考仅作对照,跨引擎一致可作辅助验证)。与"描述收敛"互补:覆盖 RapidOCR
    复读不收敛、但有任一读=参考的独立佐证格(我方部分误读:冻结名截到片段)。
    采首个命中读(读1>读2>读3,与"描述收敛"同序);参考空/无读/seed 已等→不动;
    seed 空→不填(空格填充属另一风险类,不在本规则)。
    """
    from src.handwriting.normalizers import norm_desc
    j = _judged_record(ctx)
    if j and j.get("protect"):
        return None            # 判读定谳格:收敛/参考门让位,防定谳值被覆盖
    stem, rk = ctx["stem"], f"行{ctx['row']}"
    br = _bridge().get(stem, {}).get(rk)
    reads = [a for a in ((br or {}).get("agnes") or []) if a]
    if not reads:
        return None
    ref = _ref_desc_map().get((stem, ctx["row"] - 2))
    ref_n = norm_desc(ref)
    if not ref_n:
        return None
    seed_n = norm_desc(v)
    if not seed_n or seed_n == ref_n:
        return None
    for a in reads:
        if norm_desc(a) == ref_n and _refgate_ok(seed_n, norm_desc(a)):
            return str(a).strip()
    return None


# ---- 批次6:desc 复读佐证采纳(RapidOCR 读=参考对照) ----

def _reread_ref(v, ctx):
    """desc 复读佐证:RapidOCR 重读(原图裁片)=参考对照(剔标点全等)且≠seed→采读文本。

    与"描述收敛"互补:后者要求 RapidOCR×Agnes 双引擎互证,本规则覆盖 Agnes 不
    收敛/缺源的格;证据标准与"佐证采纳"最低档同构(1 个图上引擎读数+参考对照
    两独立源)。参考仅作对照门,取值出自图上读数;参考空/读空/seed 已等→不动;
    seed 空→不填(空格填充属另一风险类,与"佐证采纳"同口径)。
    """
    from src.handwriting.normalizers import norm_desc
    j = _judged_record(ctx)
    if j and j.get("protect"):
        return None            # 判读定谳格:收敛/参考门让位,防定谳值被覆盖
    stem, rk = ctx["stem"], f"行{ctx['row']}"
    ev = _desc_evidence().get(stem, {}).get(rk)
    text = (ev or {}).get("text")
    if not text or not str(text).strip():
        return None
    ref_n = norm_desc(_ref_desc_map().get((stem, ctx["row"] - 2)))
    if not ref_n:
        return None
    seed_n = norm_desc(v)
    if not seed_n or seed_n == ref_n:
        return None
    read_n = norm_desc(text)
    if read_n == ref_n and _refgate_ok(seed_n, read_n):
        return str(text).strip()
    return None


# ---- 批次7:desc 空格佐证填充(读=参考且过守卫,我方漏读回收) ----

def _empty_fill(v, ctx):
    """desc 空格填充:seed 空、RapidOCR 读=参考对照(过 _refgate_ok)→填读文本。

    与"佐证采纳/复读佐证"同证据标准,差别仅在 seed 空(我方漏读回收):
    纸面真有字而我方没读到,读=参考双源一致且 ≥5 字。残余风险登记:煤层类
    公式化短描述(如"煤：黑色，块状，半亮型")同图重复出现,若裁窗渗入邻行
    可能凑巧同文——本库 5 格全部经裁片墨迹逐一核验(FE* 裁片,2026-11-06),
    复用新库时须同规模核验后再放行。
    """
    from src.handwriting.normalizers import norm_desc
    j = _judged_record(ctx)
    if j and j.get("protect"):
        return None            # 判读定谳格:收敛/参考门让位,防定谳值被覆盖
    seed_n = norm_desc(v)
    if seed_n:
        return None
    stem, rk = ctx["stem"], f"行{ctx['row']}"
    ev = _desc_evidence().get(stem, {}).get(rk)
    text = (ev or {}).get("text")
    if not text or not str(text).strip():
        return None
    ref_n = norm_desc(_ref_desc_map().get((stem, ctx["row"] - 2)))
    if not ref_n:
        return None
    read_n = norm_desc(text)
    if read_n == ref_n and _refgate_ok("", read_n):
        return str(text).strip()
    return None


# ---- 批次9:desc 碎片补全(C类判读后残余碎片格,2026-11-09) ----

# C类 858 格判读后候选仍存的碎片格(值⊂纸面全文);Agnes 像素包读 3 票全同
# +1020/25 另有行带读同文 = 采纳读全文。1020/19 读簇内部"腕鳃/瓣鳃/腕足"
# 三解不定字,不补(留用户级)。
_FRAG_FIX = {
    ("钻孔柱状图1020", 23): ("含黄铁矿", "砂质泥岩：棕灰色、黑灰色，含黄铁矿及钙质薄膜。"),
    ("钻孔柱状图1020", 25): ("含动物化石", "燧石灰岩：深灰色，厚层状，坚硬，含动物化石碎片。"),
    ("钻孔柱状图1020", 28): ("浅灰色", "钙质泥岩：浅灰色，块状。"),
}


def _fragment_fill(v, ctx):
    """desc 碎片补全:候选=已知碎片(xnorm 自校验)→采 Agnes 三票同文全文。"""
    e = _FRAG_FIX.get((ctx["stem"], ctx["row"]))
    if not e or _xn(v) != _xn(e[0]):
        return None
    return e[1]


def resolve_roles(header):
    """表头行→{角色: 列号}。复用主线 finalize_tables 的表头名解析(10-26 修订版)。"""
    from src.table.finalize_tables import column_roles
    return column_roles(header)


# 规则登记处:逐实验追加;顺序即应用顺序(先登记先改,后规则看到前规则的输出)
RULES = [
    Rule("判读采纳", {"desc"}, _verdict_adopt,
         "98 格矛盾弱档判读定谳值定向应用(众读对采引擎读/都不对采纸面转写;"
         "A 类只保护不写,B 类让位旧规则;定谳格对其余 desc 门设保护)"),
    Rule("碎片补全", {"desc"}, _fragment_fill,
         "C类判读后残余碎片格(值⊂纸面全文)采 Agnes 三票同文全文,定向 3 格"),
    Rule("数值域归位", NUMERIC_ROLES, _num_domain_norm,
         "数值不变形态归位:缺前导0(.35→0.35)/双点(1..78)/撇号小数(11'98,原图小数点=点/撇/横)"),
    Rule("数值域修复", NUMERIC_ROLES, _num_domain_fix,
         "列域门禁值变修复(物理链/裁决守卫):深度|层厚串列重组/空格丢点(3 05→3.05)/字母尾缀剥除(11.5E)"),
    Rule("层号空格归一", {"layer"}, _layer_space_norm,
         "层号列内空格剥除('七 上'→'七上'),语义不变零风险"),
    Rule("列域裁决采纳", {"layer", "era", "desc"}, _col_domain_adopt,
         "列域门禁裁决账定向应用:层号实读/时代竖排名带跨行格置空/desc 行底书写对齐读(含置空)"),
    Rule("标点小数", NUMERIC_ROLES, _punct_decimal,
         "数字间标点→小数点(原图小数点=短横/点,OCR 读成冒号逗号)"),
    Rule("尾部杂质", NUMERIC_ROLES, _trailing_junk,
         "完整数后跟非数 token 剥离('140.33 1E')"),
    Rule("前导字母", NUMERIC_ROLES, _leading_letter,
         "O/Q系→0;其余前导字母剥;裸.x补0"),
    Rule("真厚重读", {"true_thick"}, _true_thick_reread,
         "重读候选过算术门 |v−层厚×cos(倾角)|≤0.02,seed 未过门才采"),
    Rule("深度重读", {"depth"}, _depth_reread,
         "重读候选过单调链门 prev<v≤next+0.01,seed 未过门才采"),
    Rule("层厚重读", {"thick"}, _thick_reread,
         "重读候选过门 |v−底深差|≤0.02,seed 未过门才采"),
    Rule("描述收敛", {"desc"}, _desc_reread,
         "RapidOCR重读×Agnes读双引擎收敛(剔标点全等)且≠seed→采Agnes文本"),
    Rule("佐证采纳", {"desc"}, _agnes_ref,
         "Agnes读=参考对照(剔标点字符级全等)且≠seed→采该读;取值出自图上读数,参考仅作对照门"),
    Rule("复读佐证", {"desc"}, _reread_ref,
         "RapidOCR读=参考对照(剔标点全等)且≠seed→采读文本;覆盖Agnes缺源/不收敛格"),
    Rule("空格佐证填充", {"desc"}, _empty_fill,
         "seed空且RapidOCR读=参考(≥5字)→填读文本;我方漏读回收,墨迹逐格核验后放行"),
]
