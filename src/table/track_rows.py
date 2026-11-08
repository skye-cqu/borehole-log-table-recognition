# -*- coding: utf-8 -*-
"""阶段6 (c)：行线检测（列线同一套像素追踪，坐标转置复用，零新算法）。

横向 high 段 → 点坐标 (x,y)→(y,x) 交换 + 墨迹图转置 → 复用 track_group.build_tracks
→ 链 → track_columns.merge_tracks 同线合并 → 再按 y 聚簇成"线"。
层界判据 = 数值区覆盖率 cov_num ≥ ROW_COV：
    这条线（并集后）横断了"表左缘 → 真厚右界（柱状带西缘）"至少 ROW_COV 宽 → 它切断所有数值列
    → 它是层界。数值区右界按整簇折线向 6a 定稿列线求交（表斜，常数界两端差 100~250px）。
    柱状列不是数值列，不进窗口；带里的墨迹不进结构证据（两条带各管一道，见 load_chains 注释）：
    柱状带段级预滤 + 条目级切带内点（跨带口子画直连弦）；水文带只做条目级切（行线止步带西缘，
    东端贴切线的终端尾巴还回——岩性行线的 T 接行尾是行界证据不是污染；孤点碎片贴邻居趋势才留），
    穿到右框的表框线豁免——真墨迹贯穿（1015 顶框带内满墨实测 frac=1.00）。带缘断口以下由
    continue_below 续到表底：近锚（≤0.5×最宽格）照抄锚形平移，远锚（岩性右界 30 张全是
    1311~1603px 外的柱状带东缘）只按右框平移不抄形——1042 抄形续出 45px 幽灵线、掩膜照着
    吃掉岩性区六行行尾的教训（2026-09-30，v9）。
时代列西延+曲率桥（extend_era_rows，2026-10-01，桥为 10-02 收尾）：时代列是 rowspan 列，
    只有时代界行有横线穿过它；普查同款口径选出候选行后沿原图墨迹蛇形西行，真空段按本图
    实测曲率 profile 桥接（逐段入档 era_bridge_segs），终点无条件接触左框；普通行不动
    （全拉到框边=造线）。
行线弦修复（refine_row_chords，2026-10-02，项③）：链折线断口的直线弦 → 墨迹蛇走锚定
    （断口里的断续淡墨锚到即纠偏）+ Hermite 曲率桥（真无墨处，端点切线连续过渡）；
    柱状带内强制桥接。只动 poly/n_poly 与 chord_* 账本字段，身份字段不动。
子行线 = 跨度够但数值区没切断（岩性描述列内文字行线）。
阈值 0.40 由 30 张扫描定：1032（真值 103）取 0.40 恰为 +0，0.45 起 −1；
1042（真值 112，定稿已注明"煤层|深度未检出"）全线 −3~−13，缺检真线不由阈值补。

2026-09-25 五道门禁（分支 stage-rows-gates，起因：1027 画出的线在原图里不存在）：
    门禁2 形状（用户口径：全表大部分行线有一个共同斜率，部分线条拼接后斜率波动超阈值就是歪了）：
      判"拼成线之后"，读数 = 300px 逐窗斜率的中位数离参照斜率的距离，>SKEW(2%) 不作层界，
      落 JSON 的 off_grid（叠加图紫色），名单交回阶段5 复核拼链。参照默认是"这条线上下 SKEW_BAND(1.5) 行高
      内邻居链的窗斜率中位"（SKEW_BAND，见 line_ref）——整张弯曲的表上全表中位斜率不是任何
      一行的参照，1020 因此被误杀 64 条贴墨真行。
      实测依据：1027 y=10886 那条"层界"一条链从 x=500 的 11005 爬到 x=2300 的 10873，
      斜率 6.6%；台阶口径(Δx<60 的跳变)对它读数 0px，完全放过——这就是上一版漏修的原因。
      三条路线都被 runs/tmp/sweep_gates.py + sweep_shape.py 用原图横线墨迹量过，取最后一条：
        逐链判斜率 3% → 1027 层界 115→92、漏线 2→14，只消掉 1 条坏线（短链斜率噪，冤枉直的真行）；
        线级整体斜率 5% → 115→111，但 1040 陪葬一条真行线 y=20654（跨 2526px、离墨 0.0%，
          整体斜率 5.5% 是"弯"不是"爬"）；
        线级窗中位斜率 2% → 两张图 0 条真行被杀（真行 |窗中位| 实测最大 1%），
          1027 的爬行线 y=10886(−3.7%)、y=10894(−4.6%) 落 off_grid。
      边界要说清楚：形状读数只管得住"爬"这一类。1027 离墨>15% 的 12 条里它抓到 3 条，
      1040 的 4 条一条也抓不到（窗中位 0.0%、台阶 0.00 行高，形状跟真行一模一样）——
      剩下那些得靠墨迹验证（约束2 允许的成分），不是靠调阈值。
    门禁1 聚簇 = 完全链接 + 簇竖向直径 ≤ 半行高（两遍法估行高）。旧的单链接只跟
      "上一条链"比 y，一条中间高度的链能把上下两行逐级串成一条（1027 实测 33 条带台阶
      层界里 15 条这样来；接缝跳 55~127px）。
    门禁3 数值区右界按整簇折线对锚线求一次交；旧代码逐链求交又 clip 到该链自己的跨度，
      链断在数值区里时中位数虚高（1040 y=5101 存 2010 / 实交 1034）→ 真线被降级。
    门禁4 切分 = 聚簇之前先把链在"300px 窗两侧中位差 >SPLIT_FRAC(0.6) 行高"的台阶处下刀：
      一条链左半贴 A 行、右半贴 B 行时（1027 y=4446 实测爬 69px），只能在台阶处切开让两半
      各归各行；线级剪枝(trim_pts)试过，实测更坏（离墨>30% 的层界 1→10 条），已删。
    门禁5 内容列排除（用户第二轮指出："柱状那一列绘制的图的线条也算进去了"）：柱状列里画的是
      岩性图案（煤块上下缘、灰岩砖缝、砂岩点行），不是表格线。整条落在柱状带的横段不作结构
      证据，数值区窗口也从带东缘（岩性左界）收到带西缘（真厚右界）——同阶段6g 删列口径。
      为什么非收不可：带宽实测 162~323px，比两道闸的窗宽 WIN_DX=300px 还窄，带内的台阶两侧
      凑不满两个整半窗 → 切分闸与形状闸在带里是同一个盲区，线能在带里跳一整行而读数都是 0
      （1035 y=5739 带内比带外高 1.01 行高）。30 张门禁4 的刀口 72%（168/234）落在带里，见 runs/tmp/ab_bandmask.log。
每条线存折线 poly = 它自己那几条成员链的原点（同像素 x 取中位 y 去双描锯齿），
再 approxPolyDP 分段线性化；只删顶点不挪顶点，删完按竖向残差复核，>POLY_TOL(5px) 退回原点列。
画线与切格都按横向位置在折线上取高度；旧表征 y_at_mid 仅存为全条线高度中位数。
输出 {stem}_行判定.json + 行线 overlay；不改动任何已有产物。
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table import track_group  # noqa: E402
from src.table.track_columns import load_chain, merge_tracks, x_at  # noqa: E402

ROW_FRAC = 0.55     # 主行线跨度比例（1019 层界实测 ~0.77·表宽）
SUB_FRAC = 0.28     # 子行线跨度比例（岩性描述文字行 ~0.46·表宽）
ROW_COV = float(os.environ.get("ROW_COV", 0.40))   # 层界判据：数值区覆盖率下限，30 张扫描标定
                                                  # 环境变量只为阈值 A/B 用，默认值不变
LINE_TOL = 25.0     # 聚簇容差下限（同一条线的链碎片竖向可差这么多，1032 真行高最小 27px）
N_SAMPLE = 25       # 行链与列线求交时的采样点数
POLY_EPS = 2.0      # 折线分段线性化的垂距容差(px)
POLY_TOL = 5.0      # 用户容差：折线离成员链原点的竖向偏差上限，超了就不删顶点
STEP_DX = 60.0      # 台阶窗：Δx 小于它的相邻顶点落差才算"同一处的跳变"，长距离斜度不计
RISE_DX = 100.0     # 局部爬升窗(px)：Δx≤100 内的峰谷差，量"线在一段里抖了多少"
# 形状门禁（用户口径：全表大部分行线有一个共同斜率，部分线条拼接后斜率波动超阈值就是歪了）。
# 判"拼成线之后"，读数用逐窗斜率中位数（为什么不用整体斜率/不逐链判，见 win_slope 与
# runs/tmp/sweep_shape.py、sweep_gates.py 的实测）。阈值 2%：两张图上真行的 |窗中位| 最大 1%。
SKEW = float(os.environ.get("SKEW", 0.02))
WIN_DX = 300.0      # 斜率窗宽(px)：一窗 ≈ 数值区宽度的四成，够长才不被噪声主导
# 形状闸的"参照斜率"取谁：全表中位斜率在整张弯曲的图上不是任何一行的参照——30 张里 28 张的
# |窗中位−全表中位| 中位数落在 0.1~0.8%，1020 是 2.10%（一条真行自己就超 2% 闸），169 条线
# 被剔 94 条，其中 64 条离墨≤10%（贴在真横线上）。换成"上下 SKEW_BAND 行高内邻居链的窗斜率
# 中位"（不含自己，见 line_ref）：弯表跟着弯走，直表邻居中位≈全表中位。0 = 退回全表参照。
# 1.5 行高 = 30 张实测（runs/tmp/ab_band.py，各档都带切分闸；表头=层界/剔线/剔中贴墨=误杀/漏线）：
#   全表 3430 172 119 79 离墨>10% 1024 挤96 规整51%
#   1.0  3558  44  26 72       1059   106     52%
#   1.5  3584  18   8 64       1067   107     52%   ← 取这档
#   2.0  3586  16   6 63       1067   107     52%
# 1.5 已把误杀 119→8、漏线 79→64；2.0 只再多 2 条层界，真剔(=剔−误杀)从 1.0 的 18 降到 10 后
# 就不再变，而带越宽越靠近"全表平均"、局部性没掉得越快（5 张分档 runs/tmp/ab_band_sweep.log：
# 3 行高时 1027 反过来开始误杀真行）。1.0→1.5 只动 9 张：8 张变好，1019 多误杀 1 条。
SKEW_BAND = float(os.environ.get("SKEW_BAND", 1.5))
# 切分线：一条链在 300px 窗内"两侧中位差"超过它×行高 = 这条链把两行拼在了一起，下刀切开。
# 0.6 = 实测分档（runs/tmp/ab_split.py，基线=只形状闸，标尺=原图横线墨）：
#   1027(行高68) 层界 116→117、离墨>10% 34→30、离墨>30% 1→1、漏线 1→1，切开 12/223 条链；
#   1040(行高77) 三项读数全不变(108/31/0/1)，切开 3/216 条链，两条线从拼错的位置回到墨上
#     （y=18756→18668，挪 88px = 1.1 行高；y=7001→6967）。
#   再松（0.4/0.3）开始误伤：1027 层界 116→115→114；再紧（1.0/1.5）切不净：1027 离墨>10% 回到
#   32/33，1040 那 88px 的拼接链（唯一一条 >1.0 的）就没人管了。0.5 与 0.6 只差 1027 一条线，
#   取切得少的那档。
# 剪枝(trim_pts，把离本线中位 >0.25 行高的一段剪掉)试过、废了：它把 1027 的离墨>30% 从 1 条
# 顶到 10 条、漏线 1→2，还会把爬行的线剪平到通过形状闸（剔线 2→0），等于给坏线发通行证。
SPLIT_FRAC = float(os.environ.get("SPLIT_FRAC", 0.6))

# 柱状带 = 内容列，不是表格线。带里画的是岩性图案（煤块上下缘、灰岩砖缝、砂岩点行），
# 阶段6g clean_columns 已按用户 2026-09-05 指示把"柱状""简易水文曲线"两列裁掉；6c 同一口径：
# 整条落在带里的阶段4 横段不作结构证据，数值区右界也从带东缘（岩性左界）收到带西缘（真厚|柱状）。
# 为什么必须收：柱状列不是数值列，旧口径把它算进覆盖率窗口，等于让图案边线给"这条线切断了
# 所有数值列"投票；而且带宽 ~202px < 两道闸的窗宽 WIN_DX=300px，带内的台阶两侧凑不满两个
# 整半窗 → 切分闸和形状闸在带里是同一个盲区，线可以在带里跳一整行而两道闸读数都是 0。
BAND_MIN = 150.0        # 带宽下限(px)：30 张实测 162~323（中位 202），再窄就是数值列自己的格宽
BAND_MAX = 330.0        # 上限：最宽的 1042 带 323px（该图数值列偏窄），再宽就成岩性描述了
BAND_RATIO = 1.5        # 且带宽 ≥ 它左边各数值格中位的 1.5 倍。30 张数值格中位 68~90px → 门槛 101~135px
                        # 全低于下限 150，故这一条在本仓库从未生效（1020 的 79px 真厚列是下限挡掉的）；
                        # 留着是给"数值列本身就宽"的图，那时上下限都不 bind
BAND_W_MED = 202.0      # 带东缘未检出的图（1020）：从西缘按 30 张实测带宽中位推，同 6g 规则②
HYDRO_MAX = 900.0       # 水文带宽度上限(px)：比柱状带宽（无 BAND_MAX 硬闸，实测见 content_band）
HYDRO_FRAME_KEEP = 20.0  # 条目右端到 tab_r 不足此距 = 表框线（顶/底边框），水文带内的真墨迹不切
BAND_PAD = 6.0          # 段落在带内的判定余量：骑在带缘上的段保留（那是真行线伸到带缘的部分）
FRAME_PAD = 8.0         # 行线段裁进 6a4 外框时，离框边这么近以内算框外（框线自身有 2~4px 粗）

# ---- 时代列西延（项②，2026-10-01）----
# 诊断（runs/tmp/census_era_final_20261001.py）：时代列 = rowspan 列，29 图仅 205 行在时代列有
# 横线墨（行界横线物理上不进该列），这 205 行的线西端距左框中位 70px——成因 76 行被 clip_to_frame
# 杀贴框短段 / 57 行只有低信段 / 71 行无段。修复走行级后处理墨迹验证西延（约束2 的"墨迹验证外延"），
# 不动建链、不动 clip_to_frame（被杀 high 段 707/26057，多数与时代列无关，全局放行危险）。
# 文献判据（runs/table_reconstruct/调研_时代列rowspan与结构建模_20261001.md）：桥接容差以线宽倍数计
# （GILDA gap≤2×lw），外延须逐段过墨迹验证，墨行程粗细分"线"与"竖线穿越"（普查 P5：框线/装订条
# 竖线穿过测窗的墨不是横线证据）。
ERA_THICK = 6.0         # 细墨/竖线穿越分界 = 6×lw；lw 每图实测（行线竖向墨行程中位，30 张 3~4px）
ERA_CROSS = 30.0        # 竖线穿越最大可穿过宽度 px（时代行实测 max 28）
ERA_GAP = 60.0          # 无墨空档中止 px（±8 容差窗下 196 时代行实测无 >60 内空档；断在这儿=墨到不了框）
ERA_WIN = 8.0           # 墨迹重锚竖向容差 px（时代行普查同款 y±8，两处一把尺）
ERA_DRIFT = 6.0         # 墨行程中心离行线外推 y 的上限（≈2×lw，防拐上时代列文字笔画；不逐点累积）
ERA_STEP = 3            # 扩展点采样步长 px
# ---- 曲率桥（2026-10-02 用户口径：时代界行必须接触左框列线）----
# v1 的连接门（首墨距链端 ≤15 不接）与"墨尽收笔"留下 62 行不接触，用户判定不达标准。
# 真空段改走曲率桥：预测轨迹 = 行线线性外推 + 本图曲率 profile（同图已走查成功行的
# 墨中心-外推差按绝对 x 分箱中位——弯曲是框/装订的整图性质，同 x 各行偏差一致，实测
# 系统差 7~24px 全被 profile 吃掉），桥上逐点仍找细墨、找到就锚回真墨。
ERA_BIN = 20.0          # 曲率 profile 分箱宽 px（每行每 px 一个样本，20px 一箱样本量足、分辨率够）
ERA_CURV_DRIFT = 10.0   # 桥上墨中心离预测轨迹的残差上限（系统弯已入 profile，残差实测 ≤5px；
                        # 10≈2.5×lw 留余量，远小于行距 ≥180px 防跳行，文字笔画离线 ≥20px 仍拒）


def column_anchor(stem):
    """6a 列结构定稿 → 岩性描述左界列线 (y,x) 点列。

    定稿是视觉模型逐编号判定 + 用户肉眼核验过的列线集合（叠加图上红圈数字即其编号）。
    锚点 = 定稿列线中相邻间距最大一格的左界（实测 1300~1522px，独一无二）；
    与 5 张已写列名的定稿逐张对过：1018/1024/1025/1033/1042 差 0px。
    不用 6b 表头映射：它拿候选段重算 x，1030 外推出 -3902、1020 走空分支。
    """
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    if not fp.exists():
        return None
    st = json.load(open(fp, encoding="utf-8"))
    cols = sorted(st["columns"], key=lambda c: c["x_at_mid"])
    if len(cols) < 2:
        return None
    xs = [c["x_at_mid"] for c in cols]
    _, k = max((b - a, i) for i, (a, b) in enumerate(zip(xs, xs[1:])))
    pts, _ = load_chain({"segment_ids": cols[k]["segment_ids"]}, seg)
    return pts


def _band_chains(stem):
    """content_band / hydro_band 的公共部分：6a 定稿列链 + 最宽格（岩性描述）定位。

    返回 (cj, ch, k, w, wide, num, y_end)；列结构定稿缺失/格数不足返回 None。
    """
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    if not fp.exists():
        return None
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    cols = sorted(json.load(open(fp, encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
    xs = [c["x_at_mid"] for c in cols]
    if len(xs) < 4:
        return None
    _, k = max((b - a, i) for i, (a, b) in enumerate(zip(xs, xs[1:])))
    wide = xs[k + 1] - xs[k]
    num = [xs[i + 1] - xs[i] for i in range(k - 1)]
    if not num:
        return None
    ch = [load_chain({"segment_ids": c["segment_ids"]}, seg)[0] for c in cols]
    return cj, ch, k, xs[k] - xs[k - 1], wide, num, float(cj["height"])


def content_band(stem):
    """6a 定稿列线 → (带西缘点列, 带东缘点列, 出处)。认不出带时返回 (None, None, None)。

    带 = 最宽格（岩性描述，实测 1300~1522px）左边那一格，要同时满足：明显比它左边的数值格宽
    （≥BAND_RATIO 倍中位）、宽度落在 BAND_MIN~BAND_MAX、且远窄于岩性描述。三条件缺一就不删
    任何段（宁可留着图案边线，也不要把真数值列的证据抹掉）。
    带东缘在定稿里没检出的图（1020，finalize_columns 已注明"柱状|岩性未检出"）：锚线本身就是
    带西缘，东缘按 30 张实测带宽中位平移推出，出处记 'template'（同 6g 规则②）。这条推算的线
    只用作"排除证据"的边界，不画成结构线、不进任何产物，且落进 warnings 备查。
    两条缘出覆盖的部分一律照 continue_below 续到表底：定稿列线在表下半张常断，断口以下带子
    必须跟着整张表的偏移动走，否则压在数值列上（用户按证据片指出"绿线在原图里不存在"）。
    水文带单独走 hydro_band（col_segments.py 依赖本函数的三元签名，别并回来）。
    """
    b = _band_chains(stem)
    if b is None:
        return None, None, None
    cj, ch, k, w, wide, num, y_end = b
    if max(BAND_MIN, BAND_RATIO * float(np.median(num))) <= w <= min(BAND_MAX, 0.5 * wide):
        fr = table_frame(stem)
        west = continue_below(ch[k - 1], ch[:k - 1] + ch[k:], y_end, fr, wide)
        east = continue_below(ch[k], ch[:k] + ch[k + 1:], y_end, fr, wide)
        return west, east, "line"
    if w < BAND_MIN and k >= 6:       # 东缘漏检：锚线就是带西缘，东缘按实测带宽推
        west = continue_below(ch[k], ch[:k] + ch[k + 1:], y_end,
                              table_frame(stem), wide)
        return west, west + [0.0, BAND_W_MED], "template"
    return None, None, None


def hydro_band(stem):
    """水文带（岩性描述右缘 → 6a4 右框之间那格，1015 实测 531~621px/30 张）的西缘点列。

    用户 2026-09-30 判定：柱状/简易水温曲线两条图形带都不许出现在识别里。西缘 = 定稿里
    岩性右界那条列线（最宽格右缘）；东缘就是右框本身，不单独返回——裁点时"西缘以右全不要"。
    带宽不出 BAND_MIN~HYDRO_MAX 视为没有这格（岩性直通右框的图，如 1032）；外框不可信时
    宁可不认（宽度没法量，宁可不删也不误删）。断口以下照 continue_below 跟着邻线平移续到表底。
    """
    b = _band_chains(stem)
    if b is None:
        return None
    cj, ch, k, w, wide, num, y_end = b
    fr = table_frame(stem)
    if k + 1 >= len(ch) or fr is None:
        return None
    hright = continue_below(ch[k + 1], ch[:k + 1] + ch[k + 2:], y_end, fr, wide)
    ymid = float((hright[0, 0] + hright[-1, 0]) / 2)
    w_hydro = edge_at(fr[1], ymid) - edge_at(hright, ymid)
    return hright if BAND_MIN <= w_hydro <= HYDRO_MAX else None


def edge_at(chain, y):
    """列线在 y 处的 x，y 出覆盖时按近端常量延接（不外插斜率）。

    x_at 在覆盖外是线性外推（boundary_x 就为此按"覆盖不到就丢点"处理过），裸外插会把带甩飞：
    1035 西缘只到 y=12267、东缘到 12830，外插到 y=13320 时整条带滑成 x=[-524,511] —— 带里的
    图案边线一条没排掉，反倒把数值列那一带（中点 x 中位 601）当成"带内"删了 46 条；y=20071 更
    滑到 x=[-8963,-6240]。常量延接只是兜底，带缘真正的续法在 continue_below（跟着邻线平移）。
    """
    a = np.asarray(chain, float)
    return float(x_at(a, min(max(y, a[0, 0]), a[-1, 0])))


def continue_below(chain, others, y_end, fr=None, wide=None):
    """列线在中途断掉时，把断口以下按"最近一条当时还活着的列线 + 断口处实测偏移"平行续到 y_end。

    带的两条缘都是 6a 定稿列线、在表下半张常中断（1035 西缘只到 y=12267、东缘到 12830，表画到 20071）。
    冻结在断口处不够：整张表在下半张继续往右偏，1035 冻到 y=19500 时两条缘都离真线 113px，
    整条带压在带西边的数值列上——带里的图案边线一条没排掉，反倒去删数值列的证据。
    锚线 = 断口那一高度上离它最近、且当时仍在覆盖的定稿列线（1035 西缘→x@中点 694.7 那条，
    断口处实测间距 76px）；平移量在断口处实测，锚线本身由阶段4 候选段构成，不引入原图没有的线。
    没有任何锚线时原样返回（宁可不删，也不把带挪到没量过的地方）。

    锚分两档（2026-09-30，1042 岩性区行尾被吃 45px 定性后加）：近锚（间距 ≤ 0.5×wide，
    wide=最宽格宽）照抄锚形 + 断口平移——相邻列线受同一张纸的弯，局部形有对应；远锚
    （> 0.5×wide）只平移不抄形，改按右框续：断口以下 x = 右框(y) − 断口前 400px 实测"到右框间距"
    的中位数。岩性右界的锚在 30 张上全部是 1311~1603px 外的柱状带东缘（近档实测最大 616px，
    两档恰好分开）；1042 实抄进它 45px 宽的双线形，续出一条原图不存在的平行线，水文带掩膜
    照着把岩性区六行行尾切短。隔着一整个最宽格的远锚，局部形没有对应关系，一个像素不抄。
    无右框时退回旧抄法（没有更好的）。
    """
    a = np.asarray(chain, float)
    yb = a[-1, 0]
    if yb >= y_end:
        return chain
    best = None
    for ch in others:
        c = np.asarray(ch, float)
        if not (c[0, 0] <= yb < c[-1, 0]):        # 断口处这条线还在、且比它画得更低
            continue
        d = abs(edge_at(ch, yb) - a[-1, 1])
        if best is None or d < best[0]:
            best = (d, ch)
    if best is None:
        return chain
    if fr is not None and wide and best[0] > 0.5 * wide:
        f = np.asarray(fr[1], float)              # 右框：全高单线，弯跟着整张表走
        ov = a[a[:, 0] <= f[-1, 0]]
        last = ov[ov[:, 0] > ov[-1, 0] - 400.0]   # 断口前 400px 的局部带宽（单点会吃噪声）
        w = float(np.median(_edge_xs(f, last[:, 0]) - last[:, 1]))
        ys = f[f[:, 0] > yb, 0]
        tail = np.column_stack([ys, _edge_xs(f, ys) - w])
        return np.vstack([a, tail])
    off = a[-1, 1] - edge_at(best[1], yb)
    tail = np.asarray(best[1], float)
    tail = tail[tail[:, 0] > yb]                  # 锚线在断口以下的那截，照抄采样、只平移
    return np.vstack([a, np.column_stack([tail[:, 0], tail[:, 1] + off])])


def in_band(pts, band):
    """段的中点落在带内 = 这段是带里的图案边线。骑在带缘上的段不算（保留）。

    两条缘的 x 由 content_band 交过来（断口以下已跟着邻线平移续到表底），这里只按段的高度取值。
    """
    west, east = band
    p = np.asarray(pts, float)
    ym = float(np.median(p[:, 1]))
    x = (p[:, 0].min() + p[:, 0].max()) / 2
    return edge_at(west, ym) + BAND_PAD <= x <= edge_at(east, ym) - BAND_PAD


def _edge_xs(chain, ys):
    """列线在若干高度上的 x（向量化，y 出覆盖按近端常量延接，同 edge_at 口径）。"""
    a = np.asarray(chain, float)
    return np.interp(np.clip(np.asarray(ys, float), a[0, 0], a[-1, 0]), a[:, 0], a[:, 1])


def _in_band_mask(xs, ys, bands):
    """逐点判"在任一带内"（BAND_PAD 骑缘保留）。水文带 east=None：西缘以右全算带内。"""
    inside = np.zeros(len(xs), bool)
    for west, east in bands:
        w = _edge_xs(west, ys) + BAND_PAD
        if east is None:
            inside |= np.asarray(xs, float) >= w
        else:
            inside |= (np.asarray(xs, float) >= w) & \
                      (np.asarray(xs, float) <= _edge_xs(east, ys) - BAND_PAD)
    return inside


def all_in_band(pts, bands):
    """整段每个点都在带内 = 图案边线（追踪前整段剔掉，省得链在带里串门）。"""
    p = np.asarray(pts, float)
    return bool(len(p)) and bool(_in_band_mask(p[:, 0], p[:, 1], bands).all())


SINGLETON_FIT_TOL = 25.0  # 孤点碎片/水文终端恢复的趋势容差(px)：1042 真尾偏差 0~2px、
                          # 骑带缘台阶点 48~51px，取中
HYDRO_RESTORE = 20.0      # 水文带终端恢复深度(px)：帧相对切线的宽度漂移实测 ≤12px（1042，
                          # w 中位 vs 断口 560.2→真宽 553.6），再加 BAND_PAD 余量


def _trend_keep(ref, x, y):
    """孤点 (x,y) 离参照点列的线性趋势 ≤ SINGLETON_FIT_TOL（参照不足 2 点视为共线，留）。"""
    r = np.asarray(ref, float)
    if len(r) < 2:
        return True
    p = np.polyfit(r[-5:, 0], r[-5:, 1], 1)
    return abs(float(np.polyval(p, x)) - float(y)) <= SINGLETON_FIT_TOL


def band_split_item(it, bands, tab_l, tab_r):
    """条目点列按带切开：带内一个点不进条目，跨带的口子不桥接。

    为什么切条目不切段：段 id 是阶段4 出处，一拆两会伪造出处；切条目则 ids 原样保留
    （同一段碎成两片是事实）。断口两侧接不回来不用防——追踪的跳距上限 gap_max=150px，
    柱状带净宽 ~192px、水文带 500px+，物理上接不回来。柱状带（east≠None）对框线也照切：
    带里的图案边线/台阶点污染不分框线不框线，框线跨带的口子由画线直连弦补上（204px 弦弓高
    ≤2px，见 _draw_poly）。切条目还治追踪在带内跳上图案边线的台阶（1042 实测 49px 台阶、
    窗斜率 13.9% 超闸杀真行——台阶点全在带内，切开即消）。
    水文带（east=None）西缘以右的点整段裁掉，条目自然止步带西缘——两道例外：
    ① 穿到右框的条目（= 表框线，顶/底边框，原图真墨迹贯穿水文带，1015 顶框带内满墨实测
    frac=1.00）：它的水文带点不切。不豁免的后果实测：1028 底框东尾被切，只剩陡的西段，
    窗斜率中位 −2.4% 离全表参照超 2% 闸被误杀（全线几何窗中位 +0.6% 过闸）。
    ② 条目东端贴着切线的终端尾巴（≤HYDRO_RESTORE）按行界的 T 接尾巴还回去——岩性描述的
    行线画到带缘为止，行尾就是行界证据，不是骑带污染；切线本身有 ±12px 宽度漂移，不还会把
    真尾一起切掉（1042 岩性区六行实测）。只还终端：深入带内又折回的骑带顶点（30 张实测
    307 个）东边还有存活点，不满足"终端"，照切。
    碎片的 y 键一律用原链的 y（调用方 load_chains 会把同源碎片当场重并成一条带豁口的条目）：
    曾试过碎片局部 y（靠聚簇重聚）→ 接缝差超容差拆两条；也试过剔点不拆条 → y 键重算引发
    全表行高级联漂移。原链 y + 当场重并两条教训各取一半（2026-09-30，v8）。
    单点碎片：跟着邻居趋势才留（离趋势 >SINGLETON_FIT_TOL 的是骑带缘的台阶点，如 1042
    [955,13265]；贴趋势的是稀疏行线的真尾/带缘骑点）；全条目只剩单点碎片时彼此共线即留
    （追踪既然把两个点并成一条链，切带不该比不切更严），一条不剩点才弃。
    """
    pts = np.asarray(it["pts"], float)
    if not len(pts):
        return []
    closed = [(w, e) for w, e in bands if e is not None]
    hydro = [(w, e) for w, e in bands if e is None]
    keep_hydro = bool(hydro) and float(pts[:, 0].max()) >= tab_r - HYDRO_FRAME_KEEP
    ok = ~_in_band_mask(pts[:, 0], pts[:, 1], closed if keep_hydro else bands)
    if hydro and not keep_hydro:
        # 终端恢复：东端连续的水文带内点，贴着切线（≤HYDRO_RESTORE）的还回去
        hyd = _in_band_mask(pts[:, 0], pts[:, 1], hydro)
        e = len(pts) - 1
        if hyd[e] and ok[:e].any():
            s = e
            while s > 0 and hyd[s - 1]:
                s -= 1
            line = _edge_xs(hydro[0][0], pts[s:e + 1, 1]) + BAND_PAD
            ok[s:e + 1] = pts[s:e + 1, 0] - line <= HYDRO_RESTORE
    runs = []
    i = 0
    while i < len(pts):
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(pts) and ok[j + 1]:
            j += 1
        runs.append((i, j))
        i = j + 1
    big = [r for r in runs if r[1] > r[0]]        # ≥2 点的碎片，无条件留
    out = []
    for a, b in runs:
        pc = pts[a:b + 1]
        if b == a and big:                        # 单点碎片：贴邻居（≥2 点碎片）趋势才留
            ref_run = min(big, key=lambda r: min(abs(r[0] - a), abs(r[1] - a)))
            if not _trend_keep(pts[ref_run[0]:ref_run[1] + 1], pc[0, 0], pc[0, 1]):
                continue
        x0, x1 = max(float(pc[0, 0]), tab_l), min(float(pc[-1, 0]), tab_r)
        if x1 < x0:                               # 单点碎片 x0=x1，只在点出窗时弃
            continue
        h = dict(it)
        h["pts"] = pc
        h["x"] = (x0, x1)
        h["y"] = it["y"]                          # 原链 y 键原样保留，见 load_chains 重并
        h["step"] = step_of(pc)
        h["slope"] = slope_of(pc)
        out.append(h)
    return out


def table_frame(stem):
    """6a4 闭合外框的左右两条边 → ((y,x) 左, (y,x) 右)，不可信时 None。

    为什么要外框定表宽：行的左右界原来取"最长链自己撑出来的跨度"，链会一路拼到框外的
    深度刻度和边注上（30 张实测比真外框左多 61px、右多 100px，最坏 327/285px，
    75 条行线端点出框）。外框是 6a4 已核验过的产物，拿它当界比让链自己猜强。
    不可信 = 缺文件 / 边不在图内 / 左右颠倒或窄于半张图（1032 的左边中位落在 x=0）。
    """
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_闭合外框.json"
    if not fp.exists():
        return None
    d = json.loads(fp.read_text(encoding="utf-8"))
    if not (d.get("left", {}).get("pts") and d.get("right", {}).get("pts")):
        return None
    L = np.array([[p[1], p[0]] for p in d["left"]["pts"]], float)     # 存的是 [x,y]，换成 (y,x)
    R = np.array([[p[1], p[0]] for p in d["right"]["pts"]], float)
    w = int(json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json",
                           encoding="utf-8"))["width"])
    lo, hi = float(np.median(L[:, 1])), float(np.median(R[:, 1]))
    if not (0.02 * w < lo < hi < 0.98 * w) or hi - lo < 0.5 * w:
        return None
    return L, R


def clip_to_frame(pts, L, R):
    """横段裁到外框以内，只留框内最长的一段连续点；框内不足 2 点返回 None。

    框外那段是页边的深度刻度/标注，不是这条行线（约束：表外的东西不能算进结构线）。
    """
    p = np.asarray(pts, float)
    ok = (p[:, 0] > np.interp(p[:, 1], L[:, 0], L[:, 1]) + FRAME_PAD) & \
         (p[:, 0] < np.interp(p[:, 1], R[:, 0], R[:, 1]) - FRAME_PAD)
    best = cur = None
    for i, v in enumerate(ok):
        if v:
            cur = [i, i] if cur is None else [cur[0], i]
        elif cur:
            best = cur if best is None or cur[1] - cur[0] > best[1] - best[0] else best
            cur = None
    if cur:
        best = cur if best is None or cur[1] - cur[0] > best[1] - best[0] else best
    # 数值区里全是 2 点短段（一段 50~90px），要求 ≥3 点会把整个数值区丢掉
    return None if best is None or best[1] - best[0] < 1 else p[best[0]:best[1] + 1]


def boundary_x(row_pts, col_pts, x0, x1):
    """行链与列线求交 → 该处的数值区右界 x。

    在行链自己的 x 跨度上采样，逐点取列线在该高度的 x，取中位数：
    列线里混进别的线碎片时（实测 1035 锚线 x 从 982 抖到 287）中位数不受少数污染点影响。
    列线覆盖不到的 y 一律丢点（x_at 在区间外是线性外推，实测能把 x 推到 700px 之外），
    整条线都在覆盖之外时取列线近端 x 常量延接。
    """
    lo, hi = float(col_pts[0, 0]), float(col_pts[-1, 0])
    bs = []
    for x in np.linspace(x0 + 5, x1 - 5, N_SAMPLE):
        y = x_at(row_pts, x)
        if lo <= y <= hi:
            bs.append(x_at(col_pts, y))
    if bs:
        return float(np.median(bs))
    ymid = x_at(row_pts, (x0 + x1) / 2)
    return float(col_pts[0, 1] if ymid < lo else col_pts[-1, 1])


def union(iv):
    """区间并集长度。"""
    ca = cb = None
    tot = 0.0
    for a, b in sorted(iv):
        if ca is None:
            ca, cb = a, b
        elif a <= cb:
            cb = max(cb, b)
        else:
            tot += cb - ca
            ca, cb = a, b
    return tot + (cb - ca if ca is not None else 0.0)


def cover(mem, a, z):
    """覆盖率的量尺：成员链在窗口 [a,z] 内的横向覆盖并集 ÷ 窗口宽（门禁3 定完右界后用它）。

    每条链先裁到窗口里，裁空的丢掉。旧代码直接把 (链左界, min(链右界, z)) 塞进 union，
    整条落在窗口右边的链算出负长度，把并集拽穿 0：1040 y=5101 数值区实覆盖 85%
    （链 381→1034 横断数值区），跟它同簇的描述区链 2357→3069 贡献 -1324px，
    cov_num 读数 -1.70 → 一条真层界被降级成子行线 = 用户看到的"1040 漏线"。
    """
    iv = [(max(m["x"][0], a), min(m["x"][1], z)) for m in mem]
    return union([q for q in iv if q[1] > q[0]]) / max(z - a, 1.0)


def step_of(pts):
    """链的最大台阶（Δx<STEP_DX 的相邻顶点 |Δy| 最大）；只登记进 JSON，不作判据。
    1027 有 20 条、1040 有 13 条带大台阶的链（最大 561px），是阶段5/6 拼链带进来的。
    为什么不当门禁：它对"缓坡爬行"读数 0px（1027 那条 6.6% 斜率的爬升链），
    而 300px 内一跳的形态交给 split_pts 下刀，比按台阶剔整条线少挖空洞。"""
    p = np.asarray(pts, float)
    if len(p) < 2:
        return 0.0
    m = np.diff(p[:, 0]) < STEP_DX
    return float(np.abs(np.diff(p[:, 1]))[m].max()) if m.any() else 0.0


def span_dev(ap, ax, bp, bx):
    """两段点列的竖向落差：x 有公共段就在公共段上逐点比 y；
    纯左右并列（无公共 x）时比接缝两端各自 5 个点的中位 y。"""
    lo, hi = max(ax[0], bx[0]), min(ax[1], bx[1])
    if hi - lo >= 5:
        xs = np.linspace(lo, hi, N_SAMPLE)
        return float(np.abs(np.interp(xs, ap[:, 0], ap[:, 1])
                            - np.interp(xs, bp[:, 0], bp[:, 1])).max())
    left, right = (ap, bp) if ax[0] <= bx[0] else (bp, ap)
    return abs(float(np.median(left[-5:, 1])) - float(np.median(right[:5, 1])))


def join_dev(it, c):
    """门禁1 的量尺：链并入整簇的竖向代价 = 与"簇折线"的落差、与簇内每条 x 上重叠的
    链的落差，取最大（完全链接）。
    旧判据只跟"上一条链"比 y（单链接），一条中间高度的链能把下一行的链逐级串上来
    ——1027 实测 33 条带台阶的层界里 15 条就是这么拼出来的（接缝跳 55~127px）。
    这一闸管"一次跳半行"，簇竖向直径那一闸管"逐级爬"，两闸合起来才拦得住跨行。"""
    ds = [span_dev(it["pts"], it["x"], c["poly"], c["x"])]
    ds += [span_dev(it["pts"], it["x"], m["pts"], m["x"]) for m in c["mem"]
           if min(it["x"][1], m["x"][1]) - max(it["x"][0], m["x"][0]) >= 5]
    return max(ds)


def cluster(items, tol):
    """链按 y 排开，逐条找代价最小的簇并入，代价 > tol 则另起一簇。

    两道闸一起用：① 簇的竖向直径 ≤ tol（防"逐级爬行"——单链接靠 20px 一级的小台阶
    能从第一行走到第三行）；② 新链与整簇的形状差 ≤ tol（join_dev，防一次跳半行）。
    容差用半行高（行高由两遍法的第一遍估出，见 determine_rows）。
    """
    out = []
    for it in items:
        best, dbest = None, tol
        for c in out:
            if max(it["y"], c["y1"]) - min(it["y"], c["y0"]) > tol:
                continue                     # 闸①：并进来就撑破直径
            d = join_dev(it, c)
            if d < dbest:
                best, dbest = c, d
        if best is None:
            out.append({"mem": [it], "poly": it["pts"].copy(), "x": it["x"],
                        "y0": it["y"], "y1": it["y"]})
            continue
        best["mem"].append(it)
        best["poly"] = polyline(best["mem"])
        best["x"] = (min(best["x"][0], it["x"][0]), max(best["x"][1], it["x"][1]))
        best["y0"] = min(best["y0"], it["y"])
        best["y1"] = max(best["y1"], it["y"])
    return out


def lines_from(clusters, tab_l, tab_r, tab_w, col, ref=None):
    """一簇链 = 图上的一条线：折线表征 + 数值区覆盖率 → 层界 / 子行线 / 其余 / 走偏。

    ref=(参照斜率, 斜率闸) 或 (参照斜率, 斜率闸, 局部参照带) 时判形状（不给则不判，第一遍估行高
    用）：逐窗斜率的中位数离参照斜率 >斜率闸 的不进层界（落 offgrid），因为这条线在图上不存在，
    画出来只会把上下两行格子切坏。第三项给了带宽(px)就按 line_ref 换成局部参照，全表 s0 只兜底。
    门禁3：数值区右界按"整簇折线 vs 6a 锚线"求一次交。旧代码逐条链求交后又 np.clip 到
    该链自己的 x 跨度——链断在数值区里时 clip 把交点拽回链尾，取中位后分母虚高
    （1040 y=5101 存 2010，锚线实交 1034），真行界被降级成子行线。
    """
    rows, subs, others, offgrid = [], [], [], []
    fits = [(c, *fit_poly(c["poly"])) for c in clusters]        # (簇, 折线, 拟合残差)
    # 形状闸的参照斜率：一条线一条，全表同一个 s0 或"上下邻居的窗斜率中位"（见 line_ref）
    refs = line_ref([float(np.median(pl[:, 1])) for _, pl, _ in fits],
                    [win_list(pl) for _, pl, _ in fits], ref[0],
                    ref[2] if ref is not None and len(ref) > 2 else None) \
        if ref is not None else [0.0] * len(fits)
    for (c, pl, res), sr in zip(fits, refs):
        mem = c["mem"]
        x0, x1 = c["x"]
        b = boundary_x(pl, col, x0, x1) if col is not None else tab_r
        b = float(np.clip(b, tab_l, tab_r))
        cn = cover(mem, tab_l, b)
        cd = cover(mem, b, tab_r)
        span = x1 - x0
        rec = {"segment_ids": sorted({i for m in mem for i in m["ids"]}),
               "x": [round(x0), round(x1)],
               "poly": [[round(float(px), 1), round(float(py), 1)] for px, py in pl],
               "n_poly": len(pl),
               "y_at_mid": round(float(np.median(pl[:, 1])), 1),
               "fit_res": round(res, 1),
               "span": round(span), "res90": round(max(m["res"] for m in mem), 1),
               "n_split": sum(1 for m in mem if "src" in m),   # 成员里有几段是切开的链
               "cov_num": round(cn, 3), "cov_desc": round(cd, 3),
               "boundary_x": round(b), "n_chains": len(mem),
               "step": round(max(m["step"] for m in mem), 1),
               "slope": round(slope_of(pl) - sr, 4) if ref else 0.0,
               "win": round(win_slope(pl, sr), 4) if ref else 0.0,
               "ptp": round(ptp_off(pl, sr), 1) if ref else 0.0,
               "rise": round(rise_of(pl), 1)}
        if cn >= ROW_COV or (col is None and span >= ROW_FRAC * tab_w):
            # 层界先过形状门禁：歪的线不当层界用
            (offgrid if ref and abs(rec["win"]) > ref[1] else rows).append(rec)
        elif span >= SUB_FRAC * tab_w:
            subs.append(rec)                       # 描述区内文字行线/跨行分隔
        else:
            others.append(rec)
    rows.sort(key=lambda r: r["y_at_mid"])
    return rows, subs, others, offgrid


def rise_of(pts, dx=RISE_DX):
    """局部爬升：Δx≤dx 窗内的峰谷差(px)。先铺到 1px x 网格再滑窗，O(n)。
    一条真横线在 100px 里最多抖几个 px；抖出十几 px 的就是从一行走到另一行。"""
    p = np.asarray(pts, float)
    if len(p) < 2:
        return 0.0
    xs = np.arange(p[0, 0], p[-1, 0] + 1)
    y = np.interp(xs, p[:, 0], p[:, 1])
    w = int(dx) + 1
    if len(y) <= w:
        return float(y.max() - y.min())
    win = np.lib.stride_tricks.sliding_window_view(y, w)
    return float((win.max(axis=1) - win.min(axis=1)).max())


def slope_of(pts):
    """整体斜率 dy/dx（最小二乘）。表是斜的，所以判歪看它离参照斜率多远，不看绝对值。"""
    p = np.asarray(pts, float)
    return float(np.polyfit(p[:, 0], p[:, 1], 1)[0]) if len(p) > 1 else 0.0


def ptp_off(pts, s0):
    """扣掉全表倾斜后，这条线/链在自己的跨度上竖向走了多远(px)。只登记，不判据。

    本来想拿它当门禁（走超半行高 = 从某行爬到邻行），实测分不开好坏：
    1027 无门禁 115 条层界里，贴合真行(离墨≤10%) 81 条 ptp 中位 0.28 行高，
    离墨>10% 的 34 条 ptp 中位 0.29——两个分布重叠；1040 ptp 最大的那条(8.1 行高)
    离墨 0.0%，是一条真而弯的行线。所以它只作为读数进 JSON 供复核。
    """
    p = np.asarray(pts, float)
    q = p[:, 1] - s0 * p[:, 0]
    return float(q.max() - q.min())


def win_list(pts, dx=WIN_DX):
    """这条线的逐窗斜率列（绝对值，不减参照）。跨度不足 2 窗 → 空列（读数没意义）。"""
    dx = int(dx)
    p = np.asarray(pts, float)
    xs = np.arange(p[0, 0], p[-1, 0] + 1)
    if len(xs) < 2 * dx:
        return []
    ys = np.interp(xs, p[:, 0], p[:, 1])
    return [slope_of(np.column_stack([xs[a:a + dx], ys[a:a + dx]]))
            for a in range(0, len(xs) - dx, int(dx / 2))]


def win_slope(pts, s0, dx=WIN_DX):
    """逐窗斜率的中位数（减参照斜率）——用户那条门禁的可用形态。

    整体最小二乘斜率会被"真而弯"的行线骗到：1040 y=20654 跨 2526px、离墨 0.0%（一条
    货真价实的行线），整体斜率 5.5% 就会被 5% 闸杀掉；它每一小段都跟表平行，窗中位 −0.8%。
    反过来，拼接爬行的线（1027 y=10886）每一窗都在爬，窗中位 −3.7%，整体 −7.6%。
    两档实测：真行(离墨≤10%)的 |窗中位| 最大 1%，坏线里最高的到 4.6% → 阈值取 2%。
    """
    ws = win_list(pts, dx)
    return float(np.median(ws) - s0) if ws else 0.0


def line_ref(ys, wss, s0, band):
    """每条线的斜率参照：band=None/0 → 全表中位斜率；band=若干 px → 这条线上下 band 之内
    邻居链的逐窗斜率中位数（邻居凑不满 3 个窗也退回全表）。

    为什么要局部参照：1020 这张表整张在弯，全表中位斜率不是它任何一行的参照——3615 条线
    的 |窗中位−全表中位| 中位数，28 张在 0.1~0.8%，1020 是 2.10%，一条真行自己就超了 2% 闸，
    于是 169 条线里 94 条被剔（其中 64 条离墨≤10%，贴在真横线上）。参照换成"我上下 1.5 行高
    之内的邻居"，弯表跟着弯，直表不变（邻居中位 ≈ 全表中位）。

    邻居里不含自己：一条谁也挨不上的孤线（正是拼歪出来的那种假线）若把自己的窗算进参照，
    参照 = 自己 → 窗中位恒等于 0 → 形状闸对它就永远不会响，门禁形同虚设。剔掉自己之后邻居
    不够 3 个窗，按"没有局部上下文"处理，退回全表参照（旧行为，保守）。
    """
    if not band:
        return [s0] * len(ys)
    out = []
    for j, y in enumerate(ys):
        near = [w for k, (yj, ws) in enumerate(zip(ys, wss))
                if k != j and abs(yj - y) <= band for w in ws]
        out.append(float(np.median(near)) if len(near) >= 3 else s0)
    return out


def skewed(pts, s0, skew=SKEW):
    """这条线歪不歪：逐窗斜率的中位数离参照斜率 >skew。

    台阶口径(Δx<60 的跳变)对 1027 那条 6.6% 爬升链读数 0px，看不见缓坡，已废。
    """
    return abs(win_slope(pts, s0)) > skew


def step_score(seg, q, dx):
    """每个缝隙处的"持久台阶"读数 = 缝左右两半窗(x±dx/2)各自中位高度之差(px)。

    为什么不用峰谷差(rise_of)：峰谷差把"上下抖动"和"爬到邻行"混为一谈。同一把尺子量
    1027 的 223 条链，47% 超过 0.5 行高——真链在 300px 里也会抖出 30px，一刀下去链变 300 段，
    簇散了：层界 118→107、漏线 2→6（runs/tmp/ab_split.py 首跑，同一批链）。
    中位差只认"一侧整体压着另一侧"的持久错位：来回抖时两边中位差不多，缓坡长爬
    （真而弯的行线，1040 y=20654）两边中位只差几个 px，都不报。
    两半窗必须各自铺满 dx/2（缝隙离本段两端都 ≥ dx/2）才比：一刀切过之后，子段边缘的窗
    只剩刀口边那一两个点，中位数一翻就又是满额"台阶"，会把同一条链从刀口一路削成碎点
    （实测 3 段变 5/9 段）。贴本段端头没有两侧各一整半窗的证据，就不下第二刀。
    读数在台阶前后一整个"多数派没变"的区间里是同一个满额值（平台），平台正中才是台阶本身，
    见 split_pts。
    """
    c = (seg[:-1, 0] + seg[1:, 0]) / 2
    a = np.searchsorted(seg[:, 0], c - dx / 2)
    b = np.searchsorted(seg[:, 0], c + dx / 2, side="right")
    i = np.arange(len(c))
    ok = ((c - seg[0, 0] >= dx / 2) & (seg[-1, 0] - c >= dx / 2)
          & (a <= i) & (b >= i + 2))       # 两半窗都得有点：链上 >dx/2 的空隙会让一半空掉
    return [0.0 if not o else abs(np.median(q[lo:i + 1]) - np.median(q[i + 1:hi]))
            for i, (lo, hi, o) in enumerate(zip(a, b, ok))]


def split_pts(p, s0, jump, dx=WIN_DX):
    """链级切分：在"台阶两侧中位差 >jump px"的缝隙处下刀，返回切完的点列列表。

    要治的形态（就是用户说的"把上一行的线和下一行的线连起来了"）：一条链左半贴着某行、
    右半贴着邻行，中间一道 60~90px 的斜撑台阶。1027 y=4446 实测：左半 4447、x765→968 爬
    69px、右半 4381（放大图 runs/tmp/剪枝_1027_4446.png = 切分前，切分_1027_4446.png = 后）。
    这种线画出来把上下两行各切成半格，而它在原图上不存在。下刀切开后两半各归各行的簇
    （门禁1 重聚），一条错线变成两条对线。
    为什么不在"线"上剪：试过 trim_pts（把线上离本线中位 >0.25 行高的一段剪掉），实测反而变坏
    ——1027 离墨>30% 的层界 1→10 条、漏线 1→2，还把爬行的线剪平到能过形状闸（剔线 2→0）：
    剪出来的弦不再贴墨，形状闸也就没东西可剔了。已删，读数见 runs/tmp/ab_split2.log。
    一段要切，缝隙两侧都得有整半窗（≥dx/2）站得住——斜撑那类百来 px 的短爬升切完只剩碎渣，
    这种段自己就没有能下刀的位置，交给聚簇拦。刀口落在缝隙上，不插值造点（约束2）。
    刀口取平台正中而不是第一个最高点：台阶两侧各有一整段缝隙的读数相同（中位数的多数派还没
    换），取第一个会把上一行的三五个点留在下一行那半上，而门禁1 的 join_dev 按最差点比，
    那几点就把切开的半条挡在它的行外（实测：切完 3 簇而不是 2 簇）。
    """
    todo = [np.asarray(p, float)]
    out = []
    while todo:
        seg = todo.pop()
        if len(seg) < 3:
            out.append(seg)
            continue
        q = seg[:, 1] - s0 * seg[:, 0]             # 扣掉全表倾斜，只留这条链自己走的量
        sc = np.asarray(step_score(seg, q, dx))
        if sc.max() <= jump:
            out.append(seg)
            continue
        top = np.flatnonzero(sc == sc.max())       # 平台：多数派没变的一整段缝隙读数都是满额
        i = int(top[len(top) // 2])                # 取平台正中 = 台阶本身，两半才各自干净
        todo += [seg[:i + 1], seg[i + 1:]]
    return sorted(out, key=lambda s: s[0, 0])


def split_items(items, s0, jump):
    """把切分作用到全部链上，返回 (可直接进聚簇的链表, 被切开的链数)；jump<=0 = 不切，A/B 用。

    同一把刀切出来的两段仍带原链的 ids：段是链的一部分，不是新造的墨，
    溯源时能一眼看出"这两条线来自同一条阶段4 链"。
    """
    out = []
    cut = 0
    for it in items:
        segs = split_pts(it["pts"], s0, jump) if jump > 0 else [it["pts"]]
        if len(segs) == 1:
            out.append(it)
            continue
        cut += 1
        for sg in segs:
            out.append({"y": x_at_mid({"pts": sg}), "x": (float(sg[0, 0]), float(sg[-1, 0])),
                        "res": it["res"], "step": step_of(sg), "slope": slope_of(sg),
                        "pts": sg, "ids": it["ids"], "src": it["x"]})
    out.sort(key=lambda it: it["y"])
    return out, cut


def polyline(mem):
    """这条线的折线 = 成员链自己的点，按 x 排开（不造新点，约束2）。

    merge_tracks 把"同线双描"按 x 交织（同一 x 两个 y），直接画是锯齿：
    同一像素 x 只留一个 y，取这些点 y 的中位数——落点仍是原图墨迹处。
    """
    pts = np.vstack([m["pts"] for m in mem])
    pts = pts[np.argsort(pts[:, 0], kind="stable")]
    ix = np.rint(pts[:, 0]).astype(int)
    ends = np.r_[np.flatnonzero(ix[1:] != ix[:-1]), len(pts) - 1]
    starts = np.r_[0, ends[:-1] + 1]
    return np.array([[pts[a, 0], float(np.median(pts[a:b + 1, 1]))] for a, b in
                     zip(starts, ends)])


def v_resid(pl, raw):
    """折线 pl 相对原始点列 raw 的竖向偏离(px)：在每个原始点的 x 上取 pl 高度。"""
    return float(max([abs(x_at(pl, x) - y) for x, y in raw], default=0.0))


def fit_poly(pts):
    """折线 → 分段线性，返回 (点列, 竖向残差)。approxPolyDP 只删顶点、不挪顶点。

    approxPolyDP 的 ε 量的是垂距，陡段上"垂距 2px"折算成竖向可达 20px(1020 实测)，
    而画线与切格用的都是竖向高度 → 删完再按竖向核一遍，>POLY_TOL 就退回原始点列。
    退回去的线仍是成员链自己的点，残差 0，代价只是 JSON 长一点。
    """
    k = np.asarray(cv2.approxPolyDP(pts.reshape(-1, 1, 2).astype(np.float32),
                                    POLY_EPS, False), float).reshape(-1, 2)
    r = v_resid(k, pts)
    return (k, r) if r <= POLY_TOL else (pts.copy(), 0.0)


def row_y(rec, x):
    """横向位置 x → 该处这条线的高度（列方向 _chain_x 的镜像）。

    x 出界不外推：track_columns.x_at 在点列区间外是线性外推，实测能把 y 推到 700px
    之外（1035 缺陷）——取近端点值。
    """
    p = np.asarray(rec["poly"], float)
    if x <= p[0, 0]:
        return float(p[0, 1])
    if x >= p[-1, 0]:
        return float(p[-1, 1])
    return float(x_at(p, x))


def _swap_points(pts):
    return [[int(p[1]), int(p[0])] for p in pts]


def load_chains(stem: str):
    """阶段4 横向 high 段 → 行链（坐标转置复用列追踪那套 machinery）。

    建链是 30 多秒的重活，门禁参数不是：拆开后同一批链可以反复喂给 assemble 试阈值，
    不必每档重跑一遍追踪（阈值 A/B 从 12 次全跑变成 1 次全跑）。
    无长横链（这张图做不出行结构）返回 None。
    """
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    segs_src = [s for s in cj["lines"]
                if s["direction"] == "horizontal" and s["label"] == "high"]
    # 两条带各管一道（2026-09-30 实测定型，v6）：
    # 柱状带：段级预滤（整段在带内的多为图案边线）+ 条目级切带内点。后者不可省——预滤分不清
    #   "图案边线"和"行线自己的穿带段"（1042 一条行的带内段被预滤误杀后，追踪在带内跳上图案
    #   边线，台阶 49px，窗斜率 13.9% 超闸，真行被杀）；条目切分把带内台阶点切掉，行线跨带
    #   以直连弦画（204px 弦弓高 ≤2px）。
    # 水文带：只做条目级切（普通行线的带内顶点是骑带污染，30 张备份实测 307 个、抽查无墨），
    #   不做段级预滤——框线真穿带（1015 顶框带内满墨 frac=1.00），预滤会把 1028 底框东段误杀。
    #   穿到右框的表框线条目豁免切分（HYDRO_FRAME_KEEP，见 band_split_item）。
    west, east, band_src = content_band(stem)
    hydro = hydro_band(stem)
    n_band = 0
    if west is not None:
        keep = [s for s in segs_src if not all_in_band(s["points"], [(west, east)])]
        n_band = len(segs_src) - len(keep)
        segs_src = keep
    bands = []
    if west is not None:
        bands.append((west, east))
    if hydro is not None:
        bands.append((hydro, None))
    # 框外那段（页边深度刻度、边注）不是行线：逐段裁进 6a4 外框再建链
    fr = table_frame(stem)
    n_clip = 0
    if fr is not None:
        cut = []
        for s in segs_src:
            q = clip_to_frame(s["points"], *fr)
            if q is None:
                n_clip += 1
                continue
            if len(q) != len(s["points"]):
                s = dict(s)
                s["points"] = q.tolist()
                s["length"] = float(q[-1, 0] - q[0, 0])
            cut.append(s)
        segs_src = cut
    img_w, img_h = int(cj["width"]), int(cj["height"])

    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    ink = track_group.binarize(gray, track_group.PARAMS).T   # 转置：行→列
    del gray                                                  # 56MB/张，后面用不到

    segs = []
    for s in segs_src:
        pts = np.asarray(s["points"], float)
        i_top = int(pts[:, 1].argmin())          # 转置后 y=原 x
        i_bot = int(pts[:, 1].argmax())
        adj_t = pts[1] if i_top == 0 else pts[i_top - 1]
        adj_b = pts[-2] if i_bot == len(pts) - 1 else pts[i_bot + 1]
        segs.append({
            "id": s["id"],
            "top": pts[i_top][::-1].copy(),
            "bot": pts[i_bot][::-1].copy(),
            "v_top": _dir_down(pts[i_top][::-1], adj_t[::-1]),
            "v_bot": _dir_down(pts[i_bot][::-1], adj_b[::-1]),
            "points": _swap_points(s["points"]),
            "length": float(s["length"]),
        })
    tracks, _ = track_group.build_tracks(segs, ink, track_group.PARAMS)
    by_id = {s["id"]: s for s in segs}
    groups = merge_tracks(tracks, by_id)

    longs = [g for g in groups if g["y1"] - g["y0"] >= 0.5 * img_w]
    if not longs:
        return None
    if fr is not None:
        # 表的左右界取外框内缩最多的那一处：窗口整条都在框里，框外的刻度进不了覆盖率分母
        tab_l = float(fr[0][:, 1].max()) + FRAME_PAD
        tab_r = float(fr[1][:, 1].min()) - FRAME_PAD
    else:
        tab_l = min(g["y0"] for g in longs)
        tab_r = max(g["y1"] for g in longs)
    tab_w = max(tab_r - tab_l, 1.0)
    col = west if west is not None else column_anchor(stem)
    items = []
    for g in groups:
        x0, x1 = max(g["y0"], tab_l), min(g["y1"], tab_r)     # merge_tracks 的第一坐标=原图 x
        if x1 - x0 <= 0:
            continue
        items.append({"y": x_at_mid(g), "x": (x0, x1), "res": g["res"],
                      "step": step_of(g["pts"]), "slope": slope_of(g["pts"]),
                      "pts": g["pts"], "ids": list(g["ids"])})
    if bands:
        # 切开的碎片当场重并成一条（点列留豁口，y 用原链 y 键）：碎片若靠聚簇接缝比较重聚，
        # 框线在带缘有真台阶时接缝差超容差会拆成两条（1028 底框接缝 37px > 容差 36、
        # 1042 岩性区六行碎片各奔东西）；"剔点不拆条"则让 y 键随保留点重算，全表行高/容差
        # 级联漂移（1028 行高 72→74）。原链 y + 当场重并两个都要。豁口处孤点碎片（骑带缘的
        # 图案边线点，1042 实测 [955,13265]）在 band_split_item 已按 <2 点丢弃，不会混进来。
        merged = []
        for it in items:
            pieces = band_split_item(it, bands, tab_l, tab_r)
            if len(pieces) > 1:
                m = dict(pieces[0])
                m["pts"] = np.vstack([p["pts"] for p in pieces])
                m["pts"] = m["pts"][np.lexsort((m["pts"][:, 1], m["pts"][:, 0]))]
                m["x"] = (min(p["x"][0] for p in pieces), max(p["x"][1] for p in pieces))
                m["step"] = step_of(m["pts"])
                m["slope"] = slope_of(m["pts"])
                merged.append(m)
            else:
                merged.extend(pieces)
        items = merged
    items.sort(key=lambda it: it["y"])
    # 全表中位斜率 = 表的倾斜。歪不歪是相对它量的（表本来就斜，绝对斜率没有意义）。
    s0 = float(np.median([it["slope"] for it in items]))
    for it in items:
        it["ptp"] = ptp_off(it["pts"], s0)
    warns = [] if col is not None else ["无列结构定稿，层界退回全宽判据"]
    if fr is None:
        warns.append("闭合外框不可信：横段未裁进框、表宽退回链自撑（行线端点可能出框）")
    if band_src == "template":
        warns.append(f"柱状带东缘未检出：按 30 张实测带宽中位 {BAND_W_MED:.0f}px 从西缘推算，"
                     f"只用作排除边界不画线")
    # 带几何落 JSON：[[柱状带西缘, 柱状带东缘], [水文带西缘, None]]，(y,x) 点列。检测语义见上，
    # 几何供出数据集/叠加图/验收查顶点避带用；认不出的带不落。
    bands_js = [[np.asarray(w, float).tolist(), None if e is None else np.asarray(e, float).tolist()]
                for w, e in bands]
    return {"stem": stem, "items": items, "s0": s0, "tab_l": tab_l, "tab_r": tab_r,
            "tab_w": tab_w, "col": col, "n_segs": len(segs_src), "n_chains": len(groups),
            "n_band_segs": n_band, "n_frame_segs": n_clip, "framed": fr is not None,
            "band_src": band_src, "bands": bands_js, "warns": warns}


def assemble(ch, skew=None, split=None):
    """链 → 切分 → 簇 → 层界/子行线/走偏名单。
    skew/split = 两个阈值的覆盖（None 用模块默认，A/B 用；0 = 关掉这一道）。

    层界 = 数值区（左表缘→柱状带西缘）被这条线横断 ≥ROW_COV 的线；
    数值区右界按整簇折线向 6a 定稿锚线求交（表是斜的，常数界在左右两端差 100~250px）。
    无定稿时退回全宽跨度判据并记警告。
    门禁 1~4 在本函数（判据细节见 cluster/join_dev/split_pts/lines_from/skewed/cover 的注释）：
      1 聚簇 = 完全链接 + 簇竖向直径 ≤ 半行高 → 一条链不能把上下两行串成一条线；
      2 形状 = 拼成的线逐窗斜率的中位数离参照斜率 >skew(默认 2%) → 不作层界，落 off_grid
        （叠加图紫色，名单在 JSON 里交回阶段5 复核拼链）；链级不判，实测会误杀真行。
        参照默认取"上下 SKEW_BAND 行高内邻居链的窗斜率中位"（SKEW_BAND，不含自己），全表中位斜率只兜底；
      3 数值区右界按整簇折线对锚线求一次交，不再逐链 clip 后取中位；覆盖率按窗口裁段，
        窗口外的链不倒扣（旧算法把真层界降级成子行线 = 用户说的"1040 漏线"）；
      4 切分 = 聚簇之前先把链在台阶处下刀（split，默认 0.6 行高 / 300px 窗两侧中位差）：
        一条链把两行拼成一条时，只能在台阶处切开让两半各归各行，剪线段的办法实测更坏。
    门禁 5 内容列排除在 load_chains 做——它筛的是输入段（柱状带内的段不进链、窗口右界
    收到带西缘），不吃阈值、也不进本函数。
    """
    items, tab_l, tab_r, tab_w, col = ch["items"], ch["tab_l"], ch["tab_r"], ch["tab_w"], ch["col"]
    s0 = ch["s0"]
    # 两遍法：第一遍只按容差下限聚一遍，取相邻层界高度差的中位数 = 全表中位行高；
    # 第二遍的容差 = 半行高，这道门是"相对整表"的量，不针对单图特判（1027/1040 实测 75/79px）。
    first = lines_from(cluster(items, LINE_TOL), tab_l, tab_r, tab_w, col)[0]
    ys = [r["y_at_mid"] for r in first]
    row_h = float(np.median(np.diff(ys))) if len(ys) > 1 else 2 * LINE_TOL
    tol = max(0.5 * row_h, LINE_TOL)
    jump = (SPLIT_FRAC if split is None else split) * row_h    # 切分的尺子要用行高
    band = SKEW_BAND * row_h                                   # 形状闸参照带（0 = 全表参照）
    parts, cut = split_items(items, s0, jump)
    rows, subs, others, off = lines_from(cluster(parts, tol), tab_l, tab_r, tab_w, col,
                                         ref=(s0, SKEW if skew is None else skew, band))
    allr = rows + subs + others + off
    return {"image": ch["stem"], "table_x": [round(tab_l), round(tab_r)],
            # n_band_segs/band_src 只有 load_chains 建出来的 ch 才带；A/B 那批脚本自己手搓 ch
            # 试阈值（见 runs/tmp/ab_*.py），缺键按"没删带"记 0，不为它们改签名。
            "n_input_segments": ch["n_segs"], "n_band_segments": ch.get("n_band_segs", 0),
            "band_src": ch.get("band_src"),
            "bands": ch.get("bands"),   # 带几何 (y,x) 点列，画线/出数据集按它避带；A/B 手搓 ch 为 None
            "n_chains": ch["n_chains"],
            "n_lines": len(allr), "row_cov": ROW_COV,
            "row_h": round(row_h, 1), "step_tol": round(tol, 1),
            "slope_med": round(s0, 4), "skew_gate": SKEW, "skew_band": round(band, 1),
            "split_lim": round(jump, 1),
            "n_chains_split": cut,
            "n_pieces": len(parts),
            "n_lines_offgrid": len(off), "off_grid": off,
            "rows": rows, "sub_rows": subs, "others_n": len(others),
            "warnings": list(ch["warns"])}


def _era_row_ys(p, xs):
    """行折线在 xs 各 x 的高度：折线内线性插值，西端外按两点半径（≥50px 跨度）外推，无则常数。

    与时代行普查的 row_y_at 同口径——普查用它认出 205 行，西延选行必须同一把尺。"""
    p = np.asarray(p, float)
    xs = np.asarray(xs, float)
    ys = np.interp(xs, p[:, 0], p[:, 1])
    west = xs < p[0, 0]
    if west.any():
        k = None
        for j in range(1, len(p)):
            if p[j, 0] - p[0, 0] >= 50:
                k = (p[j, 1] - p[0, 1]) / (p[j, 0] - p[0, 0])
                break
        ys[west] = p[0, 1] if k is None else p[0, 1] + k * (xs[west] - p[0, 0])
    return ys


def _era_ink_run(col, y):
    """（某 x 的灰度列, y）→ (墨行程长, 行程中心 y)。y 本行无墨则在 ±ERA_WIN 内找最近墨行。

    容差窗与时代行普查（y±8、<210）同款。行程从墨行向两侧扩展到墨断为止。"""
    dark = col < 210
    y0 = int(round(y))
    if not (0 <= y0 < len(col)):
        return 0, float(y)
    if dark[y0]:
        lo = hi = y0
        while lo - 1 >= 0 and dark[lo - 1]:
            lo -= 1
        while hi + 1 < len(col) and dark[hi + 1]:
            hi += 1
        return hi - lo + 1, (lo + hi) / 2.0
    for d in range(1, int(ERA_WIN) + 1):
        for yy in (y0 - d, y0 + d):
            if 0 <= yy < len(col) and dark[yy]:
                lo = hi = yy
                while lo - 1 >= 0 and dark[lo - 1]:
                    lo -= 1
                while hi + 1 < len(col) and dark[hi + 1]:
                    hi += 1
                return hi - lo + 1, (lo + hi) / 2.0
    return 0, float(y)


def _era_walk(gray, p, x_e, x_w, lw, Lys, Lxs):
    """时代界行蛇形西行：从链端逐 x 向西找 ±ERA_WIN 内的细墨，锚在墨行程中心。

    细墨（行程 ≤ERA_THICK×lw）才认作行线的墨；粗墨 = 框线/装订条/列线的竖向穿越
    （同一 x 上竖向行程贯通全列），宽 ≤ERA_CROSS 穿过不计空档，更宽视为墙。
    无墨空档 >ERA_GAP 止（墨断的地方不硬走）；墨行程中心离行线外推 y >ERA_DRIFT 不跟
    （时代列文字笔画离行线的高度差，防拐上字）。搜索窗每点都重新锚回行线自己的外推轨迹，
    不逐点累积漂移。(Lys, Lxs) = 稳健左框 L(y) 插值对（_era_frame_left）。
    返回（点列（x 降序）, 到框距离 px）。"""
    thick = ERA_THICK * lw
    pts, gap, d_frame = [], 0, None
    x = int(x_e)
    while x >= int(x_w):
        y_x = float(_era_row_ys(p, [x])[0])
        r, yc = _era_ink_run(gray[:, x], y_x)
        if 0 < r <= thick:
            if abs(yc - y_x) <= ERA_DRIFT:
                pts.append((x, float(yc)))
                gap = 0
            else:
                gap += 1
                if gap > ERA_GAP:
                    break
        elif r > thick:
            wdt = 1
            while x - 1 >= int(x_w):
                r2, _ = _era_ink_run(gray[:, x - 1], float(_era_row_ys(p, [x - 1])[0]))
                if r2 > thick:
                    wdt += 1
                    x -= 1
                else:
                    break
            if wdt > ERA_CROSS:
                break
            gap = 0
        else:
            gap += 1
            if gap > ERA_GAP:
                break
        x -= 1
    if pts:
        y_w = float(_era_row_ys(p, [pts[-1][0]])[0])
        d_frame = int(pts[-1][0] - np.interp(y_w, Lys, Lxs))
    return pts, d_frame


def _era_frame_left(fr):
    """左框链 → 稳健 L(y) 插值对 (ys, xs)：按 y 排序 + 索引滑窗中位（k=15）。

    裸链 28/30 图 y 非单调、19/30 图有横向尖刺（1015 顶部 62px/4px 跳变），np.interp 在
    非单调处静默取错值；尖刺是窄窗内的孤立跳点，滑窗中位滤掉。只给时代列西延当走查目标，
    table_frame 本身不动（裁框/表宽口径不变）。"""
    L = np.array(sorted(np.asarray(fr[0], float).tolist()))
    k = 15
    xs = np.array([np.median(L[max(0, i - k):i + k + 1, 1]) for i in range(len(L))])
    return L[:, 0], xs


def _era_profile(walks):
    """本图曲率 profile：走查成功行的墨中心偏离各自行线线性外推的差值，按绝对 x 分箱取中位。

    左框弯曲/装订是整图性质，同一 x 上各行线的偏差一致（实测系统差 7~24px），profile 把
    它量出来供曲率桥预测真空段的 y 轨迹——全部来自本图实测墨，不是发明形状。
    walks = [(行基线折线 p, 该行走查点列 pts), ...]；无样本返回 None（桥退化为纯外推）。"""
    xs, ds = [], []
    for p, pts in walks:
        if not pts:
            continue
        for x, yc in pts:
            xs.append(x)
            ds.append(float(yc) - float(_era_row_ys(p, [x])[0]))
    if not xs:
        return None
    xs = np.asarray(xs, float)
    ds = np.asarray(ds, float)
    edges = np.arange(xs.min(), xs.max() + ERA_BIN, ERA_BIN)
    idx = np.clip(np.digitize(xs, edges) - 1, 0, len(edges) - 2)
    centers, meds = [], []
    for i in range(len(edges) - 1):
        m = idx == i
        if m.any():
            centers.append((edges[i] + edges[i + 1]) / 2.0)
            meds.append(float(np.median(ds[m])))
    return (np.asarray(centers), np.asarray(meds)) if centers else None


def _era_bridge_walk(gray, p, x_e, lw, Lys, Lxs, prof):
    """曲率桥：沿"行线外推 + 曲率 profile"的预测轨迹从 x_e 走到左框，真空段桥接。

    与 _era_walk 的分工：那边无墨 >ERA_GAP 止（墨断不硬走），这边是补接触——无墨即桥，
    逐列记区间；桥上每列仍按同款细墨判据找墨，找到且离预测轨迹 ≤ERA_CURV_DRIFT 就锚回
    真墨（真空里其实是断续淡墨的能纠偏）。粗墨（竖线/格框）按桥跨过，不特判穿越。
    终点无条件吸附左框：西端 x = 预测 y 处的稳健框线 x（d_frame=0，"接触列线"是项②
    收尾验收标准，用户 2026-10-02 口径）。
    返回（点列 x 降序, 桥区间列表 [[x1,x2],...]（x 升序、每段西≤东）, 桥总长 px）。"""
    thick = ERA_THICK * lw

    def pred(x):
        y = float(_era_row_ys(p, [x])[0])
        if prof is not None:
            y += float(np.interp(x, prof[0], prof[1]))
        return y

    pts, segs = [], []
    bridge = 0
    run = None                      # 当前桥区间 [东端 x, 西端 x]（x 降序积累）
    x = int(x_e)
    while x >= float(np.interp(pred(x), Lys, Lxs)):
        y_p = pred(x)
        r, yc = _era_ink_run(gray[:, x], y_p)
        if 0 < r <= thick and abs(yc - y_p) <= ERA_CURV_DRIFT:
            pts.append((x, float(yc)))
            if run is not None:
                segs.append([x + 1, run[0]])
                run = None
        else:
            bridge += 1
            if run is None:
                run = [x, x]
            else:
                run[1] = x
        x -= 1
    fx = float(np.interp(pred(max(x, 0)), Lys, Lxs))     # 循环出口处的框位
    if run is not None:
        segs.append([int(fx), run[0]])
    if not pts or pts[-1][0] > fx:
        pts.append((fx, pred(fx)))                        # 终点吸附：落在框线上
    segs = sorted([int(min(s)), int(max(s))] for s in segs)
    return pts, segs, bridge


def _era_line_width(rows, ink):
    """线宽 lw = 行线采样点上竖向墨行程的中位（每图实测；>30px 的行程是粘连，不计）。"""
    ts = []
    for r in rows[::max(1, len(rows) // 50)][:60]:
        p = np.asarray(r["poly"], float)
        for x in np.linspace(p[0, 0] + 5, max(p[0, 0] + 6, p[-1, 0] - 5),
                             min(60, max(len(p) * 2, 4))):
            col = ink[int(x)]
            y = int(np.clip(np.interp(x, p[:, 0], p[:, 1]), 0, len(col) - 1))
            if col[y]:
                lo = hi = y
                while lo - 1 >= 0 and col[lo - 1]:
                    lo -= 1
                while hi + 1 < len(col) and col[hi + 1]:
                    hi += 1
                ts.append(hi - lo + 1)
    ts = [t for t in ts if 0 < t <= 30]
    return max(float(np.median(ts)), 2.0) if ts else 2.0


# ---- 行线弦修复(项③,2026-10-02,方案=reports/分析_行列线三问题_20260930.md 现象2)----
CHORD_WIN = 8.0     # 锚定搜索竖向半窗 px(era/普查同款 ±8;09-30 实测骨架偏差 p90=2px,±8 覆盖漂移+线宽)
CHORD_DRIFT = 6.0   # 墨行程中心离当前轨迹上限(≈2×lw,同 ERA_DRIFT;文字笔画离线 ≥20px 拒锚)
CHORD_THICK = 6.0   # 细墨/粗墨分界 = 6×lw(同 ERA_THICK;行线竖向墨行程实测 3~4px)
CHORD_CROSS = 30.0  # 粗墨横穿最大可穿过宽度 px(同 ERA_CROSS,时代行实测 max 28;更宽=图案/污点当空档)
CHORD_STRIDE = 4    # 锚定点入折线的采样步长 px(≈1.5×lw;4px 间隔线性插值离墨曲线 <0.2px)
CHORD_TAN = 40.0    # Hermite 切线拟合窗 px(桥两端各取 ≤40px 已信点做最小二乘斜率;<2 点退 0)
CHORD_MINRUN = 6    # 无墨区入账最小长度 px(再短不值得动笔,量尺 60px 采样也看不见)
CHORD_GAPMAX = 30   # 蛇走空档容忍 px:断续淡墨间隔 ≤30 继续走(era 实测行内空档 ≤60),
                    # 复墨须回两点外推 ±CHORD_DRIFT 内;超限即止,余下交 Hermite
CHORD_EXC = 30.0    # 锚点离弦的竖向偏移上限 px(09-30 实测最大偏差 25px+余量;行距 ≥180px,
                    # 文字/邻行界线离弦更远——防蛇走顺墨爬上邻行,1020 深 V/1027 尖峰的教训)
BAND_PAD_IN = 3.0   # 柱状带内锚定抑制余量 px(带内图案墨不是行线证据,强制桥接)


def _chord_in_band(W, E, y, x):
    """(带缘点列 W,E, y, x) → x 是否落在柱状带内部(y 处 W+BAND_PAD_IN≤x≤E−BAND_PAD_IN)。"""
    if W is None:
        return False
    w = float(np.interp(y, W[:, 0], W[:, 1]))
    e = float(np.interp(y, E[:, 0], E[:, 1]))
    return bool(w + BAND_PAD_IN <= x <= e - BAND_PAD_IN)


def _chord_noink_runs(gray, a, b, lw, W, E):
    """段 a→b 上的无墨区([[u,v],...] x 升序):每 2px 采样,±CHORD_WIN 内无细墨即记;
    柱状带内一律算无墨(带内图案墨不是行线证据,强制桥接)。首版全段蛇走的教训:轨迹
    外推在贴墨段级联漂移,把 1015 的 >10px 偏差从 2.6% 带到 7.1%——改为只动无墨区,
    贴墨段(骨架本来贴墨,中位 0.7px)一字不动。"""
    runs, cur = [], None
    x = a[0] + 2
    dx = max(b[0] - a[0], 1e-6)
    while x < b[0]:
        y = a[1] + (b[1] - a[1]) * (x - a[0]) / dx
        if _chord_in_band(W, E, y, x):
            ok = False
        else:
            r, _ = _era_ink_run(gray[:, int(x)], y)
            ok = 0 < r <= CHORD_THICK * lw
        if not ok:
            cur = [x, x] if cur is None else [cur[0], x]
        elif cur is not None:
            if cur[1] - cur[0] >= CHORD_MINRUN:
                runs.append(cur)
            cur = None
        x += 2
    if cur is not None and cur[1] - cur[0] >= CHORD_MINRUN:
        runs.append(cur)
    return runs


def _chord_walk_side(gray, x0, y0, x1, s0, sgn, lw, W, E):
    """从贴墨边 (x0,y0) 向无墨区内部走(sgn=+1 东向/−1 西向),细墨锚在行程中心。

    轨迹 = 最近两个锚的两点外推(锚距 ≥30px 才启用,否则弦斜率 s0);锚定门 |行程中心−轨迹|
    ≤CHORD_DRIFT。粗墨横穿(列线/竖笔画)跨过;断续淡墨间的空档 ≤CHORD_GAPMAX 继续走
    (复墨须回外推轨迹 ±CHORD_DRIFT 内),超限即止——余下交 Hermite;柱状带内不锚。
    返回锚点列(行走顺序)。只服务无墨区内部(≤几百 px),两点外推的级联漂移被两端贴墨边压住。"""
    thick = CHORD_THICK * lw
    pts = []
    gap = 0
    x = int(round(x0)) + sgn
    while (x < x1) if sgn > 0 else (x > x1):
        if len(pts) >= 2 and abs(pts[-1][0] - pts[-2][0]) >= 30:
            k = (pts[-1][1] - pts[-2][1]) / (pts[-1][0] - pts[-2][0])
            y_tr = pts[-1][1] + k * (x - pts[-1][0])
        elif pts:
            y_tr = pts[-1][1] + s0 * (x - pts[-1][0])
        else:
            y_tr = y0 + s0 * (x - x0)
        if _chord_in_band(W, E, y_tr, x):
            break
        r, yc = _era_ink_run(gray[:, x], y_tr)
        y_chord = y0 + s0 * (x - x0)
        if 0 < r <= thick and abs(yc - y_tr) <= CHORD_DRIFT \
                and abs(yc - y_chord) <= CHORD_EXC:
            pts.append((x, float(yc)))
            gap = 0
        elif r > thick:
            gap = 0                                          # 竖线穿越不是断墨
            x2 = x + sgn
            while x2 != x1 and _era_ink_run(gray[:, x2], y_tr)[0] > thick:
                x2 += sgn
            x = x2 - sgn
        else:
            gap += 1
            if gap > CHORD_GAPMAX:
                break
        x += sgn
    return pts


def _chord_hermite_fill(A, B, mA, mB):
    """两已信点 A→B 的 Hermite 桥采样点(不含端点,含 B 前一步长处);dx≤步长返回空。

    切线按 Fritsch–Carlson 单调钳制(|m|≤3|Δ|,Δ=端点连线斜率):桥不过端点走廊——
    1043 鼓包/1027 尖峰的教训,放任窗拟合切线在短桥上会过冲几十 px。"""
    dx = B[0] - A[0]
    if dx <= CHORD_STRIDE:
        return []
    delta = (B[1] - A[1]) / dx
    lim = 3.0 * abs(delta)
    if delta > 0:
        mA, mB = float(np.clip(mA, 0.0, lim)), float(np.clip(mB, 0.0, lim))
    elif delta < 0:
        mA, mB = float(np.clip(mA, -lim, 0.0)), float(np.clip(mB, -lim, 0.0))
    else:
        mA = mB = 0.0
    ts = np.arange(CHORD_STRIDE, dx, CHORD_STRIDE) / dx
    out = []
    for t in ts:
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1
        h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2
        h11 = t ** 3 - t ** 2
        out.append((A[0] + t * dx, h00 * A[1] + h10 * dx * mA + h01 * B[1] + h11 * dx * mB))
    return out


def _chord_tangent(pts, i, dir_default):
    """已信点列 pts 第 i 点处的切线:向前/向后取 ≤CHORD_TAN 窗内已信点最小二乘;<2 点退 dir_default。"""
    x_i, y_i = pts[i]
    win = [(x, y) for x, y in pts if x_i - CHORD_TAN <= x <= x_i + CHORD_TAN]
    if len(win) >= 2:
        arr = np.asarray(win, float)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")     # 短窗近共线 polyfit 的 RankWarning 无实害
            return float(np.polyfit(arr[:, 0], arr[:, 1], 1)[0])
    return dir_default


def refine_row_chords(stem, out):
    """行线弦修复(项③,行级后处理):只动链折线的"无墨区",贴墨段一字不动。

    背景(09-30 诊断):折线由骨架碎片接链,碎片间断口被直线弦硬连——1015 实测 ±25px 无墨
    采样 5.8%、>10px 偏差 3%,用户看到的"扭曲不贴合"就是这些弦;贴墨段本身很紧(中位
    0.7px/p90 2.0px),不需要动。修法分三层,都满足约束2:
    ①无墨区检测(_chord_noink_runs):段上每 2px 采样,±8px 内无细墨的极大区间(柱状带内
    一律算无墨——图案墨不是行线证据);
    ②双向墨迹蛇走(_chord_walk_side):从无墨区两端的贴墨边向内走,细墨锚在行程中心——断口
    里常存断续淡墨,锚到即接上;
    ③真无墨的残余 Hermite 曲率桥(_chord_hermite_fill):两侧锚的末端各按 ≤40px 窗拟合切线,
    连续过渡替代直线弦切角;两侧全空退弦斜率直桥。
    只动 rows 的 poly/n_poly + 账本字段(chord_bridge_segs/chord_bridge_px/chord_n_anchor),
    x/segment_ids/cov/y_at_mid 等身份字段一律不动(行序与下游切格不受扰);无锚无桥的行
    poly 逐字节不动。sub_rows/off_grid 不在范围(量尺只认 rows)。返回(动笔行数, 桥总长px)。"""
    rows = out.get("rows") or []
    if not rows:
        return 0, 0
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return 0, 0
    W, E, _ = content_band(stem)
    lw = _era_line_width(rows, track_group.binarize(gray, track_group.PARAMS).T)
    n_touched = n_anchor = 0
    bpxs = []
    for r in rows:
        p = np.asarray(r["poly"], float)
        if len(p) < 2 or p[-1, 0] - p[0, 0] < CHORD_STRIDE:
            continue
        trusted = [tuple(p[0])]
        bridges = []
        n_row_anchor = 0
        for si in range(len(p) - 1):
            a, b = p[si], p[si + 1]
            if b[0] - a[0] <= CHORD_STRIDE:
                trusted.append(tuple(b))
                continue
            s0 = float(b[1] - a[1]) / (b[0] - a[0])
            for u, v in _chord_noink_runs(gray, a, b, lw, W, E):
                yu = float(a[1] + s0 * (u - a[0]))
                yv = float(a[1] + s0 * (v - a[0]))
                lp = _chord_walk_side(gray, u, yu, v, s0, +1, lw, W, E)
                rp = _chord_walk_side(gray, v, yv, u, s0, -1, lw, W, E)
                rp = rp[::-1]                                   # 转 x 升序
                if lp and rp and rp[0][0] - lp[-1][0] <= CHORD_STRIDE:
                    lp = [q for q in lp if q[0] < rp[0][0]]     # 有重叠以西側为准
                # 桥 = 两侧锚末端之间(或贴墨边)的残余;切线从各自已锚末端拟合
                A = lp[-1] if lp else (u, yu)
                B = rp[0] if rp else (v, yv)
                if B[0] - A[0] > CHORD_STRIDE:
                    mA = _chord_tangent(lp + [A], len(lp), s0) if lp else s0
                    mB = _chord_tangent([B] + rp, 0, s0) if rp else s0
                    fill = _chord_hermite_fill(A, B, mA, mB)
                    if fill:
                        bridges.append([int(A[0]), int(B[0])])
                else:
                    fill = []
                seg_pts = lp + fill + rp
                if not seg_pts:
                    continue
                n_row_anchor += len(lp) + len(rp)
                trusted.extend((float(x), float(y)) for x, y in seg_pts)
            trusted.append(tuple(b))
        new_poly = [[round(float(x), 1), round(float(y), 1)] for x, y in trusted]
        if not bridges and new_poly == r["poly"]:
            continue
        n_touched += 1
        n_anchor += n_row_anchor
        bpx = int(sum(bb[1] - bb[0] for bb in bridges))
        if bpx:
            bpxs.append(bpx)
            r["chord_bridge_segs"] = bridges
            r["chord_bridge_px"] = bpx
        r["chord_n_anchor"] = n_row_anchor
        r["poly"] = new_poly
        r["n_poly"] = len(r["poly"])
    msg = f"行线弦修复(项③):动笔 {n_touched}/{len(rows)} 行"
    if bpxs:
        msg += f",含曲率桥 {len(bpxs)} 行(桥长中位 {int(np.median(bpxs))}px、最长 {max(bpxs)}px,chord_bridge_segs 入档)"
    out["warnings"].append(msg)
    return n_touched, int(sum(bpxs))


# ---- 行线补全(项④,2026-10-05):磨损失迹/被降级的层界以 sub 为种子墨迹验证补全 ----
# 诊断(runs/tmp/补全标定_20261005.csv + 项④反例_20261005/ 14 张裁片):真漏线分两物种——
# A 描写区成链数值区磨损(1015 y8298,数值区墨只剩 stage4 噪声碎片);B 数值区墨其实还在但
# 被降级成 sub(1020 y12899:boundary_x 锚线下半张断到 x≈898 → cov_num 被算小;1020 y17286:
# I2 门禁对"三数同格"jumble 字符串静默跳过 → 漏报,走查反而锚出 frac0.717/run_w116 的真线)。
# 两物种同一处理:以 sub 的 y 为种子西向走查数值区(东向只补到邻行东端),预测 = 上下邻行
# 折线线性内插(邻行同曲率,内插相消,不发明形状),细墨锚定(era 同款容差),柱状带内强制桥;
# 验收只看种子以西新开辟段(数值区新证据),数字笔画喂锚靠连续锚程分辨(真线幸存墨是横向
# 长条 60~174px,笔画只有 10~40px)。
COMP_MARGIN = 20     # 种子 y 离上下邻行折线的最小间距 px(贴缘 = 边界重复/文字下划线,不补)
COMP_BANDMIN = 40    # 局部带高低于此不锚(邻行收敛处轨迹会贴上邻行墨,防骑邻行)
COMP_NBR = 3         # 东西走查目标取 ±NBR 行 x 端的中位(抗单行 era 西延/断头的偏置)
COMP_RUNW = 50       # 数值区连续锚程下限 px。实测分界(30 张 27 正/99 负,补全标定_20261005.csv):
                     # 真线幸存墨是横向长条——数值区西碎片单段 113~125px、巨带内真边界 66~116px;
                     # 文字负样本最高 40(数字笔画喂锚)。≥50 零误报。
COMP_FRACN = 0.15    # 数值区锚占比下限(防"孤段偶合":单段长但占比过低的不过)
COMP_RUNGAP = 3      # 连续锚程的隙容 px(≈lw):幸存墨内部小孔不劈断长条
COMP_ROWSEP = 25     # 锚点离上下邻行折线(按墨中心)的最小距离 px:数字顶/基线骑行者坐在
                     # 自己行的底界上,锚点离下方已有行 15~20px(1021/1556、1034/15462 裁片
                     # 实锤);真边界离邻行 ≥50px(1031/1033/1037/1017 实测)——分离守卫
COMP_WALL = 200      # 竖向粗墨连续超此宽 = 走出表外,该向止步


def complete_row_lines(stem, out, apply=True):
    """sub 种子 → 层界补全(项④)。apply=False 只量不改(阈值标定/回归用)。

    走查:预测 y(x) = 上下邻行折线在该 x 的线性内插(权重取种子在 x_ref 处的相对位置,
    全程不变——两邻行同曲率,内插把弯曲抵掉);每列 _era_ink_run 找 ±ERA_WIN 细墨,
    锚在行程中心(|yc−预测|≤ERA_DRIFT),竖向粗墨(列线/装订/框)整段跳过,柱状带内强制桥
    不锚,邻行收敛处(局部带高 <COMP_BANDMIN)不锚。数值区走查窗 = [x_w, bx)(bx=该 sub
    的描述列西界,满跨 sub 的西碎片也落窗内),另向东补到 ±COMP_NBR 邻行 x 端中位。
    验收双门只看数值区:连续锚程 ≥COMP_RUNW 且锚占比 ≥COMP_FRACN(真线幸存墨是横向
    长条,数字笔画短,连续性把笔画喂锚分出去;阈值实测见常量注释)。
    补出的行与普通行同构,complete_* 字段入档(锚/桥/带内 px、无锚桥段列表,渲染黄色);
    cov_num/cov_desc 改记走查实测锚占比(数值区/描述区),与链覆盖口径不同,见字段注释;
    原 sub 原样保留在 sub_rows(审计线)。
    返回(补全数, 尝试数);逐种子量测在 out["complete_stats"](apply=False 也写)。"""
    subs = out.get("sub_rows") or []
    rows = out.get("rows") or []
    if not subs or len(rows) < 2:
        return 0, 0
    W, E, _ = content_band(stem)
    if W is None or table_frame(stem) is None \
            or not (paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json").exists():
        # 无柱状带守卫(图案墨不可排除)或外框/列结构定稿缺失(1032 类,列几何不可信):
        # 补全整图跳过,交专项处理(与 extend_era_rows 的整图跳过同款判据)
        out["warnings"].append("行线补全(项④)整图跳过:无柱状带/外框/列结构定稿(图案墨、列几何不可排除)")
        return 0, 0
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    lw = _era_line_width(rows, track_group.binarize(gray, track_group.PARAMS).T)
    thick = ERA_THICK * lw
    ys_all = np.asarray([r["y_at_mid"] for r in rows], float)
    order = np.argsort(ys_all)
    stats, done = [], []
    for sub in sorted(subs, key=lambda r: r["y_at_mid"]):
        st = {"y": sub["y_at_mid"], "why": None}
        idx = int(np.searchsorted(ys_all[order], sub["y_at_mid"]))
        st["why"] = "无上邻行" if idx == 0 else ("无下邻行" if idx == len(rows) else None)
        if st["why"] is None:
            top, bot = rows[order[idx - 1]], rows[order[idx]]
            pt, bt = np.asarray(top["poly"], float), np.asarray(bot["poly"], float)
            sp = np.asarray(sub["poly"], float)
            x_ref = float(np.median(sp[:, 0]))
            y_ref = float(np.interp(x_ref, sp[:, 0], sp[:, 1]))
            ytt = float(_era_row_ys(pt, [x_ref])[0])
            ybt = float(_era_row_ys(bt, [x_ref])[0])
            st.update(band=round(ybt - ytt, 1))
            if ybt - ytt < 2 * COMP_MARGIN:
                st["why"] = "带过薄"
            elif y_ref - ytt < COMP_MARGIN or ybt - y_ref < COMP_MARGIN:
                st["why"] = "种子贴缘"
            elif not 0.0 < (y_ref - ytt) / (ybt - ytt) < 1.0:
                st["why"] = "种子出带"
            else:
                tt = (y_ref - ytt) / (ybt - ytt)
                # 走查目标:±COMP_NBR 邻行 x 端中位(单一邻行的 era 西延/断头不偏置目标)
                k0, k1 = max(0, idx - 1 - COMP_NBR), min(len(rows), idx + COMP_NBR)
                x_w = int(np.median([rows[j]["x"][0] for j in order[k0:k1]]))
                x_e = int(np.median([rows[j]["x"][1] for j in order[k0:k1]]))
                s0s = (sp[-1, 1] - sp[0, 1]) / max(sp[-1, 0] - sp[0, 0], 1e-6)

                def ypred(x, pt=pt, bt=bt, tt=tt):
                    return float(_era_row_ys(pt, [x])[0]) \
                        + tt * (float(_era_row_ys(bt, [x])[0]) - float(_era_row_ys(pt, [x])[0]))

                anchors, walked, band_px = [], 0, 0
                walked_n = 0                         # 数值区段[x_w,bx)单独记(验收只看它)
                bx = float(sub["boundary_x"])
                for sgn, xa, xb in ((1, int(sub["x"][1]) + 1, x_e),
                                    (-1, int(bx) - 1, int(x_w))):
                    x = xa
                    while (x <= xb) if sgn > 0 else (x >= xb):
                        y = ypred(x)
                        loc_band = float(_era_row_ys(bt, [x])[0]) - float(_era_row_ys(pt, [x])[0])
                        if _chord_in_band(W, E, y, x):
                            band_px += 1
                        elif loc_band < COMP_BANDMIN:
                            pass                   # 邻行收敛处不锚(防骑上邻行墨)
                        else:
                            r, yc = _era_ink_run(gray[:, x], y)
                            if 0 < r <= thick and abs(yc - y) <= ERA_DRIFT \
                                    and yc - float(_era_row_ys(pt, [x])[0]) >= COMP_ROWSEP \
                                    and float(_era_row_ys(bt, [x])[0]) - yc >= COMP_ROWSEP:
                                anchors.append((x, float(yc)))
                            elif r > thick:
                                x2 = x + sgn       # 竖向粗墨整段跳过
                                while ((x2 <= xb) if sgn > 0 else (x2 >= xb)) \
                                        and abs(x2 - x) <= COMP_WALL \
                                        and _era_ink_run(gray[:, x2], ypred(x2))[0] > thick:
                                    x2 += sgn
                                walked += abs(x2 - x)
                                x = x2 - sgn
                        walked += 1
                        if sgn < 0:
                            walked_n += 1
                        x += sgn
                # 连续锚程 = 真行线幸存墨(横向长条)与数字笔画(10~40px)的分辨尺;
                # 数值区 = [x_w, bx)(bx=描述列西界):满跨 sub 的西碎片(113~125px)也落在窗内
                axs = sorted(a[0] for a in anchors if a[0] < bx and a[0] >= x_w)

                def max_run():
                    best = cur = 0
                    prev = None
                    for x in axs:
                        cur = cur + 1 if prev is not None \
                            and x - prev <= 1 + COMP_RUNGAP else 1
                        best = max(best, cur)
                        prev = x
                    return best

                n_num = len(axs)
                st.update(walked=walked, walked_num=walked_n, band_px=band_px,
                          anchor=len(anchors), n_num=n_num,
                          frac_n=round(n_num / max(walked_n, 1), 3),
                          run_num=max_run())
                if st["run_num"] < COMP_RUNW or st["frac_n"] < COMP_FRACN:
                    st["why"] = "墨证据不足"
                else:
                    st["why"] = "ok"
                    done.append((sub, sp, sorted(anchors), walked, band_px,
                                 walked_n, x_w, x_e, s0s))
        stats.append(st)
    out["complete_stats"] = stats
    if not apply or not done:
        n = sum(1 for s in stats if s["why"] == "ok")
        return n, len(stats)

    # -- 组装折线:sub 原点 + 墨锚,近邻去重,无锚间隙 >CHORD_STRIDE 用 Hermite 桥(Fritsch–Carlson) --
    for sub, sp, anchors, walked, band_px, walked_n, x_w, x_e, s0s in done:
        bx = float(sub["boundary_x"])
        mx = {}
        for x, y in [(float(a), float(b)) for a, b in sp] + anchors:
            mx[int(round(x))] = y                 # 同 x 锚覆盖 sub 原点(墨行程中心更准)
        pts, last = [], None
        for x in sorted(mx):
            if last is None or x - last >= 2:     # 2px 内的密锚抽稀(≈0.5×lw,折线足够贴墨)
                pts.append((x, mx[x]))
                last = x
        allp, bridge = [], []
        for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            allp.append(a)
            if b[0] - a[0] > CHORD_STRIDE:
                mA = _chord_tangent(pts[:i + 1], i, s0s) if i else s0s
                mB = _chord_tangent(pts[i + 1:], 0, s0s) if i + 2 < len(pts) else s0s
                fill = _chord_hermite_fill(a, b, mA, mB)
                if fill:
                    bridge.append([int(a[0]), int(b[0])])
                    allp.extend(fill)
        allp.append(pts[-1])
        x_lo, x_hi = allp[0][0], allp[-1][0]
        rec = {"segment_ids": list(sub["segment_ids"]),
               "x": [round(x_lo), round(x_hi)],
               "poly": [[round(float(a), 1), round(float(b), 1)] for a, b in allp],
               "n_poly": len(allp),
               "y_at_mid": round(float(np.median([b for _, b in allp])), 1),
               "fit_res": 0.0, "span": round(x_hi - x_lo), "res90": 0.0, "n_split": 0,
               # cov_num/cov_desc 记走查实测锚占比(数值区=[x_w,bx)/描述区=其余),与链覆盖
               # cover() 口径不同:链覆盖量"成员段墨的 x 并集",这里量"预测轨迹踩到细墨的比例"
               "cov_num": round(sum(1 for x, _ in anchors
                                    if x < bx) / max(walked_n, 1), 3),
               "cov_desc": round(sum(1 for x, _ in anchors
                                     if x >= bx)
                                 / max(walked - walked_n, 1), 3),
               "boundary_x": sub["boundary_x"], "n_chains": 1, "step": 0.0,
               "slope": 0.0, "win": 0.0, "ptp": 0.0,
               "rise": round(max(b for _, b in allp) - min(b for _, b in allp), 1),
               "complete_from_sub": True, "complete_walked": walked,
               "complete_walked_num": walked_n,
               "complete_band_px": band_px, "complete_anchor": len(anchors),
               "complete_bridge_px": walked - band_px - len(anchors),
               "complete_num_anchor": sum(1 for a in anchors if a[0] < bx)}
        if bridge:
            rec["complete_bridge_segs"] = bridge
        rows.append(rec)
    rows.sort(key=lambda r: r["y_at_mid"])
    ok = [s for s in stats if s["why"] == "ok"]
    fr = [s["frac_n"] for s in ok]
    rw = [s["run_num"] for s in ok]
    bp = [s["walked"] - s["band_px"] - s["anchor"] for s in ok]
    out["warnings"].append(
        f"行线补全(项④):尝试 {len(stats)} 条 sub,补全 {len(ok)} 条"
        f"(数值区锚占比中位 {np.median(fr):.0%}、范围 {min(fr):.0%}~{max(fr):.0%};"
        f"数值区连续锚程中位 {int(np.median(rw))}px;桥 px 中位 {int(np.median(bp))},"
        f"complete_bridge_segs 入档);原 sub 保留在 sub_rows")
    return len(ok), len(stats)


def extend_era_rows(stem, out):
    """时代界行西延+曲率桥（项②收尾，行级后处理）：时代界行折线沿墨迹西行、真空段曲率桥、
    终点无条件接触左框（用户 2026-10-02 口径：线条必须和左边表格列线接触）。

    选行 = 时代行普查同款判据（窗 [L(y)+15, c0-25]、y±8 墨占比 ≥0.5 且 tot≥15）——就是
    诊断认出 205 行的那把尺，不新发现时代行（窄列图普查地板整图拒收，登记为限制）。
    两遍走：第一遍 _era_walk 严格墨迹西行（墨断 >ERA_GAP 止），同时喂曲率 profile；
    第二遍 _era_bridge_walk 从已收墨的西端（首墨真空行从链端）沿"外推+profile"预测轨迹
    走到左框，真空段桥接并逐段记入 era_bridge_segs/era_bridge_px（可审计、渲染时可区别
    显示），终点吸附稳健框线（era_d_frame=0）。桥上锚回的真墨点不是桥。
    普通行一律不动——rowspan 语义下时代列本来就没有行级横线，全表拉到框边=造线（约束2）。
    扩展点：墨点落在原图墨迹行程中心，桥点落在本图实测曲率轨迹上。
    无闭合外框/列结构定稿的图整图跳过（1032 框不可信，注册在案）。返回（接触数, 未接触数）。"""
    rows = out.get("rows") or []
    fr = table_frame(stem)
    fp = paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json"
    if fr is None or not rows or not fp.exists():
        out["warnings"].append("时代列西延跳过：无闭合外框或列结构定稿")
        return 0, 0
    cols = json.loads(fp.read_text(encoding="utf-8")).get("columns") or []
    if not cols:
        out["warnings"].append("时代列西延跳过：列结构定稿无列")
        return 0, 0
    c0 = float(cols[0]["x_at_mid"])          # 普查同款取 columns[0]，保持 205 行口径一致
    Lys, Lxs = _era_frame_left(fr)
    L_raw = np.array(sorted(np.asarray(fr[0], float).tolist()))
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    lw = _era_line_width(rows, track_group.binarize(gray, track_group.PARAMS).T)
    sel = []
    for r in rows:
        p = np.asarray(r["poly"], float)
        # -- 普查同款选行：窗 [L(y)+15, c0-25]，y±8 内 min<210 占比 ≥0.5 且 tot≥15 --
        x_hi = min(p[0, 0] - 1, c0 - 25)
        ok = tot = 0
        x = int(x_hi)
        while x > 100:
            y = float(_era_row_ys(p, [x])[0])
            Ly = float(np.interp(y, L_raw[:, 0], L_raw[:, 1]))
            if x < Ly + 15:
                break
            tot += 1
            if gray[max(int(y - 8), 0):int(y + 9), x].min() < 210:
                ok += 1
            x -= 1
        if tot < 15 or ok / tot < 0.5:
            continue
        # -- 第一遍：严格墨迹西行（连接门废除——首墨远的行由曲率桥补）--
        x_e = p[0, 0] - 2
        x_w = float(np.interp(float(_era_row_ys(p, [p[0, 0]])[0]), Lys, Lxs)) + 3
        pts, _ = _era_walk(gray, p, x_e, x_w, lw, Lys, Lxs)
        sel.append((r, p, x_e, pts))
    if not sel:
        return 0, 0
    # 补全行(项④)不喂曲率 profile:profile 保持与补全前一致,其余 era 行的桥逐字节不变
    # (回归纪律:未动笔行零改动);补全行自己若被选中,仍按同一 profile 西延
    prof = _era_profile([(p, pts) for r, p, _, pts in sel
                         if not r.get("complete_from_sub")])
    n_full = n_part = 0
    n_brig = 0
    bpxs = []
    for r, p, x_e, pts in sel:
        # -- 第二遍：曲率桥补接触；桥接段（无墨区）逐段入档 --
        x0 = (pts[-1][0] - 1) if pts else x_e
        bpts, segs, bpx = _era_bridge_walk(gray, p, x0, lw, Lys, Lxs, prof)
        allpts = pts + bpts if pts else bpts
        ext = allpts[::ERA_STEP]
        if ext[-1] != allpts[-1]:
            ext.append(allpts[-1])
        r["poly"] = [[round(float(a), 1), round(float(b), 1)] for a, b in ext[::-1]] + r["poly"]
        r["n_poly"] = len(r["poly"])
        r["x"][0] = round(allpts[-1][0])
        d_frame = int(round(allpts[-1][0] - np.interp(allpts[-1][1], Lys, Lxs)))
        r["era"] = "full"
        r["era_d_frame"] = d_frame
        r["era_n_ext"] = len(ext)
        if segs:
            r["era_bridge_px"] = int(bpx)
            r["era_bridge_segs"] = segs
            n_brig += 1
            bpxs.append(int(bpx))
        if d_frame <= 2:
            n_full += 1
        else:
            n_part += 1
    msg = f"时代列西延+曲率桥：{n_full} 行接触左框（era_d_frame≤2）"
    if n_part:
        msg += f"、{n_part} 行未吸附（异常，待查）"
    if n_brig:
        msg += (f"；{n_brig} 行含桥接段（桥长中位 {int(np.median(bpxs))}px、最长 {max(bpxs)}px，"
                f"era_bridge_segs 入档，渲染黄色）")
    out["warnings"].append(msg)
    return n_full, n_part


def determine_rows(stem: str):
    ch = load_chains(stem)
    if ch is None:
        return {"image": stem, "table_x": [0, 0], "n_input_segments": 0, "n_chains": 0,
                "n_band_segments": 0, "band_src": None,
                "n_lines": 0, "row_cov": ROW_COV, "row_h": 0.0, "step_tol": LINE_TOL,
                "slope_med": 0.0, "skew_gate": SKEW, "skew_band": 0.0, "split_lim": 0.0,
                "n_chains_split": 0, "n_pieces": 0,
                "n_lines_offgrid": 0, "off_grid": [],
                "rows": [], "sub_rows": [], "others_n": 0, "warnings": ["无长横链"]}
    out = assemble(ch)
    out["n_chord_touched"], out["chord_bridge_px_total"] = refine_row_chords(stem, out)
    out["n_complete"], out["n_complete_try"] = complete_row_lines(stem, out)
    out["n_era_full"], out["n_era_partial"] = extend_era_rows(stem, out)
    with open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
              "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def x_at_mid(g):
    pts = g["pts"]
    return float(pts[np.searchsorted(pts[:, 0], (pts[0, 0] + pts[-1, 0]) / 2), 1])


def _dir_down(p_end, p_adj):
    v = np.asarray(p_adj, float) - np.asarray(p_end, float)
    if v[1] < 0:
        v = -v
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-6 else np.array([0.0, 1.0])


def _draw_poly(viz, pts, color, w):
    """折线逐笔画出。跨带的口子照画：行线物理上连续穿带（原图墨迹如此），画断口反而像行遗漏；
    口子两端 ≤204px、弓高 ≤2px（1015 实测 3878 采样中位偏差 0.7px），直连弦与原线不可分。
    折线顶点无带内点（柱状带内段已预滤、水文带内点已被 band_split_item 切掉），无"造线"风险。"""
    pts = np.asarray(pts, np.int32)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        cv2.line(viz, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), color, w, cv2.LINE_AA)


def draw_rows(stem):
    out = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                         encoding="utf-8"))
    viz = cv2.imread(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}.png"))
    if viz is None:
        # track 归组产物已退役删除:底图退到阶段4 纯线条可视化图;再缺则跳过画图
        # (行判定.json 数据已在 determine_rows 落账,可视化不熔断全链)
        viz = cv2.imread(str(paths.CANDIDATE_PURE_DIR / f"{stem}.png"))
    if viz is None:
        print(f"{stem}: 无可用底图,跳过行判定可视化(数据已落账)")
        return
    for r, color, w in ([(r, (0, 0, 255), 5) for r in out["rows"]] +
                        [(r, (0, 140, 255), 3) for r in out["sub_rows"]]):
        _draw_poly(viz, r["poly"], color, w)
    # 紫：门禁2 判走的线（拼成线之后逐窗斜率中位仍离参照 >SKEW，参照=上下 SKEW_BAND 行高的邻居）。
    # 画出来才看得清"剔的是不是真歪"，名单在 JSON 的 off_grid 里，交阶段5 复核拼链用。
    for r in out.get("off_grid", []):
        _draw_poly(viz, r["poly"], (255, 0, 255), 3)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.png"), viz,
                [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2),
                      interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定_预览.jpg"),
                half, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    # 参既收全名也收 4 位编号：runs/tmp 下的标尺、对比片一律按编号点名，别在这绊一次
    stems = [f"钻孔柱状图{a}" if a.isdigit() else a for a in sys.argv[1:]] or \
            sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    for stem in stems:
        o = determine_rows(stem)
        draw_rows(stem)
        print(f"{stem}: 段 {o['n_input_segments']}（柱状带内另剔 {o['n_band_segments']}）→ 链 {o['n_chains']}，"
              f"主行线 {len(o['rows'])}，子行线 {len(o['sub_rows'])}，其余 {o['others_n']}，"
              f"走偏剔除 {o['n_lines_offgrid']} 条，切开 {o['n_chains_split']} 条链→{o['n_pieces']} 段"
              f"｜行高 {o['row_h']:.0f}px 容差 {o['step_tol']:.0f} 中位斜率 {o['slope_med']:.4f}"
              f" 斜率闸 {o['skew_gate']:.0%} 参照带 {o['skew_band']:.0f}px"
              f" 切分闸 {o['split_lim']:.0f}px {o['warnings']}")


if __name__ == "__main__":
    main()
