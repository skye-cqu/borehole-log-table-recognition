# -*- coding: utf-8 -*-
"""项③量尺:行折线对墨迹贴合指标(09-30 诊断同款口径,30 张)。

口径:每条行折线(排除 era 西延段)每 60px 取一采样,在 ±25px 竖窗内找墨(gray<210 的
行程),无墨=无墨采样;有墨则偏差=|折线y−最近行程中心|。
指标:无墨占比(基线 1015=5.8%)、>10px 偏差占比(基线 3%)、中位/p90/max。
输出 runs/tmp/chord_metrics_20261002.json;用法:python measure_chords_20261002.py [标签]。
"""
import json
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import numpy as np
import cv2

from src.core import paths
from src.table import track_rows as tr

WIN = 25.0     # 无墨判据竖窗(09-30 诊断同款)
SAMP = 60      # 采样步长 px(同款)


def row_metrics(rows, gray, bands=None):
    n = noink = 0
    devs = []
    worst = []
    nc = noink_c = gt10_c = n_c = floor_c = 0     # 内容区(扣柱状带+水文带)子指标
    W, E, HW = bands if bands else (None, None, None)

    def in_graphic(y, x):
        if tr._chord_in_band(W, E, y, x):
            return True
        if HW is not None and x > float(np.interp(y, HW[:, 0], HW[:, 1])) - 6:
            return True
        return False

    for r in rows:
        p = np.asarray(r["poly"], float)
        x0 = p[0, 0]
        k = int(r.get("era_n_ext") or 0)
        if k:
            x0 = p[k, 0]          # 排除 era 西延段,与 09-30 基线同口径
        xs = np.arange(x0 + 2, p[-1, 0] - 1, SAMP)
        for x in xs:
            y = float(np.interp(x, p[:, 0], p[:, 1]))
            col = gray[:, int(x)]
            dark = np.where(col[int(max(y - WIN, 0)):int(min(y + WIN + 1, len(col)))] < 210)[0]
            n += 1
            graphic = in_graphic(y, x)
            if not graphic:
                n_c += 1
            if len(dark) == 0:
                noink += 1
                worst.append((float(x), float(y), -1))
                if not graphic:
                    noink_c += 1
                    # 结构性地板:内容区无墨样本,±30 走廊内亦无细墨(6×lw) = 磨损失迹,不可回收
                    lo2, hi2 = int(max(y - 30, 0)), int(min(y + 31, len(col)))
                    dk2 = np.where(col[lo2:hi2] < 210)[0]
                    thin = False
                    if len(dk2):
                        runs = []
                        s = dk2[0]
                        for a, b in zip(dk2[:-1], dk2[1:]):
                            if b - a > 1:
                                runs.append((s, a))
                                s = b
                        runs.append((s, dk2[-1]))
                        thin = any(e_ - s_ + 1 <= 21 for s_, e_ in runs)
                    if not thin:
                        floor_c += 1
                continue
            # 最近墨行程中心
            runs = []
            s = dark[0]
            for a, b in zip(dark[:-1], dark[1:]):
                if b - a > 1:
                    runs.append((s, a))
                    s = b
            runs.append((s, dark[-1]))
            off = int(max(y - WIN, 0))
            c = min(runs, key=lambda t: abs((t[0] + t[1]) / 2 + off - y))
            d = abs((c[0] + c[1]) / 2 + off - y)
            devs.append(d)
            if d > 10:
                if not graphic:
                    gt10_c += 1
                worst.append((float(x), float(y), round(float(d), 1)))
    devs = np.asarray(devs)
    return {
        "n_samp": n, "n_noink": noink,
        "noink_share": round(noink / n, 4) if n else None,
        "dev_med": round(float(np.median(devs)), 2) if len(devs) else None,
        "dev_p90": round(float(np.percentile(devs, 90)), 2) if len(devs) else None,
        "gt10_share": round(float((devs > 10).mean()), 4) if len(devs) else None,
        "dev_max": round(float(devs.max()), 1) if len(devs) else None,
        "content_n": n_c, "content_noink": round(noink_c / n_c, 4) if n_c else None,
        "content_gt10": round(gt10_c / n_c, 4) if n_c else None,
        "content_floor": round(floor_c / n_c, 4) if n_c else None,
        "worst": sorted(worst, key=lambda t: -t[2])[:12],
    }


def main(tag):
    stems = sorted(p.stem for p in paths.RAW_DIR.glob("钻孔柱状图*.JPG"))
    all_m = {}
    agg = {"n_samp": 0, "n_noink": 0, "gt10n": 0, "nc": 0, "noink_c": 0, "gt10_c": 0,
           "floor_c": 0}
    for i, stem in enumerate(stems, 1):
        out = json.loads((paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
                         .read_text(encoding="utf-8"))
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        W, E, _ = tr.content_band(stem)
        HW = tr.hydro_band(stem)
        m = row_metrics(out.get("rows") or [], gray, (W, E, HW))
        all_m[stem] = m
        agg["n_samp"] += m["n_samp"]
        agg["n_noink"] += m["n_noink"]
        agg["gt10n"] += round((m["gt10_share"] or 0) * m["n_samp"])
        agg["nc"] += m["content_n"]
        agg["noink_c"] += round((m["content_noink"] or 0) * m["content_n"])
        agg["gt10_c"] += round((m["content_gt10"] or 0) * m["content_n"])
        agg["floor_c"] += round((m["content_floor"] or 0) * m["content_n"])
        print(f"[{i:2d}/{len(stems)}] {stem} noink={m['noink_share']} gt10={m['gt10_share']} "
              f"| 内容区 noink={m['content_noink']} gt10={m['content_gt10']} "
              f"地板={m['content_floor']}")
    print(f"\n[{tag}] 全域: 无墨 {agg['n_noink']/agg['n_samp']:.4f}, >10px {agg['gt10n']/agg['n_samp']:.4f}")
    print(f"[{tag}] 内容区: 无墨 {agg['noink_c']/agg['nc']:.4f} (结构性地板 {agg['floor_c']/agg['nc']:.4f}), "
          f">10px {agg['gt10_c']/agg['nc']:.4f}")
    (paths.RUNS_DIR / "tmp" / "chord_metrics_20261002.json").write_text(
        json.dumps({"tag": tag, "charts": all_m}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "baseline")
