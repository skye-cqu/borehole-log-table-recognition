"""时代列问题全量普查(30 张)——只查问题,不修。

每图产出:
- 时代列墨迹线总数(条纹判据: 墨占比≥0.5 且最长连续墨≥55% 条带宽;密度过滤剔文字笔画)
- 其中: 已检出为行 / 漏检(有墨无行)
- 已检出为行的: 西端缺口 px;缺口内阶段4 段标签与今日管线状态(被clip裁/幸存未入链/仅suspect/仅noise/无)
- 交付层: _还原.xlsx 时代列非空率与碎片度
"""
import json, sys, glob, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import numpy as np
import cv2
from src.core import paths
from src.table import track_rows as tr

B = paths.RUNS_DIR / "table_reconstruct"
INK = 210          # 淡线灰度口径(背景 221~227)


def col0_curve(stem, col0_src):
    d = json.loads((B / f"{stem}_分割线.json").read_text(encoding="utf-8"))
    for ln in d["lines"]:
        if ln.get("src") == col0_src and ln.get("pts"):
            p = np.array([[q[1], q[0]] for q in ln["pts"]], float)   # (y,x)
            return p[np.argsort(p[:, 0])]
    return None


def row_y_at(r, x):
    p = np.asarray(r["poly"], float)
    if x >= p[0, 0]:
        return float(np.interp(x, p[:, 0], p[:, 1]))
    for j in range(1, len(p)):
        if p[j, 0] - p[0, 0] >= 50:
            k = (p[j, 1] - p[0, 1]) / (p[j, 0] - p[0, 0])
            return float(p[0, 1] + k * (x - p[0, 0]))
    return float(p[0, 1])


def census(stem):
    d = json.loads((B / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    rows = d["rows"]
    fr = tr.table_frame(stem)
    if fr is None or not rows:
        return None
    L, R = fr
    Ls = np.array(sorted(L.tolist()))
    c = json.loads((B / f"{stem}_列结构定稿.json").read_text(encoding="utf-8"))
    col0_src = c["columns"][0]["src"] if c["columns"] else None
    C0 = col0_curve(stem, col0_src)
    if C0 is None:
        return None
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    ink = gray < INK
    y_lo = int(min(r["y_at_mid"] for r in rows)) - 80
    y_hi = int(max(r["y_at_mid"] for r in rows)) + 80

    # 条带内逐 y 墨占比与最长连续墨(条带 = [L(y)+12, col0(y)-15])
    ys = np.arange(max(y_lo, 0), min(y_hi, gray.shape[0]))
    frac = np.full(len(ys), np.nan)
    runf = np.full(len(ys), np.nan)
    for i, y in enumerate(ys):
        x0 = int(np.interp(y, Ls[:, 0], Ls[:, 1])) + 12
        x1 = int(np.interp(y, C0[:, 0], C0[:, 1])) - 15
        if x1 - x0 < 25:
            continue
        v = ink[y, x0:x1]
        frac[i] = v.mean()
        # 最长连续墨游程
        best = cur = 0
        for t in v:
            cur = cur + 1 if t else 0
            best = max(best, cur)
        runf[i] = best / (x1 - x0)
    ok = (frac >= 0.5) & (runf >= 0.55)
    # 聚成线候选(间隔≤3 y 合并), 密度过滤: 90px 内 ≥3 候选 = 文字笔画簇,剔
    cand = []
    i = 0
    while i < len(ys):
        if ok[i]:
            j = i
            while j + 1 < len(ys) and ok[j + 1]:
                j += 1
            seg = slice(i, j + 1)
            w = frac[seg]
            cand.append((float(np.average(ys[seg], weights=w)), float(np.nanmax(frac[seg])), j - i + 1))
            i = j + 1
        else:
            i += 1
    dens = []
    for k, (yc, f, w) in enumerate(cand):
        near = sum(1 for (y2, _, _) in cand if abs(y2 - yc) <= 90)
        dens.append(near)
    cand = [(yc, f) for (yc, f, w), dn in zip(cand, dens) if dn < 3]
    # 劈裂合并: ≤14px 的相邻候选 = 同一条线(粗线/淡段劈开), 按占比加权并一条
    merged = []
    for yc, f in sorted(cand):
        if merged and yc - merged[-1][0] <= 14:
            y0, f0 = merged[-1]
            merged[-1] = ((y0 * f0 + yc * f) / (f0 + f), max(f0, f))
        else:
            merged.append((yc, f))
    cand = merged

    # 候选 ↔ 行 匹配
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    hsegs = [s for s in cj["lines"] if s["direction"] == "horizontal"]
    matched, missed = [], []
    row_taken = {}
    for yc, f in cand:
        x0 = float(np.interp(yc, Ls[:, 0], Ls[:, 1])) + 12
        x1 = float(np.interp(yc, C0[:, 0], C0[:, 1])) - 15
        xm = (x0 + x1) / 2
        hit = min(rows, key=lambda r: abs(row_y_at(r, xm) - yc))
        dy = abs(row_y_at(hit, xm) - yc)
        if dy <= 14:
            row_taken.setdefault(id(hit), [hit, []])[1].append(yc)
        else:
            missed.append((round(yc), round(f, 2), round(dy)))
    matched = [(v[0], v[1][0]) for v in row_taken.values()]
    # 已匹配行的缺口与段普查
    detail = []
    for r, yc in matched:
        p = np.asarray(r["poly"], float)
        Ly = float(np.interp(yc, Ls[:, 0], Ls[:, 1]))
        short = p[0, 0] - Ly
        zone = (Ly - 10, p[0, 0] + 8)
        lab = {"high_out": 0, "high_in": 0, "suspect": 0, "noise": 0}
        for s in hsegs:
            xs = [q[0] for q in s["points"]]
            if max(xs) < zone[0] or min(xs) > zone[1]:
                continue
            sy = float(np.median([q[1] for q in s["points"]]))
            if abs(sy - yc) > 14:
                continue
            lb = s["label"]
            if lb == "high":
                q = tr.clip_to_frame(s["points"], *fr)
                if q is None or len(q) < 2:
                    lab["high_out"] += 1        # 今日被 clip 裁掉
                elif s["id"] in r["segment_ids"]:
                    lab["high_in"] += 1
                else:
                    lab["high_out"] += 2        # 幸存但未入链(计 2 类)
            else:
                lab[lb] = lab.get(lb, 0) + 1
        detail.append({"y": round(yc), "short": round(short), **lab})
    return {"n_rows": len(rows), "n_cand": len(cand), "n_matched": len(matched),
            "n_missed": len(missed), "missed": missed, "detail": detail}


def xlsx_stat(stem_num):
    fs = glob.glob(str(B / f"钻孔柱状图{stem_num}_还原.xlsx"))
    if not fs:
        return "无xlsx"
    import openpyxl
    wb = openpyxl.load_workbook(fs[0], read_only=True)
    ws = wb.active
    hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    ci = next((i for i, h in enumerate(hdr) if h and "时代" in str(h)), None)
    if ci is None:
        return "无时代列"
    vals = [r[ci] for r in ws.iter_rows(min_row=2, values_only=True)]
    ne = [str(v).strip() for v in vals if v not in (None, "")]
    if not ne:
        return "全空"
    frag = sum(1 for v in ne if len(v) <= 2) / len(ne)
    return f"非空{len(ne)}/{len(vals)} distinct{len(set(ne))} 碎片≤2字占{frag:.0%}"


if __name__ == "__main__":
    tot = {"cand": 0, "matched": 0, "missed": 0, "short_med": []}
    print(f"{'图':>5} {'行':>4} {'时代界线':>5} {'检出':>4} {'漏检':>4} {'西端缺口px(中位)':>12}  缺口段况(high裁/幸存未链/suspect/noise)  xlsx时代列")
    for f in sorted(B.glob("钻孔柱状图*_行判定.json")):
        stem = f.name[:-9]
        r = census(stem)
        num = stem[-4:]
        if r is None:
            print(f"{num:>5}  框不可信/无行, 跳过   {xlsx_stat(num)}")
            continue
        sh = sorted(x["short"] for x in r["detail"])
        med = sh[len(sh)//2] if sh else -1
        agg = {"裁": 0, "未链": 0, "sus": 0, "noi": 0}
        for x in r["detail"]:
            agg["裁"] += x["high_out"] > 0
            agg["未链"] += x.get("high_out", 0) >= 2
            agg["sus"] += x["suspect"] > 0
            agg["noi"] += x["noise"] > 0
        tot["cand"] += r["n_cand"]; tot["matched"] += r["n_matched"]; tot["missed"] += r["n_missed"]
        if med >= 0: tot["short_med"].append(med)
        print(f"{num:>5} {r['n_rows']:4} {r['n_cand']:9} {r['n_matched']:4} {r['n_missed']:4} "
              f"{med:12}  裁{agg['裁']}/未链{agg['未链']}/sus{agg['sus']}/noi{agg['noi']:3}  {xlsx_stat(num)}")
        if r["n_missed"]:
            print(f"        漏检线 y: {[m[0] for m in r['missed']][:14]}")
    sm = tot["short_med"]
    print(f"\n合计: 时代界线 {tot['cand']}, 检出 {tot['matched']}, 漏检 {tot['missed']}; "
          f"缺口中位 跨图中位 {int(np.median(sm))}px")
