时间：2026-02-28
主题：monthly_data_pull 批量上传改为“预览-确认-应用”流程
触发：用户同意增加识别预览，要求先看匹配结果再执行。

变更文件：
1) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 新增 batchPreview 状态与预览表（文件名、识别结果）。
- handleBatchPick 改为仅构建预览，不立即上传。
- 新增 applyBatchPreview：确认后才调用 get-sheets 上传并应用到槽位。
- 新增 clearBatchPreview：取消本次批量识别。
- 匹配升级为一对一占位分配（同一槽位只自动占用一次），降低误配覆盖风险。
- 在重新解析映射与清空目录时，自动清空 batchPreview。

后端影响：无接口变更，继续复用 get-sheets 处理确认后的文件上传。