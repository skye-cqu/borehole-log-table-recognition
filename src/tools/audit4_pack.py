# -*- coding: utf-8 -*-
"""交付包一致性审计 + 待人审自动收敛额度实测 v2(只读,不写任何文件)。

用法: python src/tools/audit4_pack.py
A 三方计数对账: 待核清单处置桶 / 复核包模板键数·HTML标题 / README 表
B 小数点伪差额度(纯数字格限定+列值域守卫): 待人审中两引擎数字序列全同
  (仅差小数点/前导零),并统计 xlsx 现值与拟采纳值的差异数
C 层厚=深度差(行内边界差值多重集) 在可信格上的成立率 + 待人审层厚可裁定额度
D 深度连续(邻行首尾衔接)+行内跨度⊆可信层厚 在待人审深度格上的可裁定额度
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpyxl import load_workbook  # noqa: E402

STEMS4 = ["钻孔柱状图1018", "钻孔柱状图1030", "钻孔柱状图1032", "钻孔柱状图1042"]
RUNS = ROOT / "runs" / "table_reconstruct"
PKG = ROOT / "outputs" / "Excel交付_最终_20260915"
TOL = 0.02


def load_flags(stem):
    return json.loads((RUNS / f"{stem}_待核清单.json").read_text(encoding="utf-8"))


def load_ht(stem):
    ws = load_workbook(RUNS / f"{stem}_还原_补产终版.xlsx").active
    rows = list(ws.iter_rows(values_only=True))
    return list(rows[0]), [list(r) for r in rows[1:]]


def num_toks(s):
    """纯数字串(可含空格/小数点/度百分号)→float 列表;含文字→None。"""
    t = str(s if s is not None else "").strip()
    if not t or t == "None" or not re.fullmatch(r"[0-9 .,。°%]+", t):
        return None
    out = []
    for tok in re.split(r"\s+", re.sub(r"[,。°%]", "", t)):
        if not tok:
            continue
        try:
            out.append(float(tok))
        except ValueError:
            return None
    return out or None


def digseq(s):
    d = re.sub(r"\D", "", str(s or ""))
    return d.lstrip("0") or "0"


def subset_eq(ts, refs, tol=TOL):
    """ts 多重集 ⊆ refs 多重集(贪心配对,±tol)。"""
    used = [False] * len(refs)
    for t in ts:
        for j, r in enumerate(refs):
            if not used[j] and abs(t - r) <= tol:
                used[j] = True
                break
        else:
            return False
    return True


def diffs(ds):
    return [round(ds[i + 1] - ds[i], 6) for i in range(len(ds) - 1)]


def main():
    summary = json.loads((RUNS / "对账汇总.json").read_text(encoding="utf-8"))
    print("== A 三方计数对账 ==")
    for stem in STEMS4:
        flags = load_flags(stem)
        c = Counter(f["处置"] for f in flags)
        code = stem[-4:]
        d = PKG / "待核复核包" / f"{stem}_待核复核包"
        htm = d / "待核清单.html"
        title = None
        if htm.exists():
            m = re.search(r"待人审 (\d+) 格", htm.read_text(encoding="utf-8"))
            title = m.group(1) if m else "?"
        strict = summary[stem]["格"] - len(flags)
        print(f"{code}: 格{summary[stem]['格']} 分歧{len(flags)} 严格{strict} "
              f"桶{dict(c)} | html标题待人审 {title}")
    rd = (PKG / "README_必读.md").read_text(encoding="utf-8")
    print("== README 数据表行 ==")
    for ln in rd.splitlines():
        if ln.startswith("| ["):
            print(" ", ln[:130])

    print("== B 小数点伪差额度(纯数字格+列值域守卫) ==")
    tot = tot_fix = 0
    for stem in STEMS4:
        flags = load_flags(stem)
        header, table = load_ht(stem)
        disp = {(f["层"], f["列"]) for f in flags}
        pools = {}
        for j, name in enumerate(header):
            vals = []
            for li, r in enumerate(table, 1):
                if (li, name) in disp:
                    continue
                vals += [v for v in (num_toks(r[j]) or [])]
            pools[name] = (min(vals), max(vals)) if vals else None
        n = n_fix = 0
        ex = []
        for f in flags:
            if not str(f["处置"]).startswith("待人审"):
                continue
            dnum = num_toks(f.get("草案"))
            if dnum is None:
                continue
            pool = pools.get(f["列"])
            if pool is None:
                continue
            for key in ("agnes单格", "agnes条"):
                cnum = num_toks(f.get(key))
                if cnum is None or digseq(f.get("草案")) != digseq(f.get(key)):
                    continue
                if not any("." in t for t in re.split(r"\s+", str(f.get(key)).strip())):
                    continue  # 采纳侧须带小数点(伪差修复方向)
                if not all(pool[0] - 0.05 <= v <= pool[1] + 0.05 for v in cnum):
                    break  # 值域外→弃判
                n += 1
                cur = table[f["层"] - 1][header.index(f["列"])]
                if isinstance(cur, float) and len(cnum) == 1 \
                        and abs(cur - cnum[0]) <= 1e-9:
                    break
                n_fix += 1
                if len(ex) < 4:
                    ex.append((f["层"], f["列"], f.get("草案"), f.get(key),
                               f"xlsx现值={cur!r}"))
                break
        tot += n
        tot_fix += n_fix
        print(f"{stem[-4:]}: 伪差可裁定 {n} (其中 xlsx 需改值 {n_fix})")
        for e in ex:
            print("   ", e)
    print(f"合计伪差可裁定 {tot} (需改值 {tot_fix})")

    print("== C 行内边界差值多重集: 可信格成立率 / 待人审层厚可裁定额度 ==")
    for stem in STEMS4:
        flags = load_flags(stem)
        header, table = load_ht(stem)
        disp = {(f["层"], f["列"]) for f in flags}
        if "深度" not in header or "层厚" not in header:
            print(f"{stem[-4:]}: 无深度/层厚列,跳过")
            continue
        i_d, i_t = header.index("深度"), header.index("层厚")
        full = part = fail = 0
        adj = 0
        ex = []
        for li, r in enumerate(table, 1):
            if (li, "深度") in disp or (li, "层厚") in disp:
                continue
            ds, ts = num_toks(r[i_d]), num_toks(r[i_t])
            if not ds or not ts or len(ds) < 2:
                continue
            dd = diffs(ds)
            if len(ts) == len(dd) and subset_eq(ts, dd):
                full += 1
            elif subset_eq(ts, dd):
                part += 1
            else:
                fail += 1
        for f in flags:
            if f["列"] != "层厚" or not str(f["处置"]).startswith("待人审"):
                continue
            li = f["层"]
            if (li, "深度") in disp:
                continue
            ds = num_toks(table[li - 1][i_d])
            if not ds or len(ds) < 2:
                continue
            dd = diffs(ds)
            quals = []
            for key in ("agnes单格", "草案", "agnes条"):
                ts = num_toks(f.get(key))
                if ts and subset_eq(ts, dd):
                    quals.append(tuple(round(t, 4) for t in ts))
            quals = sorted(set(quals))
            if len(quals) == 1:
                adj += 1
                if len(ex) < 3:
                    ex.append((li, f.get("草案"), f.get("agnes单格"),
                               f.get("agnes条"), dd))
        print(f"{stem[-4:]}: 可信格 全等{full} 子集{part} 违背{fail} "
              f"| 待人审层厚可裁定 {adj}")
        for e in ex:
            print("   ", e)

    print("== D 待人审深度格可裁定额度(邻行衔接+跨度⊆可信层厚) ==")
    for stem in STEMS4:
        flags = load_flags(stem)
        header, table = load_ht(stem)
        disp = {(f["层"], f["列"]) for f in flags}
        if "深度" not in header:
            print(f"{stem[-4:]}: 无深度列,跳过")
            continue
        i_d, i_t = header.index("深度"), header.index("层厚")
        n = len(table)
        adj = 0
        ex = []
        for f in flags:
            if f["列"] != "深度" or not str(f["处置"]).startswith("待人审"):
                continue
            li = f["层"]
            prev = num_toks(table[li - 2][i_d]) if li >= 2 else None
            nxt = num_toks(table[li][i_d]) if li < n else None
            t_ok = (li, "层厚") not in disp
            trefs = num_toks(table[li - 1][i_t]) if t_ok else None
            quals = []
            for key in ("agnes单格", "草案", "agnes条"):
                cs = num_toks(f.get(key))
                if not cs or len(cs) < 2:
                    continue
                if prev and len(prev) >= 2 and abs(cs[0] - prev[-1]) > TOL:
                    continue
                if nxt and len(nxt) >= 2 and abs(cs[-1] - nxt[0]) > TOL:
                    continue
                if trefs and not subset_eq(diffs(cs), trefs):
                    continue
                quals.append(tuple(round(c, 4) for c in cs))
            quals = sorted(set(quals))
            if len(quals) == 1:
                adj += 1
                if len(ex) < 3:
                    ex.append((li, f.get("草案"), f.get("agnes单格"),
                               f.get("agnes条"), prev, nxt, trefs))
        print(f"{stem[-4:]}: 深度可裁定 {adj}")
        for e in ex:
            print("   ", e)


if __name__ == "__main__":
    main()
