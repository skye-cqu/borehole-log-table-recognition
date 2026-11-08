# -*- coding: utf-8 -*-
"""run10:判读级最后尾池——读数不足(单票弱分 0.3)+读截断(0.8)非定谳格。

判读确认现值→protect 定谳 1.0;翻案→写值。种子现值=xlsx 全文(run8b 教训)。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
PKG = ROOT / "runs/autoresearch_align/多源定级_20261106/尾池判读包_r10"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs/tmp"))

import cv2  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

from src.core import paths  # noqa: E402
from src.handwriting import rules as R  # noqa: E402
from src.handwriting import converge_score as CS  # noqa: E402
from src.handwriting.reread import ROLE_KEEP  # noqa: E402
from run5_pkg_v2 import row_ivs_stem, build  # noqa: E402

bridge = R._bridge()
ms = json.loads((paths.AUTORESEARCH_DIR / "multisource_reads.json").read_text(encoding="utf-8"))
strip = json.loads((paths.AUTORESEARCH_DIR / "rowstrip_reads.json").read_text(encoding="utf-8")) \
    if (paths.AUTORESEARCH_DIR / "rowstrip_reads.json").exists() else {}
resweep = json.loads((paths.AUTORESEARCH_DIR / "agnes_resweep.json").read_text(encoding="utf-8")) \
    if (paths.AUTORESEARCH_DIR / "agnes_resweep.json").exists() else {}
colread = json.loads((paths.AUTORESEARCH_DIR / "colreads.json").read_text(encoding="utf-8")) \
    if (paths.AUTORESEARCH_DIR / "colreads.json").exists() else {}

judged = R._judged_map()
pool = []
for p in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
    stem = p.name[: -len("_整合.xlsx")]
    rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
    dcol = R.resolve_roles(rows[0]).get("desc")
    if dcol is None:
        continue
    rk_map = ms.get(stem, {})
    rs_map = resweep.get(stem, {})
    br_map = bridge.get(stem, {})
    st_map = strip.get(stem, {})
    cl_map = colread.get(stem, {})
    for i, row in enumerate(rows[1:]):
        r = i + 2
        cur_n = R._xn(row[dcol] if dcol < len(row) else None)
        if not cur_n:
            continue
        jd = judged.get((stem, r))
        if jd is not None:
            seeds = ([jd.get("种子现值", ""), str(jd.get("新值", ""))]
                     + str(jd.get("判读现值", "")).split("|"))
            if cur_n in (R._xn(x) for x in seeds if x):
                continue
        rk = f"行{r}"
        fam_a = [R._xn(a) for a in ((br_map.get(rk) or {}).get("agnes") or []) if a]
        if (rs_map.get(rk) or {}).get("read"):
            fam_a.append(R._xn(rs_map[rk]["read"]))
        fam_a = [x for x in fam_a if len(x) >= 2]
        m = rk_map.get(rk) or {}
        fam_b = [R._xn(m.get(k)) for k in ("tight", "loose", "montage")]
        col_n = R._xn(cl_map.get(rk) or "")
        if col_n and len(col_n) >= 2:
            fam_b.append(col_n)
        fam_b = [x for x in fam_b if len(x) >= 2]
        strip_n = R._xn((st_map.get(rk) or {}).get("strip"))
        votes = ([("A", x) for x in fam_a] + [("B", x) for x in fam_b]
                 + ([("S", strip_n)] if strip_n and len(strip_n) >= 2 else []))
        clusters = CS._clusters(votes) if votes else []
        win = clusters[0] if clusters else []
        win_n = win[0][1] if win else ""
        win_fams = {f for f, _ in win}
        rival = clusters[1] if len(clusters) > 1 else []
        if len(votes) < 2:
            tier = "读数不足"
        elif len(win) >= 3 and {"A", "B"} <= win_fams:
            tier = "双族"
        elif len(win) >= 3 and {"B", "S"} <= win_fams:
            tier = "单族双几何"
        elif len(win) >= 2:
            tier = ("分裂" if rival and len(rival) >= 2
                    and {f for f, _ in rival} - win_fams else "同族多数")
        else:
            tier = "无收敛"
        rel = ("印证现值" if (win_n == cur_n or CS._ratio(win_n, cur_n) >= CS.RATIO)
               else ("读截断" if win_n and win_n in cur_n else "矛盾/无收敛"))
        if tier == "读数不足" or rel == "读截断":
            pool.append({"tag": f"{stem.replace('钻孔柱状图', '')}_行{r}",
                         "现值": str(row[dcol]), "tier": tier, "rel": rel,
                         "win": win_n, "票": [v for _, v in win]})

print("尾池:", len(pool), "| 读数不足:", sum(1 for e in pool if e['tier'] == '读数不足'),
      "| 读截断:", sum(1 for e in pool if e['rel'] == '读截断'))
PKG.mkdir(parents=True, exist_ok=True)
cache = {}
n_fail = 0
for e in pool:
    tag = e["tag"]
    stem0, row = tag.rsplit("_行", 1)
    stem = "钻孔柱状图" + stem0
    r = int(row)
    if stem not in cache:
        cache[stem] = (row_ivs_stem(stem),
                       cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE),
                       json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                                      f"{stem}_表头映射.json", encoding="utf-8")))
    (top_bot, ivs), gray, hm = cache[stem]
    if r - 2 not in ivs:
        print("跳过(无重放行):", tag)
        continue
    y0, y1 = ivs[r - 2]
    if r - 2 in top_bot:
        top_src, bot_src = top_bot[r - 2]
    else:
        top_src = bot_src = None
    keep = None
    for k in hm["keep"]:
        if k["name"] == ROLE_KEEP["desc"]:
            keep = sorted(k["x_in_band"])
    H, W = gray.shape[:2]
    x0 = max(0, int(keep[0]) - 8)
    x1 = min(W, int(keep[1]) + 8)
    try:
        cell, stripw = build(gray, x0, x1, top_src, y0, bot_src, y1)
    except Exception:
        n_fail += 1
        continue
    cv2.imwrite(str(PKG / f"{tag}_cell.png"), cell)
    cv2.imwrite(str(PKG / f"{tag}_strip.png"), stripw)
print("裁片完成, 失败:", n_fail)
BATCH = 14
nb = (len(pool) + BATCH - 1) // BATCH
for b in range(nb):
    part = pool[b * BATCH:(b + 1) * BATCH]
    (PKG / f"分派_尾池_r10_{b}.json").write_text(
        json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"分派 {nb} 批")
