# -*- coding: utf-8 -*-
"""把定稿的行线 + 列线打成一份可直接使用的数据集，并出全分辨率叠加图。

输入只有两个判定的结果，本脚本不重新判定、不回写任何判定产物：
  runs/table_reconstruct/{stem}_行判定.json    行线（层界）——poly 已是 (x, y)
  runs/table_reconstruct/{stem}_分割线.json    列线 + 表左右边界——走 `src/table/col_segments.py`
                                              按阶段4 碎片出处**逐段出账**：断口不连线、补全单独记账

为什么列线源从 `_列结构定稿.json` 换成 `_分割线.json`(用户 2026-09-27 定的基准 = 6d 外框叠加图)：
  定稿只有 9 条内部列界，不含 6a2 的断口补全与 6a4 补好的左右外框；且上一版用
  `track_columns.load_chain()` 复原列线时把点**按 y 全局排序成一根折线**，
  于是 30 张 326 条线里 1921 段"碎片间断口直连"以真实列线几何出了盘(实测见 runs/tmp/diag_col_saw.py)。
  现在段内每一笔落点都由阶段4 碎片自己的点构成：`fills`/`extends` 有账补全记 backing，
  接不上的空档进 `col_gaps` 出账不画线。整段落在柱状图案带内的碎片不作列线证据(dropped_in_band)。

数据清洗（用户 2026-09-26 口径："不需要在'柱状'和'简易水文曲线'内做标注"）：
  柱状列画的是岩性图案、简易水文曲线列画的是测井曲线，都不是表格线，其内不画行线。
  每条层界按列分带裁开，只留 数值区(x<柱状西缘) 与 岩性描述(柱状东缘≤x<岩性|水文分隔)，
  切点落在带缘上。一条层界因此拆成 1~2 段（数值段 + 岩性段），段数≈行数×2。
  列带缘走生产代码同一套：柱状带 = content_band，岩性|水文 = 定稿最右一条列线（continue_below 续到表底）。
输出（paths.LINE_DELIVERY.dir，新目录）：
  每张/{stem}.json      单张全量：线级记录 + 折线点 + 判据参数 + 告警 + 断口账
  行列线_线级.csv        一条线段一行（含起讫、点数、来源段、backing）
  行列线_点级.csv        一个折点一行，段内直接连点成线
  清单.json             逐张计数、参数、告警、源文件指纹
  叠加图/{stem}.png     原分辨率：红=行线段 蓝=列线段 绿=外框边 青=有账桥接 橙=外延 黄=待核行线
  叠加图_半分辨率预览/{stem}.jpg
  局部1比1/{图号}_{上|中|下}.png   原尺寸裁片，肉眼看得清单

用法: python src/tools/emit_line_dataset.py [1015 1027]   # 无参数=30 张全量
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import col_segments                                  # noqa: E402
from src.table.track_columns import load_chain                      # noqa: E402
from src.table.track_rows import content_band, edge_at, continue_below  # noqa: E402

RECON = paths.RUNS_DIR / "table_reconstruct"
NEG, POS = -1e9, 1e9            # 带缘认不出时的哨兵：柱状缺→不裁带，水文缺→不裁右
ROW_COL = (0, 0, 255)     # BGR 红 = 行线
COL_COL = (255, 90, 0)    # BGR 蓝 = 列线
EDGE_COL = (0, 220, 0)    # BGR 绿 = 表左右边界（约束5：外框不作列分隔线，单独成类）
FILL_COL = (255, 220, 0)  # BGR 青 = 有账桥接段（6a2 fills）
EXT_COL = (0, 165, 255)   # BGR 橙 = 有账外延段（6a2 extends）
SUS_COL = (0, 255, 255)   # BGR 黄 = 离墨标尺判为"真歪"的行线，请人逐条看
GAP_COL = (150, 150, 150)  # BGR 灰虚 = 真断口（只示意，不作线数据）
FRAME_COL = (255, 0, 255)  # BGR 品红 = 外框上下边(6d _上下框.json,同"外框不作列分隔线"一类)
LONG_GAP = 600          # 断口超过此长度改画浅灰：这条线在这一段是真没认出来，别跟短口混
STUB = 120              # 长断口只从两端各画这么长一截，中间不猜路径
WIN_H = 2200              # 局部 1:1 裁片高（原图像素，不缩放）
TAG = {"row": "R", "col": "C", "edge": "E", "top": "T", "bottom": "B"}
W = 3


def suspects():
    """diag_off.py 落盘的真歪名单：{(图, 该线的 y_at_mid 取整)}。没有名单就当没有可疑线。"""
    if not paths.LINE_SUSPECTS.exists():
        return set()
    return {(s["image"], s["y"]) for s in
            json.load(open(paths.LINE_SUSPECTS, encoding="utf-8"))}


def fingerprint(p):
    return hashlib.md5(p.read_bytes()).hexdigest()[:12]


def _gaps(kind, index, name, items, gaps, ax=1):
    """真断口 → 带坐标的账目（出图叠成灰虚示意、断口标尺按它量墨；不进 lines/CSV，不当线数据）。

    两端点取断口两侧最近段的端点：段与段本来就同一条线，两端就是断口最可信的位置。
    ax=1 竖线：区间记进 y0/y1、横向位置记进 x0/x1；ax=0 横框：区间记进 x0/x1、纵向位置记进 y0/y1。
    这样叠图端 `dashed(x0, y0, x1, y1)` 两种朝向都能直接画，不必再分叉。
    """
    out, cr = [], 1 - ax
    for a, b in gaps:
        prev = [p for p, _, _ in items if float(p[:, ax].max()) <= a + col_segments.HOLE]
        nxt = [p for p, _, _ in items if float(p[:, ax].min()) >= b - col_segments.HOLE]
        v0 = float(prev[-1][-1, cr]) if prev else (float(nxt[0][0, cr]) if nxt else None)
        v1 = float(nxt[0][0, cr]) if nxt else v0
        if v0 is None:
            continue
        p0, p1 = (round(float(a), 1), round(float(b), 1))
        out.append({"kind": kind, "col_index": index, "col_name": name,
                    "y0": p0 if ax else round(v0, 1), "y1": p1 if ax else round(v1, 1),
                    "x0": round(v0, 1) if ax else p0, "x1": round(v1, 1) if ax else p1})
    return out


def col_records(stem):
    """列线 + 外框四条边 → 逐段记录（一条线拆成若干段，段内不连线就不可能有弦）+ 该张的账。

    kind: col=列分隔线、edge=外框左右边(6a2 `kind=edge`)、top/bottom=外框上下边(6d `_上下框.json`)。
    backing: frag=阶段4 碎片接出来的真段、fill=登记的桥接补全、extend=登记的外延。
    边上"突然大跳转"(用户 2026-09-27 标准③)按 `col_segments.line_jumps` 分三类：
      尖点 = 阶段4 碎片里的离群点(偏出去又回来) → 剔掉并落账，剔完两侧邻居差 ≤15px，不造新点；
      端点 = 落在整条线两端(实测 15 处里 11 处是顶框东端向下折 70px 接右框的直角弯) → 不剔，出账；
      台阶 = 偏出去不回来 → 不剔，出账交人看(约束3：碎片本身只报不改)。
    """
    d, fr = col_segments.line_parts(stem), col_segments.frame_parts(stem)
    srcs = {1: col_segments.frag_points(stem), 0: col_segments.frag_points(stem, "horizontal")}
    recs, seq, book = [], {"col": 0, "edge": 0, "top": 0, "bottom": 0}, []
    lines = [(ln, 1, "col" if ln["kind"] == "column" else "edge") for ln in d["lines"]] + \
            [(ln, 0, ln["kind"]) for ln in fr["lines"]]
    for ln, ax, k in lines:
        src = srcs[ax]
        parts = [(np.asarray(p, float), ids) for p, ids in ln["parts"]]
        log, drops = col_segments.line_jumps(parts, src, ax)
        parts, cut = col_segments.drop_points(parts, drops)
        items = sorted([(p, "frag", ids) for p, ids in parts] +
                       [(np.asarray(p, float), b, []) for p, b in ln["bridged"]],
                       key=lambda t: float(t[0][:, ax].min()))
        gs = _gaps(k, ln["index"], ln["name"], items, ln["gaps"], ax)
        for j, (pts, backing, ids) in enumerate(items):
            seq[k] += 1
            recs.append({"kind": k, "seq": seq[k], "col_index": ln["index"],
                         "col_name": ln["name"], "src": ln["src"], "side": ln.get("side"),
                         "part": j, "n_parts": len(items), "backing": backing,
                         "points": pts.tolist(), "segment_ids": ids,
                         "n_chains": None, "cov_num": None, "cov_desc": None,
                         "suspect": False})
        dropped = ln.get("dropped", [])
        if gs or cut or log or dropped:
            book.append({"kind": k, "col_index": ln["index"], "col_name": ln["name"], "gaps": gs,
                         "gap_px": round(sum(g["y1"] - g["y0"] for g in gs), 1),
                         "dropped_in_band": dropped,
                         "jumps": [{"shape": s, "px": px, "frag": f, "at_pct": pct}
                                   for s, px, f, pct, _, _ in log],
                         "outliers": cut, "unfilled": ln.get("unfilled", []),
                         "ext_short": ln.get("ext_short", [])})
    return recs, {"band_src": d["band_src"], "warnings": d["warnings"], "lines": book,
                  "corners": fr["corners"]}


def band_bounds(stem):
    """行线裁剪用的三条竖向分带缘 → (柱状西 zw, 柱状东 ze, 岩性|水文 sw)，都是 x = f(y) 的 callable。

    柱状带直接取生产判定同一函数 content_band（含带东缘未检出时按实测带宽中位推的兜底）。
    岩性|水文 = 定稿最右一条列线（30 张实测它就是岩性描述右界，其后即水文曲线列）；它在下半张
    常断，用 continue_below 跟着邻线平移到表底，否则裁到断口以下会把真岩性内容一起裁掉。
    任一缘认不出交哨兵：柱状缺 → zw=ze=-1e9（不裁带，数值+岩性并成一段留），水文缺 → sw=1e9（不裁右）。
    """
    w, e, _ = content_band(stem)
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]}
    cols = sorted(json.load(open(RECON / f"{stem}_列结构定稿.json", encoding="utf-8"))["columns"],
                  key=lambda c: c["x_at_mid"])
    chains = [load_chain(c, seg)[0] for c in cols]
    last = continue_below(chains[-1], chains[:-1], float(cj["height"]))
    zw = (lambda y, c=w: edge_at(c, y)) if w is not None else (lambda y: NEG)
    ze = (lambda y, c=e: edge_at(c, y)) if e is not None else (lambda y: NEG)
    sw = (lambda y, c=last: edge_at(c, y)) if last is not None else (lambda y: POS)
    return zw, ze, sw


def clip_poly(poly, zw, ze, sw):
    """一条行线折线沿 x 走一遍，只吐 数值区(x<zw) 与 岩性(ze≤x<sw) 两段，切点落在带缘上。

    逐段求与三条带缘 x=f(y) 的交点（段短，缘按端点线性插值取根即够），按交点把段切成子段，
    子段中点落在带外则并入当前 keep 段、落在带内则收段。返回若干 [(x,y)]，每段≥2 点才留。
    """
    P = np.asarray(poly, float)
    if len(P) < 2:
        x, y = P[0]
        return [] if not (x < zw(y) or ze(y) <= x < sw(y)) else [P.tolist()]

    def region(x, y):                          # 0 数值keep / 1 柱状drop / 2 岩性keep / 3 水文drop
        if x < zw(y):
            return 0
        if x < ze(y):
            return 1
        return 2 if x < sw(y) else 3

    pieces, cur, cur_r = [], [], None
    for (ax, ay), (bx, by) in zip(P, P[1:]):
        marks = [(0.0, None)]
        for f in (zw, ze, sw):
            ga, gb = ax - f(ay), bx - f(by)
            if (ga < 0) != (gb < 0) and ga != gb and 0 < ga / (ga - gb) < 1:
                marks.append((ga / (ga - gb), f))     # 交点带出处，便于把 x 钉回带缘
        marks.append((1.0, None))
        marks.sort(key=lambda m: m[0])

        def pt(t, f):
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            return (f(y), y) if f is not None else (x, y)   # 线性交点会偏离倾斜带缘，钉回 x=f(y)

        for (t0, f0), (t1, f1) in zip(marks, marks[1:]):
            tm = 0.5 * (t0 + t1)
            r = region(ax + (bx - ax) * tm, ay + (by - ay) * tm)
            s0, s1 = pt(t0, f0), pt(t1, f1)
            if r in (0, 2):
                if cur_r != r:
                    if len(cur) >= 2:
                        pieces.append(cur)
                    cur, cur_r = [s0], r
                cur.append(s1)
            elif cur_r is not None:
                if len(cur) >= 2:
                    pieces.append(cur)
                cur, cur_r = [], None
    if len(cur) >= 2:
        pieces.append(cur)
    return pieces


def sheet(stem, sus, bounds):
    """一张 → 线记录列表（行线段在前、列线段/外框边在后）+ 列线断口/剔除账。

    行线按列分带裁开，一条层界可拆成多段；列线按阶段4 碎片出处逐段出账，一条线可拆成多段。
    """
    zw, ze, sw = bounds
    rd = json.load(open(RECON / f"{stem}_行判定.json", encoding="utf-8"))
    recs, seq = [], 0
    for i, r in enumerate(rd["rows"]):
        pieces = clip_poly(r["poly"], zw, ze, sw) or [[list(map(float, p)) for p in r["poly"]]]
        for part, pc in enumerate(pieces):
            seq += 1
            recs.append({"kind": "row", "seq": seq, "row_seq": i + 1, "part": part,
                         "n_parts": len(pieces), "points": pc, "backing": "chain",
                         "segment_ids": r["segment_ids"], "n_chains": r.get("n_chains"),
                         "cov_num": r.get("cov_num"), "cov_desc": r.get("cov_desc"),
                         "suspect": (stem, round(r["y_at_mid"])) in sus})
    cols, book = col_records(stem)
    return recs + cols, rd, book


def summarize(rec):
    p = np.asarray(rec["points"], float)
    rec["x0"], rec["y0"] = float(p[0, 0]), float(p[0, 1])
    rec["x1"], rec["y1"] = float(p[-1, 0]), float(p[-1, 1])
    rec["n_pts"] = len(p)
    rec["bbox"] = [float(p[:, 0].min()), float(p[:, 1].min()),
                   float(p[:, 0].max()), float(p[:, 1].max())]
    return rec


def color_of(rec):
    if rec["suspect"]:
        return SUS_COL
    if rec["backing"] == "fill":
        return FILL_COL
    if rec["backing"] == "extend":
        return EXT_COL
    return {"row": ROW_COL, "col": COL_COL, "edge": EDGE_COL,
            "top": FRAME_COL, "bottom": FRAME_COL}[rec["kind"]]


def dashed(img, x0, y0, x1, y1, col=GAP_COL, dash=18, gap=12):
    """灰虚示意：只画在图上、不进任何坐标数据，用来显形"这里真的断了"。"""
    n = int(max(abs(y1 - y0), abs(x1 - x0)))
    for s in range(0, n, dash + gap):
        t0, t1 = s / max(n, 1), min(s + dash, n) / max(n, 1)
        cv2.line(img, (int(x0 + (x1 - x0) * t0), int(y0 + (y1 - y0) * t0)),
                 (int(x0 + (x1 - x0) * t1), int(y0 + (y1 - y0) * t1)), col, 2, cv2.LINE_AA)


def vertical_ink(gray):
    """原图"真竖线墨"掩膜：自适应二值 → 1×40 竖条开运算(短竖笔=字/图案,剔掉) → 25px 竖向闭运算。
    与 runs/tmp/yard_cols.py、yard_seg_ink.py 同一口径，是约束2 的可执行检验。"""
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8) * 255
    v = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
    del bw
    return cv2.morphologyEx(v, cv2.MORPH_CLOSE, np.ones((25, 1), np.uint8))


def ink_frac(rec, v, n=20, tol=5.0, look=30):
    """一段线落在真竖墨上的比例：沿段纵向采样 n 个 y，量它离最近竖墨的横距 ≤tol 的占多少。"""
    P = np.asarray(rec["points"], float)
    if len(P) < 2:
        return 1.0
    ys = np.linspace(P[:, 1].min(), P[:, 1].max(), n)
    xs = np.interp(ys, P[:, 1], P[:, 0])
    hit = 0
    for y, x in zip(ys, xs):
        yi, xi = int(round(y)), int(round(x))
        if not 0 <= yi < v.shape[0]:
            continue
        lo = max(0, xi - look)
        idx = np.flatnonzero(v[yi, lo:min(v.shape[1], xi + look + 1)])
        hit += bool(len(idx)) and float(np.abs(idx + lo - xi).min()) <= tol
    return hit / max(len(ys), 1)


def drop_off_ink(recs, v):
    """补全段(fill/extend)不贴真竖墨 → 从线数据里剔掉并落账（约束2：不许有原图没有的线）。

    6a2 的 `extend_end` 用自己的墨迹峰判据(整列灰度和)外延，步 250px、容 ±40px，
    会一路漂到空白纸上(实测 1019 col9 的外延落在 x2375~2391，真竖墨在 x2435，差 60px)。
    阶段4 碎片(backing=frag)是数据源本身，按约束3/4 只报不剔。
    """
    keep, cut = [], []
    for r in recs:
        if r["kind"] != "row" and r["backing"] in ("fill", "extend"):
            f = ink_frac(r, v)
            if f < 0.8:
                cut.append({"line_id": r["line_id"], "kind": r["kind"],
                            "col_index": r["col_index"], "backing": r["backing"],
                            "ink_frac": round(f, 2), "n_pts": r["n_pts"],
                            "y0": r["y0"], "y1": r["y1"], "x0": r["x0"], "x1": r["x1"]})
                continue
        keep.append(r)
    return keep, cut


def overlay(stem, gray, recs, gaps, out_png, out_jpg, out_win):
    """全分辨率叠加图 + 半分辨率预览 + 上/中/下三张原尺寸 1:1 裁片（肉眼核验用的就是它）。"""
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for m in gaps:
        if m["y1"] - m["y0"] <= LONG_GAP:                      # 短断口:虚线示意位置(两端 x 可信)
            dashed(img, m["x0"], m["y0"], m["x1"], m["y1"], (150, 150, 150))
            continue
        for x, y, s in ((m["x0"], m["y0"], 1), (m["x1"], m["y1"], -1)):   # 长断口:只从两端各伸一截,不猜路径
            dashed(img, x, y, x, y + s * STUB, (150, 150, 150))
    for rec in recs:
        pts = np.rint(np.asarray(rec["points"], float)).astype(np.int32).reshape(-1, 1, 2)
        col = color_of(rec)
        cv2.polylines(img, [pts], False, col, W + 1 if rec["suspect"] else W, cv2.LINE_AA)
    txt = ("red=row  blue=col  green=edge LR  magenta=frame TB  cyan=bridged  orange=extended  "
           "yellow=suspect row  gray dashed=open gap(账在 col_gaps,不作线数据)")
    for colr, wid in (((0, 0, 0), 6), ((255, 255, 255), 2)):
        cv2.putText(img, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, colr, wid, cv2.LINE_AA)
    cv2.imwrite(str(out_png), img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out_jpg), half, [cv2.IMWRITE_JPEG_QUALITY, 85])
    H = img.shape[0]
    for tag, yc in (("上", 0.14), ("中", 0.50), ("下", 0.86)):
        y0 = max(0, min(H - WIN_H, int(H * yc) - WIN_H // 2))
        cv2.imwrite(str(out_win / f"{stem[-4:]}_{tag}.png"), img[y0:y0 + WIN_H, :].copy(),
                    [cv2.IMWRITE_PNG_COMPRESSION, 3])
    del img, half


def main():
    stems = [f"钻孔柱状图{a}" if a.isdigit() else a for a in sys.argv[1:]] or \
            sorted(p.name[:-len("_行判定.json")] for p in RECON.glob("*_行判定.json"))
    out = paths.LINE_DELIVERY
    for d in (out.json, out.overlay, out.preview, out.window):
        d.mkdir(parents=True, exist_ok=True)

    manifest, lines, pts = [], [], []
    sus = suspects()
    for stem in stems:
        recs, rd, book = sheet(stem, sus, band_bounds(stem))
        recs = [summarize(r) for r in recs]
        for r in recs:
            r["line_id"] = f"{stem}{TAG[r['kind']]}{r['seq']:03d}"
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise FileNotFoundError(paths.RAW_DIR / f"{stem}.JPG")
        recs, unverified = drop_off_ink(recs, vertical_ink(gray))     # 补全段不贴真竖墨的一律剔掉
        for r in recs:
            lines.append(r)
            for i, (x, y) in enumerate(r["points"]):
                pts.append({"line_id": r["line_id"], "image": stem, "kind": r["kind"],
                            "i": i, "x": round(float(x), 2), "y": round(float(y), 2)})
        cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
        cnt = {"n_row_segs": sum(r["kind"] == "row" for r in recs),
               "n_col_segs": sum(r["kind"] == "col" for r in recs),
               "n_edge_segs": sum(r["kind"] == "edge" for r in recs),
               "n_cols": len({r["col_index"] for r in recs if r["kind"] == "col"}),
               "n_edges": len({(r["side"], r["col_index"]) for r in recs if r["kind"] == "edge"}),
               "n_suspect": sum(r["suspect"] for r in recs),
               "n_col_gaps": sum(len(b["gaps"]) for b in book["lines"]),
               "gap_px": round(sum(b["gap_px"] for b in book["lines"])),
               "long_gaps": sum(1 for b in book["lines"] for g in b["gaps"]
                                if g["y1"] - g["y0"] > LONG_GAP),
               "n_dropped": sum(len(b["dropped_in_band"]) for b in book["lines"]),
               "n_unverified": len(unverified)}
        payload = {"image": stem, "width": cj["width"], "height": cj["height"],
                   "source": {"行判定": fingerprint(RECON / f"{stem}_行判定.json"),
                              "分割线": fingerprint(RECON / f"{stem}_分割线.json")},
                   "params": {k: rd[k] for k in ("table_x", "row_cov", "row_h", "step_tol",
                                                 "slope_med", "skew_gate", "split_lim")}
                             | {"col_seg": {"touch_px": col_segments.TOUCH,
                                            "keep_span": col_segments.KEEP_SPAN,
                                            "band_src": book["band_src"]}},
                   "n_layer_rows": len(rd["rows"]), **cnt,
                   "col_gaps": book["lines"],
                   "dropped_unverified": unverified,
                   "warnings": rd["warnings"] + book["warnings"] +
                               [f"补全段离真竖墨被剔 {u['line_id']} {u['kind']}"
                                f"{'外延' if u['backing'] == 'extend' else '桥接'}"
                                f" 贴墨{u['ink_frac']}" for u in unverified],
                   "lines": recs}
        with open(out.json / f"{stem}.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        manifest.append({k: payload[k] for k in
                         ("image", "n_layer_rows", "n_row_segs", "n_col_segs", "n_edge_segs",
                          "n_cols", "n_edges", "n_suspect", "n_col_gaps", "gap_px", "long_gaps",
                          "n_dropped", "n_unverified", "warnings")}
                        | {"params": payload["params"]})
        overlay(stem, gray, recs, [g for b in book["lines"] for g in b["gaps"]],
                out.overlay / f"{stem}.png", out.preview / f"{stem}.jpg",
                out.window)
        del gray
        print(f"{stem}: 层界 {payload['n_layer_rows']} → 行线段 {cnt['n_row_segs']}｜"
              f"列线 {cnt['n_cols']} 条→{cnt['n_col_segs']} 段｜外框边 {cnt['n_edges']}→"
              f"{cnt['n_edge_segs']} 段｜断口 {cnt['n_col_gaps']} 处 {cnt['gap_px']}px"
              f"(>600px 的 {cnt['long_gaps']})｜带内剔 {cnt['n_dropped']}｜"
              f"离墨补全剔 {cnt['n_unverified']}｜"
              f"待核行线 {cnt['n_suspect']}｜告警 {payload['warnings']}", flush=True)

    keys = ("n_row_segs", "n_col_segs", "n_edge_segs", "n_cols", "n_edges", "n_suspect",
            "n_col_gaps", "gap_px", "long_gaps", "n_dropped", "n_unverified", "n_layer_rows")
    with open(out.lines_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "image", "kind", "seq", "col_index",
                                          "col_name", "src", "side", "backing",
                                          "row_seq", "part", "n_parts",
                                          "x0", "y0", "x1", "y1", "n_pts", "n_chains",
                                          "cov_num", "cov_desc", "suspect", "segment_ids"],
                           extrasaction="ignore")
        w.writeheader()
        for r in lines:
            r["segment_ids"] = json.dumps(r["segment_ids"])
            w.writerow(r)
    with open(out.pts_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["line_id", "image", "kind", "i", "x", "y"])
        w.writeheader()
        w.writerows(pts)
    with open(out.manifest, "w", encoding="utf-8") as f:
        json.dump({"n_images": len(manifest), "n_points": len(pts),
                   **{k: sum(m[k] for m in manifest) for k in keys},
                   "clip": "行线已裁出柱状带与简易水文曲线，一条层界拆成数值段+岩性段",
                   "col_seg": "列线/外框边按阶段4 碎片出处逐段出账：断口不连线(无弦)，"
                              "fills/extends 有账补全单独成段，柱状带内碎片不作列线证据",
                   "color": {"row": "red", "col": "blue", "edge": "green", "bridged": "cyan",
                             "extended": "orange", "suspect_row": "yellow", "open_gap": "灰虚"},
                   "clean": "桥接/外延补全段若不贴原图真竖墨(1×40 竖条开运算标尺)一律剔掉, 逐条记在 "
                            "每张 JSON 的 dropped_unverified；柱状图案带内碎片剔在 col_gaps.dropped_in_band",
                   "images": manifest}, f, ensure_ascii=False, indent=1)
    print(f"合计 {len(manifest)} 张：层界 {sum(m['n_layer_rows'] for m in manifest)} → "
          f"行线段 {sum(m['n_row_segs'] for m in manifest)}；列线 {sum(m['n_cols'] for m in manifest)} 条 → "
          f"{sum(m['n_col_segs'] for m in manifest)} 段；外框边 {sum(m['n_edges'] for m in manifest)} → "
          f"{sum(m['n_edge_segs'] for m in manifest)} 段；断口 {sum(m['n_col_gaps'] for m in manifest)} 处 "
          f"{sum(m['gap_px'] for m in manifest)}px；带内剔 {sum(m['n_dropped'] for m in manifest)}；"
          f"离墨补全剔 {sum(m['n_unverified'] for m in manifest)}；折点 {len(pts)} → {out.dir}")


if __name__ == "__main__":
    main()
