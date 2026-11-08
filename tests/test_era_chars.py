# -*- coding: utf-8 -*-
"""时代列整字裁剪器测试:纯函数(文法/分组/前置体检)与合成图像(弯曲条带/穿线字)。"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.table.era_chars import (_band_ink_frac, char_boxes, era_strip,
                                 extend_sep_by_ink, extract_from_arrays,
                                 parse_era_name, preflight_checks, split_bands,
                                 strip_header_label)


def test_parse_era_name():
    assert parse_era_name("第四系") == ("valid", "")
    assert parse_era_name("龙潭组上段") == ("valid", "")
    assert parse_era_name("茅口组") == ("valid", "")
    assert parse_era_name("上段")[0] == "suspect"          # 组名丢失前文
    assert parse_era_name("龙潭组上段茅口组")[0] == "suspect"  # 未分带(内含可断点)
    assert parse_era_name("酒")[0] == "invalid"             # 单字
    assert parse_era_name("三八")[0] == "invalid"            # 末字非系群组段阶
    assert parse_era_name("龙2组")[0] == "invalid"           # 非CJK
    assert parse_era_name("")[0] == "invalid"


def test_split_bands():
    cs = [("第", 0, 40), ("四", 60, 100), ("系", 120, 160), ("龙", 300, 340),
          ("潭", 360, 400), ("组", 420, 460), ("上", 480, 520), ("段", 540, 580),
          ("茅", 700, 740), ("口", 760, 800), ("组", 820, 860)]
    bands = split_bands(cs)   # [(名, 首y0, 末y1), ...]
    assert [b[0] for b in bands] == ["第四系", "龙潭组上段", "茅口组"]
    assert bands[0][1] == 0 and bands[0][2] == 160
    assert bands[1][1] == 300 and bands[1][2] == 580
    # 组后跟限定字不断名
    cs2 = [("大", 0, 40), ("隆", 60, 100), ("组", 120, 160)]
    assert [b[0] for b in split_bands(cs2)] == ["大隆组"]


def _synthetic_curved():
    """200x600 灰图:弯曲列界(斜率±0.05)、两个字块、一条弯行线穿过字B中心。"""
    gray = np.full((600, 200), 255, np.uint8)
    L = lambda y: 20 + 0.05 * (y - 300)
    R = lambda y: 180 - 0.05 * (y - 300)
    for y in range(600):
        for f in (L, R):
            x = int(f(y))
            gray[y, max(0, x - 1):x + 2] = 0
    gray[60:110, 80:120] = 0                                    # 字A(无穿线)
    for x in range(70, 130):                                    # 弯行线
        gray[300 + int(0.03 * (x - 100)), x] = 0
    gray[280:340, 80:120] = 0                                   # 字B(行线穿过中心)
    left = {"ys": [0, 599], "xs": [float(L(0)), float(L(599))]}
    right = {"ys": [0, 599], "xs": [float(R(0)), float(R(599))]}
    rows = [{"poly": [[0, 301], [199, 295]]}]
    return gray, left, right, rows


def test_strip_curved_and_line_prior():
    gray, left, right, rows = _synthetic_curved()
    band, ys, x0i = era_strip(gray, left, right, rows)
    boxes = char_boxes(band, ys)
    assert len(boxes) == 2                       # 穿线字=一整块,不是两块
    assert boxes[0][1] - boxes[0][0] >= 45       # 字A高度完整(50px)
    # 穿线字B:剔除行线窄带后仍应拼成一整块(280~340)
    assert boxes[1][0] <= 282 and boxes[1][1] >= 338


def test_strip_边缘截断不外推():
    gray, left, right, rows = _synthetic_curved()
    L = lambda y: 20 + 0.05 * (y - 300)
    left = {"ys": [100, 400], "xs": [float(L(100)), float(L(400))]}   # 只覆盖中段
    band, ys, x0i = era_strip(gray, left, right, rows)                # 不抛异常
    assert band.shape[0] == len(ys) and x0i >= 0
    assert all(ys[0] <= b[0] and b[1] <= ys[-1] for b in char_boxes(band, ys))


def test_char_boxes_扁平字二遍收复():
    """一/二类扁平字游程 3~8 行高,主 pass 高度滤掉;二遍按墨宽收复(1026 实测漏字)。"""
    band = np.zeros((400, 90), bool)
    band[50:100, 30:60] = True       # 高字1
    band[200:206, 30:63] = True      # "一"(h=6, 墨宽33)
    band[250:256, 30:51] = True      # "二"上杠(h=6,w=21)
    band[285:291, 30:63] = True      # "二"下杠(间隙29/跨度41=1040 型,仍并)
    band[350:395, 30:60] = True      # 高字2
    band[120:121, 40:43] = True      # 噪点(h=1,墨宽3)→不收
    band[155:157, 10:80] = True      # 宽残线(h=2,墨宽70>50)→不收
    boxes = char_boxes(band, np.arange(400))
    assert len(boxes) == 4, boxes
    assert boxes[0] == (50, 99) and boxes[-1] == (350, 394)   # runs_of 端点含端
    assert boxes[1] == (200, 205)                              # 一
    assert boxes[2] == (250, 290)                              # 二(两杠并一块)


def test_preflight_pf1_pf3():
    hm = {"band": [1000, 5000], "keep": [{"left_sep": 0, "right_sep": 1}],
          "sep_pts": [{"ys": [900, 5100], "xs": [20, 24]},
                      {"ys": [900, 5100], "xs": [180, 176]}]}
    rd = {"table_x": [200, 2000], "n_era_full": 3, "n_era_partial": 0,
          "rows": [{"poly": [[0, y], [2000, y]]} for y in range(1000, 5000, 50)]}
    rep = preflight_checks(hm, rd)          # 纯函数,不读盘
    assert rep["PF1_列界覆盖率"] >= 0.99 and rep["ok"]
    assert rep["PF2_时代界行接触率"] == 1.0 and rep["PF3_行序违规"] == []
    hm2 = copy.deepcopy(hm)
    hm2["sep_pts"][0]["ys"] = [900, 2000]   # 左界只覆盖到y=2000
    rep2 = preflight_checks(hm2, rd)
    assert rep2["PF1_列界覆盖率"] < 0.99 and not rep2["ok"]
    rd3 = dict(rd, n_era_partial=1)          # 时代界行有未接触左框的
    rep3 = preflight_checks(hm, rd3)
    assert rep3["PF2_时代界行接触率"] < 0.99 and not rep3["ok"]
    rd4 = dict(rd, n_era_full=0, n_era_partial=0)   # 西延整体缺席(如无闭合外框跳过)
    assert not preflight_checks(hm, rd4)["ok"]


def test_extract_schema_with_stub_ocr():
    gray, left, right, rows = _synthetic_curved()
    out = extract_from_arrays(gray, left, right, rows, band_top=0,
                              ocr_fn=lambda crop: "龙" if crop.shape[0] < 100 else "第四系")
    assert set(out) >= {"strip_y0", "strip_y1", "chars", "bands", "preflight"}
    assert out["bands"][0]["name"] == "第四系"
    assert all("y0" in c and "ocr" in c for c in out["chars"])
    assert all(b["判定"] in ("valid", "suspect", "invalid") for b in out["bands"])


def test_strip_header_label():
    # PF4 实测:表头"地质时代"字块越入条带顶,首名带被污染
    bands = [{"name": "时代飞仙关组", "y0": 926, "y1": 1673, "判定": "valid", "原因": ""}]
    out, cut = strip_header_label(bands, "地质时代")
    assert cut == "时代" and out[0]["name"] == "飞仙关组"
    out2, cut2 = strip_header_label([{"name": "代第四系", "y0": 825, "y1": 1126}],
                                    "地质时代")
    assert cut2 == "代" and out2[0]["name"] == "第四系"
    # 首带全是表头残字 → 整带剔除
    out3, cut3 = strip_header_label([{"name": "时代", "y0": 926, "y1": 1040}], "地质时代")
    assert cut3 == "时代" and out3 == []
    # 前置噪声字符(OCR 读出的字母/符号)连同标签后缀一起剥(1016 实测 "H代第四系")
    out5, cut5 = strip_header_label([{"name": "H代第四系", "y0": 825, "y1": 1126}],
                                    "地质时代")
    assert cut5 == "H代" and out5[0]["name"] == "第四系"
    # 不以标签后缀开头 → 原样返回
    out4, cut4 = strip_header_label([{"name": "第四系"}], "地质时代")
    assert cut4 is None and out4[0]["name"] == "第四系"

def test_pf3_行高取带内重叠中点_而非表心():
    """PF3 曾在**表心中点** x 处取行高;短行到不了那里,row_y 夹到端点值 → 假违规。

    1030 实测:第7行 poly 跨度 [252,763],表心 x=1540 在其右,row_y 返回端点 4626.0,
    与上一行 4628.6 差 −2.6 被判"行序违规";而该行在时代带 [196.7,261.0] 内的真实
    高度是 4627.9(重叠区间中点),与上一行带内高度 4556.2 相差 71.7px,完全正常。
    1042 同病(第11行 [240,595] 报 +7.7)。判据改为在"行线与时代带的真实重叠区间
    中点"取 y;完全不重叠的行才不参与。
    """
    hm = {"band": [0, 100], "keep": [{"left_sep": 0, "right_sep": 1}],
          "sep_pts": [{"ys": [0, 10000], "xs": [200.0, 200.0]},
                      {"ys": [0, 10000], "xs": [260.0, 260.0]}]}
    # 前一行:带内(左端)y=4556,到表心 x=1200 已降到 4628.6 —— 1030 第6行实测形状
    wide_prev = {"poly": [[180, 4556.0], [1200, 4628.6], [2200, 4628.6]]}
    short = {"poly": [[252, 4627.9], [763, 4626.0]]}        # 只到 x=763,不达表心
    rd = {"table_x": [200, 2200], "n_era_full": 2, "n_era_partial": 0,
          "rows": [wide_prev, short]}
    rep = preflight_checks(hm, rd)
    assert rep["PF3_行序违规"] == [], rep["PF3_行序违规"]
    assert rep["ok"]


def test_pf3_真违规仍被抓():
    """收紧口径不能放过真违规:两行都完整横穿时代带且带内间距过近,必须报。"""
    hm = {"band": [0, 100], "keep": [{"left_sep": 0, "right_sep": 1}],
          "sep_pts": [{"ys": [0, 10000], "xs": [200.0, 200.0]},
                      {"ys": [0, 10000], "xs": [260.0, 260.0]}]}
    a = {"poly": [[180, 4000], [2200, 4000]]}
    b = {"poly": [[180, 4003], [2200, 4003]]}     # 带内间距 3px < 8
    rd = {"table_x": [200, 2200], "n_era_full": 2, "n_era_partial": 0,
          "rows": [a, b]}
    rep = preflight_checks(hm, rd)
    assert len(rep["PF3_行序违规"]) == 1 and not rep["ok"]


def test_pf1_分母取时代列墨迹范围而非整张数据区():
    """PF1 曾在整个数据区 y 上量列界覆盖率 → 时代列在表底自然终止的图被误判。

    1017 实测:时代列墨迹只到 y=9261(下面一片空白,原图如此),数据区却到 9863,
    覆盖率算成 0.9325 而拒裁;时代列自身 0 缺口。分母改为该列墨迹 y 范围
    (条带内文字墨的上下界),只在墨迹范围内量列界有无断口。
    """
    hm = {"band": [0, 100], "keep": [{"left_sep": 0, "right_sep": 1}],
          "sep_pts": [{"ys": [1000, 5000], "xs": [200.0, 200.0]},
                      {"ys": [1000, 5000], "xs": [260.0, 260.0]}]}
    rd = {"table_x": [200, 2200], "n_era_full": 3, "n_era_partial": 0,
          "rows": [{"poly": [[180, y], [2200, y]]} for y in range(1000, 5100, 50)]}
    rep = preflight_checks(hm, rd, ink_y=(1000, 5000))
    assert rep["PF1_列界覆盖率"] == 1.0 and rep["ok"]
    rep2 = preflight_checks(hm, rd, ink_y=(1000, 8000))   # 墨迹到 8000,列界只到 5000
    assert rep2["PF1_列界覆盖率"] < 0.99 and not rep2["ok"]

def _syn_strip_with_gap():
    """合成:左列界在 y=200..400 有折线,400..600 只有墨迹(折线没记到)。"""
    gray = np.full((700, 400), 255, np.uint8)
    gray[:, 150:154] = 60                      # 左列界竖线(全高)
    gray[:, 300:304] = 60                      # 右列界竖线(全高)
    left = {"ys": [200.0, 400.0], "xs": [152.0, 152.0]}
    right = {"ys": [200.0, 600.0], "xs": [302.0, 302.0]}
    return gray, left, right


def test_外延_沿墨迹把折线补到墨迹末端():
    """C 类缺口:列界折线断了,但原图墨迹还在(1023/1025/1028 实测追踪命中 99.6%/98.9%/99.9%)。

    约束2 允许的"墨迹验证外延":落点全是原图实测的细行程中心,不创造原图不存在的线。
    合成图里左列界折线只到 y=400,墨迹一直到 600 —— 应补到 600,且 x 落在 152。
    """
    gray, left, right = _syn_strip_with_gap()
    xs, ys = extend_sep_by_ink(gray, left, y_stop=600)
    assert ys[-1] >= 595, ys[-1]
    assert all(abs(x - 152.0) <= 3.0 for x in xs[-20:]), xs[-20:]
    assert len(ys) > len(left["ys"])


def test_外延_无墨处不外延():
    """墨迹不在时绝不出点(不创造原图不存在的线)。"""
    gray = np.full((700, 400), 255, np.uint8)
    gray[200:400, 150:154] = 60                    # 墨迹止于 400,折线下方是空白
    left = {"ys": [200.0, 400.0], "xs": [152.0, 152.0]}
    xs, ys = extend_sep_by_ink(gray, left, y_stop=600)
    assert ys[-1] == 400.0, ys[-1]                 # 一点没加


def test_外延_不吸到相邻文字笔画():
    """外延只在容差内跟线;墨迹偏出容差就停,不许跳到别的笔画上。"""
    gray = np.full((700, 400), 255, np.uint8)
    gray[200:400, 150:154] = 60
    gray[400:600, 260:264] = 60                    # 断口下方 110px 外另一条竖线
    left = {"ys": [200.0, 400.0], "xs": [152.0, 152.0]}
    xs, ys = extend_sep_by_ink(gray, left, y_stop=600)
    assert ys[-1] < 410, ys[-1]
    assert all(abs(x - 152.0) <= 3.0 for x in xs), xs

def test_pf5_时代列带宽跳变被抓():
    """1019 实测:时代列右界折线在 y≈4377 处跳到相邻列(x 346→409,正好一个格宽),
    带宽从 62px 变成 125px 再变 158px,整条带子后半张圈进了煤层标志层号列。

    这道闸量的就是"带宽稳不稳":真时代列是印刷竖线,带宽在整表内几乎恒定。
    30 张实测 p90/p10 除 1019(2.53)外全部 ≤1.11,判据取 1.30(最坏正常值 1.11 + 余量)。
    """
    hm = {"band": [0, 100], "keep": [{"left_sep": 0, "right_sep": 1}],
          "sep_pts": [{"ys": [0, 10000], "xs": [200.0, 200.0]},
                      {"ys": [0, 10000], "xs": [262.0, 262.0]}]}
    rd = {"table_x": [200, 2200], "n_era_full": 2, "n_era_partial": 0,
          "rows": [{"poly": [[180, y], [2200, y]]} for y in range(1000, 10000, 200)]}
    rep = preflight_checks(hm, rd)
    assert rep["PF5_带宽比"] <= 1.01 and rep["ok"]
    # 右界在中段跳到 +63px 的相邻列
    hm2 = copy.deepcopy(hm)
    hm2["sep_pts"][1]["ys"] = [0, 4000, 4001, 10000]
    hm2["sep_pts"][1]["xs"] = [262.0, 262.0, 325.0, 325.0]
    rep2 = preflight_checks(hm2, rd)
    assert rep2["PF5_带宽比"] > 1.30 and not rep2["ok"]
    assert "带宽" in rep2["原因"]

def test_无时代列图判不适用不静默回绕():
    """1032 扫描左缘被裁,keep[0] 已是"深度"且 left_sep=-1。

    Python 的 -1 会静默回绕到 sep_pts 最后一条(右外框),于是"时代列"变成
    右外框到右外框、带宽 0、PF5 算出 inf —— 全是假数。必须显式判"不适用"。
    """
    hm = {"band": [0, 100], "keep": [{"name": "深度", "left_sep": -1, "right_sep": 0}],
          "sep_pts": [{"ys": [0, 10000], "xs": [150.0, 150.0]},
                      {"ys": [0, 10000], "xs": [2900.0, 2900.0]}]}
    rd = {"table_x": [150, 2900], "n_era_full": 0, "n_era_partial": 0,
          "rows": [{"poly": [[140, y], [2900, y]]} for y in range(1000, 9000, 200)]}
    rep = preflight_checks(hm, rd)
    assert rep["ok"] is False and rep.get("不适用") is True
    assert "不适用" in rep["原因"]
def test_pf5_两侧同向漂移也抓得住():
    """1042 实测:时代列左右两界同向漂移(左 70→191、右 197→325),带宽比只有 1.08,
    比值闸放行;但左界其实是**装饰轨**不是表框,条带把装饰轨一起圈进去了 ——
    条带里因此多出一条满高竖线,逐行几乎行行有墨(实测 94.6%),字块检测直接归零。

    比值闸对"两边一起漂"是盲的,所以另量条带内部墨迹:真时代列只在有字的地方有墨
    (30 张实测逐行有墨率 0.066~0.114),混进竖线则接近 1.0(1019=0.766、1042=0.946)。
    判据取 0.30(正常最坏 0.114 + 余量,离 0.766 还有 2.5 倍距离)。
    """
    clean = np.zeros((1000, 60), bool)
    clean[100:180, 20:40] = True
    clean[400:480, 20:40] = True
    assert _band_ink_frac(clean) < 0.30
    dirty = clean.copy()
    dirty[:, 5:9] = True                   # 混进一条满高竖线
    assert _band_ink_frac(dirty) > 0.30