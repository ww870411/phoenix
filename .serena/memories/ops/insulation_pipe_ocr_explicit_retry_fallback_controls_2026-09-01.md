# 单据识别失败处理显式策略（2026-09-01）

## 背景
此前审计（`mem:audit/ocr_tool_stuck_loading_2026-09-01`）确认 OCR 链路存在函数内重试、自动追加官方备选模型和无条件兜底，造成一次识别可能串行等待多次模型超时。按用户要求，策略改为由全局管理员明确选择。

## 配置与默认值
`ocr_tool_config` 新增字段：
- `enable_fallback`: 是否在主模型失败后调用手填备选模型，默认 `false`。
- `retry_primary_on_error`: 是否在主模型报错、繁忙、超时等情形重试，默认 `false`。
- `primary_retry_count`: 额外重试次数，后端限于 0～5，默认 0。

历史配置不含这些字段时均按关闭解释。全局管理页在重试未启用时显示 1 次但禁用选择器；保存后会把选择值写入配置，运行时仅在重试开关为真时使用它。

## 运行规则
`_call_gemini_vision` 改为单次 HTTP 请求，不再内部 sleep/retry。`_call_gemini_vision_with_fallbacks` 的顺序为：主模型首次调用 ->（仅已启用）主模型额外重试 ->（仅已启用）手填模型 2 / 模型 3。任何错误（含 403、429、503、连接/读取超时）均通过此顺序处理。不会再注入官方默认模型池。

## 涉及模块
- `frontend/src/projects/insulation_pipe_supply_2026/pages/GlobalManagementView.vue`
- `backend/projects/insulation_pipe_supply_2026/services/config_service.py`
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- `backend/projects/insulation_pipe_supply_2026/services/ocr_tool_service.py`
- `backend/projects/insulation_pipe_supply_2026/tests/test_config_service_dates.py`

全局配置区块和 `GET/POST /tools/ocr-config` 均透传同一字段。

## 验证
- `python -m pytest backend/projects/insulation_pipe_supply_2026/tests/test_config_service_dates.py`：12 passed（仅既有 Pydantic/依赖弃用告警）。
- `npm --prefix frontend run build`：成功；仅 Vite 大 chunk 告警。
- `git diff --check`：通过。

仍需使用管理员登录态在浏览器中保存一次配置并上传单据，完成真实 API/UI 回归。