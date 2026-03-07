时间：2026-03-08
用户反馈：取消“显示 AI 聊天气泡”并保存后当前页会隐藏，但刷新后再次出现。

处理判断：
- 保存后即时隐藏已生效，说明保存请求与前端即时回写链路正常。
- 刷新后回弹高概率来自配置读取缓存（GET 返回旧值）。

变更：
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 在以下读取接口增加 fetch 选项 cache: 'no-store'：
  1) getDataAnalysisSchema
  2) getMonthlyDataShowQueryOptions
  3) getAiSettings
  4) getAdminAiSettings

结果：
- 页面刷新后会重新拉取最新 show_chat_bubble 配置，避免旧缓存导致的回弹。

同步文档：
- configs/progress.md
- frontend/README.md
- backend/README.md