# 后端说明（FastAPI）

# 会话小结（2025-12-27 AI 智能体设定接口供前端接入）

- FastAPI 先前已提供 `GET/POST /projects/{project_key}/data_analysis/ai_settings`，读取与写入 `backend_data/api_key.json` 的 `gemini_api_key/gemini_model`。本轮前端已接入该接口，并限制仅 `Global_admin` 触发，后端无需额外改动。
- 若需联调，请确认 `AI_SETTINGS_PATH`（`backend_data/api_key.json`）具备读写权限，且调用入口的用户组为“系统管理员”或 `Global_admin`（由 `_ensure_system_admin` 校验）。否则接口会返回 403。
- 若未来要扩展更多字段，可在 `AiSettingsPayload`、`_read_ai_settings/_persist_ai_settings` 中补充键，再通知前端追加表单项即可；当前保持 `api_key/model` 双字段结构。
- `api_key.json` 新增 `instruction` 字段，并在 `data_analysis_ai_report.py` 中通过 `_load_instruction_text` 注入三个 Prompt 模板（在模板最前端输出 `### AI 指令（最高优先级）`）；如无需额外指令可留空，LLM 会继续使用默认模板。
- 同一配置文件新增 `enable_validation`（默认 True）与 `allow_non_admin_report`（默认 False）字段：前者决定 AI 报告是否执行第 4 阶段“检查核实”，后者控制非 Global_admin 账号能否勾选“智能报告生成”。Schema API 会透出 `ai_report_flags` 供前端渲染，`/data_analysis/query` 也会在 flag 未开启时自动忽略非授权的请求。

# 会话小结（2025-12-31 AI 报告核查自动修订）

- **新增修订阶段**：`backend/services/data_analysis_ai_report.py` 在 validation（第 4 阶段）返回 `warning/fail` 且存在 issues 时，自动进入“内容修订”阶段，再次调用 LLM 根据问题列表重写 `section_contents/callouts`，确保所有指摘被修正。
- **Prompt 支撑**：新增 `REVISION_PROMPT_TEMPLATE` 与 `_build_revision_prompt`，向模型提供 processed_data/insight/layout/旧正文/validation JSON，要求维持章节结构并逐条回应 issues。
- **复检机制**：修订后的内容会重新触发 validation，一旦通过才输出最终 HTML，同时 `_jobs[job_id]['stage']` 会依次记录 `revision_pending → revision_content → review`，便于前端进度条显示。

# 会话小结（2025-12-31 计划比较百分比统一）

- **问题**：月度计划 `plan_comparison` 中的 `rate_overall_efficiency` 以 0.8 存储，接口在“计划比较”表及 AI 报告摘要里都显示为 “0.80%”，与其它场景展示的 80% 不一致。
- **改动**：`backend/services/data_analysis.py` 增加 `PERCENTAGE_SCALE_METRICS` 与 `_scale_percentage_metric_value`，在构造 `plan_comparison.entries` 时自动将列入集合的指标乘以 100（仅对数据库原始值进行缩放，避免对 fallback 聚合结果重复乘 100），完成率计算逻辑保持不变。
- **影响**：`/data_analysis/query`、网页“计划比较”板块以及 AI 报告导出的“计划比较”段落都会直接展示 80% 等符合预期的百分比，数据库存储格式无需调整；如需回滚，只需移除该集合与缩放调用。

# 会话小结（2026-01-02 AI 配置简易加密恢复）

- **触发原因**：`backend_data/api_key.json` 长期以明文保存 `gemini_api_key`，虽然方便替换但在协同开发中容易被直接读取。
- **改动内容**：新增 `backend/services/api_key_cipher.py`，通过在明文第 5 个字符后插入固定串 `ww` 实现最小可逆“加密”；`_read/_persist_ai_settings` 保存/读取时分别调用 `encrypt_api_key/decrypt_api_key`，`data_analysis_ai_report.py` 与 `configs/ai_test.py` 也统一使用 `decrypt_api_key`。示例配置文件现已存储插入 `ww` 的密文。
- **影响范围**：FastAPI 返回值与前端交互保持明文体验，只是落盘改为伪加密；AI 报告线程池、测试脚本依然可以透明使用 API Key，部署环境若改用环境变量也不会受影响。
- **验证建议**：调用 `GET /api/v1/daily_report_25_26/data_analysis/ai_settings` 应看到解密后的明文；保存新 Key 后查看 `backend_data/api_key.json`，可见 `ww` 被插入第 5 位；运行 `configs/ai_test.py` 或触发 AI 报告可正常连接 Gemini。

# 会话小结（2025-12-27 全厂热效率累计口径修复）

- 问题：`rate_overall_efficiency` 属于百分比指标，累计模式下不应把逐日值求和；先前 `_execute_data_analysis_query` 在构造 `total_current/total_peer` 时默认对所有非温度指标求和，导致主城区/集团查询时的“全厂热效率”累计值错误。
- 修复：`backend/api/v1/daily_report_25_26.py` 进行了三处调整：① `NON_ACCUMULATION_METRICS = {'rate_overall_efficiency'}`，在 range 模式下遇到该类指标时改为取逐日时间线中“最近的非空值”（即区间末值），避免把百分比累加；② 对 `value_type="analysis"` 的指标在 range 模式下直接使用 `analysis_company_sum/analysis_groups_sum` 视图返回的 `value_biz_date/value_peer_date` 作为 `total_current/total_peer`，彻底与数据库视图保持一致；③ 新增 `PERCENTAGE_SCALE_METRICS`，把 `rate_overall_efficiency` 的本期/同期/总计及逐日取值统一乘以 100，以 0.8 → 80% 的形式对外展示。
- 影响：数据分析页和智能报告在累计模式下读取 `total_current/total_peer` 时即可获得正确热效率；环比/同比计算也随之恢复准确。若后续还有其他“不能求和的指标”，可继续把 key 加入该集合。
- 回滚：恢复 `backend/api/v1/daily_report_25_26.py` 的相关补丁即可。

# 会话小结（2025-12-27 AI 报告环比表百分比修复）

- 问题：API 已把 `rate_overall_efficiency` 从 0.8 → 80 输出，但 AI 报告渲染“环比比较”时仍取 `ringCompare.prevTotals` 的原始小数，导致“上期累计”列显示 0.8%。
- 修复：`backend/services/data_analysis_ai_report.py` 引入 `PERCENTAGE_SCALE_METRICS`，在 `_build_ring_compare_payload` 内对相应指标的 `prevTotals` 值统一乘以 100，确保上期/本期列展示一致。
- 影响：仅影响 AI 报告 HTML 的环比表格，API 主体结果不变。若需回滚，恢复该 Python 文件即可。

# 会话小结（2025-12-27 数据分析接口提前返回上期气温）

- 诉求：数据分析页希望一次请求就拿到“上期区间”的平均气温与环比，无需第二次请求。原实现仅在 `request_ai_report=true` 时才调用 `_compute_previous_range` 并写入 `ringCompare`，导致常规页面首次查询缺少上期平均气温。
- 改动：`backend/api/v1/daily_report_25_26.py` 在累计模式下只要存在分析指标或气温指标，就默认计算上一窗口：按需调用 `_query_analysis_rows`、`_query_temperature_rows` 并写入 `prev_rows_map/prev_temp_rows`，`ringCompare.prevTotals` 因此会包含平均气温，`rows[].ring_ratio` 也能立即得到环比值。
- 影响：数据分析页面第一次调用 `/data_analysis/query` 就能拿到 `ringCompare` 和平均气温的环比，无需再发第二个请求；AI 报告逻辑不再是唯一触发点。若要回滚，只需恢复上述 Python 文件的差异。
- 验证：累计模式下选择含“平均气温”的指标，单次请求即可在响应 `ringCompare.entries`、卡片环比字段中看到“上期平均气温 + 环比%”；无需额外参数。

# 会话小结（2025-12-27 AI 报告同比＆区间明细渲染）

- 目的：与数据分析网页同步，智能报告需补充“同比比较”“环比比较”“区间明细（逐日）”三块表格，同时让指标卡片/图表正确读取常量、气温指标的累计值与环比差异。
- 实施：  
  1. `backend/services/data_analysis_ai_report.py` 的 `_preprocess_payload` 现在保留 `value_type/decimals/timeline_entries`，并调用 `_build_timeline_matrix` 生成逐日矩阵；常量指标的累计值强制等于单值，气温指标累计改为日均。  
  2. `_build_timeline_matrix` 会输出每日数据 + “总计”行，常量复用单值、气温取平均、其余指标求和，同时返回 `summary_row` 供 HTML 渲染。  
  3. `_generate_report_html` 用新的结构渲染“同比比较”“环比比较”表、逐日双表头（日期×本期/同期/同比），卡片展示值改用 `decimals` 精度，折线图仅注入带 timeline 的指标，delta 单元格新增颜色提示。
- 验证：`python -m py_compile backend/services/data_analysis_ai_report.py` 正常；本地调用 `/api/v1/daily_report_25_26/data_analysis/query` 勾选“生成智能报告”后下载 HTML，可看到新增的同比/区间表格与平均气温的环比百分比；常量指标的“本期累计/上期累计”与单日值一致。
- 回滚：恢复 `backend/services/data_analysis_ai_report.py` 即可撤销所有渲染与预处理调整。

# 会话小结（2025-12-27 AI 报告环比字段补齐）

- 问题：AI 报告多阶段流程的预处理只输出了 `ring_fmt`（字符串），Prompt 中引用的 `ring` 字段始终为 `null`，导致洞察/段落无法写出环比结论。
- 修复：`backend/services/data_analysis_ai_report.py` 在 `_preprocess_payload` 中新增 `ring` 数值字段（直接透传 `ring_ratio`），模板仍保留 `ring_fmt/ring_color` 供 HTML 卡片使用。
- 验证：`python -m py_compile backend/services/data_analysis_ai_report.py` 通过，触发报告后 `_jobs[job_id]['payload']['metrics']` 可看到 `ring` 有实际数值，模型输出的 JSON 也重新包含环比描述。
- 回滚：恢复该文件即可。

# 会话小结（2025-12-27 AI 报告环比比较板块）

- 问题：虽然 `ring_ratio` 已对外暴露，但 AI 报告未自动呈现与前端一致的“环比比较”板块，原因是流水线既未向 Prompt 提供 `ringCompare` 数据，也没有在 HTML 模板里渲染该段。
- 处理：\n  - `backend/api/v1/daily_report_25_26.py` 在 `request_ai_report=true & analysis_mode=range` 场景下，自动计算上一窗口（`_compute_previous_range`），按指标查询上一窗口的聚合值与气温平均值，写入响应 `ringCompare = { range, prevTotals, note }`，无需前端二次请求即可取得同样数据。\n  - `backend/services/data_analysis_ai_report.py` 新增 `_build_ring_compare_payload`，将 `ringCompare` 转换为 entries、范围标签与摘要写入 `processed_data['ring_compare']`；`_generate_report_html` 渲染“环比比较”表格（指标 / 本期 / 上期 / 环比）及【环比】摘要或 warning，确保 AI 报告可视化与网页一致。
- 验证：`python -m py_compile backend/services/data_analysis_ai_report.py` 通过；生成报告后 HTML 中出现“环比比较”段，表格数据与摘要均与前端一致，Prompt 中也能引用该结构。
- 回滚：恢复该 Python 文件即可撤销本次增强。

# 会话小结（2025-12-27 数据分析区间温度 timeline 修复）

- 症状：累计模式仅勾选“平均气温”等气温指标时，数据分析页的“区间明细（逐日）”不再渲染温度列。排查 `backend/api/v1/daily_report_25_26.py` 发现 API 仍使用 legacy 流程，`timeline_rows_map` 只在存在常规指标时才构建，且未给常量/气温行注入逐日数据。
- 变更：新增 `_build_constant_timeline/_build_temperature_column_lookup/_query_temperature_timeline` 包装函数，复用服务层的逐日生成逻辑；`_execute_data_analysis_query_legacy` 在 range 模式下统一 `update` timeline，常量行调用 `_build_constant_timeline` 生成同值序列，气温行直接读取 `calc_temperature_data` 逐日值，即使无常规指标也能得到完整日期数组。
- 验证：`python -m py_compile backend/api/v1/daily_report_25_26.py` 通过；使用 `aver_temp` 单项拉取 `/data_analysis/query`，响应 `rows[0].timeline` 及 `timeline.rows` 均包含指定区间内的日均气温，前端 RevoGrid 恢复渲染。
- 回滚：恢复 `backend/api/v1/daily_report_25_26.py` 的新增 helper 与 timeline 注入逻辑即可。

# 会话小结（2025-12-27 北海分表分析视图）

- 新增 `backend/sql/analysis_beihai_sub.sql`，定义 `analysis_beihai_sub_daily`（读取 `phoenix.biz_date` 当日/同期）与 `analysis_beihai_sub_sum`（读取 `phoenix.sum_start_date/sum_end_date` 区间）两张视图：复用 `analysis_company_daily/sum` 的 params/base/const/calc 链条，并限制 `company='BeiHai'` 且 `sheet_name ∈ {BeiHai_co_generation_Sheet, BeiHai_water_boiler_Sheet}`，所有 CTE 均输出 `sheet_name` 以便直接按模板过滤。
- base 仍保留原始 `daily_basic_data` 行，calc 链只向最终结果输出 9 个指标（内售热收入、煤成本、外购电/水、可计量辅材、直接收入、边际利润、可比煤价边际利润、全厂热效率），其余 calc_* 仅作为依赖存在；`calc_direct_income/eco_marginal_profit/eco_comparable_marginal_profit` 在 sheet 粒度重算，常量 CTE 只加载 BeiHai 公司的价格/面积等参数。
- 使用方式：部署后执行 `psql -f backend/sql/analysis_beihai_sub.sql` 创建视图 → 通过 `SET LOCAL phoenix.biz_date = :date` 或设置累计区间后直接 `SELECT * FROM analysis_beihai_sub_daily|sum WHERE sheet_name='BeiHai_co_generation_Sheet'`；如需回滚，`DROP VIEW analysis_beihai_sub_daily; DROP VIEW analysis_beihai_sub_sum;` 并删除脚本即可。

# 会话小结（2025-12-27 AI 报告阶段字段前端消费）

- 本次无 FastAPI 或服务端代码改动，仅确认前端 `DataAnalysisView.vue` 会读取 `/data_analysis/ai_report/{job_id}` 响应中的 `stage` 字段，并据此在 UI 显示“阶段 x/4：…”的生成进度；后端现在按“洞察 → 结构 → 内容 → 检查”写入 `stage=insight/layout/content/review/ready/failed`。
- 若后续调整阶段名称或数量，请同步更新前端枚举（洞察分析/结构规划/内容撰写/检查核实）及 README，避免提示错位。

# 会话小结（2025-12-27 AI 报告 Prompt 输出修订）

- `backend/services/data_analysis_ai_report.py` 在 `_preprocess_payload` 为每个指标新增 `timeline_entries`（结构化的日数据 + delta_pct），供 Prompt 直接渲染表格。
- `REPORT_PROMPT_TEMPLATE` 强化约束：禁止生成 ```html/```css 等 Markdown 代码块，要求页头明确展示 unit_label/analysis_mode/date 等信息，并新增“逐日明细表 + 指标切换图表”指示，确保每个指标都含日数据列表且图表支持切换。
- `_build_report_prompt` 传递 CSS 时去掉 Markdown 样式，仅给出纯文本片段并提示模型嵌入 `<style>`，避免诱导输出围栏。
- 若模型仍输出 Markdown，可再调整 Prompt 或在生成后做正则清洗；回滚只需恢复该文件到上一版本。

# 会话小结（2025-12-27 数据分析 AI 报告多阶段管线）

- `backend/services/data_analysis_ai_report.py` 由单次 Prompt 改为四段式流程：
  1. **洞察分析阶段**：先调用 `_preprocess_payload` 得到本期/同比/环比/趋势/气温相关性指标，再用 `INSIGHT_PROMPT_TEMPLATE` 调度 Gemini 输出结构化 JSON（headline/key_findings/risks/recommendations/notable_metrics/temperature_effect）。
  2. **版面规划阶段**：基于阶段一 JSON 生成章节规划、图表计划、callouts，所有内容仍要求模型返回 JSON，由 `_run_json_stage` 自动重试最多两次并在 `_jobs` 中写入 `insight/layout`。
  3. **内容撰写阶段**：根据洞察与规划生成实际段落、callouts（HTML 片段），写入 `_jobs` 的 `content` 字段。
  4. **检查核实阶段**：以 `processed_data + content_data` 为输入，通过 `VALIDATION_PROMPT_TEMPLATE` 生成校验 JSON（status/issues/notes），确保报告中的数值与差异率与数据一致，结果写入 `_jobs.validation` 并在最终 HTML 输出“AI 自检结果”段落。
- 所有 Prompt 都会在最前端插入“### AI 指令（最高优先级）”并遵循 `backend_data/api_key.json` 的 `instruction` 文本；公共 helper `_call_model` 负责统一处理 candidate/parts，`_run_json_stage` 针对 JSON 阶段自带解析与重试；`enqueue_ai_report_job` 的内存快照新增 `stage/started_at/insight/layout/content/validation` 字段，`get_report_job` 查询结果据此可以展示实时阶段。
- `_calculate_correlation` 的 fallback 分支补齐缺失的 numerator 运算，避免 Python 3.9 环境无 `statistics.correlation` 时相关系数恒为 0；异常信息会同步写入 job。
- 回滚方式：恢复 `backend/services/data_analysis_ai_report.py` 即可返回旧版“一次 Prompt + Markdown 报告”逻辑。
- AI 报告预处理会同步消费 `plan_comparison` 字段，生成“计划比较”表格与摘要（完成率/计划值对比），确保文本段落与 HTML 导出均包含计划完成情况。

# 会话小结（2025-12-30 数据分析计划比较修复）

- `paln_and_real_month_data.period` 近期导入的数据使用“月底日期”“YYYY-MM”甚至“2025年11月30日/2025年11月”这类字符串，原逻辑使用 `period::date = :period_start` 仅能匹配每月 1 日，导致同月区间无法命中计划值。
- `backend/services/data_analysis.py` 的 `_build_plan_comparison_payload` 改为按月份前缀匹配：构造 `period_exact=YYYY-MM-01`、`period_prefix=YYYY-MM%` 与 `period_digits_prefix=YYYYMM%`，SQL 条件扩展为 `period = :period_exact OR period LIKE :period_prefix OR regexp_replace(period, '[^0-9]', '', 'g') LIKE :period_digits_prefix`，去掉 `period::date` 强制转换后即可兼容多种 period 字符串。若仍无法生成比较，会附带 `plan_comparison_note`（如“仅支持同月区间”“该月份缺少计划值”）方便前端展示原因。
- 修复后 `/data_analysis/query` 只要起止日期位于同月且存在计划数据即可重新返回 `plan_comparison` 数据，前端“计划比较”表和 Excel 导出恢复显示；回滚只需撤销上述函数的 SQL 变更。

# 会话小结（2025-12-30 AI 配置改回明文）

- 由于临时加密方案导致各模块解密不一致，现已回退：`backend_data/api_key.json` 再次保存明文 `gemini_api_key`，FastAPI 读取/写入也不再进行加解密。
- 如需保护密钥，请使用部署环境提供的安全存储（例如环境变量或密钥管理服务），当前仓库内的示例配置仍然用于本地联调。

# 会话小结（2025-12-27 数据分析流程讨论）

- 本轮仅与用户确认数据分析页面仍依赖现有 `/data_analysis/schema`（单位/指标/分析模式/小数位/默认日期）与 `/data_analysis/query`（本期/同期/环比/计划比较/逐日 timeline）接口，以及 `getDashboardBizDate` 提供的默认业务日，无任何 FastAPI 或 SQL 变更。
- `/data_analysis/query` 现支持 `request_ai_report` 布尔参数，若为真则调用 `backend/services/data_analysis_ai_report.py`：该模块读取 `backend_data/api_key.json` 的 Gemini 配置，将查询 payload 入队线程池生成 Markdown 报告，并把 `ai_report_job_id` 回传给前端。新增 `GET /data_analysis/ai_report/{job_id}` 用于查询状态（pending/ready/failed），失败不会阻断主查询；Prompt 内容已升级为“面向周/月汇报”的固定大纲，要求生成管理层可直接引用的文字。

# 会话小结（2025-12-26 analysis 指标精简）

- `backend/sql/analysis.sql` 移除 `calc_amount_heat_lose` 与 `calc_inner_heat`（内部购热成本）两个 CTE，并在 `calc`/`calc_direct_income` 中去掉对应 `UNION ALL`，主城区/集团 `WHERE item NOT IN (...)` 清理 `amount_heat_lose` 条目，保证视图与 API 不再产出“其中：供热输差”“其中：内部购热成本”。
- 成本口径仍由 `calc_inner_purchased_heat_cost`、`calc_outer_heat_cost` 等 CTE 负责，边际利润与其他派生指标不会受影响；执行 `psql -f backend/sql/analysis.sql` 后 `/data_analysis/query` 与 `analysis_groups_*` 结果即会同步。

# 会话小结（2025-12-26 analysis 视图内售热收入补齐）

- `backend/sql/analysis.sql` 为 `analysis_company_daily`/`analysis_company_sum` 新增 `calc_inner_heat_supply_income` CTE，按 `amount_heat_supply × price_inner_heat_sales / 10000` 计算“其中：内售热收入（万元）”，并将其写入视图输出。
- `calc_direct_income` 与共享的 `calc` UNION 列表现显式合并该 CTE，使“直接收入=售电+内售热+暖+售高温水+售汽”恢复正确口径；边际利润、可比煤价边际利润自动使用新的直接收入值。
- 原 `calc_inner_heat`（内购热成本）保持不变，继续为成本项服务；执行 `psql -f backend/sql/analysis.sql` 后即可在 `/data_analysis/query`、`analysis_groups_*` 聚合中看到 `eco_inner_heat_supply_income`。

# 会话小结（2025-12-25 数据分析页月度计划对比 API）

- `backend/services/data_analysis.py` 新增 `_query_plan_month_rows/_build_plan_comparison_payload` 辅助函数：当 `start_date/end_date` 位于同一自然月时，会按 `company/company_cn` 与 `item/item_cn` 同步检索 `paln_and_real_month_data`，自动匹配所选指标的月度计划值。
- `execute_data_analysis_query` 在满足上述条件且命中计划值时，响应体新增 `plan_comparison` 字段（包含 `month_label/period_start/period_end` 与逐指标的 `plan_value/actual_value/completion_rate`），前端即可直接渲染“计划比较”表与摘要；跨月或无计划值则不返回该字段，保持兼容。
- 计划值计算默认使用“本期合计（range 模式取 total_current，daily 模式取当前日值）”，完成率 = 实际/计划，计划类型字段沿用 `paln_and_real_month_data.type`（当前固定为 `plan`）。回滚只需还原 `backend/services/data_analysis.py` 的新函数与主流程插桩即可。

# 会话小结（2025-12-24 月度计划与实绩月度数据表）

- `backend/sql/create_tables.sql` 新增 `paln_and_real_month_data` 表定义，字段覆盖 `company/company_cn/item/item_cn/unit/period/value/type` 并沿用 `daily_basic_data` 的同名字段类型与约束，追加 `id BIGSERIAL` 与 `operation_time` 以保持统一的审计列。
- 表创建语句附带唯一索引 `idx_paln_and_real_month_unique (company, item, period, type)`，用于限制同单位+指标+周期+类型仅保留单条记录，便于计划值与实绩值分别入库。
- 在 `backend/sql` 目录新增独立的 `paln_and_real_month_data.sql`，脚本内容与主建表脚本保持一致，便于需要单独部署该表时直接执行；未来若要扩展月度汇总接口，可引用这一脚本落库后再实现 API。
- `backend/db/database_daily_report_25_26.py` 同步新增 `PlanAndRealMonthData` ORM 模型，字段与新表一一对应（含 `period/type`），后续服务层可直接通过 SQLAlchemy 读取或写入计划/实绩月度数据。

# 会话小结（2025-12-23 仪表盘导出自动展开折叠表）

- 前端 `DashBoard.vue` 在导出 PDF 前会强制展开“0.5 供暖期焦点指标详表”，串行等待 `nextTick → requestAnimationFrame → 360ms` 动画后再调 `html2canvas/jsPDF`，导出完毕再按初始状态还原；后端 `/dashboard` 接口与缓存逻辑无需改动，只要持续输出 0.5 段落即可满足导出内容。

# 会话小结（2025-12-23 标煤消耗量卡片多维切换）

- `/api/v1/projects/{project_key}/dashboard` 现已为 “5.标煤耗量” 节填充 `本月累计/同期月累计/本供暖期累计/同供暖期累计` 四个 buckets：服务层调用 `_fill_simple_metric(..., frame_key)`，分别对应 `sum_month_biz/sum_month_peer/sum_ytd_biz/sum_ytd_peer`，与既有“本期/同期”一致；前端即可直接读取三种展示维度，无需再 mock。

# 会话小结（2025-12-23 供暖单耗卡片新增“本月累计”数据）

- “4.供暖单耗” 节新增 `本月累计/同期月累计` 节点，`dashboard_expression._fill_metric_panel` 对应走 `sum_month_biz/sum_month_peer`，使前端能与标煤耗卡片一致支持三档维度（本期 / 本月累计 / 供暖期累计）；旧的“本供暖期累计/同供暖期累计”逻辑保持不变。
- “8.供热分中心单耗明细” 改为和单耗卡片一致的阶段结构（本期/同期/本月/同期月/本供暖期/同供暖期），`_fill_heating_branch_consumption` 现在接受阶段参数并复用 `sum_basic_data` 的 `value_*`/`sum_month_*`/`sum_ytd_*` 字段，前端即可在卡片上切换三档维度。

# 会话小结（2025-12-23 供暖单耗供暖期累计）

- `/api/v1/projects/{project_key}/dashboard` 现针对 “4.供暖单耗” 节点额外输出 “本供暖期累计”“同供暖期累计” 两个阶段，服务层通过 `_fill_metric_panel(..., "sum_ytd_biz")` / `_fill_metric_panel(..., "sum_ytd_peer")` 直接读取 `groups/sum_basic_data` 视图的 YTD 字段，字段口径与 `backend_data/数据结构_数据看板.json` 中的配置保持一致。
- 其他板块及接口未改动；若需还原旧行为，只需移除新增的两次 `_fill_metric_panel` 调用即可恢复仅本期/同期的响应结构。

# 会话小结（2025-12-23 数据看板前端结构复盘）

- 解析 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 确认 `/api/v1/projects/{project_key}/dashboard` 的 sections 仍以“编号.名称”作为 key，前端通过 `metricAliasMap`（行 1038-1145）双向映射别名 → 实际 item，并在 `resolveSection/resolveBucketByLabel`（行 1410-1475）中按编号或旧键回退；因此若后端配置新增别名或重排段落，只要保持编号与 `口径别名` 映射即可兼容现有解析。
- 缓存/气温导入动作全部依赖既有 API：`publishDashboardCache/disable.../cancel...` 与 `importTemperatureData/commitTemperatureData`（行 1232-1356、1077-1141）会在 UI 层防重/轮询，无需额外接口；同时 `getDashboardBizDate`（行 1368-1398）决定默认业务日，若后端未来新增“业务日锁定”字段可在该接口返回即可。
- 页面读取的板块有：`1.逐小时气温` → 折线/表格/平均值，`2.边际利润`、`3.集团全口径收入`、`4.供暖单耗`、`5.标煤耗量`、`6.投诉量`、`7.煤炭库存`、`8.供热中心单耗`、`9.累计卡片`、`10.每日对比趋势` 与 `0.5` 折叠表。若新增板块，请保证 sections 字典中包含可辨识索引并在配置 `口径别名` 中注明展示名，避免前端额外硬编码。
- 本次仅梳理契约，无 FastAPI 代码调整；回滚仅需删除本节记录。

# 会话小结（2025-12-22 数据看板单耗配置补充供暖期累计）

- 更新伪配置 `backend_data/数据结构_数据看板.json` “4.供暖单耗”节点，新增“本供暖期累计”“同期供暖期累计”占位，结构与本期/同期一致（集团/主城区/各厂，研究院电单耗仍标注剔除），计量单位沿用热/电/水默认值。
- 本次未改动后端接口或逻辑；后续若前端接入供暖期累计视图，可按新增键名从 dashboard 数据载荷读取。

# 会话小结（2025-12-16 填报页本单位分析组件完成）

- 前端 `UnitAnalysisLite.vue` 完成本单位分析折叠区：只允许当前单位、`analysis_mode=range`，按 `set_biz_date` 向前 7 天设置区间，调用现有 `/data_analysis/query` 获取 rows/warnings/timeline/meta；支持指标多选、温度默认勾选、逐日表/趋势图与单单位 Excel 导出。后端接口保持不变，无新增依赖。
- 本次未改动后端代码；若需回滚前端行为，恢复该组件即可。

# 会话小结（2025-12-16 数据填报页编译错误修复）

- 前端 `DataEntryView.vue` 出现悬挂的 `router.replace` 代码导致编译报错；已恢复缺失的参数校验 `if (!projectKey || !pageKey || !sheetKey)`。后端接口未改动。
- 若需回滚仅恢复该前端文件即可。

# 会话小结（2025-12-17 数据填报页分析开关位置调整）

- 前端调整本单位分析开关位置：移动到顶栏“业务日期”左侧，与表级校验开关分离，功能逻辑不变。后端接口保持不变。

# 会话小结（2025-12-17 数据填报页分析开关尺寸统一）

- 顶栏“本单位分析”开关的 checkbox 尺寸统一为 16x16，与表级校验开关一致；仅样式微调，后端接口无变化。

# 会话小结（2025-12-17 本单位分析指标面板滚动）

- 前端优化 `UnitAnalysisLite.vue` 指标选择区域：限制高度并启用滚动，防止指标过多撑高页面；后端接口不变。

# 会话小结（2025-12-17 本单位分析未知单位容错）

- 前端 `UnitAnalysisLite` 在选择 `analysisUnitKey` 时优先使用 schema 的 `unit_key`，否则按 `unit_dict` 匹配当前单位（key/label 精确或模糊），最后回退到 props，避免出现“未知单位”报错；后端接口未改动。

# 会话小结（2025-12-17 本单位分析单位匹配再修正）

- 进一步调整前端 `analysisUnitKey` 选择顺序：移除默认取 `unit_dict` 首项的行为，改为 schema `unit_key` → `unit_dict` 与 props（key/label）大小写/模糊匹配 → props 回退，防止误用其他单位导致 400。后端接口无变化。

# 会话小结（2025-12-17 本单位分析单位匹配再修正 v2）

- 增加 `_Sheet` 去除、大小写无关精确匹配和 label 模糊匹配，再回退 props 与 unit_dict 首项，进一步避免“未知单位”报错；后端接口未改动。

# 会话小结（2025-12-17 本单位分析 schema 等待与单位校验）

- 前端 `runUnitAnalysis` 先等待 schema 加载完成，若失败直接提示；运行前校验 `analysisUnitKey` 非空，避免携带空 unit_key 导致 400。后端接口无变化。

# 会话小结（2025-12-17 本单位分析禁用填报 config 透传）

- 前端调用 `/data_analysis/query` 时不再透传填报页的 config（如 `数据结构_基本指标表.json`），改用后端默认分析配置，避免因 config 错配导致“未知单位”报错。后端接口未改动。

# 会话小结（2025-12-17 本单位分析相关矩阵接入）

- 前端 `UnitAnalysisLite` 新增相关矩阵计算与展示，基于已选且有逐日数据的指标自行计算 r 值与提示；后端接口未变。

# 会话小结（2025-12-16 数据分析页现状复盘）

- 复核前端 `pages/DataAnalysisView.vue`：加载 schema 后解析单位/指标/分析模式/默认日期，按温度权重默认勾选气温类指标，表单校验要求至少选择单位与指标；`runAnalysis` 按所选单位逐一调用 `/data_analysis/query`（附带 `analysis_mode/start_date/end_date`），前端缓存 `rows/warnings/timeline/meta` 并生成摘要、相关矩阵、趋势图与多 Sheet Excel 导出。
- 后端接口契约保持现状即可：`/data_analysis/schema|query` 提供单位/指标/小数位/时间线数据，`/dashboard/date` 返回 `set_biz_date` 供默认日期使用，无需新增字段或变更逻辑。
- 未修改后端代码或配置，本次仅文档登记；若需回滚，删除本小节即可。

# 会话小结（2025-12-14 数据分析页面结构梳理）

- 本次仅阅读前端 `DataAnalysisView.vue`，确认数据分析流程依赖现有 `/data_analysis/schema` 与 `/data_analysis/query`，后端无需改动：前端按所选单位逐一调用查询接口，缓存 `rows/warnings/timeline/meta` 后在浏览器端完成相关矩阵、摘要、趋势图与 Excel 导出。
- 该页面默认业务日取自 `GET /dashboard/date`（`set_biz_date`），温度指标默认勾选取决于 schema 的温度关键词；多单位导出时每个单位生成独立 Sheet，后端响应格式保持现状即可。
- 未对后端代码、接口或配置做任何修改，记录结构梳理以便后续联调。

# 会话小结（2025-12-14 填报页本单位分析折叠区）

- 前端在 `DataEntryView.vue` 增加“本单位数据分析”折叠卡片，调用现有 `/data_analysis/schema|query`，强制使用当前模板的 `unit_id/unit_name`，仅以 `analysis_mode=range` 查询本单位汇总，不提供逐日或跨单位数据。
- 后端接口无需变更，但需确保 data_analysis 查询对传入的 `unit_key` 做权限/范围校验即可；导出为单 Sheet Excel 由前端完成。
- 未改动后端代码，如需回滚可仅恢复前端文件。

# 会话小结（2025-12-14 填报页指标聚合接口）

- 新增 `GET /projects/daily_report_25_26/data_entry/analysis/metrics`：按 `unit_key` 汇总审批/常量配置中的项目字典，并追加数据分析 schema 的气温指标与小数位，返回 `{options, decimals, source}` 供填报页本单位分析使用。
- 仅读取 JSON 配置文件，不访问数据库；调用方仍通过 `/data_analysis/query` 获取单单位汇总结果，保持数据范围受限。
- 回滚恢复 `backend/api/v1/daily_report_25_26.py` 对应增量即可。

# 会话小结（2025-12-14 填报页趋势图轴/图例同步）

- 本次只在前端 `DataEntryView.vue` 调整趋势图配置：复用数据分析页面的 legend/tooltip/渐变配色，并在前端依据 `/data_entry/analysis/metrics` 返回的 `temperature` 分组（以及 `value_type == 'temperature'`）将平均气温固定映射到右轴，其余指标走左轴；后端 `/data_analysis/query` 与 `/data_entry/analysis/metrics` 的数据结构保持不变。
- 接口契约未改动，仍返回 `timeline.current/peer/date`、`decimals` 与按组区分的指标选项；若未来 schema 需要新增其它“特殊轴”类型，可继续在接口层通过 `value_type` / 分组标识传递，前端即可沿用同一轴分配逻辑。
- 无需部署后端，回滚仅涉及前端文件恢复。

# 会话小结（2025-12-14 填报页分析默认日期/导出增强）

- `DataEntryView.vue` 现在也会调用现有 `GET /projects/{project_key}/dashboard/date` 接口获取 `set_biz_date`，并在折叠区默认将分析区间设置为“set_biz_date 向前 6 天”，与仪表盘/数据分析页面保持一致；后端接口无需改动。
- 指标多选与 Excel 导出增强完全发生在前端：仍沿用 `GET /data_entry/analysis/metrics` 与 `POST /data_analysis/query` 的返回结构，额外的序号展示与逐日表导出均在浏览器侧完成。
- 若需要回滚，只需恢复前端 `DataEntryView.vue`；后端 API 无新增依赖。

# 会话小结（2025-12-14 指标排序与命名更新）

- `GET /projects/daily_report_25_26/data_entry/analysis/metrics` 中，将“审批指标”重命名为“主要指标”，主要/常量指标按配置文件原始顺序输出，附带 `unit_dict` 供前端使用正确的 `unit_key`。
- 不涉及数据库操作，回滚恢复 `daily_report_25_26.py` 即可。

# 会话小结（2025-12-14 填报页指标分组排序 + 单位修正）

- 指标接口附带 `unit_dict`，前端查询 `unit_key` 优先用接口值，避免“未知单位”错误；分组选项以审批/常量/气温顺序并按中文排序。
- 后端仍仅读取 JSON 配置，无数据库改动；回滚同上。

# 会话小结（2025-12-12 dockerignore 添加）

- 仓库根目录新增 `.dockerignore`，默认忽略 `db_data`（PostgreSQL 本地数据目录），避免容器构建上下文携带大体积数据库文件；后端代码与依赖未改动，回滚只需删除该忽略文件或移除对应条目。

# 会话小结（2025-12-13 AI 测试脚本文本化）

- `configs/ai_test.py` 现仅支持多轮文本对话：移除了 HTML 报告生成、文件保存与浏览器自动打开逻辑，保留 Google Search Grounding 工具链与会话记录；提示信息改为“返回纯文本答案”。回滚时恢复旧版 HTML 报告分支即可。

# 会话小结（2025-12-13 AI 测试脚本提示词变量）

- `configs/ai_test.py` 新增 `BASE_SYSTEM_PROMPT` 基础提示词常量，默认引导模型“用中文简洁回答、避免编造数据”，每次请求都会自动附加。若想关闭只需将该常量置空或覆盖为其他提示词。

# 会话小结（2025-12-13 采暖收入键名纠正）

- `backend/sql/analysis.sql` 四个分析视图的采暖收入项统一改名：`item` 由 `eco_heating_income` 调整为 `eco_heating_supply_income`，`item_cn` 改为“其中：暖收入”；售电/暖/高温水/蒸汽收入的直接收入汇总聚合同样切换为新键名。重新部署视图后，查询结果应按新键返回并参与合计。

# 后端说明（FastAPI）

## 会话小结（2025-12-?? 仪表盘气温导入对比）

- `POST /api/v1/projects/daily_report_25_26/dashboard/temperature/import` 继续保持 `can_publish` 权限，但返回值新增“重合区间与差异列表”：调用 Open-Meteo 后，会在同一事务外只读查询 `temperature_data`，计算接口返回的小时与数据库已存小时的重合区间（start/end/hours），并列出同小时但数值不同的记录（接口值/数据库值），方便人工决策。
- 新增 `POST /api/v1/projects/daily_report_25_26/dashboard/temperature/import/commit`：再次拉取 Open-Meteo 数据并覆盖写入 `temperature_data`（按时间段 delete+bulk insert，小时去重），返回写入/覆盖条数与起止时间；仍需 `can_publish` 权限。
- 补充：前端已引入 `commitTemperatureData` 调用新接口，修复未定义报错。
- 修复：入库/比对时统一补齐时区为东八区并按小时归一，避免 API 时间缺少 tzinfo 导致的时区错位。
- 追加：比对返回 `overlap_records`（所有重合小时的接口/库值，差异标记 different），前端全部列出并将差异高亮。
- 更新：即便数据库无该小时，也会在明细中列出接口值（库值为空用 “—”），保证每小时对齐结果可见。
- 提示：前端在写库成功后会提示“气温数据写库成功”，失败时显示错误原因。
- 增强：仪表盘业务日期默认值现优先使用后端 `set_biz_date`，仅在获取失败时回退到“昨日”，保证日期显示与数据源一致。
- `backend/services/weather_importer.py` 新增 `compare_with_existing`，统一小时粒度（东八区），用于比对 API 数据与 `temperature_data`；对比逻辑仅做读取，不改数据库。
- 回滚方式：恢复 `backend/services/weather_importer.py` 与 `backend/api/v1/daily_report_25_26.py` 的本次修改即可。

## 会话小结（2025-12-?? 仪表盘气温导入预览）

- 新增 `backend/services/weather_importer.py`，封装固定 Open-Meteo 请求（past_days=3、Asia/Singapore 时区、用户提供坐标），解析 `hourly.time/temperature_2m` 并返回逐小时列表与涉及日期；当前阶段仅提供数据预览，不落库。
- `/api/v1/projects/daily_report_25_26/dashboard/temperature/import` 仅允许具备 `can_publish` 权限的账号调用，成功后返回 `hourly/summary/dates/source/fetched_at`，供仪表盘按钮展示“导入进度”。
- `backend/requirements.txt` 新增 `httpx` 依赖，后续若要真正写入 `temperature_data` 可在该服务基础上追加 upsert/事务逻辑；若要停用该功能，删除新模块与路由即可回滚。

## 会话小结（2025-12-11 数据分析默认选项优化）

- 数据分析页面的默认选项逻辑全部在前端完成：单位多选默认置空，温度指标通过权重算法优先锁定“平均气温”，后端 `/data_analysis/schema` 与 `/data_analysis/query` 无需任何调整。该变更仅影响前端如何解读现有 Schema。
- 若未来需要为不同项目提供其它温度指标作为默认项，可在 `metric_groups` 中明确 temperature 组并保证 `平均气温` 出现在选项列表中，前端会自动捕捉并勾选；后端仍按既定格式返回 `metric_groups/metric_dict` 即可。

## 会话小结（2025-12-11 数据分析指标组自由组合）

- 前端已移除基于 `metric_group_views` 的禁用判断，所有指标组在任意单位/分析模式下都可选；FastAPI 输出的 Schema 保持不变，仅提示逻辑交由前端查询结果中的 `warnings` 处理。
- 若需要限制某些单位的指标，可在服务层直接控制查询结果或返回 `warnings`，无需再依赖前端禁用视图。

## 会话小结（2025-12-12 数据简报相关矩阵）

- “数据简报”卡片新增前端相关矩阵计算展示，完全基于 `/data_analysis/query` 返回的逐日数据（`timeline.current/peer`）在浏览器端计算皮尔逊相关系数；后端无需提供额外接口或字段。
- 若未来在接口层加入其它度量（如运行天数、极值等），前端可复用相同矩阵组件，只需保证逐日数据对齐即可。
- 同日更新：整体概览与趋势观测文字均在前端处理——前者仅统计有效指标数量与同比方向，后者基于逐日数据计算区间均值（不再附“约”字）并覆盖所有勾选指标——仍然只依赖现有 API 字段。

## 会话小结（2025-12-11 趋势图温度固定右轴）

- 趋势图改为在前端统一分配坐标轴：检测到气温类指标（尤其“平均气温”）时自动绑定右轴，其它指标保持在左轴，以免受勾选顺序影响；后端 `timeline` 返回格式维持不变。
- 如果未来新增其它特定轴需求，可在 `timeline` 数据中附带标记，由前端扩展轴分配逻辑即可，无须额外接口。

## 会话小结（2025-12-10 数据分析区间趋势图支持）

- 前端 `DataAnalysisView.vue` 在“区间明细（逐日）”下方新增 ECharts 趋势图组件，通过既有 `/data_analysis/query` 返回的 `timeline` 数据绘制本期/同期双折线，并提供指标芯片切换及 dataZoom 缩放。该功能完全复用后端结果，无需追加接口或字段。
- 趋势图默认仅展示首个可用指标；若用户选择第二个指标，前端会自动启用双纵轴（左右轴）策略来容纳不同量纲，其余指标复用右轴刻度，可通过芯片全部取消以获得空态提示，数据契约保持不变。
- 如需扩展其它类型的趋势（例如同比视图），只需在返回的 `timeline` 数组中补充 `current/peer/date` 即可被前端自动识别；若后端后续调整字段命名，请同步通知前端以免图表解析失败。
- 2025-12-10 更新：前端 `TrendChart` 在刷新 series 时使用 `notMerge: true`，确保隐藏指标或切换芯片时旧曲线不会残留；后端接口仍无需改动。

## 会话小结（2025-12-10 数据分析筛选布局重排）

- 本次需求仅涉及前端 `DataAnalysisView.vue` 布局：通过新增 `form-layout/form-grid--top/form-panel--metrics`，将“单位选择（多选）”与“分析模式”固定在同一行，指标面板独占下一行，便于并排操作。后端接口、Schema 与服务逻辑均未改变，此处仅留痕说明前端已对交互方式进行调整。
- 若未来接口返回结构或筛选项顺序发生改变，需要同步通知前端以免布局假设失效；当前版本继续复用既有 `/data_analysis/schema` 与 `/data_analysis/query`。

## 会话小结（2025-12-10 数据分析页面开放至 Group_admin）

- `backend_data/auth/permissions.json` 重新为 `Group_admin` 注入 `data_analysis` page_access，维持 `Global_admin` 全量权限不变，其它角色（ZhuChengQu_admin/Unit_admin/unit_filler/Group_viewer）仍无法看到该页面。FastAPI 层 `permissions` 响应会把该 page_key 下发给 Group_admin，前端 `PageSelectView` 将在卡片列表中显示“数据分析页面”入口。
- 权限控制依旧由 `page_access` 与 `sheet_rules` 组合完成，新增 page_access 不会改变审批/填报等权限矩阵。若需再次收紧，可将 `data_analysis` 从目标角色的数组中移除并通知前端刷新 session。

## 会话小结（2025-12-10 数据分析同比颜色纠正）

- 本次问题由前端同比颜色映射导致，FastAPI 与数据计算逻辑无改动，接口依旧按照 `delta >= 0` 输出为正、`delta < 0` 输出为负。为保持前后端协同，这里留痕：前端 `DataAnalysisView.vue` 更新了 `.delta-up/.delta-down` 的颜色定义，使同比增加显示 `danger`（红色），同比下降显示 `success`（绿色）。
- 若后续在其它客户端/导出流程复用同比字段，同样应遵循“同比增加=红、同比下降=绿”的约定，避免出现语义反转。

## 会话小结（2025-12-10 数据分析默认日期同步 set_biz_date）

- 前端 `DataAnalysisView.vue` 现在会在加载 schema 前调用已存在的 `GET /projects/{project_key}/dashboard/date` 接口，并将 `start_date/end_date` 默认为 `backend_data/date.json` 中的 `set_biz_date`（若 schema 未提供专属默认值）。后端接口与 `date.json` 维护方式均保持原状，本条仅记录该接口已被数据分析页面复用。
- 若未来调整 `date.json` 结构或接口路径，需要同步通知前端，避免默认日期回退到本地时间。

## 会话小结（2025-12-10 数据分析支持多单位批量查询/导出）

- 多单位需求完全由前端批量调用现有 `POST /projects/{project_key}/data_analysis/query` 实现，后端 service/API 无需新增 batch 接口。前端会按所选单位逐一请求，并在结果区提供“单位标签”切换展示，确保各单位的数据互不混合。
- Excel 导出时，每个单位生成独立 Sheet（包含该单位的汇总、区间明细、查询信息），若某单位查询失败，前端会在错误提示中标注该单位，其它单位的结果仍可正常显示/导出。

## 会话小结（2025-12-10 数据分析常量/气温逐日补齐）

- `data_analysis_service` 现会为常量指标构造逐日 timeline：在区间模式下，`price_std_coal` 等常量会把当前值/同期值按日期展开到“区间明细”表格里，虽然每天数据相同，但可与其它指标并排查看。
- 气温指标新增逐日查询：`calc_temperature_data` 每日值会写入 timeline，区间汇总的 `total_current/total_peer` 改为对逐日数据取平均，满足“显示每日气温 + 合计用平均值”的需求；同时逐日数据包含本期与同期（peer_date）以供对照。

## 会话小结（2025-12-09 AI 多轮助手 + google-genai Grounding）

- `configs/ai_test.py` 已切换到官方新版 `google-genai` SDK（`from google import genai`），并示范如何在 `GenerateContentConfig` 中注册 `Tool(google_search=GoogleSearch())`，用于测试 Gemini 2.5 Flash 结合 Google Search Grounding 的回答效果。
- 多轮上下文改由 `_conversation`（`types.Content` 列表）维护，每次 `send_message` 都会带上对话历史，方便后续在服务端迁移同样的会话管理机制；若后端要实现 `/ai/report` 等接口，可直接复用该结构并按需扩展缓存策略。
- “HTML 报告”分支仍存在：检测到关键词后会额外附加统一的报告指令，让模型输出完整 HTML（包含 ECharts CDN 与至少一张图表）并保存到 `runtime_reports/gemini_report_*.html`，之后尝试用默认浏览器打开；提示语已加强为“禁止说明无法打开/请复制代码”，确保模型直接返回 HTML；若只需文本回答或不需要图表可自行修改提示语。

## 会话小结（2025-12-09 NewAPI Gemini 兼容脚本）

- `configs/ai_test_newapi.py` 再次改为 OpenAI Chat Completions 兼容范式：基址 `https://api.voct.top/v1`、模型 `grok-4-expert`，直接发送 `{model, messages}`，保留多轮对话/HTML 报告分支与浏览器打开逻辑，便于验证“OpenAI SDK 语义 + Grok 模型”。
- API Key 仍按“环境变量 NEWAPI_API_KEY → backend_data/newapi_api_key.json → 默认密钥”顺序加载，会话历史存储 `system/user/assistant` 消息；后续若要切换回 generateContent 版本，只需调整 `BASE_URL` 和 `send_message()` payload。

## 会话小结（2025-12-08 数据分析指标补齐）

- 为修复数据分析页面在选择“集团全口径 + 调整指标 > 供暖电单耗(-研究院)”时始终显示“缺失”的问题，已将该指标的计算逻辑从 `backend/sql/groups.sql` 同步到 `backend/sql/analysis.sql`。新增的 `yjy_power/yjy_area` CTE 会预先扣除研究院的站购电量与挂网面积，并在 `analysis_groups_daily`、`analysis_groups_sum` 两个视图中加入 `rate_power_per_10k_m2_YanJiuYuan` 的 `UNION ALL` 片段，确保单日和累计查询都能返回正确数据。
- FastAPI 层无需改动即可受益：`backend/services/data_analysis.py` 在解析 schema 时已经把“供暖电单耗(-研究院)”放入调整指标分组，更新视图后 `/data_analysis/query` 会像普通指标一样读取 `analysis_groups_daily/analysis_groups_sum`，不再落入 missing 分支；`runDataAnalysis` 前端也能直接得到 `rows` 数据。
- 部署时请重新执行 `analysis.sql`，以便数据库中的视图结构与 repo 同步。若未来新增集团级指标，需要同时更新 `analysis.sql` 和 `groups.sql`，避免再次出现服务层查询不到数据的情况。

## 会话小结（2025-12-04 analysis.sql 视图列清理）

- 执行 `psql -f backend/sql/analysis.sql` 时出现 `column \"sum_7d_biz\" does not exist`，原因是 `analysis_company_sum` 之前保留下的 `yjy_power` 聚合仍试图汇总 `sum_7d_* / sum_month_* / sum_ytd_*` 字段，但 `company` CTE 早已不再返回这些列。现已将该 CTE 中多余的列全部移除，仅保留 `value_biz_date/value_peer_date`，从而恢复视图创建。
- 该调整只影响集团“供暖电单耗(-研究院)”的分子预处理逻辑，最终指标依旧按“集团站购电量 - 研究院站购电量”计算，不会改变对外接口。更新后重新执行 `psql -f backend/sql/analysis.sql` 即可。
- 同日也将两个 `calc_rate_water_per_10k_m2` CTE 的分子改为一次网补水、站补水与网用水（`consumption_network_fill_water`、`consumption_station_fill_water`、`consumption_network_water`），修复“供热公司”等单位在“供暖水单耗”指标上查询不到数据的问题。

## 会话小结（2025-12-04 AI 报告预研）

- 为验证 Google Gemini 2.5 Flash 在本项目的可用性，新建了 `configs/ai_test.py`，使用官方 `google-generativeai`（别名 `genai`）SDK，可在服务器直接运行 `python configs/ai_test.py` 进行交互式调用，确认网络、API Key 及响应格式是否符合预期。脚本会按“环境变量 → `backend_data/api_key.json`”的顺序加载密钥，方便集中管理。
- 后端计划以 `backend/app/services/ai.py` 的形式封装统一的 AI 客户端，再经由 `POST /api/v1/projects/daily_report_25_26/ai/report` 暴露给前端；测试脚本已经演示了请求体、超时与异常处理逻辑，可在正式落地时直接迁移。
- 建议在 `.env` 或部署环境变量中声明 `GOOGLE_GEMINI_API_KEY` 与可选的 `GOOGLE_GEMINI_MODEL`；如需共享密钥或模型设定，可编辑 `backend_data/api_key.json`。若需要回滚 AI 功能，删除 `configs/ai_test.py` 即可恢复当前状态。

## 会话小结（2025-12-01 数据看板缓存）

- 新增 `backend/services/dashboard_cache.py`，集中负责 `backend_data/dashboard_cache.json` 的读写、set_biz_date 七日窗口（含当日及前六日）生成与禁用逻辑；内部复用 `normalize_show_date/load_default_push_date`，写入时统一使用临时文件替换确保并发安全。
- `/api/v1/projects/daily_report_25_26/dashboard` 现在会先命中缓存文件，再 fallback 到 `evaluate_dashboard()`，响应中额外附带 `cache_hit/cache_disabled/cache_dates/cache_updated_at/cache_key` 供前端渲染提示；当缓存被手动禁用时接口不会再写入文件。
- 新增 `GET /projects/daily_report_25_26/dashboard/date`，直接读取 `backend_data/date.json` 的 `set_biz_date` 提供给前端，保证首屏加载即可携带业务日期命中缓存。
- 为避免长时间占用资源，引入 `backend/services/dashboard_cache_job.py` 管理后台发布任务：`POST /dashboard/cache/publish` 按“set_biz_date → 前 6 日”的顺序（从最近向过去）执行并立即返回任务快照，`GET /dashboard/cache/publish/status` 可轮询进度，`POST /dashboard/cache/publish/cancel` 可中途停止；若需要单独刷新某一天仍可调用 `/dashboard/cache/refresh`，禁用逻辑继续使用 `DELETE /dashboard/cache`。以上接口均要求 `can_publish` 权限账号调用。
- 默认缓存文件位于 `backend_data/dashboard_cache.json`，结构为 `{ project_key, disabled, items, updated_at }`，items 中的 value 就是 `/dashboard` 的原始响应对象，可直接对照前端请求排查。

## 会话小结（2025-11-30 数据分析服务抽离）

- 新增 `backend/services/data_analysis.py`，集中实现数据分析 schema 解析、指标分组/小数位、常量与气温查询、逐日/累计取值以及 Excel 导出所需的全部辅助函数，FastAPI 端仅保留 Pydantic 校验与文件读取。
- `backend/api/v1/daily_report_25_26.py` 的 `/data_analysis/schema` 在解析配置文件后直接调用 `data_analysis.build_schema_payload()`，`/data_analysis/query` 则委托 `execute_data_analysis_query()`，其余旧的 `_query_*` 辅助函数被包装成服务层别名，避免双份实现。
- API 层复用了服务内的 `TEMPERATURE_COLUMN_MAP/TEMPERATURE_UNIT/MAX_TIMELINE_DAYS` 常量并保留 `_execute_data_analysis_query_legacy` 供需要调试旧逻辑时参考，正常路径全部走新的 service 实现，接口入参/出参保持不变。
- 通过 `python -m py_compile backend/api/v1/daily_report_25_26.py backend/services/data_analysis.py` 校验语法，确保拆分后无缩进或依赖遗漏；如需回滚，可恢复旧版 API 函数或直接调用 `*_legacy` 版本。

## 会话小结（2025-11-30 数据看板每日对比趋势）

- `backend/services/dashboard_expression.py` 新增 `_fill_daily_trend_section`、`_normalize_metric_entries`、`_build_group_metric_cache` 等 helper，按配置 `10.每日对比趋势` 将供暖期起点（HEATING_SEASON_START=2025-11-01）至 `push_date` 的每日日志转换为 `labels + series` 结构，本期包含“标煤耗量汇总(张屯)”与“平均气温”两条曲线，同期提供标煤耗量曲线。
- helper 内部对 `groups` 视图结果做日期缓存，并调用 `_fetch_daily_average_temperature_map` 获取气温时间序列；填充结果写回 `section['本期'/'同期']`，并附 `meta`（起止日期、同期映射日期）以便前端展示。
- `evaluate_dashboard` 在处理完累计卡片后调用该 helper，因此 `/dashboard` API 会自动返回新的时间序列数据；若要回滚此功能，只需移除配置中的 10 号段并删除该 helper 调用。

## 会话小结（2025-11-28 全厂热效率分母引入油耗）

- `backend/sql/sum_basic_data.sql` 的 `calc_overall_efficiency` 现以 `29.308 * (consumption_std_coal + 1.4571 * consumption_oil)` 作为分母，仍在 `base` 聚合结果上计算，确保单日/同期、7 日、月度、YTD 六个窗口全部共享同一口径。
- `backend/sql/groups.sql` 中集团层的热效率派生段落同步更新，新口径应用于 `Group` 行的全部窗口，保持公司级与集团级视图一致。
- 修改仅触及分母，分子仍为“供热量 + 36×售电量 - 外购热量”；无油耗数据的单位自动回落为旧表达式，不影响其他派生指标。
- `backend/sql/analysis.sql` 的 `analysis_company_daily/analysis_groups_daily/analysis_company_sum/analysis_groups_sum` 四张视图全部沿用同一分母，主城区与集团汇总段落的 `rate_overall_efficiency` 也引用含油耗公式，避免分析接口与基础视图出现口径偏差。

## 会话小结（2025-11-27 集团口径新增“-研究院”电单耗）

- `backend/sql/groups.sql` 添加 `rate_power_per_10k_m2_YanJiuYuan` 指标，分子在集团 `consumption_station_purchased_power` 的聚合中扣除研究院值，分母同期扣除研究院 `amount_heating_fee_area`，其余逻辑与 `rate_power_per_10k_m2` 一致，并统一展示名为“供暖电单耗(-研究院)”。
- 新增 CTE `yjy_power`/`yjy_area` 分别存放研究院站购电与面积，便于同一查询中复用；`rate_power_per_10k_m2_YanJiuYuan` 输出完整 8 列（当日/同期/7日/月度/YTD）。
- 该指标主要用于观察集团整体在剔除研究院后的单位电耗，仍保留原有 `rate_power_per_10k_m2` 以供对照。

## 会话小结（2025-11-27 分析简报绑定“-研究院”电单耗）

- `backend_data/数据结构_全口径展示表.json` 中 `Group_analysis_brief_report_Sheet` 的“供暖电单耗”行现明确调用 `value_biz_date(rate_power_per_10k_m2_YanJiuYuan)` / `value_peer_date(rate_power_per_10k_m2_YanJiuYuan)`，集团列直接使用新口径。
- `date_diff_rate` 同步传入相同 key，避免函数 fallback 至旧 `rate_power_per_10k_m2` 导致默认值 0；其他单位维持默认 `value_biz_date()` 行为继续引用各自口径。
- 数据看板 `4.供暖单耗` 已在早前配置中切换到该字段，两端配置现保持一致，报表与看板可对照同一指标。

## 会话小结（2025-11-27 数据分析查询接口 + 调整指标分组）

- `backend_data/数据结构_数据分析表.json` 新增“调整指标字典”与对应 `视图映射`，`get_data_analysis_schema` 现会在 `adjustment_metric_dict/adjustment_metric_options/metric_groups` 中返回该分组，同时 `metric_group_views` 明确每个分组允许的视图组合（例如调整指标仅允许 `groups_daily_analysis/groups_sum_analysis`）。
- 同一接口同步支持“气温指标字典”，并将 `metric_group_views['temperature']` 映射到 `calc_temperature_data`。前端勾选 `aver_temp/max_temp/min_temp` 等键后，后端会直接查询 `calc_temperature_data`：单日模式读取指定 `date`，累计模式对窗口内的日均温做 `AVG()`；单位一律返回 `℃`。
- 支持在配置中通过 `指标小数位` 指定个别指标的保留小数位（默认 2 位），例如 `rate_heat_per_10k_m2`、`rate_power_per_10k_m2`、`rate_water_per_10k_m2` 配置为 4。接口会在 `rows[].decimals` 中返回对应值，前端据此格式化展示。
- 新增 `POST /projects/daily_report_25_26/data_analysis/query`：根据 `unit_key/analysis_mode` 自动映射到 `company_daily_analysis`、`groups_sum_analysis` 等视图，并在事务中通过 `SET LOCAL phoenix.biz_date` 或 `phoenix.sum_start_date/sum_end_date` 控制时间窗口；常量指标直接读取 `constant_data`，气温指标通过 `calc_temperature_data` 视图取数，结果集中统一返回 `value_type/source_view` 标记。
- 累计模式会额外生成 `timeline` 明细：后端在 62 天范围内循环设置 `phoenix.biz_date` 调用逐日视图，返回 `[ { date, current, peer } ]`，并附带 `total_current/total_peer`，方便前端用 RevoGrid 展示逐日/累计。若日期跨度超过 62 天，会直接返回 400 提示缩小范围。
- 响应额外包含 `rows/missing_metrics/warnings` 以及解析后的 `view/start_date/end_date`，前端可直接展示提示条与缺失标记；若所选指标不属于当前视图允许的范围，接口返回 400 并列出需调整的指标。
- 可执行 `python -m py_compile backend/api/v1/daily_report_25_26.py` 快速校验语法，数据库层需确保 `analysis_company_daily`、`analysis_groups_daily`、`calc_temperature_data` 等视图已按 `analysis.sql`/`calc_temp.sql` 部署。

## 会话小结（2025-11-27 数据分析页面权限收紧）

- `backend_data/auth/permissions.json` 调整：除 `Global_admin` 外的角色（Group_admin、ZhuChengQu_admin、Unit_admin、unit_filler、Group_viewer）均移除 `data_analysis` page_access，确保 `projects/.../data_analysis` 仅对全局管理员可见。
- 其他页面与表单权限保持不变，角色仍可照常访问 dashboard/data_entry 等模块。
- 如需恢复访问，可在权限文件中为目标角色重新加入 `data_analysis`，或临时将用户加入 `Global_admin`。

## 会话小结（2025-11-27 集团口径站购电回滚）

- 用户确认“集团全口径”需重新包含研究院 `consumption_station_purchased_power`，已将 `backend/sql/groups.sql` 中 `base_grp` 的排除条件移除，恢复原始聚合范围。
- 回滚后，`Group` 行的 `rate_power_per_10k_m2` 及其它依赖站购电的派生指标会再次涵盖 `YanJiuYuan`，与历史报表逻辑保持一致；主城区 `base_zc` 仍只含 `BeiHai/XiangHai/GongRe`。
- 如已执行过带过滤条件的脚本，请重新 `\\i backend/sql/groups.sql`，并在数据库中比对 `SELECT company,item,value_biz_date FROM groups WHERE item='consumption_station_purchased_power' AND company='Group';`，确认集团值恢复为八家单位之和。

## 会话小结（2025-11-26 数据分析 Schema 接口）

- 新增 `/projects/{project_key}/data_analysis/schema` GET 接口，对应 FastAPI 路由 `get_data_analysis_schema`。接口默认读取 `DATA_ANALYSIS_SCHEMA_PATH`（容器路径 `/app/data/数据结构_数据分析表.json`），可通过 `?config=相对路径` 临时加载其他配置文件，返回值包含：
  - `unit_dict/unit_options`：单位编码与显示名称（单选），供前端绘制单选芯片；
  - `display_unit_keys/display_unit_options`：当 `backend_data/数据结构_数据分析表.json` 的 `显示单位` 列表存在时，仅将匹配到的单位返回给前端；若列表为空则回退到 `unit_options`；
  - `metric_dict/metric_options`：可自由勾选的指标清单（多选），字段与 `entries.item_key` 保持一致；
  - `primary_metric_dict/constant_metric_dict` + `metric_groups`：若 `指标选择` 划分了“主要指标字典/常量指标字典”，接口会同时返回分组选项与 `metric_view_mapping`，便于前端区分来自四张分析视图或 `constant_data` 的常量字段；
  - `view_mapping`：按“单日/累计”区分的视图映射，后端在后续查询接口中可直接据此映射到 `company_daily_analysis`、`groups_sum_analysis` 等视图；
  - `analysis_modes`：根据 `view_mapping` 动态生成的模式选项，前端据此切换“单日/累计”卡片；
  - `date_defaults`：`backend_data/数据结构_数据分析表.json` 内 `日期选择` 区域的默认值（允许为空字符串）。
- 该接口仅负责读取配置，不执行数据库查询，便于后续继续扩展真实的分析查询 API（可直接消费 `daily_analysis.sql` 内四张视图）。
- 前端 `DataAnalysisView.vue` 通过 `getDataAnalysisSchema` 首屏加载，`PageSelectView` 新增“数据分析页面”入口卡片，后续若调整配置结构，只需保持上述字段兼容即可。
- 权限配置 `backend_data/auth/permissions.json` 已同步把 `data_analysis` 加入各角色 `page_access`，确保页面卡片对具备登录权限的用户可见。

## 会话小结（2025-11-25 日分析视图拆分）

- 新增 `backend/sql/daily_analysis.sql`，定义 `company_daily_analysis` 与 `gourps_daily_analysis` 两张日口径视图。前者在 `daily_basic_data`+`constant_data` 基础上重算所有派生指标，但仅保留 `value_biz_date/value_peer_date`，通过 `current_setting('phoenix.biz_date')` 接受任意查询日期，避免重复计算 7 日/月份/采暖期累计窗口。
- `gourps_daily_analysis` 直接复用 `company_daily_analysis` 的结果，分别对“主城区（BeiHai/XiangHai/GongRe）”与“集团全口径（全部 8 个单位）”做汇总、张屯口径特殊并表以及投诉率/单耗/热效率等派生指标，输出结构与旧 `groups` 视图一致但仅包含日值与同期值。
- 部署数据库时可直接执行 `\i backend/sql/daily_analysis.sql`，或在迁移/初始化脚本中追加该文件；自由构建页面如需按日/区间查询，可循环设置 `SET phoenix.biz_date` 后访问两张新视图，再由业务层聚合时间段。
- 同一脚本额外提供 `company_sum_analysis` / `groups_sum_analysis`：通过 `phoenix.sum_start_date`、`phoenix.sum_end_date` 参数指定累计区间（默认供暖期至昨日），直接在后端完成期间求和与派生指标计算，并输出主城区/集团两类累计口径，供自由构建页面重复使用。

## 会话小结（2025-11-24 数据模板行内格式统一）

- `backend_data/数据结构_基本指标表.json` 的 12 个 `“数据”` 数组全部改为单行写法（如 `["发电量", "万kWh", "", "", ""]`），不再拆成多行。字段、顺序与值保持原样，仅压缩排版，便于代码审查与差异对比。
- `GongRe_branches_detail_Sheet`、`Coal_inventory_Sheet` 等包含大量行的模板也同步处理，确保后端在序列化/反序列化时不会感知结构变化，接口 `/template`、`/submit`、`/query` 无需调整。
- 若后续通过脚本生成模板，请保持同样的行内格式（或在提交前运行 formatter），否则再次出现多行数组会导致 diff 噪音；必要时可在生成脚本中复用 `json.dumps(..., ensure_ascii=False)` 后自行拼装行文本。

## 会话小结（2025-11-23 仪表盘图表监听优化）

- 本次仅调整前端 `DashboardEChart` 渲染逻辑，后端 `/dashboard` 接口结构、字段及缓存策略均保持不变；无需重新发布服务或调整 SQL 视图。
- 若未来需要对接口做进一步分页/拆分，可继续沿用现有 `sections` 字典返回格式；前端已通过浅引用缓存消费 `data`，暂不需要后端提供额外的 diff 标识。
- 同日新增的日期切换防抖/请求缓存同样只发生在前端：前端会中止旧请求或直接命中本地缓存，后端接口仍按原有逻辑串行返回最新数据即可。

## 会话小结（2025-11-22 校验提示细化）

- 本次仅调整前端校验信息的呈现方式，后端接口及 JSON 模板无需更新：`/template` 仍按照原格式返回 `validation_rules`，新增的“当前值/参照值/比例”明细由前端根据已有数值计算得出。
- 若需要扩展提示内容，只需确保规则中附带的 `min/max/reference_row/columns` 等字段准确，前端就能自动读取并显示最新阈值。

## 会话小结（2025-11-22 全局校验开关 API）

- 新增 `/projects/{project_key}/data_entry/validation/master-switch`：
  - `GET`：读取 `backend_data/数据结构_基本指标表.json` 的 `__global_settings__` 并返回 `validation_enabled`。
  - `POST`：仅“系统管理员”可调用，接受 `{"validation_enabled": true/false}`，写入 `校验总开关/validation_master_switch/validation_master_toggle/validation_enabled`，并通过临时文件替换确保落盘成功。
- 建议任何批处理脚本都调用该接口而非直接手改 JSON，避免格式差异或并发写入冲突。
- 若需要扩展到其他数据源，可在 `DATA_FILE_CANDIDATES` 中新增路径并复用 `_load_master_validation_config()` 逻辑。
- 同步新增 `/projects/{project_key}/data_entry/sheets/{sheet_key}/validation-switch` GET/POST，用于读取 & 修改各表的 `校验开关`；写操作同样仅 Global_admin/系统管理员可用，后端会在对应模板文件中更新 `validation_enabled/校验开关` 字段并安全落盘。
- 各模板若存在虚拟校验项（如“全厂热效率”）却无对应行，可在 `backend_data/数据结构_基本指标表.json` 中为该表新增 `校验说明映射`，例如 `{"全厂热效率": "标煤耗量"}`，表示只要在“标煤耗量”的解释列填写原因即可放行该错误。接口会将该映射透传给前端。

## 会话小结（2025-11-22 数据填报校验配置批量化）

- `backend_data/数据结构_基本指标表.json` 现在维持 `__global_settings__.校验总开关 = false` 以便一键停用；但除 `BeiHai_co_generation_Sheet`、`BeiHai_gas_boiler_Sheet`、`Coal_inventory_Sheet` 外，其余常规模板均显式标记 `校验开关: true`，接口返回的 `validation_enabled` 可直接指导前端是否运行规则。
- 针对拥有 `rate_overall_efficiency` 的电厂模板（北海水炉、香海、金州、北方、金普、庄河），补充了“全厂热效率” `expression_range` 规则：复用 `(value('供热量') + value('售电量') * 36) / (29.308 * value('标煤耗量'))` 计算虚拟指标，要求本期/同期均落在 0.5~0.95，且本期对同期的波动不超过 ±10%，违规则级别为 error。
- 针对具备“耗水量”行的模板（包括研究院）新增 `number_range + column_ratio` 组合：本期与同期均需大于 0，同时强制本期位于同期 50%~115% 区间。供热公司模板仅启用耗水量规则（缺乏标煤字段无法计算热效率），煤炭库存/供热分中心明细因无对应指标保持不变。
- 若需临时停用，可将某模板的 `校验开关` 置为 `false` 或直接删除 `校验规则` 块；彻底关闭则修改全局 `校验总开关`。

## 会话小结（2025-11-21 Dashboard 气温标签提示）

- `/api/v1/projects/daily_report_25_26/dashboard` 仍按 `sections['1']` 返回“本期/同期”逐日气温数组及 `meta.pushDate`；前端据此在折线图中定位 push_date，并在蓝/橙 markPoint 之间自动判定标签是否需要左右错位（温差 ≤1℃ 时启用）。若 push_date 或同期数组缺失，将跳过 markPoint 渲染。
- 当前逻辑要求主/同期桶均能通过 `normalizeDateKey(label)` 匹配，如需变更日期格式，请维持 `YYYY-MM-DD` 或可被 `Date.parse` 识别的字符串，否则前端无法计算 highlight index。
- 回滚仅牵涉前端展示，后端接口无需改动；若未来去掉该标签策略，保持 `sections['1']` 的结构不变即可。

## 会话小结（2025-11-19 Dashboard 净投诉量累计）

- `/dashboard` 的 “集团汇总净投诉量” 现映射到 `sum_season_total_net_complaints` 指标，并直接取 `value_biz_date/value_peer_date` 作为供暖期累计本期/同期值，避免再次累加 `amount_daily_net_complaints`。
- `_build_group_summary_metrics` 引入 `SUMMARY_PERIOD_ITEM_OVERRIDES` 与 override mode：当 0.5 折叠表解析“净投诉量（件）”时，会按“当日/本月累计/本供暖期累计净投诉量”三个指标分别取值，且全部走 `value_biz_date/value_peer_date`。
- “0.5卡片详细信数据表（折叠）”下的“净投诉量（件）”分三列取值：本日=“当日净投诉量”、本月累计=“本月累计净投诉量”、本供暖期累计=“本供暖期累计净投诉量”，均借助 `项目字典` 别名解析，无需前端硬编码。
- 2025-11-19 本次仅前端格式调整，后端逻辑保持不变。
- 若后续要扩展至“省/市平台净投诉量”等拆分指标，可继续在配置内新增行，后端无需改动；如需回滚该功能，删除 `_fill_cumulative_cards` 的新 mapping 条目即可。

## 会话小结（2025-11-18 Dashboard 平均气温 trace 撤销）

- 为避免后端日志过量，`backend/services/dashboard_expression.py` 中 `_build_temperature_summary_metrics` 先前新增的 `[dashboard-trace] temperature-summary …` 输出已移除；现在 `/dashboard` 不再在服务器控制台打印日均/本月/供暖期均温的原始值。
- 此变更不影响接口返回，若后续仍需调试，可临时在本地分支恢复该 `logger.info` 行或使用数据库查询对比。

## 会话小结（2025-11-17 Dashboard 顶部折叠表）

- 本次需求仅调整前端 `DashBoard.vue` 展示方式：以 `/dashboard` 现有返回中的累计 headline（来源 `sum_basic_data`/`groups`）组合出 4×5 表格，并新增折叠交互。后端接口、视图、配置数据均无需改动。
- 请继续保证 `/api/v1/projects/daily_report_25_26/dashboard` 响应里提供 `9.累计卡片` 的 `计量单位` 与本期/同期数值，以及（若存在）`0.5卡片详细信数据表（折叠）` 节点，供前端在折叠表格中渲染与排序；如需回滚折叠表，仅需恢复前端模板即可，后端无须操作。
- `_fill_summary_fold_section` 现已落地：后端会从 `calc_temperature_data` 直接写入日均气温/本月平均/供暖期平均，同时读取 `groups` 视图的 `value_biz_date/sum_month_biz/sum_ytd_biz`（含 `*_peer` 字段）填充标煤、边际利润、投诉列，确保 0.5 节点返回的就是展示用的最终数值。

## 会话小结（2025-11-17 数据看板配置蓝图）

- 新增并扩展 `backend_data/dashboard_frontend_config.json`，作为仪表盘配置驱动蓝本。除原有 `/dashboard` 接口响应结构、全局组织顺序/单位、1~9 号板块组件布局外，本次补充 `data_contracts`，明确每个模块所依赖的真实视图/表（`sum_basic_data`、`groups`、`temperature_data`、`coal_inventory_data`、`calc_temperature_data` 等）、item_key、公司口径与时间窗口。
- 配置中的 `widgets.summary_cards`、`sections[*].data_mappings` 等字段现可指向具体 `contract_id`，为后端未来“按配置生成查询”或“透传配置给前端”提供一手契约，逐步淘汰硬编码。
- 当前后端实现尚未动态读取该文件，仅存档于 `backend_data`；如需回滚，删除该 JSON 并在 `configs/progress.md` 记录即可。

## 会话小结（2025-11-15 会话持久化筹备）

- 在 `backend/sql` 新增 `create_auth_sessions_table.sql`，定义 `auth_sessions` 表结构：包含 token、username、user_group、unit、hierarchy、权限/可审批单位 JSONB、签发/过期/最近访问时间等字段，并创建 `username`、`expires_at` 索引。
- 目的：为后续将 `AuthManager` 的内存会话迁移到 PostgreSQL 提前准备建表脚本，保证服务重启或多实例部署时登录状态可延续。
- 当前后端逻辑尚未接入该表；若需要落地会话持久化，可执行该 SQL 并将登录/验证/注销流程改为读写此表即可。回滚仅需删除脚本或忽略执行。

## 会话小结（2025-11-15 前端提示联动）

- 前端 `DataEntryView` 的提交成功提示文案从“提交成功，数据已入库。”调整为“提交成功，数据已入库！”，后端接口与返回结构不变；提醒记录在此以便后续追踪前后端交互文案。

## 会话小结（2025-11-15 集团张屯煤耗汇总）

- `backend/sql/groups.sql` 新增 `group_sum_raw_zhangtun`、`group_sum_std_zhangtun` 两个 CTE，并在 `company = 'Group'` 的输出中追加 `sum_consumption_amount_raw_coal_zhangtun`（原煤耗量汇总·张屯）与 `sum_consumption_std_coal_zhangtun`（标煤耗量汇总·张屯）两个指标。
- 计算逻辑：以 `sum_basic_data` 视图为底，先聚合主城区（`BeiHai/XiangHai/GongRe`，对应视图中的 `ZhuChengQu` 汇总）、`JinZhou/BeiFang/JinPu` 的 `consumption_amount_raw_coal` 或 `consumption_std_coal`，再叠加 `ZhuangHe` 公司报送的 `*_zhangtun` 特殊口径，分别对日值、7 日、当月、供暖期累计以及同期数做逐列求和。
- 前端或 BI 查询 `groups` 视图时，`company='Group'` 将多出上述两条记录，可直接沿用其它量化指标的字段（`value_biz_date/sum_ytd_peer` 等）；如需回滚，删除两个 CTE 及对应 `UNION ALL` 片段即可恢复旧版结构。

## 会话小结（2025-11-16 张屯口径别名同步）

- `backend_data/数据结构_数据看板.json` 新增顶层 `口径别名` 映射（如 `标煤耗量汇总(张屯)` → `标煤耗量`、`原煤耗量汇总(张屯)` → `原煤耗量`），用于标记“张屯汇总”指标在 UI 上的展示名称。
- 该映射由前端 `DashBoard.vue` 读取，渲染时依旧显示“标煤耗量/原煤耗量”，同时后台照常按 `sum_consumption_amount_*_zhangtun` 指标取数；删除该映射即可回滚到旧表现。
- 2025-11-16 晚间：前端在解析别名时出现“字符串递归替换”导致浏览器内存暴涨，本文件无须修改，但已记录问题原因，详见前端 README 的“张屯指标别名渲染”段（别名映射保持不变，只需避免无限替换）。
- 2025-11-16 夜间：`dashboard_expression._fill_simple_metric` 支持在配置中为各公司写自定义表达式（如“标煤耗量汇总(张屯)”），若表达式为空则回落到根指标；`_fill_cumulative_cards` 也改用 `sum_consumption_std_coal_zhangtun` 作为集团供暖期标煤耗量的数据来源，确保前端 5/9 号段读取到张屯汇总数。

## 会话小结（2025-11-13 数据看板业务日输入稳定性）

- 本次修复集中于前端 `DashBoard.vue`：当用户在仪表盘手动选择业务日期时，不再以 `/dashboard` 响应中的 `push_date` 强制覆盖输入框，仅在 `show_date` 未指定且本地值为空的情况下同步，以免界面显示的日期与查询参数不一致。
- 后端 `/api/v1/projects/daily_report_25_26/dashboard` 接口签名、参数与返回结构保持不变；仍建议在响应中保留 `push_date` 字段，供前端初次加载或清空输入时回落使用。
- 回滚流程（若要恢复旧交互）：前端重新在每次响应后无条件同步 `payload.push_date` 即可，后端无需改动。

## 会话小结（2025-11-12 数据展示页业务日自动刷新）

- 最新交互调整位于前端 `DisplayRuntimeView.vue`：选择新的业务日期时会在 400ms 去抖后自动调用 `/api/v1/projects/{project_key}/runtime/spec/eval`，若先前请求仍在执行则排队等待，避免向后端并发发送相同查询。
- 后端接口签名、参数与返回结构保持不变；需要确保 `/runtime/spec/eval` 在 `biz_date` 为空字符串时继续按 `regular` 分支处理，以兼容用户清空日历触发的自动刷新。
- 回滚流程：前端可移除 `pendingAutoRefresh` 与相关监听；后端无需回滚。

## 会话小结（2025-11-12 累计卡片气温逐日序列）

- `/api/v1/projects/daily_report_25_26/dashboard` 的“9.累计卡片”板块新增逐日气温输出：`供暖期平均气温` 现返回 `[{"date": "YYYY-MM-DD", "value": <float|None>}, ...]`，覆盖供暖期起始日至 `push_date` 全部日期；同期数组按上一供暖季同区间映射。
- 新增 `_fetch_daily_average_temperature_map` 辅助函数，`_fill_cumulative_cards` 改为按日期补全缺口并返回带 `None` 的完整序列，其他 `sum_ytd_*` 指标仍使用 `groups` 视图。
- 若需要恢复旧版单值返回，可还原 `dashboard_expression.py` 中上述两个函数即可。

## 会话小结（2025-11-11 填报提交倒计时刷新）

- 交互更新位于前端 `DataEntryView`：提交成功后 3 秒倒计时提示，倒计时结束调用 `reloadTemplate()` 再拉当前业务日期数据（不整页刷新），以便立即在同一业务日期下查看回填结果。
- 后端 `/submit` 行为、返回结构与事务逻辑未改动；回滚时仅需恢复前端组件即可。

## 会话小结（2025-11-11 单耗卡片布局与视觉调整）

- 近期连续两次更新集中在前端（`frontend/src/daily_report_25_26/pages/DashBoard.vue`），包括栅格跨度改为 12、柱状图高度提升至 360px、以及本期/同期配色统一为蓝与橙；后端 `/api/v1/projects/daily_report_25_26/dashboard` 的 `unitSeries` 返回结构与字段命名均保持不变。
- `evaluate_dashboard` 仍按编号解析 `data['4.供暖单耗']`，未引入新字段或排序调整，因此后端无需协同改动。
- 若前端需回滚旧布局或颜色，只需恢复上述 `.vue` 文件，无需对后端进行任何修改或部署。
- 同日补充：单耗卡片的标签逻辑已在前端拆分为“本期/同期”各自展示，后端数据结构无需配合调整。

## 会话小结（2025-11-11 “集团汇总”文案同步）

- 配置 `backend_data/数据结构_数据看板.json` 及 `单位字典` 中的“集团全口径”统一改名为“集团汇总”，以保持 UI 命名一致；`evaluate_dashboard` 在 `get_section_by_index` 中追加新标题别名，兼容旧配置。
- `/api/v1/projects/daily_report_25_26/dashboard` 现返回“集团汇总”作为公司中文名，业务含义不变；若需恢复旧称谓，仅需还原上述配置与别名即可。
- 其他接口、SQL 视图及聚合逻辑未改动，联调时关注前端是否同步更新 fallback 数组即可。

## 会话小结（2025-11-11 数据看板段名序号化）

- 状态：`/dashboard` 渲染流程现根据段落编号前缀（例如 `1.`、`6.`）定位配置节点，允许自由调整中文标题。
- 改动：`services/dashboard_expression.py` 引入 `_build_section_index_map` 与 `get_section_by_index`，`evaluate_dashboard` 统一使用序号解析；投诉板块仍沿用 `_fill_complaint_section`，但不再依赖“当日省市平台服务投诉量”字面值。
- 影响：只要在 `backend_data/数据结构_数据看板.json` 中保留数字编号，前后端即可随配置改名同步展示；若需回滚，恢复旧版 `evaluate_dashboard` 并同步撤销前端 `resolveSection` 即可。
- 下一步：若后续希望完全去掉编号，可在配置中增加 `type` 字段并扩展匹配策略；当前方案已满足标题改名与排序需求。

## 会话小结（2025-11-11 净投诉面积口径迁移）

- 将正式使用的视图脚本 `backend/sql/sum_basic_data.sql` 与 `backend/sql/groups.sql` 中“万平方米省市净投诉量”分母从 `amount_whole_heating_area`（挂网面积）调整为 `amount_heating_fee_area`（供暖收费面积），保持集团/主城区聚合与公司明细口径一致。
- `create_view.sql` 仅作为备份样例，已恢复原挂网面积配置；回滚时只需把上述两个文件内的常量项改回并刷新数据库视图。
- 接口字段与单位保持不变，建议在刷新视图后对比历史报表确认数值变化符合收费面积口径预期。

## 会话小结（2025-11-10 仪表盘加载提示 & 填报反馈）

- 本次改动集中在前端：仪表盘增加加载提示、数据填报页面增加提交成功/失败提示条。
- 后端 API、数据模型与权限配置保持不变，无需额外联调；现有 `/dashboard` 与 `/submit` 调用方式照旧。

## 会话小结（2025-11-10 数据库连接池扩容）

- `backend/db/database_daily_report_25_26.py` 的 `create_engine` 现指定 `pool_size=20, max_overflow=40, pool_timeout=60, pool_recycle=1800`，缓解 `/dashboard` 高频调用触发的 QueuePool timeout。
- 接口签名与查询逻辑未改动；如需恢复旧设置，将上述参数移除即可。
- requirements.txt 新增 `psycopg2-binary`，修复容器环境缺乏 PostgreSQL 驱动导致 v1 路由未挂载、/api/v1 全部 404 的问题。

## 会话小结（2025-11-10 供暖单耗柱距优化）

- 本次仅调整前端 `DashBoard.vue` 中“供暖单耗”柱状图的间距配置，并清理页面所有数值标签的白色背景，后端 `/dashboard` 数据结构未发生变化。
- 现有 `data.4.供暖单耗` 节点继续输出既定格式；若未来调整字段，仅需通知前端同步图表配置，无需额外后端适配。

## 会话小结（2025-11-10 投诉卡片双图拆分）

- 本次仍为前端展示层调整：投诉量卡片改为两张柱状图 + 表格组合，后端 `/dashboard` 第六段返回结构不变，无需调整 `_fill_complaint_section`。

## 会话小结（2025-11-10 仪表盘修复与PDF下载）

- 本次变更主要集中在前端，修复了仪表盘组件的渲染错误，并新增了客户端的PDF下载功能。
- 后端代码、接口或配置未做任何修改。

## 会话小结（2025-11-10 投诉标签零值处理）

- 本次变更仅涉及前端展示层；后端 `/dashboard` 输出结构与 `_fill_complaint_section` 逻辑保持不变，无需改动。

## 会话小结（2025-11-10 页面入口信息脱敏）

- 状态：前端在页面选择视图隐藏了模板文件路径，后端 `list_project_pages` 返回结构维持 `{page_key/page_name/config_file}` 不变。
- 说明：`PROJECT_LIST_FILE` 仍以 `数据源` 字段承载模板路径，前端通过本地映射生成业务描述；接口继续透传该字段供路由 query 使用。
- 影响：无需调整 `_normalize_pages` 或项目配置文件；如需回滚，只需恢复前端模板即可。
- 下一步：若后续希望后端提供正式描述，可在 `项目列表.json` 中新增 `页面描述` 字段并透传给前端，替代本地映射。

## 会话小结（2025-11-10 项目列表补充页面描述）

- 状态：`backend_data/项目列表.json` 已为各页面补充 `页面描述`。
- 改动：`_normalize_pages` 透传该字段到响应体的 `page_description/description`；补齐旧格式回退值为空字符串。
- 影响：前端直接使用接口返回描述，不再依赖硬编码；若配置缺失描述仍会回退到前端映射。
- 下一步：新增页面时务必在配置补齐 `页面描述`；如需多语言支持，可扩展字段结构并在接口中透传。

## 会话小结（2025-11-10 投诉板块数据填充）

- 新增 `_fill_complaint_section`：支持同时拉取“当日省市平台服务投诉量”“当日净投诉量”两个指标的本期/同期值，解析 `groups` 与 `sum_basic_data` 配置，按 `push_date` 查询 `sum_basic_data` 视图并写回 `dashboard` 响应。
- `/dashboard` 内第六段改为调用新助手，输出结构保持 `{指标:{阶段:{company:value}}}`，默认单位沿用配置中的“件”；缺失数据时回退 0。
- 适配前端：卡片图表现根据返回的多指标结构渲染四条柱状系列，摘要数值默认取“集团全口径”本期投诉量。

## 会话小结（2025-11-09 气温/边际利润卡片面积调整确认）

- 状态：前端调整了气温与边际利润卡片的宽度与高度，后端 `/dashboard` 输出结构保持不变。
- 说明：该视觉修改不影响后端字段解析，仍按既定 `data.1.逐小时气温`、`data.2.边际利润` 节点提供数据。
- 影响：统一 legend 底部位置及表格盒模型后，坐标轴刻度不再被遮挡，气温表格也无多余滚动条，“投诉量”卡片宽度调整为 6 列且移除满宽标记，三张供暖单耗卡片统一宽度为 4 列，“标煤消耗量对比”与“煤炭库存”同排为 6 列，柱状图标签启用 `labelLayout.hideOverlap`；后端无需配合改动，若新增字段前端可在现有布局中继续呈现。
- 下一步：后端可专注完善相关节点的数据准确性、补齐同期对比等。

## 会话小结（2025-11-09 边际利润表格回归图表卡片）

- 状态：前端将边际利润表格重新并入“边际利润简报”卡片，与“气温变化情况”同排展示；后端 `/dashboard` 输出结构维持不变。
- 说明：表格仍依赖 `data.2.边际利润` 节点，字段解析逻辑不变；前端仅调整布局与滚动样式。
- 影响：若后端扩展该节点字段，可继续在当前卡片中呈现；若计划拆分更多信息，需提前协调前端布局。
- 下一步：可考虑在接口中提供分页或摘要字段，以匹配前端卡片内的滚动展示。

## 会话小结（2025-11-09 边际利润板块布局调整确认）

- 状态：前端将“边际利润简报”和“收入分类对比”放置同一行，并新增独立“边际利润明细”表格卡片；后端 `/dashboard` 输出结构保持不变。
- 说明：前端仍读取 `data.2.边际利润` 节点生成图表与表格；表格从原卡片拆分为独立卡片，不影响字段解析。
- 影响：若后端调整节点名称或列顺序，需提醒前端同步更新表格映射；当前接口无需改动。
- 下一步：持续完善该节点数据（如同比/环比），前端可直接在新卡片上展示。

## 会话小结（2025-11-09 仪表盘 Trace 选项移除确认）

- 状态：前端仪表盘移除 Trace 复选框，后端 `/api/v1/projects/daily_report_25_26/dashboard` 等接口参数保持不变。
- 说明：前端仍按原逻辑请求仪表盘数据，未再上传 `trace` 标记；后端无需配合改动。
- 影响：若后端仍保留调试 trace 逻辑，可通过其他工具触发；若需重新支持前端开关，应与前端协作新增安全的内部入口。
- 下一步：专注完善仪表盘数据填充与日志追踪方案，必要时提供独立的调试接口。

## 会话小结（2025-11-09 数据看板布局确认）

- 状态：本次调整仅涉及前端仪表盘的视觉布局，后端 `/api/v1/projects/daily_report_25_26/dashboard` 等接口结构保持不变。
- 说明：前端压缩摘要卡片尺寸并统一主体卡片高度，仍按既有字段 `show_date`、`push_date`、`data` 各 section 渲染；后端无需配合改动。
- 影响：布局优化后，前端依旧使用原模板字段渲染各板块；若后续调整返回结构，请提前同步前端确认映射。
- 下一步：后端可聚焦完善剩余板块的数据填充与日期校验逻辑，为前端布局优化后的组件提供完整数据源。

## 会话小结（2025-11-09 边际利润接口前端对接确认）

- 状态：前端仪表盘已开始直接读取 `/api/v1/projects/daily_report_25_26/dashboard` 返回的“2.边际利润”节点，展示集团及各单位的真实边际利润与可比煤价边际利润。
- 说明：当前接口仍由 `services/dashboard_expression.evaluate_dashboard` 组装，字段名需保持 `直接收入`、`煤成本`、`外购热成本`、`水、电及辅材成本`、`边际利润`、`可比煤价边际利润`，否则前端将无法正确取值；前端折线节点现直接展示可比煤价边际利润（一位小数），若后端返回非数值或字符串需及时修正。
- 影响：后端若调整字段或命名需同步更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 的映射逻辑；未触及其他 API。
- 下一步：可在后端补充单元测试或监控，确保上述字段在各公司均有返回，或提供同期数据接口以支持前端的同比展示。

## 会话小结（2025-11-09 集团收入明细前端对接确认）

- 状态：前端已将“3.集团全口径收入明细”图表切换为 `/dashboard` 返回的真实数据，依赖 `groups` 视图输出的 `暖收入/售电收入/售高温水收入/售汽收入` 等科目。
- 说明：请保持该节点结构中“本期”“同期”两个对象的键名及顺序稳定；若新增或更名收入科目，应同步告知前端调整映射及显示顺序。前端柱状图现于顶部直接显示本期、同期数值（保留一位小数），若返回值为非数值或缺失会显示 `—`，请及时修正数据。
- 影响：后端字段缺失会在前端以 0 兜底绘图，但建议确保每个科目均返回数值以避免误读。
- 下一步：可在后端补充单位说明或增加科目分组，供前端扩展更多对比分析。

## 会话小结（2025-11-09 单耗板块前端对接确认）

- 状态：前端“单耗”板块已改为读取 `/dashboard` 的“4.供暖单耗”节点，并拆分为热/电/水三张双柱图，分别展示本期与同期数据。
- 说明：请保持该节点结构中 `计量单位` 键及“供暖热单耗/供暖电单耗/供暖水单耗”字段名称稳定，前端 tooltip 会直接引用相应单位文本；若某单位缺值，前端会显示 `—` 标签并保留占位。
- 影响：接口若返回非数值将导致图表标签显示 `—`，请确保数据为浮点；若字段缺失，前端会回退到演示数据。
- 下一步：后端可提供更多单耗指标或补充同比/环比字段，前端即可扩展图例展示。

## 会话小结（2025-11-09 标煤耗量板块前端对接确认）

- 状态：前端“标煤消耗量对比”图表已切换为 `/dashboard` 返回的“5.标煤耗量”节点，本期/同期数据、表格和摘要卡片随接口刷新并统一保留一位小数。
- 说明：该节点须提供“本期”“同期”两个对象，键名为单位中文（如“集团全口径”），字段值为数值；缺失时前端会回退演示数据。若新增单位，请保持与前端显示顺序一致或同步更新。
- 影响：若后端返回非数值/字符串，图表会显示 `—` 并导致标签对齐偏差，请确保输出浮点类型；集团全口径的本期值用于头部卡片展示。
- 下一步：可在后端追加同比、环比或环节拆分字段，前端即可扩展指标或进一步可视化。

## 会话小结（2025-11-08 数据看板刷新按钮移除）

- 状态：本次动作仅清理前端仪表盘头部的临时“刷新”按钮，后端接口与配置保持原状。
- 说明：按钮、顶部“今日/业务日期”静态文字及 `refreshDashboard` 占位逻辑被删除，Trace 开关与业务日期选择仍只在前端生效。
- 影响：后端 `/template`、`/submit`、`/query` 等既有接口无变动；待 `/dashboard` API 实现后再结合日期参数返回数据。
- 下一步：规划 `/dashboard` 接口时，可考虑支持 `biz_date` 与可选 `trace` 参数，以便前端直接调用。

## 会话小结（2025-11-08 数据看板煤炭库存聚合修正）

- 状态：`services/dashboard_expression.py` 的 `_fill_coal_inventory` 现按 `company_cn + storage_type_cn` 聚合当日 `coal_type` 明细，避免多条记录互相覆盖导致返回 0。
- 改动：构建库存缓存时对同一仓储类型累计求和，并对空值判空处理；模板中的集团合计表达式继续基于聚合结果执行逐公司累加。
- 影响：`GET /api/v1/projects/daily_report_25_26/dashboard` 的“7.煤炭库存明细”模块开始返回实际库存合计数值；如需回滚，请恢复该函数旧版赋值方式。
- 下一步：可在后续版本补充单元测试，确保不同煤种/仓储组合的聚合逻辑长期稳定；如需增加同期或同比展示，可在模板扩展对应字段并沿用现有求和策略。

## 会话小结（2025-11-08 气温序列缺测处理）

- 状态：`_fetch_temperature_series` 现在对缺失小时返回 `None`，不再以 0 补齐，避免平均温度被拉低。
- 改动：温度查询逻辑保持 24 小时顺序输出，但缺测项保留 `None`，供前端按需忽略；真实记录继续返回四舍五入的浮点数。
- 影响：`/dashboard` 的“1.逐小时气温”模块在缺测情况下不再混入 0，前端均值计算与展示更贴近实际；如需回滚，请恢复旧版填充逻辑。
- 下一步：待温度数据完整后，可评估在后端补充缺测填补策略（如线性插值），目前默认由前端识别空值。

## 会话小结（2025-11-08 供热分中心单耗明细接入）

- 状态：数据看板新增“8.供热分中心单耗明细”模块已接入后端，直接从 `sum_basic_data` 视图获取各中心的热、电、水单耗本期值。
- 改动：`dashboard_expression.py` 增加 `_fill_heating_branch_consumption`，在 `evaluate_dashboard` 中调用该函数，对模板中的每个中心逐项填充 `value_biz_date`（空表达式默认按指标中文名取值）。
- 影响：`/dashboard` 返回的数据现包含真实单耗数值，“计量单位”节点保持原样下发至前端；如需回滚，可删除新函数与调用逻辑。
- 下一步：可根据需要扩展同期或同比逻辑，或在前端对接图表展示；建议后续补充自动化测试验证视图取值与映射关系。

## 会话小结（2025-11-08 数据看板 API 初版）

- 状态：新增 `GET /api/v1/projects/daily_report_25_26/dashboard` 接口，支持 `show_date` 查询参数（默认空字符串）。
- 改动：创建 `services/dashboard_expression.py` 渲染引擎，统一读取 `backend_data/date.json` 与 `backend_data/数据结构_数据看板.json`，并输出 `DashboardResult`；API 调用该引擎返回 `data`、`project_key`、`show_date`、`push_date`、`generated_at`、`source`。
- 影响：目前仍返回静态 JSON，占位字段 `展示日期` 会根据传入的 `show_date` 写回；后续可替换为实时数据库聚合结果。
- 下一步：在数据库设计完成后接入真实查询逻辑，并按照需要补充 trace/调试字段或缓存策略。

## 会话小结（2025-11-07 数据填报指标联动）

- 状态：数据填报模板与标准报表提交流程现支持 `linkage_dict`（配置别名“指标联动”）字段，后端会在入库前同步联动指标的数值，避免出现同列不同值。
- 改动：`daily_report_25_26.py` 新增 `LINKAGE_DICT_KEYS` 与 `_apply_linkage_constraints`，在模板/查询响应透传 `linkage_dict`，并在标准报表 `submit` 前按模板映射同步行值；同时引入 `_detect_readonly_limit_backend`、`Sequence` 类型以匹配前端的“计量单位”锁列逻辑。
- 影响：在 `backend_data/数据结构_基本指标表.json` 中声明 `"指标联动"` 的表格会在加载及提交时自动保持主子项数值一致，联动字段会随模板一并返回；如需回滚，可移除上述常量与辅助函数，恢复旧的自由填报行为。
- 下一步：可考虑结合审计需求，对历史存在差异的联动项输出告警列表，或扩展 `_apply_linkage_constraints` 至煤炭库存等特殊模板分支。

## 会话小结（2025-11-20 数据填报行内校验）

- 状态：模板接口新增 `validation_rules`（JSON 中可用 `校验规则`/`数据校验` 别名）字段，`GET /projects/{project_key}/data_entry/sheets/{sheet_key}/template` 会与 `item_dict` 等字典一同返回，前端得以在本地执行行列校验。
- 模板写法：以 `backend_data/数据结构_基本指标表.json` 中的 `BeiHai_co_generation_Sheet` 为例，`"校验规则": { "发电量": [{ "type":"number_range","min":0,"columns":[2,3],"message":"发电量需为非负数"}], "其中：电厂耗水量": [{ "type":"less_equal_than","reference_row":"耗水量","columns":[2,3]}] }`。键名对应行标签，`columns` 以 0 基列序定义作用范围。
- 规则语义：
  - `number_range`：支持 `min`/`max`/`allow_empty`/`level`/`message`，用于约束具体列的取值范围；
  - `less_equal_than`：通过 `reference_row`（可写中文行名）比较行间关系，默认不允许被比较行大于参照行，可选 `tolerance` 指定容差。
  - 2025-11-20 扩展：
    - `column_ratio`：在同一行内比较“本期 vs 同期”或任意两列的比例，字段包含 `columns`（被检测列）、`reference_column`、`min_ratio`/`max_ratio`，适合声明“本期值在同期的80%-120%之间”等规则；
    - `expression_range`：支持以 `value('行名')`（默认使用当前列）为基础编写任意算式，并设置 `min/max` 或 `reference_column`+`min_ratio`/`max_ratio`，可通过 `depends_on` 显式声明依赖行，示例：`(value('供热量') + value('售电量') * 36) / (29.308 * value('标煤耗量'))` 对应“全厂热效率”；
    - `virtual: true` + `target_label`：用于声明“仅校验、不展示”的虚拟指标，例如衍生热效率，模板 `rows` 中无需增加对应行，系统会基于依赖行执行校验并在前端提示 `target_label`。
- 校验开关：模板字典可额外提供 `validation_enabled` / `enable_validation` / `校验开关`（布尔值），后端会将其透传为 `validation_enabled` 字段；当设为 `false` 时，前端跳过所有规则解析与提示，仅保留基础填报能力。
- 总开关：`backend_data/数据结构_基本指标表.json` 顶层的 `__global_settings__`（字段如 `校验总开关`）可统一控制校验启停；接口在加载模板时会读取该值并与模板局部 `校验开关` 取“全局 && 局部”，实现一处暂停全部校验。
- 兼容性：`daily_report_25_26.py` 的 `DICT_KEY_GROUPS` 已纳入 `validation_rules`，因此老模板无需修改即可继续返回 `item_dict` 等已有字典；新字段缺省时后端/前端都会自动跳过校验。
- 回滚方案：若未来不再需要本地校验，可在模板中删除 `"校验规则"` 段落，并在 `DICT_KEY_GROUPS` 中移除 `validation_rules` 配置即可恢复原状。

## 会话小结（2025-11-07 审批撤销能力）

- 状态：审批流程新增 `/workflow/revoke` 接口与 `can_revoke` 权限，可撤回已批准的单位并恢复 `pending` 状态。
- 改动：`schemas/auth.py` 引入 `WorkflowRevokeRequest` / `can_revoke` 字段，`services/auth_manager.py` 扩展 `ActionFlags` 解析与权限输出，`workflow_status.py` 新增 `mark_pending` 重置逻辑，`daily_report_25_26.py` 注册撤销路由并校验权限；权限矩阵为 Global_admin / Group_admin / ZhuChengQu_admin 打开 `can_revoke`。
- 影响：具备撤销权限的账号可在可见单位范围内将审批状态回写为 `pending`（`status.json` 恢复 `pending/null/null`），其它接口行为不变；如需回滚，移除 `can_revoke` 字段并恢复上述文件即可。
- 下一步：如需追踪撤销记录，可在 `status.json` 扩展撤销人/时间字段并于前端提示。

## 会话小结（2025-11-07 数据展示页加载提示同步）

- 状态：数据展示页仅调整前端占位文案，后端视图查询与接口返回结构保持不变。
- 说明：`DisplayRuntimeView.vue` 在等待 `/runtime/spec/eval` 与数据库视图响应时展示“数据载入中...”，加载结束却仍无列数据时继续提示“无展示数据”，以降低首屏空白造成的误判。
- 影响：后端接口无需改动；如需回滚，可恢复前端组件旧版本即可，还原原有占位文案。
- 下一步：若后续需要提供更细粒度的加载进度，可评估在接口层增加耗时指标或分页/缓存方案，与前端提示配合。

## 会话小结（2025-11-03 仪表盘 DashBoard.vue 文件审查）

- 状态：本次操作为审查 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 文件内容，无代码改动。
- 说明：该文件是一个 Vue3 组件，用于展示仪表盘，包含本地 `Card`、`Table` 和 `EChart` 组件，以及模拟数据和样式。仪表盘展示了与“生产日报”相关的各项指标和图表。
- 影响：本次操作仅为文件审查，无任何代码改动，因此无影响范围。
- 下一步：根据项目计划，可以开始将仪表盘组件与后端 `dashboard/summary` 接口进行联调，替换模拟数据为真实数据。

## 会话小结（2025-11-06 移除 placeholder 页面配置）

- 状态：项目 `daily_report_25_26` 的页面清单中已删除 `placeholder` 占位项，防止后端接口继续暴露空页面。
- 改动：`backend_data/项目列表.json` 移除 `pages.placeholder` 节点，仅保留真实存在的页面及调试入口。
- 影响：`/api/v1/projects/daily_report_25_26/pages` 返回值不再包含占位页面，前端项目页不会再渲染该链接；如需回滚，可恢复该 JSON 节点。
- 下一步：如需支持“纯页面”而非配置驱动的入口，可在后续迭代中扩展 JSON 结构（例如增加 `type` 标记或跳转路由字段）。

## 会话小结（2025-11-06 审批页面默认业务日调整）

- 状态：审批视图默认业务日改为使用 workflow status 返回的 `biz_date`（东八区昨日），`set_biz_date` 仅影响展示页与项目页提示。
- 改动：前端 `ApprovalView.vue` 调用 `getWorkflowStatus` 获取 `biz_date`，在 `biz_date` 模式为 `regular` 时将该日期传递给 `/runtime/spec/eval`；后端无需调整。
- 影响：审批页面刷新或切换 Trace 不再读取 `set_biz_date`，仍可通过“自定义”模式手动指定日期；展示页继续受 `set_biz_date` 控制。
- 下一步：若需在审批页面显示“当前展示日期”提示，可结合 `workflow/status` 中的 `display_date` 做友好提示。

## 会话小结（2025-11-06 仪表盘前端重构同步说明）

- 状态：本次改动仅重写前端 `DashBoard.vue` 为 Vue3 组件，后端 `dashboard/summary` 接口及其它 API 未作调整。
- 影响：现有聚合接口仍输出气温、边际利润、收入分类、单耗、煤耗、投诉量与煤炭库存七大板块，可直接与新版前端页面联调；若需要回滚前端页面，无需回滚后端代码。
- 下一步：待页面切换到真实数据后，可评估是否新增缓存或物化视图以降低聚合查询压力；前端通过 CDN 引入 `echarts`，对后端接口无额外要求。

## 会话小结（2025-11-06 售电煤炭库存权限）

- 状态：售电公司填报账号 `shoudian_filler` 已在权限矩阵中显式放行 `Coal_inventory_Sheet`，补齐煤炭库存专项表的访问链路。
- 改动：
  - `backend_data/auth/permissions.json` 将 `unit_filler` 组的 `data_entry` 规则改为 `by_unit + sheets` 组合，写入 `Coal_inventory_Sheet` 白名单并刷新 `updated_at`。
  - 对应前端逻辑允许读取该显式白名单（详见前端 README），无需调整后端接口。
- 影响：售电公司账号沿用数据填报接口即可访问煤炭库存表，其余单位仍按原先的单位前缀匹配策略过滤；如需回滚，恢复权限文件旧版本即可。

## 会话小结（2025-11-06 HTTP-only 访问修复）

- 状态：补全 `deploy/nginx.http-only.conf` 的 `/api/` 反向代理，在 `ww.bash` 中加入 `VITE_API_BASE` 二次校验、构建日志以及自动同步 `latest` 标签，并新增 `ww-certbot.yml`（固定 `locookies123@gmail.com` 与 `platform.smartview.top`）便于单独拉起 HTTP-only + Certbot 的申请流程；如需调整邮箱或域名，直接在 `ww-certbot.yml` 的 `command` 中替换对应参数后再执行即可。
- 影响：HTTP-only 镜像使用默认 `/api/v1` 相对路径即可透传到后端，如需指向其它域名，可继续通过环境变量设置 `VITE_API_BASE`，脚本会输出最终取值供验证。
- 回滚：恢复 `deploy/nginx.http-only.conf` 与 `ww.bash` 的旧版本即可撤销本次部署修复。

## 会话小结（2025-11-05 仪表盘聚合服务）

- 状态：面向“数据展示-仪表盘”页面提供统一聚合接口，首版覆盖气温、边际利润、收入分类、单耗、标煤消耗、投诉量与煤炭库存七个板块。
- 改动：
  - 新增 `backend/schemas/dashboard.py` 定义仪表盘响应模型（时间序列、分组指标、煤炭库存等结构化字段）。
  - 新增 `backend/services/dashboard.py`，从 `calc_temperature_data`、`sum_basic_data`、`groups`、`sum_coal_inventory_data` 视图聚合数据，按登录用户的 `allowed_units` 过滤可见单位。
  - `backend/api/v1/daily_report_25_26.py` 暴露 `GET /api/v1/projects/daily_report_25_26/dashboard/summary` 接口，支持 `biz_date` 查询参数并返回生成时间、业务日/同期日期。
- 数据口径：温度按业务日前后三天 + 同期七日折线；各类业务指标返回本期/同期值、差值和差率；煤炭库存输出厂内/港口/在途堆积数据与合计。
- 回滚：删除上述 schema/service，移除路由注册即可恢复到无仪表盘接口的状态。

## 会话小结（2025-11-04）

- 状态：新增 `ww.bash` / `ww.ps1` 两套脚本，本地运行后会以仓库根目录为构建上下文，使用 `backend/Dockerfile.prod` 生成带时间戳标签的 phoenix-backend 镜像并推送至 Docker Hub；另补充 `ww-http-only.yml`，在无需证书时仅启动 HTTP 版前端配合后端/数据库部署。
- 改动：脚本统一写入 `BUILD_TIMESTAMP` 构建参数，便于追溯镜像来源，并在完成后打印 `BACKEND_IMAGE`、`WEB_IMAGE`、`WEB_HTTP_IMAGE` 供 `ww.yml` 或服务器 `.env` 引用。PowerShell 版本默认在纯 Windows 环境执行；两版脚本新增 `VITE_API_BASE` 校验，防止误将 `file://` 或 `C:\` 等本地路径写入构建产物。
- 部署：补充 `ww.yml`，将原本在服务器执行的构建阶段替换为直接拉取镜像，保留数据库、数据卷和 Certbot 服务；`ww-http-only.yml` 去除证书依赖，仅暴露 `80:80`，适合临时 HTTP 或使用 Cloudflare Flexible 模式的场景。后端仍通过 `./backend_data:/app/data` 读取配置。
- 下一步：建议在运行脚本前后追加最小健康检查（如临时 `docker run --rm` 调用），确保镜像可用后再推送至远端仓库。
- 视图：`backend/sql/create_view.sql` 新增 `calc_temperature_data` 普通视图，按 `temperature_data` 的日期（日粒度）聚合 `value`，输出当日最高/最低/平均温度，为天气数据统计提供聚合入口。

## 会话小结（2025-11-03）

- 状态：根据最新业务要求，`sum_basic_data` 视图中“煤成本”改为按“标煤耗量 × 标煤单价 / 10000”计算，并在所有时间窗口产出公司级指标。
- 改动：`create_view.sql` 的 `calc_coal_cost` CTE 使用 `consumption_std_coal` 叠加 `price_std_coal` 常量，替换原先的原煤耗量/单价组合；注释同步更新以便检索。
- 影响：`groups` 视图沿用 `sum_basic_data` 聚合结果，因此主城区与集团口径自动适配。后续若需回滚，可恢复 `calc_coal_cost` 中的原煤字段与常量键。
- 下一步：若还需要单独保留“原煤成本”指标，可新增独立 CTE 并在视图中以新 item 输出，避免覆盖现有字段。

## 会话小结（2025-11-02）

- 状态：已修正运行时表达式在投诉类累计指标上的取值方式，避免再次被窗口累计逻辑覆盖。
- 改动：`runtime_expression.Evaluator._value_of_item` 引入 `_PREAGG_VALUE_ITEMS` 白名单，将 `sum_month_total_net_complaints`、`sum_season_total_net_complaints` 等预聚合投诉指标固定返回 `value_biz_date/value_peer_date`；新增集合位于模块顶部，便于后续补充同类条目。
- 影响：数据展示页/审批页中“省市平台净投诉量”及其万㎡折算项在 `(本期月)/(本供暖期)` 列将与视图 `sum_basic_data/groups` 的单日累计值保持一致，不再出现额外求和。
- 新增：`/runtime/spec/eval` 在未显式指定 `biz_date` 或传入 `regular` 时，会读取 `auth_manager.current_display_date()`（映射 `backend_data/date.json` 的 `set_biz_date`），以该日期执行 `render_spec` 并在响应中回显 `biz_date`/`biz_date_mode`/`requested_biz_date`，方便展示页在同一口径下切换历史数据。
- 视图支持业务日期参数：`sum_basic_data`、`groups` 通过数据库会话变量 `phoenix.biz_date` 读取日期；运行时在查询前执行 `SET LOCAL phoenix.biz_date = :biz_date`，既保留原 SQL 中的派生计算，又允许展示页自由指定日期。
- 下一步：如需扩展到其它“不可加”指标，可追加英文键至 `_PREAGG_VALUE_ITEMS` 并验证对应模板配置。

### 增补（2025-11-02 晚 - 登录与权限）

- 新增 `services/auth_manager.py`、`services/workflow_status.py`、`api/v1/auth.py`、`schemas/auth.py`，负责账号认证、权限解析、审批状态缓存，数据源分别为 `backend_data/账户信息.json` 与新建 `backend_data/auth/permissions.json`。
- `api/v1/routes.py` 的项目页面接口会根据 `permissions.page_access` 过滤可见页面；`api/v1/daily_report_25_26.py` 默认要求 Bearer Token，新增 `/workflow/status|approve|publish` 持久化接口（Biz 日=东八区昨日），状态文件位于 `backend_data/status.json`。
- 新建 `backend_data/date.json` 统一维护“数据展示日期”，`auth_manager.current_display_date()` 若未发布当日数据则回落至上一期；发布成功后调用 `set_display_date()` 同步配置，确保展示端在审批完成前仍读取上一批数据。
- 后台默认不再设置登录时长限制（仅在显式退出或管理员清理时失效），`/auth/login|logout|me` 继续提供登录、退出、会话自查。
- “记住我的登录状态”勾选后，会将会话写入 PostgreSQL `auth_sessions` 表（默认 90 天滑动有效），服务重启或多副本部署时仍可自动恢复；未勾选则沿用内存会话，不触发数据库写入。
- 回滚方式：删除上述新增模块并恢复 `routes.py`、`daily_report_25_26.py` 相关改动即可退回原“无鉴权”状态。

### 部署说明补充（2025-11-02 深夜）

- 新增 `backend/requirements.txt`、`backend/Dockerfile.prod` 作为生产镜像专用依赖与构建脚本，构建阶段安装至 `/install`，运行阶段仅包含必要库与代码；默认执行 `uvicorn ... --workers 4`。
- 推荐配合仓库根目录的 `docker-compose.prod.yml` 统一启动数据库 / 后端 / 前端镜像，后端仍通过卷 `./backend_data:/app/data` 读取配置与上传文件。
- Windows 服务器可运行 `deploy/server_setup.bat` 自动构建并上线；Linux 主机可参考该脚本的步骤（创建数据目录 → docker compose build/up → 清理悬挂镜像）。
- 若需加入额外依赖，请更新 `backend/requirements.txt` 并重新构建 `backend/Dockerfile.prod`，无需修改开发环境 Dockerfile。
- 提供 `docker-compose.server.yml`：沿用旧项目的 nginx + certbot 布局，`web` 服务使用 `deploy/Dockerfile.web`（内置 `deploy/nginx.prod.conf`），默认监听 80/443 并反向代理至 `backend`，证书文件存放在命名卷 `certbot_etc`/`certbot_www`。运行 `bash init-certbot.sh` 会暂时启用 HTTP-only 容器、申请证书，并在成功后恢复 HTTPS 全栈。

### 单镜像打包（可选）

- 根目录新增 `Dockerfile.full` 与 `build-single-image.sh`，用于将后端 + 前端 + nginx 打包为单个镜像。
- 构建命令示例：
  ```bash
  ./build-single-image.sh           # 生成 phoenix-all:latest
  REGISTRY=registry.example.com TAG=2025-10-31 ./build-single-image.sh
  ```
- 运行示例：
  ```bash
  docker run -p 80:80 \
    -e DATABASE_URL="postgresql://user:pass@host:5432/phoenix" \
    -v $(pwd)/backend_data:/app/data \
    phoenix-all:latest
  ```
  该镜像由 supervisord 同时拉起 `uvicorn`（端口 8000）与 `nginx`（端口 80，代理 `/api/`）。

## 会话小结（2025-11-01）

- 状态：本次会话未改动后端代码与接口，运行时表达式仍沿用现有 `accuracy` 默认值输出。
- 说明：运行时表达式 `render_spec` 已输出 `accuracy_map`（行级精度覆盖），接口 `/runtime/spec/eval` 透传为 `accuracy_overrides`；前端优先使用该字段，模板读取为兜底。
- 新增：`value_*`/`sum_*` 系列函数允许通过 `value_biz_date(ZhuChengQu)`、`value_biz_date(BeiHai+XiangHai)` 等写法跨 company 取值，解析顺序为“优先视作公司名 → 否则视作项目/常量”。
- 同时支持 `value_biz_date(GongRe.本月累计净投诉量)` 这种 `company.item` 写法：优先按 company 取数，再将 item 按项目字典逆查中文名称取值（默认主表遵循模板 `default` 配置）。
- 下一步：等待你确认是否需要在后端补充 `accuracy_map` 字段或其它元数据，以减少前端额外的模板请求。

## 会话小结（2025-10-29）

- 状态：本次会话为初始化与规范确认，无后端代码改动。
- 动作：完成 Serena 项目激活与入职检查；按 AGENTS 3.9 对 Markdown 文档使用 `apply_patch` 安全降级记录进度。
- 下一步：待你指令后进入 `/template`、`/submit`、`/query` 的最小闭环实现与联调。

### 增补（2025-10-29 晚）
- runtime 表达式求值服务适配 `groups` 视图：`backend/services/runtime_expression.py` 新增 `_fetch_metrics_from_view()` 并基于模板“查询数据源.主表”在 `sum_basic_data/groups` 间切换，修复 `ZhuChengQu_approval_Sheet` 选择 `主表=groups` 时无数据显示的问题（原逻辑固定读取 `sum_basic_data`）。

### 增补（2025-10-29 夜）
- SQL 指标修正（groups 主城区）：按 `configs/10.29计算指标修正.md`，`groups` 视图中 `company='ZhuChengQu'` 的 `eco_direct_income` 由“售电+暖+售高温水+售汽”四项相加重算（不含“内售热”），实现方式为：
  - 从主城区直汇清单中排除 `eco_direct_income`；
  - 新增一段 `UNION ALL` 对四项收入进行加总后产出 `eco_direct_income` 行。
  - 其它公司与其它指标保持不变；`sum_basic_data` 中“边际利润/可比煤价边际利润”已包含外购热/内购热成本，无需修改。

### 增补（2025-10-29 夜-2）
- 常量模板识别：模板接口 `get_sheet_template` 现在识别 `_constant_sheet`，返回 `template_type: 'constant'`；查询接口早已支持按 `constant` 回填 period 列。配合前端新增的常量分支，可正确显示 `constant_data` 的已入库数据。

## 结构快照更新（2025-10-29）

- 视图职责拆分（与 `configs/10.29提示词.md` 一致）：
  - `sum_basic_data` 现仅输出公司明细粒度的 8 个时间口径聚合（不再包含任何“主城区/集团”分组）。
  - 新增视图 `groups`：基于 `sum_basic_data` 对公司集合进行再聚合，产出“ZhuChengQu（主城区）/Group（集团全口径）”两类结果，列结构与 `sum_basic_data` 一致。
- 示例数据与命名修正（新增脚本 + 规范化）：
  - 修复 Center 大小写：中心英文码统一为 `*_Center`；`sheet_name` 统一 `*_Sheet`（S 大写）。
  - 更新 `backend/scripts/generate_daily_basic_sample.py`：示例数据同时生成“本期+同期”，并满足“本期=同期×1.25（提高25%）”。
  - 新增 `backend/scripts/generate_constant_sample.py`：从 `backend_data/数据结构_常量指标表.json` 生成 `constant_data` 示例数据（period：`24-25` 同期、`25-26` 本期），并满足“本期=同期×0.8（下降20%）”。
  - 输出路径：`backend/sql/sample_daily_basic_data.(csv|sql)`、`backend/sql/sample_constant_data.(csv|sql)`。
- 计算指标：
  - 第一批（已实现）加入 `sum_basic_data`：售电/内售热/暖/高温水/售汽收入，煤/气/外购电/购水/辅材/外购热/内购热成本，直接收入、边际利润、可比煤价边际利润、全厂热效率；并新增计算行 `consumption_station_heat`（站内耗热量，特殊公司按“供热量-高温水销售量”），`amount_heat_lose` 仅对 `GongRe` 输出。
  - 第二批（已实现）加入 `sum_basic_data`：`amount_daily_net_complaints_per_10k_m2`、`rate_std_coal_per_heat`、`rate_heat_per_10k_m2`、`rate_power_per_10k_m2`、`rate_water_per_10k_m2`（水单耗分子=一次网补水+换热站补水+热网补水）。
  - `groups` 重算策略：量/金额类按 SUM 聚合；比率/单耗类按“组内分子累计/组内常量累计”重算（电单耗分子×10000），并不汇总 `amount_heat_lose`（保留 GongRe 自身）。

## 新增能力（2025-10-23）

- 新增接口 `GET /api/v1/projects/{project_id}/pages`，用于按项目返回页面与所属模板文件映射。
- 所有 `/data_entry/sheets` 相关接口新增可选查询参数 `config`，允许前端显式指定模板 JSON 文件；默认仍回落至基础指标表。
- 模板枚举逻辑会自动读取 `backend_data/项目列表.json` 中声明的所有模板文件，无需手工维护候选列表。

## 结构快照更新（2025-10-28）

- 已在 `backend/sql/create_view.sql` 中完善二级物化视图并发刷新支持：
  - `calc_sum_basic_data` 增加唯一索引 `(company, item, scope)` → 允许 `REFRESH MATERIALIZED VIEW CONCURRENTLY`。
  - `calc_sum_gongre_branches_detail_data` 增加唯一索引 `(center, item, scope)` → 允许 `REFRESH MATERIALIZED VIEW CONCURRENTLY`。
  - 两处均以中文注释标明用途与行粒度假设，避免误删。
  - 新增调试视图 `calc_sum_basic_trace`，用于排查二级视图计算过程（显示数量、单价、乘积与缺失标记）。

## 运行时计算（替代二级物化视图，可选）

- 新增服务模块：`backend/services/calc_fill.py`
  - 函数：`fill_company_calc(payload: Dict[str, Any], db: Optional[Session]=None) -> Dict[str, Any]`
  - 入参：`{ company | company_cn, scope, period? }`，`scope` 支持 `value_biz_date/value_peer_date/sum_7d_*/sum_month_*/sum_ytd_*`。
  - 行为：直接聚合 `sum_basic_data` 指定口径列 + 读取 `constant_data`（带键名/期别规范化），在内存计算并返回一个“填满的对象”，字段与原二级物化视图一致。
  - 单位换算与公式同 `calc_sum_basic_data`：售电收入为万元（万kWh×元/kWh），售热收入除以 10000。
  - 适用场景：放弃/停用二级物化视图时，后端可用该函数按需计算，避免迁移成本。

- 新增表达式求值模块：`backend/services/expression_eval.py`（本次新增）
  - 函数：`fill_sheet_from_dict(sheet_obj: Dict[str, Any], db=None, trace: bool=False) -> Dict[str, Any]`
  - 输入：与 `configs/字典样例.json` 单表对象相同结构（含“单位标识/单位名/列名/数据/项目字典”）；
  - 行为：
    - 解析并执行单元格表达式与函数：`value_biz_date()/value_peer_date()/sum_month_*/sum_ytd_*`、`date|month|ytd_diff_rate()`；
    - 支持 `c.售电单价/售热单价/...` 的常量引用（来源 `constant_data`，自动 period 规范化）；
    - 支持同列行间引用（如“直接收入-煤成本-...”优先使用同列已算值）；
    - 单位换算与 `calc_fill.py` 保持一致：除 `售电单价` 外，数量×单价默认 `/10000` → 万元；
  - 输出：返回“数据已填满”的同结构对象；`trace=True` 时附带 `_trace.cells[]` 展示每个单元格的求值明细（便于排障）。

该目录存放 Phoenix 项目的后端代码，采用「FastAPI + 版本化路由」的结构：

- `main.py`：FastAPI 应用入口，挂载 `/api/v1` 前缀并提供 `/healthz`。 
- `api/v1/routes.py`：顶层路由调度，将不同项目的路由注册到 `/api/v1/projects/*`。 
- `api/v1/daily_report_25_26.py`：`daily_report_25_26` 项目的业务路由，实现 `ping`、`sheets`、`template/submit/query` 等接口。 
- `models/`、`schemas/`、`services/`：预留 ORM、Pydantic、领域服务层。 

## 运行方式

Docker 开发环境：

```bash
docker compose up -d --build
```

本地直接运行：

```bash
python -m pip install fastapi "uvicorn[standard]"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

常用访问：

- 健康检查：`http://127.0.0.1:8000/healthz`
- 系统心跳：`http://127.0.0.1:8000/api/v1/ping`
- 项目心跳：`http://127.0.0.1:8000/api/v1/daily_report_25_26/ping`

## 目录快照（自动维护）

更新时间：2025-10-22

- 目录
  - `Dockerfile`
  - `README.md`
  - `__init__.py`
  - `config.py`
  - `main.py`
  - `api/`
    - `__init__.py`
    - `v1/`
      - `__init__.py`
      - `routes.py`（统一前缀 `/api/v1`）
    - `daily_report_25_26.py`（项目路由与模板/填报/查询逻辑）
      - 标准表提交流程：`_flatten_records` 从“列头日期文本”提取每列 `date`；前端应确保列头根据所选 `biz_date` 动态替换。
      - 煤炭库存表（`Coal_inventory_Sheet`）特殊处理：解析顶层 `biz_date` 并持久化到 `coal_inventory_data`。
      - 镜像查询：`Coal_inventory_Sheet` 的交叉表结果会按模板中 `(单位, 煤种)` 的顺序回填，数据库中额外的组合会附加在模板行之后，确保刷新页面时行顺序保持稳定。
    - 查询接口设计（提案，待实现）：
      - 单表查询：`POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`
        - 内部按模板类型自适应返回：
          - standard：`{ template_type:'standard', columns:[...], rows:[...] }`
          - crosstab（煤炭库存）：`{ template_type:'crosstab', columns:[...], rows:[...] }`
          - constants：同 standard，按 columns+rows 回填对应期别列。
      - 项目级聚合查询：`POST /api/v1/projects/{project_key}/query`
        - 入参：`sheet_keys[]`、`scope`（data_entry/display/constants）、`biz_date|date_range`、`mode`（records/matrix）。
        - 出参：`{ results: { [sheet_key]: ... }, meta: {...} }`，适用于数据展示/仪表盘批量读取。
  - `db/`
    - `__init__.py`
    - `database_daily_report_25_26.py`
- `models/`
    - `__init__.py`
- `schemas/`
    - `__init__.py`
- `services/`
    - `__init__.py`
- `sql/`
    - `create_tables.sql`
    - SQL 不再包含 `gongre_branches_detail_data`；分中心数据已统一落库 `daily_basic_data`（以 sheet_name='GongRe_branches_detail_Sheet' 区分）。
    - `create_view.sql`（集中维护物化视图/分析视图定义；包含：
      - 一级视图：`sum_basic_data`、`sum_gongre_branches_detail_data`（来源基于 `daily_basic_data` 并按 `sheet_name='GongRe_branches_detail_Sheet'` 过滤，视图对外仍以 `center/center_cn` 别名输出）。
      - 二级视图：`calc_sum_basic_data`、`calc_sum_gongre_branches_detail_data`；已添加唯一索引以支持并发刷新）。
      - 排障视图：`calc_sum_basic_trace`（仅用于查看中间输入与乘积，非物化）。

## 常量数据写库（2025-11-02 更新）

- 目标：移除 center/center_cn 维度依赖，常量数据幂等键调整为 `(company, item, period)`（按公司-指标-期次唯一）。
- 生效范围：所有 `*_constant_Sheet` 的提交接口。
- 关键模块/流程：
  - 解析：`_parse_constant_records(payload)`
    - 读取 `columns/rows` 与 `item_dict/center_dict`；如模板含“中心”列，仅用其解析 `company/company_cn`，不再持久化 `center/center_cn` 字段。
  - 写库：`_persist_constant_data(records)`
    - `ON CONFLICT (company, item, period) DO UPDATE`，更新 `company_cn/item_cn/value/unit/operation_time`；
    - 清理残留 `center/center_cn` 键，避免写入不存在的列。
- 数据库要求：`constant_data` 需具备唯一约束/索引 `(company, item, period)`；表结构不应包含 `center/center_cn` 列。
- 影响：同一公司-指标-期次的重复提交将覆盖旧值；前端提交 payload 无需包含中心字段。

## 评估：一级物化视图→普通视图（2025-10-28）

- 结论：`sum_basic_data` 与 `sum_gongre_branches_detail_data` 可改为普通视图（`CREATE OR REPLACE VIEW`）。两者仅做基于 `current_date-1` 的窗口聚合，不依赖物化视图特性。
- 行为差异：
  - 物化视图：需刷新（可并发刷新），结果是刷新时刻的“快照”；
  - 普通视图：实时计算，自动随底表变更与“昨日/同期”口径滚动。
- 性能要点：普通视图无法在视图本体建索引，但会内联到底表。建议保留/补充底表索引以支撑常见筛选与分组：
  - `CREATE INDEX IF NOT EXISTS idx_daily_basic_company_item_date ON daily_basic_data(company, item, date);`
  - `CREATE INDEX IF NOT EXISTS idx_daily_basic_branches ON daily_basic_data(sheet_name, date, company, item) WHERE sheet_name='GongRe_branches_detail_Sheet';`
- DDL 替换示例（示意）：
  - 将
    ```
    DROP MATERIALIZED VIEW IF EXISTS sum_basic_data;
    CREATE MATERIALIZED VIEW sum_basic_data AS
    <SELECT ...>;
    CREATE UNIQUE INDEX ... ON sum_basic_data(...);
    ```
    替换为
    ```
    CREATE OR REPLACE VIEW sum_basic_data AS
    <相同 SELECT ...>;
    -- 注意：普通视图不可创建索引；请改为在 daily_basic_data 上维护索引
    ```
  - `sum_gongre_branches_detail_data` 同理。
- 迁移步骤（建议）：
  1) 以 `v_*_draft` 名旁路创建普通视图并抽样对比；
  2) 业务低峰切换同名视图，删除 `REFRESH` 相关任务；
  3) 观察性能，必要时增加/调整底表索引。
- 回滚：若性能不达标，可恢复为物化视图并重新创建唯一索引（用于并发刷新）。

## 查询接口（镜像查询）
- 单表查询（已实现）：`POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`
  - standard（每日）：`{ template_type:'standard', biz_date, columns:[...], rows:[...], attatch_time, request_id, source }`
  - constants（常量）：`{ template_type:'constant', period, columns:[...], rows:[...], attatch_time, request_id, source }`（返回列头已替换为供暖期编码，如 `25-26`、`24-25`，便于前端直接展示与回填）
  - crosstab（煤炭库存）：`{ template_type:'crosstab', biz_date, columns:[...], rows:[...] }`
- 聚合查询（规划中）：`POST /api/v1/projects/{project_key}/query`
  - 入参：`sheet_keys[]`、`scope`（data_entry/display/constants）、`biz_date|date_range`、`mode`（records/matrix）。
  - 附加：`attatch_time` 为东八区时间戳（毫秒），便于前端对照调试；`request_id` 回显前端请求ID，便于去重与仅消费最新响应。
  - 附加：`source` 为调试信息，包含：
    - `handler`：处理本次查询的函数名（如 `query_sheet`）
    - `template_type`：`standard`/`constant`/`crosstab`
    - `received`：请求来源摘要 `{ path, query, payload:{ biz_date, period, company } }`
  - 出参：`{ results: { [sheet_key]: ... }, meta: {...} }`。

## 接口路线图（2025-10-19）

- `GET /api/v1/ping`：系统级心跳。
- `GET /api/v1/projects`：读取 数据目录（默认 `/app/data`）下的 `项目列表.json` 并返回项目（`project_id/project_name`）。
- `GET /api/v1/projects/{project_key}/data_entry/sheets`：读取 数据目录中的数据填报模板清单。返回字段包含：
  - `单位名`、`表名`：兼容旧有前端；
  - `unit_name`、`sheet_name`：便于英文字段访问。
- `GET /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/template`：
  - 从数据目录中的 `数据结构_基本指标表.json` 读取指定模板；
  - 支持 `sheet_key` 大小写归一化匹配，若该文件提供 “单位标识” 字段将优先返回该版本；
  - 自动追加两列日期，返回结构为 `sheet_key/sheet_name/unit_name/columns/rows`；
  - 附带模板内定义的字典字段（如“项目字典”“单位字典”等）；前端需保持字段名称与内容一致并在提交时原样回传；
  - `columns` 形如 `[项目, 计量单位, <今日（东八区）>, <去年同日>]`。
- `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/submit`：当前为调试出口，会打印原始 payload、拆解结果与扁平化列表，后续可平滑接入数据库写入；自 2025-10-22 起，空值单元格在后端统一落库为 `NULL` 以区分未填与真实零值。
  - `GongRe_branches_detail_Sheet`：专用分支解析中心/指标，现已统一写入 `daily_basic_data`（company=中心英文名，company_cn=中心中文名，sheet_name='GongRe_branches_detail_Sheet'），调试记录输出至 `configs/111.md`。
  - `Coal_inventory_Sheet`：使用 `_parse_coal_inventory_records` 写入 `coal_inventory_data`，调试记录追加在 `backend_data/test.md`。
- `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`：占位。

## 模板处理规则

1. 读取 数据目录中的 `数据结构_基本指标表.json`。
2. 查找到的模板字段会进行以下标准化：
   - 提取单位名、表名（支持多种键名）；
   - `columns` 保持模板内的占位符（如“(本期日)”“(同期日)”“(本期月)”），具体日期由前端渲染阶段替换；
   - `rows` 兼容任意长度的数组，逐行按列表返回。
   - 模板中出现的 `*_dict` 字段（如项目/单位/中心/状态字典）会在接口中全部透传给前端，便于提交时带回。
   - 前端渲染会按照列头中首次出现“计量单位”的位置，将此前列自动标记为只读，后端无需额外维护该规则。
3. 当模板缺少 `列名` 或 `数据` 字段时，接口返回 422 以提示数据管理员处理。

## CORS 设置

- 默认允许 `http://localhost:5173`、`http://127.0.0.1:5173`。
- 通过环境变量 `PHOENIX_CORS_ORIGINS`（逗号分隔）扩展来源，例如：

```bash
PHOENIX_CORS_ORIGINS=http://localhost:5173,http://my-host
```

- Docker Compose 场景下，`backend` 服务会自动挂载 `./backend_data` 至容器 `/app/data`，保持模板与日志可追溯；程序内部统一通过 `DATA_DIRECTORY`（默认 `/app/data`）访问。

## 数据库初始化脚本

- 新增 `backend/sql/create_tables.sql`，包含 `Daily_basic_data`、`Constant_data`、`Temperature_data`、`Coal_inventory_data` 四张业务表的建表语句，可重复执行（使用 `CREATE TABLE IF NOT EXISTS` / 索引自动去重）。
- docker-compose 已将宿主机 `backend/sql` 目录挂载至数据库容器 `/app/sql`，可通过以下命令在 `phoenix` 数据库中执行脚本（数据库容器需处于运行状态）：

```bash
docker compose exec db psql -U postgres -d phoenix -f /app/sql/create_tables.sql
```

- PostgreSQL 数据卷已绑定宿主机目录 `D:/编程项目/phoenix/db_data`，请确保目录存在并拥有写权限后再启动容器。
# 示例数据脚本更新（2025-10-28）

- 位置：`backend/scripts/generate_daily_basic_sample.py`
- 变更：
  - 模板来源切换为 `configs/数据结构_基本指标表.json`（不再读取 `backend_data`）。
  - 新增对 `GongRe_branches_detail_sheet` 的交叉表扁平化：按列头中心拆分为 `company/company_cn` 后统一写入 `daily_basic_data`。
  - 文本型单元（单位为 `-` 或项目为“主设备启停情况/突发情况说明”）写入 `note`，`value` 置 `NULL`。
  - 插入目标表名修正为小写 `daily_basic_data`，与建表脚本一致。
  - 日期范围固定生成 2025-10-20 ～ 2025-10-27（含首尾）的样例数据。
- 输出：
  - `backend/sql/sample_daily_basic_data.csv`
  - `backend/sql/sample_daily_basic_data.sql`
- 导入（容器内示例）：
  ```bash
  docker compose exec db psql -U postgres -d phoenix -f /app/sql/sample_daily_basic_data.sql
  ```
#
# 变更记录（2025-10-23）

- 前端修复：交叉表（`Coal_inventory_Sheet`）默认日期首次进入页面不显示数据的问题，属前端初始化顺序导致的镜像查询结果被覆盖；本次无后端接口与数据结构改动。
## 变更：镜像查询返回模板结构（2025-10-25）

- 动机：`cells` 形式在标准/常量表上增加了前后端复杂度；现已改为完全复用模板渲染路径（rows-only），降低分支逻辑与心智负担。
- 新行为：
  - `/api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query` 现返回与 `/template` 一致的结构：`columns` + `rows`（另附 `sheet_name`、`unit_id`、`unit_name` 及各类 `*_dict`）。
  - 已移除 `cells` 字段，响应统一为 `columns` + `rows` 结构。
- 分表说明：
  - standard/每日类：默认将数值回填到第一个数据列（索引 2）；若模板存在备注列则同步回填文本。
  - constant/常量类：按模板期别列定位列索引并回填。
  - coal_inventory/煤炭库存：保持宽表 `columns`+`rows` 行为，无需调整。
- 迁移指引：前端已改为消费 `columns`+`rows`；后端已移除 `cells`。

## 变更记录（2025-10-25）

- 本轮仅在前端添加全链路调试日志，后端接口与数据模型无改动。
- 排查目标：确认前端在 rows-only 模式下收到正确的 `/template` 与 `/query` 数据并正确渲染。

### 运维提示：Docker 启动失败（数据库 unhealthy）

- 现象：`phoenix_db` 报 `invalid magic number ...`、`could not locate a valid checkpoint record`，健康检查失败。
- 原因：数据库数据目录（绑定 `./db_data`）WAL/检查点损坏。
- 处理优先级：先尝试 `pg_resetwal -f "$PGDATA"` 修复 WAL；不行再备份并清空 `./db_data` 重新初始化。
## 前端调试输出合规说明（2025-10-25）

- 前端已清理所有调试输出（`console.*` 与 `alert(...)`）。
- 后端接口契约不变：`/template`、`/submit`、`/query` 返回 rows-only；附带 `request_id`、`attatch_time`（东八区毫秒）、`source` 元信息。
### 2025-10-27 PostgreSQL 视图规划说明（AI 辅助）
- 现有核心业务表：`daily_basic_data`、`constant_data`、`temperature_data`、`coal_inventory_data`。
- 建议在 `backend/sql/create_views.sql` 中集中维护视图定义，覆盖日常汇总、常量维度对照以及煤炭库存的分支口径。
- 后续生成视图后，可通过 Alembic/初始化脚本执行 `CREATE OR REPLACE VIEW`，供查询接口直接消费。
### 2025-10-31 煤炭库存汇总视图（新增）
- 新增 `sum_coal_inventory_data`，仅抓取 `coal_inventory_data` 最新日期的记录；首先按 `company + storage_type` 汇总 `value` 并保留 `unit`/中文名称。
- 为每个公司追加 `storage_type='all_sites'`（中文名“全部地点”）的合计行，并额外写出 `company='ZhuChengQu_sum'`、`company='Group_sum'` 等聚合键，便于与模板中的 `scid.*` 表达式一致。
- 运行时求值在加载常量别名时识别 `sum_coal_inventory_data`，按公司注入 `*_sum` 聚合值（所有时间帧返回同一数值），数据展示页“库存煤量（含港口、在途）”因此可直接取到最新库存。
- CTE 结构保证空表返回空集，不会生成包含 `NULL` 的汇总；如需回滚只需移除相应 SQL 段落并重新执行脚本。
### 2025-10-27 运行时表达式求值服务（计划）
- 目标：以 `sum_basic_data` / `sum_gongre_branches_detail_data` 与现有基础表为数据源，按“字典样例.json”的表达式规则运行时计算审批表/展示表单元格，避免扩张二级视图。
- 建议位置：`backend/app/services/runtime_expression.py`
- 拟定函数（待确认）：
  - `render_spec(spec: dict, project_key: str, primary_key: dict, *, trace: bool=False) -> dict`
  - 功能：预取主表与常量表，构建指标缓存与常量缓存；按列口径（本期日/同期日/月/供暖期）求值，支持 `value_*()`、`sum_*()`、`*_diff_rate()` 以及项目名与 `c.<常量>` 引用。
- 安全与一致性：
  - 表达式使用受限求值器（白名单运算与函数），禁止任意 Python 代码执行；
  - 差异率定义为 `(biz-peer)/NULLIF(abs(peer),0)`，除零返回 `None`。
- 后续：待产品确认常量口径与差异口径后实现，并补充单元测试与 `_trace` 调试输出。
### 2025-10-27 运行时表达式求值服务（首版已实现）
- 位置：`backend/services/runtime_expression.py`
- 核心能力：
  - 列名→帧映射（本期日/同期日/本期月/同期月/本供暖期/同供暖期）
  - 物化视图/动态日期两条路径：
    - `context.biz_date == "regular"`（默认）：从 `sum_basic_data` 读取缓存值；
    - 指定日期（如 `"2025-10-27"`）：在 `daily_basic_data` 上参数化聚合，口径与视图一致；
  - 常量 period 映射：`25-26`（biz系）/`24-25`（peer系），来自常量表 `period`
  - 多常量别名预留：表达式 `a.常量名` → `CA("a","常量名")`，别名到表名在 `spec['查询数据源']['缩写']` 中声明；保留 `C("常量名")` 等价于 `CA("c", ...)`
  - 受限表达式求值：仅允许 `+ - * / ()` 和 `I("项目名")/C("常量名")/CA("别名","常量名")/value_*()/sum_*()`；不执行任意代码
  - 差异列与“全厂热效率”按百分比字符串返回，保留两位小数；除零显示 `"-"`
- 调试路由：
  - `POST /api/v1/projects/daily_report_25_26/runtime/spec/eval`
  - 请求体：
    ```json
    {
      "sheet_key": "BeiHai_co_generation_approval_Sheet",
      "project_key": "daily_report_25_26",
      "primary_key": {"company":"BeiHai"},
      "config": "configs/字典样例.json",
      "biz_date": "regular",
      "trace": false
    }
    ```
  - 返回 rows-only：`columns` + `rows`，`trace=true` 时附带 `debug._trace`
- 使用示例：
```python
from backend.services.runtime_expression import render_spec
import json

spec = json.load(open('configs/字典样例.json','r',encoding='utf-8'))['BeiHai_co_generation_approval_Sheet']
out = render_spec(
    spec=spec,
    project_key='daily_report_25_26',
    primary_key={'company':'BeiHai'},
    trace=True,
    context={'biz_date':'regular'}  # 或 {'biz_date':'2025-10-27'}
)
# out['数据'] 可直接用于 rows-only 渲染；out['_trace'] 可用于抽查验证
```

### 2025-10-30 运行时表达式参数解析修复
- 触发场景：`configs/10.30trace.md` 中 “省市平台净投诉量” 相关单元格报 `unmatched ')'`，`safe_expr` 输出形如 `value_biz_date("I("当日撤件后净投诉量""))`。
- 修复内容：`Evaluator._preprocess` 重新构建帧函数参数处理流程，允许 `I(...)` 包含括号一次匹配，并在合并后统一拆分 `value_*("指标") + value_*("指标")`。
- 同步扩展常量读取：识别 `c.<company>.<常量>` 写法并跨公司取值，例如 `c.GongRe.挂网面积`。
- 调试建议：若类似问题重现，可调用 `_preprocess(expr)` 或启用 `trace=True`，核对 `_trace.cells[].safe_expr` 是否为 `value_*(\"指标\")` 形态。

### 2025-10-30 展示表二交叉表支持
- 新增 `列名1/列名2` 两行表头解析，输出 `column_headers`+`column_groups` 元数据供前端排版。
- 列级 company 映射：根据头部 company 文本选择 metrics/constant 缓存，支持 `date_diff_rate()` 按公司计算。
- `render_spec` 同步透传 `column_groups`，API `/runtime/spec/eval` 返回结构与 rows-only 保持兼容。

## 会话小结（2025-11-06 HTTPS 切换）
- 变更：
  - `ww.ps1:1` 新增 `BUILD_HTTP_ONLY` 开关，默认仅构建/推送 HTTPS 版前端镜像（`WEB_IMAGE`），HTTP-only 版本改为按需构建。
  - `ww-http-only.yml:1` 从纯 HTTP 升级为 HTTPS（`80/443` 端口、证书卷、`certbot` 自动续期），`web` 服务改为 `WEB_IMAGE`。
- 后端参与点：Nginx 在 443 端口反代 `/api/` 到 `backend:8000`，无需改动 FastAPI 入口与路由；数据库与数据卷保持不变。
- 回滚：将 compose 的 `web` 服务切回 `WEB_HTTP_IMAGE` 并设置 `BUILD_HTTP_ONLY=1` 重新构建，即可回到 HTTP-only。

### 域名/证书具体化（2025-11-06）
- 域名：platform.smartview.top；Nginx `server_name` 已匹配。
- 证书：容器内读取 `/etc/letsencrypt/live/platform.smartview.top/*`，由 compose 将宿主机目录 `/home/ww870411/25-26/certbot/letsencrypt` 绑定到该路径；ACME webroot 宿主机目录 `/home/ww870411/25-26/certbot/www` 绑定到 `/var/www/certbot`。
- 影响：后端无需改动；Nginx 以 `/api/` 代理 FastAPI，TLS 交由 web 容器处理。

### 会话小结（2025-11-06 ww.ps1 精简）
- 构建/发布：脚本现仅构建并推送两张镜像：`phoenix-backend:<ts>`、`phoenix-web:<ts>`。
- 参数：`VITE_API_BASE` 仅在配置时传入；`NO_CACHE=1` 可禁用缓存；均非必填。
- 禁止 latest：脚本不再生成/推送 `:latest`。

### 构建镜像源调整（2025-11-06）
- 基础镜像改为 DaoCloud 镜像源，以规避 `auth.docker.io` EOF：
  - `docker.m.daocloud.io/library/python:3.12-slim`
- 不影响应用逻辑；如需回退到官方 Hub，只需把 Dockerfile 的 FROM 改回官方镜像名即可。

## 会话小结（2025-11-19 前端折叠表 fallback 移除）

- 本次仅涉及前端展示层调整：移除了 `DashBoard.vue` 折叠表的兜底逻辑，后端 `/dashboard` 接口保持不变；请继续确保返回中包含 `0.5卡片详细信数据表（折叠）` 节点以供前端渲染。
- 若 0.5 段落缺失，前端将不再回退到本地推导数据，以避免口径不一致；如需恢复原行为，仅需回滚前端对应代码。

## 会话小结（2025-12-17 供暖水单耗口径调整）

- 更新 `backend/sql/analysis.sql`：公司级日/累计视图的 `rate_water_per_10k_m2` 去除分子乘以 10000 的系数，现公式为（一次网补水量+站内补水量+一次网耗水量）/供暖收费面积（万㎡）。
- 影响：供暖水单耗数值与集团/主城区汇总口径一致，不再放大 10000 倍；如需回滚，恢复乘 10000 的写法并重新部署视图。

## 会话小结（2025-12-18 数据分析环比提示）

- 前端 `DataAnalysisView.vue` 增加区间环比比较（同长度上一周期、整月取上月，最早不早于 2025-11-01），后端接口保持不变；如需支持更早日期，可在后端放宽最小日期并同步更新前端逻辑。

## 会话小结（2025-12-02 北海分表分析视图）
- 新增 `backend/sql/analysis_beihai_sub.sql` 定义视图 `analysis_beihai_sub_daily`、`analysis_beihai_sub_sum`，仅对 `company='BeiHai'` 且 `sheet_name` ∈ {BeiHai_co_generation_Sheet, BeiHai_water_boiler_Sheet} 聚合。
- 输出 9 个指标：内售热收入、煤成本、外购电成本、购水成本、可计量辅材成本、直接收入、边际利润、可比煤价边际利润、全厂热效率；日视图按 `phoenix.biz_date`，累计视图按 `phoenix.sum_start_date/sum_end_date`，暖收入按天数缩放。
- 使用方法：`psql -f backend/sql/analysis_beihai_sub.sql` 刷新后，可直接 `SELECT * FROM analysis_beihai_sub_daily WHERE item='eco_direct_income';` 或设置区间参数查询累计视图。

### 2025-12-02 北海分表分析口径切换（前端配合说明）
- 前端 `UnitAnalysisLite.vue` 增加北海公司口径切换（公司级 + 2 个分表），后端可直接复用现有分析接口/视图（含 `analysis_beihai_sub_*`）。无需额外接口调整，保持指标字段一致。
- 前端口径选择改为下拉，北海默认公司口径，可切换两个分表（口径一致、指标同源）。- 北海公司口径文案改为“北海汇总”。- 北海分表口径文案：热电分表改为“北海热电联产”，水锅炉分表改为“北海水炉”。- 北海分表口径指标加载改为用公司口径获取 schema，避免分表缺失指标；查询仍用所选分表 unit_key。- 前端对北海分表分析统一以公司 unit_key=BeiHai 调用接口，附带 scope_key（分表）供后端区分，避免未知单位错误。- 前端分析请求：schema_unit_key 仍用公司（BeiHai）加载指标；unit_key 随用户口径（含分表）传递；scope_key 携带分表，便于后端路由至 `analysis_beihai_sub_*`。- 分表查询参数：unit_key 固定 BeiHai（防未知单位），scope_key 为所选分表，后端可据 scope_key 路由至 analysis_beihai_sub_* 视图。- data_analysis 路由支持北海分表：scope_key 为北海分表时切换视图至 analysis_beihai_sub_daily/analysis_beihai_sub_sum，并按 sheet_name 过滤。
# 会话小结（2025-12-02 数据分析接口 scope_key 修复）

- 修正 `backend/api/v1/daily_report_25_26.py` 中 `DataAnalysisQueryPayload` 模型，补充缺失的 `scope_key` 与 `schema_unit_key` 字段。






## 会话小结（2025-12-27 AI 报告前端轮询修复）

- 前端 `DataAnalysisView.vue` 修复了轮询触发逻辑，后端无改动。
