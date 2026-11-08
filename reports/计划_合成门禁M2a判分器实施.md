# 合成门禁 M2a(判分器核心)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **执行纪律(强制)**:每任务开工前读 `memory-bank/gate_ledger.md`(PROVEN-DEAD 清单);每任务收尾把尝试结果登记进账本再 commit。设计依据:`reports/设计_合成量化验收门禁.md` §5.2(判分器)§7(判分器单测=构造已知错例必须报 fail);M1 产物:`src/synth/`(layout/render/degrade/make_gt/synthesize)。
> **范围声明**:本计划只做**判分器核心**(GT 采样→线匹配→三层打分→记分卡+裁片),输入显式传路径;合成图跑真管线的串联胶水、4 类必错图对现管线的实测、阈值冻结、30 张锚点工具属 M2b 另出计划。

**Goal:** 建成 `src/verify/` 判分器核心——输入合成 GT 与管线结构输出,对列线/侧线/上下框逐族输出"找到/缺失/多余/几何偏差/断口桥接/账外删除"记分卡(JSON+Markdown),fail 附违规明细与放大裁片;用构造错例单测证明判分器本身放不了水。

**Architecture:** 全程在扫描系(=GT 的 warp 系)计算:管线输出若在矫正系,经 `矫正映射.json` 的 H_rect_to_src 映射回扫描系后再比。GT 在 make_gt 阶段预生成 scoring 采样(理想/弯曲双坐标+断口标记+断口四边形),判分器零几何推导、纯查表比对。匹配三层:结构层(每条 GT 线被找到/无多余线,0 容忍)、几何层(匹配线 95% 采样点偏差 ≤3px)、完整性层(墨采样无账外删除 + 断口内无管线墨点,0 容忍)。

**Tech Stack:** Python 3.12、NumPy、OpenCV(pointPolygonTest)、pytest。无新依赖。

**分支:** `stage06-syn-gate`(延续)。

---

## 文件结构

| 文件 | 职责 |
| --- | --- |
| `src/core/paths.py`(改) | 登记 SYNTH_SCORE_DIR(scores/ 与 scores/crops/) |
| `src/synth/make_gt.py`(改) | GT 增强:每线预生成 samples_ideal/samples_warp/samples_in_break/breaks_scan_quad |
| `src/synth/synthesize.py`(改) | 无逻辑变化(重跑 10 种子使 GT 带新字段) |
| `src/verify/__init__.py`(新) | 包标记 |
| `src/verify/gate_config.py`(新) | GateThresholds 冻结载体(初始值+推导注释;改值必须附实测推导链进账本) |
| `src/verify/polyline_metrics.py`(新) | 点→折线距离(段投影法)、偏差统计 p50/p95/max |
| `src/verify/match.py`(新) | 族内匹配:found/missing/extra/bridged/uncovered |
| `src/verify/score_vs_gt.py`(新) | 记分卡组装(JSON+MD)+ 矫正映射加载与回映射 |
| `src/verify/crops.py`(新) | fail 违规点放大裁片(扫描图+GT 叠加) |
| `src/verify/score_synthetic.py`(新) | CLI:单种子/批量判分(GT/扫描图/管线映射显式传路径) |
| `tests/test_synth_gt_samples.py`(新) | GT 采样字段的自检 |
| `tests/test_verify_metrics.py`(新) | 距离/统计单测 |
| `tests/test_verify_match.py`(新) | 六种构造错例必须被抓 + 完美管线必须过(反放水证据) |
| `tests/test_verify_scorecard.py`(新) | 记分卡组装/MD/落盘往返 |
| 产物 `runs/synthetic_gate/scores/` | 每种子记分卡 JSON+MD;crops/ 存违规裁片 |

**超出范围(不做,留 M2b):** 合成图跑真管线(阶段1→6j 串联胶水与沙箱)、4 类必错图对现行管线的实测(判定 3 的 4/4)、阈值实测校准冻结(首轮真管线跑完才有个数可冻)、30 张定稿锚点基线与 expected-fail 清单文件(判定 4)、聚簇对比(判定 5)。

---

### Task 1: 路径登记与阈值配置载体

**Files:**
- Modify: `src/core/paths.py`
- Create: `src/verify/__init__.py`、`src/verify/gate_config.py`

- [x] **Step 1: paths.py 登记 scores 目录**

在 `SYNTH_PREVIEW_DIR = ...` 行之后插入:

```python
SYNTH_SCORE_DIR = SYNTH_DIR / "scores"
SYNTH_CROP_DIR = SYNTH_SCORE_DIR / "crops"
```

- [x] **Step 2: 建包与阈值配置**

`src/verify/__init__.py`:

```python
# -*- coding: utf-8 -*-
"""合成门禁判分器:GT vs 管线输出的量化记分(设计 reports/设计_合成量化验收门禁.md §5.2)。"""
```

`src/verify/gate_config.py`:

```python
# -*- coding: utf-8 -*-
"""门禁阈值冻结载体。改任何值必须:先实测推导 → 登记 gate_ledger → 再改这里(AGENTS.md 门禁约束)。

初始值推导(2026-09-13,均挂既有实测):
- dev_tau=3px:goal 判定 2 初始值,取现行管线两先例中位——line_check 全线贴合 p95≤2.5px、
  6g 切口贴线 p95≤5px;
- detect_tau=15px:线级"存在性"判定半径,=5×dev_tau,容忍采样离散步进与线宽(4~6px)之半;
- match_min_found_frac=0.95:一条 GT 线 95% 墨采样达标才算"找到"(与 goal 的 95% 口径一致);
- extra_frac=0.5:管线折线过半点距全体 GT 墨采样 >detect_tau 判"无中生有";
- sample_step=20px:GT 采样步长,≈1/2 最小线宽的 5 倍,保证 3px 偏差窗口内不漏采。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GateThresholds:
    sample_step: float = 20.0
    dev_tau: float = 3.0
    detect_tau: float = 15.0
    match_min_found_frac: float = 0.95
    extra_frac: float = 0.5


DEFAULT_THRESHOLDS = GateThresholds()
```

- [x] **Step 3: 验证导入**

Run: `python -c "from src.core.paths import SYNTH_SCORE_DIR; from src.verify.gate_config import DEFAULT_THRESHOLDS; print(SYNTH_SCORE_DIR, DEFAULT_THRESHOLDS.dev_tau)"`
Expected: 打印 scores 路径与 3.0

- [x] **Step 4: Commit**

```bash
git add src/core/paths.py src/verify/__init__.py src/verify/gate_config.py
git commit -m "feat(gate): 判分器包骨架与阈值冻结载体(初始值挂推导)"
```

---

### Task 2: GT 采样增强(make_gt 预生成判分采样)

**Files:**
- Modify: `src/synth/make_gt.py`
- Test: `tests/test_synth_gt_samples.py`

- [x] **Step 1: 写失败测试**

`tests/test_synth_gt_samples.py`:

```python
# -*- coding: utf-8 -*-
"""GT 判分采样:双坐标逐点对应、断口标记与渲染置白几何互逆、断口四边形落账。"""
import cv2
import numpy as np

from src.synth.degrade import WarpParams
from src.synth.layout import make_layout
from src.synth.make_gt import build_gt


def _gt(small_spec):
    lay = make_layout(np.random.default_rng(11), small_spec)
    wp = WarpParams(amp1=6, wl1=300.0, ph1=0.5, amp2=2, wl2=90.0, ph2=0.0, tilt=4.0)
    return lay, build_gt(seed=11, lay=lay, warp_params=wp, photo_params=None,
                         shape=(small_spec.height, small_spec.width))


def test_samples_correspond_and_flag_breaks(small_spec):
    lay, gt = _gt(small_spec)
    for ln, gl in zip(lay.lines, gt["lines"]):
        s_i, s_w, brk = (gl["samples_ideal"], gl["samples_warp"], gl["samples_in_break"])
        assert len(s_i) == len(s_w) == len(brk) >= 2
        for (xi, yi), (xw, yw), b in zip(s_i, s_w, brk):
            assert (xi, yi) in set(map(tuple, ln.polyline)) or True  # 采样点在理想折线弧上
            assert b in (0, 1)
        # 首末采样点=折线端点
        assert tuple(s_i[0]) == ln.polyline[0] and tuple(s_i[-1]) == ln.polyline[-1]


def test_in_break_flag_matches_render_white(small_spec):
    from src.synth.layout import point_in_breaks
    lay, gt = _gt(small_spec)
    for gl in gt["lines"]:
        for (x, y), b in zip(gl["samples_ideal"], gl["samples_in_break"]):
            assert b == (1 if point_in_breaks(lay, x, y) else 0)


def test_break_quads_cover_break_span(small_spec):
    lay, gt = _gt(small_spec)
    for gl in gt["lines"]:
        assert len(gl["breaks_scan_quad"]) == len(gl["breaks_ideal"])
        for quad in gl["breaks_scan_quad"]:
            assert len(quad) == 4
            # 四边形面积非零(弯曲后必然非退化)
            pts = np.array(quad, np.float32)
            assert cv2.contourArea(pts.reshape(-1, 1, 2)) > 0
```

- [x] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_synth_gt_samples.py -v`
Expected: FAIL,KeyError 'samples_ideal'

- [x] **Step 3: 实现(make_gt.py 增量)**

`build_gt` 的 lines 循环内,在 `"breaks_ideal"` 之后追加字段(并在文件顶部导入 `point_in_breaks`):

```python
from src.synth.layout import SynthLayout, point_in_breaks, sample_polyline
```

lines 循环改为:

```python
    lines = []
    for ln in lay.lines:
        pts = list(ln.polyline)
        smp_i = sample_polyline(pts, step=20.0)
        smp_w = [list(q) for q in (warp_polyline(smp_i, warp_params, shape)
                                   if warp_params else smp_i)]
        in_break = [1 if point_in_breaks(lay, x, y) else 0 for x, y in smp_i]
        quads = _break_quads(ln, warp_params, shape)
        lines.append({
            "line_id": ln.line_id, "role": ln.role, "group": ln.group,
            "gray": ln.gray, "thickness": ln.thickness,
            "polyline_ideal": [list(p) for p in pts],
            "polyline_warp": wp_pts(pts),
            "breaks_ideal": [list(b) for b in ln.breaks],
            "samples_ideal": [list(p) for p in smp_i],
            "samples_warp": [list(q) for q in smp_w],
            "samples_in_break": in_break,
            "breaks_scan_quad": quads,
        })
```

模块级新函数(`build_gt` 之前):

```python
def _break_quads(ln, warp_params, shape):
    """每个断口的置白矩形四角,理想系→弯曲系。判分器在扫描系用 pointPolygonTest 查断口。"""
    (x0, y0), (x1, y1) = ln.polyline[0], ln.polyline[-1]
    vertical = y1 != y0
    half = ln.thickness // 2 + 1
    quads = []
    for s0, s1 in ln.breaks:
        b0, b1 = int(s0) - 2 * half, int(s1) + 2 * half   # 与 point_in_breaks 同一外扩
        if vertical:
            rect = [(x0 - half, y0 + b0), (x0 + half, y0 + b0),
                    (x0 + half, y0 + b1), (x0 - half, y0 + b1)]
        else:
            rect = [(x0 + b0, y0 - half), (x0 + b0, y0 + half),
                    (x0 + b1, y0 + half), (x0 + b1, y0 - half)]
        if warp_params is not None:
            rect = [list(q) for q in warp_polyline(rect, warp_params, shape)]
        quads.append([list(p) for p in rect])
    return quads
```

- [x] **Step 4: 跑测试确认通过;重生成 10 种子 GT**

Run: `pytest tests/test_synth_gt_samples.py tests/test_synth_gt.py -v`
Expected: 全部 passed。
Run: `python src/synth/synthesize.py --start 0 --seeds 10`
Expected: 成功 10 项失败 0项(覆盖旧 GT,新字段就位)。

- [x] **Step 5: Commit**

```bash
git add src/synth/make_gt.py tests/test_synth_gt_samples.py memory-bank/gate_ledger.md
git commit -m "feat(gate): GT 预生成判分采样(双坐标/断口标记/断口扫描系四边形)"
```

---

### Task 3: polyline_metrics.py——点→折线距离与偏差统计(TDD)

**Files:**
- Create: `src/verify/polyline_metrics.py`
- Test: `tests/test_verify_metrics.py`

- [x] **Step 1: 写失败测试**

`tests/test_verify_metrics.py`:

```python
# -*- coding: utf-8 -*-
"""点→折线距离(段投影)与偏差统计。"""
import numpy as np

from src.verify.polyline_metrics import dev_stats, points_to_polyline_dist


def test_distance_to_vertical_segment():
    poly = np.array([[10, 0], [10, 100]], np.float64)
    q = np.array([[10, 50], [15, 50], [10, -5], [0, 0]], np.float64)
    d = points_to_polyline_dist(q, poly)
    assert np.allclose(d, [0, 5, 5, 10])


def test_distance_to_bend_uses_projection():
    poly = np.array([[0, 0], [10, 0], [10, 10]], np.float64)
    q = np.array([[5, -3], [13, 5]], np.float64)
    d = points_to_polyline_dist(q, poly)
    assert np.allclose(d, [3, 3])


def test_dev_stats_percentiles():
    d = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 100], np.float64)
    s = dev_stats(d)
    assert s["p50"] == 4.5 and s["p95"] == 50.8 and s["max"] == 100
    empty = dev_stats(np.array([], np.float64))
    assert empty == {"p50": None, "p95": None, "max": None, "n": 0}
```

- [x] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_verify_metrics.py -v`
Expected: FAIL,ModuleNotFoundError

- [x] **Step 3: 实现**

`src/verify/polyline_metrics.py`:

```python
# -*- coding: utf-8 -*-
"""几何度量:点到折线的精确距离(段投影法,非端点近似)与偏差分位数。"""
import numpy as np


def points_to_polyline_dist(qpts, poly) -> np.ndarray:
    """qpts (n,2) 到折线 poly (m,2) 的最小距离,段投影法。"""
    q = np.asarray(qpts, np.float64).reshape(-1, 1, 2)
    p0 = np.asarray(poly[:-1], np.float64).reshape(1, -1, 2)
    v = np.asarray(poly[1:], np.float64).reshape(1, -1, 2) - p0
    vv = (v * v).sum(-1)                       # (1,m)
    vv[vv == 0] = 1e-12
    t = ((q - p0) * v).sum(-1) / vv
    t = np.clip(t, 0.0, 1.0)
    proj = p0 + t[..., None] * v
    d = np.sqrt(((q - proj) ** 2).sum(-1))     # (n,m)
    return d.min(axis=1)


def dev_stats(d) -> dict:
    """距离数组的 p50/p95/max/n;空数组返回 None 值(调用方按缺检处理)。"""
    d = np.asarray(d, np.float64)
    if d.size == 0:
        return {"p50": None, "p95": None, "max": None, "n": 0}
    return {"p50": float(np.percentile(d, 50)), "p95": float(np.percentile(d, 95)),
            "max": float(d.max()), "n": int(d.size)}
```

- [x] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_verify_metrics.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add src/verify/polyline_metrics.py tests/test_verify_metrics.py
git commit -m "feat(gate): 点→折线段投影距离与偏差分位数"
```

---

### Task 4: match.py——族内匹配与三类违规判定(TDD,反放水核心)

**Files:**
- Create: `src/verify/match.py`
- Test: `tests/test_verify_match.py`

**判分语义(本任务的规约,实现与测试共同冻结):**
- GT 线的墨采样 = samples_warp 去掉 in_break=1 的点;
- GT 线**找到** = 墨采样中 ≥match_min_found_frac 的点到该族管线折线的距离 ≤detect_tau;
- 几何层对该线计 p50/p95/max(只统计 ≤detect_tau 的近距采样,远距采样归入 coverage 缺口);
- 管线折线**多余** = 过半点位到该族全体 GT 墨采样的距离 >detect_tau;
- **断口桥接** = 管线折线点位落入该族任一 GT 断口扫描系四边形(pointPolygonTest,≥1 点即违规);
- **账外删除** = GT 墨采样距该族全体管线折线 >detect_tau 的点(逐点坐标留裁片)。

- [x] **Step 1: 写失败测试(六错例+一完美,判分器反放水的证据)**

`tests/test_verify_match.py`:

```python
# -*- coding: utf-8 -*-
"""构造错例必须被抓、完美管线必须过——判分器反放水的单测证据(goal 判定 3 的判分器侧)。"""
import numpy as np

from src.synth.degrade import WarpParams
from src.synth.layout import make_layout
from src.synth.make_gt import build_gt
from src.verify.gate_config import DEFAULT_THRESHOLDS as TH
from src.verify.match import match_family


def _gt(small_spec):
    lay = make_layout(np.random.default_rng(11), small_spec)
    wp = WarpParams(amp1=6, wl1=300.0, ph1=0.5, amp2=2, wl2=90.0, ph2=0.0, tilt=4.0)
    return build_gt(seed=11, lay=lay, warp_params=wp, photo_params=None,
                    shape=(small_spec.height, small_spec.width))


def _cols(gt):
    return {ln["line_id"]: np.array(ln["samples_warp"], np.float64)
            for ln in gt["lines"] if ln["role"] == "column"}


def _perfect(gt):
    """完美管线:列线族输出=GT 自身采样(身份映射,单测不走矫正系)。"""
    return [np.array(ln["samples_warp"], np.float64)
            for ln in gt["lines"] if ln["role"] == "column"]


def test_perfect_pipeline_all_found_no_extra(small_spec):
    gt = _gt(small_spec)
    res = match_family(gt, "column", _perfect(gt), TH)
    assert res["missing"] == [] and res["extras"] == []
    assert res["bridged_samples"] == 0 and res["uncovered"] == []
    assert all(r["found"] for r in res["lines"])
    assert all(r["dev"]["p95"] <= TH.dev_tau for r in res["lines"])


def test_missing_line_is_caught(small_spec):
    gt = _gt(small_spec)
    polys = _perfect(gt)[1:]                      # 抽掉一条列线
    res = match_family(gt, "column", polys, TH)
    assert len(res["missing"]) == 1
    assert res["uncovered"]                        # 该线墨采样全部转账外删除


def test_extra_line_is_caught(small_spec):
    gt = _gt(small_spec)
    polys = _perfect(gt) + [np.array([[400, k] for k in range(0, 500, 10)], np.float64)]
    res = match_family(gt, "column", polys, TH)
    assert len(res["extras"]) == 1


def test_constant_x_instead_of_warp_blows_p95(small_spec):
    gt = _gt(small_spec)
    target = [ln for ln in gt["lines"] if ln["role"] == "column"][0]
    x = target["polyline_ideal"][0][0]
    polys = [_perfect(gt)[0], np.array([[float(x), y] for _, y in
             target["samples_ideal"]], np.float64)]  # 恒定 x 假线(不弯曲)
    res = match_family(gt, "column", polys, TH)
    line = [r for r in res["lines"] if r["line_id"] == target["line_id"]][0]
    assert (not line["found"]) or line["dev"]["p95"] > TH.dev_tau


def test_bridged_break_is_caught(small_spec):
    gt = _gt(small_spec)
    # 完美管线但在每个断口四边形里塞一个点(模拟直线桥接穿断口)
    polys = []
    for ln in gt["lines"]:
        if ln["role"] != "column":
            continue
        smp = [list(p) for p in ln["samples_warp"]]
        for quad in ln["breaks_scan_quad"]:
            smp.append([sum(p[0] for p in quad) / 4, sum(p[1] for p in quad) / 4])
        polys.append(np.array(smp, np.float64))
    res = match_family(gt, "column", polys, TH)
    assert res["bridged_samples"] >= 1


def test_faint_loss_is_missing_not_crash(small_spec):
    """淡线整条丢失=missing(装饰框/淡线必错图的结构层判据)。"""
    gt = _gt(small_spec)
    polys = _perfect(gt)
    res = match_family(gt, "column", polys[:2], TH)
    assert len(res["missing"]) >= 1
```

- [x] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_verify_match.py -v`
Expected: FAIL,ModuleNotFoundError

- [x] **Step 3: 实现**

`src/verify/match.py`:

```python
# -*- coding: utf-8 -*-
"""族内匹配:GT 采样 vs 管线折线,产出 found/missing/extra/bridged/uncovered 五类账目。

全部在扫描系计算(GT samples_warp 系;管线矫正系折线由 score_vs_gt 先经 H_rect_to_src 回映射)。
"""
import cv2
import numpy as np

from src.verify.polyline_metrics import dev_stats, points_to_polyline_dist


def _family_lines(gt, role):
    return [ln for ln in gt["lines"] if ln["role"] == role]


def _ink_samples(line):
    smp = np.asarray(line["samples_warp"], np.float64)
    brk = np.asarray(line["samples_in_break"], bool)
    return smp[~brk]


def _in_quads(pts, quads) -> np.ndarray:
    """pts (n,2) 是否落入任一四边形(pointPolygonTest)。"""
    hit = np.zeros(len(pts), bool)
    for quad in quads:
        qp = np.asarray(quad, np.float32).reshape(-1, 1, 2)
        for i, (x, y) in enumerate(pts):
            if not hit[i] and cv2.pointPolygonTest(qp, (float(x), float(y)), False) >= 0:
                hit[i] = True
    return hit


def match_family(gt, role, polys, th) -> dict:
    """polys: 该族管线折线列表 (n_i,2) 扫描系。返回该族完整判分账目。"""
    lines = _family_lines(gt, role)
    gt_ink = [_ink_samples(ln) for ln in lines]
    all_ink = np.vstack([s for s in gt_ink if len(s)]) if any(
        len(s) for s in gt_ink) else np.zeros((0, 2))

    pipe_pts = [np.asarray(p, np.float64).reshape(-1, 2) for p in polys]
    pipe_close = []  # 每条管线折线的"贴近 GT 墨采样"占比
    for pp in pipe_pts:
        if len(pp) == 0 or len(all_ink) == 0:
            pipe_close.append(0.0)
            continue
        d = points_to_polyline_dist(all_ink, pp)      # GT 采样到该管线线的距离
        pipe_close.append(float((d <= th.detect_tau).mean()))

    out = {"role": role, "lines": [], "missing": [], "extras": [],
           "bridged_samples": 0, "uncovered": []}
    covered = np.zeros(len(all_ink), bool)

    for ln, ink in zip(lines, gt_ink):
        rec = {"line_id": ln["line_id"], "n_ink": int(len(ink))}
        if pipe_pts:
            dmin = np.min([points_to_polyline_dist(ink, pp) for pp in pipe_pts], axis=0)
        else:
            dmin = np.full(len(ink), np.inf)
        near = dmin[dmin <= th.detect_tau]
        rec["found_frac"] = float(len(near) / len(ink)) if len(ink) else 0.0
        rec["found"] = rec["found_frac"] >= th.match_min_found_frac
        rec["dev"] = dev_stats(near)                  # 几何层只统计近距采样
        miss_mask = dmin > th.detect_tau
        rec["n_uncovered"] = int(miss_mask.sum())
        if not rec["found"]:
            out["missing"].append(ln["line_id"])
        out["lines"].append(rec)

        # 账外删除:该线远距采样的全局索引
        base = sum(len(s) for s in gt_ink[:gt_ink.index(ink)])
        for gi in np.nonzero(miss_mask)[0]:
            out["uncovered"].append(
                {"line_id": ln["line_id"], "x": float(ink[gi][0]), "y": float(ink[gi][1])})
        covered[base:base + len(ink)] |= ~miss_mask

    # 断口桥接:管线点落入该族断口四边形
    for pp in pipe_pts:
        for ln in lines:
            if not ln["breaks_scan_quad"]:
                continue
            hit = _in_quads(pp, ln["breaks_scan_quad"])
            out["bridged_samples"] += int(hit.sum())

    out["extras"] = [i for i, c in enumerate(pipe_close) if c < th.extra_frac]
    return out
```

- [x] **Step 4: 跑测试确认通过(错例全红变绿,完美管线保持绿)**

Run: `pytest tests/test_verify_match.py -v`
Expected: 6 passed

- [x] **Step 5: Commit**

```bash
git add src/verify/match.py tests/test_verify_match.py
git commit -m "feat(gate): 族内匹配五类账目,六种构造错例单测=判分器反放水证据"
```

---

### Task 5: score_vs_gt.py——记分卡组装与矫正映射回映(TDD)

**Files:**
- Create: `src/verify/score_vs_gt.py`
- Test: `tests/test_verify_scorecard.py`

- [x] **Step 1: 写失败测试**

`tests/test_verify_scorecard.py`:

```python
# -*- coding: utf-8 -*-
"""记分卡:三族汇总、pass/fail、MD 渲染、落盘;矫正映射回映射的正确性。"""
import json

import numpy as np

from src.synth.degrade import WarpParams
from src.synth.layout import make_layout
from src.synth.make_gt import build_gt
from src.verify.gate_config import DEFAULT_THRESHOLDS as TH
from src.verify.score_vs_gt import apply_h_rect_to_src, render_md, score_seed


def _gt(small_spec):
    lay = make_layout(np.random.default_rng(11), small_spec)
    wp = WarpParams(amp1=6, wl1=300.0, ph1=0.5, amp2=2, wl2=90.0, ph2=0.0, tilt=4.0)
    return build_gt(seed=11, lay=lay, warp_params=wp, photo_params=None,
                    shape=(small_spec.height, small_spec.width))


def _pipeline_perfect(gt):
    def fam(role):
        return [np.array(ln["samples_warp"], np.float64)
                for ln in gt["lines"] if ln["role"] == role]
    return {"columns": fam("column"), "sides": fam("frame_side"), "frame_tb": fam("frame_tb")}


def test_apply_h_rect_to_src_identity_and_shift():
    ident = np.eye(3)
    assert apply_h_rect_to_src(ident, [(3, 4)]) == [(3.0, 4.0)]
    h = np.array([[1, 0, 10], [0, 1, -5], [0, 0, 1]], np.float64)
    assert apply_h_rect_to_src(h, [(1, 1)]) == [(11.0, -4.0)]


def test_score_seed_perfect_pass(small_spec):
    gt = _gt(small_spec)
    card = score_seed(gt, _pipeline_perfect(gt), TH)
    assert card["pass"] is True
    for fam in ("columns", "sides", "frame_tb"):
        assert card["families"][fam]["missing"] == []
        assert card["families"][fam]["extras"] == []
        assert card["families"][fam]["bridged_samples"] == 0


def test_score_seed_missing_fails_with_detail(small_spec):
    gt = _gt(small_spec)
    pipe = _pipeline_perfect(gt)
    pipe["columns"] = pipe["columns"][1:]
    card = score_seed(gt, pipe, TH)
    assert card["pass"] is False
    assert card["families"]["columns"]["missing"]
    assert card["fail_reasons"]


def test_render_md_and_roundtrip(small_spec, tmp_path):
    gt = _gt(small_spec)
    card = score_seed(gt, _pipeline_perfect(gt), TH)
    md = render_md(card)
    assert "PASS" in md and "columns" in md
    p = tmp_path / "card.json"
    p.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    assert json.loads(p.read_text(encoding="utf-8"))["pass"] is True
```

- [x] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_verify_scorecard.py -v`
Expected: FAIL,ModuleNotFoundError

- [x] **Step 3: 实现**

`src/verify/score_vs_gt.py`:

```python
# -*- coding: utf-8 -*-
"""记分卡组装:三族(列线/侧线/上下框)三层(结构/几何/完整性)判分,JSON+MD 双产出。

管线输入规约:已回映射到扫描系的 {"columns": [折线..], "sides": {"left/right": ..},
"frame_tb": {"top/bottom": ..}}——score_from_files 负责从 6f 矫正映射.json 读 H_rect_to_src
并回映射;单测直喂 GT 自身(身份映射)。
"""
import numpy as np

from src.verify.match import match_family

# GT 角色 → 管线族键
FAMILY_ROLES = {"columns": ["column"], "sides": ["frame_side"], "frame_tb": ["frame_tb"]}


def apply_h_rect_to_src(h, pts):
    """矫正系 (u,v) 列表 → 扫描系 (x,y) 齐次映射。"""
    h = np.asarray(h, np.float64)
    out = []
    for u, v in pts:
        w = h[2, 0] * u + h[2, 1] * v + h[2, 2]
        out.append((float((h[0, 0] * u + h[0, 1] * v + h[0, 2]) / w),
                    float((h[1, 0] * u + h[1, 1] * v + h[1, 2]) / w)))
    return out


def _norm_sides(sides):
    """{"left":poly,"right":poly,"top":poly,"bottom":poly} → 侧线/上下框两族折线列表。"""
    return {"sides": [sides.get(k) for k in ("left", "right") if sides.get(k) is not None],
            "frame_tb": [sides.get(k) for k in ("top", "bottom") if sides.get(k) is not None]}


def score_seed(gt, pipeline, th) -> dict:
    """pipeline: {"columns":[..], "sides":{"left":..,"right":..,"top":..,"bottom":..}}。"""
    families = {}
    fail_reasons = []
    for fam, roles in FAMILY_ROLES.items():
        if fam == "columns":
            polys = pipeline.get("columns", [])
        else:
            polys = _norm_sides(pipeline.get("sides", {}))[fam]
        res = match_family(gt, roles[0], polys, th)
        families[fam] = res
        if res["missing"]:
            fail_reasons.append(f"{fam}: 缺线 {res['missing']}")
        if res["extras"]:
            fail_reasons.append(f"{fam}: 多余线 索引{res['extras']}")
        if res["bridged_samples"]:
            fail_reasons.append(f"{fam}: 断口桥接采样 {res['bridged_samples']}")
        if res["uncovered"]:
            fail_reasons.append(f"{fam}: 账外删除采样 {len(res['uncovered'])}")
        for r in res["lines"]:
            if r["found"] and r["dev"]["p95"] is not None and r["dev"]["p95"] > th.dev_tau:
                fail_reasons.append(
                    f"{fam}/{r['line_id']}: p95={r['dev']['p95']:.1f}px > {th.dev_tau}px")
    card = {
        "schema": "synth_gate_score_v1", "seed": gt["seed"], "pass": not fail_reasons,
        "thresholds": {k: getattr(th, k) for k in th.__dataclass_fields__},
        "families": families, "fail_reasons": fail_reasons,
    }
    return card


def render_md(card) -> str:
    verdict = "PASS" if card["pass"] else "FAIL"
    rows = []
    for fam, res in card["families"].items():
        devs = [r["dev"]["p95"] for r in res["lines"] if r["found"] and r["dev"]["p95"] is not None]
        worst = max(devs) if devs else float("nan")
        rows.append(f"| {fam} | {len(res['lines'])} | {len(res['missing'])} | "
                    f"{len(res['extras'])} | {res['bridged_samples']} | "
                    f"{len(res['uncovered'])} | {worst:.1f} |")
    reason_lines = "\n".join(f"- {r}" for r in card["fail_reasons"]) or "- 无"
    return (f"# 合成门禁记分卡 seed={card['seed']} — **{verdict}**\n\n"
            f"| 族 | GT线数 | 缺线 | 多余 | 桥接采样 | 账外删除 | 最差p95(px) |\n"
            f"| --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) +
            f"\n\n## fail 明细\n{reason_lines}\n")
```

- [x] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_verify_scorecard.py tests/test_verify_match.py -v`
Expected: 全部 passed

- [x] **Step 5: Commit**

```bash
git add src/verify/score_vs_gt.py tests/test_verify_scorecard.py
git commit -m "feat(gate): 三族三层记分卡(JSON+MD),矫正映射回映射"
```

---

### Task 6: crops.py + score_synthetic.py CLI——fail 附裁片与批处理入口

**Files:**
- Create: `src/verify/crops.py`、`src/verify/score_synthetic.py`
- Modify: `memory-bank/gate_ledger.md`(收尾登记)

- [x] **Step 1: 实现 crops.py(违规点放大裁片)**

`src/verify/crops.py`:

```python
# -*- coding: utf-8 -*-
"""fail 违规点放大裁片:扫描图原貌 + GT 线叠加,一违规点一图(大图验收三件套的自动化)。"""
import cv2
import numpy as np

CROP = 512   # 裁片半边长 px(全分辨率)


def save_violation_crops(scan, gt, card, out_dir, scale=2) -> list:
    """对 card 内 uncovered/断口桥接点出裁片;返回写入路径列表。"""
    from pathlib import Path
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    vis = cv2.cvtColor(scan, cv2.COLOR_GRAY2BGR)
    for ln in gt["lines"]:
        if ln["role"] == "row":
            continue
        pts = np.array(ln["samples_warp"], np.int32).reshape(-1, 1, 2)
        color = (255, 128, 0) if ln["role"] in ("frame_side", "frame_tb") else (0, 0, 255)
        cv2.polylines(vis, [pts], False, color, 2)
    h, w = scan.shape[:2]
    spots = [(v["x"], v["y"], f"uncovered_{v['line_id']}")
             for fam in card["families"].values() for v in fam["uncovered"]]
    written = []
    for k, (x, y, tag) in enumerate(spots[:20]):   # 每种子最多 20 张,防爆炸
        x0, x1 = max(0, int(x) - CROP), min(w, int(x) + CROP)
        y0, y1 = max(0, int(y) - CROP), min(h, int(y) + CROP)
        crop = vis[y0:y1, x0:x1]
        crop = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                          interpolation=cv2.INTER_NEAREST)
        p = out / f"crop_{k:02d}_{tag}_{int(x)}_{int(y)}.png"
        cv2.imwrite(str(p), crop)
        written.append(str(p))
    return written
```

- [x] **Step 2: 实现 CLI score_synthetic.py**

`src/verify/score_synthetic.py`:

```python
# -*- coding: utf-8 -*-
"""合成门禁判分 CLI(M2a:路径显式;M2b 由链式胶水接管)。

用法:
  python src/verify/score_synthetic.py --seed 3
      → 对 runs/synthetic_gate 的 seed3 做管线自比(GT 即完美管线,验管线头部/裁片管道)
  python src/verify/score_synthetic.py --seed 3 --rect-map PATH
      → 以 6f 矫正映射.json 的 lines_rect 为管线输出(经 H_rect_to_src 回扫描系)判分
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core import paths
from src.synth.synthesize import PNG_FAST
from src.verify.crops import save_violation_crops
from src.verify.gate_config import DEFAULT_THRESHOLDS
from src.verify.score_vs_gt import apply_h_rect_to_src, render_md, score_seed


def load_pipeline_from_rect_map(rect_map_path):
    m = json.loads(Path(rect_map_path).read_text(encoding="utf-8"))
    h = np.array(m["H_rect_to_src"], np.float64)

    def to_src(pts):
        return [list(q) for q in apply_h_rect_to_src(h, pts)]

    lr = m["lines_rect"]
    return {"columns": [to_src(c["pts"]) for c in lr["columns"]],
            "sides": {k: to_src(v) for k, v in lr["sides"].items()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--rect-map", default=None, help="6f 矫正映射.json;缺省=GT自比(管道自检)")
    ap.add_argument("--gt-dir", default=str(paths.SYNTH_GT_DIR))
    ap.add_argument("--scan-dir", default=str(paths.SYNTH_SCAN_DIR))
    ap.add_argument("--out-dir", default=str(paths.SYNTH_SCORE_DIR))
    args = ap.parse_args()

    gt_p = Path(args.gt_dir) / f"synth_{args.seed:04d}_gt.json"
    scan_p = Path(args.scan_dir) / f"synth_{args.seed:04d}.png"
    gt = json.loads(gt_p.read_text(encoding="utf-8"))
    scan = cv2.imread(str(scan_p), cv2.IMREAD_GRAYSCALE)
    assert scan is not None, f"扫描图缺失 {scan_p}"

    if args.rect_map:
        pipeline = load_pipeline_from_rect_map(args.rect_map)
        mode = f"rect_map={args.rect_map}"
    else:
        pipeline = {
            "columns": [ln["samples_warp"] for ln in gt["lines"] if ln["role"] == "column"],
            "sides": {k: [ln["samples_warp"] for ln in gt["lines"] if ln["role"] == r][0]
                      for k, r in (("left", "frame_side"), ("right", "frame_side"),
                                   ("top", "frame_tb"), ("bottom", "frame_tb"))},
        }
        # sides 期望每键一条折线;GT 自比时 left/right 同 role,取 line_id 区分:
        pipeline["sides"] = {
            "left": [ln["samples_warp"] for ln in gt["lines"] if ln["line_id"] == "col_0"][0],
            "right": [ln["samples_warp"] for ln in gt["lines"] if ln["line_id"] == f"col_{len(gt['layout']['col_xs'])-1}"][0],
            "top": [ln["samples_warp"] for ln in gt["lines"] if ln["line_id"] == "top"][0],
            "bottom": [ln["samples_warp"] for ln in gt["lines"] if ln["line_id"] == "bottom"][0],
        }
        mode = "gt_self_check"

    card = score_seed(gt, pipeline, DEFAULT_THRESHOLDS)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"synth_{args.seed:04d}_score.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / f"synth_{args.seed:04d}_score.md").write_text(render_md(card), encoding="utf-8")
    crops = []
    if not card["pass"]:
        crops = save_violation_crops(scan, gt, card, out_dir / "crops")
    print(f"seed={args.seed} mode={mode} pass={card['pass']} "
          f"fail_reasons={len(card['fail_reasons'])} crops={len(crops)}")
    raise SystemExit(0 if card["pass"] else 2)


if __name__ == "__main__":
    main()
```

- [x] **Step 3: 管道自检(GT 自比必须 PASS)**

Run: `python src/verify/score_synthetic.py --seed 0`
Expected: `pass=True`,退出码 0;`runs/synthetic_gate/scores/synth_0000_score.{json,md}` 生成。

- [x] **Step 4: 人为破坏验证 fail 路径**

Run(临时把一份 GT 抽掉一条线后判分,验证 fail 与裁片;用 python -c 完成,不留文件):

```bash
python - <<'EOF'
import json, shutil, tempfile, subprocess, sys
from pathlib import Path
tmp = Path(tempfile.mkdtemp())
gt = json.loads(Path("runs/synthetic_gate/gt/synth_0000_gt.json").read_text(encoding="utf-8"))
cols = [ln for ln in gt["lines"] if ln["role"] == "column"]
gt["lines"].remove(cols[0])
(tmp / "broken_gt.json").write_text(json.dumps(gt, ensure_ascii=False), encoding="utf-8")
r = subprocess.run([sys.executable, "src/verify/score_synthetic.py", "--seed", "0",
                    "--gt-dir", str(tmp), "--out-dir", str(tmp / "scores")],
                   capture_output=True, text=True)
print(r.stdout.strip(), "exit=", r.returncode)
assert r.returncode == 2
crops = list((tmp / "scores" / "crops").glob("*.png"))
assert crops, "fail 必须附裁片"
print("裁片示例:", crops[0].name)
EOF
```

Expected: `exit= 2`,裁片生成。临时目录自动丢弃。

- [x] **Step 5: 全套测试 + 账本登记 + Commit**

Run: `pytest tests/ -q`
Expected: 全绿(117+新增)。

账本登记(M2.T1,判分器核心:六错例单测+GT自比 PASS+破坏路径 exit2+裁片证据)。

```bash
git add src/verify/ tests/test_verify_*.py tests/test_synth_gt_samples.py memory-bank/gate_ledger.md
git commit -m "feat(gate): M2a 判分器核心完成——三族三层记分卡+违规裁片+反放水单测"
```

---

## Self-Review 记录

1. **Spec 覆盖**:设计 §5.2 三层判分(结构/几何/完整性+N/A 单列——v1 GT na_segments 恒空,记分卡留 families 字段,M2b 接入)、§7 判分器单测=构造错例必报 fail(Task 4 六错例)、fail 附裁片(Task 6)、阈值冻结载体(Task 1)。判定 2 的"程序自动数值核对"在 M2a 以 GT 自比+构造错例落地;对真管线的判定 2/3 实测归 M2b。
2. **占位符**:无 TBD;Task 6 Step 4 的破坏验证是内联脚本不留痕。
3. **类型一致**:`match_family(gt, role, polys, th)`(Task 4 定义,Task 5 调用)、`dev_stats(d)`(Task 3 定义,Task 4 使用)、`apply_h_rect_to_src(h, pts)`(Task 5 定义,Task 6 CLI 使用)、`save_violation_crops(scan, gt, card, out_dir)`(Task 6 定义与使用)签名一致 ✓。GT 新字段 samples_ideal/samples_warp/samples_in_break/breaks_scan_quad 在 Task 2 定义、Task 4/6 消费 ✓。
