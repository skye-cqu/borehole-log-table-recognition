# -*- coding: utf-8 -*-
"""把待人审格的重裁片拼成可直接翻阅的 PNG 看图清单(不依赖浏览器/HTML)。

素材分工:
  tag映射.json + 几何预判.json + crops/*.png 由 recrop_pending.py 生成
  (裁片=本格行区间内墨段包围盒,邻行数字已从根上排除);本脚本只负责排版。

每卡片:短编号、层·列、三个候选(A草案/B单格/C条带)、本格墨段块数提示、裁片。
按裁片高度分档排版,保证小字不被压糊。
用法: python src/tools/inline_review_sheets.py [1032 1018 ...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

OUT_DIR = paths.RUNS_DIR / "复核直览"
CROPS = OUT_DIR / "crops"
LIST_DIR = paths.RUNS_DIR / "table_reconstruct"

PAGE_W = 1420
MARGIN = 20
GAP = 12
MAX_PAGE_H = 2600
LINE = 29
# 分档:(单列宽上限, 每行格数, 裁片最大高)
# 分档:(裁片最大高, 每行格数, 裁片显示上限高)。宽裁片(岩性描述等)独占整页宽,
# 否则 1300px 原图压进 340px 列宽手写字直接糊掉。
BANDS = ((260, 4, 260), (560, 3, 560), (100000, 3, 1150), (100000, 1, 1500))
FONT_PATHS = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]


def font(size):
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_ID, F_CAND, F_HINT = font(26), font(22), font(20)


def show(v) -> str:
    s = "" if v in (None, "None", "-") else str(v).strip()
    return re.sub(r"\s+", " ", s) if s else "(空)"


def load_cells(stem):
    n4 = stem[-4:]
    tags = json.loads((OUT_DIR / "tag映射.json").read_text(encoding="utf-8"))
    pre = json.loads((OUT_DIR / "几何预判.json").read_text(encoding="utf-8"))
    out = []
    for c in tags.get(stem, []):
        p = CROPS / f"{stem}_L{c['层']}_{c['列']}.png"
        if not p.exists():
            continue                          # 几何判空,不占视觉额度
        c = dict(c)
        c["crop"] = p
        c["blocks"] = pre.get(c["tag"], "")
        out.append(c)
    return n4, out


def fit(img, w, h):
    scale = min(w / img.width, h / img.height)
    if img.width < 260 and img.height < 260:
        whole = int(scale)
        if whole >= 1:
            scale = whole
    scale = min(max(scale, 1.0), w / img.width, h / img.height)
    return img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                      Image.LANCZOS)


NUM_COLS = ("深度", "层厚", "采长", "倾角", "真厚")


def nvals(v) -> int:
    """候选串里的数值个数,用于与几何墨段块数互校(一格多值时先缩小候选范围)。"""
    s = show(v)
    if s == "(空)":
        return 0
    return len(re.findall(r"\d+\.\d+|\d+\.|\.\d+|\d+", s))


def card(cell, col_w, img_h):
    img = fit(Image.open(cell["crop"]).convert("RGB"), col_w - 12, img_h)
    nb = 0
    if cell["blocks"].startswith("HAS_INK:"):
        nb = int(cell["blocks"].split(":")[1])
    hint = "" if nb <= 1 else f"本格几何墨段 {nb} 块(多值)"
    lines = [(f"{cell['tag']}  第{cell['层']}层 · {cell['列']}", F_ID, (20, 20, 120))]
    for lab, key in (("A草案", "草案"), ("B单格", "agnes单格"), ("C条带", "agnes条")):
        txt = show(cell[key])
        if nb and cell["列"] in NUM_COLS:
            k = nvals(cell[key])
            txt += f"  [{k}值{'=块数✓' if k == nb else ''}]"
        lines.append((f"{lab} {txt}", F_CAND, (150, 30, 30)))
    if hint:
        lines.append((hint, F_HINT, (0, 120, 0)))
    label_h = 8 + LINE * len(lines)
    c = Image.new("RGB", (col_w, label_h + img.height + 12), "white")
    d = ImageDraw.Draw(c)
    y = 8
    for text, fnt, fill in lines:
        d.text((6, y), text, fill=fill, font=fnt)
        y += LINE
    c.paste(img, (6, label_h))
    d.rectangle([0, 0, col_w - 1, c.height - 1], outline=(150, 150, 150), width=1)
    return c


def band_of(w, h):
    if w > 500:
        return 3                              # 宽裁片:整页宽
    for i, (maxh, _, _) in enumerate(BANDS[:3]):
        if h <= maxh:
            return i
    return 2


def strips_for(cells, per_row, col_w, img_h):
    for i in range(0, len(cells), per_row):
        grp = cells[i:i + per_row]
        cards = [card(c, col_w, img_h) for c in grp]
        rowh = max(x.height for x in cards)
        strip = Image.new("RGB", (col_w * per_row + GAP * (per_row - 1), rowh), "white")
        x = 0
        for k in cards:
            strip.paste(k, (x, 0))
            x += col_w + GAP
        yield strip


def paginate(strips, title):
    pages, cur, cur_h = [], [], 0
    for s in strips:
        if cur and cur_h + s.height > MAX_PAGE_H:
            pages.append(cur)
            cur, cur_h = [], 0
        cur.append(s)
        cur_h += s.height + GAP
    if cur:
        pages.append(cur)
    out = []
    for i, pg in enumerate(pages, 1):
        head = Image.new("RGB", (PAGE_W, 56), (245, 245, 245))
        ImageDraw.Draw(head).text((MARGIN, 12),
                                  f"{title}   第 {i}/{len(pages)} 页   "
                                  f"蓝线以上=本格内容,无邻行干扰",
                                  fill=(20, 20, 20), font=F_ID)
        tot = head.height + sum(x.height for x in pg) + GAP * len(pg) + MARGIN
        page = Image.new("RGB", (PAGE_W, tot), "white")
        page.paste(head, (0, 0))
        y = head.height + MARGIN // 2
        for s in pg:
            page.paste(s, (MARGIN, y))
            y += s.height + GAP
        out.append(page.crop((0, 0, PAGE_W, max(y, 1))))
    return out


def build(stem):
    n4, cells = load_cells(stem)
    if not cells:
        print(f"{stem}: 无待判读格")
        return []
    buckets = [[] for _ in BANDS]
    for c in cells:
        with Image.open(c["crop"]) as im:
            buckets[band_of(im.width, im.height)].append(c)
    strips = []
    for i, (_, per, bandh) in enumerate(BANDS):
        if not buckets[i]:
            continue
        col_w = (PAGE_W - 2 * MARGIN - GAP * (per - 1)) // per
        strips += list(strips_for(buckets[i], per, col_w, bandh))
    files = []
    title = f"钻孔柱状图{n4} 待判读 {len(cells)} 格"
    for i, pg in enumerate(paginate(strips, title), 1):
        f = OUT_DIR / f"{n4}_待人审_第{i}页.png"
        pg.save(f)
        files.append(f)
    print(f"{stem}: {len(cells)} 格 → {len(files)} 页  "
          f"(小 {len(buckets[0])} / 中 {len(buckets[1])} / 高 {len(buckets[2])} "
          f"/ 宽文本 {len(buckets[3])})")
    return files


if __name__ == "__main__":
    args = sys.argv[1:]
    for s in ([f"钻孔柱状图{a}" for a in args] if args else
              [f"钻孔柱状图{x}" for x in ("1032", "1018", "1042", "1030")]):
        build(s)
