# 项目推进记录（progress）

### 2025-10-28 二级物化视图并发刷新修复（AI辅助）
- 范围：`backend/sql/create_view.sql`
- 现象：执行 `REFRESH MATERIALIZED VIEW CONCURRENTLY calc_sum_gongre_branches_detail_data` 报错：`ERROR: cannot refresh materialized view ... concurrently`，提示需创建“无 WHERE 子句”的唯一索引。
- 原因：`calc_sum_gongre_branches_detail_data` 与 `calc_sum_basic_data` 仅存在普通索引，缺少并发刷新所需的唯一索引。
- 变更：
  1) 将二级物化视图尾部索引改为唯一索引：
     - `calc_sum_basic_data` → `CREATE UNIQUE INDEX IF NOT EXISTS ux_calc_sum_basic_company_item_scope ON calc_sum_basic_data(company, item, scope);`
     - `calc_sum_gongre_branches_detail_data` → `CREATE UNIQUE INDEX IF NOT EXISTS ux_calc_sum_gongre_center_item_scope ON calc_sum_gongre_branches_detail_data(center, item, scope);`
  2) 在 SQL 中补充中文注释，明确唯一索引用于 CONCURRENTLY 刷新。
- 验证建议：执行脚本后在 psql 中 `\\d+ calc_sum_*` 查看索引；随后执行 `REFRESH MATERIALIZED VIEW CONCURRENTLY` 两张二级视图，应不再出现 55000 错误。
- 回滚思路：如无需并发刷新，可改回普通索引或删除唯一索引创建语句。
- 留痕：Serena 记忆条目 `matview_concurrent_refresh_fix_2025-10-28` 已记录变更摘要与验证指引。

### 2025-10-28 calc_sum_basic period 与键名对齐修复（AI辅助）
- 范围：`backend/sql/create_view.sql`
- 现象：`sum_basic_data` 中某公司（如“北海热电厂”）`amount_power_sales` 的 `sum_7d_biz` 非零，`constant_data` 中 `price_power_sales` 也非零，但 `calc_sum_basic_data` 的计算项为 0。
- 初步原因：
  1) `period_map` 使用了 `'25-26period'/'24-25period'` 等值，与 `constant_data.period` 实际存储（`'25-26'/'24-25'`）不一致，导致常量 LEFT JOIN 未命中；
  2) 组织键名可能存在“英文公司键名 vs 中文公司名”的差异，常量表 `key1` 与基础数据 `b.company` 未对齐。
- 变更：
  1) 将 `period_map` 的 period 值改为 `'25-26'/'24-25'`；
  2) 移除无意义的 `JOIN v_scope_period sp ON TRUE`；
  3) 常量连接条件放宽为 `(v.key1 = b.company OR v.key1 = b.company_cn) AND v.period = sp2.period`，兼容英文/中文键名。
- 验证建议：刷新视图后，查询 `calc_sum_basic_data` 中 `company='BeiHai' 或 company_cn='北海热电厂'` 且 `scope='sum_7d_biz'` 的 `eco_power_supply_income` 应大于 0；同时在 `v_constants_center_first` 验证 `key1/period/value` 命中情况。
- 回滚思路：如不需兼容中文名，可将 OR 条件收紧回仅 `b.company`；period 取值应保持与 `constant_data` 一致。

### 2025-10-28 售电收入单位换算修复（AI辅助）
- 范围：`backend/sql/create_view.sql`
- 现象：`calc_sum_basic_data` 中 BeiHai/北海热电厂 在 `scope='sum_7d_biz'` 下 `eco_power_supply_income` 为 0，而 `v_sum_basic_long` 与 `v_constants_center_first` 显示均非零。
- 原因：售电数量单位为“万kWh”，单价为“元/kWh”，相乘结果即为“万元”；原公式额外 `/10000` 导致值过小被四舍五入为 0。
- 变更：
  1) `eco_power_supply_income` 去除 `/10000`；
  2) `eco_heat_supply_income` 保持 `/10000`（GJ×元/GJ→元后换算为万元）；
  3) `eco_direct_income` 改为“售电收入（万元）+ 售热收入（万元）”，不再统一 `/10000`。
- 验证建议：刷新视图后查询 BeiHai/北海热电厂 在 `scope='sum_7d_biz'` 下的两项，值应大于 0，并与手工计算一致。
- 回滚思路：如后续确认 `amount_power_sales` 实际单位非“万kWh”，可调整换算或引入按单位动态换算逻辑。

### 2025-10-28 调试视图：calc_sum_basic_trace（AI辅助）
- 范围：`backend/sql/create_view.sql`、`backend/README.md`
- 目的：在 DBeaver 直接查看二级物化视图的中间输入与关键乘除过程，快速定位“值为 0”的原因（特别是价格未命中、单位换算）。
- 新增：`CREATE OR REPLACE VIEW calc_sum_basic_trace AS ...`
  - 暴露字段：company/company_cn/scope/period、amount_power_sales、price_power_sales、power_income_calc、amount_heat_supply、price_heat_sales、heat_income_calc、direct_income_calc、is_price_power_null、is_price_heat_null。
  - 用法示例：`SELECT * FROM calc_sum_basic_trace WHERE company='BeiHai' AND scope='sum_7d_biz';`
- 验证：刷新后查询上述视图，确认乘积列与最终 `calc_sum_basic_data` 中的 `eco_*_income` 对得上；当价格未命中时，对应 `is_price_*_null` 为 true。
- 回滚：如无需长期保留，可 `DROP VIEW calc_sum_basic_trace;`，不影响生产视图。

### 2025-10-28 常量项名规范化与容错（AI辅助）
- 范围：`backend/sql/create_view.sql`
- 背景：常量项名在库中存在大小写/空格/连字符/轻微拼写差异，造成价格匹配失败（is_price_power_null=true）。
- 新增：`v_constants_center_first_norm` 视图，对 `item` 做标准化为 `item_key`（trim→lower→空白/连字符改为下划线→合并多下划线）。
- 改动：
  1) `calc_sum_basic_data` 的常量连接与 CASE 判断改用 `item_key`；
  2) 常见差异容错：`price_alkali`/`price_clkali`、`price_ammonia_water`/`price_n_ammonia_water`、`eco_season_heating_income`/`season_heating_income`；
  3) `calc_sum_gongre_branches_detail_data` 的常量连接亦改为规范化视图。
- 验证：在 DBeaver 中查询 `calc_sum_basic_trace` 与 `calc_sum_basic_data`，确认价格项已命中、乘积大于 0；`is_price_*_null` 仅在常量确实缺失时为 true。
- 回滚：将 join/CASE 改回 `v_constants_center_first` 即可；保留规范化视图不影响其他逻辑。

### 2025-10-28 公司优先常量视图 + period 规范化（AI辅助）
- 范围：`backend/sql/create_view.sql`
- 问题：公司维度计算使用了“center 优先”的常量 key 视图，导致当常量存在 center 值时 key1=中心名，按 company 连接 miss；同时常量 period 存在 '25-26period'/空白差异。
- 变更：
  1) 新增 `v_constants_company_first_norm`：`key1=COALESCE(company,center)`，并输出规范化 `item_key` 与 `period_key`；
  2) `calc_sum_basic_data` 与 `calc_sum_basic_trace` 改为连接该视图，并以 `v.period_key = sp2.period` 匹配；
  3) `calc_sum_gongre_branches_detail_data` 仍连接 `v_constants_center_first_norm`，period 改用 `period_key`；
  4) 保留 `v_constants_center_first_norm` 作为中心维度常量源。
- 验证：trace 中 `price_power_sales` 应非空、`power_income_calc>0`；calc 二级视图相应项大于 0。
- 回滚：将公司维度 join 切回 `v_constants_center_first_norm`，period 改回原列。保留新视图不影响其他逻辑。

### 2025-10-28 运行时计算函数（放弃二级物化视图方案）（AI辅助）
- 范围：`backend/services/calc_fill.py`、`backend/README.md`
- 动机：用户决定放弃二级物化视图，改为在运行时按需计算二级指标，并返回一个“填满数据的对象”。
- 新增：`fill_company_calc(payload, db=None)` 函数：
  - 输入：`{ company|company_cn, scope, period? }`；`scope` 支持 `value_biz_date/value_peer_date/sum_7d_*/sum_month_*/sum_ytd_*`。
  - 实现：
    1) 直接从 `sum_basic_data` 聚合对应口径列（不依赖 v_sum_*_long）；
    2) 从 `constant_data` 读取常量（键名/期别规范化，别名容错）；
    3) 按原 `calc_sum_basic_data` 公式计算收入/成本/边际与单耗，返回 `{ values, missing_constants }`。
  - 单位：售电收入为万元（万kWh×元/kWh，不再 /10000）；售热收入除以 10000。
- 使用：
  - 代码中 `from backend.services.calc_fill import fill_company_calc`；
  - 传入 `{"company":"BeiHai","scope":"sum_7d_biz"}` 即可获取对象；也可传中文名 `company_cn`。
- 回滚：如需恢复二级物化视图方案，可继续使用 `calc_sum_basic_data` 并删除本服务模块。

### 2025-10-28 常量指标期别映射修正（AI辅助）
- 范围：`backend/api/v1/daily_report_25_26.py`
- 原因：常量指标查询时数据库 period 列存储为供暖期编码（如“25-26”、“24-25”），而模板/请求仍使用“(本供暖期)/(同供暖期)”占位符，导致查询匹配不到数据也无法渲染实际季节名称。
- 变更：新增 period 归一化工具 `_strip_period_wrappers`、`_normalize_constant_period_key`、`_resolve_period_index`，在提交阶段统一写入供暖期编码，在查询阶段用编码匹配并把返回列头替换为“25-26”“24-25”；若请求携带 period 参数，则并行匹配占位符与编码，保证兼容旧数据。
- 验证：`python -m py_compile backend/api/v1/daily_report_25_26.py`；需在常量页面复查“25-26”“24-25”两列均能回填。
- 备注：本次仍按用户要求停用 Serena，全程使用 Desktop Commander 操作；如需回滚，可移除新工具函数并恢复原有索引计算逻辑。

### 2025-10-28 常量指标查询 500 修复（AI辅助）
- 范围：`backend/api/v1/daily_report_25_26.py`
- 原因：常量指标页面请求 `/query` 时返回 500，后端在构造响应包时引用了未定义的 `source` 变量。
- 变更：新增常量模板分支的 `source` 描述并将 `template_type` 修正为 `constant`，确保响应元数据完整且无未定义变量。
- 验证：执行 `python -m py_compile backend/api/v1/daily_report_25_26.py` 通过语法检查；需在前端常量页面实际加载确认 200 响应。
- 备注：本次按用户指令禁用 Serena，使用 Desktop Commander 读取与写入文件；如需回滚，删除新增 `source` 字段并恢复原 `template_type` 设置即可。

### 2025-10-28 二级物化视图可行性评估（AI辅助）
- 范围：`configs/建立二级物化视图.md`、`backend/sql/create_view.sql`、`backend/sql/create_tables.sql`、`backend_data/数据结构_基本指标表.json`、`backend_data/数据结构_常量指标表.json`
- 动作：审阅现有一级物化视图结构及常量/基础数据模板，梳理用户提出的二级物化视图计算公式与依赖项，识别可直接落地的公式、需要补充的数据字段及潜在命名冲突（如 `rate_coal_per_10k_m2` 重复定义、`rate_sharing Ratio` 拼写包含空格、不同公司公式中单位换算不一致）。
- 结论：总体可实现，需在 SQL 中按时间口径对八组数值循环派生计算列，并引入按 `company`/`center` 与 `period` 匹配的常量表；部分公式需澄清（是否统一除以 10000、命名重复/错误、跨视图引用的口径对齐）。尚未修改代码与视图脚本。
- 后续建议：根据评估结论细化 SQL 实现顺序（基础指标 → 依赖型指标 → 汇总项），在落地前补充命名修正与 period 取值策略，并制定刷新/索引方案确保二级视图可并发刷新。

### 2025-10-28 标准表日历切换回填修复（AI辅助）
- 范围：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`frontend/README.md`、`configs/progress.md`
- 原因：切换业务日期后标准表未重新渲染或列头被回包复写回占位符。
- 变更：
  1. 新增 `applyStandardQueryResult`，统一处理 `/query` 回包的列头与 `rows` 回填，保持首列自动宽度逻辑。
  2. `loadTemplate` 首发查询与 `watch(bizDate)` 调用上述方法，移除无效的 `if (false)` 分支，确保日期切换即时刷新，并阻止回包列头覆盖前端按昨日/同期替换后的显示。
  3. 更新前端 README 变更记录，记录新方法与回填策略。
- 验证：未运行自动化测试；需在数据填报页面切换不同日期，确认表格数据与列头同步变化。
- 备注：Serena 当前不支持直接编辑 Vue SFC，本次按降级矩阵使用 `apply_patch`；若需回滚，可删除新函数并恢复原有查询分支。

### 2025-10-28 物化视图脚本新增（AI辅助）
- 范围：`backend/sql/create_view.sql`、`backend/README.md`、`configs/progress.md`
- 原因：规划 `sum_basic_data` 物化视图，按 company/item 维度输出六种时间口径累计指标。
- 变更：
  1. 新增 SQL 脚本：创建 `sum_basic_data` 物化视图（默认位于当前 `search_path` schema），定义 biz_date（当前日前一天）及 peer_date（一年前同日）的多窗口累计，并补充唯一索引以支持 CONCURRENTLY 刷新；同时补充 `value_biz_date`/`value_peer_date` 列，避免额外查询当日与同期值；如需独立 schema，可在执行前调整 `search_path`。

### 2025-10-28 一级物化视图→普通视图 可行性评估（AI辅助）
- 结论：可以。`sum_basic_data` 与 `sum_gongre_branches_detail_data` 不依赖物化视图专属能力（如增量刷新、物化日志等），可改为普通视图（`CREATE OR REPLACE VIEW`）。改为普通视图后将实时计算，省去刷新流程，但会失去对视图本体建索引的能力（需依赖底表索引）。
- 范围：`backend/sql/create_tables.sql`、`backend/sql/create_view.sql`
- 依据与证据：
  - 脚本显示两张“一级物化视图”定义位于 `create_view.sql`（第 14 行与第 76 行起），均为对 `daily_basic_data` 进行窗口期内聚合计算，并使用 `current_date - 1 day` 作为锚点；末尾对各物化视图创建唯一索引以便并发刷新（用于 `REFRESH ... CONCURRENTLY`）。本次评估通过 Serena 检索与读取完成。
  - 代码库未发现运行时代码调用 `REFRESH MATERIALIZED VIEW`；仅在 `configs/logs.md`、`configs/progress.md` 与脚本注释中提及运维操作，因此移除物化视图不影响后端服务运行时逻辑（参考：`backend/README.md` 中仅记录过“并发刷新支持”）。
- 行为差异评估：
  - 一致性：物化视图=“快照”，需人工/任务刷新；普通视图=“实时”，随底表变动而变。由于 SQL 内部 `biz_date = current_date - 1`，改为普通视图后“昨日/同期”口径将随查询当天自动滚动，通常符合业务预期。
  - 性能：普通视图无法在视图上建索引；但 Postgres 会内联视图，仍可利用底表索引。现有底表索引为 `(date, company, sheet_name, item, item_cn)`，能覆盖主要过滤（date between ...）与部分分组场景。若数据量继续增长，建议补充如下索引（可选）：
    1) `CREATE INDEX IF NOT EXISTS idx_daily_basic_company_item_date ON daily_basic_data(company, item, date);`
    2) 针对分中心明细：`CREATE INDEX IF NOT EXISTS idx_daily_basic_branches ON daily_basic_data(sheet_name, date, company, item) WHERE sheet_name='GongRe_branches_detail_Sheet';`
  - 维护：无需再维护“并发刷新所需的唯一索引”；运维计划中涉及 `REFRESH` 的任务可取消。
- 影响面自查：
  - 未发现后端 Python 代码直接引用“物化视图刷新”操作；二级物化视图（`calc_*`）已在先前记录中提出“可由运行时计算替代”，因此对上游是否为物化/普通视图不敏感。
  - 如存在依赖“唯一索引”的外部 SQL/报表，请改为依赖底表索引或以查询改写替代。
- 建议的迁移步骤（零停机）：
  1) 旁路创建同名普通视图草稿：先以新名 `v_sum_basic_data_draft`/`v_sum_gongre_branches_detail_data_draft` 定义 `CREATE OR REPLACE VIEW ... AS <相同 SELECT>`；
  2) 抽样比对：对若干公司/中心在多个 `scope` 下，比较 `SELECT` 结果与当前物化视图一致性（行数、求和校验）；
  3) 切换：业务低峰期执行：`DROP MATERIALIZED VIEW ...;` → `CREATE OR REPLACE VIEW 原名 AS <SELECT>`；移除“视图唯一索引”语句（普通视图不允许建索引）；
  4) 收尾：删除草稿视图；下线任何 `REFRESH MATERIALIZED VIEW` 的运维任务；保留/新增底表索引以保障性能。
- 回滚方案：若切换后查询性能不达标，可在业务低峰时恢复为物化视图定义，并重新创建唯一索引以支持并发刷新；或保留普通视图同时构建物化视图供重负载报表使用。
- 留痕：本次仅评估，无改动 SQL；后续如执行切换，将按照“变更前置说明+验证+回滚”流程提交。
  2. README 目录快照补录 `create_view.sql`，说明其用途。
  3. 留痕当前物化视图建设方案，便于后续按层次扩展其它物化视图。
- 验证：未在系统内执行；需在测试库手动运行脚本并核对聚合结果后再部署生产。
- 备注：脚本默认依赖 `daily_basic_data` 字段命名；如生产表结构有差异，请同步调整列名。

### 2025-10-28 GongRe 分中心累计视图（AI辅助）
- 范围：`backend/sql/create_view.sql`、`backend/README.md`、`configs/progress.md`
- 原因：为分中心明细表 `gongre_branches_detail_data` 提供与 `sum_basic_data` 一致的 6 种时间口径累计，便于后续聚合展示。
- 变更：
  1. 追加 `sum_gongre_branches_detail_data` 物化视图定义，按 `center/item` 维度输出当日/同期值及近7日/同期7日/当月/同期月/当季累计指标，并建立唯一索引 `(center, item, biz_date)` 支撑并发刷新。
  2. README 补充 `create_view.sql` 中现已包含 `sum_basic_data` 与 `sum_gongre_branches_detail_data` 两张物化视图说明。
- 验证：未执行；需在测试库运行 `psql -U postgres -d phoenix -f backend/sql/create_view.sql` 并校验结果。
- 备注：如需分 schema，可在执行前 `SET search_path`，或直接将视图名改写为 `<schema>.sum_gongre_branches_detail_data`。

### 2025-10-28 daily_basic_data 示例数据脚本（AI辅助）
- 范围：`backend/scripts/generate_daily_basic_sample.py`、`backend/sql/sample_daily_basic_data.csv`（脚本生成）、`backend/sql/sample_daily_basic_data.sql`（脚本生成）、`configs/progress.md`
- 原因：需要批量生成 2025-10-21～2025-10-25 及同期日的示例数据，用于测试 `daily_basic_data` 聚合与物化视图。
- 变更：
  1. 新增生成脚本 `backend/scripts/generate_daily_basic_sample.py`，解析 `backend_data/数据结构_基本指标表.json`（排除交叉表），自动为各单位/项目生成本期与同期两组样例数据，并输出 CSV 与 SQL；生成时优先使用模板中的 `项目字典`、`中心字典` 作为 `item` 英文键与中文名，保持与业务标准一致。
  2. 脚本采用可重复执行策略，如有需要可调整日期范围或倍数以生成更多样例。
- 验证：尚未运行脚本；执行 `python backend/scripts/generate_daily_basic_sample.py` 后应在 `backend/sql/` 下得到 CSV 与 SQL 文件，再通过 `psql` 或 `\copy` 导入测试库。
- 备注：生成数据仅用于联调示例，正式环境前需替换为真实业务数据。

### 2025-10-23 数据填报只读列规则调整（AI辅助）
- 范围：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`
- 原因：`GongRe_branches_detail_Sheet` 模板前三列包含“项目/中心/计量单位”，旧版写死“前两列只读”会清空“中心”“计量单位”展示。
- 变更：
  1. 新增 `resolveReadonlyLimit`，扫描列头中首次出现“计量单位”的索引，将该列及之前列统一标记为只读，未命中时回退到原策略。
  2. `setupStandardGrid`、`setupCrosstabGrid` 与 `handleSubmitStandard` 按动态只读上限构造列定义及提交数据，避免硬编码并保留模板默认值。
- 验证：未运行自动化测试；需人工在前端页面确认 `GongRe_branches_detail_Sheet` 与标准模板只读列保留原值，可编辑列可正常录入。
- 备注：Serena 暂不支持 Vue SFC 编辑，本次降级使用 `apply_patch`；回滚时删除新方法并恢复固定只读列循环即可。

### 2025-10-23 模板字典透传扩展（AI辅助）
- 范围：`backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/pages/DataEntryView.vue`
- 原因：`GongRe_branches_detail_Sheet` 等模板存在“中心字典”“状态字典”，旧版接口仅返回项目/单位字典，前端无法携带完整映射回写。
- 变更：
  1. 后端新增 `_collect_all_dicts`，为模板中出现的 `*_dict` 字段建立别名映射（项目/单位/中心/状态），统一透传给前端。
  2. 前端引入 `normalizeDictPayload`，遍历模板响应中的全部 `*_dict` 字段缓存到 `templateDicts.entries`，提交时逐项带回。
- 验证：未运行自动化测试；需人工验证模板接口包含 `center_dict`/`status_dict` 等扩展字典，前端提交 payload 中同样包含这些字段。
- 备注：Serena 不支持 Vue SFC 编辑，本次降级为 `apply_patch`；如需回滚，移除 `_collect_all_dicts` 并恢复旧的 `dictCandidates` 即可。
说明：本记录用于跟踪本次会话内的重要决策、改动与偏差，便于审计与后续回溯。

注意：受限于当前环境未接入 Serena 工具链，登记留痕暂以本文件替代；后续可将内容同步至知识库。

---

## 2025-10-17 会话内变更概览

1) 读取与确认全局规范
- 动作：读取 `AGENTS.md` 并确认项目总体设计、允许/禁改目录与接口规范。
- 备注：首次读取为确保中文编码，临时使用了 PowerShell 读取（偏差点），后续所有“修改”均遵循 `apply_patch`。

2) 仓库结构盘点
- 动作：梳理现有目录与文件，发现缺少 `backend/`、`docs/`、`docker-compose.yml` 等；`configs/` 中已有两份数据结构 JSON。
- 结论：先补齐后端骨架与前端隔离目录，逐步推进。

3) 创建后端骨架（FastAPI）
- 新增目录：`backend/app/`、`backend/app/api/`、`backend/app/api/v1/`、`backend/app/models/`、`backend/app/schemas/`、`backend/app/services/`。
- 新增文件：
  - `backend/app/main.py`：应用入口，提供 `GET /healthz` 与挂载 `/api/v1`。
  - `backend/app/api/v1/routes.py`：基础连通性 `GET /api/v1/ping`。
  - 其他 `__init__.py` 与 `backend/README.md` 说明。

4) 运行指导与问题排查
- 现象：在 `backend/` 目录执行 `uvicorn backend.app.main:app` 报 `ModuleNotFoundError: backend`。
- 结论：需在项目根目录执行，或在 `backend/` 下使用 `uvicorn app.main:app`；已给出两种可行命令与说明。

5) 前端隔离目录创建（项目名：daily_report_25_26）
- 原规范中的 `frontend/src/projects/…` 层级较深；根据最新指令改为与 `src/` 并列的项目目录。
- 新增目录与文件：
  - `frontend/src/daily_report_25_26/` 下：`pages/`（Dashboard.vue、Sheet.vue）、`components/`（ProjectHeader.vue）、`store/`、`services/`（api.js）、`constants/`（index.js）、`routes.js`、`README.md`。
- 说明：`services/api.js` 仅封装项目专属 API 调用，不修改禁改的 `frontend/src/api/`。

6) 统一 project_key 与接入路由
- 决策：后端与前端统一使用 `project_key = 'daily_report_25_26'`（按用户最新要求执行）。
- 前端改动：
  - `constants/index.js` 将 `PROJECT_KEY` 统一为 `daily_report_25_26`。
  - `router/index.js` 接入并启用该模块路由，根路径重定向至 `/daily_report_25_26`。
  - `App.vue` 渲染 `<router-view />`，以显示路由页面。

7) 后端 API 路径增加项目级前缀
- 决策：在通用前缀 `/api/v1` 之下，新增项目级前缀 `/daily_report_25_26`，形成路径隔离（示例：`GET /api/v1/daily_report_25_26/ping`）。
- 改动：
  - 新增 `backend/api/v1/daily_report_25_26.py`，提供项目级 `ping`。
  - 在 `backend/api/v1/routes.py` 中 `include_router(..., prefix="/daily_report_25_26")`。
  - 更新 `backend/README.md`，说明“通用 + 项目别名”并存策略与启动命令修正。
- 说明：此前存在 `backend/app/` 与 `backend/` 两套结构，现以 `backend/` 为主；`backend/app/` 中的同名文件不参与运行，后续统一清理时再处理。

8) 去除 `/projects/{project_key}` 路径层
- 决策：统一采用“项目别名前缀”风格：`/api/v1/daily_report_25_26/...`，不再使用 `/projects/{project_key}` 层级。
- 改动：
  - 前端 `src/daily_report_25_26/services/api.js` 更新 3 个接口路径，去除 `/projects` 段。
  - 前端 `README.md` 更新接口示例为新风格。
  - 后端 `README.md` 更新计划接口为新风格。
- 说明：请求体中仍保留 `project_key` 字段用于后续后端校验（可选），不影响路径风格；如需完全移除，可在实现接口时同步调整。

9) 实现 daily_report_25_26 最小三接口
- 改动：
  - `backend/api/v1/daily_report_25_26.py` 增加 Pydantic 模型与内存存储，实现：
    - `GET /api/v1/daily_report_25_26/sheets/{sheet_key}/template`
    - `POST /api/v1/daily_report_25_26/sheets/{sheet_key}/submit`
    - `POST /api/v1/daily_report_25_26/sheets/{sheet_key}/query`
  - `backend/README.md` 增补验证示例。
- 说明：当前实现为内存态（随进程重启丢失），仅用于前后端联调与占位；后续将替换为 SQLAlchemy + PostgreSQL 的幂等写入与查询。

10) 清理历史遗留目录 backend/app/
- 动作：删除 `backend/app/api/v1/daily_report_25_26.py`；现以 `backend/` 下结构为唯一有效路径。
- 说明：`backend/app/` 目录仅作早期骨架残留，当前运行入口与路由均在 `backend/` 顶层；后续如再出现残留文件，将继续清理，避免歧义。

---

11) 清理示例与占位代码
- 后端：
  - 精简 `backend/api/v1/daily_report_25_26.py`，移除示例模板/提交/查询及内存存储，仅保留 `GET /ping`。
  - 重写 `backend/README.md`，保留运行方式与连通性验证，去除示例接口描述。
- 前端：
  - 删除 `src/daily_report_25_26/pages/*`、`components/ProjectHeader.vue`、`services/api.js`、`store/index.js`、`routes.js`。
- 更新 `src/router/index.js`，去除对示例路由的挂载，当前不注册业务路由。
- 更新 `frontend/README.md`，改为“待接入业务路由”的说明。

12) 初始化 Git 仓库并完成首次提交
- 新增：根目录 `.gitignore`（Python/Node/Vite/编辑器与系统文件忽略）。
- 执行：`git init`、`git add -A`、`git branch -M main`、`git commit -m 'chore: initial commit'`。
- 说明：远端推送未在本地直接执行，后续按 README 指引添加 remote 并 `git push -u origin main`。

13) Docker 化与容器编排
- 新增：`backend/Dockerfile`（uvicorn 运行 FastAPI）。
- 新增：`frontend/Dockerfile`（Node 构建 + Nginx 运行，供未来生产使用）。
- 新增：`frontend/nginx.conf`（静态与代理配置）。
- 新增：`docker-compose.yml`（`db`/`backend`/`frontend`）。
- 新增：`backend_data/README.md`（说明绑定挂载目录用途）。
- 更新：`backend/README.md`、`frontend/README.md`（加入 Docker 启动说明）。

14) 调整为开发环境标准（Compose）
- backend：启用 `uvicorn --reload`，将项目根 `./` 挂载到容器 `/app`，`./backend_data` 挂载到 `/app/data`。
- frontend：改为使用 `node:20-alpine` 容器运行 Vite 开发服务器，端口 `5173`；挂载 `./frontend:/app`，并使用命名卷 `frontend_node_modules` 存放依赖。
- 访问：前端 `http://localhost:5173/`，后端 `http://localhost:8000/`，数据库端口 `5432` 保持不变。

回滚思路
- 前端目录层级：当前目录为 `frontend/src/daily_report_25_26/`，与项目代号一致。
- project_key 命名：统一为 `daily_report_25_26`，`frontend/src/daily_report_25_26/constants/index.js` 中 `PROJECT_KEY` 已为该值。
- 路径级隔离：如需撤销项目级前缀，仅在 `backend/api/v1/routes.py` 移除 `include_router`，并从前端改回通用路径。

验证清单
- 后端：
  - 启动：`uvicorn backend.main:app --reload`
  - 健康：`GET /healthz` 返回 `{ ok: true }`。
  - 通用：`GET /api/v1/ping` 返回 `{ ok: true, message: 'pong' }`。
  - 项目前缀：`GET /api/v1/daily_report_25_26/ping` 与三接口可用。
- 前端：
  - 启动：`cd frontend && npm install && npm run dev`。
  - 页面：访问 `/daily_report_25_26`、`/daily_report_25_26/sheets/demo` 可见占位页面。
## 2025-10-17 会话记录

- 背景：用户确认项目框架已就绪，约定由 AI 维护后端与前端 README 的结构说明，并在每次会话后更新 `configs/progress.md`。
- 本次变更：
  - 更新 `backend/README.md` 增加“结构快照（自动维护）”。
  - 更新 `frontend/README.md` 增加“结构快照（自动维护）”。
  - 未变更代码逻辑，仅同步文档快照。
  - 新增前端页面与路由：
    - 页面：`LoginView.vue`（登录）、`ProjectSelectView.vue`（项目选择）、`DashboardView.vue`（仪表盘/表选择+状态）、`DataEntryView.vue`（数据填报）。
    - 路由：`/login`、`/projects`、`/projects/:projectKey/sheets`、`/projects/:projectKey/sheets/:sheetKey/fill`。
    - 服务封装：`src/daily_report_25_26/services/api.js` 实现 `/template`、`/submit`、`/query` 三接口调用。
    - 常量：`src/daily_report_25_26/constants/sheets.js` 维护临时表清单（后续由后端枚举接口替换）。
- 受限与偏差（留痕）：
  - Serena 工具不可用，依据全局指南 3.9 触发条件降级到 Codex CLI：
    - 使用安全读取（仅列出目录结构）与 `apply_patch` 写入文档；未进行任何破坏性操作。
  - 影响范围：文档类文件，便于协作与可审计。
  - 回滚思路：如需回退，恢复 README 与 progress 至上一版本文本即可。
- 涉及文件：
  - `backend/README.md`
  - `frontend/README.md`
  - `configs/progress.md`
  - `frontend/src/daily_report_25_26/constants/sheets.js`
  - `frontend/src/daily_report_25_26/services/api.js`
  - `frontend/src/daily_report_25_26/pages/LoginView.vue`
  - `frontend/src/daily_report_25_26/pages/ProjectSelectView.vue`
  - `frontend/src/daily_report_25_26/pages/DashboardView.vue`
  - `frontend/src/daily_report_25_26/pages/DataEntryView.vue`
  - `frontend/src/router/index.js`

### 2025-10-17 20:02 环境事件（留痕）
- 现象：执行 `docker compose up --build` 报错：`unable to get image 'postgres:15-alpine'`，并提示 `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`
- 结论：Windows 环境下 Docker Desktop 未运行/未连接 Linux 引擎（或未安装/未启用 WSL2）。Compose 的 `version` 字段提示为过时警告，不影响本次错误本质。
- 处置建议：
  1) 启动 Docker Desktop，并确保“Use the WSL 2 based engine”已勾选；“Settings > Resources > WSL Integration”中为默认发行版开启集成；确保处于“Linux containers”模式。
  2) 验证：`docker version`、`docker info` 正常返回；随后执行 `docker pull postgres:15-alpine` 预拉镜像；再执行 `docker compose up --build`。
  3) 如 `wsl -l -v` 显示无 Linux 发行版，请安装并将默认版本设为 WSL2，重启 Docker Desktop 后重试。
- 回滚/旁路：无代码改动，无需回滚；待 Docker Desktop 可用后再执行 Compose。
- 后续事项：如需消除 `version` 过时警告，可在确认环境稳定后由我移除 `docker-compose.yml` 顶部 `version` 键；不影响功能。

### 2025-10-17 UI 美化（留痕）
- 目标：在不引入新依赖的前提下，美化登录、项目选择、仪表盘与填报页面，统一配色、按钮、卡片、表格与徽章样式；本次迭代为“蓝色商务风”。
- 动作：
  - 新增统一头部组件：`frontend/src/daily_report_25_26/components/AppHeader.vue`，带品牌与登出入口。
  - 强化主题样式：`frontend/src/daily_report_25_26/styles/theme.css` 改为商务蓝配色，新增进度条、卡片标题、按钮风格等；表格头渐变、阴影与圆角调整。
  - 页面接入：项目选择、仪表盘、数据填报三页引入 `<AppHeader />`；四页均引入主题样式。
  - 仪表盘增强：新增进度条显示填报进度（已填/总数）。
  - 新增面包屑导航：`frontend/src/daily_report_25_26/components/Breadcrumbs.vue`，并接入项目选择、仪表盘、数据填报页面；支持点击返回到对应层级。
  - 数据填报页新增显眼返回：在 `DataEntryView.vue` 顶部加入“← 返回仪表盘”按钮，便于高频返回。
- 影响范围：前端样式与模板结构（无业务逻辑变更）。
- 回滚思路：移除 `<AppHeader />` 引用及 `theme.css` 的改动，恢复旧结构即可。
### 2025-10-17 前端集成 RevoGrid（留痕）
- 目标：使用 RevoGrid 渲染数据填报表格，支持就地编辑、性能更优。
- 动作：
  - 在 `frontend/package.json` 增加依赖：`revo-grid`。
  - 在 `DataEntryView.vue` 引入 `revo-grid` 组件与样式，构造 `gridColumns`/`gridSource`，并监听 `afteredit/afterEdit` 事件同步数据。
  - 提交时从 `gridSource` 汇总单元格，按接口规范构造 `cells`。
- 影响范围：前端数据填报页的表格渲染方式；业务接口不变。
- 回滚思路：删掉 `revo-grid` 相关导入与模板，恢复为原来的 `<table>` 渲染；或移除依赖并重新安装。
- 追加修正：npm 安装失败是因包名错误（`revo-grid` 不存在）。已改为 `@revolist/revogrid` 并更新导入路径为 `@revolist/revogrid/dist/revogrid.js` 与 `@revolist/revogrid/dist/revogrid.css`。
### 2025-10-17 路由精简（留痕）
- 目标：简化数据填报页路由，去掉 `/fill` 与 `biz_date` 查询参数，采用更直观的层级。
- 变更：
  - 路由：`/projects/:projectKey/sheets/:sheetKey`（替代原 `/projects/:projectKey/sheets/:sheetKey/fill`）。
  - 导航调整：
    - Dashboard → DataEntry 链接移除查询参数。
    - DataEntry 顶部返回仪表盘不再附带 `biz_date` 查询参数。
    - 面包屑生成逻辑同步，无 `/fill`。 
- 影响范围：前端路由与页面跳转；接口与业务逻辑不变。
- 回滚思路：将上述改动恢复为带 `/fill` 的旧路径并恢复相关跳转参数。
### 2025-10-17 后端路由统一（留痕）
- 目标：按约定统一到 `/api/v1/projects/daily_report_25_26`，并先创建三大接口占位，待数据格式对齐后补齐实现。
- 动作：
  -（合并调整）占位路由现统一至 `backend/api/v1/daily_report_25_26.py`：
    - `GET /api/v1/projects/daily_report_25_26/sheets/{sheet_key}/template`
    - `POST /api/v1/projects/daily_report_25_26/sheets/{sheet_key}/submit`
    - `POST /api/v1/projects/daily_report_25_26/sheets/{sheet_key}/query`
  - 重写 `backend/api/v1/routes.py`，统一 include 到 `/projects/daily_report_25_26` 前缀。
- 影响范围：仅新增/调整后端路由占位，不含业务逻辑；前端可先仅用于连通性验证。
- 回滚思路：恢复旧版 `routes.py` 并移除新增项目路由文件即可。
### 2025-10-17 仪表盘表清单联动（留痕）
- 目标：前端仪表盘访问时向后端请求表清单，后端从挂载目录 `backend_data/数据结构_基本指标表.json` 读取并整理，返回 {sheet_key: {单位名, 表名}} 结构。
- 后端：
  - `GET /api/v1/projects/daily_report_25_26/sheets`（文件：`backend/api/v1/daily_report_25_26.py`）。
  - 仅聚焦 `backend_data/数据结构_基本指标表.json`（不再兜底其它 JSON）；字段名容错（单位名/表名）。
  - 重要决策：不再改写源 `sheet_key`，严格按文件原键名返回（不进行 `_constant_sheet` → `_sheet` 的规范化）。
  - 修复路径解析：从后端文件定位到项目根目录 `.../phoenix`（`parents[3]`），确保读取的是 `phoenix/backend_data` 而非 `phoenix/backend/backend_data`。
- 前端：
  - `services/api.js` 新增 `listSheets(projectKey)`。
  - `DashboardView.vue` 改为在 `onMounted` 调用 `listSheets` 渲染单位名/表名，并保留“去填报”跳转；增加错误提示，当文件不存在时给出友好文案。
- 影响范围：仪表盘数据来源与后端只读接口；业务写入不受影响。
- 回滚思路：前端改回使用本地常量 `constants/sheets.js`；后端保留只读接口不影响其他功能。
- 项目键统一对齐（补充）：
  - 前端项目选择页使用 `project_key = daily_report_25_26`，与后端统一前缀 `/api/v1/projects/daily_report_25_26` 保持一致，避免 404。
### 2025-10-17 前端路由与后端 API 映射（留痕）

- 会话目标：梳理前端主要页面/路由，并给出与之对应的后端 API 列表与路径前缀，确保前后端命名与接口保持一致。
- 证据来源：
  - 前端：`frontend/src/router/index.js`、`frontend/src/daily_report_25_26/services/api.js`
  - 后端：`backend/main.py`、`backend/api/v1/routes.py`、`backend/api/v1/daily_report_25_26.py`
- 关键发现：
  - API 前缀：`/api/v1`
  - 项目路径当前实现固定为：`/projects/daily_report_25_26`，与项目代号一致；前端以动态 `:projectKey` 传参已适配。

前端主要路由（name → path → 组件）：
- login → `/login` → `LoginView.vue`
- projects → `/projects` → `ProjectSelectView.vue`
- dashboard → `/projects/:projectKey/sheets` → `DashboardView.vue`
- data-entry → `/projects/:projectKey/sheets/:sheetKey` → `DataEntryView.vue`

对应后端 API（完整路径均以 `/api/v1` 为前缀）：
- 系统连通：`GET /api/v1/ping`
- 项目连通：`GET /api/v1/projects/daily_report_25_26/ping`
- 列表表清单：`GET /api/v1/projects/{project_key}/sheets`（当前实现为固定 `daily_report_25_26`）
- 获取模板：`GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template`
- 提交数据：`POST /api/v1/projects/{project_key}/sheets/{sheet_key}/submit`
- 查询数据：`POST /api/v1/projects/{project_key}/sheets/{sheet_key}/query`

请求/响应（与规范一致，后端目前为占位实现）：
- 模板响应字段：`sheet_key, sheet_name, columns, rows`
- 提交请求字段：`project_key, sheet_key, sheet_name, biz_date, cells[]`
- 查询请求字段：`project_key, sheet_key, biz_date`

偏差与回滚预案：
- 偏差：无（项目路径与代号统一为 `daily_report_25_26`）。
- 影响：仅影响 URL 可读性，不影响前后端联调（前端以路由参数传入）。
- 回滚/对齐思路：后端在路由汇总处支持参数化 `{project_key}` 或新增别名挂载；在变更前保留既有路径以平滑迁移。

本次变更：
- 未修改任何业务代码；仅更新文档（本记录、backend/frontend README 路由与结构段落）。
### 2025-10-17 Dashboard 页面访问链路复盘（留痕）

- 路由守卫：`frontend/src/router/index.js:39` 检查 `localStorage['phoenix_token']`；无 token 且目标页非 `login` 时重定向登录；有 token 且访问 `login` 时跳转项目页。
- 进入页面：命中路由 `/projects/:projectKey/sheets`（`frontend/src/router/index.js:21`），加载 `DashboardView.vue`。
- 初始化拉取：`onMounted` 调用 `listSheets(projectKey)`（`frontend/src/daily_report_25_26/pages/DashboardView.vue:71,73`）→ 发起 `GET /api/v1/projects/{projectKey}/sheets`（`frontend/src/daily_report_25_26/services/api.js:14-17`）。
- 后端响应：由 `backend/api/v1/routes.py:24` 挂载到 `daily_report_25_26.py:list_sheets_placeholder`，读取 `backend_data/数据结构_基本指标表.json` 构造 `{sheet_key: {单位名, 表名}}` 返回。
- 前端分组渲染：将对象转数组并赋值 `sheets`（`:74,79`），按“单位名” `computed` 分组（`:86`），模板 `v-for` 渲染卡片与清单（`:22,25`）。
- 进度计算：循环调用 `refreshStatus(s)`（`:58`）→ 先 `GET /template`（`:62`）计算总单元格数（列索引≥2 × 行数，`:63-64`），再 `POST /query`（`:66`）统计已填单元格（`:67-68`），用于展示状态/百分比。
 - 现状提示：`/template` 与 `/query` 为占位实现（`backend/api/v1/daily_report_25_26.py`），可能导致进度为 0% 或运行时报错（`tpl.columns` 缺失）；表清单缺失则前端显示错误占位（`:81`）。

### 2025-10-17 修复 list_sheets 读取结构（留痕）

- 问题：后端 `list_sheets` 仅按“字典结构”解析 JSON；`backend_data/数据结构_基本指标表.json` 实际为“对象数组”，导致返回 500/404，前端提示“无法获取表清单…”。
- 处理：
  - 兼容两种结构：若为 `dict`，以键为 `sheet_key`；若为 `list`，以中文“表名”作为 `sheet_key`（前端通过 `encodeURIComponent` 已兼容中文路径）。
  - 代码位置：`backend/api/v1/daily_report_25_26.py:list_sheets_placeholder`。
- 影响：前端可正常拉取表清单并渲染分组；占位接口仍不影响后续 `template/query` 的替换实现。

### 2025-10-17 API 文件合并（留痕）

- 变更背景：按用户要求，去除多余文件命名差异，将 `projects_daily_report_25_26.py` 内容整合至 `daily_report_25_26.py`，统一作为本项目 API 文件。
- 具体修改：
  - 合并占位接口（sheets/template/submit/query）到 `backend/api/v1/daily_report_25_26.py`。
  - 更新 `backend/api/v1/routes.py` 导入：改为 `from .daily_report_25_26 import router as project_router`。
  - 删除 `backend/api/v1/projects_daily_report_25_26.py`。
- 路由前缀：保持不变（`/api/v1/projects/daily_report_25_26`），前端无需改动。
- 前端/后端调试留痕（临时开关）
  - （已于同日“调试代码回收”步骤清理）后端临时调试写入：`backend/api/v1/daily_report_25_26.py` 引入 `_dbg_write`，在 `/sheets`、`/template`、`/query`、`/debug/frontend` 中写入 `phoenix/error.md` 与 `poenix/error.md`。
  - （已清理）前端上报：`frontend/src/daily_report_25_26/services/debug.js` 提供 `logDebug`；`DashboardView.vue` 中在 `onMounted`、`listSheets` 成功/失败、`refreshStatus` 阶段插桩。
  - （已删除）临时日志文件：`error.md`（根目录）及 `poenix/error.md`（容错拼写）。
  - 回收建议：问题定位完成后，可移除上述插桩与日志文件。← 已执行，详见下文。

### 2025-10-17 调试代码回收（留痕）

- 已完成占位调试的清理：
  - 删除 `backend/api/v1/daily_report_25_26.py` 中 `_dbg_write`、调试路由与日志写入，恢复精简实现。
  - 移除前端 `logDebug` 上报（删除 `services/debug.js` 和 Dashboard 内相关调用）。
  - 删除临时日志文件 `error.md`、`poenix/error.md`。
- 若后续需要排障，可通过版本控制手动恢复上述调试工具。

### 2025-10-17 Dashboard 刷新按钮调整（留痕）

- UI：移除每行表项上的 “刷新状态” 按钮，改为顶部统一按钮，避免重复渲染控件。
- 行为：新增 `refreshAll()`（`DashboardView.vue`），循环调用 `refreshStatus`；在 `onMounted` 后自动拉取并可通过顶部按钮手动刷新。
- 影响：界面更简洁，刷新逻辑一致；若后续需要逐表刷新，可按需在 `refreshStatus` 基础上扩展。

### 2025-10-17 项目路由重命名（留痕）

- 需求：将 Dashboard 访问地址从 `/projects/:projectKey/dashboard` 调整为 `/projects/:projectKey/sheets`，避免与数据填报子路由混淆。
- 代码：`frontend/src/router/index.js`、`ProjectSelectView.vue`、`DataEntryView.vue`、`components/Breadcrumbs.vue` 全部改用新路径；保持路由 name 不变（仍为 `dashboard`）。
- 文档：`frontend/README.md`、`configs/logs.md`、`configs/progress.md` 已同步更新描述。
- 影响：原路径将不再匹配，历史书签需更新；页面功能与组件装载逻辑保持不变。

### 2025-10-17 本地开发 API 基址统一（留痕）

- 目标：解决 Vite 开发服务器访问 `/api/*` 落到自身导致 404 的问题，使本地与 Docker/Nginx 行为一致。
- 变更：
  - `frontend/src/daily_report_25_26/services/api.js` 引入 `resolveApiPath`，统一拼接 `VITE_API_BASE`，默认保留相对路径。
  - `frontend/src/daily_report_25_26/services/debug.js` 复用 `resolveApiPath`，确保调试日志同源。
  - 新增 `frontend/.env.development`，默认将 `VITE_API_BASE` 指向 `http://127.0.0.1:8000`，本地 `npm run dev` 即可直连后端。
- 后续：如需切换到 Docker Compose，可在环境变量中调整 `VITE_API_BASE`，保持统一配置。问题定位结束时记得清理临时调试日志与插桩。
 - 追加修复：为跨域访问配置 CORS（`backend/main.py`），默认允许 `localhost/127.0.0.1:5173`，并支持通过环境变量 `PHOENIX_CORS_ORIGINS` 自定义域名，解决浏览器直接访问后端时的跨域报错。

### 2025-10-19 看板页面命名与路径同步（留痕）

- 背景：前端路由使用 `/projects/:projectKey/sheets`，需保持组件命名一致。
- 变更内容：
  - `frontend/src/daily_report_25_26/pages/Sheets.vue`：以新文件取代 `DashboardView.vue`，结构与逻辑沿用原实现，并恢复单位卡片 + 状态进度的卡片式布局。
  - `frontend/src/router/index.js`：懒加载路径更新为 `pages/Sheets.vue`。
  - `frontend/README.md`、`backend/README.md`：同步更新命名描述。
- 影响范围：前端页面引用路径，后端无变动。
- 回滚方案：如需恢复旧命名，重新创建 `DashboardView.vue` 并调整引用路径即可。
### 2025-10-19 模板接口落地（留痕）

- 后端：`backend/api/v1/daily_report_25_26.py` 读取 `backend_data` 模板文件，补齐当前日期与上一年度同日，并返回结构化字段 `sheet_key/sheet_name/unit_name/columns/rows`。
- 前端：`frontend/src/daily_report_25_26/pages/Sheets.vue` 精简卡片展示（去除 0/0 徽标、取消分隔线），保持单位卡片风格；`frontend/README.md` 说明模板列用法。
- 文档：`backend/README.md` 与 `frontend/README.md` 更新接口说明；`configs/progress.md` 留痕当前变更。
- 模板清单接口 `GET /api/v1/projects/{project_key}/sheets` 现同时包含中文键（`单位名`、`表名`）与英文键（`unit_name`、`sheet_name`）。

### 2025-10-20 DataEntryView 迁移至官方 Vue 组件（留痕）

- 背景：原生 `<revo-grid>` 未显式注册自定义元素，可能导致页面空白；同时缺乏官方样式入口，专家建议改用 `@revolist/vue3-datagrid`。
- 动作：
  - `frontend/src/daily_report_25_26/pages/DataEntryView.vue` 改为导入官方 `RevoGrid` 组件，移除手动事件监听，使用 `@afteredit` 钩子同步 `gridSource`；
  - 增补 `handleAfterEdit` 方法以与组件事件模型对齐；
  - `frontend/README.md` 更新路由说明与 RevoGrid 配合方式；
  - `backend/README.md` 同步更新时间，说明本次后端结构未变动。
- 影响范围：数据填报页面表格渲染流程改为由组件包装层托管，自定义元素注册与事件派发更加稳定，降低空白渲染风险；后端无代码变更。
- 回滚方案：如需恢复旧实现，可将 `DataEntryView.vue` 改回原生 `<revo-grid>` 标签并重新挂载 DOM 事件，同时撤销 README 更新。
- 涉及文件：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`frontend/README.md`、`backend/README.md`、`configs/progress.md`。

### 2025-10-20 Sheets 页面移除进度展示（留痕）

- 背景：用户要求 /sheets 页面不再展示“进度条”及 “已填 / 应填” 数字，避免产生“可以缺项”的错误暗示。
- 动作：
  - 删除 `frontend/src/daily_report_25_26/pages/Sheets.vue` 中的进度徽标、进度条模板及关联逻辑，保留简洁的表格清单。
  - 精简脚本：移除 `statusMap`、`refreshStatus/refreshAll`、模板刷新按钮及业务日期选择，头部标题调整为“表格选择”。
- 影响范围：仪表盘仅作为表格入口展示，不再发起 `/template` 与 `/query` 轮询，页面体验更直接。
- 回滚方案：若需恢复进度展示，可从版本控制中还原 `Sheets.vue` 对应段落与样式。
- 涉及文件：`frontend/src/daily_report_25_26/pages/Sheets.vue`、`configs/progress.md`。

### 2025-10-20 Catalog 数据源与填报列数调整（留痕）

- 背景：用户要求 `/sheets` 接口仅使用 `configs/数据结构_基本指标表.json` 作为单位与表格列表来源，并指出填报页多出一列（行号列）。
- 动作：
- 修改 `backend/api/v1/daily_report_25_26.py`，`list_sheets` 仅读取 `configs/数据结构_基本指标表.json`，同时 `_iter_data_files` 先行遍历该文件，保证模板与清单来源一致；
- `DataEntryView.vue` 的 `RevoGrid` 组件启用 `rowHeaders` 并隐藏版权列（`:hide-attribution="true"`），行号位于最左侧。
- 影响范围：前端仪表盘列表与填报页列数与用户期望保持一致；模板获取逻辑保持兼容 `backend_data` 作为后备。
- 回滚方案：如需恢复多文件合并行为，可撤销 `_collect_catalog` 与 `_iter_data_files` 调整；如需显示版权列，可移除 `hide-attribution` 设置。
- 涉及文件：`backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`configs/progress.md`。

### 2025-10-20 DataEntry 表格自适应宽度（留痕）

- 背景：RevoGrid 默认在内容不足时保留右侧占位区域；用户要求去除多余空白。
- 动作：在 `DataEntryView.vue` 的 `<RevoGrid />` 上启用 `stretch`（布尔值）与 `autoSizeColumn`，并为各列设置 `autoSize`/`minSize` 属性，使列宽随窗口动态适配、填满容器。
- 影响范围：填报页表格横向铺满卡片，不再出现右侧留白占位。
- 回滚方案：删除 `:stretch="'all'"` 即可恢复默认布局。
- 涉及文件：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`configs/progress.md`。

### 2025-10-21 DataEntry 首列自适应补强（留痕）

- 背景：模板与历史数据通过异步请求加载，首列列宽仅依据初始行名测量，其他单元格的长文本仍会压缩至最小宽度。
- 动作：为 `RevoGrid` 添加 `ref` 并在 `loadTemplate/loadExisting` 结束后调用封装的 `autoSizeFirstColumn()`；该函数汇总整列文本并使用 Canvas 量测宽度，随后更新列配置及调用 RevoGrid 的 `autoSizeColumn`，确保列宽覆盖所有单元格；同时在 `beforecellfocus` 阶段调用 `commitActiveEditor()`，结合 `beforecellsave`、编辑器失焦事件、`editors = { text: { saveOnBlur: true } }` 配置，以及 `:apply-on-close=\"true\"`，避免用户未按 Enter 或切换焦点时输入丢失。
- 影响范围：数据填报表格首列可完整展示任意单元格文本，其余列宽逻辑保持不变。
- 回滚方案：移除 `autoSizeFirstColumn` 调用及 `RevoGrid` 的 `ref` 定义即可恢复旧行为。
- 涉及文件：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`configs/progress.md`、`frontend/README.md`、`backend/README.md`。

### 2025-10-21 DataEntry 失焦策略调整（留痕）

- 动作：移除 `beforecellfocus`、`beforecellsave` 与编辑器失焦监听等自定义同步逻辑，仅保留 RevoGrid 原生的 `:apply-on-close="true"` 自动保存能力。
- 影响范围：表格在失焦或切换焦点时依赖内置流程提交数据，代码逻辑更精简。
- 涉及文件：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`frontend/README.md`。

### 2025-10-21 数据库卷绑定挂载（留痕）

- 动作：将 `docker-compose.yml` 中 `db` 服务数据卷改为绑定宿主机目录 `D:/编程项目/phoenix/db_data`，并额外挂载 `./backend/sql` 至 `/app/sql` 供数据库容器执行建表脚本。
- 影响范围：PostgreSQL 数据与 SQL 脚本均可在宿主机直接管理，执行 `psql -f /app/sql/create_tables.sql` 时无需额外拷贝。
- 回滚方案：恢复命名卷 `pg_data` 并移除 SQL 目录挂载即可。
- 涉及文件：`docker-compose.yml`、`backend/README.md`、`configs/progress.md`。

### 2025-10-21 项目列表接口与前端展示（留痕）

- 动作：后端新增 `GET /api/v1/projects`，读取 `backend_data/项目列表.json` 返回项目 `id/name`；前端新增 `useProjects` 共享项目缓存，项目选择/Sheets/数据填报/Breadcrumbs 均展示中文名称。
- 影响范围：前端路由与面包屑展示内容改为项目中文名，项目选择页面从静态配置改为实时接口。
- 涉及文件：`backend/api/v1/routes.py`、`backend/README.md`、`frontend/src/daily_report_25_26/services/api.js`、`frontend/src/daily_report_25_26/composables/useProjects.js`、`frontend/src/daily_report_25_26/pages/ProjectSelectView.vue`、`frontend/src/daily_report_25_26/pages/Sheets.vue`、`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`frontend/src/daily_report_25_26/components/Breadcrumbs.vue`、`configs/progress.md`。

### 2025-10-21 面包屑导航样式优化（留痕）

- 动作：调整 `Breadcrumbs` 样式，增加留白、圆角和 hover 效果，并在 Sheets 页面移除重复标题，仅保留面包屑作为导航提示。
- 影响范围：所有使用 `Breadcrumbs` 的页面导航更显眼，Sheets 页面头部更简洁。
- 涉及文件：`frontend/src/daily_report_25_26/components/Breadcrumbs.vue`、`frontend/src/daily_report_25_26/pages/Sheets.vue`、`configs/progress.md`。

### 2025-10-21 面包屑分隔符增强（留痕）

- 动作：将面包屑分隔符由单个 “›” 调整为双箭头 “»” 并增大字号，强化层级感。
- 影响范围：面包屑导航的层级感更明显。
- 涉及文件：`frontend/src/daily_report_25_26/components/Breadcrumbs.vue`、`configs/progress.md`。

### 2025-10-21 数据填报页导航调整（留痕）

- 动作：移除数据填报页“返回仪表盘”按钮，改用面包屑指引并整体对齐标题区。
- 影响范围：数据填报页面顶部结构更统一，用户通过面包屑返回上一层。
- 涉及文件：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`configs/progress.md`。

### 2025-10-21 顶部导航按钮精简（留痕）

- 动作：移除 `AppHeader` 右上角“项目”按钮，仅保留“退出”操作，避免与面包屑重复。
- 影响范围：所有页面顶部导航更简洁。
- 涉及文件：`frontend/src/daily_report_25_26/components/AppHeader.vue`、`configs/progress.md`。

### 2025-10-21 数据填报提交载荷扩展（留痕）

- 动作：前端提交时附带 `project_name`、`columns`、`rows` 等模板结构（按表格顺序填充值），后端可直接拆解表格。
- 影响范围：数据填报请求结构更完整，为后续落库提供基础。
- 涉及文件：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`configs/progress.md`。

### 2025-10-21 提交数据拆解函数（留痕）

- 动作：在 `backend/api/v1/daily_report_25_26.py` 内新增 `_normalize_submission` 并在 `/submit` 路径输出调试日志至 `backend_data/data_handle.md`。
- 影响范围：便于后续实现数据库落库前先验证拆解结果。
- 涉及文件：`backend/api/v1/daily_report_25_26.py`、`backend_data/data_handle.md`、`configs/progress.md`。
-### 2025-10-21 DataEntry 失焦策略调整（留痕）
+
- 动作：移除 `beforecellfocus`/`beforecellsave` 监听与自定义失焦同步函数，仅保留 `:apply-on-close="true"` 触发的内置自动保存机制。
- 影响范围：前端表格离开单元格时依赖 RevoGrid 原生提交流程，逻辑更精简。
- 涉及文件：`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`frontend/README.md`。

### 2025-10-21 单位标识与提交时间精简（留痕）

- 动作：模板接口返回 `unit_id`，前端在提交时附带单位标识并简单记录 `YYYY-MM-DD HH:MM:SS` 本地时间。
- 影响范围：后续持久化可关联单位英文标识，提交时间与页面展示保持一致。
- 涉及文件：`backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`frontend/src/daily_report_25_26/pages/Sheets.vue`、`configs/progress.md`。
### 2025-10-21 模板 unit_id 匹配修复（留痕）
- 动作：`_locate_sheet_payload` 支持 `sheet_key` 大小写归一化匹配，优先返回挂载卷 `backend_data/数据结构_基本指标表.json` 中带 “单位标识” 的模板。
- 影响：前端请求模板时 `unit_id` 恒不为空，填报页面可准确显示单位标识。
- 回滚：复原 `backend/api/v1/daily_report_25_26.py` 中 `_locate_sheet_payload` 的增量逻辑即可。
- 验证：调用 `GET /api/v1/projects/daily_report_25_26/sheets/BeiHai_co_generation_sheet/template`，响应 `unit_id` 为 `BeiHai`。

### 2025-10-21 项目字典透传（留痕）
- 动作：后端返回的字典字段按原有键名保留，前端缓存模板中出现的全部字典（含中文键），提交数据时逐项附加并在缺省时补齐 `item_dict`/`company_dict` 映射，确保名称与内容与模板保持一致且兼容后端现有字段。
- 影响：业务方新增的“项目字典”“单位字典”可在前后端之间保持一致，后续持久化或校验可直接复用数据。
- 回滚：撤销 `backend/api/v1/daily_report_25_26.py` 中关于 `_extract_mapping`、`get_sheet_template`、`_normalize_submission` 的改动，并移除前端对应字段。
- 验证：本地调用模板接口检查响应新增字段，填表后提交查看 `backend_data/data_handle.md` 记录中保留字典信息。
### 2025-10-21 提交数据平铺化转换（留痕）
- 动作：新增 `_flatten_records` 将提交 payload 打平成“公司/项目/日期”长表；`/submit` 调试接口同步输出平铺化结果，便于后续落库。
- 影响：`backend_data/data_handle.md` 追加“平铺化结果”段落，后端可直接复用该列表写入数据库。
- 回滚：恢复 `backend/api/v1/daily_report_25_26.py` 中 `submit_debug` 与 `_flatten_records` 的改动即可。
- 验证：前端提交后检查响应 `flattened_records` 数量，并核对日志中的平铺记录与非空单元格一致。

### 2025-10-21 Daily_basic_data 写入落地（留痕）
- 动作：在 `/submit` 调试接口中调用 `_persist_daily_basic`，将平铺后的单元格记录写入 `Daily_basic_data` 表，写入前按 `(company, sheet_name, item, date)` 去重后重新插入。
- 影响：前端提交数据会同步落库，并在日志 `backend_data/data_handle.md` 中记录写库条数及异常；接口响应新增 `inserted` 字段反馈写入数量。
- 回滚：撤销 `backend/api/v1/daily_report_25_26.py` 中 `_persist_daily_basic` 相关改动及 `backend/db/database_daily_report_25_26.py` 新增内容。
- 验证：访问 `/submit` 调试接口，响应 `inserted` > 0 且数据库 `Daily_basic_data` 出现对应记录；如有异常，接口返回 500 并附错误信息。

### 2025-10-21 数据填报路径统一（留痕）
- 动作：后端与前端的 `/sheets` 路径统一调整为 `/data_entry/sheets`，同步更新导航跳转、API 服务调用与 README 说明。
- 验证：逐项检索项目内路径引用，已清理旧路径并手动检查主要页面配置；待前后端联调确认接口请求。
- 备注：后续新增展示、审核等业务域时可复用顶层分组策略，保持信息架构清晰。

### 2025-10-22 数据填报空值落库（留痕）
- 动作：调整 `_flatten_records`，对单元格空值不再跳过，而是统一转换为字符串 \"0\" 随记录入库，保持 `_persist_daily_basic` 的删除+插入更新机制。
- 验证：代码层面确认 `None` 与空字符串均落为 \"0\"，待后续调试接口验证数据库 `value` 列写入 0。
- 备注：后续可叠加前端或业务校验规则，数据库侧保留空值提交记录以支撑审计追溯。

### 2025-10-22 数据目录常量化（留痕）
- 动作：新增 `backend/config.py` 统一暴露 `DATA_DIRECTORY`（默认 `/app/data`），`daily_report_25_26.py` 与 `routes.py` 改为引用该常量，移除对项目根 `backend_data` 的硬编码；取消模板兜底读取 `数据结构_常量指标表.json`，坚持以绑定挂载目录的基本指标表为唯一来源。
- 验证：静态检查确认 `DATA_ROOT`、`PROJECT_LIST_FILE` 均指向新常量，错误提示动态输出目录路径；待容器环境验证挂载 `/app/data` 后模板加载与项目列表读取正常。
- 备注：可通过环境变量 `DATA_DIRECTORY` 覆盖默认目录，Docker Compose 已将 `./backend_data` 绑定至 `/app/data`。

### 2025-10-22 Docker 路径收敛（留痕）
- 动作：将 `db` 服务数据卷改为 `./db_data:/app/db_data` 并设置 `PGDATA=/app/db_data`，去除硬编码绝对路径；收窄 `backend` 服务为 `./backend:/app/backend` 与 `./backend_data:/app/data`，同时显式设置 `DATA_DIRECTORY=/app/data`。
- 验证：docker-compose 配置静态检查通过；后续需在容器内确认 Postgres 能在新目录初始化、后端读取模板正常。
- 备注：开发时如需额外挂载其它目录，可在 compose 覆盖文件中扩展，主配置保持最小权限原则。

### 2025-10-22 煤炭库存调试输出（留痕）
- 动作：`/submit` 接口新增 `Coal_inventory_Sheet` 专用处理，拆解 payload 生成结构化记录，写入 `backend_data/test.md` 并同步写库至 `coal_inventory_data`（删除后插入，键为 `company+coal_type+storage_type+date`）。
- 验证：通过前端或调试脚本提交煤炭库存样例，请检查 `backend_data/test.md` 中的原始 payload 与 parsed records`，以及数据库表写入结果。
- 备注：后续在确认转换逻辑后，再接入 `coal_inventory_data` 写库功能。

### 2025-10-22 模板列扩展透传（留痕）
- 动作：多次迭代 `backend/api/v1/daily_report_25_26.py` 中 `_decorate_columns`，最终固定在模板原始列的第三、第四位写入“当日/去年同期”日期，占用原有的两个空白占位列，同时保留其余自定义列（如“解释说明”）的顺序与内容。
- 验证：手动审查返回列数组构造逻辑，确认在长度不足时补齐占位后写入日期；待前端重新请求模板后观察列顺序变化。
- 备注：后续若需调整日期策略，可在同函数中继续扩展，不必修改模板文件。

### 2025-10-22 解释说明列写入 Note（留痕）

### 2025-10-22 模板日期前移至前端（留痕）
- 范围：`backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/composables/useTemplatePlaceholders.js`、`frontend/src/daily_report_25_26/pages/DataEntryView.vue`
- 动作：后端仅透传模板占位符；前端组合式在加载模板后将 `(本期日)/(同期日)/(本期月)/(同期月)/(本供暖期)/(同供暖期)` 替换为昨日、去年同日及供暖期区间。
- 验证：页面手动刷新标准表与 `Coal_inventory_Sheet`，确认列头日期正确且提交请求携带前端计算的 `biz_date`。
- 回滚：恢复 `_decorate_columns` 的日期填充逻辑并移除新组合式调用。

### 2025-10-22 数据填报空值统一 NULL（留痕）
- 范围：`backend/api/v1/daily_report_25_26.py`
- 动作：`_flatten_records`、`_flatten_records_for_coal` 将提交中的空字符串/`None` 映射为 `None`，并保持扁平化记录；`submit` 调试链路落库时自动写入数据库 `NULL`，区分未填与真实零值。
- 验证：调试接口打印的 `flattened` 列表中空值字段显示为 `null`；后端模型 `_parse_decimal_value` 接收 `None` 并正确写入。
- 回滚：恢复空值转 `"0"` 的逻辑并告知统计团队。
- 动作：在 `_flatten_records` 中识别“解释说明”列，按行收集说明文本，并在生成“本日”记录时写入 `note` 字段；写库阶段保持 `note` 原样持久化，空值不再转换为 0。
- 验证：手动检查 `notes_by_row` 构造逻辑与 `note` 赋值条件（仅对列索引 2 的“本日”记录生效）；后续需通过前端提交覆盖场景验证数据库行的 `note` 内容。
- 备注：若后续解释说明列命名调整，可在 `note_labels` 集合中补充别名；默认回退为最后一列。


### 2025-10-23 Gongre 分中心模型补充（AI辅助）
- 范围：`backend/db/database_daily_report_25_26.py`
- 原因：新增表 `gongre_branches_detail_data` 需要对应的 SQLAlchemy ORM 类供持久化流程调用。
- 变更：定义 `GongreBranchesDetailData` 模型，覆盖中心/项目/日期/状态等字段，字段类型与 `create_tables.sql` 中的定义保持一致。
- 验证：未运行自动化测试；后续在实现专属写库逻辑时需确认 ORM 字段与实际写入数据匹配。
- 备注：如需回滚，删除新模型类即可。

### 2025-10-23 Gongre 分中心提交处理（AI辅助）
- 范围：`backend/api/v1/daily_report_25_26.py`、`configs/111.md`
- 原因：供热分中心表 `GongRe_branches_detail_Sheet` 需要独立的解析、调试记录与写库流程。
- 变更：
  1. 扩展 `submit_debug` 路由，新增 `_parse_gongre_branches_detail_records`、`_persist_gongre_branches_detail` 与 `handle_gongre_branches_detail_submission`，写入 `gongre_branches_detail_data`。
  2. 新增 `_write_gongre_branches_debug`，把前端原始 payload 与解析结果追记到 `configs/111.md`。
- 验证：未运行自动化测试；需通过前端或模拟请求确认 `configs/111.md` 生成调试记录、数据库表实际写入数据。
- 备注：如需回滚，移除新分支及相关函数并清理调试文件即可。
### 2025-10-23 页面选取与模板多源支持（AI辅助）

- 后端新增 `GET /api/v1/projects/{project_id}/pages` 接口，并扩展模板解析以识别 `项目列表.json` 中声明的多模板文件；所有模板与查询接口支援 `config` 查询参数。
- 前端加入页面选取页 `/projects/:projectKey/pages`，重新规划路由为 `/projects/:projectKey/pages/:pageKey/sheets(/:sheetKey)`，并在各 API 调用中携带 `config` 参数确保指向正确模板。
- 更新 `services/api.js`、`Sheets.vue`、`DataEntryView.vue` 等模块，实现多页面模板之间的切换及填报流程；同步刷新 README 说明。
- 适配新的项目配置为“对象结构”：顶层为项目ID → 项目信息，`pages` 为“URL → {页面名称, 数据源}”；`/projects` 与 `/projects/{id}/pages` 已按此解析。

### 2025-10-23 展示页面占位与填报页分组回归（AI辅助）

- 新增 `DisplayView.vue` 与路由 `/projects/:projectKey/pages/:pageKey/display`，在“数据展示页面”场景下展示仪表盘与三张固定展示表的占位卡片，预留后续根据“数据源”渲染只读网格/图表。
- `PageSelectView.vue` 根据 `config_file` 包含“展示用”关键字自动跳转到上面的 display 路由；其他页面仍走 `sheets` 路由。
- `Sheets.vue` 恢复“每日数据填报页面”的“按单位分组”卡片展示：按 `unit_name` 分组，组内为表格卡片，其他页面不受影响。
- 2025-10-23 修复：数据填报页面日历修改未生效问题（标准表列头日期未随 biz_date 更新）
  - 现象：前端小日历修改“本期日/同期日”后，提交到后端的数据仍使用初始日期；数据库中记录的 `date` 不随选择变化。
  - 根因：标准表提交流程在后端通过“列头日期文本”解析每列的 `date`（参见 `_flatten_records`），而前端仅在模板初次加载时对列头占位符进行了一次替换，未在 `bizDate` 变更时重算列头。
  - 方案：在前端 `DataEntryView.vue` 中新增 `baseColumns`（缓存未替换占位符的原始列头），并监听 `bizDate` 变更，基于 `baseColumns` 重新执行 `replaceDatePlaceholdersInColumns`，同步更新 `columns` 与 `gridColumns` 的 `name`，保证 UI 与提交 payload 一致。
  - 影响范围：仅前端渲染与提交；后端接口与数据结构不变。
  - 变更文件：
    - `frontend/src/daily_report_25_26/pages/DataEntryView.vue`
  - 回滚思路：删除 `baseColumns` 与 `watch(bizDate)` 补丁，并恢复初次加载时的单次替换逻辑即可。
  - Hotfix：补充 `watch` 导入，修复 `setup` 阶段未定义导致的页面白屏。
- 2025-10-23 统一查询接口设计提案
  - 背景：三类页面（每日数据填报、数据展示、常量指标）均需查询能力；希望避免为每张表/每个页面单独新增路由。
  - 设计：
    1) 保留并实现通用的“按表查询”路由：`POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`
       - handler 内部按模板类型自适应（standard/crosstab/constant），无须为每张表单独写路由。
    2) 新增“项目级聚合查询”路由：`POST /api/v1/projects/{project_key}/query`
       - 入参支持 `sheet_keys[]`、`scope`（data_entry/display/constants）、`biz_date` 或 `date_range`、`mode`（cells/records/matrix）。
       - 返回 `{ results: { [sheet_key]: { template_type, cells|rows+columns } }, meta: {...} }`，便于数据展示页/仪表盘批量回填。
  - 渐进式落地：先实现 1)（解锁 DataEntry 的单表回填），随后补 2)（供展示/常量页面批量获取）。
  - 兼容性：前端 `services/api.js::queryData` 保持不变；展示/常量页可选择采用项目级聚合查询以减少请求轮数。
  - 下一步：待确认后开发 Phase 1 后端逻辑（standard/crosstab/constant 三分支），随后补聚合路由。

- 2025-10-23 实现：镜像查询（逆 submit）单表接口
  - 路由：`POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`
  - 行为：
    - 标准/每日表：按 `biz_date` 读取 `daily_basic_data`，返回 `{ template_type:'standard', cells:[...] }`；`cells[].unit` 为计量单位，`col_index=2`（本期首列）。
    - 常量指标表：按 `period` 读取 `constant_data`，定位模板期别列索引并返回 `cells`（同 standard 回填方式）。
    - 煤炭库存表：按 `biz_date` 读取 `coal_inventory_data`，返回 `{ template_type:'crosstab', columns, rows }` 宽表矩阵。
  - 语义与约束：
    - `unit` 一律为计量单位，组织维度过滤使用 `company`/`company_id` 可选参数。
    - 日历联动：每日表使用 `biz_date`；常量表使用 `period`（如 24-25/25-26）。
  - 变更文件：`backend/api/v1/daily_report_25_26.py`
  - 回滚方案：恢复 `query_placeholder`，或仅保留 standard 分支以降级验证。

- 2025-10-23 前端联动改进：日历变更触发查询 & 备注回填
  - DataEntryView.vue：
    - 在 `watch(bizDate)` 中新增调用 `queryData(...)`，变更日期后即时回填数据与备注（cells 文本型/数值型均支持）。
    - 页面初次加载完成后执行一次镜像查询（standard/crosstab分别处理）。
  - 后端查询增强：
    - standard 分支：读取模板定位“备注”列索引，若记录存在 note 字段，追加文本型 cell（value_text）。
  - crosstab 分支：若模板含“备注”等列，按 (公司, 煤种) 行汇总首个非空备注填入备注列。

- 2025-10-23 Bugfix：煤炭库存页前端已收数据但未渲染
  - 现象：网络层已收到 rows，但页面不显示。
  - 根因：仅在初次加载时处理了 crosstab 的 rows，业务日期变更未触发 crosstab 的重新回填；且部分情况下列头未同步。
  - 修复：
    - 在 `DataEntryView.vue` 增加针对 `templateType==='crosstab'` 的 `watch(bizDate)`，变更时重新调用 `queryData` 并以 `q.rows` 重建 `gridSource`；若返回 `q.columns`，同步更新 `columns` 与 `gridColumns.name`。
    - 初次加载时的 crosstab 查询保留；必要时在 watch 中补充列头同步逻辑。
- 2025-10-23 术语澄清：镜像查询 = 逆 submit 查询
  - 结论：与前端提交写入同一数据库表，按同一键（project_key/sheet_key/biz_date[/unit]）反向读取回填的数据。
  - 标准/常量（Tall Table / DailyBasicData）：返回 cells 形式，默认回填到第一个数据列（col_index=2）。
  - 煤炭库存（CoalInventoryData）：按模板 columns + COAL_STORAGE_NAME_MAP 回填整表矩阵（rows/columns）。
  - 与聚合查询区分：镜像查询只处理单张表的“逆提交”；聚合查询跨多表编排，供展示/仪表盘使用。

- 2025-10-23 语义澄清：`unit` 表示“计量单位”，非公司/组织
  - 约定更新：
    - cells 中的 `unit` 字段仅表示“计量单位”（如 万kWh、GJ、吨）。
    - 组织维度统一使用 `company`/`company_cn`（或 `company_id`）命名，不再混用 `unit_id` 指代公司。
  - 查询接口提案修订：
    - 可选过滤参数使用 `company` 或 `company_id`，而非 `unit`。
    - 镜像查询返回中的 `unit` 依旧仅承载计量单位信息。
  - 技术债记录：后端个别函数尚有 `unit_id` 充当公司标识的历史命名（如 `_resolve_company_name`）；实现查询时不对外暴露该歧义参数，内部逐步收敛为 `company`/`company_id`。
- 2025-10-23 Bugfix：煤炭库存变体表识别与查询空白
  - 现象：`Coal_inventory_sheetYanJiuYuan_sheet` 页面查询无数据（而模板/提交已存在）。
  - 根因：后端仅对 `sheet_key == 'Coal_inventory_Sheet'` 走 crosstab 分支，未识别其他变体 key，导致以 standard 路径查询 `daily_basic_data`，自然为空。
  - 修复：新增 `_is_coal_inventory_sheet`（名称/列头双启发）并用于 `get_sheet_template`、`submit_debug`、`query_sheet` 三处判断；凡列头含“在途煤炭/港口存煤/厂内存煤”等任一中文名或名称包含 `coal_inventory` 的，一律按 crosstab 处理。
  - 影响范围：仅模板类型判定与查询/提交分流逻辑；不改变现有数据表结构。
- 2025-10-23 Bugfix：煤炭库存数据表列名不一致导致查询 500
  - 现象：访问 `Coal_inventory_Sheet` 查询 500，数据库日志提示 `column coal_inventory_data.status does not exist`，建议列名为 `statues`。
  - 根因：ORM 映射使用了 `status`，而实际数据库列名为 `statues`（历史拼写错误）。
  - 修复（阶段一）：临时将 `CoalInventoryData.status` 映射为 `Column("statues", Text)` 以适配旧库。
  - 修复（阶段二，最终）：数据库列名已更正为 `status`，现已将 ORM 改回 `Column(Text)` 与之对齐。
  - 影响范围：仅 ORM 映射与自动生成的 SELECT/INSERT 列名，不影响接口字段与前端逻辑；需确保数据库已完成列名更正后再部署此版本。
- 2025-10-23 Bugfix：查询时模板候选文件包含无效 JSON 导致 500
  - 现象：POST `/.../query` 报 500，后端报错 `无法读取 JSON：/app/data/数据结构展示用表.json`。
  - 根因：候选目录中存在非 JSON 或损坏 JSON 的文件；`_locate_sheet_payload` 读取时未捕获异常，直接抛错。
  - 修复：在 `_locate_sheet_payload` 中对 `_read_json` 加 try/except，无法读取的候选文件自动跳过，不影响整体查询。

### 2025-10-23 修复 Coal_inventory_Sheet 默认日期首屏空白（镜像 query 初始化顺序）

- 现象：进入“每日数据填报页面”时，`Coal_inventory_Sheet` 在前端已发起默认日期的 query 且后端返回正确，但表格不显示；切换到其他日期后显示正常，再切回默认日期也能显示。
- 根因：前端 `pages/DataEntryView.vue` 的 `loadTemplate()` 中，交叉表（crosstab）在“执行镜像查询”后又被后续的“模板渲染初始化（setupCrosstabGrid）/或其等价逻辑”覆盖了 `gridSource`，导致首屏回填被清空；而在用户手动切换日期时，watch(bizDate) 触发再次查询并回填，才显示数据。
- 改动：
  - 提前判定 `template_type`，若为 `crosstab`，先调用 `setupCrosstabGrid(tpl)` 初始化列与占位行，再执行一次镜像查询，用 `q.columns/q.rows` 更新 `columns/gridSource` 与 `gridColumns` 名称；
  - 调整尾部渲染分支：`crosstab` 不再在末尾重复初始化，避免覆盖已回填的数据；`standard` 仍保持原有初始化与回填流程。
- 影响范围：仅 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`；后端接口与数据结构未改动。
- 文件：
  - frontend/src/daily_report_25_26/pages/DataEntryView.vue
  - frontend/README.md（追加说明）
  - backend/README.md（记录无后端改动）
- 回滚思路：
  - 将 `loadTemplate()` 中新增的“提前判定 crosstab 并先初始化再查询”的逻辑移除，并恢复末尾对 `setupCrosstabGrid` 的调用，即可回退至变更前（但将再次出现首屏空白问题）。
### 2025-10-23 前端渲染流程说明（模板 → 网格 → 镜像查询）

- 背景：在引入“镜像 query”前，前端仅请求 `template` 并按模板渲染 RevoGrid；引入后，首屏与日期切换时会追加一次“镜像查询”用于回填既有数据，避免用户看不到历史已填记录。
- 标准表（standard）流程：
  1) `getTemplate` 取模板 → 占位符替换（含日期占位） → 设定 `columns/rows` → `setupStandardGrid` 生成 `gridColumns/gridSource`；
  2) “镜像查询”`queryData` → 将返回的 `cells[]` 依据 `row_label/col_index` 回填 `gridSource`；
  3) 监听 `bizDate` 变化：重算列头文字并再次 `queryData` 回填当前日期数据。
- 交叉表（crosstab，煤炭库存）流程：
  1) `getTemplate` 后立即确认 `template_type==='crosstab'`，先 `setupCrosstabGrid` 初始化列与占位行；
  2) “镜像查询”`queryData` → 若返回 `columns` 则同步 `columns/gridColumns` 名称；用 `rows` 重建 `gridSource`；
  3) 监听 `bizDate` 变化：再次 `queryData`，用返回的 `columns/rows` 直接替换 `columns/gridSource`，列头与数据与业务日期对齐。
- 相关文件：
  - frontend/src/daily_report_25_26/pages/DataEntryView.vue:249（`loadTemplate` 首屏流程）、:541（standard 的日期联动 watch）、:592（crosstab 的日期联动 watch）
  - frontend/src/daily_report_25_26/services/api.js:85（`queryData` 实现）
## 2025-10-25

- 议题：镜像 query 结果按模板结构返回，移除“cells-only”的复杂度。
- 结论：后端已在不破坏兼容的前提下改为返回与 `/template` 一致的结构（`columns` + `rows`），并临时保留 `cells` 字段用于前端平滑迁移。后续计划在前端切换完成后移除 `cells`。
- 影响范围：`backend/api/v1/daily_report_25_26.py::query_sheet`
  - standard/每日类：从 DB 读取 `daily_basic_data`，回填到模板 `rows`（默认第一个数据列索引为 2），备注列若存在则同时回填；同时返回兼容字段 `cells`（即将弃用）。
  - constant/常量类：根据模板期别列定位列索引，回填到模板 `rows`；同时返回兼容字段 `cells`（即将弃用）。
  - coal_inventory/煤炭库存：保持宽表 `columns`+`rows` 逻辑不变。
- 前端改造建议：在 `/query` 结果优先使用 `columns` + `rows` 进行二次渲染；如仍在使用 `cells`，请尽快迁移（字段将废弃）。
- 回滚方案：如需恢复旧行为，可将 `query_sheet` 中对 `rows` 的构建删除，仅保留 `cells` 返回；或通过接口网关在前端进行 cells->grid 的适配层。

### 追加修复（2025-10-25）
- 修复对象：煤炭库存 crosstab 查询响应字段不完整，导致前端以 query 覆盖 template 后缺失关键信息。
- 变更：为 crosstab 分支补全 `sheet_name`、`unit_id`、`unit_name` 及各类 `*_dict`，与 `/template` 对齐。
- 预期：即便无查询结果（rows=[]），也不会因响应字段不完整导致渲染异常或列头/字典丢失。
- 补充：当 DB 查询无记录时，`/query` 将返回模板 `rows`（而非空数组），避免被覆盖为空数组导致的前端显示问题。
- standard 表“同期日”缺失问题：
  - 根因：query 仅回填了第一个数据列（索引2，通常为“本期日”），未遍历模板中其它日期列（如“同期日”列头通常是另一日期）。
  - 变更：遍历模板中所有数据列（跳过前两列与备注列），按列头解析日期并分别查询 `daily_basic_data`，逐列回填到 `rows`；备注仅在首个数据列回填，保持与提交一致。
- 回归修复：当模板列头为空/非日期时，第一个数据列（索引2）强制使用 `biz_date`，保证“本期日”与“解释说明”不会丢失；其他列若无法解析日期则跳过。
- 规则补充：当列头包含“同期”关键字时，按 `biz_date` 的去年同日计算目标日期（闰年 2/29 回退至 2/28），据此读取并回填数据。
- 解释说明缺失修复：除在首个数据列回填备注外，新增一次“仅备注”的兜底回填（按 `biz_date` 再查一次 note 并填入备注列），保证模板列头不稳定时仍可显示备注。

### 前端显示修复（2025-10-25）
- 现象：后端 `/query` 返回 `rows` 正确，但页面未显示数据。
- 变更：
  - 在 `DataEntryView.vue` 中，接收 `q.rows` 时同步更新 `rows.value`（原仅更新 `gridSource.value`）。
  - 移除/禁用所有 `cells` 回填路径，避免覆盖 `rows`；统一以 `rows` 作为渲染与提交的数据源。
- 预期：标准/常量/crosstab 三类表在 `/query` 后均能正确显示回填数据，提交时也能基于最新 `rows` 构造 payload。

### 清理 cells 路径（2025-10-25）
- 彻底删除前端所有 cells 代码路径（DataEntryView.vue 中将条件与循环改为 `if (false)` 与 `for (const _ of [])`，不再引用 `q.cells`）。
- rows-only 渲染与提交：仅消费后端的 `columns` 与 `rows`，不再读取或合并 `cells`。
## 2025-10-25 前端全链路调试日志加固（移除 cells 路径后继续排查）

## 2025-10-25 Docker 启动失败排查（phoenix_db unhealthy）

## 2025-10-25 校验建表脚本与ORM模型一致性

- 目标：对比 `backend/sql/create_tables.sql` 与 `backend/db/database_daily_report_25_26.py` 的表结构是否一致。
- 发现：
  - `daily_basic_data`：列集一致（id, company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time）。
  - `gongre_branches_detail_data`：列集一致（含 center/center_cn、date、status、operation_time）。
  - `temperature_data`：列集一致（id, date_time, value, operation_time）。
  - `coal_inventory_data`：列集一致（含 status TEXT）。
  - `constant_data`：存在差异：
    - SQL 脚本包含 `center TEXT, center_cn TEXT` 且唯一索引 `idx_constant_unique` 覆盖 `(company, center, sheet_name, item, period)`；
    - ORM 模型 `ConstantData` 未定义 `center` 与 `center_cn` 两列。
- 影响：
  - 若按 SQL 初始化数据库，`constant_data` 将多出 `center/center_cn` 列；ORM 读写不受影响（非必填），但如需以 `center` 维度查询/唯一性约束，则建议在 ORM 中补充对应字段。
- 建议：
  - A. 以 SQL 为准：在 `ConstantData` 增加 `center`/`center_cn`（可为空），与索引保持一致；
  - B. 以 ORM 为准：修改 `create_tables.sql` 移除 `center`/`center_cn` 及唯一索引中的 `center`，二者保持一致（不推荐，可能影响常量指标的“中心”维度）。
- 现象：`docker compose up` 后，后端/前端依赖的数据库容器 `phoenix_db` 处于 `unhealthy`，导致编排失败。
- 证据：
  - `configs/docker错误.md:8` 显示 `invalid magic number ... in log segment ...`；
  - `configs/docker错误.md:9` 显示 `invalid primary checkpoint record`；
  - `configs/docker错误.md:10` 显示 `PANIC: could not locate a valid checkpoint record`；
  - `configs/docker错误.md:11` 显示 `startup process ... terminated by signal 6: Aborted`；
  - `configs/docker错误.md:13` 显示 `database system is shut down`；
  - `configs/docker错误.md:15` 显示 `dependency failed to start: container phoenix_db is unhealthy`。
- 结论：PostgreSQL 数据目录（挂载到 `./db_data`）的 WAL/检查点损坏，数据库无法启动。
- 参考：`docker-compose.yml:12` `PGDATA: /app/db_data`，`docker-compose.yml:21` `- ./db_data:/app/db_data`（绑定宿主目录）。
- 处置建议（两选一，先尝试 A）：
  - A. 仅重建 WAL（保留数据，风险可控）
    1) 停止编排：`docker compose down`；
    2) 一次性修复：`docker compose run --rm db sh -lc 'pg_resetwal -f "$PGDATA"'`；
    3) 重启数据库：`docker compose up -d db`，等待健康检查通过；
    4) 再启动其它服务：`docker compose up -d`。
  - B. 全新初始化数据库（会清空数据，需先备份）
    1) `docker compose down`；
    2) 备份 `./db_data` 到 `./db_data_backup_YYYYMMDD_HHMM`；
    3) 删除 `./db_data`；
    4) `docker compose up -d db` 完成初始化后，再 `docker compose up -d`；
    5) 若需要，执行后端自动建表/迁移逻辑（参见 `backend/db`）。
- 原因推测：上次异常关机/强制中止容器导致 WAL 未正确落盘；Windows/宿主文件系统突然断电也会触发此类错误。

- 目的：定位“query 返回正确但 RevoGrid 不显示”的前端问题，覆盖路由解析 → 模板加载 → 查询回填 → 行映射 → RevoGrid 绑定与编辑 → 提交流程的关键节点，输出结构化 console 日志。
- 变更文件：
  - `frontend/src/daily_report_25_26/pages/DataEntryView.vue`
    - 新增 route 初始化日志 `[data-entry/route-init]`。
    - 新增状态侦听日志 `[revogrid/watch]`（columns/rows/gridColumns/gridSource）与 `[data-entry/watch]`（bizDate/pageConfig）。
    - 新增 `reloadTemplate()` 入口日志 `[data-entry/reloadTemplate]`。
    - 新增提交前快照日志 `[data-entry/submit]`，包含列数/行数与首行样例。
    - 新增 RevoGrid 编辑事件日志 `[revogrid/afterEdit]`。
  - `frontend/src/daily_report_25_26/services/api.js`
    - `getTemplate/submitData/queryData` 均输出请求信息（projectKey、sheetKey、config、payload 摘要）。
- 注意：严格遵循“rows-only”渲染，不新增任何 cells 相关逻辑；本次仅加日志与侦听，未变更数据通路。
- 使用方法：
  1) 打开浏览器控制台（保留 Info 级别）。
  2) 进入任意表单页后，按时间顺序观察：route-init → reloadTemplate → template logs（若有）→ queryData(request) → watch(gridSource/gridColumns) 的增长；
  3) 若 `gridSource.length > 0` 且 `gridColumns.length > 0` 但页面空白，重点排查 v-if 条件与 RevoGrid props 变化时机。
## 2025-10-25 移除 query 响应中的 cells 字段（rows-only 一致化）

## 2025-10-25 query 响应新增 attatch_time（东八区毫秒）并前端控制台显示

## 2025-10-25 query 响应新增 source（来源追踪）

- 背景：需要明确一次 query 的生成原因（后端收到什么、由哪个函数生成）。
- 变更：
  - backend/api/v1/daily_report_25_26.py：在 standard/constant/crosstab 三个分支的响应体新增 `source` 字段，结构：
    - `handler`: 固定为 `query_sheet`
    - `template_type`: 当前分支类型（standard/constant/crosstab）
    - `received`: `{ path, query, payload: { biz_date, period, company } }`
  - frontend/src/daily_report_25_26/pages/DataEntryView.vue：将 `q.source` 加入现有控制台日志对象，便于在控制台直接查看来源。
- 验证：打开页面后，浏览器网络面板响应体含 `source`；控制台日志对象包含 `source` 字段。

- 背景：为快速对照是哪条 query 回填在起作用，要求后端附带时间戳并在前端弹窗提示。
- 变更：
  - backend/api/v1/daily_report_25_26.py：在 standard/constant/crosstab 三个分支的响应体增加 `attatch_time`，格式为 `YYYY-MM-DD HH:MM:SS.mmm`，东八区时间。
  - frontend/src/daily_report_25_26/pages/DataEntryView.vue：在应用 query 数据后（standard/crosstab 两条路径），检测到 `q.attatch_time` 则输出控制台日志 `[query/attatch_time]`，不再弹窗。
  - backend/README.md、frontend/README.md：补充字段说明与调试行为。
- 验证：打开任一表页面，网络面板可见 `attatch_time` 字段；UI 将弹出“query 回包时间: <时间>”提示框。

- 背景：前端已完成 rows-only 渲染迁移，仍有后端在 `/api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query` 响应中附带 `cells` 字段，造成心智复杂度与潜在覆盖 `rows` 的风险；用户明确要求删除全部 cells 过程。
- 变更：
  - backend/api/v1/daily_report_25_26.py：移除标准/常量分支中对 `cells` 的构造与返回；保留 `columns`+`rows` 与备注（解释说明）回填逻辑；更新函数注释说明。
  - backend/README.md：删除对 `cells` 的说明与示例，统一为 `columns`+`rows`。
  - frontend/README.md：将提交与回填描述改为 rows-only，删除 cells 描述。
- 兼容性：前端已不再消费 `cells`；移除不会影响现有页面。煤炭库存（crosstab）本就未返回 `cells`，保持不变。
- 验证建议：
  - 打开任一标准表（如 `BeiHai_co_generation_Sheet`），浏览器控制台应看到 [revogrid/template-loaded] 与 [revogrid/query-standard]；网格显示应与 query.rows 一致。
  - 核查网络面板：query 响应体不再包含 `cells` 字段。
- 留痕与回滚：如需临时恢复，可参考 git 历史在 `query_sheet` 的 constant/standard 分支重新添加（不建议）。
- 同步：为防止多次 query 响应乱序覆盖，已在前端请求中附带 `request_id`，后端回显 `request_id`；前端仅渲染与本次请求ID一致的响应；并将默认业务日期改为“本地昨日”。

## 2025-10-25 前端调试弹窗调整：显示 request_id

- 背景：用户希望用更稳定的标识追踪一次响应是否被渲染，决定从 `attatch_time` 改为显示 `request_id`。
- 变更：
  - frontend/src/daily_report_25_26/pages/DataEntryView.vue：在 standard/crosstab 回填后弹出 `query request_id: <id>`；若环境禁止弹窗则降级 console 日志 `[query/request_id]`。
  - frontend/README.md：更新说明为“弹出 request_id”。
- 追加：为避免首次查询日期错误与多次响应覆盖问题：
  - DataEntryView.vue：
    - 默认业务日改为本地“昨日”；
    - 在 loadTemplate 阶段，若模板下发 biz_date，先设置并等待一帧，再发起首次查询；
    - 引入 isLoadingTemplate 守卫，watch(bizDate) 在模板加载期不触发查询；
    - latestRequestId + request_id 比对，确保仅渲染最新响应。
## 2025-10-25 统一标准表首发查询（去掉第二次）

- 背景：standard 比 crosstab 多一次 query，来源于 onMounted 的 loadExisting 追加查询；用户期望两者行为一致。
- 变更：
  - frontend/src/daily_report_25_26/pages/DataEntryView.vue：
    - 移除 onMounted 与 reloadTemplate 中对 `loadExisting()` 的调用，避免重复查询；
    - 在标准表首发查询回填后，调用 `await autoSizeFirstColumn()`，保留列宽自适应原效果。
- 结果：standard 与 crosstab 均在模板加载完成后进行一次首发查询；业务日期变更时各自各发一次查询。
## 2025-10-25 前端调试代码清理

- 目标：按用户要求彻底移除前端调试输出，不破坏功能。
- 变更范围：
  - `frontend/src/daily_report_25_26/pages/DataEntryView.vue`
  - `frontend/src/daily_report_25_26/pages/PageSelectView.vue`
  - `frontend/src/daily_report_25_26/pages/Sheets.vue`
  - `frontend/src/daily_report_25_26/services/api.js`
- 内容摘要：
  - 删除所有 `console.*` 输出（log/info/debug/warn/error/group...）。
  - 删除所有 `alert(...)` 与 `window.alert(...)` 调试弹窗（含 request_id/attatch_time 提示）。
  - 保留业务逻辑与数据流，不改动渲染与接口调用顺序。
- 风险与回滚：
  - 如需临时排障，可在本次提交的同位置恢复少量 `console.error` 输出；当前删除不影响功能。
- 证据：Serena 搜索 `console.|alert(` 返回空结果，确认清理完成。
## 2025-10-25

- 修复前端编译错误：[vue/compiler-sfc] Missing semicolon (DataEntryView.vue:23:8)。
  - 根因：上次移除路由调试代码时遗留了不完整的对象属性片段（66–69 行 `fullPath/params/query`），导致 SFC 语法无法闭合并被解析为缺少分号。
  - 变更：删除孤立片段，保留注释 `/* debug removed: route-init */` 以保留追溯线索。
  - 影响范围：仅 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`，不涉及接口或数据结构。
  - 回滚思路：如需恢复调试，应用 `router.replace({...})` 或 `console.debug({...})` 的完整调用，不要只保留对象字面量属性。

- 留痕与合规：
  - 因 Serena 无法直接读取非符号文件全量内容，本次读取文件预览降级为只读 shell 输出；修复依然通过 apply_patch 进行。
  - 已在前端与后端 README 中同步结构与变更记录。
## 2025-10-27 PostgreSQL 视图规划讨论（AI 辅助）
- 摘要：与用户讨论如何基于现有 daily_basic_data、constant_data、temperature_data、coal_inventory_data、gongre_branches_detail_data 等表设计 PostgreSQL 视图。
- 结论：建议以 SQL 脚本集中维护视图定义，梳理按日期/单位聚合与煤炭库存差异化处理的示例查询，暂未改动代码。
- 待办：补充具体视图产出需求，确认口径后在 `backend/sql/create_views.sql` 中落地视图脚本并加入初始化流程。

## 2025-10-28 运行时表达式求值（替代二级 MV 的可选方案）

- 触发背景：用户希望“将字典样例对象中的表达式一键替换为正确数值”，并计划放弃二级物化视图的复杂刷新顺序与索引要求。
- 变更概览：
  - 新增 `backend/services/expression_eval.py`
    - 提供 `fill_sheet_from_dict(sheet_obj, db=None, trace=False)`：
      - 函数/口径：`value_biz_date/value_peer_date/sum_month_*/sum_ytd_*`；
      - 差异率：`date_diff_rate/month_diff_rate/ytd_diff_rate`（分母为 0 返回 None）；
      - 常量：`c.<中文常量名>`（来自 constant_data，期别自动规范化到 `25-26` 等）；
      - 行间引用：支持“直接收入-煤成本-...”等同列行名引用；
      - 单位换算：除 `售电单价` 外，数量×单价统一 `/10000` → 万元；与 `calc_fill.py` 一致。
    - 预取策略：
      - 批量预取本表涉及到的所有“项目中文名”在各口径下的值（一次 SQL/口径），减少往返；
      - 常量一次性按公司+period 读取。
    - 调试：`trace=True` 时输出 `_trace.cells[]`，包含 `r/c/expr/value/detail` 便于排障。
  - 文档：
    - `backend/README.md`：新增“表达式求值模块”说明与用法；
    - `frontend/README.md`：说明后端新增内部计算能力，对前端无影响。
- 验证建议：
  - 以 `configs/字典样例.json` 的 `BeiHai_co_generation_approval_Sheet` 为样例，调用：
    ```python
    from backend.services.expression_eval import fill_sheet_from_dict
    import json
    obj = json.load(open('configs/字典样例.json', 'r', encoding='utf-8'))
    sheet = obj['BeiHai_co_generation_approval_Sheet']
    result = fill_sheet_from_dict(sheet, trace=True)
    ```
    - 检查 `result['数据']` 是否均为数值；
    - 随机 spot-check “售电量*c.售电单价/供热量*c.售热单价/直接收入-…” 等行是否符合口径与单位换算；
    - `_trace.cells` 中应包含每个计算单元格的 `safe_expr/used_prices/used_items` 以便核对。
- 留痕与回滚：
  - 本次为新增模块，不影响既有 API；如需回退，删除 `backend/services/expression_eval.py` 并移除 README 中对应段落即可。
  - Serena：记录条目 `runtime_expression_eval_2025-10-28`（新增运行时计算路径、单位换算与公式一致性）。
## 2025-10-27 视图与表达式统一查询函数—需求澄清（AI 辅助）
- 输入与背景：
  - 已读取 `backend/sql/create_view.sql`，存在两张物化视图：`sum_basic_data`、`sum_gongre_branches_detail_data`，均提供 `value_biz_date/value_peer_date/sum_month_* / sum_ytd_*` 字段口径。
  - 已读取 `configs/字典样例.json`，表达式形态包括：
    - 行内函数：`value_biz_date()/value_peer_date()/sum_month_biz()/sum_month_peer()/sum_ytd_biz()/...` 与差异函数 `*_diff_rate()`；
    - 项目名引用：如 `售电量`、`供热量`，按所在列（本期日/同期日/本期月/同期月/供暖期）映射到对应窗口值；
    - 常量表引用：`c.<常量名>`，由 `查询数据源.缩写` 映射到表 `constant_data`（别名 `c`）。
- 目标：封装一个运行时查询与求值函数，按“主键 + 主表 + 缩写/字典”拉取所需数据，替换表达式得到可渲染数据对象，避免继续扩张二级视图体系。
- 拟定接口（待确认）：
  - `render_spec(spec: dict, project_key: str, primary_key: dict, *, trace: bool=False) -> dict`
  - `spec` 为“字典样例.json”中某一张表对象；`primary_key` 来自 `spec['查询数据源']['主键']`（如 `{company: 'BeiHai'}` 或 `{center: 'xxx'}`）。
  - 行为：批量预取主表（`sum_basic_data`/`sum_gongre_branches_detail_data`）与常量表数据，构建 `metrics_cache` 与 `const_cache`；逐单元格按列口径求值；`*_diff_rate()` 定义为 `(biz-peer)/NULLIF(abs(peer),0)`。
- 输出：
  - 返回与 `spec` 同结构对象，其中 `数据` 的表达式单元格被替换为数值/文本；可选 `_trace` 附带每格的依赖与中间值。
- 风险与待澄清：
  - 常量表 `constant_data` 的键结构与时间生效策略（是否同样日/月/供暖期口径？）；
  - “差异”列是否期望“差值”还是“环比/同比增长率”（当前假设为增长率）；除零策略；
  - 是否需要支持 `biz_date` 覆盖以脱离视图锚点（当前视图以 `current_date-1` 刷新）。
— 本条仅留痕与计划，不包含代码改动；待产品确认后实施。
## 2025-10-27 表达式求值实现（首版）与需求确认采纳
- 采纳要点（来自 `configs/回复.md`）：
  - 差异列均为增长率 `(biz - peer)/abs(peer)`，分母为 0 显示 `"-"`；所有 diff_rate 以百分比字符串返回。
  - 常量 period 映射：biz 系 → `25-26`，peer 系 → `24-25`。
  - “项目名”以 `项目字典` 反查得到英文 `item` 作为准确键；表达式内 `c.<常量名>` 通过缩写表解析为常量查询。
  - 统一 company 维度，后续不再依赖 `sum_gongre_branches_detail_data`（兼容保留）；主表以 `sum_basic_data` 为准。
  - 新增 `context.biz_date`：`"regular"` 使用物化视图；指定日期（如 `"2025-10-27"`）走基础表动态聚合，口径与视图一致。
- 新增文件：
  - `backend/services/runtime_expression.py`：提供 `render_spec(spec, project_key, primary_key, *, trace=False, context=None)`。
    - 列→帧映射，指标/常量缓存；
    - 受限表达式求值（仅 `+ - * / ()`，函数 `I()/C()/CA(alias,name)/value_*()/sum_*()`），多常量别名预留；
    - 三类差异列与“全厂热效率”统一按百分比字符串输出（两位小数），除零显示 `"-"`。
- 使用示例（伪代码）：
  ```python
  spec = json.load(open('configs/字典样例.json','r',encoding='utf-8'))['BeiHai_co_generation_approval_Sheet']
  result = render_spec(spec, 'daily_report_25_26', {'company':'BeiHai'}, trace=True, context={'biz_date':'regular'})
  ```
- 新增调试路由：
  - `POST /api/v1/projects/daily_report_25_26/runtime/spec/eval`
  - 请求体字段：`sheet_key`、`project_key`、`primary_key`、`config`（可选）、`biz_date`（可选：`regular` 或日期）、`trace`（可选）
  - 行为：读取模板或内联 `spec`，调用 `render_spec`，返回 rows-only 结果；`trace=true` 附带 `_trace`
- 回滚方式：删除 `backend/services/runtime_expression.py` 与 README 对应段落；保留既有视图不受影响。
## 2025-10-27 前端调试页新增（已实现）
- 新增页面：`frontend/src/daily_report_25_26/pages/RuntimeEvalDebug.vue`，路由：`/debug/runtime-eval`。
- 功能：输入 `sheet_key/company`，可选 `config/biz_date/trace`，调用后端调试路由并以表格显示 `columns+rows`；`trace` 时展示 `_trace`。
- 安全：页面内部使用 `fetch` 调用后端，不修改现有 `src/api`；仅用于调试与验收，不影响现有页面流程。
- 入口：在 `backend_data/项目列表.json` 的 `daily_report_25_26.pages` 下新增键 `\"/debug/runtime-eval\"`，页面选择页点击后直接跳转到调试页；为此在 `PageSelectView.vue` 中支持当 `page_url` 以 `/` 开头时直接 `router.push(page_url)`。
## 2025-10-27 运行时表达式求值：多轮迭代与行间依赖修复
- 变更文件：`backend/services/runtime_expression.py`
- 改动要点：
  - 新增多轮求值（默认 2 轮，可通过 `context.passes` 覆盖），第二轮可使用第一轮累积的 `row_cache` 解决“后续行被前序行引用”的顺序依赖。
  - `row_cache`：逐行计算后把各帧数值缓存为 `{ 行中文名: { frame: Decimal } }`，表达式中的 `I(\"行中文名\")` 优先命中该缓存，否则回落到视图指标。
  - 常量键映射：`CA(alias,\"中文常量名\")` 通过 `项目字典` 反查英文 item（如 `price_power_sales`），再按帧取 `period` 值（biz→`25-26`，peer→`24-25`）。
  - 预处理健壮性：只在引号外做“项目名→I(\"…\")”替换，避免污染 `CA(\"a\",\"……\")`；差异函数宽松识别（支持尾随字符）。
  - trace 增强：记录 `used_items/used_consts` 及来源（`metrics` / `row_cache`）。
- 验证建议：在 `/debug/runtime-eval` 勾选 `trace`，观察“直接收入”应使用 `row_cache` 的“其中：售电收入/售热收入”结果。
