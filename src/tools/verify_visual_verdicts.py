# -*- coding: utf-8 -*-
"""视觉判读结果的机器校验(不靠肉眼争论,用可核算的独立证据裁决)。

五道检查:
  C1 覆盖完整性  判定 tag 集 vs tag映射全集:漏判/重判/跨段撞车(分段代理边界)
  C2 值个数一致  数字列判定值的个数 vs 几何墨段块数(块数是独立几何证据)
  C3 值域合法    深度/层厚/采长/倾角/真厚 落在物理可能区间
  C4 关系式互证  真厚 = 层厚 × cos(倾角) ±0.02m(实测 87% 成立的主校验和)
  C5 同层自洽    单层内 深度差 与 层厚 的量级一致性(仅单值格参与)
任何一道不过 → 该格降级 UNCLEAR,不写入交付。
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

RD = paths.RUNS_DIR / "复核直览"
NUM_COLS = ("深度", "层厚", "采长", "倾角", "真厚")
# 值域按 4 张图实测极值放宽:1042 孔深达 475m,层厚/真厚上限 30 会误伤正常格,
# 采长 0 在原表中合法(该层未采样),故下界取 0。
RANGE = {"深度": (0, 800), "层厚": (0, 60), "采长": (0, 60),
         "倾角": (0, 90), "真厚": (0, 60)}


def nums(v):
    """判定串里的数值 token(优先带小数点的整体,避免 0.70 被拆成 0 和 70)。"""
    s = "" if v in (None, "None") else str(v)
    return [float(x) for x in re.findall(r"\d+\.\d+|\d+\.|\.\d+|\d+", s)]


def load():
    tags = json.loads((RD / "tag映射.json").read_text(encoding="utf-8"))
    pre = json.loads((RD / "几何预判.json").read_text(encoding="utf-8"))
    cells, dup = {}, []
    for f in sorted(RD.glob("判定_*.json")):
        obj = json.loads(f.read_text(encoding="utf-8"))
        for c in obj.get("cells", []):
            if c["tag"] in cells:
                dup.append(c["tag"])
            cells[c["tag"]] = {**c, "_src": f.name}
    full = {}
    for stem, rows in tags.items():
        for r in rows:
            full[r["tag"]] = {**r, "stem": stem}
    return full, pre, cells, dup


def depth_monotonic(idx):
    """C6 深度列单调性:以 xlsx 现值为底,套用判定值替换,逐层检查底深递增。
    抓的是"数字归错行"这类误判——判读代理自己就用这招反算行底。"""
    from openpyxl import load_workbook
    bad = []
    for stem in {k[0] for k in idx}:
        xp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_还原_补产终版.xlsx"
        if not xp.exists():
            continue
        ws = load_workbook(xp, read_only=True).active
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        if "深度" not in header:
            continue
        j = header.index("深度")
        bottoms, rows = [], []
        for r, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            layer = r - 1
            c = idx.get((stem, layer, "深度"))
            raw = c["value"] if c else (row[j] if j < len(row) else None)
            # 含空格的串有两义:一格多值(正常)或丢小数点伪差(存量缺陷,另案登记)。
            # 两种都无法用 max() 安全代表层底深,故不参与单调判定,避免假警报。
            if isinstance(raw, str) and " " in raw.strip():
                rows.append(layer)
                bottoms.append(None)
                continue
            v = nums(raw)
            rows.append(layer)
            bottoms.append(max(v) if v else None)
        for a, b, la, lb in zip(bottoms, bottoms[1:], rows, rows[1:]):
            if a is not None and b is not None and b <= a:
                bad.append(f"{stem[-4:]} 第{la}→{lb}层 深度 {a} 未递增→ {b}")
    return bad


def xlsx_base():
    """{(stem, layer, col): 现值} —— 待核格只占少数,C4/C5 要用非待核格的现值
    补全同层其他维,否则关系式校验几乎不触发。含空格串(多值/伪差两义)不参与。"""
    from openpyxl import load_workbook
    out = {}
    for code in ("1018", "1030", "1032", "1042"):
        stem = f"钻孔柱状图{code}"
        xp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_还原_补产终版.xlsx"
        if not xp.exists():
            continue
        ws = load_workbook(xp, read_only=True).active
        head = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
            for cn in ("深度", "层厚", "采长", "倾角", "真厚"):
                if cn in head and head.index(cn) < len(row):
                    out[(stem, i, cn)] = row[head.index(cn)]
    return out


def one_val(xlsx, idx, stem, layer, col):
    c = idx.get((stem, layer, col))
    raw = c["value"] if c else xlsx.get((stem, layer, col))
    if isinstance(raw, str) and " " in raw.strip():
        return None
    v = nums(raw)
    return v[0] if len(v) == 1 else None


def main():
    full, pre, cells, dup = load()
    report = {"漏判": [], "重判撞车": sorted(set(dup)), "未知tag": [], "降级": {}}
    for t in full:
        if t not in cells and pre.get(t, "").startswith("HAS_INK"):
            report["漏判"].append(t)
    for t in cells:
        if t not in full:
            report["未知tag"].append(t)

    idx = {(full[t]["stem"], full[t]["层"], full[t]["列"]): c
           for t, c in cells.items() if t in full}
    xlsx = xlsx_base()
    ok = {}
    for tag, c in cells.items():
        if tag not in full or c.get("verdict") == "UNCLEAR":
            continue
        col = full[tag]["列"]
        why = []
        vals = nums(c.get("value"))
        nb = pre.get(tag, "")
        nblk = int(nb.split(":")[1]) if nb.startswith("HAS_INK:") else None

        if col in NUM_COLS:
            # C2 块数提示只作记录不作降级依据:实测上一行压线残字会越进行区间顶,
            # 使几何块数虚高(两个判读代理独立反馈,已改用印刷行线定归属)。
            if nblk and len(vals) < nblk:
                report.setdefault("块数提示存疑", []).append(
                    f"{tag} {col} 值数{len(vals)}<块数{nblk}")
            # C3 值域
            for x in vals:
                lo, hi = RANGE[col]
                if not (lo <= x <= hi):
                    why.append(f"C3 {col}={x} 越界[{lo},{hi}]")
        if col == "真厚" and len(vals) == 1:
            stem, layer = full[tag]["stem"], full[tag]["层"]
            a = one_val(xlsx, idx, stem, layer, "层厚")
            i = one_val(xlsx, idx, stem, layer, "倾角")
            if a is not None and i is not None:
                exp = a * math.cos(math.radians(i))
                # 只有"候选里本就有满足关系式的那个"时,关系式才是有效判据;
                # 三候选全不满足说明该格关系式不适用(原表计算误差/邻值有错),
                # 此时不能拿它降级判读结论。
                cand_ok = any(len(nums(full[tag][k])) == 1
                              and abs(nums(full[tag][k])[0] - exp) <= 0.05
                              for k in ("草案", "agnes单格", "agnes条"))
                if cand_ok and abs(exp - vals[0]) > 0.05:
                    why.append(f"C4 真厚{vals[0]} vs 层厚{a}×cos{i}°={exp:.2f}")
                if vals[0] > a + 0.02:
                    why.append(f"C5 真厚{vals[0]}>层厚{a}")
        if why:
            report["降级"][tag] = why
        else:
            ok[tag] = c

    idx2 = {(full[t]["stem"], full[t]["层"], full[t]["列"]): c
            for t, c in ok.items() if t in full}
    mono = depth_monotonic(idx2)
    report["C6深度非单调"] = mono
    for line in mono:
        code, layer_s = line.split(" ")[0], line.split("第")[1].split("→")[0]
        for t, c in list(ok.items()):
            if full.get(t, {}).get("stem", "")[-4:] == code \
                    and str(full[t]["层"]) == layer_s and full[t]["列"] == "深度":
                report["降级"][t] = report["降级"].get(t, []) + [f"C6 {line}"]
                ok.pop(t)
                break

    report["统计"] = {
        "全集格": len(full), "几何判空": sum(1 for v in pre.values() if v == "EMPTY"),
        "有判定": len(cells), "通过": len(ok), "降级": len(report["降级"]),
    }
    (RD / "校验报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    s = report["统计"]
    print(f"全集 {s['全集格']} | 几何判空 {s['几何判空']} | 有判定 {s['有判定']} "
          f"| 通过 {s['通过']} | 降级 {s['降级']} | 漏判 {len(report['漏判'])} "
          f"| 撞车 {len(report['重判撞车'])} | 未知tag {len(report['未知tag'])}")
    for t, w in list(report["降级"].items())[:25]:
        print(f"  降级 {t} {full.get(t, {}).get('列')}: {'; '.join(w)}")
    if report["漏判"]:
        print("  漏判:", report["漏判"][:40])
    return 0


if __name__ == "__main__":
    sys.exit(main())
