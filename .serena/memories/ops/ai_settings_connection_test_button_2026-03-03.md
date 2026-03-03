时间：2026-03-03
需求：在智能体设定中增加“测试连接”能力，避免完整报告前无法判断 provider 配置是否可用。
实现：
1) 后端服务
- 文件：backend/services/data_analysis_ai_report.py
- 新增：run_ai_connection_test(payload)
- gemini/newapi 分别执行最小 prompt 测试并返回 provider/model/message
2) 项目级接口
- 文件：backend/projects/daily_report_25_26/api/legacy_full.py
- 新增 payload: AiSettingsConnectionTestPayload
- 新增路由：POST /data_analysis/ai_settings/test
3) 管理后台接口
- 文件：backend/api/v1/admin_console.py
- 新增 payload: AiSettingsConnectionTestPayload
- 新增路由：POST /admin/ai-settings/test
4) 前端 API
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 新增：testAiSettings(projectKey,payload)
- 新增：testAdminAiSettings(payload)
5) 前端弹窗
- 文件：frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue
- 新增 prop：testSettings（可选）
- 新增按钮：测试连接
- 测试成功提示：连接测试成功：{provider}(model)
6) 页面接入
- DataAnalysisView.vue: 绑定项目级 testAiSettings
- AdminConsoleView.vue: 绑定管理后台 testAdminAiSettings
- MonthlyDataShowQueryToolView.vue: 绑定管理后台 testAdminAiSettings
留痕文档：configs/progress.md、backend/README.md、frontend/README.md 已更新。