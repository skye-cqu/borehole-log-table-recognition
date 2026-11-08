# -*- coding: utf-8 -*-
"""数据级 diff 核验器(设计 reports/调研_阻塞与开发界方案_20260930.md §4.1)。

行线:按 line_id 对齐逐点比残差——两代数据集行判定源 md5 相同,几何应逐位相等,
     残差 >TOL 即真变更(新增/消失/漂移/点数不同),不做像素 diff、不猜原因。
列线/框边:两代表征不同(v1 整线 / v2 逐碎片段),只出计数与 backing 账,不做点级对齐。
变更行线出 1:1 对照裁片(旧|新并排),底图用两代各自的叠加图;缺叠加图只记账不裁片。
退出码:行线有任一变更 → 1(两代同源时这就是"行几何被谁动了"的报警)。

用法:
  python -u -X utf8 src/tools/review_diff.py --old <v1目录> --new <v2目录> \
      [--stems 1015 1019 ...] [--out runs/tmp/review_diff_20260930]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOL = 0.5          # px;同源行线残差实测应逐位为 0,0.5 只吸收浮点落盘误差
PAD = 150          # 裁片上下文外扩


def _load(ds: Path, stem: str) -> dict:
    return json.load(open(ds / "每张" / f"钻孔柱状图{stem}.json", encoding="utf-8"))


def diff_rows(old: dict, new: dict, tol: float = TOL) -> dict:
    a = {l["line_id"]: np.asarray(l["points"], float)
         for l in old["lines"] if l["kind"] == "row"}
    b = {l["line_id"]: np.asarray(l["points"], float)
         for l in new["lines"] if l["kind"] == "row"}
    moved, res = [], []
    for k in sorted(set(a) & set(b)):
        if a[k].shape != b[k].shape:
            moved.append({"line_id": k, "why": "点数不同", "d": None})
            continue
        d = float(np.abs(a[k] - b[k]).max())
        res.append(d)
        if d > tol:
            moved.append({"line_id": k, "why": "坐标漂移", "d": round(d, 3)})
    r = np.asarray(res, float)
    return {"n_old": len(a), "n_new": len(b), "n_moved": len(moved), "moved": moved,
            "added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
            "residual": {"max": float(r.max()) if r.size else None,
                         "p99": float(np.percentile(r, 99)) if r.size else None}}


def diff_cols(old: dict, new: dict) -> dict:
    def acc(d):
        col = [l for l in d["lines"] if l["kind"] == "col"]
        edge = [l for l in d["lines"] if l["kind"] == "edge"]
        return {"col_lines": len({l["col_index"] for l in col}),
                "col_segs": len(col),
                "edge_segs": len(edge),
                "backing": {k: sum(1 for l in col if l.get("backing") == k)
                            for k in ("frag", "fill", "extend")}}
    return {"old": acc(old), "new": acc(new)}


def _crops(stem: str, moved: list, old: dict, new: dict,
           old_dir: Path, new_dir: Path, out_dir: Path):
    """变更行线的 旧|新 1:1 对照裁片;缺叠加图返回跳过名单。"""
    ov_old = old_dir / "叠加图" / f"钻孔柱状图{stem}.png"
    ov_new = new_dir / "叠加图" / f"钻孔柱状图{stem}.png"
    if not (ov_old.exists() and ov_new.exists()):
        return [], [f"{m['line_id']} 缺叠加图" for m in moved]
    pts = {l["line_id"]: np.asarray(l["points"], float)
           for d in (old, new) for l in d["lines"] if l["kind"] == "row"}
    im_old = Image.open(ov_old)
    im_new = Image.open(ov_new)
    (out_dir / "局部1比1").mkdir(parents=True, exist_ok=True)
    made, skips = [], []
    for m in moved:
        k = m["line_id"]
        if k not in pts:
            skips.append(f"{k} 点集缺失")
            continue
        p = pts[k]
        box = (max(0, int(p[:, 0].min()) - PAD), max(0, int(p[:, 1].min()) - PAD),
               min(im_new.width, int(p[:, 0].max()) + PAD),
               min(im_new.height, int(p[:, 1].max()) + PAD))
        a, b = im_old.crop(box), im_new.crop(box)
        canvas = Image.new("RGB", (a.width + b.width + 4, max(a.height, b.height)),
                           (255, 255, 255))
        canvas.paste(a, (0, 0))
        canvas.paste(b, (a.width + 4, 0))
        fp = out_dir / "局部1比1" / f"{stem}_{k}.png"
        canvas.save(fp)
        made.append(fp.as_posix())
    return made, skips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--stems", nargs="*", default=[])
    ap.add_argument("--out", default="runs/tmp/review_diff_20260930")
    a = ap.parse_args()
    old_dir, new_dir, out_dir = Path(a.old), Path(a.new), Path(a.out)
    stems = a.stems or sorted(p.stem.removeprefix("钻孔柱状图")
                              for p in (new_dir / "每张").glob("*.json"))
    report = {"old": old_dir.as_posix(), "new": new_dir.as_posix(), "stems": {}}
    alarm = 0
    for stem in stems:
        old, new = _load(old_dir, stem), _load(new_dir, stem)
        rows, cols = diff_rows(old, new), diff_cols(old, new)
        crops, skips = ([], [])
        if rows["n_moved"] or rows["added"] or rows["removed"]:
            crops, skips = _crops(stem, rows["moved"], old, new, old_dir, new_dir, out_dir)
        n_change = rows["n_moved"] + len(rows["added"]) + len(rows["removed"])
        alarm += n_change
        report["stems"][stem] = {"rows": rows, "cols": cols, "crops": crops, "skips": skips}
        print(f"{stem}: 行线 变更 {n_change}"
              f"(漂移 {rows['n_moved']} / 新增 {len(rows['added'])} / 消失 {len(rows['removed'])})"
              f" 残差max {rows['residual']['max']};"
              f"列账 old{cols['old']['col_segs']}→new{cols['new']['col_segs']}段")
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / "diff账目.json"
    fp.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"账目 → {fp};行线变更合计 {alarm}")
    sys.exit(1 if alarm else 0)


if __name__ == "__main__":
    main()
