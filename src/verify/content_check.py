# -*- coding: utf-8 -*-
"""内容层只读互证(原则 9:先验证后实现):层厚=相邻深度差、真厚=层厚×cos(倾角)。

数据源=已核验的旧轮 OCR 还原 Excel(runs/table_reconstruct/钻孔柱状图*_还原.xlsx)。
只读,不改动任何产物;OCR 单元格常含多子层与空格分裂的数字,解析规则见 parse_numbers。
"""
import math
import re


def parse_numbers(v) -> list:
    """单元格 → 数字列表。

    OCR 空格分裂:'3. 88'→[3.88]、'7 .97'→[7.97];一格多子层:
    '136.75 137.00'→[136.75,137.00];垃圾('C'、'5-7')丢弃;
    垃圾数字('1.4 49 0.60' 里的 49)保留——由配对计数失衡暴露,不猜。
    """
    if v is None:
        return []
    if isinstance(v, (int, float)):
        return [float(v)]
    toks = str(v).replace("°", "").split()
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        merged = None
        if i + 1 < len(toks) and (t.endswith(".") or t.isdigit()):
            nxt = toks[i + 1]
            if (t.endswith(".") and nxt.isdigit()) or (t.isdigit() and nxt.startswith(".")):
                try:
                    merged = float(t + nxt)
                except ValueError:
                    merged = None   # OCR 形近字混入(如 '了. 45'):合并失败按垃圾丢弃
                if merged is not None:
                    out.append(merged)
                    i += 2
                    continue
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            out.append(float(t))
        i += 1
    return out


def parse_dip(v):
    """'5 D'/'4°'/8 → 度数;'5 5' 等歧义形态(度分?)→ None,不参与真厚互证。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("°", "").replace("D", " ").strip()
    toks = s.split()
    if len(toks) == 1 and re.fullmatch(r"\d+(?:\.\d+)?", toks[0]):
        return float(toks[0])
    return None


def check_rows(rows) -> dict:
    """rows: [{"d":[..],"t":[..],"z":[..],"dip":度数或None}, ...](已按行序)。

    层厚=深度差:行内子层配对计数须一致;d[0] 用上一行末深度(首行=0 表面)。
    上行计数不齐时,深度梯仍以该行深度列表末值续接(防级联),仅 d[0] 层跳过。
    """
    res = {"layers_checked": 0, "unpaired_rows": 0, "structural_rows": 0,
           "records": [], "errors": [],
           "dip_checked": 0, "dip_records": [], "dip_errors": [], "z_vs_t_nodip": []}
    prev_d = 0.0
    for ri, r in enumerate(rows):
        d, t, z = r.get("d", []), r.get("t", []), r.get("z", [])
        dip = r.get("dip")
        paired = len(d) == len(t) and len(d) > 0
        if not paired:
            res["unpaired_rows"] += 1
        else:
            exp = prev_d
            broken = False
            for j, (dv, tv) in enumerate(zip(d, t)):
                if dv <= exp + 1e-9:
                    # 钻孔深度必须递增:非单调=OCR 截断/误读造成的结构性损伤
                    # (如 '329.79' 被截成 '3'),该行其余层不计违规,深度梯不前移。
                    res["structural_rows"] += 1
                    broken = True
                    break
                gap = dv - exp
                rec = {"row": ri, "j": j, "t": tv, "gap": round(gap, 4),
                       "abs": round(abs(tv - gap), 4)}
                res["records"].append(rec)
                if rec["abs"] > 1e-9:
                    res["errors"].append(rec)
                res["layers_checked"] += 1
                exp = dv
            if broken:
                continue
        if len(d) > 0 and d[-1] > prev_d:
            prev_d = d[-1]
        # 真厚互证:z 与 t 配对且倾角可解析
        if dip is not None and paired and len(z) == len(d):
            for j, (tv, zv) in enumerate(zip(t, z)):
                pred = tv * math.cos(math.radians(dip))
                rec = {"row": ri, "j": j, "dip": dip, "z": zv, "pred": round(pred, 4),
                       "abs": round(abs(zv - pred), 4)}
                res["dip_records"].append(rec)
                if rec["abs"] > 1e-9:
                    res["dip_errors"].append(rec)
                res["dip_checked"] += 1
        elif dip is None and paired and len(z) == len(d):
            for j, (tv, zv) in enumerate(zip(t, z)):
                res["z_vs_t_nodip"].append(round(abs(zv - tv), 4))
    return res
