# -*- coding: utf-8 -*-
"""全30图:表头带满高竖笔中,哪些是"被漏掉的真列界"(抗漂移墨迹连通判定)。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

WIN, THR, STEP, MAXSTEP, GAPSTOP = 6, 150, 3, 0.4, 90

def grow(g, y_start, x_start, y_lo, y_hi):
    W = g.shape[1]
    hits = tot = 0
    def walk(direction):
        nonlocal hits, tot
        x = float(x_start); gap = 0; y = y_start
        while y_lo < y < y_hi:
            y += direction
            lo = max(0, int(round(x)) - WIN); hi = min(W, int(round(x)) + WIN + 1)
            row = g[y, lo:hi]
            k = int(np.argmin(row)); v = int(row[k])
            tot += 1
            if v < THR:
                hits += 1; gap = 0
                nx = lo + k; d = nx - x
                if abs(d) > MAXSTEP * STEP: nx = x + MAXSTEP * STEP * (1 if d > 0 else -1)
                x = nx
            else:
                gap += STEP
                if gap > GAPSTOP: break
        return y
    y_lo_end = walk(-1); y_hi_end = walk(1)
    return (hits / float(max(tot, 1)), abs(y_hi_end - y_lo_end))

def header_strokes(gray, band, thr=0.55):
    b0, b1 = band; bh = b1 - b0
    dens = (gray[b0:b1, :] < 150).sum(axis=0)
    out, i, W = [], 0, gray.shape[1]
    while i < W:
        if dens[i] >= thr * bh:
            j = i
            while j < W and dens[j] >= thr * bh: j += 1
            out.append(float(i + int(np.argmax(dens[i:j]))))
            i = j
        else:
            i += 1
    return out

print("%-16s %-6s %-6s %-6s  %s" % ("图", "表头竖笔", "已用界", "未配", "未配竖笔的墨迹连通判定"))
rep = {}
for p in sorted((paths.RUNS_DIR/"table_reconstruct").glob("*_表头映射.json")):
    stem = p.stem.replace("_表头映射", "")
    hm = json.loads(p.read_text(encoding="utf-8"))
    band = hm.get("band")
    sx = hm.get("sep_x_band") or []
    if not band or not sx: continue
    g = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    if g is None: continue
    H, W = g.shape
    strokes = header_strokes(g, band)
    un = [s for s in strokes if not any(abs(s - v) <= 8 for v in sx)]
    y_lo, y_hi = int(band[0]), H - 4
    span_full = y_hi - y_lo
    lines = []
    for s in un:
        r, span = grow(g, (band[0]+band[1])//2, s, y_lo, y_hi)
        ok = (r >= 0.55 and span >= 0.75 * span_full)
        lines.append("x=%.0f 命中%.2f 跨度%.0f%% %s" % (s, r, 100.0*span/span_full, "★真列界" if ok else "文字/短笔"))
        if ok: rep.setdefault(stem, []).append(round(s, 1))
    if un:
        print("%-16s %-6d %-6d %-6d" % (stem, len(strokes), len(sx), len(un)))
        for t in lines: print("        " + t)
print()
print("=== 判定为被漏掉的真列界 ===")
for k, v in rep.items(): print("  %s: %s" % (k, v))
if not rep: print("  无")
