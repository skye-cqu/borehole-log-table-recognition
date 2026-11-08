# -*- coding: utf-8 -*-
"""run4:巨带行(desc rowspan >400px 被行带读器跳过)的分行拼接补读。

worker 同款几何,box 先按 y 中心聚类分行(阈值=box 高中位数×0.9),
行内按 x 排序,行间按 y 排序拼接——修复 x 排序跨行乱序。
目标=定级账"读数不足"格;merge 只填空/无条目,不动已有非空读。
出 rowstrip_tall.json 并并入 rowstrip_reads.json。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

from src.core import paths
from src.handwriting.multisource_rowstrip import MX, MY, OUT, _merge
from src.handwriting.reread import ROLE_KEEP, _ocr

TALL = paths.AUTORESEARCH_DIR / "rowstrip_tall.json"


def target_rows():
    d = json.loads((paths.AUTORESEARCH_DIR / "多源定级_20261106" / "定级.json")
                   .read_text(encoding="utf-8"))
    per = {}
    for e in d["cells"]:
        if e["级"] == "读数不足":
            per.setdefault(e["stem"], []).append(e["行"])
    return per


def read_win(ocr, win, x0, x1):
    """裁窗→box 按 y 聚类分行→行内 x 排序→行间 y 拼接。"""
    res, _c = ocr(win)
    boxes = []
    for box, t, _conf in (res or []):
        t = str(t).strip()
        if not t:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        bl, br = min(xs), max(xs)
        if br < x0 - 60 or bl > x1 + 120:
            continue                       # 粗分配:离 desc 名义界过远不收
        boxes.append((sum(ys) / len(ys), bl, br, t))
    if not boxes:
        return ""
    hs = sorted(br - bl for _, bl, br, _t in boxes)
    med = hs[len(hs) // 2]
    boxes.sort()
    lines, cur, last_y = [], [boxes[0]], boxes[0][0]
    for b in boxes[1:]:
        if b[0] - last_y > max(35.0, med * 0.9):
            lines.append(cur)
            cur = []
        cur.append(b)
        last_y = b[0]
    lines.append(cur)
    parts = []
    for ln in lines:
        parts.append(" ".join(t for _, bl, br, t in sorted(ln, key=lambda z: z[1]) if t))
    return " ".join(parts)


def main():
    per = target_rows()
    out = json.loads(TALL.read_text(encoding="utf-8")) if TALL.exists() else {}
    n = 0
    for stem, rows_ in sorted(per.items()):
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"{stem}_表头映射.json", encoding="utf-8"))
        keep = None
        for k in hm["keep"]:
            if k["name"] == ROLE_KEEP["desc"]:
                keep = sorted(k["x_in_band"])
        if not keep:
            continue
        x0, x1 = int(keep[0]), int(keep[1])
        cache = json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
        ivs = {int(k): v for k, v in cache[stem]["ivs"].items()}
        import cv2
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        H, W = gray.shape[:2]
        xa, xb = max(0, x0 - MX), min(W, x1 + MX)
        ocr = _ocr()
        ev = {}
        t0 = time.time()
        for r in sorted(rows_):
            if r - 2 not in ivs:
                continue
            y0, y1 = (int(v) for v in ivs[r - 2])
            ya, yb = max(0, y0 - MY), min(H, y1 + MY)
            if yb - ya < 30:
                continue
            ev[f"行{r}"] = {"strip": read_win(ocr, gray[ya:yb, xa:xb], x0, x1)}
        out[stem] = ev
        n += len(ev)
        print(f"{stem}: {len(ev)} 行 {round(time.time() - t0, 1)}s", flush=True)
    TALL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    # merge:只填空/无条目
    main_strips = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    filled = 0
    for stem, ev in out.items():
        dst = main_strips.setdefault(stem, {})
        for rk, e in ev.items():
            if not dst.get(rk, {}).get("strip"):
                dst[rk] = e
                filled += 1
    OUT.write_text(json.dumps(main_strips, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"巨带补读 {n} 行,并入 {filled} 行(只填空);汇总 {_merge and ''}")


if __name__ == "__main__":
    main()
