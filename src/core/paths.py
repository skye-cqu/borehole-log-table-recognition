# -*- coding: utf-8 -*-
"""项目路径集中配置。

所有脚本一律通过本模块获取路径，禁止在脚本中硬编码绝对路径；
新增数据目录或外部输入时，先在此处登记。
项目根目录由本文件位置推导（parents[2]），整体搬移目录不影响运行。
"""
from pathlib import Path
from types import SimpleNamespace

# ---- 项目根目录 ----
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---- 数据目录（data/，各阶段输出，中文名与既有产物保持一致）----
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw_images"                    # 阶段0：原始扫描件（JPG，全程只读）
BINARIZED_DIR = DATA_DIR / "二值处理"                  # 阶段1：多尺度 Sauvola 二值化
THINNING_DIR = DATA_DIR / "thinning"                  # 阶段2：Zhang-Suen 细化
THINNING_TEST_DIR = THINNING_DIR / "test"             # 细化算法对比测试输出
SKELETON_DIR = DATA_DIR / "LingDong-skeleton-tracing处理"  # 阶段3：骨架追踪
SKELETON_COORD_DIR = SKELETON_DIR / "坐标数据"
SKELETON_VIZ_DIR = SKELETON_DIR / "可视化图"

# 阶段4：表格线候选识别（每图五件套）
CANDIDATE_DIR = DATA_DIR / "表格线候选识别处理"
CANDIDATE_ORIG_DIR = CANDIDATE_DIR / "原图"
CANDIDATE_OVERLAY_DIR = CANDIDATE_DIR / "叠加可视化图"
CANDIDATE_PURE_DIR = CANDIDATE_DIR / "纯线条可视化图"
CANDIDATE_COORD_DIR = CANDIDATE_DIR / "坐标数据"
CANDIDATE_STATS_DIR = CANDIDATE_DIR / "特征统计"

# 阶段5a：列线清洗与结构识别
COLUMN_CLEAN_DIR = DATA_DIR / "列线清洗与结构识别"
COLUMN_CLEAN_ORIG_DIR = COLUMN_CLEAN_DIR / "原图"
COLUMN_CLEAN_OVERLAY_DIR = COLUMN_CLEAN_DIR / "叠加可视化图"
COLUMN_CLEAN_PURE_DIR = COLUMN_CLEAN_DIR / "纯结构图"
COLUMN_CLEAN_COORD_DIR = COLUMN_CLEAN_DIR / "坐标数据"

# 阶段5b：纵向主框架恢复（与 5a 并列的另一种列结构识别方案）
COLUMN_RECOVER_DIR = DATA_DIR / "纵向主框架恢复"
COLUMN_RECOVER_ORIG_DIR = COLUMN_RECOVER_DIR / "原图"
COLUMN_RECOVER_OVERLAY_DIR = COLUMN_RECOVER_DIR / "叠加可视化图"
COLUMN_RECOVER_PURE_DIR = COLUMN_RECOVER_DIR / "纯线条可视化图"
COLUMN_RECOVER_COORD_DIR = COLUMN_RECOVER_DIR / "坐标数据"
COLUMN_RECOVER_STATS_DIR = COLUMN_RECOVER_DIR / "特征统计"

# 阶段4（主分隔线拟合）：column_fit，纵向+横向主分隔线重建（含 noise 再召回、折线轨迹）
COLUMN_FIT_DIR = DATA_DIR / "主分隔线拟合"
COLUMN_FIT_ORIG_DIR = COLUMN_FIT_DIR / "原图"
COLUMN_FIT_OVERLAY_DIR = COLUMN_FIT_DIR / "叠加可视化图"
COLUMN_FIT_PURE_DIR = COLUMN_FIT_DIR / "纯线条可视化图"
COLUMN_FIT_COORD_DIR = COLUMN_FIT_DIR / "坐标数据"
COLUMN_FIT_STATS_DIR = COLUMN_FIT_DIR / "特征统计"

# 阶段4（纵向主分隔线重建原型）：按固定 y 分层 + 多路径 Non-crossing 联合恢复（已废弃，见 column_fit.py）
VERTICAL_SEP_DIR = DATA_DIR / "纵向主分隔线重建"
VERTICAL_SEP_OVERLAY_DIR = VERTICAL_SEP_DIR / "叠加可视化图"
VERTICAL_SEP_PURE_DIR = VERTICAL_SEP_DIR / "纯线条可视化图"
VERTICAL_SEP_COORD_DIR = VERTICAL_SEP_DIR / "坐标数据"
VERTICAL_SEP_STATS_DIR = VERTICAL_SEP_DIR / "特征统计"

# 阶段6：第一行标注
FIRST_ROW_DIR = DATA_DIR / "第一行标注"
FIRST_ROW_VIZ_DIR = FIRST_ROW_DIR / "标注图"
FIRST_ROW_PARAM_DIR = FIRST_ROW_DIR / "参数"
FIRST_ROW_SUMMARY = FIRST_ROW_DIR / "汇总.json"

# ---- 输出与运行期目录 ----
OUTPUTS_DIR = PROJECT_ROOT / "outputs"                  # 交付物输出
SPEEDVIEW_DIR = OUTPUTS_DIR / "流程速览_20261023"        # 管线逐步速览文档+半分辨率预览图(用户快速筛查用)
RUNS_DIR = PROJECT_ROOT / "runs"                        # 运行期临时产物
TMP_DIR = RUNS_DIR / "tmp"
# 按现行行界重出的表：另开新目录，table_reconstruct 里的正式还原.xlsx（含已回写判读）一律不覆盖
# (历史版本 20260925/20260930/20261005 的登记已随僵尸清理_20261025 摘除,目录不在盘上)
REEMIT_DIR_20261005B = RUNS_DIR / "table_reconstruct_重出_20261005_项④行线补全"   # 项④(sub种子墨迹验证补全)后的全量重出
REEMIT_DIR_20261023 = RUNS_DIR / "table_reconstruct_重出_20261023_列线修复"   # M6.T6 列线修复(数据区墨迹重描+质量门)后的 8 图重出
ERA_CHAR_DIR = RUNS_DIR / "era_chars_20261010"   # 时代列整字裁剪试点(列界折线掩膜+行线窄带先验,验收门禁G1-G4)
ERA_CHECK_DIR_20261010 = PROJECT_ROOT / "outputs/时代列整字裁剪核验_20261010"   # 试点核验包(montage拼段+裁片+门禁报告,交用户眼验)
FINALIZE_DIR = RUNS_DIR / "table_整合_20261010"   # 整合表(合并单元格+语义校正+合理性门禁,试点5图)
FINALIZE_PACKAGE_DIR = PROJECT_ROOT / "outputs/时代列整合试点包_20261010"   # 整合xlsx+校正账+验收汇总,交用户核验
USER_VERDICTS_20261010 = RUNS_DIR / "用户裁决_20261010.json"   # 时代列用户裁决输入(图+原→新,管线最后执行,用户赢一切)
LAYER_VERDICTS_20261027 = RUNS_DIR / "B列乱码裁决_20261027.json"   # 煤层标志层号乱码裁决(图+xlsx行→新值,助手判读用户授权免裁)
FINALIZE_FULL_DIR = RUNS_DIR / "table_整合_全量_20261011"   # 全量30张整合表(合并单元格+语义校正+合理性门禁)
FINAL_DELIVERY_DIR_20261028 = PROJECT_ROOT / "outputs/Excel交付_最终_20261028"   # 最终交付:30张整合表成品(含对标红字),纯xlsx
REF_XLSX_DIR_20261011 = DATA_DIR / "参考表_1015-1044_20261011"   # 用户提供的另一套LLM整理结果(1015-1044(1).zip解包,只读输入;2026-11-09 收官清理移入 data)
AGNES_REREAD_DIR_20261028 = RUNS_DIR / "Agnes全列复读_20261028"   # 时代带整块裁剪+Agnes全列复读(块图+账+答+比对)
AGNES_REPEAT_DIR_20261029 = RUNS_DIR / "Agnes全列复读_20261028_重读对照"   # 同配置强制重读的第一次答案备份(一致性核对)
AGNES_COMPARE3_DIR_20261029 = PROJECT_ROOT / "outputs/Agnes三读对照_20261029"   # 我方+三读逐格对照表(每图xlsx:对照+汇总两页)
AGNES_PIXEL_PACK_DIR_20261029 = PROJECT_ROOT / "outputs/Agnes像素核验包_20261029"   # 分歧格原图单格裁片+核验索引(人核后经裁决转正)
# v7 缺陷修复专项(分支 fix-v7-specials):产物一律写新目录,不覆盖 20261011 溯源
FINALIZE_FULL_DIR_20261016 = RUNS_DIR / "table_整合_全量_20261016"   # 专项修复后的全量整合表(门禁口径修正+列角色解耦)
OVERLAY_CHECK_DIR_20260930 = PROJECT_ROOT / "outputs/结构叠加核验_20260930"   # 行界/列界叠加图+1:1裁片,交用户眼验(约束7)

# 行列线定稿交付：可直接使用的行线+列线数据集 + 全分辨率叠加图（只读 table_reconstruct，不写回）
def line_delivery(base):
    """交付数据集的一套路径：换版本只换根目录，子目录名固定。"""
    return SimpleNamespace(
        dir=base, json=base / "每张", overlay=base / "叠加图",
        preview=base / "叠加图_半分辨率预览", window=base / "局部1比1",
        lines_csv=base / "行列线_线级.csv", pts_csv=base / "行列线_点级.csv",
        manifest=base / "清单.json")


# v1（2026-09-26 已交付）：列线当时还是一根按 y 全局排序的整线，把 1921 段"无账弦"
# 当成真实几何出了盘（见 STATUS P10）。冻结留档，不删不改，供新旧对照。
LINE_DELIVERY_V1 = line_delivery(OUTPUTS_DIR / "行列线数据集_20260926")
# 现行版：列线/外框边改走 src/table/col_segments.py —— 按阶段4 碎片出处逐段出账，
# 断口不连线；柱状图案带内的碎片不作列线证据。行线侧与 v1 同判据、同产物。
LINE_DELIVERY = line_delivery(OUTPUTS_DIR / "行列线数据集_列线分段_20260927")
# 离墨成因分类的产物：diag_off.py 顺手落一份"真歪名单"，交付时给这些线上黄色标记
LINE_SUSPECTS = RUNS_DIR / "行列线可疑清单.json"

# 列线正确数据源核验：几何取阶段4 column_fit 的 column_lines[].trajectory（30 张全有、逐 y 连续）
# 只读 COLUMN_FIT_COORD_DIR 与 6a 定稿，产物另开新目录，不回写 LINE_DELIVERY
COLFIX_DIR = OUTPUTS_DIR / "列线核验_column_fit_20260927"
COLFIX_OVERLAY_DIR = COLFIX_DIR / "叠加图"            # 全分辨率 PNG
COLFIX_PREVIEW_DIR = COLFIX_DIR / "叠加图_预览"        # 分段 JPG，肉眼可看
COLFIX_LINES_CSV = COLFIX_DIR / "列线_线级.csv"
COLFIX_MAP = COLFIX_DIR / "定稿对应.json"              # 6a 定稿列 ↔ column_fit 轨迹 匹配表
COLFIX_MANIFEST = COLFIX_DIR / "清单.json"

# 阶段5 新方案：全局锚点列边界恢复（不覆盖 COLUMN_FIT_DIR 旧产物）
LINE_FOLLOW_DIR = RUNS_DIR / "stage5_line_follow"
LINE_FOLLOW_COORD_DIR = LINE_FOLLOW_DIR / "坐标数据"
LINE_FOLLOW_OVERLAY_DIR = LINE_FOLLOW_DIR / "叠加可视化图"
LINE_FOLLOW_DIAG_DIR = LINE_FOLLOW_DIR / "诊断图"

# 阶段5 实验：碎片→物理竖线 Track 归组（track_group；冻结线段，只新增归属关系）
TRACK_GROUP_DIR = RUNS_DIR / "stage5_track_grouping"
TRACK_GROUP_COORD_DIR = TRACK_GROUP_DIR / "坐标数据"
TRACK_GROUP_OVERLAY_DIR = TRACK_GROUP_DIR / "叠加可视化图"

# autoresearch 内容层对标实验区(结构层冻结只读;不改 20261028 交付与 20261011 整合表)
AUTORESEARCH_DIR = RUNS_DIR / "autoresearch_align"        # 会话工作区
AUTORESEARCH_SEED_DIR = AUTORESEARCH_DIR / "seed"        # 基线快照(=table_整合_全量_20261011 的30张整合xlsx,冻结)
AUTORESEARCH_CANDIDATE_DIR = AUTORESEARCH_DIR / "candidate"   # 候选整合表(规则引擎产出,可随时重置重生成)
AUTORESEARCH_ROWCACHE = AUTORESEARCH_DIR / "row_ivs.json"     # 行区间缓存(与 compare_ref 重放同参;结构冻结才可复用)

# 合成量化验收门禁(分支 stage06-syn-gate):合成扫描件 / GT / 叠加预览
SYNTH_DIR = RUNS_DIR / "synthetic_gate"
SYNTH_SCAN_DIR = SYNTH_DIR / "scans"
SYNTH_GT_DIR = SYNTH_DIR / "gt"
SYNTH_PREVIEW_DIR = SYNTH_DIR / "preview"
SYNTH_SCORE_DIR = SYNTH_DIR / "scores"
SYNTH_CROP_DIR = SYNTH_SCORE_DIR / "crops"
VERIFIED_CONTENT_DIR = RUNS_DIR / "verify_content"   # 内容层只读互证报告(判定6)
STAGE_AUDIT_DIR = RUNS_DIR / "阶段巡检包_20260923"    # 全阶段产物巡检包(用户排查用)
CHAIN_DIR = SYNTH_DIR / "chain"             # 合成图跑真管线的沙箱根

THIRD_PARTY_DIR = PROJECT_ROOT / "src" / "third_party"  # 第三方源码（skeleton-tracing）

# ---- 外部输入（桌面文件，不属于本项目，运行前请确认存在）----
EXTERNAL_DESKTOP = Path(r"D:\Skye\Desktop")
DELIVERY_XLSX = EXTERNAL_DESKTOP / "钻孔数据_交付版_20260730_v4.xlsx"  # 交付版 Excel（审计/QC 输入）
V4_TEMPLATE_XLSX = EXTERNAL_DESKTOP / "1015-1044.xlsx"                 # 套入模板（fill_and_pack 输入）
PACKED_DIR = EXTERNAL_DESKTOP / "钻孔数据_套入v4"                        # fill_and_pack 输出目录
PACKED_ZIP = EXTERNAL_DESKTOP / "钻孔数据_套入v4.zip"                     # fill_and_pack 打包输出
# 外部 LLM 重建管线产物（reconstruct_all 输入，当前未纳入本项目）
AI_PIPELINE_DIR = PROJECT_ROOT / "ai_pipeline" / "deliverables" / \
    "manual_review_1015_1044_geologic_v2" / "derived_graphs"


def pair_jpg_json(json_dir: Path) -> list:
    """配对 data/raw_images 的 JPG 与其在 json_dir 下的坐标 JSON。

    返回 [(jpg_path, json_path), ...]，按文件名排序；无配对的 JPG 忽略。
    """
    pairs = []
    for jpg in sorted(RAW_DIR.iterdir()):
        if jpg.is_file() and jpg.suffix.lower() in (".jpg", ".jpeg"):
            jf = json_dir / f"{jpg.stem}.json"
            if jf.exists():
                pairs.append((jpg, jf))
    return pairs


def ensure_dirs(*dirs: Path) -> None:
    """批量创建目录（parents=True, exist_ok=True）。"""
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
