"""时代列修复 参数推导测量(30 张, 单进程) —— Phase 0。

量什么(全部为动代码前推导链服务):
A. 线宽 lw: 行线采样点上的竖向墨迹行程(管线 binarize 与 raw<210 两套), 推 2×lw 容差。
B. 左框链质量: y 非单调点数/横向尖刺; 稳健 L(y)(按 y 排序+滑窗中位) vs 裸 interp。
C. 时代行 墨迹西行剖面: 从 poly 西端向西走到框, 逐 x 分类(细墨=线/粗墨=竖线穿越/空),
   得 覆盖率/最大空档/最大穿越宽/首墨距离/到框距离 —— 推 GAP_MAX、ERA_COV、THICK_MAX、CROSS_W、REACH。
D. 假阳探针: 同一剖面测试跑在普通行上, 三个判据(连接性/覆盖率/触框)各拦多少。
E. 被杀段审计: 每图 clip_to_frame 整段杀掉的 high 段数。

输出: runs/tmp/era_fix_metrics_20261001.json + stdout 摘要。
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
OUT = {}


def row_y_at(p, x):
    """行折线在 x 的高度; 西端外按两点半径外推(≥50px 跨度), 否则取西端常数。"""
    if x >= p[0, 0]:
        return float(np.interp(x, p[:, 0], p[:, 1]))
    for j in range(1, len(p)):
        if p[j, 0] - p[0, 0] >= 50:
            k = (p[j, 1] - p[0, 1]) / (p[j, 0] - p[0, 0])
            return float(p[0, 1] + k * (x - p[0, 0]))
    return float(p[0, 1])


def v_run(col, y, half=40):
    """竖向墨迹行程(px): col 是某 x 的整列; bool 列按 True, 灰度列按 <210。无墨返回 0。"""
    h = len(col)
    y0 = min(max(int(y), 0), h - 1)
    has = col[y0] if col.dtype == bool else col[y0] < 210
    if not has:
        return 0
    t, lo, hi = 1, y0, y0
    while lo - 1 >= 0 and y0 - (lo - 1) <= half and \
            (col[lo - 1] if col.dtype == bool else col[lo - 1] < 210):
        t += 1; lo -= 1
    while hi + 1 < h and (hi + 1) - y0 <= half and \
            (col[hi + 1] if col.dtype == bool else col[hi + 1] < 210):
        t += 1; hi += 1
    return t


def summarize(prof, lw):
    """剖面 → 三类分类指标(line=细墨, cross=粗墨竖线, 其余=空)。"""
    xs = np.array([q[0] for q in prof])
    yp = np.array([q[1] for q in prof])
    out = {}
    for tag, t in (("pipe", np.array([q[2] for q in prof])),
                   ("raw", np.array([q[3] for q in prof]))):
        line = (t > 0) & (t <= 6 * lw)
        cross = t > 6 * lw
        cw, cur = [], 0
        for v in cross:
            if v:
                cur += 1
            elif cur:
                cw.append(cur); cur = 0
        if cur:
            cw.append(cur)
        gaps, cur = [], 0
        for v in line | cross:
            cur = cur + 1 if not v else 0
            gaps.append(cur)
        idx = np.flatnonzero(line)
        if len(idx):
            i_w = idx[-1]                       # 剖面向西走, idx[-1] = 最西线墨
            d_frame = int(xs[i_w] - Ly_of(yp[i_w]))
            first_ink = int(xs[0] - xs[idx[0]])
            reach = int(xs[0] - xs[idx[-1]])
        else:
            d_frame, first_ink, reach = 9999, -1, -1
        out[tag] = {"cov": round(float(line.mean()), 3) if len(line) else 0.0,
                    "max_gap": int(max(gaps) if gaps else 0),
                    "cross_w": int(max(cw) if cw else 0),
                    "n_cross": len([c for c in cw if c > 0]),
                    "first_ink": first_ink, "reach": reach, "d_frame": d_frame}
    return out


Ly_of = lambda y: 0.0      # main 里替换为稳健 L(y)


def era_rows_of(rows, Ls, c0):
    """普查同款时代行判据(阈值 210, y±8, 窗 [L+15, c0-25])。"""
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
            col = gray_part[:, x]
            if col[max(int(y - 8), 0):int(y + 9)].min() < 210:
                ok += 1
        if tot >= 15 and ok / tot >= 0.5:
            era.append(r)
    return era


gray_part = None


def main():
    global gray_part, Ly_of
    stems = sorted(f.name[:-9] for f in B.glob("钻孔柱状图*_行判定.json"))
    lw_all, frame_res, kills = [], [], []
    era_m = {"pipe": [], "raw": []}
    ctrl_hits = {"conn": 0, "cov": 0, "reach": 0, "pass": 0}
    ctrl_n = 0
    for stem in stems:
        d = json.loads((B / f"{stem}_行判定.json").read_text(encoding="utf-8"))
        rows = d["rows"]
        fr = tr.table_frame(stem)
        fp = B / f"{stem}_列结构定稿.json"
        if fr is None or not rows or not fp.exists():
            print(f"{stem[-4:]}: 跳过(框{fr is not None}/行{len(rows)}/定稿{fp.exists()})")
            continue
        L, R = fr
        Ls = np.array(sorted(L.tolist()))
        c0 = json.loads(fp.read_text(encoding="utf-8"))["columns"][0]["x_at_mid"]
        gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
        ink = track_group.binarize(gray, track_group.PARAMS).T
        gray_part = gray

        # A. 线宽: 全高散采 60 行
        tp, trw = [], []
        for r in rows[::max(1, len(rows) // 50)][:60]:
            p = np.asarray(r["poly"], float)
            for x in np.linspace(p[0, 0] + 5, p[-1, 0] - 5, min(60, max(len(p) * 2, 4))):
                y = row_y_at(p, x)
                tp.append(v_run(ink[int(x)], y))
                trw.append(v_run(gray[:, int(x)], y))
        tp, trw = np.array(tp), np.array(trw)
        tpp = tp[(tp > 0) & (tp <= 30)]
        trwp = trw[(trw > 0) & (trw <= 30)]
        lw_p = float(np.median(tpp)) if len(tpp) else 2.0
        lw_r = float(np.median(trwp)) if len(trwp) else 2.0
        lw = max(lw_p, 2.0)
        lw_all.append({"stem": stem, "lw_pipe": round(lw_p, 1), "lw_raw": round(lw_r, 1),
                       "p90_pipe": round(float(np.percentile(tpp, 90)), 1) if len(tpp) else 0,
                       "p90_raw": round(float(np.percentile(trwp, 90)), 1) if len(trwp) else 0})

        # B. 框链质量 + 稳健 L(y)(按 y 排序 + 索引滑窗中位 k=15)
        nonmono = int((np.diff(L[:, 0]) <= 0).sum())
        spike = sum(1 for i in range(1, len(Ls))
                    if Ls[i, 0] - Ls[i - 1, 0] <= 4 and abs(Ls[i, 1] - Ls[i - 1, 1]) > 20)
        ysr, xsr = Ls[:, 0], Ls[:, 1]
        k = 15
        xsm = np.array([np.median(xsr[max(0, i - k):i + k + 1]) for i in range(len(xsr))])
        Ly_of = lambda y: float(np.interp(y, ysr, xsm))
        frame_res.append({"stem": stem, "nonmono": nonmono, "spikes": spike,
                          "n_pts": len(Ls)})

        # C+D. 时代行剖面 / 控制行假阳探针
        era = era_rows_of(rows, Ls, c0)
        ey = [r["y_at_mid"] for r in era]
        ys_all = sorted(r["y_at_mid"] for r in rows)
        rh = float(np.median(np.diff(ys_all))) if len(ys_all) > 1 else 100
        ctrl = [r for r in rows if all(abs(r["y_at_mid"] - y) > 0.6 * rh for y in ey)][:40]
        nprof = 0
        for grp, is_era in ((era, True), (ctrl, False)):
            for r in grp:
                p = np.asarray(r["poly"], float)
                x_e = p[0, 0] - 2
                x_w = Ly_of(row_y_at(p, p[0, 0])) + 3
                if x_e - x_w < 8:
                    continue
                prof = [(x, row_y_at(p, x), v_run(ink[int(x)], row_y_at(p, x)),
                         v_run(gray[:, int(x)], row_y_at(p, x)))
                        for x in range(int(x_e), int(x_w) - 1, -1)]
                if not prof:
                    continue
                nprof += 1
                s = summarize(prof, lw)
                if is_era:
                    for tag in ("pipe", "raw"):
                        era_m[tag].append({"stem": stem, "y": r["y_at_mid"], **s[tag]})
                else:
                    pr = s["raw"]
                    ctrl_n += 1
                    conn = 0 <= pr["first_ink"] <= 15
                    cov = pr["cov"] >= 0.5
                    reach = pr["d_frame"] <= 15
                    ctrl_hits["conn"] += conn
                    ctrl_hits["cov"] += cov
                    ctrl_hits["reach"] += reach
                    ctrl_hits["pass"] += (conn and cov and reach)

        # E. 被杀 high 段审计
        cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
        hsegs = [s for s in cj["lines"] if s["direction"] == "horizontal" and s["label"] == "high"]
        hk = sum(1 for s in hsegs if tr.clip_to_frame(s["points"], *fr) is None)
        kills.append({"stem": stem, "killed": hk, "n_high": len(hsegs)})
        print(f"{stem[-4:]}: lw={lw_p:.0f}/{lw_r:.0f} 时代行{len(era)} 控{len(ctrl)} "
              f"剖面{nprof} 杀{hk}/{len(hsegs)} 非单调{nonmono} 尖刺{spike} 框点{len(Ls)}")
        del gray, ink

    OUT.update(lw=lw_all, frame=frame_res, era_walk=era_m,
               ctrl={"n": ctrl_n, **ctrl_hits}, kills=kills)
    json.dump(OUT, open("runs/tmp/era_fix_metrics_20261001.json", "w", encoding="utf-8"),
              ensure_ascii=False)

    print("\n== 摘要 ==")
    print(f"线宽(管线/	raw 中位): {np.median([x['lw_pipe'] for x in lw_all])}/"
          f"{np.median([x['lw_raw'] for x in lw_all])}; p90 管线 "
          f"{np.median([x['p90_pipe'] for x in lw_all])}")
    print(f"框链: 非单调 {sum(1 for x in frame_res if x['nonmono'])}/30 图, "
          f"尖刺 {sum(1 for x in frame_res if x['spikes'])}/30 图")
    for tag in ("pipe", "raw"):
        m = era_m[tag]
        if not m:
            continue
        cov = np.array([x["cov"] for x in m])
        gap = np.array([x["max_gap"] for x in m])
        dw = np.array([x["cross_w"] for x in m])
        fi = np.array([x["first_ink"] for x in m])
        df = np.array([x["d_frame"] for x in m])
        dfok = df[df < 9000]
        print(f"[{tag}] n={len(m)}: 覆盖 p10={np.percentile(cov,10):.2f} med={np.median(cov):.2f} | "
              f"空档 p50={np.percentile(gap,50):.0f} p90={np.percentile(gap,90):.0f} max={gap.max()} | "
              f"穿越宽 p90={np.percentile(dw,90):.0f} max={dw.max()} | "
              f"首墨 p50={np.percentile(fi,50):.0f} p90={np.percentile(fi,90):.0f} | "
              f"到框 p50={np.percentile(dfok,50):.0f} p90={np.percentile(dfok,90):.0f} "
              f"max={dfok.max()} 无墨{int((df>=9000).sum())}")
    print(f"控制行 n={ctrl_n}: 连接 {ctrl_hits['conn']} 覆盖 {ctrl_hits['cov']} "
          f"触框 {ctrl_hits['reach']} 全过(假阳) {ctrl_hits['pass']}")
    print(f"被杀 high 段: 合计 {sum(x['killed'] for x in kills)}/"
          f"{sum(x['n_high'] for x in kills)}")


if __name__ == "__main__":
    main()
