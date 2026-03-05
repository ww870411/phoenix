时间：2026-03-04
主题：模板设计器第三期（类 Excel 画布增强）

实现文件：frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue

主要能力：
1) 画布内直接拖拽
- 列头拖拽重排（复用列拖拽逻辑）
- 行拖拽重排（复用行拖拽逻辑）

2) 画布内直接操作
- 列头支持就地删除
- 画布工具栏新增“新增列/新增行”

3) 列宽能力
- 列定义新增 width 字段
- 画布按 width 渲染列宽

4) 后续接库预留
- 新增连接配置区
- meta.binding: target_table / write_mode / id_strategy
- meta.layout: frozen_columns

5) 兼容性
- 继续通过既有模板 API 保存发布
- 保留 rows JSON 兼容模式

验证：
- frontend 执行 npm run build 通过

留痕文件：
- configs/progress.md
- frontend/README.md
- backend/README.md