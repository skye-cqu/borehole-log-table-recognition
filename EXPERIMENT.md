# EXPERIMENT.md — 实验台账索引

逐条尝试的假设/方法/数字/结论在 `memory-bank/gate_ledger.md`(门禁分支强制登记,活文件,
M#→T#→A# 编号)。本文件只做索引:哪个实验留下哪个目录、结论是什么、还能不能删。

## 1. 里程碑状态(M0~M5,详见 gate_ledger)

| 里程碑 | 内容 | 状态 |
| --- | --- | --- |
| M0 | 开源退化/渲染调研 | ✅ Augraphy 复用范围定案,版式层自研 |
| M1 | 合成器 v1 | ✅ 渲染自检全绿、seed 字节级复现、8.9 s/张 |
| M2 | 判分器+记分卡+串联胶水 | 🔄 判定2 通路建成,4 seed 首批真管线记分卡;M2b-2b 阻塞于用户 b′ 裁决 |
| M3 | 首里程碑人工校准 | 未开始(需用户) |
| M4 | 日常自动跑分 | 未开始 |
| M5 | 内容层 v3 数字互证 | 🔄 互证关系实测成立(真厚=层厚×cos 87% ≤0.02m;行内层厚 90.8%),置信度分级未做 |

## 2. PROVEN-DEAD 汇总(禁止重试,除非有新证据并在 gate_ledger 注记)

- Augraphy `BleedThrough` 用于 68.6 MP 门禁批量路径(6 种子 OOM,单进程峰值 3.02 GB)→ 透印改自研。
- Augraphy `LightingGradient` 用于 68.6 MP 门禁路径(20 GB 分配失败)→ 灰度不均改自研 OpenCV 梯度。
- 选项 a"纯回溯修复使重跑=核验定稿"(M2.T3):6a 出处链断裂,写产物的代码版与判定输入均已丢失。
- EasyOCR 作第三 OCR 引擎:中文手写精度不达标。
- 分箱中位重采样 / 固定 X 分组 / A2 大容差桥接 / recall-precision 当结构验收:见 `EXPERIENCE.md` §1。
- 数值角色"参考对照门"(autoresearch run12,2026-11-06):物理门合取后 0 增量(40 格全被批次2 算术门收割);
  参考门单独用会误采 118 个行错位值——参考门只对无物理门的角色(desc)有增量。
- rowspan 展开(autoresearch run3,2026-11-05):写入 4990 格 align 0.7215→0.5731 崩盘,牺牲保真。
- 倾角重读采纳(autoresearch run6,2026-11-05):邻带笔画污染+小角度 cos 门退化,无独立第三证据源不重试。
- C类三方分歧整池采纳(autoresearch run16 试点,2026-11-06):25 格弱档判读=我方对 10/参考对 8/
  双方皆偏 6/字形变体 1,混合池无系统偏向——整池采任何一方都注错 ~1/3,须逐格人审。
- "读=参考未收割漏网"可自动化(autoresearch run19,2026-11-06):diff 池中读=参考共 32 格,
  全量值逐格归因全为守卫正确拒采(读⊂seed 截断 17+短读 <5 字 15)——佐证/复读/填充三规则
  收割完全,零自动化缺口,0.7322 即现证据标准可达上限(run20 repeat:3 三跑全同封账)。

## 3. `runs/` 目录归属

| 目录 | 大小 | 来源实验 | 处置 |
| --- | --- | --- | --- |
| `table_reconstruct/` | 20 G | 阶段6 现行工作区(定稿叠加、读数、待核清单、还原表、视觉核验台账) | **保留**,JSON/台账是交付输入 |
| `autoresearch_align/` | 小 | 内容层规则引擎会话(2026-11-05/06,align 0.7180→0.7322,run1–20;seed/candidate/证据 JSON/账本/待裁清单/试点裁片包/C类全池分层) | **保留**,candidate 可由 seed+RULES 重建,证据 JSON 只增不改;已并入 main(ad67c3b) |
| `验收包/` | 3.7 G | 5d~5h 用户核验包(外框/闭合/清洗预览/行线) | 保留,用户核验凭据 |
| `synthetic_gate/` | 5.5 G | M1/M2 合成图与记分卡 | 保留种子基线,重生成图可删 |
| `阶段巡检包_20260923/` | 0(全硬链接) | 全阶段产物巡检包(`src/tools/stage_audit_pack.py`) | 可随时删,重跑即回 |
| `复核直览/` | 533 M | 低置信格高分辨率复核页(`build_recheck_pages.py`) | 可删,判读台账已另存 |
| `verify_content/` | 小 | M5 深度-层厚互证报告 | 保留 JSON |
| `stage5_track_grouping/` | 3.4 G | Track 归组实验(定案,已被 6a 定稿取代) | 退役,可删 |
| `stage04_role_recovery_v2/` | 2.2 G | 阶段4 角色回收 R1~R4 系列(结论进 reports) | 退役,可删 |
| `stage5_line_follow/` | 789 M | 沿线追踪首版(被 track_grouping 取代) | 退役,可删 |
| `stage04_soft_contour_experiment/` | 452 M | 软轮廓/显著度实验(未采纳) | 退役,可删 |
| `1035_visual_audit/` | 380 M | 1035 漏线逐层核查 | 退役,可删 |
| `stage5_segment_plan/`、`stage5_diag*`、`stage5_route_feasibility/`、`stage04_missing_line_layer_audit/` | <200 M | 段拼接诊断、路线可行性 | 退役,可删 |
| `mineru_*` | <250 M | MinerU 对照识别(未进主线) | 退役,可删 |
| `stage5_top_border_agnes/` | 49 M | 顶框 Agnes 旁证 | 退役,可删 |
| `tmp/` | 102 M | 一次性裁片与日志 | 可删 |

删除前提:重放验证证明可再生,或用户认损。去重已由 `src/tools/dedupe.py` 完成(65→53 G,零删除)。
已实测的再生凭据:阶段1 重跑逐字节一致;巡检包删后重建文件数一致(可删)。
`table_reconstruct/`、`验收包/` **不可删**——`gate_ledger` M2.T2/M2.T3 证明 6a 起重跑不出一模一样的
核验产物(写产物的代码版与核验期人工修正输入都已丢失),这两处的现存产物是唯一实体。

## 4. `reports/` 索引

| 文件 | 一句话结论 |
| --- | --- |
| `设计_合成量化验收门禁.md` | 验收语义唯一来源,改设计先改它 |
| `计划_合成门禁M*/….md` | M1/M2a/M2b-1/M2b-2a 实施计划 |
| `阶段04_R1~R4_*.md`、`阶段04_*调研/核查/批处理*.md`(21 篇) | 阶段4 角色判定实验全序列;终局=阶段4 输出经用户核验为正确基线 |
| `阶段04_失败方法与经验清单.md`、`阶段04_当前状态.md` | 废止路线原始记录 |
| `阶段5_列线识别_oracle*.md`、`阶段5_段拼接_*.md`(4 篇) | oracle 上界诊断:瓶颈在线跟随判据,不在数据源 |
| `项目清理与归档报告.md` | 2026-08 归档轮次记录 |

## 5. 活文件与归档

- 活:`memory-bank/gate_ledger.md`、`STATUS.md`、`EXPERIENCE.md`、本文件、`AGENTS.md`。
- 归档(2026-09-23 文档归位):`archive/docs_20260923/` 内的 `activeContext.md`、`progress.md`、
  `decisions.md`、`lessons.md`、`stage5_user_principles_checklist.md`、`阶段4-5技术报告.md`、`清理方案.md`。
  其有效内容已并入上述四份文件,原文仅作历史留档,不再更新。

## 6. 收官清理与归档(2026-11-09,终态)

- **删除(可重跑中间产物,~1.5GB)**:判读裁片包 8 个(`多源定级_20261106/同族判读包_r9` 等,
  可由 run5_pkg_v2 等脚本+原图重跑)、`Agnes全列复读_20261028`(可 reread.py 重跑)、
  `era_chars_20261010`、`table_reconstruct` 内 R2/R3 历史迭代 json、runs/tmp 大件。
- **保留(runs 现存,均为运行时依赖或账本)**:`autoresearch_align/seed`(终值基线)、
  `candidate`、根 json(multisource_reads/rowstrip_reads/agnes_resweep/colreads/
  reread_desc/reread_num/pack_bridge/row_ivs——converge_score/rules 加载)、
  `多源定级_20261106/*.json`(判读三表 997 条等账本)、`人工裁定_20261109`(验收页证据)、
  `table_reconstruct` 终版结构 json(红字重出/行构重放依赖)、
  `table_整合_全量_20261011`(校正账)、`table_reconstruct_重出_20261023`。
- **移动**:用户参考表 `runs/参考表_1015-1044_20261011` → `data/`(paths.py 已同步)。
- **归档**:`runs/tmp` 601 个脚本 → `archive/runs_tmp_scripts_20261109/`。
- **分支**:autoresearch-align 无独有提交(main 全含),已删;本地仅 main。
- **git**:旧历史含 4.72GiB 数据,以 bundle 留档 `rollback/full-history_20261109.bundle`
  + `archive/full-history` 分支;public 仓库从 orphan 干净根重建(代码+文档,数据不入)。
