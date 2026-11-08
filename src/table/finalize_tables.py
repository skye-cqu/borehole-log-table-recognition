# -*- coding: utf-8 -*-
"""整合表管线:合并单元格(时代列 rowspan)+ 列特征校验 + 语义校正接线。

纯函数在本模块;Agnes 调用在 agnes_post;xlsx 写出在 finalize(stem)。
判据出处:
- 行→带分组 = 时代名带 y 区间(era_chars 定稿)对行中点 y 最近归属,带间空隙
  (时代界行)归最近带——时代列是 rowspan 列,一层一行切格即根因,合并即修复。
- 深度单调/层厚=Δ深度 = 钻孔柱状图数值列固有特征(终深累计、层厚即相邻终深差,
  1016 前五层实测核验);偏差>容差=疑似丢小数点/串行。
- 时代序 = 标准地层阶序(教科书级:川东南煤田柱状图常见单元),未知名不判不编造。
"""
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 地层单元阶序 (系索引, 组索引):系索引自新到老递增(第四系0→二叠系6),组索引在系内
# 自新到老递增(如二叠系:大隆0→长兴1→龙潭2→茅口3)。柱状图自上而下=自新到老,序须不减。
# 只收教科书级常见单元(川东南煤田柱状图常见集合),未知名不判(约束:不编造)。
ERA_RANK = {
    "第四系": (0, 0), "新近系": (1, 0), "古近系": (2, 0), "白垩系": (3, 0),
    "侏罗系": (4, 0), "蓬莱镇组": (4, 0), "遂宁组": (4, 1), "沙溪庙组": (4, 2),
    "自流井组": (4, 3), "三叠系": (5, 0), "须家河组": (5, 0), "嘉陵江组": (5, 1),
    "飞仙关组": (5, 2), "二叠系": (6, 0), "大隆组": (6, 0), "长兴组": (6, 1),
    "龙潭组": (6, 2), "吴家坪组": (6, 2), "茅口组": (6, 3), "栖霞组": (6, 4),
    "梁山组": (6, 5), "石炭系": (7, 0), "泥盆系": (8, 0), "志留系": (9, 0),
    "奥陶系": (10, 0), "寒武系": (11, 0), "震旦系": (12, 0),
}
THICK_TOL = 0.015   # 层厚 vs Δ深度 容差:两位小数表的舍入量级(≤0.015≈末位1.5)


def rows_to_era_groups(rows_y, bands):
    """行中点 y → 时代名带 (带序号, 行号列表):带间空隙(时代界行)归最近带。

    rows_y 升序;bands=[{name,y0,y1},...](era_chars 定稿序)。
    返回 [(带序号, [行号...]), ...] 按行序分组;无带时 [(None, 全部行)]。
    """
    if not bands:
        return [(None, list(range(len(rows_y))))] if rows_y else []

    def dist(y, b):
        return max(b["y0"] - y, 0, y - b["y1"])

    assign = [min(range(len(bands)),
                  key=lambda k: (dist(y, bands[k]), k)) for y in rows_y]
    groups = []
    for i, k in enumerate(assign):
        if groups and groups[-1][0] == k:
            groups[-1][1].append(i)
        else:
            groups.append((k, [i]))
    return groups


def _f(v):
    """单元格→float(空/串/非数返回 None)。"""
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None


def check_depth_monotonic(depths):
    """终深须自上而下严格不减(钻孔越打越深);空/非数格跳过不判。返回 [{行,问题,上,下}]。"""
    ds = [_f(v) for v in depths]
    return [{"行": i, "问题": "深度逆序", "上": ds[i - 1], "下": ds[i]}
            for i in range(1, len(ds))
            if ds[i] is not None and ds[i - 1] is not None
            and ds[i] < ds[i - 1]]


def check_thickness_delta(depths, thicks, tol=THICK_TOL):
    """层厚 ≈ 相邻终深差(首行=本层终深)。空/非数格跳过。超出容差=疑似丢小数点/串行。"""
    problems = []
    ds, ts = [_f(v) for v in depths], [_f(v) for v in thicks]
    for i in range(len(ds)):
        if ds[i] is None or ts[i] is None:
            continue
        expect = ds[i] if i == 0 or ds[i - 1] is None else ds[i] - ds[i - 1]
        if abs(ts[i] - expect) > tol:
            problems.append({"行": i, "问题": "层厚≠深度差", "层厚": ts[i],
                             "深度差": round(expect, 3), "差": round(ts[i] - expect, 3)})
    return problems


def _rank(name):
    for key, rk in ERA_RANK.items():
        if key in name:
            return rk
    return None


def check_era_sequence(names):
    """时代带自上而下的地层阶序须不减(倒转=误读/串带;缺系=不整合,合法不判)。

    未知名(查不到 ERA_RANK)不判——不编造。返回 [{带,问题,上,下}]。
    """
    problems = []
    for i in range(1, len(names)):
        r0, r1 = _rank(names[i - 1]), _rank(names[i])
        if r0 is None or r1 is None:
            continue
        if r1 < r0:
            problems.append({"带": i, "问题": "系序倒转" if r1[0] < r0[0] else "组序倒转",
                             "上": names[i - 1], "下": names[i]})
    return problems


def _edit_dist1(a, b):
    """Levenshtein 距离恰为 1(名短,直接 DP)。"""
    if abs(len(a) - len(b)) > 1:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] == 1


def repair_cross_chart(chart_names, min_votes=2, dominate=3):
    """跨图 1 编辑距多数决:本图名与他图 ≥min_votes 张的名距离恰 1 → 采纳。

    压倒口径(全量实测:龙组中段×3 互抱变体 vs 龙潭组中段×16 真名):最高票候选须
    ≥dominate×次名票 且 ≥dominate×互证数(他图原样出现本图名=互证)才采;近票/歧义
    一律只记账。返回 (修复后的 dict, ledger):ledger 条目 {图,原,新,依据,应用}。
    """
    charts = {s: list(ns) for s, ns in chart_names.items()}
    ledger = []
    for stem, names in charts.items():
        others = [n for s2, ns in charts.items() if s2 != stem for n in ns]
        for bi, n in enumerate(names):
            corr = others.count(n)                # 互证数(他图原样出现本名)
            votes = {}
            for m in set(others):
                if m != n and _edit_dist1(n, m):
                    votes[m] = sum(1 for s2, ns in charts.items()
                                   if s2 != stem and m in ns)
            ranked = sorted(votes.items(), key=lambda kv: -kv[1])
            v1 = ranked[0][1] if ranked else 0
            v2 = ranked[1][1] if len(ranked) > 1 else 0
            if v1 >= min_votes and v1 >= dominate * v2 and v1 >= dominate * corr:
                charts[stem][bi] = ranked[0][0]
                why = f"跨图1编辑距多数决({v1}票"
                if corr:
                    why += f",压倒互证{corr}"
                if v2:
                    why += f",压倒次名{v2}"
                ledger.append({"图": stem, "带": bi, "原": n, "新": ranked[0][0],
                               "依据": why + ")", "应用": 1})
            elif ranked and corr == 0:
                # 有互证=名在他图原样成立,不记账;无互证且未压倒才是真存疑
                ledger.append({"图": stem, "带": bi, "原": n, "新": "",
                               "依据": f"候选{ranked[:3]}互证{corr},未压倒不采",
                               "应用": 0})
    return charts, ledger


def agnes_adopt_decision(local_name, read_name):
    """Agnes 复读采纳策略:(是否采用, 理由)。

    本地文法 valid 时分歧只记账(1022"石二至一段"教训:双引擎各错一半,盲采即回归);
    本地 invalid/suspect 才采 valid 的 Agnes 读数(漏字/碎片正是 Agnes 补位处)。
    """
    from src.table.era_chars import parse_era_name
    v_read, why_read = parse_era_name(read_name)
    if v_read != "valid":
        return False, f"Agnes复读{read_name}文法{v_read}({why_read}),未应用"
    v_local, _ = parse_era_name(local_name)
    if v_local == "valid":
        return False, "两引擎分歧,只记账待裁"
    return True, "Agnes视觉复读(本地invalid),文法valid"


HEADER_ROW = re.compile(r"^地\s*质\s*时\s*代$")

NUMPAIR = re.compile(r"^(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)$")

# 表头名 → 角色(与 delivery_gate.COL_RULES 同源口径)。历史硬编码列号
# (倾角=5/描述=7/NUM=(2,3,4,6))只在 8 列表上成立;1032 为 6 列、1042 为 7 列
# (扫描左缘裁切,时代/层号两列不在图内,用户已确认),按列号取值会串列,
# 重跑 1032 直接 IndexError。故一律先由表头行解析角色再取列。
COL_ALIASES = {
    "地质时代": "era", "时代": "era", "地层时代": "era",
    "煤层标志层号": "layer", "煤层标志层": "layer", "标志层号": "layer",
    "深度": "depth", "孔深": "depth",
    "层厚": "thick",
    "采长": "length",
    "倾角": "dip",
    "真厚": "true_thick",
    "柱状": "column", "柱状图": "column",
    "岩性描述": "desc", "岩性": "desc",
}
NUM_ROLES = ("depth", "thick", "length", "true_thick")


def column_roles(header):
    """表头行 → {角色: 0-based 列下标}。未知名忽略;缺列的角色不出现在结果里。"""
    out = {}
    for i, h in enumerate(header or ()):
        key = re.sub(r"[\s\u3000]+", "", str(h if h is not None else ""))
        key = key.replace("（", "(").replace("）", ")").replace("·", "")
        key = re.sub(r"\((?:m|米)\)$", "", key).replace("/", "")
        r = COL_ALIASES.get(key)
        if r and r not in out:
            out[r] = i
    return out


def num_cols(roles):
    """数值列下标集合(升序;仅集合语义,消费方都按 set/字典用)。
    表头无法解析时回退历史硬编码 (2,3,4,6)。"""
    if roles and "depth" in roles:
        cols = tuple(sorted(roles[r] for r in NUM_ROLES if r in roles))
        if cols:
            return cols
    return (2, 3, 4, 6)


def normalize_dip_column(ws, ledger, roles=None):
    """倾角列格式归一:裸数字(如"5")补 "°"。像素实证 1015 行3 原图为"5°",
    B 目录 OCR 丢符号;数值不动,非数字(空/文字)不编造。12.6 旧管线步骤
    (2026-10-11 22:16 账实证"同列格式归一补°")在 T4 重构中丢失,本函数恢复;
    逐格记账(来源=规则)。返回改动格数。倾角列号由 roles 解析,缺则回退列6。"""
    di = (roles or {}).get("dip")
    di = 5 if di is None else di
    n = 0
    for row in ws.iter_rows(min_row=2):
        c = row[di]                                     # 倾角列(表头名解析)
        if c.__class__.__name__ == "MergedCell":
            continue
        old = c.value
        new = add_degree_symbol(old)
        if new is None or str(old).strip() == new:
            continue
        c.value = new
        ledger.append({"行": c.row - 2, "列": "倾角", "原": str(old), "新": new,
                       "依据": "同列格式归一补°(像素实证1015行3原图5°,B目录OCR丢符号)",
                       "来源": "规则", "应用": 1})
        n += 1
    return n


def unstuck_chain(data, rows_b, roles=None):
    """行粘连重建(原图眼验定性 2026-10-11:1037 r42-46、1035 r36、1044 r75、1037 r79):
    B 目录行切分漂移,数值列(深度/层厚/采长/真厚)多值并格。三形态分账:
    情形B 多值+下一行数值全空且描述非空(描述独立行)→ 拆,末值行待②吃描述;
    情形A ≥3 数值列多值+深度链全闭合(第j深度-第j层厚==第j-1深度,j≥1)→ 拆 n 行
      (1035 r36 两行/1029 r41 四行,原图实锤);2 值列链不闭但 k=(差)/层厚 为 10 的幂
      = 深度丢小数点,按 k 还原后拆(1044 r75 '29556/29646'÷100,记账);
    碎片串写 恰 2 值且下行自有深度('0.23 79'/'1.0 08' 类跨行 OCR 碎片)
      → 留首值弃碎片只记账,不拆(拆则造重复行,1037 r79 教训);
      ≥3 值且链不闭 → 原样保留记账(疑粘连不拆,留给像素仲裁/人审)。
    ③ 双值首值==最近次值行深度 → 首值为重复表达,弃,次值承接单值列。
    返回 (new_data, new_rows_b, ops, ledger);ops 的 split 值为次行值列表(可多行),
    finalize 物理手术:同 xlsx 行先 over 后 split,全局按行号逆序应用;
    ledger 为校正账条目 dict。行界:拆行按 n 均分区间,保持连续。"""
    NUM = num_cols(roles)
    D_DEPTH = (roles or {}).get("depth", 2)     # 深度列(链判据全用它)
    D_DESC = (roles or {}).get("desc", 7)       # 描述列
    D_DIP = (roles or {}).get("dip", 5)
    D_ERA = (roles or {}).get("era", 0)
    D_LAYER = (roles or {}).get("layer", 1)
    WIDTH = len(data[0]) if data else 0
    TOK = re.compile(r"^-?\d+(?:\.\d+)?$")

    def at(row, i):
        """越界安全取值:1032 只有 6 列,按列号直取会 IndexError。"""
        return row[i] if 0 <= i < len(row) else None

    def set_at(row, i, v):
        if 0 <= i < len(row):
            row[i] = v

    def vals_of(row):
        m = {}
        for c in NUM:
            v = at(row, c)
            if v is None:
                continue
            toks = str(v).strip().split()
            if len(toks) >= 2 and all(TOK.match(t) for t in toks):
                m[c] = toks
        return m

    def empty_num(row):
        return all(at(row, c) in (None, "") for c in NUM)

    def _f(v):
        try:
            return float(str(v))
        except (TypeError, ValueError):
            return None

    out, ops, ledger = [data[0]], [], []
    bounds = []                    # 每产出行一个 top 界,末尾补总底
    last_second = None             # 最近次值行(dict):② 待回填,③ 重复首值判定
    fed = False                    # 该次值行描述已回填
    for i in range(len(data) - 1):
        row = data[i + 1]
        top = rows_b[i] if i < len(rows_b) else rows_b[-1]
        mv = vals_of(row)
        if not mv and empty_num(row) and str(at(row, D_DESC) or "").strip():
            if last_second is not None and not fed:     # ② 描述独立行 → 回填(保留供③)
                set_at(last_second, D_DESC, at(row, D_DESC))
                fed = True
                ops.append(("drop", i + 2, None))       # 该物理行删除
            else:
                out.append(row)
                bounds.append(top)
            continue
        if mv:
            n = max(len(t) for t in mv.values())
            rows_n = [list(row) for _ in range(n)]      # n 个拆出行
            for c, toks in mv.items():
                for j in range(n):
                    rows_n[j][c] = toks[j] if j < len(toks) else None
            if n == 2 and last_second is not None and _f(at(rows_n[0], D_DEPTH)) is not None \
                    and _f(at(last_second, D_DEPTH)) is not None \
                    and abs(float(at(rows_n[0], D_DEPTH)) - float(at(last_second, D_DEPTH))) < 1e-9:
                second = rows_n[1]
                for _c, _d in ((D_ERA, D_ERA), (D_LAYER, D_LAYER),
                               (D_DIP, D_DIP), (D_DESC, D_DESC)):
                    set_at(second, _c, at(row, _d))
                out.append(second)                      # ③ 弃重复首值,D 承接
                bounds.append(top)
                ops.append(("over", i + 2, second))
                last_second, fed = None, False
                continue
            nxt = data[i + 2] if i + 2 < len(data) else None
            case_b = nxt is not None and empty_num(nxt) and str(at(nxt, D_DESC) or "").strip()
            restore = 0
            case_a = False
            if len(mv) >= 3 and D_DEPTH in mv and (roles or {}).get("thick", 3) in mv:
                ds = [_f(t) for t in mv[D_DEPTH]]
                ts = [_f(t) for t in mv[(roles or {}).get("thick", 3)]]
                if n == 2:
                    d1, d2, t2 = ds[0], ds[1], ts[1]
                    if None not in (d1, d2, t2) and t2 > 0:
                        if abs(d2 - t2 - d1) < 0.05:
                            case_a = True
                        else:
                            k = (d2 - d1) / t2
                            kp = int(round(k))
                            if kp in (10, 100, 1000) and abs(k - kp) < 1e-6:
                                case_a, restore = True, kp  # 深度丢小数点,链闭合定 k
                else:
                    case_a = all(
                        None not in (ds[j], ds[j - 1], ts[j]) and ts[j] > 0
                        and abs(ds[j] - ts[j] - ds[j - 1]) < 0.05
                        for j in range(1, n))
            if case_b or case_a:
                if restore:
                    set_at(rows_n[0], D_DEPTH, f"{ds[0] / restore:g}")
                    set_at(rows_n[1], D_DEPTH, f"{ds[1] / restore:g}")
                    ledger.append({"行": str(i + 2), "列": "深度",
                                   "原": f"{mv[D_DEPTH][0]}|{mv[D_DEPTH][1]}",
                                   "新": f"{at(rows_n[0], D_DEPTH)}|{at(rows_n[1], D_DEPTH)}",
                                   "依据": f"深度链闭合定小数点÷{restore}",
                                   "来源": "行粘连重建", "应用": 1})
                for j in range(1, n):                   # 次行:未多值数值列/单值列全清
                    for c in NUM:
                        if c not in mv:
                            set_at(rows_n[j], c, None)
                    for _c in (D_ERA, D_LAYER, D_DIP, D_DESC):
                        set_at(rows_n[j], _c, None)
                out.append(rows_n[0])
                bounds.append(top)
                for j in range(1, n):                   # 拆:n 均分区间
                    out.append(rows_n[j])
                    nxt_b = rows_b[i + 1] if i + 1 < len(rows_b) else top + 1
                    bounds.append(top + (nxt_b - top) * j / n)
                ops.append(("over", i + 2, rows_n[0]))  # 原行覆写为首值(不覆写则串残留)
                ops.append(("split", i + 2, rows_n[1:]))
                last_second, fed = (rows_n[-1], False) if case_b else (None, False)
            elif n == 2:                                # 碎片串写:留首值弃次值
                out.append(rows_n[0])
                bounds.append(top)
                ops.append(("over", i + 2, rows_n[0]))
                ledger.append({"行": str(i + 2), "列": "数值列",
                               "原": " ".join(mv[c][1] for c in sorted(mv)),
                               "新": "", "依据": "碎片串写(下行自有深度),弃次值",
                               "来源": "行粘连重建", "应用": 1})
                last_second, fed = None, False
            else:                                       # ≥3 值链不闭:原样留,记账待裁
                out.append(row)
                bounds.append(top)
                ledger.append({"行": str(i + 2), "列": "数值列",
                               "原": str(at(row, D_DEPTH))[:40], "新": "",
                               "依据": f"疑粘连{n}值但链不闭合,不拆待裁",
                               "来源": "行粘连重建", "应用": 0})
                last_second, fed = None, False
        else:
            out.append(row)
            bounds.append(top)
    bounds.append(rows_b[-1] if rows_b else 0)
    return out, bounds, ops, ledger


def drop_header_rows(data, rows_b):
    """剔除 B 目录混进数据区的表头文字行(1030:表头映射带底浅于实际表头,
    行切分把表头带下部当首数据行)。rows_b=行界列表(len==len(data)),数据行 i
    的顶界=rows_b[i];剔行连顶界同删,底界留作下行顶界;幂等。
    返回 (data, rows_b, dropped_xlsx_rows)——dropped 供 ws.delete_rows 物理删行
    (finalize 在 B 目录还原表 ws 上就地改,不删物理行则表头文字仍留在表内)。"""
    drop = set()
    for i in range(1, len(data)):
        v = str(data[i][0]) if data[i] and data[i][0] is not None else ""
        if HEADER_ROW.match(re.sub(r"\s+", "", v)):
            drop.add(i - 1)                     # 数据行 i-1 的顶界下标
    if not drop:
        return data, rows_b, []
    keep_d = [data[0]] + [data[j] for j in range(1, len(data)) if (j - 1) not in drop]
    keep_b = [rows_b[i] for i in range(len(rows_b)) if i not in drop]
    return keep_d, keep_b, sorted(d + 2 for d in drop)


def add_degree_symbol(v):
    """倾角列格式归一:裸数字(如"5")补 "°"。像素实证 1015 行3 原图为"5°",
    B 目录 OCR 丢符号;数值不动,非数字(空/文字)不编造。"""
    s = str(v).strip() if v is not None else ""
    if not s:
        return None
    try:
        float(s)
    except ValueError:
        return s
    return s + "°"


def flags_wireless(flags_has_line):
    """像素判定账(有线=True,None=存疑)→ value_merge_spans 入参(无线=True)。
    语义转换独立成函数+测试:曾因两侧语义相反未对齐,把有线界当合并界全并错。"""
    return [None if f is None else (not f) for f in flags_has_line]


def value_merge_spans(flags, val_rows):
    """层号/倾角列合并区(值管辖规则):段从值行起,沿无线界向下延伸,
    止于有线界(None 同)或下一值行前——段内至多一值行,合并零丢值。
    flags=无线语义(True=无线,None=存疑按有线,经 flags_wireless 转换);
    val_rows=值行(0 基);返回 [(a,b)](0 基双闭),单行不返回。
    不做无线全并:层号列值格间原图无线,全并会把下一层号值吞进上一段。"""
    vs = sorted(val_rows)
    spans = []
    for i, v in enumerate(vs):
        end = vs[i + 1] if i + 1 < len(vs) else len(flags) + 1
        b = v
        while b < end - 1 and b < len(flags) and flags[b]:
            b += 1
        if b > v:
            spans.append((v, b))
    return spans


def join_split_bands(bands):
    """名带分裂接续:相邻 A=`^.+组$` + B=`^段$` 合并为 A+"段"(y 并集)。

    现场实证(1026):"下"字块 OCR 空读(y[18726,18766] 正常字高但 ocr="")把
    龙潭组|段 劈成两带——空读是墨迹未读出,不是带界。返回 (bands, ledger)。
    """
    import re
    out, ledger = [], []
    for b in bands:
        if (out and re.fullmatch(r".+组", out[-1]["name"])
                and b["name"] == "段"):
            a = out[-1]
            ledger.append({"原": f'{a["name"]}|段', "新": a["name"] + "段",
                           "依据": "名带分裂接续(组段间空读字块)"})
            out[-1] = {"name": a["name"] + "段", "y0": a["y0"], "y1": b["y1"]}
        else:
            out.append(dict(b))
    return out, ledger


def fill_missing_qualifier(bands):
    """组段限定字补全:`^(.+组)段$` 且同前缀 `[上中下]段` 邻带在场、
    {上,中,下}-在场 恰剩一个才补(用户口径:根据地质特征补;不足唯一=不编造)。
    返回 (bands, ledger)。"""
    import re
    out, ledger = [dict(b) for b in bands], []
    for i, b in enumerate(out):
        m = re.fullmatch(r"(.+组)段", b["name"])
        if not m:
            continue
        prefix = m.group(1)
        present = {mm.group(1) for x in out if (mm := re.fullmatch(re.escape(prefix) + r"([上中下])段", x["name"]))}
        missing = {"上", "中", "下"} - present
        if len(missing) == 1:
            old = b["name"]                       # 先存:b 是 out[i] 同一引用,改名后即新值
            q = missing.pop()
            out[i]["name"] = prefix + q + "段"
            ledger.append({"原": old, "新": out[i]["name"],
                           "依据": f"限定字按上中下次序唯一缺补全(同组在场:{''.join(sorted(present))})",
                           "应用": 1})
    return out, ledger


def apply_user_verdicts(chart_names, verdicts):
    """用户裁决落地:按 图+原 精确匹配替换名带(用户赢一切,最后执行)。

    原值对不上当前名=漂移,只记账不应用。返回 (names, ledger)。
    """
    names = {s: list(ns) for s, ns in chart_names.items()}
    ledger = []
    for v in verdicts:
        stem, old, new = v["图"], v["原"], v["新"]
        if stem not in names:
            continue
        ns = names[stem]
        if old in ns:
            bi = ns.index(old)
            ns[bi] = new
            ledger.append({"图": stem, "带": bi, "原": old, "新": new, "来源": "用户裁决",
                           "依据": v.get("依据", "用户裁决"), "应用": 1})
        else:
            ledger.append({"图": stem, "原": old, "新": new, "来源": "用户裁决",
                           "依据": f"裁决原值与当前名不符({ns}),未应用", "应用": 0})
    return names, ledger


# ---- 整合执行(xlsx 读改写 + Agnes 接线;CLI 见 main) ----

ERA_READ_PROMPT = ("图中是钻孔柱状图时代列的一个名带,竖排汉字自上而下,中间可能有分隔横线。"
                   "只输出 JSON:{\"text\": \"自上而下连写的名\"},不要其他内容。")

DESC_PROMPT = """你是地质钻孔柱状图"岩性描述"列的 OCR 校对员。下面是同一张图连续若干行的描述文本(行号: 文本)。
该列 OCR 常见形误:形近字(士/土、在/石、混/泥、爽/夹)、音近字、繁体/异体字、多余空格、标点缺失。
规则(违反即编造,严禁):
1. 只修明显 OCR 形误,改后须与岩性术语吻合(如"表士"→"表土"、"化在"→"化石");
2. 不得增删地质事实/数字/层号,不得改写句式,不得补充解释;
3. 数字与单位一律不动;
4. 繁体/异体字转简体,"依据"注明"繁转简";
5. 拿不准一律不改,宁缺勿改。
只输出 JSON 数组:[{"i":行号,"原":"当前文本","改":"改后全文","依据":"X→X"}],无改动输出 [],不要其他内容。
文本清单:
"""


def _era_band_crop(gray, sp_l, sp_r, y0, y1, seg_h=1200):
    """名带条带裁片:列界折线取带,切 seg_h 段横排拼图(竖长条→可读横图)。"""
    import cv2
    from src.table.rect_struct import strip_band
    a, b = max(0, int(y0) - 10), min(gray.shape[0], int(y1) + 10)
    _, gb, _ = strip_band(gray, a, b, (sp_l["ys"], sp_l["xs"]),
                          (sp_r["ys"], sp_r["xs"]), inset=1)
    cols = []
    for i in range(0, max(gb.shape[0], 1), seg_h):
        c = gb[i:i + seg_h]
        if c.shape[0] < seg_h:
            c = np.vstack([c, np.full((seg_h - c.shape[0], c.shape[1]), 255, np.uint8)])
        cols.append(np.hstack([c, np.full((seg_h, 6), 120, np.uint8)]))
    return np.hstack(cols)


def _read_band_with_agnes(gray, sp_l, sp_r, b):
    """Agnes 视觉复读名带 → 清理空白后的文本(失败/未解析返回 None)。"""
    import cv2
    import re
    from src.table import agnes_post
    img = _era_band_crop(gray, sp_l, sp_r, b["y0"], b["y1"])
    ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    content = agnes_post.ask(ERA_READ_PROMPT, image_jpeg=jpeg.tobytes())
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    import json
    try:
        return json.loads(m.group(0)).get("text")
    except Exception:
        return None


def apply_cross_repairs(stem, changes, band_rows, out_dir=None,
                        source="跨图多数决", basis="跨图1编辑距多数决", era_col=0):
    """跨图修复回写:changes=[(带序号, 新名)],band_rows[带序号]=该带首格 xlsx 行。

    重开整合 xlsx 改时代格并保存;校正账 CSV 追加;验收 JSON 名带同步。
    era_col=时代列 0-based 下标(缺省 0,与历史行为一致);调用方须传本图实际值,
    否则 6 列的 1032(无时代列)会被写错列。
    返回写入格数。
    """
    import csv
    import json
    from pathlib import Path as _P
    from openpyxl import load_workbook
    from src.core import paths

    out = _P(out_dir) if out_dir else paths.FINALIZE_FULL_DIR
    wb = load_workbook(out / f"{stem}_整合.xlsx")
    ws = wb.active
    # 以盘上表头为准解析时代列(比调用方传参更抗漂移);解析不到则用 era_col
    _hdr = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    _r = column_roles(_hdr)
    if "era" in _r:
        era_col = _r["era"]
    led = []
    for bi, new in changes:
        row = band_rows[bi]
        old = ws.cell(row=row, column=era_col + 1).value
        ws.cell(row=row, column=era_col + 1, value=new)
        led.append({"行": f"带{bi}", "列": "地质时代", "原": old, "新": new,
                    "依据": basis, "来源": source, "应用": 1})
    wb.save(out / f"{stem}_整合.xlsx")

    rep = json.loads((out / f"{stem}_验收.json").read_text(encoding="utf-8"))
    for bi, new in changes:
        rep["名带"][bi] = new
    rep.setdefault("跨图修复", []).extend(
        {k: v for k, v in e.items() if k != "图"} for e in led)
    rep["账条数"] = rep.get("账条数", 0) + len(led)
    (out / f"{stem}_验收.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")

    csv_path = out / f"{stem}_校正账.csv"
    rows = []
    if csv_path.exists():
        rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    rows.extend(led)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["行", "列", "原", "新", "依据", "来源", "应用"])
        w.writeheader()
        w.writerows(rows)
    return len(led)


def finalize(stem, use_agnes=True, desc_batch=15, out_dir=None):
    """单图整合:B 目录 xlsx + era_chars 名带 → 合并+校正+门禁 → 整合 xlsx/校正账/验收。

    应用纪律:Agnes 改动须"原"与表内现值逐字一致才应用(防错位/幻觉),且黄色高亮;
    数值列只校验+给建议,不自动改数。返回汇总 dict(error 时含 "error")。
    """
    import csv
    import json
    import re
    import cv2
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, PatternFill
    from src.core import paths
    from src.table.agnes_post import ask as agnes_ask
    from src.table.era_chars import _load_inputs, strip_header_label
    from src.table.track_rows import row_y

    hm, rd = _load_inputs(stem)
    x_mid_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_mid_tbl) >= hm["band"][1]]
    ep = paths.ERA_CHAR_DIR / stem / "era_chars.json"
    if ep.exists():
        prod = json.loads(ep.read_text(encoding="utf-8"))
        bands = [dict(b) for b in prod["bands"]]
    else:
        # 整字裁剪拒裁图(1017 preflight/1019 旧版映射):时代列保持 B 目录原样,不合并不校正
        bands = []
    # 名带分裂接续+限定字补全(整合层语义修复,era_chars 产物不动;须在 Agnes/分组前)
    band_fix_led = []
    bands, jl = join_split_bands(bands)
    band_fix_led += [{"行": f"带{k}", "列": "地质时代", "来源": "规则", **e}
                     for k, e in enumerate(jl)]
    bands, fl = fill_missing_qualifier(bands)
    band_fix_led += [{"行": f"带{k}", "列": "地质时代", "来源": "规则", **e}
                     for k, e in enumerate(fl)]
    # 2026-10-27 切源:吃列线修复后的新草案(REEMIT_DIR_20261023),替代旧 20261005B
    wb = load_workbook(paths.REEMIT_DIR_20261023 / f"{stem}_还原.xlsx")
    ws = wb.active
    data = list(ws.iter_rows(values_only=True))
    n_data = len(data) - 1
    # 列角色由表头行解析(1032=6列/1042=7列,硬编码列号会串列甚至 IndexError)
    roles = column_roles(data[0] if data else [])
    if "depth" not in roles:
        return {"error": f"表头无法解析列角色: {data[0] if data else None}"}
    x_era = sum(hm["keep"][0]["x_in_band"]) / 2
    ys = [row_y(r, x_era) for r in rows_r]        # 行界 y 序列(行手术/分组全用它)
    if n_data != len(ys) - 1:
        return {"error": f"行数不一致 xlsx={n_data} 行判定={len(ys) - 1}"}
    data, ys, dropped_x = drop_header_rows(data, ys)  # 表头文字行(1030)物理剔除
    data = [list(r) if r is not None else [] for r in data]  # 行转 list,下游可写(标志层号值搬格首行)
    for xr in sorted(dropped_x, reverse=True):
        ws.delete_rows(xr)
    # 数据行 ↔ 原始行界(rows_r)对齐:剔行/拆行后 data 与 rows_r 长度失配,标志层号
    # 贴墨探测按下标直取会错位。bmap[i] = 数据行 i 顶界对应的 rows_r 下标;
    # 拆行内部界(原图真线但行判定未收录)记 None → 按切分处理,不跨拆行合并。
    bmap = [i for i in range(len(ys) + len(dropped_x)) if i not in {x - 2 for x in dropped_x}]
    data, ys, stuck_ops, stuck_led = unstuck_chain(data, ys, roles)   # 行粘连重建(三形态)
    for op in sorted(stuck_ops, key=lambda o: (o[1], 0 if o[0] == "over" else 1), reverse=True):
        # 同 xlsx 行先 over 后 split;全局行号大者先行,防位移
        kind, xr, vals = op
        if kind == "split":
            new_rows = vals if isinstance(vals[0], (list, tuple)) else [vals]
            ws.insert_rows(xr + 1, len(new_rows))
            for off, rv in enumerate(new_rows):
                for cidx, v in enumerate(rv, start=1):
                    ws.cell(row=xr + 1 + off, column=cidx, value=v)
            bmap[xr - 1:xr - 1] = [None] * len(new_rows)   # xr=xlsx 行;split 值=次行列表,
                                                           # 原行经同号 over 改写,新增 len 行各记内部界 None
        elif kind == "drop":
            ws.delete_rows(xr)
            del bmap[xr - 1]        # debris 行(数据行 xr-2)删除,并其顶底两界保上界
        elif kind == "over":
            for cidx, v in enumerate(vals, start=1):
                ws.cell(row=xr, column=cidx, value=v)
    n_data = len(data) - 1
    y_mids = [(ys[i] + ys[i + 1]) / 2 for i in range(n_data)]
    groups = rows_to_era_groups(y_mids, bands)
    # sp 折线仅 Agnes 名带复读用;bands 为空(拒裁图)或旧版映射无 sep_pts 时不用
    sp_l = sp_r = None
    if bands and "sep_pts" in hm:
        sp_l = hm["sep_pts"][hm["keep"][0]["left_sep"]]
        sp_r = hm["sep_pts"][hm["keep"][0]["right_sep"]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    _CENTER = Alignment(horizontal="center", vertical="center")  # 合并格默认底端对齐,值渲染在末行像错位
    ledger, flags, merges = [], [], []
    ledger.extend(band_fix_led)
    ledger.extend(stuck_led)
    normalize_dip_column(ws, ledger, roles)   # 倾角补°(12.6 丢失步骤恢复,逐格记账)

    # 1) Agnes 名带复读(第二引擎;采纳策略见 agnes_adopt_decision)
    header_label = hm["keep"][0]["name"]
    if use_agnes and sp_l is not None:
        for bi, b in enumerate(bands):
            read = _read_band_with_agnes(gray, sp_l, sp_r, b)
            if read is None:
                continue
            rn = re.sub(r"\s+", "", str(read))
            stripped, _ = strip_header_label([{"name": rn}], header_label)
            rn = stripped[0]["name"] if stripped else ""
            if rn == b["name"]:
                continue
            adopt, why = agnes_adopt_decision(b["name"], rn)
            ledger.append({"行": f"带{bi}", "列": "地质时代", "原": b["name"], "新": rn,
                           "依据": why, "来源": "Agnes", "应用": 1 if adopt else 0})
            if adopt:
                b["name"] = rn

    # 2) 时代列合并单元格(替换碎片,组账入 ledger)
    # 列号由表头解析:1032 无时代列(扫描左缘裁切),按列1写会把时代名盖进深度列。
    _era = roles.get("era")
    for k, rows in groups:
        if k is None or _era is None:
            continue
        frags = [str(data[r + 1][_era]) for r in rows if data[r + 1][_era] not in (None, "")]
        name = bands[k]["name"]
        if len(rows) >= 2:
            ws.merge_cells(start_row=rows[0] + 2, start_column=_era + 1,
                           end_row=rows[-1] + 2, end_column=_era + 1)
            ws.cell(row=rows[0] + 2, column=_era + 1).alignment = _CENTER
            merges.append({"带": name, "xlsx行": [rows[0] + 2, rows[-1] + 2],
                           "层数": len(rows)})
        ws.cell(row=rows[0] + 2, column=_era + 1, value=name)
        if not (len(frags) == 1 and frags[0].replace(" ", "") == name):
            ledger.append({"行": f"带{k}", "列": "地质时代",
                           "原": " | ".join(frags)[:80], "新": name,
                           "依据": "整字裁剪名带+rowspan合并", "来源": "era_chars", "应用": 1})

    # 2.5) rowspan 合并:煤层标志层号列 + 倾角列(2026-10-27 用户指出层号缺合并,
    # 2026-10-28 补倾角——v7 旧机制本就两列同源)。原图这两列一格常罩多层("三下"
    # 罩两层、"5°"管数行)。判据=行界折线在该列 x 范围内的最长连墨(30 采样):
    # ≥12 视为界线穿过该列=切分,否则同一格延续。值取格内首个非空并搬到格首行
    # (Excel 合并保左上值);格内多个不同非空=疑似串行,记账不改。
    _lay = roles.get("layer")
    if n_data >= 2 and "sep_pts" in hm and any(
            _c is not None and _c < len(hm["keep"]) for _c in (_lay, roles.get("dip"))):
        if len(bmap) != n_data + 1:
            return {"error": f"行界对齐失配: bmap={len(bmap)} data={n_data + 1}"}
        _v3 = hm["sep_pts"]

        def _lay_x(i, y, edge):
            if i is None or i < 0:
                return float(edge)
            _b = _v3[i]
            _r = np.interp(y, _b["ys"], _b["xs"])
            return float(_r) if np.ndim(_r) else float(_r)

        def _ink_run(i, kl, kr):
            """行界在该列内的最长连墨采样数(30 采样,±4px 窗)。
            bmap[i]=None(拆行内部界)→ 30:行粘连修复已实证该处多行,按切分处理,
            不跨拆行合并。判据=最长连墨≥12:真穿线中段留连续残段(全量灰区实测
            13~17 连墨),端部渗入/分位线偏移只在两端成簇(实测 ≤11),12 落间隙上。
            列是斜的:x 范围按本行界自己的 y 中点取(全行 min/max 会采进邻列的线)。"""
            _bi = bmap[i]
            if _bi is None:
                return 30
            _y_mid = (row_y(rows_r[_bi - 1], x_mid_tbl) + row_y(rows_r[_bi], x_mid_tbl)) / 2
            _xl = _lay_x(kl, _y_mid, 0.0)
            _xr = _lay_x(kr, _y_mid, float(gray.shape[1]))
            if _xr - _xl < 12:
                return 30
            _xs = np.linspace(_xl + 6, _xr - 6, 30)
            _yy = np.array([row_y(rows_r[_bi], x) for x in _xs])
            _best = _cur = 0
            for _x, _y in zip(_xs, _yy):
                _xi, _yi = int(_x), int(_y)
                if (gray[max(0, _yi - 4):_yi + 5, _xi] < 128).any():
                    _cur += 1
                    _best = max(_best, _cur)
                else:
                    _cur = 0
            return _best

        for _col, _colname in ((_lay, "煤层标志层号"), (roles.get("dip"), "倾角")):
            if _col is None or _col >= len(hm["keep"]):
                continue
            _kl, _kr = hm["keep"][_col]["left_sep"], hm["keep"][_col]["right_sep"]
            _cuts = [i for i in range(1, n_data) if _ink_run(i, _kl, _kr) >= 12]
            _runs, _s = [], 0
            for _c in _cuts + [n_data]:
                _runs.append((_s, _c))
                _s = _c
            for _r0, _r1 in _runs:
                if _r1 - _r0 < 2:
                    continue
                _vals = [(i, data[i + 1][_col]) for i in range(_r0, _r1)
                         if len(data[i + 1]) > _col and data[i + 1][_col] not in (None, "")]
                _uniq = sorted({str(v) for _, v in _vals})
                if not _vals:
                    continue
                _i0, _v0 = _vals[0]
                if _i0 != _r0:
                    data[_r0 + 1][_col] = _v0
                    data[_i0 + 1][_col] = None
                    # merge_cells 会抹掉非左上格的值,搬移必须写回 ws,只改 data 副本=丢值
                    ws.cell(row=_r0 + 2, column=_col + 1, value=_v0)
                    ws.cell(row=_i0 + 2, column=_col + 1, value=None)
                ws.merge_cells(start_row=_r0 + 2, start_column=_col + 1,
                               end_row=_r1 - 1 + 2, end_column=_col + 1)
                ws.cell(row=_r0 + 2, column=_col + 1).alignment = _CENTER
                merges.append({"带": _colname, "xlsx行": [_r0 + 2, _r1 - 1 + 2],
                               "层数": _r1 - _r0})
                if len(_uniq) > 1:
                    flags.append({"图": stem, "列": _colname,
                                  "问题": f"同格多值(疑似OCR串行): {'|'.join(_uniq)}",
                                  "行": f"带{_r0}-{_r1 - 1}"})
                if _i0 != _r0 or len(_vals) > 1:
                    ledger.append({"行": f"带{_r0}-{_r1 - 1}", "列": _colname,
                                   "原": " | ".join(str(v) for _, v in _vals),
                                   "新": str(_v0), "依据": "行界无墨=同格,值搬格首行",
                                   "来源": "规则", "应用": 1})

    if _lay is not None and n_data >= 2:
        # 标志层号乱码门禁:非"数字/中文数字±上下"模式的值只标不改
        for _i in range(n_data):
            _v = data[_i + 1][_lay] if len(data[_i + 1]) > _lay else None
            if _v in (None, ""):
                continue
            if not re.fullmatch(r"[0-9]{1,3}|[一二三四五六七八九十]+[上下]?", str(_v).strip()):
                flags.append({"图": stem, "列": "煤层标志层号",
                              "问题": f"疑似乱码(原图需人核): {_v}",
                              "行": str(_i + 1)})
        # 乱码裁决落地(2026-10-27,助手判读+约束复读,用户授权免裁决):按图+xlsx行
        # 改 B 列值并入账。原值不符=漂移,只记账不应用(防行号漂移改错格)。
        _vp = paths.LAYER_VERDICTS_20261027
        if _vp.exists():
            _verdicts = json.loads(_vp.read_text(encoding="utf-8"))
            for _vd in _verdicts:
                if _vd.get("图") != stem:
                    continue
                _r = int(_vd["行"])
                if not (2 <= _r <= n_data + 1):
                    continue
                _cell = data[_r - 1][_lay] if len(data[_r - 1]) > _lay else None
                _new = str(_vd["新值"])
                if str(_cell) == _new:
                    continue
                _match = str(_vd.get("现值")) == str(_cell)
                _tgt = ws.cell(row=_r, column=_lay + 1)
                if _match and _tgt.__class__.__name__ != "MergedCell":
                    _tgt.value = _new
                    data[_r - 1][_lay] = _new
                flags[:] = [f for f in flags
                            if not (f.get("列") == "煤层标志层号" and f.get("行") == str(_r - 1))]
                ledger.append({"行": f"r{_r - 1}", "列": "煤层标志层号",
                               "原": str(_cell), "新": _new,
                               "依据": _vd.get("依据", "乱码裁决") + ("" if _match else ";原值漂移未应用,仅销旗"),
                               "来源": "助手判读(用户授权免裁决)", "应用": 1 if _match else 0})

    # 2.6) 数值横杠小数修复(2026-10-28 用户"修复"):原图小数点印成短横(1043 像素
    # 实证,同形被 OCR 读成'.'或'-'),^数字-数字 的数值格换点,逐格算术验证:
    # 深度=相邻深度链 / 层厚=本行终深−上行终深 / 采长、真厚≤层厚×1.05(真厚另验
    # ≈层厚×cos倾角)。验证不过=维持原样只旗。全部逐格入账,来源=规则。
    import math
    _numroles = {nm: roles.get(r) for nm, r in
                 (("深度", "depth"), ("层厚", "thick"), ("采长", "length"),
                  ("真厚", "true_thick"), ("倾角", "dip"))}
    _numroles = {k: v for k, v in _numroles.items() if v is not None}
    _DASH = re.compile(r"^-?\d+-\d+$")

    def _plain(v):
        try:
            return float(str(v).replace("°", "").strip())
        except (TypeError, ValueError):
            return None

    def _best(i, k):
        """行 i 列 k 的最优数值:横杠候选按已修计(联合验证),否则原值。"""
        v = data[i][k] if len(data[i]) > k else None
        if v is not None and _DASH.match(str(v).strip()):
            try:
                return float(str(v).replace("-", "."))
            except ValueError:
                return None
        return _plain(v)

    _depk = _numroles.get("深度")
    for _i in range(1, n_data + 1):
        for _name, _k in _numroles.items():
            _v = data[_i][_k] if len(data[_i]) > _k else None
            if _v is None or not _DASH.match(str(_v).strip()):
                continue
            _s = str(_v).strip()
            _new = _s.replace("-", ".")
            try:
                _x = float(_new)
            except ValueError:
                continue
            _why = None
            if _name == "深度":
                # 本表口径:本行终深=上行终深+本行层厚(层厚=终深差)
                _prev = _nxt = None
                if _i >= 2 and _numroles.get("层厚") is not None:
                    _d0, _t0 = _best(_i - 1, _depk), _best(_i, _numroles.get("层厚"))
                    if _d0 is not None and _t0 is not None:
                        _prev = _d0 + _t0
                if _i < n_data and _numroles.get("层厚") is not None:
                    _d1, _t1 = _best(_i + 1, _depk), _best(_i + 1, _numroles.get("层厚"))
                    if _d1 is not None and _t1 is not None:
                        _nxt = _d1 - _t1
                for _ref in (_prev, _nxt):
                    if _ref is not None and abs(_ref - _x) <= 0.02:
                        _why = "深度链闭合(相邻深度−层厚)"
                        break
            elif _name == "层厚":
                if _depk is not None and _i >= 2:
                    _d0, _d1 = _best(_i - 1, _depk), _best(_i, _depk)
                    if _d0 is not None and _d1 is not None and abs((_d1 - _d0) - _x) <= 0.02:
                        _why = "层厚=本行终深−上行终深"
            else:
                _thk = _best(_i, _numroles["层厚"]) if "层厚" in _numroles else None
                if _thk is not None and 0 <= _x <= _thk * 1.05 + 0.05:
                    _why = "≤层厚(上界旁证)"
                    if _name == "真厚" and "倾角" in _numroles:
                        _dip = _plain(data[_i][_numroles["倾角"]])
                        if _dip is not None and abs(_x - _thk * math.cos(math.radians(_dip))) <= 0.15:
                            _why = "≈层厚×cos倾角"
            if _why:
                data[_i][_k] = _new
                ws.cell(row=_i + 1, column=_k + 1, value=_new)
                ledger.append({"行": str(_i), "列": _name, "原": _s, "新": _new,
                               "依据": f"原图小数点为短横(1043像素实证);{_why}",
                               "来源": "规则", "应用": 1})
            else:
                flags.append({"图": stem, "列": _name,
                              "问题": f"疑似短横小数,算术验证不过,维持原样: {_s}",
                              "行": str(_i)})
                ledger.append({"行": str(_i), "列": _name, "原": _s, "新": _new,
                               "依据": "原图小数点为短横;验证不过不应用",
                               "来源": "规则", "应用": 0})

    # 2.7) Agnes 全列复读裁决落地(2026-10-28 用户拍板:按时代带整块裁原图送 Agnes,
    # 链算术/词表/编辑距裁决后的应用条目在此改值入账)。原值不符=漂移只记账不应用;
    # MergedCell 不写(合并区值在区首);desc 半角标点转全角,倾角裸数字补°。
    _avp = paths.AGNES_REREAD_DIR_20261028 / stem / "裁决.json"
    if _avp.exists():
        _vd = json.loads(_avp.read_text(encoding="utf-8"))
        for _e in _vd.get("条目", []):
            if _e.get("处置") != "应用" or not str(_e.get("新值") or "").strip():
                continue
            _r = int(_e["行"])
            if not (2 <= _r <= n_data + 1):
                continue
            _c = roles.get(_e["角色"])
            if _c is None:
                continue
            _tgt = ws.cell(row=_r, column=_c + 1)
            if _tgt.__class__.__name__ == "MergedCell":
                continue
            _new = str(_e["新值"]).strip()
            if _e["角色"] == "desc":
                for _a, _b in ((",", "，"), (";", "；"), (":", "："),
                               ("(", "（"), (")", "）")):
                    _new = _new.replace(_a, _b)
            elif _e["角色"] == "dip" and re.fullmatch(r"\d+(\.\d+)?", _new):
                _new += "°"
            _cur = _tgt.value
            if (_cur is None and not _new) or str(_cur) == _new:
                continue
            _cur_s = "" if _cur is None else str(_cur)
            if _cur_s != str(_e.get("原") or ""):
                ledger.append({"行": f"r{_r - 1}", "列": _e["列"], "原": _cur_s,
                               "新": _new, "依据": f"现值漂移未应用(裁据原值{_e.get('原')})",
                               "来源": "Agnes复读", "应用": 0})
                continue
            _tgt.value = _new
            data[_r - 1][_c] = _new
            ledger.append({"行": f"r{_r - 1}", "列": _e["列"], "原": str(_cur),
                           "新": _new, "依据": _e.get("依据", "Agnes复读裁决"),
                           "来源": "Agnes复读", "应用": 1})

    # 3) 数值列合理性门禁(只判+建议,不改数)
    _dep, _thk = roles["depth"], roles.get("thick", 3)
    depths = [data[i + 1][_dep] if len(data[i + 1]) > _dep else None for i in range(n_data)]
    thicks = [data[i + 1][_thk] if len(data[i + 1]) > _thk else None for i in range(n_data)]
    for p in check_depth_monotonic(depths):
        flags.append({**p, "图": stem, "列": "深度"})
    for p in check_thickness_delta(depths, thicks):
        flags.append({**p, "图": stem, "列": "层厚"})
        ledger.append({"行": p["行"], "列": "层厚", "原": p["层厚"],
                       "新": f"建议 {p['深度差']}", "依据": "层厚≠相邻终深差",
                       "来源": "规则", "应用": 0})
    for p in check_era_sequence([b["name"] for b in bands]):
        flags.append({**p, "图": stem, "列": "地质时代"})

    # 4) 描述列 Agnes 形误校正(原值逐字核对才应用,黄色高亮)
    if use_agnes:
        _desc = roles.get("desc")
        idxs = [i for i in range(n_data)
                if _desc is not None and len(data[i + 1]) > _desc and data[i + 1][_desc]]
        for s in range(0, len(idxs), desc_batch):
            chunk = idxs[s:s + desc_batch]
            listing = "\n".join(f"{i}: {data[i + 1][_desc]}" for i in chunk)
            content = agnes_ask(DESC_PROMPT + listing)
            m = re.search(r"\[.*\]", content, re.S)
            if not m:
                continue
            try:
                items = json.loads(m.group(0))
            except Exception:
                continue
            for it in items:
                try:
                    i = int(it["i"])
                except (KeyError, ValueError, TypeError):
                    continue
                if not (0 <= i < n_data) or _desc is None or not data[i + 1][_desc]:
                    continue
                orig, new = str(data[i + 1][_desc]), str(it.get("改", ""))
                if not new or new == orig:
                    continue
                ok = str(it.get("原", "")) == orig
                ws.cell(row=i + 2, column=_desc + 1, value=new)
                # 蓝底已废(用户裁决 2026-10-11"不要蓝底"):校正语义只在账,
                # 现役颜色口径=红字(与参考表分歧,compare_ref 层),无其他底色
                ledger.append({"行": i, "列": "岩性描述", "原": orig[:60],
                               "新": new[:60], "依据": str(it.get("依据", ""))[:60],
                               "来源": "Agnes", "应用": 1 if ok else 0})

    # 5) 落盘:整合 xlsx + 校正账 CSV + 验收 JSON
    # out_dir 可显式指定;缺省仍写历史目录(调用方不传时行为不变)。
    # 专项修复必须显式传新目录,否则会原地覆盖 v7 溯源。
    out = Path(out_dir) if out_dir else paths.FINALIZE_FULL_DIR
    out.mkdir(parents=True, exist_ok=True)
    wb.save(out / f"{stem}_整合.xlsx")
    if ledger:
        with open(out / f"{stem}_校正账.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["行", "列", "原", "新", "依据", "来源", "应用"])
            w.writeheader()
            w.writerows(ledger)
    report = {"图": stem, "名带": [b["name"] for b in bands], "合并组": merges,
              "门禁问题": flags, "账条数": len(ledger),
              "时代带行": {k: rows[0] + 2 for k, rows in groups if k is not None}}
    (out / f"{stem}_验收.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


def main(argv):
    """两阶段:①逐图整合(合并+Agnes 校正+门禁);②全图名带齐了再跨图 1 编辑距
    多数决修复,回写 xlsx/账/JSON(跨图票数必须全图跑完才作数)。
    `--repair-only` 跳过整合,从盘上验收.json 读名带做修复(支持分批跑后统一收口)。"""
    import json
    from src.core import paths
    no_agnes = bool(argv and argv[0] == "--no-agnes")
    if no_agnes:
        argv = argv[1:]
    if argv and argv[0] == "--repair-only":
        nums = argv[1:] or sorted(d.name for d in paths.ERA_CHAR_DIR.iterdir() if d.is_dir())
    else:
        nums = argv or sorted(d.name for d in paths.ERA_CHAR_DIR.iterdir() if d.is_dir())
    bad = []
    reports = {}
    for num in nums:
        stem = num if num.startswith("钻孔柱状图") else f"钻孔柱状图{num}"
        if argv and argv[0] == "--repair-only":
            rp = paths.FINALIZE_FULL_DIR / f"{stem}_验收.json"
            if rp.exists():
                rep = json.loads(rp.read_text(encoding="utf-8"))
                # JSON 整数键落盘变字符串,回写定位需 int
                rep["时代带行"] = {int(k): v
                                   for k, v in rep.get("时代带行", {}).items()}
                reports[stem] = rep
            continue
        rep = finalize(stem, use_agnes=not no_agnes)
        if "error" in rep:
            print(stem, "FAIL", rep["error"])
            bad.append(stem)
            continue
        reports[stem] = rep
        print(stem, f"名带{len(rep['名带'])} 合并组{len(rep['合并组'])} "
                    f"门禁{len(rep['门禁问题'])} 账{rep['账条数']}",
            [f["问题"] for f in rep["门禁问题"]] or "")
    fixed, led = repair_cross_chart({s: r["名带"] for s, r in reports.items()})
    if led:
        print("跨图多数决:", [(e["图"], e["原"], e["新"], e["应用"]) for e in led])
    for stem, rep in reports.items():
        changes = [(e["带"], e["新"]) for e in led
                   if e["图"] == stem and e["应用"] == 1]
        if changes:
            apply_cross_repairs(stem, changes, rep["时代带行"])
    # 用户裁决最后(用户赢一切);原值对不上=漂移只记账
    vp = paths.USER_VERDICTS_20261010
    verdicts = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else []
    if verdicts:
        fixed_v, led_v = apply_user_verdicts(
            {s: r["名带"] for s, r in reports.items()}, verdicts)
        print("用户裁决:", [(e["图"], e["原"], e["新"], e["应用"]) for e in led_v])
        for s, ns in fixed_v.items():
            reports[s]["名带"] = ns
        for e in led_v:
            if e["应用"] == 1:
                apply_cross_repairs(e["图"], [(e["带"], e["新"])],
                                    reports[e["图"]]["时代带行"],
                                    source="用户裁决", basis=e["依据"])
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
