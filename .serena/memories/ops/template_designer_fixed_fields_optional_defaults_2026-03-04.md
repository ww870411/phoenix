时间：2026-03-04
需求：固定字段“单位”不应默认硬编码，应可选并支持默认值。

实现文件：frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue

实现内容：
1) 新增固定字段配置区
- row_label 开关 + 默认值
- unit 开关 + 默认值

2) 数据落位
- 写入 form.meta.fixed_fields
- 写入 form.meta.default_values

3) UI 联动
- 行编辑区按 fixed_fields 显示/隐藏列
- 预览网格按 fixed_fields 显示/隐藏“项目/单位”列

4) 提交流程联动
- 新增行自动应用默认值
- 关闭字段后提交前清空对应字段值

验证：
- npm run build（frontend）通过。

留痕文件：
- configs/progress.md
- frontend/README.md
- backend/README.md