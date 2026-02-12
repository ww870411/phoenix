时间：2026-02-11
任务：为 daily_report_spring_festval_2026 搭建直达页面，并实现 xlsx 上传提取 JSON。

实现结果：
1) 路由与入口
- 前端新增路由 /projects/:projectKey 对应 SpringFestivalEntryView。
- ProjectSelectView 对 daily_report_spring_festval_2026 直达 /projects/{projectKey}，不再进入 /pages。
- SpringFestivalEntryView 对非目标项目自动重定向回 /projects/{projectKey}/pages，避免影响原项目。

2) 后端接口
- 新增项目模块：backend/projects/daily_report_spring_festval_2026/api/
  - router.py
  - xlsx_extract.py
- 注册到 backend/api/v1/project_router_registry.py。
- 新接口：POST /api/v1/projects/daily_report_spring_festval_2026/spring-festival/extract-json。
- 解析逻辑：
  - 自动识别“本期/同期/差异”表头行；
  - 表头上一行为日期行；
  - 合并单元格补全（scope 等）；
  - 输出结构 meta/dates/byDate；
  - 支持 keep_diff_cell / compute_diff / normalize_metric 参数。

3) 前端上传解析
- 新页面：frontend/src/daily_report_25_26/pages/SpringFestivalEntryView.vue。
- 新 API：extractSpringFestivalJson(projectKey, file, options)。
- 页面支持：文件上传、可选 sheet、三个布尔选项、JSON 预览、下载、localStorage 缓存。

4) 文档与留痕
- 更新 backend/README.md、frontend/README.md、configs/progress.md。

后续建议（下一阶段）：
- 基于解析后 JSON 设计“简化看板指标映射 + 卡片/趋势图 + PDF 导出”流程。