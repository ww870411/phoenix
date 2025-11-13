# 进度记录

## 2025-12-01（数据看板缓存与前端管控）

前置说明：
- `backend/api/v1/daily_report_25_26.py` 与 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 均超过 4k 行，Serena 无法在单次操作中完成插入/替换，因此本次按指南降级使用 Codex CLI `apply_patch` 更新相关片段；如需回滚，可恢复上述文件及新增的 `backend/services/dashboard_cache.py` 的上一版本。

本次动作：
- 新增 `backend/services/dashboard_cache.py`，封装 `backend_data/dashboard_cache.json` 读写、set_biz_date 三日窗口推导、禁用/重建缓存与 key 规范化；`/dashboard` 接口在命中缓存后直接返回缓存内容，miss 时补写文件，并在响应中追加 `cache_hit/cache_disabled/cache_dates/cache_updated_at/cache_key`。
- 新增后台接口 `POST /dashboard/cache/publish`（set_biz_date 及前两日 + 默认请求批量生成）、`POST /dashboard/cache/refresh`（单日刷新）与 `DELETE /dashboard/cache`（禁用并清空），仅 `can_publish` 权限可调用；禁用状态下 `/dashboard` 只读不写，避免误触导致缓存恢复。
- `frontend/src/daily_report_25_26/services/api.js` 增加对应 API 调用；`DashBoard.vue` 顶部新增“发布缓存/刷新看板/禁用缓存”按钮与状态提示（命中缓存/实时加载/禁用、最近更新时刻、操作消息），并在成功后以 `allowCache: false` 重新加载仪表盘，确保 UI 与缓存一致。
- README 同步：后端说明新增缓存章节，前端 README 记录操作流程，方便后续运维；`configs/progress.md`（本文）亦留存操作留痕。

影响与验证：
- 手动调用 `POST /api/v1/projects/daily_report_25_26/dashboard/cache/publish` 可在 `backend_data/dashboard_cache.json` 中看到三日数据与 `__default__` 条目；随后访问 `/dashboard?show_date=<任一日期>` 时响应带 `cache_hit=true`，命中缓存即不再命中数据库视图。
- 前端登录具备发布权限的账号后，点击新增按钮即可驱动上述接口；普通账号看不到缓存操作区，避免误操作。尚未执行 `npm run build`，如需验证请本地构建后访问 Dashboard。
- 如需回滚，可删除 `dashboard_cache.py`、移除 `/dashboard` 缓存逻辑及新增接口，同时撤销前端按钮与服务 API。

## 2025-12-02（缓存窗口延长到五日）

前置说明：
- 继续沿用 2025-12-01 的缓存机制，本次仅调整窗口大小；Serena 无法直接对大文件做局部替换，因此仍通过 `apply_patch` 修改 `backend/services/dashboard_cache.py` 与 README。

本次动作：
- `default_publish_dates()` 的默认窗口从 3 改为 5（set_biz_date 及前四日）；`POST /dashboard/cache/publish` 也会同步生成 5 天的缓存切片，缓存命中范围扩大。
- 更新后端 README 中的描述，明确缓存批量生成覆盖“set_biz_date + 前四日”；前端无需改动。
- `DashBoard.vue` 的“标煤耗量与平均气温趋势图”新增窗口滑块：默认展示 `push_date` 及前 9 日共 10 日的数据，并可向前滑动至 2025-11-01；同时提供“跳至最新”按钮，配合 CSS 调整保持布局紧凑。

影响与验证：
- 调用 `POST /dashboard/cache/publish` 时应可在 `backend_data/dashboard_cache.json` 看到 5 个 ISO 日期键；`cache_dates` 元数据也会返回 5 日清单。
- 若需恢复三日窗口，可将 `default_publish_dates` 的默认 `window` 参数改回 3 并更新 README。趋势图若需恢复全量显示，可移除滑块相关状态并让 EChart 直接消费完整 `dailyTrendSeries`。

## 2025-11-30（数据分析服务抽离）

前置说明：
- Serena 无法在 4k+ 行的 `backend/api/v1/daily_report_25_26.py` 中定位 `_execute_data_analysis_query` 及相关私有函数，尝试多次 `find_symbol` 均返回空，因此降级到 Codex CLI `apply_patch` 进行重写；如需回滚，可恢复该文件在本次提交前的版本，或直接调用保留的 `_execute_data_analysis_query_legacy`。

本次动作：
- 将 `/data_analysis/schema` 与 `/data_analysis/query` 的核心实现迁移至 `backend/services/data_analysis.py`，包含模板解析、指标分组、小数位、常量/气温/逐日查询等逻辑，并补齐 `TEMPERATURE_COLUMN_MAP/TEMPERATURE_UNIT/MAX_TIMELINE_DAYS` 常量与辅助函数。
- API 层 `backend/api/v1/daily_report_25_26.py` 现在只负责 JSON 读取与 Pydantic 校验，之后调用 service；旧的 `_query_*` 函数被包装成对 service 的别名，同时新增 `_execute_data_analysis_query_legacy` 以备调试。
- `configs/progress.md`、`backend/README.md`、`frontend/README.md` 分别记录了该结构调整，便于后续参考；`py_compile` 校验通过，保证拆分后无语法问题。

影响与验证：
- 运行 `python -m py_compile backend/api/v1/daily_report_25_26.py backend/services/data_analysis.py`，确保 service 与 API 拆分后语法和依赖完整；接口入参/出参保持不变，前端页面无需调整即可继续调用。
- 如需回退，可将 API 恢复为 legacy 版本，或直接在路由中调用 `_execute_data_analysis_query_legacy`，不影响其它模块。

## 2025-11-30（数据看板每日对比趋势）

前置说明：
- Serena 无法直接在 4k+ 行的 `DashBoard.vue` 中完成结构化插入，也无法更新大型 JSON 配置，因此本次针对 Dashboard 前端与 `dashboard_expression.py` 的改动使用 `apply_patch`；如需回滚，可恢复对应文件的上一版本。

本次动作：
- `backend/services/dashboard_expression.py` 新增 `_fill_daily_trend_section`，读取配置 `10.每日对比趋势`，按供暖期起点（2025-11-01）至 `push_date` 逐日拉取 `groups` 视图的“标煤耗量汇总(张屯)”以及 `calc_temperature_data` 的平均气温，生成本期/同期曲线数据并写回 `section['本期'/'同期']`。
- 同步新增 `_normalize_metric_entries`、`_build_group_metric_cache` 等辅助函数，并在 `evaluate_dashboard` 中调用，API `/dashboard` 现会返回 `labels + series` 结构供前端绘图。
- `frontend/src/daily_report_25_26/pages/DashBoard.vue` 新增“每日对比趋势”卡片（12 格宽，位于“煤炭库存”之后），`useDailyTrendOption` 根据后端提供的 `labels`/`series` 生成双轴折线图（左轴标煤耗量、右轴平均气温），并复用别名表展示图例。
- 配套增加 `dailyTrendExtraLabel`、样式类 `.dashboard-grid__item--trend` 以及解析函数 `normalizeTrendBucket`，以便在数据缺失时 graceful degrade。

影响与验证：
- 运行 `python -m py_compile backend/services/dashboard_expression.py` 确认后端语法正确；前端尚未执行 `npm run build`，如需验证请在本地构建并刷新 `/projects/.../dashboard` 页面。
- 历史配置仍可继续扩展其他指标；若要回滚该功能，可移除 10 号段配置并删除相应 helper 调用。

## 2025-11-28（全厂热效率分母引入油耗）

前置说明（降级留痕）：
- Serena 暂不支持直接编辑 SQL/Markdown，大文件亦无法在符号粒度上操作，本次使用 `apply_patch` 更新 `backend/sql/sum_basic_data.sql`、`backend/sql/groups.sql`、`backend/README.md`、`frontend/README.md` 与本文；如需回滚，请恢复上述文件的前一版本。

本次动作：
- `calc_overall_efficiency` 以及集团 `rate_overall_efficiency` 聚合的分母统一改为 `29.308 * (consumption_std_coal + 1.4571 * consumption_oil)`，保持分子不变，使热效率计算同时考虑燃油折算热量。
- 各时间窗口（单日/同期、7 日、月度、YTD）全部按同一口径更新，防止不同窗口出现混用旧分母的情况。
- backend/frontend README 记录此次口径微调，方便后续排查报表差异。
- `backend/sql/analysis.sql` 中四张分析视图（company/group × daily/sum）的“全厂热效率”也同步使用新分母，主城区与集团聚合段落全部复用含油耗的 Nullif 表达式，保证自由构建/报表分析端与基础视图一致。

影响范围与验证：
- 执行 `\i backend/sql/sum_basic_data.sql`、`\i backend/sql/groups.sql` 重新创建视图后，查询 `SELECT company,item,value_biz_date FROM sum_basic_data WHERE item='rate_overall_efficiency'` 应能看到非零油耗的单位热效率略有下降；集团 `groups` 视图亦会出现相同变化。
- 若某单位没有 `consumption_oil` 数据，新分母自动回落为旧表达式，无需额外常量配置。
- 如需验证分母系数，可通过 `SELECT company, SUM(CASE ... consumption_oil ...) FROM daily_basic_data` 比对新增项在窗口内的累计值是否匹配预期。
- 数据分析相关接口依赖 `analysis_company_daily/analysis_groups_daily/analysis_company_sum/analysis_groups_sum`，需重新 `\i backend/sql/analysis.sql` 并复查 `SELECT * FROM analysis_groups_sum WHERE item='rate_overall_efficiency'`，结果应与 `groups` 视图保持一致。

## 2025-11-27（数据分析页面权限收紧）

前置说明（降级留痕）：
- Serena 暂无法直接写入 JSON/Markdown，本次使用 `apply_patch` 更新 `backend_data/auth/permissions.json`、`backend/README.md`、`frontend/README.md` 与本文；如需回滚，恢复对应文件即可。

本次动作：
- 仅 `Global_admin` 保留 `data_analysis` page_access，Group_admin / ZhuChengQu_admin / Unit_admin / unit_filler / Group_viewer 均移除该页面权限，确保 `http://localhost:5173/.../data_analysis` 仅全局管理员可见。
- backend/frontend README 记录相应变更，提醒如需调试须使用 Global_admin 账号或恢复权限。

影响范围与验证：
- 执行 `GET /auth/permissions`（或查看 `permissions.json`）应显示只有 `Global_admin` 拥有 `data_analysis`；使用非 Global_admin 账号登录页面，`data_analysis` 卡片不再显示。
- 如需恢复其他角色访问，需重新将 `data_analysis` 写回相应 `page_access` 列表。

## 2025-11-27（集团电单耗双口径）

前置说明（降级留痕）：
- 依据根目录 AGENTS.md，Serena 仍无法直接对 `.sql`/Markdown 编辑，本次使用 `apply_patch` 更新 `backend/sql/groups.sql`、`backend/README.md`、`frontend/README.md` 与本文；如需回滚，可恢复上述文件。

本次动作：
- 在 `groups.sql` 新增 CTE `yjy_power`、`yjy_area`，并基于 `consumption_station_purchased_power` 计算 `rate_power_per_10k_m2_YanJiuYuan`，实现集团电单耗在分子/分母双向扣除研究院数据的新口径。
- 后端 README 记录该指标的业务背景与实现方式；前端 README 提示可同时展示包含/不含研究院的两种口径。
- 维持原 `rate_power_per_10k_m2` 不变，方便对比分析。

影响范围与验证：
- 仅新增字段，不影响既有字段值。执行 `\\i backend/sql/groups.sql` 后，查询 `SELECT item, value_biz_date FROM groups WHERE item='rate_power_per_10k_m2_YanJiuYuan' LIMIT 5;` 可看到新指标；与 `rate_power_per_10k_m2` 比较，差值应等于研究院站购电/面积贡献。
- 若分母扣除后为 0，返回值将为 `NULL`；可在常量表中确认研究院 `amount_heating_fee_area` 已配置，以免出现空分母。

## 2025-11-27（分析简报绑定“-研究院”电单耗）

前置说明（降级留痕）：
- Serena 无法对 JSON 做结构化编辑，本次继续以 `apply_patch` 调整 `backend_data/数据结构_全口径展示表.json`，并同步 README 与本文；如需回滚，可恢复该文件。

本次动作：
- `Group_analysis_brief_report_Sheet` 的“供暖电单耗”行将集团列的 `value_biz_date/peer/date_diff_rate` 显式指向 `rate_power_per_10k_m2_YanJiuYuan`，其余单位仍沿用默认 `rate_power_per_10k_m2`。
- backend/frontend README 追加说明，提示看板与分析简报均已引用“供暖电单耗(-研究院)”口径，避免再出现 0 值。

影响范围与验证：
- 仅影响 `Group_analysis_brief_report_Sheet` 中“集团全口径”三列。执行自由构建/大屏查询时应能看到与数据看板一致的值；若仍为 0，请确认 `groups` 视图已重新加载并包含 `rate_power_per_10k_m2_YanJiuYuan`。
- 其他单位（主城区及各公司）继续沿用 `value_biz_date()` 的默认口径，无需额外配置。

## 2025-11-27（集团购电口径回滚）

前置说明（降级留痕）：
- 延续根目录 AGENTS.md“文本编辑使用 apply_patch”要求，Serena 仍无法直接写入 `.sql`/Markdown，本次以 `apply_patch` 方式恢复 `backend/sql/groups.sql`、并同步更新 `backend/README.md`、`frontend/README.md`、`configs/progress.md`；如需回滚至“剔除研究院”方案，参见下方同日记录重新应用即可。

本次动作：
- 移除 `backend/sql/groups.sql` 内 `base_grp` 对 `YanJiuYuan` 站购电的排除条件，集团层级重新统计全部八家单位，为后续比对历史报表保留一致数据源。
- `backend/README.md` 追加“集团口径站购电回滚”会话小结，提醒执行 `\\i backend/sql/groups.sql` 后即可让 `Group` 行恢复为完整汇总。
- `frontend/README.md` 同步说明前端重新收到包含研究院的集团数据，避免误解主城区/集团差异来源。
- 本文件记录此次撤销动作，指明与早先“剔除研究院”方案的差异。

影响范围与验证：
- 仅影响 `groups` 视图项 `consumption_station_purchased_power` 及依赖该项的集团派生指标；主城区 `base_zc` 与其它量值保持不变。
- 在数据库中执行 `SELECT company,item,value_biz_date FROM groups WHERE item='consumption_station_purchased_power' AND biz_date=:target AND company='Group';`，结果应等于 `BeiHai`~`YanJiuYuan` 全部八家相同日期的值之和。
- 若需确认回滚成功，可与“剔除研究院”版本的查询结果对比，两者差值应正好等于研究院站购电。

## 2025-11-27（数据分析查询上线）

前置说明（降级留痕）：
- 根目录 AGENTS.md 要求 Markdown/源码编辑统一使用 `apply_patch`，Serena 暂不支持对 `vue/js` 文件做结构化编辑，本次全量使用 `apply_patch` 更新 `backend/api/v1/daily_report_25_26.py`、README 及 `DataAnalysisView.vue`；如需回滚，恢复上述文件即可。

本次动作：
- `get_data_analysis_schema` 解析 `backend_data/数据结构_数据分析表.json` 新增的“调整指标”分组，并返回 `metric_group_views`，方便前端判断分组与视图的适配关系。
- 新增 `POST /projects/daily_report_25_26/data_analysis/query`，根据单位/模式设置 `SET LOCAL phoenix.biz_date/sum_*` 后查询 `company_daily_analysis` 等视图，同时兼容 `constant_data`，统一返回 `rows/missing_metrics/warnings`。
- `DataAnalysisView.vue` 接入上述查询接口，指标选择面板按视图自动禁用不兼容的分组，结果表支持单位、常量/缺失标签、环比增减色，并在查询中显示 Loading 与 warning。
- `frontend/README.md` 与 `backend/README.md` 记录接口、视图映射与前端联动方式，方便后续排障。

影响范围与验证：
- 运行 `python -m py_compile backend/api/v1/daily_report_25_26.py` 已通过语法校验；前端部分尚未执行 `npm run build`，如需验证请在 node 环境中手动运行。
- 打开 `http://localhost:5173/.../data_analysis`，选择不同单位/模式后提交，界面应提示“正在生成分析结果”，并在成功后显示后端返回的数据及 warning；若指标列表为空，请检查配置文件中的视图映射是否覆盖该单位。

## 2025-11-27（气温指标 + 常量分组兼容）

前置说明（降级留痕）：
- Serena 仍无法对 Vue/Markdown 做结构化编辑，本次继续以 `apply_patch` 更新 `backend/api/v1/daily_report_25_26.py`、`DataAnalysisView.vue`、README 与本文；如需回滚，可恢复这些文件。

本次动作：
- Schema 解析新增“气温指标字典”，后端将 `metric_group_views['temperature']` 映射到 `calc_temperature_data`，并在查询阶段按模式（单日/累计）读取该视图：单日直接取 `date = start_date` 的记录，累计对区间做 `AVG()`；单位统一返回 `℃`。
- 常量/气温分组不再依赖单位视图，前端芯片保持可选；真正不兼容的组合由后端 400 提示。
- 结果表新增“气温”标签，前端 README 记录使用方式。

影响范围与验证：
- `python -m py_compile backend/api/v1/daily_report_25_26.py` 通过；若需验证新视图，请确保数据库已执行 `backend/sql/calc_temp.sql`。
- 在数据分析页面选择“气温指标”并提交：单日模式会返回当日平均温度，累计模式返回区间平均值；常量分组可搭配任何视图使用。
- 若自定义的 `气温指标` key 未在视图列中找到，会收到明确的字段缺失提示，可据此校对配置。

## 2025-11-27（指标面板滚动 + 默认空选 + RevoGrid 逐日明细）

前置说明（降级留痕）：
- 继续使用 `apply_patch` 调整 `DataAnalysisView.vue`、前端 README 与本文；Serena 仍不支持 Vue 文件直接编辑。

本次动作：
- “指标选择”区域包裹独立滚动容器，整体高度保持在 420px 内，不会再撑开整页；“单位选择/分析模式”卡片增加 `min-height`，整体排版更均衡。
- 初始状态不再默认勾选任何指标，`重置选择` 也回到全空；需要时可用“全选”“清空”按钮快速操作。
- 结果表把“环比”文案改为“同比”，与后端返回的 `value_peer_date` 含义一致。
- 累计模式下后台返回 `timeline` 明细后，前端新增 RevoGrid 表格展示所选区间内每日的本期/同期值，同时保留顶部的汇总表；滚动和列宽自动适配。

- 指标可通过 `指标小数位` 配置各自的小数保留位（默认 2），`rate_heat_per_10k_m2`/`rate_power_per_10k_m2`/`rate_water_per_10k_m2` 默认 4 位；后端将 `decimals` 字段返给前端，RevoGrid 与汇总表都会按该精度显示。

影响范围与验证：
- 刷新数据分析页面后，可看到“单位选择/分析模式”高度一致，指标面板内部出现滚动条；滚动区域内的勾选逻辑与之前一致。
- 初次进入或执行“重置选择”时不再有默认勾选，需主动选择指标后才能查询。
- 切换到“累计模式”并勾选主要指标后，结果区会出现“区间明细（逐日）” RevoGrid，按日期展示本期/同期值，底部自动追加“总计”行；若日期跨度超过 62 天，后端会返回提示信息。
- 供暖热/电/水单耗类指标在汇总表与 RevoGrid 中均会保留 4 位小数，其他指标维持 2 位。
- 结果区新增“下载 Excel”按钮，导出的文件包含“汇总”“区间明细”“查询信息”三个工作表；使用 `xlsx` 库生成，需运行 `npm install` 安装新依赖。

## 2025-11-27（集团购电汇总剔除研究院）

前置说明（降级留痕）：
- Serena MCP 尚不支持直接对 `.sql` 及 Markdown 文本进行结构化编辑，本次以 Codex CLI `apply_patch` 分别更新 `backend/sql/groups.sql`、`configs/progress.md`、`backend/README.md` 与 `frontend/README.md`；回滚时恢复对应文件即可。

本次动作：
- `backend/sql/groups.sql` 的 `base_grp` CTE 增加 `AND NOT (company='YanJiuYuan' AND item='consumption_station_purchased_power')` 条件，并附中文注释，确保集团“供暖电单耗”及其他引用站购电的派生指标在聚合时剔除研究院数据，满足“主城区/集团全口径”双视图的一致性要求。
- `backend/README.md` 新增本次 SQL 口径调整会话小结，说明触发背景、修改位置与影响的报表项，便于查阅。
- `frontend/README.md` 同步补充“集团购电口径”说明，提示前端在消费 `groups` 视图数据时无需额外过滤。
- `configs/progress.md` 记录本次指令、降级原因与验证方式，保持全局留痕。

影响范围与验证：
- 仅影响 `groups` 视图中 item=`consumption_station_purchased_power` 的集团层级值；其它指标与主城区逻辑不受影响。
- 建议执行 `\\i backend/sql/groups.sql` 重新创建视图后，在数据库中运行 `SELECT company, item, value_biz_date FROM groups WHERE item='consumption_station_purchased_power' AND company='Group';`，确认值已不包含 `YanJiuYuan`。
- 如需比对调整前后差异，可在执行脚本前备份旧视图查询结果，两次查询相减应等于研究院当日站购电。

## 2025-11-26（数据分析 Schema 说明补档）

前置说明（降级留痕）：
- 遵循根目录 AGENTS.md “文本编辑须使用 apply_patch” 约束，本次通过 Codex CLI 的 `desktop-commander::edit_block` 更新 `backend/README.md` 与本文；如需回滚，仅需恢复相应文件版本。

本次动作：
- 在 `backend/README.md` 新增“2025-11-26 数据分析 Schema 接口”会话记录，说明 `/projects/{project_key}/data_analysis/schema` GET 的路径、查询参数、返回字段（单位/指标选项、视图映射、分析模式、默认日期）及与 `DATA_ANALYSIS_SCHEMA_PATH` 的关系，方便后端/前端联调时查阅。
- 明确 `DataAnalysisView.vue` 首屏只调用该 schema API，不直接查询数据库，后续若新增真实分析接口可直接复用 `daily_analysis.sql` 四张视图。
- 更新 `backend_data/auth/permissions.json`，将 `data_analysis` 加入所有角色的 `page_access`，用户重新登录或刷新 token 后即可在页面列表看到“数据分析页面”卡片；前端 README 已同步说明。
- 同一配置新增 `显示单位` 列表后，`get_data_analysis_schema` 会返回 `display_unit_keys/display_unit_options`，`DataAnalysisView.vue` 仅渲染这些单位芯片，其余单位仍在 `unit_dict` 中供视图映射匹配，避免页面拥挤。
- “指标选择”支持“主要指标字典/常量指标字典”双分组：后端 schema 返回 `primary_metric_dict/constant_metric_dict/metric_groups/metric_view_mapping`，前端按组渲染复选项，其中常量组注明数据源为 `constant_data`，便于后续按来源路由查询。
- `DataAnalysisView.vue` 将“日期范围”嵌入“分析模式”面板，同步展示模式与日期设置，避免额外面板占位并提升关联度。

影响范围与验证：
- 仅更新文档与进度记录，对 API 行为无改动；查阅 `backend/README.md` 顶部即可看到新增条目。
- 若访问 `/projects/{project_id}/pages` 仍无该页面，请确认权限缓存已刷新（重新登录或清理浏览器缓存）。
- 如需验证“显示单位”效果，可将列表改为少数单位并重新加载页面，单选区仅展示选中的单位，其余逻辑保持不变。
- 校验“主要/常量指标”分组：修改 JSON 中某组的字段并刷新数据分析页面，可见复选框按组分类显示，常量组带“常量”标记，并与多选操作（全选/清空）保持一致。

## 2025-11-25（日分析视图拆分）

前置说明（降级留痕）：
- Serena MCP 暂无法直接写入 `.sql` 文件，本次以 `desktop-commander::apply_patch` 新建 `backend/sql/daily_analysis.sql` 并维护两张视图（company_daily_analysis / gourps_daily_analysis）；如需回滚，只需恢复该文件即可。

本次动作：
- 复制 `sum_basic_data.sql` / `groups.sql` 的口径与计算方式，重新梳理“仅包含本日/同期”所需字段，编写 `company_daily_analysis` 视图：保留全部派生指标（热效率、边际利润、各类成本/收入、投诉率等），但仅输出 `value_biz_date`、`value_peer_date`，去掉 7 日、月度、采暖期累计窗口以降低查询成本，并允许通过 `phoenix.biz_date` GUC 注入任意日期。
- 在同一脚本中定义 `gourps_daily_analysis`（按需求保持拼写），基于 `company_daily_analysis` 汇总出“主城区”与“集团全口径”两大层级：常规指标直接求和，派生指标（净投诉量、标煤/热/电/水单耗、全厂热效率、直接收入、张屯煤耗补表等）按原逻辑重算，仅输出本期/同期数值。
- 进一步扩展 `company_sum_analysis` / `groups_sum_analysis`：通过 `phoenix.sum_start_date`、`phoenix.sum_end_date` 指定累计区间，对本期与同期日历分别求和，并沿用相同的派生指标/汇总逻辑（含张屯特例、主城区/集团层级、投诉率与效率类指标），供自由构建页面进行期间累计查询。

验证建议：
1. 在数据库连接中执行 `\i backend/sql/daily_analysis.sql` 应成功创建/替换两张视图，且不依赖额外函数；如需指定日期，可在会话前执行 `SET phoenix.biz_date = '2025-11-15';`。
2. 通过 `SELECT * FROM company_daily_analysis WHERE company='BeiHai' LIMIT 10;` 与 `SELECT * FROM gourps_daily_analysis WHERE company='Group' LIMIT 10;` 检查字段，只应包含 `value_biz_date/value_peer_date` 两列，且与旧视图在相同日期下的日值保持一致。
3. 设置 `SET phoenix.sum_start_date='2025-11-01'; SET phoenix.sum_end_date='2025-11-15';` 后查询 `company_sum_analysis`/`groups_sum_analysis`，与直接在 `daily_basic_data` 汇总或旧 `sum_*` 逻辑比对，确认累计结果以及主城区/集团派生指标与期望一致。

## 2025-11-24（数据模板行内格式统一）

前置说明（降级留痕）：
- Serena MCP 当前无法直接写入大体量 JSON 文件，本次需以 `desktop-commander::apply_patch` 批量改写 `backend_data/数据结构_基本指标表.json`；如需回滚，仅需恢复该文件至上一版本。

本次动作：
- 将 `backend_data/数据结构_基本指标表.json` 里全部 12 个 `“数据”` 数组的行项目改为单行表示（例如 `["发电量", "万kWh", "", "", ""]`），避免多行拆分导致的 diff 噪音与模板比对困难。
- 同步刷新 `Coal_inventory_Sheet` 的煤种明细、供热公司分中心明细等近 200 条行记录，确保列顺序与原模板一致，仅调整排版不更改任何业务字段。
- 在 `backend/README.md`、`frontend/README.md` 记录此次结构化调整及其影响范围，方便后续定位模板层面的差异。

验证建议：
1. 使用 `python -m json.tool backend_data/数据结构_基本指标表.json >/dev/null` 或任意 JSON linter 确认文件仍为合法 JSON，且只发生排版变化。
2. 通过 `git diff backend_data/数据结构_基本指标表.json` 应仅看到每个行项目收敛为单行，没有字段值或顺序改变；若需比较具体表，可检视任意 `“数据”` 段落确认所有逗号位置正确。

# 进度记录

# 进度记录

# 进度记录

## 2025-11-23（仪表盘 ECharts 监听优化）

前置说明（降级留痕）：
- Serena MCP 暂无法直接写入 `.vue` 文件，此次对 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 的修改改用 `desktop-commander::apply_patch`，如需回滚请还原该文件。

本次动作：
- 优化 `DashboardEChart` 子组件：新增浅引用缓存以追踪 `props.option`，移除 `deep` 级别的 watcher 并通过 `chart.setOption(..., { notMerge: false, lazyUpdate: true })` 进行增量更新，避免每次响应式细节变化都触发整棵 option 深度遍历与整图重绘，降低页面加载与交互时的 CPU 占用。

验证建议：
1. 打开 `projects/daily_report_25_26/pages/dashboard` 页面，在 DevTools Performance 中观察业务日期切换过程，`setOption` 调用次数应较以往显著减少且不再伴随长时间 scripting 栈。
2. 调整浏览器窗口尺寸或切换折叠面板，所有图表依旧能随容器 resize，数值展示与优化前保持一致。

# 进度记录

## 2025-11-23（仪表盘日期请求防抖与缓存）

前置说明（降级留痕）：
- Serena MCP 暂不支持直接写入 `.vue/.js/.md`，对 `frontend/src/daily_report_25_26/pages/DashBoard.vue`、`frontend/src/daily_report_25_26/services/api.js`、`frontend/README.md`、`backend/README.md` 的调整全部通过 `desktop-commander::apply_patch` 完成，回滚即可恢复这些文件。

本次动作：
- `DashboardEChart` 之外，再次优化仪表盘数据加载：在前端为业务日期切换新增 450ms 防抖、请求缓存与 AbortController。`loadDashboardData` 现在会优先命中内存缓存，否则自动中止上一条 `/dashboard` 请求，仅保留最后一次；`scheduleDashboardLoad` 统一调度 watch 触发，避免用户连续输入导致的请求风暴。
- `services/api.js` 的 `getDashboardData` 支持传入 `signal`，以便前端中止不再需要的请求。

验证建议：
1. 打开仪表盘页面，快速滚动日期选择器，Network 面板应只保留最后一次 `/dashboard?show_date=...` 请求，其余被标记为 `canceled`。
2. 切换到曾经加载过的日期，再次点击时应瞬间完成渲染（命中缓存），同时 loading 提示不会闪烁；刷新页面后再次切换仍会触发真实请求。

# 进度记录

## 2025-11-22（全局校验开关可视化控制）

前置说明（降级留痕）：
- Serena MCP 暂无法直接写入 `.py/.vue/.md`，因此以 `desktop-commander::apply_patch` 调整 `backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/services/api.js`、`frontend/src/daily_report_25_26/pages/Sheets.vue`、`backend/README.md`、`frontend/README.md` 与 `configs/progress.md`。若需回滚，恢复上述文件即可。

本次动作：
- 后端新增 `/projects/{project_key}/data_entry/validation/master-switch` GET/POST：GET 返回 `validation_enabled`；POST 仅允许“系统管理员”调用，写入 `backend_data/数据结构_基本指标表.json` 的 `__global_settings__`，同步更新 `校验总开关/validation_master_switch/...` 字段，并采用临时文件覆写确保可回滚。
- 前端 `Sheets.vue` 在卡片标题区增加“全局校验开关”复选框，所有角色都能看到实时状态；仅系统管理员可勾选，其他角色禁用控件。切换时调用新 API，出现错误会回退到原状态并记录日志。
- 新增 `/projects/{project_key}/data_entry/sheets/{sheet_key}/validation-switch` GET/POST，用于读取/修改各表 `校验开关` 字段；同样仅 Global_admin 有写权限。
- `DataEntryView.vue` 在“业务日期”左侧加入无文字复选框（除 `Coal_inventory_Sheet` 外），用于控件该表校验开关；管理员勾选后立即落盘并重载模板，普通用户只可查看。
- 若存在 error 级校验项，但用户在对应行（或模板中 `校验说明映射` 指定的行）的“解释说明”列填写了内容，即视为“带解释放行”，提交按钮不再锁定；未给出说明的错误仍会阻止提交。相关映射直接记录在 `backend_data/数据结构_基本指标表.json` 的 `校验说明映射` 字段。
- UI 微调：为避免控件顶端高于页面标题，开关整体下移并隐藏“仅系统管理员可修改”字样，管理员身份通过账号的 group 包含“系统管理员”即可启用，非管理员仍可查看状态但无法点击。
- `services/api.js` 新增 `getValidationMasterSwitch/setValidationMasterSwitch` 用于发起请求。

验证建议：
1. 以系统管理员登录至 `.../sheets` 页面，右上角复选框加载后应与后端文件一致；切换勾选会立刻触发保存提示，刷新后仍保持最新状态。
2. 以普通账号登录同页面，控件应处于禁用状态但实时反映当前开关；强制修改将被后端拒绝并在 UI 上看到“仅系统管理员可修改”。

## 2025-11-22（校验提示细化为实际值）

前置说明（降级留痕）：
- Serena MCP 仍无法直接写入 `.vue/.md`，因此以 `desktop-commander::apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`frontend/README.md`、`backend/README.md`、`configs/progress.md`。回滚可恢复上述文件。

本次动作：
- `DataEntryView.vue` 的校验引擎新增 `formatNumericDisplay/formatViolationDetail` 助手，将数值格式化为中文本地化文案；`evaluateRule` 为 `number_range/less_equal_than/column_ratio/expression_range` 违规记录补充 `cellValue/referenceValue/expressionValue` 元数据。
- 校验面板在默认/自定义提示语后自动拼接“（当前值…，参照值…）”等细节，示例：当耗水量 <0 会显示“当前值：-5”，比例违规则同时展示“当前值”“参照值”“当前比例”，方便定位问题单元格的真实数据。
- 由于该逻辑完全运行在前端，后端接口及 JSON 模板无需改动，仅补充 README 说明以便排查。

验证建议：
1. 在数据填报页输入负数耗水量，校验面板会显示“耗水量 … 不得小于 0（当前值：-5）”；修正为正值后提示消失。
2. 将本期耗水量调为同期的 30%，提示信息会追加“当前比例：0.30，参照值：xxx”，确认上下限区间与当前值匹配。

## 2025-11-22（数据填报校验规则批量启用）

前置说明（降级留痕）：
- 已通过 Serena MCP 完成项目激活、定位 `backend_data/数据结构_基本指标表.json` 与 README/进度文件，但当前 Serena 仍无法直接写入 JSON/Markdown，依据 AGENTS.md 3.9 降级为 `desktop-commander::apply_patch` 修改 `backend_data/数据结构_基本指标表.json`、`configs/progress.md`、`backend/README.md`、`frontend/README.md`。如需回滚，恢复上述文件即可。

本次动作：
- 将 `__global_settings__.校验总开关` 维持关闭（便于一键停用），但把除 `BeiHai_co_generation_Sheet`、`BeiHai_gas_boiler_Sheet`、`Coal_inventory_Sheet` 之外的各表 `校验开关` 统一设为 `true`，使其表级规则默认生效。
- 在 `BeiHai_water/XiangHai/JinZhou/BeiFang/JinPu/ZhuangHe` 等具备 `rate_overall_efficiency` 的模板中新增“全厂热效率” `expression_range` 规则：计算公式沿用 `(供热量 + 售电量*36)/(29.308*标煤耗量)`，本期/同期均需落在 0.5~0.95 且本期对同期的波动不超过 ±10%，全部归类为 `level: error`。
- 为 `BeiHai_water/XiangHai/GongRe/JinZhou/BeiFang/JinPu/ZhuangHe/YanJiuYuan` 等存在“耗水量”行的模板补充 `number_range + column_ratio` 组合：强制本期/同期耗水量大于 0，并限定本期处于同期 50%~115% 区间；`YanJiuYuan_Sheet` 特别包含在该范围内。
- 对 `GongRe` 模板仅落地耗水量规则（因无标煤指标无法计算热效率），`Coal_inventory_Sheet`、`BeiHai_co_generation_Sheet`、`BeiHai_gas_boiler_Sheet`、`GongRe_branches_detail_Sheet` 维持原状。

验证建议：
1. 通过 `GET /api/v1/projects/daily_report_25_26/data_entry/sheets/JinPu_Sheet/template`，确认响应包含 `validation_enabled: true` 以及新增的 `validation_rules.全厂热效率/耗水量` 条目，数值区间及 ratio 均与上述描述一致。
2. 在前端数据填报界面选择任意已开启校验的表，输入 0 或负的“耗水量”应立即抛出 error 级提示；将本期耗水量调至同期 30%/150% 亦应触发区间校验，恢复 80%~110% 后可继续提交。

## 2025-11-21（Dashboard 气温标签防重叠）

前置说明（降级留痕）：
- Serena MCP 已用于项目激活与 `DashBoard.vue` 片段检索，但当前对 `.vue/.md` 文件仍无法直接写入；依据 AGENTS.md 3.9 采用 `desktop-commander::apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`、`configs/progress.md`、`frontend/README.md`、`backend/README.md`。若需回滚，恢复上述文件即可。

本次动作：
- 气温折线图在构造 option 时新增标签重叠检测：当 push_date 对应的本期与同期温差 ≤1℃ 且双值有效时，自动将两个 markPoint 标签改为左右平移（含 offset、align 配置）并共用 `buildTempLabel` 样式，彻底避免在“前后三日”窗口中上下堆叠。
- 同步提升标签可读性：所有 markPoint 标签增加半透明背景、统一 padding 与 12px 距离，使零度附近也不会被线条遮挡。
- 文档补记：在 `frontend/README.md` 的 Dashboard 章节描述气温标签错位策略，并在 `backend/README.md` 的前端依赖说明中注明 push_date 标注行为，便于后续追踪。

验证建议：
1. 打开仪表盘切换到 push_date 日期，观察气温图同一日期下的“本期/同期”标签已分列左右且互不覆盖。
2. 将任一日期的同期温度调高至与本期差值 >1℃，刷新后应恢复默认的上下布局，以保持趋势直观。

## 2025-11-20（数据填报行内校验）

前置说明（降级留痕）：
- Serena MCP 已用于项目定位与符号检索，但当前仍无法对 `.py/.vue/.json/.md` 进行写入，依据 AGENTS.md 3.9 采用 `desktop-commander::apply_patch` 完成代码与文档改动；若需回滚，恢复本次涉及的 `backend/api/v1/daily_report_25_26.py`、`backend_data/数据结构_基本指标表.json`、`frontend/src/daily_report_25_26/pages/DataEntryView.vue`、`backend/README.md`、`frontend/README.md`、`configs/progress.md` 即可。

本次动作：
- 后端模板接口：`daily_report_25_26.py` 将 `validation_rules/校验规则/数据校验` 归类到 `DICT_KEY_GROUPS`，`GET .../template` 会随 `item_dict` 等字典一并返回校验配置。
- 模板示例：在 `BeiHai_co_generation_Sheet` 中新增 `"校验规则"`，对“发电量/供热量/耗水量/外购电量”执行非负校验，并约束“其中：电厂耗水量/外购电量”不得超过主项；同时演示 `column_ratio`（本期发电量维持在同期 80%-120% 区间）与 `expression_range`（以 `(value('供热量') + value('售电量') * 36) / (29.308 * value('标煤耗量'))` 计算“全厂热效率”并限制区间/同比）的配置，表达式规则可设置 `virtual: true` + `target_label` 隐藏衍生指标避免出现在表格中。
- 模板示例提供 `校验开关`（别名 `validation_enabled`/`enable_validation`），置为 `false` 时前后端均跳过全部校验逻辑，可用于停运或调试阶段的临时放行。
- 全局总开关：在 `backend_data/数据结构_基本指标表.json` 顶部新增 `__global_settings__`，`\"校验总开关\": false` 时所有表一律关闭校验，优先级高于各模板 `校验开关`，便于提供“一键停用”能力。
- 前端校验系统：`DataEntryView.vue` 引入 `validationRuleMap`、`runFullValidation`、`validateRow` 等逻辑，实时执行 `number_range`、`less_equal_than`、`column_ratio`、`expression_range` 规则；顶部新增“校验提醒”面板，阻止存在 error 的提交并在 warning 状态下提示放行。`校验开关` 为 false 时会隐藏提醒并允许提交。
- 文档同步：在 `backend/README.md`、`frontend/README.md` 记录字段含义、示例写法、回滚路径，并在此文件登记任务背景与验证步骤。

影响范围与回滚：
- 仅对声称 `"校验规则"` 的表生效；删除模板中的该字段即可恢复旧体验。若需彻底移除，可同时还原 README 与 `DICT_KEY_GROUPS` 中的 `validation_rules` 项。

验证建议：
1. 调用 `GET /api/v1/projects/daily_report_25_26/data_entry/sheets/BeiHai_co_generation_Sheet/template`，确认响应中含 `validation_rules` 且规则与 JSON 声明一致。
2. 在数据填报页面手动输入负的“发电量”，应立即出现“校验提醒”，提交按钮被禁用；调高值至 ≥0 后提示消失。
3. 在“其中：电厂耗水量”输入大于“耗水量”的数字，应提示“不得大于耗水量”，修改主项或子项后可恢复提交。

## 2025-11-19（Dashboard 净投诉量累计）

前置说明（降级留痕）：
- Serena MCP 已用于 `dashboard_expression.py` 的符号级改动；但对 Markdown 记录（`configs/progress.md`、`backend/README.md`、`frontend/README.md`）仍缺乏写入支持，依据 AGENTS.md 3.9 采用 `apply_patch` 更新，回滚时只需恢复上述三个文件。

本次动作：
- `_fill_cumulative_cards` 现按配置将“集团汇总净投诉量”映射到 `sum_season_total_net_complaints`，直接取 `value_biz_date/value_peer_date`，避免重复累计；其它供暖期指标仍走 `sum_ytd_*` 字段。
- `SUMMARY_PERIOD_ITEM_OVERRIDES` 新增“净投诉量”专属映射，并在 `_build_group_summary_metrics` 中支持 override mode：本日/本月/供暖期三列分别绑定“当日/本月累计/本供暖期累计净投诉量”，全部读取 `value_biz_date/value_peer_date`，杜绝二次累加。
- “0.5卡片详细信数据表（折叠）” 中“净投诉量（件）”的“本日/本月累计/本供暖期累计”分别映射到“当日净投诉量 / 本月累计净投诉量 / 本供暖期累计净投诉量”，通过 `项目字典` 的别名自动定位，无需前端硬编码。
- summary 第 4/8 张卡片同步展示“投诉量 / 净投诉量”：当日卡读取“当日省市平台投诉量 / 当日净投诉量”，供暖期卡读取“集团汇总供暖期省市平台投诉量 / 集团汇总净投诉量”，括号差值分别与同期值做差。
- 两张投诉卡片的 `summary-card__value--paired` 字体整体较默认缩小 3px（24px→21px），便于与主 summary 卡片区分；“件”字保持原文本，未再单独包裹单位标签。
- “供暖期关键指标详表”中的“净投诉量”列现以整数展示：在 `DashBoard.vue` 的 `SUMMARY_VALUE_DIGITS/OPTIONS` 中为“净投诉量”配置 0 位小数与非千分位格式。
- 在 `backend/README.md` 与 `frontend/README.md` 记录本次接口补充与前端依赖说明，便于会后追踪。

影响范围与回滚：
- 后端仅新增一个 mapping 条目，不影响其它指标；若需回滚可从 `_fill_cumulative_cards` 中移除 “集团汇总净投诉量” 映射。

验证建议：
1. 调用 `/api/v1/projects/daily_report_25_26/dashboard`，确认 `9.累计卡片.集团汇总净投诉量` 返回本期/同期值。
2. 在数据看板页面展开“供暖期关键指标详表”，查看“净投诉量（件）”列是否能展示本日/月累计/供暖期累计数据。

## 2025-11-18（Dashboard 平均气温 trace）

前置说明（降级留痕）：
- 本次工作需要在后端 Python 文件中插入调试日志。Serena 对非符号级别的 Python 片段暂无法直接注入，因此根据 AGENTS.md 3.9 采用 `desktop-commander::apply_patch` 修改 `backend/services/dashboard_expression.py`，并同步更新 `backend/README.md`、`frontend/README.md` 与本记录；如需回滚，恢复上述文件即可。

本次动作：
- 撤销 `_build_temperature_summary_metrics` 中的 `[dashboard-trace] temperature-summary` 日志输出，避免服务器端 INFO 日志过量；同时在 README 中记录 trace 已移除。
- 删除 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 针对“平均气温”折叠表的浏览器 `console.group/table` 调试逻辑，防止 Console 信息干扰业务使用；对应 README 说明亦已更新。

影响范围与回滚：
- 仅新增 INFO 级别日志输出，不影响接口返回或 SQL 逻辑；回滚可删除新增的 `logger.info` 行或提高服务日志级别到 WARNING 即可。

验证建议：
1. 运行 `/dashboard` 接口，确认服务器控制台已不再输出 `[dashboard-trace] temperature-summary`。
2. 在浏览器中切换数据看板业务日期，检查 Console 不再出现 `[dashboard-trace] summary-fold` 相关日志。

## 2025-11-17（Dashboard 顶部折叠指标表）

前置说明（降级留痕）：
- Serena MCP 仍无法对 `.vue` 模板执行符号级写入，依据 AGENTS.md 3.9 采用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 及随附样式/逻辑；如需回滚，恢复该文件并删除下述条目。

本次动作：
- 在数据看板第八个 summary 卡片之后新增“供暖期关键指标详表”折叠区，使用 12 栅格宽度；按钮切换可折叠内容，折叠体内绘制 4×5 表格（指标/单位/本期/同期/差值）。
- 新增 `cumulativeHeadlineTable`（后续升级为 `summaryFoldTable`）计算逻辑、`toggleCumulativeTable` 控制状态以及相关样式（`summary-card--span-full`、`summary-card__toggle`、`fold` transition），复用既有累计 headline 数据自动填充四行数据。
- 按业务方要求将折叠表格的三项数据列更新为“本日 / 本月累计 / 供暖期累计”，并同步改写数据来源：本日列取自顶部 summary 卡片的即时值，供暖期列沿用 9 号累计卡片数据，月累计暂留空位以待后端提供。
- 将折叠表格升级为“指标占两行、第一列纵向合并、第二列标示本期/同期”的结构：使用新 computed `summaryFoldTable` 和专用 `<table>` 模板替代通用 `Table` 组件，配套 `summary-fold-table` 样式，支持行合并及“本期/同期”双行对照。
- 进一步优化列宽与对齐：通过 `<colgroup>` 固定“指标/口径/数值”列宽，增加单位展示与右对齐数字，让折叠表在不同屏幕下保持自然排版。
- 折叠表数据源接入配置项 `0.5卡片详细信数据表（折叠）`：若配置存在则按其声明的指标顺序与单位解析，否则回落到默认顺序；指标映射逻辑会依据配置中的“标煤耗量汇总(张屯)”等别名自动匹配现有 headline 数据。
- 后端 `evaluate_dashboard` 现对 `0.5卡片` 节点执行 `_fill_summary_fold_section`：直接从 `calc_temperature_data` 与 `groups` 视图写入“本日/本月累计/供暖期累计”数值，同时将温度月度/供暖期平均改为基于 `calc_temperature_data` 聚合，避免再手动平均逐小时数据。

影响范围与回滚：
- 仅前端展示层改动，对后端接口无影响；如需回滚，移除新增模板块、相关 computed 与样式，或直接恢复 `DashBoard.vue`。

验证建议：
1. 打开数据看板顶部 summary 区域，确认新增卡片默认折叠，点击“展开”后展示 4×5 表格且动画平滑。
2. 切换业务日期，折叠表格数据应与供暖期 headline 一致（本期/同期/差值随日期联动）。
3. 在移动端或窄屏下验证 summary 卡片排布，确认为 span-full 卡片独占一行但仍保持折叠逻辑。

## 2025-11-17（前端配置驱动蓝图文件）

前置说明（降级留痕）：
- Serena 符号级工具暂不支持在 `backend_data` 下创建非代码类 JSON，因此依照 AGENTS.md 3.9 使用 `desktop-commander::read_file` + `apply_patch` 新增 `backend_data/dashboard_frontend_config.json` 并在本文件登记；如需回滚，删除该文件并恢复本记录即可。

本次动作：
- 新增 `backend_data/dashboard_frontend_config.json`，定义仪表盘前端所需的完整配置：包含数据源描述、全局组织顺序/单位、顶部摘要卡映射以及 1~9 号 section 的组件布局与数据绑定（图表、表格、排序规则等），使前端能够在后续改造中仅凭读取该文件即可渲染现有数据看板。
- 追加 `data_contracts` 节点与 `data_mapping`/`data_mappings` 配置，逐条声明各组件所依赖的真实视图/表（如 `sum_basic_data`、`groups`、`temperature_data`、`coal_inventory_data`、`calc_temperature_data`）、item_key、公司口径以及可用窗口，确保“去哪取数、依据是什么”在同一份配置内可追溯。

影响范围与回滚：
- 目前仅新增配置文件，对现有运行逻辑无直接影响；若后续试点配置驱动出现问题，可先移除该文件并恢复前端硬编码逻辑。

验证建议：
1. 打开 `backend_data/dashboard_frontend_config.json`，确认 `data_sources / sections / widgets` 等节点与现有页面组件一致。
2. 以脚本加载该 JSON，验证能解析出 summary cards、chart/table 绑定信息，为后续前端改造提供依据。

## 2025-11-16（张屯煤耗口径别名 + DashBoard 渲染）

前置说明（降级留痕）：
- Serena 仍无法直接写入 SQL/前端文件，依照 AGENTS.md 3.9 要求，本次通过 `desktop-commander::read_file` + `apply_patch` 修改 `backend_data/数据结构_数据看板.json`、`frontend/src/daily_report_25_26/pages/DashBoard.vue` 以及相关 README/本文件；如需回滚，恢复上述文件至变更前版本即可。

本次动作：
- 在数据看板配置新增 `口径别名` 映射（`标煤耗量汇总(张屯)`→`标煤耗量`、`原煤耗量汇总(张屯)`→`原煤耗量`），用于指明张屯汇总口径的展示名称。
- `DashBoard.vue` 补充 `metricAliasMap/buildLabelVariants` 辅助，`resolveSection` 支持多别名，`cumulativeUnits`、`getCumulativeMetric`、投诉图表/表格与收入/标煤表格均按别名展示，同时保持底层仍读取 `sum_consumption_amount_*_zhangtun` 数据。
- 同日补丁：`buildLabelVariants` 过去会在别名包含原名时无限执行字符串替换（`标煤耗量` → `标煤耗量汇总(张屯)` → `标煤耗量汇总(张屯)汇总(张屯)` ...），导致浏览器堆爆；现已改为仅在“别名/规范名”节点之间 BFS，不再做 substring 替换，从而消除内存泄漏。
- 后端 `dashboard_expression._fill_simple_metric` 现允许每家公司在配置里写表达式（例如“标煤耗量汇总(张屯)”），若留空则回落到根指标；`_fill_cumulative_cards` 的“集团汇总供暖期标煤耗量”改读 `sum_consumption_std_coal_zhangtun`，确保 5/9 号段与张屯汇总保持一致。

影响范围与回滚：
- 影响仪表盘所有读取张屯煤耗指标的卡片/表格；若要回滚，删除 `口径别名` 节点并恢复 `DashBoard.vue` 中 alias 相关逻辑即可。

验证建议：
1. 打开仪表盘，确认“标煤消耗量对比”“供暖期标煤耗量”等位置仍显示“标煤耗量”文案，但与数据库中 `sum_consumption_amount_std_coal_zhangtun` 数据一致。
2. 手动修改 `口径别名` 中的映射条目，刷新后验证 `DashBoard.vue` 能自动采用新的展示文案；删除该节点则回退到原始名称。
3. 在 `backend/sql` 刷新视图后请求 `/dashboard`，确认 5 号段“集团汇总”以及 9 号段累计卡片的数据都来源于新的 `sum_consumption_std_coal_zhangtun`；如需回滚，撤销上述配置与 `_fill_simple_metric` 的表达式支持即可。

## 2025-11-15（集团张屯煤耗汇总视图增强）

前置说明（降级留痕）：
- Serena MCP 仍无法对 SQL/Markdown 执行符号级写入，按 AGENTS.md 3.9 要求本次降级使用 `desktop-commander::read_file` + `apply_patch` 修改 `backend/sql/groups.sql`、前后端 README 及本文件；如需回滚，恢复上述文件即可。

本次动作：
- `groups` 视图新增 `group_sum_raw_zhangtun`、`group_sum_std_zhangtun` 聚合，追加 `sum_consumption_amount_raw_coal_zhangtun` 与 `sum_consumption_amount_std_coal_zhangtun` 两条 `company=Group` 指标，按主城区（BeiHai/XiangHai/GongRe）、JinZhou、BeiFang、JinPu 的常规煤耗叠加 `ZhuangHe` 张屯口径求和值覆盖全部时间窗口。
- `backend/README.md`、`frontend/README.md` 记录新指标含义、取值来源与前端接入提示，保持进度对齐。

影响范围与回滚：
- 影响 `groups` 视图消费者（仪表盘/BI）；若需回滚删除张屯汇总，只需移除新增 CTE 与 `UNION ALL` 片段，并同步清理 README 说明。

验证建议：
1. 在数据库执行 `SELECT * FROM groups WHERE company='Group' AND item LIKE 'sum_consumption_amount_%_zhangtun';`，确认返回两行且 `value_biz_date` 等字段与期望的公司组合一致。
2. 对比 `sum_ytd_biz` 是否等于（主城区 + JinZhou + BeiFang + JinPu 的 `consumption_amount_*`）+（ZhuangHe 的 `*_zhangtun`）。

## 2025-11-14（登录状态记忆选项 + 数据库存储）

前置说明（降级留痕）：
- Serena 仍无法对 Python/JS/Markdown 执行符号级写入，本次继续降级使用 `desktop-commander::read_file` + `apply_patch` 修改 `backend/services/auth_manager.py`、`backend/api/v1/auth.py`、`backend/schemas/auth.py`、`frontend/src/daily_report_25_26/store/auth.js`、`frontend/.../pages/LoginView.vue`、前后端 README 以及本文件；如需回滚，恢复上述文件即可。

本次动作：
- 后端 `AuthManager` 支持“记住登录状态”：`/auth/login` 接收 `remember_me`，勾选后会话写入 `auth_sessions` 表（90 天滚动有效），`require_session` 可在服务重启后从数据库恢复；未勾选仍采用内存会话，不写库。
- 新增 `_persist_session/_load_persistent_session/_touch_persistent_session` 等逻辑，自动维护 `expires_at` 与 `last_accessed`，并在 `logout`/过期时清理数据库记录。
- `LoginRequest`/`LoginView`/Pinia `auth` store 增加复选框与参数传递；前端持久化策略改为“localStorage（记住）/sessionStorage（临时）”双通道，刷新或重开浏览器可按选项恢复登录。
- README（前/后端）补充“记住登录”说明，记录 `auth_sessions` 表依赖与回滚策略。

影响范围与回滚：
- 仅影响账号体系与登录页面；回滚可将相关文件恢复至 2025-11-13 版本，并删除新增字段/SQL 调用。

验证建议：
1. 不勾选登录，刷新浏览器后需重新登录，数据库 `auth_sessions` 应保持空表。
2. 勾选登录，确认 `auth_sessions` 有对应记录；重启后端服务、只携带 Bearer Token 调用 `/auth/me` 仍返回 200。
3. 在登录状态下点击退出或接口 401 过期，`auth_sessions` 与 local/sessionStorage 均应清空。

## 2025-11-14（登录状态稳定性提升）

前置说明（降级留痕）：
- Serena MCP 目前仍无法对 Python/JS/Markdown 执行符号级写入，本次依 AGENTS.md 3.9 规定降级使用 `desktop-commander::read_file` + `apply_patch` 修改 `backend/services/auth_manager.py`、`backend/api/v1/auth.py`、前后端 README、Pinia `auth` store 以及本文件；如需回滚，恢复上述文件至变更前版本即可。

本次动作：
- 后端 `AuthManager` 去除固定 24 小时会话 TTL，改为默认无限期（仅手动退出或清理会失效），并允许同一账号多端并发登录，避免因单点登录冲突导致的掉线；`/auth/login` 在 `expires_in` 字段返回 `-1` 代表“长期有效”。
- `require_session`/_cleanup 逻辑在关闭 TTL 时跳过过期校验与清理，彻底消除后台定时回收造成的“登录状态失效”提示。
- 前端 `auth` 仓库存储策略改为 localStorage 优先、sessionStorage 兜底，刷新或重新打开浏览器后可自动恢复登录信息；README 记录新的持久化与稳定性策略。
- `backend/README.md` 更新“登录与权限”段描述，明确当前版本默认不再限制会话时长。

影响范围与回滚：
- 影响 `/auth/login|logout|me` 及依赖 Authorization 头的所有页面；若需恢复时间限制，可重新设置 `SESSION_TTL_SECONDS` 并开启 `ALLOW_CONCURRENT_SESSIONS = False`。

验证建议：
1. 登录后长时间保持闲置（含刷新/新开页面），确认调用 `/auth/me` 仍返回 200，router 不再跳回登录页。
2. 同一账号在不同浏览器同时登录，互不影响且 `me` 接口仍可获取权限。
3. 手动调用 `/auth/logout` 或点击退出，确认 token 与 localStorage 条目清除，页面重定向至 `/login`。

## 2025-11-13（数据看板业务日切换修复）

前置说明（降级留痕）：
- Serena MCP 当前仍无法对 `.vue`/`.md` 文件执行符号级写入，本次依 AGENTS.md 3.9 要求降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`、前后端 README 以及本文件；回滚可恢复上述文件至变更前版本。

本次动作：
- `loadDashboardData` 仅在未显式指定 `showDate` 且本地 `bizDateInput` 为空时，才依据接口返回的 `push_date` 重写输入框，避免用户手动选择业务日期后又被服务器默认值覆盖，导致“切换日期无效”。
- 若接口未返回 `push_date` 但输入框为空，仍回落到默认业务日（东八区前一日），确保初次加载有可视日期。
- `frontend/src/daily_report_25_26/README.md` 增补“业务日同步策略（2025-11-13）”章节，描述前端如何决定是否覆盖日期；`backend/README.md` 记录本次交互纯前端处理，后端 `/dashboard` API 无需调整。
- `configs/progress.md` 写入本记录，方便审计。

影响范围与回滚：
- 仅影响仪表盘页面的业务日期输入及其触发 `/dashboard?show_date=YYYY-MM-DD` 的行为；如需回滚，恢复 `DashBoard.vue` 中 `payload.push_date` 赋值逻辑即可。

验证建议：
1. 打开仪表盘默认加载一遍，确认自动填入的是推送日（或默认业务日），并显示最新数据。
2. 手动选择任意历史日期，确认输入框维持用户选择值，且网络请求 `show_date` 参数与之匹配，数据渲染为对应日期。
3. 清空输入或将日期改回默认值时，仍可重新回落到服务器推送日，watcher 不会陷入循环请求。

## 2025-11-12（数据展示页业务日自动刷新）

前置说明（降级留痕）：
- Serena MCP 暂未开放本仓库 `.vue`/`.md` 文件的符号级写入能力，本次依照 AGENTS.md 3.9 规定，降级使用 `desktop-commander::read_file` + `apply_patch` 编辑 `frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue` 与前后端 README；如需回滚，可恢复上述文件至变更前版本。

本次动作：
- 为 `DisplayRuntimeView.vue` 增加 `pendingAutoRefresh`、`scheduleAutoRefresh`、`bizDateAutoRefreshTimer` 以及 `suppressNextBizDateReaction`，监听 `bizDate` 输入并在 400ms 去抖后自动调用 `runEval()`；当首次加载未完成或已有刷新进行中时，将自动刷新请求排队至当前任务结束，避免并发压测 `/runtime/spec/eval`。
- 组件卸载时统一清理定时器，并跳过初始化阶段 `loadDefaultBizDate()` 对 `bizDate` 的写入，确保首屏仅发起一次请求。
- 更新 `frontend/README.md`、`backend/README.md` 记录“数据展示页业务日自动刷新”特性及对后端接口的影响说明。

影响范围与回滚：
- 仅影响 `projects/daily_report_25_26/pages/data_show/sheets` 页面在切换业务日期时的行为；若要回滚，删除新增的自动刷新逻辑或恢复旧版组件即可，README 可同步恢复上一版本。

验证建议：
1. 进入数据展示任意子页面，等待首屏加载完成后切换业务日期，观察 400ms 内自动出现“数据载入中…”并刷新结果，无需再点击“刷新”按钮。
2. 在加载过程中连续切换多个日期，确认前一次请求完成后会自动排队执行最新一次变更，网络面板不会出现大量并发 `runtime/spec/eval`。
3. 清空日期或切回默认值仍能自动刷新，且 `effectiveBizDate` 提示与返回数据保持一致。

## 2025-11-10（数据库连接池扩容）

前置说明（降级留痕）：
- Serena 暂未支持对 Python 源文件进行符号级写入，本次根据 AGENTS.md 3.9 要求，降级使用 `desktop-commander::read_file` + `apply_patch` 调整 `backend/db/database_daily_report_25_26.py`；回滚时恢复该文件的 `create_engine` 配置即可。

本次动作：
- 针对 `/dashboard` 高频访问导致的 `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached` 报错，将数据库 engine 的 `pool_size` 提升至 20、`max_overflow` 至 40，并补充 `pool_timeout=60`、`pool_recycle=1800`，同时保留 `pool_pre_ping`，缓解连接占满问题。
- 新增后端依赖 `psycopg2-binary`（记录需求文件），确保容器部署时 SQLAlchemy 能连接 PostgreSQL，避免 “No module named 'psycopg2'” 导致 v1 路由未挂载。

影响范围与回滚：
- 仅影响 `daily_report_25_26` 专用 engine 的连接池设置；若需回滚，可恢复旧配置（不带额外参数）。

验证建议：
1. 重启后端服务或热加载代码，访问仪表盘页面多次触发 `/dashboard` 请求，确认日志不再出现 QueuePool 超时。
2. 在高并发或并行加载时观察数据库连接数，确认连接池容量能支撑峰值访问。
3. 重新构建后端镜像并部署，确认 `docker logs phoenix-backend` 不再出现 `No module named 'psycopg2'`，`/api/v1` 接口恢复 200/401 等正常响应。

## 2025-11-10（供暖单耗柱距优化）

前置说明（降级留痕）：
- Serena 当前仍无法对 `.vue` 组件执行符号级写入，本次按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚时恢复该文件对应段落即可。

本次动作：
- 调整仪表盘“供暖单耗”三张卡片所用的 `useUnitConsumptionOption` 图表配置，将同一单位下“本期/同期”柱形的 `barGap` 调整为 `0%` 以贴紧成组显示，同时把 `barCategoryGap` 提升至 `65%` 拉开不同单位分组的间距，避免视觉重叠。
- 同期柱状图标签取消显示（`label.show=false`），并清理全局所有标签的背景色配置，保持图面整洁。
- “本期”柱体标签改为双行文案，顶部一次展示“本期 / 同期”两组数据（若同期为空则自动省略），避免叠加额外标签仍能看清对比值。
- 投诉量分项卡片的柱状标签改为始终显示数值（含 0），确保零值不会被隐藏。
- 新增“供热分中心单耗明细”卡片：支持按热/电/水单耗切换排序，左侧条形图展示从低到高排名并带平均值参考线，右侧表格同步展示三项单耗（字号 8px）；所有数值采用千位分隔展示，图表与表格在桌面端各占 6 列，布局与现有仪表盘风格一致。
- 平均气温摘要改为展示“本期均值 + 与同期差值”格式（例：12.3（+0.8）），便于快速对比同期温度。

影响范围与回滚：
- 仅影响“供暖单耗”卡片内的三张柱状图；若需回滚，可把 `barGap` 恢复为 `20%`、`barCategoryGap` 恢复为 `40%`。

验证建议：
1. 打开数据看板页面并定位到“供暖单耗”卡片，确认每个单位下的“本期”与“同期”柱形紧邻且不再重叠。
2. 对比相邻两个单位，确认组与组之间留白增大、读数标签未被遮挡。
3. 切换业务日期或重新加载，确认样式设置对不同数据集保持一致。
4. 确认“供暖单耗”“标煤消耗量对比”卡片的标签均以双行展示本期/同期，投诉量卡片零值标签可见，“供热分中心单耗明细”条形图与表格排序正确且平均线正常（表格字号 8px、左右各占 6 列），平均气温摘要已呈现与同期差值，边际利润标签新增轻量白底，煤炭库存卡片仅保留堆叠柱且顶部仍显示合计标签（通过零半径散点实现）；同时确保其它卡片的数值标签已移除白色背景。

## 2025-11-10（仪表盘加载提示与填报反馈）

前置说明（降级留痕）：
- Serena 目前仍无法对 `.vue` 组件进行符号级写入，本次按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 与 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`；回滚时恢复上述文件即可。

本次动作：
- 仪表盘组件新增 `isLoading` 计数状态，请求 `/dashboard` 数据时在页面顶部展示“数据载入中，请稍候…”提示，防止用户误以为界面卡死；并通过并发计数避免多次请求提前关闭提示。
- 数据填报页面引入 `isSubmitting` 与 `submitFeedback` 状态，提交期间禁用按钮，成功/失败分别弹出绿色与红色提示条，并在 3.2 秒后自动收起，离开页面时清理定时器。
- `onSubmit` 捕获异常并写入控制台日志，同时在失败提示中展示具体错误信息，提交成功后刷新“最近提交”时间戳。

影响范围与回滚：
- 前端仪表盘加载大批量数据时能够给出明确等待提示，若需回滚可移除 `isLoading` 状态、模板提示及对应样式。
- 数据填报页面的提交体验提升，后端接口未改动；回滚时恢复旧版 `onSubmit` 实现与模板中的按钮/提示结构即可。

验证建议：
1. 打开 `/projects/daily_report_25_26/pages/dashboard/dashboard` 页面，首次加载应出现“数据载入中，请稍候…”提示，数据返回后自动消失。
2. 在数据填报页面提交一次有效数据，确认出现“提交成功，数据已入库”提示且按钮在请求结束后恢复可点击。
3. 断开网络或手动让后端返回错误，再次提交验证会出现失败提示，提示消失后按钮恢复。

## 2025-11-10（投诉卡片双图拆分）

前置说明（降级留痕）：
- Serena 仍无法对 `.vue` 文件执行符号级编辑，本次继续按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚时恢复该文件即可。

本次动作：
- 将仪表盘“投诉量”卡片拆分为两张图（“省市平台服务投诉量”“净投诉量”），分别对比本期/同期，并共享原表格。
- 新增 `useComplaintSingleOption`，按指标生成单独的双柱图配置；图表渲染逻辑改为 `complaintChartConfigs` 数组驱动，可根据数据动态扩展。
- 卡片内部新增 `complaint-charts` 栅格，默认纵向排列，≥768px 时并列两列；柱图高度调整为 260px。
- 栅格布局调整：投诉卡片在 ≥1024px 时占据 8 列宽度，收入卡片收窄为 4 列，与投诉卡片同排；投诉卡片最小高度提升至 360px。
- 同期系列柱形改为橙色填充，移除斜纹样式，突出不同时间段的对比色。
- “收入分类对比”卡片补充表格，展示各分类本期/同期数值并与图表同步。

影响范围与回滚：
- 仪表盘“投诉量”卡片显示为两张图 + 表格的组合；`/dashboard` 返回结构未改动。若需回滚，恢复 `DashBoard.vue` 中投诉卡片模板与 `useComplaintSingleOption` 变更前版本即可。
- `dashboard-grid__item--income` 改为 4 列，`dashboard-grid__item--complaint` 改为 8 列；回滚时恢复对应样式。

验证建议：
1. 刷新仪表盘，确认“投诉量分项”卡片内出现两张图，并列展示“省市平台服务投诉量”“净投诉量”本期/同期柱状图。
2. 检查同期柱形颜色已变为橙色，tooltip 显示本期/同期数值且带单位，标签仅在非零时出现。
3. 切换业务日期或变更数据源，确认投诉表格与两张图同步更新，收入卡片新增表格正常显示本期/同期数值，并保持 8+4 列布局。

## 2025-11-10 (仪表盘修复与PDF下载)

- 修复了仪表盘“投诉量”卡片因 `phaseGap` 和 `metricGap` 变量未定义而导致的渲染崩溃问题。
- 为仪表盘页面增加了“下载为PDF”功能：
  - 在 `index.html` 中通过 CDN 引入 `html2canvas` 和 `jsPDF` 库。
  - 在仪表盘头部添加了“下载PDF”按钮。
  - 实现了 `downloadPDF` 函数，利用 `html2canvas` 截取页面内容，并通过 `jsPDF` 生成和保存 PDF 文件。
  - PDF 文件名会动态包含当前的业务日期。
  - 在截图过程中会自动隐藏“下载PDF”按钮，避免其出现在最终的PDF文件中。
- 优化了PDF下载功能，将截图格式从 PNG 改为高质量的 JPEG，并启用了 jsPDF 的中等压缩，显著减小了生成的 PDF 文件体积。
- 根据用户反馈再次调整了PDF生成策略，以在文件大小和清晰度之间取得更好的平衡。将截图格式恢复为 PNG 以保证无损画质，同时将 `html2canvas` 的渲染比例（`scale`）提升至 2 倍以提高分辨率，并配合 `jsPDF` 的 `FAST` 压缩模式。

## 2025-11-10（投诉板块真实数据接入）

前置说明（降级留痕）：
- Serena 对 `evaluate_dashboard` 局部删除/替换仍缺乏粒度控制，本次按 3.9 矩阵降级使用 `apply_patch` 调整投诉段调用逻辑；回滚时恢复 `backend/services/dashboard_expression.py` 中 `_fill_complaint_section` 定义及 `evaluate_dashboard` 对应片段。
- Serena 无法对 `.vue` 文件执行符号级写入，继续按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚恢复该文件即可。

本次动作：
- 新增 `_fill_complaint_section`，支持同时拉取“当日省市平台服务投诉量”“当日净投诉量”两个指标的本期/同期数据，并基于 `groups` / `sum_basic_data` 配置与 `push_date` 查询数据库视图；`evaluate_dashboard` 第六段改为调用新助手填充投诉板块。
- 仪表盘投诉卡片改为消费后端真实数据：自动解析指标 → 生成公司列表、列标题与四条系列（两指标 × 本期/同期），并保留“件”单位回退逻辑。
- 图表采用分组柱状呈现并启用 `labelLayout.moveOverlap='shiftY'`，表格列扩展为“本期/同期”+“本期净/同期净”四列，摘要数值聚焦“集团全口径”本期投诉量、缺失时逐项回退。
- 全部图表内部标签与 tooltip 移除单位文本，保留卡片 `extra` 提示，避免重复显示计量单位。
- 投诉量柱图对“同期”系列附加斜线 `decal` 样式并调成蓝绿色，同时通过 `barGap`/`barCategoryGap` 拆分每个指标组，使本期/同期成对展示且不同指标间有明显留白。
- 删除页面残留的演示数值（煤耗、单耗、库存等 fallback 仅保留结构，默认填 0），确保外观不再显示 980 吨等示例数据。
- 投诉量表格字体缩小至 11px，并将所有柱状图的“同期”系列统一使用亮蓝斜线空心样式，便于快速区分。
- 权限调整：`backend_data/auth/permissions.json` 中 `ZhuChengQu_admin` 的 `page_access` 新增 `dashboard`，允许主城区管理员访问数据看板。

影响范围与回滚：
- `/api/v1/projects/daily_report_25_26/dashboard` 返回的投诉板块现包含两个指标、每指标下的公司字典；如需回退，移除 `_fill_complaint_section` 并把 `evaluate_dashboard` 恢复为 `_fill_simple_metric` 版本即可。
- 前端投诉卡片依赖上述结构渲染图表与表格；若需回退，将 `DashBoard.vue` 恢复至接入前的静态数据实现即可。

验证建议：
1. 启动后端访问 `/dashboard?show_date=YYYY-MM-DD`，确认响应中 “6.当日省市平台服务投诉量” 段包含两个指标及本期/同期→公司维度的数值。
2. 前端仪表盘加载后，检查投诉卡片展示 4 条系列、图例与柱体颜色一致，顶部标签无重叠；表格出现四列数值并与图表一致。
3. 切换 `show_date`，验证摘要卡片、图表与表格随 `push_date` 更新；若后端缺数据，则图表/表格展示 0 占位而不报错。

## 2025-11-10（数据标签零值统一隐藏）

前置说明（降级留痕）：
- Serena 仍无法对 `.vue` 模板区块精确写入，继续按 3.9 矩阵使用 `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚恢复该文件即可。

本次动作：
- 在 `DashBoard.vue` 内统一封装 `shouldDisplayLabel/formatLabelNumber`，对边际利润折线、收入对比、三张单耗、标煤消耗量、投诉量等图表的标签 formatter 加入零值判定；投诉量、供热单耗、标煤等柱状图标签在值为 `null/NaN/0` 时返回空字符串，温度曲线的高亮 markPoint 也需为非零才渲染。

影响范围与回滚：
- 影响所有仪表盘卡片的图表标签显示；如需恢复显示零值，可撤销 `shouldDisplayLabel/formatLabelNumber` 辅助函数及各图表中的调用即可。

验证建议：
1. 加载仪表盘，确认边际利润折线、收入对比、单耗、标煤、投诉等图表在数值为 0 时不再显示顶部标签。
2. 切换日期确保非零值标签仍显示且 tooltip 数据保持完整。

## 2025-11-10（煤炭库存卡片接入真实数据）

前置说明（降级留痕）：
- Serena 无法对 `.vue` 文件进行结构化插入，本次继续按 3.9 矩阵使用 `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚恢复该文件即可。

本次动作：
- 新增 `coalStockSection/coalStockSeries` 计算属性，从 `/dashboard` 第七段解析各公司“厂内存煤/港口存煤/在途煤炭”数值，空数据时回退至演示数据。
- `useCoalStockOption` 支持动态数据并使用蓝/橙/绿等高对比调色盘，按返回公司与仓储类型组装堆叠柱图，同时叠加“合计”折线显示每根柱子的总量标签；`coalStockOpt` 改为 computed，使卡片随 `push_date` 自动刷新。
- 卡片新增底部表格 `coalStockColumns/coalStockTableData`，在“单位 × 存储方式 + 合计”维度展示吨数，与柱状图保持一致。

影响范围与回滚：
- 仅影响煤炭库存卡片的数据来源与配置；如需回退，移除新增计算属性并将 `useCoalStockOption` 恢复为静态模拟即可。

验证建议：
1. 调用 `/dashboard?show_date=YYYY-MM-DD` 检查 “7.煤炭库存明细” 节点存在公司与三类库存数据。
2. 打开仪表盘，确认煤炭库存柱图按公司与堆栈展示真实数据、底部表格同步列出各仓储吨数；切换展示日期后数据同步刷新。

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
  - 为所有柱状图（收入、单耗、标煤等）统一设置 `distance=6`、启用 `labelLayout.moveOverlap='shiftY'`，并在有分类轴的图表上开启 `axisLabel.hideOverlap=true`，通过纵向错位与智能避让避免标签互相遮挡。

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

## 2025-11-10（页面入口信息脱敏）

前置说明（降级留痕）：
- Serena 对 `.vue` 组件仍不支持符号级编辑，本次按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/PageSelectView.vue`；回滚时恢复该文件即可。

本次动作：
- 页面选择视图的卡片副标题改为通过 `pageDescription` 辅助函数生成的业务描述，移除了模板文件路径展示。
- 新增 `PAGE_DESCRIPTION_MAP` 描述表覆盖“数据看板/数据展示/审批/填报/常量/调试”等入口，默认回退文案为“点击进入功能页面”。

影响范围与回滚：
- `/projects/daily_report_25_26/pages` 页面卡片不再泄露 `/app/data/*.json`、`configs/*.json` 路径，改为直观的功能简介；如需回滚，删除 `pageDescription` 函数并恢复模板中原文本即可。
- 路由跳转逻辑未改动，`openPage` 仍按 `page.config_file` 控制 query 参数，对后端 API 与权限判定无影响。

验证建议：
1. 登录平台进入页面选择视图，确认所有卡片副标题都为中文功能说明且无文件路径。
2. 分别点击“数据填报”“数据审批”“数据展示”等卡片，验证跳转路径与历史行为一致。
3. 检查“运行时表达式求值（调试）”卡片描述是否为“运行时表达式调试工具，仅限技术人员”，确保内部入口仍可区分。

## 2025-11-10（项目列表补充页面描述）

前置说明（降级留痕）：
- Serena 暂未支持 JSON/脚本文件细粒度写入，继续按 3.9 矩阵使用 `desktop-commander::read_file` + `apply_patch` 修改 `backend_data/项目列表.json`、`backend/api/v1/routes.py` 与 `frontend/src/daily_report_25_26/pages/PageSelectView.vue`，回滚时恢复上述文件即可。

本次动作：
- `backend_data/项目列表.json` 中为 `dashboard/data_show/data_approval/data_entry/constant_data//debug/runtime-eval` 写入 `页面描述` 字段，内容与前端映射保持一致。
- `backend/api/v1/routes.py` 的 `_normalize_pages` 透传 `页面描述`（同时兼容 `page_description`）到 `page_description/description` 字段，便于前端直接消费。
- `frontend/src/daily_report_25_26/pages/PageSelectView.vue` 更新 `pageDescription`：优先使用接口返回的 `page_description`/`description`/`page_desc` 等字段，映射表仅在缺省时兜底。

影响范围与回滚：
- `/projects/:projectId/pages` 接口附带 `page_description`，前端、其他客户端可直接读取业务文案；若需回滚描述，可删除新增字段并恢复前后端文件。
- 映射表仍存在以防遗留项目未配置描述，确保兼容性。

验证建议：
1. 调用 `/api/v1/projects/daily_report_25_26/pages`，确认 `pages[]` 结果包含 `page_description` 且文本与配置一致。
2. 刷新页面选择视图，确保卡片副标题仍显示相同文案；临时删除某条 `页面描述` 可验证回退逻辑。
3. 检查调试入口描述是否同步来自配置文件（可通过修改 JSON 验证）。

## 2025-11-10（净投诉面积口径切换）

前置说明（降级留痕）：
- Serena 暂不支持对大体量 SQL/Markdown 文件的符号级写入，本次按照 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 更新 `backend/sql/create_view.sql`、`backend/README.md` 与 `frontend/README.md`；回滚时恢复上述文件即可。

本次动作：
- 将 `calc_amount_daily_net_complaints_per_10k_m2` 及主城区/集团视图中引用的常量项从 `amount_whole_heating_area` 全部替换为 `amount_heating_fee_area`，并修正相关注释，确保“万平方米净投诉量”基于供暖收费面积计算。
- 后端、前端 README 新增同步说明，提示当前视图口径变更且前端暂无需改动。

影响范围与回滚：
- 影响统计口径：相关指标将按收费面积生成结果，若需恢复旧口径，可将 SQL 中的常量项恢复为 `amount_whole_heating_area` 并撤销 README 更新。
- 视图结构、接口字段及前端渲染代码未改动，联调时仅需确认数值是否符合预期。

验证建议：
1. 在数据库中刷新 `sum_basic_data` 及 `groups` 视图后，检查 `amount_daily_net_complaints_per_10k_m2` 的值是否与收费面积口径一致。
2. 对比切换前的历史报表，确认主营单位指标变化符合面积基数调整的预期趋势。
3. 若前端需展示口径说明，可在仪表盘投诉卡片补充“按供暖收费面积计算”备注。

## 2025-11-11（净投诉面积口径迁移修订）

前置说明（降级留痕）：
- Serena 仍无法对大型 SQL/Markdown 文件做符号级写入，本次继续按 3.9 矩阵使用 `desktop-commander::read_file` + `apply_patch` 更新 `backend/sql/sum_basic_data.sql`、`backend/sql/groups.sql`、`backend/README.md`、`frontend/README.md`；如需回滚请恢复上述文件。
- 同时将 `backend/sql/create_view.sql` 恢复为原挂网面积配置，避免示例脚本与正式视图脚本口径混用。

本次动作：
- 将 `sum_basic_data` 与 `groups` 视图中“万平方米省市净投诉量”的分母统一替换为 `amount_heating_fee_area`，确保公司明细、主城区与集团聚合均以供暖收费面积为基准。
- README 分别记录后端、前端侧的口径调整及联调提示；在 `configs/progress.md` 留痕修订过程。

影响范围与回滚：
- 数据口径：相关指标将基于收费面积统计；若需恢复挂网面积，只需将上述 SQL 内常量项改回 `amount_whole_heating_area` 并重新刷新视图。
- 示例脚本 `create_view.sql` 已恢复旧逻辑，不影响生产；如需再次验证收费面积，可复制正式脚本内容进行演示。

验证建议：
1. 重新执行两份视图脚本，确认 `amount_daily_net_complaints_per_10k_m2` 数值随收费面积调整。
2. 对比主城区与集团的投诉量指标，确认分母与单体公司保持一致。
3. 前端仪表盘若需提示，可在投诉量卡片增加“按供暖收费面积计算”说明，确保业务侧知悉变更。

## 2025-11-11（数据填报提交倒计时刷新）

前置说明（降级留痕）：
- Serena 仍无法对 `.vue` 组件进行符号级写入，本次按 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`，并同步更新 `frontend/README.md`、`backend/README.md`；回滚时恢复上述文件即可。

本次动作：
- 提交成功后触发 3 秒倒计时，`submitFeedback` 提示条展示剩余秒数，倒计时结束调用 `reloadTemplate()` 重新拉取当前业务日期数据，避免整页刷新并保持用户选中的日历日期。
- 新增 `refreshCountdown`/`refreshCountdownTimer` 状态与清理函数，确保倒计时在失败、重复提交或组件卸载时能安全终止。
- 样式新增 `.submit-countdown`，与原提示外观一致；README 记录交互变更及回滚方式。（闪动高亮尝试因体验不佳已撤回）

影响范围与回滚：
- 行为仅发生在数据填报页面前端层，后端 `/submit` 接口与数据库逻辑未改动；若不需要倒计时刷新，可恢复 `DataEntryView.vue` 原实现。
- 旧版不会显示倒计时提示，也不会自动刷新，需要手动重新加载页面。

验证建议：
1. 在本地填报页面成功提交一次，确认提示条显示“提交成功”并开始 3、2、1 倒计时，3 秒后自动刷新当前业务日期表格。
2. 提交失败或取消页面时，倒计时应立即停止且不再自动刷新。
3. 刷新后“最近提交”时间应更新为最新时间戳，验证写库数据已回填。

## 2025-11-11（数据看板段名序号化解析）

前置说明（降级留痕）：
- Serena 对 `.py`/`.vue` 文件的符号级编辑仍有限制，本次依照 3.9 矩阵使用 `desktop-commander::read_file` + `apply_patch` 更新 `backend/services/dashboard_expression.py` 与 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；需要回滚时直接恢复两文件即可。

本次动作：
- 后端 `evaluate_dashboard` 通过 `_build_section_index_map` 按编号前缀定位各板块，投诉分项等段落不再依赖完整中文标题，配置改名后仍能正确回填数据。
- 前端仪表盘增加 `resolveSection` 辅助，所有 `sections['N.xxx']` 访问切换为序号解析；投诉卡片的指标排序与标题映射同时兼容“省市平台投诉量”的新命名。

影响范围与回滚：
- 数据看板所有分区（气温、边际利润、投诉、煤炭库存等）读取逻辑统一按编号解析；若需回滚，撤销上述文件到改动前版本即可恢复原硬编码行为。
- JSON 配置如继续变更标题文本，无需再同步改代码；但若删除编号前缀（如 `6.`），需补充新的匹配策略或恢复编号。

验证建议：
1. 调整 `backend_data/数据结构_数据看板.json` 中 `6.` 段标题，刷新前端仪表盘确认“投诉量分项”仍能显示本期/同期数据。
2. 在同一配置中新增或重命名其它段落标题，验证边际利润、标煤耗量等模块仍可正常回填。
3. 运行 `/api/v1/projects/daily_report_25_26/dashboard` 接口，确认返回 `data` 中的原始键保持配置名称，同时新增代码逻辑不会插入额外字段。

## 2025-11-11（数据看板单耗卡片视觉调优）

前置说明（降级留痕）：
- Serena 暂无法对 `.vue` 样式与脚本混合片段进行符号级写入，本次沿用 `desktop-commander::read_file` + `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚时请恢复该文件。

本次动作：
- 调整“供暖热/电/水单耗对比”三张卡片的 ECharts 高度至 `360px`，配合 12 栅格布局提升可视空间。
- 统一本期柱色为蓝色（#2563eb），同期柱色改为高对比橙色（#f97316），并保留条纹以强调差异。
- 优化柱宽与图表内边距，使单个对比更醒目。

影响范围与回滚：
- 仅影响前端渲染与配色，后端 `/dashboard` 返回结构未变；若需恢复旧视觉，撤销上述文件改动即可。

验证建议：
1. 在桌面端刷新仪表盘，确认三张单耗卡片高度扩大且蓝/橙颜色区分明显。
2. 切换至移动端视口，确保自适应布局仍正常。
3. 对比历史截图，确认本期/同期图例颜色一致更新。

## 2025-11-11（数据看板单耗卡片栅格调整）

前置说明（降级留痕）：
- Serena 暂不支持对 `.vue` 样式块进行符号级编辑，本次按 3.9 矩阵使用 `desktop-commander::read_file` + `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；如需回滚恢复该文件即可。

本次动作：
- 将供暖热/电/水单耗对比卡片的栅格跨度由 `span 4` 调整为 `span 12`，三张图表在宽屏下独占一行，提升阅读空间。

影响范围与回滚：
- 仅影响仪表盘前端排版，后端 `/dashboard` 输出结构未变。如需回滚，将样式中的 `grid-column: span 12;` 恢复为 `span 4;`。

验证建议：
1. 打开数据看板页面，确认三张单耗对比卡片在 ≥1024px 宽度下各占一行。
2. 缩小至平板或手机宽度，检查卡片仍保持单列自适应展示。

## 2025-11-11（数据看板“集团汇总”文案统一）

前置说明（降级留痕）：
- Serena 对 JSON/Vue 大文件的写入仍有限制，本次沿用 `desktop-commander::read_file` + `apply_patch` 调整 `backend_data/数据结构_数据看板.json`、`backend/services/dashboard_expression.py`、`frontend/src/daily_report_25_26/pages/DashBoard.vue`、`frontend/src/daily_report_25_26/pages/DashBoard888.vue`；回滚时分别恢复这些文件即可。

本次动作：
- 将数据看板配置、单位字典以及所有占位数据中的“集团全口径”统一改为“集团汇总”，并把板块标题改名为“3.集团汇总收入明细”。
- 后端 `get_section_by_index` 新增别名以兼容新旧标题，前端 `resolveSection`、各类 fallback 数组和 complaint/煤耗/边际利润组件同步替换，确保 API 与 UI 一致展示。

影响范围与回滚：
- `/api/v1/projects/daily_report_25_26/dashboard` 中公司中文名现在输出“集团汇总”；若需恢复旧称谓，只需将上述文件的文案改回“集团全口径”。
- 由于仍按编号前缀解析，旧配置若暂未更新标题也可被别名捕获，但建议一次性完成改名避免混写。

验证建议：
1. 调用 `/api/v1/projects/daily_report_25_26/dashboard`，确认 `data`、`unitSeries` 等字段中的公司名称均已替换为“集团汇总”。
2. 刷新仪表盘页面，检查卡片、图例、表格以及 fallback 标签均显示新文案。
3. 若存在导出或打印流程，验证在新称谓下仍可正常命中“集团汇总”数据。

## 2025-11-11（单耗卡片标签分离）

前置说明（降级留痕）：
- Serena 暂无法对 `.vue` 组件混合片段做符号级写入，本次继续使用 `desktop-commander::read_file` + `apply_patch` 更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚只需恢复该文件。

本次动作：
- `useUnitConsumptionOption` 取消“本期/同期”组合标签，改为分别在两根柱体上独立显示数值，并启用同期柱的标签，便于在 12 栅格宽度下直接对比。

影响范围与回滚：
- 仅影响前端 ECharts 标签展示，后端 `/dashboard` 返回结构不变；若需回滚，将标签 formatter 改回 `formatCombinedLabel` 并关闭同期标签即可。

验证建议：
1. 刷新仪表盘单耗卡片，确认本期与同期柱体分别显示各自标签且不再堆叠。
2. 检查标签在移动端与缩放后的布局下不会互相遮挡，必要时可调整偏移或字体。

## 2025-11-11（单耗卡片水平布局试验）

前置说明（降级留痕）：
- Serena 仍无法对 `.vue` 组件混合片段做符号级写入，本次继续使用 `desktop-commander::read_file` + `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚请恢复该文件。

- 本次动作：
- 将三张单耗柱状图改为水平展示（ECharts horizontal orientation），卡片高度提升至 450px（原 300px 的 1.5 倍），同时保持 `.dashboard-grid__item--unit` 为 `span 4` 以便三图并排展示。
- 强制单耗卡片的公司顺序为“研究院→庄河环海→金普热电→北方热电→金州热电→主城区→集团汇总”，若某指标缺少数据（如电耗无研究院）则自动跳过。
- 在 summary 区域新增 4 张紧凑卡片（煤炭库存、集团热/电/水单耗），使用 `summary-card--compact` 将高度压缩至原卡片的约 80%，并各自配套渐变与图标。

影响范围与回滚：
- 仅影响前端展示方向与布局，后端 `/dashboard` 数据结构、单位等均未变；若需恢复竖向排列，可将 orientation 改回 `vertical` 并把 `.dashboard-grid__item--unit` 栅格设为 `span 12`。

验证建议：
1. 刷新仪表盘确认三张卡片呈水平条形图，并在同一行内按热/电/水顺序展示。
2. 检查 tooltip/标签显示是否适配水平布局；必要时调整 `grid.left` 与标签偏移。
3. 核对公司排序是否按照“研究院→庄河环海→金普热电→北方热电→金州热电→主城区→集团汇总”，电耗缺失单位时应自动省略。
4. 查看新增 summary 卡片的展示数值与单位是否与图表数据一致（煤炭库存合计、集团热/电/水单耗）。

## 2025-11-12（累计卡片气温逐日输出）

前置说明（降级留痕）：
- Serena 暂不支持对 Markdown 文档追加段落，本次使用 `apply_patch` 追加 `configs/progress.md`；回滚时删除本节即可。

本次动作：
- `backend/services/dashboard_expression.py` 新增 `_fetch_daily_average_temperature_map`，并改造 `_fill_cumulative_cards`，将“供暖期平均气温”字段改为返回推送日期范围内逐日平均气温列表（含同期对照）。
- 日均值缺失日期以 `None` 补位，其他供暖期累计指标仍读取 `groups` 视图的 `sum_ytd_*` 字段。

影响范围与回滚：
- `/api/v1/projects/daily_report_25_26/dashboard` 的 `data["9.累计卡片"]["供暖期平均气温"]` 现为数组结构；如需恢复旧版单值响应，请还原上述函数改动。
- 当前前端尚未消费该字段，可在接入前先验证数据质量。

验证建议：
1. 调用 `/api/v1/projects/daily_report_25_26/dashboard` 并指定 `show_date`，确认本期/同期数组长度与供暖期天数一致。
2. 以 `push_date=2025-11-03` 为例，核对数组首三项是否分别对应 11-01 至 11-03 的 `aver_temp` 日均值。

## 2025-11-12（仪表盘累计摘要卡片接入）

前置说明（降级留痕）：
- Serena 暂无法对 `.vue` 单文件组件做符号级追加，本次使用 `apply_patch` 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`；回滚时恢复该文件即可。

本次动作：
- 新增 `cumulativeSection`、`cumulativeSeasonAverageHeadline` 等计算属性，读取 `/dashboard` 返回的 “9.累计卡片” 数据并形成本期/同期差值。
- 后四张 summary card 改为展示供暖期平均气温、可比煤价边际利润、标煤耗量、投诉量及其与同期的增量（括号内显示 `±`）。
- 抽象 `formatHeadlineNumber/formatHeadlineDelta`，支持千分位与差值统一格式；原煤炭库存与单耗临时卡片逻辑已移除。
- 新增 `summary-card--outline` 样式，后四张卡片改为仅保留边框、不再显示图标与背景填充，主/差值颜色调整为暗蓝系以增强对比，并在最新迭代中将卡片高度下调约 10%（padding=12px）。
- 首页前四张 summary card（当日可比煤价边际利润/标煤消耗/投诉量）现同步显示与同期对比的括号增量；对应脚本新增 `primary*Headline` 计算属性以便复用格式化逻辑。
- “供热分中心单耗明细”条形图移除横轴坐标文字与单位标题（保留标线），避免横向布局拥挤；“收入分类对比（集团）”的横轴标签会在窄屏下自动分行并固定字体大小/底部留白，从而不再被隐藏。
- “当日集团可比煤价边际利润”卡片改用 2 号段返回的 `本期/同期` 数据直接比对（优先匹配“集团汇总/集团全口径/Group”），修复差值显示偏小的问题。
- 气温曲线仅展示 `push_date` 前 3 天至预测区间，且同期曲线按相同窗口自动映射至上一供暖季日期，避免整段数据被截断。
- “收入分类对比（集团）”横轴字体增大、底部留白更充足，并将分类标签旋转 30° 以避免窄屏被遮挡。

影响范围与回滚：
- 仅影响前端仪表盘摘要区的显示文案和数据来源，后端接口结构未改。如需恢复旧版，可撤销 `DashBoard.vue` 的相关修改。

验证建议：
1. 刷新数据看板页面，确认后四张紧凑卡片按要求显示本期值与括号内的同期增量。
2. 切换 `push_date`（或 `show_date`）检查差值会随日期变化；确保单位与 `backend_data/数据结构_数据看板.json` 中一致。

## 2025-11-13（煤炭库存镜像查询顺序纠正）

前置说明（降级留痕）：
- Serena 仍无法对 `backend/api/v1/daily_report_25_26.py` 做符号级插入，本次依 3.9 矩阵降级使用 `desktop-commander::read_file` + `apply_patch` 修改；回滚时恢复该文件即可。

本次动作：
- 调整 `/data_entry/sheets/{sheet_key}/query` 中 crosstab 分支的 `result_rows` 构建逻辑，先按模板 `rows` 顺序匹配 `(单位, 煤种)` 键回填数据库值，再对模板缺少的组合附加在末尾，避免刷新后行顺序被数据库返回顺序打乱。
- 模板行缺失数据时依旧返回 `rows_raw` 的原始结构，保持空表占位体验一致。

影响范围与回滚：
- 仅影响 `Coal_inventory_Sheet` 镜像查询结果的行排序，写库流程与接口字段未改动；恢复旧版即可回到数据库原始排序。
- 若后续需定制排序，可直接调整模板 JSON 中行顺序。

验证建议：
1. 选取任意业务日期重复提交后刷新页面，确认“香海 印尼煤”等行不会再跳到表头。
2. 若数据库存在模板未定义的单位/煤种组合，确认它们会附加在模板行之后并保留数值。
3. 通过 `docker logs phoenix-backend -f` 观察 `/query` 输出，确保 200 返回且 `rows` 顺序与模板一致。

## 2025-11-15（会话持久化建表脚本）

前置说明：
- 本次仅新增 SQL 文件，无需 Serena 符号级操作；如需回滚，删除该脚本或忽略执行即可。

本次动作：
- 在 `backend/sql` 目录新增 `create_auth_sessions_table.sql`，包含 `auth_sessions` 表建表语句与 `username/expires_at` 索引，用于后续将登录 token 持久化到 PostgreSQL。
- 表字段覆盖 token、用户名、所属组、单位、层级、权限 JSONB、可审批单位 JSONB、签发/过期/最近访问时间，便于与 `AuthManager` 的 dataclass 对应。

影响与验证：
- 当前仅是建表脚本，对运行中服务无影响；后续执行该 SQL 并修改后端即可实现会话持久化。
- 建表成功后，可在数据库中通过 `\d auth_sessions` 检查结构，或插入示例记录验证索引生效。

## 2025-11-15（填报成功提示微调）

- 修改 `frontend/src/daily_report_25_26/pages/DataEntryView.vue` 中 `startRefreshCountdown()` 的提示文案，将“提交成功，数据已入库。”调整为“提交成功，数据已入库！”，保持倒计时逻辑不变。
- 影响范围：仅前端提示文字，功能与交互一致；如需回滚，恢复该文件的文案即可。

## 2025-11-15（审批进度过滤集团行）

- `frontend/src/daily_report_25_26/pages/PageSelectView.vue` 的 `workflowUnits` 计算属性新增黑名单 `{'系统管理员','Group'}`，不再在审批表中展示集团本身的行。
- 影响：审批列表仅保留需要人工审核的单位，集团行默认隐藏；回滚时删除该黑名单即可。


## 2025-11-19（Dashboard 折叠表 fallback 移除）

前置说明（治理与留痕）：
- 依据用户指令，前端折叠表不再使用任何兜底（fallback）推导，仅展示后端 0.5 段落返回的数据；符合“接口最小化与标准化”的原则，避免前后端口径不一致。
- 变更通过 Codex CLI 的 apply_patch 完成；本次仅涉及前端 `.vue` 文件，未改动后端。

本次动作：
- 移除 `DashBoard.vue` 中折叠表的兜底逻辑（`SUMMARY_FOLD_FALLBACK_KEYS`、`resolveSummaryMetricPayload`、`summaryFoldFallbackTable`）。
- `summaryFoldTable` 现在仅返回 `buildSummaryTableFromSection(summaryFoldSection.value)` 的结果；若 0.5 段落缺失或为空，则折叠表不再展示兜底数据。

影响范围与回滚：
- 影响：当后端未返回 `0.5卡片详细信数据表（折叠）` 或其数值为空时，折叠表可能为空（按预期）；避免误导性的展示。
- 回滚：恢复被删除的三个代码块，并将 `summaryFoldTable` 改回“有数据用段落，否则回退兜底”的逻辑即可。

验证建议：
1) 访问仪表盘，确认折叠表数据与 `/dashboard` 返回中 0.5 段落一致；
2) 临时在后端去除 0.5 段落，前端折叠表应不显示兜底数据；
3) 切换业务日期（`push_date`），折叠表本期/同期联动更新。
