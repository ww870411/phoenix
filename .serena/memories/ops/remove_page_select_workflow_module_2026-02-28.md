时间：2026-02-28
主题：移除项目页面选择页“审批进度”模块

用户反馈：审批进度模块没有必要。

实现：
- 文件：frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
  1) 移除审批进度区域 UI
  2) 移除 workflow 状态请求与错误处理
  3) 移除 approve/revoke/publish 操作逻辑
  4) 移除对应样式

结果：
- 项目页仅保留页面卡片选择，界面简化。

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md