# -*- coding: utf-8 -*-
"""低置信格高分辨率复核页:把 conf<阈值 或 UNCLEAR 的格单独成页,裁片按原始像素
呈现(宽裁片横向切段堆叠,绝不整体缩放),供逐格定案。

用法: python src/tools/build_recheck_pages.py [--min-conf 0.7]
输出: runs/复核直览/复核_第k页.png  +  复核清单.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

RD = paths.RUNS_DIR / "复核直览"
CROPS = RD / "crops"
PAGE_W = 1420
MARGIN, GAP, LINE = 20, 14, 30
SEG_W = PAGE_W - 2 * MARGIN
F_ID = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26)
F_CAND = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)


def load(min_conf):
    tags = json.loads((RD / "tag映射.json").read_text(encoding="utf-8"))
    idx = {r["tag"]: {**r, "stem": s} for s, rows in tags.items() for r in rows}
    rep = json.loads((RD / "校验报告.json").read_text(encoding="utf-8"))
    down = set(rep.get("降级", {}))          # 机器校验不过的也要复核,它们 conf 未必低
    need = []
    for f in sorted(RD.glob("判定_*.json")):
        for c in json.loads(f.read_text(encoding="utf-8")).get("cells", []):
            if (c.get("verdict") == "UNCLEAR" or float(c.get("conf", 1)) < min_conf
                    or c["tag"] in down):
                need.append({**c, "src": f.name, "cell": idx.get(c["tag"], {}),
                             "降级原因": rep.get("降级", {}).get(c["tag"])})
    return need


def segs(img, w):
    """宽裁片横向切段,每段原尺寸;窄图整张返回。"""
    if img.width <= w:
        return [img]
    return [img.crop((i, 0, min(i + w, img.width), img.height))
            for i in range(0, img.width, w)]


def card(c):
    stem = c["cell"].get("stem", "")
    p = CROPS / f"{stem}_L{c['层']}_{c['列']}.png"
    lines = [(f"{c['tag']}  第{c['层']}层 · {c['列']}  "
              f"[代理判 {c['verdict']}={c.get('value','')} conf={c.get('conf')}]", F_ID, (20, 20, 120)),
             (f"A {c['cell'].get('草案')}", F_CAND, (150, 30, 30)),
             (f"B {c['cell'].get('agnes单格')}", F_CAND, (150, 30, 30)),
             (f"C {c['cell'].get('agnes条')}", F_CAND, (150, 30, 30)),
             (f"代理理由: {str(c.get('reason',''))[:120]}", F_CAND, (0, 100, 0))]
    if c.get("降级原因"):
        lines.append(("机器校验降级: " + "; ".join(c["降级原因"]), F_CAND, (200, 0, 0)))
    label_h = 8 + LINE * len(lines)
    if not p.exists():
        img = Image.new("RGB", (SEG_W, 40), (250, 240, 240))
        parts = [img]
    else:
        with Image.open(p) as im:
            parts = segs(im.convert("RGB"), SEG_W)
    h = label_h + sum(x.height for x in parts) + GAP * (len(parts) - 1) + 12
    cardimg = Image.new("RGB", (PAGE_W - 2 * MARGIN, h), "white")
    d = ImageDraw.Draw(cardimg)
    y = 8
    for text, fnt, fill in lines:
        d.text((6, y), text, fill=fill, font=fnt)
        y += LINE
    yy = label_h
    for x in parts:
        cardimg.paste(x, (6, yy))
        yy += x.height + GAP
    d.rectangle([0, 0, cardimg.width - 1, h - 1], outline=(120, 120, 120), width=2)
    return cardimg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-conf", type=float, default=0.7)
    a = ap.parse_args()
    need = load(a.min_conf)
    for f in RD.glob("复核_第*页.png"):
        f.unlink()
    pages, cur, cur_h = [], [], 0
    limit = 2500
    owner = {}                       # tag -> 页号,供复核代理与事后审计对照覆盖度
    for c in need:
        k = card(c)
        if cur and cur_h + k.height > limit:
            pages.append(cur)
            cur, cur_h = [], 0
        cur.append(k)
        cur_h += k.height + GAP
        owner[c["tag"]] = len(pages) + 1
    if cur:
        pages.append(cur)
    for i, pg in enumerate(pages, 1):
        head = Image.new("RGB", (PAGE_W, 56), (255, 245, 235))
        ImageDraw.Draw(head).text(
            (MARGIN, 12),
            f"低置信复核  {len(need)} 格 / {len(pages)} 页  第 {i} 页"
            f"(裁片为原始像素,宽图已切段,未缩放)", fill=(20, 20, 20), font=F_ID)
        tot = head.height + sum(x.height for x in pg) + GAP * len(pg) + MARGIN
        page = Image.new("RGB", (PAGE_W, tot), "white")
        page.paste(head, (0, 0))
        y = head.height + MARGIN // 2
        for x in pg:
            page.paste(x, (MARGIN, y))
            y += x.height + GAP
        page.save(RD / f"复核_第{i}页.png")
    (RD / "复核清单.json").write_text(
        json.dumps([{k: c.get(k) for k in ("tag", "层", "列", "verdict", "value", "conf", "src")}
                    | {"页": owner[c["tag"]]} for c in need],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"低置信/UNCLEAR {len(need)} 格 → {len(pages)} 页复核图")


if __name__ == "__main__":
    sys.exit(main())
