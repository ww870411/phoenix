时间：2025-10-25
主题：Coal_inventory_Sheet 渲染失败修复（template_type 回退推断）
触发条件：页面可获取模板但无法渲染，系前端将交叉表按 standard 流程初始化导致列/行映射异常。
操作范围：frontend/src/daily_report_25_26/pages/DataEntryView.vue；README 同步说明。
变更摘要：在模板加载后，若 `sheetKey === 'Coal_inventory_Sheet'` 且未提供 `template_type`，则强制设为 `'crosstab'`，保证后续按交叉表流程（列初始化 + 镜像查询回填）。
降级说明：Serena 对 .vue 文件无符号级编辑能力，采用 Codex CLI apply_patch 小步修改并记录。
回滚思路：删除回退赋值逻辑（rawTemplate.template_type = 'crosstab'）并恢复仅依赖后端返回的 template_type；若后端统一补齐该字段，亦可移除此回退。