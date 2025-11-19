# 前端说明（Vue3 + Vite）

该目录使用 Vue3 + Vite 作为开发脚手架，业务模块 `daily_report_25_26` 与后端接口一一对应。

## 会话小结（2025-12-10 数据分析筛选布局优化）

- `pages/DataAnalysisView.vue` 将“单位选择（多选）”与“分析模式”并排在同一行（`form-grid--top` 最小列宽 320px），新增 `form-layout` 容器，将“指标选择（多选）”移动到下一行独占整行，保持指标面板的滚动与操作区域不受压缩。
- 样式新增 `.form-layout/.form-grid--top/.form-panel--metrics`，确保宽屏为“两列 + 一列”布局，窄屏自动折行；未改动接口调用或数据处理逻辑。

## 会话小结（2025-12-10 数据分析区间明细趋势图）

- “区间明细（逐日）”下方新增趋势图：基于逐日 timeline 同时绘制本期/同期双折线，支持 dataZoom（slider + inside）缩放；Tooltip 显示单位与同比百分比，右上角 Legend 可滚动。
- 新增指标切换器：按照当前查询结果中带有 timeline 的指标生成芯片，多选控制 series 显示；当切换单位或重新查询时自动保留可用指标，缺失时提示“请选择至少一个包含逐日数据的指标”。
- 图表组件 `TrendChart` 内置自适应 resize，配色含渐变填充（本期）+ 虚线（同期），依赖全局 `echarts` CDN 与输入的 timeline 数据，后端无需改动。

## 会话小结（2025-12-10 数据分析页面开放 Group_admin）

- 登录态中 `Group_admin` 角色现在同样会在 `permissions.page_access` 中收到 `data_analysis`，`PageSelectView.vue` 因此会为集团管理员展示“数据分析页面”入口，导航逻辑沿用已有 `normalizedKey === 'data_analysis'` 分支。
- 其他角色（ZhuChengQu_admin/Unit_admin/unit_filler/Group_viewer）依旧无法看见该卡片；如需临时排查，可切换到 `Global_admin` 或 `Group_admin` 账号登录。

## 会话小结（2025-12-10 数据分析同比颜色纠正）

- `pages/DataAnalysisView.vue` 中“分析预览”表格的 `.delta-up/.delta-down` 色彩定义调整为“同比增加=红、同比下降=绿”，与逐日区间明细中 `timelineDeltaCellTemplate` 的 `getDeltaColor` 输出保持一致，避免颜色语义反转。
- 不涉及 API 调整；若后续新增其它同比展示模块，复用同一 CSS class 即可获得正确的颜色映射。

## 会话小结（2025-12-10 数据分析默认日期读取 set_biz_date）

- `DataAnalysisView.vue` 加载 schema 前会调用 `getDashboardBizDate()`（即 `GET /projects/daily_report_25_26/dashboard/date`），将 `start_date/end_date` 默认值优先设置为 `backend_data/date.json` 的 `set_biz_date`，未命中时再退回当日。这样在 D 端未切换日期时能与仪表盘保持同一业务日期。
- `resetSelections` 及日期默认逻辑也会复用这一配置，后续若需更改默认日期，只需更新 `date.json` 或相应接口。

## 会话小结（2025-12-10 数据分析支持多单位批量查询/导出）

- 单位选择改为多选芯片，点击“生成分析结果”会对所选单位逐一调用 `/data_analysis/query` 并缓存结果，在结果区域可通过“切换单位”标签切换查看，UI 中的指标/逐日明细始终只展示当前选中的单位；单位芯片左侧显示顺序编号，勾选顺序同时决定结果与导出 Sheet 的排列顺序。
- 指标芯片同样显示勾选顺序编号，便于按选定顺序检查/导出。
- 下载 Excel 时，每个单位都会生成独立 Sheet，内容包含“汇总”“区间明细”“查询信息”三部分（按顺序垂直排布），并自动去重 Sheet 名，满足“一个单位对应一个标签”的需求。
- 如果部分单位查询失败，错误提示会标注具体单位名称，其他单位的结果仍可正常查看/导出，后端接口无需改动。

## 会话小结（2025-12-10 数据分析常量/气温逐日显示）

- 常量与气温指标现在也会出现在“区间明细（逐日）”里：常量每天显示同值；气温每天从 `calc_temperature_data` 读取本期/同期值。区间合计（total）使用逐日数据的平均值，避免常量被按天数累加。

## 会话小结（2025-12-09 AI 多轮助手 + google-genai Grounding）

- `configs/ai_test.py` 现已改用 `google-genai` 客户端并启用 Google Search Grounding，可作为前端验证“带搜索引用的 AI 报告”交互的样例；若输入包含“html报告”，模型会输出完整 HTML 并尝试在浏览器打开，方便直接查看效果。
- 该脚本的会话状态通过 `_conversation`（`google.genai.types.Content`）维护，展示了如何在发送请求时将历史轮次与工具配置一同提交，后续 DashBoard/DailyReport 若需要上线 AI 报告，可参考这一写法将前端收集的上下文附带到后端服务；为了防止模型输出“请复制粘贴”之类的提示，HTML 报告指令已强化为“只输出包含 ECharts 图表的完整 HTML”。

## 会话小结（2025-12-09 NewAPI Gemini 兼容脚本）

- `configs/ai_test_newapi.py` 再次切换到 OpenAI Chat Completions 兼容模式：`POST https://api.voct.top/v1/chat/completions`、`model=grok-4-expert`，`messages` 列表维持 system/user/assistant 历史，依旧在检测到 “html报告” 时追加提示并生成 HTML/ECharts 报告。
- API Key 顺序未变（环境变量 → backend_data/newapi_api_key.json → 默认值），因此前端若要测试其他模型，可直接改 `MODEL_NAME` 并复用同样的 CLI 逻辑。

## 会话小结（2025-12-08 数据分析指标补齐）

- 今天后端 `analysis.sql` 已同步“供暖电单耗(-研究院)”指标的视图定义，`pages/DataAnalysisView.vue` 中当你选择“集团全口径 + 调整指标 > 供暖电单耗(-研究院)”时，将直接从 `/data_analysis/query` 得到完整数据（`missing=false`），不再弹出“缺失”告警。
- 该指标仍位于“调整指标”分组，key 为 `rate_power_per_10k_m2_YanJiuYuan`，单位 `kWh/万㎡`。前端渲染逻辑保持不变：选定指标 → 发送 `metrics` 数组 → 结果表格按 `previewRows` 显示当前值/同期值/同比，若有区间查询还可在“区间明细” RevoGrid 中看到逐日曲线。
- 若需要确认后端刷新成功，可在调试面板观察 `/data_analysis/query` 返回对象内的 `source_view`（应为 `analysis_groups_daily` 或 `analysis_groups_sum`）以及 `missing=false`，再对比旧数据验证扣除研究院后的差异。

## 会话小结（2025-12-04 analysis.sql 基础数据修复）

- 后端执行 `analysis.sql` 报错 `column "sum_7d_biz" does not exist`，已移除 `yjy_power` CTE 中多余的 `sum_7d_* / sum_month_* / sum_ytd_*` 列聚合，只保留 `value_biz_date/value_peer_date`，保证集团“供暖电单耗(-研究院)”的指标能够顺利刷新。
- 前端依赖的 `/data_analysis/query`、仪表盘展示表和后续 AI 报告在读取该指标时将继续得到稳定结果，无需额外代码调整；部署或本地调试时记得重新执行 `psql -f backend/sql/analysis.sql`。
- 同期修复“供热公司”在“供暖水单耗”上无值的问题：后端 `calc_rate_water_per_10k_m2` 现在汇总一次网补水、站补水与网用水三类指标，前端无需修改即可正常查询。

## 会话小结（2025-12-04 AI 报告预研）

- AI 报告功能计划接入 `DashBoard.vue`，前端只需等待后端提供统一的 `/api/v1/projects/daily_report_25_26/ai/report` 接口；本次会话新增的 `configs/ai_test.py`（基于官方 `google-generativeai` SDK，并从 `backend_data/api_key.json` 读取密钥与模型配置）可用于提前验证 API Key 与模型表现。
- 未来在 `pages/DashBoard.vue` 中将新增“生成 AI 报告”区域，捕获仪表盘现有数据包后请求后端 AI 接口，再将文本结果渲染为卡片或者弹窗；前端无需直接暴露 API Key。
- 若后续评估中决定暂缓该功能，只需保持现有 DashBoard 结构不变，并删除 `configs/ai_test.py` 与相关文档说明即可。

## 会话小结（2025-11-30 数据分析接口模块化）

- 后端已将 `/data_analysis/schema` 与 `/data_analysis/query` 的核心逻辑抽离到 `backend/services/data_analysis.py`，前端 `DataAnalysisView.vue` 继续沿用同一接口契约，不需要额外改动即可获得统一的 schema/查询结果。
- 服务层统一处理指标分组、常量/气温/逐日明细与 Excel 导出数据，因此前端在渲染 RevoGrid、同比列以及下载文件时的字段含义保持不变；如需调试历史实现，可与后端 `_execute_data_analysis_query_legacy` 对照。
- 若后续要在数据看板或其它页面复用同一查询结果，可直接请求 `/data_analysis/query`，现在的实现已经聚合在 service 层，便于多路调用共享逻辑。

## 会话小结（2025-11-30 数据看板每日对比趋势）

- `pages/DashBoard.vue` 新增 “每日对比趋势” 卡片（位于“煤炭库存”之后，栅格宽度 12），展示供暖期内标煤耗量（本期/同期）与平均气温同轴曲线，使用全新的 `useDailyTrendOption` 生成双纵轴折线图。
- 新增 `dailyTrendSection/dailyTrendSeries` 解析函数，将后端返回的 `labels + series` 结构解耦为左轴（吨）与右轴（℃），并通过 `getDisplayLabel`/别名系统同步展示图例名称。
- 样式层追加 `.dashboard-grid__item--trend` 以占满一行，`dailyTrendExtraLabel` 在卡片副标题中提示双轴单位；如需回滚，只需移除 10 号段配置与上述组件/样式即可。

## 会话小结（2025-11-28 全厂热效率分母引入油耗）

- 后端 `sum_basic_data`/`groups` 视图更新后，`rate_overall_efficiency` 与集团同名字段在所有窗口的分母将包含 `consumption_oil`（按 1.4571 系数折算为等效标煤）；前端直接读取相同字段即可得到新口径。
- UI 若展示热效率对比，请注意新旧数据存在轻微差异，尤其是富油耗单位，必要时可在说明文字中提示“含油耗折算热量”。
- 若需要回滚旧算法，仅需重新执行上一版本 SQL 并刷新接口，前端无需代码调整。
- 数据分析页面调用的 `analysis_*` 视图也同步调整，`/data_analysis/query`、自由构建等功能读取的 `rate_overall_efficiency` 会与 dashboard/展示表一致，无需额外前端兼容。

## 会话小结（2025-11-27 集团电单耗双口径）

- 后端 `groups` 视图新增 `rate_power_per_10k_m2_YanJiuYuan` 字段（中文名“供暖电单耗(-研究院)”），其值等于集团整体现有 `rate_power_per_10k_m2` 在分子、分母上扣除 `YanJiuYuan` 数据后的结果。
- UI 若需要展示两个口径，可沿用当前表格结构增加一列或在 tooltip 中切换；字段 key 与接口一致，单位仍为 `kWh/万㎡`。
- 旧字段 `rate_power_per_10k_m2` 继续返回包含研究院的全量数据，可用于对比分析。

## 会话小结（2025-11-27 数据看板/展示表同步）

- 数据看板 `backend_data/数据结构_数据看板.json` 的“4.供暖单耗-集团汇总”已将“供暖电单耗”映射到 `供暖电单耗(-研究院)`，仪表盘直接展示新口径。
- `backend_data/数据结构_全口径展示表.json` 的 `Group_analysis_brief_report_Sheet` 现通过 `value_biz_date(rate_power_per_10k_m2_YanJiuYuan)`/`value_peer_date(rate_power_per_10k_m2_YanJiuYuan)` 读取同一字段，避免出现 0 值。
- 前端无需额外改动即可在数据看板与分析简报中看到一致的“集团电单耗（-研究院）”数据，如需保留旧口径可继续使用 `rate_power_per_10k_m2` 字段。

## 会话小结（2025-11-27 数据分析页面仅限 Global_admin）

- 后端权限矩阵仅为 `Global_admin` 保留 `data_analysis` page_access，页面 `/projects/daily_report_25_26/pages/data_analysis/data-analysis` 只有全局管理员可见，其余角色在页面入口列表中不再显示该卡片。
- 如需调试，需使用 Global_admin 账号或临时调整 `permissions.json`；前端逻辑无需改动，入口是否可见完全由后端权限接口决定。

## 会话小结（2025-11-27 集团口径站购电回滚）

- 因口径需求调整，后端已恢复 `consumption_station_purchased_power` 在集团层级中包含 `YanJiuYuan`，前端读取 `groups` 视图时会重新看到包含研究院的数据。
- 这意味着“集团全口径” `rate_power_per_10k_m2` 与其它派生指标将再度与历史报表一致，如需与主城区对比请注意主城区仍只包含 `BeiHai/XiangHai/GongRe`。
- 若要确认效果，可在调试面板中比较 `/groups` 返回的 `Group` 行与各单位数值总和：集团列应等于全部八家单位之和。

## 会话小结（2025-11-26 数据分析页面入口补丁）

- `PageSelectView.vue` 已自带 `data_analysis` 卡片逻辑，但受权限矩阵控制；后台 `permissions.json` 现将该 page_key 加入所有角色 `page_access`，登录后刷新即可看到“数据分析页面”卡片。
- 新页面仍由 `DataAnalysisView.vue` 渲染，首屏依赖 `/data_analysis/schema` 接口拉取单位/指标/日期选项；后续若扩展真实查询 API，可在该页面中追加表单提交逻辑。
- 若 `数据结构_数据分析表.json` 中配置 `显示单位` 列表，`DataAnalysisView.vue` 仅展示这些单位的单选项（其余单位仍保留在 `unit_dict` 中供派生逻辑使用）。
- `指标选择` 支持“主要指标”与“常量指标”两组：常量组展示来自 `constant_data` 表的字段，并在 UI 中以独立卡片标示；多选集合依旧共享，方便后续统一提交。

## 会话小结（2025-11-25 日分析视图拆分）

- 后端新增 `backend/sql/daily_analysis.sql`，提供 `company_daily_analysis`（公司维度）与 `gourps_daily_analysis`（主城区/集团汇总）两张“本日/同期”专用视图；自由构建页面在展示任意日期或日期区间时，可循环设置 `SET phoenix.biz_date = :target_date` 并查询上述视图，而不再调用包含月度/YTD 聚合的旧视图，显著降低资源消耗。
- `company_daily_analysis` 输出与现有 `sum_basic_data` 相同的 item 语义（含热效率、边际利润、投诉率等），字段仅保留 `value_biz_date/value_peer_date`。前端只需将新接口结果映射到既有 `valueCurrent/valuePeer` 即可。
- `gourps_daily_analysis` 已将主城区与集团全口径的派生指标（投诉率、单耗、张屯口径煤耗、全厂热效率、直接收入等）重新按日值计算；当自由构建页面需要“主城区/集团”切换时，无需再重复在前端聚合。
- 后续若为自由构建页面新增 API，建议直接调用上述视图，将日期/区间作为参数（循环查询或在 SQL 中聚合），即可与现有固定视图共享同一计算链路。
- 若前端需要进行期间累计展示，可在调用前设置 `phoenix.sum_start_date`/`phoenix.sum_end_date`，复用后端新建的 `company_sum_analysis` 与 `groups_sum_analysis` 结果，直接获取区间累计值及主城区/集团派生指标，避免在浏览器端逐日累加。

## 会话小结（2025-11-24 数据模板行内格式统一）

- 后端 `backend_data/数据结构_基本指标表.json` 现将所有 `“数据”` 数组行合并为单行，RevoGrid 模板接口返回的数据结构不变。前端解析 `rows/cells` 时无需改动，只是未来 `git diff` 更易阅读。
- 若本地有依赖旧格式的脚本（例如基于换行数计算列宽），请改用 JSON 解析而非行文本判断，以免在模板再次格式化时受到影响。
- `Coal_inventory_Sheet` 与 `GongRe_branches_detail_Sheet` 的长列表也已行内化，前端在渲染这些大表格时可获得更清晰的 diff；如需确认模板是否更新，可比较 `sheet_key` 相应的 `rows` 列表应全部为单行字符串数组。

## 会话小结（2025-11-23 仪表盘图表监听优化）

- `pages/DashBoard.vue` 中的 `DashboardEChart` 组件新增 `shallowRef` 缓存，`chart.setOption` 改为 `notMerge: false, lazyUpdate: true` 的增量更新，并取消 `deep` 级 watcher，避免每次响应式细节变化都触发整棵 option 深度遍历与整图重绘。
- 由于 `props.option` 现在以浅引用追踪，任意图表数据更新只会触发一次重绘；图表在窗口 resize 或折叠面板切换时仍可通过已有的 `handleResize` 监听正常响应。
- 若需回滚到旧实现，只需恢复 `DashboardEChart` 组件中的 `chart.setOption(props.option, true)` 与 `watch(..., { deep: true })` 逻辑。

## 会话小结（2025-11-23 仪表盘日期请求防抖）

- `pages/DashBoard.vue` 为业务日期切换新增 450ms 防抖（`scheduleDashboardLoad`）、内存缓存以及 `AbortController`，`loadDashboardData` 会取消仍在进行的旧请求，仅保留用户最后一次选择；命中缓存时直接复用上次 payload，避免重复渲染。
- `services/api.js/getDashboardData` 允许传入 `signal`，供前端在切换日期时中止先前的 fetch；其他调用方可忽略此参数，行为保持不变。
- 卸载页面时会清理计时器并 abort 悬挂的请求，防止切换路由后依旧写入已销毁的组件。

## 会话小结（2025-11-22 校验提示细化）

- `pages/DataEntryView.vue` 在校验面板中追加“当前值/参照值/当前比例”等明细。`formatViolationDetail` 会根据 `evaluateRule` 返回的 `cellValue/referenceValue/expressionValue` 拼装文案，默认提示或自定义 `message` 都会附带这些括号说明。
- `number_range`/`less_equal_than`/`column_ratio`/`expression_range` 均会把实时数值写入违规记录，便于提示面板直接展示；无须修改模板配置即可获得更详尽的错误描述。
- 任何新增的规则只要沿用现有字段（如 `min/max/min_ratio/reference_row`），前端就能自动附带数值说明；若要关闭细节，可在模板级关闭校验或在 UI 端过滤。

## 会话小结（2025-11-22 全局校验开关）

- `pages/Sheets.vue` 在列表顶部新增“全局校验开关”复选框：所有用户都能看到当前状态；仅“系统管理员”可勾选，其他角色呈现禁用态并提示“仅系统管理员可修改”。
- UI 已微调：开关控件整体下移以与页面标题对齐，同时仅在切换失败或加载中提示信息，普通用户不再看到“仅系统管理员可修改”字样；具备“系统管理员”关键词的账号即可操作。
- `pages/DataEntryView.vue` 在“业务日期”输入框左侧新增无文字复选框（`Coal_inventory_Sheet` 除外），用于联动各模板的 `校验开关`：管理员勾选时调用 `/data_entry/sheets/{sheet_key}/validation-switch` 写入 JSON，并在成功后自动重载模板；普通用户只能查看当前状态。
- 若存在 error 级校验且对应行的“解释说明”列已填写内容，则视为“带解释放行”，提交按钮不会被锁定；未填写说明的错误仍会阻止提交。
- 各模板通过 `校验说明映射` 字段指定“错误行需要在哪个指标填写解释才能放行”，当前 `backend_data/数据结构_基本指标表.json` 为所有“全厂热效率”映射到“标煤耗量”。前端在模板响应的 `validation_explanation_map` 中读取该配置。
- 勾选状态与后端 `/data_entry/validation/master-switch` GET/POST 同步，切换时先更新 UI，再落盘；写入失败会回滚到上一次值并显示错误信息。
- `services/api.js` 暴露 `getValidationMasterSwitch/setValidationMasterSwitch`，供其他页面按需重用；如需自定义 UI，可复用这两个方法。

## 会话小结（2025-11-22 数据填报校验联动）

- `GET /api/v1/projects/daily_report_25_26/data_entry/sheets/{sheet_key}/template` 现会为除 `BeiHai_co_generation_Sheet`、`BeiHai_gas_boiler_Sheet`、`Coal_inventory_Sheet` 外的大部分模板返回 `validation_enabled: true`，且新增“全厂热效率”与“耗水量”规则；渲染 `DataEntryView` 时需尊重该开关，并在 `runFullValidation` 中读取新的 rule 集合。
- “全厂热效率”规则沿用 `(value('供热量') + value('售电量') * 36) / (29.308 * value('标煤耗量'))`，前端需要把 `depends_on` 对应的行数值写入 `virtualContext` 才能计算表达式；若 `validation_rules['全厂热效率'][*].virtual` 为 true，则不要尝试在 RevoGrid 中渲染该指标。
- “耗水量”规则由 `number_range`（本期/同期需 >0）与 `column_ratio`（本期需在同期 50%~115%）组成，UI 在展示错误摘要时应保留 message 原文，以指示用户是超出区间还是出现 0 值。
- 特殊情况：`GongRe_branches_detail_Sheet` 暂无耗水量行，因此仍不会收到相关规则；`YanJiuYuan_Sheet` 只包含耗水量校验而无热效率校验，前端需要支持部分规则缺失的场景。

## 会话小结（2025-11-21 仪表盘气温标签错位）

- `pages/DashBoard.vue` 的 `useTempOption` 现会计算 push_date 对应的本期/同期温度差，当差值 ≤1℃ 且双值有效时，自动把 markPoint 标签改为左右平移（左侧对齐蓝色“本期”，右侧对齐橙色“同期”），避免前后三日窗口内的标签上下堆叠；差值大于阈值时则维持原来的上下排布。
- 新增 `buildTempLabel` 助手统一 label 样式（600 粗体、半透明白色背景、12px 间距与 padding），无论温度为正为负都能保持可读，并确保 markLine、折线本身不挡住数值。
- 如需回退至旧行为，可删除 `buildTempLabel`、`highlightLabelOverlap` 相关逻辑并恢复 markPoint 标签的默认 `position: 'top'/'bottom'`。

## 会话小结（2025-11-19 仪表盘净投诉量累计数据）

- 后端 `/dashboard` 现以 `sum_season_total_net_complaints` 提供“集团汇总净投诉量”本期/同期值，并在 `0.5卡片详细信数据表（折叠）` 中分别填充“当日/本月累计/本供暖期累计”净投诉量（全部使用 `value_biz_date/value_peer_date` 状态值），前端 `summaryFoldTable` 等组件直接沿用现有解析逻辑即可。
- summary 区第 4/8 张卡片同步改为“投诉量 / 净投诉量”双值展示：当日卡读取“当日省市平台投诉量 / 当日净投诉量”，供暖期卡读取“集团汇总供暖期省市平台投诉量 / 集团汇总净投诉量”，括号差值均与同期值相比；同时通过 `summary-card__value--paired` 将整行字号减小 3px（24px→21px），突出其他卡片主值。
- “供暖期关键指标详表”中新增的“净投诉量（件）”已配置 0 位小数、禁止千分位，和表格内其它整数指标保持一致。
- 若需要在 UI 中展示新的累计卡片，可在 `DashBoard.vue` 的 `resolveSection('9.累计卡片')` 结果中追加渲染逻辑；若暂不使用，只需保持隐藏或过滤该字段即可。

## 会话小结（2025-11-18 仪表盘平均气温 trace 撤销）

- 由于浏览器 Console 输出过多，`DashBoard.vue` 中针对“平均气温”折叠表的 `[dashboard-trace] summary-fold …` 调试日志已移除；切换业务日期时将不再自动打印本期/同期的本日值。
- 若后续需要排查，可在本地备份中临时恢复该 `console.group/table` 代码或直接比对 UI 数值即可。

## 会话小结（2025-11-17 仪表盘折叠表格）

- `pages/DashBoard.vue` 在第八个 summary 卡片后追加“供暖期关键指标详表”折叠区，默认收起，展开后渲染 4×5 表格（指标/单位/本日/本月累计/供暖期累计），并通过 `summary-card--span-full` 让其在 12 栅格中独占一行。
- 新增 `summaryFoldTable`（原 `cumulativeHeadlineTable` 升级）、`toggleCumulativeTable` 及相关样式/动画（`fold` transition、`summary-card__toggle` 等），直接复用顶部 summary 卡片与 9 号累计卡片的数据，并可优先读取 `backend_data/数据结构_数据看板.json` 中的 `0.5卡片详细信数据表（折叠）` 配置来决定指标顺序与单位；其中“本月累计”列已预留，待后端提供数值后即可填充。
- 折叠表格改为“第一列纵向合并 + 第二列标示本期/同期”的定制 `<table>`，支持双行对照展示（本期/同期），替换掉通用 `Table` 组件。
- 当前版本已优先读取 `/dashboard` 响应中的 `0.5卡片详细信数据表（折叠）` 节点：只要后端填入 `本日/本月累计/本供暖期累计` 数值，前端即可直接渲染；若该节点缺失，则折叠表不展示数据（不再回退兜底）。
- 如需回滚，可删除新增 summary 块与相关 computed/样式，或恢复 `DashBoard.vue` 至变更前的版本。

## 会话小结（2025-11-17 仪表盘配置驱动蓝图）

- `backend_data/dashboard_frontend_config.json` 现已包含两类信息：一是前端渲染所需的布局/组件绑定；二是 `data_contracts` 与 `data_mapping`，明确每个图表/卡片对应的真实视图、item_key 与公司口径。前端改造时可先读取该 JSON，按 `contract_id` + selection 直接驱动数据请求与渲染。
- 目标：把 `DashBoard.vue` 里关于组织顺序、单位、指标来源的硬编码迁移到配置层，未来仅需解析该文件即可完成页面搭建；当前代码仍未接入，待实现时请在加载 `/dashboard` 数据前同步加载该配置。
- 如需回滚，删除上述 JSON 并沿用现有硬编码逻辑即可；本文件记录其存在，方便定位来源。

## 会话小结（2025-11-15 会话持久化说明）

- 本次改动仅涉及后端新增 `backend/sql/create_auth_sessions_table.sql`，准备将登录 token 持久化到 PostgreSQL，前端代码暂无变更。
- 现有 Pinia `auth` 仓库、路由守卫与页面结构保持不变；待后端切换到数据库会话后，前端可继续沿用当前 `Authorization` 头部与刷新逻辑，无需额外适配。
- 如需在前端提示用户“会话可跨重启保留”等信息，可在登录页或顶部 `AppHeader` 中追加文案；回滚时删除上述说明即可。

## 会话小结（2025-11-15 填报提示符号优化）

- `pages/DataEntryView.vue` 中填报成功提示由“提交成功，数据已入库。”更新为“提交成功，数据已入库！”，与产品文案保持一致；倒计时与刷新逻辑未改动。

## 会话小结（2025-11-15 审批列表隐藏集团行）

- `pages/PageSelectView.vue` 的审批进度表格新增 `Set(['系统管理员','Group'])` 黑名单，默认不再展示集团本身的审批行，避免无意义的按钮。

## 会话小结（2025-11-15 集团张屯煤耗汇总数据对齐）

- 后端 `groups` 视图为 `company = 'Group'` 新增 `sum_consumption_amount_raw_coal_zhangtun`、`sum_consumption_std_coal_zhangtun` 两条记录，均携带标准的 `value_biz_date / sum_ytd_biz` 等字段，可直接呈现为新的量化卡片或表格行。
- 如需在仪表盘或数据展示页引用，请通过 `item` 判断（`sum_consumption_amount_*_zhangtun`），`item_cn` 已内置“原煤耗量汇总(张屯)/标煤耗量汇总(张屯)”中文名；其取值系 `ZhuChengQu + JinZhou + BeiFang + JinPu` 的常规煤耗与 `ZhuangHe` 张屯口径的叠加。
- 当前前端代码未读取该条目，待设计稿确认后可在 `unitCards` 或 `unitSeries` 相关配置中追加映射。若需回滚，仅需忽略或过滤上述 `item` 即可。

## 会话小结（2025-11-16 张屯指标别名渲染）

- `DashBoard.vue` 读取配置新增的 `口径别名` 映射，统一构建 `metricAliasMap` 与 `buildLabelVariants`，在 `resolveSection`、`getCumulativeMetric`、`cumulativeUnits`、投诉图表/表格以及收入表格中始终以“标煤耗量/原煤耗量”等原口径文案展示，但数据来源仍是 `sum_consumption_amount_*_zhangtun`。
- 兼容性：当后台未来继续追加其他别名，只需在 `backend_data/数据结构_数据看板.json` 的 `口径别名` 中注册即可；若要回滚，删除该配置并还原 `DashBoard.vue` 中的 alias 逻辑即可恢复旧有直读模式。
- UI 不再出现“标煤耗量汇总(张屯)”等内部口径名称，且 `resolveSection` 现支持多别名参数，确保改名后仍可定位第 5 段落。
- 2025-11-16 晚间补丁：修复 `buildLabelVariants` 在做字符串级别替换时导致的无限扩展（例如“标煤耗量”→“标煤耗量汇总(张屯)”→“标煤耗量汇总(张屯)汇总(张屯)”……），该 bug 会让浏览器内存持续膨胀直至崩溃；现在 BFS 仅在“别名/规范名”之间跳转，不再做字符串替换。

# 前端说明（Vue3 + Vite）

该目录使用 Vue3 + Vite 作为开发脚手架，业务模块 `daily_report_25_26` 与后端接口一一对应。

## 会话小结（2025-11-12 数据展示页业务日自动刷新）

- 状态：数据展示子页面（`DisplayRuntimeView.vue`）现会在用户调整业务日期后自动拉取最新只读数据，结束依赖手动点击“刷新”按钮。
- 改动：新增 `pendingAutoRefresh`、`scheduleAutoRefresh` 与 `bizDateAutoRefreshTimer`，对 `<input type="date">` 的 `bizDate` 建立 400ms 去抖监听；当首次加载尚未完成或已有请求在途时，自动刷新请求会排队至当前任务结束，避免并发压垮 `/runtime/spec/eval`。
- 安全措施：为 `loadDefaultBizDate()` 增加 `suppressNextBizDateReaction` 标记，跳过初始化时写入 `bizDate` 触发的监听，确保首屏只执行一次 `runEval()`；组件卸载时统一清理定时器。
- 影响：`projects/.../pages/data_show/sheets` 的每个子页面在切换日历日期后会自动显示“数据载入中…”并刷新到对应日期；原“刷新”按钮仍可手动重试，逻辑保持不变。
- 下一步：可视需要在顶部添加“自动刷新进行中”提示或禁用刷新按钮，进一步降低用户对请求状态的疑惑。

## 会话小结（2025-11-11 填报提交倒计时刷新）

- `pages/DataEntryView.vue` 提交成功后新增 3 秒倒计时提示，实时展示剩余秒数，同时保持提示条常显。
- 倒计时结束时调用 `reloadTemplate()` 重新拉取当前业务日期的数据（不整页刷新），确保留在此前日历选择的表格并立即看到回填结果。
- 新增 `.submit-countdown` 样式与倒计时清理逻辑；若提交失败或页面卸载会立即终止倒计时，提示恢复原状。

## 会话小结（2025-11-11 供暖收费面积口径说明）

- 后端已在 `sum_basic_data` 与 `groups` 视图中将“万平方米净投诉量”分母调整为 `amount_heating_fee_area`，前端读取的字段、单位不变。
- 联调时建议在仪表盘投诉量卡片补充“按供暖收费面积计算”等提示语，确保业务侧理解口径变更；如需改动 UI，可在数据看板页面追加说明文案。

## 会话小结（2025-11-10 仪表盘修复与PDF下载）

- 状态：修复了仪表盘“投诉量”卡片的渲染崩溃问题，并为仪表盘页面增加了“下载为PDF”的功能。
- 改动：
  - `pages/DashBoard.vue`:
    - 在 `useComplaintsOption` 函数中定义了缺失的 `phaseGap` 和 `metricGap` 变量，解决了渲染错误。
    - 在页面头部新增了“下载PDF”按钮，并为其添加了样式。
    - 实现了 `downloadPDF` 函数，该函数使用 `html2canvas` 截取仪表盘页面，并使用 `jsPDF` 将其转换为 PDF 文件进行下载。
    - PDF 文件名会根据当前业务日期动态生成。
    - 在生成截图时，下载按钮会被自动隐藏。
    - **优化**: 将截图格式从无损的 PNG 切换为 80% 质量的 JPEG，并在 `jsPDF` 中启用 `MEDIUM` 压缩，以显著减小生成的 PDF 文件大小。
    - **二次优化**: 为解决JPEG压缩导致的清晰度下降问题，将截图格式恢复为 PNG，同时将 `html2canvas` 的渲染比例提升至 2 倍，并使用 `FAST` 压缩模式，以在保证清晰度的前提下，适度控制文件大小。
  - `index.html`:
    - 添加了 `html2canvas` 和 `jsPDF` 的 CDN 链接，以支持PDF下载功能。
- 影响：用户现在可以从仪表盘页面下载包含当前视图的PDF文件，并且文件大小得到了显著优化。

## 会话小结（2025-11-10 供暖单耗柱距优化）

- 状态：优化“供暖单耗”三张卡片的柱状图排布，提升本期/同期对比的可读性。
- 改动：
  - `pages/DashBoard.vue`：在 `useUnitConsumptionOption` 中将柱状图系列的 `barGap` 调整为 `0%`，令同一单位下本期与同期柱形紧贴；同时把 `barCategoryGap` 提升至 `65%`，扩大不同单位分组间距，避免视觉拥挤。
  - “供暖单耗”与“标煤消耗量对比”卡片移除同期柱体的独立数值标签，改由“本期”标签双行展示本期/同期；“煤炭库存”卡片移除合计虚线折线但保留顶部合计标签（以零半径散点实现），“边际利润简报”标签新增轻量白底，同时清理其它标签的白色背景。
  - “投诉量分项”卡片的柱状标签改为始终显示数值（即便为 0），避免零值被判定为“无标签”。
  - 新增“供热分中心单耗明细”卡片：支持在热/电/水单耗间切换排序，条形图按从低到高展示并标注平均线，右侧表格同步列出三项单耗（字号 8px），数值统一使用千位分隔符；在桌面端条形图与表格各占 6 列。
  - 平均气温摘要添加与同期差值展示（示例：12.34（+0.80）），便于对比趋势。
- 影响：相关卡片更易对比时间段，煤炭库存视觉更简洁，其余交互保持不变。

## 会话小结（2025-11-10 投诉卡片联调）

- 仪表盘 `pages/DashBoard.vue` 投诉卡片现直接消费 `/dashboard` 第六段数据：按配置解析“当日省市平台服务投诉量”“当日净投诉量”两个指标的本期/同期 company 值，缺失时退回 0。
- 图表渲染四条分组柱（两指标 × 本期/同期），启用 `labelLayout.moveOverlap='shiftY'` 与 `axisLabel.hideOverlap=true` 保持标签可读；表格列扩展为“本期/同期”“本期净/同期净”四列并随数据自动生成单位。
- 摘要数值默认读取“集团全口径”本期投诉量，若缺失则遍历当前公司列表回退第一个有效值。
- 2025-11-10 补充：新增统一的标签判定逻辑，投诉量、单耗、标煤、收入及边际利润等图表在数值为 0 时不再显示顶部标签，仅保留非零值标注。
- 2025-11-10 补充：煤炭库存卡片改为读取 `/dashboard` 第七段返回的“厂内/港口/在途”库存数据，按公司堆叠展示（颜色为蓝/橙/绿等高对比调色板，附带折线标注合计），空数据时回退至演示数据。
- 2025-11-10 补充：煤炭库存卡片新增底部表格，按“单位 × 存储方式 + 合计”列出吨数，与堆叠柱图数据同步。
- 2025-11-10 补充：投诉量柱图为“同期”系列开启斜线 `decal` 并调成蓝绿色，同时通过 `barGap`/`barCategoryGap` 将每个指标组（本期/同期）与下一个指标组拉开距离，提升可读性。
- 2025-11-10 补充：投诉量表格字体缩小为 11px，且所有柱状图的“同期”系列统一采用亮蓝斜纹填充，快速区分本期/同期。
- 2025-11-10 补充：投诉量卡片拆分为两张图（省市平台服务投诉量、净投诉量），分别对比本期/同期，且同期柱形统一改为橙色；卡片占 8 列并保留原表格，收入卡片缩为 4 列并新增表格展示本期/同期对比。

## 会话小结（2025-11-10 仪表盘加载提示 & 填报反馈）

- `pages/DashBoard.vue`：
  - 新增 `isLoading` 计数状态，加载 `/dashboard` 数据时在卡片区前显示“数据载入中，请稍候…”提示，全部请求完成后自动隐藏。
  - Loading 提示样式写入 `.dashboard-loading-hint`，确保首屏没有数据时也有明确反馈。
- `pages/DataEntryView.vue`：
  - 引入 `isSubmitting` 状态阻止重复提交，并在模板中禁用提交按钮。
  - 新增 `submitFeedback` 轻量提示条（绿色成功、红色失败），提交完成后立即显示，约 3.2 秒后自动淡出；组件销毁时清理定时器。
  - `onSubmit` 捕获异常写入日志并将错误文案透传到提示条，成功提交后刷新“最近提交”时间戳。
- 样式：补充 `.submit-feedback*` 相关类与过渡动画，提示醒目但不遮挡表格区域。

## 会话小结（2025-11-10 页面入口信息脱敏）

- 状态：项目页面选择视图的卡片副标题统一替换为业务描述，避免直接暴露模板/配置文件路径。
- 改动：`pages/PageSelectView.vue` 新增 `PAGE_DESCRIPTION_MAP` 与 `pageDescription` 辅助函数，依据 `page_key` 输出“数据看板”“数据填报”“数据审批”“数据展示”“常量指标”“运行时调试”等中文说明，并在模板中改用该函数。
- 影响：`/projects/:projectKey/pages` 页面卡片仅呈现友好文案，隐藏 `/app/data/*.json`、`configs/*.json` 等敏感路径，同时保留既有路由跳转与 query 传参；调试入口文案提醒为内部设施。
- 下一步：后续新增页面时，请同步在映射表补充描述；若配置文件未来提供正式描述字段，可改为直接透传后端内容。

## 会话小结（2025-11-10 项目列表补充页面描述）

- 状态：项目配置 `backend_data/项目列表.json` 现含 `页面描述` 字段，接口直接返回描述文案。
- 改动：`backend/api/v1/routes.py` 在 `_normalize_pages` 中透传描述为 `page_description/description`；`PageSelectView` 的 `pageDescription` 优先使用接口字段，映射表仅兜底旧项目。
- 影响：页面副标题与接口返回保持一致，后续如需调整文案可直接编辑配置文件；未配置描述的项目仍回退至固定映射。
- 下一步：新增页面时请在配置中填好 `页面描述`；若需多语言，可考虑在配置添加 `descriptions` 子字段并在前端按语言读取。

## 会话小结（2025-11-09 仪表盘移除 Trace 选项）

- 状态：数据看板页面顶部只保留业务日期输入；调试用 Trace 复选框已下线。
- 改动：`pages/DashBoard.vue` 删除 Trace 复选框模板与 `traceEnabled` 响应式变量，其余日期监听与数据加载逻辑保持不变。
- 影响：避免生产用户误触调试开关，页面交互更简洁；如需恢复，可回滚该文件。
- 下一步：如后续需要调试功能，可单独引入仅内部可见的调试入口或通过路由守卫限制访问。

## 会话小结（2025-11-09 气温/边际利润卡片面积调整）

- 状态：气温曲线与边际利润图表在宽屏模式下平均分配一行，图例下沉后不再遮挡坐标轴文字。
- 改动：`pages/DashBoard.vue` 将气温 ECharts 高度调为 240px，并为两张卡片补充 `min-height: 320px`、移除气温卡片的满宽修饰，同时统一各图表 `legend.bottom` 与 `grid.bottom` 设置，并为 `.dashboard-table` 增加 `box-sizing: border-box`；“投诉量”卡片在宽屏下改为 span 6、移除 `dashboard-grid__item--table` 标记，三个“供暖单耗”卡片统一为 span 4，“标煤消耗量对比”“煤炭库存”统一为 span 6 且移除全幅标记；栅格行间距减半（14px），并为柱状图启用 `labelLayout.moveOverlap='shiftY'`、统一 `distance`，并开启 `axisLabel.hideOverlap=true` 以配合智能避让保持标签清晰。
- 影响：上排两张卡片更紧凑整齐，所有图例脱离坐标轴刻度；若需恢复旧高度或位置，可回滚该文件。
- 下一步：如需继续压缩排版，可评估引入图例折叠或分页方式，避免 legend 占用过多纵向空间。

## 会话小结（2025-11-09 气温/边际利润卡片面积调整）

- 状态：气温变化与边际利润卡片在宽屏模式下各占半屏，并保持统一高度，气温图表高度收紧至 240px。
- 改动：`pages/DashBoard.vue` 将气温 ECharts 高度调低，同时为两张卡片补充 `min-height: 320px` 限制，并移除气温卡片的满宽修饰，使其在宽屏下与边际利润卡片同排对齐。
- 影响：上排卡片更加紧凑，仍可完整展示气温曲线与边际利润表格；若需恢复旧高度，可回滚该文件。
- 下一步：后续若再压缩页面空间，可评估为气温表格增加折叠或分页。

## 会话小结（2025-11-09 边际利润表格回归卡片）

- 状态：“边际利润简报”卡片重新包含明细表格，并与“气温变化情况”卡片在宽屏模式下并排显示。
- 改动：`pages/DashBoard.vue` 将表格回迁至卡片内部，新增 `dashboard-table-wrapper--compact` 以保持卡片高度；同时将“气温变化情况”列宽调整为 6，与“边际利润简报”相同，实现同排对齐。
- 影响：布局较拆分方案更紧凑，表格仍随业务日期刷新且支持滚动；若需恢复独立表格卡片，可回滚该文件。
- 下一步：视需要可进一步为表格添加分页或导出功能，保持视觉高度一致时注意滚动条样式。

## 会话小结（2025-11-09 边际利润板块布局分离）

- 状态：“边际利润简报”与“收入分类对比（集团）”卡片默认同排展示，原表格拆分为独立的“边际利润明细”卡片并置于两者下方。
- 改动：`pages/DashBoard.vue` 调整网格列宽（两卡片各占 6 列），移除“边际利润简报”卡片内部表格，新增独立网格项承载表格内容。
- 影响：页面层次更清晰，图表与表格分离后阅读体验提升；如需恢复旧结构，可回滚该文件。
- 下一步：可在明细卡片补充同比/环比信息或导出入口，进一步强化分析能力。

## 会话小结（2025-11-09 数据看板布局优化）

- 状态：仪表盘页面完成摘要卡片与主体网格的视觉调整，摘要区更为紧凑，主体各组件高度保持一致，避免纵向堆叠时的遮挡感。
- 改动：`pages/DashBoard.vue` 调整摘要卡片圆角、内边距与图标尺寸，降低投影强度；为主体 `.dashboard-grid` 增加 `grid-auto-rows` 与 flex 拉伸规则，使所有卡片在 12 列布局和窄屏单列下均能自动拉伸至统一高度；修正 `z-index` 设置，消除下方组件侵入上方内容的现象。
- 影响：页面布局更整洁，摘要与各图表区域在不同分辨率下对齐；如需恢复旧版视觉，可回滚该文件。
- 下一步：可在布局稳定基础上继续接入余下数据板块，并根据实际内容微调断点下的最小高度。

## 会话小结（2025-11-09 边际利润面板接入真实数据）

- 状态：`pages/DashBoard.vue` 中“边际利润简报”面板现直接读取 `/dashboard` 返回的“2.边际利润”数据，卡片、图表与表格随业务日期自动刷新。
- 改动：新增 `marginSection`/`marginSeries` 等计算属性，将接口数据转换为单位指标列表；`useMarginOption` 改为根据真实数值绘制“直接收入/煤成本/外购热成本/水电辅材成本”堆叠与“可比煤价边际利润”折线；摘要卡片标题更新为“集团全口径可比煤价边际利润”并输出两位小数；折线节点新增标签（现保留一位小数并配气泡背景），图表高度调至 300px，移除卡片副标题以保持视觉简洁；“收入分类对比（集团）”柱状图同步为本期、同期系列增加一位小数的顶部标签；“单耗”板块解析 `/dashboard` “4.供暖单耗” 节点后拆分为热/电/水三张图，每张图展示本期/同期两组柱并在卡片 `extra` 中标注计量单位，tooltip 带单位说明；“标煤消耗量对比”读取“5.标煤耗量”节点，图表/表格/摘要实时呈现本期与同期数据且统一保留一位小数，并清理页面内“本期 vs 同期”文案。
- 影响：仪表盘不再依赖演示常量，若接口缺失某指标则以 0/空值兜底；其他尚未接入的板块仍沿用演示数据。
- 下一步：可进一步引入同期曲线或同比条形图，并结合 `marginSeries` 中保留的同期数据，扩展对比展示或下载功能。

## 会话小结（2025-11-09 集团收入明细接入）

- 状态：仪表盘“集团全口径收入明细”柱状图现在使用 `/dashboard` 的真实数据展示当期/同期收入，并按模板定义科目顺序显示。
- 改动：`DashBoard.vue` 新增 `incomeSection`/`incomeSeries` 计算属性，统一将“3.集团全口径收入明细”节点解析为分类、本期、同期数组；`useIncomeCompareOption` 直接消费该计算结果输出常规柱状图，并移除早先的断轴尝试，保持与当前 ECharts 版本兼容。
- 影响：图表随业务日期变化自动刷新，若某收入科目缺值则以 0 兜底避免绘图错误；其他板块保持原状。
- 下一步：可考虑追加数值表格或同比/环比指标，或在图表下方展示总收入与增幅信息。

## 会话小结（2025-11-08 数据看板刷新按钮移除）

- 状态：仪表盘页面头部现仅保留 Trace 调试开关与业务日期选择器，临时“刷新”按钮已删除。
- 改动：`pages/DashBoard.vue` 清理按钮 DOM、顶部“今日/业务日期”静态提示、`refreshDashboard` 占位函数及相关样式，防止出现无效交互。
- 影响：用户依旧可以勾选 Trace 或调整业务日期，界面保持原有布局；如需恢复按钮，可回滚该文件。
- 下一步：待 `/dashboard` 接口完成后，可在日期变化时触发真实刷新逻辑，并补充 Trace/日期的引导文案。

## 会话小结（2025-11-08 数据看板统一数据容器）

- 状态：`DashBoard.vue` 已建立 `dashboardData` 响应式容器，集中存放 `/dashboard` 接口返回的 `meta` 与各个板块原始数据。
- 改动：`loadDashboardData` 成功后写入 `show_date/push_date/generated_at`，并将接口返回的 section 数据（去除 `push_date`、`展示日期`）同步到 `dashboardData.sections`，为后续逐块替换静态演示数据做准备。
- 影响：页面短期仍显示演示数据，但内部状态已统一，后续图表只需读取容器即可切换为真实数据；如需回滚，移除该容器与赋值逻辑即可。
- 下一步：逐步将温度、边际利润、单耗、库存等模块的图表/表格改为引用 `dashboardData.sections`，并补充加载/错误态处理。

## 会话小结（2025-11-08 仪表盘气温模块接入）

- 状态：气温折线图、表格及顶部“平均气温”卡片已改为读取 `/dashboard` 返回的“1.逐小时气温”数据。
- 改动：在 `DashBoard.vue` 增加 `temperatureSection/temperatureSeries` 计算属性，对后端数据进行日期排序与均值计算；`tempOpt`、`temperatureTableData`、`averageTemp` 绑定该计算结果，缺失值自动兜底。
- 卡片直接读取 `push_date` 当日的 24 小时列表求算术平均（两位小数），若该日期缺失则显示“—”。
- 表格与折线图统一使用两位小数的日均结果，保持与后端一致。
- 配合后端将缺失小时返回为 `null`，前端均值计算会自动忽略缺测数据，避免平均值偏低。
- 气温折线图新增 `markLine` 标记 `push_date` 对应的日期列，突出业务日。

## 会话小结（2025-11-08 数据看板 Revogrid 表格统一）

- 状态：仪表盘内所有表格（气温、边际利润、标煤耗量、投诉）已统一切换为 Revogrid。
- 改动：新增 `components/DashboardRevoGrid.vue` 封装 Revogrid 默认样式与只读配置；`DashBoard.vue` 删除自定义 Table 组件，列/行结构改为 `prop + 对象` 的形式，便于后续接入真实接口。
- 影响：表格外观、滚动体验、复制能力保持一致，后续需要排序、锁列等能力可直接在包装组件中扩展；其它页面未引入该组件。
- 下一步：待真实数据接入后，可依据同一包装组件快速渲染各模块指标，也可在此基础上扩展导出/过滤等功能。
- 影响：切换业务日期时气温模块实时更新，若后端无数据则显示 0 基线与“—”；其他模块仍保持演示数据。
- 下一步：继续为边际利润、单耗、库存等模块接入真实数据，完成仪表盘整体联调。

## 会话小结（2025-11-08 数据看板煤炭库存聚合修正）

- 状态：后端 `/dashboard` 接口的“7.煤炭库存明细”模块现返回按单位与仓储类型聚合后的库存值，前端无需额外改动即可展示真实数据。
- 影响：DashBoard 页面收到的数据结构保持不变，但各 storage_type 数值将不再出现 0 或缺失；如需调试，可在浏览器网络面板观察最新响应。
- 下一步：结合新数据，可在前端补充单位/仓储类型的可视化（如堆叠条形图），并按需展示集团合计或趋势信息。

## 会话小结（2025-11-08 数据看板 API 初版）

- 状态：后端已提供 `GET /api/v1/projects/daily_report_25_26/dashboard`，可按 `show_date` 查询参数获取数据看板 JSON。
- 改动：`services/api.js` 新增 `getDashboardData`，`pages/DashBoard.vue` 在挂载后请求该接口并根据返回的 `push_date` 更新日历默认值；未指定 `show_date` 时由 `backend_data/date.json` 的 `set_biz_date` 决定默认日期，选择新日期会再次触发请求。
- 影响：仪表盘打开后即可展示后端给定日期；后续需将接口返回的数据映射到图表与表格。
- 下一步：完善加载/错误提示，并将返回的数据填充至 ECharts 与表格；待后端接入数据库后同步更新数据映射逻辑。

## 会话小结（2025-11-07 数据填报指标联动）

- 状态：数据填报页面读取模板中的 `linkage_dict`/“指标联动”配置后，会在 RevoGrid 中保持主子指标的输入一致，用户编辑任一联动单元格，其余联动行会即时同步。
- 改动：`pages/DataEntryView.vue` 新增 `linkageMap`、`pickLinkageDict`、`rebuildLinkageMapFromPayload` 与 `ensureLinkedRowsAligned`，在模板加载与镜像查询后重建联动映射；`handleAfterEdit` 将最新值广播到映射内的所有行，并随提交 payload 回传 `linkage_dict`。
- 影响：声明 `"指标联动"` 的表格初始展示与后续提交会自动保持各联动项的列值一致，旧数据加载后也会被前端同步为主行取值；若需回滚，可移除上述辅助函数并恢复原有 `handleAfterEdit` 逻辑。
- 下一步：可在表格 UI 中增加联动提示（如行高亮、气泡说明）并关联后端差异告警，帮助填报人员理解同步规则。

## 会话小结（2025-11-20 数据填报行内校验）

- 状态：`DataEntryView.vue` 现会读取模板响应中的 `validation_rules`（后端兼容 `校验规则`/`数据校验`），在本地构建行列级校验映射并于编辑/提交前自动执行，校验结果通过“校验提醒”卡片集中提示。
- 改动：
  - 新增 `templateValidationRaw/validationRuleMap/validationDependents/cellValidationMap` 状态与 `rebuildValidationRulesFromRows`、`runFullValidation`、`validateRow` 等辅助方法，解析 `number_range` 与 `less_equal_than` 两类规则，支持列限定、参照行及 warning/error 级别；
  - `handleAfterEdit` 在同步联动行的同时触发行内与被依赖行的校验；`onSubmit` 会在发送请求前强制执行一次全量校验并在存在 error 时阻止提交；
  - 模板顶部新增“校验提醒”面板，按照严重级别与行列定位展示消息；若仍有 warning，提交按钮可用但会保留提醒；
  - 2025-11-20：新增 `column_ratio`（本期列与 `reference_column` 的比例需落在 `min_ratio/max_ratio`）与 `expression_range`（通过 `value('行名')` 求值、可声明 `reference_column` + `min_ratio/max_ratio`、`depends_on`）两种语法，并支持 `virtual: true` + `target_label` 声明“只校验、不展示”的衍生指标，示例见“发电量”80%-120%与“全厂热效率”表达式校验。
- 影响：示例模板 `BeiHai_co_generation_Sheet` 现对“发电量/供热量/耗水量/外购电量”执行非负校验，对“其中：电厂耗水量/外购电量”执行“不得大于主项”校验，并新增发电量本期/同期80%-120%区间与全厂热效率（虚拟指标）表达式校验。如需扩展其它表，只需在模板 JSON 中追加同名规则即可生效。无规则的模板体验保持不变。
- 校验总开关：模板若返回 `validation_enabled` / `enable_validation` / `校验开关 = false`，页面会完全跳过校验（不展示提醒、不阻塞提交）；恢复为 `true` 时重新解析规则并立即失效/生效。
- 回滚：若暂不需要校验，删除模板中的 `"校验规则"` 字段即可；前端检测到 `validation_rules` 为空后将自动移除提醒面板、恢复旧的提交行为。

## 会话小结（2025-11-07 审批取消批准按钮）

- 状态：项目页审批进度卡片依据新增 `can_revoke` 权限显示“取消批准”按钮，允许在前端撤回已完成审批的单位。
- 改动：扩展 Pinia `auth` 仓库（`store/auth.js`）与 API 客户端（`services/api.js`）以支持 `revokeWorkflow`、`canRevokeUnit`，并在 `PageSelectView.vue` 的审批列表中根据状态/权限切换“批准”与“取消批准”按钮。
- 影响：Global_admin / Group_admin / ZhuChengQu_admin 登录时，若单位处于 `approved` 状态且在可见范围内，可直接将其恢复为待审批；其它角色界面不受影响。
- 下一步：如需追踪撤销记录，可在 UI 中补充撤销人和时间字段，并与后端潜在审计字段对齐。

## 会话小结（2025-11-07 数据展示页加载提示）

- 状态：`DisplayRuntimeView.vue` 在等待数据库视图数据回填时，展示“数据载入中...”占位文案，加载完成但仍无列数据时继续提示“无展示数据”。
- 改动：占位块绑定现有 `loading` 状态，使用三元表达式区分加载阶段与真实空数据，避免首屏短暂闪现“无展示数据”导致误解。
- 影响：仅影响 `projects/daily_report_25_26/pages/data_show/sheets` 页面；其它页面抢占逻辑、接口与样式保持不变，如需回滚文案可恢复该 Vue 文件的旧版本。
- 下一步：可按需求评估骨架屏或进度条组件，进一步优化长耗时查询的用户体验。

## 会话小结（2025-11-03 仪表盘 DashBoard.vue 文件审查）

- 状态：本次操作为审查 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 文件内容，无代码改动。
- 说明：该文件是一个 Vue3 组件，用于展示仪表盘，包含本地 `Card`、`Table` 和 `EChart` 组件，以及模拟数据和样式。仪表盘展示了与“生产日报”相关的各项指标和图表。
- 影响：本次操作仅为文件审查，无任何代码改动，因此无影响范围。
- 下一步：根据项目计划，可以开始将仪表盘组件与后端 `dashboard/summary` 接口进行联调，替换模拟数据为真实数据。

## 会话小结（2025-11-06 项目页移除占位入口）

- 状态：项目页列表不再显示 `placeholder` 占位卡片，确保只展示可访问的实际页面或调试入口。
- 改动：后端调整 `backend_data/项目列表.json`，前端读取 `/projects/daily_report_25_26/pages` 时已不包含该节点，页面枚举逻辑无需修改。
- 影响：`/projects/daily_report_25_26/pages` 页面与卡片列表将消失“用于占位（稍后开始构建）”项；如需恢复，可让后端重新添加对应配置。
- 下一步：若需要支持跳转至非配置文件驱动的页面，可在页面清单中增加 `type`/`route` 等字段，与当前卡片渲染逻辑配合扩展。

## 会话小结（2025-11-06 审批页面默认业务日）

- 状态：审批页 `ApprovalView.vue` 中 `regular` 模式默认读取 workflow status 的 `biz_date`（昨天），不再随 `set_biz_date` 变化。
- 改动：组件在刷新前调用 `getWorkflowStatus`，将返回的 `biz_date` 作为请求体传递给 `/runtime/spec/eval`；“自定义”模式仍沿用既有输入框。
- 影响：审批页面只受业务日驱动，展示页仍使用 `set_biz_date` 控制；如需恢复旧逻辑，可回滚该组件改动。
- 下一步：可视需要在顶部提示“当前展示日期”并引用 workflow status 的 `display_date`，帮助审批员了解展示口径。

## 会话小结（2025-11-06 仪表盘 Vue 组件重构）

- 状态：依据 `configs/仪表盘参考.vue` 的设计稿，`pages/DashBoard.vue` 已改写为 Vue3 `<script setup>` 单文件组件，保留示例数据与栅格布局，直接在前端渲染 7 个仪表盘卡片与顶部指标摘要。
- 改动：
  - 重写 `pages/DashBoard.vue`，定义局部 `Card` / `Table` 组件并通过 `EChart` 渲染 ECharts 配置，复刻气温、收入分类、单耗、煤耗、投诉量、煤炭库存等模块。
  - 统一整理静态演示数据、表格列定义与关键指标展示值，后续可替换为后端 `dashboard/summary` 接口的真实返回；内联 CSS 重现原设计的配色、阴影与栅格布局，无需依赖 Tailwind。
  - `router/index.js` 与 `PageSelectView.vue` 新增 `dashboard` 路径处理，“数据看板”卡片现可直接跳转到新版仪表盘页面。
  - `index.html` 通过 CDN 注入 `echarts.min.js`，`DashBoard.vue` 内置 `EChart` 轻量包装组件管理实例，避免额外 npm 依赖；摘要卡片与表格样式升级为渐变配色与栅格阴影风格，并自动读取 ECharts 调色板为表格边框/悬停色提供渐变。
- 影响：仪表盘页面可在 Vue 环境完整呈现设计稿，后端接口联调时仅需替换数据载入逻辑；如需回滚，恢复旧版 `DashBoard.vue` 与路由改动即可退回 React 风格占位实现。

## 会话小结（2025-11-06 售电煤炭库存权限）

- 状态：为售电公司账号开放煤炭库存表访问权限，`filterSheetsByRule` 支持在 `by_unit` 模式下读取权限文件中的显式授权白名单。
- 改动：`src/daily_report_25_26/store/auth.js` 在 `by_unit` 分支新增 `extraSheets` 集合，允许 `permissions.json` 提供的 `sheets` 列表直接放行无单位前缀的表单，并保留原有单位名称匹配。
- 影响：账号 `shoudian_filler` 登录后可在数据填报页看到 `Coal_inventory_Sheet` 卡片；其他单位仍受单位名前缀限制。如需回滚，删除白名单逻辑即可恢复单纯的单位匹配。

## 会话小结（2025-11-06 HTTP-only 访问修复）

- 状态：为避免构建后的前端请求落入 `D://.../api`，补齐 `deploy/nginx.http-only.conf` 的 `/api/` 代理，在 `ww.bash` 中加入 `VITE_API_BASE` 二次校验、日志输出与 `latest` 标签同步，并新增 `ww-certbot.yml`（固定 `locookies123@gmail.com` 与 `platform.smartview.top` 的参数）供服务器按需单独拉起 HTTP-only + Certbot 组合；需要其它邮箱或域名时，直接修改该文件的 `certbot` 命令参数即可。
- 影响：HTTP-only 部署现在可以继续沿用 `/api/v1` 相对路径；如需自定义外部域名，可显式设置 `VITE_API_BASE`（脚本会打印最终值以便确认）。
- 回滚：还原 `deploy/nginx.http-only.conf` 与 `ww.bash` 到上一个版本即可恢复既有行为。

## 会话小结（2025-11-05 仪表盘页面）

- 状态：展示页 `DisplayView.vue` 从占位按钮升级为真实仪表盘，联动后端新接口展示 7 个板块。
- 改动：
  - `services/api.js` 新增 `getDashboardSummary`，统一调用 `GET /api/v1/projects/daily_report_25_26/dashboard/summary` 并支持 `biz_date` 参数。
  - `pages/DisplayView.vue` 集成交互：业务日选择、加载状态提示，以及气温折线、指标对比、煤库存堆积柱等卡片布局。
  - 新增 `components/dashboard/LineChart.vue`、`GroupedBarChart.vue`、`StackedBarChart.vue`、`TemperaturePanel.vue`、`MetricComparisonPanel.vue`、`CoalInventoryPanel.vue` 等基础组件，使用 SVG 手绘满足图形化展示要求。
  - 交互特点：可按业务日刷新、指标下拉切换（单耗/投诉等），表格同步展示本期/同期值、差值与差率，煤炭库存卡片以堆积柱并列三段。
- 回滚方式：删除新增组件并恢复 `DisplayView.vue` 至原占位版本即可回退到旧展示状态；同时移除 `api.js#getDashboardSummary`。

## 会话小结（2025-11-04）

- 状态：`ww.bash` / `ww.ps1` 新增前端镜像构建链路，同步生成 `phoenix-web`（HTTPS 版）与 `phoenix-web-http`（HTTP-only 版）镜像并推送到 Docker Hub，可配合 `ww.yml` 或 `ww-http-only.yml` 直接部署。
- 改动：脚本允许通过 `VITE_API_BASE` 环境变量覆写打包时的接口前缀，同时记录构建时间戳；新增校验自动过滤 `file://` / Windows 本地路径，避免前端构建后指向本地磁盘。PowerShell 版本便于在纯 Windows 环境执行。
- 部署：`ww.yml` 继续使用 `deploy/Dockerfile.web` 生成的静态资源镜像，运行时只需从远端仓库拉取镜像即可；`ww-http-only.yml` 仅暴露 `80:80`，适合纯 HTTP 或将 TLS 托管给 Cloudflare 的场景。
- 下一步：如需缩短镜像体积，可在后续迭代中将 `npm ci` 缓存目录挂载到宿主或改用多阶段缓存策略。
- 数据接口：后端新增 `calc_temperature_data` 视图（按 `temperature_data` 的日期聚合日最高/最低/平均温度），后续若开放 REST 接口，可在天气数据填报或展示页面接入该聚合结果。

## 会话小结（2025-11-03）

- 状态：登录页已按“雏鸟计划”参考风格重构，采用左右分栏视觉面板 + 表单布局，沿用现有 Pinia 登录流程。
- 影响：`daily_report_25_26/pages/LoginView.vue` 新增视觉装饰与响应式样式，其余页面结构未调整；今日补充标题与描述文字居中，并微调蓝色渐变令整体色调更深。
- 下一步：若需要验证码或更多公告信息，可在当前表单面板内扩展交互，不影响已有登录链路。

## 会话小结（2025-11-02）

- 状态：本次后端仅调整运行时表达式取值规则，前端代码与路由结构未发生变化。
- 影响：展示页/审批页已依赖的指标（如“省市平台净投诉量”行的 `(本期月)/(本供暖期)` 列）会自动受益于后端修复，无需额外前端补丁。
- 下一步：待后端提供更多不可加指标白名单时，若需要在前端显式提示“按日累计值已直接返回”，可在表格列标题处补充说明。

## 会话小结（2025-10-29）

- 状态：本次会话仅为初始化与规范确认，无前端代码改动与目录调整。
- 动作：完成 Serena 项目激活与入职检查；按 AGENTS 3.9 使用 `apply_patch` 对仓库文档进行留痕。
- 下一步：待后端最小闭环接口到位后，在 `daily_report_25_26/pages/DataEntryView.vue` 路径接入行数据渲染与提交链路联调。

### 增补（2025-10-29 夜）
- 常量页查询修复：`DataEntryView.vue` 在 `templateType==='constant'` 时增加一次 `/query` 调用（无需 `biz_date`），并使用通用回填函数 `applyStandardQueryResult` 将常量 period 列与行数据写入网格，解决“constant_data 有数据但前端不显示”的问题。

## 结构快照更新（2025-10-29）

- 本次仅对后端 SQL 视图进行了职责拆分与计算指标扩展：`sum_basic_data`（仅公司明细 + 计算指标）与视图 `groups`（主城区/集团再聚合，比例/单耗类按“组内分子/常量”重算）。前端接口与页面结构不变。
- 命名对齐说明（无前端改动）：后端已统一 `sheet_name` 尾缀为 `*_Sheet`，中心英文码为 `*_Center`。前端无需感知大小写修正，依旧消费 `template/sumbit/query` 返回的字段。

## 目录结构

```
frontend/
├─ .env.development         # 本地调试环境变量（API 基础路径等）
├─ Dockerfile               # 前端容器镜像定义
├─ nginx.conf               # Nginx 转发配置
├─ package.json
├─ vite.config.js
├─ src/
│  ├─ App.vue               # 根组件
│  ├─ main.js               # 应用入口
│  ├─ router/index.js       # 全局路由：/login、/projects、/projects/:projectKey/data_entry/sheets、/projects/:projectKey/data_entry/sheets/:sheetKey
│  ├─ stores/               # Pinia store（占位）
│  └─ daily_report_25_26/
│     ├─ components/        # AppHeader、Breadcrumbs、dashboard 下的可视化组件
│     ├─ constants/         # project_key、sheet 常量
│     ├─ pages/             # LoginView、ProjectSelectView、DisplayView（仪表盘）、Sheets、DataEntryView 等
│     ├─ services/          # API 封装（api.js）
│     ├─ store/             # 业务状态（预留）
│     └─ styles/theme.css   # 统一视觉风格
├─ public/
└─ README.md
```

## 结构快照更新（2025-10-28）

- 本次变更为后端 SQL 脚本中补充二级物化视图的“唯一索引（并发刷新支持）”，前端目录与页面结构不变、接口不变。
- 若后续展示页直接消费二级物化视图结果，将在 `daily_report_25_26/pages/` 下新增展示组件并同步更新本文结构说明。
 - 本轮后端新增“运行时表达式求值”模块（`backend/services/expression_eval.py`），作为后端内部计算能力，对前端结构与接口无影响。
 - 追加说明（2025-10-28）：评估将后端“一级物化视图”改为“普通视图”不影响前端接口与目录结构；前端依然调用 `/template`、`/submit`、`/query`，与视图物化与否无关。
 - 补充说明（2025-10-28）：示例数据生成脚本已更新至 `backend/scripts/generate_daily_basic_sample.py`，前端无改动；用于快速填充 2025-10-20～2025-10-27 的演示数据。

## 启动方式

开发模式：

```bash
cd frontend
npm install
npm run dev
```

容器模式：

```bash
docker compose up -d --build
```

默认访问地址：`http://localhost:5173/`

## 路由与页面

- `/login` → `LoginView.vue`
- `/projects` → `ProjectSelectView.vue`
  - 首次进入时请求 `GET /api/v1/projects`，显示项目中文名列表并根据所选项目跳转。
- `/projects/:projectKey/data_entry/sheets` → `Sheets.vue`
  - 展示模板清单；按单位分组并以卡片呈现；点击表名进入填报页面；
  - `listSheets` 响应新增 `unit_name/sheet_name` 字段，以适配英文/中文双写。 
- `/projects/:projectKey/data_entry/sheets/:sheetKey` → `DataEntryView.vue`
  - 使用 `@revolist/vue3-datagrid` 提供的 `RevoGrid` 组件渲染表格，自带自定义元素注册；
  - 通过 `@afteredit` 事件回调同步 `gridSource`，提交阶段直接基于 `gridSource` 生成提交数据（rows-only）；
  - 模板 `columns` 会扫描列头中首次出现“计量单位”的位置，将该列及之前列标记为只读，其余列渲染本期/同期/解释说明等可编辑数据。
  - 模板响应中的所有 `*_dict` 字段会缓存至 `templateDicts.entries`，提交时逐项带回，扩展字典（中心/状态等）无需额外适配。
  - 首列在模板与历史数据完成加载后触发 `autoSizeFirstColumn()`，基于整列文本宽度动态设定列宽并再次调用 RevoGrid 自适应，支持任意单元格内容完整显示。
  - 通过 `:apply-on-close="true"` 启用 RevoGrid 内建的失焦自动保存机制，配合 `@afteredit` 更新本地状态，确保未按 Enter 的输入也能保留。

## API 交互要点

所有请求以 `/api/v1` 为前缀，`project_key` 统一为 `daily_report_25_26`。

### 变更记录（2025-10-23）
- 修复数据填报页日历联动：标准表在后端以“列头日期文本”决定每列的 `date`，现于 `pages/DataEntryView.vue` 中缓存原始列头 `baseColumns` 并在 `bizDate` 变更时重算列头与 `gridColumns` 名称，确保提交与展示使用最新日期。
- 通用查询接口（设计中）：保持现有 `services/api.js::queryData(projectKey, sheetKey, payload)` 用于“单表查询”；后续将新增“项目级聚合查询”接口，前端可在数据展示/常量页选择批量请求以减少 HTTP 次数。

### 变更记录（2025-10-28）
- 修复标准表日历切换后数据未刷新的问题：在 `DataEntryView.vue` 中新增 `applyStandardQueryResult`，统一处理 `/query` 回包的列头与 `rows` 回填；`loadTemplate` 首发查询与 `watch(bizDate)` 共同调用该方法，确保切换日期后即时刷新并保持首列自适应宽度，同时避免回包中的列头覆盖前端按昨日/同期替换后的显示。

| 接口 | 说明 |
| --- | --- |
| `GET /api/v1/projects` | 返回项目列表（`project_id/project_name`），供前端展示中文名 |
| `GET /api/v1/projects/{project_key}/data_entry/sheets` | 返回数据填报模板清单；单个条目同时包含 `单位名/表名` 以及 `unit_name/sheet_name` |
| `GET /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/template` | 返回填报模板；`columns` 先保留模板配置中的全部列（含“解释说明”等自定义列），再自动追加当前日期与上一年度同日；`rows` 为二维数组；同时附带模板定义的字典字段（如“项目字典”“单位字典”），提交时需保持字段名与内容不变 |
| `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/submit` | 占位（待实现） |
| `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query` | 占位（待实现） |

前端 `services/api.js` 会读取 `.env` 中的 `VITE_API_BASE`，默认 `http://127.0.0.1:8000`，可按部署场景调整。

## 与 @revolist/vue3-datagrid 的配合

- `DataEntryView.vue` 直接导入 `@revolist/vue3-datagrid` 默认导出的 `RevoGrid` 组件，无需手动调用 `defineCustomElements`；
  - 调试日志：已在 `DataEntryView.vue` 和 `services/api.js` 加入 rows-only 渲染链路的调试输出，包括：
    - `[data-entry/route-init]`、`[data-entry/reloadTemplate]`
    - `[revogrid/watch]`（columns/rows/gridColumns/gridSource 长度）
    - `[api/getTemplate]`、`[api/queryData/request]`、`[api/submitData/request]`
    - `[revogrid/afterEdit]`、`[data-entry/submit]`
  - 观察要点：当 `gridColumns.length > 0` 且 `gridSource.length > 0` 后，应能显示数据；若仍空白，检查模板容器的 `v-if="columns.length"` 是否及时更新。
- 模板首行使用后端返回的四列表头（项目、计量单位、今日日期、去年同日）； 
- 数据从第二行开始对应后端返回的 `rows`（二维数组），并根据列数动态渲染；
- 用户编辑后触发的 `afteredit/afterEdit` 事件统一由 `handleAfterEdit` 处理，同步更新 `gridSource` 与本地缓存，最终调用 `submitData` 接口提交。

## 接口演进记录（2025-10-19）

- 模板接口返回结构已定型：`sheet_key/sheet_name/unit_name/columns/rows`；`columns[2]`、`columns[3]` 自动写入日期，无需前端手动拼装。 
- 模板清单接口兼容中文/英文键名，便于组件直接显示。
- 若模板缺失列名或数据，后端会返回 422，前端需引导用户检查模板配置。

## 环境变量

- `VITE_API_BASE`：前端调用后端的基础地址，开发默认 `http://127.0.0.1:8000`；
- 其余变量按需扩展。

## 生产部署（Nginx + Certbot）

- 使用 `docker-compose.server.yml` 启动生产栈：包含 `web`（Nginx + 前端静态资源 + 反向代理）、`certbot`、`backend`、`db` 四个服务。
- `deploy/Dockerfile.web` 会构建 Vue 静态文件并复制到 Nginx（基础镜像 `nginx:1.27-alpine`），同时加载 `deploy/nginx.prod.conf`。
- 默认域名沿用旧项目 `platform.smartview.top`，`/api/` 反向代理到 `backend:8000`。若域名不同，请同步修改 `nginx.prod.conf` 与证书路径。
- HTTPS 证书存放于卷 `certbot_etc`、`certbot_www`；首次部署需在服务器上执行 `docker compose -f docker-compose.server.yml run --rm certbot certonly --webroot -w /var/www/certbot -d <你的域名>` 获取证书，之后常驻的 `certbot` 服务会每 12 小时自动尝试续期。
- 启动命令示例：`docker compose -f docker-compose.server.yml up -d --build`。
#
# 追加变更记录（2025-10-23）

- 修复交叉表（煤炭库存 Coal_inventory_Sheet）首屏空白：调整 `pages/DataEntryView.vue` 的 `loadTemplate()` 初始化顺序，先判定 `template_type==='crosstab'` 并调用 `setupCrosstabGrid` 初始化列与占位行，再执行镜像查询以回填 `columns/rows`，并避免后续渲染流程覆盖查询结果，确保打开页面即可显示默认日期数据。
# 追加说明：渲染流程（模板 + 镜像查询）

- 标准表（standard）
- 首屏：`getTemplate` → 占位符应用（含日期文字）→ `setupStandardGrid` 渲染 → 立刻调用 `queryData` 以 `rows` 回填网格；
- 首屏：`getTemplate` → 占位符应用（含日期文字）→ `setupStandardGrid` 渲染 → 立刻调用 `queryData` 以 `rows` 回填网格；
- 调试：在应用 query 数据时，会弹出提示框显示响应中的 `request_id`，便于你核对具体是哪一次响应被渲染（若弹窗不可用则降级为控制台 `[query/request_id]` 日志）。
 - 统一行为：standard 与 crosstab 均只在模板加载完成后触发一次首发查询；不再执行二次 `loadExisting()` 查询。
  - 日期切换：重算列头文字 → `queryData` 回填当前日期数据；
  - 关键代码：`pages/DataEntryView.vue:249`（`loadTemplate`）、`pages/DataEntryView.vue:541`（watch 处理）。

- 交叉表（crosstab，Coal_inventory_Sheet）
  - 首屏：`getTemplate` 后先确定 `template_type==='crosstab'`，调用 `setupCrosstabGrid` 初始化列与占位行 → 再 `queryData`，若返回 `columns` 则同步列头，并用 `rows` 重建 `gridSource`；
  - 日期切换：`queryData` 返回的 `columns/rows` 直接替换 `columns/gridSource`；
  - 行顺序：后端 `/query` 已按模板定义的 `(单位, 煤种)` 顺序回填，前端无需额外排序即可保持与配置文件一致。
  - 关键代码：`pages/DataEntryView.vue:249`（`loadTemplate`）、`pages/DataEntryView.vue:592`（watch 处理）。

- 接口：`services/api.js:85` `queryData(projectKey, sheetKey, payload, { config })`。
## 数据获取与回填（2025-10-25 更新）

- `/template`：提供模板元信息（`columns`、`rows`、`*_dict` 等）。
- `/query`：现已与模板结构对齐，直接返回 `columns` + `rows`，前端仅消费 `rows` 与 `columns`。
- 已移除 cells 路径：不再读取或合并 `cells`，避免覆盖 `rows`。

### 前端回填要点（2025-10-25）
- 回填顺序与要点：
  - 若存在 `q.columns`，重建/对齐 `gridColumns`（`prop: c${i}`）。
  - 将 `q.rows` 映射为 `gridSource`：`{ c0, c1, ... }`，单元格统一转字符串或空串。
  - 同步设置内部 `rows` 为 `q.rows`，保持显示与提交一致。
## 运维提示：Docker 启动失败（数据库 unhealthy）

- 现象：`phoenix_db` 在编排启动时变为 `unhealthy`，日志包含 `invalid magic number`/`could not locate a valid checkpoint record`。
- 原因：数据库挂载目录 `./db_data` 的 WAL/检查点损坏。
- 建议：先尝试 `pg_resetwal -f "$PGDATA"` 修复；若仍失败，备份并清空 `./db_data` 后重新初始化数据库，再启动前端服务。
## 调试输出策略（2025-10-25）

- 已移除所有前端调试输出：不再使用 `console.*` 与 `alert(...)`。
- 不影响功能：模板加载与 rows-only 渲染流程保持一致。
- 如需排障，建议临时在本地分支加入日志，避免进入主干。
### 2025-10-27 视图规划沟通（AI 辅助）
- 当前会话仅讨论 PostgreSQL 视图设计，前端无需改动；待后端提供视图接口后再补充数据展示方案。
### 2025-10-31 煤炭库存汇总视图对接提示
- 后端新增 `sum_coal_inventory_data`，已按最新日期产出公司与存储方式汇总行，附带 `storage_type='all_sites'`（全部地点）和 `company='sum_company'` 的合计。
- 前端若需展示煤炭库存总览，可直接请求该视图或等待 API 包装，注意根据 `storage_type_cn` 判断列分组并保持单位一致。
### 2025-10-27 审批表渲染对接（计划）
- 后端将提供“运行时表达式求值”服务，返回已替换表达式的 `columns + rows`（rows-only）结构。
- 前端保持 RevoGrid 渲染逻辑不变，仅消费后端返回的行数据；无需内置任何公式解析。
- 如需差异颜色/箭头等展示效果，可在拿到 `*_diff_rate()` 结果后按阈值做样式扩展（后续再议）。
### 2025-10-27 调试页新增（已实现）
- 新增页面：`/debug/runtime-eval` → `src/daily_report_25_26/pages/RuntimeEvalDebug.vue`
- 用途：调用后端 `POST /api/v1/projects/daily_report_25_26/runtime/spec/eval`，按模板运行时计算表达式并以表格展示结果。
- 使用：支持“零参数”请求，程序会从 `config` 指定的模板自动读取 `sheet_key` 与 `unit_id(company)`；也可手动输入覆盖。
  - 建议：`config` 使用 `configs/字典样例.json`（相对 `/app/data`）；`biz_date` 可选 `regular` 或指定日期。
 - 项目入口：已在 `backend_data/项目列表.json` 增加 `\"/debug/runtime-eval\"` 页面项，在“选择页面”界面点击“运行时表达式求值（调试）”卡片即可跳转。

### 2025-10-30 数据展示页后台修复提示
- 影响说明：后端运行时表达式 `_preprocess` 已修复嵌套 `I(...)` 参数解析，`value_*` 不再返回空值；数据展示页（含“省市平台净投诉量”）将直接收到数值，无需前端改动。
- 验证建议：若单元格仍为空，可在调试页开启 `trace=true`，核对 `safe_expr` 是否为 `value_*(\"指标\")`，并结合 `configs/10.30trace.md` 对比排查。

### 2025-10-30 展示表二（交叉表）支持
- 新增 `column_headers`/`column_groups` 元数据透传，RevoGrid 通过 `column-grouping` 渲染两行表头。
- 首两列继续显示“项目/计量单位”，其余列按“公司 × (本期日/同期日/日差异)” 分组，支持多公司比较。
- Trace 模式下可对比 `_trace` 中 `func_calls`、`used_consts`，快速定位某公司缺数据的原因。

## 会话小结（2025-11-06 HTTPS 切换）
- 变更：`ww-http-only.yml:1` 已升级为 HTTPS 部署方案，`web` 改用 `WEB_IMAGE` 并开放 `80/443`；证书卷与 `certbot` 容器保证续期。
- 影响：前端打包无需指定完整域名，默认 `/api/v1` 即可；Nginx 在容器内负责将 `/api/` 代理到 `backend:8000`。
- 构建：如需临时纯 HTTP-only，可设置环境变量 `BUILD_HTTP_ONLY=1` 并在 compose 中改回 `WEB_HTTP_IMAGE`。

### 域名/证书具体化（2025-11-06）
- 前端部署域名：platform.smartview.top；HTTPS 由 Nginx 终止，证书路径通过 compose 绑定到容器内 `/etc/letsencrypt`。
- 生产构建：维持 `VITE_API_BASE=/api/v1`（相对路径），由 Nginx `/api/` 反代后端，无需在前端写死域名。

### 会话小结（2025-11-06 ww.ps1 精简）
- 生产构建：脚本只产出 `phoenix-web:<ts>`，不再涉及 HTTP-only 或 latest。
- API 前缀：默认 `/api/v1`；如需更改，构建时设置 `VITE_API_BASE` 即可。

### 构建镜像源调整（2025-11-06）
- 前端构建所用基础镜像切换为 DaoCloud 镜像源：
  - Node: `docker.m.daocloud.io/library/node:20-alpine`
  - Nginx: `docker.m.daocloud.io/library/nginx:1.27-alpine`
- 仅影响拉取来源，前端功能与打包结果不变；需要回退时把 Dockerfile 恢复原 FROM 即可。
## 会话小结（2025-11-02 常量提交键位调整）

- 状态：后端常量写库不再使用 `center/center_cn`；幂等键改为 `(company, sheet_name, item, period)`。
- 前端影响：
  - 提交 `constant` 模板时，继续发送 `columns/rows` 与字典字段；无需包含中心字段；
  - 若模板包含“中心”列，其值仅用于后端解析 `company/company_cn`，前端无需特殊处理。
