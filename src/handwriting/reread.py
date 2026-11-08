# -*- coding: utf-8 -*-
"""重裁复读证据引擎(可复用):对指定格从原图裁片做 RapidOCR 复读,落证据 JSON。

吃  表头映射 keep(列 x 区间)+ 行区间缓存 row_ivs(行 y 区间)+ 原图 JPG + 待复读格清单
出  runs/autoresearch_align/reread_num.json:
    {stem: {"行<r>": {role: {"ocr": str, "norm": float|null}}}}
确定性与纪律
  - RapidOCR intra_op=1(多进程池互踩教训),同裁片同读;
  - 证据文件只增不改,重跑覆盖同键;规则(取值方)与选择(往哪看)分离——
    选择清单可用"与参考表分歧"做分诊,采纳值只能由 复读+算术门 产生;
  - 裁片在内存里即用即弃,不落盘(磁盘纪律);分片写 reread_parts/,合并后即删。

CLI: python src/handwriting/reread.py [--all] [--roles=depth,thick,...]
  缺省=只读 FINALIZE_FULL_DIR 对比账里 diff/ours_empty 的数值格;--all=数值角色全格。
"""
import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import paths
from src.handwriting.cellcrop import read_cell_cands, read_cell_text
from src.handwriting.normalizers import parse_num

ROLE_KEEP = {"depth": "深度", "thick": "层厚", "length": "采长",
             "dip": "倾角", "true_thick": "真厚", "desc": "岩性描述"}
OUT = paths.AUTORESEARCH_DIR / "reread_num.json"
OUT_DESC = paths.AUTORESEARCH_DIR / "reread_desc.json"
PARTS = paths.AUTORESEARCH_DIR / "reread_parts"

_OCR = None


def _ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR(intra_op_num_threads=1)   # 满核线程在进程池互踩,实测慢12倍
    return _OCR


def targets_from_ledger(roles):
    """对比账 → 待复读格 {(stem, 行, role)}:判定 diff/ours_empty 的数值角色格。"""
    out = set()
    num_names = {ROLE_KEEP[r]: r for r in roles}
    for fp in sorted(paths.FINALIZE_FULL_DIR.glob("*_对比账.csv")):
        stem = fp.name.split("钻孔柱状图")[1][:4]
        for row in csv.DictReader(open(fp, encoding="utf-8-sig")):
            role = num_names.get(row["列"])
            if role and row["判定"] in ("diff", "ours_empty"):
                out.add((stem, int(row["行"]), role))
    return out


def targets_all(roles):
    """数值角色全格(数据行每格)。"""
    from openpyxl import load_workbook
    from src.table.finalize_tables import column_roles
    out = set()
    for fp in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
        stem = fp.name.split("钻孔柱状图")[1][:4]
        wb = load_workbook(fp, read_only=True)
        rows = list(wb.active.iter_rows(values_only=True))
        wb.close()
        idx_role = {c: r for r, c in column_roles(rows[0]).items()}
        for i, row in enumerate(rows[1:]):
            for c, role in idx_role.items():
                if role in roles:
                    out.add((stem, i + 2, role))
    return out


def targets_desc_bridged():
    """desc 复读目标:像素包桥接文件里唯一匹配回 seed 行的争议格。"""
    fp = paths.AUTORESEARCH_DIR / "pack_bridge.json"
    if not fp.exists():
        return set()
    bridge = json.loads(fp.read_text(encoding="utf-8"))
    return {(stem[5:], int(rk[1:]), "desc")
            for stem, rows in bridge.items() for rk in rows}


def targets_desc_diff():
    """desc 复读目标补全(D包外):活态与参考分歧、无复读证据、参考非空的格。

    分诊按与参考分歧(纪律允许:采纳值仍只由 复读+对照门 产生);
    参考空/行未配对→无对照门,读了也采不了,不进目标。
    """
    from openpyxl import load_workbook

    from src.handwriting.normalizers import norm_desc
    from src.handwriting.rules import _desc_evidence, _ref_desc_map
    from src.table.finalize_tables import column_roles
    refs = _ref_desc_map()
    have = _desc_evidence()
    out = set()
    for fp in sorted(paths.AUTORESEARCH_CANDIDATE_DIR.glob("*_整合.xlsx")):
        stem = fp.name[:-len("_整合.xlsx")]
        wb = load_workbook(fp, read_only=True)
        grid = list(wb.active.iter_rows(values_only=True))
        wb.close()
        c = column_roles(grid[0]).get("desc")
        if c is None:
            continue
        for i, row in enumerate(grid[1:]):
            if (stem, i) not in refs or f"行{i + 2}" in have.get(stem, {}):
                continue
            ref_n = norm_desc(refs[(stem, i)])
            if not ref_n:
                continue
            live = row[c] if c < len(row) else None
            if norm_desc(live) != ref_n:
                out.add((stem[5:], i + 2, "desc"))
    return out


def worker(payload):
    """单图复读:吃 (stem, [(行,role)]),证据分片落盘。batch 约定 (stem, ok, info)。"""
    stem, cells = payload
    try:
        import cv2
        text_mode = any(role == "desc" for _, role in cells)
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                            f"钻孔柱状图{stem}_表头映射.json", encoding="utf-8"))
        keep = {}
        for r, name in ROLE_KEEP.items():
            for k in hm["keep"]:
                if k["name"] == name:
                    keep[r] = sorted(k["x_in_band"])
        cache = json.loads(paths.AUTORESEARCH_ROWCACHE.read_text(encoding="utf-8"))
        ivs = {int(k): tuple(float(a) for a in v)
               for k, v in cache[f"钻孔柱状图{stem}"]["ivs"].items()}
        gray = cv2.imread(str(paths.RAW_DIR / f"钻孔柱状图{stem}.JPG"),
                          cv2.IMREAD_GRAYSCALE)
        ocr = _ocr()
        ev = {}
        n_read = 0
        for r, role in sorted(cells):
            if r - 2 not in ivs or role not in keep:
                continue
            x0, x1 = keep[role]
            y0, y1 = ivs[r - 2]
            if y1 - y0 > 400:
                continue             # 表头区/退化巨行:非数据行,且巨图喂det会OOM
            if role == "desc":
                text = read_cell_text(gray, x0, x1, y0, y1, ocr)
                n_read += 1
                if text:
                    ev.setdefault(f"行{r}", {})["desc"] = {"text": text}
                continue
            cands = read_cell_cands(gray, x0, x1, y0, y1, ocr)
            n_read += 1
            if cands:
                ev.setdefault(f"行{r}", {})[role] = {
                    "cands": cands,
                    "norms": [parse_num(c) for c in cands],
                }
        PARTS.mkdir(parents=True, exist_ok=True)
        (PARTS / f"{stem}.json").write_text(
            json.dumps(ev, ensure_ascii=False), encoding="utf-8")
        return stem, True, f"读{n_read}/{len(cells)} 格有读{len(ev)}"
    except Exception as e:  # noqa: BLE001
        return stem, False, f"{type(e).__name__}: {e}"


def main(argv):
    roles = {"depth", "thick", "true_thick"}   # 有采纳门的角色(dip/length 无门不读)
    all_cells = "--all" in argv
    only_stems = None
    desc_mode = "--desc" in argv
    desc_diff_mode = "--desc-diff" in argv
    for a in argv:
        if a.startswith("--roles="):
            roles = set(a.split("=", 1)[1].split(","))
        if a.startswith("--only-stems="):
            only_stems = set(a.split("=", 1)[1].split(","))
    if desc_diff_mode:
        targets = targets_desc_diff()
        desc_mode = True
    elif desc_mode:
        targets = targets_desc_bridged()
    else:
        targets = targets_all(roles) if all_cells else targets_from_ledger(roles)
    if only_stems:
        targets = {t for t in targets if t[0] in only_stems}
    per = {}
    for stem, r, role in targets:
        per.setdefault(stem, []).append((r, role))
    items = sorted(per.items())
    n_cells = sum(len(v) for _, v in items)
    print(f"待复读 {n_cells} 格 / {len(items)} 图"
          f",角色 {sorted(roles) if not desc_mode else 'desc(桥接行)'}")
    from src.core import batch
    results = batch.run_batch(items, worker, max_workers=3)
    failed = [it for it, (_s, ok, _i) in zip(items, results) if not ok]
    if failed:                                 # OOM 等瞬态失败:单进程重试一轮
        print(f"重试 {len(failed)} 张失败图(单进程)")
        retry = dict((s, (s, ok, info)) for s, ok, info in
                     batch.run_batch(failed, worker, max_workers=1))
        results = [retry.get(s, res) for s, res in
                   zip([it[0] for it in items], results)]
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    out_desc = (json.loads(OUT_DESC.read_text(encoding="utf-8"))
                if OUT_DESC.exists() else {})
    n_ev = 0
    for stem, ok, info in results:
        if not ok:
            print(f"  {stem} FAIL {info}")
            continue
        part = json.loads((PARTS / f"{stem}.json").read_text(encoding="utf-8"))
        s_out = out.setdefault(f"钻孔柱状图{stem}", {})
        s_outd = out_desc.setdefault(f"钻孔柱状图{stem}", {})
        for rk, cell in part.items():
            # 格级合并(行级 update 会把同行的其他角色证据整格替换——
            # 2026-11-05 实锤:倾角复读砸掉同行批次2 证据,批次2 21→18)
            for k, v in cell.items():
                if k == "desc":
                    s_outd[rk] = v                  # desc 文件平铺:{"行r": {"text":…}}
                else:
                    s_out.setdefault(rk, {})[k] = v
        n_ev += sum(len(v) for v in part.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_DESC.write_text(json.dumps(out_desc, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    shutil.rmtree(PARTS, ignore_errors=True)
    print(f"证据入库 {n_ev} 格 → {OUT.name}+{OUT_DESC.name}")
    bad = [s for s, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))