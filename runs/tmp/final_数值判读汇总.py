# -*- coding: utf-8 -*-
"""final 数值判读汇总 v2(2026-11-09):全部抄录合并 → 链验证/主判优先 → 裁决账。

输入:runs/tmp/_数值判读结果_*.json(子代理 16 批 + _main 主会话亲判)
选择:候选去 marker 后,数值角色(depth/thick/true_thick)取首个过物理链者,
      全不过→残余;链外角色(length/dip/layer/era/desc)主判(_main)优先
      (争议格已经 zoom 定谳后回写 main)。
跳过:纸面==现值(规范化后,空格/中点/°不敏感)——规则层归一已覆盖;
      (空) 且现值已空。
输出:合并进 runs/autoresearch_align/数值裁决账_20261109.json(既有条目保留,
      1020 r3 已手改 11.56)+ 未覆盖/残余清单。
"""
import glob
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(ROOT))
from openpyxl import load_workbook  # noqa: E402
from openpyxl.cell.rich_text import CellRichText  # noqa: E402

LEDGER = ROOT / "runs/autoresearch_align/数值裁决账_20261109.json"
GATE = ROOT / "runs/autoresearch_align/多源定级_20261106/列域门禁_20261109.json"
# 人工仲裁(2026-11-09 zoom/物理定谳):链与双源都无法判时按此直采
OVERRIDES = {
    ("1019", 19, "地质时代"): ("", "zoom:r19带era列空"),
    ("1019", 26, "真厚"): ("0.39", "代理0-1复核裁片:0.39(初读误深度列)"),
    ("1019", 27, "深度"): ("151.57", "深度链147.63+3.94=151.57 且下行152.77-1.20=151.57 双链"),
    ("1019", 37, "深度"): ("192.81", "深度链192.00+0.81=192.81=193.01-0.20 双链;zoom 行位核"),
    ("1019", 72, "层厚"): ("0.60", "X条带『21|294.97|0.60|0』清晰;链294.37+0.60=294.97"),
    ("1019", 78, "真厚"): ("0.59", "快照位移行dip列值即tth;0.60×cos10°=0.591;批4-5实测列界"),
    ("1019", 83, "真厚"): ("1.31", "快照位移行dip列值;行83=333.10 行,1.33×cos8°=1.317"),
    ("1019", 101, "真厚"): ("4.00", "zoom:4.04 层行 tth=4.00;4.04×cos8°=4.0005"),
    ("1015", 48, "采长"): ("1.00", "zoom:228.72 行 len 首字符微迹判1(低置信);228.72-227.62=1.10 层厚"),
    ("1015", 119, "煤层标志层号"): ("", "zoom:404.20 行 mark 空;『十二』属 403.70 行(r118)锚"),
    ("1016", 92, "煤层标志层号"): ("", "zoom:150.89 行 mark 空;『22』属 150.64 行(r91)"),
    ("1025", 85, "真厚"): ("11.11", "批6-7放大核验;cur『11.LI』前缀;11.2×cos6°≈11.14"),
    ("1027", 32, "真厚"): ("0.96", "cur『0.96,』同文去尾逗号"),
    ("1031", 47, "真厚"): ("0.70", "物理:层厚0.70,tth≤层厚;批8-9 的1.89系上行串位"),
    ("1034", 152, "真厚"): ("1.01", "zoom:360.30 行 tth=1.01 清晰"),
    ("1034", 172, "真厚"): ("0.83", "zoom:391.29 行 tth=0.83;0.85×cos12°=0.831"),
    ("1042", 16, "真厚"): ("4.67", "5.00×cos21°=4.668;批10-12 的6.35系r17串位"),
    ("1042", 17, "真厚"): ("6.35", "6.80×cos21°=6.348"),
    ("1042", 89, "深度"): ("367.94", "zoom:『32|367.94|0.30|0』清晰;链367.64+0.30=367.94"),
    ("1016", 126, "真厚"): ("0.70", "批0-1复核裁片;『U.7U』系OCR形误"),
    ("1019", 17, "真厚"): ("1.79", "快照位移行:dip列值『1.79°』即tth(行内左移一格模式)"),
    ("1019", 18, "真厚"): ("2.36", "快照位移行:dip列值『2.36°』即tth"),
}
SNAP = ROOT / "outputs/Excel交付_终版_20261109"
_COL2ROLE = {"深度": "depth", "层厚": "thick", "采长": "length", "真厚": "true_thick",
             "倾角": "dip", "煤层标志层号": "layer", "地质时代": "era", "岩性描述": "desc"}
_NUM = re.compile(r"^\d+(?:\.\d+)?$")
MARKERS = ("(窗外)", "(裁片不含该列)", "?")
cache = {}


def nnum(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def txt(v):
    if v is None:
        return ""
    if isinstance(v, CellRichText):
        v = str(v)
    return str(v).strip()


def ctx_vals(stem0, r):
    """快照上下文:rows 含表头(rows[0]),数据行 r(Excel 行号)= rows[r-1]。"""
    if stem0 not in cache:
        wb = load_workbook(SNAP / f"钻孔柱状图{stem0}_整合.xlsx")
        ws = wb.active
        hdr = [c.value for c in ws[1]]

        def col(*names):
            for j, h in enumerate(hdr):
                if h and any(n in str(h) for n in names):
                    return j
            return None
        cache[stem0] = ([list(row) for row in ws.iter_rows(min_row=1, values_only=True)],
                        col("深度"), col("层厚"), col("真厚"), col("倾角"))
    rows, cD, cT, cTT, cA = cache[stem0]
    i = r - 1
    row = rows[i] if 0 <= i < len(rows) else [""] * 20

    def d_clean(v):
        s = txt(v)
        m = re.match(r"^(\d+(?:\.\d+)?)\s*[|;]", s)
        return nnum(m.group(1) if m else s)
    out = {}
    for tag, c in (("d", cD), ("t", cT), ("tt", cTT)):
        out[tag] = nnum(d_clean(row[c]) if c is not None and c < len(row) else None)
    for k, rr in (("pd", i - 1), ("nd", i + 1)):
        if cD is not None and 0 <= rr < len(rows):
            out[k] = d_clean(rows[rr][cD]) if cD < len(rows[rr]) else None
        else:
            out[k] = None
    out["ang"], out["ang_r"] = None, None
    for rr in (i, i - 1, i + 1):
        if cA is not None and 0 <= rr < len(rows) and cA < len(rows[rr]):
            m = re.search(r"(\d+(?:\.\d+)?)", txt(rows[rr][cA]))
            if m:
                out["ang"], out["ang_r"] = float(m.group(1)), rr
                break
    return out


def chain_ok(cand, role, stem0, r):
    cv = nnum(cand)
    if cv is None:
        return False
    c = ctx_vals(stem0, r)
    if role == "depth":
        if c["t"] is None:
            return False
        return ((c["pd"] is not None and abs(c["pd"] + c["t"] - cv) <= 0.021)
                or (c["nd"] is not None and abs(cv + c["t"] - c["nd"]) <= 0.021))
    if role == "thick":
        for ref in ((c["d"] - c["pd"]) if (c["d"] is not None and c["pd"] is not None) else None,
                    (c["nd"] - c["d"]) if (c["d"] is not None and c["nd"] is not None) else None):
            if ref is not None and abs(cv - ref) <= 0.021:
                return True
        return False
    if role == "true_thick":
        if c["t"] is None or c["t"] > 60 or c["ang"] is None:
            return False
        return abs(cv - c["t"] * math.cos(math.radians(c["ang"]))) <= 0.09
    return False


def norm_eq(a, b, colname):
    def n(s, c):
        s = str(s).strip()
        if c in ("深度", "层厚", "采长", "真厚", "倾角"):
            return re.sub(r"[\s\u3000·•‧⋅]", "", s).replace("°", "").rstrip(".")
        if c == "煤层标志层号":
            return re.sub(r"[\s\u3000]", "", s)
        return s
    return n(a, colname) == n(b, colname)


# ---- 载入候选 ----
cands = {}
for f in sorted(glob.glob(str(ROOT / "runs/tmp/_数值判读结果_*.json"))):
    is_main = f.endswith("_main.json")
    try:
        arr = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("SKIP", f, repr(e)[:50])
        continue
    for x in arr:
        try:
            k = (str(x["图"]), int(x["xlsx行"]), str(x["列"]))
        except (KeyError, ValueError, TypeError):
            continue
        cands.setdefault(k, []).append((Path(f).name, str(x.get("纸面", "")).strip(),
                                        str(x.get("现值", "")).strip(), is_main))

# ---- 选择与写账 ----
ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
have = {(e["图"], int(e["xlsx行"]), e["列"]) for e in ledger}
new, residual, identity = [], [], []
for k in sorted(cands):
    stem0, r, colname = k
    role = _COL2ROLE.get(colname)
    key5 = (stem0, r, colname)
    if key5 in have:
        continue
    lst = cands[k]
    cur = next((c for (_, _, c, _) in lst if c), "")
    # 主判优先排后(链外角色);marker 候选沉底
    core = [x for x in lst if not any(m in x[1] for m in MARKERS)]
    order = sorted(core, key=lambda x: (not x[3],))          # main(True=0)在前
    if not core:
        ov = OVERRIDES.get(key5)
        if ov:
            picked, how = ov[0], f"人工仲裁:{ov[1]}"
        else:
            residual.append((k, cur, [x[1] for x in lst]))
            continue
    else:
        # 身份前置:任一候选与现值规范化同文 → 规则层归一已覆盖,不写账
        if any(norm_eq(x[1], cur, colname) for x in core):
            identity.append(k)
            continue
        picked, how = None, None
        if role in ("depth", "thick", "true_thick"):
            for name, paper, _, _ in order:
                c = paper
                if paper == "(空)":
                    picked, how = "", "纸面空"
                    break
                sp = re.sub(r"[\s\u3000]", "", paper)
                for cand in ([paper] + ([sp] if sp != paper and _NUM.match(sp) else [])):
                    if chain_ok(cand, role, stem0, r):
                        picked, how = cand, f"链验证({name})"
                        break
                if picked is not None:
                    break
            if picked is None:
                # 分层回收:双源一致/现值数值前缀同文 → 直采;主判候选 → 主判直采
                vals = {re.sub(r"[\s\u3000]", "", x[1]) for x in core}
                mcur = re.search(r"\d+(?:\.\d+)?", cur)
                if len(vals) == 1:
                    v = next(iter(vals))
                    srcs = {x[0] for x in core}
                    if (mcur and nnum(v) == nnum(mcur.group(0))) or len(srcs) >= 2:
                        picked, how = v, f"双源一致/现值前缀同文(链邻格污染:{'/'.join(sorted(srcs))})"
                if picked is None and any(x[3] for x in core):
                    mv = next(x[1] for x in core if x[3])
                    msp = re.sub(r"[\s\u3000]", "", mv)
                    picked = msp if _NUM.match(msp) else mv
                    how = "主判直采(链邻格污染,裁片+zoom工作流)"
                if picked is None:
                    ov = OVERRIDES.get(key5)
                    if ov:
                        picked, how = ov[0], f"人工仲裁:{ov[1]}"
                    else:
                        residual.append((k, cur, [x[1] for x in lst]))
                        continue
        else:
            name, paper, _, _ = order[0]
            if paper == "(空)":
                picked, how = "", f"纸面空({name})"
            else:
                picked = paper
                if role in ("length", "dip"):
                    sp = re.sub(r"[\s\u3000]", "", paper)
                    if sp != paper and _NUM.match(sp):
                        picked = sp
                how = f"主判/代理({name})"
    if cur == "" and picked == "":
        identity.append(k)
        continue
    if norm_eq(picked, cur, colname):
        identity.append(k)
        continue
    ledger.append({"图": stem0, "xlsx行": r, "列": colname, "现值": cur,
                   "新值": picked, "依据": f"数值门禁裁片判读:{how}"})
    new.append((key5, cur, picked))

LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")

# ---- 覆盖检查 ----
gate = json.loads(GATE.read_text(encoding="utf-8"))
uncov = [g for g in gate if (g["图"], g["xlsx行"], g["列"]) not in cands]
print(f"候选键 {len(cands)}; 新裁决 {len(new)}; 同文跳过 {len(identity)}; 残余 {len(residual)}; "
      f"门禁未覆盖 {len(uncov)}")
print("新裁决列分布:", dict(Counter(k[0][2] for k in new)))
for k, cur, nv in new:
    print("  ", k, repr(cur), "->", repr(nv))
if residual:
    print("\n残余(需人工):")
    for k, cur, ps in residual:
        print("  ", k, "cur=", repr(cur), "候选:", ps)
if uncov:
    print("\n门禁违例无候选:", uncov[:20])
print("裁决账总条目:", len(ledger))
