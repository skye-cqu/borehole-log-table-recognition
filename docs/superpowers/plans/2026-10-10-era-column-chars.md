# 时代列整字裁剪:验收门禁先行 + 弯曲感知裁剪器(TDD 小步)

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:executing-plans 在本会话内逐任务执行(每任务:先写失败测试→看它失败→最小实现→看它通过→提交)。步骤用 `- [ ]` 勾选跟踪。

**Goal:** 时代列弃"按行切格"改"整字裁剪":先落程序化验收门禁(G1–G4)并在当前交付表上出基线,再实现弯曲感知的整字裁剪器,5 张试点图过门禁。

**Architecture:** 裁剪器消费既有定稿数据(sep_pts 列界折线 + 行判定 poly),列界逐行插值、行线逐列插值,全部走曲线、零直线假设;字块=剔行线窄带后的墨迹投影游程;OCR 裁片回原图取原始像素(线穿字不删)。门禁是独立脚本,只读裁剪产物+原图+json 重算收支,不 import 裁剪器内部(判分/修复分离)。

**Tech Stack:** pytest、numpy/cv2、RapidOCR(依赖注入可换 stub)。复用:`strip_band`(rect_struct.py:213,折线带掩膜)、`runs_of`(rect_struct.py:451,游程)、`row_y`(track_rows.py:854)、`_crop_cell`(reconstruct_excel.py:43)、`binarize`(track_group.py:92)。分支:stage-rows-gates(现有工作分支)。范围:**不含** merge_cells 写出、不含 30 张全量、不含视觉 LLM 第二引擎(下一步)。

**前置体检(用户要求"上游没问题才动")**:`preflight()` 先于实跑:PF1 列界折线对数据区 y 覆盖率≥99%、PF2 行折线伸入时代带的比例、PF3 带内行序单调(≥8px 间距)、PF4 顶部表头串头墨。有 FAIL → 停下先报上游问题,不带病裁剪。已登记缺陷(3 条时代西延未接触行等)只登记不阻塞。

## 文件结构

- 新建 `src/table/era_chars.py`:裁剪器+前置体检。公开:`parse_era_name(s)`、`split_bands(chars)`、`char_boxes(band, ys)`、`era_strip(gray, left, right, rows)`、`preflight_checks(hm, rd)`、`preflight(stem)`、`extract_from_arrays(...)`、`extract(stem, ocr_fn=None)`(ocr_fn 注入,默认 RapidOCR)。
- 新建 `src/tools/audit_era_column.py`:门禁。`check_ink_accounting(...)`、`check_box_heights(...)`、`check_bands_order(...)`、`check_cross_charts(...)`(全部阈值参数化),CLI:`python src/tools/audit_era_column.py [era_chars输出目录 | xlsx目录] [--strict]`,CSV/JSON 落 `runs/tmp/`,违反退出 1(审计惯例同 audit_invariants)。
- 新建 `tests/test_era_chars.py`、`tests/test_audit_era_column.py`(沿用 tests/ 约定:手动 sys.path、中文用例名、numpy 合成夹具)。
- 修改 `src/core/paths.py`:+`ERA_CHAR_DIR = RUNS_DIR / "era_chars_20261010"`。
- 产物:`ERA_CHAR_DIR/{stem}/`(整字裁片 PNG、`era_chars.json`、`montage.png`);`runs/tmp/时代列前置体检_20261010.csv`、`runs/tmp/时代列门禁基线_20261010.{csv,json}`、`runs/tmp/时代列门禁_20261010.{csv,json}`。

## 任务清单

### Task 1: 登记与骨架
- [ ] paths.py 加 ERA_CHAR_DIR;era_chars.py 建 docstring(判据与"行线位置来自行判定定稿,非阈值判定")+ 常量 LINE_BAND_PAD=2 / MERGE_GAP=12 / MIN_CHAR_H=15 / MAX_CHAR_H=260 / ENDERS="系群组段阶" / QUAL="上中下一二三四五"
- [ ] 提交 `时代列: 登记era_chars产物目录与模块骨架`

### Task 2: 文法解析 + 名带分组(G2 核心,TDD)
- [ ] test_parse_era_name:第四系/龙潭组上段/茅口组=valid;上段=suspect(组名丢失);龙潭组上段茅口组=suspect(未分带);酒/三八/龙2组/空=invalid
- [ ] 看失败 → 实现 `parse_era_name(s)`:invalid=空/len<2/末字∉ENDERS/含非CJK;suspect=首字∈QUAL 或内部存在可断边界;否则 valid
- [ ] test_split_bands:11 字序列 → ["第四系","龙潭组上段","茅口组"];断名=末字∈ENDERS 且非(组+下一字∈QUAL)
- [ ] 看失败 → 实现 → 通过;提交 `时代列: 命名文法与名带分组(先测后码)`

### Task 3: 弯曲条带 + 剔行线 + 字块检测(TDD,合成图)
- [ ] test_strip_curved_and_line_prior:200×600 灰图,列界斜率±0.05,行折线穿过字B中心;断言 boxes==2(穿线字=一整块)、字A高度完整
- [ ] 看失败 → 实现 `era_strip`(strip_band 掩膜 + 行折线逐列 row_y ±(LINE_BAND_PAD+2) 置 False)、`char_boxes`(逐y墨计数>2 → runs_of → ≤MERGE_GAP 缝合 → 高度过滤)
- [ ] 补 test_strip_边缘截断不外推;提交 `时代列: 弯曲条带掩膜+行线窄带先验+整字块检测(合成图全绿)`

### Task 4: 前置体检 preflight(TDD,合成 json)
- [ ] test_preflight_pf1_pf3:合成 hm/rd → PF1≥0.99 ok;左界截断 → not ok
- [ ] 实现 preflight_checks(PF1 覆盖率/PF2 行线入带比例/PF3 行序≥8px/PF4 顶部串头)+ preflight(stem) 读盘包装 + CLI(--preflight,CSV 落 runs/tmp,FAIL exit 1)
- [ ] 5 张试点实跑,**有 FAIL 停下向用户报上游问题**;提交 `时代列: 前置体检PF1-PF4`

### Task 5: extract() 组装 + 产物 JSON(TDD,stub OCR)
- [ ] test_extract_schema_with_stub_ocr:注入 ocr_fn,断言 out 键 {strip_y0,strip_y1,chars,bands,preflight}、bands[0].name=="第四系"
- [ ] 实现 extract_from_arrays(era_strip→char_boxes→_crop_cell 回原图→ocr_fn→split_bands→parse_era_name)+ extract(stem) 读盘包装(JSON/裁片/montage 落 ERA_CHAR_DIR)
- [ ] 提交 `时代列: 整字裁剪组装(OCR注入/名带/裁片归档)`

### Task 6: 门禁 G1 收支 + G3 区间(TDD)
- [ ] test_ink_accounting_and_order:收支=总墨/线带墨/字块墨/残墨/残墨率(线带墨单独立账);check_bands_order 抓乱序/区间重叠
- [ ] 实现(先例 column_line_follow.py:845 收支结构);提交 `时代列: 门禁G1墨迹收支+G3名带区间(阈值参数化)`

### Task 7: 门禁 CLI + G4 + 当前B目录基线
- [ ] check_cross_charts(两两 Levenshtein,valid 名替换对列字级差异;test_cross_charts_substitution 含 潭/酒)
- [ ] CLI:era_chars 目录=G1–G4;xlsx 目录(基线)=30 张第 0 列碎片跑 G2/G3/G4;输出 runs/tmp;--strict 退出码;阈值常量 None 待 T8 回填
- [ ] 跑基线(当前 B 目录),valid率=标靶;提交 `时代列: 门禁CLI+当前交付表基线(G2/G3/G4)`

### Task 8: 试点实跑 + 门禁闭环 + 收尾
- [ ] 回填阈值(试点 G1 实测,门限设实测分布谷值,注释=推导链)
- [ ] 5 图 extract → audit --strict 全绿;对照基线:酒/山/画 是否被 G2/G4 拦截
- [ ] 助手视觉判读(弱档)montage 自检;裁片+报告交用户核验(约束7/10)
- [ ] STATUS.md 增补(基线 vs 试点、阈值推导链、遗留:G5/merge_cells/30 张)
- [ ] 提交 `交付(5张试点): 时代列整字裁剪过门禁G1-G4,基线对照入档`;不推送,合并 main 待用户
