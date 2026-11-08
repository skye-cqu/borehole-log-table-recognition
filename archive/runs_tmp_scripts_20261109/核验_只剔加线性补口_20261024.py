# 一次性:核验 20261024 只剔+线性补口重跑。
# 1) extends = 备份原状 + 且仅 + 本线线性补口点(逐点落在该补口拟合直线上);
# 2) 6b 表头带 sep_pts x(带中点插值,与修复门A同口径)vs 修复前备份位移。
import json
import sys
from pathlib import Path

import numpy as np

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ))
from src.table import col_line_repair as clr  # noqa: E402

RECON = PROJ / "runs/table_reconstruct"
BAK = PROJ / "rollback/列线修复前_20261023"
BAD = 0
for c in clr.ALLOW:
    cur = json.loads((RECON / f"钻孔柱状图{c}_分割线.json").read_text(encoding="utf-8"))
    bak = json.loads((BAK / f"钻孔柱状图{c}_分割线.json").read_text(encoding="utf-8"))
    rep = cur.get(clr.REPAIR_TAG, {})
    n_rm = n_veto = n_lf = n_skip = ext_bad = 0
    for lr in rep.get("lines", []):
        n_rm += sum(len(sp.get("removed_frags") or []) for sp in lr.get("spans", []))
        n_veto += sum(1 for sp in lr.get("spans", []) if sp.get("action") == "vetoed")
        fills = []
        for f in lr.get("linear_fills", []):
            if "fit" not in f:
                n_skip += 1
                continue
            h0, h1 = f["linear_fill"]
            if "frame_join" in f:       # 接框段补到交点 y,范围按方向扩
                jy = f["frame_join"][1]
                h0, h1 = (h0, int(jy)) if jy > h1 else (int(jy), h1)
            fills.append(((h0, h1), f["fit"]))
        n_lf += len(fills)
        # 本线不变式:备份老外延一个不少;新增点逐点落在本线账内某条拟合线上
        i = next(i for i, l in enumerate(cur["lines"])
                 if l.get("index") == lr.get("index") and l.get("name") == lr.get("name"))
        ec = cur["lines"][i].get("extends") or []
        eb = bak["lines"][i].get("extends") or []
        fits = [(k, b) for _, (k, b) in fills]
        eb_keys = {}
        for p in eb:
            eb_keys[(round(float(p[0]), 4), round(float(p[1]), 4))] = \
                eb_keys.get((round(float(p[0]), 4), round(float(p[1]), 4)), 0) + 1
        ec_keys = {}
        for p in ec:
            key = (round(float(p[0]), 4), round(float(p[1]), 4))
            ec_keys[key] = ec_keys.get(key, 0) + 1
            if eb_keys.get(key, 0) > 0:
                eb_keys[key] -= 1        # 老点
            else:                        # 新点:必须落在账内某条拟合线上
                if not any(abs(float(p[0]) - (k * float(p[1]) + b)) <= 0.5
                           for k, b in fits):
                    ext_bad += 1
        leftover = sum(eb_keys.values())
        if leftover:
            ext_bad += leftover
            print(f"  {c} line{i}: 备份老外延有 {leftover} 点被动过")
    hmb = json.loads((PROJ / f"rollback/表头映射修复前_20261023/钻孔柱状图{c}_表头映射.json")
                     .read_text(encoding="utf-8"))
    hmc = json.loads((RECON / f"钻孔柱状图{c}_表头映射.json").read_text(encoding="utf-8"))
    ymid = (hmc["band"][0] + hmc["band"][1]) / 2.0
    bm = {(s["kind"], s.get("index")): float(np.interp(ymid, s["ys"], s["xs"]))
          for s in hmb["sep_pts"]}
    cm = {(s["kind"], s.get("index")): float(np.interp(ymid, s["ys"], s["xs"]))
          for s in hmc["sep_pts"]}
    drift = max((abs(bm[k] - cm[k]) for k in bm if k in cm), default=0.0)
    n_extra = len(set(cm) - set(bm))
    # 带中点位移≤2px:剔除误收碎片后 interp 括区微移(方向=向真车道),量级=噪声
    ok = ext_bad == 0 and drift <= 2.0 and n_extra == 0
    BAD += 0 if ok else 1
    print(f"{c}: 线性补口 {n_lf}(弃 {n_skip}) 剔碎片 {n_rm} 否决span {n_veto} "
          f"extends违例 {ext_bad} 6b带中点位移 {round(drift, 2)}px 新增界 {n_extra} "
          f"{'OK' if ok else '<<BAD'}")
print("---", "ALL OK" if BAD == 0 else f"{BAD} 图 BAD")
sys.exit(1 if BAD else 0)
