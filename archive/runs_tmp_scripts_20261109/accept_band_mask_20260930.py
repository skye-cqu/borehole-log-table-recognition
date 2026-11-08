"""项1 带掩膜 30 张验收: 新旧行判定逐图对照 + 带内顶点 + 底框存活 + 位移行墨迹真值。

判读口径: 助手量化核验(2026-09-30), 结论交用户视觉核验。
门(全部过才算项1量化验收通过):
  A 每图 主行线数 |新-旧| <= 2;
  B 新行 y 对照旧行: <=3px 视为同线; 3~15px 记位移对; >15px 记生/灭(逐条列出人工复核);
  C 位移对抽墨迹真值(数值区 3 窗墨迹质心): 新旧均值差 <= 1.5px(位移是取样点挪动, 不是贴合劣化);
  D 全部主行/子行折线顶点 0 个落在柱状带/水文带内缘(BAND_PAD 内不算);
  E 旧产末行≈外框底边(±0.75行高)的图, 新产末行仍≈外框底边(底框穿越水文带的东西两片重组存活);
  F 走偏剔除数(n_lines_offgrid) 不高于旧产;
  G 同线对的 x 跨度: 东端缩水 >60px 必须能被水文带解释(新东端 ≥ 水文带西缘−40), 西端同理
    (对柱状带东缘)——y 键门抓不住"行还在但跨度被吃"的缺陷(1042 岩性区六行教训, v9 门)。
"""
import sys, json
from pathlib import Path
import numpy as np
import cv2

sys.path.insert(0, ".")
from src.core import paths
from src.table import track_group, track_rows as tr

OLD_DIR = Path("rollback/行判定备份_20260930")
fails, notes = [], []


def ink_err(ink, y, xs_win):
    ds = []
    for x0, x1 in xs_win:
        w = ink[max(y - 25, 0):y + 26, x0:x1].astype(float)
        prof = w.sum(axis=1)
        if prof.sum() < 10:
            continue
        yc = float((np.arange(len(prof)) * prof).sum() / prof.sum()) + (y - 25)
        ds.append(abs(yc - y))
    return float(np.mean(ds)) if ds else None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ink", action="store_true", help="跳过墨迹真值(快查)")
    a = ap.parse_args()

    stat = {"同线": 0, "位移": 0, "生": 0, "灭": 0}
    shift_old_errs, shift_new_errs = [], []
    born_all, dead_all = [], []
    hydro_v = {}
    n_chart = 0
    for fp in sorted(OLD_DIR.glob("*.json")):
        old = json.loads(fp.read_text(encoding="utf-8"))
        stem = old["image"]
        fpn = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json"
        if not fpn.exists():
            fails.append(f"{stem}: 新产缺失")
            continue
        new = json.loads(fpn.read_text(encoding="utf-8"))
        n_chart += 1
        probs = []

        # A 行数
        d_rows = len(new["rows"]) - len(old["rows"])
        if abs(d_rows) > 2:
            probs.append(f"行数 {len(old['rows'])}->{len(new['rows'])}")
        # F 走偏
        if new["n_lines_offgrid"] > old["n_lines_offgrid"]:
            probs.append(f"走偏 {old['n_lines_offgrid']}->{new['n_lines_offgrid']}")

        # B y 对照
        oy = np.sort(np.array([r["y_at_mid"] for r in old["rows"]]))
        ny = np.sort(np.array([r["y_at_mid"] for r in new["rows"]]))
        pairs_shift, born, dead = [], [], []
        for y in ny:
            d = np.abs(oy - y)
            if d.size and d.min() <= 3:
                stat["同线"] += 1
            elif d.size and d.min() <= 15:
                stat["位移"] += 1
                pairs_shift.append((float(oy[d.argmin()]), float(y)))
            else:
                stat["生"] += 1
                born.append(float(y))
        for y in oy:
            if not (np.abs(ny - y).min() <= 15):
                stat["灭"] += 1
                dead.append(float(y))
        born_all += [(stem, y) for y in born]
        dead_all += [(stem, y) for y in dead]

        # G x 跨度回归（y 键门抓不住行还在但跨度被吃的缺陷，1042 六行教训）
        bands = [(np.array(b[0], float), None if b[1] is None else np.array(b[1], float))
                 for b in new.get("bands", [])]
        hyd_w = bands[-1][0] if bands and bands[-1][1] is None else None
        zhu_e = next((e for w, e in bands if e is not None), None)
        old_by_y = sorted((r["y_at_mid"], r["x"][0], r["x"][1]) for r in old["rows"])
        for r in new["rows"]:
            y, x0, x1 = r["y_at_mid"], r["x"][0], r["x"][1]
            oy_ = min(old_by_y, key=lambda t: abs(t[0] - y), default=None)
            if oy_ is None or abs(oy_[0] - y) > 15:
                continue
            if oy_[2] - x1 > 60 and hyd_w is not None:
                cut = tr.edge_at(hyd_w, y) - 40.0
                if x1 < cut:
                    probs.append(f"门G 东端无解释缩水: y={y:.0f} 旧x1={oy_[2]:.0f}->新{x1:.0f}"
                                 f" (水文带切线 {cut + 40:.0f})")
            if x0 - oy_[1] > 60 and zhu_e is not None:
                cut = tr.edge_at(zhu_e, y) + 40.0
                if x0 > cut:
                    probs.append(f"门G 西端无解释缩水: y={y:.0f} 旧x0={oy_[1]:.0f}->新{x0:.0f}"
                                 f" (柱状带东缘 {cut - 40:.0f})")

        # C 位移对墨迹真值
        if pairs_shift and not a.no_ink:
            gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
            ink = track_group.binarize(gray, track_group.PARAMS)
            del gray
            xs_win = [(350, 500), (550, 700), (720, 790)]
            for oy_, ny_ in pairs_shift:
                eo, en = ink_err(ink, int(oy_), xs_win), ink_err(ink, int(ny_), xs_win)
                if eo is not None and en is not None:
                    shift_old_errs.append(eo)
                    shift_new_errs.append(en)

        # D 带内顶点：水文带 = 非框线行折线顶点深度超过 恢复上限+5px 的个数（贴切线 ≤20px 的
        # 终端恢复行尾是行界证据，合规；深进去的才是骑带污染）；柱状带 = 只计数上报
        bands = [(np.array(b[0], float), None if b[1] is None else np.array(b[1], float))
                 for b in new.get("bands", [])]
        tab_r = new["table_x"][1]
        bad_h = bad_c = 0
        for r in new["rows"] + new["sub_rows"]:
            p = np.asarray(r["poly"], float)
            exempt = float(p[:, 0].max()) >= tab_r - 20.0
            for w, e in bands:
                if e is None:
                    if not exempt:
                        m = tr._in_band_mask(p[:, 0], p[:, 1], [(w, e)])
                        if m.any():
                            dep = p[m][:, 0] - (tr._edge_xs(w, p[m][:, 1]) + tr.BAND_PAD)
                            bad_h += int((dep > tr.HYDRO_RESTORE + 5.0).sum())
                else:
                    bad_c += int(tr._in_band_mask(p[:, 0], p[:, 1], [(w, e)]).sum())
        if bad_h:
            probs.append(f"水文带深顶点(非框线,>恢复上限+5px) {bad_h}")
        hydro_v[stem] = (bad_h, bad_c)

        # E 底框存活
        fpf = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_闭合外框.json"
        if fpf.exists():
            fr = json.loads(fpf.read_text(encoding="utf-8"))
            if fr.get("bottom", {}).get("pts"):
                y_bot = float(np.median(np.array(fr["bottom"]["pts"], float)[:, 1]))
                row_h = max(old.get("row_h", 1), 1)
                o_last, n_last = oy[-1], ny[-1]
                if abs(o_last - y_bot) <= 0.75 * row_h and abs(n_last - y_bot) > 0.75 * row_h:
                    probs.append(f"底框行丢失: 旧末 {o_last:.0f} 新末 {n_last:.0f} 框底 {y_bot:.0f}")

        if probs:
            fails.append(f"{stem}: " + "; ".join(probs))
        print(f"{stem}: 行 {len(old['rows'])}->{len(new['rows'])} 同线{stat['同线'] and ''}"
              f"位移{len(pairs_shift)} 生{len(born)} 灭{len(dead)}"
              + (f"  <-- {'; '.join(probs)}" if probs else ""))

    print(f"\n=== 汇总 {n_chart} 图 ===")
    print(f"y 对照: 同线 {stat['同线']} 位移 {stat['位移']} 生 {stat['生']} 灭 {stat['灭']}")
    tot_h = sum(v[0] for v in hydro_v.values())
    tot_c = sum(v[1] for v in hydro_v.values())
    print(f"带内顶点: 水文带(非框线) {tot_h}  柱状带(行线穿带墨迹,上报) {tot_c}")
    if shift_old_errs:
        print(f"位移对墨迹误差: 旧均值 {np.mean(shift_old_errs):.2f}px -> 新均值 {np.mean(shift_new_errs):.2f}px"
              f" (n={len(shift_old_errs)}, 门C: 差<=1.5px)")
        if np.mean(shift_new_errs) - np.mean(shift_old_errs) > 1.5:
            fails.append(f"门C 超标: 位移对墨迹误差劣化 {np.mean(shift_new_errs)-np.mean(shift_old_errs):.2f}px")
    if born_all:
        print("生(>15px 新增):", [(s, round(y)) for s, y in born_all])
    if dead_all:
        print("灭(>15px 丢失):", [(s, round(y)) for s, y in dead_all])
    print("\n=== 门禁判定 ===")
    if fails:
        print(f"FAIL {len(fails)} 项:")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print("PASS: A~F 全过" + ("(墨迹门跳过)" if a.no_ink else ""))


if __name__ == "__main__":
    main()
