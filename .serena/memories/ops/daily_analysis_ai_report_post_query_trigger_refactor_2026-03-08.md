时间：2026-03-08
需求：日报分析页智能报告改为“先查询，再点击生成”，不再要求查询前勾选触发。

变更文件：
1) frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

核心实现：
- UI：结果区新增独立“生成智能报告”按钮；下载按钮独立保留。
- 逻辑：
  - runAnalysis 查询流程固定 request_ai_report=false。
  - 新增 triggerAiReport()：基于当前激活单位和当前查询上下文再次调用 query 接口，携带 request_ai_report=true 启动报告任务。
  - 保留既有轮询 startAiReportPolling(jobId)。
- 状态机：
  - 无任务时不再置为 pending，改为 idle + 引导文案（点击生成）。
  - 切换单位时若无 job_id，提示“当前单位尚未生成智能报告，可点击生成”。

效果：
- 日报智能报告触发方式与月报一致，支持查询后按需生成，交互更灵活。