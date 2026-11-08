# -*- coding: utf-8 -*-
"""与参考表逐格对比(用户提供的另一套 LLM 整理,REF_XLSX_DIR_20261011)。

对齐:两表出自同一扫描原图——我方行区间=行判定折线相邻 y,参考行区间=其 y_top/y_bottom
像素坐标;区间重叠互相最佳(1:1 互证)且过半行高才配对,切分粗细不同(我方 155 行 vs
参考 190 行/图)不硬配。
比对语义(用户口径 2026-10-11):我方=对原版的纠错版,参考表(*_llm_corrected)=原版(错多);
仅同语义列、双方非空且不等 → 我方格打**黄色字体**(=我方纠错点,供用户快速看改了哪);
单方空缺只记账不打色(参考表时代列碎片化/数值列错位多,打色会淹没真分歧)。
数字按 float 容差 0.005(两位小数表的舍入量级),°/全角/空白差异视为相等。
CLI: python src/table/compare_ref.py [图号...] → 我方整合 xlsx 原地标黄 + {stem}_对比账.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

COLS = ["地质时代", "煤层/标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]
REF_COL = {0: 4, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10, 7: 12}   # 我方列号→参考列号
TEXT_COLS = {"地质时代", "煤层/标志层号", "岩性描述"}   # 文本列:标点排版差异不算分歧
RICH_COLS = {"地质时代", "岩性描述"}   # 长文本列:字级标红(一句话差一个字只标那个字,用户指令)
# 角色→参考列(1032 六列异版按表头角色映射,位置映射会串列)
ROLE_REF_COL = {"era": 4, "layer": 5, "depth": 6, "thick": 7,
                "length": 8, "dip": 9, "true_thick": 10, "desc": 12}


def red_mark(ours, theirs):
    """我方文本 vs 参考:我方中差异字符标红(rich text),文本不变。

    字符级 SequenceMatcher:replace/delete 标我方对应段;insert(我方缺字)标
    插入点邻近一字定位。无差异返回 None。"""
    import difflib
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    a, b = str(ours), str(theirs)
    parts, red = [], InlineFont(color="FFFF0000")
    pending_head = False
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            seg = a[i1:i2]
            if pending_head and seg:
                parts += [TextBlock(red, seg[0]), seg[1:]]
                pending_head = False
            else:
                parts.append(seg)
        elif i2 > i1:
            parts.append(TextBlock(red, a[i1:i2]))
        else:                                  # insert=我方缺字:插入点邻字标红定位,不增删文本
            if i1 > 0 and parts and isinstance(parts[-1], str) and parts[-1]:
                parts[-1] = parts[-1][:-1]
                parts.append(TextBlock(red, a[i1 - 1]))
            else:
                pending_head = True
    parts = [x for x in parts if not (isinstance(x, str) and not x)]
    if not any(not isinstance(x, str) for x in parts):
        return None
    return CellRichText(parts)
THICK_TOL = 0.015   # 与 finalize 数值门禁同容差口径

_HALF = {chr(c): chr(c - 0xFEE0) for c in range(0xFF01, 0xFF5F)}


def norm_cell(v):
    """单元格→比对口径:全角转半角、去 °/空白;空返回 None。"""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = "".join(_HALF.get(ch, ch) for ch in s)
    s = s.replace("°", "").replace("℃", "")
    s = "".join(s.split())
    return s or None


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


_PUNCT = "，。：；、,.:;·()（）-—_'\" 　/"


def cell_diff(ours, theirs, tol=0.005, text=False):
    """比对:(equal|diff|ours_empty|theirs_empty)。数字双可析按容差,否则字符串。

    text=True(描述类文本列):先剔标点再比——参考表用空格/点号风格、我方用全角
    标点,属排版差异不算分歧(实测占描述 diff 16% 假阳);文字差异仍 diff。
    """
    a, b = norm_cell(ours), norm_cell(theirs)
    if a is None and b is None:
        return "equal"
    if a is None:
        return "ours_empty"
    if b is None:
        return "theirs_empty"
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None and not text:
        return "equal" if abs(na - nb) <= tol else "diff"
    if text:
        a = "".join(ch for ch in a if ch not in _PUNCT)
        b = "".join(ch for ch in b if ch not in _PUNCT)
    return "equal" if a == b else "diff"


def pair_rows(ours_ivs, ref_ivs, min_frac=0.6):
    """像素区间 1:1 互证配对:[(我方行号,参考行号)]。

    互相最佳 + 重叠须覆盖双方各 ≥ min_frac(双侧口径:我方一刀 vs 参考两刀的
    聚合行只覆对方一半,拒配——切分不同不硬比)。
    """
    def ov(iv_a, iv_b):
        return max(0.0, min(iv_a[1], iv_b[1]) - max(iv_a[0], iv_b[0]))

    best_o, best_r = {}, {}
    for i, ia in enumerate(ours_ivs):
        for j, jb in enumerate(ref_ivs):
            o = ov(ia, jb)
            if i not in best_o or o > ov(ia, ref_ivs[best_o[i]]):
                best_o[i] = j
            if j not in best_r or o > ov(ref_ivs[j], ours_ivs[best_r[j]]):
                best_r[j] = i
    pairs = []
    for i, j in best_o.items():
        if best_r.get(j) != i:
            continue
        ia, jb = ours_ivs[i], ref_ivs[j]
        o = ov(ia, jb)
        if o and o / (ia[1] - ia[0]) >= min_frac and o / (jb[1] - jb[0]) >= min_frac:
            pairs.append((i, j))
    return sorted(pairs)


def _ref_rows(path):
    from openpyxl import load_workbook
    ws = load_workbook(path).active
    rows = list(ws.iter_rows(values_only=True))
    return rows[0], rows[1:]


def compare_chart(stem, ours_dir, ref_dir, out_dir=None,
                  ref_suffix="_llm_corrected.xlsx", row_ivs=None):
    """单图对比:我方整合 xlsx 原地标黄 + {stem}_对比账.csv;返回统计 dict。

    row_ivs=None 时由行判定 json 现算(与 finalize 同口径:表中点 x 处相邻行折线 y);
    传入则用调用方区间(测试/复算用),键=0 基数据行号。
    """
    import csv
    from openpyxl import load_workbook
    from copy import copy
    from openpyxl.styles import Font, PatternFill
    from src.core import paths
    from src.table.finalize_tables import column_roles

    ours_dir = Path(ours_dir)
    ref_path = Path(ref_dir) / f"{stem}{ref_suffix}"
    out_dir = Path(out_dir) if out_dir else ours_dir
    wb = load_workbook(ours_dir / f"{stem}_整合.xlsx", rich_text=True)  # 不加则保存丢 rich 红字
    ws = wb.active
    _all = list(ws.iter_rows(values_only=True))
    roles = column_roles(_all[0] if _all else [])
    idx_role = {v: k for k, v in roles.items()}          # 我方列号→角色
    data = _all[1:]

    if row_ivs is None:
        from src.table.era_chars import _load_inputs
        from src.table.track_rows import row_y
        from src.table.finalize_tables import drop_header_rows, unstuck_chain
        hm, rd = _load_inputs(stem)
        x_mid_tbl = sum(rd["table_x"]) / 2
        rr = [r for r in rd["rows"] if row_y(r, x_mid_tbl) >= hm["band"][1]]
        # 行界走 finalize 同款重放(表头剔除+粘连行手术),与交付 xlsx 行序一致;
        # 裸行判定数会在拆行/剔行图(1044 N值拆等)上假 FAIL。
        # 2026-10-28 切源:重放吃现行草案 REEMIT_DIR_20261023 + 表头角色解析,
        # 与 finalize 完全同参(旧 20261005B 行构与新链不符,行数校验必炸)。
        x = sum(hm["keep"][0]["x_in_band"]) / 2
        ys = [row_y(r, x) for r in rr]
        from src.core import paths as _paths
        _bwb = load_workbook(_paths.REEMIT_DIR_20261023 / f"{stem}_还原.xlsx")
        bdata = [tuple(r)[:8] + (None,) * max(0, 8 - len(r))
                 for r in _bwb.active.iter_rows(values_only=True)]
        bdata, ys, _ = drop_header_rows(bdata, ys)
        bdata, ys, _, _ = unstuck_chain(bdata, ys, column_roles(bdata[0] if bdata else []))
        # 草案尾部全空行:openpyxl 不写无单元格的空行,交付 xlsx 里不存在,重放须同删
        # (1032 草案末行全空,不删则 kept=104 vs xlsx=103 假 FAIL)
        while bdata and not any(v is not None and str(v).strip() for v in (bdata[-1] or ())):
            bdata.pop()
            ys.pop()
        # 假行手术行以校正账为准(来源=假行归并/列=整行),不重推导——
        # 退化区间+无深度的行在别图是真实交付行,仅 1033 做过手术
        surg = set()
        _csvp = _paths.FINALIZE_FULL_DIR / f"{stem}_校正账.csv"
        if _csvp.exists():
            for _r in csv.DictReader(open(_csvp, encoding="utf-8-sig")):
                if _r.get("来源") == "假行归并" and _r.get("列") == "整行":
                    try:
                        surg.add(int(_r["行"]))
                    except ValueError:
                        pass
        kept = [i for i in range(len(ys) - 1) if i not in surg]
        n_data = len(data)
        if n_data != len(kept):
            return {"图": stem, "error": f"行数不一致 xlsx={n_data} 行重放={len(kept)}"}
        row_ivs = {k: (ys[i], ys[i + 1]) for k, i in enumerate(kept)}

    hdr, rdata = _ref_rows(ref_path)
    ref_ivs, ref_keep = [], []
    for j, r in enumerate(rdata):
        try:
            iv = (float(r[1]), float(r[2]))
        except (TypeError, ValueError):
            continue
        if iv[1] > iv[0]:
            ref_ivs.append(iv)
            ref_keep.append(j)

    pairs = pair_rows([row_ivs[i] for i in sorted(row_ivs)], ref_ivs)
    ledger, stat = [], {"diff": 0, "标黄": 0, "ours_empty": 0, "theirs_empty": 0}
    # 红字=我方(纠错版)与原版参考表不一致处(用户:黄色看不清,改红);先清上轮残留黄/红
    red_font = Font(color="FF0000")
    for row in ws.iter_rows():
        for c in row:
            rgb = c.fill.start_color.rgb if c.fill and c.fill.start_color else None
            if isinstance(rgb, str) and rgb.endswith("FFFF00"):
                c.fill = PatternFill(fill_type=None)
            fc = c.font.color if c.font else None
            if fc and isinstance(fc.rgb, str) and fc.rgb.endswith(("FFFF00", "FF0000")):
                f = copy(c.font)                  # 清残留色字,保留字体名/字号
                f.color = None
                c.font = f
    for i, j in pairs:
        rrow = rdata[ref_keep[j]]
        for k in sorted(idx_role):
            name = {"era": "地质时代", "layer": "煤层/标志层号", "depth": "深度",
                    "thick": "层厚", "length": "采长", "dip": "倾角",
                    "true_thick": "真厚", "desc": "岩性描述"}[idx_role[k]]
            rk = ROLE_REF_COL[idx_role[k]]
            ours_v = data[i][k] if len(data[i]) > k else None
            ref_v = rrow[rk] if len(rrow) > rk else None
            d = cell_diff(ours_v, ref_v, tol=0.005, text=name in TEXT_COLS)
            if d == "equal":
                continue
            stat[d] = stat.get(d, 0) + 1
            if d == "diff":
                cell = ws.cell(row=i + 2, column=k + 1)
                if name in RICH_COLS:
                    rt = red_mark(ours_v, ref_v)   # 长文本:只标差异字
                    if rt is not None:
                        cell.value = rt
                    else:
                        cell.font = red_font
                else:
                    cell.font = red_font           # 数值/短文本:整格红
                stat["标黄"] += 1
            ledger.append({"行": i + 2, "列": name,
                           "我方值": str(ours_v)[:80] if ours_v is not None else "",
                           "参考值": str(ref_v)[:80] if ref_v is not None else "",
                           "判定": d, "处置": "红字(差异字级)" if d == "diff" else "仅记账"})
    wb.save(ours_dir / f"{stem}_整合.xlsx")
    with open(out_dir / f"{stem}_对比账.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["行", "列", "我方值", "参考值", "判定", "处置"])
        w.writeheader()
        w.writerows(ledger)
    total = len(pairs) * len(idx_role)
    return {"图": stem, "配对行": len(pairs), "比对列数": len(idx_role),
            "未配对我方行": len(row_ivs) - len(pairs),
            "未配对参考行": len(ref_ivs) - len(pairs),
            "比对格": total,
            "equal": total - stat["diff"] - stat["ours_empty"] - stat["theirs_empty"],
            "diff": stat["diff"], "标黄": stat["标黄"],
            "ours_empty": stat["ours_empty"], "theirs_empty": stat["theirs_empty"]}


def main(argv):
    import json
    from src.core import paths
    ref_dir = paths.REF_XLSX_DIR_20261011 / "1015-1044"
    stems = argv or sorted(p.name[:-len("_整合.xlsx")] for p in
                           paths.FINALIZE_FULL_DIR.glob("*_整合.xlsx"))
    bad, summary = [], []
    for num in stems:
        stem = num if num.startswith("钻孔柱状图") else f"钻孔柱状图{num}"
        if not (paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx").exists():
            print(stem, "SKIP 无整合表")
            summary.append({"图": stem, "error": "无整合表"})
            continue
        if not (ref_dir / f"{stem}_llm_corrected.xlsx").exists():
            print(stem, "SKIP 无参考表")
            summary.append({"图": stem, "error": "无参考表"})
            continue
        try:
            rep = compare_chart(stem, paths.FINALIZE_FULL_DIR, ref_dir)
        except Exception as e:                       # 单图失败不断批
            print(stem, "FAIL", repr(e)[:100])
            bad.append(stem)
            summary.append({"图": stem, "error": repr(e)[:100]})
            continue
        summary.append(rep)
        if "error" in rep:
            print(stem, "FAIL", rep["error"])
            bad.append(stem)
            continue
        print(stem, f"配对{rep['配对行']} diff{rep['diff']} 标黄{rep['标黄']} "
                    f"我方空{rep['ours_empty']} 参考空{rep['theirs_empty']} "
                    f"未配对(我{rep['未配对我方行']}/参{rep['未配对参考行']})")
    paths.FINALIZE_FULL_DIR.mkdir(parents=True, exist_ok=True)
    (paths.FINALIZE_FULL_DIR / "对比汇总.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    ok_reps = [r for r in summary if "比对格" in r]
    if ok_reps:
        tg = sum(r["比对格"] for r in ok_reps)
        te = sum(r["equal"] for r in ok_reps)
        print(f"整体一致率: {te}/{tg} = {te / tg:.4f} ({te / tg * 100:.2f}%)")
        for r in sorted(ok_reps, key=lambda x: x["equal"] / max(1, x["比对格"])):
            print(f"  {r['图']} {r['equal']}/{r['比对格']} = {r['equal'] / r['比对格'] * 100:.2f}%"
                  f" (diff{r['diff']} 我空{r['ours_empty']} 参空{r['theirs_empty']})")
    print("汇总:", paths.FINALIZE_FULL_DIR / "对比汇总.json")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
