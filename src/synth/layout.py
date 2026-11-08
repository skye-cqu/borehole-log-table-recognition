# -*- coding: utf-8 -*-
"""合成图版式:线系要素的矢量定义与推导(理想帧=直图,弯曲只由 degrade.WarpField 引入)。

布局常数取自定稿阶段拟合的标准版式量级(见 vision 定稿:60/65/125/80x4/200/1320/85/545),
实测校准延后(preview 目检偏差后立 M1.5)。所有随机性(淡线选择/断口)经 rng 注入,seed 可复现。

与实施计划的偏差(计划自洽性修正,已登记 gate_ledger):
- col_gaps 是 LayoutSpec 字段(默认标准间隙),小样测试需覆盖——类常量版无法满足 len(col_xs)==4;
- 顶框/底框/表头底线是横贯全宽的水平折线(计划误用竖线助手会画出零长度退化点);
- point_in_breaks 精确复刻渲染断口置白几何,供渲染自检/warp 自检与 M2 判分器共用。
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class LayoutSpec:
    width: int
    height: int
    x0: int                 # 左框 x
    y_top: int              # 顶框 y
    header_h: int           # 表头带高
    row_heights: tuple[int, ...]
    merge_spans: tuple[tuple[int, int], ...]   # 第0列(地质时代)rowspan 行组(闭区间)
    faint_cols: set[int] = field(default_factory=set)  # 褪色列线索引(col_xs 下标)
    faint_rows: set[int] = field(default_factory=set)  # 褪色行线索引(行序号)
    break_prob: float = 0.35
    col_gaps: tuple[int, ...] = (60, 65, 125, 80, 80, 80, 80, 200, 1320, 85, 545)
    deco_pad_r: int = 80    # 东装饰框距最东列线偏移(必错图1 用近距版本)
    faint_gray: int = 130   # 淡线灰度(必错图2 用真图实测 172~196 带内亚阈值版本)

    # 类常量(无注解,不是 dataclass 字段)
    INK_GRAY = 60
    # 淡线灰度定标(2026-09-14 实测):30张真图312根分隔线线芯灰度,可测者最淡
    # 100~130(p5≈115);管线 5t 墨闸=逐行min中位<180。185+blur(σ1.5,3px线提亮
    # ~+10)+noise 后带内读数≈188,恰被墨闸系统性误杀(col_3/col_5 全长轨被
    # header_sup 拒,seed0 实测)。130=真实包络内最淡档,blur 后≈140,留 40 余量。
    # 必错图2"淡线被切断"需亚阈值淡线时由该场景配置另行压低,不在此处。
    FAINT_GRAY = 130
    DECO_GRAY = 40
    BAND_GRAY = 30
    THICK = 4
    DECO_THICK = 6
    DOUBLE_OFFSET = 8   # 平行双线伴随线间距


# 默认全幅版式(3280x20941,与真图同尺寸);测试用小 spec 覆盖
DEFAULT_SPEC = LayoutSpec(
    width=3280, height=20941, x0=200, y_top=150, header_h=400,
    row_heights=(900, 600) * 9,
    merge_spans=((0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (10, 11)),
    faint_cols={3, 5}, faint_rows=set(range(3, 12)),
    break_prob=0.35,
)


@dataclass(frozen=True)
class LineSpec:
    line_id: str
    role: str               # column | row | frame_tb | frame_side | deco
    group: str              # 同组平行线共享(如 "col_8"),单线=自身 id
    polyline: tuple[tuple[int, int], ...]
    gray: int
    thickness: int
    breaks: tuple[tuple[float, float], ...] = ()   # 沿折线弧长 px,渲染置白,GT 落账


@dataclass(frozen=True)
class BlockSpec:
    block_id: str
    kind: str               # band(实心竖带) | rect_outline(粗框)
    geometry: tuple         # band=(x0,x1); rect=(x0,y0,x1,y1)
    gray: int
    thickness: int = 0


@dataclass(frozen=True)
class SynthLayout:
    spec: LayoutSpec
    lines: tuple[LineSpec, ...]
    blocks: tuple[BlockSpec, ...]
    col_xs: tuple[int, ...]
    row_ys: tuple[int, ...]        # 数据行边界(不含 header 底线;长度=len(row_heights)+1)
    header_bottom: int
    y_bottom: int


def sample_polyline(pts, step: float = 50.0):
    """沿折线按弧长步长采样,含端点。返回 [(x,y), ...]。"""
    out = [pts[0]]
    carried = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = float(np.hypot(x1 - x0, y1 - y0))
        if seg == 0:
            continue
        s = step - carried
        while s < seg:
            t = s / seg
            out.append((int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t))))
            s += step
        carried = (carried + seg) % step
    out.append(pts[-1])
    return out


def point_in_breaks(lay: SynthLayout, x: float, y: float) -> bool:
    """点是否落在任一断口的置白区域内。

    与 render._paint_breaks_white 的几何严格互逆:置白半径=thickness//2+1,
    沿线方向再外扩同半径(逐 s 圆盘并集恰好铺满该矩形)。渲染自检与判分器共用。
    """
    for ln in lay.lines:
        if not ln.breaks:
            continue
        (x0, y0), (x1, y1) = ln.polyline[0], ln.polyline[-1]
        vertical = y1 != y0
        half = ln.thickness // 2 + 1
        for s0, s1 in ln.breaks:
            b0, b1 = int(s0) - half, int(s1) + half
            if vertical:
                if abs(x - x0) <= half and y0 + b0 - half <= y <= y0 + b1 + half:
                    return True
            else:
                if abs(y - y0) <= half and x0 + b0 - half <= x <= x0 + b1 + half:
                    return True
    return False


def _vline(line_id, role, group, x, y0, y1, gray, thick, breaks=()):
    return LineSpec(line_id, role, group, ((x, y0), (x, y1)), gray, thick, breaks)


def _hline(line_id, role, group, y, x0, x1, gray, thick, breaks=()):
    return LineSpec(line_id, role, group, ((x0, y), (x1, y)), gray, thick, breaks)


def make_layout(rng: np.random.Generator, spec: LayoutSpec | None = None) -> SynthLayout:
    sp = spec or DEFAULT_SPEC
    col_xs = [sp.x0]
    for g in sp.col_gaps:
        col_xs.append(col_xs[-1] + g)
    row_ys = [sp.y_top + sp.header_h]
    for h in sp.row_heights:
        row_ys.append(row_ys[-1] + h)
    y_bottom = row_ys[-1]

    def breaks_for(length: float) -> tuple:
        if rng.random() >= sp.break_prob:
            return ()
        n = 1 if rng.random() < 0.7 else 2
        out = []
        for _ in range(n):
            s0 = rng.uniform(0.1, 0.85) * length
            out.append((s0, min(s0 + rng.uniform(30, 120), length - 5)))
        return tuple(sorted(out))

    lines: list[LineSpec] = []
    for i, x in enumerate(col_xs):
        role = "frame_side" if i in (0, len(col_xs) - 1) else "column"
        gray = sp.faint_gray if i in sp.faint_cols else sp.INK_GRAY
        thick = 3 if gray == sp.faint_gray else sp.THICK
        brks = breaks_for(float(y_bottom - sp.y_top))
        lines.append(_vline(f"col_{i}", role, f"col_{i}", x, sp.y_top, y_bottom, gray, thick, brks))
        if i == len(col_xs) - 2:  # 柱状带东缘做平行双线(真图柱状区多条平行竖线的最小化身)
            lines.append(_vline(f"col_{i}b", "column", f"col_{i}", x + sp.DOUBLE_OFFSET,
                                sp.y_top, y_bottom, gray, thick))
    for r, y in enumerate(row_ys[:-1]):  # 数据行线(每行顶边)
        gray = sp.faint_gray if r in sp.faint_rows else sp.INK_GRAY
        thick = 3 if gray == sp.faint_gray else 3
        brks = breaks_for(float(col_xs[-1] - col_xs[0]))
        lines.append(_hline(f"row_{r}", "row", f"row_{r}", y,
                            col_xs[0], col_xs[-1], gray, thick, brks))
    lines.append(_hline("header_bottom", "row", "header_bottom", row_ys[0],
                        col_xs[0], col_xs[-1], sp.INK_GRAY, 5))
    lines.append(_hline("top", "frame_tb", "top", sp.y_top,
                        col_xs[0], col_xs[-1], sp.INK_GRAY, 5))
    lines.append(_hline("bottom", "frame_tb", "bottom", y_bottom,
                        col_xs[0], col_xs[-1], sp.INK_GRAY, 5))
    lines.append(_vline("deco_l", "deco", "deco", sp.x0 - 80, sp.y_top - 70, y_bottom + 70,
                        sp.DECO_GRAY, sp.DECO_THICK))
    lines.append(_vline("deco_r", "deco", "deco", col_xs[-1] + sp.deco_pad_r, sp.y_top - 70,
                        y_bottom + 70, sp.DECO_GRAY, sp.DECO_THICK))
    blocks = (BlockSpec("band_bind", "band", (18, 52), sp.BAND_GRAY),)
    return SynthLayout(sp, tuple(lines), blocks, tuple(col_xs), tuple(row_ys),
                       row_ys[0], y_bottom)
