时间：2026-02-28
主题：monthly_data_pull 功能口径收敛为仅支持 xlsx（撤回 xls 兼容）
触发：用户明确“不必兼容 xls，只会上传 xlsx”。

变更文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) backend/requirements.txt
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

实施内容：
- 移除 engine.py 中所有 xlrd/.xls 适配代码与分支。
- 源文件读取恢复为统一 openpyxl。
- requirements.txt 移除 xlrd 依赖。
- 文档与进度记录补充“仅支持 xlsx”的最终口径。

结果：
- 登录链路不会再受 xlrd 依赖影响；
- 导表模块技术边界清晰：只处理 xlsx。