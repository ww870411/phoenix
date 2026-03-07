时间：2026-03-08
用户反馈：配置接口 no-store 后仍出现刷新回弹。

处理决策：
- 增加页面级强一致兜底：页面初始化后主动读取 AI 设置接口，并以 show_chat_bubble 覆盖本地气泡状态。
- 不再仅依赖 schema/query-options 中的开关字段。

修改文件：
1) frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

实现细节：
- 两页均新增：
  - chatBubbleOverride 状态（优先级最高）
  - syncChatBubbleFromSettings() 主动拉取设置并覆盖
- 页面 mounted 初始化流程中加入该同步步骤。
- 保存设置成功时也同步写入 chatBubbleOverride。

预期结果：
- 关闭并保存后立即生效；
- 刷新后也保持隐藏，以 AI 设置实时值为准。