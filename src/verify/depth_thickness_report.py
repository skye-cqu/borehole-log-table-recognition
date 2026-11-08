# -*- coding: utf-8 -*-
"""判定 6 只读验证:层厚=相邻深度差、真厚=层厚×cos(倾角),对 26 份已核验还原 Excel 出实测数字。

用法:python src/verify/depth_thickness_report.py   (只读数据,报告写 runs/verify_content/)
"""
import json
import sys
from pathlib import Path

import openpyxl

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core import paths
from src.verify.content_check import check_rows, parse_dip, parse_numbers

STEMS_ALL = [str(s) for s in range(1015, 1045)]
BANDS = [0.02, 0.05, 0.11]   # 米:0.02=两位小数四舍五入界;0.05/0.11 观察分布用


def _pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def _dist(abs_values) -> dict:
    vals = sorted(abs_values)
    n = len(vals)
    out = {"n": n}
    if n:
        import statistics
        out["median"] = round(statistics.median(vals), 4)
        out["p95"] = round(vals[min(n - 1, int(0.95 * n))], 4)
        for b in BANDS:
            out[f"le_{b}"] = sum(1 for v in vals if v <= b)
            out[f"le_{b}_pct"] = _pct(out[f"le_{b}"], n)
    return out


def load_rows(xlsx_path) -> list:
    """读层数据行。煤层标志层号行整行右移一格(层号占 C、深度在 D、层厚在 E),
    信号=C 恰为单个 ≤60 整数、且 D 首值越过深度梯而 C 末值未越过(表头行 prev_d=0 恒不触发)。"""
    ws = openpyxl.load_workbook(xlsx_path, data_only=True).worksheets[0]
    rows = []
    prev_d = 0.0
    for row in ws.iter_rows(min_row=2, values_only=True):
        c, dd, e = parse_numbers(row[2]), parse_numbers(row[3]), parse_numbers(row[4])
        shifted = (len(c) == 1 and c[0] <= 60 and prev_d > 0
                   and dd and dd[0] > prev_d and (not c or c[-1] <= prev_d))
        if shifted:
            rows.append({"d": dd, "t": e, "z": parse_numbers(row[6]),
                         "dip": parse_dip(row[5])})
            ladder = dd
        else:
            rows.append({"d": c, "t": dd, "z": parse_numbers(row[6]),
                         "dip": parse_dip(row[5])})
            ladder = c
        if not ladder and not dd:
            rows.pop()                                # 深度层厚全空:非数据行
        elif ladder:
            prev_d = max(prev_d, ladder[-1]) if ladder[-1] > prev_d else prev_d
    return rows


def main() -> None:
    files = sorted(paths.RUNS_DIR.glob("table_reconstruct/钻孔柱状图*_还原.xlsx"))
    stems = [p.stem.replace("钻孔柱状图", "").split("_")[0] for p in files]
    per_file, all_abs, all_dip_abs, all_nodip, files_res = {}, [], [], [], []
    for p, stem in zip(files, stems):
        res = check_rows(load_rows(p))
        files_res.append((stem, res))
        abs_v = [r["abs"] for r in res["records"]]
        dip_v = [r["abs"] for r in res["dip_records"]]
        all_abs += abs_v
        all_dip_abs += dip_v
        all_nodip += res["z_vs_t_nodip"]
        per_file[stem] = {
            "layers_checked": res["layers_checked"], "unpaired_rows": res["unpaired_rows"],
            "n_viol_011": sum(1 for v in abs_v if v > 0.11),
            "dip_checked": res["dip_checked"],
            "dip_viol_005": sum(1 for v in dip_v if v > 0.05),
        }
    worst = sorted(((v, k, r) for k, f in per_file.items() for r in
                    [next(x for x in [None])] ), strict=False) if False else None
    report = {
        "schema": "content_crosscheck_v1", "date": "2026-09-14",
        "source": "runs/table_reconstruct/钻孔柱状图*_还原.xlsx(旧轮 OCR,26 份)",
        "stems_present": stems, "stems_missing": [s for s in STEMS_ALL if s not in stems],
        "aggregate": {
            "layers_checked": len(all_abs),
            "thickness_eq_depth_diff": _dist(all_abs),
            "dip_checked": len(all_dip_abs),
            "true_thick_eq_t_cos_dip": _dist(all_dip_abs),
            "z_vs_t_nodip": _dist(all_nodip),
        },
        "per_file": per_file,
    }
    out_dir = paths.VERIFIED_CONTENT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "深度层厚互证_报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    a = report["aggregate"]["thickness_eq_depth_diff"]
    d = report["aggregate"]["true_thick_eq_t_cos_dip"]
    # 行首层(j=0,跨行边界)vs 行内子层(j>=1)分组——边界断裂与行内自洽分开计量
    j0 = [r for f, res in files_res for r in res["records"] if r["j"] == 0]
    jn = [r for f, res in files_res for r in res["records"] if r["j"] >= 1]
    g0 = _dist([r["abs"] for r in j0])
    gn = _dist([r["abs"] for r in jn])
    report["aggregate"]["row_start_j0"] = g0
    report["aggregate"]["within_row_j1p"] = gn
    print(f"文件: {len(files)}/30 份,缺 {report['stems_missing']}")
    print(f"层厚=深度差: 检查 {a['n']} 层 | ≤0.02m: {a['le_0.02']} ({a['le_0.02_pct']}%) "
          f"| ≤0.05: {a['le_0.05']} ({a['le_0.05_pct']}%) | ≤0.11: {a['le_0.11']} "
          f"({a['le_0.11_pct']}%) | 中位 {a['median']}m, p95 {a['p95']}m")
    print(f"  行首层 j0:  {g0['n']} 层 | ≤0.11: {g0['le_0.11']} ({g0['le_0.11_pct']}%)")
    print(f"  行内 j≥1:  {gn['n']} 层 | ≤0.11: {gn['le_0.11']} ({gn['le_0.11_pct']}%)")
    if d["n"]:
        print(f"真厚=层厚×cos(倾角): 检查 {d['n']} 层 | ≤0.02: {d['le_0.02']} "
              f"({d['le_0.02_pct']}%) | ≤0.05: {d['le_0.05']} ({d['le_0.05_pct']}%) "
              f"| 中位 {d['median']}m")
    print(f"报告 → {out_dir / '深度层厚互证_报告.json'}")


if __name__ == "__main__":
    main()
