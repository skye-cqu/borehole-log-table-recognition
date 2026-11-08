# -*- coding: utf-8 -*-
"""整合表管线纯函数测试:行→时代带分组(合并单元格依据)与列特征校验器(合理性门禁)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.table.finalize_tables import (check_depth_monotonic, check_era_sequence,
                                       check_thickness_delta, fill_missing_qualifier,
                                       join_split_bands, repair_cross_chart,
                                       rows_to_era_groups)


def test_rows_to_era_groups():
    bands = [{"name": "第四系", "y0": 100, "y1": 500},
             {"name": "龙潭组", "y0": 620, "y1": 1000}]
    rows_y = [150, 300, 450, 480, 700, 900]      # 行中点 y
    groups = rows_to_era_groups(rows_y, bands)
    assert groups == [(0, [0, 1, 2, 3]), (1, [4, 5])]
    # 带间空隙里的行(时代界行)归最近的带
    rows_y2 = [150, 560, 700]
    groups2 = rows_to_era_groups(rows_y2, bands)
    assert groups2 == [(0, [0, 1]), (1, [2])]


def test_check_depth_monotonic():
    assert check_depth_monotonic([12.28, 12.83, 15.98]) == []
    v = check_depth_monotonic([12.28, 12.83, 12.30, 20.0])
    assert len(v) == 1 and v[0]["行"] == 2 and v[0]["问题"] == "深度逆序"


def test_check_thickness_delta():
    depths = [12.28, 12.83, 15.98, 16.95]
    thicks = [12.28, 0.55, 3.15, 0.97]
    assert check_thickness_delta(depths, thicks) == []
    thicks_bad = [12.28, 0.55, 31.5, 0.97]        # 小数点丢失型错误
    v = check_thickness_delta(depths, thicks_bad)
    assert len(v) == 1 and v[0]["行"] == 2 and abs(v[0]["差"] - 28.35) < 1e-6


def test_check_era_sequence():
    seq = ["第四系", "飞仙关组二至段", "大隆组", "长兴组", "龙潭组上段", "茅口组"]
    assert check_era_sequence(seq) == []
    v = check_era_sequence(["茅口组", "龙潭组上段"])          # 组级倒转(同为二叠系)
    assert any(x["问题"] == "组序倒转" for x in v)
    v2 = check_era_sequence(["龙潭组", "飞仙关组"])           # 系级倒转(二叠系下出现三叠系)
    assert any(x["问题"] == "系序倒转" for x in v2)
    assert check_era_sequence(["第一系", "某组"]) == []        # 未知名不判(不编造)


def test_repair_cross_chart_一编辑距多数决():
    # 删一字:1016 残线多出的"一",1022/1040 两票同为 龙潭组下段
    names = {"1016": ["龙潭组一下段"], "1022": ["龙潭组下段"], "1040": ["龙潭组下段"]}
    fixed, led = repair_cross_chart(names)
    assert fixed["1016"] == ["龙潭组下段"]
    assert len(led) == 1 and led[0]["图"] == "1016" and led[0]["应用"] == 1
    # 换一字:1040 天隆组,他图两票 大隆组
    names2 = {"1040": ["天隆组", "长兴组"], "1022": ["大隆组", "长兴组"],
              "1026": ["大隆组", "长兴组"]}
    fixed2, led2 = repair_cross_chart(names2)
    assert fixed2["1040"][0] == "大隆组" and len(led2) == 1


def test_repair_cross_chart_守卫():
    # 本地名在他图原样出现=已互证,不修
    names = {"a": ["长兴组"], "b": ["长兴组"], "c": ["长兴组"]}
    fixed, led = repair_cross_chart(names)
    assert fixed == names and led == []
    # 换一字且他图两票:长兴八组 → 长兴组(试点实例)
    fixed1, led1 = repair_cross_chart({"a": ["长兴组"], "b": ["长兴组"], "c": ["长兴八组"]})
    assert fixed1["c"] == ["长兴组"] and led1[0]["应用"] == 1
    # 单票不采(只有一张他图同名;无互证存疑记应用=0账)
    fixed2, led2 = repair_cross_chart({"a": ["天隆组"], "b": ["大隆组"]})
    assert fixed2["a"] == ["天隆组"]
    assert len(led2) == 2 and all(e["应用"] == 0 for e in led2)
    # 距离>1 不采
    fixed3, _ = repair_cross_chart({"a": ["龙潭组上组"], "b": ["茅口组"], "c": ["茅口组"]})
    assert fixed3["a"] == ["龙潭组上组"]
    # 多候选近票=歧义,跳过并记账
    names4 = {"a": ["甲乙丙丁"], "b": ["甲乙丙戊"], "c": ["甲乙丙戊"],
              "d": ["甲乙丙己"], "e": ["甲乙丙己"]}
    fixed4, led4 = repair_cross_chart(names4)
    assert fixed4["a"] == ["甲乙丙丁"]
    assert len(led4) == 1 and led4[0]["应用"] == 0 and led4[0]["依据"]


def test_repair_cross_chart_压倒性多数():
    # 全量实例:真名 16-20 票 vs 同类OCR变体 1-3 票 → 压倒才采(≥3倍次名、≥3倍互证)
    names = {"1015": ["龙组下段"], "1021": ["龙融组中段"], "a": ["龙组中段"],
             "b": ["龙组中段"], "c": ["龙组中段"]}
    others = [f"t{i}" for i in range(16)]
    names.update({f"t{i}": ["龙潭组中段"] for i in range(16)})
    names["d"] = ["龙潭组下段"]
    names["e"] = ["龙潭组下段"]
    fixed, led = repair_cross_chart(names)
    got = {e["图"]: (e["原"], e["新"], e["应用"]) for e in led}
    # 龙组下段:候选 龙潭组下段2票/龙组中段3票 → 3<3*2 未压倒,歧义不采
    assert got["1015"] == ("龙组下段", "", 0)
    # 龙融组中段:候选 龙潭组中段16票/龙组中段3票 → 16>=9 压倒采
    assert got["1021"] == ("龙融组中段", "龙潭组中段", 1)
    # 龙组中段:互证2张+候选16票 → 16>=6 压倒互证采
    assert got["a"] == ("龙组中段", "龙潭组中段", 1)
    # 近票互证不压:三图互证 X(每图corr=2),三图有 Y(距离1,3票) → 3<3*2 不采
    names2 = {"a": ["龙组上段"], "b": ["龙组上段"], "f": ["龙组上段"],
              "c": ["龙潭组上段"], "d": ["龙潭组上段"], "e": ["龙潭组上段"]}
    fixed2, led2 = repair_cross_chart(names2)
    assert fixed2["a"] == ["龙组上段"] and led2 == []


def test_agnes_adopt_decision():
    from src.table.finalize_tables import agnes_adopt_decision
    # 本地文法 valid 且与 Agnes 分歧 → 只记账不采用(1022 石二至一段教训)
    assert agnes_adopt_decision("飞仙关组二至一段", "石二至一段") == (False, "两引擎分歧,只记账待裁")
    # 本地 invalid/suspect → 采 valid 的 Agnes 读数
    assert agnes_adopt_decision("酒", "龙潭组上段")[0] is True
    assert agnes_adopt_decision("上段", "龙潭组上段")[0] is True
    # Agnes 读数本身 invalid → 不采
    d = agnes_adopt_decision("酒", "三八")
    assert d[0] is False and "invalid" in d[1]


def test_apply_cross_repairs_回写(tmp_path):
    import csv
    import json
    from openpyxl import Workbook
    from src.table.finalize_tables import apply_cross_repairs
    wb = Workbook()
    ws = wb.active
    ws.append(["地质时代", "深度"])
    for i in range(5):
        ws.append(["碎片", i, "x"])
    xlsx = tmp_path / "a_整合.xlsx"
    wb.save(xlsx)
    (tmp_path / "a_验收.json").write_text(
        json.dumps({"图": "a", "名带": ["龙潭组一下段", "茅口组"], "账条数": 0},
                   ensure_ascii=False), encoding="utf-8")
    n = apply_cross_repairs("a", [(0, "龙潭组下段")], [2, 6], out_dir=tmp_path)
    assert n == 1
    wb2 = __import__("openpyxl").load_workbook(xlsx)
    assert wb2.active.cell(row=2, column=1).value == "龙潭组下段"
    rep = json.loads((tmp_path / "a_验收.json").read_text(encoding="utf-8"))
    assert rep["名带"][0] == "龙潭组下段" and rep["账条数"] == 1
    rows = list(csv.DictReader(open(tmp_path / "a_校正账.csv", encoding="utf-8-sig")))
    assert rows[0]["新"] == "龙潭组下段" and rows[0]["应用"] == "1"


def test_apply_user_verdicts():
    from src.table.finalize_tables import apply_user_verdicts
    names = {"1022": ["萧系", "飞仙关组二至一段"], "1040": ["第四系"]}
    verdicts = [{"图": "1022", "原": "萧系", "新": "第四系",
                 "依据": "用户裁决:直接是第四系,没有前代"}]
    fixed, led = apply_user_verdicts(names, verdicts)
    assert fixed["1022"][0] == "第四系" and fixed["1040"] == ["第四系"]
    assert len(led) == 1 and led[0]["应用"] == 1 and led[0]["来源"] == "用户裁决"
    # 原值对不上=漂移,只记账不应用
    fixed2, led2 = apply_user_verdicts({"1022": ["第四系"]}, verdicts)
    assert fixed2["1022"] == ["第四系"]
    assert led2[0]["应用"] == 0 and "不符" in led2[0]["依据"]


def test_join_split_bands():
    bands = [{"name": "龙潭组", "y0": 16000, "y1": 18766},
             {"name": "段", "y0": 19711, "y1": 19754},
             {"name": "茅口组", "y0": 20115, "y1": 21571}]
    joined, led = join_split_bands(bands)
    assert [b["name"] for b in joined] == ["龙潭组段", "茅口组"]
    assert joined[0]["y0"] == 16000 and joined[0]["y1"] == 19754   # y 并集
    assert len(led) == 1 and "龙潭组|段" in led[0]["原"]
    # 不相邻/前带不以组结尾:不动
    b2 = [{"name": "第四系", "y0": 0, "y1": 100}, {"name": "段", "y0": 200, "y1": 300}]
    joined2, led2 = join_split_bands(b2)
    assert len(joined2) == 2 and led2 == []


def test_fill_missing_qualifier():
    bands = [{"name": "龙潭组上段", "y0": 0, "y1": 1},
             {"name": "龙潭组中段", "y0": 2, "y1": 3},
             {"name": "龙潭组段", "y0": 4, "y1": 5},
             {"name": "茅口组", "y0": 6, "y1": 7}]
    filled, led = fill_missing_qualifier(bands)
    assert filled[2]["name"] == "龙潭组下段"          # 上/中在场,唯一缺=下
    assert len(led) == 1 and led[0]["应用"] == 1
    assert led[0]["原"] == "龙潭组段" and led[0]["新"] == "龙潭组下段"   # 原=改前值
    # 只有一带在场,缺两个=歧义,不补
    b2 = [{"name": "龙潭组上段", "y0": 0, "y1": 1}, {"name": "龙潭组段", "y0": 2, "y1": 3}]
    filled2, led2 = fill_missing_qualifier(b2)
    assert filled2[1]["name"] == "龙潭组段" and led2 == []


def test_add_degree_symbol():
    from src.table.finalize_tables import add_degree_symbol
    assert add_degree_symbol("5") == "5°"          # 裸数字补°(1015行3像素实证原图带°)
    assert add_degree_symbol("5°") == "5°"         # 已有不动
    assert add_degree_symbol(3) == "3°"
    assert add_degree_symbol("") is None
    assert add_degree_symbol(None) is None
    assert add_degree_symbol("直") == "直"          # 非数字不动(不编造)


def test_value_merge_spans():
    from src.table.finalize_tables import value_merge_spans
    # 值管辖规则:段从值行起沿无线界延伸,止于有线界或下一值行前(段内至多一值,零丢值)
    flags = [True, False, False, True, True, False]
    assert value_merge_spans(flags, {0}) == [(0, 1)]      # r0 向下无线延伸,止于有线界1
    assert value_merge_spans(flags, {3}) == [(3, 5)]      # r3-r4 无线,r5 前无线但止于末行
    assert value_merge_spans(flags, {0, 3}) == [(0, 1), (3, 5)]
    # 止于下一值行前:不吞后续值(层号列值格间原图无线,全并会吞值)
    assert value_merge_spans([True, True, True], {0, 2}) == [(0, 1), (2, 3)]
    assert value_merge_spans([True, True], {0, 1}) == [(1, 2)]  # 末值向下管到末行
    # 全无线整列一个值:值管到末行
    assert value_merge_spans([True] * 3, {1}) == [(1, 3)]
    # None(存疑)按有线,不延伸
    assert value_merge_spans([None, True], {0}) == []
    # 无线但下一值行前止
    assert value_merge_spans([True, True, False], {0, 3}) == [(0, 2)]


def test_flags_wireless_语义对齐回归():
    from src.table.finalize_tables import flags_wireless, value_merge_spans
    # 像素账语义:True=有线,None=存疑 → 函数语义:True=无线合并
    assert flags_wireless([True, False, None]) == [False, True, None]
    # 回归错例(1015 倾角 4°|5° 间有线,曾被当合并界把两格并一):
    has_line = [True]                       # 界有线 → 必须断开,两值各自成格
    assert value_merge_spans(flags_wireless(has_line), {0, 1}) == []
    # 无线界才合并
    assert value_merge_spans(flags_wireless([False, None]), {0}) == [(0, 1)]
    # None(存疑)按有线,不并
    assert value_merge_spans(flags_wireless([None]), {0, 1}) == []


def test_drop_header_rows():
    from src.table.finalize_tables import drop_header_rows
    hdr = ("地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述")
    data = [hdr,
            ["地 质 时 代", "煤层，标层号", "深 度", "层 厚", "采 长", "倾 角", "真 厚", "岩 性 描 述"],
            ["飞 仙 关 组 一 段", None, 84.4, None, None, None, None, None],
            ["大隆组", None, 88.5, 4.1, 2.5, "4°", 4.09, "硅质岩"]]
    rows_b = [571, 873, 4017, 5000]      # len==len(data):界 i=数据行 i 顶界
    d2, b2, dropped = drop_header_rows(data, rows_b)
    assert len(d2) == 3 and len(b2) == 3             # 剔 1 数据行连顶界
    assert d2[1][0] == "飞 仙 关 组 一 段" and b2[0] == 873     # 底界留作下行顶界
    assert dropped == [2]                             # 数据行0 → xlsx 第2行(供 ws.delete_rows)
    assert drop_header_rows(d2, b2) == (d2, b2, [])  # 幂等
    # 正常图:数据行首格非表头文本 → 原样
    d3, b3, dropped3 = drop_header_rows([hdr, ["飞仙关组", None, 84.4]], [100, 200])
    assert d3 == [hdr, ["飞仙关组", None, 84.4]] and b3 == [100, 200] and dropped3 == []




def test_unstuck_chain_1037型():
    from src.table.finalize_tables import unstuck_chain
    hdr = ("时代", "层号", "深度", "层厚", "采长", "倾角", "真厚", "描述")
    data = [hdr,
            ["", "16", "355.95 357.47", "0.46 1.52", "0.35 1.25", "11°", "0.45 1.49", "泥质粉砂岩。"],
            ["", "", "", "", "", "", "", "煤,深黑色,块状。"],
            ["", "16", "357.47 357.80", "1.52 0.33", "1.25 0.30", "", "1.49 0.32", "泥岩。"],
            ["", "17", "358.10", "0.30", "0.30", "", "0.30", "砂岩。"]]
    rows_b = [100, 200, 260, 320, 400]
    d2, b2, ops, led = unstuck_chain(data, rows_b)
    assert [(o[0], o[1]) for o in ops] == [("over", 2), ("split", 2), ("drop", 3), ("over", 4)]
    assert ops[0][2][2] == "355.95"                       # over vals=行
    assert ops[1][2][0][2] == "357.47" and ops[3][2][2] == "357.80"  # split vals=次行列表
    assert len(d2) == 5                                   # hdr + B + C + D + 砂岩
    assert [r[2] for r in d2[1:]] == ["355.95", "357.47", "357.80", "358.10"]
    assert d2[1][3] == "0.46" and d2[2][3] == "1.52" and d2[3][3] == "0.33"
    assert d2[1][7] == "泥质粉砂岩。" and d2[2][7] == "煤,深黑色,块状。" and d2[3][7] == "泥岩。"
    assert d2[2][5] is None and d2[3][4] == "0.30"       # 次值行单值列清空
    assert d2[3][7] == "泥岩。" and d2[1][5] == "11°"      # ③ D 承接单值列,B 留倾角
    assert b2 == [100, 150, 260, 320, 400]                # 拆中点+删行区间并入,连续
    assert led == []                                      # 全链闭合,无记账
    # 无粘连图原样
    d3, b3, ops3, led3 = unstuck_chain([hdr, ["", "1", "10.0", "1", "1", "5°", "1", "x"]],
                                       [100, 200])
    assert d3 == [hdr, ["", "1", "10.0", "1", "1", "5°", "1", "x"]] and ops3 == []


def test_unstuck_chain_1035r36情形A拆():
    """全列双值+下行自有深度(1035 r36 原图两行实锤)→ 拆,未配对数值列次行清空。"""
    from src.table.finalize_tables import unstuck_chain
    hdr = ("时代", "层号", "深度", "层厚", "采长", "倾角", "真厚", "描述")
    data = [hdr,
            ["组", "", "147.05 151.11", "3.20 4.06", "3.20 3.40", "19°", "3.03 3.82", "砂质泥岩。"],
            ["", "", "152.91", "1.8", "1.8", "", "1.69", "砂质泥岩:中层状。"]]
    d2, b2, ops, led = unstuck_chain(data, [100, 300, 400])
    assert [(o[0], o[1]) for o in ops] == [("over", 2), ("split", 2)]
    assert [r[2] for r in d2[1:]] == ["147.05", "151.11", "152.91"]
    assert d2[1][5] == "19°" and d2[2][5] is None         # 倾角留首行,次行清空
    assert d2[2][7] is None and d2[2][0] is None          # 次行描述/时代清空
    assert d2[2][3] == "4.06" and d2[2][6] == "3.82"
    assert b2 == [100, 200, 300, 400]                     # 拆中点
    assert led == []


def test_unstuck_chain_1037r79碎片不拆():
    """单列双值+下行自有深度(1037 r79 真厚'0.23 79')→ 留首值弃碎片,不拆行。"""
    from src.table.finalize_tables import unstuck_chain
    hdr = ("时代", "层号", "深度", "层厚", "采长", "倾角", "真厚", "描述")
    data = [hdr,
            ["", "", 496.6, 0.23, 0.1, "", "0.23 79", "泥质粉砂岩。"],
            ["", "", 498.4, 1.8, 1.25, "", None, None]]
    d2, b2, ops, led = unstuck_chain(data, [100, 200, 300])
    assert len(d2) == 3                                   # 行数不变
    assert d2[1][6] == "0.23" and d2[1][2] == 496.6       # 留首值
    assert [(o[0], o[1]) for o in ops] == [("over", 2)]
    assert len(led) == 1 and "79" in led[0]["原"]         # 弃碎片记账


def test_unstuck_chain_1044r75深度点还原():
    """≥3 列对但链差 10 的幂(1044 r75 '29556/29646'÷100)→ 还原后拆+记账。"""
    from src.table.finalize_tables import unstuck_chain
    hdr = ("时代", "层号", "深度", "层厚", "采长", "倾角", "真厚", "描述")
    data = [hdr,
            ["", "", "29556 29646", "6.20 0.90", "6.15 0.90", "", "6.06 0.88", "粉砂岩。"],
            ["", "", "297.10", "0.64", "0.60", "", "0.63", "粉砂岩:深灰色。"]]
    d2, b2, ops, led = unstuck_chain(data, [100, 300, 400])
    assert [r[2] for r in d2[1:]] == ["295.56", "296.46", "297.10"]
    assert len(led) == 1 and "÷100" in led[0]["依据"]
    assert [(o[0], o[1]) for o in ops] == [("over", 2), ("split", 2)]


def test_unstuck_chain_1029r41四值拆():
    """≥3 列 4 值并格+全链闭合(1029 r41:291.67-1.73=289.94 等三段全闭)→
    拆 4 行,2 值列第 3/4 行清空,单值列留首行。"""
    from src.table.finalize_tables import unstuck_chain
    hdr = ("时代", "层号", "深度", "层厚", "采长", "倾角", "真厚", "描述")
    data = [hdr,
            ["组", "", "289.94 291.67 293.30 307.49", "0.40 1.73 1.63 14.19",
             "0.40 1.72", "19°", "0.40 1.72 1.62 14.09", "砂质泥岩。"],
            ["", "", "321.68", "14.19", "", "", "14.00", "下一行。"]]
    d2, b2, ops, led = unstuck_chain(data, [100, 500, 600])
    assert len(d2) == 6                                   # hdr + 4 拆行 + 下一行
    assert [r[2] for r in d2[1:5]] == ["289.94", "291.67", "293.30", "307.49"]
    assert [r[3] for r in d2[1:5]] == ["0.40", "1.73", "1.63", "14.19"]
    assert [r[6] for r in d2[1:5]] == ["0.40", "1.72", "1.62", "14.09"]
    assert d2[1][4] == "0.40" and d2[2][4] == "1.72"      # 2值列前两行承接
    assert d2[3][4] is None and d2[4][4] is None          # 第3/4行采长清空
    assert d2[1][5] == "19°" and d2[2][5] is None         # 单值列留首行
    assert d2[5][2] == "321.68"                           # 下一行原样
    assert [(o[0], o[1]) for o in ops] == [("over", 2), ("split", 2)]
    assert len(ops[1][2]) == 3                            # split 携带 3 个次行
    assert led == []
    assert b2[:5] == [100, 200, 300, 400, 500]            # 4行均分区间


def test_normalize_dip_column_补度号记账():
    """倾角列裸数字补°(12.6 丢失步骤恢复):裸数/数值补°,带°/空/文字不动,逐格记账。"""
    from openpyxl import Workbook
    from src.table.finalize_tables import normalize_dip_column
    wb = Workbook()
    ws = wb.active
    ws.append(["h"] * 8)
    for v in (3, "4°", None, "x", 5):
        ws.append([""] * 5 + [v] + ["", ""])
    led = []
    n = normalize_dip_column(ws, led)
    assert n == 2
    assert [ws.cell(row=r, column=6).value for r in range(2, 7)] == ["3°", "4°", None, "x", "5°"]
    assert len(led) == 2 and led[0]["原"] == "3" and led[0]["新"] == "3°" and led[0]["来源"] == "规则"
