# 数据看板布局优化（2025-11-09）
- 触发原因：数据看板页面纵向排列时出现卡片投影遮挡，下方组件看似侵入上方区域；摘要卡片体量偏大影响整体观感。
- 主要改动：在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 中缩减摘要卡片圆角、内边距与投影，调整图标尺寸；为 `.dashboard-grid` 增加 `grid-auto-rows` 与父子级 flex 拉伸，统一卡片高度并修正 `z-index`；降低主体卡片投影强度并保持内容列自适应。
- 验证建议：在桌面与窄屏浏览仪表盘，确认摘要卡片更紧凑、主体卡片高度一致且纵向排列无重叠，`show_date/push_date` 交互不受影响。
- 回滚方式：恢复 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 至本次修改前版本即可撤销布局调整。