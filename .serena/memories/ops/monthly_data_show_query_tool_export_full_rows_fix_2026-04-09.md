时间：2026-04-09
主题：monthly_data_show query-tool 导出 XLSX 仅导出前 200 条修复

前置说明：
- Serena 项目激活与 onboarding 校验已完成。
- 本轮涉及 Vue 与 Markdown 文本编辑；因 Serena 当前仅支持 Python 符号级检索，无法对 .vue / .md 做可靠结构化编辑，因此按仓库规范降级使用 apply_patch。
- 降级范围：
  - frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
  - configs/progress.md
  - frontend/README.md
  - backend/README.md
- 回滚思路：回退上述四个文件到本次修改前版本即可恢复旧行为。

问题现象：
- query-tool 页面查询时每页只展示 200 条，这是正常分页行为。
- 但点击“导出 XLSX”时，Excel 的“查询结果”sheet 直接使用前端当前页 rows，导致总命中条目超过 200 时，只导出当前页/前 200 条，不是全量结果。

根因：
- 前端 MonthlyDataShowQueryToolView.vue 中 downloadXlsx() 直接基于 rows.value 组装结果 sheet。
- buildPayload() 固定携带 limit=200 与当前 offset，用于页面分页展示；导出错误复用了这份分页结果。
- 后端 /monthly-data-show/query 本身支持分页查询，且单次 limit 上限为 1000。

处理：
- 新增 exportLoading 状态，导出期间禁用按钮并显示“导出中...”。
- 新增 fetchAllQueryRowsForExport()：根据 total 值按批次调用 queryMonthlyDataShow('monthly_data_show', payload)，每批最多 1000 条，循环直到取满全部数据。
- downloadXlsx() 改为异步导出：先拉取 exportRows，再用 exportRows 写入“查询结果”sheet；比较明细、分析结论、气温汇总保持原有逻辑。
- 若批量拉取结果数小于 total，会抛错阻止导出不完整文件。

验证：
- 在 frontend 目录执行 npm run build，Vite 构建通过。

结果：
- 页面仍按每页 200 条显示，不影响日常查询性能。
- XLSX 导出已与分页解耦，可覆盖全部查询命中结果。