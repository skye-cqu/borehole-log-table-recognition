# -*- coding: utf-8 -*-
"""清交付门禁违规(符号幻读+粘连专项):像素 strip_band 裁格→RapidOCR→decide 仲裁
→像素非法时 Agnes 第二引擎复读。逐格证据链入校正账(来源=像素仲裁,幂等:
同(行,列)旧"像素仲裁"条目先清再追加)。错位专项(1019/1032/1042)不在此处理,
整图降级见交付说明。裁格 y 界与现行整合 xlsx 行对齐:B 目录 data 过
drop_header_rows+unstuck_chain(与 finalize 同函数同序)得每产出行界序列,
行手术图(1030/1035/1037/重出8图)不漂移。

用法: python runs/tmp/清违规_20261011.py [--only N]   (先跑 delivery_gate 刷新报告)
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import cv2  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from rapidocr_onnxruntime import RapidOCR  # noqa: E402

from src.core import paths  # noqa: E402
from src.table.era_chars import _load_inputs  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402
from src.table.rect_struct import strip_band  # noqa: E402
from src.table.finalize_tables import drop_header_rows, unstuck_chain  # noqa: E402
from src.table.delivery_gate import decide, COLS, cell_text  # noqa: E402

AGNES_PROMPT = ("这是钻孔柱状图『{col}』列的一个格子。读出格内全部文字/数字,只输出读数;"
                "格内没有文字输出 EMPTY;有墨但无法辨认输出 UNKNOWN。不要其他内容。")
NUMERIC_COLS = {3, 4, 5, 7}          # 深度/层厚/采长/真厚写 float,与列内类型一致


def typed(col, v):
    if v is None:
        return None
    if col in NUMERIC_COLS:
        try:
            return float(v)
        except ValueError:
            return v
    return v


def row_bounds(stem):
    """现行整合 xlsx 每数据行的 y 界 + 列界折线(与 finalize 行手术逻辑同步重放)。"""
    hm, rd = _load_inputs(stem)
    x_mid_tbl = sum(rd["table_x"]) / 2
    rows_r = [r for r in rd["rows"] if row_y(r, x_mid_tbl) >= hm["band"][1]]
    x_era = sum(hm["keep"][0]["x_in_band"]) / 2
    ys = [row_y(r, x_era) for r in rows_r]
    wb = load_workbook(paths.REEMIT_DIR_20261005B / f"{stem}_还原.xlsx")
    data = list(wb.active.iter_rows(values_only=True))
    data, ys, _ = drop_header_rows(data, ys)
    data, ys, _, _ = unstuck_chain(data, ys)
    return ys, hm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    args = ap.parse_args()
    from src.table import agnes_post
    ocr = RapidOCR()
    rep = json.loads((paths.FINALIZE_FULL_DIR / "交付门禁_报告.json").read_text(encoding="utf-8"))
    by_chart = {}
    for it in rep["符号幻读"] + rep["粘连专项"]:
        k = int(re.sub(r"\D", "", it["图"]))
        if args.only is None or k == args.only:
            by_chart.setdefault(it["图"], []).append(it)
    stats = {"替换": 0, "Agnes替换": 0, "清空": 0, "失配": 0, "跳过图": []}
    for stem, lst in sorted(by_chart.items()):
        p = paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx"
        hm = None
        try:
            ys, hm = row_bounds(stem)
        except Exception as e:
            stats["跳过图"].append(f"{stem}:{str(e)[:30]}")
            continue
        if "sep_pts" not in hm:
            stats["跳过图"].append(f"{stem}:无sep_pts")
            continue
        seps, keep = hm["sep_pts"], hm["keep"]
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        wb = load_workbook(p, rich_text=True)
        ws = wb.active
        changes = []
        for it in lst:
            xr, col = it["行"], COLS.index(it["列"]) + 1
            i = xr - 2
            if i < 0 or i + 1 >= len(ys):
                continue
            cur = cell_text(ws.cell(row=xr, column=col).value).strip()
            if cur[:40] != it["值"]:            # 报告过期(重出后该格已变),留给下轮 gate
                stats["失配"] += 1
                continue
            kp = keep[col - 1]
            L, R = seps[kp["left_sep"]], seps[kp["right_sep"]]
            _, band, _ = strip_band(gray, int(ys[i]) + 2, int(ys[i + 1]) - 2,
                                    (L["ys"], L["xs"]), (R["ys"], R["xs"]), inset=2)
            res, _ = ocr(band)
            px = "".join(x[1] for x in (res or [])).strip()
            ag = None
            act, new, basis = decide(px, None, col)
            if act == "清空" and basis != "格内无墨":      # 像素读而非法→第二引擎
                big = cv2.resize(band, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                ok2, jpeg = cv2.imencode(".jpg", big, [cv2.IMWRITE_JPEG_QUALITY, 90])
                try:
                    ag = agnes_post.ask(AGNES_PROMPT.format(col=it["列"]),
                                        image_jpeg=jpeg.tobytes(),
                                        max_tokens=4096).strip().strip('"')
                except Exception:
                    ag = None
                act, new, basis = decide(px, ag, col)
            ev = basis + (f"/像素[{px[:12]}]" if px else "/无墨") + \
                (f"/Agnes[{str(ag)[:12]}]" if ag else "")
            changes.append((xr, col, cur, typed(col, new), ev))
            if basis == "像素非法,Agnes读数合法":
                stats["Agnes替换"] += 1
            elif act == "替换":
                stats["替换"] += 1
            else:
                stats["清空"] += 1
        if not changes:
            continue
        for xr, col, _old, newv, _ev in changes:
            # openpyxl 的 cell(value=None) 是跳过赋值而非清空,必须 .value 直接赋
            ws.cell(row=xr, column=col).value = newv
        wb.save(p)
        csvp = paths.FINALIZE_FULL_DIR / f"{stem}_校正账.csv"
        rows = list(csv.DictReader(open(csvp, encoding="utf-8-sig")))
        touched = {(xr, col) for xr, col, *_ in changes}
        # 幂等:同(行,列)旧"像素仲裁"条目先清
        keep_rows = []
        for r in rows:
            try:
                key = (int(r["行"]) + 2, COLS.index(r["列"]) + 1)
            except (ValueError, KeyError):
                keep_rows.append(r)
                continue
            if r["来源"] == "像素仲裁" and key in touched:
                continue
            keep_rows.append(r)
        for xr, col, old, newv, ev in changes:
            keep_rows.append({"行": xr - 2, "列": COLS[col - 1], "原": str(old)[:60],
                              "新": str(newv or "")[:60], "依据": ev[:60],
                              "来源": "像素仲裁", "应用": 1})
        with open(csvp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["行", "列", "原", "新", "依据", "来源", "应用"])
            w.writeheader()
            w.writerows(keep_rows)
        print(stem, "处理", len(changes), "格")
    print("统计:", stats)


if __name__ == "__main__":
    main()
