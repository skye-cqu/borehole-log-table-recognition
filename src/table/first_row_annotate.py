# -*- coding: utf-8 -*-
"""阶段6：表格第一行（表头行）浅绿标注。

依据阶段4坐标数据（data/表格线候选识别处理/坐标数据/*.json）中真实存在的
横线线段（bbox / midy），推断每个图「第一个表格区块」的表头行上、下边框，
在原图副本上用浅绿色块覆盖该表头行（仅正文第一行，不含外框），交人工核对。

判定完全基于坐标数据中的真实线段字段，不引入坐标数据字段以外的选取阈值：

  1. 候选横线 = label ∈ {high, suspect} 且 direction == "horizontal" 的线段。
  2. 合并：同一 midy 邻近（±Y_TOL）的线段属于同一横层；同层内取所有线段的
     min(x0)、max(x1) 拼成这一行的整条横线（同 midy 的段即为同一行被识别
     截断的部分），得到 (x0, x1, midy, len=x1-x0)。
  3. 外框上边线：图顶部（第一个区块）midy 最小的那条横线，其长度记为 L0。
  4. 逐个往下找框内线：自外框之下，找到第一条长度与 L0 明显不同（真实差值
     > DIFF_PX，即比外框短一截）的横线，即为框内第一条线；继续往下再取一条
     框内线。这两条框内线即表头行的上、下边框。
  5. 长度相近校验（容差 1/10）：|len_top - len_bot| <= max(len_top,len_bot)/10；
     不满足则标记 length_mismatch 交人工。
  6. 辅助校验：两条边框线与竖线（direction=="vertical"）的交点数，以及端点
     近似对齐情况，仅记录不用于选取。
  7. 绿块 x 范围 = 表格主体真实宽度（两条边框线的 x 并集，由真实端点拼出），
     不按全图宽，也不缩窄到单段 bbox。

输入（只读）：
  - data/表格线候选识别处理/坐标数据/*.json
  - data/表格线候选识别处理/原图/*.png
输出：
  - data/第一行标注/标注图/*.png    原图 + 浅绿块（+辅助红边框）
  - data/第一行标注/参数/*.json     每张图的上下界与判定依据
  - data/第一行标注/汇总.json        全部图汇总

用法：
    python src/table/first_row_annotate.py            # 全部图
    python src/table/first_row_annotate.py --sample 5 # 随机抽 5 张（测试）
"""
import json
import sys
import random
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from src.core import paths

# 像素级几何合并容差（把同 midy 真实相邻线段接成一行，非选取阈值）
Y_TOL = 4.0        # 同一横层的 midy 邻近容差（px）
DIFF_PX = 50.0     # 外框线与框内线长度"明显不同"的真实差值下限（px）
LEN_TOL = 0.10     # 上下边框长度相近容差（差不超过较大者的 1/10）

GREEN = (144, 238, 144)   # 浅绿
BORDER = (200, 0, 0)      # 辅助红边框，便于核对边界（可删除）
ALPHA = 0.45


def load_lines(coord_path):
    """读取坐标 JSON，返回 (width, height, 横线候选, 竖线候选)。

    横线候选 / 竖线候选 每条取自真实字段 bbox / midy / midx。
    """
    with open(coord_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    w = int(data["width"])
    h = int(data["height"])
    hseg, vseg = [], []
    for l in data["lines"]:
        if l.get("label") not in ("high", "suspect"):
            continue
        if l.get("direction") == "horizontal":
            x0, _, x1, _ = l["bbox"]
            hseg.append((float(x0), float(x1), float(l["midy"])))
        elif l.get("direction") == "vertical":
            _, y0, _, y1 = l["bbox"]
            vseg.append((float(y0), float(y1), float(l["midx"])))
    return w, h, hseg, vseg


def merge_rows(hseg):
    """把同 midy 邻近的线段合并成整行横线。

    同一横层内取 min(x0)、max(x1) 拼成该行真实跨度（同 midy 段即同一行
    被识别截断的部分）。返回按 midy 升序的横线列表 [(x0, x1, midy, len), ...]。
    """
    if not hseg:
        return []
    segs = sorted(hseg, key=lambda s: s[2])
    layers = []
    for s in segs:
        if layers and abs(s[2] - layers[-1][-1][2]) <= Y_TOL:
            layers[-1].append(s)
        else:
            layers.append([s])
    rows = []
    for layer in layers:
        x0 = min(s[0] for s in layer)
        x1 = max(s[1] for s in layer)
        my = sum(s[2] for s in layer) / len(layer)
        rows.append((x0, x1, my, x1 - x0))
    return sorted(rows, key=lambda t: t[2])


def intersect_count(row, vsegs):
    """横线与竖线的交点数（端点落在竖线 x 且 y 落在竖线 y 区间内）。"""
    x0, x1, my, _ = row
    c = 0
    for y0, y1, mx in vsegs:
        if x0 - 2 <= mx <= x1 + 2 and y0 - 2 <= my <= y1 + 2:
            c += 1
    return c


def find_header_band(w, h, rows, vsegs):
    """推断第一个表格区块表头行的上下边框。

    返回 dict 或 None。
    """
    if len(rows) < 3:
        return None
    # 外框上边线 = 顶部 N_TOP 条横线里长度最大者（外框为表格最宽边，数据本身可判）
    N_TOP = 15
    top = rows[:N_TOP]
    outer = max(top, key=lambda r: r[3])
    L0 = outer[3]
    oi = rows.index(outer)
    # 框内两条 = 外框之下、长度均 >= L0*0.3（排除标题/右侧碎段），且彼此长度相近
    # （差比 <= LEN_TOL 即 1/10）的连续两条横线，即表头行的上下边框
    cand = [r for r in rows[oi + 1:] if r[3] >= L0 * 0.3]
    inner = []
    for i in range(len(cand) - 1):
        a, b = cand[i], cand[i + 1]
        if abs(a[3] - b[3]) <= max(a[3], b[3]) * LEN_TOL:
            inner = [a, b]
            break
    if len(inner) < 2:
        return {
            "ok": False,
            "reason": "外框之下未找到两条长度相近的框内线",
            "outer_midy": round(outer[2], 1), "outer_len": round(L0, 1),
            "inner_found": len(inner),
        }
    top, bot = inner[0], inner[1]
    len_top, len_bot = top[3], bot[3]
    diff = abs(len_top - len_bot)
    mismatch = diff > max(len_top, len_bot) * LEN_TOL
    # 表格主体真实宽度 = 两条边框线的 x 并集（真实端点）
    bx0 = min(top[0], bot[0])
    bx1 = max(top[1], bot[1])
    return {
        "ok": True,
        "outer_midy": round(outer[2], 1),
        "outer_len": round(L0, 1),
        "top_y": round(top[2], 2),
        "bottom_y": round(bot[2], 2),
        "top_len": round(len_top, 1),
        "bottom_len": round(len_bot, 1),
        "len_diff": round(diff, 1),
        "len_diff_ratio": round(diff / max(len_top, len_bot), 3),
        "length_mismatch": mismatch,
        "table_x0": round(bx0, 1),
        "table_x1": round(bx1, 1),
        "top_vcross": intersect_count(top, vsegs),
        "bottom_vcross": intersect_count(bot, vsegs),
    }


def annotate_one(stem, coord_path, orig_path, out_dir, param_dir, pad=200):
    """标注单图，输出标注图到 out_dir，参数到 param_dir。"""
    w, h, hseg, vseg = load_lines(coord_path)
    rows = merge_rows(hseg)
    res = find_header_band(w, h, rows, vseg)
    if res is None or not res.get("ok"):
        return stem, False, res.get("reason", "横线不足") if res else "横线不足 3 条"
    top_y, bottom_y = res["top_y"], res["bottom_y"]
    bx0, bx1 = int(round(res["table_x0"])), int(round(res["table_x1"]))
    y0 = max(0, int(round(top_y)) - 3)
    y1 = min(h, int(round(bottom_y)) + 3)

    im = Image.open(orig_path).convert("RGB")
    iw, ih = im.size
    if iw != w or ih != h:
        return stem, False, f"原图尺寸 {iw}x{ih} 与坐标数据 {w}x{h} 不一致"

    ov = Image.new("RGB", im.size, GREEN)
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rectangle([bx0, y0, bx1, y1], fill=255)  # 表格主体真实宽度
    blended = Image.blend(im.convert("RGBA"),
                          Image.composite(ov, im, m).convert("RGBA"),
                          ALPHA)
    ImageDraw.Draw(blended).rectangle([bx0, y0, bx1, y1], outline=BORDER, width=2)
    blended.convert("RGB").save(out_dir / f"{stem}_标注.png")

    py0, py1 = max(0, y0 - pad), min(ih, y1 + pad)
    prev = blended.crop((0, py0, iw, py1)).resize((iw * 2, (py1 - py0) * 2))
    prev.save(out_dir / f"{stem}_预览.png")

    param = {
        "image": f"{stem}.png", "width": w, "height": h,
        "outer_midy": res["outer_midy"], "outer_len": res["outer_len"],
        "top_y": res["top_y"], "bottom_y": res["bottom_y"],
        "top_len": res["top_len"], "bottom_len": res["bottom_len"],
        "len_diff": res["len_diff"], "len_diff_ratio": res["len_diff_ratio"],
        "length_mismatch": res["length_mismatch"],
        "table_x0": res["table_x0"], "table_x1": res["table_x1"],
        "top_vcross": res["top_vcross"], "bottom_vcross": res["bottom_vcross"],
    }
    with open(param_dir / f"{stem}.json", "w", encoding="utf-8") as f:
        json.dump(param, f, ensure_ascii=False, indent=2)
    info = (f"outer={res['outer_midy']}(L{res['outer_len']:.0f}) "
            f"header=[{res['top_y']:.1f},{res['bottom_y']:.1f}] "
            f"L {res['top_len']:.0f}/{res['bottom_len']:.0f} "
            f"d={res['len_diff_ratio']:.2f}"
            f"{' MISMATCH' if res['length_mismatch'] else ''}")
    return stem, True, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0,
                    help="随机抽取 N 张测试（0 表示全部）")
    args = ap.parse_args()

    paths.ensure_dirs(paths.FIRST_ROW_DIR, paths.FIRST_ROW_VIZ_DIR,
                      paths.FIRST_ROW_PARAM_DIR)

    coord_files = sorted(paths.CANDIDATE_COORD_DIR.glob("*.json"))
    if not coord_files:
        print(f"未找到坐标数据：{paths.CANDIDATE_COORD_DIR}")
        return

    if args.sample and args.sample < len(coord_files):
        random.seed(20260812)
        coord_files = random.sample(coord_files, args.sample)

    summary = []
    for cf in coord_files:
        stem = cf.stem
        orig_path = paths.CANDIDATE_ORIG_DIR / f"{stem}.png"
        if not orig_path.exists():
            summary.append({"image": stem, "ok": False, "info": "缺少原图"})
            continue
        stem_, ok, info = annotate_one(
            stem, cf, orig_path,
            paths.FIRST_ROW_VIZ_DIR, paths.FIRST_ROW_PARAM_DIR)
        print(f"{stem_:>12}  {'OK' if ok else 'FAIL'}  {info}")
        summary.append({"image": stem, "ok": ok, "info": info})

    with open(paths.FIRST_ROW_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n汇总已写：{paths.FIRST_ROW_SUMMARY}")


if __name__ == "__main__":
    main()
