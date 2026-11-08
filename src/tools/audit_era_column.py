# -*- coding: utf-8 -*-
"""时代列门禁(G1-G4):只读裁剪产物+原图+表头映射/行判定 json 独立重算,判分/修复分离。

不 import src/table/era_chars.py(裁剪器内部);共享的只有 rect_struct.strip_band 与
track_rows.row_y 两个基建函数。模式:
  era_chars 目录模式 = G1 墨迹收支 + G2 命名文法 + G3 名带区间 + G4 跨图一致
  xlsx 目录模式(基线) = 把交付表第 0 列非空碎片当单字名带跑 G2/G3/G4(修复标靶)
用法:
  python src/tools/audit_era_column.py runs/era_chars_20261010 [--strict]
  python src/tools/audit_era_column.py runs/table_reconstruct_重出_20261005_项④行线补全
违反 --strict 阈值退出 1;明细 CSV/JSON 落 runs/tmp/(审计惯例:docstring 用法+手工 argv)。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ---- 阈值(2026-10-10 五图试点实测回填,注释=推导链;None=只报数不判) ----
STRICT_RESID_RATE = 0.15    # G1 残墨率上限;试点实测 [0.033, 0.042, 0.073, 0.090, 0.146]
                            # (n=5,p90≈最大值 0.146,余量到 0.15;残墨=柱状图案边线渗入+字距杂点)
STRICT_VALID_RATE = 0.90    # G2 valid 率下限;试点实测 34/36=94.4%(失败项=已登记 OCR 层
                            # 漏字/误读:段/茅口P组),基线(按行切格)仅 3.1%
G4_MAX_SUBS = None          # G4=核验清单生成器(替换对交人/视觉LLM复核),不作硬门禁(计划T7口径)

# G2 文法判据自持实现(与 era_chars 同判据但独立:判分不信任修复方,故意不 import)
_ENDERS = "系群组段阶"
_QUAL = "上中下一二三四五"


def check_grammar(name):
    """G2 命名文法:(判定, 原因)。invalid=空/单字/含非CJK/末字非地层单位字;
    suspect=首字为段限定字 或 内部存在可断名边界(疑未分带);否则 valid。"""
    if not name or len(name) < 2:
        return "invalid", "空或单字"
    if any(not ("\u4e00" <= c <= "\u9fff") for c in name):
        return "invalid", "含非CJK"
    if name[-1] not in _ENDERS:
        return "invalid", "末字非地层单位字"

    def brk(k):
        """name[k] 后可断名?末字∈ENDERS 且非(组+限定字)。"""
        if name[k] not in _ENDERS:
            return False
        if name[k] == "组" and k + 1 < len(name) and name[k + 1] in _QUAL:
            return False
        return True

    if name[0] in _QUAL:
        return "suspect", "首字为段限定字,组名疑丢前文"
    if any(brk(k) for k in range(len(name) - 1)):
        return "suspect", "内部存在可断名边界,疑未分带"
    return "valid", ""


def _lev_align(a, b):
    """Levenshtein 对齐回溯:返回 [(a元素|None, b元素|None)...],同位对=相等或替换。"""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    pairs = []
    i, j = n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            pairs.append((a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            pairs.append((a[i - 1], None))
            i -= 1
        else:
            pairs.append((None, b[j - 1]))
            j -= 1
    pairs.reverse()
    return pairs


def check_cross_charts(chart_bands):
    """G4 跨图一致:两两名带序列对齐,两侧各自 valid 且不相等的名对 → 字级差异。"""
    import itertools
    problems = []
    for k1, k2 in itertools.combinations(sorted(chart_bands), 2):
        s1, s2 = chart_bands[k1], chart_bands[k2]
        for n1, n2 in _lev_align(s1, s2):
            if n1 is None or n2 is None or n1 == n2:
                continue
            if check_grammar(n1)[0] != "valid" or check_grammar(n2)[0] != "valid":
                continue                       # 替换对只在两侧各自 valid 时计数
            diffs = [f"{c1}/{c2}" for c1, c2 in _lev_align(n1, n2)
                     if c1 is not None and c2 is not None and c1 != c2]
            problems.append({"图对": f"{k1}/{k2}", "名对": f"{n1}|{n2}", "差异": diffs})
    return problems


# ---- CLI:独立重算(判分不调裁剪器,同判据分头实现) ----

def _rebuild_strip(stem, band_top):
    """从原图+表头映射/行判定 json 独立重算 (带内原始墨, 行线先验掩膜)。

    与裁剪器 era_strip 同判据、分头实现:行滤到表头底界下、条带顶钳 band_top、
    行线窄带=折线y ± (线宽半宽2px + pad2)。
    """
    import json
    import cv2
    from src.core import paths
    from src.table.rect_struct import strip_band
    from src.table.track_rows import row_y
    hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                        encoding="utf-8"))
    rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                        encoding="utf-8"))
    x_mid = sum(rd["table_x"]) / 2.0
    rows = [r for r in rd["rows"] if row_y(r, x_mid) >= hm["band"][1]]
    sp_l = hm["sep_pts"][hm["keep"][0]["left_sep"]]
    sp_r = hm["sep_pts"][hm["keep"][0]["right_sep"]]
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    y0 = max(int(max(sp_l["ys"][0], sp_r["ys"][0])), int(band_top))
    y1 = int(min(sp_l["ys"][-1], sp_r["ys"][-1]))
    band, _, x0i = strip_band(gray, y0, y1, (sp_l["ys"], sp_l["xs"]),
                              (sp_r["ys"], sp_r["xs"]), inset=3)
    line_mask = np.zeros_like(band)
    xs_cols = np.arange(x0i, x0i + band.shape[1])
    for r in rows:
        p = np.asarray(r["poly"], float)
        ly = np.interp(xs_cols, p[:, 0], p[:, 1])
        lo = np.floor(ly - 4).astype(int) - y0
        hi = np.ceil(ly + 4).astype(int) - y0
        for k in range(band.shape[1]):
            a, b = max(0, lo[k]), min(line_mask.shape[0], hi[k] + 1)
            if a < b:
                line_mask[a:b, k] = True
    return band, line_mask


def audit_era_dir(d):
    """era_chars 目录模式:逐图 G1/G1b/G2/G3,跨图 G4。返回 (逐图清单, G4清单)。"""
    import json
    per, names = [], {}
    for sub in sorted(p for p in d.iterdir() if p.is_dir()):
        pj = sub / "era_chars.json"
        if not pj.exists():
            continue
        prod = json.loads(pj.read_text(encoding="utf-8"))
        num = sub.name.replace("钻孔柱状图", "")
        boxes = [(c["y0"], c["y1"]) for c in prod["chars"]]
        band, line_mask = _rebuild_strip(sub.name, prod["strip_y0"])
        # 产物框是全图绝对 y,收支数组是条带相对行(row0=strip_y0)→ 转相对再记账
        boxes_rel = [(a - prod["strip_y0"], b - prod["strip_y0"]) for a, b in boxes]
        g1 = check_ink_accounting(band, line_mask, boxes_rel, pad=2)
        g1b = check_box_heights(boxes, prod["params"]["min_char_h"],
                                prod["params"]["max_char_h"])
        g2v = [check_grammar(b["name"]) for b in prod["bands"]]
        g2 = {"n": len(g2v),
              "valid": sum(v == "valid" for v, _ in g2v),
              "suspect": sum(v == "suspect" for v, _ in g2v),
              "invalid": sum(v == "invalid" for v, _ in g2v),
              "例": [f"{b['name']}({v})" for b, (v, _) in zip(prod["bands"], g2v)
                     if v != "valid"][:6]}
        g3 = check_bands_order([{**b, "rows": [b["y0"], b["y1"]]}
                                for b in prod["bands"]])
        names[num] = [b["name"] for b in prod["bands"]]
        per.append({"图号": num, "字块数": len(boxes), "名带数": len(prod["bands"]),
                    **g1, "G2": g2, "G3明细": g3, "G1b明细": g1b,
                    "preflight_ok": bool(prod["preflight"]["ok"])})
    return per, check_cross_charts(names)


def audit_xlsx_dir(d):
    """xlsx 基线模式:交付表第 0 列非空碎片当单字名带,跑 G2/G3/G4(修复标靶)。"""
    from openpyxl import load_workbook
    per, names = [], {}
    for f in sorted(d.glob("*_还原.xlsx")):
        num = f.name.replace("钻孔柱状图", "").replace("_还原.xlsx", "")
        ws = load_workbook(f, read_only=True).active
        frags = []
        for i, row in enumerate(ws.iter_rows(min_col=1, max_col=1, values_only=True)):
            if i == 0:
                continue                       # 表头"地质时代"
            v = row[0]
            if v is None or not str(v).strip():
                continue
            frags.append((i, str(v).strip()))
        g2v = [check_grammar(t) for _, t in frags]
        g3 = check_bands_order([{"name": t, "rows": [i]} for i, t in frags])
        names[num] = [t for _, t in frags]
        per.append({"图号": num, "碎片数": len(frags),
                    "valid": sum(v == "valid" for v, _ in g2v),
                    "suspect": sum(v == "suspect" for v, _ in g2v),
                    "invalid": sum(v == "invalid" for v, _ in g2v),
                    "例": [f"{t}({v})" for (_, t), (v, _) in zip(frags, g2v)
                           if v != "valid"][:6],
                    "G3明细": g3})
    return per, check_cross_charts(names)


def main(argv):
    import csv
    import json
    from src.core import paths
    if not argv:
        print(__doc__)
        return 2
    d = Path(argv[0])
    strict = "--strict" in argv[1:]
    is_era = d.is_dir() and any((s / "era_chars.json").exists() for s in d.iterdir())
    if is_era:
        per, g4 = audit_era_dir(d)
        tag = "时代列门禁_20261010"
    else:
        per, g4 = audit_xlsx_dir(d)
        tag = "时代列门禁基线_20261010"
    paths.TMP_DIR.mkdir(parents=True, exist_ok=True)
    (paths.TMP_DIR / f"{tag}.json").write_text(
        json.dumps({"逐图": per, "G4": g4}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    keys = []
    for r in per:
        keys.extend(k for k in r if k not in keys and not isinstance(r[k], list))
    with open(paths.TMP_DIR / f"{tag}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(per)
    viol = []
    for r in per:
        if strict and STRICT_RESID_RATE is not None and r.get("残墨率", 0) > STRICT_RESID_RATE:
            viol.append(f"{r['图号']} 残墨率 {r['残墨率']}")
        if strict and r.get("G3明细"):
            viol.append(f"{r['图号']} G3 {len(r['G3明细'])}条")
        if strict and r.get("G1b明细"):
            viol.append(f"{r['图号']} 字高越界 {len(r['G1b明细'])}条")
        if strict and "preflight_ok" in r and not r["preflight_ok"]:
            viol.append(f"{r['图号']} preflight未过")
        if strict and STRICT_VALID_RATE is not None:
            n = r.get("valid", 0) + r.get("suspect", 0) + r.get("invalid", 0)
            if n and r["valid"] / n < STRICT_VALID_RATE:
                viol.append(f"{r['图号']} valid率 {r['valid']}/{n}")
    if strict and G4_MAX_SUBS is not None and len(g4) > G4_MAX_SUBS:
        viol.append(f"G4 替换对 {len(g4)}")
    print(f"{'era_chars' if is_era else 'xlsx基线'}模式 {len(per)} 图;G4 替换对 {len(g4)}"
          f" → {paths.TMP_DIR / tag}.csv/.json")
    for v in viol:
        print("违反:", v)
    return 1 if viol else 0


def check_ink_accounting(ink, line_mask, boxes, pad=2):
    """G1 墨迹收支:总墨 = 线带墨 + 字块墨 + 残墨(线带墨单独立账,即便落在字框内)。

    ink=条带原始墨位图(剔线前);line_mask=行线先验窄带;boxes=[(y0,y1),...]字块框
    (y 向外扩 pad);残墨=框外且线带外墨。返回 dict(先例 column_line_follow 收支结构)。
    """
    total = int(ink.sum())
    line_in = int((ink & line_mask).sum())
    box_mask = np.zeros(ink.shape, bool)
    for a, b in boxes:
        box_mask[max(0, a - pad):b + pad + 1, :] = True
    box_in = int((ink & box_mask & ~line_mask).sum())
    resid = total - line_in - box_in
    return {
        "总墨": total,
        "线带墨": line_in,
        "字块墨": box_in,
        "残墨": resid,
        "残墨率": round(resid / total, 6) if total else 0.0,
    }


def check_box_heights(boxes, min_h, max_h):
    """G1b 字块高度分布须落在裁剪参数 [min_h, max_h] 内(读产物 params,不拍脑袋)。"""
    return [{"问题": "字高越界", "y0": a, "y1": b, "高": b - a}
            for a, b in boxes if not (min_h <= b - a <= max_h)]


def check_bands_order(bands):
    """G3 名带区间:自上而下须行/带序单调、区间不重叠、覆盖行(或 y)不重复。

    bands 每项带 "rows"(有序覆盖列表:试点=y0,y1;基线=行号列表)与 "name"。
    返回问题清单([{问题, ...}]),空=过。
    """
    problems = []
    seen, prev_min, prev_max = set(), None, None
    for i, b in enumerate(bands):
        rows = [r for r in b.get("rows") or []]
        if not rows:
            continue
        rmin, rmax = min(rows), max(rows)
        if prev_min is not None and rmin < prev_min:
            problems.append({"带": i, "问题": "乱序",
                             "细节": f"{b.get('name', '')} 首值 {rmin} < 前带首值 {prev_min}"})
        if prev_max is not None and rmin <= prev_max:
            problems.append({"带": i, "问题": "区间重叠",
                             "细节": f"{b.get('name', '')} [{rmin},{rmax}] 与前带尾值 {prev_max} 交叠"})
        dup = sorted(seen & set(rows))
        if dup:
            problems.append({"带": i, "问题": "覆盖行重复", "细节": dup[:8]})
        seen.update(rows)
        prev_min, prev_max = rmin, rmax
    return problems


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
