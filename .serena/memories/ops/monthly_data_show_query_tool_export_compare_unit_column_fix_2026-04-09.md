时间：2026-04-09
主题：monthly_data_show query-tool 导出 XLSX 的“对比明细”缺少计量单位列修复

前置说明：
- Serena 项目激活与 onboarding 校验已完成。
- 本轮涉及 Vue 与 Markdown 文本编辑；由于 Serena 不能对 .vue / .md 做可靠结构化编辑，按仓库规范降级使用 apply_patch。
- 降级范围：
  - frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
  - configs/progress.md
  - frontend/README.md
  - backend/README.md
- 回滚思路：回退上述四个文件到本次修改前版本即可恢复旧模板结构。

问题现象：
- 导出的 XLSX 文件中，“对比明细”sheet 的“指标”列右侧缺少“计量单位”列。
- 导致用户在查看同名或近似指标时无法直接从导出结果判断单位口径。

根因：
- 前端 MonthlyDataShowQueryToolView.vue 中 compareHeader 未包含“计量单位”。
- compareData 行映射也未写出 x.unit。
- 数值写入索引以旧列布局为基准，因此不能只加表头，必须同步后移数值列索引。

处理：
- 在对比明细导出模板中将表头改为“口径 / 指标 / 计量单位 / 期间 / 类型 / …”。
- 在 compareData 的行数组里将 x.unit 插入到 x.item 之后。
- 将 setSheetNumericCell 的数值列写入索引整体后移 1。
- 调整对比明细 sheet 的列宽数组，给“计量单位”预留单独宽度。

验证：
- 在 frontend 目录执行 npm run build，Vite 构建通过。

结果：
- 导出的“对比明细”sheet 现在包含“计量单位”列，且位于“指标”右侧。
- 其他导出 sheet 与后端接口协议未改动。