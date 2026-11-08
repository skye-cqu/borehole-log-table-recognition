# -*- coding: utf-8 -*-
"""列线修复(M6.T6):先剔干净、再端点连线补口——**不吸墨重描、不跟字造线、不拟合直线**。

流程(用户 2026-10-25 拍板:表格整体歪斜、列线是斜线,且列线为手绘拼接的长线、各段斜率
相近但不相同——所以补口不拟合直线,直接把缺口两端的线端点连起来,斜率由端点自带):
只处理混轨体检(M6.T6)名单内的图,只动检出受损 span 的线,只动**数据区**:
- 第一遍·剔错轨:错轨 span = 现役线离墨迹重描 >TOL_DEV 持续 ≥MIN_SPAN 的区间;span 内
  偏离碎片判为误收,剔除回 _orig_ids。跨表头带边界的碎片不剔(整条删会带走表头带真墨,
  抬走 6b interp 括区,1042 sep8 实测偏 11.6px)。吸墨重描只作检测参照,绝不落账——
  逐 y 吸墨实测在行线交叉/手写度数处跟字走(1042 真厚|倾角界每行线一钩,用户核验发现)。
- 第二遍·端点连线补口:幸存碎片按整段 y 极值求 ≥MIN_SPAN 的洞(碎片是 2 点直线段,只标
  点会把段内误判成洞),把洞两端的线端点直接连起来;缺一端的洞按本线幸存点平均斜率外推,
  连到外框上/下框的交点(6a3/6a4 已建的折线,用户 2026-10-25 拍板)。补口点逐点落在端点
  /平均斜率确定的直线上,账记端点/交点坐标,可机器复验。
- 门A/B/C=第一遍的剔除否决:重描锚点离本线表头车道 >40px(门A)、重描中位骑到邻线轨
  ±15px 内(门B)、重描偏离自身平滑参考占比 >8%(门C)→ 重描参照不可信,该 span 不剔
  (1019 实测锚被跨轨桥带跑 +51px;参照错时剔真碎片=二次破坏)。
账:分割线 JSON 顶层 repair 字段(逐 span 记 dev_frac/action/removed_frags,逐洞记
linear_fills 端点)+ rollback 备份。

用法: python src/table/col_line_repair.py 1042 1035 ...   (无参数=allowlist 全部; --dry 只报不改)
"""
import json
import shutil
import sys

import cv2
import numpy as np
from scipy.signal import medfilt

from src.core import paths
from src.table import col_segments
from src.table.header_assign import _ink_line

REPAIR_TAG = "repair_20261023"
ALLOW = ["1019", "1023", "1024", "1030", "1031", "1033", "1035", "1042"]
MIN_SPAN = 100.0    # 修复/错轨判定的最小 span(px)
TOL_DEV = 30.0      # 现役线离墨迹重描超过此值算偏离
GAP_TOL = 12.0      # span 分组容忍的单点间断
DEV_FRAC_MAX = 0.08  # 门C:重描参照点偏离自身平滑参考(151px 中值滤波,12px 容差)的占比上限。
# 实测:贴线重描(1042 柱状 5952-12708,已核验)=0.042;跟手写数字走的(1023/1042 数值列)=0.12~0.28。
# 超门=重描在跟字,参照不可信 → 该 span 不剔任何碎片。
TOL_ANCHOR = 40.0    # 质量门A:锚点 x vs 本线表头带 x 中值(车道身份,墨迹核验过)之差的上限。
# 数据区顶部的 cover 点可能只有 6a2 跨轨桥的点,锚点会被带跑到邻轨(1019 倾角|真厚线实测 +51px)。
# 本线碎片不能当车道真值——它们的段集正是混轨受害者(1042 柱状侧翼碎片=图案边,偏 71px 是碎片错不是重描错)。
TOL_NB = 15.0        # 门B:重描 x 中位落在某邻列线局部轨 ±15px 内 → 参照不可信,该 span 不剔(列分隔线不可能骑邻线)。
NB_WIN = 800.0       # 门B 邻线局部轨的 y 窗口(px)


def _x_at(items, y):
    """coverage [(点列, 随附)] 在 y 处的现役 x;无覆盖返回 None。"""
    for p, _ in items:
        if p[0, 1] - 3 <= y <= p[-1, 1] + 3:
            return float(np.interp(y, p[:, 1], p[:, 0]))
    return None


def _avg_slope(pts):
    """本线幸存点的平均斜率(一次拟合,离群 >TOL_DEV 剔一轮)→ (k, b):x = k*y + b。"""
    wy, wx = pts[:, 1], pts[:, 0]
    k, b = np.polyfit(wy, wx, 1)
    keep = np.abs(np.polyval((k, b), wy) - wx) <= TOL_DEV
    if keep.sum() >= 2:
        k, b = np.polyfit(wy[keep], wx[keep], 1)
    return float(k), float(b)


def _frame_hit(polylines, end, k, b, down):
    """延长线 x=k*y+b 与外框折线的交点;取沿延长方向最近的。返回 (y, x) 或 (None, None)。"""
    hits = []
    for p in polylines:
        for a, c in zip(p[:-1], p[1:]):
            den = (c[0] - a[0]) - k * (c[1] - a[1])
            if abs(den) < 1e-9:
                continue
            t = (k * a[1] + b - a[0]) / den
            if not 0.0 <= t <= 1.0:
                continue
            y = float(a[1] + t * (c[1] - a[1]))
            if (down and y > end[1] + 1) or (not down and y < end[1] - 1):
                hits.append((y, float(k * y + b)))
    if not hits:
        return None, None
    return min(hits) if down else max(hits)


def _spans(flag, min_len):
    """bool 序列 → 连续 True 区间(容忍 GAP_TOL 间断),≥min_len 的 [(i0,i1)]。"""
    out, start, last = [], None, None
    for i, f in enumerate(flag):
        if f:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last > GAP_TOL:
            if last - start >= min_len:
                out.append((start, last))
            start = None
    if start is not None and last - start >= min_len:
        out.append((start, last))
    return out


def _data_top(stem, table_top):
    """数据区起点 = 表头带以下(与 header_assign.determine 同口径)。

    修复只动数据区:表头带里列线常与表头文字笔画相邻/相交,吸墨会跟字走(1023 实测),
    那里本来也不该由修复补线。
    """
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    hline = sorted(s["midy"] for s in cj["lines"]
                   if s["direction"] == "horizontal" and s["label"] == "high")
    below = [y for y in hline if y >= table_top + 150]
    return below[0] if below else table_top + 400


def repair_chart(stem, dry=False):
    recon = paths.RUNS_DIR / "table_reconstruct"
    f = recon / f"{stem}_分割线.json"
    d = json.load(open(f, encoding="utf-8"))
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                        encoding="utf-8"))
    ymid_h = (hm["band"][0] + hm["band"][1]) / 2.0
    hdr = {}                                    # (kind, index) → 表头带 x 中值(车道身份)
    for s in hm["sep_pts"]:
        hdr[(s["kind"], s.get("index"))] = float(np.interp(ymid_h, s["ys"], s["xs"]))
    seg = col_segments.frag_points(stem)
    fsegs = {}      # 外框上下框折线(kind → [(N,2) 折线...]):缺一端补口连到外框交点用
    for fl in col_segments.frame_parts(stem)["lines"]:
        fsegs.setdefault(fl["kind"], []).extend(
            [np.asarray(p, float) for p, _ in fl["parts"]]
            + [np.asarray(p, float) for p, _ in fl["bridged"]])
    anchors = [float(np.median(b["xs"])) for b in hm["sep_pts"]]  # 锚族中心=各界 xs 全距中位(已核验重描出自此口径)
    drawn = {(-1 if l["index"] is None else l["index"], l["name"]): l
             for l in col_segments.line_parts(stem)["lines"]}
    own_pts = {}                                # column index → 本线全部阶段4 碎片点(门B 用)
    for l in d["lines"]:
        if l.get("kind") == "column" and l.get("index") is not None:
            ps = [seg[i] for i in l.get("_orig_ids", []) if i in seg]
            if ps:
                own_pts[l["index"]] = np.vstack(ps)
    report = {"tool": "col_line_repair", "lines": []}
    for ln in d["lines"]:
        if ln.get("kind") != "column" or not ln.get("_orig_ids"):
            continue
        key = (-1 if ln.get("index") is None else ln["index"], ln.get("name"))
        dl = drawn.get(key)
        if dl is None:
            continue
        parts = [(np.asarray(p, float), i) for p, i in dl["parts"]]
        cover = parts + [(np.asarray(p, float), b) for p, b in dl["bridged"]]
        frags = [(i, seg[i]) for i in ln["_orig_ids"] if i in seg]
        if not cover or len(frags) < 2:
            continue
        bot = int(max(p[:, 1].max() for p, _ in cover))
        top = int(_data_top(stem, int(min(p[:, 1].min() for p, _ in cover))))
        if top >= bot:
            continue
        head = np.vstack([p[(p[:, 1] >= top) & (p[:, 1] <= top + 300)]
                          for p, _ in cover])[:, 0]
        if not len(head):
            continue
        x_anchor = float(np.median(head))
        # 门A:锚点必须在本线自己的车道上(表头带身份)。跑偏=顶部只有跨轨桥的点可依,整线放弃。
        x_hdr = hdr.get(("column", ln.get("index")))
        if x_hdr is not None and abs(x_anchor - x_hdr) > TOL_ANCHOR:
            continue
        y_lo, y_hi = top, bot
        rx, ry = _ink_line(gray, x_anchor, anchors, y_lo, y_hi)
        rx, ry = np.asarray(rx, float), np.asarray(ry, float)
        if len(rx) < 2:
            continue
        idx = {int(y): i for i, y in enumerate(ry)}

        gap_flag = np.zeros(y_hi - y_lo + 1, bool)
        for g0, g1 in dl["gaps"]:
            a, b = int(max(g0, y_lo)) - y_lo, int(min(g1, y_hi)) - y_lo
            if b >= a:
                gap_flag[a:b + 1] = True
        dev_flag = np.zeros(y_hi - y_lo + 1, bool)
        for i, y in enumerate(range(y_lo, y_hi + 1)):
            xe = _x_at(cover, y)
            j = idx.get(y)
            if xe is not None and j is not None and abs(xe - rx[j]) > TOL_DEV:
                dev_flag[i] = True
        spans = [(a + y_lo, b + y_lo) for a, b in _spans(gap_flag | dev_flag, MIN_SPAN)]

        rec = {"index": ln.get("index"), "name": ln.get("name"), "spans": []}
        cand = []                                   # (act, probe_pts, removed_ids)
        for s0, s1 in spans:
            m = (ry >= s0) & (ry <= s1)
            act = {"y": [int(s0), int(s1)], "ink_pts": int(m.sum()),
                   "ink_cover": round(float(m.sum()) / (s1 - s0 + 1), 2)}
            probe = [[float(rx[j]), float(ry[j])] for j in np.nonzero(m)[0]]
            rm = set()
            for fid, p in frags:
                if p[:, 1].min() < y_lo:
                    continue                # 跨表头带边界的碎片不剔:整条删会带走表头带真墨段,
                                            # 抬走 6b 的 interp 括区(1042 sep8 实测偏 11.6px)
                if not (p[:, 1].min() <= s1 and p[:, 1].max() >= s0):
                    continue
                ov = p[(p[:, 1] >= s0) & (p[:, 1] <= s1)]
                if not len(ov):
                    continue
                pairs = [(float(np.interp(y, p[:, 1], p[:, 0])), idx.get(int(y)))
                         for y in ov[:, 1]]
                pairs = [(x, j) for x, j in pairs if j is not None]
                if pairs and float(np.median(
                        [abs(x - rx[j]) for x, j in pairs])) > TOL_DEV:
                    rm.add(fid)
                    act.setdefault("removed_frags", []).append(str(fid))
            cand.append((act, probe, rm))
        seq = np.asarray([p for _, probe, _ in cand for p in probe], float)
        eval_ok = len(seq) >= 151
        if eval_ok:
            order = np.argsort(seq[:, 1])
            seq_y, ref = seq[order][:, 1], medfilt(seq[order][:, 0], 151)
        removed = set()
        for act, probe, rm in cand:
            off = bias = None
            if eval_ok and probe:
                pb = np.asarray(probe, float)
                off = float((np.abs(np.interp(pb[:, 1], seq_y, ref) - pb[:, 0])
                             > 12.0).mean())
            if probe:
                s0, s1 = act["y"]
                mid = (s0 + s1) / 2.0
                for ni, npts in own_pts.items():
                    if ni == ln.get("index"):
                        continue
                    xh = hdr.get(("column", ni))
                    if xh is None:
                        continue
                    wn = npts[(npts[:, 1] > mid - NB_WIN) & (npts[:, 1] < mid + NB_WIN)]
                    wn = wn[np.abs(wn[:, 0] - xh) <= 30.0]
                    if len(wn) < 8:
                        continue
                    nx = float(np.median(wn[:, 0]))
                    if abs(float(np.median([p[0] for p in probe])) - nx) < TOL_NB:
                        bias = round(float(np.median([p[0] for p in probe])) - nx, 1)
                        break
            act["dev_frac"] = None if off is None else round(off, 3)
            act["nb_hit_px"] = bias
            # 门A/B/C=剔除否决:重描参照本身不可信(锚离道/骑邻线/跟字)时不剔任何碎片。
            bad = (off is not None and off > DEV_FRAC_MAX) or bias is not None
            if bad:
                act["action"] = "vetoed"
                act["removed_frags"] = []
                rm = set()
            elif rm:
                act["action"] = "removed"
            else:
                act["action"] = "none"
            removed |= rm
        if removed:
            ln["_orig_ids"] = [i for i in ln["_orig_ids"] if i not in removed]
        # 第二遍·端点连线补口(用户 2026-10-25 拍板:表格整体歪斜,列线是斜线;列线为手绘
        #     拼接的长线,各段斜率相近但不相同——所以不拟合直线,直接把缺口两端的线端点
        #     连起来,斜率由端点自带)。覆盖按碎片整段 y 极值算(碎片是 2 点直线段,只标点
        #     会把段内误判成洞);洞 ≥MIN_SPAN 才补。缺一端(如缺口到图底)不猜,如实留口。
        frag_pts = [seg[i] for i in ln["_orig_ids"] if i in seg]
        if not frag_pts:
            continue
        surv = np.vstack(frag_pts)
        surv = surv[np.argsort(surv[:, 1])]
        old_ext = [p for p in ln.get("extends", [])]
        cov = np.zeros(y_hi - y_lo + 1, bool)
        for p in frag_pts:
            a = int(np.clip(p[:, 1].min(), y_lo, y_hi)) - y_lo
            b = int(np.clip(p[:, 1].max(), y_lo, y_hi)) - y_lo
            cov[a:b + 1] = True
        if old_ext:     # 老 6a2 外延(有账整线)按相邻点连覆盖,不重复补
            oe = np.asarray(old_ext, float)
            for a, b in zip(oe[:-1], oe[1:]):
                a1 = int(np.clip(min(a[1], b[1]), y_lo, y_hi)) - y_lo
                b1 = int(np.clip(max(a[1], b[1]), y_lo, y_hi)) - y_lo
                cov[a1:b1 + 1] = True
        for h0, h1 in [(a + y_lo, b + y_lo) for a, b in _spans(~cov, MIN_SPAN)]:
            rec1 = {"linear_fill": [int(h0), int(h1)]}
            up = surv[surv[:, 1] < h0]
            dn = surv[surv[:, 1] > h1]
            if len(up) and len(dn):
                (x0, y0), (x1, y1) = up[-1], dn[0]      # 缺口两侧最近的线端点
                k = (x1 - x0) / (y1 - y0)
                b0 = x0 - k * y0
                old_ext.extend([[float(k * y + b0), float(y)] for y in range(h0, h1 + 1)])
                rec1["fit"] = [round(float(k), 6), round(float(b0), 2)]
                rec1["endpoints"] = [[round(float(x0), 1), round(float(y0), 1)],
                                     [round(float(x1), 1), round(float(y1), 1)]]
            else:
                # 缺一端(缺口到图底/起于表底):按本线幸存点平均斜率外推,连到外框上/下框
                # 交点(用户 2026-10-25 拍板;外框=6a3/6a4 已建好的折线)。
                end = up[-1] if len(up) else dn[0]
                down = bool(len(up))
                k, b0 = _avg_slope(surv)
                y_hit, x_hit = _frame_hit(fsegs.get("bottom" if down else "top", []),
                                          end, k, b0, down)
                if y_hit is None:
                    rec1["skipped"] = "no_frame_hit"    # 外框没接着,不猜
                else:
                    ya, yb = (h0, int(y_hit)) if down else (int(y_hit), h1)
                    covered = lambda y: y_lo <= y <= y_hi and bool(cov[y - y_lo])
                    old_ext.extend([[float(k * y + b0), float(y)]
                                    for y in range(ya, yb + 1) if not covered(y)])
                    rec1["fit"] = [round(float(k), 6), round(float(b0), 2)]
                    rec1["frame_join"] = [round(float(x_hit), 1), round(float(y_hit), 1)]
            rec.setdefault("linear_fills", []).append(rec1)
        ln["extends"] = old_ext
        rec["spans"] = [act for act, _, _ in cand]
        report["lines"].append(rec)
    if dry:
        return report
    bk = paths.PROJECT_ROOT / "rollback" / f"列线修复前_{REPAIR_TAG.split('_')[1]}"
    bk.mkdir(parents=True, exist_ok=True)
    if not (bk / f.name).exists():
        shutil.copy2(f, bk / f.name)
    d[REPAIR_TAG] = report
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    return report


def main():
    dry = "--dry" in sys.argv
    codes = [a for a in sys.argv[1:] if a.isdigit() and len(a) == 4] or ALLOW
    for c in codes:
        if c not in ALLOW:
            print(f"skip {c}: 不在混轨名单")
            continue
        r = repair_chart(f"钻孔柱状图{c}", dry=dry)
        n_sp = sum(len(l["spans"]) for l in r["lines"])
        n_veto = sum(1 for l in r["lines"] for s in l["spans"] if s["action"] == "vetoed")
        n_rm = sum(len(s.get("removed_frags", [])) for l in r["lines"] for s in l["spans"])
        lf = [f for l in r["lines"] for f in l.get("linear_fills", [])]
        n_lf = sum(1 for f in lf if "fit" in f)
        n_skip = sum(1 for f in lf if "skipped" in f)
        n_fj = sum(1 for f in lf if "frame_join" in f)
        print(f"{c}: 受损线 {len(r['lines'])} 条, span {n_sp} 个(否决 {n_veto}),"
              f" 剔碎片 {n_rm}, 连线 {n_lf - n_fj} 段+接框 {n_fj} 段(弃 {n_skip})"
              + ("  [dry]" if dry else ""))


if __name__ == "__main__":
    main()
