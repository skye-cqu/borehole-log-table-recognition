# -*- coding: utf-8 -*-
"""阶段5 实验：碎片 → 物理竖线 Track 归组（像素证据沿线追踪）。

冻结输入线段：只读 table_line_detect 的坐标 JSON（sha256 前后校验），
不删除、不筛选、不改坐标、不延长、不新增任何线段；唯一新增的是归属关系
Track = [segment_id, ...]，以及每个接续点的归组证据（证据不写回为线条）。

方法（第一性原理：人是顺着墨迹看下去的）：
  1. 把碎片段端点放回原图墨迹（原图 JPG 现场自适应二值化）上；
  2. 从段底端沿局部方向以小锥窗口逐像素探墨（动量转向、倾角限幅），
     自然穿过行线交叉点——横向对称的行线墨迹不会带偏方向；
  3. 墨尽（真断口）时按当前方向死推跳断口，跳距受
     「横向漂移 ≤ drift_max」随当前倾角动态封顶——结构化实现用户
     「斜率像 + 延伸对齐 + 缺口可用同斜率补」三要件；
  4. 落点必须命中未归属碎片段的顶端（横向 ≤ tol_land，小于实测
     不同线最小间距 37px 的一半）且方向一致才接上，否则不接。

不判断 Track 是否真表格列；不处理岩层/水文干扰区域；无 DBSCAN/分箱/全局斜率。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402

# ---- 可调参数（实测校准：真线倾角 ±3.3°内、线宽 4-5px、不同线最小间距 37px）----
PARAMS = {
    "bin_block": 31,        # 自适应二值化窗口
    "bin_c": 12,            # 自适应二值化 C
    "look_t": 3,            # 墨步探窗：前方 1..t px
    "look_lat": 2,          # 墨步探窗：横向 ±2px
    "max_tilt_deg": 25.0,   # 墨步相对竖直的最大倾角（真线 ±3.3°，防顺行线/曲线逃跑）
    "blend": 0.15,          # 动量：每步方向更新中新步向权重（≈每步最大转 10°）
    "tol_land": 12.0,       # 落点横向容差（< 不同线最小间距 37px 的一半）
    "land_back": 3,         # 落点 y 窗口：顶端允许在当前点上方 3px（y 重叠容差）
    "land_ahead": 10,       # 落点 y 窗口：顶端允许在当前点下方 10px
    "dir_tol_deg": 10.0,    # 接续时两段方向一致阈值
    "gap_max": 150,         # 死推跳断口上限（px）
    "drift_max": 12.0,      # 死推横向漂移上限（= tol_land，保证落点不会漂到邻线）
    "step_cap": 6000,       # 单次追踪总步数保险丝
}


# ---------------------------------------------------------------- 数据准备
def load_segments(json_path: Path):
    """读候选 JSON，取 vertical+high 碎片段（只读），派生端点与端部方向。"""
    with open(json_path, "r", encoding="utf-8") as f:
        raw = f.read()
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    data = json.loads(raw)
    segs = []
    for s in data["lines"]:
        if s["direction"] != "vertical" or s["label"] != "high":
            continue
        pts = np.asarray(s["points"], dtype=float)
        i_top = int(pts[:, 1].argmin())
        i_bot = int(pts[:, 1].argmax())
        adj_top = pts[1] if i_top == 0 else pts[i_top - 1]
        adj_bot = pts[-2] if i_bot == len(pts) - 1 else pts[i_bot + 1]
        segs.append({
            "id": s["id"],
            "top": pts[i_top],            # 顶端点 (x, y)
            "bot": pts[i_bot],            # 底端点 (x, y)
            "v_top": _dir_down(pts[i_top], adj_top),   # 顶端向下的单位方向
            "v_bot": _dir_down(pts[i_bot], adj_bot),   # 底端向下的单位方向
            "orig_points": s["points"],   # 原始坐标（只读，可视化用）
        })
    return segs, data["width"], data["height"], sha


def _dir_down(p_end, p_adj):
    """端点处向下的单位方向（沿靠端点的 RDP 腿）。"""
    v = np.asarray(p_adj, float) - np.asarray(p_end, float)
    if v[1] < 0:
        v = -v
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-6 else np.array([0.0, 1.0])


def binarize(gray: np.ndarray, prm: dict) -> np.ndarray:
    """原图灰度 → 墨迹 bool 图（自适应高斯阈值；仅作证据，不产出线条）。"""
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, prm["bin_block"], prm["bin_c"])
    return bw == 0


# ---------------------------------------------------------------- 像素追踪
def _probe(ink, p, d, look_t, look_lat):
    """在 p 前方沿 d 的锥窗内探墨。命中返回 (步进向量, True)。深度优先、
    横向取离轴线最近者——行线交叉点两侧对称，不会把追踪带偏。"""
    perp = np.array([-d[1], d[0]])
    h, w = ink.shape
    for t in range(1, look_t + 1):
        for lat in range(0, look_lat + 1):
            for s in ((0,) if lat == 0 else (lat, -lat)):
                q = p + d * t + perp * s
                x, y = int(round(q[0])), int(round(q[1]))
                if 0 <= x < w and 0 <= y < h and ink[y, x]:
                    return q - p, True
    return None, False


def _clamp_tilt(d, max_tilt_deg):
    """把方向 d 相对竖直向下的倾角限制在 ±max_tilt_deg 内。"""
    tilt = math.degrees(math.atan2(d[0], max(d[1], 1e-9)))
    if abs(tilt) <= max_tilt_deg:
        return d
    tilt = math.copysign(max_tilt_deg, tilt)
    rad = math.radians(tilt)
    return np.array([math.sin(rad), math.cos(rad)])


def _find_landing(tops, alive, ids, seg_by_id, p, d, prm):
    """当前点附近寻找可接续的未归属段顶端：横向 ≤ tol_land 且方向一致。
    多候选时取（横向 + 3×角度差）最小者。返回 (seg, lateral, dir_diff) 或 None。"""
    dy = tops[:, 1] - p[1]
    m = (dy >= -prm["land_back"]) & (dy <= prm["land_ahead"]) & alive
    if not m.any():
        return None
    idx = np.nonzero(m)[0]
    lat = np.abs(tops[idx, 0] - p[0])
    ok = lat <= prm["tol_land"]
    if not ok.any():
        return None
    idx, lat = idx[ok], lat[ok]
    best, best_score = None, None
    for k, i in enumerate(idx):
        seg = seg_by_id[ids[i]]
        dot = float(np.clip(np.dot(d, seg["v_top"]), -1.0, 1.0))
        ang = math.degrees(math.acos(dot))
        if ang > prm["dir_tol_deg"]:
            continue
        score = lat[k] + 3.0 * ang
        if best_score is None or score < best_score:
            best, best_score = seg, score
    if best is None:
        return None
    return best


def _walk(ink, p, d, tops, alive, ids, seg_by_id, prm):
    """从 (p, d) 沿墨迹向下追踪，直到接上未归属段或线尽。
    返回 (attach_seg|None, evidence, p, d)。evidence 记录墨步/跳步与终止原因。"""
    ev = {"ink_px": 0, "jump_px": 0, "mode": "ink", "stop": "step_cap"}
    max_jump = _max_jump(d, prm)
    for _ in range(prm["step_cap"]):
        hit = _find_landing(tops, alive, ids, seg_by_id, p, d, prm)
        if hit is not None:
            ev["stop"] = "attached"
            return hit, ev, p, d
        if ev["mode"] == "ink":
            step_vec, found = _probe(ink, p, d, prm["look_t"], prm["look_lat"])
            if found:
                s_hat = step_vec / np.linalg.norm(step_vec)
                nd = d + prm["blend"] * (s_hat - d)
                nd /= np.linalg.norm(nd)
                d = _clamp_tilt(nd, prm["max_tilt_deg"])
                p = p + step_vec
                ev["ink_px"] += 1
                continue
            ev["mode"] = "jump"
            max_jump = _max_jump(d, prm)  # 跳距随当前倾角封顶（漂移 ≤ drift_max）
        if ev["jump_px"] >= max_jump:
            ev["stop"] = "gap_capped"
            return None, ev, p, d
        p = p + d
        ev["jump_px"] += 1
        _, found = _probe(ink, p, d, prm["look_t"], prm["look_lat"])
        if found:
            ev["mode"] = "ink"  # 墨迹恢复（穿过行线或断口结束）
    ev["stop"] = "step_cap"
    return None, ev, p, d


def _max_jump(d, prm):
    """死推跳距上限：min(gap_max, drift_max / tan(|倾角|))——倾角越大允许跳距越短，
    保证整段死推的横向漂移不超过 tol_land（不会漂进邻线走廊）。"""
    tilt = math.atan2(abs(d[0]), max(d[1], 1e-9))
    tan_t = max(math.tan(tilt), 1e-3)
    return int(min(prm["gap_max"], prm["drift_max"] / tan_t))


# ---------------------------------------------------------------- 归组主流程
def build_tracks(segs, ink, prm=None):
    """沿墨迹追踪归组。返回 (tracks, unassigned_ids)。
    不增删改 segs（只读）；每段至多属于一条 Track。"""
    prm = prm or PARAMS
    seg_by_id = {s["id"]: s for s in segs}
    order = sorted(segs, key=lambda s: (s["top"][1], s["top"][0]))
    ids = np.array([s["id"] for s in order])
    tops = np.array([s["top"] for s in order])
    alive = np.ones(len(order), dtype=bool)
    tracks = []
    for i0, seed in enumerate(order):
        if not alive[i0]:
            continue
        track = {"track_id": len(tracks) + 1, "segment_ids": [seed["id"]], "links": []}
        alive[i0] = False
        p = seed["bot"].astype(float).copy()
        d = seed["v_bot"].copy()
        prev = seed
        while True:
            nxt, ev, p_land, d_land = _walk(ink, p, d, tops, alive, ids, seg_by_id, prm)
            if nxt is None:
                track.setdefault("open_end", ev["stop"])
                break
            j = int(np.nonzero(ids == nxt["id"])[0][0])
            alive[j] = False
            track["links"].append({
                "from_id": prev["id"], "to_id": nxt["id"],
                "gap_y": round(float(nxt["top"][1] - prev["bot"][1]), 1),
                "land_lateral_px": round(abs(float(nxt["top"][0] - p_land[0])), 1),
                "dir_diff_deg": round(math.degrees(math.acos(
                    float(np.clip(np.dot(d_land, nxt["v_top"]), -1, 1)))), 2),
                "ink_px": ev["ink_px"], "jump_px": ev["jump_px"],
            })
            track["segment_ids"].append(nxt["id"])
            p = nxt["bot"].astype(float).copy()
            d = nxt["v_bot"].copy()
            prev = nxt
        tracks.append(track)
    unassigned = [int(ids[i]) for i in range(len(ids)) if alive[i]]
    return tracks, unassigned


# ---------------------------------------------------------------- 可视化
_HSV = [(int(h), 230, 230) for h in range(0, 180, 12)]


def draw_overlay(orig_bgr, seg_by_id, tracks, unassigned_ids):
    """Track 分色叠加原图；未归属段红色；断口跳接处以黄圈标记（只标证据，
    不画任何推断路径）。返回叠加图。"""
    viz = orig_bgr.copy()
    for ti, tr in enumerate(tracks):
        color = _hsv_bgr(_HSV[ti % len(_HSV)])
        for sid in tr["segment_ids"]:
            _poly(viz, seg_by_id[sid]["orig_points"], color, 2)
    red = (0, 0, 255)
    for sid in unassigned_ids:
        _poly(viz, seg_by_id[sid]["orig_points"], red, 1)
    for tr in tracks:
        for lk in tr["links"]:
            if lk["jump_px"] > 0:
                x, y = seg_by_id[lk["to_id"]]["top"]
                cv2.circle(viz, (int(x), int(y)), 6, (0, 255, 255), 2)
    _legend(viz, len(tracks), len(unassigned_ids))
    return viz


def _hsv_bgr(hsv):
    bgr = cv2.cvtColor(np.uint8([[list(hsv)]]), cv2.COLOR_HSV2BGR)[0, 0]
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))


def _poly(img, pts, color, thick):
    arr = np.asarray(pts, dtype=int).reshape(-1, 1, 2)
    cv2.polylines(img, [arr], False, color, thick, cv2.LINE_AA)


def _legend(img, n_tracks, n_un):
    lines = [
        f"tracks={n_tracks} color=cycled  unassigned(red)={n_un}",
        "yellow circle = gap jump (evidence only)",
    ]
    y = 30
    for t in lines:
        cv2.putText(img, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(img, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (255, 255, 255), 2, cv2.LINE_AA)
        y += 40


# ---------------------------------------------------------------- 运行入口
def process_stem(stem: str, prm=None):
    """处理单张图：输出 Track JSON + 叠加图。返回统计 dict。"""
    prm = prm or PARAMS
    json_path = paths.CANDIDATE_COORD_DIR / f"{stem}.json"
    jpg_path = paths.RAW_DIR / f"{stem}.JPG"
    segs, img_w, img_h, sha = load_segments(json_path)
    seg_by_id = {s["id"]: s for s in segs}

    gray = cv2.imread(str(jpg_path), cv2.IMREAD_GRAYSCALE)
    ink = binarize(gray, prm)
    tracks, _ = build_tracks(segs, ink, prm)

    paths.ensure_dirs(paths.TRACK_GROUP_COORD_DIR, paths.TRACK_GROUP_OVERLAY_DIR)
    n_single = sum(1 for t in tracks if len(t["segment_ids"]) == 1)
    links = [lk for t in tracks for lk in t["links"]]
    flagged = [lk for lk in links
               if lk["dir_diff_deg"] > 5.0 or lk["land_lateral_px"] > 6.0]
    out = {
        "image": stem, "source_json": str(json_path),
        "segments_frozen_sha256": sha,
        "n_input_segments": len(segs), "params": prm,
        "n_tracks": len(tracks), "n_single_segment_tracks": n_single,
        "tracks": tracks,
        "flagged_links": flagged,
    }
    with open(paths.TRACK_GROUP_COORD_DIR / f"{stem}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    orig = cv2.imread(str(jpg_path), cv2.IMREAD_COLOR)
    viz = draw_overlay(orig, seg_by_id, tracks, [])
    cv2.imwrite(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}.png"), viz,
                [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (img_w // 2, img_h // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}_预览_半分辨率.jpg"),
                half, [cv2.IMWRITE_JPEG_QUALITY, 88])

    n_jump = sum(1 for lk in links if lk["jump_px"] > 0)
    return {"stem": stem, "segments": len(segs), "tracks": len(tracks),
            "single": n_single, "multi": len(tracks) - n_single,
            "links": len(links), "jumps": n_jump, "flagged": len(flagged)}


def main():
    ap = argparse.ArgumentParser(description="碎片→物理竖线 Track 归组实验")
    ap.add_argument("--stems", nargs="*", help="图名（如 1035）；缺省随机抽 n 张")
    ap.add_argument("--n", type=int, default=3, help="随机抽取张数")
    ap.add_argument("--seed", type=int, default=20260830, help="随机种子")
    ap.add_argument("--gap-max", type=int, default=PARAMS["gap_max"])
    ap.add_argument("--tol-land", type=float, default=PARAMS["tol_land"])
    ap.add_argument("--dir-tol", type=float, default=PARAMS["dir_tol_deg"])
    args = ap.parse_args()

    prm = dict(PARAMS, gap_max=args.gap_max, tol_land=args.tol_land,
               dir_tol_deg=args.dir_tol)
    stems = args.stems
    if not stems:
        all_stems = sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
        rng = np.random.default_rng(args.seed)
        stems = sorted(rng.choice(all_stems, size=args.n, replace=False).tolist())
        print(f"[seed={args.seed}] 随机抽取 {args.n} 张: {stems}")
    for stem in stems:
        stat = process_stem(stem, prm)
        print(f"{stat['stem']}: segments={stat['segments']} tracks={stat['tracks']} "
              f"(multi={stat['multi']}, single={stat['single']}) links={stat['links']} "
              f"jumps={stat['jumps']} flagged={stat['flagged']}")


if __name__ == "__main__":
    main()
