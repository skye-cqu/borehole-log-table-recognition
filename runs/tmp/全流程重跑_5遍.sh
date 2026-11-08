#!/bin/bash
# 全流程重跑 N 遍 + 每遍哈希比对(2026-10-25)。
#
# 用法:  bash runs/tmp/全流程重跑_5遍.sh [遍数]     # 遍数默认 5
#
# 设计:
# - 流程没有任何随机源(仅有的两个随机种子写死在代码里),同一份输入各遍结果应当
#   逐字节一致。所以每遍跑完对关键产物做 SHA256:任何一遍与上一遍不一致 → 立即
#   中止报错,不等跑完 5 遍。
# - 结构层产物(阶段4 候选/分割线/行判定/表头映射/闭合外框)在盘上的现值是已核验
#   状态:第 1 遍跑完先和它比,不一致说明"重跑把核验状态跑漂了",最严重的失败,
#   单独报警。
# - 任何阶段脚本退出码非 0 → 立即中止(不往下带病跑)。
# - 出表后按约束 12 跑 audit_deliverable(审重出目录),哨兵非 0 即失败退出。
#
# 注意:
# - 正式表 runs/table_reconstruct/*_还原.xlsx(含人审判读)本链不碰(reemit 设计保证);
#   Agnes 三源互证/判读回写不在本自动链内。
# - 整合表 finalize_tables 目前固定吃 20261005B 重出目录(不是本次重出的 20261023),
#   现状遗留,本脚本不擅自改源。
# - 单遍耗时以小时计(大头是 OCR:era_chars 26 图逐格 + reemit 30 表逐格),
#   5 遍请留整夜。

set -u
cd "$(dirname "$0")/../.." || exit 1
export PYTHONPATH=.
PY=".venv/Scripts/python.exe"
N="${1:-5}"

STAGES=(
  "src/binarize/multi_scale_sauvola.py"      # 1 二值化
  "src/thinning/thin_zhangsuen.py"           # 2 细化
  "src/skeleton/trace_skeleton_batch.py"     # 3 骨架追踪
  "src/table/table_line_detect.py"           # 4 表格线候选
  # 5 列线定稿(6a finalize_columns)+断口补全(6a2 bridge_gaps)不在此列:
  #   两脚本吃已退役的 track 归组产物(按 track 编号硬编码,EXPERIMENT.md 定案退役,
  #   产物已删)——_分割线.json 是冻结的 6a 产物,不可从阶段4 再生,直接沿用并受
  #   基线哈希保护。2026-10-25 实跑实锤,沿用前先撞过 SystemExit 守卫。
  "src/table/frame_topbottom.py"             # 6 上下框(6a3)
  "src/table/close_frame.py"                 # 6 外框闭合(6a4)
  "src/table/col_line_repair.py"             # 5.5 列线修复(剔错轨+端点连线+接框)
  "src/table/track_rows.py"                  # 7 行界判定
  "src/table/header_assign.py"               # 8 表头映射(6b)
  "src/tools/emit_line_dataset.py"           # 9 行列线数据集(叠加图+CSV)
)
# 时代列整字裁剪:该脚本无参数=不跑任何图,必须显式给图号;清单取自盘上已裁图目录
ERA_CHARTS=$(for d in runs/era_chars_20261010/*/; do basename "$d"; done | tr '\n' ' ')

# 结构层哈希(已核验状态漂移检查用)
hash_struct() {
  cat data/表格线候选识别处理/坐标数据/*.json \
      runs/table_reconstruct/*_分割线.json \
      runs/table_reconstruct/*_行判定.json \
      runs/table_reconstruct/*_表头映射.json \
      runs/table_reconstruct/*_闭合外框.json 2>/dev/null | sha256sum | cut -d' ' -f1
}
# 全产物哈希(遍间一致性检查用;只取数据文件,叠加图 PNG 不入账省时)
hash_full() {
  { cat data/表格线候选识别处理/坐标数据/*.json \
        runs/table_reconstruct/*_分割线.json \
        runs/table_reconstruct/*_行判定.json \
        runs/table_reconstruct/*_表头映射.json \
        runs/table_reconstruct/*_闭合外框.json 2>/dev/null;
    find outputs/行列线数据集_列线分段_20260927 \
         runs/table_reconstruct_重出_20261023_列线修复 \
         runs/table_整合_全量_20261016 \
         runs/era_chars_20261010 -type f \( -name '*.json' -o -name '*.csv' -o -name '*.xlsx' \) -print0 2>/dev/null \
      | sort -z | xargs -0 cat 2>/dev/null; } | sha256sum | cut -d' ' -f1
}

BASE_STRUCT=$(hash_struct)
echo "基线(已核验状态)结构哈希: $BASE_STRUCT"
echo "共 $N 遍;每遍 12 个结构阶段 + 时代列(${ERA_CHARTS% }) + 出表 + 整合 + audit"

for i in $(seq 1 "$N"); do
  echo ""
  echo "================ 第 $i/$N 遍 ================"
  for s in "${STAGES[@]}"; do
    echo "--- $s"
    "$PY" -X utf8 "$s" || { echo "!!! 中止: $s 失败(第 $i 遍)"; exit 1; }
  done
  echo "--- src/table/era_chars.py (26 图显式清单)"
  "$PY" -X utf8 src/table/era_chars.py $ERA_CHARTS || { echo "!!! 中止: era_chars 失败(第 $i 遍)"; exit 1; }
  echo "--- src/tools/era_cell_montage.py"
  "$PY" -X utf8 src/tools/era_cell_montage.py || { echo "!!! 中止: era_cell_montage 失败(第 $i 遍)"; exit 1; }
  echo "--- src/tools/reemit_tables.py"
  "$PY" -X utf8 src/tools/reemit_tables.py || { echo "!!! 中止: reemit_tables 失败(第 $i 遍)"; exit 1; }
  echo "--- src/table/finalize_tables.py"
  "$PY" -X utf8 src/table/finalize_tables.py || { echo "!!! 中止: finalize_tables 失败(第 $i 遍)"; exit 1; }
  echo "--- audit_deliverable (重出目录)"
  "$PY" -X utf8 src/tools/audit_deliverable.py runs/table_reconstruct_重出_20261023_列线修复 \
    || { echo "!!! 中止: audit_deliverable 未过(第 $i 遍)"; exit 1; }

  H_STRUCT=$(hash_struct)
  H_FULL=$(hash_full)
  if [ "$H_STRUCT" != "$BASE_STRUCT" ]; then
    echo "!!! 中止: 第 $i 遍结构产物与重跑前(已核验状态)不一致 —— 结构层有漂移,先查再跑"
    exit 1
  fi
  if [ -n "${LAST_FULL:-}" ] && [ "$H_FULL" != "$LAST_FULL" ]; then
    echo "!!! 中止: 第 $i 遍与第 $((i-1)) 遍产物不一致 —— 流程非确定,先查再跑"
    exit 1
  fi
  LAST_FULL="$H_FULL"
  echo ">>> 第 $i 遍完成: 结构与核验状态一致,遍间一致 ($H_FULL)"
done

echo ""
echo "================ $N 遍全部完成,零漂移 ================"
