用户指令（优先级最高）：统一项目代号与路径为 `daily_report_25_26`，清理仓库中文档/展示中的 `25-26daily_report`。

执行摘要：
- 更新 AGENTS.md：所有示例与关键词改为 `daily_report_25_26`；示例 JSON 中的 `project_key` 同步更正。
- 更新 backend/README.md、frontend/README.md：删除“命名不一致”的说明，改为统一表述。
- 更新前端页面：ProjectSelectView 展示文案改为 `daily_report_25_26`。
- 更新前端子域 README：两处 `25-26daily_report` 改为 `daily_report_25_26`。
- 更新 configs/progress.md：修正历史条目中的残留文案，并保留本次变更的记录条目。

影响范围：文档与展示字符串；后端与前端实际调用路径原本已为 `daily_report_25_26`，业务接口不受影响。
回滚思路：若需回退，仅需恢复上述文件至变更前版本（git 历史）。