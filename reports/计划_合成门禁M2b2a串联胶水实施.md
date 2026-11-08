# 合成门禁 M2b-2a(串联胶水:合成图接真管线)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。每任务收尾登记 `memory-bank/gate_ledger.md` 再 commit。
> 设计依据:`reports/设计_合成量化验收门禁.md` §5.2(端到端模式);调研事实:子代理笔记(2026-09-14,阶段1-6f 沙箱化细节)。
> 范围:胶水本体+单种子全链打分跑通(判定 2 的首个真管线数据点)。4 类必错图实测(判定 3)、批量与阈值冻结、6j 级恒定x陷阱 → M2b-2b。

**Goal:** 建成 `src/synth/chain.py`——把一张合成 PNG 扫描图在 **paths 沙箱**(不动真实 data/ 与 runs/)里跑过 阶段1→6f(二值化→细化→骨架→候选→track_group→track_columns→synth-finalize→6b→6c→6d→6e→6f),产出沙箱内的 `矫正映射.json`,并当场对 GT 出记分卡。

**Architecture:** 全部阶段脚本对 paths 常量是调用期属性访问(monkeypatch 可行;唯一 import 期绑定 table_line_detect.OUTPUT_DIRS 只影响 ensure_dirs,无害)。沙箱=runs/synthetic_gate/chain/<seed>/ 下镜像真实目录树;合成扫描以 **PNG 内容 + `.JPG` 文件名** 放入沙箱 raw(cv2/PIL 按内容解码,pair_jpg_json 按后缀配对,5/6 段 `{stem}.JPG` 路径精确命中)。打分只需 6f 矫正映射(lines_rect+H_rect_to_src),无需 6j。角色推导:判定 JSON 的 separators/frames 按 x_at_mid 与 GT 列几何最近匹配,构造与真实 finalize 同 schema 的 列结构定稿(不注入 GT 之外的任何管线知识,side 字段不注——真链没有)。

**Tech Stack:** Python 3.12、contextlib、pytest。无新依赖。

---

## 文件结构

| 文件 | 职责 |
| --- | --- |
| `src/core/paths.py`(改) | 登记 CHAIN_DIR = SYNTH_DIR / "chain" |
| `src/synth/chain.py`(新) | 沙箱 context、synth finalize(几何角色推导)、run_chain 编排 |
| `src/synth/run_chain.py`(新) | CLI:--seed N → 合成→全链→记分卡 |
| `tests/test_synth_chain.py`(新) | patch 往返/角色推导单测(快速);全链冒烟走 CLI 不进 pytest |

---

### Task 1: CHAIN_DIR 登记 + 沙箱 patch 上下文(TDD)

- [ ] **Step 1: paths.py 登记**

在 `VERIFIED_CONTENT_DIR` 行后:

```python
CHAIN_DIR = SYNTH_DIR / "chain"             # 合成图跑真管线的沙箱根
```

- [ ] **Step 2: 写失败测试**

```python
# tests/test_synth_chain.py
# -*- coding: utf-8 -*-
"""串联胶水:paths 沙箱 patch 往返 + 合成角色推导。"""
from src.core import paths
from src.synth.chain import sandbox_paths


def test_sandbox_paths_patch_and_restore(tmp_path):
    raw = tmp_path / "raw"
    with sandbox_paths(tmp_path) as s:
        assert paths.RAW_DIR == raw
        assert paths.BINARIZED_DIR == tmp_path / "二值处理"
        assert paths.SYNTH_GT_DIR == paths.SYNTH_DIR / "gt"   # import 期绑定的派生量不受影响
    assert paths.RAW_DIR != raw


def test_sandbox_layout_complete(tmp_path):
    with sandbox_paths(tmp_path) as s:
        assert s["stem_jpg"].name.endswith(".JPG")
```

Run: `pytest tests/test_synth_chain.py` → FAIL(ModuleNotFoundError)。

- [ ] **Step 3: 实现 chain.py 沙箱部分**

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_synth_chain.py -v` → 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/core/paths.py src/synth/chain.py tests/test_synth_chain.py
git commit -m "feat(gate): 串联胶水沙箱(paths整体重定向,往返恢复)"
```

---

### Task 2: synth 角色推导与合成 finalize(同 schema 定稿)

- [ ] **Step 1: 追加失败测试**

```python
def test_synth_finalize_maps_roles_by_geometry(tmp_path):
    """判定 separators/frames 按 x_at_mid 匹配 GT 列:内列→columns,侧框→frames。"""
    import json
   判定 = {
        "separators": [
            {"no": 1, "x_at_mid": 223.0, "y": [100, 14000], "segment_ids": [1, 2]},
            {"no": 2, "x_at_mid": 500.0, "y": [100, 14000], "segment_ids": [3]},
            {"no": 3, "x_at_mid": 700.0, "y": [100, 14000], "segment_ids": [4]},
        ],
        "frames": [{"x_at_mid": 60.0, "y": [90, 14010], "segment_ids": [9]},
                   {"x_at_mid": 3000.0, "y": [90, 14010], "segment_ids": [8]}],
        "others": [],
    }
    gt = {"lines": [
        {"line_id": "col_0", "role": "frame_side", "polyline_warp": [[60, 0], [60, 14000]]},
        {"line_id": "col_1", "role": "column", "polyline_warp": [[224, 0], [222, 14000]]},
        {"line_id": "col_2", "role": "column", "polyline_warp": [[500, 0], [500, 14000]]},
        {"line_id": "col_3", "role": "frame_side", "polyline_warp": [[3000, 0], [3000, 14000]]},
    ]}
    p = tmp_path / "判定.json"
    p.write_text(json.dumps(判定, ensure_ascii=False), encoding="utf-8")
    struct = synth_finalize(p, gt)
    assert [c["src"] for c in struct["columns"]] == [1, 2]
    assert [f["x_at_mid"] for f in struct["frames"]] == [60.0, 3000.0]
    assert struct["frames"][0]["side"] not in ("left", "right")  # 不注入真链没有的知识
```

- [ ] **Step 2: 实现 synth_finalize(chain.py 追加)**

```python
def _gt_columns(gt, role):
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
    只做角色分配(GT 列位已知,等价真实链的 FINAL dict);不注入 side 等真链没有的知识。"""
    import json
    col = json.loads(Path(judging_path).read_text(encoding="utf-8"))
    gt_cols = _gt_columns(gt, "column")
    gt_sides = _gt_columns(gt, "frame_side")

    columns, frames, unmatched = [], [], []
    for s in col.get("separators", []):
        x = s["x_at_mid"]
        cid, cx = _nearest(x, gt_cols) if gt_cols else (None, 1e18)
        sid, sx = _nearest(x, gt_sides) if gt_sides else (None, 1e18)
        if cx <= sx and cx <= match_tol:
            entry = {"index": 0, "name": None, "src": s["no"], "x_at_mid": x,
                     "y": s["y"], "segment_ids": s["segment_ids"]}
            columns.append((cid, entry))
        elif sx <= match_tol:
            frames.append({"x_at_mid": x, "y": s["y"], "segment_ids": s["segment_ids"]})
        else:
            unmatched.append(s)
    frames += [{"x_at_mid": f["x_at_mid"], "y": f["y"],
                "segment_ids": f["segment_ids"]}
               for f in col.get("frames", [])
               if abs(_nearest(f["x_at_mid"], gt_sides)[1] - f["x_at_mid"]) <= match_tol]
    columns.sort(key=lambda t: t[1]["x_at_mid"])
    struct = {
        "image": Path(judging_path).stem.replace("_列判定", ""),
        "columns": [{**e, "index": i + 1} for i, (cid, e) in enumerate(columns)],
        "frames": frames, "content": [], "others": col.get("others", []), "missing": "",
    }
    Path(out_path).write_text(json.dumps(struct, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    return struct
```

注:测试里 `frames[0]["side"] not in (...)` 用 `.get` 语义——构造时本就不写 side,断言防未来误注。

- [ ] **Step 3: 测试通过后 Commit**

```bash
git add src/synth/chain.py tests/test_synth_chain.py
git commit -m "feat(gate): 合成finalize——判定JSON按GT几何推导角色,同schema定稿"
```

---

### Task 3: run_chain 编排(阶段1→6f)+ CLI

- [ ] **Step 1: 实现 run_chain(chain.py 追加)**

每阶段优先直调 process 函数(避开 main 内可能的 run_batch 子进程——spawn 子进程不继承 patch);track_group/track_columns/6b-6f 为单张脚本,patch sys.argv 后调 main。

```python
def run_chain(seed: int, gt: dict, scan_png: Path, work_root: Path) -> dict:
    """合成图 → 阶段1→6f 全链(沙箱),返回各阶段状态与关键产物路径。"""
    import json
    import sys
    stem = f"钻孔柱状图S{seed:04d}"
    n = f"S{seed:04d}"                      # 6b-6f 的 argv 数字后缀
    with sandbox_paths(work_root) as s:
        raw = s["stem_jpg"]
        raw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(scan_png, raw)       # PNG 内容 + .JPG 名
        status = {}

        from src import binarize, thinning, skeleton, table
        paths.ensure_dirs(paths.BINARIZED_DIR, paths.THINNING_DIR,
                          paths.SKELETON_COORD_DIR, paths.SKELETON_VIZ_DIR)
        binarize.process_image(raw); status["1"] = "ok"
        thin_img = paths.BINARIZED_DIR / f"{stem}.png"
        thinning.process_image(thin_img); status["2"] = "ok"
        skeleton.process_image(thin_img); status["3"] = "ok"
        skel_json = paths.SKELETON_COORD_DIR / f"{stem}.json"
        table.table_line_detect.process_image(raw, skel_json); status["4"] = "ok"

        from src.table import track_group, track_columns
        paths.ensure_dirs(paths.TRACK_GROUP_COORD_DIR, paths.TRACK_GROUP_OVERLAY_DIR)
        sys.argv = ["track_group.py", "--stems", stem]
        track_group.main(); status["5g"] = "ok"
        sys.argv = ["track_columns.py", stem]
        track_columns.main(); status["5c"] = "ok"

        judging = paths.TRACK_GROUP_DIR / f"{stem}_列判定.json"
        struct = synth_finalize(judging, gt,
                                paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json")
        status["6a"] = f"ok cols={len(struct['columns'])} frames={len(struct['frames'])}"

        for mod_name, stage in (("bridge_gaps", "6b"), ("frame_topbottom", "6c"),
                                ("close_frame", "6d"), ("extract_table", "6f")):
            mod = getattr(__import__(f"src.table.{mod_name}", fromlist=["main"]), )
            sys.argv = [f"{mod_name}.py", n]
            mod.main()
            status[stage] = "ok"
        return {"status": status,
                "rect_map": paths.RUNS_DIR / "table_reconstruct" / f"{stem}_矫正映射.json"}
```

实现时按实际报错微调(直调函数名/参数以工作区代码为准:bridge_gaps 等 main 是否吃 argv、process 函数签名),**不得**为凑绿改真实阶段脚本。

- [ ] **Step 2: CLI run_chain.py**

```python
# -*- coding: utf-8 -*-
"""合成图全链打分 CLI:合成→阶段1→6f(沙箱)→ GT 记分卡。

用法:python src/synth/run_chain.py --seed 0
"""
import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import cv2

from src.core import paths
from src.verify.gate_config import DEFAULT_THRESHOLDS
from src.verify.score_vs_gt import render_md, score_seed
from src.verify.score_synthetic import load_pipeline_from_rect_map


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()
    from src.synth.chain import run_chain
    gt = json.loads((paths.SYNTH_GT_DIR / f"synth_{args.seed:04d}_gt.json").read_text(encoding="utf-8"))
    scan = paths.SYNTH_SCAN_DIR / f"synth_{args.seed:04d}.png"
    work = paths.CHAIN_DIR / f"synth_{args.seed:04d}"
    res = run_chain(args.seed, gt, scan, work)
    print("stages:", res["status"])
    pipeline = load_pipeline_from_rect_map(res["rect_map"])
    card = score_seed(gt, pipeline, DEFAULT_THRESHOLDS)
    out = paths.SYNTH_SCORE_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / f"synth_{args.seed:04d}_chain_score.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"synth_{args.seed:04d}_chain_score.md").write_text(render_md(card), encoding="utf-8")
    print(f"chain score: pass={card['pass']} fail_reasons={card['fail_reasons'][:6]}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 单种子全链冒烟(首个真管线数据点)**

Run: `python src/synth/run_chain.py --seed 0`
Expected: 12 阶段全 ok;记分卡落盘。**无论 pass/fail 都是首个端到端实测值**——结果(含具体指标)登记账本;fail 的违规明细就是判定 2 首次对真管线的输出。

- [ ] **Step 4: 账本登记 + Commit**

```bash
git add src/synth/chain.py src/synth/run_chain.py tests/test_synth_chain.py memory-bank/gate_ledger.md memory-bank/activeContext.md
git commit -m "feat(gate): 串联胶水跑通——合成图过阶段1→6f真管线并出首个真管线记分卡"
```

---

## Self-Review

1. **Spec 覆盖**:判定 2 的"经串联胶水对真管线打分"通路建成;判定 3 的执行条件(可重复跑 trap 图)具备。6j 级恒定x陷阱、4 类 trap 配置、批量、阈值冻结 → M2b-2b。
2. **占位符**:Task 3 Step 1 已声明"按实际报错微调直调签名,不得改真实阶段脚本"——这是实现期允许的适配自由度,不是 TBD。
3. **类型一致**:`sandbox_paths(work_root)`/`synth_finalize(judging, gt, out)`/`run_chain(seed, gt, scan, work)` 与 CLI 消费一致 ✓。
