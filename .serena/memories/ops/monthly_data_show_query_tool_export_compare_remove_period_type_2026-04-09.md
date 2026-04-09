时间：2026-04-09
主题：monthly_data_show query-tool 导出 XLSX 的“对比明细”移除“期间”“类型”列

前置说明：
- Serena 项目激活与 onboarding 校验已完成。
- 本轮涉及 Vue 与 Markdown 文本编辑；由于 Serena 不能对 .vue / .md 做可靠结构化编辑，按仓库规范降级使用 apply_patch。
- 降级范围：
  - frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
  - configs/progress.md
  - frontend/README.md
  - backend/README.md
- 回滚思路：回退上述四个文件到本次修改前版本即可恢复旧列结构。

需求：
- 用户明确要求导出的“对比明细”sheet 不再保留“期间”“类型”两列。

处理：
- 在对比明细导出模板中将表头从“口径 / 指标 / 计量单位 / 期间 / 类型 / …”改为“口径 / 指标 / 计量单位 / 本期值 / 同期值 / …”。
- compareData 行映射中移除 x.period 与 x.type。
- setSheetNumericCell 的所有数值列索引整体前移 2。
- 列宽数组同步删除两列对应宽度。
- 年计划相关三列仍按启用状态追加在末尾。

验证：
- 在 frontend 目录执行 npm run build，Vite 构建通过。

结果：
- 导出的“对比明细”sheet 不再展示“期间”“类型”列，列结构更贴合用户实际使用需求。