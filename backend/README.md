# 后端说明（FastAPI）

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
- 默认登录有效期 30 分钟（滑动），配置文件热更新自动清理会话；`/auth/login|logout|me` 提供登录、退出、会话自查。
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
