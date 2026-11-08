# -*- coding: utf-8 -*-
"""阶段6：固化 30 图列结构，输出定稿 JSON + 定稿叠加图。

角色来源 = 逐图坐标间距拟合 + 表头带放大核验（_dbg_*_hdr.jpg 裁片），
并以 Agnes 判定、视觉验收结论作旁证。历史叠加图所用 VERDICT 编号基于
重生成前的旧分隔线集合，与现 JSON 编号错位，本表为其修正版。

列线只由第四阶段候选段构成（segment_ids 原样沿用），不创造、不拟合。
缺检真线仅在 note 中声明，不画线、不补线。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

# 每图最终角色（no 为 钻孔柱状图NNNN_列判定.json 中 separators 的编号）。
# columns: 真列分隔线（按 x 排序后重新编号 1..N）；frame/content: 其余角色；
# reclaim_frames: frames[] 中实为列界被误分类的线（按 x_at_mid 匹配）回收为列。
FINAL = {
    "1015": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": [11]},
    "1016": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 11], "content": []},
    "1017": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 12], "content": [11]},
    "1018": {"columns": [1, 2, 3, 4, 5, 6, 7, 8], "frame": [], "content": [],
             "missing": "柱状|岩性未检出"},
    "1019": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": []},
    "1020": {"columns": [2, 3, 4, 5, 6, 7, 8], "frame": [1], "content": [],
             "reclaim_frames": [("岩性|水文", 2356)], "missing": "柱状|岩性未检出(在others中)"},
    "1021": {"columns": [1, 2, 3, 4, 5, 6, 7, 8, 9], "frame": [11], "content": [10]},
    "1022": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": []},
    "1023": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 12], "content": [11]},
    "1024": {"columns": [2, 3, 4, 5, 6, 7, 8, 9], "frame": [1, 10], "content": [],
             "missing": "真厚|柱状未检出(x≈800黑线)"},
    "1025": {"columns": [2, 3, 4, 5, 6, 7, 8, 9], "frame": [1, 10], "content": [],
             "missing": "岩性|水文未检出"},
    "1026": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": [11]},
    "1027": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": []},
    "1028": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": []},
    "1029": {"columns": [1, 2, 3, 4, 5, 6, 7, 8, 9], "frame": [], "content": []},
    "1030": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": [11]},
    "1031": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 11], "content": []},
    "1032": {"columns": [1, 2, 3, 4, 5, 6], "frame": [], "content": [],
             "reclaim_frames": [("深度|层厚", 65)],
             "missing": "扫描件左缘被裁：地质时代/煤层标志层号两列不在图内"},
    "1033": {"columns": [2, 3, 4, 5, 6, 7, 8, 9], "frame": [1], "content": [],
             "missing": "真厚|柱状未检出"},
    "1034": {"columns": [3, 4, 5, 6, 7, 8, 9, 10, 11], "frame": [1, 2], "content": [12]},
    "1035": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 11], "content": []},
    "1036": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 12], "content": [11]},
    "1037": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": [11]},
    "1038": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 12], "content": [11]},
    "1039": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": [11]},
    "1040": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": []},
    "1041": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1, 11], "content": []},
    "1042": {"columns": [2, 3, 4, 5, 6, 7, 8, 9], "frame": [1, 11], "content": [10],
             "missing": "煤层|深度未检出"},
    "1043": {"columns": [1, 2, 3, 4, 5, 6, 7, 8, 9], "frame": [], "content": [10]},
    "1044": {"columns": [2, 3, 4, 5, 6, 7, 8, 9, 10], "frame": [1], "content": []},
}

COLUMN_NAMES = ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角",
                "真厚", "柱状", "岩性描述", "简易水文曲线"]


def finalize(n):
    stem = "钻孔柱状图" + n
    spec = FINAL[n]
    # 本脚本按 track 编号硬编码(30 图 FINAL 表),track 源已退役 → 显式报错,不再抛裸 FileNotFoundError
    tp = paths.TRACK_GROUP_DIR / f"{stem}_列判定.json"
    if not tp.exists():
        raise SystemExit(f"{stem}: track 源已退役({tp.name} 不存在),本脚本(编号硬编码)不可用;"
                         f"现口径请走 6b 表头映射 + _分割线 sep_pts")
    col = json.load(open(tp, encoding="utf-8"))
    seps = {s["no"]: s for s in col["separators"]}
    frames = col.get("frames", [])

    for no in spec["columns"] + spec["frame"] + spec["content"]:
        assert no in seps, f"{stem}: 编号{no}不在分隔线集合中"

    reclaim = []
    for tag, x_hint in spec.get("reclaim_frames", []):
        # 按给定 x_at_mid 匹配 frames 中被误分类为框线的列界，回收为列
        assert frames, f"{stem}: 无 frames 可回收"
        f = min(frames, key=lambda f: abs(f["x_at_mid"] - x_hint))
        assert abs(f["x_at_mid"] - x_hint) < 30, \
            f"{stem}: 回收 {tag} 失败，最近 frame x={f['x_at_mid']}"
        reclaim.append(f)

    cols = sorted((seps[no] for no in spec["columns"]), key=lambda s: s["x_at_mid"])
    cols += sorted(reclaim, key=lambda f: f["x_at_mid"])
    cols.sort(key=lambda s: s["x_at_mid"])
    frame_seps = [seps[no] for no in spec["frame"]]
    content_seps = [seps[no] for no in spec["content"]]
    frame_other = [f for f in frames if f not in reclaim]

    names = COLUMN_NAMES[-len(cols):] if len(cols) == 10 else None
    out = {
        "image": stem,
        "columns": [{"index": i + 1,
                     "name": names[i] if names else None,
                     "src": s.get("no") or "frames",
                     "x_at_mid": s["x_at_mid"], "y": s["y"],
                     "segment_ids": s["segment_ids"]}
                    for i, s in enumerate(cols)],
        "frames": [{"x_at_mid": f["x_at_mid"], "segment_ids": f["segment_ids"]}
                   for f in frame_other],
        "content": [{"src": s["no"], "x_at_mid": s["x_at_mid"],
                     "segment_ids": s["segment_ids"]} for s in content_seps],
        "others": col.get("others", []),
        "missing": spec.get("missing", ""),
    }
    json.dump(out, open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json",
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    render(stem, out)
    return len(cols)


def frags_of(seg, ids):
    """逐碎片独立绘制：每段用自己的点原样画，绝不跨碎片连线。"""
    for i in ids:
        yield np.asarray(seg[i]["points"], int).reshape(-1, 1, 2)


def render(stem, struct):
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    orig = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR)
    viz = orig.copy()

    dim = np.zeros(viz.shape[:2], bool)
    for o in struct["others"]:
        ids = o.get("segment_ids") or o.get("track_ids") or []
        for arr in frags_of(seg, ids):
            cv2.polylines(dim, [arr], False, True, 3)
    for c in struct["content"]:
        for arr in frags_of(seg, c["segment_ids"]):
            cv2.polylines(dim, [arr], False, True, 3)
    # 装饰框（side=deco/None）不是分割边界，压暗处理；绿线只画表格左右边界
    for f in struct["frames"]:
        if f.get("side") not in ("left", "right"):
            for arr in frags_of(seg, f["segment_ids"]):
                cv2.polylines(dim, [arr], False, True, 3)
    viz[dim] = (viz[dim] * 0.45).astype(np.uint8)

    for f in struct["frames"]:
        if f.get("side") not in ("left", "right"):
            continue
        for arr in frags_of(seg, f["segment_ids"]):
            cv2.polylines(viz, [arr], False, (0, 200, 0), 5, cv2.LINE_AA)

    for c in struct["columns"]:
        allp = np.asarray([pt for sid in c["segment_ids"]
                           for pt in seg[sid]["points"]], float)
        for arr in frags_of(seg, c["segment_ids"]):
            cv2.polylines(viz, [arr], False, (0, 0, 255), 5, cv2.LINE_AA)
        ymid = (allp[:, 1].min() + allp[:, 1].max()) / 2
        i = int(np.argmin(np.abs(allp[:, 1] - ymid)))
        x, y = int(allp[i, 0]), int(allp[i, 1])
        cv2.circle(viz, (x, y), 16, (0, 0, 255), 3, cv2.LINE_AA)
        cv2.putText(viz, str(c["index"]), (x - 11, y + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3, cv2.LINE_AA)
        ytag = int(allp[:, 1].min()) + 150
        j = int(np.argmin(np.abs(allp[:, 1] - ytag)))
        x2, y2 = int(allp[j, 0]), int(allp[j, 1])
        cv2.circle(viz, (x2, y2), 26, (0, 0, 255), 4, cv2.LINE_AA)
        cv2.putText(viz, str(c["index"]), (x2 - 20, y2 + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4, cv2.LINE_AA)

    ncol = len(struct["columns"])
    txt = f"red+No.=column x{ncol}  green=table edge(L/R)  dim=content/deco"
    if struct["missing"]:
        txt += "  |  " + struct["missing"]
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_定稿叠加图.png"),
                viz, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_定稿叠加图_预览.jpg"),
                half, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    only = sys.argv[1:] or sorted(FINAL)
    for n in only:
        k = finalize(n)
        print(n, "columns:", k, flush=True)


if __name__ == "__main__":
    main()
