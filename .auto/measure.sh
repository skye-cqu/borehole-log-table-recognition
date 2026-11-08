#!/usr/bin/env bash
# 冻结基准:规则引擎重置候选→应用规则→内置门禁→只读对标打分。输出 METRIC align=… 行。
# 双 bash 兼容:插件侧=System32 WSL bash(看不见 D:/,须 wslpath 转 /mnt/d);
# 本地侧=Git Bash(D:/ 直接可读)。
# 输出纪律:Windows python(interop 子进程)在 detached 管道下 stdout 会丢,
# 故一切输出只落 LOG,末尾由 bash 原生 tail 出尾(METRIC 行在内)。
# 门禁内置:插件 runChecks 以反斜杠绝对路径调 bash,反斜杠被当转义,恒 127
# (server.ts runChecks 的 Windows 路径缺陷)——verify_candidate.py 并入本基准:
# 门禁不过 = 本基准 exit 非0,按 checks_failed 记账。
set -u
ROOT_WIN="D:/Skye/Documents/Work/高维智矿/7.13杂活"
ROOT="$ROOT_WIN"
[ -d "$ROOT" ] || ROOT="$(wslpath -u "$ROOT_WIN")"
cd "$ROOT" || exit 1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export WSLENV="PYTHONIOENCODING/u:PYTHONUTF8/u"
PY="$ROOT/.venv/Scripts/python.exe"
LOG="$ROOT/runs/autoresearch_align/_measure.log"
LOG_WIN="$ROOT_WIN/runs/autoresearch_align/_measure.log"
: > "$LOG"
"$PY" -I src/handwriting/apply_rules.py      >>"$LOG" 2>&1 || { tail -c 2000 "$LOG"; exit 1; }
"$PY" -I src/handwriting/verify_candidate.py >>"$LOG" 2>&1 || { tail -c 2000 "$LOG"; exit 1; }
"$PY" -I src/handwriting/converge_score.py   >>"$LOG" 2>&1 || { tail -c 2000 "$LOG"; exit 1; }
"$PY" -I src/tools/align_score.py            >>"$LOG" 2>&1 || { tail -c 2000 "$LOG"; exit 1; }
# 主指标=收敛分级 conv(零参考,segment5);align 仅落 LOG 供人工对照。
grep -E "^METRIC conv=" "$LOG"
