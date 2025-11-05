# 项目页面描述同步（2025-11-10）
- 时间：2025-11-10
- 涉及文件：`backend_data/项目列表.json`、`backend/api/v1/routes.py`、`frontend/src/daily_report_25_26/pages/PageSelectView.vue`、`configs/progress.md`、`frontend/README.md`、`backend/README.md`
- 操作内容：
  - 在项目配置中为 `dashboard`、`data_show`、`data_approval`、`data_entry`、`constant_data`、`/debug/runtime-eval` 页面新增 `页面描述` 字段，文字与前端既有映射一致。
  - `_normalize_pages` 透传描述到接口字段 `page_description/description`，兼容旧数据结构默认空字符串。
  - `pageDescription` 函数改为优先使用接口返回描述，映射表保留兜底逻辑。
- 降级说明：Serena 未支持 JSON/Vue 写入，使用 `desktop-commander::read_file` + `apply_patch` 完成编辑，回滚恢复上述文件即可。
- 验证要点：调用 `/api/v1/projects/daily_report_25_26/pages` 可看到 `page_description`；页面卡片副标题与配置描述保持一致。