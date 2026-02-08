时间戳：2026-02-08
任务：按用户要求对在线填报平台进行优化。

前置说明/偏差记录：
- 规则冲突：仓库 AGENTS.md 倾向 Serena 优先编辑，但用户在项目说明中明确要求“读取和修改文件禁止使用 cmd/powershell，必须使用 apply_patch 这类原生工具”。
- 处置：检索仍使用 Serena；文件改动统一通过 apply_patch 执行。未使用 shell 进行读写。
- 回滚思路：
  1) 回滚 backend/api/v1/daily_report_25_26.py 的缓存和去重变更；
  2) 回滚 configs/progress.md、backend/README.md、frontend/README.md 新增段落。

变更文件清单：
1. backend/api/v1/daily_report_25_26.py
2. configs/progress.md
3. backend/README.md
4. frontend/README.md

变更摘要：
- 清理煤炭库存重复定义：删除早期版本 _flatten_records_for_coal / _persist_coal_inventory / handle_coal_inventory_submission，保留末尾唯一生效版本，避免同名覆盖造成的维护风险。
- 模板读取性能优化：_read_json 改为调用 _read_json_cached，缓存键包含 path + mtime_ns + size，文件变更自动失效，减少模板查询中的重复磁盘 I/O。
- 文档留痕：在 progress 和前后端 README 补充本次会话变更与最新结构。

验证证据：
- 搜索确认：_flatten_records_for_coal 已不存在；_persist_coal_inventory 与 handle_coal_inventory_submission 各仅保留一处定义；_read_json_cached 已新增且被 _read_json 调用。