时间：2026-02-28
主题：外部导表程序（外部待导入-导表程序）并入 Phoenix 在线运行可行性调研

一、结论
1) 外部程序业务流程可迁移，但执行内核不可原样线上化。
2) 原因：外部程序核心依赖 xlwings + 本机 Excel（COM），而 Phoenix 当前后端部署是 Linux 容器（python:3.12-slim），不具备该运行前提。
3) 建议路线：保留流程与规则模型，重写执行内核为 openpyxl/纯 Python，可作为 Phoenix 项目内新增导表能力上线。

二、证据（本地文件）
- 外部程序入口与路由：外部待导入-导表程序/app/main.py
- 外部程序执行引擎：外部待导入-导表程序/app/core/engine.py
- 外部程序依赖：外部待导入-导表程序/requirements.txt（含 xlwings）
- 外部程序流程说明：外部待导入-导表程序/README.md、外部待导入-导表程序/项目说明.md
- Phoenix 容器环境：backend/Dockerfile（python:3.12-slim）、docker-compose.yml（backend 为 Linux 容器）
- Phoenix 主填报链：backend/projects/daily_report_25_26/api/legacy_full.py（template/submit/query 与 Coal_inventory_Sheet 分支）

三、本轮留痕文件
- configs/progress.md：新增“2026-02-28（外部导表程序接入可行性调研）”
- backend/README.md：新增“最新结构与状态（2026-02-28）”
- frontend/README.md：新增“最新结构与状态（2026-02-28）”

四、影响范围与回滚
- 本轮仅文档更新，无业务代码行为变更。
- 回滚方式：删除上述三个文件新增的 2026-02-28 小节即可。