日期：2025-12-27
文件：backend/api/v1/daily_report_25_26.py、configs/progress.md
摘要：修正 AI 设置接口路由。原先 FastAPI 装饰器写成 `/projects/{project_key}/data_analysis/ai_settings`，但 router 已由 `/projects/daily_report_25_26` 前缀包裹，导致前端请求 404。现改为 `/data_analysis/ai_settings` 并移除多余的 `project_key` 形参，系统管理员校验逻辑保持不变。progress.md 已记录原因与回滚方式。