# -*- coding: utf-8 -*-
"""阶段6b：全竖线编号叠加图 + Agnes 分片逐编号判定。

用户指示（2026-09-02）：把所有竖线一起给 Agnes，不做预筛选，保证它能看到并分析；
过于密集处适当拆分，防止识别压力导致不精准。
- 渲染：判定.json 的全部 track（separators/frames/others）一律红色等权绘制，
  逐碎片独立画线（不跨碎片连线），主图不编号。
- 分片：标签落在顶部 图宽×图宽 裁片内的 track 按 x 排序，每片 ≤9 条，
  片内重新编号 1..N（个位数，杜绝两位数误读），片宽=标签跨度±250 提供表头上下文。
- 判定：每片放大 2 倍送 agnes-2.5-flash 判 column/content/frame/unknown；
  片内编号→全局 track 序号（gidx）由程序映射，跨片无歧义。
输出 {stem}_全竖线叠加图.png / _预览.jpg、全竖线分片/{stem}_片k.jpg、
{stem}_全竖线判定.json（merged_by_track 键=全局 track 序号 gidx）。"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table import agnes_verify as av  # noqa: E402

PROMPT = """你是表格列线验收员。图中：红色粗线+数字红圈=程序从扫描图中检出的竖向线段组（未做任何预筛选，编号为片内顺序号1..N），其中既有真列分隔线，也有表格框线、柱状条带图案边线、水文区内部竖线和噪声线。
表格表头（多数图）：地质时代|煤层标志层号|深度|层厚|采长|倾角|真厚|柱状|岩性描述|简易水文曲线。柱状列内部的条带图案边线与水文曲线区内部竖线属于内容线，不是列分隔线；表格最左、最右的竖线是外框。
任务：对图中每个数字编号对应的红线，判定它是：column（真列分隔线）/ content（内容线，如条带边、水文内线）/ frame（表格左右外框）/ unknown（无法判断）。
只输出一个 JSON 对象，格式：{"numbers": {"1": "column", "2": "content"}}"""


def load_tracks(stem):
    """判定.json 的全部 track（x 序），gidx=全局序号 1..N，role_hint 仅存档。"""
    tp = paths.TRACK_GROUP_DIR / f"{stem}_列判定.json"
    if not tp.exists():
        raise SystemExit(f"{stem}: track 源已退役({tp.name} 不存在);"
                         f"本核验按 track 分组口径,该路径不可用")
    d = json.load(open(tp, encoding="utf-8"))
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    tracks = []
    for role, groups in (("sep", d["separators"]), ("frame", d.get("frames", [])),
                         ("other", d.get("others", []))):
        for g in groups:
            ids = g.get("segment_ids") or g.get("track_ids") or []
            ids = [i for i in ids if i in seg]
            if not ids:
                continue
            pts = np.asarray([p for i in ids for p in seg[i]["points"]], float)
            tracks.append({"role_hint": role, "ids": ids, "gidx": 0,
                           "x_mid": float(np.median(pts[:, 0])),
                           "y_min": float(pts[:, 1].min())})
    tracks.sort(key=lambda t: t["x_mid"])
    for i, t in enumerate(tracks):
        t["gidx"] = i + 1
    return d, seg, tracks


def frags_of(seg, ids):
    for i in ids:
        yield np.asarray(seg[i]["points"], int).reshape(-1, 1, 2)


def render(stem, seg, tracks):
    """主图：全部 track 红色等权绘制，不编号（编号按片局部画在分片上）。"""
    orig = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR)
    viz = orig.copy()
    for t in tracks:
        for arr in frags_of(seg, t["ids"]):
            cv2.polylines(viz, [arr], False, (0, 0, 255), 5, cv2.LINE_AA)
    txt = f"red=ALL vertical tracks x{len(tracks)} (no pre-filter)"
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_全竖线叠加图.png"),
                viz, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_全竖线叠加图_预览.jpg"),
                half, [cv2.IMWRITE_JPEG_QUALITY, 85])


def plan_panels(tracks, crop_w, max_tags=9, overlap=250, min_w=600):
    """标签落在顶部裁片内的 track 按 x 切片：每片 ≤max_tags 条（片内个位数编号），
    片宽=标签跨度±overlap（留表头上下文），不足 min_w 扩展。"""
    vis = sorted((t for t in tracks if t["y_min"] + 510 < crop_w),
                 key=lambda t: t["x_mid"])
    panels, i, n = [], 0, len(vis)
    while i < n:
        j = min(i + max_tags, n) - 1
        x0 = 0 if i == 0 else max(0, int(vis[i]["x_mid"]) - overlap)
        x1 = crop_w if j == n - 1 else min(crop_w, int(vis[j]["x_mid"]) + overlap)
        if x1 - x0 < min_w:
            x1 = min(crop_w, x0 + min_w)
        panels.append((x0, x1, vis[i:j + 1]))
        i = j + 1
    return panels


def verify(stem):
    d, seg, tracks = load_tracks(stem)
    render(stem, seg, tracks)
    viz = cv2.imread(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_全竖线叠加图.png"))
    H, W = viz.shape[:2]
    crop_h = min(H, W)
    panels = plan_panels(tracks, crop_h)
    panel_dir = paths.RUNS_DIR / "table_reconstruct" / "全竖线分片"
    panel_dir.mkdir(exist_ok=True)

    prio = {"content": 0, "frame": 1, "unknown": 2, "column": 3}
    merged, raws = {}, []
    for k, (x0, x1, ptracks) in enumerate(panels, 1):
        part = viz[0:crop_h, x0:x1].copy()
        loc = []
        for i, t in enumerate(ptracks):
            allp = np.asarray([p for sid in t["ids"] for p in seg[sid]["points"]], float)
            ytag = int(allp[:, 1].min()) + (150 + (i % 3) * 180)
            j = int(np.argmin(np.abs(allp[:, 1] - ytag)))
            x2, y2 = int(allp[j, 0]) - x0, int(allp[j, 1])
            cv2.circle(part, (x2, y2), 30, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(part, (x2, y2), 30, (0, 0, 255), 5, cv2.LINE_AA)
            cv2.putText(part, str(i + 1), (x2 - 16, y2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 255), 6, cv2.LINE_AA)
            loc.append({"no": i + 1, "gidx": t["gidx"], "role_hint": t["role_hint"],
                        "x_mid": t["x_mid"], "y_min": t["y_min"]})
        big = cv2.resize(part, ((x1 - x0) * 2, crop_h * 2), interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(str(panel_dir / f"{stem}_片{k}.jpg"), big,
                    [cv2.IMWRITE_JPEG_QUALITY, 92])
        ok, jpeg = cv2.imencode(".jpg", big, [cv2.IMWRITE_JPEG_QUALITY, 92])
        content = av.ask(jpeg.tobytes(), prompt=PROMPT)
        parsed = av.parse(content)
        verdicts = {}
        if parsed:
            nums, _ = parsed
            for n, r in (nums or {}).items():
                n = str(int(n))
                verdicts[n] = r if r in prio else "unknown"
        for t in loc:  # 片内编号→全局 gidx；每条 track 只属一片，无跨片冲突
            r = verdicts.get(str(t["no"]), "unjudged")
            merged[t["gidx"]] = r
        raws.append({"panel": [x0, x1], "parsed": 1 if parsed else 0,
                     "n_tracks": len(ptracks),
                     "map": [{"no": t["no"], "gidx": t["gidx"],
                              "role_hint": t["role_hint"]} for t in loc],
                     "head": content[:200]})
    by_role = {}
    for t in tracks:
        by_role.setdefault(t["role_hint"], []).append(t["gidx"])
    cols = sorted(g for g, v in merged.items() if v == "column")
    out = {"image": stem, "n_tracks": len(tracks),
           "n_visible": sum(1 for t in tracks if t["y_min"] + 510 < crop_h),
           "track_nos": by_role,
           "merged_by_track": {str(k): v for k, v in sorted(merged.items())},
           "columns_gidx": cols,
           "n_panels": len(panels), "raws": raws,
           "crop": [0, 0, W, crop_h]}
    json.dump(out, open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_全竖线判定.json",
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def main():
    stems = sys.argv[1:]
    if not stems or stems == ["--all"]:
        stems = sorted(p.stem.replace("_列判定", "")
                       for p in paths.TRACK_GROUP_DIR.glob("钻孔柱状图*_列判定.json"))
        if not stems:      # track 源已退役:回退到 6b 表头映射清单(同为 30 图全集)
            stems = sorted(p.name[:-len("_表头映射.json")]
                           for p in (paths.RUNS_DIR / "table_reconstruct").glob("钻孔柱状图*_表头映射.json"))
            print(f"track 源已退役,按表头映射清单取 {len(stems)} 张")
    if len(stems) > 1:
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(verify, s): s for s in stems}
            for fu in as_completed(futs):
                s = futs[fu]
                try:
                    o = fu.result()
                    np_ = sum(r["parsed"] for r in o["raws"])
                    print(s, "tracks:", o["n_tracks"], "片:", o["n_panels"],
                          "解析:", np_, "column:", len(o["columns_gidx"]), flush=True)
                except Exception as e:
                    print(s, "FAIL", repr(e)[:120], flush=True)
    else:
        o = verify(stems[0])
        np_ = sum(r["parsed"] for r in o["raws"])
        print(stems[0], "tracks:", o["n_tracks"], "片:", o["n_panels"],
              "解析:", np_, "column gidx:", o["columns_gidx"], flush=True)


if __name__ == "__main__":
    main()
