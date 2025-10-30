# 进度记录

## 2025-10-29（会话开始：问候/初始化）

前置说明（降级留痕）：
- 已按 AGENTS 规范先调用 Serena 完成“项目激活 + 入职检查”。
- 本次仅为问候与初始化，无代码变更；需要将对话与动作留痕至仓库文档。
- 由于涉及 Markdown 文档编辑（非符号文件），依据 3.9 矩阵安全降级使用 `apply_patch` 进行写入，并将在 Serena 记忆中补录时间戳、文件清单与变更摘要。

本次动作：
- Serena：`activate_project(D:\编程项目\phoenix)` 与 `check_onboarding_performed()` 成功。
- 目录扫描：完成项目根目录 2 层结构快照（用于本地理解，不落盘）。
- 文档维护：在 `backend/README.md` 与 `frontend/README.md` 追加“会话小结（无代码改动）”。

影响范围与回滚：
- 仅文档新增小节；如需回滚，可删除本条与两个 README 中对应小节，不影响任何代码与接口。

下一步建议：
- 请告知本轮具体开发目标（接口/脚本/页面），我将据此更新计划并实施变更；如无特别指令，将优先补齐 `/template`、`/submit`、`/query` 的最小闭环联调样例。

## 2025-10-29（审批页面空白修复：runtime 适配 groups 视图）

前置说明（降级留痕）：
- 根据 10.29提示词.md [16:55] 的问题，`ZhuChengQu_approval_Sheet` 在模板中设置 `查询数据源.主表=groups`，但后端 `runtime_expression.py` 固定从 `sum_basic_data` 取数，导致 company=`ZhuChengQu` 无匹配记录而整表空白。
- 本次为 Python 源码修复，直接使用 `apply_patch` 小步修改，并在此留痕；后续将把验证结果补录至 Serena 记忆。

变更内容：
- 新增函数 `_fetch_metrics_from_view(session, table, company)`，白名单允许 `sum_basic_data|groups`；当模板指定 `主表=groups` 时，改为读取 `groups` 视图。
- 原 `_fetch_metrics_from_matview` 被替换为更通用的 `_fetch_metrics_from_view` 调用；动态日期路径仍保持直接聚合底表的实现不变。

影响范围与回滚：
- 仅影响 runtime 模式下的求值来源切换；如需回滚，改回固定表名 `sum_basic_data` 即可。

后续建议：
- 请确认数据库中 `create_view.sql` 已成功创建 `sum_basic_data` 与 `groups`；若 `groups` 未成功创建（10.29日志中出现 CTE 顺序错误提示），请先修正 SQL 后再验证本修复效果。

## 2025-10-29（SQL 校验：主城区直接收入等式）

结论：成立。
- `sum_basic_data` 中 `calc_direct_income` 明确定义为五项之和：
  - 售电收入（`calc_power`）+ 内售热收入（`calc_inner_heat`）+ 暖收入（`calc_heating_income`）+ 售高温水收入（`calc_hot_water`）+ 售汽收入（`calc_steam`）。
  - 证据：backend/sql/create_view.sql:706、713、720-727；组件 CTE 见：344（售电）、360（内售热）、392（暖收入）、414（售高温水）、437（售汽）。
- `groups` 视图以 `s AS (SELECT * FROM sum_basic_data)` 为来源并按公司集合聚合；`base_zc/base_grp` 会把上述“直接收入”以及“五项分项收入”分别求和汇总到主城区（ZhuChengQu）与集团（Group）。因此在分组层面同样满足：
  `ZhuChengQu.直接收入 = ZhuChengQu.(售电+内售热+暖+售高温水+售汽)`。
  - 证据：backend/sql/create_view.sql:960 起（groups 定义），`base_zc` 聚合来源于 `sum_basic_data` 的 item 全量（仅对比率等特殊项另行重算）。

备注：若实际对比发现不相等，优先检查 `sum_basic_data` 是否已成功创建且包含上述六个 item；其次检查分组视图是否过滤了这些 item（当前版本未过滤）。

## 2025-10-29（指标修正：groups 主城区直接收入口径）

前置说明：
- 根据 `configs/10.29计算指标修正.md`：groups 视图中 company=ZhuChengQu 的“直接收入”应等于“其中：售电收入 + 其中：暖收入 + 其中：售高温水收入 + 其中：售汽收入”（不含“内售热收入”）。

改动内容：
- 修改 `backend/sql/create_view.sql` 的 `groups` 定义：
  - 在“主城区：量/金额类直接汇总”分支中，将 `eco_direct_income` 从直汇名单中排除；
  - 新增一段 `UNION ALL` 重算主城区 `eco_direct_income` 为上述四项之和，分别对应 value_biz_date/value_peer_date/sum_7d_*/sum_month_*/sum_ytd_*。

影响范围与回滚：
- 仅影响 `groups` 视图中 `company='ZhuChengQu'` 的 `eco_direct_income` 行；其它公司与其它指标不受影响。
- 回滚方式：恢复直汇（将 `eco_direct_income` 从排除列表移除，并删除重算片段）。

sum_basic_data 相关：
- 文档同时要求将“边际利润/可比煤价边际利润”引入外购热成本与内购热成本；现有 `create_view.sql` 已包含这两项，无需改动。

## 2025-10-29（审批占位符透传修复）

问题：
- `backend_data/数据结构_审批用表.json` 中 `GongRe_approval_Sheet` 的“突发情况说明”行，在非数值列使用了占位符（如“——”），但渲染为空。

原因：
- `backend/services/runtime_expression.py` 在渲染阶段对非只读列一律尝试按表达式求值；求值失败或空值返回 `None`，最终显示逻辑将 `None` 映射为空串，导致占位符被吞掉。

修复：
- 统一占位符为单字符 `-`：当单元格求值结果为 `None` 且原始文本为 `-` 时，显示 `-`；其它文本不再作为占位符处理。
- 代码位置：`backend/services/runtime_expression.py`（新增 `_is_placeholder()` 并在显示阶段仅对 `-` 占位）。

影响与回滚：
- 仅影响非表达式文本在审批/展示模板中的显示；不改变数字/比率/表达式的求值逻辑。
- 回滚：移除新增的占位符透传分支即可恢复原行为。

## 2025-10-29（常量页无数据：前端未触发常量查询）

问题：
- 表 `constant_data` 已有数据，但“常量指标页面”不显示。原因是前端 `DataEntryView.vue` 仅在模板类型为 `standard` 或 `crosstab` 时调用 `/query`，`constant` 类型未触发查询。

改动：
- 前端 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`：在 `loadTemplate()` 中为 `templateType==='constant'` 增加一次 `queryData` 调用，并使用 `applyStandardQueryResult(q)` 回填 `columns+rows`。
- 不需要 `biz_date`，period 标签由后端按列头“(本供暖期)/(同供暖期)”映射为 `25-26/24-25`。

- 后端 `backend/api/v1/daily_report_25_26.py::get_sheet_template`：补齐常量模板类型识别，`_is_constant_sheet(sheet_key)` 时返回 `template_type='constant'`，避免前端误判为 `standard`。

影响与回滚：
- 仅影响常量页首屏加载的回填显示；其他模板不受影响。回滚删除该分支即可。

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
  1) `内售热收入` 使用的单价是否等同于常量表的“售热单价”（`price_heat_sales`）？文档中未出现“内售热单价”常量条目。\\n  2) `days_to_biz()` 是否对每个时间口径分别取“从该口径起点到口径末日的天数”（如：7日口径=7，本月口径=当月日序，本供暖期口径=自10-01起的天数；同理用于同期口径）？\\n  3) `全厂热效率` 返回单位为`%`，是否需要四舍五入到小数点后两位？\\n  4) 字典中存在 `eco_inner_purchased_heat_cost`（内购热成本）、`eco_heat_lose`（网损成本）等，但公式未定义，是否需要补充？\\n  5) 常量 period 取值：是否统一按供暖期编码映射（biz=当年“YY-YY+1”，peer=上一年“YY-1-YY”）？\\n  6) 对于公司 {JinZhou, BeiFang, JinPu, ZhuangHe, YanJiuYuan} 的“站内耗热量”优先使用推导式（供热量-高温水销售量），如底表已填同名指标是否仍以推导覆盖？\\n- SQL 设计建议：在 `sum_basic_data` 基础 CTE 上“按公司聚合+按 item 条件汇总出 8 口径值”，再 `UNION ALL` 生成计算指标行为新 item（如 `eco_direct_income`），常量按 period（二套：biz/peer）左连接；`groups` 视图自然对新计算项做再聚合。\\n- 等待你的确认后，将一次性补齐完整 SQL（含口径天数与异常口径保护 `NULLIF(...,0)` + `COALESCE(...,0)`）。

## 2025-10-30

前置说明：
- 延续仓库规范，已通过 Serena 执行项目激活与上手检查；运行时代码通过 `serena__replace_symbol_body` 修改。
- Markdown 文档（progress / README）因 Serena 暂不支持直接写入，按 3.9 降级矩阵使用 `apply_patch`，本条记录作为留痕。
- 排障依据：`configs/10.30trace.md` 中 `safe_expr` 报错（`unmatched ')'`）与数据展示页“省市平台净投诉量”空值。

本次改动：
- 修复 `runtime_expression.Evaluator._preprocess` 对帧函数参数的解析，支持 `I(...)` 含括号一次捕获，避免生成 `value_biz_date("I("...` 导致语法错误。
- 对多指标累加的 `value_*` 调用在二次遍历阶段拆分为多个 `value_*("名称")` 相加，确保“不可加指标”仅返回单值。
- 新增 `c.<公司>.<常量>` 跨单位常量读取：解析表达式中的公司码并预取对应常量，解决“万平方米省市净投诉量”分母为 0 的问题。
- README 补充运行时表达式调试提示，提醒通过 `_trace` 检查帧函数入参展开情况。
- 新增展示表二（`Group_analysis_brief_report_Sheet`）跨列交叉表支持：
  - 解析 `列名1/列名2` 多级表头并生成 `column_headers`+`column_groups` 元数据；
  - 列级 company 映射 + 多 company evaluator 缓存，按日口径求值 `value_biz_date()/value_peer_date()`；
  - `date_diff_rate()` 按列组（公司维度）计算，支撑复数差异列；
  - 前端 `RevoGrid` 启用列分组与多行表头排版，保留追踪信息。

验证：
- 运行临时脚本直接调用 `_preprocess`，确认 `value_biz_date(当日撤件后净投诉量)` 输出 `value_biz_date("当日撤件后净投诉量")`，`value_biz_date(当日撤件后净投诉量+本月累计净投诉量)` 拆分为两个 `value_biz_date("…")` 相加。
- 执行 `render_spec(..., trace=True)` 重产 `configs/10.30trace.md`，确认 `used_consts` 中 `c.GongRe.挂网面积` 等返回实际数值，分母不再为 0；新表 `Group_analysis_brief_report_Sheet` 返回 `column_headers`+`column_groups`，并针对每家公司输出日口径差异。

涉及文件：
- 更新：`backend/services/runtime_expression.py`、`backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue`、`backend_data/数据结构_全口径展示表.json`、`configs/10.30trace.md`、`configs/progress.md`、`backend/README.md`、`frontend/README.md`

影响范围与回滚：
- 如需回滚，可恢复 `_preprocess` 至 2025-10-27 版本并撤销本条文档说明；届时“省市平台净投诉量”会再次返回空值并在 `10.30trace.md` 重现 `unmatched ')'` 错误。若仅需撤销交叉表渲染，可恢复本条涉及的 `runtime_expression.py`/`DisplayRuntimeView.vue`/`api` 改动并还原配置文件。

## 2025-10-31

前置说明：
- 依照 AGENTS 规范，仍先通过 Serena 激活项目与检查上手；由于 Serena 在 `create_view.sql` 等纯文本 SQL 上仅能返回定位信息，无法直接读取上下文，本次根据 3.9 降级矩阵改用 Desktop Commander 的 `read_file`/`apply_patch` 操作；此处留痕，稍后会在 Serena 记忆补录。

本次改动：
- 新增视图 `sum_coal_inventory_data`：聚焦 `coal_inventory_data` 最新日期数据，按 `company + storage_type` 汇总 `value` 并保留 `unit`。
- 追加公司级与集团级汇总行：为各公司生成 `storage_type='all_sites'`（中文名“全部地点”）的合计行，同时输出 `company='ZhuChengQu_sum'`、`company='Group_sum'` 等聚合键以匹配模板中的 `scid.*` 写法。
- 运行时表达式支持 `scid.*`：`render_spec` 在加载常量别名时识别 `sum_coal_inventory_data`，按公司提取 `*_sum` 聚合值并在所有时间帧返回相同结果，解决“库存煤量（含港口、在途）”空白问题。

涉及文件：
- 更新：`backend/sql/create_view.sql`、`backend/services/runtime_expression.py`

验证：
- 通过 CTE 锁定最大日期后再做分组，确保空表不会产出虚假汇总；`MAX()` 保留单位/中文名，避免混合口径带来 NULL。
- 运行 `render_spec` 针对 `Group_analysis_brief_report_Sheet` 启用 `trace=True`，可在 `_trace.used_consts` 中看到 `scid.Group_sum`、`scid.JinZhou_sum` 等命中最新库存值。

影响范围与回滚：
- 若需恢复旧行为，可删除新增的 `sum_coal_inventory_data` SQL 段并重新执行脚本；恢复后最新库存的公司级/集团级汇总行将不再提供。若仅需移除 `scid` 支持，可恢复 `runtime_expression.py` 中别名加载逻辑至本条前版本。

下一步建议：
- 如需将该视图用于运行时表达式或展示页，可在后端补充查询接口，并确认 `company_cn` 与 `storage_type_cn` 的展示文案是否需要进一步本地化。

## 2025-11-01

前置说明：
- 继续按 AGENTS 流程激活 Serena 项目并检索上下文；对 Vue 文件与 JSON 模板因 Serena 暂不支持完整渲染，依 3.9 降级矩阵使用 Desktop Commander `read_file`/`apply_patch`，本条作为留痕。

本次改动：
- `backend/services/runtime_expression.py`：解析模板 `accuracy` 字典时生成 `accuracy_map`，按行（项目中文名）计算精度覆盖并在回填阶段应用不同小数位；新增 `accuracy_map` 字段输出。
- `backend/api/v1/daily_report_25_26.py`：透传 `accuracy_map` 为响应字段 `accuracy_overrides`，默认值沿用 `accuracy`。
- `frontend/src/daily_report_25_26/pages/ApprovalView.vue`：新增模板精度加载逻辑，通过 `getTemplate` 读取 `accuracy` 配置并解析 `default+分项`，按“项目”列定位行标签，将 RevoGrid 每行数值格式化与 `Intl.NumberFormat` 缓存绑定，实现审批页分项小数位控制。
- `frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue`：同步引入分项精度解析与格式化，支持展示页在同一表中按“项目”配置不同小数位；优先使用后端返回的 `accuracy_overrides`，模板请求作为兜底，保留差异列百分比格式及列分组渲染。
- `backend/services/runtime_expression.py`：扩展 `value_*` 系列函数参数解析，优先将括号内内容视作公司编码（支持中文/英文与 `A+B` 组合），并在预取阶段按需加载多 company 指标；运行时根据参数动态切换公司或降级为项目/常量读取。
- `backend/services/runtime_expression.py`：`date/sum_month/sum_ytd_diff_rate` 仅在单元格显式填写时才计算；空表达式的“日/月/供暖期差异”列保持空白，避免模板中用于分隔的行被强制填入 `-`。
- `backend/services/runtime_expression.py`：新增 `company.item` 解析（如 `value_biz_date(GongRe.本月累计净投诉量)`），优先按英文 item 反查中文名称再取值，默认表仍遵循模板 `default` 路由逻辑。

验证：
- 通过手动审查 `render_spec` 行级量化与前端 `buildSource` 输出逻辑，确认含 `%` 的差异列仍返回字符，不受小数位影响；建议在前端运行环境下分别加载 `Group_sum_show_Sheet` 与 `Group_analysis_brief_report_Sheet`，观察“万平方米省市净投诉量”等配置项是否以 2 位小数展示，其余保持模板默认精度。
- 针对新模板 `ZhuChengQu_sum_show_Sheet` 逐项检查 `value_biz_date(ZhuChengQu)`、`value_biz_date(BeiHai+XiangHai)` 等写法能正确取到目标公司指标，组合求和等价于逐项累加。
- 多段标题（如“二、热源厂”）所在行的差异列未填写 `date_diff_rate()` 时，应在审批/展示页保持为空。

影响范围与回滚：
- 变更主要影响审批页(`ApprovalView`)、展示页(`DisplayRuntimeView`)的渲染逻辑以及运行时表达式的行级精度；若需回滚，可还原上述文件至本次改动前版本，或删除后端 `accuracy_map` 相关逻辑并恢复统一小数位行为。
- 若需恢复旧的单 company 求值，可还原 `runtime_expression.py` 中 `_resolve_company_item/_value_of_item` 调整，并将 `companies_needed` 解析段落改回仅按行默认 company 读取。
