# 进度记录

## 2025-10-29（示例数据与命名修正）

前置说明：
- 按 AGENTS 全局指南，已使用 Serena 激活项目并完成上手检查；后续文件读写均通过 `apply_patch` 执行（不使用 cmd/pwsh）。本次修正覆盖“示例数据生成逻辑 + 命名规范统一”，并在此留痕，稍后会将摘要补录至 Serena 记忆。

本次改动：
- 修复命名：中心英文码统一为 `*_Center`；`sheet_name` 统一为 `*_Sheet`（S 大写）。
- 更新 `backend/scripts/generate_daily_basic_sample.py`：
  - 由“仅本期”改为“本期+同期”，且满足关系“本期=同期×1.25（提高25%）”；
  - 生成时同步应用 `*_Center` 与 `*_Sheet` 规范。
  - 修复 item 键来源：严格按 backend_data/数据结构_基本指标表.json 的“项目字典”（权威）生成 item 与 item_cn；若字典缺失即抛错（不做任何猜测与回退）。
- 新增 `backend/scripts/generate_constant_sample.py`：
  - 读取 `backend_data/数据结构_常量指标表.json`；
  - 生成 period=`24-25`（同期）与 `25-26`（本期）两期数据，满足“本期=同期×0.8（下降20%）”；
  - 统一 `*_Center` 与 `*_Sheet` 命名；输出到 `backend/sql/sample_constant_data.(csv|sql)`。
  - 修正分中心常量表“公司/中心”字段语义：将中心作为 `company/company_cn` 输出，`center/center_cn` 置空（与 daily_basic_data 对齐）。
  - 同步修复 item 键来源：严格按常量模板“项目字典”生成键名，若缺失则抛错（不猜测）。

涉及文件：
- 更新：`backend/scripts/generate_daily_basic_sample.py`
- 新增：`backend/scripts/generate_constant_sample.py`
- 文档：`backend/README.md`、`frontend/README.md`

影响范围与回滚：
- 若需要恢复旧命名（`*_center`/`*_sheet`）或旧同比关系，可回退对应脚本至本条之前的版本；已在 README 标注输出文件路径，便于对比与替换。

下一步建议：
- 如需我直接把 CSV/SQL 成品也落盘（体量较大），请确认后我将以 `apply_patch` 方式一次性写入 `backend/sql/` 目录，便于直接导入数据库。

补充（2025-10-29 晚）：
- daily 示例脚本：模板来源固定为 `backend_data/数据结构_基本指标表.json`；跳过 `Coal_inventory_Sheet`（交叉表归属 `coal_inventory_data`）；严格用同表“项目字典”反查 item，不命中直接报错，并在报错中列出前 30 个可用中文项。
- constant 示例脚本：模板来源固定为 `backend_data/数据结构_常量指标表.json`；分中心常量表将“中心”作为 `company/company_cn`；严格用“项目字典”反查 item，不命中直接报错，并在报错中列出前 30 个可用中文项。

## 2025-10-29

前置说明：
- 本次根据 `configs/10.29提示词.md` 的要求，优先使用 Desktop Commander 工具进行文件读取与编辑。会话开始时为遵循仓库 AGENTS 规范先行调用了 Serena 进行项目激活与上手检查；随后已切换为 Desktop Commander 优先。该偏差已在此处留痕并将在 Serena 记忆中补录。

本次改动：
- 拆分视图职责：将 `sum_basic_data` 还原为“公司明细粒度（无分组）”，新建独立分组视图 `groups` 复用 `sum_basic_data` 进行再聚合。
- 未引入“计算指标”逻辑，等待业务公式与常量 period 口径确认后再补充。

涉及文件：
- 更新：`backend/sql/create_view.sql`

影响范围与回滚：
- 查询分组口径的下游改为读取 `groups` 视图；如需回滚，可将 `groups` 中两段 `SELECT ... GROUP BY` 合并回 `sum_basic_data`（参照 git 历史或本次提交前版本）。

下一步计划：
- 确认收入/成本/利润/单耗/效率等“计算指标”所依赖的底表 item/constant 名称与单位，以及 `constant_data.period` 的取值规范；据此在 `sum_basic_data` 中追加“计算指标”行或列（建议追加为行，item=计算项）。

## 2025-10-29 公式解析与待确认
- 已阅读：`configs/10.29建视图公式.md`，整理了“直接收入/成本/利润/单耗/效率/投诉量/网损热量”等公式与中英文 item 映射，以及 `c.xxx` 常量清单。
- 存疑点（待你确认）：
  1) `内售热收入` 使用的单价是否等同于常量表的“售热单价”（`price_heat_sales`）？文档中未出现“内售热单价”常量条目。\n  2) `days_to_biz()` 是否对每个时间口径分别取“从该口径起点到口径末日的天数”（如：7日口径=7，本月口径=当月日序，本供暖期口径=自10-01起的天数；同理用于同期口径）？\n  3) `全厂热效率` 返回单位为`%`，是否需要四舍五入到小数点后两位？\n  4) 字典中存在 `eco_inner_purchased_heat_cost`（内购热成本）、`eco_heat_lose`（网损成本）等，但公式未定义，是否需要补充？\n  5) 常量 period 取值：是否统一按供暖期编码映射（biz=当年“YY-YY+1”，peer=上一年“YY-1-YY”）？\n  6) 对于公司 {JinZhou, BeiFang, JinPu, ZhuangHe, YanJiuYuan} 的“站内耗热量”优先使用推导式（供热量-高温水销售量），如底表已填同名指标是否仍以推导覆盖？\n- SQL 设计建议：在 `sum_basic_data` 基础 CTE 上“按公司聚合+按 item 条件汇总出 8 口径值”，再 `UNION ALL` 生成计算指标行为新 item（如 `eco_direct_income`），常量按 period（二套：biz/peer）左连接；`groups` 视图自然对新计算项做再聚合。\n- 等待你的确认后，将一次性补齐完整 SQL（含口径天数与异常口径保护 `NULLIF(...,0)` + `COALESCE(...,0)`）。
