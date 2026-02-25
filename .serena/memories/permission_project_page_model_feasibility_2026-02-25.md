日期：2026-02-25
主题：权限文件按“项目>页面”组织可行性

结论：可行。

建议方案：
1) permissions.json 新增 projects 结构，示例：groups.<group>.projects.<project_key>.page_access/sheet_rules；actions/units_access 可允许项目级覆盖。
2) auth_manager 解析层做双栈兼容：优先读取 projects.*，缺失则回退旧平铺字段。
3) 后端 list_project_pages 使用 project_id 读取对应项目页面权限；项目接口动作权限逐步切到项目级读取，保留旧逻辑兜底。
4) 前端 store/auth.js 过滤函数增加 projectKey 入参，优先用项目级权限，回退旧平铺权限。

迁移策略：
- 第一阶段：代码先支持双结构；
- 第二阶段：权限文件逐组迁移到 projects 结构；
- 第三阶段：验证完成后可清理旧平铺字段（可选）。

本次改动文件：
- configs/progress.md
- backend/README.md
- frontend/README.md

说明：本轮仅方案评估，无业务代码修改。