时间：2025-10-19
变更文件：frontend/src/daily_report_25_26/pages/Sheets.vue

需求：恢复 /projects/:projectKey/sheets 页面原有卡片式外观（每个单位对应一组卡片，卡片内展示表格名称与填报进度）。

实施：
- 重写模板，使用 card-grid + sheet-card-line 样式，把每个表格呈现为小卡片。
- 卡片内展示表名（router-link 跳转）、sheet_key、副标题。
- 显示 statusMap 统计的填报进度（徽标 + 进度条），与 getTemplate/queryData 同步刷新。
- 兼容 listSheets 响应结构，支持 meta.sheet_name/unit_name 与中文键名。
- 引入主题样式 theme.css，保持原 UI 设计。watch(bizDate) 触发刷新。

回滚：恢复 Sheets.vue 至前一版本即可。

待办：configs/progress.md 当前文件编码存在异常，未能写入相应记录，需人工确认后再补录。