前置说明（偏差登记）
- 时间：2025-10-27T00:00:00+08:00
- 触发：用户明确要求“优先使用 desktop-commander 工具”。
- 偏差：未按流程先调用 Serena activate/check_onboarding；直接使用 Desktop Commander 进行代码检索与阅读。
- 原因：遵从《AGENTS.md 1.2 执行优先级》—用户显式命令优先。
- 影响范围：仅限本次仓库内检索与评估，不含写操作；后续真正改动仍会在 Serena 记忆中留痕。
- 回滚思路：若需严格遵循 Serena 优先，可补做 serena__activate_project 与 check_onboarding，并将本次操作摘要补录（本条即为补录）。

任务背景摘要
- 目标：将“6.供热公司分中心明细表”（GongRe_branches_detail_Sheet）的读写，从表 `gongre_branches_detail_data` 统一到 `daily_basic_data`。
- 口径变化：以“中心字典”中 center 英文名/中文名分别对应 `company`/`company_cn`；其它字段随原逻辑。
- 期望：前端行为保持不变（提交/查询接口相同），后端内部落库与读取统一到 `daily_basic_data`，减少分支复杂度。