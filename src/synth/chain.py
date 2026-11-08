# -*- coding: utf-8 -*-
"""串联胶水:合成扫描图在 paths 沙箱中跑真管线阶段1→6f。

事实依据(2026-09-14 调研):阶段1-6f 对 paths 常量均为调用期属性访问,可整体重定向;
合成扫描以 PNG 内容 + .JPG 文件名放入沙箱 raw(cv2/PIL 按内容解码,pair_jpg_json
按后缀配对,5/6 段 f"{stem}.JPG" 路径精确命中)。真实 data/ 与 runs/ 零接触。
"""
import shutil
from contextlib import contextmanager
from pathlib import Path

from src.core import paths

# (paths 属性名, 沙箱相对路径)
_SANDBOX_MAP = [
    ("RAW_DIR", "raw"),
    ("BINARIZED_DIR", "二值处理"),
    ("THINNING_DIR", "细化"),
    ("SKELETON_COORD_DIR", "骨架/坐标数据"),
    ("SKELETON_VIZ_DIR", "骨架/可视化图"),
    ("CANDIDATE_DIR", "候选"),
    ("CANDIDATE_ORIG_DIR", "候选/原图"),
    ("CANDIDATE_OVERLAY_DIR", "候选/叠加可视化图"),
    ("CANDIDATE_PURE_DIR", "候选/纯线条可视化图"),
    ("CANDIDATE_COORD_DIR", "候选/坐标数据"),
    ("CANDIDATE_STATS_DIR", "候选/特征统计"),
    ("TRACK_GROUP_DIR", "track"),
    ("TRACK_GROUP_COORD_DIR", "track/坐标数据"),
    ("TRACK_GROUP_OVERLAY_DIR", "track/叠加可视化图"),
    ("RUNS_DIR", "runs"),          # 5/6 段写 RUNS_DIR/'table_reconstruct' → 沙箱
]


@contextmanager
def sandbox_paths(work_root: Path):
    """把 paths 常量整体重定向到 work_root 沙箱,退出时恢复。SYNTH_*/派生量不受影响。"""
    work_root = Path(work_root)
    saved = {name: getattr(paths, name) for name, _ in _SANDBOX_MAP}
    mapping = {}
    try:
        for name, rel in _SANDBOX_MAP:
            tgt = work_root / rel
            mapping[name] = tgt
            setattr(paths, name, tgt)
        yield {"stem_jpg": work_root / "raw" / "scan.JPG", "dirs": mapping}
    finally:
        for name, val in saved.items():
            setattr(paths, name, val)


def _gt_mids(gt, role):
    """GT 指定角色各线的 x 中位(弯曲系)。"""
    out = []
    for ln in gt["lines"]:
        if ln["role"] != role:
            continue
        xs = [p[0] for p in ln["polyline_warp"]]
        out.append((ln["line_id"], sum(xs) / len(xs)))
    return out


def _nearest(x, cands):
    return min(cands, key=lambda t: abs(t[1] - x))


def synth_finalize(judging_path, gt, out_path, match_tol=40.0):
    """合成版 finalize:判定 separators/frames 按 x_at_mid 匹配 GT 几何角色,
    构造与真实 finalize_columns 同 schema 的 列结构定稿.json。

    只做角色分配(GT 列位已知,等价真实链的 FINAL dict);不注入 side 等真链没有的知识。
    """
    import json
    col = json.loads(Path(judging_path).read_text(encoding="utf-8"))
    gt_cols = _gt_mids(gt, "column")
    gt_sides = _gt_mids(gt, "frame_side")

    columns, frames = [], []
    for s in col.get("separators", []):
        x = s["x_at_mid"]
        cid, cmid = _nearest(x, gt_cols) if gt_cols else (None, x + 1e18)
        sid, smid = _nearest(x, gt_sides) if gt_sides else (None, x + 1e18)
        dc, ds = abs(cmid - x), abs(smid - x)
        if dc <= ds and dc <= match_tol:
            columns.append({"src": s["no"], "x_at_mid": x, "y": s["y"],
                            "segment_ids": s["segment_ids"]})
        elif ds <= match_tol:
            frames.append({"x_at_mid": x, "y": s["y"],
                           "segment_ids": s["segment_ids"]})
    for f in col.get("frames", []):
        if gt_sides and abs(_nearest(f["x_at_mid"], gt_sides)[1] - f["x_at_mid"]) <= match_tol:
            frames.append({"x_at_mid": f["x_at_mid"], "y": f["y"],
                           "segment_ids": f["segment_ids"]})
    columns.sort(key=lambda c: c["x_at_mid"])
    # side 按位置派生(镜像已核验基线语义:真实定稿 frames 带 side=left/right;
    # 现行工作区 6a 丢失了该字段,属已登记漂移)。框线在全部列线外侧者得 side。
    col_xs = [c["x_at_mid"] for c in columns]
    if col_xs:
        for f in frames:
            if f["x_at_mid"] < min(col_xs):
                f["side"] = "left"
            elif f["x_at_mid"] > max(col_xs):
                f["side"] = "right"
    struct = {
        "image": Path(judging_path).stem.replace("_列判定", ""),
        "columns": [{**c, "index": i + 1, "name": None} for i, c in enumerate(columns)],
        "frames": frames, "content": [], "others": col.get("others", []), "missing": "",
    }
    Path(out_path).write_text(json.dumps(struct, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    return struct


def run_chain(seed: int, gt: dict, scan_png: Path, work_root: Path) -> dict:
    """合成图 → 阶段1→6f 全链(paths 沙箱),返回各阶段状态与矫正映射路径。

    阶段1 绕开 main(run_batch 走 spawn 子进程,不继承 paths patch),直调 process;
    其余阶段均为单进程单张脚本,patch sys.argv 后调 main。
    """
    import sys

    stem = f"钻孔柱状图S{seed:04d}"
    n = f"S{seed:04d}"                      # 6b-6f 的 argv 数字后缀
    work_root = Path(work_root)
    if work_root.exists():                  # 全新链语义:清掉上轮产物,杜绝陈旧文件混入
        shutil.rmtree(work_root)
    # 阶段脚本存在 import 期 paths 绑定(如 table_line_detect.OUTPUT_DIRS):
    # 同进程第二次跑链会把产物写进上一沙箱。清模块缓存,让 with 块内 import 在
    # 当前沙箱下重新执行模块顶层。
    import sys as _sys
    for mod_name in [m for m in _sys.modules
                     if m == "src.table" or m.startswith(("src.table.", "src.binarize.",
                                                          "src.thinning.", "src.skeleton."))]:
        del _sys.modules[mod_name]
    # 注意:仅删 sys.modules 不够——`from src.table import X` 经包属性短路返回旧模块,
    # 必须连父包(src.table 等)一起删,强制包与子模块在当前沙箱下整体重导入。
    with sandbox_paths(work_root) as s:
        raw = work_root / "raw" / f"{stem}.JPG"   # PNG 内容 + .JPG 名,下游按 stem 找文件
        raw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(scan_png, raw)
        status = {}

        from src.table import (bridge_gaps, close_frame, extract_table,
                               frame_topbottom, table_line_detect, track_columns,
                               track_group)
        from src.binarize import multi_scale_sauvola
        from src.skeleton import trace_skeleton_batch
        from src.thinning import thin_zhangsuen

        paths.ensure_dirs(paths.BINARIZED_DIR, paths.THINNING_DIR,
                          paths.SKELETON_COORD_DIR, paths.SKELETON_VIZ_DIR,
                          paths.TRACK_GROUP_COORD_DIR, paths.TRACK_GROUP_OVERLAY_DIR,
                          paths.RUNS_DIR / "table_reconstruct")

        def _must(ret, stage):
            """阶段脚本约定 (name, ok, info);失败时 info 是异常串——吞掉=静默跳过,
            必须转成阶段崩溃进记分卡。"""
            _, ok, info = ret
            if not ok:
                raise RuntimeError(f"{info}")
            status[stage] = "ok"

        try:
            _must(multi_scale_sauvola.process(raw), "1")
            _must(thin_zhangsuen.process_image(paths.BINARIZED_DIR / f"{stem}.png"), "2")
            # 真实阶段3读 THINNING_DIR(细化图),不是二值图
            _must(trace_skeleton_batch.process_image(paths.THINNING_DIR / f"{stem}.png"), "3")
            _must(table_line_detect.process_image(
                raw, paths.SKELETON_COORD_DIR / f"{stem}.json"), "4")

            sys.argv = ["track_group.py", "--stems", stem]
            track_group.main()
            status["5g"] = "ok"
            # --source track_group:与已核验真实基线同配置(实测 1015 两条 source,
            # track_group span 17047-17517 与判定 JSON 一致;cluster 的 to_groups
            # 坐标换位缺失,真图上 span 也塌到 ≤75px,登记 gate_ledger 待判定5 修)
            sys.argv = ["track_columns.py", stem, "--source", "track_group"]
            track_columns.main()
            status["5t"] = "ok"

            judging = paths.TRACK_GROUP_DIR / f"{stem}_列判定.json"
            struct = synth_finalize(
                judging, gt,
                paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json")
            status["6a"] = f"ok cols={len(struct['columns'])} frames={len(struct['frames'])}"

            # 反放水:管线阶段崩溃 = 记分卡 FAIL 的一种(登记阶段与异常),不是炸链
            for mod_name, stage in (("bridge_gaps", "6b"), ("frame_topbottom", "6c"),
                                    ("close_frame", "6d"), ("extract_table", "6f")):
                mod = __import__(f"src.table.{mod_name}", fromlist=["main"])
                sys.argv = [f"{mod_name}.py", n]
                mod.main()
                status[stage] = "ok"
        except Exception as exc:  # noqa: BLE001
            crashed = next((s for s in ("1", "2", "3", "4", "5g", "5t", "6a",
                                        "6b", "6c", "6d", "6f")
                            if s not in status), "?")
            status[crashed] = f"CRASH {type(exc).__name__}: {exc}"
        rect_map = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_矫正映射.json"
        return {"status": status, "stem": stem,
                "rect_map": rect_map if rect_map.exists() else None}
