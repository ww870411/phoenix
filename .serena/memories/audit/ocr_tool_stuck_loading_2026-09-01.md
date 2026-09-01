# 业务单据智能识别长时间 loading 审计（2026-09-01）

## 范围
只读审计：
- frontend/src/projects/insulation_pipe_supply_2026/pages/DeliveryBillOcrTool.vue
- frontend/src/projects/daily_report_25_26/services/api.js
- backend/projects/insulation_pipe_supply_2026/api/workspace.py
- backend/projects/insulation_pipe_supply_2026/services/ocr_tool_service.py
- backend_data/projects/insulation_pipe_supply_2026/tube_config.json
- phoenix_backend 运行日志

## 结论
1. 主要根因是后期新增的串行多模型兜底。每个模型底层 httpx 超时 45 秒；主模型失败后才试下一模型，候选池还会自动追加模型，理论等待可累加到数分钟。
2. 运行配置为主模型 gemini-3.5-flash-lite，备选首先是 gemini-3.1-flash-lite、gemini-3.7-flash。2026-09-01 14:48-14:49 左右的日志显示主模型 504 超时，约 57 秒后接口由备选模型成功返回 HTTP 200。
3. 前端 ocrDeliveryBill 使用普通 fetch，没有 AbortController、请求总 deadline、取消入口；loading 只在 Promise resolve/reject 后清除，且等待文案固定，所以后端 pending 时用户只能看到“正在使用 AI 视觉模型解析单据内容与表格...”。
4. 开发期日志曾出现 NameError: time 未定义、NameError: primary_model 未定义，均导致 OCR 接口 500；当前工作区代码已不再引用错误变量并已导入 time，但反映该链路经历过未稳定的热修改。
5. 当前工作区存在未提交的降耗修改：前后端默认 enable_double_check=False；这只能减少第二阶段调用，不能解决第一阶段主模型 45 秒超时、串行多模型累计和前端无限等待问题。
6. 最近多次 OCR 请求最终返回 200，因此“始终不返回”在当前日志下更准确地说是约一分钟无阶段反馈；若用户页面在 200 后仍保持 loading，需要在同一登录会话的 DevTools 中核对该请求响应与 Vue 运行时异常。此次独立审计浏览器因无登录态被重定向到 /login。

## 建议修复优先级
P0：为整次识别设置硬 deadline（例如 60 秒）并取消后续模型；前端 AbortController + 明确超时错误与取消按钮。
P0：仅对明确可恢复错误执行兜底，并限制模型总数/单模型连接与读取超时；不要无界追加官方池。
P1：首选模型做健康检查或根据最近成功率动态排序，避免每次固定先支付 45 秒失败成本。
P1：将模型尝试阶段通过任务状态或 SSE/轮询返回前端，至少显示“主模型超时，正在切换备选模型”。
P1：补充时间预算测试、主模型超时后备选成功测试、全部模型失败的总耗时测试和前端超时恢复测试。
