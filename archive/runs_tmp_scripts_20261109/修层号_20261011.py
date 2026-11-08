# -*- coding: utf-8 -*-
"""修复煤层/标志层号列乱码(用户 2026-10-11):字母/乱码/串行值不该出现在层号列。

证据链(每格):
1. 像素直查格内墨:RapidOCR 读数;格内无墨 → 清空(B 目录幻读,客观事实);
2. 像素读数为合法层号(数字/汉字数字/上下分层)→ Agnes 视觉复读同格,
   双引擎一致才替换(RapidOCR 复读自己不算独立证据);分歧 → 清空(乱码不留,账留痕);
3. 像素读数非层号(表头/别列串墨)→ 清空。
1032 整图 B 目录列错位(登记专项)、1019 旧版映射 → 整图跳过。
修复写入整合 xlsx + 校正账 CSV 追加。用法: python runs/tmp/修层号_20261011.py
"""
import json
import re
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import cv2  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from src.core import paths  # noqa: E402
from src.table.era_chars import _load_inputs  # noqa: E402
from src.table.track_rows import row_y  # noqa: E402
from src.table.rect_struct import strip_band  # noqa: E402
from rapidocr_onnxruntime import RapidOCR  # noqa: E402

LEGAL = re.compile(r"^[0-9]+$|^[一二三四五六七八九十]+$|^[一二三四五六七八九十]\s*[上下]$"
                   r"|^十[一二三四五]$|^[0-9]+[上下]$")
AGNES_PROMPT = ("这是钻孔柱状图『煤层/标志层号』列的一个格子(竖排或单个编号,可能是汉字数字"
                "如 三上/七/十一,或阿拉伯数字)。只输出格内编号;格内没有文字输出 EMPTY;"
                "有文字但不是层号编号输出 UNKNOWN。不要其他内容。")


def is_bad(s):
    return not LEGAL.fullmatch(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    args = ap.parse_args()
    from src.table import agnes_post
    ocr = RapidOCR()
    stats = {"清空": 0, "替换": 0, "分歧清空": 0, "跳过图": []}
    for k in range(1015, 1045):
        if args.only is not None and k != args.only:
            continue
        stem = f"钻孔柱状图{k}"
        p = paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx"
        if not p.exists():
            continue
        hm, rd = _load_inputs(stem)
        if "sep_pts" not in hm or k == 1032:
            stats["跳过图"].append(k)
            continue
        x_mid = sum(rd["table_x"]) / 2
        rr = [r for r in rd["rows"] if row_y(r, x_mid) >= hm["band"][1]]
        kd = hm["keep"][1]
        sp_l = hm["sep_pts"][kd["left_sep"]]
        sp_r = hm["sep_pts"][kd["right_sep"]]
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        wb = load_workbook(p)
        ws = wb.active
        changes = []
        for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True)):
            v = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
            if not v or not is_bad(v) or i + 1 >= len(rr):
                continue
            y0, y1 = int(row_y(rr[i], x_mid)), int(row_y(rr[i + 1], x_mid))
            _, band, _ = strip_band(gray, y0 + 2, y1 - 2, (sp_l["ys"], sp_l["xs"]),
                                    (sp_r["ys"], sp_r["xs"]), inset=2)
            res, _ = ocr(band)
            px = "".join(x[1] for x in (res or [])).replace(" ", "")
            new, basis = None, None
            if not px:
                new, basis = "", "格内无墨(B目录幻读),清空"
            elif LEGAL.fullmatch(px):
                # 第二引擎:Agnes 视觉复读,一致才替换
                big = cv2.resize(band, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                ok, jpeg = cv2.imencode(".jpg", big, [cv2.IMWRITE_JPEG_QUALITY, 90])
                try:
                    ag = agnes_post.ask(AGNES_PROMPT, image_jpeg=jpeg.tobytes(),
                                        max_tokens=4096).strip().strip('"')
                except Exception as e:
                    ag = f"ERR"
                ag_n = ag.replace(" ", "")
                if ag_n == px or ag_n.replace("上", "").replace("下", "") == px.replace("上", "").replace("下", ""):
                    new, basis = px, f"像素+Agnes双引擎一致读[{px}],替换乱码"
                else:
                    new, basis = "", f"双引擎分歧(像素[{px}]/Agnes[{ag[:12]}]),乱码清空待人工"
            else:
                new, basis = "", f"像素读数[{px[:12]}]非层号(疑串墨),清空"
            changes.append((i + 2, v, new, basis))
        if not changes:
            continue
        for row_i, old, new, basis in changes:
            # openpyxl 的 cell(value=None) 是跳过赋值而非清空,必须直接 .value 赋值
            ws.cell(row=row_i, column=2).value = new if new else None
        wb.save(p)
        import csv
        csvp = paths.FINALIZE_FULL_DIR / f"{stem}_校正账.csv"
        rows = list(csv.DictReader(open(csvp, encoding="utf-8-sig")))
        touched = {row_i - 2 for row_i, *_ in changes}
        # 幂等:本次涉及行的旧"像素+Agnes"条目(含未生效假账)先清再追加
        rows = [r for r in rows if not (r["列"] == "煤层/标志层号"
                                        and r["来源"] == "像素+Agnes"
                                        and int(r["行"]) in touched)]
        for row_i, old, new, basis in changes:
            rows.append({"行": row_i - 2, "列": "煤层/标志层号", "原": old,
                         "新": new, "依据": basis[:60], "来源": "像素+Agnes", "应用": 1})
            stats["替换" if new else ("分歧清空" if "分歧" in basis else "清空")] += 1
        with open(csvp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["行", "列", "原", "新", "依据", "来源", "应用"])
            w.writeheader()
            w.writerows(rows)
        print(stem, "修", len(changes), "格")
    print("统计:", stats)


if __name__ == "__main__":
    main()
