时间：2026-03-03
需求：智能体设定支持多 provider（每个 provider 含 base_url/api_key/model），可选择当前使用 provider；设置页优化为折叠分组；主按钮改为“保存并退出”。
后端改动：
1) backend/projects/daily_report_25_26/api/legacy_full.py
- AiSettingsPayload / AiSettingsConnectionTestPayload 增加 providers, active_provider_id
- _read_ai_settings 支持读取 providers+active_provider_id，兼容旧字段回退
- _persist_ai_settings 支持保存 providers+active_provider_id，并同步旧字段做兼容
- /data_analysis/ai_settings GET/POST 响应与入参支持 providers/active_provider_id
- /data_analysis/ai_settings/test 支持按 providers 当前生效项测试
2) backend/api/v1/admin_console.py
- AiSettingsPayload / AiSettingsConnectionTestPayload 同步增加 providers, active_provider_id
- /admin/ai-settings 与 /admin/ai-settings/test 支持新字段
- 管理后台 AI 摘要增加 active_provider 与 provider 数量信息
3) backend/services/data_analysis_ai_report.py
- 新增 _resolve_active_provider_record，运行时优先按 active provider 取配置
- run_ai_connection_test 支持 providers+active_provider_id
- 保留旧 provider/gemini/newapi 字段作为兜底
- 增加 API key 解码保护：避免对明文 sk-/AIza key 误解密（处理第6,7位恰好为ww导致的误删）
前端改动：
1) frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue
- 组件重写为折叠式分组布局
- 支持 provider 列表增删、选择 active provider、独立维护 keys/model/base_url
- 主按钮文案改为“保存并退出”
2) frontend/src/projects/daily_report_25_26/services/api.js
- update/test 系列接口新增 providers/active_provider_id 字段透传
配置文件：
- backend_data/shared/ai_settings.json 增加 providers 和 active_provider_id 示例。