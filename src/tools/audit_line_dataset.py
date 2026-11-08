# -*- coding: utf-8 -*-
"""行列线数据集回读校验：从落盘的文件重新数一遍，跟清单对账，不过就退出码非 0。

查的是"交付物自己对不对"（计数、重复 id、越界坐标、折线点数、图幅尺寸、缺图），
外加一条 **无弦断言**：列线/外框边每个真段的相邻两点，必须同属一条阶段4 碎片，
否则两点距离必须 ≤TOUCH px —— 这正是 P10 锯齿的可执行定义，防它以后偷偷长回来。
不查"线判得准不准"——后者由 runs/tmp 的三把尺子和用户肉眼核验负责。

用法: python src/tools/audit_line_dataset.py [交付目录]     # 默认 paths.LINE_DELIVERY.dir
"""
import csv as _csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None          # 叠加图是 3200×4 万量级的巨图，去掉解压炸弹告警

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import col_segments                                   # noqa: E402

bad = []
KINDS = ("row", "col", "edge")


def chk(cond, msg):
    if not cond:
        bad.append(msg)


def main():
    argv = sys.argv[1:]
    if "--against-manifest" in argv:
        from src.tools.make_manifest import check
        d = Path(next(a for a in argv if a != "--against-manifest"))
        r = check(d)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(1 if (r["added"] or r["missing"] or r["changed"]) else 0)
    out = (paths.line_delivery(Path(argv[0])) if argv else paths.LINE_DELIVERY)
    man = json.load(open(out.manifest, encoding="utf-8"))

    per = {}
    for p in sorted(out.json.glob("*.json")):
        d = json.load(open(p, encoding="utf-8"))
        per[d["image"]] = d
    chk(len(per) == man["n_images"], f"每张 JSON {len(per)} ≠ 清单 {man['n_images']}")

    # 线级 / 点级 CSV：表头在，行数与清单对得上
    with open(out.lines_csv, encoding="utf-8-sig", newline="") as f:
        ln_rows = list(_csv.DictReader(f))
    with open(out.pts_csv, encoding="utf-8-sig", newline="") as f:
        pt_rows = list(_csv.DictReader(f))
    for k in KINDS:
        want = man[f"n_{k}_segs"]
        chk(sum(1 for r in ln_rows if r["kind"] == k) == want,
            f"线级 CSV {k} 段数 ≠ 清单 {want}")
    chk(len(ln_rows) == sum(man[f"n_{k}_segs"] for k in KINDS), "线级 CSV 总行数与清单不符")
    chk(len({r["line_id"] for r in ln_rows}) == len(ln_rows), "线级 CSV 有重复 line_id")
    cnt = Counter(r["line_id"] for r in pt_rows)
    chk(sum(cnt.values()) == man["n_points"], f"点级行数 {sum(cnt.values())} ≠ 清单 {man['n_points']}")
    chk(all(v >= 2 for v in cnt.values()), "有折线点数 <2 的线")

    # 逐张：清单计数 = JSON 计数 = 点级计数；坐标在图幅内；叠加图尺寸 = 原图尺寸；段内无弦
    for image, d in sorted(per.items()):
        for k in KINDS:
            chk(sum(1 for r in d["lines"] if r["kind"] == k) == d[f"n_{k}_segs"],
                f"{image} JSON 内部 {k} 段计数不符")
        m = next((x for x in man["images"] if x["image"] == image), None)
        chk(m is not None and all(m[f"n_{k}_segs"] == d[f"n_{k}_segs"] for k in KINDS),
            f"{image} 清单段数不符")
        chk(d["n_cols"] == len({r["col_index"] for r in d["lines"] if r["kind"] == "col"}),
            f"{image} 列线条数不符")
        chk(sum(cnt[l["line_id"]] for l in d["lines"]) ==
            sum(len(l["points"]) for l in d["lines"]), f"{image} 点级 CSV 与 JSON 折点数不符")
        seg = col_segments.frag_points(image)
        for l in d["lines"]:
            x0, y0, x1, y1 = l["bbox"]
            chk(l["n_pts"] == len(l["points"]), f"{l['line_id']} n_pts ≠ 实际点数")
            chk(x0 >= 0 and y0 >= 0, f"{l['line_id']} 坐标为负")
            chk(x1 <= d["width"] and y1 <= d["height"], f"{l['line_id']} 坐标越出图幅")
            if l["kind"] != "row" and l["backing"] == "frag":
                v = col_segments.chord_violations(
                    [(np.asarray(l["points"], float), json.loads(l["segment_ids"])
                      if isinstance(l["segment_ids"], str) else l["segment_ids"])], seg)
                chk(not v, f"{l['line_id']} 有 {len(v)} 处无弦越界" +
                    (f"，最远 {max(x[2] for x in v):.0f}px" if v else ""))
        ov, raw = (out.overlay / f"{image}.png", paths.RAW_DIR / f"{image}.JPG")
        chk(ov.exists() and raw.exists(), f"{image} 缺叠加图或原图")
        if ov.exists() and raw.exists():
            # 只读文件头不整幅解码：Image.open 拿 size 是惰性的，30 张也不占内存
            chk(Image.open(ov).size == Image.open(raw).size, f"{image} 叠加图尺寸 ≠ 原图")

    print(f"回读 {out.dir.name}：{len(per)} 张，层界 {man['n_layer_rows']} → 行线段 "
          f"{man['n_row_segs']}；列线 {man['n_cols']} 条→{man['n_col_segs']} 段；外框边 "
          f"{man['n_edges']}→{man['n_edge_segs']} 段；断口 {man['n_col_gaps']} 处；"
          f"带内剔 {man['n_dropped']}；折点 {man['n_points']}")
    if bad:
        print("不合格：")
        for b in bad[:40]:
            print("  -", b)
        sys.exit(1)
    print("校验通过（含无弦断言）")


if __name__ == "__main__":
    main()
