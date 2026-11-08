# -*- coding: utf-8 -*-
"""阶段6 (b)：列名映射（结构锚定 v2）。

全部 30 张图表头经接触印张人工识读为同一 10 列布局：
  (空窄格)|地质时代|煤层标志层号|深度|层厚|采长|倾角|真厚|柱状|岩性描述|简易水文曲线
本脚本不依赖脆弱的文字簇计数，用结构锚定：
  1. 相邻分隔线间距最大的一格 = 岩性描述（宽 ~1300px，独一无二）；
  2. 其右全部 = 简易水文曲线区（删除，含次级分隔线/外框）；
  3. 其左邻格 = 柱状（删除）；再往右到左 7 格依次 = 真厚/倾角/采长/层厚/深度/煤层/地质时代；
  4. 更左侧剩余分隔线围出的格 = 空窄格/可疑（宽度过窄或数量超出 8 → 警告）。
文字簇仍计算并输出，但只作交叉验证（簇中心应落入对应命名格）。
"""
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
from src.table import col_segments  # noqa: E402
from src.table.track_columns import x_at, load_chain  # noqa: E402

NUMERIC_NAMES = ["真厚", "倾角", "采长", "层厚", "深度", "煤层标志层号", "地质时代"]
DROP_NAMES = {"柱状", "简易水文曲线"}
# 版式覆盖：1023 的"深度/层厚"两列序与标准版式互换。
# 依据（2026-10-18 原图 4x 放大实测，非目读传闻）：两图同为印刷体表头，
# 1023 左格(宽125px)印"层"、右格(宽87px)印"深"；其余 29 图左格(宽123px)印"深"、
# 右格(宽85px)印"层"。格宽规律一致而字互换 → 该图为合法异版，按图改写列名。
LAYOUT_OVERRIDES = {
    "钻孔柱状图1023": {"深度": "层厚", "层厚": "深度"},
}
# 合法异版：这些图的列名序列不与标准序列一致，但不是缺陷（ok 判据据此放行）
LAYOUT_VARIANTS = {
    "钻孔柱状图1023": ["地质时代", "煤层标志层号", "层厚", "深度", "采长",
                       "倾角", "真厚", "岩性描述"],
}
CELL_W_MIN, CELL_W_MAX = 30.0, 180.0   # 数值列格宽合理范围
TOL_SEP = 12.0                          # 竖笔与既有界的最小间距(px),防同线重复记
TXT_GAP = 14

# 表头内容锚定:格内 OCR 文本的关键词 → 列名(煤/柱 先于 层 判,因"煤层"含"层")
KEYCHAR = {"煤层标志层号": "煤", "柱状": "柱", "地质时代": "地", "深度": "深",
           "层厚": "层", "采长": "采", "倾角": "倾", "真厚": "真", "岩性描述": "岩"}


def match_name(text: str):
    """表头格 OCR 文本 → 列名;认不出返回 None。

    优先级:煤/标/层号(单字"标"防残读"层、标"/"保层标"错配成层厚) → 柱 → 其余单字。
    """
    if not text:
        return None
    if "煤" in text or "标" in text or "层号" in text:
        return "煤层标志层号"
    if "柱" in text:
        return "柱状"
    for nm in ("地质时代", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"):
        if KEYCHAR[nm] in text:
            return nm
    return None


def _get_ocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
        return RapidOCR(intra_op_num_threads=1)  # 默认满核线程在多进程池里互踩,实测慢 12 倍
    except ImportError:
        return None


def _cell_text(ocr, gray, band, x0, x1) -> str:
    x0, x1 = int(x0) + 4, int(x1) - 4
    if x1 - x0 < 8:
        return ""
    crop = gray[band[0]:band[1], x0:x1]
    if crop.size == 0:
        return ""
    res, _ = ocr(crop)
    return "".join(x[1] for x in (res or [])).strip()


def _relabel_by_content(cells, xs, band, gray, ocr):
    """表头内容锚定:数值区各格按 OCR 关键词重贴标签。

    边界集缺线/双描时,算术命名会整体错位(1020 实测:标签错移一格)。
    以格内表头文字为准:认出关键词 → 贴该名;算术名被别格凭内容认领且本格无词 → 让位
    (空窄格);关键词全库未出现 → 警告"内容未检出",不静默错位。
    岩性描述不重贴(最宽格锚定),只验证其文本含"岩"。
    返回 (cells', label_verify{name: text}, warns')。
    """
    warns = []
    veri = {}                                   # k -> (arithmetic名, ocr文本, 内容匹配名)
    for k, (li, ri, nm) in enumerate(cells):
        if nm in ("简易水文曲线",) or (nm is None and k >= len(cells) - 1 and ri == -1):
            continue
        if nm == "岩性描述":
            continue
        x0 = 0.0 if li < 0 else xs[li]
        x1 = float(gray.shape[1]) if ri < 0 else xs[ri]
        t = _cell_text(ocr, gray, band, x0, x1) if ocr else ""
        veri[k] = (nm, t, match_name(t))
    matched = {}
    for k, (nm, t, m) in veri.items():
        if m and m not in matched:
            matched[m] = k
    out = [list(c) for c in cells]
    for k, (nm, t, m) in veri.items():
        if m is not None:
            out[k][2] = m
        elif nm in matched:
            out[k][2] = None                    # 算术名已被别格认领,本格无词 → 让位
    # 重名守卫:版式不允许重复列名,同名取最右(先出现的)格,其余让位
    claimed = {}
    for k, (nm, t, m) in veri.items():
        final = out[k][2]
        if final in ("岩性描述", "柱状") or final is None:
            continue
        if final in claimed:
            out[k][2] = None
            warns.append(f"重复列名 {final}: 左格让位（双描或误配）")
        else:
            claimed[final] = k
    label_verify = {veri[k][2]: veri[k][1] for k in veri if veri[k][2]}
    # 岩性描述验证
    for k, (li, ri, nm) in enumerate(cells):
        if nm == "岩性描述":
            x0 = 0.0 if li < 0 else xs[li]
            x1 = float(gray.shape[1]) if ri < 0 else xs[ri]
            t = _cell_text(ocr, gray, band, x0, x1) if ocr else ""
            label_verify["岩性描述"] = t
            break
    # 未检出列
    for nm in NUMERIC_NAMES:
        if nm not in matched and not any(c[2] == nm for c in out):
            warns.append(f"表头内容未检出: {nm}（该列界缺失或与邻格并格，几何不外推）")
    return [tuple(c) for c in out], label_verify, warns


def _sep_bounds(stem: str) -> list:
    """列/框边界真段几何(单一真源 = col_segments.line_parts,即 _分割线.json 的 P10 口径)。

    parts=真段(无账弦),bridged=有账补全(fill/extend);dropped(带内图案碎片)不入选。
    返回边界列表(文件原序),每项 {kind,index,side,xs,ys},ys 升序,供 np.interp 取 x。
    真断口处 interp 线性跨接——只作切格裁片的导引,不作为结构线外传(与 6a2 fill 同性质)。
    """
    lp = col_segments.line_parts(stem)
    bounds = []
    for ln in lp["lines"]:
        pts = [p for seg, _ in ln["parts"] for p in seg]
        pts += [p for seg, _ in ln.get("bridged", []) for p in seg]
        if len(pts) < 2:
            continue
        pts = sorted(pts, key=lambda p: p[1])          # [[x,y],...] → y 升序
        bounds.append({"kind": ln["kind"], "index": ln.get("index"),
                       "side": ln.get("side"),
                       "xs": [float(p[0]) for p in pts], "ys": [float(p[1]) for p in pts]})
    return bounds


# --- 表头竖笔 ↔ 边界集对账(去双描 / 补漏检界)--------------------------------
# 触发条件一律是原图墨迹与几何事实,不含单图特判:
#   ① 去双描——相邻界 x_mid 间距 < CELL_W_MIN:同一物理竖线被检出两次,合并为均值;
#   ② 补界——已命名格宽 > CELL_W_MAX 且格内存在未被任何界认领的满高竖笔:
#      该界在原图上真实存在而 _分割线 漏检,按竖笔位置补入。
STROKE_MIN = 0.60       # 满高竖笔:表头带内暗色占比下限
STROKE_WMAX = 3         # 满高竖笔最大宽度(px);更宽的是文字笔画,不是列线
SNAP_WMAX = 5           # 逐 y 细行程最大宽度(px)
SNAP_TOL = 20.0         # 锚点到最近细行程的最大容许距离(px)
SNAP_MIN_HIT = 6        # 统一漂移拟合成立所需的最少命中锚点数


def _thin_runs(row) -> np.ndarray:
    """一行内的细暗色行程中心(候选竖线位置)。"""
    out, s = [], None
    for i, v in enumerate(row):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s <= SNAP_WMAX:
                out.append((s + i - 1) / 2.0)
            s = None
    if s is not None and len(row) - s <= SNAP_WMAX:
        out.append((s + len(row) - 1) / 2.0)
    return np.asarray(out, float)


def _header_strokes(gray, band) -> list:
    """表头带内满高竖笔 x 位置:该处确有印刷竖线(墨迹事实,与 _分割线 独立)。"""
    b0, b1 = int(band[0]), int(band[1])
    bh = b1 - b0
    dens = (gray[b0:b1] < 150).sum(axis=0)
    out, i, W = [], 0, gray.shape[1]
    while i < W:
        if dens[i] >= STROKE_MIN * bh:
            j = i
            while j < W and dens[j] >= STROKE_MIN * bh:
                j += 1
            if j - i <= STROKE_WMAX:
                out.append(float(i + int(np.argmax(dens[i:j]))))
            i = j
        else:
            i += 1
    return out


def _ink_line(gray, x_anchor, anchors, y0, y1):
    """墨迹验证外延:逐 y 求锚点族的统一漂移,再把 x_anchor 吸附到最近的细墨迹行程。

    落点全是原图实测的细行程中心——不创造原图不存在的线,不分箱重采样。
    锚点族是表头带内实测的其它列界,与目标界同属一族印刷竖线;用"统一漂移"
    拟合可把目标界钉在正确的物理线上,而不是吸到文字笔画。
    返回 (xs, ys) 按 y 升序;该 y 拟合不成立时不出点,缺口交下游线性跨接。
    """
    dark = gray < 150
    A = np.asarray(anchors, float)
    xs, ys = [], []
    for y in range(int(y0), int(y1) + 1):
        rr = _thin_runs(dark[y])
        if len(rr) < SNAP_MIN_HIT:
            continue
        idx = np.abs(rr[None, :] - A[:, None]).argmin(axis=1)
        f = float(np.median(rr[idx] - A))
        if int((np.abs(rr[idx] - A - f) <= SNAP_TOL).sum()) < SNAP_MIN_HIT:
            continue
        k = int(np.abs(rr - (x_anchor + f)).argmin())
        if abs(rr[k] - (x_anchor + f)) <= SNAP_TOL:
            xs.append(float(rr[k]))
            ys.append(float(y))
    return xs, ys


def _span_y(bounds, gray):
    y0 = int(min(b["ys"][0] for b in bounds))
    y1 = int(min(max(b["ys"][-1] for b in bounds), gray.shape[0] - 1))
    return y0, y1


def _merge_twins(bounds, xs, gray, warns):
    """① 去双描:相邻界 x_mid 间距 < CELL_W_MIN → 同一物理竖线的两次检出,合并为均值。

    合并后的折线由墨迹验证外延重建(_ink_line):原两笔各自的折线在下段可能各走
    各的(一笔漂到邻线),取谁都不对,只有按合并后的 x 重新吸附才落在真线上。
    """
    if len(xs) < 2:
        return bounds, xs
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    groups, cur = [], [order[0]]
    for i in order[1:]:
        if xs[i] - xs[cur[-1]] < CELL_W_MIN:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)
    if all(len(g) == 1 for g in groups):
        return bounds, xs
    y0, y1 = _span_y(bounds, gray)
    nb, nx = [], []
    for g in groups:
        xm = float(np.mean([xs[i] for i in g]))
        if len(g) == 1:
            nb.append(bounds[g[0]])
            nx.append(xs[g[0]])
            continue
        b = dict(bounds[max(g, key=lambda k: bounds[k]["ys"][-1] - bounds[k]["ys"][0])])
        sx, sy = _ink_line(gray, xm, xs, y0, y1)
        if len(sy) >= 2:
            b["xs"], b["ys"] = sx, sy
        b["x_mid"] = xm
        nb.append(b)
        nx.append(xm)
        warns.append("相邻界 x=%s 间距 < %.0fpx，判为同一竖线双描，合并为 x=%.1f"
                     % ([round(xs[i], 1) for i in g], CELL_W_MIN, xm))
    return nb, nx


def _add_missing_splits(bounds, xs, cells, ia, gray, band, warns):
    """② 补漏检界:已命名格宽 > CELL_W_MAX 且格内有未被认领的满高竖笔 → 补为列界。

    限定在岩性描述左界以左:其右是柱状图案与简易水文曲线区,那里的满高笔画不是列界
    (不限定时会在 11 张图上误劈简易水文曲线)。
    """
    strokes = _header_strokes(gray, band)
    if not strokes:
        return bounds, xs
    left_desc = xs[ia]
    y0, y1 = _span_y(bounds, gray)
    nb, nx = list(bounds), list(xs)
    for li, ri, nm in list(cells):
        if nm is None or nm == "岩性描述":     # 未命名格与最宽锚格不参与劈分
            continue
        lx = 0.0 if li < 0 else nx[li]
        rx = float(gray.shape[1]) if ri < 0 else nx[ri]
        if rx > left_desc + TOL_SEP or rx - lx <= CELL_W_MAX:
            continue
        for s in strokes:
            if not (lx + CELL_W_MIN <= s <= rx - CELL_W_MIN):
                continue
            if any(abs(s - v) <= TOL_SEP for v in nx):
                continue
            sx, sy = _ink_line(gray, s, xs, y0, y1)
            if len(sy) < 2:
                continue
            nb.append({"kind": "column", "index": None, "side": None,
                       "xs": sx, "ys": sy, "x_mid": s})
            nx.append(s)
            warns.append("%s 格宽 %.0fpx 超出预期，格内检出满高竖笔 x=%.0f（墨迹实测），补为列界"
                         % (nm, rx - lx, s))
    if len(nb) == len(bounds):
        return bounds, xs
    nb.sort(key=lambda b: b["x_mid"])
    return nb, [b["x_mid"] for b in nb]


def determine(stem: str):
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    hline_y = sorted(s["midy"] for s in cj["lines"]
                     if s["direction"] == "horizontal" and s["label"] == "high")

    bounds = _sep_bounds(stem)
    if len(bounds) < 2:
        out = {"image": stem, "ok": False, "n_sep": len(bounds), "columns": [],
               "drop_columns": [], "keep": [], "sep_pts": [],
               "warnings": ["分割线真段不足两条，需人工复核"]}
        with open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                  "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        return out
    table_top = min(min(b["ys"]) for b in bounds)
    below = [y for y in hline_y if y >= table_top + 150]
    band = (int(table_top + 8), int(round((below[0] - 10) if below else table_top + 400)))

    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    H, W = gray.shape
    bw = cv2.adaptiveThreshold(gray[band[0]:band[1]], 255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 12)
    dens = (bw == 0).sum(axis=0)
    bh = band[1] - band[0]
    txt = (dens >= 3) & (dens < 0.65 * bh)
    clusters = []
    for i, v in enumerate(txt):
        if v and clusters and i - clusters[-1][-1] <= TXT_GAP:
            clusters[-1].append(i)
        elif v:
            clusters.append([i])
    centers = [(g[0] + g[-1]) / 2 for g in clusters if len(g) >= 8]

    ymid = (band[0] + band[1]) / 2
    for b in bounds:
        b["x_mid"] = float(np.interp(ymid, b["ys"], b["xs"]))
    bounds.sort(key=lambda b: b["x_mid"])              # x 序 = 原序:下标即左右邻接界
    xs = [b["x_mid"] for b in bounds]

    def walk(xs):
        """算术命名:间距最宽处 = 岩性描述,其左邻 = 柱状,再左推 7 个数值列。

        返回 (cells, ia, ib, wid, warns);cells = [(左sep下标, 右sep下标, 列名)],-1=图缘。
        只做几何推演,内容锚定见 _relabel_by_content。
        """
        ww = []
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        xs_s = [xs[i] for i in order]
        gaps = [(b - a, k) for k, (a, b) in enumerate(zip(xs_s, xs_s[1:]))]
        wid, k_desc = max(gaps)
        if wid < 400:
            return None, None, None, wid, ww
        ia, ib = order[k_desc], order[k_desc + 1]      # 岩性描述左右界的 sep 序号（原列表）
        # S_b 右侧全部 = 简易水文曲线区（删除，含次级分隔线与外框）
        cells = []                                      # (left_i, right_i) sep 下标，-1=图左/右缘
        cells.append((ia, ib, "岩性描述"))
        if ia - 1 >= 0:
            cells.append((ia - 1, ia, "柱状"))
            for j, nm in enumerate(NUMERIC_NAMES):
                ri = ia - 1 - j
                cells.append((ri - 1, ri, nm))          # ri-1 可为 -1（图左缘）
                if ri - 1 < -1:
                    ww.append(f"数值列 {nm} 超出图左缘（扫描裁切）")
                    cells.pop()
                    break
            if len([c for c in cells if c[2] not in DROP_NAMES]) < len(NUMERIC_NAMES) + 1:
                ww.append("数值列不足 7（左列被扫描裁切或漏检）")
        else:
            ww.append("岩性描述左界缺失")
        # 左侧多余分隔线 → 未命名格（空窄格）
        leftmost_named = cells[-1][0]
        for li in range(leftmost_named - 1, -1, -1):
            cells.append((li - 1, li, None))
        # 右侧水文区子格
        n_sep = len(xs)
        if ib + 1 < n_sep:
            cells.append((ib, ib + 1, "简易水文曲线"))
            for ri in range(ib + 1, n_sep):
                cells.append((ri, ri + 1 if ri + 1 < n_sep else -1, "简易水文曲线"))
        else:
            cells.append((ib, -1, "简易水文曲线"))
        return cells, ia, ib, wid, ww

    warns, notes = [], []          # warns=结构问题(影响 ok);notes=修复记录(不影响 ok)
    # ① 去双描(相邻界间距过近 → 同一竖线的两次检出)
    bounds, xs = _merge_twins(bounds, xs, gray, notes)
    cells, ia, ib, wid, ww = walk(xs)
    if cells is None:
        return {"image": stem, "band": list(band), "sep_x": [round(x) for x in sorted(xs)],
                "n_sep": len(xs), "columns": [], "drop_columns": [], "keep": [],
                "warnings": [f"最宽格仅 {wid:.0f}px，未找到岩性描述锚"]}
    warns.extend(ww)
    # ② 补漏检界(已命名格过宽 + 格内满高竖笔) → 边界集变化则重走命名
    n_sep0 = len(bounds)
    bounds, xs = _add_missing_splits(bounds, xs, cells, ia, gray, band, notes)
    if len(bounds) != n_sep0:
        cells, ia, ib, wid, ww = walk(xs)
        warns.extend(ww)
    xs_s = sorted(xs)

    # 版式覆盖:OCR 读不出的手绘表头(1023)按人工复核记录换名;可读版式一律由
    # _relabel_by_content 内容锚定命名,不再做几何互换猜测
    ovr = LAYOUT_OVERRIDES.get(stem)
    if ovr:
        cells = [(l, r, ovr.get(n, n)) for l, r, n in cells]
        notes.append(f"应用人工复核版式覆盖: {sorted(ovr.items())}")

    ocr = _get_ocr()
    cells, label_verify, relabel_warns = _relabel_by_content(cells, xs, band, gray, ocr)
    warns.extend(relabel_warns)

    columns, drop, keep = [], [], []
    for li, ri, name in cells:
        lx = 0.0 if li < 0 else xs[li]
        rx = float(W) if ri < 0 else xs[ri]
        entry = {"name": name, "left_sep": li, "right_sep": ri,
                 "x_in_band": [round(lx, 1), round(rx, 1)],
                 "width": round(rx - lx, 1)}
        if name is None:
            entry["name"] = "空窄格"
            drop.append(entry)
        elif name in DROP_NAMES:
            drop.append(entry)
        else:
            if name != "岩性描述" and name != "地质时代" and not (
                    CELL_W_MIN <= rx - lx <= CELL_W_MAX):
                warns.append(f"{name} 格宽 {rx-lx:.0f}px 超出预期")
            columns.append(entry)
            keep.append(entry)
    columns.sort(key=lambda c: c["x_in_band"][0])
    keep.sort(key=lambda c: c["x_in_band"][0])
    # 交叉验证：文字簇中心应落入某个格（含被删格；落在外面才算异常）
    mis = []
    allc = columns + [d for d in drop if d["name"] != "空窄格"]
    for cx in centers:
        if not any(c["x_in_band"][0] <= cx <= c["x_in_band"][1] for c in allc):
            mis.append(round(cx, 1))
    if mis:
        warns.append(f"{len(mis)} 个文字簇落在所有格之外: {mis[:6]}")

    expected = ["地质时代", "煤层标志层号", "深度", "层厚", "采长",
                "倾角", "真厚", "岩性描述"]
    # 合法异版(如 1023 深度/层厚互换)与标准版式同等算通过
    ok = [c["name"] for c in columns] in (expected, LAYOUT_VARIANTS.get(stem))

    out = {"image": stem, "band": list(band), "sep_x_band": [round(x, 1) for x in xs_s],
           "n_sep": len(xs_s), "columns": columns, "drop_columns": drop,
           "keep": keep, "warnings": warns, "notes": notes,
           "ok": bool(ok and not warns),
           "header_src": "line_parts", "label_verify": label_verify,
           "sep_pts": [{"kind": b["kind"], "index": b["index"], "side": b["side"],
                        "xs": b["xs"], "ys": b["ys"]} for b in bounds]}
    with open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
              "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def _score(out: dict):
    """择优得分:(内容核验数, -未检出列数, -格宽违例数)。结构失败 → (-1,-1,-1)。"""
    if not out.get("keep") or out.get("ok") is None:
        return (-1, -1, -1)
    ver = len(out.get("label_verify") or {})
    unwarn = sum(1 for w in out.get("warnings", []) if "内容未检出" in w)
    width = sum(1 for w in out.get("warnings", []) if "格宽" in w)
    return (ver, -unwarn, -width)


def select_map(stem: str) -> dict:
    """单一真源 line_parts(_分割线真段);track 链源已退役(EXPERIMENT.md 定案)。

    表头内容核验得分随账落盘。6a 列线集的双描/缺口(1019/1042)由同一把内容
    尺子裁决,不针对单图特判。
    """
    best = determine(stem)
    best["header_src"] = "line_parts"
    best["selection"] = {"line_parts": list(_score(best))}
    with open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
              "w", encoding="utf-8") as f:
        json.dump(best, f, ensure_ascii=False, indent=1)
    return best


def main():
    stems = sys.argv[1:] or sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    bad = 0
    for stem in stems:
        o = select_map(stem)
        names = [c["name"] for c in o["columns"]]
        bad += 0 if o.get("ok") else 1
        print(f"{stem}: [{o.get('header_src')}] sep={o['n_sep']} 保留={names}"
              f" 核验={len(o.get('label_verify') or {})}"
              f" {'OK' if o.get('ok') else '<<异常'} {o['warnings']}")
    print(f"--- {len(stems)} 张中 {len(stems)-bad} 张完全正常")


if __name__ == "__main__":
    main()
