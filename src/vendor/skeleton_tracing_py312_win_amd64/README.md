# skeleton-tracing Windows运行时

本目录保存阶段3运行所需的预编译运行时：

- `trace_skeleton.py`
- `_trace_skeleton.cp312-win_amd64.pyd`

环境：Windows x86-64、CPython 3.12。

上游源码位于 `src/third_party/skeleton-tracing`。当前Python封装由SWIG 4.4.1生成；编译中间物和清理前副本保存在 `rollback/stage04_cleanup_20260820/archived_content/third_party_build/`。

更新该运行时时必须同时验证：

1. `.venv`中的Python能够导入 `trace_skeleton`；
2. `trace_skeleton.from_numpy()` 可处理最小二值数组；
3. 第三方子模块保持干净。
