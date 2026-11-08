# -*- coding: utf-8 -*-
"""run6:desc 列读器(用户指引)——整列大窗一次多行识别+按行线折线归行。

动因:逐格裁窗受几何风险(切字/截字/邻行污染)困扰(run5 实证);desc 列
文字多、框线结构清晰,适合整段大窗一次 OCR,行归属交给行线折线。
列读=RapidOCR 家族新窗(与 tight/loose/montage 同引擎同族),并入 B 族
增强票数、救读数不足行;归行=run5 同款 rows[i].poly 折线(交付同链)。

分段:每 ~SEG 行一段(段界=行线处,保证行完整),OCR→box 按 y 中心
落入 [top(xc)+2, bot(xc)-2] 归行,行内按 x 排序拼接。
输出 paths.AUTORESEARCH_DIR/colreads.json:{stem: {"行N": read}}(xlsx 行号)。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

import cv2
import numpy as np

from src.core import paths
from src.handwriting.reread import ROLE_KEEP, _ocr
from src.table.track_rows import row_y

SEG = 30            # 每段行数
OUT = paths.AUTORESEARCH_DIR / "colreads.json"

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\tmp")
from run5_pkg_v2 import row_ivs_stem   # noqa: E402  (全行 (top_src,bot_src)+ivs)


def stem_list():
    return sorted(p.name[: -len("_整合.xlsx")]
                  for p in paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx"))


def read_stem(ocr, stem, keep, top_bot, ivs):
    hm_keep = keep
    x0, x1 = int(hm_keep[0]) - 8, int(hm_keep[1]) + 8
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    H = gray.shape[0]
    ks = sorted(k for k in ivs if k in top_bot)
    ev = {}
    for s in range(0, len(ks), SEG):
        chunk = ks[s:s + SEG]
        # 段窗:chunk 各行上下界的外包络(逐 x 折线取 min/max 近似用中点)
        ys_top, ys_bot = [], []
        for k in chunk:
            t, b = top_bot[k]
            xc = (x0 + x1) / 2
            ys_top.append(row_y(t, xc) if t is not None else ivs[k][0])
            ys_bot.append(row_y(b, xc) if b is not None else ivs[k][1])
        ya = max(0, int(min(ys_top)) - 10)
        yb = min(H, int(max(ys_bot)) + 10)
        win = gray[ya:yb, x0:x1]
        res, _c = ocr(win)
        # 归行
        rows_txt = {k: [] for k in chunk}
        for box, t, _cf in (res or []):
            t = str(t).strip()
            if not t:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            xc_abs = x0 + sum(xs) / len(xs)
            yc_abs = ya + sum(ys) / len(ys)
            hit = None
            for k in chunk:
                trec, brec = top_bot[k]
                y0, y1 = ivs[k]
                top_y = row_y(trec, xc_abs) if trec is not None else y0
                bot_y = row_y(brec, xc_abs) if brec is not None else y1
                if top_y + 2 <= yc_abs <= bot_y - 2:
                    hit = k
                    break
            if hit is not None:
                rows_txt[hit].append((min(xs), t))
        for k, items in rows_txt.items():
            if items:
                ev[f"行{k + 2}"] = " ".join(t for _, t in sorted(items) if t)
    return ev


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    ocr = _ocr()
    stems = args or stem_list()
    for stem in stems:
        t0 = time.time()
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"{stem}_表头映射.json", encoding="utf-8"))
        keep = None
        for k in hm["keep"]:
            if k["name"] == ROLE_KEEP["desc"]:
                keep = sorted(k["x_in_band"])
        if not keep:
            print(f"{stem}: 无 desc 列,跳过")
            continue
        top_bot, ivs = row_ivs_stem(stem)
        ev = read_stem(ocr, stem, keep, top_bot, ivs)
        out[stem] = ev
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"{stem}: {len(ev)} 行列读 {round(time.time() - t0, 1)}s", flush=True)
    print(f"colreads 总图数 {len(out)} -> {OUT.name}")


if __name__ == "__main__":
    main()
