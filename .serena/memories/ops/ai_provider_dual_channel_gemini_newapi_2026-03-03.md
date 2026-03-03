时间：2026-03-03
需求：扩展 AI 智能服务支持 New API 格式接入（base_url/api_key/model）并可与 Gemini 官方 API 切换。
变更范围：
1) backend/services/data_analysis_ai_report.py
- 新增 provider 读取逻辑：provider in {gemini,newapi}
- 新增 newapi 配置加载（newapi_base_url/newapi_api_keys/newapi_model）
- 新增 OpenAI-compatible chat/completions 调用链（urllib）
- 保留 gemini SDK 调用链并改为 runtime provider 分流
- 客户端缓存由 _model/_model_name 改为 runtime client/signature/model
2) backend/projects/daily_report_25_26/api/legacy_full.py
- AiSettingsPayload 扩展 provider/newapi_* 字段
- _read_ai_settings/_safe_read_ai_settings/_persist_ai_settings 扩展双通道字段读写并兼容旧 key
- /data_analysis/ai_settings GET/POST 扩展响应与入参
3) backend/api/v1/admin_console.py
- AiSettingsPayload 扩展 provider/newapi_* 字段
- /admin/ai-settings POST 调用 _persist_ai_settings 新参数
- 管理后台概览 AI 摘要增加 provider/newapi 统计
4) frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue
- 新增 provider 选择（Gemini / New API）
- 新增 New API Base URL / Keys / Model 输入
- 保存 payload 新增 provider/newapi_* 透传
5) frontend/src/projects/daily_report_25_26/services/api.js
- updateAiSettings/updateAdminAiSettings 新增 provider/newapi_* 字段透传
6) backend_data/shared/ai_settings.json
- 新增默认键：provider/newapi_base_url/newapi_model/newapi_api_keys
留痕：configs/progress.md、backend/README.md、frontend/README.md 已同步更新。