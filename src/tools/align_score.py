# -*- coding: utf-8 -*-
"""只读对标打分:候选整合表 vs 用户参考表(1015-1044)。

与 src/table/compare_ref.py 同参同判(行配对/数值容差 0.005/文本剔标点口径),
但**不写任何 xlsx/CSV**——autoresearch 冻结基准专用。差异:
  1. 打分对象是 paths.AUTORESEARCH_CANDIDATE_DIR(规则引擎产出),非 FINALIZE_FULL_DIR;
  2. 行区间重放与 compare_ref 完全同码路径,结果缓存到 AUTORESEARCH_ROWCACHE
     (结构层冻结,缓存才可复用;行数对不上时对该图现算重缓);
  3. 打印 METRIC 行供 .auto/measure.sh 解析,per-chart 与 per-role 明细在 METRIC 之前。

CLI: python src/tools/align_score.py [候选目录]
"""
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.table.compare_ref import cell_diff, pair_rows, ROLE_REF_COL, TEXT_COLS

ROLE_NAME = {"era": "地质时代", "layer": "煤层/标志层号", "depth": "深度",
             "thick": "层厚", "length": "采长", "dip": "倾角",
             "true_thick": "真厚", "desc": "岩性描述"}


def _row_ivs(stem):
    """行区间重放——与 compare_ref.compare_chart 逐行同参(2026-10-28 切源版)。"""
    from openpyxl import load_workbook
    from src.table.era_chars import _load_inputs
    from src.table.track_rows import row_y
    from src.table.finalize_tables import column_roles, drop_header_rows, unstuck_chain
    hm, rd = _load_inputs(stem)
    x_mid_tbl = sum(rd["table_x"]) / 2
    rr = [r for r in rd["rows"] if row_y(r, x_mid_tbl) >= hm["band"][1]]
    x = sum(hm["keep"][0]["x_in_band"]) / 2
    ys = [row_y(r, x) for r in rr]
    bwb = load_workbook(paths.REEMIT_DIR_20261023 / f"{stem}_还原.xlsx")
    bdata = [tuple(r)[:8] + (None,) * max(0, 8 - len(r))
             for r in bwb.active.iter_rows(values_only=True)]
    bdata, ys, _ = drop_header_rows(bdata, ys)
    bdata, ys, _, _ = unstuck_chain(bdata, ys, column_roles(bdata[0] if bdata else []))
    while bdata and not any(v is not None and str(v).strip() for v in (bdata[-1] or ())):
        bdata.pop()
        ys.pop()
    surg = set()   # 假行手术以校正账为准,不重推导(仅 1033 做过手术)
    csvp = paths.FINALIZE_FULL_DIR / f"{stem}_校正账.csv"
    if csvp.exists():
        for r in csv.DictReader(open(csvp, encoding="utf-8-sig")):
            if r.get("来源") == "假行归并" and r.get("列") == "整行":
                try:
                    surg.add(int(r["行"]))
                except ValueError:
                    pass
    kept = [i for i in range(len(ys) - 1) if i not in surg]
    return {k: (ys[i], ys[i + 1]) for k, i in enumerate(kept)}


def row_ivs_cached(stem, n_data, cache, cache_path):
    """行区间缓存:结构冻结才可复用;行数对不上=结构变了,现算重缓并告警。"""
    hit = cache.get(stem)
    if hit and hit.get("n") == n_data:
        return {int(k): tuple(v) for k, v in hit["ivs"].items()}, False
    ivs = _row_ivs(stem)
    if len(ivs) != n_data:
        raise RuntimeError(f"{stem} 行数不一致 xlsx={n_data} 行重放={len(ivs)}")
    cache[stem] = {"n": n_data, "ivs": {str(k): list(v) for k, v in ivs.items()}}
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return ivs, True


def score_chart(stem, cand_dir, ref_dir, cache, cache_path):
    """单图打分(只读):返回统计 dict 与 per-role 明细。"""
    from openpyxl import load_workbook
    from src.table.finalize_tables import column_roles
    wb = load_workbook(cand_dir / f"{stem}_整合.xlsx", read_only=True)
    _all = list(wb.active.iter_rows(values_only=True))
    wb.close()
    roles = column_roles(_all[0] if _all else [])
    idx_role = {v: k for k, v in roles.items()}
    data = _all[1:]
    while data and not any(v is not None and str(v).strip() for v in (data[-1] or ())):
        data.pop()   # 与重放同删草案尾部全空行(1032)
    ivs, recomputed = row_ivs_cached(stem, len(data), cache, cache_path)
    ref_path = ref_dir / f"{stem}_llm_corrected.xlsx"
    rwb = load_workbook(ref_path, read_only=True)
    rrows = list(rwb.active.iter_rows(values_only=True))
    rwb.close()
    hdr, rdata = rrows[0], rrows[1:]
    ref_ivs, ref_keep = [], []
    for j, r in enumerate(rdata):
        try:
            iv = (float(r[1]), float(r[2]))
        except (TypeError, ValueError):
            continue
        if iv[1] > iv[0]:
            ref_ivs.append(iv)
            ref_keep.append(j)
    pairs = pair_rows([ivs[i] for i in sorted(ivs)], ref_ivs)
    stat = {"diff": 0, "ours_empty": 0, "theirs_empty": 0}
    per_role = {ROLE_NAME[r]: {"n": 0, "equal": 0, "diff": 0,
                               "ours_empty": 0, "theirs_empty": 0}
                for r in sorted(set(idx_role.values()))}
    for i, j in pairs:
        rrow = rdata[ref_keep[j]]
        for k in sorted(idx_role):
            name = ROLE_NAME[idx_role[k]]
            rk = ROLE_REF_COL[idx_role[k]]
            ours_v = data[i][k] if len(data[i]) > k else None
            ref_v = rrow[rk] if len(rrow) > rk else None
            d = cell_diff(ours_v, ref_v, tol=0.005, text=idx_role[k] in
                          {"era", "layer", "desc"})
            pr = per_role[name]
            pr["n"] += 1
            if d == "equal":
                pr["equal"] += 1
            else:
                stat[d] = stat.get(d, 0) + 1
                pr[d] = pr.get(d, 0) + 1
    total = len(pairs) * len(idx_role)
    equal = total - stat["diff"] - stat["ours_empty"] - stat["theirs_empty"]
    return {"图": stem, "配对行": len(pairs), "比对格": total, "equal": equal,
            "diff": stat["diff"], "ours_empty": stat["ours_empty"],
            "theirs_empty": stat["theirs_empty"], "重放": recomputed,
            "per_role": per_role}


def main(argv):
    cand_dir = Path(argv[0]) if argv else paths.AUTORESEARCH_CANDIDATE_DIR
    ref_dir = paths.REF_XLSX_DIR_20261011 / "1015-1044"
    seed = paths.AUTORESEARCH_SEED_DIR
    src_glob = seed if seed.is_dir() and any(seed.glob("*_整合.xlsx")) else cand_dir
    stems = sorted(p.name[:-len("_整合.xlsx")] for p in src_glob.glob("*_整合.xlsx"))
    if not stems:
        print("FAIL 无候选整合表:", cand_dir)
        return 2
    cache_path = paths.AUTORESEARCH_ROWCACHE
    cache = (json.loads(cache_path.read_text(encoding="utf-8"))
             if cache_path.exists() else {})
    t0, summary, bad = time.time(), [], []
    for stem in stems:
        try:
            rep = score_chart(stem, cand_dir, ref_dir, cache, cache_path)
        except Exception as e:
            print(stem, "FAIL", repr(e)[:120])
            bad.append(stem)
            continue
        summary.append(rep)
        print(f"{stem} 配对{rep['配对行']} 格{rep['比对格']} 等{rep['equal']} "
              f"diff{rep['diff']} 我空{rep['ours_empty']} 参空{rep['theirs_empty']}"
              + (" [重放]" if rep["重放"] else ""))
    agg_role = {}
    for rep in summary:
        for name, pr in rep["per_role"].items():
            a = agg_role.setdefault(name, {"n": 0, "equal": 0, "diff": 0,
                                           "ours_empty": 0, "theirs_empty": 0})
            for k in a:
                a[k] += pr[k]
    tg = sum(r["比对格"] for r in summary)
    te = sum(r["equal"] for r in summary)
    td = sum(r["diff"] for r in summary)
    toe = sum(r["ours_empty"] for r in summary)
    tte = sum(r["theirs_empty"] for r in summary)
    num_roles = ["深度", "层厚", "采长", "倾角", "真厚"]
    txt_roles = ["地质时代", "煤层/标志层号", "岩性描述"]
    def _rate(names, field="equal"):
        n = sum(agg_role[x]["n"] for x in names)
        e = sum(agg_role[x][field] for x in names)
        return e / n if n else 0.0
    print(f"整体一致率: {te}/{tg} = {te / tg:.4f}" if tg else "无配对格")
    for name in sorted(agg_role):
        a = agg_role[name]
        print(f"  {name}: {a['equal']}/{a['n']} = {a['equal'] / max(1, a['n']) * 100:.2f}% "
              f"(diff{a['diff']} 我空{a['ours_empty']} 参空{a['theirs_empty']})")
    print(f"耗时 {time.time() - t0:.1f}s")
    if tg:
        print(f"METRIC align={te / tg:.4f}")
        print(f"METRIC align_num={_rate(num_roles):.4f}")
        print(f"METRIC align_txt={_rate(txt_roles):.4f}")
        print(f"METRIC diff={td}")
        print(f"METRIC ours_empty={toe}")
        print(f"METRIC theirs_empty={tte}")
    print(f"METRIC charts={len(summary)}/{len(stems)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
