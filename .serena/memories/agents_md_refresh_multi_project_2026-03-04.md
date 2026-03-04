时间：2026-03-04
用户请求：更新根目录 AGENTS.md，保留 Codex 系统性执行要求，同时将项目结构与风格要求更新为最新版本。
实施：
1) 重写 AGENTS.md：从初期单项目说明升级为“当前多项目协作规范”。
2) 保留并强化强制规则：
- 使用原生文件工具（apply_patch 等）读写；
- 每轮同步 configs/progress.md、frontend/README.md、backend/README.md；
- 交付需说明模块/函数/流程/结果。
3) 更新结构口径：
- 前端：frontend/src/projects/{daily_report_25_26,daily_report_spring_festval_2026,monthly_data_pull,monthly_data_show}
- 后端：backend/projects/{daily_report_25_26,daily_report_spring_festval_2026,monthly_data_pull,monthly_data_show}
4) 补充可改/禁改范围、风格要求、质量安全底线与执行清单。
文档留痕：
- configs/progress.md
- frontend/README.md
- backend/README.md
结果：AGENTS.md 已可直接指导当前多项目并行开发，不再与现状脱节。