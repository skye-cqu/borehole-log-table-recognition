# -*- coding: utf-8 -*-
"""把"离墨"落到原因上：一条线的超差采样，是画歪了、图上本来没横线、还是压在柱状图案上。

对 30 张的每条层界，按标尺同一套采样（60 点、找墨半径取半行高、容差 5px），把每个采样分成：
  ok    ±5px 内有横线墨
  偏    半径内有横线墨但超过 5px —— 线画歪了（唯一该修的这一类）
  空    半径内根本没有横线墨 —— 图在这一段本来没有横线（断口/图案/裁边）
再按采样落在柱状带内/外分开计，回答"去掉柱状图案还剩多少坏线"。

用法: python runs/tmp/diag_off.py [1027 1040]    # 无参数=30 张
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
import yardstick as Y                                              # noqa: E402
from src.table.track_rows import content_band, edge_at             # noqa: E402


def diag(code):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((Y.SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(stem)
    west, east, _ = content_band(stem)
    S = Y.search_of(rd.get("row_h"))
    n_bad = n_dev = n_dev_o = n_gap = still = 0
    worst, all_lines = [], []
    for r in rd["rows"]:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        dev = gap = band = dev_o = gap_o = 0
        xs, ysv, ds = Y.samples(r, ruling, S)
        for xi, y, d in zip((int(x) for x in xs), ysv, ds):
            off_s = d > 5
            dev += 5 < d <= S
            gap += d > S
            inb = west is not None and edge_at(west, y) <= xi <= edge_at(east, y)
            band += off_s and inb
            dev_o += (5 < d <= S) and not inb
            gap_o += (d > S) and not inb
        n = Y.SAMPLE
        off = (dev + gap) / n * 100
        off_out = (dev_o + gap_o) / n * 100     # 只数柱状带以外的采样
        if off > 10:
            n_bad += 1
            n_dev += dev >= 6                   # 超差线里：≥6 个采样"有墨但偏"
            n_dev_o += dev_o >= 6               # 只数柱状带以外的真偏＝真该修的
            n_gap += gap >= 6                   # 超差线里：≥6 个采样"±60px 内无墨"
            still += off_out > 10
            worst.append((off, off_out, round(r["y_at_mid"]), r["x"], dev, gap, band,
                          r["n_chains"]))
        all_lines.append({"code": code, "y": round(r["y_at_mid"]), "x0": x0, "x1": x1,
                          "dev": dev, "gap": gap, "dev_o": dev_o, "gap_o": gap_o,
                          "band": band, "n_chains": r["n_chains"],
                          "cov_desc": r.get("cov_desc"), "cov_num": r.get("cov_num")})
    return {"code": code, "n": len(rd["rows"]), "bad": n_bad, "still": still,
            "pian": n_dev, "pian_o": n_dev_o, "kong": n_gap,
            "good": len(rd["rows"]) - n_bad, "all": all_lines,
            "worst": sorted(worst, key=lambda t: -t[1])[:5]}


tot = dict(n=0, bad=0, still=0, pian=0, pian_o=0, kong=0)
ALL = []
for code in [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in Y.paths.CANDIDATE_COORD_DIR.glob("*.json")):
    d = diag(code)
    ALL += d.pop("all")
    for k in tot:
        tot[k] += d[k]
    print(f"{code}: 层界{d['n']:>4}  合格{d['good']:>4}  超差10%+{d['bad']:>4}"
          f"  去柱状带仍超差{d['still']:>4}  带外真偏≥6点{d['pian_o']:>4}  有无墨段{d['kong']:>4}")
    for t in d["worst"]:
        print(f"      y={t[2]:<6} x={t[3][0]}-{t[3][1]:<6} 离墨{t[0]:>3.0f}%→带外{t[1]:>3.0f}%"
              f"（带内{t[6]:>2}/真偏{t[4]:>2}/无墨{t[5]:>2} 共60） 链{t[7]}")
print(f"合计: 层界{tot['n']}  超差10%+{tot['bad']}  去柱状带仍超差{tot['still']}"
      f"  带外真偏≥6点{tot['pian_o']}  有无墨段{tot['kong']}")
out = Path(os.environ.get("OFF_OUT", Path(__file__).parent / "off_lines.json"))
out.write_text(json.dumps(ALL, ensure_ascii=False), encoding="utf-8")
print(f"逐条明细 {len(ALL)} 条 → {out.name}")
# 真歪名单交给出交付物的脚本：叠加图上标黄，人一眼就能找到该看哪几条
sus = [{"image": f"钻孔柱状图{r['code']}", "y": r["y"], "x": [r["x0"], r["x1"]],
        "dev_o": r["dev_o"], "gap_o": r["gap_o"]} for r in ALL if r["dev_o"] >= 6]
Y.paths.LINE_SUSPECTS.write_text(json.dumps(sus, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"真歪名单 {len(sus)} 条 → {Y.paths.LINE_SUSPECTS}")
