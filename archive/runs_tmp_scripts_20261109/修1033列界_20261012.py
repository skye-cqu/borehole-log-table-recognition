# -*- coding: utf-8 -*-
"""1033 倾角/真厚列界缺陷修复(2026-10-12 抽验实锤):
列线阶段 k5R/k6L(倾角|真厚界)折线中段跳到真厚|砖界线,k6R 同期失稳 →
倾角带宽 139-179px(B 倾角列=真厚污染+补°洗白成假角度),真厚带塌成 18-43px(空/碎片)。
深度/层厚/采长带宽全程正常,不动。
修复:逐行墨迹检测三条竖界(strip 暗像素占比峰,自健康顶行连续性跟踪,窗口±18px),
破损行(墨迹界与 traced 折线差>8px)按新界重裁 → RapidOCR → decide 仲裁,
替换格一律 Agnes 复读双引擎一致才写,分歧/无墨清空记账(与修层号同标准)。
行界与现行整合表对齐:B 目录 data 过 drop_header_rows+unstuck_chain 重放(1033 无粘连 ops)。
倾角 col6 合并区仅前 23 行(健康区),破损行无合并冲突。

用法: python runs/tmp/修1033列界_20261012.py [--write]  (缺省 dry-run 只打印决策)
"""
import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from rapidocr_onnxruntime import RapidOCR  # noqa: E402

from src.core import paths  # noqa: E402
from src.table.era_chars import _load_inputs  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402
from src.table.rect_struct import strip_band  # noqa: E402
from src.table.finalize_tables import drop_header_rows, unstuck_chain  # noqa: E402
from src.table.delivery_gate import decide, cell_text  # noqa: E402

STEM = "钻孔柱状图1033"
X0, X1, WIN, TH = 600, 1000, 18, 0.55
AGNES_PROMPT = ("这是钻孔柱状图『{col}』列的一个格子。读出格内全部文字/数字,只输出读数;"
                "格内没有文字输出 EMPTY;有墨但无法辨认输出 UNKNOWN。不要其他内容。")


def peaks_at(gray, ym):
    strip = gray[int(ym) - 12:int(ym) + 12, X0:X1]
    frac = (strip < 150).mean(axis=0)
    out = []
    for x in range(2, len(frac) - 2):
        if frac[x] > TH and frac[x] == frac[x - 2:x + 3].max():
            out.append((X0 + x, float(frac[x])))
    merged = []
    for x, f in out:
        if merged and x - merged[-1][0] <= 3:
            if f > merged[-1][1]:
                merged[-1] = (x, f)
        else:
            merged.append((x, f))
    return merged


def track(gray, ys, sp_l, sp_m, sp_r):
    """三界逐行跟踪:自顶行 traced 位置锚定,逐行取窗口内最优墨迹峰。"""
    n = len(ys) - 1
    prev = [float(np.interp((ys[0] + ys[1]) / 2, sp["ys"], sp["xs"])) for sp in (sp_l, sp_m, sp_r)]
    miss = [0, 0, 0]
    res = [None] * n
    for i in range(n):
        ym = (ys[i] + ys[i + 1]) / 2
        pk = peaks_at(gray, ym)
        cur = list(prev)
        for b in range(3):
            cand = [(f, -abs(x - prev[b]), x) for x, f in pk if abs(x - prev[b]) <= WIN]
            if cand:
                cur[b] = max(cand)[2]
                miss[b] = 0
            else:
                miss[b] += 1               # 无峰:冻结在前值(漂移~1.3px/行)
        ok = 55 <= cur[1] - cur[0] <= 115 and 50 <= cur[2] - cur[1] <= 115
        res[i] = (tuple(cur), ok, ym)
        if ok:
            prev = cur
    return res


def ndip(s):
    s = str(s).strip().replace(" ", "")
    if s.endswith("°"):
        s = s[:-1] + "°"
    if re.fullmatch(r"\d+(\.\d+)?", s):
        s += "°"
    return s


def fnum(s):
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(" ", ""))
    return float(m.group()) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--px-only", action="store_true",
                    help="纯像素仲裁,不调 Agnes(快速验证边界/读数;与重出批次并行时防限流)")
    args = ap.parse_args()
    from src.table import agnes_post
    ocr = RapidOCR()

    hm, rd = _load_inputs(STEM)
    kp, seps = hm["keep"], hm["sep_pts"]
    x_mid_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_mid_tbl) >= hm["band"][1]]
    x_era = sum(kp[0]["x_in_band"]) / 2
    ys = [row_y(r, x_era) for r in rows_r]
    bwb = load_workbook(paths.REEMIT_DIR_20261005B / f"{STEM}_还原.xlsx")
    bdata = list(bwb.active.iter_rows(values_only=True))
    bdata, ys, _ = drop_header_rows(bdata, ys)
    bdata, ys, _, _ = unstuck_chain(bdata, ys)
    assert len(ys) - 1 == 80, len(ys)

    gray = cv2.imread(str(paths.RAW_DIR / f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
    sp_l, sp_m, sp_r = (seps[kp[5]["left_sep"]], seps[kp[5]["right_sep"]], seps[kp[6]["right_sep"]])
    trk = track(gray, ys, sp_l, sp_m, sp_r)

    # 假行: 行界双检线退化区间(ys[i+1]<=ys[i]+3),该 xlsx 行须删,描述归还上行。
    # 手术后 xlsx 少一行 → i>=fake_i 的映射 xr=i+1(重入对齐)。
    fake_i = next((i for i in range(len(ys) - 1) if ys[i + 1] <= ys[i] + 3), None)
    p = paths.FINALIZE_FULL_DIR / f"{STEM}_整合.xlsx"
    wb0 = load_workbook(p)
    n_x = wb0.active.max_row - 1
    shift = 0
    if fake_i is not None and n_x == len(ys) - 2:
        shift = 1                                # 手术已完成,跳过
    elif n_x != len(ys) - 1:
        raise SystemExit(f"行数不符 xlsx={n_x} replay={len(ys) - 1},拒改")
    wb = load_workbook(p, rich_text=True)
    ws = wb.active

    def xr_of(i):
        return i + 2 - shift if (shift and fake_i is not None and i > fake_i) else i + 2

    broken = []
    for i, (b, ok, ym) in enumerate(trk):
        if shift and fake_i is not None and i == fake_i:
            continue                             # 假行已删,跳过
        (L, M, R), ok, ym = trk[i]
        d_m = abs(M - float(np.interp(ym, sp_m["ys"], sp_m["xs"])))
        d_r = abs(R - float(np.interp(ym, sp_r["ys"], sp_r["xs"])))
        if not ok or d_m > 8 or d_r > 8:
            broken.append(i)
    print(f"破损行(0基): {len(broken)} 行, 首末 {broken[0] if broken else '-'}..{broken[-1] if broken else '-'},"
          f" 跟踪失败行: {sum(1 for _, ok, _ in trk if not ok)}, 假行 i={fake_i} shift={shift}")

    changes, stats = [], {"替换": 0, "清空": 0, "无墨": 0}
    for i in broken:
        (L, M, R), ok, ym = trk[i]
        y0, y1 = int(ys[i]) + 2, max(int(ys[i + 1]) - 2, int(ys[i]) + 6)   # 退化区间钳制
        bands = {}
        for col, xl, xr_, tag in ((6, L, M, "倾角"), (7, M, R, "真厚")):
            _, band, _ = strip_band(gray, y0, y1,
                                    (np.array([y0, y1], float), np.array([xl, xl], float)),
                                    (np.array([y0, y1], float), np.array([xr_, xr_], float)),
                                    inset=2)
            bands[col] = band
            res, _ = ocr(band)
            px = "".join(x[1] for x in (res or [])).strip()
            cur = cell_text(ws.cell(row=xr_of(i), column=col).value).strip()
            ag = None
            act, new, basis = decide(px, None, col)
            if args.px_only:
                pass
            elif act == "清空" and basis != "格内无墨":
                big = cv2.resize(band, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                _, jpeg = cv2.imencode(".jpg", big, [cv2.IMWRITE_JPEG_QUALITY, 90])
                try:
                    ag = agnes_post.ask(AGNES_PROMPT.format(col=tag), image_jpeg=jpeg.tobytes(),
                                        max_tokens=4096).strip().strip('"')
                except Exception:
                    ag = None
                act, new, basis = decide(px, ag, col)
            if act == "替换":
                # 语义守卫:倾角≤90°;真厚≤层厚×1.05(本图竖孔,真厚略小于层厚,
                # 健康行实证 1.43/1.41、5.99/5.92)。超限=读数串它列,清空记账。
                try:
                    fv = float(new)
                except (TypeError, ValueError):
                    fv = None
                if col == 6 and fv is not None and fv > 90:
                    act, new, basis = "清空", None, f"倾角{new}>90°,清空记账"
                elif col == 7 and fv is not None:
                    tc = ws.cell(row=xr_of(i), column=4).value
                    try:
                        tcv = float(str(tc))
                    except (TypeError, ValueError):
                        tcv = None
                    if tcv is not None and fv > tcv * 1.05 + 0.05:
                        act, new, basis = "清空", None, \
                            f"真厚{new}>层厚{tcv},清空记账"
            if act == "替换" and not args.px_only:
                # 替换格一律双引擎一致才落
                big = cv2.resize(band, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                _, jpeg = cv2.imencode(".jpg", big, [cv2.IMWRITE_JPEG_QUALITY, 90])
                try:
                    ag2 = agnes_post.ask(AGNES_PROMPT.format(col=tag), image_jpeg=jpeg.tobytes(),
                                         max_tokens=4096).strip().strip('"')
                except Exception:
                    ag2 = None
                same = (ndip(ag2) == ndip(new)) if col == 6 else \
                    (fnum(ag2) is not None and fnum(new) is not None
                     and abs(fnum(ag2) - fnum(new)) < 1e-6)
                if not same:
                    act, new = "清空", None
                    basis = f"双引擎分歧(像素[{px[:12]}]/Agnes[{str(ag2)[:12]}]),清空记账"
                    cv2.imwrite(str(ROOT / f"runs/tmp/1033复核_x{xr_of(i)}_c{col}.png"),
                                cv2.resize(band, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC))
                else:
                    basis += f"/Agnes一致[{ag2}]"
            ev = basis + (f"/像素[{px[:12]}]" if px else "/无墨") + \
                (f"/Agnes[{str(ag)[:12]}]" if ag and ag != ag2 else "")
            if act == "替换":
                stats["替换"] += 1
            elif basis == "格内无墨":
                stats["无墨"] += 1
            else:
                stats["清空"] += 1
            newv = None
            if act == "替换":
                newv = new if col == 6 else float(new)
            changes.append((xr_of(i), col, cur, newv, ev, f"[{xl:.0f},{xr_:.0f}]px"))
        print(f"行{xr_of(i)}: 界[{L:.0f},{M:.0f},{R:.0f}]",
              " | ".join(f"{t}:{c!r}→{ch[3]!r} {ch[4][:46]}"
                         for (xr_, col_, c, _n, _e, _b), ch, t in
                         [(changes[-2], changes[-2], "倾角"), (changes[-1], changes[-1], "真厚")]))
    print("统计:", stats)
    if not args.write:
        print("(dry-run,未写入;加 --write 落盘)")
        return
    for xr, col, _old, newv, _ev, _b in changes:
        ws.cell(row=xr, column=col).value = newv      # openpyxl 清空必须 .value 赋值
    surg = 0
    if shift == 0 and fake_i is not None:
        # 假行手术:无深度/层厚、仅有泄漏值+上行描述 → 描述归还上行,整行删除。
        # 实证:裁片 眼验_1033_假行描述归属.png(泥质粉砂岩在物理行B内,无芯在行C);
        # 深度链 402.19+2.15(行B层厚)→402.19,402.19+5.99=408.18 闭合,假行多余。
        fxr = fake_i + 2
        d, t = ws.cell(row=fxr, column=3).value, ws.cell(row=fxr, column=4).value
        desc = ws.cell(row=fxr, column=8).value
        tgt = ws.cell(row=fxr - 1, column=8).value
        if (d in (None, "") and t in (None, "") and cell_text(desc).strip()
                and not cell_text(tgt).strip()):
            ws.cell(row=fxr - 1, column=8).value = desc
            # 合并区显式拆-删-重建(openpyxl delete_rows 不保证移动合并区;
            # A48:A78 时代 span 横跨假行,必须处理)
            saved = [(r.min_row, r.min_col, r.max_row, r.max_col)
                     for r in ws.merged_cells.ranges if r.max_row >= fxr]
            for r0, c0, r1, c1 in saved:
                ws.unmerge_cells(start_row=r0, start_column=c0, end_row=r1, end_column=c1)
            ws.delete_rows(fxr, 1)
            for r0, c0, r1, c1 in saved:
                ws.merge_cells(start_row=(r0 if r0 < fxr else r0 - 1), start_column=c0,
                               end_row=r1 - 1, end_column=c1)
            surg = 1
            print(f"假行手术: xlsx{fxr} 描述→{fxr - 1},整行删除,合并区重建{len(saved)}个")
    wb.save(p)
    csvp = paths.FINALIZE_FULL_DIR / f"{STEM}_校正账.csv"
    rows = list(csv.DictReader(open(csvp, encoding="utf-8-sig")))
    touched = {(xr, col) for xr, col, *_ in changes}

    # 幂等:同(行,列)旧"像素仲裁"条目先清
    def key(r):
        try:
            return (int(r["行"]) + 2, {"倾角": 6, "真厚": 7}.get(r["列"], -1))
        except (ValueError, KeyError):
            return None
    rows = [r for r in rows if not (r["来源"] == "像素仲裁" and key(r) in touched)]
    fxr = (fake_i + 2) if (surg and fake_i is not None) else None
    for xr, col, old, newv, ev, bd in changes:
        di = xr - 3 if (fxr and xr > fxr) else xr - 2   # 假行删除后上方行号-1
        rows.append({"行": di, "列": {6: "倾角", 7: "真厚"}[col], "原": str(old)[:60],
                     "新": str(newv or "")[:60], "依据": f"列界墨迹重提{bd}:{ev}"[:80],
                     "来源": "像素仲裁", "应用": 1})
    if surg:
        rows.append({"行": fake_i - 1, "列": "岩性描述",
                     "原": "", "新": cell_text(ws.cell(row=fake_i + 1, column=8).value)[:60],
                     "依据": "假行描述归还上行(物理行B,裁片实证)", "来源": "假行归并", "应用": 1})
        rows.append({"行": fake_i, "列": "整行", "原": "泄漏倾角2.12°+描述", "新": "(整行删除)",
                     "依据": "行界17011/17012双检线退化区间,深度链402.19+5.99=408.18闭合,无此物理行",
                     "来源": "假行归并", "应用": 1})
    with open(csvp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["行", "列", "原", "新", "依据", "来源", "应用"])
        w.writeheader()
        w.writerows(rows)
    print("写入", len(changes), "格;账", csvp)


if __name__ == "__main__":
    main()
