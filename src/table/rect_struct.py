# -*- coding: utf-8 -*-
"""阶段6j：方案一——矫正系表格结构还原（2026-09-07 用户批准；09-08 修正数据源；
09-09 修复三缺陷，产物改用 _R2 新文件名，不动既有产物）。

用户指示：**沿用前面阶段的数据源，不得重新寻找/拟合未识别的线条**。

数据源（全部为前阶段已定稿落账，坐标已映射至矫正系）：
  - 列线 = `{stem}_分割线.json`（6a 列结构定稿 + 6a2 断口补全，经 6f 映射为
    矫正映射.json lines_rect.columns）——经用户视觉验收的识别结果；
  - 左右边界 = `{stem}_闭合外框.json`（6e）→ lines_rect.sides；
  - sem7/8/9 = **矫正系** 6g 规则链（SANITY 窗内就近检出线 → 柱状带宽互检 →
    墨迹吸附；规则与常量复用 clean_columns.py）。不再读取被否决拉直路线的
    清洗映射 separators_straight（拉直系与矫正系同线可差 17~61px，曾致 4 张图
    拒真线后造出恒定 x 竖线）。

09-09 三缺陷修复：
  1. 画布（方案F，用户指示"去掉无用信息、真删"）：清洗画布=矫正图逐行去除删除列，
     边界**逐行跟随真实墨迹**（`_track_rule_edge`：col7/col8/col9 规则线墨缘，
     行间步进受限、墨断保持）——三条规则线本体保留为边界，严丝合缝、零内容损失；
     hstack/半透明遮罩/常数切口全部废弃；
  2. 画线只画落账线且**分段绘制**：侧线/辅助线经逐点真伪校验（verify_side）+
     偏离滤点（dev_filter，DEV=6px 实测推导）后按 intervals 分段，天窗真开窗，
     不再直线桥接；删除 ±6px 容差复制线；上下框改画 6d/6e 落账折线（原全宽
     横线越表角、贯穿删除列）；sem 缺线不再造恒定 x 竖线——6g 定案切口经同名
     对账取落账线（不加跨系 px 门槛），aux 切口一律标 requires_human_review，
     只画经逐点校验的真实墨线段（红色，账目见 sems）；带宽互检=全量旁证
     （失配只报警转人工不改写）；校验零命中的整线开天窗（沿用 1032 模式）；
  3. 贴线爬行锯齿：dev_filter 剔除偏离局部中位 >6px 的跳轨/爬行点（实测
     真线点 p90≤3px、污染尾≥6px），只删不造。

09-10 外框连通修复（R4，用户批准）：外框四线（side_left/side_right/frame_top/
frame_bottom 的 6e 折线原文）**整线绘制保证封闭连贯**，按逐点校验分色——贴墨
验证段=实线（现色：侧线蓝/上下框青），未验证/悬浮/出界段=黄色虚线+"6e 未验证段"
文字标注+图例卡片（画在东侧删除白带内，不遮保留区内容）。绘制层不再只画校验
存活碎段（曾致 1035 西缘 35% 覆盖 8 段、1015 东缘 61% 缺口 6255px 的碎裂外框）；
上下框折线改按原文存储顺序（西→东）绘制（旧代码按 y 排序会打乱水平线点序）。
JSON 账目不变（side_verify 真伪仍逐点记录）；删除白带、三条删除边界、列线/aux
的保留区绘制裁剪（clip_to_kept）一概不动。

输出：{stem}_清洗画布_R4.png、{stem}_矫正结构叠加_R4.png、{stem}_结构_R4.json、
{stem}_样格R2_k.png。逐格组装（第2期）所需的全部边界/行线数据在 _R4.json 落账。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.clean_columns import (BAND_TOL, BAND_W, MARGIN, SANITY, T,  # noqa: E402
                                     snap_to_ink as _cc_snap)
import src.table.row_line_detect as RLD  # noqa: E402

TR_DIR = paths.RUNS_DIR / 'table_reconstruct'
HDR_TOL = 28.0       # 表头底簇容差（同 6i）
DEV_WIN = 8          # 偏离滤点：局部中位取 ±8 个相邻命中点
DEV_PX = 6.0         # 偏离阈值：实测真线点 p90≤3px、污染尾≥6px（2026-09-09，6 条侧线）

# ---- R4 外框整线绘制（2026-09-10 用户批准）：外框四线整线绘制保证封闭连贯，
# 按逐点校验分色。JSON 账目不变（真伪仍逐点记录）；删除白带与三条删除边界不动。
COL_SIDE = (255, 0, 0)          # 侧线验证段（现色：蓝）
COL_FRAME_TB = (255, 255, 0)    # 上下框验证段（现色：青）
COL_UNVERIFIED = (0, 255, 255)  # 未验证/悬浮/出界段（黄虚线）
DASH_ON = 26.0                  # 虚线短划长 px
DASH_OFF = 16.0                 # 虚线净空 px
DASH_W = 3                      # 虚线线宽（实线保持现粗细 2）
LABEL_MIN_PX = 260.0            # 未验证段折线弧长达到该值才加文字标注
LABEL_TEXT = '6e 未验证段'
CN_FONTS = ('C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/msyh.ttc')


def verify_hline(gray, ys, xs, win=10, rule_max_w=12, ink_thr=180):
    """水平线逐点真伪校验（verify_side 的 90° 旋转，用于上下框折线）：
    命中=该点竖向 ±win 内存在含点自身的竖向窄游程（宽 ≤rule_max_w，即框线厚度）。
    悬浮伪点（6e 底框 V 尖刺/角部钩尾离墨）竖向无墨 → miss。返回 (hit, 命中率)。"""
    h, w = gray.shape
    hits = np.zeros(len(ys), bool)
    for i, (x, y) in enumerate(zip(np.round(xs).astype(int), np.round(ys).astype(int))):
        if not (0 <= x < w and 0 <= y < h):
            continue
        seg = gray[max(0, y - win):min(h, y + win + 1), x]
        dark = np.where(seg < ink_thr)[0]
        if dark.size == 0:
            continue
        runs = np.split(dark, np.where(np.diff(dark) > 3)[0] + 1)
        base = y - max(0, y - win)
        r = next((r for r in runs if r[0] <= base <= r[-1]),
                 min(runs, key=lambda r: min(abs(r[0] - base), abs(r[-1] - base))))
        dist = 0 if r[0] <= base <= r[-1] else min(abs(r[0] - base), abs(r[-1] - base))
        if dist <= 3 and (r[-1] - r[0] + 1) <= rule_max_w:
            hits[i] = True
    return hits, round(float(hits.mean()), 3)


def verify_side(gray, ys, xs, win=25, rule_max_w=20, ink_thr=180):
    """侧折线逐点真伪校验（方案一选项1，只删不造）：每点经 H_rs 回原图，
    命中=所在横向墨游程是窄游程（宽 ≤rule_max_w，即印刷细规则线）。
    落在空白（无墨）或粗黑带/大片墨区（游程过宽）= 不命中——幻影补线多画在
    外侧粗带上，纯"有墨"判据区分不了细线与粗带，必须用游程宽度。
    返回 (hit 布尔数组, 命中率)。"""
    h, w = gray.shape
    hits = np.zeros(len(ys), bool)
    for i, (x, y) in enumerate(zip(np.round(xs).astype(int), np.round(ys).astype(int))):
        if not (0 <= x < w and 0 <= y < h):
            continue
        seg = gray[y, max(0, x - win):min(w, x + win + 1)]
        dark = np.where(seg < ink_thr)[0]
        if dark.size == 0:
            continue
        runs = np.split(dark, np.where(np.diff(dark) > 3)[0] + 1)
        base = x - max(0, x - win)
        r = next((r for r in runs if r[0] <= base <= r[-1]),
                 min(runs, key=lambda r: min(abs(r[0] - base), abs(r[-1] - base))))
        dist = 0 if r[0] <= base <= r[-1] else min(abs(r[0] - base), abs(r[-1] - base))
        if dist <= 4 and (r[-1] - r[0] + 1) <= rule_max_w:
            hits[i] = True
    return hits, round(float(hits.mean()), 3)


def dev_filter(ys, xs, win=DEV_WIN, dev=DEV_PX):
    """偏离滤点（只删不造）：命中点偏离"±win 个相邻点的局部中位"超过 dev 判为
    跳轨/爬行锯齿（verify_side 的盲区：贴真线的抖动点与粗带边缘点同样是窄游程）。
    实测依据（2026-09-09，1015/1017/1035×2 侧）：真线点偏离 p90≤3px，
    污染点（跳轨/V 凸/装饰框混轨）≥6px，取分界 6px。返回 keep 布尔数组。"""
    xs = np.asarray(xs, float)
    keep = np.ones(len(xs), bool)
    for i in range(len(xs)):
        lo, hi = max(0, i - win), min(len(xs), i + win + 1)
        if abs(xs[i] - np.median(xs[lo:hi])) > dev:
            keep[i] = False
    return keep


def side_intervals(ys, hits, max_chain_gap=300):
    """命中点链化：相邻命中点 y 间隔 ≤max_chain_gap 归为同段。
    返回 (intervals[(y0,y1)...], gaps[(g0,g1)...])——gaps 为天窗（含首尾截断）。"""
    idx = np.where(hits)[0]
    if idx.size == 0:
        return [], [(0, int(ys[-1]) if len(ys) else 0)]
    iv, gaps = [], []
    groups = np.split(idx, np.where(np.diff(ys[idx]) > max_chain_gap)[0] + 1)
    for g in groups:
        iv.append((int(ys[g[0]]), int(ys[g[-1]])))
    for (a1, b1), (a2, b2) in zip(iv, iv[1:]):
        gaps.append((b1, a2))
    if iv[0][0] > int(ys[0]):
        gaps.insert(0, (int(ys[0]), iv[0][0]))
    if iv[-1][1] < int(ys[-1]):
        gaps.append((iv[-1][1], int(ys[-1])))
    return iv, gaps


def segments_from_gaps(ys, xs, intervals):
    """按 intervals 把保留点切成绘制段（天窗处真开窗，绝不跨段直连）。"""
    ys = np.asarray(ys, float)
    xs = np.asarray(xs, float)
    segs = []
    for a, b in intervals:
        m = (ys >= a) & (ys <= b)
        if m.any():
            segs.append(np.stack([xs[m], ys[m]], 1))
    return segs


def dev_filter_h(ys, win=DEV_WIN, dev=DEV_PX):
    """水平框线的偏离滤点：偏离量取 y 向（尖刺=纵向跳点）。"""
    vals = np.asarray(ys, float)
    keep = np.ones(len(vals), bool)
    for i in range(len(vals)):
        lo, hi = max(0, i - win), min(len(vals), i + win + 1)
        if abs(vals[i] - np.median(vals[lo:hi])) > dev:
            keep[i] = False
    return keep


def verify_polyline(gray, b, orient='v'):
    """侧线/辅助线/上下框统一管线（只删不造）：逐点真伪校验 + 偏离滤点 + 分段落账。
    orient='v' 竖线（侧线/列/aux，横向窄游程判据）；'h' 水平框线（竖向窄游程
    verify_hline，偏离滤点取 y 向）。原地更新 b：只保留存活点并存 'segs'
    （绘制用，天窗不桥接）。返回 side_verify 账目 dict；零命中时折线清空。"""
    ys, xs = b['ys'], b['xs']
    hits, rate = (verify_hline(gray, ys, xs) if orient == 'h'
                  else verify_side(gray, ys, xs))
    n_verify_drop = int((~hits).sum())
    dev_drop = 0
    if hits.any():
        keep_dev = (dev_filter_h(ys[hits]) if orient == 'h'
                    else dev_filter(ys[hits], xs[hits]))
        idx = np.where(hits)[0]
        dev_drop = int((~keep_dev).sum())
        hits[idx[~keep_dev]] = False
    if not hits.any():
        b['ys'] = b['ys'][:0]
        b['xs'] = b['xs'][:0]
        b['segs'] = []
        return {'hit_rate': rate, 'n_dropped': n_verify_drop, 'n_dev_dropped': dev_drop,
                'intervals': [], 'open_gaps': [[0, int(gray.shape[0])]]}
    ky, kx = ys[hits], xs[hits]
    iv, gaps = side_intervals(ky, hits[hits], max_chain_gap=300)
    b['ys'], b['xs'] = ky, kx
    b['segs'] = segments_from_gaps(ky, kx, iv)
    return {'hit_rate': rate, 'n_dropped': n_verify_drop, 'n_dev_dropped': dev_drop,
            'intervals': [[int(a), int(c)] for a, c in iv],
            'open_gaps': [[int(g0), int(g1)] for g0, g1 in gaps]}


def strip_band(gray, v0, v1, wpoly, epoly, inset=RLD.STRIP_INSET):
    """逐行曲线带提取：带内 = [west(v)+inset, east(v)−inset]。
    返回 (band_soft, gray_band, x0i)；带外 band=False、gray=255。"""
    ys_w, xs_w = wpoly
    ys_e, xs_e = epoly
    vs = np.arange(v0, v1)
    L = np.interp(vs, ys_w, xs_w) + inset
    R = np.interp(vs, ys_e, xs_e) - inset
    x0i = max(0, int(np.floor(L.min())) - 1)
    x1i = int(np.ceil(R.max())) + 1
    band = gray[v0:v1, x0i:x1i] < RLD.INK_THR_SOFT
    gray_band = gray[v0:v1, x0i:x1i].copy()
    cols = np.arange(x0i, x1i)
    mask = (cols[None, :] >= L[:, None]) & (cols[None, :] <= R[:, None])
    band &= mask
    gray_band[~mask] = 255
    return band, gray_band, x0i


def remove_deleted_bands(rect, curves):
    """方案F：清洗画布=矫正图逐行白化删除列，边界=落账曲线本身（严丝合缝）。
    每行白化 [col7曲线(v), col8曲线(v)) 柱状带 与 [col9曲线(v), 右缘] 水文列。
    注：曾试验逐行墨迹跟随边界，真实数据上跟踪器会游移到贴线文字上
    （1035 实测数字区 5.5 万+岩性区 10.6 万像素账外删除），已废弃——
    落账曲线虽局部偏离印刷真线 ≤20px（6a/6f 固有精度），但只影响空白边距
    观感、不伤文字（judge 多轮核验），第 2 期逐格多边形裁剪同样不受影响。"""
    canvas = rect.copy()
    h, w = canvas.shape[:2]
    vs = np.arange(h, dtype=float)
    c7 = np.interp(vs, *curves[7])
    c8 = np.interp(vs, *curves[8])
    c9 = np.interp(vs, *curves[9])
    cols = np.arange(w)
    mask = ((cols[None, :] >= c7[:, None]) & (cols[None, :] < c8[:, None])) |            (cols[None, :] >= c9[:, None])
    canvas[mask] = 255
    return canvas


def build_boundaries(stem):
    """边界折线（矫正系）= 前阶段落账线原文。列线零重选零遗漏；
    侧线做逐点真伪校验+偏离滤点（只删不造），天窗分段落账不造线。"""
    m = json.load(open(TR_DIR / f'{stem}_矫正映射.json', encoding='utf-8'))
    rect = cv2.imread(str(TR_DIR / f'{stem}_表格矫正.png'), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY)
    imgh = gray.shape[0]

    def add(nm, pts, prov):
        arr = np.asarray(pts, float)
        arr = arr[(arr[:, 1] >= -2) & (arr[:, 1] <= imgh + 2)]
        o = np.argsort(arr[:, 1])
        ys, xs = arr[o, 1], arr[o, 0]
        bnds[nm] = {'ys': ys, 'xs': xs, 'prov': prov,
                    'orig': (ys.copy(), xs.copy()),   # R4 整线绘制用原文（侧线 y 单调，=JSON 账目同序）
                    'median_x': round(float(np.median(xs)), 1)}

    bnds = {}
    for s in ('left', 'right'):
        add(f'side_{s}', m['lines_rect']['sides'][s], '闭合外框(6e)')
    for c in m['lines_rect']['columns']:
        add(f"col{c['index']}", c['pts'], '分割线(6a 定稿+断口补全)')

    side_gaps = {}
    for nm in ('side_left', 'side_right'):
        b = bnds[nm]
        rec = verify_polyline(gray, b)
        if not rec['intervals']:
            b['prov'] += '+真伪校验(零命中:无窄规则线,整线开天窗)'
        else:
            b['prov'] += f"+真伪校验(命中{rec['hit_rate']})+偏离滤点(删{rec['n_dev_dropped']})"
        side_gaps[nm] = rec
    aux = {'side_gaps': side_gaps}
    return bnds, gray, rect, m, aux


def resolve_sems(names, xs, W, snap_fn, hints=None):
    """sem7/8/9 矫正系解析（6g clean_columns 同款规则链，纯函数便于单测）：
    ⓪ hints（6g 定案切口：经拉直映射 targets 同名对账的落账线）直接采用——
       同源同名天然可信，**不做跨系 px 门槛**（合法系差实测 0~61px+ 随位置变化，
       固定门槛必错：1035 col7 两账差 61px 曾被误拒，切口被挪进柱状带）；
    ① SANITY 窗内距模板位置最近的检出线；② 缺失侧按柱状带宽模板推算（6g 规则）；
    ③ 推算位置 ±40px 墨迹吸附（snap_fn(x)->(x,strength)，strength>0 即吸中）；
    ④ 带宽互检 = **全量旁证**：两侧都是⓪①切口而带宽失配 >BAND_TOL 时不改写切口，
       只在两侧落 band_check_warning 转人工复核（2026-09-09 方案A，用户批准）。
    非⓪①得到的为 aux（切口数据，非落账线）。返回 {sid: {...}}。"""
    out, picked = {}, {}
    hints = hints or {}

    def hinted(sid):
        return hints.get(sid) in names

    for sid in (7, 8, 9):
        if hinted(sid):
            n = hints[sid]
            x = float(xs[names.index(n)])
            picked[sid] = x
            out[sid] = {'ref': n, 'cut_x': round(x, 1), 'source': 'detected',
                        'via': '6g 定案切口(经拉直映射同名对账)'}
    for sid in (7, 8, 9):
        if sid in picked:
            continue
        lo, hi = SANITY[sid][0] * W + MARGIN, SANITY[sid][1] * W + MARGIN
        cands = [(n, x) for n, x in zip(names, xs) if lo <= x <= hi]
        if cands:
            t_abs = T[sid] * W + MARGIN
            n, x = min(cands, key=lambda c: abs(c[1] - t_abs))
            picked[sid] = float(x)
            out[sid] = {'ref': n, 'cut_x': round(float(x), 1), 'source': 'detected'}
    # ④ 带宽互检旁证（仅 ⓪① 切口；缺失推算/吸附出的 aux 不参检）
    if 8 in out and 7 in out and out[7]['source'] == 'detected' and out[8]['source'] == 'detected':
        band = picked[8] - picked[7]
        if abs(band - BAND_W * W) > BAND_TOL:
            warn = ('柱状带宽 %.0fpx 与模板 %.0fpx 差 %.0fpx>%.0f → 人工复核（旁证报警，切口不改写）'
                    % (band, BAND_W * W, abs(band - BAND_W * W), BAND_TOL))
            out[7]['band_check_warning'] = warn
            out[8]['band_check_warning'] = warn
    if 8 not in picked:
        if 7 in picked:
            picked[8] = picked[7] + BAND_W * W
        elif 9 in picked:
            picked[8] = picked[9] - (T[9] - T[8]) * W
        out[8] = {'ref': 'aux8', 'cut_x': round(picked[8], 1), 'source': 'template'}
    if 7 not in picked:
        picked[7] = picked[8] - BAND_W * W
        out[7] = {'ref': 'aux7', 'cut_x': round(picked[7], 1), 'source': 'template'}
    if 9 not in picked and 8 in picked:
        picked[9] = picked[8] + (T[9] - T[8]) * W
        out[9] = {'ref': 'aux9', 'cut_x': round(picked[9], 1), 'source': 'template'}
    for sid in (7, 8, 9):
        if out[sid]['source'] != 'detected':
            x_snap, strength = snap_fn(picked[sid])
            if strength > 0:
                picked[sid] = float(x_snap)
                out[sid]['cut_x'] = round(float(x_snap), 1)
                out[sid]['source'] += '+snapped'
            out[sid]['aux'] = True
            out[sid]['requires_human_review'] = True
        else:
            out[sid]['aux'] = False
    return out


def sem_assign(stem, bnds, gray):
    """sem 解析（矫正系）+ aux 折线入账。aux 不画，只作切口/带边界数据；
    aux 折线同样过 真伪校验+偏离滤点，校验存活段作为带的有效区间。

    hints 来源：6g 定案切口（用户验证过"30 张三边界全部落在真实线上"）。
    清洗映射 separators_straight 的 source=='line' 条目，其 u_straight 值即
    拉直映射 targets 中同名落账线的拉直系坐标——**只在拉直系内做同名对账**，
    对上后取该落账线的矫正系折线为边界。**不加跨系 px 门槛**（合法系差实测
    0~61px+ 随位置变化，固定门槛必错——1035 col7 两账差 61px 曾被误拒）。
    source 非 'line' 或无唯一同名 → 走 SANITY/推算/吸附 aux 链，aux 切口一律
    标 requires_human_review（实测无可靠的图形带自动判别，见
    汇报_1035底图与西列线二轮诊断.md 第四节）。"""
    m = json.load(open(TR_DIR / f'{stem}_矫正映射.json', encoding='utf-8'))
    mc = json.load(open(TR_DIR / f'{stem}_清洗映射.json', encoding='utf-8'))
    ms = json.load(open(TR_DIR / f'{stem}_拉直映射.json', encoding='utf-8'))
    W = float(m['rect_size'][0])
    cols = sorted((k for k in bnds if k.startswith('col')),
                  key=lambda k: bnds[k]['median_x'])
    names = cols
    xs = np.array([bnds[k]['median_x'] for k in cols], float)

    targets = ms.get('targets', {})
    hints, hint_log = {}, {}
    for sid in (7, 8, 9):
        e = mc['separators_straight'].get(f'sem{sid}', {})
        if e.get('source') != 'line':
            continue
        u = float(e['u_straight'])
        near = [(nm, abs(float(tv) - u)) for nm, tv in targets.items()
                if abs(float(tv) - u) <= 2.0]
        if len(near) == 1 and near[0][0] in names:
            nm = near[0][0]
            hints[sid] = nm
            hint_log[f'sem{sid}'] = (f'u_straight={u} → targets.{nm} → 落账线{nm}'
                                     f'(矫正系 {bnds[nm]["median_x"]}, 两账差{abs(bnds[nm]["median_x"] - u):.1f}px=合法系差)')
        else:
            hint_log[f'sem{sid}'] = 'source=line 但无唯一同名目标 → SANITY/推算/吸附 aux 链'

    sems = resolve_sems(names, xs, W, snap_fn=lambda x: _cc_snap(gray, x, None), hints=hints)
    if hint_log:
        sems['_hints'] = hint_log

    for sid in (7, 8, 9):
        e = sems[sid]
        if not e['aux']:
            continue
        nm = e['ref']
        x0 = float(e['cut_x'])
        # 密集采样（~10px）：恒定 x 切口只有两端点时 verify_side 无从校验
        ys = np.arange(0.0, float(gray.shape[0]), 10.0)
        bnds[nm] = {'ys': ys,
                    'xs': np.full(len(ys), x0),
                    'prov': f'aux({e["source"]},6g 规则切口)',
                    'median_x': round(x0, 1), 'aux': True}
        rec = verify_polyline(gray, bnds[nm])
        if not rec['intervals']:
            bnds[nm]['prov'] += '+校验零命中(整线开天窗,带不作有效边界)'
        else:
            bnds[nm]['prov'] += (f"+校验(命中{rec['hit_rate']})+偏离滤点(删{rec['n_dev_dropped']})"
                                 '+仅校验存活段作有效边界')
        e['verify'] = rec
    return sems


def poly_pair(bnd):
    return (bnd['ys'], bnd['xs'])


def to_pts(pts):
    """(n,2) 折线点 → cv2.polylines 顶点格式（画布=全幅矫正系，无需换算）。"""
    return np.asarray(pts, np.int32).reshape(-1, 1, 2)


def clip_to_kept(pts, curves):
    """方案D 呈现一致性（红线2"只画保留区内的线"）：绘制点只保留保留区
    [0, c7+2] ∪ [c8-2, c9+3]（边界线自身 ±2~3px 容差不误裁）；跨越删除带的
    折线拆成多段（不在白带上重新连桥）。落账折线本身不裁——JSON 全量出账，
    本函数只用于叠加图绘制。返回 [(n,2) 段, ...]。"""
    p = np.asarray(pts, float)
    if len(p) == 0:
        return []
    ys = p[:, 1]
    c7 = np.interp(ys, *curves[7])
    c8 = np.interp(ys, *curves[8])
    c9 = np.interp(ys, *curves[9])
    x = p[:, 0]
    keep = (x <= c7 + 2) | ((x >= c8 - 2) & (x <= c9 + 0.5))
    idx = np.where(keep)[0]
    segs = []
    for g in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
        if len(g) >= 2:
            segs.append(p[g])
    return segs


# ---- R4 外框整线绘制（只分色，不造线：画的全部是 6e 折线原文的点与连线） ----

def runs_of(mask):
    """布尔数组的连续 True 段 [(i0,i1) 闭区间, ...]。"""
    idx = np.where(np.asarray(mask, bool))[0]
    if idx.size == 0:
        return []
    return [(int(g[0]), int(g[-1]))
            for g in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)]


def frame_status(gray, ys, xs, orient):
    """外框线绘制用逐点真伪：判据与 verify_side/verify_hline/dev_filter 完全同参，
    但在折线**原文存储顺序**上计算（侧线原文即自上而下 y 序，与 JSON 账目同序
    同结果；上下框原文为西→东 x 序）。返回等长 bool 数组（True=贴墨验证存活，
    False=未验证/悬浮/出界）。"""
    ys = np.asarray(ys, float)
    xs = np.asarray(xs, float)
    hits, _ = (verify_hline(gray, ys, xs) if orient == 'h'
               else verify_side(gray, ys, xs))
    status = hits.copy()
    if hits.any():
        idx = np.where(hits)[0]
        keep = (dev_filter_h(ys[hits]) if orient == 'h'
                else dev_filter(ys[hits], xs[hits]))
        status[idx[~keep]] = False
    return status


def dash_segments(pts, on=DASH_ON, off=DASH_OFF, step=2.0):
    """折线按弧长切虚线短划：返回短划点列列表。相邻短划净空≈off，首短划贴合
    折线起点，**末短划到达折线终点**（尾段不足一个周期时补收尾短划——否则虚线
    会在实线段前留出最长 on+off 的裸口，视觉上像断线）。"""
    p = np.asarray(pts, float)
    if len(p) < 2:
        return []
    seg = np.sqrt((np.diff(p, axis=0) ** 2).sum(1))
    total = float(seg.sum())
    if total < 1:
        return []
    s = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(int(np.ceil(total / step)) + 1, 2)
    q = np.linspace(0.0, total, n)
    dense = np.stack([np.interp(q, s, p[:, 0]), np.interp(q, s, p[:, 1])], 1)
    k_on = max(int(round(on / step)), 1)
    period = max(int(round((on + off) / step)), k_on + 1)
    pieces = [dense[st:min(st + k_on + 1, n)] for st in range(0, n - 1, period)]
    st_last = ((n - 2) // period) * period
    en_last = min(st_last + k_on + 1, n)
    if en_last < n:
        pieces.append(dense[max(en_last - 1, n - 1 - k_on):n])
    return pieces


def draw_frame_polyline(overlay, ys, xs, status, solid_color):
    """外框线整线绘制（R4，封闭连贯）：贴墨验证段=现色实线；未验证段=黄色虚线，
    虚线路径两端各外延一个折线点与相邻实线相接——整线无缺口。
    不做保留区裁剪：外框是整表边界，跨删除白带处保持连贯（用户批准）。"""
    pts = np.stack([np.asarray(xs, float), np.asarray(ys, float)], 1)
    status = np.asarray(status, bool)
    n = len(pts)
    for a, b in runs_of(status):
        if b > a:
            cv2.polylines(overlay, [to_pts(pts[a:b + 1])], False,
                          solid_color, 2, cv2.LINE_AA)
    for a, b in runs_of(~status):
        lo, hi = max(a - 1, 0), min(b + 1, n - 1)
        if hi <= lo:
            continue
        for piece in dash_segments(pts[lo:hi + 1]):
            cv2.polylines(overlay, [to_pts(piece)], False,
                          COL_UNVERIFIED, DASH_W, cv2.LINE_AA)


def collect_unverified_labels(ys, xs, status, min_len=LABEL_MIN_PX, merge_gap=150.0):
    """未验证连续段的标注锚点 [(x,y,text), ...]。相邻未验证段之间被 ≤merge_gap
    弧长的验证小岛隔开时合并测长——单点/短验证岛不画实线（视觉上仍是连续黄虚），
    逐段测长会漏标（1015 底框西段实测：0~42px 未验证段与 0~79px 单点岛交替
    ≈800px，逐段最长 42px 全部低于阈值）。合并段弧长 ≥min_len 才在段中点加字，
    短碎段交给图例说明，避免满图文字噪音。"""
    pts = np.stack([np.asarray(xs, float), np.asarray(ys, float)], 1)
    groups = []
    for a, b in runs_of(~np.asarray(status, bool)):
        if groups and np.linalg.norm(pts[a] - pts[groups[-1][1]]) <= merge_gap:
            groups[-1][1] = b
        else:
            groups.append([a, b])
    out = []
    for a, b in groups:
        seg = pts[a:b + 1]
        if len(seg) < 2:
            continue
        length = float(np.sqrt((np.diff(seg, axis=0) ** 2).sum(1)).sum())
        if length >= min_len:
            mid = seg[len(seg) // 2]
            out.append((float(mid[0]), float(mid[1]), LABEL_TEXT))
    return out


def _font_path():
    for f in CN_FONTS:
        if Path(f).exists():
            return f
    return None


def _nudge_to_blank(bg_gray, tx, ty, tw, th):
    """标注摆放避让：候选文字框落在画布墨迹上（如底框标注压底行数字，1015 实测）
    时平移到无墨处。做法：对 3 个候选行带逐列算墨迹，取能容下整框的无墨区间中
    离原位置最近的点（网格试探会因 1~2px 容差错过窄空隙）；找不到原样返回。"""
    h, w = bg_gray.shape[:2]
    tw, th = int(tw) + 2, int(th)
    best, best_cost = None, None
    for dy in (0, -(th + 10), th + 10):
        y0 = int(ty) + dy
        y1 = y0 + th
        if y0 < 0 or y1 > h:
            continue
        ink_cols = (bg_gray[y0:y1] < 195).any(0)
        idx = np.where(~ink_cols)[0]
        if idx.size == 0:
            continue
        for g in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1):
            if g[-1] - g[0] + 1 < tw:
                continue
            cx = min(max(tx, int(g[0])), int(g[-1]) - tw + 1)
            cost = abs(cx - tx) + abs(dy) * 0.3
            if best_cost is None or cost < best_cost:
                best, best_cost = (cx, y0), cost
    return best if best else (tx, ty)


def annotate_overlay(overlay, labels, legend=None, font_size=42,
                     label_font_size=36, bg=None):
    """PIL 中文标注层：未验证段文字（黄字黑描边）+ 图例卡片（白底灰框，
    应画在空白区内如东侧删除白带）。无中文字体时静默跳过（分色线条仍可辨）。
    legend={'x0','y0','xlim','entries':[(kind,text)...],'note'}，kind∈
    side/frame/unver。bg=画布（无线条），标注按 bg 避让墨迹（1015 底框标注
    曾压底行数字——字号取 36 使文字框 ≈190px 能放进底行列间空隙）。收尾一次。"""
    fp = _font_path()
    if fp is None or (not labels and not legend):
        return
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    dr = ImageDraw.Draw(im)
    W, H = im.size
    f_main = ImageFont.truetype(fp, font_size)
    f_lab = ImageFont.truetype(fp, label_font_size)
    f_note = ImageFont.truetype(fp, int(font_size * 0.7))
    bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY) if bg is not None else None
    for x, y, text in labels:
        tw = dr.textlength(text, font=f_lab)
        tx, ty = x + 18, y - label_font_size - 12
        if bg_gray is not None:
            tx, ty = _nudge_to_blank(bg_gray, tx, ty, tw, label_font_size + 10)
        tx = min(max(tx, 8), W - tw - 8)
        ty = min(max(ty, 8), H - label_font_size - 8)
        dr.text((tx, ty), text, font=f_lab, fill=(255, 255, 0),
                stroke_width=3, stroke_fill=(0, 0, 0))
    if legend:
        entries = legend['entries']
        note = legend.get('note')
        sw, gap, pad = 90, 16, 18
        lh = int(font_size * 1.35)
        texts = [t for _, t in entries] + ([note] if note else [])
        text_w = max((dr.textlength(t, font=f_main) for _, t in entries), default=0.0)
        if note:
            text_w = max(text_w, dr.textlength(note, font=f_note))
        cw, ch = int(pad + sw + gap + text_w + pad), int(pad * 2 + lh * len(entries)
                                                         + (lh - 10 if note else 0))
        x0 = min(int(legend['x0']), max(0, W - cw))
        y0 = int(legend['y0'])
        dr.rectangle([x0, y0, x0 + cw, y0 + ch], fill=(255, 255, 255),
                     outline=(150, 150, 150), width=3)
        rgb = {'side': (0, 0, 255), 'frame': (0, 255, 255), 'unver': (255, 255, 0)}
        for i, (kind, text) in enumerate(entries):
            cy = y0 + pad + lh * i + lh // 2
            xa, xb = x0 + pad, x0 + pad + sw
            if kind == 'unver':
                for k in range(5):
                    s0 = xa + k * (sw / 5.0)
                    dr.line([s0, cy, min(s0 + sw / 5.0 - 5, xb), cy],
                            fill=rgb[kind], width=4)
            else:
                dr.line([xa, cy, xb, cy], fill=rgb[kind], width=4)
            dr.text((x0 + pad + sw + gap, cy - font_size / 2), text,
                    font=f_main, fill=(0, 0, 0))
        if note:
            dr.text((x0 + pad, y0 + pad + lh * len(entries) + 2), note,
                    font=f_note, fill=(90, 90, 90))
    overlay[:] = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def process(stem):
    bnds, gray, rect, m, aux = build_boundaries(stem)
    sems = sem_assign(stem, bnds, gray)
    v_top = float(np.median([p[1] for p in m['lines_rect']['sides']['top']]))
    v_bot = float(np.median([p[1] for p in m['lines_rect']['sides']['bottom']]))
    v0 = int(v_top) + 2
    v1 = int(min(gray.shape[0] - 4, v_bot + 320))  # 搜索带向下延伸：底框校准证据窗

    # 方案D：删除切口 = 落账曲线本身（逐行置白，无拼缝/shift）
    curves = {}
    for sid in (7, 8, 9):
        b = bnds.get(sems[sid]['ref'])
        if b is not None and len(b['ys']) >= 2:
            curves[sid] = (b['ys'], b['xs'])
        else:   # 校验零命中的 aux：以切口常数线兜底（对应条带本就整线开天窗）
            curves[sid] = (np.array([0.0, float(gray.shape[0])]),
                           np.full(2, float(sems[sid]['cut_x'])))
    canvas = remove_deleted_bands(rect, curves)   # 方案F：逐行白化删除列，边界=落账曲线

    order = sorted(bnds, key=lambda k: bnds[k]['median_x'])
    mx = {k: bnds[k]['median_x'] for k in order}
    wset = [k for k in order if mx['side_left'] <= mx[k] <= mx[sems[7]['ref']]]
    eset = [k for k in order if mx[sems[8]['ref']] <= mx[k] <= mx[sems[9]['ref']]]
    strips = []
    for lst, w_nm, e_nm in ((wset, 'side_left', sems[7]['ref']), (eset, sems[8]['ref'], sems[9]['ref'])):
        for a, b in zip(lst, lst[1:]):
            strips.append((a, b))
        if lst and lst[0] != w_nm:
            strips.insert(0, (w_nm, lst[0]))
        if lst and lst[-1] != e_nm:
            strips.append((lst[-1], e_nm))

    result = {'image': stem,
              'coord_frame': 'rect（矫正系；回原图走 H_rect_to_src）',
              'canvas': f'{stem}_清洗画布_R4.png（矫正图逐行去除删除列，边界逐行跟随真实墨迹，严丝合缝）',
              'canvas_rule': {'col7_curve': sems[7]['ref'], 'col8_curve': sems[8]['ref'],
                              'col9_curve': sems[9]['ref'],
                              'rule': '每行白化 [col7规则线东缘(v), col8规则线西缘(v)) 与 [col9规则线东缘(v), W]；边界=行内墨迹跟随'},
              'data_source': '边界=前阶段落账线原文（分割线/闭合外框，经 6f 映射），零重选零拟合；'
                             'sem=矫正系 6g 规则链（不读拉直系）',
              'boundaries': {nm: {'median_x': b['median_x'], 'prov': b['prov'],
                                  'aux': bool(b.get('aux', False)),
                                  'n_pts': int(len(b['ys'])),
                                  'y_span': ([round(float(b['ys'].min())), round(float(b['ys'].max()))]
                                              if len(b['ys']) else None)}
                             for nm, b in bnds.items()},
              'sems': {**{f'sem{sid}': sems[sid] for sid in (7, 8, 9)},
                       **({'_hints': sems['_hints']} if '_hints' in sems else {})},
              'side_verify': aux['side_gaps'],
              'dev_filter': {'win_pts': DEV_WIN, 'dev_px': DEV_PX,
                             'basis': '实测 1015/1017/1035×2 侧命中点偏离局部中位：真线 p90≤3px、污染尾≥6px'},
              'strips': []}

    overlay = canvas.copy()

    traced = []
    for a, b in strips:
        if len(bnds[a]['ys']) < 2 or len(bnds[b]['ys']) < 2:
            result['strips'].append({'west': a, 'east': b, 'skipped': 'boundary_unverified(该边界整线开天窗或零校验)'})
            traced.append(None)
            continue
        w_poly = poly_pair(bnds[a])
        e_poly = poly_pair(bnds[b])
        band, gray_band, x0i = strip_band(gray, v0, v1, w_poly, e_poly)
        vr = np.ones(v1 - v0, bool)
        for iv_nm in (a, b):
            for g0, g1 in aux['side_gaps'].get(iv_nm, {}).get('open_gaps', []):
                vr[max(g0 - v0, 0):max(g1 - v0, 0)] = False
        band &= vr[:, None]
        gray_band[~vr, :] = 255
        w_eff = float(np.median(np.interp(np.arange(v0, v1), e_poly[0], e_poly[1])
                                - np.interp(np.arange(v0, v1), w_poly[0], w_poly[1])
                                - 2 * RLD.STRIP_INSET))
        if w_eff < 40:
            result['strips'].append({'west': a, 'east': b, 'skipped': 'too_narrow'})
            traced.append(None)
            continue
        cands = RLD.projection_candidates(band, strip_w=w_eff)
        lines, rejected = RLD.trace_strip_lines(band, gray_band, cands,
                                                n_cols=band.shape[1], x0=x0i, v_off=v0)
        traced.append((a, b, lines, rejected, len(cands), w_eff))

    full = []
    for si, t in enumerate(traced):
        if t is None:
            continue
        a, b, lines, _, _, w_eff = t
        for ln in lines:
            if v0 + 6 <= ln['v_center'] <= v1 - 6:
                if sum(sp['u1'] - sp['u0'] for sp in ln['spans']) >= 0.8 * w_eff:
                    full.append((ln['v_center'], si))
    v_hdr = None
    if full:
        for v, _ in sorted(full):
            sis = {si for vv, si in full if abs(vv - v) <= 25}
            if len(sis) >= max(3, int(0.55 * len(traced))):
                v_hdr = float(np.median([vv for vv, _ in full if abs(vv - v) <= 25]))
                break
    v_bot_eff = None
    if full:
        v_max = max(v for v, _ in full)
        v_bot_eff = float(np.median([vv for vv, _ in full if abs(vv - v_max) <= 25]))
    v1_rows = int((v_bot_eff if v_bot_eff is not None else v_bot)) - 2

    total = 0
    for si, t in enumerate(traced):
        if t is None:
            continue
        a, b, lines, rejected, n_cands, w_eff = t
        kept = []
        for ln in lines:
            if ln['v_center'] < v0 + 6 or ln['v_center'] > v1_rows + 6:
                rejected.append({'v': ln['v_center'], 'reason': 'frame_line(上下框线归闭合外框)'})
                continue
            if v_hdr is not None and ln['v_center'] < v_hdr - HDR_TOL:
                rejected.append({'v': ln['v_center'], 'reason': 'header_band(表头印刷字笔画)'})
                continue
            if v_hdr is not None and ln['v_center'] <= v_hdr + HDR_TOL:
                ln['kind'] = 'header_bottom(表头底线，随倾斜)'
                continue
            kept.append(ln)
        lines = kept
        for ln in lines:
            if ln.get('kind', '').startswith('header_bottom'):
                for sp in ln['spans']:
                    cv2.polylines(overlay, [to_pts(sp['pts'])], False,
                                  (255, 0, 255), 2, cv2.LINE_AA)
                continue
            col = (0, 200, 0) if ln['support_frac'] >= 0.8 else (0, 160, 255)
            for sp in ln['spans']:
                cv2.polylines(overlay, [to_pts(sp['pts'])], False,
                              col, 2, cv2.LINE_AA)
        result['strips'].append({'west': a, 'east': b, 'n_candidates': n_cands,
                                 'n_lines': len(lines), 'n_rejected': len(rejected),
                                 'lines': lines, 'rejected': rejected})
        total += len(lines)

    # 落账边界绘制（方案D 呈现一致性：只画保留区内的段，跨越删除带处拆段收口；
    # JSON 的 boundaries/side_verify 仍全量出账不裁）。
    # R4 起**侧线不再画校验存活碎段**（曾致外框碎裂），改下方整线绘制；此处仅列线。
    drawn = []
    for nm in set(wset + eset + ['side_left', 'side_right']):
        if nm not in bnds or nm.startswith('side_'):
            continue
        b = bnds[nm]
        drawn.append((nm, np.stack([b['xs'], b['ys']], 1), (255, 0, 0)))
    for sid in (7, 8, 9):
        e = sems[sid]
        nm = e['ref']
        if e['aux'] and nm in bnds and bnds[nm].get('segs'):
            for seg in bnds[nm]['segs']:
                drawn.append((nm, seg, (0, 0, 255)))
    for nm, pts, colr in drawn:
        for seg in clip_to_kept(pts, curves):
            cv2.polylines(overlay, [to_pts(seg)], False, colr, 2, cv2.LINE_AA)
    # 上下框：6d/6e 落账折线逐点校验（只删不造）——仅作 JSON 账目（side_verify）
    # 与行带开窗依据；**R4 起绘制不再走此处碎段**（旧代码还把折线按 y 排序，
    # 会打乱水平线的西→东点序），改下方整线绘制
    frame_verify = {}
    for s in ('top', 'bottom'):
        arr = np.asarray(m['lines_rect']['sides'][s], float)
        o = np.argsort(arr[:, 1])
        b = {'ys': arr[o, 1], 'xs': arr[o, 0], 'prov': f'闭合外框(6e) {s}'}
        rec = verify_polyline(gray, b, orient='h')
        frame_verify['frame_' + s] = rec
        aux['side_gaps']['frame_' + s] = rec
        b['prov'] += (f'+真伪校验(命中{rec["hit_rate"]})+偏离滤点(删{rec["n_dev_dropped"]})'
                      if rec['intervals'] else '+校验零命中(整线开天窗)')

    # ---- R4：外框四线整线绘制（用户批准）——6e 折线原文按存储顺序整线画出保证
    # 封闭连贯，按逐点校验分色：贴墨验证段=实线（现色），未验证/悬浮/出界段=
    # 黄色虚线+文字标注。JSON 账目不变；删除白带与三条删除边界不动。
    frame_labels = []
    frame_top_ymax = 0.0
    for nm, orient, colr in (('side_left', 'v', COL_SIDE), ('side_right', 'v', COL_SIDE),
                             ('frame_top', 'h', COL_FRAME_TB),
                             ('frame_bottom', 'h', COL_FRAME_TB)):
        if nm.startswith('side_'):
            oys, oxs = bnds[nm]['orig']
        else:
            arr = np.asarray(m['lines_rect']['sides'][nm[6:]], float)
            oys, oxs = arr[:, 1], arr[:, 0]
        status = frame_status(gray, oys, oxs, orient)
        draw_frame_polyline(overlay, oys, oxs, status, colr)
        frame_labels += collect_unverified_labels(oys, oxs, status)
        if nm == 'frame_top':
            frame_top_ymax = float(np.max(oys))

    legend_xlim = int(min(np.min(bnds['side_right']['orig'][1]), gray.shape[1])) - 25
    legend = {'x0': int(np.min(curves[9][1])) + 36,
              'y0': int(frame_top_ymax) + 80,
              'xlim': legend_xlim,
              'entries': [('side', '外框侧线·验证段'),
                          ('frame', '上下框·验证段'),
                          ('unver', '6e 未验证段')],
              'note': '黄虚线=悬浮/跳轨/出界点'}
    annotate_overlay(overlay, frame_labels, legend=legend, bg=canvas)

    env_candidates = [float(bnds[k]['ys'].max()) for k in wset + eset if len(bnds[k]['ys'])]
    env = max(env_candidates) if env_candidates else v_bot
    shift_cal = None if v_bot_eff is None else round(v_bot_eff - v_bot, 1)
    divergence = {'frame_v_bot': round(v_bot, 1),
                  'calibrated_bottom_v': None if v_bot_eff is None else round(v_bot_eff, 1),
                  'shift_px': shift_cal,
                  'action': ('frame_kept(框线即墨线)' if abs(shift_cal) <= 25 else 'calibrated(底框校准)')
                  if shift_cal is not None else 'no_rule_found',
                  'col_endpoint_envelope': round(env, 1)}

    eset_strips = [t for t in traced if t is not None and t[0] == sems[8]['ref']] or \
                  [t for t in traced if t is not None and t[0] in eset]
    samples = []
    if eset_strips:
        a, b, lines, _, _, _ = eset_strips[0]
        lines_sorted = sorted(lines, key=lambda l: l['v_center'])
        pairs = list(zip(lines_sorted, lines_sorted[1:]))
        w_poly, e_poly = poly_pair(bnds[a]), poly_pair(bnds[b])

        def cell_ink(pair):
            rt, rb = pair
            vt = min(sp['pts'][0][1] for sp in rt['spans'])
            vb = max(sp['pts'][-1][1] for sp in rb['spans'])
            vs = np.arange(int(vt) + 2, int(vb) - 1)
            if len(vs) < 10:
                return -1.0
            L = np.interp(vs, w_poly[0], w_poly[1]) + 3
            R = np.interp(vs, e_poly[0], e_poly[1]) - 3
            ink = 0
            for v2, l2, r2 in zip(vs, L, R):
                seg = gray[int(v2), int(l2):int(r2)]
                ink += int((seg < 150).sum())
            return ink / max(1, len(vs))

        pairs.sort(key=cell_ink, reverse=True)
        for k, (rt, rb) in enumerate(pairs[:2]):
            tile = cell_crop(rect, w_poly, e_poly,
                             min(sp['pts'][0][1] for sp in rt['spans']),
                             max(sp['pts'][-1][1] for sp in rb['spans']))
            out = TR_DIR / f'{stem}_样格R2_{k + 1}.png'
            cv2.imwrite(str(out), tile, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            samples.append(out.name)

    cv2.imwrite(str(TR_DIR / f'{stem}_清洗画布_R4.png'), canvas, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    out_png = TR_DIR / f'{stem}_矫正结构叠加_R4.png'
    cv2.imwrite(str(out_png), overlay, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    result['header_bottom_v'] = None if v_hdr is None else round(v_hdr, 1)
    result['bottom_check'] = divergence
    result['sample_cells'] = samples
    json.dump(result, open(TR_DIR / f'{stem}_结构_R4.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return {'stem': stem, 'strips': len(traced), 'lines': total,
            'header_bottom_v': result['header_bottom_v'], 'bottom': divergence,
            'overlay': out_png.name}


def cell_crop(rect, wpoly, epoly, v_top, v_bot, pad=2):
    """多边形掩膜样格裁剪（零重采样）：带外置白。"""
    y0, y1 = int(v_top) - pad, int(v_bot) + pad
    vs = np.arange(y0, y1)
    L = np.interp(vs, wpoly[0], wpoly[1]) + 3
    R = np.interp(vs, epoly[0], epoly[1]) - 3
    x0 = max(0, int(L.min()) - pad)
    x1 = int(R.max()) + pad
    tile = rect[y0:y1, x0:x1].copy()
    cols = np.arange(x0, x1)
    m = (cols[None, :] >= (L - x0)[:, None]) & (cols[None, :] <= (R - x0)[:, None])
    tile[~m] = 255
    return tile


def main():
    only = sys.argv[1:] or ('1015', '1035', '1017')
    for n in only:
        r = process('钻孔柱状图' + n)
        print(r['stem'], 'strips=%d lines=%d v_hdr=%s bottom=%s -> %s'
              % (r['strips'], r['lines'], r['header_bottom_v'], r['bottom'], r['overlay']),
              flush=True)


if __name__ == '__main__':
    main()
