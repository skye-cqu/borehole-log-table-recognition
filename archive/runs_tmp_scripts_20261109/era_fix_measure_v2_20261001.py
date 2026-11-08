"""时代列修复 参数推导 v2(30 张, 单进程) —— Phase 0 第二轮。

v1 教训: 精确 y 外推行走丢墨(时代行覆盖中位 0.17, census 用 y±8 才 ≥0.5);
条带没按 c0 封顶, c0 以东的真行线墨混进证据(控制行假阳 80)。

v2 行走:
- 条带 x ∈ [L_rob(y)+3, min(poly_west-2, c0-2)](时代列以内);
- 每 x 在 y±8 窗内找竖向墨行程: line=存在 run≤THICK, cross=只有 run>THICK(竖线穿越),
  空=无墨; line 点的 y 取"离外推 y 最近的合格 run 中心"(贴墨, 不造线);
- 无墨空档 >GAP_MAX 提前中止(线断的地方不硬走), 穿越 run>CROSS_W 同样止步(墙)。
- 门禁: 连接(首墨距东端≤CONN) ∧ 覆盖(走到的范围内 line 占比≥ERA_COV) ∧ 触框(最西 line 距 L≤REACH)。

输出: 每行剖面指标 + 门禁逐行结果 → 推 GAP_MAX/THICK/CROSS_W/CONN/REACH/ERA_COV。
"""
import json, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import numpy as np
import cv2
from src.core import paths
from src.table import track_rows as tr
from src.table import track_group

B = paths.RUNS_DIR / "table_reconstruct"

THICK_MULT = 6.0        # line/cross 分界 = 6×lw (lw 每图实测)
GAP_MAX = 60            # 无墨空档中止(v1 raw max_gap=63, 取 60 起步; 敏感性另测)
CROSS_W = 30            # 穿越 run 宽上限(v1 raw max=28)
CONN = 15               # 首墨距东端上限(v1 raw p90=81 太松, 先 15 看通过率)
REACH = 15              # 最西 line 距 L(y) 上限
ERA_COV = 0.5           # census 同款


def row_y_at(p, x):
    if x >= p[0, 0]:
        return float(np.interp(x, p[:, 0], p[:, 1]))
    for j in range(1, len(p)):
        if p[j, 0] - p[0, 0] >= 50:
            k = (p[j, 1] - p[0, 1]) / (p[j, 0] - p[0, 0])
            return float(p[0, 1] + k * (x - p[0, 0]))
    return float(p[0, 1])


def run_at(gray_col, y, half=8):
    """(x列, y) 处包含 y 的竖向墨行程 (长度, 中心y); y 处无墨返回 (0, y)。
    先看 y 本行, 无墨则在 ±half 内找最近墨行(容差窗, census 同款 ±8)。"""
    h = len(gray_col)
    dark = gray_col < 210
    y0 = int(round(y))
    if not (0 <= y0 < h):
        return 0, y
    if dark[y0]:
        lo = hi = y0
        while lo - 1 >= 0 and dark[lo - 1]:
            lo -= 1
        while hi + 1 < h and dark[hi + 1]:
            hi += 1
        return hi - lo + 1, (lo + hi) / 2
    for d in range(1, half + 1):
        for yy in (y0 - d, y0 + d):
            if 0 <= yy < h and dark[yy]:
                lo = hi = yy
                while lo - 1 >= 0 and dark[lo - 1]:
                    lo -= 1
                while hi + 1 < h and dark[hi + 1]:
                    hi += 1
                return hi - lo + 1, (lo + hi) / 2
    return 0, y


def walk(gray, p, L_rob, x_e, x_w, lw):
    """v2 行走。返回 (prof, reach_x, stop_reason)。prof = [(x, y_line)] line 点列。"""
    thick = THICK_MULT * lw
    prof = []
    gap = 0
    last_line = x_e + 1
    reason = "bound"
    x = int(x_e)
    while x >= x_w:
        y_x = row_y_at(p, x)
        r, yc = run_at(gray[:, x], y_x)
        if 0 < r <= thick:
            prof.append((x, float(yc)))
            gap = 0
            last_line = x
        elif r > thick:
            # 穿越: 量这次穿越的宽度, >CROSS_W 视为墙
            wdt = 1
            while x - 1 >= x_w:
                r2, _ = run_at(gray[:, x - 1], row_y_at(p, x - 1))
                if r2 > thick:
                    wdt += 1; x -= 1
                else:
                    break
            if wdt > CROSS_W:
                reason = "wall"
                break
            gap = 0                      # 穿越不中断线(结点), 不计空档
        else:
            gap += 1
            if gap > GAP_MAX:
                reason = "gap"
                break
        x -= 1
    return prof, last_line, reason


def gates(prof, x_e, last_line, L_rob, y_w):
    """三判据 + 墨迹位置直方图(西/中/东三等分)。返回 (era?, 指标)。"""
    if not prof:
        return False, {"cov": 0.0, "first_ink": -1, "d_frame": 9999, "reach_px": 0,
                       "hist": [0, 0, 0]}
    xs = [q[0] for q in prof]
    span = x_e - last_line + 1
    cov = len(prof) / max(span, 1)                      # line 点占比(每 x 最多 1 点)
    first_ink = int(x_e - xs[0])
    d_frame = int(xs[-1] - L_rob(y_w))
    w = x_e - xs[-1]
    hist = [0, 0, 0]
    for x in xs:
        hist[min(2, int((x_e - x) / max(w, 1) * 3))] += 1
    ok = bool(first_ink <= CONN and cov >= ERA_COV and d_frame <= REACH)
    return ok, {"cov": round(cov, 3), "first_ink": first_ink,
                "d_frame": d_frame, "reach_px": int(x_e - xs[-1]),
                "hist": hist}


def main():
    stems = sorted(f.name[:-9] for f in B.glob("钻孔柱状图*_行判定.json"))
    recs = {"era": [], "ctrl": []}
    lw_all = []
    for stem in stems:
        d = json.loads((B / f"{stem}_行判定.json").read_text(encoding="utf-8"))
        rows = d["rows"]
        fr = tr.table_frame(stem)
        fp = B / f"{stem}_列结构定稿.json"
        if fr is None or not rows or not fp.exists():
            print(f"{stem[-4:]}: 跳过")
            continue
        L = fr[0]
        Ls = np.array(sorted(L.tolist()))
        c0 = json.loads(fp.read_text(encoding="utf-8"))["columns"][0]["x_at_mid"]
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)

        # lw(管线二值同 v1) + 稳健 L(y)
        ink = track_group.binarize(gray, track_group.PARAMS).T
        tp = []
        for r in rows[::max(1, len(rows) // 50)][:60]:
            p = np.asarray(r["poly"], float)
            for x in np.linspace(p[0, 0] + 5, p[-1, 0] - 5, min(60, max(len(p) * 2, 4))):
                col = ink[int(x)]
                y0 = min(max(int(row_y_at(p, x)), 0), len(col) - 1)
                if col[y0]:
                    t, lo, hi = 1, y0, y0
                    while lo - 1 >= 0 and col[lo - 1]:
                        t += 1; lo -= 1
                    while hi + 1 < len(col) and col[hi + 1]:
                        t += 1; hi += 1
                    tp.append(t)
        tp = np.array([t for t in tp if 0 < t <= 30])
        lw = float(np.median(tp)) if len(tp) else 2.0
        lw_all.append({"stem": stem, "lw": round(lw, 1)})
        del ink
        k = 15
        xsm = np.array([np.median(Ls[max(0, i - k):i + k + 1, 1]) for i in range(len(Ls))])
        L_rob = lambda y: float(np.interp(y, Ls[:, 0], xsm))

        # 时代行(census 同款) + 控制行
        era = []
        for r in rows:
            p = np.asarray(r["poly"], float)
            x_start = min(int(p[0, 0]) - 1, int(c0) + 5)
            ok = tot = 0
            for x in range(x_start, 100, -1):
                y = row_y_at(p, x)
                Ly = float(np.interp(y, Ls[:, 0], Ls[:, 1]))
                if x < Ly + 15 or x > c0 - 25:
                    continue
                tot += 1
                if gray[max(int(y - 8), 0):int(y + 9), x].min() < 210:
                    ok += 1
            if tot >= 15 and ok / tot >= 0.5:
                era.append(r)
        ey = [r["y_at_mid"] for r in era]
        ys_all = sorted(r["y_at_mid"] for r in rows)
        rh = float(np.median(np.diff(ys_all))) if len(ys_all) > 1 else 100
        ctrl = [r for r in rows if all(abs(r["y_at_mid"] - y) > 0.6 * rh for y in ey)][:40]

        for grp, tag in ((era, "era"), (ctrl, "ctrl")):
            for r in grp:
                p = np.asarray(r["poly"], float)
                x_e = min(p[0, 0] - 2, c0 - 2)
                y_e = row_y_at(p, p[0, 0])
                x_w = L_rob(y_e) + 3
                if x_e - x_w < 8:
                    recs[tag].append({"stem": stem, "y": r["y_at_mid"], "skip": "narrow"})
                    continue
                prof, last_line, reason = walk(gray, p, L_rob, x_e, x_w, lw)
                ok, m = gates(prof, x_e, last_line, L_rob, row_y_at(p, last_line))
                recs[tag].append({"stem": stem, "y": r["y_at_mid"], "pw": round(float(p[0, 0])),
                                  "c0": round(c0), "era_ok": ok, "reason": reason, **m,
                                  "n_pts": len(prof)})
                if tag == "ctrl" and ok:
                    y1, y2 = int(y_e) - 60, int(y_e) + 60
                    crop = gray[max(y1, 0):y2, max(int(x_w) - 20, 0):int(x_e) + 20]
                    cv2.imwrite(f"runs/tmp/era_fp/{stem}_y{int(y_e)}.png", crop)
                if tag == "era" and ok and len([1 for x in recs['era']
                                                if x.get('era_ok') and x['stem'] == stem]) <= 3:
                    y1, y2 = int(y_e) - 60, int(y_e) + 60
                    crop = gray[max(y1, 0):y2, max(int(x_w) - 20, 0):int(x_e) + 20]
                    cv2.imwrite(f"runs/tmp/era_fp/OK_{stem}_y{int(y_e)}.png", crop)
        n_ok = sum(1 for x in recs["era"] if x.get("era_ok") and x["stem"] == stem)
        n_fp = sum(1 for x in recs["ctrl"] if x.get("era_ok") and x["stem"] == stem)
        print(f"{stem[-4:]}: 时代行{len(era)} 过{n_ok} 控{len([x for x in recs['ctrl'] if x['stem']==stem])} "
              f"假阳{n_fp} lw={lw:.0f}")
        del gray

    json.dump({"lw": lw_all, "recs": recs},
              open("runs/tmp/era_fix_metrics_v2_20261001.json", "w", encoding="utf-8"),
              ensure_ascii=False)
    e = [x for x in recs["era"] if "era_ok" in x]
    c = [x for x in recs["ctrl"] if "era_ok" in x]
    print(f"\n== v2 摘要 == 时代行 {len(e)} 行: 过 {sum(x['era_ok'] for x in e)} "
          f"({sum(x['era_ok'] for x in e)/max(len(e),1):.0%}), 无墨/中止原因: "
          f"{ {r: sum(1 for x in e if x['reason']==r and not x['era_ok']) for r in ('gap','wall','bound')} }")
    cov = np.array([x["cov"] for x in e]); fi = np.array([x["first_ink"] for x in e])
    df = np.array([x["d_frame"] for x in e])
    print(f"覆盖 med={np.median(cov):.2f} p10={np.percentile(cov,10):.2f} | "
          f"首墨 p90={np.percentile(fi,90):.0f} | 到框 p90={np.percentile(df,90):.0f} max={df.max()}")
    print(f"控制行 {len(c)}: 假阳 {sum(x['era_ok'] for x in c)}")
    fp = [x for x in c if x["era_ok"]]
    for x in fp[:15]:
        print(f"  FP {x['stem']} y={x['y']} cov={x['cov']} fi={x['first_ink']} df={x['d_frame']} pw={x['pw']} c0={x['c0']}")
    print("未过时代行(逐行):")
    for x in e:
        if not x["era_ok"]:
            print(f"  {x['stem']} y={x['y']} cov={x['cov']} fi={x['first_ink']} df={x['d_frame']} reason={x['reason']}")


if __name__ == "__main__":
    main()
