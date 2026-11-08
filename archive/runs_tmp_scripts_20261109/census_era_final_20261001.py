"""时代列问题终版清单(30 张, 行基扫描)——只查问题。

每图: 有时代列墨的行数(墨占比≥0.5, 阈值210, y±8 跟随行线两点半径外推) + 西端缺口 +
缺口内阶段4 段逐段分类(今日被clip裁/幸存未入链/仅suspect/仅noise/无段) + xlsx 时代列状态。
"""
import json, sys, glob, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import numpy as np
import cv2
from src.core import paths
from src.table import track_rows as tr

B = paths.RUNS_DIR / "table_reconstruct"


def row_y_at(p, x):
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
    if not c["columns"]:
        return None
    c0 = c["columns"][0]["x_at_mid"]
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    hsegs = [s for s in cj["lines"] if s["direction"] == "horizontal"]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    era = []
    for r in rows:
        p = np.asarray(r["poly"], float)
        ok = tot = 0
        for x in range(int(p[0, 0]) - 1, 100, -1):
            y = row_y_at(p, x)
            Ly = float(np.interp(y, Ls[:, 0], Ls[:, 1]))
            if x < Ly + 15 or x > c0 - 25:
                continue
            tot += 1
            if gray[max(int(y - 8), 0):int(y + 9), x].min() < 210:
                ok += 1
        if tot >= 15 and ok / tot >= 0.5:
            era.append((r, p, ok / tot))
    det = []
    for r, p, ratio in era:
        ym = r["y_at_mid"]
        Ly = float(np.interp(ym, Ls[:, 0], Ls[:, 1]))
        short = float(p[0, 0]) - Ly
        zone = (Ly - 10, float(p[0, 0]) - 2)          # 严格西区: 不含行自身链段
        cl = set()
        for s in hsegs:
            xs = [q[0] for q in s["points"]]
            if max(xs) < zone[0] or min(xs) > zone[1]:
                continue
            sx = float(np.median(xs))
            if abs(row_y_at(p, min(sx, float(p[0, 0]))) - float(np.median([q[1] for q in s["points"]]))) > 16:
                continue
            lb = s["label"]
            if lb != "high":
                cl.add(lb)
                continue
            q = tr.clip_to_frame(s["points"], *fr)
            if q is None or len(q) < 2:
                cl.add("killed")
            elif s["id"] not in r["segment_ids"]:
                cl.add("unchained")
        # 单归属(按证据强度): 有可回收 high 段 > high 未入链 > 只有低置信段 > 无段
        if "killed" in cl:
            pri = "killed"
        elif "unchained" in cl:
            pri = "unchained"
        elif cl:
            pri = "low_only"
        else:
            pri = "empty"
        det.append({"y": round(ym), "short": round(short), "pri": pri})
    return {"n_rows": len(rows), "era": det}


def xlsx_stat(num):
    fs = glob.glob(str(B / f"钻孔柱状图{num}_还原.xlsx"))
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
    return f"非空{len(ne)}/{len(vals)} 碎片{frag:.0%}"


if __name__ == "__main__":
    T = {"era": 0, "short": [], "killed": 0, "unchained": 0, "low_only": 0, "empty": 0}
    print(f"{'图':>5} {'行':>4} {'时代墨行':>5} {'缺口中位':>6}  单归属成因(裁死/未链/仅低信/无段)  xlsx时代列")
    for f in sorted(B.glob("钻孔柱状图*_行判定.json")):
        stem = f.name[:-9]
        num = stem[-4:]
        r = census(stem)
        if r is None:
            print(f"{num:>5} {xlsx_stat(num)} (框不可信或无列结构)")
            continue
        sh = sorted(x["short"] for x in r["era"])
        med = int(sh[len(sh) // 2]) if sh else -1
        n = {"killed": 0, "unchained": 0, "low_only": 0, "empty": 0}
        for x in r["era"]:
            n[x["pri"]] += 1
            T[x["pri"]] += 1
        T["era"] += len(r["era"]); T["short"] += sh
        print(f"{num:>5} {r['n_rows']:4} {len(r['era']):7} {med:8}  "
              f"{n['killed']}/{n['unchained']}/{n['low_only']}/{n['empty']}  {xlsx_stat(num)}")
    print(f"\n合计: 时代墨行 {T['era']} (29图), 缺口中位 {int(np.median(T['short']))}px, "
          f"范围 {min(T['short'])}~{max(T['short'])}px")
    print(f"单归属成因: 缺口内有high段但今日被clip裁死 {T['killed']} 行 / high段幸存未入链 {T['unchained']} 行 / "
          f"只有suspect/noise段 {T['low_only']} 行 / 完全无段 {T['empty']} 行")
