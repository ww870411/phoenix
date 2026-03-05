时间：2026-03-05
需求：管理后台气温导入弹窗需显示逐小时气温并标示一致性（对齐数据看板）。

实现：
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
1) 弹框新增逐小时一致性列表：
   - 显示字段：time、apiValue、dbValue（未命中库显示“—”）、一致/不一致
   - 差异项使用红色高亮样式 temp-import-modal__diff-item--different
2) 预览数据映射增强：
   - 新增 temperatureImportStatus.overlapRecords
   - 从 payload.overlap_records 映射 time/api_value/db_value/different/in_db
3) 统计字段修正：
   - 重合小时读取改为 payload.overlap.hours（避免 NaN）

验证：
- frontend 执行 npm run build 通过

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md