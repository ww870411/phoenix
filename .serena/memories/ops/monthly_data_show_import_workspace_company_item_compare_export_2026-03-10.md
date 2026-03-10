时间：2026-03-10
需求：在 `https://platform.smartview.top/projects/monthly_data_show/import-workspace` 页面上，步骤 3 后新增独立分支“步骤 3.1：标准表对照”，先实现一个按钮：基于当前上传表并在“提取 CSV”完成后，导出只含 `company,item` 的 CSV，对后续历史表差异比对使用；不得影响原下载 CSV 与步骤 4 入库功能。
实现：
1) `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
- 新增“步骤 3.1：标准表对照”卡片与按钮 `导出 company,item 对照表`。
- 仅在步骤 3 已成功提取、`lastExtractedCsvFile` 存在时可点击。
- 新增前端本地逻辑：
  - 读取刚提取的 CSV 文件；
  - 解析 `company`、`item` 两列；
  - 去重后生成新 CSV；
  - 浏览器直接下载 `${原文件名}_company_item_compare.csv`。
- 新增状态：`comparingStandard`、`compareMessage`。
2) 设计选择
- 本轮未新增后端接口；
- 直接复用步骤 3 的标准化提取结果，降低耦合，不影响后续下载原 CSV 与第 4 步入库。
3) 文档同步
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`
验证：
- `cd frontend && npm run build` 通过。
降级说明：
- Serena 不支持直接编辑 Vue/Markdown，按仓库规范使用 `apply_patch`。
回滚：
- 删除 `MonthlyDataShowEntryView.vue` 中新增的步骤 3.1 UI、状态与 `exportStandardCompareCsv()` 等辅助函数；移除对应文档记录。