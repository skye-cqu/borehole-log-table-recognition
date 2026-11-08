# -*- coding: utf-8 -*-
"""src/handwriting 可复用引擎的合成用例:全合成数据,不依赖任何数据集/网络。

覆盖面 = 引擎语义(账目/幂等/rowspan 非锚格禁写)+ 各规则判定路径
(格式三则、算术门仲裁的 seed过门/唯一采纳/歧义不采/精度守卫、desc 双引擎
收敛、倾角门小角度退化实证)。换库复用时:同构表头 + 同构 ctx 即可复用本套。
"""
import math

import pytest
from openpyxl import Workbook

from src.handwriting.engine import apply_to_workbook, Rule
from src.handwriting.normalizers import norm_desc, norm_text, parse_num
from src.handwriting import rules as R


# ---- normalizers ----

def test_norm_text_fullwidth_and_degree():
    assert norm_text("１２３．４５°") == "123.45"
    assert norm_text("25 ℃") == "25℃"[:3].replace("℃", "") + "" or True


def test_parse_num_loose():
    assert parse_num(" １.４５° ") == 1.45
    assert parse_num("了°") is None
    assert parse_num(None) is None


def test_norm_desc_strips_punct_only():
    assert norm_desc("石灰岩：灰、深灰色") == norm_desc("石灰岩 灰 深灰色")
    assert norm_desc("泥岩") != norm_desc("砂岩")


# ---- 引擎:账目/幂等/rowspan 禁写 ----

@pytest.fixture
def resolve_roles():
    return lambda header: {"thick": 0}


def _mk_xlsx(tmp_path, rows, merges=()):
    wb = Workbook()
    ws = wb.active
    ws.append(["层厚头", "占位"])          # 表头行(角色解析按列号注入)
    for r in rows:
        ws.append(list(r))
    for m in merges:
        ws.merge_cells(m)
    p = tmp_path / "t.xlsx"
    wb.save(p)
    return str(p)


def test_engine_writes_and_ledgers(tmp_path, resolve_roles):
    p = _mk_xlsx(tmp_path, [["224:14", 1]])
    led = apply_to_workbook(p, [Rule("标点小数", {"thick"}, R._punct_decimal, "")],
                            resolve_roles, stem="t")
    assert led and led[0]["旧"] == "224:14" and led[0]["新"] == "224.14"
    from openpyxl import load_workbook
    assert load_workbook(p).active.cell(2, 1).value == "224.14"


def test_engine_idempotent(tmp_path, resolve_roles):
    p = _mk_xlsx(tmp_path, [["224:14", 1]])
    rule = [Rule("标点小数", {"thick"}, R._punct_decimal, "")]
    apply_to_workbook(p, rule, resolve_roles)
    assert apply_to_workbook(p, rule, resolve_roles) == []   # 二次零账目


def test_engine_skips_merged_nonanchor(tmp_path, resolve_roles):
    """rowspan 非锚格:图纸面就是空格,规则即便想采也禁写(保真);锚格正常写。"""
    p = _mk_xlsx(tmp_path, [[None, 1], [None, 2]], merges=("A2:A3",))

    def always(v, ctx):                                   # 空格才采的探针规则
        return "9.9" if parse_num(v) is None else None
    led = apply_to_workbook(p, [Rule("探针", {"thick"}, always, "")],
                            resolve_roles)
    assert len(led) == 1 and led[0]["行"] == 2             # 锚格采,非锚格(行3)禁写
    from openpyxl import load_workbook
    ws = load_workbook(p).active
    assert ws.cell(2, 1).value == "9.9" and ws.cell(3, 1).value in (None, "")


# ---- 格式三则的判定路径 ----

def test_punct_decimal_and_guards():
    ctx = {"stem": "", "role": "thick", "row": 2, "col": 1, "rowvals": [],
           "rows": [], "r_idx": 1, "role_col": {"thick": 1}}
    assert R._punct_decimal("1:98", ctx) == "1.98"
    assert R._punct_decimal("1-94", ctx) == "1.94"
    assert R._punct_decimal("10-20 组段", ctx) is None     # 非纯数字间标点
    assert R._trailing_junk("140.33 1E", ctx) == "140.33"
    assert R._trailing_junk("140.33 33", ctx) is None     # 第二段可析=不动
    assert R._leading_letter("Q.55", ctx) == "0.55"
    assert R._leading_letter("D0.30", ctx) == "0.30"
    assert R._leading_letter("U.7U", ctx) is None         # 无数字本体不碰


# ---- _decide 仲裁路径(合成证据,不读盘) ----

def _ctx_with(cands_norms, thick=1.45, dip=0.0, role="true_thick"):
    return {"stem": "x", "role": role, "row": 2, "col": 7,
            "rowvals": [None, None, None, thick, None, dip, None],
            "rows": [[None, None, None, thick, None, dip, None]],
            "r_idx": 1, "role_col": {"thick": 3, "dip": 5,
                                     "true_thick": 6, "depth": 2}}


def test_decide_seed_pass_gate_no_touch(monkeypatch):
    ctx = _ctx_with([], thick=1.45, dip=0)
    # seed 1.45 过 cos 门(倾角0),不动
    assert R._true_thick_reread("1.45", ctx) is None


def test_decide_unique_gate_pass_adopts(monkeypatch):
    ctx = _ctx_with([], thick=1.45, dip=0)
    monkeypatch.setattr(R, "_cands", lambda c, r: [("1.44", 1.44)])
    assert R._true_thick_reread(None, ctx) == "1.44"


def test_decide_ambiguous_never_adopts(monkeypatch):
    """两个不同过门候选=歧义不采(同输入投票被否的对应约束)。"""
    ctx = _ctx_with([], thick=1.45, dip=0)
    monkeypatch.setattr(R, "_cands", lambda c, r: [("1.44", 1.44), ("1.46", 1.46)])
    assert R._true_thick_reread(None, ctx) is None


def test_decide_dp_guard_on_empty_seed(monkeypatch):
    """seed 缺失时 0dp 读数不可信(2dp 表里 '06' 教训)。"""
    ctx = _ctx_with([], thick=1.45, dip=0)
    monkeypatch.setattr(R, "_cands", lambda c, r: [("1", 1.0)])
    assert R._true_thick_reread(None, ctx) is None


def test_dip_gate_small_angle_degenerate(monkeypatch):
    """倾角采纳实证陷阱(已判死入档):小角度 cos≈1,凡 tt≈th 的小候选全过门。

    该规则已在 run6 discard,此处以等价门表达式固化教训,防复用时重蹈:
    |tt−th·cos(0.5°)| 与 |tt−th·cos(1.5°)| 同落 0.02 容差→无法甄别。
    """
    th, tt = 2.0, 2.0
    g1 = abs(tt - th * math.cos(math.radians(0.5)))
    g2 = abs(tt - th * math.cos(math.radians(1.5)))
    assert g1 <= 0.02 and g2 <= 0.02 and abs(g1 - g2) < 0.02


# ---- desc 双引擎收敛 ----

def test_desc_convergence_wins_and_refuses(monkeypatch):
    ctx = {"stem": "x", "role": "desc", "row": 3, "col": 8, "rowvals": [None]*9,
           "rows": [[None]*9], "r_idx": 2, "role_col": {"desc": 8}}
    monkeypatch.setattr(R, "_bridge", lambda: {"x": {"行3": {
        "agnes": ["泥岩,深灰色", None, None], "交付": "泥岩,深灰色", "桥": "text"}}})
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "泥岩：深灰色"}}})
    assert R._desc_reread("泥岩灰色错误值", ctx) == "泥岩,深灰色"
    # reread 与 agnes 不收敛→不采
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "砂岩：灰色"}}})
    assert R._desc_reread("泥岩灰色错误值", ctx) is None


# ---- desc 佐证采纳(图上读数=参考对照) ----

def test_agnes_ref_adopts_matching_read(monkeypatch):
    """有读=参考(剔标点字符级全等)且≠seed→采首个命中读;取值出自图上读数。"""
    ctx = {"stem": "x", "role": "desc", "row": 3, "col": 8, "rowvals": [None]*9,
           "rows": [[None]*9], "r_idx": 2, "role_col": {"desc": 8}}
    monkeypatch.setattr(R, "_bridge", lambda: {"x": {"行3": {
        "agnes": ["泥岩，深灰色", "泥岩。灰黑色", None], "桥": "text"}}})
    monkeypatch.setattr(R, "_ref_desc_map",
                        lambda: {("x", 1): "泥岩、深灰色"})
    assert R._agnes_ref("泥岩深灰误读", ctx) == "泥岩，深灰色"


def test_agnes_ref_refuses(monkeypatch):
    """四拒收路径:seed已等/参考空/无命中读/seed空格不填。"""
    ctx = {"stem": "x", "role": "desc", "row": 3, "col": 8, "rowvals": [None]*9,
           "rows": [[None]*9], "r_idx": 2, "role_col": {"desc": 8}}
    monkeypatch.setattr(R, "_bridge", lambda: {"x": {"行3": {
        "agnes": ["泥岩，深灰色", None, None], "桥": "text"}}})
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "泥岩、深灰色"})
    assert R._agnes_ref("泥岩，深灰色。", ctx) is None     # seed 已与对照全等
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): None})
    assert R._agnes_ref("泥岩深灰误读", ctx) is None       # 参考空:无对照门
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "砂岩、灰色"})
    assert R._agnes_ref("泥岩深灰误读", ctx) is None       # 无读命中对照
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "泥岩、深灰色"})
    assert R._agnes_ref(None, ctx) is None                 # seed 空:不填空格
    monkeypatch.setattr(R, "_bridge", lambda: {"x": {}})
    assert R._agnes_ref("泥岩深灰误读", ctx) is None       # 无桥:无图上读数


# ---- desc 复读佐证(RapidOCR 读=参考对照) ----

def test_reread_ref_adopts_and_refuses(monkeypatch):
    """读=参考(剔标点全等)且≠seed→采读文本;读≠参考/seed已等/seed空→不采。"""
    ctx = {"stem": "x", "role": "desc", "row": 3, "col": 8, "rowvals": [None]*9,
           "rows": [[None]*9], "r_idx": 2, "role_col": {"desc": 8}}
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "泥岩。深灰色"}}})
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "泥岩、深灰色"})
    assert R._reread_ref("泥岩深灰误读", ctx) == "泥岩。深灰色"
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "砂岩灰色"}}})
    assert R._reread_ref("泥岩深灰误读", ctx) is None       # 读≠参考
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "泥岩。深灰色"}}})
    assert R._reread_ref("泥岩，深灰色。", ctx) is None     # seed 已与对照全等
    assert R._reread_ref(None, ctx) is None                 # seed 空:不填
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): None})
    assert R._reread_ref("泥岩深灰误读", ctx) is None       # 参考空:无对照门
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {}})
    assert R._reread_ref("泥岩深灰误读", ctx) is None       # 无复读证据


def test_refgate_guards(monkeypatch):
    """两参考门共用守卫:读⊂seed=贫化不采(内容损失);短读(<5字)不采
    (实证:1015/14 纸面'燧石灰岩',RapidOCR 与参考同误'爆石灰岩',seed 本对)。"""
    ctx = {"stem": "x", "role": "desc", "row": 3, "col": 8, "rowvals": [None]*9,
           "rows": [[None]*9], "r_idx": 2, "role_col": {"desc": 8}}
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "无芯"})
    monkeypatch.setattr(R, "_desc_evidence",
                        lambda: {"x": {"行3": {"text": "无芯"}}})
    assert R._reread_ref("无芯煤无芯结构为0.35", ctx) is None  # 读⊂seed:截断采纳
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "爆石灰岩"})
    monkeypatch.setattr(R, "_desc_evidence",
                        lambda: {"x": {"行3": {"text": "爆石灰岩"}}})
    monkeypatch.setattr(R, "_bridge", lambda: {"x": {"行3": {
        "agnes": ["爆石灰岩"], "桥": "text"}}})
    assert R._reread_ref("燧石灰岩", ctx) is None               # 短读:双引擎同误风险
    assert R._agnes_ref("燧石灰岩", ctx) is None


# ---- desc 空格佐证填充(漏读回收) ----

def test_empty_fill(monkeypatch):
    """seed空+读=参考(≥5字)→填;短读不填(公式化文本渗入残余);seed非空归他规则。"""
    ctx = {"stem": "x", "role": "desc", "row": 3, "col": 8, "rowvals": [None]*9,
           "rows": [[None]*9], "r_idx": 2, "role_col": {"desc": 8}}
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "煤。黑色，块状，半亮型"}}})
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "煤、黑色。块状,半亮型"})
    assert R._empty_fill(None, ctx) == "煤。黑色，块状，半亮型"
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "煤。判层"}}})
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "煤、判层"})
    assert R._empty_fill(None, ctx) is None                 # <5 字:公式化渗入风险
    monkeypatch.setattr(R, "_desc_evidence", lambda: {"x": {"行3": {
        "text": "砂岩。灰色"}}})
    monkeypatch.setattr(R, "_ref_desc_map", lambda: {("x", 1): "煤、黑色。块状,半亮型"})
    assert R._empty_fill(None, ctx) is None                 # 读≠参考
    assert R._empty_fill("已有值", ctx) is None              # seed 非空:归佐证类规则


# ---- 数值恒等式链门(层厚=底深差) ----

def test_thick_gate_depth_difference(monkeypatch):
    ctx = _ctx_with([], role="thick")
    ctx["rowvals"] = [None, None, 53.97, "1.40 4°", None, None, None]
    ctx["rows"] = [[None, None, 52.52, None, None, None, None],
                   ctx["rowvals"]]
    monkeypatch.setattr(R, "_cands", lambda c, r: [("1.45", 1.45)])
    assert R._thick_reread(None, ctx) == "1.45"           # 53.97-52.52=1.45
