# -*- coding: utf-8 -*-
"""阶段6：把视觉 LLM 验收结论应用为最终角色，输出全图验收叠加图。
角色来源 = 视觉验收结论.md（人工+视觉LLM 逐编号判定）：
  column=真列（红粗线+编号圈）；frame=外框（灰）；content=误编内容线（压暗）；
  unknown=存疑（橙）。未在 verdict 里的既有 others 照旧压暗。"""
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

# 视觉验收结论（详 runs/table_reconstruct/视觉验收结论.md）：每图 content/frame/unknown 编号
VERDICT = {
    "1015": {}, "1017": {}, "1019": {}, "1018": {},
    "1016": {"content": [10, 11], "frame": [14]},
    "1020": {"frame": [1], "content": [11], "unknown": [4, 7]},
    "1021": {"frame": [11]}, "1022": {"frame": [1]},
    "1023": {"frame": [1, 12]}, "1024": {"frame": [1, 11]},
    "1025": {"frame": [1, 10]}, "1026": {"frame": [1, 12]},
    "1027": {"frame": [1]}, "1028": {"frame": [1]}, "1029": {"frame": [1]},
    "1030": {"content": [8, 11]}, "1031": {"content": [9, 12]},
    "1032": {"content": [11]}, "1033": {"content": [11, 12]},
    "1034": {"frame": [1], "content": [8, 11]},
    "1035": {"frame": [1, 11]},
    "1036": {"frame": [1, 2, 13], "content": [12]},
    "1037": {"frame": [1, 2, 13], "content": [12]},
    "1038": {"frame": [1, 13], "content": [12], "unknown": [9]},
    "1039": {"frame": [1, 13], "content": [12]},
    "1040": {"frame": [1, 12, 13, 21], "content": [8, 9, 28]},
    "1041": {"frame": [12, 13, 23, 24, 34]},
    "1042": {"frame": [1, 12, 13, 24, 25, 27, 35], "content": [11, 23, 26, 34]},
    "1043": {"content": [8, 11, 19, 22, 29, 32]},
    "1044": {"frame": [1], "content": [16, 17, 18, 28], "unknown": [27]},
}


def apply(stem):
    n = stem.replace("钻孔柱状图", "")
    v = VERDICT.get(n, {})
    bad = {"content", "frame", "unknown"}
    # track 源已退役:本脚本按"编号"组织裁决,无 track 编号则无意义 → 显式报错
    tp = paths.TRACK_GROUP_DIR / f"{stem}_列判定.json"
    if not tp.exists():
        raise SystemExit(f"{stem}: track 源已退役({tp.name} 不存在);"
                         f"裁决表按 track 编号组织,该路径不可用")
    col = json.load(open(tp, encoding="utf-8"))
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}

    def frags_of(ids):
        """逐碎片独立绘制：每段用自己的点原样画，绝不跨碎片连线。"""
        for i in ids:
            yield np.asarray(seg[i]["points"], int).reshape(-1, 1, 2)

    orig = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR)
    viz = orig.copy()
    dim = np.zeros(viz.shape[:2], bool)
    # 既有 others（聚簇时已判内容线）压暗——逐碎片画
    for o in col["others"]:
        ids = o.get("segment_ids") or o.get("track_ids") or []
        for arr in frags_of(ids):
            cv2.polylines(dim, [arr], False, True, 3)
    # 验收降级的编号线（content/unknown）也压暗
    for s in col["separators"]:
        if s["no"] in v.get("content", []) or s["no"] in v.get("unknown", []):
            for arr in frags_of(s["segment_ids"]):
                cv2.polylines(dim, [arr], False, True, 3)
    viz[dim] = (viz[dim] * 0.45).astype(np.uint8)
    # 外框灰——逐碎片画
    for f in col["frames"]:
        for arr in frags_of(f["segment_ids"]):
            cv2.polylines(viz, [arr], False, (128, 128, 128), 3, cv2.LINE_AA)
    for s in col["separators"]:
        role = ("frame" if s["no"] in v.get("frame", [])
                else "unknown" if s["no"] in v.get("unknown", [])
                else "content" if s["no"] in v.get("content", []) else "column")
        for arr in frags_of(s["segment_ids"]):
            if role == "column":
                cv2.polylines(viz, [arr], False, (0, 0, 255), 5, cv2.LINE_AA)
            elif role == "unknown":
                cv2.polylines(viz, [arr], False, (0, 165, 255), 3, cv2.LINE_AA)
        # content 已在压暗掩码里
        if role == "column":
            allp = np.asarray([pt for sid in s["segment_ids"]
                               for pt in seg[sid]["points"]], float)
            ymid = (allp[:, 1].min() + allp[:, 1].max()) / 2
            i = int(np.argmin(np.abs(allp[:, 1] - ymid)))
            x, y = int(allp[i, 0]), int(allp[i, 1])
            cv2.circle(viz, (x, y), 16, (0, 0, 255), 3, cv2.LINE_AA)
            cv2.putText(viz, str(s["no"]), (x - 11, y + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3, cv2.LINE_AA)
            # 顶部大号编号（供 Agnes 顶部 3200×3200 裁片识读）
            ytag = int(allp[:, 1].min()) + 150
            j = int(np.argmin(np.abs(allp[:, 1] - ytag)))
            x2, y2 = int(allp[j, 0]), int(allp[j, 1])
            cv2.circle(viz, (x2, y2), 26, (0, 0, 255), 4, cv2.LINE_AA)
            cv2.putText(viz, str(s["no"]), (x2 - 20, y2 + 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4, cv2.LINE_AA)
    txt = f"red+No.=column({sum(1 for s in col['separators'] if s['no'] not in sum(v.values(), []))})  gray=frame  dim=content"
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 2, cv2.LINE_AA)
    out = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_验收叠加图.png"
    cv2.imwrite(str(out), viz, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_验收叠加图_预览.jpg"),
                half, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return n


def main():
    for n in sorted(VERDICT):
        apply("钻孔柱状图" + n)
        print(n, "ok")


if __name__ == "__main__":
    main()
