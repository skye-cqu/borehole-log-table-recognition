# -*- coding: utf-8 -*-
"""时代列(keep[0] 地质时代)整字裁剪器 + 前置体检。

背景:行界线在原图直接穿过竖排时代名(如"龙潭组上段"一字一行带),按行切格把字拦腰
切成两半分属相邻两格,OCR 见半字→空/误读(1016 实测"潭"→"酒"、"中"→"山")。
本模块改为按"字"切:列界走 sep_pts 折线逐行插值、行线走行判定折线逐列插值,
全程曲线、零直线假设;行线位置来自行判定定稿(已知先验),不做"是不是线"的阈值判定——
只在已知行线 ±窄带内排除墨计数,字块检测不受字内长横干扰;OCR 裁片回原图取原始像素
(线穿字不删像素,OCR 本身认得带线的字)。

判据出处(2026-10-10 调研):先验删线+复原(ruling line removal without breaking
characters 一系)与拓扑验证(行线假设须两端接触竖界)两条成熟路线;本模块用前者,
后者作为行检测层守卫已在 6c 门禁存在。验收门禁独立在 src/tools/audit_era_column.py
(G1 墨迹收支/G2 命名文法/G3 名带区间/G4 跨图一致),判分不读本模块内部。

用法:
  python src/table/era_chars.py --preflight 1016 1022 ...   # 前置体检,FAIL 退出 1
  python src/table/era_chars.py 1016 1022 ...               # 整字裁剪,产物落 ERA_CHAR_DIR
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.table.reconstruct_excel import _crop_cell
from src.table.rect_struct import strip_band
from src.table.track_rows import row_y

# ---- 常量(全部在试点图实测后回填推导链,见 tests 与 audit_era_column) ----
LINE_BAND_PAD = 2      # 行线窄带=折线y ± (线宽半宽估计2px + PAD)
MERGE_GAP = 12         # 字内断口缝合上限 px(行线厚度+pad 实测量级)
MIN_CHAR_H = 15        # 字块高度下限 px(试点字高中位 43~54px 的 ~1/3)
MAX_CHAR_H = 260       # 字块高度上限 px(防整列连块)
FLAT_MIN_H = 3         # 扁平字游程高度下限(1026 实测"一/二"横杠 h=5~6;噪点 h=1 排除)
FLAT_MIN_W = 15        # 扁平字墨宽下限(实测横杠墨宽 21~33;噪点 3 排除)
FLAT_MAX_W = 50        # 扁平字墨宽上限(残线横贯带宽 70+ 排除;正字墨宽 22~38)
FLAT_GLYPH_H = 45      # 杠形字互并判据=合并后总跨度(1026"二"跨30px、1040"二"跨41px;正字 29~39px)
ENDERS = "系群组段阶"   # 地层单位结尾字(断名)
QUAL = "上中下一二三四五"  # 段限定字(组后跟限定字则不断,"龙潭组上段")


def _is_cjk(ch):
    return "\u4e00" <= ch <= "\u9fff"


def _break_after(text, next_ch=None):
    """text 末字之后是否断名:末字∈ENDERS,且 组+限定字 不断(龙潭组上段一体)。"""
    if not text or text[-1] not in ENDERS:
        return False
    if text[-1] == "组" and next_ch is not None and next_ch in QUAL:
        return False
    return True


def parse_era_name(s):
    """(判定, 原因):valid / suspect(登记不阻塞) / invalid。"""
    if not s or len(s) < 2:
        return "invalid", "空或单字"
    if not all(_is_cjk(c) for c in s):
        return "invalid", "含非CJK"
    if s[-1] not in ENDERS:
        return "invalid", "末字非地层单位字"
    if s[0] in QUAL:
        return "suspect", "首字为段限定字,组名疑丢前文"
    if any(_break_after(s[: i + 1], s[i + 1]) for i in range(len(s) - 1)):
        return "suspect", "内部存在可断名边界,疑未分带"
    return "valid", ""


def split_bands(chars):
    """chars=[(字, y0, y1),...](自上而下)→ [(名, 首块y0, 末块y1), ...]。"""
    bands, cur = [], None
    for i, (ch, y0, y1) in enumerate(chars):
        if cur is None:
            cur = [ch, y0, y1]
        else:
            cur[0] += ch
            cur[2] = y1
        nxt = chars[i + 1][0] if i + 1 < len(chars) else None
        if _break_after(cur[0], nxt):
            bands.append(tuple(cur))
            cur = None
    if cur is not None:
        bands.append(tuple(cur))
    return bands


def era_strip(gray, left, right, rows):
    """列界折线掩膜取条带 + 行折线窄带剔墨。

    left/right: sep_pts 元素({"ys","xs"} 平行数组);rows: 行判定 rows 子集(带 poly)。
    返回 (墨位图 bool[y,x], ys数组, x0i):列界外置白(strip_band)、行线 ±(2+PAD) 置 False。
    y 范围取两列界 ys 的公共覆盖区间;np.interp 出界取端点值,不外推。
    """
    y0 = int(max(left["ys"][0], right["ys"][0]))
    y1 = int(min(left["ys"][-1], right["ys"][-1]))
    band, _, x0i = strip_band(gray, y0, y1,
                              (left["ys"], left["xs"]),
                              (right["ys"], right["xs"]), inset=3)
    band = band.copy()
    ys = np.arange(y0, y1)
    xs_cols = np.arange(x0i, x0i + band.shape[1])
    for r in rows:
        p = np.asarray(r["poly"], float)
        # 与 row_y 同语义(分段线性+出界取近端点),向量化
        ly = np.interp(xs_cols, p[:, 0], p[:, 1])
        lo = np.floor(ly - (2 + LINE_BAND_PAD)).astype(int) - y0
        hi = np.ceil(ly + (2 + LINE_BAND_PAD)).astype(int) - y0
        for k in range(band.shape[1]):
            a, b = max(0, lo[k]), min(band.shape[0], hi[k] + 1)
            if a < b:
                band[a:b, k] = False
    return band, ys, x0i


def char_boxes(band, ys):
    """主 pass:逐 y 墨计数>2 → 游程 → ≤MERGE_GAP 断口缝合 → 高度过滤;
    二 pass:扁平字收复——"一/二"类横杠游程仅 3~8 行高被高度滤掉,按墨宽
    [FLAT_MIN_W,FLAT_MAX_W] 收复、间隙 ≤FLAT_MERGE_GAP 互并(判据=1026 实测)。"""
    from src.table.rect_struct import runs_of
    prof = band.sum(axis=1)
    runs = runs_of(prof > 2)
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] <= MERGE_GAP:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    boxes = [(a, b) for a, b in merged if MIN_CHAR_H <= b - a <= MAX_CHAR_H]
    # 扁平字墨宽上限取 绝对50 与 50%带宽 的较小者:真"一"约为带宽30%(实测21~33/91),
    # 横贯带宽的折痕/残线(1016 实测 62/65px)由此排除
    w_cap = min(FLAT_MAX_W, int(0.5 * band.shape[1]))
    flat = [(a, b) for a, b in merged
            if FLAT_MIN_H <= b - a < MIN_CHAR_H
            and FLAT_MIN_W <= int(band[a:b + 1].any(axis=0).sum()) <= w_cap]
    fused = []
    for a, b in flat:
        if fused and b - fused[-1][0] <= FLAT_GLYPH_H:
            fused[-1][1] = b
        else:
            fused.append([a, b])
    return sorted([(ys[a], ys[b]) for a, b in boxes] + [(ys[a], ys[b]) for a, b in fused])


# ---- 前置体检阈值(实测/计划依据见行尾注释,改动须附新推导链) ----
PF1_MIN_COV = 0.99    # 列界折线须覆盖数据区 y 的 99%(计划定;缺段/断尾在此暴露)
PF2_MIN_CONTACT = 0.99  # 时代界行西延接触左框率;项③实测 30 图 206/206 全接触,试点 5 图亦全接触
PF3_MIN_GAP = 8.0     # 带内相邻行线在带中点处 y 间距下限 px(计划定,行高∝层厚且有下限)
PF4_WARN_INK = 0.01   # 条带顶部 120px 墨占比 >1% 记 warn(表头文字串头),不翻 ok
PF5_MAX_WRATIO = 1.30  # 时代列带宽 p90/p10 上限;30 张实测除 1019(2.53)外全部 ≤1.11
                       # (最坏 1018/1038 1.11),取 1.11+余量。超限=列界折线跳到相邻列
PF5_MAX_INKFRAC = 0.30  # 条带逐行有墨率上限;30 张实测 0.066~0.114,混进竖线后 0.766(1019)
                        # /0.946(1042)。比值闸对"左右两界同向漂移"是盲的(1042 比值仅 1.08),
                        # 这条量的是"条带里有没有多出来的那条竖线"


def _band_y(rec, xl, xr):
    """行折线在时代带 [xl,xr] 内的代表高度;与带不重叠返回 None。

    口径取"行线与带的重叠区间中点"而不是表心中点:短行(如 1030 第7行只到 x=763)
    到不了表心,row_y 会把端点值当该处高度,两行因此被算成贴在一起——那是量尺错,
    不是行序错(1030/1042 实测各 1 例假违规)。完全不与带重叠的行没有带内高度可比,
    返回 None 不参与行序判定。
    """
    p = np.asarray(rec["poly"], float)
    lo, hi = max(float(p[:, 0].min()), xl), min(float(p[:, 0].max()), xr)
    if hi - lo < 1.0:
        return None
    return row_y(rec, (lo + hi) / 2.0)


def preflight_checks(hm, rd, ink_y=None):
    """PF1列界覆盖 / PF2时代界行西延接触 / PF3带内行序(纯函数,不读盘);PF4需原图由 preflight() 补填。

    hm=表头映射 json、rd=行判定 json。PF1 的 y 范围取"时代列自身墨迹范围"ink_y=(y0,y1);
    不传则退回整张数据区(纯函数测试用)。分母必须是列自己的墨迹范围:时代列在表底横线
    处自然终止(1017 墨迹止于 9261,数据区到 9863),按数据区量覆盖率会把"本无列的地方"
    算成缺口(1017 0.9325/1020 0.9695 即此,实测该处原图为空白)。
    PF2 量的是行判定账本 n_era_full/n_era_partial——rowspan 语义下普通行本无带内横线
    (extend_era_rows:普通行拉到框边=造线,违反约束2),只有时代界行西延须全接触左框。
    """
    if "sep_pts" not in hm:
        # 旧版表头映射(如 1019)无折线,列结构定稿只有直线近似——用之即造直线,违反约束4
        return {"PF1_列界覆盖率": 0.0, "PF2_时代界行接触率": 0.0, "PF2_未接触数": 0,
                "PF3_行序违规": [], "PF4_顶部墨占比": 0.0, "ok": False,
                "原因": "旧版表头映射无sep_pts折线,需先升级该图列定稿"}
    k0 = hm["keep"][0]
    n_sep = len(hm["sep_pts"])
    if not (0 <= k0["left_sep"] < n_sep) or not (0 <= k0["right_sep"] < n_sep):
        # 1032 扫描左缘被裁,整列地质时代不在图上(keep[0] 已是"深度",left_sep=-1)。
        # 注意:Python 的 -1 会静默回绕到 sep_pts 最后一条(右外框),不能直接索引。
        return {"PF1_列界覆盖率": 0.0, "PF2_时代界行接触率": 0.0, "PF2_未接触数": 0,
                "PF3_行序违规": [], "PF4_顶部墨占比": 0.0, "PF5_带宽比": None,
                "ok": False, "不适用": True,
                "原因": "该图无地质时代列(扫描左缘裁切),时代列整字裁剪不适用"}
    sp_l = hm["sep_pts"][k0["left_sep"]]
    sp_r = hm["sep_pts"][k0["right_sep"]]
    midx = sum(rd["table_x"]) / 2.0
    ys_rows = [row_y(r, midx) for r in rd["rows"]]
    y0, y1 = min(ys_rows), max(ys_rows)
    if ink_y is not None:
        y0, y1 = max(y0, float(ink_y[0])), min(y1, float(ink_y[1]))
    span = y1 - y0

    def _cov(sp):
        lo, hi = min(sp["ys"]), max(sp["ys"])
        return max(0.0, min(hi, y1) - max(lo, y0)) / span if span > 0 else 0.0

    pf1 = min(_cov(sp_l), _cov(sp_r))

    n_full = int(rd.get("n_era_full") or 0)
    n_part = int(rd.get("n_era_partial") or 0)
    n_era = n_full + n_part
    pf2 = n_full / n_era if n_era else 0.0

    xr = float(np.interp((y0 + y1) / 2.0, sp_r["ys"], sp_r["xs"]))
    xl = float(np.interp((y0 + y1) / 2.0, sp_l["ys"], sp_l["xs"]))

    # PF5 带宽稳定:真时代列是印刷竖线,带宽整表几乎恒定。右界跳到相邻列时带宽翻倍,
    # 整条带子会圈进煤层标志层号列(1019 实测 y≈4377 处 x 346→409,带宽 62→125→158px)。
    w = []
    for y in np.arange(y0, y1, 5.0):
        w.append(float(np.interp(y, sp_r["ys"], sp_r["xs"]))
                 - float(np.interp(y, sp_l["ys"], sp_l["xs"])))
    w = np.asarray(w, float) if len(w) else np.zeros(1)   # 区间退化时取单点,比值为 1
    w10, w90 = (float(np.percentile(w, 10)), float(np.percentile(w, 90))) if len(w) else (0.0, 0.0)
    pf5 = (w90 / w10) if w10 > 0 else float("inf")

    viol, prev = [], None
    for r in rd["rows"]:
        yb = _band_y(r, xl, xr)
        if yb is None:
            continue                      # 与时代带不重叠的行没有带内高度可比
        if prev is not None and yb - prev < PF3_MIN_GAP:
            viol.append({"y": round(yb, 1), "间距": round(yb - prev, 1)})
        prev = yb

    out = {
        "PF1_列界覆盖率": round(pf1, 4),
        "PF2_时代界行接触率": round(pf2, 4),
        "PF2_未接触数": n_part,
        "PF3_行序违规": viol,
        "PF4_顶部墨占比": None,
        "PF5_带宽比": round(pf5, 3) if np.isfinite(pf5) else 999.0,
        "PF5_带宽中位": round(float(np.median(w)), 1),
        "PF5_逐行有墨率": None,
        "ok": bool(pf1 >= PF1_MIN_COV and n_era > 0 and pf2 >= PF2_MIN_CONTACT
                   and not viol and pf5 <= PF5_MAX_WRATIO),
    }
    if not out["ok"] and pf5 > PF5_MAX_WRATIO:
        out["原因"] = (f"时代列带宽不稳(p90/p10={pf5:.2f}>"
                      f"{PF5_MAX_WRATIO}):列界折线中途跳到相邻列,该图须先修列定稿")
    return out


def _band_ink_frac(band):
    """条带"逐行有墨率":墨点数 >2 的行占比。真时代列只在有字处有墨(30 张 0.066~0.114),
    条带里混进满高竖线(装饰轨/邻列)时接近 1.0。纯函数,PF5 的补充闸。"""
    if band is None or band.size == 0:
        return 0.0
    return float((band.sum(axis=1) > 2).mean())


def preflight(stem):
    """读盘包装:表头映射+行判定(行滤到表头底界下,同 build_cells)+PF4 顶部墨。"""
    import cv2
    from src.core import paths
    hm, rd = _load_inputs(stem)
    x_mid = sum(rd["table_x"]) / 2.0
    rd["rows"] = [r for r in rd["rows"] if row_y(r, x_mid) >= hm["band"][1]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    if "sep_pts" in hm and gray is not None:
        hm = _extend_era_bounds(hm, gray, float(max(row_y(r, x_mid) for r in rd["rows"])))
    rep = preflight_checks(hm, rd, ink_y=_era_ink_span(hm, gray) if gray is not None else None)
    if not rep["ok"] and "原因" in rep:
        return rep                        # 旧版映射无 sep_pts:结构性拒裁,不算 PF4
    sp_l = hm["sep_pts"][hm["keep"][0]["left_sep"]]
    sp_r = hm["sep_pts"][hm["keep"][0]["right_sep"]]
    if gray is not None:
        band, _, _ = era_strip(gray, sp_l, sp_r, rd["rows"])
        top = band[:120]
        rep["PF4_顶部墨占比"] = round(float(top.mean()) if top.size else 0.0, 4)
        rep["PF4_warn"] = rep["PF4_顶部墨占比"] > PF4_WARN_INK
        # PF5 补充闸:条带里混进满高竖线时逐行都有墨(1019 0.766 / 1042 0.946),
        # 真时代列只在有字处有墨(其余 28 张 0.066~0.114)。此时整字裁剪必然产出 0 个字块。
        fr = _band_ink_frac(band)
        rep["PF5_逐行有墨率"] = round(fr, 4)
        if fr > PF5_MAX_INKFRAC:
            rep["ok"] = False
            rep["原因"] = (f"时代列条带内混入满高竖线(逐行有墨率 {fr:.3f}>"
                          f"{PF5_MAX_INKFRAC}):列界把装饰轨/邻列圈进了条带,该图须先修列定稿")
    return rep


def _load_inputs(stem):
    import json
    from src.core import paths
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                        encoding="utf-8"))
    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                        encoding="utf-8"))
    return hm, rd


ERA_INK_PAD = 12      # 条带左右各让出的像素(避开两侧列线自身的墨)
ERA_INK_MIN_FRAC = 0.85  # 一行墨占比超过此值 = 横穿条带的表格线,不是文字墨


ERA_EXT_TOL = 25.0    # 外延逐 y 搜索半径(px):半带宽 38~136 的 1/5~2/3,不越到邻列
ERA_EXT_GAPMAX = 40   # 连续无墨多少行后停止外延(断口实测 p50=7px;>40px 是真断口,交人看)


def _thin_runs(row, wmax=5):
    """一行内的细暗色行程中心(候选竖线位置)。与 header_assign._thin_runs 同口径。"""
    out, s = [], None
    for i, v in enumerate(row):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s <= wmax:
                out.append((s + i - 1) / 2.0)
            s = None
    if s is not None and len(row) - s <= wmax:
        out.append((s + len(row) - 1) / 2.0)
    return np.asarray(out, float)


def extend_sep_by_ink(gray, sp, y_stop=None):
    """沿原图墨迹把列界折线外延到墨迹末端;返回 (xs, ys) 升序,未延长则原样返回。

    为什么需要:1023/1025/1028 的列界折线在表中下部断掉(覆盖率 0.95/0.76/0.84),
    但原图那条竖线一直在——逐 y 追踪实测命中 485/487、3910/3954、2647/2650,偏移中位
    **0.0px**。断的是折线记录,不是原图的线。
    约束2 允许的"墨迹验证外延":落点全是原图实测的细行程中心(宽 ≤5px 的暗色游程),
    不创造原图不存在的线、不分箱重采样。找不到墨就立刻停,绝不外推。
    """
    ys = [float(v) for v in sp["ys"]]
    xs = [float(v) for v in sp["xs"]]
    if not ys:
        return np.asarray(xs, float), np.asarray(ys, float)
    y_to = int(y_stop if y_stop is not None else ys[-1])
    if y_to <= ys[-1]:
        return np.asarray(xs, float), np.asarray(ys, float)
    dark = gray < 160
    H = gray.shape[0]
    x = xs[-1]
    miss = 0
    for y in range(int(ys[-1]) + 1, min(y_to, H - 1) + 1):
        rr = _thin_runs(dark[y])
        if len(rr) == 0:
            miss += 1
        else:
            k = int(np.abs(rr - x).argmin())
            if abs(rr[k] - x) <= ERA_EXT_TOL:
                x = float(rr[k])
                ys.append(float(y))
                xs.append(x)
                miss = 0
                continue
            miss += 1
        if miss > ERA_EXT_GAPMAX:
            break
    return np.asarray(xs, float), np.asarray(ys, float)


def _extend_era_bounds(hm, gray, y_stop):
    """时代列左右两条界按原图墨迹外延到表底;返回 hm 的副本(不改盘上文件)。

    只动 keep[0](地质时代)那一格的左右界:它们是"这一列"的边界,断了下游整字裁剪
    就没有条带可用。落点全部来自 extend_sep_by_ink 的实测细行程中心。
    """
    k0 = hm["keep"][0]
    sep = [dict(s) for s in hm["sep_pts"]]
    changed = False
    for key in ("left_sep", "right_sep"):
        i = k0[key]
        if not (0 <= i < len(sep)):
            continue
        xs, ys = extend_sep_by_ink(gray, sep[i], y_stop)
        if len(ys) > len(sep[i]["ys"]):
            sep[i] = {"kind": sep[i].get("kind"), "index": sep[i].get("index"),
                      "side": sep[i].get("side"),
                      "xs": [float(v) for v in xs], "ys": [float(v) for v in ys]}
            changed = True
    if not changed:
        return hm
    out = dict(hm)
    out["sep_pts"] = sep
    return out


def _era_ink_span(hm, gray):
    """时代列"文字墨"的 y 范围 (y0, y1);认不出返回 None。

    PF1 的分母必须是**这一列自己的墨迹范围**,不是整张数据区:时代列在表底横线处自然
    终止(1017 墨迹止于 9261 而数据区到 9863、1020 止于 18269 而数据区到 18810),按数据区
    量覆盖率会把"原图本无列"的空白算成缺口,把合格的列判成断尾(实测 1017=0.9325、
    1020=0.9695,两处裁片均为空白)。
    口径:条带内每行暗像素数 >0 且占带宽 ≤ERA_INK_MIN_FRAC(排除横穿条带的表格线,
    1016/1033/1037 底部那 1~3 行墨占比≈1.00 即此),取首末行。
    """
    try:
        sp_l = hm["sep_pts"][hm["keep"][0]["left_sep"]]
        sp_r = hm["sep_pts"][hm["keep"][0]["right_sep"]]
    except (KeyError, IndexError):
        return None
    if gray is None:
        return None
    y0 = int(max(sp_l["ys"][0], sp_r["ys"][0]))
    y1 = int(min(sp_l["ys"][-1], sp_r["ys"][-1]))
    if y1 - y0 < 2:
        return None
    rows = []
    H, W = gray.shape
    for y in range(max(0, y0), min(y1, H - 1)):
        a = int(np.interp(y, sp_l["ys"], sp_l["xs"])) + ERA_INK_PAD
        b = int(np.interp(y, sp_r["ys"], sp_r["xs"])) - ERA_INK_PAD
        if b - a < 8:
            continue
        c = int((gray[y, a:b] < 150).sum())
        if c > 0 and c / (b - a) <= ERA_INK_MIN_FRAC:
            rows.append(y)
    return (rows[0], rows[-1]) if rows else None


def _char_crop(gray, left, right, y0, y1):
    """单字块回原图裁剪:_crop_cell 逐像素折线掩膜,行界=块外 ±6px 水平折线,列界=sep 折线。"""
    lys, lxs = np.asarray(left["ys"], float), np.asarray(left["xs"], float)
    rys, rxs = np.asarray(right["ys"], float), np.asarray(right["xs"], float)
    xa = float(min(np.interp(y0, lys, lxs), np.interp(y0, rys, rxs)))
    xb = float(max(np.interp(y1, lys, lxs), np.interp(y1, rys, rxs)))
    top = {"poly": [[xa, y0 - 6], [xb, y0 - 6]]}
    bot = {"poly": [[xa, y1 + 6], [xb, y1 + 6]]}
    return _crop_cell(gray, top, bot,
                      lambda y: np.interp(y, lys, lxs),
                      lambda y: np.interp(y, rys, rxs),
                      xa, xb, y0, y1, pad=3, margin=40)


def strip_header_label(bands, label):
    """首名带剔除表头残字:标签后缀(如"时代"/"代",锚定 keep[0].name)+ 前置非 CJK 噪声
    (1016 实测扁平字二遍后多收表头区噪声块 OCR 读作"H")。剥空则整带剔除。
    返回 (bands, 剥去串|None)。
    """
    if not bands or not label:
        return bands, None
    name = bands[0]["name"]
    cut = ""
    while name:
        suf = next((label[-k:] for k in range(len(label), 0, -1)
                    if name.startswith(label[-k:])), "")
        if suf:
            cut += suf
            name = name[len(suf):]
        elif not _is_cjk(name[0]):
            cut += name[0]
            name = name[1:]
        else:
            break
    if not cut:
        return bands, None
    b0 = dict(bands[0])
    if name:
        b0["name"] = name
        b0["判定"], b0["原因"] = parse_era_name(name)
        return [b0] + bands[1:], cut
    return bands[1:], cut                  # 首带全是表头残字


def extract_from_arrays(gray, left, right, rows, band_top=0, ocr_fn=None,
                        header_label=None):
    """era_strip → char_boxes → 逐块回原图裁剪 OCR → split_bands → 表头残字剔除 → 文法。

    band_top=条带顶钳制(表头底界;PF4 实测 sep 起点在表头带内,不钳则检出表头字)。
    纯函数不落盘;ocr_fn 注入(crop灰图→文本),None 则跳过 OCR。
    """
    band, ys, _ = era_strip(gray, left, right, rows)
    keep = ys >= band_top
    band, ys = band[keep], ys[keep]
    chars = []
    for gi, (a, b) in enumerate(char_boxes(band, ys)):
        text = ""
        if ocr_fn is not None:
            crop = _char_crop(gray, left, right, int(a), int(b))
            if crop is not None:
                text = ocr_fn(crop)
        entry = {"y0": int(a), "y1": int(b), "ocr": text}
        if not text and b - a < MIN_CHAR_H and gi > 0:
            # 扁平单杠字形 OCR 常返回空;h∈[FLAT_MIN_H,MIN_CHAR_H)+已过墨宽滤=横杠"一"
            # (1026 实测"二至一段"的单杠;位置/形状双证据,Agnes 独立复读同判)。
            # 全局首字位不推定——那是表头区残杠(1022/1040 实测)。
            entry["ocr"] = "一"
            entry["推定"] = "扁平单杠字形"
        chars.append(entry)
    bands = [{"name": n, "y0": int(a), "y1": int(b),
              "判定": v, "原因": why}
             for n, a, b in split_bands([(c["ocr"], c["y0"], c["y1"]) for c in chars])
             for v, why in (parse_era_name(n),)]
    bands, cut = strip_header_label(bands, header_label)
    return {"strip_y0": int(ys[0]), "strip_y1": int(ys[-1]),
            "chars": chars, "bands": bands, "preflight": None,
            "header_strip": cut or "",
            "params": {"line_band_pad": LINE_BAND_PAD, "line_half_w": 2,
                       "merge_gap": MERGE_GAP, "min_char_h": MIN_CHAR_H,
                       "max_char_h": MAX_CHAR_H}}


def _default_ocr():
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1)  # 默认满核线程在多进程池里互踩,实测慢 12 倍

    def fn(crop):
        res, _ = ocr(crop)
        return " ".join(r[1] for r in (res or [])).strip()
    return fn


def _montage(gray, left, right, out, path):
    """判读用条带拼图:剔线后墨面 + 红框字块 + 蓝框名带。不进门禁。"""
    import cv2
    y0, y1 = out["strip_y0"], out["strip_y1"] + 1
    _, gb, x0i = strip_band(gray, y0, y1, (left["ys"], left["xs"]),
                            (right["ys"], right["xs"]), inset=3)
    viz = cv2.cvtColor(gb, cv2.COLOR_GRAY2BGR)
    w = viz.shape[1]
    for c in out["chars"]:
        cv2.rectangle(viz, (0, c["y0"] - y0), (w - 1, c["y1"] - y0), (0, 0, 255), 2)
    for b in out["bands"]:
        cv2.rectangle(viz, (2, b["y0"] - y0), (w - 3, b["y1"] - y0), (255, 0, 0), 1)
    cv2.imwrite(str(path), viz)


def extract(stem, ocr_fn=None):
    """读盘组装:preflight FAIL 拒裁 → extract_from_arrays → 裁片PNG/montage/JSON 落 ERA_CHAR_DIR。"""
    import json
    import cv2
    from src.core import paths
    rep = preflight(stem)
    if not rep["ok"]:
        return None, rep
    hm, rd = _load_inputs(stem)
    x_mid = sum(rd["table_x"]) / 2.0
    rows = [r for r in rd["rows"] if row_y(r, x_mid) >= hm["band"][1]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    if gray is not None:
        # 与 preflight() 同口径:列界按墨迹外延后再取条带,否则预检通过而裁剪用旧折线
        hm = _extend_era_bounds(hm, gray, float(max(row_y(r, x_mid) for r in rows)))
    sp_l = hm["sep_pts"][hm["keep"][0]["left_sep"]]
    sp_r = hm["sep_pts"][hm["keep"][0]["right_sep"]]
    out = extract_from_arrays(gray, sp_l, sp_r, rows, band_top=int(hm["band"][1]),
                              ocr_fn=ocr_fn or _default_ocr(),
                              header_label=hm["keep"][0]["name"])
    out["preflight"] = rep
    d = paths.ERA_CHAR_DIR / stem
    d.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(out["chars"]):
        crop = _char_crop(gray, sp_l, sp_r, c["y0"], c["y1"])
        if crop is not None:
            cv2.imwrite(str(d / f"字_{i:02d}_y{c['y0']}.png"), crop)
    _montage(gray, sp_l, sp_r, out, d / "montage.png")
    (d / "era_chars.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, rep


def main(argv):
    import csv
    from src.core import paths
    if argv and argv[0] == "--preflight":
        out_csv = paths.TMP_DIR / "时代列前置体检_20261010.csv"
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        rows_out, bad = [], []
        for num in argv[1:]:
            stem = _stem(num)
            rep = preflight(stem)
            v = rep["PF3_行序违规"]
            rows_out.append({
                "图号": stem,
                "PF1_列界覆盖率": rep["PF1_列界覆盖率"],
                "PF2_时代界行接触率": rep["PF2_时代界行接触率"],
                "PF2_未接触数": rep["PF2_未接触数"],
                "PF3_行序违规数": len(v),
                "PF3_首例": v[0] if v else "",
                "PF4_顶部墨占比": rep["PF4_顶部墨占比"],
                "ok": rep["ok"],
                "备注": "" if rep["ok"] else "PF1/PF2/PF3 有 FAIL",
            })
            print(stem, {k: rep[k] for k in
                         ("PF1_列界覆盖率", "PF2_时代界行接触率", "PF3_行序违规", "PF4_顶部墨占比", "ok")})
            if not rep["ok"]:
                bad.append(stem)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            w.writeheader()
            w.writerows(rows_out)
        print(f"报告: {out_csv}")
        if bad:
            print(f"FAIL: {bad} —— 上游问题,不进入整字裁剪实跑")
            return 1
        return 0
    bad = []
    for num in argv or []:
        stem = _stem(num)
        out, rep = extract(stem)
        if out is None:
            print(stem, "preflight FAIL 拒裁", rep["PF1_列界覆盖率"], rep["PF2_时代界行接触率"])
            bad.append(stem)
            continue
        print(stem, f"字块 {len(out['chars'])} 名带 {[b['name'] or '∅' for b in out['bands']]}"
                    f" 判定 {[b['判定'] for b in out['bands']]}")
    return 1 if bad else 0


def _stem(num):
    return num if num.startswith("钻孔柱状图") else f"钻孔柱状图{num}"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))