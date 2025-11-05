# 进度记录

# 进度记录

## 2025-11-09（气温/边际利润卡片面积调整）

前置说明（降级留痕）：
- Serena 仍无法对 `.vue` 模板与样式区块执行结构化写入，依 3.9 矩阵降级使用 `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚可将该文件恢复至变更前版本。

- 本次动作：
  - 将气温卡片内 ECharts 高度调整为 240px，使卡片整体更紧凑。
  - 在宽屏布局下使气温与边际利润卡片各占 6 列，并为两者补充 `min-height: 320px`，保证同排时高度一致。
  - 移除气温卡片上的 `dashboard-grid__item--table` 修饰，使其不再强制占满一行，宽屏下可与边际利润卡片同排展示。
  - 为所有图表 legend 统一增加 `bottom` 配置并相应增大 `grid.bottom`，避免图例遮挡坐标轴刻度。
  - 调整 `.dashboard-table` 为 `box-sizing: border-box;`，消除气温表格在卡片中出现的多余滚动条。
  - 将“当日省市平台服务投诉量”卡片在宽屏下设置为 `span 6`、最小高度 320px，并去除 `dashboard-grid__item--table` 修饰，使其在宽屏下与同排卡片共享一行。
  - 三个“供暖单耗”卡片在宽屏布局下统一改为 `span 4`，三列排布保持等宽整齐。
  - 缩小 `.dashboard-grid` 的行间距至 14px，以减半卡片间的垂直空隙。
  - “标煤消耗量对比”“煤炭库存”两张卡片在宽屏下均改为 `span 6` 并移除 `dashboard-grid__item--table` 标记，确保并行展示。

影响范围与回滚：
- 仅影响 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 样式与图表高度；如需恢复旧尺寸，回滚该文件即可。

验证建议：
1. 在桌面宽度下查看仪表盘，确认两个卡片平均分布并保持等高。
2. 检查气温曲线在新高度下仍完整展示关键刻度，边际利润表格滚动正常。

## 2025-11-09（边际利润表格回归图表卡片）

前置说明（降级留痕）：
- Serena 仍不支持 `.vue` 模板区块的结构化写入，按 3.9 矩阵降级使用 `apply_patch` 调整 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；如需回滚，可恢复该文件至本次修改前版本。

本次动作：
- 将“边际利润简报”卡片内重新嵌入边际利润表格，并为表格外层添加 `dashboard-table-wrapper--compact` 以撑满卡片空间。
- 调整网格列宽，使“气温变化情况（7日窗口）”与“边际利润简报”在宽屏下各占 6 列，同排显示且卡片高度保持一致。
- 移除临时的“边际利润明细”独立网格项，保持页面结构简洁。

影响范围与回滚：
- 仅影响 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚该文件即可恢复拆分布局。

验证建议：
1. 在桌面端打开仪表盘，确认“气温变化情况”“边际利润简报”并排展示且高度一致。
2. 检查“边际利润简报”卡片内图表与表格均随业务日期更新，表格滚动区域正常。

## 2025-11-09（边际利润板块布局分离）

前置说明（降级留痕）：
- Serena 暂不支持 `.vue` 模板区块的结构化编辑，按 3.9 矩阵使用 `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；若需回滚，可恢复该文件至本次修改前版本。

本次动作：
- 将“边际利润简报”与“收入分类对比”卡片设为各占 6 列，使其默认同排显示并保持统一宽度。
- 新增独立网格项“边际利润明细”承载原表格内容，位置放置于上述两张卡片下方，方便阅读。
- 清理“边际利润简报”卡片内的表格，保证卡片内仅保留图表内容。

影响范围与回滚：
- 仅影响 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 模板与样式；回滚该文件即可恢复原布局。

验证建议：
1. 打开仪表盘页面确认“边际利润简报”和“收入分类对比”在桌面宽度下共行显示，宽度相同。
2. 检查“边际利润明细”表格是否独立显示在两张卡片下方，数据与切换的业务日期同步更新。

## 2025-11-09（仪表盘移除 Trace 选项）

前置说明（降级留痕）：
- Serena 仍不支持对 `.vue` 单文件组件的模板区块进行结构化写入，依 3.9 矩阵降级使用 `apply_patch` 编辑 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；如需回滚，可恢复该文件到变更前版本。

本次动作：
- 删除页面头部“Trace”复选框及对应的 `traceEnabled` 响应式变量，避免用户在正式环境看到调试开关。
- 保留原业务日期选择与自动刷新逻辑，其余布局及数据处理未受影响。

影响范围与回滚：
- 仅影响 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；如需恢复调试开关，可回滚至本次修改前的版本。

验证建议：
1. 打开仪表盘页面确认头部仅保留业务日期输入框，Trace 开关不再显示。
2. 切换业务日期确保 `loadDashboardData` 行为正常，`show_date/push_date` 机制无回归。

## 2025-11-09（数据看板布局调整）

前置说明（降级留痕）：
- Serena 暂无法对 `.vue` 单文件组件的样式区块执行结构化写入，依 3.9 矩阵降级使用 `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；如需回滚，可恢复该文件至变更前版本。

本次动作：
- 缩减仪表盘顶部摘要卡片的圆角、内边距与投影，使整体视觉更紧凑。
- 为 `dashboard-grid` 增加 `grid-auto-rows` 与父子级 flex 拉伸，使各图表卡片在不同分辨率下保持统一高度、宽度自适应。
- 调整卡片阴影强度与 z-index 设定，修正纵向排列时下方组件侵入上方区域的视觉问题。

影响范围与回滚：
- 仅影响 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 样式；如需恢复旧版布局，可直接回滚该文件。

验证建议：
1. 打开仪表盘页面，确认摘要卡片尺寸更为紧凑且不遮挡下方内容。
2. 在不同窗口宽度下查看图表区域，确保组件高度一致且纵向排列时无重叠现象。

## 2025-11-09（边际利润面板接入真实数据）

前置说明（降级留痕）：
- Serena 仍不支持对 `.vue` 单文件组件执行结构化写入，依 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；如需回滚，可恢复该文件到变更前版本。

本次动作：
- 新增 `marginSection`/`marginSeries` 等计算属性，将 `/dashboard` 返回的“2.边际利润”节点转换为单位列表与指标数值，替换原先的演示常量。
- 调整 `useMarginOption` 图表配置，按真实数据绘制“直接收入/煤成本/外购热成本/水电辅材成本”堆叠柱与“可比煤价边际利润”折线，并在表格中同步展示七列指标。
- 顶部卡片“集团当日边际利润（演示）”更名为“集团全口径可比煤价边际利润”，数值直接取集团口径的 `可比煤价边际利润` 并保留两位小数。
- “收入分类对比（集团）”“标煤消耗量对比”卡片文案移除“本期 vs 同期”字样，仅保留单位说明，页面措辞统一。
- “标煤消耗量对比”板块接入 `/dashboard` 的“5.标煤耗量”节点，自动解析本期/同期并绘制双柱图、顶部标签与表格；摘要卡片随“集团全口径”本期值刷新，缺失时回退演示数据，并在图表/表格/卡片中统一保留一位小数。

影响范围与回滚：
- 仅影响 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；如需恢复演示模式，可将文件回退至本次修改前的版本，即可重新使用模拟数组。

验证建议：
1. 打开数据看板页面，确认“边际利润简报”图表与表格在业务日期切换后即时刷新，图例与表格列包含外购热、水电辅材、边际利润等真实指标。
2. 检查页面顶部“集团全口径可比煤价边际利润”卡片数值是否与 `/api/v1/projects/daily_report_25_26/dashboard` 响应中 `data.2.边际利润.本期.集团全口径.可比煤价边际利润` 保持一致。

## 2025-11-09（集团收入明细面板接入真实数据）

前置说明（降级留痕）：
- 按 3.9 矩阵继续使用 `desktop-commander::read_file` + `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`，若需回滚请恢复该文件。

本次动作：
- 新增 `incomeSection`/`incomeSeries` 计算属性，解析 `/dashboard` 的“3.集团全口径收入明细”节点，将本期/同期收入转化为分类数组及数值列表。
- `useIncomeCompareOption` 改为根据上述计算结果绘制常规柱状图（图例保持“本期/同期”），同时移除此前的断轴尝试，恢复单轴展示以保持与现有 ECharts 版本兼容。

影响范围与回滚：
- 仅调整 `DashBoard.vue`；如需恢复演示数据，可回退至修改前版本重新启用静态数组。

验证建议：
1. 进入仪表盘切换业务日期，确认“集团全口径收入明细”柱状图随接口数据更新，分类顺序与配置保持一致。
2. 对照 `/api/v1/projects/daily_report_25_26/dashboard` 返回的 `data.3.集团全口径收入明细`，核对各收入科目当期/同期数值是否正确映射。

## 2025-11-08（数据看板煤炭库存聚合修正）

前置说明（降级留痕）：
- Serena 当前无法对 `.py` 文件执行结构化写入，按照 3.9 矩阵要求降级使用 `desktop-commander::read_file` + `apply_patch` 修改 `backend/services/dashboard_expression.py`，如需回滚可恢复该文件。

本次动作：
- 将 `_fill_coal_inventory` 中的库存装载逻辑由覆盖写入调整为按 `company_cn + storage_type_cn` 累加，确保同一仓储类型下的不同煤种数值会聚合求和。
- 对空值与缺失字段保持跳过，避免写入 `None` 导致的异常；表达式求和依旧按模板定义的公司列表执行。

影响范围与回滚：
- 仅影响 `/api/v1/projects/daily_report_25_26/dashboard` 返回的“7.煤炭库存明细”模块；若需恢复旧行为，将上述函数回滚即可。
- 集团全口径等汇总表达式现会基于累加后的公司库存再求和，模板语法无需调整。

验证建议：
1. 访问 `/api/v1/projects/daily_report_25_26/dashboard?show_date=YYYY-MM-DD`，确认各单位/仓储类型返回的 `value` 与数据库按煤种求和后的结果一致。
2. 检查“集团全口径”各指标是否等于下方单位数值之和，与 `coal_inventory_data` 中同日数据比对。

## 2025-11-08（供热分中心单耗明细接入）

前置说明（降级留痕）：
- 受 Serena 限制继续使用 `desktop-commander::read_file` + `apply_patch` 编辑 `backend/services/dashboard_expression.py`，若需回滚请恢复该文件。

本次动作：
- 新增 `_fill_heating_branch_consumption`，读取 `sum_basic_data` 视图中各供热中心的 `value_biz_date`，并按模板字典映射填充“8.供热分中心单耗明细”下的热、电、水三项单耗。
- 在 `evaluate_dashboard` 中调用该函数，仅针对本期数据填充，保持“计量单位”配置原样传递。

影响范围与回滚：
- `/api/v1/projects/daily_report_25_26/dashboard` 现会返回供热中心单耗的实际数值；如需恢复旧行为，移除新增函数及调用即可。
- 仅涉及数据呈现，不改动其他板块或数据库结构。

验证建议：
1. 调用上述接口并检查“8.供热分中心单耗明细”中各中心三项指标与 `sum_basic_data` 当日 `value_biz_date` 一致。
2. 若某中心无数据，确认视图是否存在对应记录；必要时在模板中补充表达式或回退为 0。

## 2025-11-08（仪表盘统一数据容器搭建）

前置说明（降级留痕）：
- Serena 仍无法直接修改 `.vue` 文件，按照 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`。

本次动作：
- 引入 `reactive` 并创建 `dashboardData` 容器，用于集中存放 `/dashboard` 响应的元信息（`show_date`、`push_date`、`generated_at`）及各板块原始数据。
- `loadDashboardData` 在请求成功后写入上述字段，并将 `payload.data` 去除 `push_date`、`展示日期` 后整体挂载到 `dashboardData.sections`，为后续逐模块替换静态演示数据做准备。

影响范围与回滚：
- 当前页面仍显示历史假数据，暂无直接视觉变化；如需回滚，可恢复该文件并移除容器赋值逻辑。
- 后续各图表/表格只需引用 `dashboardData`，即可逐步迁移到真实接口数据。

验证建议：
1. 打开仪表盘页面，借助 Vue DevTools 或控制台打印 `dashboardData`，确认 `meta` 与 `sections` 会随 `/dashboard` 响应更新。
2. 检查 `sections` 中是否已经包含“1.逐小时气温”“2.边际利润”等节点，为下一步数据映射提供依据。

## 2025-11-08（仪表盘气温模块接入）

前置说明（降级留痕）：
- 继续按 3.9 矩阵使用 `desktop-commander::read_file` + `apply_patch` 调整 `frontend/src/daily_report_25_26/pages/DashBoard.vue`。

本次动作：
- 新增 `temperatureSection`、`temperatureSeries` 计算属性，将 `/dashboard` 响应中的“1.逐小时气温”数据转换为图表与表格所需结构，支持日期排序、均值计算及缺失值兜底。
- `tempOpt`、`temperatureTableData`、`averageTemp` 改为依赖上述计算结果，实时反映后端数据；保持原有图表/表格组件不变。
- 顶部“平均气温（7日当期）”卡片直接读取 `push_date` 对应的 24 小时列表求算术平均（保留两位小数）；若无该日期则显示“—”。
- 表格与折线图同样使用两位小数的日均结果，确保与后端算法一致。
- 后端 `_fetch_temperature_series` 缺失小时不再填 0，而返回 `null`，前端均值计算会自动忽略缺测点，避免平均值被拉低。
- 折线图新增 `markLine` 在 `push_date` 对应的日期列上标注“业务日期”，方便识别当前展示日。

影响范围与回滚：
- 仪表盘气温图与表格现基于真实接口数据；若需回滚，可将相关计算属性与 `useTempOption` 回退为原静态数组。
- 其他模块仍使用演示数据，未受影响。

验证建议：
1. 访问 `/projects/daily_report_25_26/pages/dashboard/...`，观察气温折线图与表格是否随 `show_date` 切换而变化。
2. 检查顶部“平均气温（7日当期）”卡片取值是否与表格展示一致；若返回空数组，应显示“—”并保持图表为 0 基线。

## 2025-11-08（数据看板 Revogrid 表格统一）

前置说明（降级留痕）：
- Serena 无法对 `.vue` 文件进行符号级写入，按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 新增组件并改写 `frontend/src/daily_report_25_26/pages/DashBoard.vue`，如需回滚可恢复上述文件。

本次动作：
- 新建 `frontend/src/daily_report_25_26/components/DashboardRevoGrid.vue`，封装 Revogrid 默认主题、列模板与只读配置，并统一引入 `@revolist/vue3-datagrid` 样式。
- `DashBoard.vue` 删除自定义 Table 组件，改以 `DashboardRevoGrid` 展示气温、边际利润、标煤耗量、投诉等表格，同时将数据结构统一为列定义 + 对象行，便于后续接入真实接口。

影响范围与回滚：
- 数据看板所有表格外观与交互保持一致，可复制滚动；如需回滚，移除新组件并恢复 `DashBoard.vue` 即可。
- 其他页面未引用该组件，行为不受影响。

验证建议：
1. 打开仪表盘确认四个表格均渲染为 Revogrid，列宽自适应且支持复制。
2. 若需扩展排序、锁列等能力，可在 `DashboardRevoGrid` 中追加 Revogrid 对应配置。

## 2025-11-08（数据看板 API 初版）

前置说明（降级留痕）：
- Serena 当前无法对 `.py`、`.js`、`.vue` 文件执行结构化插入，依据 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/services/api.js`、`frontend/src/daily_report_25_26/pages/DashBoard.vue`，如需回滚可恢复这些文件。

本次动作：
- 新建 `backend/services/dashboard_expression.py` 渲染引擎，负责解析 `show_date`、读取 `backend_data/date.json` 与 `backend_data/数据结构_数据看板.json`，输出标准化 `DashboardResult`。
- `GET /api/v1/projects/daily_report_25_26/dashboard` 调整为调用上述引擎，返回 `project_key`、`show_date`、`push_date`、`generated_at`、`source` 及 `data` 节点，`show_date` 校验失败返回 400。
- 前端新增 `getDashboardData` 封装，请求该 API 并在仪表盘头部默认展示 `push_date`；日历选取新日期时会重新调用接口。

影响范围与回滚：
- 仅新增接口，不改动既有模板/填报/审批能力；若需回滚，可删除新增路由与辅助函数。
- 前端现已根据 API 返回结构渲染仪表盘日期；文件读取依赖 `backend_data/数据结构_数据看板.json` 与 `backend_data/date.json`，若需更换数据源可替换或扩展加载逻辑。

下一步建议：
1. 完成数据库查询逻辑后，将当前 JSON 占位返回替换为实时数据聚合结果。
2. 在前端 `DashBoard.vue` 中完善数据映射与错误提示，后续可补充加载状态与图表数据还原。

## 2025-11-08（数据看板头部刷新按钮移除）

前置说明（降级留痕）：
- Serena 对 `.vue` 单文件组件暂未开放结构化写入能力，依 3.9 矩阵降级使用 `desktop-commander::read_file` 与 `apply_patch` 在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 内定位并移除刷新按钮；如需回滚，可恢复该文件至修改前版本。

本次动作：
- 数据看板头部仅保留 Trace 开关与业务日期选择器，彻底移除临时“刷新”按钮。
- 删除顶部“今日/业务日期”静态文字，保持仪表盘标题区域简洁。
- 清理脚本中的 `refreshDashboard` 占位函数以及对应按钮/文字样式，避免无效依赖。

影响范围与回滚：
- 仅影响仪表盘页面头部交互；回滚 `DashBoard.vue` 即可恢复按钮。
- Trace 开关与日期选择绑定仍为前端本地状态，尚未触发后端接口。

下一步建议：
1. 待 `/dashboard` API 就绪后，可在日期选择变化时触发数据刷新逻辑。
2. 如需补充提示信息，可在 Trace/日期组件上增加帮助文案，便于非技术人员理解。

## 2025-11-07（数据填报指标联动保持一致）

前置说明（降级留痕）：
- Serena `search_for_pattern` 对 `.vue`、`.py` 文件仅返回行号，无法读取完整上下文，按 3.9 矩阵降级使用 `desktop-commander::read_file` 配合 `apply_patch` 修改 `backend/api/v1/daily_report_25_26.py` 与 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`，若需回滚可恢复上述文件旧版本。
- Serena 暂不支持对 Markdown 进行写入，降级使用 `apply_patch` 更新 `configs/progress.md`、`backend/README.md`、`frontend/README.md`，回滚方式为还原对应文档。

本次动作：
- 后端补充 `LINKAGE_DICT_KEYS` 并实现 `_apply_linkage_constraints`，在模板/查询响应透传 `linkage_dict`，标准报表提交前按配置同步联动行值，避免写库后出现主子项不一致。
- 前端 `DataEntryView.vue` 构建 `linkageMap`，在模板加载与镜像查询阶段重建联动映射，并在 `handleAfterEdit` 中将用户输入同步至所有关联行；提交 payload 同步携带 `linkage_dict`，便于后端二次校验。
- README 系列文件同步记录联动规则与回滚方式，确保交付说明与实现一致。

影响范围与回滚：
- 在 `backend_data/数据结构_基本指标表.json` 中声明 `"指标联动"` 的基础指标表会在加载/提交阶段保持各联动项列值一致，历史差异数据加载后也会按主项值展示；如需恢复自由编辑，可移除新增常量与 `_apply_linkage_constraints`，并回滚前端联动逻辑。
- 常量指标、煤炭库存等其它模板未改动；回滚上述文件即可恢复原有行为。

下一步建议：
1. 在数据填报 UI 中增加联动提示（如行高亮或说明气泡），降低填报人员误解。
2. 结合审计需求输出联动差异告警或历史日志，便于排查过往数据是否存在不一致。

## 2025-11-07（审批取消批准功能）

前置说明（降级留痕）：
- Serena 无法对 `.vue`、`.js` 非符号文件执行结构化编辑，依据 3.9 矩阵降级使用 `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/PageSelectView.vue`、`frontend/src/daily_report_25_26/store/auth.js`、`frontend/src/daily_report_25_26/services/api.js`。
- Serena 对导入语句及 JSON 文件缺乏符号编辑能力，降级使用 `apply_patch` 调整 `backend/api/v1/daily_report_25_26.py` 导入与 `backend_data/auth/permissions.json` 权限矩阵；回滚可恢复上述文件旧版本。

本次动作：
- 后端新增 `can_revoke` 权限标识、`WorkflowRevokeRequest` 模型、`/workflow/revoke` 接口及 `WorkflowStatusManager.mark_pending`，允许将已批准单位恢复为 `pending` 状态。
- 更新权限矩阵，向 Global_admin / Group_admin / ZhuChengQu_admin 授予 `can_revoke`，其它用户组默认 `false`。
- 前端扩展 Pinia `auth` 仓库与 API 客户端，新增 `revokeWorkflow`、`canRevokeUnit`，并在审批卡片中提供“取消批准”按钮，成功后自动刷新进度。
- 同步文档与权限输出结构，确保新增字段在前后端一致展示。

影响范围与回滚：
- 具备撤销权限的账号可在可见单位范围内将审批状态从 `approved` 复位为 `pending`，`status.json` 对应字段恢复 `pending/null/null`。
- 若需撤销该能力，可回滚上述文件改动并移除 `can_revoke` 字段，前端按钮将随之消失。

下一步建议：
1. 如需保留审计信息，可在 `status.json` 扩展撤销人/时间字段并在前端展示。
2. 建议补充批准→取消批准→再次批准的端到端测试，验证接口幂等与权限校验。

## 2025-11-07（数据展示页加载提示优化）

前置说明（降级留痕）：
- Serena 暂不支持对 `.vue` 单文件组件执行符号级编辑，依据 3.9 矩阵降级使用 `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue`。
- 回滚思路：恢复上述文件旧版本即可恢复原有“无展示数据”占位提示。

本次动作：
- 数据展示页占位块根据 `loading` 状态在加载阶段显示“数据载入中...”，加载结束但无数据时仍提示“无展示数据”，避免首次进入页面时出现突兀的空提示。
- 相关说明同步至 `frontend/README.md` 与 `backend/README.md`，保持跨端文档一致。

影响范围与回滚：
- 页面请求数据库视图过程中以内联占位提示展示加载状态，数据库/接口逻辑保持不变；回滚文件可恢复旧文案。
- 其他页面（仪表盘、审批、数据填报等）占位逻辑未改动。

下一步建议：
1. 可进一步结合接口响应耗时埋点，评估是否需要骨架屏或进度条形式的加载反馈。
2. 若后续视图返回空数据，需要优化空状态文案与引导，避免与加载提示混淆。

## 2025-11-06（移除占位页面配置）

前置说明（降级留痕）：
- Serena 暂不支持对 JSON 非符号文件执行删除操作，依据 3.9 矩阵降级使用 `apply_patch` 修改 `backend_data/项目列表.json`。
- 回滚思路：恢复该文件旧版本即可重新出现占位页面。

本次动作：
- 从 `backend_data/项目列表.json` 删除 `placeholder` 页面配置，确保项目页不再渲染“用于占位”链接；其他页面配置保持不变。
- 文档同步：本记录、`backend/README.md`、`frontend/README.md` 更新项目结构描述。

影响范围与回滚：
- 前端项目页列表将不再出现 placeholder 卡片；如需恢复，可在 JSON 中重新加入同名节点。
- 既有页面（dashboard/data_show/data_approval/data_entry/constant_data/debug）不受影响。

下一步建议：
1. 若未来新增实际页面，可直接在 `项目列表.json` 登记，或为无需配置文件的页面补充专用元数据。
2. 建议前端渲染层增加空数据校验，避免因配置缺失产生占位链接。

## 2025-11-06（审批页面默认业务日调整）

前置说明（降级留痕）：
- Serena 对 `.vue` 文件暂无符号级编辑能力，依据 3.9 矩阵降级使用 `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/ApprovalView.vue`。
- 回滚思路：恢复该文件旧版本即可恢复审批页默认读取 `set_biz_date` 的行为。

本次动作：
- `ApprovalView.vue` 在 `biz_date` 选择为 regular 时，新增 `getWorkflowStatus` 调用获取服务端 `biz_date`，并将该日期随请求发送至 `/runtime/spec/eval`，避免 `set_biz_date` 影响审批视图。
- 保留“自定义”模式逻辑不变，审批员仍可手动切换日期。
- 文档同步：本记录、`backend/README.md`、`frontend/README.md` 更新审批页面默认日期说明。

影响范围与回滚：
- 审批页面刷新、切换 trace 或回到页面时默认显示业务日（东八区昨日），不再随 `set_biz_date` 变化；如需恢复旧逻辑，回滚该组件即可。
- 数据展示页仍沿用 `set_biz_date` 控制展示日期，功能未受影响。

下一步建议：
1. 若未来还需在审批页展示“当前展示日期”提示，可考虑复用 workflow status 返回的 `display_date` 信息作辅助说明。
2. 当业务日计算逻辑变更时，请同步更新 workflow status 的 `biz_date` 以保持审批页默认值一致。

## 2025-11-06（仪表盘 DashBoard.vue Vue 化）

前置说明（降级留痕）：
- Serena 当前无法对 `.vue` 单文件组件执行符号级编辑，依据 3.9 矩阵降级使用 `apply_patch` 重写 `frontend/src/daily_report_25_26/pages/DashBoard.vue`。
- 回滚思路：恢复上述文件至本次改动前的版本即可撤销页面重构。

本次动作：
- 将 `configs/仪表盘参考.vue` 中的 React + Tailwind 示例转译为 Vue3 `<script setup>` 组件，定义局部 `Card` / `Table` 组件与静态演示数据，复刻 7 块 ECharts 图表及顶部指标摘要。
- 页面通过 `v-chart` 组件加载静态配置并同步渲染表格明细，为后续对接 `dashboard/summary` 后端接口预留数据结构。
- 文档同步：`frontend/README.md`、`backend/README.md` 新增会话小结，记录前端重构与后端接口现状。
- `router/index.js` 新增 `/dashboard` 路由匹配；`PageSelectView.vue` 调整 `openPage` 逻辑，点击“数据看板”卡片即进入新版仪表盘页面。
- `index.html` 注入 CDN 版 `echarts.min.js`，`DashBoard.vue` 内置 `EChart` 包装组件以 `window.echarts` 驱动图表，避免额外 npm 依赖；摘要卡与表格样式升级为渐变/阴影风格，并根据 ECharts 调色板动态生成边框与悬停配色，整体视觉更聚合。

影响范围与回滚：
- 仪表盘页面现可在纯前端环境展示设计稿效果，暂未切换到真实 API；如需回滚，恢复 `DashBoard.vue` 旧版本即可退回原占位实现。
- 现有后端聚合接口不受影响，后续联调时仅需替换页面数据来源。

下一步建议：
1. 接入 `GET /api/v1/projects/daily_report_25_26/dashboard/summary`，用真实业务日/同期数据替换静态示例。
2. 结合后端聚合成本评估是否需要引入缓存或按日预计算，避免频繁刷新触发重量级查询。

## 2025-11-06（售电煤炭库存填报权限）

前置说明（降级留痕）：
- Serena 暂不支持对 JSON / JS 非符号文件执行插入更新，依据 3.9 矩阵降级使用 `apply_patch` 修改 `backend_data/auth/permissions.json` 与 `frontend/src/daily_report_25_26/store/auth.js`。
- 回滚思路：恢复上述两个文件的旧版本即可撤销额外授权及前端筛选逻辑。

本次动作：
- `backend_data/auth/permissions.json` 在 `unit_filler` 组的 `data_entry` 规则下追加 `Coal_inventory_Sheet` 显式授权，并更新 `updated_at` 标记此次权限变更。
- `frontend/src/daily_report_25_26/store/auth.js` 在 `by_unit` 模式下引入 `extraSheets` 白名单，允许通过权限文件显式授权的表单绕过单位前缀匹配，从而展示售电公司煤炭库存表。
- 文档同步：本记录、`backend/README.md`、`frontend/README.md` 补充售电煤炭库存权限开通说明。

影响范围与回滚：
- 新账号 `shoudian_filler` 登录后可在数据填报页面访问 `Coal_inventory_Sheet`；回滚时删除授权或恢复文件快照即可恢复旧行为。
- 其他单位仍沿用原 `by_unit` 筛选逻辑，未列入授权清单的表单行为不受影响。

下一步建议：
1. 如售电公司后续新增独立表单，可继续在权限文件 `sheets` 中登记并复用本次逻辑。
2. 后端可考虑在模板元数据中补充 `unit_code` 字段，减少前端依赖命名约定进行匹配。

## 2025-11-06（HTTP-only API 路由修复）

前置说明（降级留痕）：
- Serena 对 Bash 与 Nginx 配置文件暂不提供符号级编辑，依据 3.9 矩阵降级使用 `apply_patch` 更新 `ww.bash` 与 `deploy/nginx.http-only.conf`。
- Serena 暂不支持在仓库根目录新增 Compose 文件，因此使用 `apply_patch` 创建 `ww-certbot.yml`。
- 回滚思路：恢复上述两个文件的旧版本即可撤销本次调整。

本次动作：
- `deploy/nginx.http-only.conf` 新增 `/api/` 反向代理，HTTP-only 镜像在同域下即可透传请求到 `backend:8000`，无需依赖构建期写入完整域名。
- `ww.bash` 补充 `VITE_API_BASE` 二次校验，仅允许 `http(s)://` 或 `/` 开头的值，在构建日志中输出最终取值，并在推送后自动同步 `latest` 标签，防止继续生成指向本地磁盘的前端静态资源且确保服务器默认拉取即可获得最新镜像。
- 新增 `ww-certbot.yml`，包含 HTTP-only 前端和 Certbot 组合，通过 `/bin/sh -c` 执行申请脚本；目前命令内固定邮箱 `locookies123@gmail.com` 与域名 `platform.smartview.top`，如需使用其它参数可直接编辑该命令。

影响范围与回滚：
- 重新构建前端镜像后，默认执行 `./ww.bash` 即可生成指向 `/api/v1` 的资产；如需跨域 API，可显式设置合法 URL 并从日志确认。
- 回滚时恢复两个文件即可返回旧行为，但需注意旧版 HTTP-only 配置访问 `/api` 会返回前端资源。

下一步建议：
1. 将脚本打印的 `VITE_API_BASE` 同步写入构建产物的元数据或 Markdown 记录，方便部署后回溯。
2. 评估在 `ww.bash` 内加入最小 smoke test（如 `curl` `/api/health`），确保镜像在推送前即可发现 API 代理异常。

## 2025-11-05（仪表盘聚合与前端联动）

前置说明（降级留痕）：
- Serena 目前无法对全新 schema/service 文件及 `.vue` 组件执行符号级编辑，依据 3.9 矩阵降级使用 `apply_patch` 创建 `backend/schemas/dashboard.py`、`backend/services/dashboard.py` 与 `components/dashboard/*` 等文件。
- 回滚思路：删除新增后端模块并还原 `backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/pages/DisplayView.vue`、`services/api.js` 及文档改动，即可恢复到原有占位仪表盘状态。

本次动作：
- 后端：实现 `GET /api/v1/projects/daily_report_25_26/dashboard/summary`，按业务日聚合气温、边际利润、收入分类、单耗、煤耗、投诉量与煤炭库存数据，新增 `dashboard` schema/service 并在路由层返回结构化 JSON。
- 前端：重写 `DisplayView.vue`，引入业务日筛选、加载提示及 7 个仪表盘卡片；新增基于 SVG 的折线图、分组柱状图、堆积柱状图组件，并在各卡片中配套表格展示本期/同期差异。
- 文档：更新 `backend/README.md`、`frontend/README.md` 描述仪表盘接口与页面结构；在本文件登记改动与降级原因。

影响范围与回滚：
- 新增接口默认受登录权限控制，并按 `allowed_units` 过滤可见单位；若需回滚，可移除 dashboard 相关模块与路由注册，前端恢复旧版展示页即可。
- 前端 SVG 图表未引入第三方依赖，渲染失败时仍可通过返回的表格信息查看关键指标；如需临时停用，可在页面中隐藏对应卡片。

下一步建议：
1. 视图聚合会触发多次查询，可评估 Postgres 物化视图/缓存策略或在服务层增加简单缓存。
2. 根据业务反馈补充更多异常提示（如缺报单位/指标高亮）及导出能力，完善仪表盘配套交互。

## 2025-11-04（镜像构建与部署拆分）

前置说明（降级留痕）：
- Serena 当前不支持在仓库根目录新建脚本/Compose 文件，依据 3.9 矩阵降级使用 `apply_patch` 创建 `ww.bash`、`ww.ps1` 与 `ww.yml`。
- 回滚思路：删除新增脚本/配置或恢复 `docker-compose.server.yml` 的本地构建流程即可撤销本次调整。

本次动作：
- 新增 `ww.bash` / `ww.ps1`，分别面向 Bash 与 PowerShell 环境封装后端、前端 HTTPS 与 HTTP-only 三个镜像的构建与推送步骤，统一写入时间戳标签并在完成后提示镜像名称，便于服务器部署引用；脚本增加 `VITE_API_BASE` 校验，自动过滤 `file://` 或 Windows 本地路径，避免构建产物引用本地磁盘。
- 新增 `ww.yml`，以预构建镜像替换原 build 阶段，保留 PostgreSQL、Certbot 服务与后端数据目录挂载，方便服务器直接拉取镜像运行。
- 新增 `ww-http-only.yml`，在无需证书的场景仅启动 HTTP 版前端、后端与数据库，去除 Certbot 与证书卷，适用于暂不启用 HTTPS 或交给 Cloudflare 托管的部署。
- 文档同步：更新 `backend/README.md`、`frontend/README.md` 与 `configs/progress.md`，补充镜像分发链路与部署指引。

影响范围与回滚：
- 如需恢复服务器本地构建，可继续使用 `docker-compose.server.yml` 或删除 `ww.bash`、`ww.ps1`、`ww.yml`、`ww-http-only.yml` 并回退本次文档变更。
- `ww.yml` 依赖 Docker Hub 镜像与证书卷，部署前需确认 `.env` 内的 `BACKEND_IMAGE`、`WEB_IMAGE`、`WEB_HTTP_IMAGE` 与实际推送版本一致；`ww-http-only.yml` 默认暴露 `80:80`，需确认云端/防火墙已放行 HTTP 访问。

下一步建议：
1. 将 `ww.bash`/`ww.ps1` 输出的镜像标签自动写入共享 `.env` 或脚本内更新 `ww.yml`，减少人为同步成本。
2. 为构建脚本增加基础 smoke test，如通过 `docker run --rm` 检查健康端口，再执行推送，降低线上运行风险。

## 2025-11-03（登录页面视觉同步）

前置说明（降级留痕）：
- Serena 暂不支持对 `.vue` 单文件组件进行符号级编辑，依据 3.9 矩阵在本次会话中降级使用 `apply_patch` 完成模板与样式重构，并保留原文件备份以备回滚。
- 回滚思路：将 `frontend/src/daily_report_25_26/pages/LoginView.vue` 恢复至 11-02 版本即可撤销本次视觉调整；文档条目可按需删除。

本次动作：
- 前端：重构 `LoginView.vue`，引入视觉面板与装饰图形，保持登录逻辑不变并增加响应式样式；追加视觉面板文本居中并下调蓝色渐变亮度以贴合参考页面效果。
- 后端：调整 `backend/sql/create_view.sql` 中 `calc_coal_cost`，使“煤成本”按“标煤耗量 × 标煤单价 / 10000”计算，替换原煤耗量逻辑。
- 文档：更新 `frontend/README.md`、`backend/README.md` 与 `configs/progress.md` 记录登录页与煤成本公式的同步情况。

影响范围与回滚：
- 前端：影响范围仅限登录页面的外观展示；若需回滚，覆盖旧版组件即可恢复原样式。
- 后端：如需回退，可将 `calc_coal_cost` 中的字段与常量键恢复为 `consumption_amount_raw_coal` / `price_raw_coal`。

下一步建议：
1. 如需对接验证码或企业公告，可在当前表单面板内扩展，不会破坏已实现的左右分栏布局。
2. 若仍需保留“原煤成本”口径，可新增独立 item 避免覆盖现有指标。

## 2025-11-02（登录与审批进度打通）

前置说明（降级留痕）：
- Serena 对 `backend_data/账户信息.json` 返回空结果，改用 `read_file` 获取原始配置；后续所有代码编辑均使用 `apply_patch` 小步提交。
- 新增权限矩阵、后端模块与前端状态管理涉及多个新文件，均按 3.9 矩阵要求记录，并可通过删除新增文件与恢复引用完成回滚。

本次动作：
- 配置：新增 `backend_data/auth/permissions.json`，整理用户组→页面/操作/单位映射及审批 Biz 日偏移（默认东八区“昨日”）。
- 后端：新增 `backend/services/auth_manager.py`、`backend/services/workflow_status.py` 与 `backend/api/v1/auth.py`、`backend/schemas/auth.py`；`routes.py`、`daily_report_25_26.py` 接入登录校验、审批/发布接口；所有项目路由默认要求 Bearer Token。
- 前端：新增 Pinia `auth` store、统一请求头注入与 `/auth/*` 调用；登录页改为真实认证流程；路由守卫自动判定跳转；页面选择页增加审批进度卡片（含批准/发布操作与权限过滤）；模板/表格列表按用户权限过滤。
- 日期管理：创建 `backend_data/date.json`，`auth_manager` 统一计算实际业务日（东八区昨日）并维护“数据展示日期”；发布动作会将展示日期同步至当前业务日，未发布时保持上一批数据，前端在审批卡片中提示“当前业务日期 | 当前数据展示日期”。
- 部署：新增 `backend/requirements.txt`、`backend/Dockerfile.prod`、`frontend/Dockerfile.prod`、`deploy/nginx.conf`、`docker-compose.prod.yml` 与 `deploy/server_setup.bat`，形成可直接在服务器构建的生产版容器栈；批处理脚本负责创建数据目录、载入 `.env.prod` 并执行 `docker compose build/up`。
- UI：`DataEntryView` 为 `Unit_admin` / `unit_filler` 引入历史日期只读模式（非当期业务日仅可查看、不能编辑提交），并在 `main.js` 全局引入主题样式修复子路由刷新样式丢失问题。
- 编排：`docker-compose.prod.yml` 中数据库使用命名卷 `db_data`，后端数据仍通过宿主挂载 `./backend_data:/app/data` 保持可读写配置。
- 新增 `docker-compose.server.yml` / `deploy/Dockerfile.web` / `deploy/nginx.prod.conf`，复刻旧项目的 Nginx+Certbot 方案（80/443 暴露、域名 `platform.smartview.top`），方便在 VPS 上直接替换运行。
- 新增 `init-certbot.sh`：一键执行“停 web → 构建/启动临时 HTTP-only → certbot 签发 → 恢复 web”流程，便于首次申请或更新 HTTPS 证书。
- 单镜像支持：新增 `Dockerfile.full`、`deploy/nginx.full.conf`、`deploy/supervisord.conf` 与 `build-single-image.sh`，可一次构建前后端合并镜像（`phoenix-all`），用于资源受限或“单容器”部署场景。

- 影响范围与回滚：
  - 认证与权限逻辑集中在 `backend/services/auth_manager.py` 与 `frontend/src/daily_report_25_26/store/auth.js`；删除新文件并还原调用点即可回滚至旧版“摆设登录”。
  - 审批/发布状态现持久化于 `backend_data/status.json`，如需回滚，可移除文件并将 `workflow_status.py` 恢复至内存版本，同时删除前端审批卡片即可恢复旧界面。

下一步建议：
1. 后端提交/审批接口接入细粒度权限校验（当前仅验证登录态）。
2. 账户明文密码与配置热加载策略需在上线前引入哈希与缓存失效通知。
3. 审批/发布状态落地数据库或 Redis，补充多节点场景下的一致性策略。

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
- `backend/services/runtime_expression.py`：锚点日期改用 Asia/Shanghai 时区的当日日期（`_project_today()`），默认仍回退“今日-1”，避免部署在 UTC 环境下导致 (本期日) 滞后两天。
- `backend/services/runtime_expression.py`：当 `item_en` 以 `sum_month_`/`sum_season_` 等前缀开头时，`value_*` 自动映射到 `sum_month_*` / `sum_ytd_*` 字段，保障累计类指标在日列/比率列中返回非零值。

验证：
- 通过手动审查 `render_spec` 行级量化与前端 `buildSource` 输出逻辑，确认含 `%` 的差异列仍返回字符，不受小数位影响；建议在前端运行环境下分别加载 `Group_sum_show_Sheet` 与 `Group_analysis_brief_report_Sheet`，观察“万平方米省市净投诉量”等配置项是否以 2 位小数展示，其余保持模板默认精度。
- 针对新模板 `ZhuChengQu_sum_show_Sheet` 逐项检查 `value_biz_date(ZhuChengQu)`、`value_biz_date(BeiHai+XiangHai)` 等写法能正确取到目标公司指标，组合求和等价于逐项累加。
- 多段标题（如“二、热源厂”）所在行的差异列未填写 `date_diff_rate()` 时，应在审批/展示页保持为空。

影响范围与回滚：
- 变更主要影响审批页(`ApprovalView`)、展示页(`DisplayRuntimeView`)的渲染逻辑以及运行时表达式的行级精度；若需回滚，可还原上述文件至本次改动前版本，或删除后端 `accuracy_map` 相关逻辑并恢复统一小数位行为。
- 若需恢复旧的单 company 求值，可还原 `runtime_expression.py` 中 `_resolve_company_item/_value_of_item` 调整，并将 `companies_needed` 解析段落改回仅按行默认 company 读取。

## 2025-11-02

前置说明：
- 运行时表达式模块需补充白名单逻辑，Serena 无法在模块顶部对常量行做精确删除，按 3.9 降级矩阵使用 `apply_patch` 调整字面文本，已在本条记录留痕；其余修改通过 Serena 完成。

本次改动：
- `backend/services/runtime_expression.py`：新增 `_PREAGG_VALUE_ITEMS` 集合，并在 `_value_of_item` 中针对 `sum_month_total_net_complaints`、`sum_season_total_net_complaints` 等预聚合投诉指标直接返回 `value_biz_date/value_peer_date` 字段，避免被累计窗口逻辑强制改写为 `sum_month_*`/`sum_ytd_*`。
- `backend/api/v1/daily_report_25_26.py`：`/runtime/spec/eval` 默认读取 `auth_manager.current_display_date()`（映射 `DATA_DIRECTORY/date.json` 的 `set_biz_date`），在未显式指定或传入 `regular` 时以该日期调用 `render_spec`，并在响应中附带 `biz_date`/`biz_date_mode`/`requested_biz_date` 便于前端追踪。

验证：
- 暂未执行自动化用例；建议在 `ZhuChengQu_sum_show_Sheet` 页面检查“省市平台净投诉量”行 `(本期月)/(本供暖期)` 列是否与视图 `sum_basic_data` 的 `value_biz_date` 保持一致（与前一版本对比应无再次累加现象），并通过展示页 Trace 响应确认 `biz_date` 已回显 `date.json` 中的 `set_biz_date`。

影响范围与回滚：
- 影响展示页及审批页涉及“本月累计净投诉量”“本供暖期累计净投诉量”的表达式求值；若需回退，可移除 `_PREAGG_VALUE_ITEMS` 并恢复 `_value_of_item` 中的累计字段映射逻辑，或整文件回滚至本次提交前版本；如需恢复旧的 `biz_date` 透传逻辑，可撤销 `/runtime/spec/eval` 中关于 `set_biz_date` 的默认处理。

### 补充记录（2025-11-02 晚）

- `create_view.sql` 中的 `sum_basic_data`、`groups` 视图改为读取数据库会话级参数 `phoenix.biz_date`（缺省回落至 `current_date-1`）。运行时通过 `SET LOCAL phoenix.biz_date = :biz_date` 在查询阶段切换业务日期，沿用原 SQL 中的全部派生计算逻辑。
- `runtime_expression.py` 删除手写聚合逻辑，统一走视图查询：当 `context.biz_date` 提供具体日期时设置 GUC，未指定则重置为 `DEFAULT`，保证回退到旧口径。
- `frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue`：展示页的日期选择器默认读取 `date.json`（display_date），用户修改后直接把选定日期作为 `biz_date` 发送给 `/runtime/spec/eval`，日历旁显示当前生效口径。
- 建议在 `Group_sum_show_Sheet`、`ZhuChengQu_sum_show_Sheet` 开启 Trace 验证 `biz_date` 是否与 `date.json` 一致，并核对直接收入、供暖单耗、投诉 per 万㎡ 等关键指标已恢复正确值。

## 2025-11-04

前置说明：
- Serena 无法直接在 SQL 文件末尾追加内容，依据 3.9 降级矩阵使用 `apply_patch` 编辑 `backend/sql/create_view.sql`；回滚时删除新增视图定义并重新执行脚本。

本次改动：
- `backend/sql/create_view.sql`：新增普通视图 `calc_temperature_data`，按 `temperature_data` 的业务日期（24 小时）分组计算日最高/最低/平均温度，为后续天气数据统计提供聚合入口。

验证：
- 暂未执行数据库验证；建议在数据库运行 `SELECT * FROM calc_temperature_data LIMIT 5;`，确认视图创建成功并返回按日聚合的期望结构。

影响范围与回滚：
- 仅新增视图，不影响现有 `sum_basic_data` 等视图逻辑；如需回滚，删除该视图定义并重新加载脚本即可。

## 2025-11-06（HTTPS 切换与部署文件调整）

前置说明（留痕与合规）：
- 环境为沙箱只读，已按“3.9 编辑与文件操作降级矩阵”使用 Desktop Commander 工具进行小步安全修改；不涉及破坏性命令。
- 本次仅变更仓库内脚本/编排文件，不触及受限目录或远端 CI/CD。

本次动作：
- 更新 `ww.ps1:1`：新增 `BUILD_HTTP_ONLY` 开关（默认关闭），将 HTTP-only 前端镜像的构建与推送改为“可选”；启用 HTTPS 时默认跳过，避免不必要的镜像产出。
- 更新 `ww-http-only.yml:1`：升级为支持 HTTPS 的部署（开放 `80/443`，挂载 `certbot_etc` 与 `certbot_www` 卷，并内置 `certbot` 更新服务），`web` 服务改用 `WEB_IMAGE`（HTTPS 版）。

实现要点与流程：
- PowerShell 脚本：`Divider` 与 `Tag-And-PushLatest` 两个函数保持不变；通过新增布尔变量 `$BuildHttpOnly`（读取 `BUILD_HTTP_ONLY`）在构建阶段做分支，默认只构建/推送 HTTPS 版 `WEB_IMAGE`。
- Compose 部署：沿用 `deploy/nginx.prod.conf` 的证书路径与重定向策略，`web` 容器暴露 `80/443`（80 做 301 跳转，443 提供 TLS 服务）；`certbot` 容器以 `renew` 循环任务维持证书更新。

影响范围与回滚：
- 现有服务器可直接切换到本次调整后的 `ww-http-only.yml` 运行 HTTPS（需已有证书卷或先按 `ww.yml`/`ww-certbot.yml` 完成一次申请）。
- 若需回退到纯 HTTP-only，设置 `BUILD_HTTP_ONLY=1` 并改回 `WEB_HTTP_IMAGE` 的 compose 文件即可。

证据与文件清单：
- 修改：`ww.ps1:1`, `ww-http-only.yml:1`
- 参考：`deploy/nginx.prod.conf:1`, `ww.yml:1`

### 2025-11-06（域名与证书路径具体化）
- 域名：`platform.smartview.top`
- 邮箱：`locookies12@gmail.com`
- 证书（宿主机）：`/home/ww870411/25-26/certbot/letsencrypt/live/platform.smartview.top/`
- 变更：
  - `ww.yml:1` 与 `ww-http-only.yml:1` 的 `web`/`certbot` 服务将证书与 ACME webroot 改为宿主机绑定挂载：
    - `/home/ww870411/25-26/certbot/letsencrypt:/etc/letsencrypt`
    - `/home/ww870411/25-26/certbot/www:/var/www/certbot`
  - 移除两份 compose 中不再使用的命名卷 `certbot_etc`/`certbot_www`。
  - `ww-certbot.yml:1` 更新邮箱为 `locookies12@gmail.com`，并同步改为宿主机路径绑定挂载，便于一次性签发或重签直接落盘到上述目录。
- Nginx 配置确认：`deploy/nginx.prod.conf:1` 中 `server_name` 已是 `platform.smartview.top`；证书路径继续使用容器内 `/etc/letsencrypt/live/platform.smartview.top/`，与 compose 的宿主机路径绑定保持一致。
- 上线前自检：DNS 指向、80/443 放行、宿主目录存在并具备读写、已有证书文件可被 web 容器读取。

### 2025-11-06（禁用 latest 推送）
- 依据用户要求“绝对禁止 latest”，已移除 `ww.ps1` 中所有 `latest` 标记与推送逻辑：删除 `Tag-And-PushLatest` 函数，并去除后端/前端/HTTP-only 的调用。
- 影响：后续仅按时间戳 tag 推送，不再产生 `:latest`。
- 备注：本次构建失败的前端镜像为拉取 `nginx:1.27-alpine` 时网络 EOF；建议重试或预先 `docker pull nginx:1.27-alpine node:20-alpine` 后再运行脚本。

### 2025-11-06（ww.ps1 精简为“必要最小”）
- 目标：仅保留必要步骤，避免“为考虑而加”的非必要逻辑。
- 变更：
  - 移除 HTTP-only 分支与相关变量；脚本只构建/推送后端与 HTTPS 前端两张镜像。
  - 移除复杂的 `VITE_API_BASE` 过滤逻辑；仅当设置该环境变量时才作为 build-arg 传入，否则使用前端源码默认值。
  - 保留 `NO_CACHE` 支持与 `BUILD_TIMESTAMP`；日志仅输出关键信息。
- 影响：脚本总行数由 ~115 行降至 ~66 行，更易读、易控。

### 2025-11-06（构建稳定性增强：重试与预拉）
- ww.ps1 增强：
  - 新增 `Invoke-Retry`（最多 3 次，间隔 6 秒），用于 docker pull/build/push 的瞬时失败自动重试。
  - 在构建前预拉基础镜像：`python:3.12-slim`、`node:20-alpine`、`nginx:1.27-alpine`。
  - 对后端/前端 build/push 全部包裹重试，降低 EOF 失败概率。
- 说明：不改变输出镜像或版本，仅增强稳定性；无 latest 相关操作。

### 2025-11-06（构建加速镜像源——避免 auth.docker.io EOF）
- 现象：`failed to fetch oauth token: https://auth.docker.io/token EOF`，公共 Hub 取元数据不稳定。
- 变更：将基础镜像切换为 DaoCloud Hub 镜像源（可在国内稳定访问）：
  - backend/Dockerfile.prod:1 `FROM docker.m.daocloud.io/library/python:3.12-slim`（builder 与 runtime 两处）
  - deploy/Dockerfile.web:1 `FROM docker.m.daocloud.io/library/node:20-alpine`
  - deploy/Dockerfile.web:20 `FROM docker.m.daocloud.io/library/nginx:1.27-alpine`
- 影响：不改变业务产物，只更换镜像拉取来源；如需回退，改回 `python:3.12-slim` / `node:20-alpine` / `nginx:1.27-alpine` 即可。
### 2025-11-02（常量提交 500：移除 center/center_cn 依赖）
- 现象：在 `ZhuangHe_constant_Sheet` 提交数据时，前端 500；控制台报错 `{"ok":false,"message":"处理常量表数据时发生错误","error":"center_cn"}`（见 `configs/11.2常量提交错误.md:1,18`）。
- 根因：后端常量写库函数在构造 upsert 时引用了 `center/center_cn` 字段与唯一键 `(company, center, sheet_name, item, period)`；但数据库表与 ORM 模型均不再使用/不存在 `center/center_cn`，导致引用 `stmt.excluded.center_cn` 抛错。
- 变更：
  - `backend/api/v1/daily_report_25_26.py`
    - `_parse_constant_records`：取消向记录附加 `center_cn`；仅将中心中文名用于解析 `company/company_cn`，不再持久化中心字段。
    - `_persist_constant_data(records)`：
      - 写入前清理 `center/center_cn` 残留键；
      - `ON CONFLICT` 唯一键改为 `(company, item, period)`；
      - 更新字段集合移除 `center_cn`。
    - `_parse_decimal_value`：支持自动剔除字符串中的 `,`/`，`/空格，并过滤 `--`、`N/A` 等占位符，避免“采暖期供暖收入”等金额类单元格因存在千位分隔符而被解析为 `NULL`。
- 影响：
  - 常量数据幂等粒度以 `(company, item, period)` 为准；
  - 前端常量表 payload 无需也不应包含 `center/center_cn`；含中心维结构的表也仅用于解析 company/company_cn，不再单独存储 center 维度。
- 需要的数据库侧配合：为 `constant_data` 创建唯一约束/索引 `(company, item, period)`，并确保不存在 `center/center_cn` 列；否则 `ON CONFLICT` 将无法命中唯一键。
- 回滚思路：若需恢复 center 维度，需同步恢复表列 `center/center_cn`、唯一键 `(company, center, sheet_name, item, period)`，并回退服务端 upsert 的 `index_elements` 与 `set_`。
- 证据：
  - 服务端引用位置：`backend/api/v1/daily_report_25_26.py:1346`（变更后）
  - 模型定义：`backend/db/database_daily_report_25_26.py:40`（ConstantData 无 center/center_cn）
  - 示例 SQL（历史意图，仅供参考）：`backend/sql/sample_constant_data.sql:820` 起含 center/center_cn 列

### 2025-11-02（运行时温度极值接入 Group 分析简报）
- 场景：`Group_analysis_brief_report_Sheet` 中“日最高气温/日最低气温”需要取 `temperature_data` 当日极值，默认 `value_biz_date()` 仍接 sum_basic_data 导致返回 0。
- 变更：
  - `backend/sql/create_view.sql`、`backend/sql/create_temperature_view.sql`：视图更名为 `calc_temperature_data`，按日输出 `max_temp`/`min_temp`/`aver_temp`。
  - `backend/services/runtime_expression.py`
    - `_fetch_temperature_extremes`：新增从 `calc_temperature_data` 读取当日与同期日温度极值，统一映射到 `amount_temp_highest`、`amount_temp_lowest` 六个帧字段。
    - `render_spec` 在预取指标阶段将上述极值合并到 `metrics_by_company['Group']`，保持其它单位不受影响。
- 效果：模板仍使用 `value_biz_date()`/`value_peer_date()`，集团列可直接显示真实温度极值；差异列 `date_diff_rate()` 自动生效。
- 验证建议：
  1) 调用 `/runtime/spec/eval` 加 `trace=true`，确认 `_trace.used_items` 出现 `amount_temp_highest`/`amount_temp_lowest` 并返回新值；
  2) SQL：`SELECT * FROM calc_temperature_data WHERE date='2025-11-02';`；如需同期日，检查同一天减一年数据。
- 回滚思路：
  - 视图恢复为原 `average_temperature_data`；
  - 删除 `_fetch_temperature_extremes` 调用，并在 `Group_analysis_brief_report_Sheet` 中改回常量或默认值。

### 2025-11-06（供热分中心提交：center/center_cn 映射修复）
- 现象：在 `GongRe_branches_detail_Sheet` 提交数据时，`daily_basic_data` 中 `company`、`company_cn` 均写成“XX中心”（中文），未使用模板里的英文代号。
- 原因：`_parse_gongre_branches_detail_records` 仅从 payload 的 `center_dict` 键读取字典，但模板和前端传值使用的是“单位字典”，导致反向映射缺失。
- 变更：`backend/api/v1/daily_report_25_26.py`
  - `_parse_gongre_branches_detail_records` 使用 `_extract_mapping`，先查 `CENTER_DICT_KEYS`，若不存在再回落到 `COMPANY_DICT_KEYS`，并统一对项目字典走同样的转换，保证 `center_lookup` 能找到英文代号。
- 效果：分中心提交会将 `company` 写入 `HuaLe_Center` 等英文编码，`company_cn` 写入中文名称，满足数据库 Tall Table 设计。
- 验证建议：
  1) 在页面填写分中心数据并提交；
  2) 查询 `SELECT DISTINCT company, company_cn FROM daily_basic_data WHERE sheet_name='GongRe_branches_detail_Sheet' ORDER BY company;` 应显示英文编码 + 中文名称配对。
- 回滚：如需恢复旧行为，仅需将 `_extract_mapping` 调用还原为直接 `payload.get("center_dict")`。

### 2025-11-06（集团直接收入去除内售热）
- 现象：`groups` 视图中 `company='Group'`、`item_cn='直接收入'` 的重算块会把 `eco_direct_income` 连同 sum_basic_data 中的“内售热收入”一起求和。
- 变更：`backend/sql/groups.sql`
  - 在集团汇总基表 `base_grp` 中排除 `eco_direct_income` 基础行，避免重复；
  - 新增集团口径的自定义重算块，仅汇总 `售电/暖/售高温水/售汽` 四项收入。
- 效果：集团“直接收入”不再包含“内售热收入”，与主城区计算口径一致。
- 验证：执行 `SELECT item, value_biz_date FROM groups WHERE company='Group' AND item='eco_direct_income' LIMIT 1;` 并确认数值与四项收入之和一致。
- 回滚：删除新增 UNION 块，并将 `eco_direct_income` 从 `WHERE item NOT IN (...)` 的排除列表中移除即可。

### 2025-11-06（scid.* 省级汇总常量兼容）
- 现象：`ZhuChengQu_sum_show_Sheet` 行内使用 `scid.ZhuChengQu_sum` 时返回 0，原因是 `_value_of_const` 仅在当前 company 的常量缓存中查找，未回退到全局常量集合。
- 变更：`backend/services/runtime_expression.py`
  - `_value_of_const` 在本地别名查找不到时，会在 `self.consts_all` 中循环各公司别名，优先命中同名键，再进入 period 取值，兼容 `scid.Group_sum`、`scid.ZhuChengQu_sum` 等写法。
- 效果：`scid.*` 无需指定 `公司.常量` 形式即可返回合计库存值，历史模板写法保持有效。
- 验证：运行 `/runtime/spec/eval` 并检查 `_trace.used_consts` 是否出现 `scid.Group_sum` 等记录；或直接在前端页面观察库存列是否正常展示。
- 回滚：若要恢复旧行为，只需移除新增循环，让 `_value_of_const` 只在当前 company 常量缓存中查找即可。

## 2025-11-09（边际利润折线标签显示）

前置说明（降级留痕）：
- Serena 无法对 `.vue` 文件执行符号级写入，再次按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚时恢复该文件即可。

本次动作：
- 在 `useMarginOption` 中为“可比煤价边际利润”折线新增数值标签，统一使用一位小数并为每个单位显示气泡背景，便于直接读取边际利润值。
- 根据需求将图表高度调至 300px，同步移除卡片副标题“集团/各单位”保持视觉简洁。
- 在“收入分类对比（集团）”柱状图中为“本期”“同期”系列新增顶部标签，统一保留一位小数，便于直接比较收入规模。
- “单耗对比”板块新增基于 `/dashboard` “4.供暖单耗” 节点的对接：自动解析热/电/水单耗的本期与同期数据，缺失时回退至演示数据。
- 将单耗展示拆分为三张图（热/电/水），每张图内仅展示对应指标的本期/同期双柱并在卡片 `extra` 中标注计量单位，减轻图表拥挤感。
- 为三张单耗图的顶部标签增加左右偏移，避免本期/同期标签在柱顶发生重叠。
- “标煤消耗量对比”板块接入 `/dashboard` 的“5.标煤耗量”节点，自动解析本期/同期并绘制双柱图、顶部标签与表格；摘要卡片随“集团全口径”本期值刷新，缺失时回退演示数据。

影响范围与回滚：
- 仪表盘“边际利润简报”折线上方出现单点标签，帮助展示集团及各单位的可比煤价边际利润；如需回退，移除折线 `label` 配置即可。
- “收入分类对比（集团）”柱状图增加标签，若需回退可删除两个系列的 `label` 配置。
- “单耗”三图依赖 `/dashboard` 实际数据，若需回退可将 `useUnitConsumptionOption` 与相关计算属性恢复为单一图的静态模拟逻辑。
- 其他图表与后端接口保持不变。

验证建议：
1. 打开仪表盘，确认折线上每个单位节点均显示一位小数的边际利润值。
2. 切换业务日期或单位排序，确保标签随数据更新且未出现重叠遮挡；观察 300px 高度是否满足展示需求。
3. 检查收入柱状图顶部标签是否按一位小数显示且未与其他元素重叠。
4. 分别查看热/电/水单耗图表，确认每张图仅包含两条柱（本期/同期），卡片 `extra` 显示正确计量单位，tooltip 数值与单位匹配且无遮挡。

## 2025-11-08（数据看板 Revogrid 表格统一）

前置说明（降级留痕）：
- Serena 无法对 `.vue` 文件进行符号级写入，按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 新增组件并改写 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚可恢复上述文件。

本次动作：
- 新建 `frontend/src/daily_report_25_26/components/DashboardRevoGrid.vue`，封装 Revogrid 默认主题、列模板与只读配置，并统一引入 `@revolist/vue3-datagrid` 依赖。
- 在 `DashBoard.vue` 中将原自定义表格替换为 `<DashboardRevoGrid>`，覆盖气温、边际利润、标煤耗量、投诉 4 处表格；数据结构统一为列定义（prop/name/size）+ 行对象，便于后续接入真实接口。

影响范围与回滚：
- 数据看板表格外观与交互统一；如需回滚，移除新组件并恢复 `DashBoard.vue` 即可。
- 其他页面未引用该组件，行为不受影响。

验证建议：
1. 打开仪表盘，确认 4 个表格均渲染为 Revogrid，可滚动/复制且行高样式一致。
2. 若需扩展排序、锁列、导出等能力，可在 `DashboardRevoGrid` 增加对应配置或插件。

## 2025-11-03（仪表盘 DashBoard.vue 文件审查）

前置说明：
- 本次操作为审查 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 文件内容，无代码改动。
- 该文件是一个 Vue3 组件，用于展示仪表盘，包含本地 `Card`、`Table` 和 `EChart` 组件，以及模拟数据和样式。

本次动作：
- 审查了 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 文件，了解其结构、组件定义、数据流和样式。
- 确认该文件是一个功能完整的仪表盘组件，使用 Vue3 的 `<script setup>` 语法，并集成了 ECharts 进行数据可视化。
- 发现该组件使用了模拟数据，并预留了与后端 `dashboard/summary` 接口联调的接口。

影响范围与回滚：
- 本次操作仅为文件审查，无任何代码改动，因此无影响范围和回滚操作。

下一步建议：
- 根据项目计划，可以开始将仪表盘组件与后端 `dashboard/summary` 接口进行联调，替换模拟数据为真实数据。

