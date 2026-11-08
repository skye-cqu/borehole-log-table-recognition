# src/handwriting — 手写长图内容层值修正引擎(可复用)

定位:表格结构(行列/切格)已由上游定稿后,对单元格**取值**做证据驱动的规则修正。
不碰图像、不碰结构、不调 OCR——读数冻结在整理表 xlsx 里。

## 数据流(吃什么 → 产出 → 给谁用)

```
seed/*.xlsx (定稿整合表快照,冻结)
   │  apply_rules.py:重置 candidate←seed → 按 rules.RULES 逐格修正 → _manifest.json + _账目.json
   ▼
candidate/*.xlsx ──► src/tools/align_score.py(对标打分,METRIC align=…)
                └──► verify_candidate.py(结构无损+哨兵+数值类型门禁)
```

- `engine.py` 通用核心:`Rule(name, roles, fn, note)`,`fn(v, ctx)->新值|None`,纯函数,只改值不增删行列。
- `rules.py` 本库实例:角色解析(复用 finalize_tables 表头名解析)+ 规则登记处 `RULES` + 数值角色名单。
- `normalizers.py` 通用规范化:`norm_text`(全角/°/空白,与 compare_ref 同口径)、`parse_num`。
- `apply_rules.py` 执行器:候选区全量重置重建,candidate 是规则的纯函数,无残留状态。
- `verify_candidate.py` 门禁:checks.sh 的执行器,退出码 0/1。

## 换一套手写长图怎么接

1. 整理表 xlsx 放入 seed 目录(第一行是表头,可被角色解析器识别);
2. `rules.py`:换 `resolve_roles`(同构的表头→角色映射)与 `NUMERIC_ROLES`;
3. 按本项目误读模式登记规则——规则来源只能是:像素核验/裁片证据、多读一致、数字自洽
   (如 真厚=层厚×cos倾角),以及参考对照门(2026-11-06 用户口径:参考仅作对照,
   跨引擎一致可作辅助验证;**被采文本必须出自图上引擎读数**)。
   **禁止抄"另一套识别结果"**(那是度量,不是真值)。

## 纪律

- 一次实验一条聚焦规则;泛化(全库模式匹配),不针对单图特判;
- 账目(_账目.json)逐格记 旧→新+规则名,可回溯、可回滚(candidate 随时可由 seed 重建);
- 用户已裁决值不可回退;`suspect`/结构性空格(rowspan)不填,除非有逐格证据定性。

## 验证

- 合成用例:`python -m pytest tests/test_handwriting_engine.py`(14 条,全合成数据,
  覆盖引擎账目/幂等/rowspan 禁写、格式三则、_decide 四仲裁路径、desc 双引擎收敛);
- 门禁:每次候选重建跑 `verify_candidate.py`(文件集/维度/哨兵/数值可析/manifest 一致);
- 对标:`src/tools/align_score.py`(只读,与 compare_ref 同参同判)。
