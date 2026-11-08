# 钻孔柱状图表格还原与内容识别

30 张扫描的手写地质钻孔柱状图(33MP,倾斜/弯曲/断线/模糊/大量 rowspan)
→ 还原真实表格结构(行、列、单元格及坐标)→ 识别内容 → 输出结构化长表。
**收敛打分 conv=1.0000(满分)**,内容识别经多源交叉验证+逐格判读+用户终裁三级把关。

**先读哪份**:约束看 `AGENTS.md`;终态与历史看 `STATUS.md`;
废止路线与判读纪律看 `EXPERIENCE.md`;实验台账与 `runs/` 目录归属看 `EXPERIMENT.md`。

## 管线

```
原始扫描件 data/raw_images (30 张, 不公开)
  → 二值化 multi_scale_sauvola → 细化 thinning → 骨架 skeleton
  → 表格线候选/聚簇 (src/table, 列线聚簇+段桥接+墨迹验证外延)
  → 行判定/表头映射/还原 (行线以折线表征 rows[i].poly, 不拟合直线)
  → 整合表 finalize_tables (合并单元格+语义校正+合理性门禁)
  → 规则引擎 apply_rules (src/handwriting, 重读收敛/佐证采纳/判读定谳等 20+ 规则)
  → 多源交叉验证 (RapidOCR×Agnes×行带读×列读 + 几何独立轴, 墨迹 y 实测)
  → 终版交付 outputs/Excel交付_终版_20261109 (30 张 xlsx, 差异字级标红)
```

## 复现

```bash
pip install -r requirements.txt        # Python 3.12,与现成 SWIG pyd 匹配
bash .auto/measure.sh                  # 重建→内置门禁→conv/align 打分(主指标 conv)
python -m pytest -q                    # 281 passed
```

- 路径一律经 `src/core/paths.py`(项目根由文件位置推导,可整体搬移);新增目录先在此登记,禁硬编码。
- 阶段 1~5 并行统一走 `src/core/batch.py` 的 `run_batch`(取半核,失败不中断)。
- 规则引擎每次从种子表(冻结基线)全量重置重建候选区——候选区是规则的纯函数。
- 判读定谳账本在 `runs/autoresearch_align/多源定级_20261106/判读_采纳_*.json`
  (997 条:tag/种子现值/新值/判读现值链,守卫=寻址自校验)。

## 结果

| 指标 | 值 |
| --- | --- |
| conv 收敛打分(主指标,零参考) | **1.0000**(3610 格,判读定谳+双族印证) |
| align 参考对照一致率(仅 log) | 0.7599 |
| 终版 vs 用户参考包 字级对比一致率 | 19171/25884 = 0.7407 |
| 交付审计(audit_deliverable) | 30 表,哨兵 0,退出码 0 |

内容识别三级把关:**多源引擎交叉验证**(4 读源+几何独立轴)→ **逐格弱档判读**
(助手视觉判读,用户授权流程,997 格定谳)→ **用户终裁**(验收网页 28 格,含 4 格
推翻助手判读的人工亲核)。参考表仅作对照不作真值,取值一律出自原图读数。

## 目录

```
src/core|binarize|thinning|skeleton|table|excel|tools   管线各段与工具
src/vendor                已验证的本机预编译运行时
src/third_party           skeleton-tracing 上游源码(保持干净)
tests/                    281 合成用例(冒烟字节级复现+门禁反放水六错例)
.auto/                    measure.sh 打分链 + 实验账本 log.jsonl
archive/                  历史脚本档案(runs_tmp_scripts_20261109)+ 旧文档(docs_20260923)
reports/                  设计与实验报告
memory-bank/              门禁账本(gate_ledger)
data/                     原始扫描件/参考表/结构中间产物(不入 Git,见下)
outputs/                  交付包(不入 Git,见下)
runs/                     运行期产物,不入 Git;归属与可删性见 EXPERIMENT.md §3
rollback/                 失败实验与安全归档,不入 Git;不得作为输入或运行
```

## 数据说明(为什么仓库里没有数据)

**本仓库只含代码与文档。** 原始扫描件(30 张煤矿地质钻探柱状图)、用户参考表、
交付 Excel、运行期产物均为业务数据,出于隐私与体积原因不入库(`.gitignore` 排除,
git 历史自 2026-11-09 收官重置起不含任何数据)。代码可在自备数据上复现全链;
目录约定、产物可删性见 `EXPERIMENT.md`。

## `src/excel/` 特例

这些脚本操作**桌面外部交付文件**(路径见 `paths.py` 的 `EXTERNAL_DESKTOP`),运行前先确认文件存在:
`qc_independent.py`/`final_audit.py`/`merge_gap_report.py` 只读质检,`fill_and_pack.py` 套模板重合并,
`reconstruct_all.py` 按区域层序重建地层块。
