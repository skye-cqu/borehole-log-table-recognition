# -*- coding: utf-8 -*-
"""阶段6i：列带内行线检测（试点 1015/1035/1017，用户 2026-09-06 批准先看效果）。

目标：逐列带检测行分隔线折线（行线可能倾斜/弯曲——用户明确纠正，不得假设水平），
为逐格拆分/裁剪/结构还原提供像素坐标。检测在拉直图上进行（v 与矫正系/清洗系完全
相同），叠加图与验收图画在清洗图上（2026-09-07 方案 A，柱状/水文列已删）；
u_clean = u_straight − strips[].u_off_clean（恒等平移），回原图走既有坐标链。

方法（调研报告 runs/table_reconstruct/调研_表格结构还原方案.md 方案甲）：
  1. 列带划分：保留区 [west_edge, sem7] ∪ [sem8, sem9] 内相邻控制线目标
     （拉直映射.json targets）围成列带；<MIN_STRIP_W 的窄带为双线伪带剔除。
  2. 候选生成（测量不是拟合）：逐行测最长连续墨游程，≥run_abs 的"实心行"
     相邻（≤3px）聚类成种子，种子须 ≥2 个实心行——行线必有长贯通游程，
     文字行只有短笔画（实测文字横笔画 40~60px < run_abs=80；1017 缓弯行线
     单行切片仅 ~15% 贯通，"单行高占比"式投影在原理上漏线，故不用）。
  3. 分块去倾：CHUNK 宽分块，逐列取候选中心 ±CHUNK_WIN 内最近暗游程中心，
     块内中位数 → 趋势线 y0(x)；无墨块线性内插并标记 unsupported。
  4. DP 贴墨精化：y0(x)±DP_WIN 窗内逐列动态规划，
     代价 = C_INK×空白度 + C_SLOPE×|步长|；断口按空白代价直穿，
     锯齿由斜率代价抑制（去倾后窗口小，曲率项省略）。支持掩膜落账不掩盖。
  5. 落账：支持段 ≥MIN_SPAN 输出为行线 span 折线；支持率/骑线率/rejected
     候选全部落账。某带某行无行线 = rowspan 证据，不补造。
  6. 表头/框线排除（2026-09-07）：表头印刷字的横笔画在窄带内会被误判为行线
     （1015 实证）。表头底 = 最上面的"跨 ≥55% 列带的全宽行线"簇（容差 25px
     容倾斜），其以上 28px 内不出账（表头结构归 表头映射/第一行标注）；
     紧贴搜索带上/下缘 ±6px 的是框线，剔除（框归 闭合外框 资产）。

参数依据：runs/table_reconstruct/行线参数实测.json —— 长规则段倾角 ≤0.7°；
背景灰度 221~227，墨核 75~129；1015 岩性行线存在淡段（172~196）→ 软阈 190。

输出：{stem}_行线试点.json、{stem}_行线叠加图.png（试点，无预览 JPG）。"""
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

TR_DIR = paths.RUNS_DIR / 'table_reconstruct'

# ---- 参数（依据 行线参数实测.json 与试点调试，改动须先补实测） ----
INK_THR_SOFT = 190   # 软墨阈：淡规则线（实测低至 172）也入掩膜；纸底 221~227 不入
MIN_STRIP_W = 25.0   # 列带最小宽：最小线距 37px 的一半以下视为双线伪带
STRIP_INSET = 3      # 带内缘缩进，避免列线笔画混入投影
RUN_ABS_MAX = 80.0   # 贯通游程长度上限（px）：文字横笔画实测 40~60px
RUN_ABS_MIN = 30.0   # 贯通游程长度下限（窄带按 0.6×带宽 收缩）
SEED_GAP = 3         # 相邻实心行的聚类间距（px）
SEED_MIN_SOLID = 2   # 种子最少实心行数（规则线 2~6 行；孤立粗笔画为 1~3 行）
CHUNK = 60           # 去倾分块宽
CHUNK_WIN = 40       # 分块找墨半窗（≥实测带内漂移 16px + 弯曲余量）
CHUNK_MIN_INK = 0.3  # 分块判"有墨"的列占比下限
DP_WIN = 12          # DP 精化半窗（去倾后残余 ±12px）
DP_DELTA = 3         # DP 逐列最大 y 步长
C_INK, C_SLOPE = 1.0, 0.8    # DP 代价权重（空白度标定见 _blank）
MIN_SPAN = 40        # 支持段最短长度（px）
MIN_ROW_SEP = 10.0   # 同带两条行线的最小 v 间距（重复检出合并）
PARAMS_NOTE = ('软墨阈190（淡线实测172~196）；候选=实心行（最长连续游程≥max(30,min(80,0.6×带宽))）'
               '聚类≥2行，文字横笔画40~60px被排除；1017缓弯行线单行切片仅~15%贯通，'
               '单行高占比式投影在原理上漏线故弃用；DP权重首版经验值，试点后复核')


# ---------------------------------------------------------------- 基础工具

def col_run_centers(dark2d):
    """逐列暗游程中心。dark2d: (H,W) bool → (cols, ys, lengths)（列内自上而下对齐）。"""
    pad = np.zeros((1, dark2d.shape[1]), bool)
    starts = dark2d & ~np.vstack([pad, dark2d[:-1]])
    ends = dark2d & ~np.vstack([dark2d[1:], pad])
    sc, sr = np.nonzero(starts.T)
    ec, er = np.nonzero(ends.T)
    keep = sc == ec
    return sc[keep], (sr[keep] + er[keep]) / 2.0, (er[keep] - sr[keep] + 1)


def nearest_per_col(cols, ys, query, win):
    """每列取 |ys−query|≤win 的最近游程中心。返回 (cols, dy)，dy 为带符号偏移。"""
    m = np.abs(ys - query) <= win
    c, y = cols[m], ys[m]
    if len(c) == 0:
        return np.empty(0, int), np.empty(0)
    d = np.abs(y - query)
    order = np.lexsort((d, c))
    c, dy = c[order], (y - query)[order]
    first = np.unique(c, return_index=True)[1]
    return c[first], dy[first]


def row_longest_run(row):
    """一行内最长连续墨游程长度（允许 ≤2px 空隙视为连续）。"""
    idx = np.where(row)[0]
    if idx.size == 0:
        return 0
    parts = np.split(idx, np.where(np.diff(idx) > 2)[0] + 1)
    return int(max(r[-1] - r[0] + 1 for r in parts))


# ---------------------------------------------------------------- 列带划分

def build_strips(stem):
    """保留区列带：边界全部来自已落账数据（targets/清洗映射），不新造。"""
    mu = json.load(open(TR_DIR / f'{stem}_拉直映射.json', encoding='utf-8'))
    mc = json.load(open(TR_DIR / f'{stem}_清洗映射.json', encoding='utf-8'))
    mr = json.load(open(TR_DIR / f'{stem}_矫正映射.json', encoding='utf-8'))
    targets = {k: float(v) for k, v in mu['targets'].items()}
    sl = float(mc['west_edge_u_straight'])
    x7, x8 = [float(v) for v in mc['removed_bands_straight'][0]]
    x9 = float(mc['separators_straight']['sem9']['u_straight'])
    tname = {round(t, 1): nm for nm, t in targets.items()}

    def bname(u):
        return tname.get(round(float(u), 1), f'edge@{round(float(u), 1)}')

    def piece(lo, hi, lo_nm, hi_nm, off):
        bs = [lo] + sorted(t for t in targets.values() if lo + 0.5 < t < hi - 0.5) + [hi]
        out = []
        for a, b in zip(bs, bs[1:]):
            if b - a < MIN_STRIP_W:
                continue  # 双线伪带（两条检出线本身仍是相邻带的边界）
            out.append({'west': float(a), 'east': float(b), 'u_off_clean': float(off),
                        'west_name': lo_nm if abs(a - lo) < 1 else bname(a),
                        'east_name': hi_nm if abs(b - hi) < 1 else bname(b)})
        return out

    # u_clean = u_straight − u_off_clean（西片 −sl；东片 −sl−(sem8−sem7)，恒等平移）
    strips = piece(sl, x7, 'west_edge(真左边界)', 'sem7(真厚|柱状)', sl) \
        + piece(x8, x9, 'sem8(柱状|岩性→新缝)', 'sem9(岩性|水文→东界)', sl + (x8 - x7))
    v_top = float(np.median([p[1] for p in mr['lines_rect']['sides']['top']]))
    v_bot = float(np.median([p[1] for p in mr['lines_rect']['sides']['bottom']]))
    return strips, v_top, v_bot, targets


# ---------------------------------------------------------------- 候选生成

def projection_candidates(band_soft, strip_w):
    """带内"实心行"聚类 → 行线候选种子。band_soft: (H,W) bool（灰度<INK_THR_SOFT）。

    逐行测最长连续墨游程；≥run_abs 的实心行相邻（≤SEED_GAP）聚类，种子须
    ≥SEED_MIN_SOLID 个实心行（行线必有 2~6 个贯通行，文字笔画只有孤立行）。
    返回 [{'v','thick','n_solid','run_peak','cov_any'}]，v 为带内相对行号。"""
    H, W = band_soft.shape
    run_abs = max(RUN_ABS_MIN, min(RUN_ABS_MAX, 0.6 * strip_w))
    solid_rows, solid_runs = [], []
    for r in range(H):
        L = row_longest_run(band_soft[r])
        if L >= run_abs:
            solid_rows.append(r)
            solid_runs.append(L)
    cands = []
    if not solid_rows:
        return cands
    groups = np.split(np.arange(len(solid_rows)),
                      np.where(np.diff(solid_rows) > SEED_GAP)[0] + 1)
    for g in groups:
        if len(g) < SEED_MIN_SOLID:
            continue  # 孤立粗笔画（单行贯通）非行线
        rows_arr = [solid_rows[i] for i in g]
        pk = solid_rows[max(g, key=lambda i: solid_runs[i])]
        seg = band_soft[max(0, pk - 2):min(H, pk + 3)]
        cands.append({'v': float(np.median(rows_arr)), 'thick': int(rows_arr[-1] - rows_arr[0] + 1),
                      'n_solid': len(g), 'run_peak': int(max(solid_runs[i] for i in g)),
                      'run_abs': round(run_abs, 1),
                      'cov_any': round(float(seg.any(axis=0).mean()), 3)})
    return cands


# ---------------------------------------------------------------- 去倾 + DP

def detrend(band_soft, yc, xs):
    """分块去倾：返回 (y0(xs), supported(xs))。xs 为带内相对列号数组。"""
    n = len(xs)
    v_lo = max(0, int(yc - CHUNK_WIN - 8))
    v_hi = min(band_soft.shape[0], int(yc + CHUNK_WIN + 9))
    sl_cols, sl_ys, _ = col_run_centers(band_soft[v_lo:v_hi])
    hit_cols, hit_dy = nearest_per_col(sl_cols, sl_ys + v_lo, yc, CHUNK_WIN)
    hit_map = dict(zip(hit_cols.tolist(), hit_dy.tolist()))
    sup_c, y0_c = [], []
    for xc in range(xs[0] + CHUNK // 2, xs[-1], CHUNK // 2):
        dys = np.array([hit_map.get(int(x), np.nan) for x in range(xc - CHUNK // 2,
                                                                  min(xc + CHUNK // 2, xs[-1]))])
        fin = np.isfinite(dys)
        if fin.mean() >= CHUNK_MIN_INK:
            sup_c.append(xc)
            y0_c.append(yc + float(np.median(dys[fin])))
    if not sup_c:
        return np.full(n, float(yc)), np.zeros(n, bool)
    y0 = np.interp(xs.astype(float), np.array(sup_c, float), np.array(y0_c))
    sup = np.zeros(n, bool)
    for xc in sup_c:
        sup[(xs >= xc - CHUNK // 2) & (xs < xc + CHUNK // 2)] = True
    return y0, sup


def dp_refine(gray_band, y0, xs):
    """y0±DP_WIN 窗内逐列 DP 贴墨（步长罚抑制锯齿）。返回 path_y（带内相对 v）。"""
    n_off = 2 * DP_WIN + 1
    offs = np.arange(-DP_WIN, DP_WIN + 1)
    INF = 1e18
    n = len(xs)
    dp = np.empty((n, n_off))
    par = np.zeros((n, n_off), int)
    col = xs.astype(int)

    def blank_vec(i):
        rows = np.clip(np.round(y0[i] + offs).astype(int), 0, gray_band.shape[0] - 1)
        g = gray_band[rows, col[i]].astype(float)
        return np.clip((g - 60.0) / 160.0, 0.0, 1.0) * C_INK

    dp[0] = blank_vec(0)
    for i in range(1, n):
        slope = y0[i] - y0[i - 1]
        best = np.full(n_off, INF)
        bstep = np.zeros(n_off, int)
        for s in range(-DP_DELTA, DP_DELTA + 1):
            dy = slope + s
            if abs(dy) > DP_DELTA:
                continue
            val = dp[i - 1] + C_SLOPE * abs(dy)
            shifted = np.full(n_off, INF)
            if s >= 0:
                shifted[s:] = val[:n_off - s]
            else:
                shifted[:s] = val[-s:]
            better = shifted < best
            bstep[better] = s
            best[better] = shifted[better]
        dp[i] = best + blank_vec(i)
        par[i] = bstep
    k = int(np.argmin(dp[-1]))
    if not np.isfinite(dp[-1, k]):
        return y0.copy()
    path = np.empty(n)
    for i in range(n - 1, -1, -1):
        path[i] = y0[i] + offs[k]
        if i > 0:
            k -= int(par[i, k])
    return path


def support_mask(band_soft, path, xs, win=3):
    """路径 ±win 行内有墨的列掩膜。"""
    rows = np.clip(np.round(path).astype(int), 0, band_soft.shape[0] - 1)
    sup = np.zeros(len(xs), bool)
    for d in range(-win, win + 1):
        r = np.clip(rows + d, 0, band_soft.shape[0] - 1)
        sup |= band_soft[r, xs]
    return sup


def extract_spans(xs, sup, path, band_soft):
    """支持掩膜 → span 列表（连续支持段 ≥MIN_SPAN）。pts 的 v 为带内相对行号。"""
    spans = []
    idx = np.where(sup)[0]
    if idx.size == 0:
        return spans
    for grp in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
        if grp[-1] - grp[0] + 1 < MIN_SPAN:
            continue
        i0, i1 = int(grp[0]), int(grp[-1])
        cols = xs[i0:i1 + 1]
        step = max(1, (i1 - i0) // 300)
        sel = list(range(0, i1 - i0 + 1, step))
        if sel[-1] != i1 - i0:
            sel.append(i1 - i0)
        pr = np.clip(np.round(path[i0:i1 + 1]).astype(int), 0, band_soft.shape[0] - 1)
        spans.append({'u0': float(cols[0]), 'u1': float(cols[-1]),
                      'pts': [[int(cols[i]), round(float(path[i0 + i]), 1)] for i in sel],
                      'ink_frac': round(float(band_soft[pr, cols].mean()), 3)})
    return spans


# ---------------------------------------------------------------- 逐带串接

def trace_strip_lines(band_soft, gray_band, cands, n_cols, x0, v_off):
    """候选 → 去倾 → DP → 支持段。内部一律用带内相对坐标（列 0..n_cols−1、
    行相对带顶），出账时 u+x0、v+v_off 换回拉直系绝对坐标。"""
    xs = np.arange(n_cols)
    lines, rejected = [], []
    for c in cands:
        y0, sup0 = detrend(band_soft, c['v'], xs)
        path = dp_refine(gray_band, y0, xs)
        sup = support_mask(band_soft, path, xs)
        spans = extract_spans(xs, sup, path, band_soft)
        tot = sum(s['u1'] - s['u0'] for s in spans)
        dark_at = band_soft[np.clip(np.round(path).astype(int), 0, band_soft.shape[0] - 1), xs]
        if tot < MIN_SPAN:
            rejected.append({'v': round(c['v'] + v_off, 1),
                             'reason': f'support {round(tot)}px < {MIN_SPAN}',
                             'n_solid': c['n_solid'], 'run_peak': c['run_peak'],
                             'thick': c['thick']})
            continue
        lines.append({'v_center': round(c['v'] + v_off, 1), 'thick': c['thick'],
                      'n_solid': c['n_solid'], 'run_peak': c['run_peak'],
                      'cov_any': c['cov_any'],
                      'detrend_supported_frac': round(float(sup0.mean()), 3),
                      'support_frac': round(float(sup.mean()), 3),
                      'edge_ride_frac': round(float((sup & ~dark_at).mean()), 3),
                      'spans': [{'u0': s['u0'] + x0, 'u1': s['u1'] + x0, 'ink_frac': s['ink_frac'],
                                 'pts': [[p[0] + x0, round(p[1] + v_off, 1)] for p in s['pts']]}
                                for s in spans],
                      'n_spans': len(spans)})
    # 同带重复检出合并（v 相距 <MIN_ROW_SEP）：留支持率高者，落账被并者
    lines.sort(key=lambda r: r['v_center'])
    kept = []
    for r in lines:
        dup = next((q for q in kept if abs(q['v_center'] - r['v_center']) < MIN_ROW_SEP), None)
        if dup is None:
            kept.append(r)
        elif r['support_frac'] > dup['support_frac']:
            r['merged_dup'] = [dup['v_center']]
            kept[kept.index(dup)] = r
        else:
            dup.setdefault('merged_dup', []).append(r['v_center'])
    return kept, rejected


# ---------------------------------------------------------------- 主流程

def process(stem):
    strips, v_top, v_bot, targets = build_strips(stem)
    # 画布 = 清洗图（2026-09-07，方案 A）：已删柱状/水文两列、西缘为真左边界；
    # 行线坐标仍以拉直系落账（v 三系相同），u_clean = u_straight − u_off_clean
    img = cv2.imread(str(TR_DIR / f'{stem}_表格清洗.png'), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(cv2.imread(str(TR_DIR / f'{stem}_表格拉直.png'),
                                   cv2.IMREAD_COLOR), cv2.COLOR_BGR2GRAY)
    imgh, imgw = gray.shape
    v0, v1 = int(v_top) + 2, int(v_bot) - 2
    result = {'image': stem,
              'coord_frame': 'straight（拉直系；v 与矫正/清洗系相同）；'
                             'u_clean = u_straight − strips[].u_off_clean（恒等平移）',
              'params': {k: globals()[k] for k in
                         ('INK_THR_SOFT', 'MIN_STRIP_W', 'STRIP_INSET',
                          'RUN_ABS_MIN', 'RUN_ABS_MAX', 'SEED_GAP', 'SEED_MIN_SOLID',
                          'CHUNK', 'CHUNK_WIN', 'DP_WIN', 'DP_DELTA', 'C_INK', 'C_SLOPE',
                          'MIN_SPAN', 'MIN_ROW_SEP')},
              'params_note': PARAMS_NOTE,
              'frames': {'v_top': round(v_top, 1), 'v_bot': round(v_bot, 1)},
              'targets': {k: round(v, 1) for k, v in targets.items()},
              'strips': []}
    overlay = img.copy()
    cw = overlay.shape[1]
    cv2.line(overlay, (0, int(v_top)), (cw - 1, int(v_top)), (255, 255, 0), 2, cv2.LINE_AA)
    cv2.line(overlay, (0, int(v_bot)), (cw - 1, int(v_bot)), (255, 255, 0), 2, cv2.LINE_AA)
    total_lines = total_rej = 0
    # 第一遍：逐带检测（出账/绘图在表头过滤之后统一做）
    traced = []
    for st in strips:
        off = st['u_off_clean']
        x0i = int(np.ceil(st['west'])) + STRIP_INSET
        x1i = int(np.floor(st['east'])) - STRIP_INSET
        if x1i - x0i < 40:
            result['strips'].append({**st, 'skipped': 'too_narrow_after_inset'})
            traced.append(None)
            continue
        band_soft = gray[v0:v1, x0i:x1i] < INK_THR_SOFT
        gray_band = gray[v0:v1, x0i:x1i]
        cands = projection_candidates(band_soft, strip_w=x1i - x0i)
        lines, rejected = trace_strip_lines(band_soft, gray_band, cands,
                                            n_cols=x1i - x0i, x0=x0i, v_off=v0)
        traced.append((st, off, lines, rejected, len(cands)))

    # 表头区排除（2026-09-07）：表头印刷字的横笔画在窄带内会被误判为行线
    # （1015 实证）。表头底规则线 = 最上面的"跨 ≥55% 列带的全宽行线"簇
    # （容差 25px 容纳整体倾斜）；其以上不出账（表头结构归 表头映射/第一行标注）。
    full = []  # (v_center, strip_idx) 全宽行线（框线除外）
    for si, t in enumerate(traced):
        if t is None:
            continue
        st, _, lines, _, _ = t
        w_eff = st['east'] - st['west'] - 2 * STRIP_INSET
        for ln in lines:
            if v0 + 6 <= ln['v_center'] <= v1 - 6:  # 紧贴带缘的是上/下框线，非行线
                if sum(sp['u1'] - sp['u0'] for sp in ln['spans']) >= 0.8 * w_eff:
                    full.append((ln['v_center'], si))
    v_hdr = None
    if full:
        for v, _ in sorted(full):
            grp = [vv for vv, _ in full if abs(vv - v) <= 25]
            sis = {si for vv, si in full if abs(vv - v) <= 25}
            if len(sis) >= max(3, int(0.55 * len(traced))):
                v_hdr = float(np.median(grp))
                break
    for t in traced:
        if t is None:
            continue
        st, off, lines, rejected, n_cands = t
        kept = []
        for ln in lines:
            if ln['v_center'] < v0 + 6 or ln['v_center'] > v1 - 6:
                rejected.append({'v': ln['v_center'], 'reason': 'frame_line(上下框线归闭合外框)',
                                 'thick': ln['thick']})
                continue
            if v_hdr is not None and ln['v_center'] < v_hdr - 28:
                rejected.append({'v': ln['v_center'], 'reason': 'header_band(表头印刷字笔画)',
                                 'n_solid': ln['n_solid'], 'run_peak': ln['run_peak'],
                                 'thick': ln['thick']})
                continue
            kept.append(ln)
        lines = kept
        for ln in lines:
            col = (0, 200, 0) if ln['support_frac'] >= 0.8 else (0, 160, 255)
            for sp in ln['spans']:
                pts = np.asarray([[p[0] - off, p[1]] for p in sp['pts']],
                                 np.int32).reshape(-1, 1, 2)
                cv2.polylines(overlay, [pts], False, col, 2, cv2.LINE_AA)
        for b in (st['west'], st['east']):
            cv2.line(overlay, (int(round(b - off)), v0 - 60), (int(round(b - off)), v1 + 60),
                     (255, 80, 0), 1, cv2.LINE_AA)
        result['strips'].append({**st, 'n_candidates': n_cands,
                                 'n_lines': len(lines), 'n_rejected': len(rejected),
                                 'header_bottom_v': None if v_hdr is None else round(v_hdr, 1),
                                 'lines': lines, 'rejected': rejected})
        total_lines += len(lines)
        total_rej += len(rejected)
    out_png = TR_DIR / f'{stem}_行线叠加图.png'
    cv2.imwrite(str(out_png), overlay, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    json.dump(result, open(TR_DIR / f'{stem}_行线试点.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return {'stem': stem, 'strips': len(strips), 'lines': total_lines,
            'rejected': total_rej, 'overlay': out_png.name}


def main():
    only = sys.argv[1:] or ('1015', '1035', '1017')
    for n in only:
        r = process('钻孔柱状图' + n)
        print(r['stem'], 'strips=%d lines=%d rejected=%d -> %s'
              % (r['strips'], r['lines'], r['rejected'], r['overlay']), flush=True)


if __name__ == '__main__':
    main()
