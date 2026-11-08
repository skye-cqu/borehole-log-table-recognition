# -*- coding: utf-8 -*-
"""合并视觉判读结果 → apply_review 回写格式 + 全量判读台账。

只把"机器校验通过"的格写入回用文件;降级格与 UNCLEAR 格保留"待人审"不动,
并全部落进台账供审计(含代理来源、置信、理由、降级原因)。

输出:
  runs/复核直览/视觉回写.json    {code: {"层:列": 值}}   → apply_review.py 输入
  runs/复核直览/判读台账.json    全 409 格逐格账目
用法: python src/tools/merge_verdicts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

RD = paths.RUNS_DIR / "复核直览"


def clean_value(v) -> str:
    return str(v if v not in (None, "None") else "").strip()


RANGE = {"深度": (0, 800), "层厚": (0, 60), "采长": (0, 60),
         "倾角": (0, 90), "真厚": (0, 60)}


def load_recheck():
    """第二轮高分辨率复核结论:tag → {verdict2,value2,conf2,reason2}。"""
    out = {}
    for f in sorted(RD.glob("复核_*.json")):
        for c in json.loads(f.read_text(encoding="utf-8")).get("cells", []):
            out[c["tag"]] = {**c, "_src": f.name}
    return out


def in_range(col, value):
    """改判值只过值域这一道(关系式需同层三值,已在第一轮校验覆盖)。"""
    if col not in RANGE:
        return True
    for tok in str(value).split():
        try:
            x = float(tok)
        except ValueError:
            continue
        lo, hi = RANGE[col]
        if not (lo <= x <= hi):
            return False
    return True


HEADERS = ("地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述")


def header_contam(col, layer, val) -> bool:
    """第1~2层格若判读值就是表头列名(或其片段)→ OCR 把表头当数据读了。
    实测 1030 第1层地质时代格现值'地 质 时',裁片内全是印刷表头、无手写内容。"""
    if layer > 2:
        return False
    v = str(val).replace(" ", "").strip()
    return bool(v) and col.startswith(v)


def scan_header_rows():
    """4 张终版表**全表**扫"值=列名前缀"的格:实测 1030 第1行 8 列全是印刷表头
    (OCR 把表头当成一个数据行整行误入),不止待核集里那一格。
    只清值不删行——裁片行号与 xlsx 行号同源(都含这一行),删行会让全部层号错位。
    """
    from openpyxl import load_workbook
    out = {}
    for code in ("1018", "1030", "1032", "1042"):
        xp = paths.RUNS_DIR / "table_reconstruct" / f"钻孔柱状图{code}_还原_补产终版.xlsx"
        if not xp.exists():
            continue
        ws = load_workbook(xp, read_only=True).active
        head = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
            if i > 2:
                break
            for cn in HEADERS:
                if cn not in head:
                    continue
                v = row[head.index(cn)]
                if isinstance(v, str):
                    s = v.replace(" ", "").strip()
                    if len(s) >= 2 and cn.startswith(s):
                        out.setdefault(code, {})[f"{i}:{cn}"] = v
    return out


def main():
    tags = json.loads((RD / "tag映射.json").read_text(encoding="utf-8"))
    pre = json.loads((RD / "几何预判.json").read_text(encoding="utf-8"))
    rep = json.loads((RD / "校验报告.json").read_text(encoding="utf-8"))
    verdicts = {}
    for f in sorted(RD.glob("判定_*.json")):
        for c in json.loads(f.read_text(encoding="utf-8")).get("cells", []):
            verdicts[c["tag"]] = {**c, "_src": f.name}
    recheck = load_recheck()

    idx = {r["tag"]: {**r, "stem": s} for s, rows in tags.items() for r in rows}
    writeback, ledger = {}, []
    n_pass = n_down = n_unclear = n_empty = n_missing = n_range = n_contam = 0

    for tag, cell in idx.items():
        code = cell["stem"][-4:]
        col = cell["列"]
        key = f"{cell['层']}:{cell['列']}"
        rec = {"tag": tag, "图": code, "层": cell["层"], "列": cell["列"],
               "A草案": cell.get("草案"), "B单格": cell.get("agnes单格"),
               "C条带": cell.get("agnes条")}
        v = verdicts.get(tag)
        if v is None:
            if pre.get(tag) == "EMPTY":
                rec.update(状态="几何判空", 采用值="",
                           依据="本格行区间内无墨段;C条带的值经核对为邻列串扰")
                writeback.setdefault(code, {})[key] = ""
                n_empty += 1
            else:
                rec.update(状态="无判读", 采用值=None, 依据="代理未覆盖该格")
                n_missing += 1
            ledger.append(rec)
            continue

        first = clean_value(v.get("value"))
        final, 复核, hard = first, "", v.get("verdict") == "UNCLEAR"
        if tag in rep["降级"]:
            hard = True
            rec["机器校验"] = "; ".join(rep["降级"][tag])
        rc = recheck.get(tag)
        if rc:
            v2 = rc.get("verdict2")
            rec.update(复核判定=v2, 复核值=clean_value(rc.get("value2")),
                       复核置信=rc.get("conf2"), 复核理由=rc.get("reason2"),
                       复核来源=rc["_src"])
            if v2 == "REVISE" and rec["复核值"]:
                复核 = f"改判 {first}→{rec['复核值']}"
                final, hard = rec["复核值"], False
            elif v2 == "CONFIRM" and first:
                复核 = "二次一致"
                hard = tag in rep["降级"]          # 算术矛盾不因复读一致而解除
            elif v2 == "STILL_UNCLEAR":
                复核 = "两轮不定"
                hard = True
        rec.update(判读=final, verdict=v.get("verdict"), conf=v.get("conf"),
                   理由=v.get("reason"), 来源文件=v["_src"], 复核=复核)
        if hard:
            rec.update(状态="待人审", 采用值=None,
                       依据=rec.get("机器校验") or "两轮判读无法确定")
            n_unclear += 1 if v.get("verdict") == "UNCLEAR" else 0
            n_down += 1 if tag in rep["降级"] else 0
        elif col in RANGE and not in_range(col, final):
            rec.update(状态="待人审", 采用值=None, 依据=f"值域自检不过 {final}")
            n_range += 1
        elif header_contam(col, cell["层"], final):
            rec.update(状态="可回写", 采用值="@EMPTY",
                       依据=f"判读值'{final}'即表头列名,本格无手写内容→清除")
            writeback.setdefault(code, {})[key] = "@EMPTY"
            n_contam += 1
            n_pass += 1
        else:
            rec.update(状态="可回写", 采用值=final)
            writeback.setdefault(code, {})[key] = final
            n_pass += 1
        ledger.append(rec)

    for code, d in scan_header_rows().items():
        for key, old in d.items():
            layer, name = key.split(":", 1)
            if writeback.setdefault(code, {}).get(key) == "@EMPTY":
                continue
            writeback[code][key] = "@EMPTY"
            n_contam += 1
            ledger.append({"tag": "(全表扫描)", "图": code, "层": int(layer), "列": name,
                           "状态": "可回写", "采用值": "@EMPTY",
                           "依据": f"印刷表头误入数据行,原值 {old!r} →清除"})

    (RD / "视觉回写.json").write_text(
        json.dumps(writeback, ensure_ascii=False, indent=1), encoding="utf-8")
    (RD / "判读台账.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    n_rev = sum(1 for x in ledger if x.get("复核判定") == "REVISE")
    n_con = sum(1 for x in ledger if x.get("复核判定") == "CONFIRM")
    n_suc = sum(1 for x in ledger if x.get("复核判定") == "STILL_UNCLEAR")
    print(f"全集 {len(idx)} | 可回写 {n_pass} | 几何判空 {n_empty} | 待人审 "
          f"{sum(1 for x in ledger if x['状态']=='待人审')} (UNCLEAR {n_unclear} "
          f"/ 校验降级 {n_down} / 值域 {n_range}) | 无判读 {n_missing}")
    print(f"二次复核: 一致 {n_con} / 改判 {n_rev} / 仍不定 {n_suc}")
    print(f"回写文件 {sum(len(v) for v in writeback.values())} 键 → 视觉回写.json"
          f"(其中表头污染清除 {n_contam} 格)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
