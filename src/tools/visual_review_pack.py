# -*- coding: utf-8 -*-
"""助手视觉核验工具(用户 2026-09-16 授权代核 409 格,禁止再向用户询问)。

audit   四图待人审计数 + 复核包裁片齐套检查
sheets  生成决策图版:每格=序号+层:列 标签行 / 放大裁片行 / 三候选(草/单/条)行
resolve 决策文件 {"code": {"序号": "@草|@单|@条|字面"}} → apply_review 回写 JSON

裁决约定:@草=采纳草案读数;@单=采纳 Agnes 单格读数;@条=采纳 Agnes 条带读数;
字面=自由裁定值(原样写入单元格)。候选原值从账本解析,避免转写误差。
序号=该图待人审格按账本顺序的 1 起编号(与 sheets 输出清单一致)。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs" / "table_reconstruct"
CODES4 = ["1018", "1030", "1032", "1042"]
STEMS4 = [f"钻孔柱状图{c}" for c in CODES4]
OUT = RUNS / "视觉核验_20260916"

TEXT_COLS = {"岩性描述", "地质时代"}
SHEET_W, SHEET_H = 1568, 1560


def _flags(stem):
    data = json.loads((RUNS / f"{stem}_待核清单.json").read_text(encoding="utf-8"))
    return [f for f in data if f["处置"] == "待人审" and f.get("列")]


def _font(size):
    for p in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cmd_audit():
    total = 0
    for code, stem in zip(CODES4, STEMS4):
        fs = _flags(stem)
        total += len(fs)
        pack = RUNS / f"{stem}_待核复核包"
        pngs = {p.name for p in pack.glob("*.png")} if pack.is_dir() else set()
        miss = [f"{stem}_L{f['层']}_{f['列']}.png" for f in fs
                if f"{stem}_L{f['层']}_{f['列']}.png" not in pngs]
        print(f"{code}: 待人审 {len(fs)} 格, 裁片缺 {len(miss)}")
        for m in miss[:8]:
            print(f"  缺 {m}")
    print(f"合计待人审 {total}")


def _cell_rows(code, stem):
    """[(序号, 层, 列, PIL图|None, 候选行文本)]"""
    pack = RUNS / f"{stem}_待核复核包"
    out = []
    for i, f in enumerate(_flags(stem), 1):
        li, name = f["层"], f["列"]
        png = pack / f"{stem}_L{li}_{name}.png"
        im = None
        if png.is_file():
            try:
                im = Image.open(png)
                if im.mode != "RGB":
                    im = im.convert("RGB")
            except OSError:
                im = None
        if im is not None:
            if name in TEXT_COLS:
                th = 120
            else:
                th = 84
            scale = th / im.height
            w = int(im.width * scale)
            if w > 1420:
                w = 1420
                scale = w / im.width
                th = max(int(im.height * scale), 12)
            if scale > 1 and im.width < 80:
                pass
            im = im.resize((max(w, 1), max(th, 1)), Image.LANCZOS)
        cands = f"草={f.get('草案')!r}  单={f.get('agnes单格')!r}  条={f.get('agnes条')!r}"
        cands = cands.replace("None", "∅").replace("\n", " ")
        out.append((i, li, name, im, cands))
    return out


def cmd_sheets():
    OUT.mkdir(exist_ok=True)
    fnt = _font(17)
    fnt_s = _font(16)
    for code, stem in zip(CODES4, STEMS4):
        cells = _cell_rows(code, stem)
        sheet_i, y, idx0 = 1, 6, 0
        img = Image.new("RGB", (SHEET_W, SHEET_H), "white")
        d = ImageDraw.Draw(img)
        names = []

        def flush(i0, i1, sheet_i):
            if i0 >= i1:
                return
            outp = OUT / f"{code}_决策_{sheet_i:02d}.png"
            img.save(outp)
            seg = cells[i0:i1]
            print(f"{outp.name}: {len(seg)} 格 ["
                  + " ".join(f"{i}:{li}:{nm}" for i, li, nm, _, _ in seg) + "]")

        start_idx = 0
        for (i, li, name, im, cands) in cells:
            h_img = im.height if im is not None else 24
            need = 22 + h_img + 22 + 8
            if y + need > SHEET_H - 8 and start_idx < i - 1:
                flush(start_idx, i - 1, sheet_i)
                img = Image.new("RGB", (SHEET_W, SHEET_H), "white")
                d = ImageDraw.Draw(img)
                y, start_idx, sheet_i = 6, i - 1, sheet_i + 1
            d.line([(0, y), (SHEET_W, y)], fill=(185, 185, 185), width=1)
            d.text((8, y + 3), f"#{i:03d}  L{li} {name}", fill="black", font=fnt)
            y += 22
            if im is not None:
                d.rectangle([7, y - 1, 9 + im.width, y + im.height + 1],
                            outline=(160, 160, 160), width=1)
                img.paste(im, (8, y))
            else:
                d.text((8, y + 4), "(无裁片)", fill=(200, 0, 0), font=fnt_s)
            y += h_img + 2
            d.text((8, y + 2), cands, fill=(15, 15, 130), font=fnt_s)
            y += 22 + 6
        flush(idx0, y, sheet_i)


def cmd_resolve():
    dec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    picks = {}
    n_lit = n_cand = 0
    for code, stem in zip(CODES4, STEMS4):
        fs = _flags(stem)
        got = dec.get(code, {})
        ids = {str(i) for i in range(1, len(fs) + 1)}
        miss = sorted(ids - set(got), key=int)
        extra = sorted(set(got) - ids, key=int)
        if miss or extra:
            print(f"{code}: 覆盖不全 缺{len(miss)} {miss[:8]} 多{len(extra)} {extra[:8]}")
            sys.exit(1)
        out = {}
        for i, f in enumerate(fs, 1):
            v = str(got[str(i)]).strip()
            if v == "@草":
                out[f"{f['层']}:{f['列']}"] = (
                    "" if f.get("草案") in (None, "None") else str(f["草案"]))
                n_cand += 1
            elif v == "@单":
                out[f"{f['层']}:{f['列']}"] = (
                    "" if f.get("agnes单格") in (None, "None") else str(f["agnes单格"]))
                n_cand += 1
            elif v == "@条":
                out[f"{f['层']}:{f['列']}"] = (
                    "" if f.get("agnes条") in (None, "None") else str(f["agnes条"]))
                n_cand += 1
            else:
                out[f"{f['层']}:{f['列']}"] = v
                n_lit += 1
        picks[code] = out
    outp = RUNS / "视觉核验回写_20260916.json"
    outp.write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in picks.values())
    print(f"回写 {total} 格(候选采纳 {n_cand}, 字面 {n_lit}) → {outp}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "audit":
        cmd_audit()
    elif cmd == "sheets":
        cmd_sheets()
    elif cmd == "resolve":
        cmd_resolve()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
