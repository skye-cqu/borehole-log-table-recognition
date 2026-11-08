# -*- coding: utf-8 -*-
"""列线/外框边的"无弦分段"账：把 6a2 `_分割线.json` 重切成一段一段真段,不连线。

为什么需要它(用户 2026-09-27 肉眼指出 6d 叠加图上有一堆锯齿线,`runs/tmp/diag_col_saw.py` 实测):
`_分割线.json` 的 `lines[].pts` 与它 `_orig_ids` 那些阶段4 碎片的点集**逐点全等**,只是被按 y
全局排过序;而 6d/6j 的画法(`frame_topbottom.py:302-305`)把这串排序后的点当**一条**折线画,
于是每处碎片断口都被连成直线弦 —— 30 张 326 条线里 **1921 段这种弦是 JSON 里根本没有的**(最长 9284px),
另有 757 段确实是该阶段 `fills`/`extends` 登记过的断口补全(有账,该画,但要单独着色)。
同一份 JSON,`bridge_gaps.render_continuous` 按碎片逐段画就没有这些斜穿。**数据无罪,是画法与表征。**

本模块只做两件事:
  1. 按出处把每条线切成 parts(真段)/bridged(有账桥接)/gaps(真断口);
  2. 按 6g/门禁5 的现成判据 `track_rows.in_band` 剔掉整段落在柱状图案带内的碎片(图案自己的边线不是列线)。
**只读**:不改写 `_分割线.json`,剔除逐条落账,随时可还原。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

if str(Path(__file__).resolve().parents[2]) not in sys.path:      # 允许直接跑本文件自检
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.table.track_rows import content_band, in_band

TOUCH = 3.0        # 两碎片端点相距在这个范围内才算"接得上",并成一段;超出就是断口,不连线
HOLE = 8.0         # 空档小于此值不当断口出账:实测 2085 处断口 p50=7px,是碎片端点量化噪声
KEEP_SPAN = 0.95   # 守卫:剔完带内碎片后,y 跨度至少要保住全线的这个比例,否则整条不剔
RECON = paths.RUNS_DIR / "table_reconstruct"


def frag_points(stem, direction="vertical"):
    """该图的阶段4 段: {碎片id: (x,y) 点列(按前进轴升序;竖段=按 y,横段=按 x)}。"""
    ax = 1 if direction == "vertical" else 0
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    out = {}
    for s in cj["lines"]:
        if s["direction"] != direction:
            continue
        a = np.asarray(s["points"], float)
        out[s["id"]] = a[np.argsort(a[:, ax])] if len(a) > 1 else a
    return out


def chain_frags(frags, axis=1):
    """[(碎片id, 点列)] → 真段 [(点列, [碎片id...]), ...]。

    按前进轴起讫排序后贪心接续:下一条碎片的首端点离当前段尾端点欧氏距离 ≤TOUCH 才接,否则收段另起。
    段内每一笔落点都由碎片自己的点构成 → 结构上不存在"无账弦"。axis=1 竖线(按 y 走)、0 横线(按 x 走)。
    """
    fs = sorted(((float(p[:, axis].min()), i, p) for i, p in frags))
    parts, cur, cur_ids = [], None, []
    for _, i, p in fs:
        if cur is not None:
            gap = float(np.hypot(*(p[0] - cur[-1])))
            if gap <= TOUCH:                          # 接得上：并段(端点重合则不重复记点)
                cur = np.vstack([cur, p[1:] if gap == 0.0 else p])
                cur_ids.append(i)
                continue
            parts.append((cur, cur_ids))              # 接不上：收段另起
        cur, cur_ids = p.copy(), [i]
    if cur is not None:
        parts.append((cur, cur_ids))
    return [q for q in parts if len(q[0]) >= 2]


def split_band_frags(frags, band):
    """整段落在柱状带内的碎片剔掉(图案边线不是列线)。带认不出或守卫不过 → 一条不剔。

    守卫查"带外碎片的 y 跨度 ≥ 全线跨度 × KEEP_SPAN":带认错会把真列线整截抹掉,
    那种情况宁可不剔,把告警交人看。
    """
    if band is None or not frags:
        return frags, [], ""
    flag = [in_band(p, band) for _, p in frags]
    keep = [t for t, f in zip(frags, flag) if not f]
    dropped = [t for t, f in zip(frags, flag) if f]
    if not dropped:
        return frags, [], ""
    def span(ts):
        return (max(p[:, 1].max() for _, p in ts) - min(p[:, 1].min() for _, p in ts)) if ts else 0.0
    if not keep or span(keep) < KEEP_SPAN * span(frags):
        return frags, [], (f"带内碎片 {len(dropped)} 条但守卫不过(带外 y 跨度 "
                           f"{span(keep):.0f}/{span(frags):.0f}px),整条不剔")
    return keep, dropped, ""


def holes(ivs, min_len=HOLE):
    """若干 [y0,y1] 区间并集之外的空档(断口)。"""
    ivs = sorted([sorted(map(float, v)) for v in ivs if v[1] > v[0]])
    if not ivs:
        return []
    merged = [ivs[0]]
    for a, b in ivs[1:]:
        if a - merged[-1][1] <= min_len:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [[merged[k][1], merged[k + 1][0]] for k in range(len(merged) - 1)]


def _bridges(line, axis=1):
    """该阶段登记过的补全: fills(桥接,直线) / extends(外延,逐点墨迹实证) → [(点列, 种类)]。

    `bridge_gaps.py:293` 把 extends 存成**扁平点列** `[[x,y],...]`(上端外延一路 + 下端外延一路,
    每点一步 250px)，所以这里按前进轴跳变 >400px 处切成上下两段，段内按登记顺序连。
    上下框(`frame_topbottom.py`)同样登记 fills/extends,并另有 ext_conn(外延端点接回链体的两点点子)。
    """
    out = [(np.asarray(fl["fill"], float), "fill")
           for fl in line.get("fills", []) if np.asarray(fl["fill"], float).shape == (2, 2)]
    out += [(np.asarray(c, float), "fill") for c in line.get("ext_conn", [])
            if np.asarray(c, float).shape == (2, 2)]
    ex = np.asarray(line.get("extends", []), float)
    if ex.ndim == 2 and ex.shape[1] == 2 and len(ex) >= 2:
        cuts = [0] + [k for k in range(1, len(ex)) if abs(ex[k, axis] - ex[k - 1, axis]) > 400] \
            + [len(ex)]
        out += [(ex[cuts[i]:cuts[i + 1]], "extend") for i in range(len(cuts) - 1)
                if cuts[i + 1] - cuts[i] >= 2]
    return out


def line_parts(stem):
    """一张图 → {'image','band_src','warnings','lines':[{kind,index,name,src,parts,bridged,gaps,dropped}]}

    parts   = [([ [x,y]... ], [阶段4 碎片id...])]，真段，段内绝无无账弦
    bridged = [([ [x,y]... ], 'fill'|'extend')]，有账补全，出图单独着色、出账单独一类
    gaps    = [[y0,y1]...]，parts+bridged 合起来仍接不上的真断口，只出账不画线
    dropped = 被剔的带内碎片 id(图案边线)，逐条留名可还原
    """
    dd = json.load(open(RECON / f"{stem}_分割线.json", encoding="utf-8"))["lines"]
    seg = frag_points(stem)
    w, e, band_src = content_band(stem)
    band = (w, e) if w is not None else None
    out, warn = [], []
    for ln in dd:
        if not ln.get("pts"):
            continue
        frags = [(i, seg[i]) for i in ln.get("_orig_ids", []) if i in seg]
        dropped = []
        if ln["kind"] == "column":
            frags, dropped, msg = split_band_frags(frags, band)
            if msg:
                warn.append(f"{ln['kind']}{ln.get('index')}: {msg}")
        parts = chain_frags(frags)
        bridged = _bridges(ln)
        cov = [(p[:, 1].min(), p[:, 1].max()) for p, _ in parts]
        cov += [(p[:, 1].min(), p[:, 1].max()) for p, _ in bridged]
        out.append({"kind": ln["kind"], "index": ln.get("index"), "side": ln.get("side"),
                    "name": ln.get("name"), "src": ln.get("src"),
                    "parts": [(p.tolist(), list(ids)) for p, ids in parts],
                    "bridged": [(p.tolist(), k) for p, k in bridged],
                    "gaps": [[round(a, 1), round(b, 1)] for a, b in holes(cov)],
                    "dropped": [i for i, _ in dropped]})
    return {"image": stem, "band_src": band_src, "warnings": warn, "lines": out}


def frame_parts(stem):
    """6d 的上下框 `_上下框.json` → 与 `line_parts` 同形状的记录 + 6d 自己登记的四角证据。

    顶/底框由 6d 用**阶段4 横段 + fills 桥接 + 墨迹验证外延(extends)** 拼出来(约束2 的三种来源都在),
    它的 `groups[].pts` 和 6a2 一样是"碎片点全集按前进轴排过序的折线",所以照同一把刀切成真段、不连线。
    corners 取 evidence 里 6d 登记的 corner_tl/tr/bl/br(它按左右边在角 y 处取点),用来量四角接不接得上。
    """
    d = json.load(open(RECON / f"{stem}_上下框.json", encoding="utf-8"))
    seg = frag_points(stem, "horizontal")
    out = []
    for kind in ("top", "bottom"):
        for gi, g in enumerate(d.get(kind, {}).get("groups", [])):
            frags = [(i, seg[i]) for i in g.get("segment_ids", []) if i in seg]
            parts = chain_frags(frags, axis=0)
            bridged = _bridges(g, axis=0)
            cov = [(p[:, 0].min(), p[:, 0].max()) for p, _ in parts]
            cov += [(p[:, 0].min(), p[:, 0].max()) for p, _ in bridged]
            out.append({"kind": kind, "index": gi, "side": None, "name": f"{kind}框", "src": "6d",
                        "missing": [i for i in g.get("segment_ids", []) if i not in seg],
                        "parts": [(p.tolist(), list(ids)) for p, ids in parts],
                        "bridged": [(p.tolist(), k) for p, k in bridged],
                        "gaps": [[round(a, 1), round(b, 1)] for a, b in holes(cov)],
                        "unfilled": g.get("unfilled", []), "ext_short": g.get("ext_short", [])})
    return {"image": stem, "corners": d.get("evidence", {}), "lines": out}


def chord_violations(parts, seg):
    """守门人:段内相邻两点必须同属一条阶段4 碎片,否则距离必须 ≤TOUCH。返回越界清单。

    `parts` = [((x,y) 点列, [碎片id...])]；这就是"不许有无账弦"的可执行定义,出表与回读都跑它。
    """
    fp = {i: {tuple(p) for p in a} for i, a in seg.items()}
    bad = []
    for pts, ids in parts:
        a = np.asarray(pts, float)
        owned = {tuple(p): set() for p in a}
        for i in ids:
            for p in fp.get(i, ()):
                if tuple(p) in owned:
                    owned[tuple(p)].add(i)
        for p, q in zip(a, a[1:]):
            k0, k1 = tuple(p), tuple(q)
            if owned[k0] & owned[k1]:
                continue
            if float(np.hypot(*(q - p))) > TOUCH:
                bad.append([k0, k1, round(float(np.hypot(*(q - p))), 1)])
    return bad


JUMP = 40.0        # 单跳超过此值 = 用户口径的"边上突然大跳转"(2026-09-27 标准③)
SUDDEN = 0.5       # 且跳距至少要够到沿线前进量的这个比例,否则叫倾斜不叫跳转


def _owner(pts, ids, src):
    """段内点 → 所属阶段4 碎片id。只有同一条碎片内部的两个相邻点才谈得上"线自己的形状"。"""
    own = {}
    for i in ids:
        for p in src.get(i, np.zeros((0, 2))):
            own.setdefault((round(float(p[0])), round(float(p[1]))), i)
    return own


def _is_outlier(a, i, off, d):
    """点 a[i] 是不是孤零零偏出去:两邻居水平一致、它离两边都远 → 偏出去又回来。"""
    if i <= 0 or i >= len(a) - 1:
        return False
    n0, n1 = a[i - 1, off], a[i + 1, off]
    return abs(n0 - n1) <= max(15.0, 0.3 * abs(d)) and \
        min(abs(a[i, off] - n0), abs(a[i, off] - n1)) >= 0.5 * abs(d)


def line_jumps(parts, src, axis=1):
    """一条线(列线/框边/上下框)→ (跳账, 每段要剔的离群点下标)。

    跳账按形态三类:
      尖点 = 偏出去又回来(阶段4 碎片里的离群点,真线没动) → 出图出表都剔,剔完两侧邻居差 ≤15px;
      端点 = 落在整条线最外两端、前后看不全 → 角上的直角拐弯就是这一类,不剔;
      台阶 = 偏出去不回来 → 碎片跨了两条线或线真折了,不剔,交人看。
    碎片之间由 `chain_frags` 保证端点距离 ≤TOUCH,不可能有跳,所以只判同碎片内部的跳。
    axis=1 竖线(沿线走 y、偏移看 x)、axis=0 横线(沿线走 x、偏移看 y)。
    """
    off, prog = (0, 1) if axis == 1 else (1, 0)
    if not parts:
        return [], []
    a_all = np.vstack([np.asarray(p, float) for p, _ in parts])
    lo, hi = float(a_all[:, prog].min()), float(a_all[:, prog].max())
    log, drops = [], []
    for pts, ids in parts:
        a = np.asarray(pts, float)      # parts 由 chain_frags 产出,已按前进轴排好
        own, bad = _owner(a, ids, src), set()
        for j in range(len(a) - 1):
            k0 = (round(float(a[j, 0])), round(float(a[j, 1])))
            k1 = (round(float(a[j + 1, 0])), round(float(a[j + 1, 1])))
            if own.get(k0) is None or own[k0] != own.get(k1):
                continue
            d = float(a[j + 1, off] - a[j, off])
            dp = abs(float(a[j + 1, prog] - a[j, prog]))
            if abs(d) < JUMP or abs(d) < SUDDEN * dp:      # 够不上"突然"的算倾斜,不出账
                continue
            sp = [i for i in (j, j + 1) if _is_outlier(a, i, off, d)]
            bad.update(sp)
            log.append(('尖点' if sp else '端点' if j <= 1 or j + 1 >= len(a) - 2 else '台阶',
                        round(abs(d)), own[k0],
                        round(100 * (float(a[j, prog]) - lo) / max(1.0, hi - lo)),
                        [round(float(a[j, 0])), round(float(a[j, 1]))],
                        [round(float(a[j + 1, 0])), round(float(a[j + 1, 1]))]))
        drops.append(sorted(bad))
    return log, drops


def drop_points(parts, drops):
    """按 `line_jumps` 的下标剔点 → (新 parts, 被剔的点 [[x,y,碎片id], ...])。剔完不足 2 点的段整段丢。"""
    out, cut = [], []
    for (pts, ids), bad in zip(parts, drops):
        a = np.asarray(pts, float)
        for i in bad:
            cut.append([round(float(a[i, 0]), 1), round(float(a[i, 1]), 1)])
        keep = np.delete(np.arange(len(a)), bad)
        if len(keep) >= 2:
            out.append((a[keep], list(ids)))
    return out, cut


if __name__ == "__main__":
    stem = "钻孔柱状图1024"
    d = line_parts(stem)
    seg = frag_points(stem)
    c7 = next(l for l in d["lines"] if l["kind"] == "column" and l["index"] == 7)
    assert len(d["lines"]) == 11, len(d["lines"])                 # 9 列 + 2 框边
    assert len(c7["dropped"]) == 55, len(c7["dropped"])           # 实测 1024 col7 带内 55/206
    bad = [v for l in d["lines"] for v in chord_violations(
        [(np.asarray(p, float), i) for p, i in l["parts"]], seg)]
    assert not bad, bad[:3]
    whole = [l for l in d["lines"] if l["kind"] == "column"]
    assert sum(len(l["parts"]) for l in whole) > 1, "分段过碎"

    # 上下框：切段后必须与 6d 登记的点集**逐点全等**，且不许有无账弦
    fr, raw = frame_parts(stem), json.load(open(RECON / f"{stem}_上下框.json", encoding="utf-8"))
    fh = frag_points(stem, "horizontal")
    assert len(fr["lines"]) == 2, len(fr["lines"])
    for rec, kind in zip(fr["lines"], ("top", "bottom")):
        src = {tuple(map(float, x)) for g in raw[kind]["groups"] for x in g["pts"]}
        got = {tuple(map(float, x)) for p, _ in rec["parts"] for x in p}
        got |= {tuple(map(float, x)) for p, _ in rec["bridged"] for x in p}
        assert src == got and not rec["missing"], (kind, len(src - got), rec["missing"])
        assert not chord_violations([(np.asarray(p, float), i) for p, i in rec["parts"]], fh)

    # 边上突然大跳转：1024 左边顶部那个 x=285 的离群点(实测把左上角顶歪 47px)必须被判成尖点并剔掉
    e = next(l for l in d["lines"] if l["kind"] == "edge" and l["side"] == "left")
    parts = [(np.asarray(p, float), i) for p, i in e["parts"]]
    log, drops = line_jumps(parts, seg, 1)
    assert [(s, f) for s, _, f, _, _, _ in log] == [("尖点", 33), ("尖点", 33)], log
    kept, cut = drop_points(parts, drops)
    assert [round(float(p[0])) for p in cut] == [285], cut
    assert not line_jumps(kept, seg, 1)[0], "剔完还有突跳"
    assert not chord_violations(kept, seg)
    print(f"OK 1024: 线 {len(d['lines'])} 条 + 上下框 {len(fr['lines'])} 条(逐点全等)｜"
          f"col7 真段 {len(c7['parts'])} 桥接 {len(c7['bridged'])} "
          f"断口 {len(c7['gaps'])} 带内剔 {len(c7['dropped'])}｜左边尖点剔 {len(cut)} 点，剔后无突跳")
