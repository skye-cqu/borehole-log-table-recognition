# -*- coding: utf-8 -*-
"""run5 v2(v4 几何):分裂判读包重裁——多边形裁剪,边界=阶段5 行线折线真值。

缺陷(v1):row_ivs 是行线折线在 desc 列中点 x 的单点采样(align_score._row_ivs),
水平带假设;框线斜/弯 ±5-36px,窗内混邻行字头/切本行笔画(1017_行43 实证,
用户指出"不贴合框线不可能识别准确")。
修法(用户定案:裁剪成多边形,不拉伸):行边界折线取阶段5 行判定 rows[i].poly
(与交付 xlsx 同链,零自测),desc 列 x 范围内逐 x 取 row_y(rec,x),沿 top(x)/
bot(x) 折线围四边形掩码,掩码内=原图墨迹原样,掩码外填白。
手术对齐:drop_header_rows 随剔;unstuck_chain 的 over 不动边界、split 在
src 插 n-1 个虚拟边界(取 ivs 均分值退化平线)、drop 删边界;src 长度校验
不过的图整图回退 ivs 标量窗并登记。
只作判读裁片,不动结构管线。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

from src.core import paths
from src.handwriting.reread import ROLE_KEEP

SRC = paths.AUTORESEARCH_DIR / "多源定级_20261106" / "分裂判读包_20261109"
DST = paths.AUTORESEARCH_DIR / "多源定级_20261106" / "分裂判读包_20261109_v2"
INSET = 3          # 框线内缩,线本身不进窗
STEP = 8           # 折线采样步长 px


def row_ivs_stem(stem):
    """行区间重放(与 align_score._row_ivs 同参),并保留每条边界线的来源:
    rec(含 poly 折线)=真实行线;None=手术虚拟边界(取 ivs 均分值)。

    返回 ({k: (top_src, bot_src)}, {k: (y0, y1)});src 长度校验不过返回 ({}, ivs)。
    """
    import csv
    from openpyxl import load_workbook
    from src.table.era_chars import _load_inputs
    from src.table.track_rows import row_y
    from src.table.finalize_tables import column_roles, drop_header_rows, unstuck_chain
    hm, rd = _load_inputs(stem)
    x_mid_tbl = sum(rd["table_x"]) / 2
    rr = [r for r in rd["rows"] if row_y(r, x_mid_tbl) >= hm["band"][1]]
    bwb = load_workbook(paths.REEMIT_DIR_20261023 / f"{stem}_还原.xlsx")
    bdata = [tuple(r)[:8] + (None,) * max(0, 8 - len(r))
             for r in bwb.active.iter_rows(values_only=True)]
    bdata, rr, _ = drop_header_rows(bdata, rr)
    bdata, ys, ops, _ledger = unstuck_chain(bdata, [r["y_at_mid"] for r in rr],
                                            column_roles(bdata[0] if bdata else []))
    while bdata and not any(v is not None and str(v).strip() for v in (bdata[-1] or ())):
        bdata.pop()
        ys.pop()
    surg = set()
    csvp = paths.FINALIZE_FULL_DIR / f"{stem}_校正账.csv"
    if csvp.exists():
        for r in csv.DictReader(open(csvp, encoding="utf-8-sig")):
            if r.get("来源") == "假行归并" and r.get("列") == "整行":
                try:
                    surg.add(int(r["行"]))
                except ValueError:
                    pass
    kept = [i for i in range(len(ys) - 1) if i not in surg]
    ivs = {k: (ys[i], ys[i + 1]) for k, i in enumerate(kept)}
    # src 同步:over 不动;split xlsx_row=r 在 i=r-2 后插 n-1 个 None;drop 删 i
    src = list(rr)
    for op in sorted(ops, key=lambda o: -o[1]):
        kind, r = op[0], op[1]
        i = r - 2
        if kind == "split":
            n = len(op[2]) + 1
            if 0 <= i < len(src):
                src[i + 1:i + 1] = [None] * (n - 1)
        elif kind == "drop":
            if 0 <= i < len(src):
                src.pop(i)
    if len(src) != len(ys):
        return {}, ivs          # 对齐失败:整图回退标量窗
    top_bot = {}
    for k, i in enumerate(kept):
        t, b = src[i], src[i + 1]
        top_bot[k] = (t, b)
    return top_bot, ivs


def poly_ys(src, xs, fallback):
    """边界在 xs 各处的 y:rec=折线取值(row_y 同口径);None=ivs 均分平线。"""
    if src is None:
        return np.full(len(xs), float(fallback))
    from src.table.track_rows import row_y
    return np.array([row_y(src, float(x)) for x in xs], float)


def _crop(gray, x0, x1, top_src, top_fb, bot_src, bot_fb, pad):
    xs = np.arange(x0, x1, STEP, dtype=float)
    if xs[-1] != x1 - 1:
        xs = np.append(xs, x1 - 1)
    ya = poly_ys(top_src, xs, top_fb)
    yb = poly_ys(bot_src, xs, bot_fb)
    if pad:
        h = float(np.median(yb - ya))
        ya, yb = ya - pad, yb + pad
    ins = 0 if pad else INSET
    ya_i = np.clip(np.round(ya).astype(int) + ins, 0, gray.shape[0] - 1)
    yb_i = np.clip(np.round(yb).astype(int) - ins, 0, gray.shape[0] - 1)
    y_top = int(ya_i.min()) - 2
    y_bot = int(yb_i.max()) + 3
    H = y_bot - y_top
    win = np.full((H, x1 - x0), 255, np.uint8)
    band = gray[max(0, y_top):y_bot, x0:x1]
    win[:band.shape[0], :band.shape[1]] = band
    xi = np.clip(np.round(xs - x0).astype(int), 0, x1 - x0 - 1)
    pts = np.concatenate([
        np.stack([xi, ya_i - y_top], axis=1),
        np.stack([xi[::-1], yb_i[::-1] - y_top], axis=1),
    ]).astype(np.int32)
    mask = np.zeros((H, x1 - x0), np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    win[mask == 0] = 255
    return win


def build(gray, x0, x1, top_src, top_fb, bot_src, bot_fb):
    ya0 = poly_ys(top_src, np.arange(x0, x1, STEP, float), top_fb)
    yb0 = poly_ys(bot_src, np.arange(x0, x1, STEP, float), bot_fb)
    # 守卫:折线带高与 ivs 带高偏差超限=手术行 src 错位(1027_行101 实证),
    # 整格回退 ivs 标量窗
    h_ivs = float(bot_fb) - float(top_fb)
    h_poly = float(np.median(yb0 - ya0))
    if abs(h_poly - h_ivs) > max(30.0, 0.4 * h_ivs) or h_poly < 10:
        top_src = bot_src = None
    cell = _crop(gray, x0, x1, top_src, top_fb, bot_src, bot_fb, pad=0.0)
    ya0 = poly_ys(top_src, np.arange(x0, x1, STEP, float), top_fb)
    yb0 = poly_ys(bot_src, np.arange(x0, x1, STEP, float), bot_fb)
    h = float(np.median(yb0 - ya0))
    strip = _crop(gray, x0, x1, top_src, top_fb, bot_src, bot_fb, pad=0.55 * h)
    return cell, strip


def main():
    DST.mkdir(parents=True, exist_ok=True)
    n = n_fallback = n_fail = 0
    fallback_stems = []
    cache = {}
    for b in range(16):
        f = SRC / f"分派_分裂_{b}.json"
        if not f.exists():
            continue
        items = json.loads(f.read_text(encoding="utf-8"))
        for e in items:
            tag = e["tag"]
            stem, row = tag.rsplit("_行", 1)
            stem = "钻孔柱状图" + stem
            r = int(row)
            if stem not in cache:
                cache[stem] = row_ivs_stem(stem)
            top_bot, ivs = cache[stem]
            if r - 2 not in ivs:
                print("跳过(无重放行):", tag)
                continue
            y0, y1 = ivs[r - 2]
            if r - 2 in top_bot:
                top_src, bot_src = top_bot[r - 2]
            else:                       # 校正账手术行:整行回退标量
                top_src = bot_src = None
                n_fallback += 1
            hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                                f"{stem}_表头映射.json", encoding="utf-8"))
            keep = None
            for k in hm["keep"]:
                if k["name"] == ROLE_KEEP["desc"]:
                    keep = sorted(k["x_in_band"])
            if not keep:
                print("跳过(无desc列):", tag)
                continue
            gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"),
                              cv2.IMREAD_GRAYSCALE)
            H, W = gray.shape[:2]
            x0 = max(0, int(keep[0]) - 8)
            x1 = min(W, int(keep[1]) + 8)
            try:
                cell, strip = build(gray, x0, x1, top_src, y0, bot_src, y1)
            except Exception as ex:
                print(f"失败 {tag}: {type(ex).__name__} {ex}", flush=True)
                n_fail += 1
                continue
            cv2.imwrite(str(DST / f"{tag}_cell.png"), cell)
            cv2.imwrite(str(DST / f"{tag}_strip.png"), strip)
            n += 1
        (DST / f"分派_分裂_{b}.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"v2 重裁(v4 折线几何): {n} 格(标量回退 {n_fallback},失败 {n_fail})"
          f" -> {DST.relative_to(paths.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
