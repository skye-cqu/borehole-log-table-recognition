# -*- coding: utf-8 -*-
"""阶段6c：分割线断口补全（用户 2026-09-02 指示：对原始不完整线条补全，保证连续性）。

对象 = 每图分割线集合：左右边界(frames side=left/right) + 全部列线(columns)。
补全规则 = 用户断口补齐三点要求，缺一不可：
  ① 斜率像：相邻碎片与竖直的夹角差 ≤ SLOPE_TOL；
  ② 延伸对齐：弦延伸到对面碎片端点的横向偏差 ≤ ALIGN_TOL；
  ③ 中间缺口能用同斜率线补上：缺口 ≤ GAP_MAX，补全段 = 两迎面端点间的直线段。
边界守住两条：只补碎片之间的内部缺口（不外延端点）；补全段逐条落账、
叠加图上单独配色（青色），与原始片段可区分。

输出 {stem}_分割线.json（每线连续折线 + fills + unfilled + ends 报告）
与 {stem}_连续性叠加图.png（红=原始、青=补全、绿=左右边界、压暗=内容线）。"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

SLOPE_TOL = 3.0    # deg，与竖直的夹角差（备用）
ALIGN_TOL = 40.0   # px，迎面端点偏离线走廊的容差
KINK_TOL = 45.0    # px/300px，缺口上下段趋势方向差（斜率像）
GAP_MAX = 700.0    # px，可补缺口上限（1024 实证 615px 为真缺口）
GAP_MIN = 8.0      # px，小于此不视为缺口


def chord_angle(p0, p1):
    dy = p1[1] - p0[1]
    dx = p1[0] - p0[0]
    return math.degrees(math.atan2(abs(dx), abs(dy))) if abs(dy) > 1e-6 else 90.0


def x_at(p0, p1, y):
    y0, y1 = p0[1], p1[1]
    if abs(y1 - y0) < 1e-6:
        return p0[0]
    t = min(1.0, max(0.0, (y - y0) / (y1 - y0)))
    return p0[0] + t * (p1[0] - p0[0])


def line_pieces(seg, ids):
    """碎片 → 按 y 排序的折线段列表 [(pts, y0, y1, x@y0, x@y1)]，pts 为单条折线。"""
    out = []
    for sid in ids:
        if sid not in seg:
            continue
        p = np.asarray(seg[sid]['points'], float)
        if len(p) < 2:
            continue
        p = p[np.argsort(p[:, 1])]
        out.append((p, p[0][1], p[-1][1], p[0][0], p[-1][0]))
    out.sort(key=lambda t: t[1])
    return out


def bridge_line(seg, ids):
    """线级趋势桥接：先建该线自己的 x(y) 走廊（400px 带中位），缺口按三点要求判定。
    端部串线碎片（中位 x 偏离全碎片中位 >60px）先裁除并记录。
    返回 (chain_pts, fills, unfilled, trims)。"""
    pieces = line_pieces(seg, ids)
    fills, unfilled, trims = [], [], []
    if not pieces:
        return np.zeros((0, 2)), fills, unfilled, trims
    core = float(np.median([p[3] for p in pieces]))
    while len(pieces) > 1 and abs(pieces[0][3] - core) > 90:
        t = pieces.pop(0)
        trims.append({'y': [round(t[1]), round(t[2])], 'x': round(t[3])})
    while len(pieces) > 1 and abs(pieces[-1][3] - core) > 90:
        t = pieces.pop()
        trims.append({'y': [round(t[1]), round(t[2])], 'x': round(t[3])})
    allp = np.vstack([p for p, *_ in pieces])
    y_lo, y_hi = float(allp[:, 1].min()), float(allp[:, 1].max())
    band = 400.0
    centers, meds = [], []
    y = y_lo
    while y < y_hi:
        sel = allp[(allp[:, 1] >= y) & (allp[:, 1] < y + band)]
        if len(sel) >= 8:
            centers.append(y + band / 2)
            meds.append(float(np.median(sel[:, 0])))
        y += band
    if len(centers) < 2:                     # 线太短，无需补
        return np.vstack([p for p, *_ in pieces]), fills, unfilled, trims

    def trend(t):
        return float(np.interp(t, centers, meds))

    chain = [pieces[0][0]]
    cur = pieces[0]
    for nxt in pieces[1:]:
        y_a, y_b = cur[2], nxt[1]
        gap = y_b - y_a
        if gap <= GAP_MIN:                   # 重叠/贴合：直接续链
            chain.append(nxt[0])
            cur = nxt
            continue
        if gap > GAP_MAX:
            unfilled.append({'y': [round(y_a), round(y_b)], 'gap': round(gap),
                             'reason': '缺口超上限%.0fpx' % gap})
            chain.append(nxt[0])
            cur = nxt
            continue
        pa = (cur[4], cur[2])                # 迎面端点
        pb = (nxt[3], nxt[1])
        d_a = abs(pa[0] - trend(y_a))
        d_b = abs(pb[0] - trend(y_b))
        if d_a <= ALIGN_TOL and d_b <= ALIGN_TOL:
            fills.append({'y': [round(y_a), round(y_b)], 'gap': round(gap),
                          'fill': [[round(pa[0]), round(pa[1])], [round(pb[0]), round(pb[1])]]})
        else:
            unfilled.append({'y': [round(y_a), round(y_b)], 'gap': round(gap),
                             'reason': '端点偏离走廊%.0f/%.0fpx' % (d_a, d_b)})
        chain.append(nxt[0])
        cur = nxt
    pts = np.vstack([p for p in chain])
    return pts, fills, unfilled, trims


def render_continuous(stem, struct, lines, seg):
    viz = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR)
    dim = np.zeros(viz.shape[:2], bool)
    for o in struct["others"]:
        for sid in (o.get("segment_ids") or o.get("track_ids") or []):
            if sid in seg:
                cv2.polylines(dim, [np.asarray(seg[sid]["points"], int).reshape(-1, 1, 2)], False, True, 3)
    for c in struct["content"]:
        for sid in c.get("segment_ids", []):
            if sid in seg:
                cv2.polylines(dim, [np.asarray(seg[sid]["points"], int).reshape(-1, 1, 2)], False, True, 3)
    for f in struct["frames"]:
        if f.get("side") not in ("left", "right"):
            for sid in f["segment_ids"]:
                if sid in seg:
                    cv2.polylines(dim, [np.asarray(seg[sid]["points"], int).reshape(-1, 1, 2)], False, True, 3)
    viz[dim] = (viz[dim] * 0.45).astype(np.uint8)
    for f in struct["frames"]:
        if f.get("side") in ("left", "right"):
            for sid in f["segment_ids"]:
                if sid in seg:
                    cv2.polylines(viz, [np.asarray(seg[sid]["points"], int).reshape(-1, 1, 2)],
                                  False, (0, 200, 0), 5, cv2.LINE_AA)
    # 原始片段（红/绿）与补全段（青）分开画
    for ln in lines:
        col = (0, 200, 0) if ln["kind"] == "edge" else (0, 0, 255)
        src_ids = ln.get("_orig_ids", [])
        for sid in src_ids:
            if sid in seg:
                cv2.polylines(viz, [np.asarray(seg[sid]["points"], int).reshape(-1, 1, 2)],
                              False, col, 5, cv2.LINE_AA)
        for fl in ln["fills"]:
            a, b = np.asarray(fl["fill"], float)
            cv2.line(viz, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (255, 200, 0), 5, cv2.LINE_AA)
        for ex in ln.get("extends", []):
            if len(ex) >= 2:
                arr = np.asarray(ex, float).astype(int).reshape(-1, 1, 2)
                cv2.polylines(viz, [arr], False, (0, 165, 255), 5, cv2.LINE_AA)
    cv2.putText(viz, "red=orig col  cyan=bridged  orange=extended  green=edges  dim=dropped",
                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(viz, "red=orig col  cyan=bridged  orange=extended  green=edges  dim=dropped",
                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_连续性叠加图.png"),
                viz, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_连续性叠加图_预览.jpg"),
                half, [cv2.IMWRITE_JPEG_QUALITY, 85])


def _peak_in(o, y_a, y_b, x0, x1, x_prev, cont, thr, look=0):
    """[y_a..y_b]×[x0..x1] 内测墨迹峰（可加前瞻 look）：强度达阈值且与 x_prev 连续（±cont）→ 返回峰位 x，否则 None。"""
    y0, y1 = min(y_a, y_b), max(y_a, y_b)
    if look:
        y0, y1 = (y0 - look, y0) if y1 > y0 else (y1, y1 + look)
    x0, x1 = max(0, int(x0)), int(x1)
    band = o[int(y0):int(y1), x0:x1]
    if band.size == 0:
        return None
    strength = (255.0 - band.astype(float)).sum(axis=0)
    if strength.max() < thr * (y1 - y0):
        return None
    xi = x0 + int(np.argmax(strength))
    if abs(xi - x_prev) > cont:
        return None
    return float(xi)


def extend_end(o, pts, x_nominal, y_stop, up, band_h=250.0, win=80.0, cont=40.0, thr=0.10):
    """A 方案端点外延（标称位置锚定）：从线端向表格边逐带（250px）走，
    首步在 标称x±win 内找本线，后续只按连续性 ±cont 跟走（漂移由步进自然跟踪，
    也跳不到间距 80 的邻线）；每带需墨迹峰达阈值，墨迹断即停。
    返回外延点列 [(x,y)...]。"""
    H = o.shape[0]
    ext = []
    if up:
        p = pts[0]
        y_cur, x_cur = float(p[1]), float(p[0])
        first = True
        while y_cur > y_stop + band_h:
            yt = max(float(y_stop), y_cur - band_h)
            # 首步在标称位置 ±win 内找本线；后续只按连续性 ±cont 跟走（漂移由步进跟踪）
            win0, win1 = (int(x_nominal - win), int(x_nominal + win)) if first else \
                         (int(x_cur - cont), int(x_cur + cont))
            first = False
            xi = _peak_in(o, y_cur, yt, win0, win1, x_cur, cont, thr, look=band_h)
            if xi is None:
                break
            ext.append((xi, yt))
            y_cur, x_cur = yt, xi
        if ext and ext[-1][1] > y_stop:
            ext.append((ext[-1][0], float(y_stop)))
        return list(reversed(ext))
    p = pts[-1]
    y_cur, x_cur = float(p[1]), float(p[0])
    first = True
    while y_cur < y_stop - band_h:
        yt = min(float(y_stop), y_cur + band_h)
        win0, win1 = (int(x_nominal - win), int(x_nominal + win)) if first else \
                     (int(x_cur - cont), int(x_cur + cont))
        first = False
        xi = _peak_in(o, y_cur, yt, win0, win1, x_cur, cont, thr, look=band_h)
        if xi is None:
            break
        ext.append((xi, yt))
        y_cur, x_cur = yt, xi
    if ext and ext[-1][1] < y_stop:
        ext.append((ext[-1][0], float(y_stop)))
    return ext


def robust_span(spans):
    """lines 的 (y_min, y_max) → 稳健表格范围：取最大聚类的范围。"""
    def largest(vals):
        best, bc = None, -1
        for v in vals:
            c = sum(1 for w in vals if abs(w - v) <= 120)
            if c > bc:
                best, bc = v, c
        return best
    tops = largest([s[0] for s in spans])
    bots = largest([s[1] for s in spans])
    return tops, bots


def main():
    only = sys.argv[1:] or sorted('%d' % i for i in range(1015, 1045))
    summary = {}
    for n in only:
        stem = '钻孔柱状图' + n
        struct = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_列结构定稿.json', encoding='utf-8'))
        cj = json.load(open(paths.CANDIDATE_COORD_DIR / f'{stem}.json', encoding='utf-8'))
        seg = {s['id']: s for s in cj['lines'] if s['direction'] == 'vertical' and s['label'] == 'high'}
        o = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)

        lines = []
        for f in struct['frames']:
            if f.get('side') in ('left', 'right'):
                pts, fills, unf, trims = bridge_line(seg, f['segment_ids'])
                lines.append({'kind': 'edge', 'side': f['side'], 'src': f.get('src'),
                              '_orig_ids': [sid for sid in f['segment_ids'] if sid in seg],
                              '_nom': f['x_at_mid'], 'pts_arr': pts, 'fills': fills,
                              'unfilled': unf, 'trims': trims})
        for c in struct['columns']:
            pts, fills, unf, trims = bridge_line(seg, c['segment_ids'])
            lines.append({'kind': 'column', 'index': c['index'], 'name': c.get('name'),
                          'src': c.get('src'), '_orig_ids': [sid for sid in c['segment_ids'] if sid in seg],
                          '_nom': c['x_at_mid'], 'pts_arr': pts, 'fills': fills,
                          'unfilled': unf, 'trims': trims})

        # 稳健表格范围：已达边的线的范围（抗离群碎片）
        spans = [(float(l['pts_arr'][:, 1].min()), float(l['pts_arr'][:, 1].max())) for l in lines]
        y_top, y_bot = robust_span(spans)

        # A 方案端点外延：分带墨迹实证（标称位置锚定+连续性），逐带跟进，墨迹断即停
        nexts = 0
        for ln in lines:
            pts = ln['pts_arr']
            ext_top = extend_end(o, pts, ln['_nom'], y_top, up=True) if pts[0][1] - y_top > 60 else []
            ext_bot = extend_end(o, pts, ln['_nom'], y_bot, up=False) if y_bot - pts[-1][1] > 60 else []
            if ext_top:
                pts = np.vstack([np.asarray(ext_top, float), pts])
            if ext_bot:
                pts = np.vstack([pts, np.asarray(ext_bot, float)])
            ln['pts_arr'] = pts
            ln['extends'] = [[round(x), round(y)] for x, y in ext_top + ext_bot]
            nexts += len(ext_top) + len(ext_bot)

        ends = []
        for ln in lines:
            pts = ln['pts_arr']
            top_s, bot_s = pts[0][1] - y_top, y_bot - pts[-1][1]
            if top_s > 60 or bot_s > 60:
                ends.append({'line': ln.get('index', ln.get('side')), 'name': ln.get('name'),
                             'top_short': int(max(0, top_s)), 'bottom_short': int(max(0, bot_s))})
        for ln in lines:
            ln['pts'] = np.round(ln['pts_arr'], 1).tolist()
            del ln['pts_arr']
            ln.pop('_nom', None)
        nfill = sum(len(l['fills']) for l in lines)
        nunf = sum(len(l['unfilled']) for l in lines)
        out = {'image': stem, 'table_y': [round(y_top), round(y_bot)], 'lines': lines, 'ends_report': ends}
        json.dump(out, open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_分割线.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)
        render_continuous(stem, struct, lines, seg)
        summary[n] = {'fills': nfill, 'unfilled': nunf, 'extends': nexts, 'ends': len(ends)}
        print(n, '补全%d处 外延%d步 未补%d处 剩端差%d线' % (nfill, nexts, nunf, len(ends)), flush=True)

    json.dump(summary, open(paths.RUNS_DIR / 'table_reconstruct' / '补全汇总.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
