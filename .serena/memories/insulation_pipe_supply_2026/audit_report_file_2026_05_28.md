# tube 项目审计报告文件生成记录

时间：2026-05-28

## 前置说明
当前 Serena 工具未暴露 Markdown 文件新建/编辑能力，本轮按项目降级规则使用 `apply_patch` 在仓库内创建审计报告。影响范围仅为文档，不涉及业务代码。

## 新增/修改文件
- 新增：`configs/tube_audit_report_2026-05-28.md`
- 更新：`configs/progress.md`
- 更新：`frontend/README.md`
- 更新：`backend/README.md`

## 报告内容
审计报告覆盖 tube 项目当前主要逻辑风险：
1. 全局管理员物流编辑入口绕过状态机。
2. 库存、净缺口、硬缺口多处计算且负库存策略不一致。
3. Dashboard KPI 与硬缺口由前端重复推导。
4. 物流状态字典、标签、样式和动作规则多处维护。
5. `total_arrived_qty` 字段名与实际计算语义混杂。
6. 日期截止规则隐式。
7. API 返回结构不统一导致前端误用风险。

## 回滚方式
删除 `configs/tube_audit_report_2026-05-28.md`，并移除 `configs/progress.md`、`frontend/README.md`、`backend/README.md` 中本轮新增的审计报告生成记录即可。