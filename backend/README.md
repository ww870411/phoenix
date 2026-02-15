# daily_report_25_26 后端说明

## 最新结构与状态（2026-02-08）

- 项目列表来源：`backend_data/shared/项目列表.json`
  - `GET /api/v1/projects` 由 `backend/api/v1/routes.py` 中 `list_projects` 返回项目卡片数据；
  - 当前已增加第二个项目：`mini_project_demo`（迷你项目示例），并已精简为单页面最小配置（无审批、无常量指标配置清单）。
- 新增春节简化日报项目模块：`backend/projects/daily_report_spring_festval_2026/`
  - 路由入口：`api/router.py`；
  - 首个接口：`POST /api/v1/projects/daily_report_spring_festval_2026/spring-festival/extract-json`；
  - 功能：上传 xlsx 后提取 `byDate` JSON（按“本期/同期/差异”列组解析，含合并单元格补全逻辑）。
- 前端目录规范化协同状态：
  - 春节项目页面已迁移到独立目录 `frontend/src/projects/daily_report_spring_festval_2026/`；
  - `daily_report_25_26` 前端模块已迁移至 `frontend/src/projects/daily_report_25_26/`，与春节项目同层管理；
  - 后端接口路径与鉴权方式保持不变，无需调整调用协议。
- 发布缓存日期配置修复（2026-02-11）：
  - 修复 `dashboard_expression._resolve_date_config_path`，日期文件解析顺序改为：
    1) `projects/<project_key>/config/date.json`；2) `shared/date.json`（全局回退）；
  - 解决 `/dashboard/cache/publish` 在模块化目录下误报 `{\"detail\":\"日期配置文件不存在\"}` 的问题。
- 春节迷你看板联调说明（2026-02-11）：
  - 前端迷你看板页温度数据复用 `daily_report_25_26` 的 `/dashboard` 接口读取数据库气温；
  - 春节项目上传解析接口仍为 `/projects/daily_report_spring_festval_2026/spring-festival/extract-json`；
  - 解析接口会将最近一次结果写入 `runtime/spring_festival_latest_extract.json`，并可通过 `GET /spring-festival/latest-json` 回读；
  - 本轮后端接口无新增变更，继续保持与前端迷你看板的数据契约。
- 核心接口主文件：`backend/projects/daily_report_25_26/api/legacy_full.py`
  - 数据填报：`/data_entry/sheets/{sheet_key}/template`、`/submit`、`/query`
  - 数据分析：`/data_analysis/query`、`/data_analysis/ai_report`、`/data_analysis/ai_settings`
  - 仪表盘：`/dashboard`、缓存发布与取消接口
- 目录职责：
  - `backend/api/`：路由与请求编排
  - `backend/services/`：仪表盘表达式、分析服务、认证、缓存任务、天气导入等业务能力
  - `backend/db/`：ORM 模型与会话（`DailyBasicData`、`ConstantData`、`CoalInventoryData` 等）
  - `backend/sql/`：分析视图与数据结构 SQL
  - `backend/schemas/`：鉴权与接口数据模型
- 本次优化状态：
  - 已清理煤炭库存提交链路的重复函数定义，统一到单一生效实现。
  - 已给模板 JSON 读取增加基于文件变更指纹的内存缓存（`mtime_ns + size`），降低重复读取成本。
  - 已统一部分服务模块顶部注释中的数据路径口径：采用 `shared/project` 目录优先并保留旧路径回退说明。
  - 本轮后端无代码变更，仅同步前端 `jsconfig` 修复的联调说明与项目日志。
  - 已新增模块化结构总览文档：`configs/2.8项目模块化.md`（含旧/新结构与路径映射表）。

## 数据看板缓存发布优化（2026-02-08）

- 发布接口支持窗口参数：
  - `POST /dashboard/cache/publish?days=1..30`
  - 默认 `days=7`，可按运维场景缩短为 1 天快速发布。
- 发布任务执行优化：
  - `backend/services/dashboard_cache_job.py` 在单次发布任务内引入 `shared_metrics_cache`，跨日期复用查询结果，减少重复访问 `groups/sum_basic_data` 视图。
- 看板计算优化：
  - `backend/services/dashboard_expression.py` 移除进度回调中的固定 `sleep(0.1)`，降低人为等待。
  - “1.逐小时气温”改为回溯窗口模式：默认最近 7 天（可由配置 `回溯天数` 调整，范围 1~31）+ 预测天数，不再从历史起点全量扫描。

## 项目模块化第一步（2026-02-08）

- 新增路径兼容层：`backend/services/project_data_paths.py`
  - 规则：优先 `DATA_DIRECTORY/projects/<project_key>/{config|runtime}`，不存在则回退旧平铺目录。
- 已接入模块：
  - `backend/api/v1/daily_report_25_26.py`（模板/分析/审批/常量/API Key/调试文件路径）
  - `backend/services/dashboard_expression.py`（看板配置与 `date.json`）
  - `backend/services/dashboard_cache.py`（`dashboard_cache.json`）
  - `backend/services/data_analysis_ai_report.py`（`api_key.json`）
- 兼容策略：
  - 不要求立即迁移 `backend_data` 现有文件；
  - 若新项目目录文件存在则优先读取；否则保持旧路径行为不变。

## 项目模块化第一步增强（2026-02-08）

- shared 全局文件路径已纳入兼容层：
  - 项目列表：`shared/项目列表.json` → 回退 `项目列表.json`
  - 账户信息：`shared/auth/账户信息.json` → 回退 `账户信息.json`
  - 权限配置：`shared/auth/permissions.json` → 回退 `auth/permissions.json`
  - 全局日期：`shared/date.json` → 回退 `date.json`
- 已接入位置：
  - `backend/api/v1/routes.py`
  - `backend/services/auth_manager.py`
  - `backend/api/v1/daily_report_25_26.py`（项目列表扫描）

## 项目模块化过渡工具（2026-02-08）

- 新增迁移工具函数（`backend/services/project_data_paths.py`）：
  - `ensure_project_dirs(project_key)`：创建项目目录骨架；
  - `bootstrap_project_files(project_key, config_files, runtime_files)`：将旧平铺文件复制到新目录（仅复制缺失文件）；
  - `get_project_file_status(project_key, ...)`：返回新旧文件存在状态与路径。
- 新增项目管理接口（系统管理员可用）：
  - `GET /api/v1/projects/daily_report_25_26/project/modularization/status`
  - `POST /api/v1/projects/daily_report_25_26/project/modularization/bootstrap`
- 用途：
  - 先查询状态，再执行一键初始化；执行后可再次查询确认迁移结果。

## 仪表盘缓存控制（2025-12-01）

- 仪表盘缓存逻辑由 `dashboard_cache.py` 迁移至 `dashboard_cache_job.py`，改为后台任务模式以避免前端请求超时。
- 任务执行时通过 `cache_publish_job_manager` 跟踪进度，支持发布（publish）、取消（cancel）与状态查询（status）。
- 发布过程会遍历配置中的所有业务日期（`date.json` 指定的 `set_biz_date` 及前后若干天），逐一调用 `evaluate_dashboard` 并写入缓存。
- 缓存键格式为 `dashboard:daily_report_25_26:<date>`，内容为完整的 JSON 响应包。

## 数据分析页面接口（2025-11-27）

- `POST /data_analysis/query`：核心查询接口。
  - 接收 `unit_key`、`metrics`、`start_date`、`end_date`、`analysis_mode` 等参数。
  - 根据 `unit_key` 自动路由至 `sum_basic_data`（分公司）或 `groups`（集团/主城区）视图。
  - 支持 `daily`（逐日）与 `range`（累计）模式；累计模式下若勾选气温或常量指标，会自动补齐 `timeline` 逐日明细。
  - 返回结构包含 `rows`（汇总行）、`timeline`（明细行，仅累计模式）、`warnings`（缺失或异常提示）。
- `GET /data_analysis/ai_settings` 与 `POST /data_analysis/ai_settings`：
  - 读取/保存 `backend_data/projects/daily_report_25_26/config/api_key.json`（兼容旧平铺路径回退），管理 Gemini API Key、模型名称、Prompt 指令及开关。
  - 支持“验证开关（enable_validation）”与“非管理员权限（allow_non_admin_report）”。
- `POST /data_analysis/ai_report`（异步）：
  - 接收查询结果快照，将其转换为 HTML 表格与 Prompt，调用 Gemini 生成分析报告。
  - 任务 ID 写入响应，前端轮询 `GET /data_analysis/ai_report/{job_id}` 获取生成状态与最终 HTML。

## 仪表盘设备运行状态板块（2025-12-09）

- **功能新增**：在 `dashboard_expression.py` 中实现了 `_fill_device_status_section` 逻辑，用于填充仪表盘的“11.各单位运行设备数量明细表”。
- **逻辑说明**：
  - 读取配置中的单位列表（如“北海热电厂”）和指标列表（如“运行汽炉数”）。
  - 调用 `_fetch_metrics_from_view` 从 `sum_basic_data` 视图查询当日数值。
  - 将结果填充至 JSON 响应的 `section['本期']` 中，供前端渲染。
  - 该逻辑在 `evaluate_dashboard` 流程末尾自动执行，无需额外 API 调用。

## AI 报告修正（2025-12-30 ~ 2026-01-03）

- **计划比较恢复**：修复了遗留 API `_execute_data_analysis_query_legacy` 漏调计划对比逻辑的问题；Service 层增加单位映射（如 `BeiHai_co_generation_Sheet` -> `BeiHai`），确保计划值能正确匹配。
- **百分比展示**：引入 `PERCENTAGE_SCALE_METRICS`（如 `rate_overall_efficiency`），在生成 `plan_comparison` 与 `rows` 时自动乘以 100，修复了“80% 显示为 0.8%”的问题。
- **自动修订**：AI 报告流程新增“核查-修订”循环。若 Validation 阶段发现数值错误，会自动生成修订 Prompt 让模型重写报告，最大程度减少幻觉。
- **环比展示**：单日模式或 1 天跨度的累计模式下，强制计算上一日/上一周期的环比值，并输出至前端与 AI 报告。
- **配置加密**：恢复了对 `api_key.json` 的伪加密存储（`encrypt_api_key`），内存中透明解密，防止明文 Key 落地。
- **热加载**：修改 AI 配置后立即重置 Gemini Client，无需重启服务即可生效。

## 视图口径调整（2026-01-03）



- **净投诉量**：`analysis_company_sum` 与 `analysis_groups_sum` 视图中的“万平方米省市净投诉量”计算公式调整，改为取终止日的 `sum_season_total_net_complaints` 除以 `amount_heating_fee_area`，不再使用每日累加值，以符合最新的业务统计口径。



## 数据分析环比缩放修正（2026-01-10）



- **缩放对齐**：修正了 `_execute_data_analysis_query_legacy` 在构造 `ringCompare.prevTotals` 时漏调 `_scale_metric_value` 的 Bug。现在“全厂热效率”等百分比指标在环比比较中的“上期累计”值将正确显示为放大 100 倍后的数值（如 85.00% 而非 0.85%），确保了环比增长率计算的准确性。

## 项目模块化第三步（2026-02-08）

- 通用项目管理接口（系统管理员）已上线：
  - `GET /api/v1/projects/{project_id}/modularization/status`
  - `POST /api/v1/projects/{project_id}/modularization/bootstrap`
- 实现位置：
  - `backend/api/v1/routes.py`
  - 依赖 `backend/services/project_data_paths.py` 的目录创建、状态检查、缺失文件复制能力。
- 角色控制：
  - 仅 `系统管理员` 与 `Global_admin` 可执行。
- 兼容说明：
  - 仍保留 `daily_report_25_26` 下原有专用接口；
  - 通用接口可面向后续新项目复用，默认文件清单按当前日报项目模板执行。

## 项目模块化第四步（2026-02-08）

- `backend/api/v1/routes.py` 的迁移文件清单改为“配置驱动优先”：
  1. 优先读取项目配置中的目录化声明：
     - `modularization` / `目录化迁移` / `project_modularization`
     - 支持 `config_files`（或 `config/配置文件`）、`runtime_files`（或 `runtime/运行时文件`）
  2. 若未声明 `config_files`，自动从 `pages` 下各页面 `数据源/data_source` 推断 JSON 文件名；
  3. 若仍为空，再回退默认清单（兼容旧项目）。
- 这意味着新增项目可以仅通过 `项目列表.json` 配置迁移文件清单，无需改后端代码。

## 项目模块化第五步（2026-02-08）

- 新增 `backend/services/project_registry.py`，统一默认项目与内置迁移清单：
  - `get_default_project_key()`
  - `get_project_modularization_files(project_key)`
- 接入范围：
  - `backend/api/v1/routes.py`（通用模块化接口兜底清单来源）
  - `backend/api/v1/daily_report_25_26.py`（项目迁移清单来源）
  - `backend/services/dashboard_cache.py`
  - `backend/services/dashboard_expression.py`
  - `backend/services/data_analysis_ai_report.py`
- 结果：减少 `daily_report_25_26` 字符串与默认清单的散落硬编码，后续多项目扩展更可控。

## 项目模块化第六步（2026-02-08）

- 新增项目路由注册表：`backend/api/v1/project_router_registry.py`
  - 统一管理各项目 `router/public_router` 映射。
- `backend/api/v1/routes.py` 改造为循环挂载：
  - 按注册表自动挂载 `/api/v1/projects/<project_key>` 前缀。
- 效果：新增项目时路由接入改动点更集中，主路由文件稳定性更高。

## 项目模块化第七步（2026-02-08）

- 新增服务：`backend/services/project_modularization.py`
  - 统一封装项目目录化文件清单解析（配置声明 > pages 推断 > 注册表默认清单）。
  - 提供 `load_project_entries/load_project_entry` 供接口层复用。
- 接入调整：
  - `backend/api/v1/routes.py` 改为调用该服务，不再维护本地重复解析函数；
  - `backend/api/v1/daily_report_25_26.py` 的专用模块化接口也改为同一服务解析，确保口径一致。
- 效果：通用与专用接口共享同一解析链路，后续演进只需维护一处实现。

## 项目模块化第八步（2026-02-08）

- 新增项目目录路由入口：
  - `backend/projects/daily_report_25_26/api/router.py`
- 路由注册切换：
  - `backend/api/v1/project_router_registry.py` 改为从项目目录入口导入 `router/public_router`。
- 说明：
  - 当前为“入口迁移完成、实现复用旧模块”的过渡态；
  - 下一阶段将把 `backend/api/v1/daily_report_25_26.py` 的实现按功能继续拆分下沉到项目目录。

## 项目模块化第九步（2026-02-08）

- 新增项目目录实现文件：
  - `backend/projects/daily_report_25_26/api/modularization.py`
- 路由组装更新：
  - `backend/projects/daily_report_25_26/api/router.py` 现组合 `legacy_router + modularization_router`。
- 旧文件收缩：
  - `backend/api/v1/daily_report_25_26.py` 已移除 `/project/modularization/*` 接口实现，避免双维护。
- 结果：
  - 模块化管理接口已“实现归位到项目目录”，但对外 URL 与前端调用不变。

## 项目模块化第十步（2026-02-08）

- 新增项目目录实现文件：
  - `backend/projects/daily_report_25_26/api/dashboard.py`
- 路由组装更新：
  - `backend/projects/daily_report_25_26/api/router.py` 现组合 `legacy_router + modularization_router + dashboard_router`；
  - `public_router` 同时组合 legacy 与 dashboard 的公开接口。
- 旧文件收缩：
  - `backend/api/v1/daily_report_25_26.py` 已移除 `/dashboard*` 相关接口实现与冗余依赖导入。
- 结果：
  - 数据看板接口实现已按项目目录归位，且对外路径保持兼容。

## 项目模块化第十一步（2026-02-08）

- 文件归位：
  - 原 `backend/api/v1/daily_report_25_26.py` 已整体迁移到
    `backend/projects/daily_report_25_26/api/legacy_full.py`。
- 兼容策略：
  - `backend/api/v1/daily_report_25_26.py` 现为轻量兼容层，仅转发导入项目目录实现；
  - 旧导入路径继续可用，避免一次性改动冲击。
- 路由入口：
  - `backend/projects/daily_report_25_26/api/router.py` 已直接引用项目目录 `legacy_full.py`。

## 项目模块化第十二步（2026-02-08）

- `backend_data` 目录已完成数据层归位：
  - 全局文件：`backend_data/shared/`、`backend_data/shared/auth/`
  - 项目文件：`backend_data/projects/daily_report_25_26/config/`、`backend_data/projects/daily_report_25_26/runtime/`
- `shared/项目列表.json` 已更新：
  - 页面数据源路径切换为 `projects/daily_report_25_26/config/...`
  - 增加 `modularization.config_files/runtime_files` 清单
- 兼容性说明：
  - 路径解析已是“shared/project 优先 + 旧路径回退”，因此本次数据归位可平滑衔接。

## 项目模块化第十三步（2026-02-08）

- 全局状态文件归位：
  - `backend_data/shared/status.json`
  - `backend_data/shared/ai_usage_stats.json`
- 服务层路径修正：
  - `workflow_status.py` 使用 `resolve_workflow_status_path()`
  - `ai_usage_service.py` 使用 `resolve_ai_usage_stats_path()`
  - `project_data_paths.py` 新增上述解析函数（shared 优先，旧路径回退）
- 其他归位：
  - `api_key.json.backup` 迁移到 `projects/daily_report_25_26/config/`
  - `shared/项目列表.json` 的 `runtime_files` 清单移除 `ai_usage_stats.json`（改由 shared 统一维护）

## 结构同步（2026-02-08）

- 本轮后端代码无新增改动；主要变更发生在前端全局页面目录归属修复。

## 结构同步（2026-02-11 春节迷你项目提取链路）

- 春节迷你项目接口目录：`backend/projects/daily_report_spring_festval_2026/api/`
  - `xlsx_extract.py`：上传 xlsx、提取 `byDate`、落盘 latest-json、读取 latest-json。
- 本轮修复：
  - `xlsx_extract.py` 新增“Excel 公式转数值”能力（单元格引用与四则运算），用于将 `current/prior` 从公式文本转换为可视化所需数值。
- 结果：
  - mini 看板后续消费的提取 JSON 将优先包含可计算数值，减少“有数据但图表空白”问题。

## 结构同步（2026-02-12 春节迷你看板前端联调）

- 本轮后端接口与服务无新增改动。
- 前端已将 mini 看板气温解析逻辑对齐到主看板数据结构回退策略，以更稳定消费后端 `dashboard` 返回的气温 section（来源仍为 `calc_temperature_data` 视图链路）。

## 结构同步（2026-02-12 春节迷你看板日期窗口调整）

- 本轮后端接口与服务无新增改动。
- 前端已实现北京时间“昨日优先”默认日期与气温图 `±3` 天窗口展示，继续复用现有后端 `dashboard` 数据接口。

## 结构同步（2026-02-12 春节迷你看板气温图显示增强）

- 本轮后端接口与服务无新增改动。
- 前端新增气温图 tooltip 两位小数显示、业务日期竖线与业务日期本期/同期温度点位标注，数据来源仍沿用既有 `dashboard` 接口。

## 结构同步（2026-02-12 春节迷你看板气温标签策略调整）

- 本轮后端接口与服务无新增改动。
- 前端将气温图改为“全点位标签默认显示 + 业务日期竖线无文字标签”，继续复用既有 `dashboard` 接口数据。

## 结构同步（2026-02-12 春节迷你看板显示口径调整）

- 本轮后端接口与服务无新增改动。
- 前端新增气温标签防碰撞、浅色业务日期竖线，并将四卡差异展示口径调整为“绝对增减量”。

## 结构同步（2026-02-12 春节迷你看板煤耗口径图重构）

- 本轮后端接口与服务无新增改动。
- 前端将煤耗图重构为“业务日期当日各口径耗原煤量对比”，并完成四卡配色与主看板风格对齐。

## 结构同步（2026-02-12 春节迷你看板煤耗图同期补齐）

- 本轮后端接口与服务无新增改动。
- 前端煤耗图已从单柱扩展为“本期+同期”双柱对比，单位继续使用“吨”。

## 结构同步（2026-02-12 春节迷你看板精度与庄河同期规则）

- 本轮后端接口与服务无新增改动。
- 前端补充“庄河同期优先取剔除指标”规则，并按业务要求统一卡片/图表精度与煤耗图配色。

## 结构同步（2026-02-12 庄河同期来源修正）

- 本轮后端接口与服务无新增改动。
- 前端已将庄河口径同期来源从“剔除指标泛匹配”收敛为“其中：张屯原煤消耗量”优先匹配。

## 结构同步（2026-02-12 投诉量分项展示重构）

- 本轮后端接口与服务无新增改动。
- 前端将投诉量分项展示改为“双图（总/净）+一表”，并在两张图中叠加本期气温折线。

## 结构同步（2026-02-12 投诉分项布局与视觉优化）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图布局调整为半屏并排，并完成清新化样式与无横线图表设置。

## 结构同步（2026-02-12 投诉图气温线业务日期截断）

- 本轮后端接口与服务无新增改动。
- 前端在投诉双图中将“本期气温”折线限制到业务日期，业务日期后的预报点不再绘制。

## 结构同步（2026-02-12 投诉柱业务日期截断）

- 本轮后端接口与服务无新增改动。
- 前端已将投诉双图中的本期/同期柱同样限制到业务日期，业务日期后数据不绘制。

## 结构同步（2026-02-12 投诉区统一业务日期可见范围）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图与下方表统一限制到业务日期可见范围，并移除了气温线数值标签。

## 结构同步（2026-02-12 投诉图横轴与柱形观感优化）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图横轴改为 `MM-DD`，并通过固定窗口日期轴与柱宽间距优化改善早日期场景的图面比例。

## 结构同步（2026-02-12 投诉图全业务日期轴）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图横轴调整为完整业务日期范围，业务日期后以空数据保留右侧空间。

## 结构同步（2026-02-12 mini看板PDF导出入口）

- 本轮后端接口与服务无新增改动。
- 前端在 mini 看板顶部新增“下载PDF”按钮，复用浏览器打印导出能力。

## 结构同步（2026-02-12 mini看板PDF直出与差值+0修正）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出从浏览器打印流升级为 `html2canvas + jsPDF` 直出下载，并完善导出中按钮状态反馈。
- 前端同步修正顶部四卡差值显示规则：当差异为 0 时显示 `+0`（按字段既定精度）。

## 结构同步（2026-02-12 mini看板PDF链路改为主看板同款）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出实现切换为与主看板一致的全局脚本链路（`window.html2canvas` + `window.jspdf.jsPDF`），并移除本地模块依赖以消除 `jspdf` 模块错误风险。

## 结构同步（2026-02-12 mini看板PDF边距优化）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出内容增加统一页边距（6mm），修复左右贴边裁切观感。

## 结构同步（2026-02-12 mini看板新增原煤/设备明细表）

- 本轮后端接口与服务无新增改动。
- 前端在春节 mini 看板新增两块表格能力：  
  1) 原煤对比图下方新增“春节期间每日各口径本期/同期原煤消耗量”宽表（首列含气温，按业务日期截断）；  
  2) 页面底部新增“各单位运行设备数量明细表”（业务日期），口径覆盖北海（含北海水炉）、香海、金州、北方、金普、庄河。

## 结构同步（2026-02-12 mini看板设备表样式对齐）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板设备明细表调整为与主看板参考一致的分组组合样式（炉机组态/调峰水炉/燃煤锅炉），并过滤本期/同期均为 0 的冗余设备项。

## 结构同步（2026-02-12 mini看板设备组合项换行显示）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板设备表中的组合项改为纵向逐行展示，提升汽炉/汽轮机数值的左右对应可读性。

## 结构同步（2026-02-12 mini看板原煤明细列结构调整）

- 本轮后端接口与服务无新增改动。
- 前端将原煤明细表调整为“口径单列 + 单元格本期/同期”形式，不再拆分为本期列和同期列。

## 结构同步（2026-02-12 mini看板原煤明细分级表头）

- 本轮后端接口与服务无新增改动。
- 前端将原煤明细表改为分级表头：父级口径 + 子级本期/同期，匹配业务侧对“集团汇总下分本期/同期”的展示要求。

## 结构同步（2026-02-12 mini看板风格切换与春节主题）

- 本轮后端接口与服务无新增改动。
- 前端为春节 mini 看板新增主题切换能力（默认/春节氛围）及本地持久化，并增加春节风格背景与卡片/表格配色模板。

## 结构同步（2026-02-12 mini看板春节主题可读性修复）

- 本轮后端接口与服务无新增改动。
- 前端修复春节主题下顶部四卡可读性，并补充轻量节庆装饰元素（灯笼与主题徽标），在增强节日氛围的同时保持数据区清晰。

## 结构同步（2026-02-12 mini看板PDF清晰度提升）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出渲染倍率从 2 提升到 3，以约 1.5 倍像素密度提升导出清晰度。

## 结构同步（2026-02-12 mini看板标题文案调整）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板主标题文案由“春节简化数据看板”调整为“春节数据看板”。

## 结构同步（2026-02-12 主看板气温读取切换至日聚合视图）

- 修改文件：`backend/services/dashboard_expression.py`
- 核心调整：
  - 将第1节气温填充由“查询 `temperature_data` 小时序列”切换为“查询 `calc_temperature_data` 日级统计”；
  - 新增 `_fetch_daily_temperature_stats_map` 读取 `max_temp/min_temp/aver_temp`；
  - `_fill_temperature_block` 改为按日期写入 `{max, min, avg}` 日级结构。
- 口径说明：
  - 某一时期平均气温仍按 `AVG(aver_temp)` 计算，即“每日平均气温的平均值”。
- 验证结果：
  - `python -m py_compile backend/services/dashboard_expression.py` 通过。

## 结构同步（2026-02-12 主看板第1节命名切换为日均气温）

- 修改文件：`backend/services/dashboard_expression.py`、`backend_data/projects/daily_report_25_26/config/数据结构_数据看板.json`、`backend_data/projects/daily_report_25_26/config/dashboard_frontend_config.json`
- 调整内容：
  - 第1节命名由“逐小时气温”改为“日均气温”；
  - 配置中的 `key/title/source_section` 与 `数据来源` 已同步切到 `1.日均气温` + `calc_temperature_data`；
  - 后端 section 解析保留旧键兼容（`1.逐小时气温`）以平滑过渡缓存。

## 结构同步（2026-02-12 下线项目模块化管理接口）

- 修改文件：`backend/projects/daily_report_25_26/api/router.py`
- 删除文件：`backend/projects/daily_report_25_26/api/modularization.py`
- 清理内容：
  - `daily_report_25_26` 项目路由不再挂载 `modularization_router`；
  - 项目专属 `/project/modularization/status` 与 `/project/modularization/bootstrap` 接口下线。
- 验证结果：
  - `python -m py_compile backend/projects/daily_report_25_26/api/router.py backend/api/v1/routes.py` 通过。

## 结构同步（2026-02-12 春节迷你看板“金镶玉”主题重构）

- 本轮后端接口与服务无新增改动。
- 前端对 `SpringFestivalDashboardView.vue` 的“春节氛围”模式进行了视觉重构，引入了深红暗纹背景、暖白卡片、金色边框及动态挂饰动画，提升了节日模式下的数据可读性与美观度。

## 结构同步（2026-02-12 数据展示页导出 Excel 504 超时修复）

- 本轮后端接口与服务无新增改动。
- 前端导出链路调整为串行 `runtime/spec/eval` + 超时中断 + 504 重试与可读报错，减少网关超时导致的导出失败。

## 结构同步（2026-02-12 修复 frontend/jsconfig 报错）

- 本轮后端接口与服务无新增改动。
- 前端 `frontend/jsconfig.json` 完成路径别名与 `include` 范围修正，用于提升工程索引与模块解析稳定性。

## 结构同步（2026-02-12 登录“账户信息文件缺失”部署兼容修复）

- 修改文件：`backend/services/project_data_paths.py`、`backend/services/auth_manager.py`
- 调整内容：
  - `resolve_accounts_path` 增加多路径候选（含 `accounts.json`）；
  - `resolve_permissions_path` 增加兼容候选路径；
  - 账户/权限文件缺失时报错中附带实际解析路径，提升线上排障效率。
- 验证结果：
  - `python -m py_compile backend/services/project_data_paths.py backend/services/auth_manager.py` 通过。

## 结构同步（2026-02-15 春节看板卡片文案修正）

- 本轮后端接口与服务无新增改动。
- 前端将春节看板顶部卡片文案从“当日集团标煤消耗（剔除庄河改造锅炉房）”调整为“当日集团原煤消耗（剔除庄河改造锅炉房）”，不涉及后端数据口径变更。

## 结构同步（2026-02-15 春节看板原煤图标题补充口径）

- 本轮后端接口与服务无新增改动。
- 前端将原煤对比图标题从“当日各口径耗原煤量对比”调整为“当日各口径耗原煤量对比（剔除庄河改造锅炉房）”，仅为展示文案更新。

## 结构同步（2026-02-15 春节看板两张表新增合计行）

- 本轮后端接口与服务无新增改动。
- 前端在春节看板页面为“当日各口径耗原煤量对比（剔除庄河改造锅炉房）”和“投诉量分项”两张表新增末尾“合计”行展示；其中“净投诉量（本期/同期）”合计单元格固定显示 `-`，不做汇总。

## 结构同步（2026-02-15 春节看板两张表去除非气温单位）

- 本轮后端接口与服务无新增改动。
- 前端将春节看板两张表中的原煤消耗量/投诉量列调整为纯数字展示（不带“吨/件”单位），气温列仍保留“℃”。

## 结构同步（2026-02-15 春节看板气温取数项目键修复）

- 本轮后端接口与服务无新增改动。
- 前端修复春节看板气温接口调用的项目键传参：不再固定请求 `daily_report_25_26`，改为按当前页面 `projectKey` 请求对应项目看板数据，减少无关数据包加载并修复跨项目取数偏差。

## 结构同步（2026-02-15 春节看板气温空白修复：新增轻量温度接口）

- 修改文件：`backend/projects/daily_report_25_26/api/dashboard.py`
- 新增接口：`GET /api/v1/projects/daily_report_25_26/dashboard/temperature/trend`
- 能力说明：
  - 按 `show_date/start_date/end_date` 查询 `calc_temperature_data`，返回本期 `main` 与同期 `peer` 的日均气温映射；
  - 用于春节看板气温曲线，避免前端再请求全量 `/dashboard` 数据包。
- 兼容说明：
  - 既有 `/dashboard`、`/dashboard/date` 等接口行为不变；新增接口为向后兼容扩展。

## 结构同步（2026-02-15 春节气温接口路由归位到 spring 项目）

- 新增文件：`backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py`
- 修改文件：`backend/projects/daily_report_spring_festval_2026/api/router.py`
- 调整内容：
  - 在 spring 项目下新增公开接口：`GET /api/v1/projects/daily_report_spring_festval_2026/spring-dashboard/temperature/trend`；
  - spring 项目 `public_router` 已挂载该接口，前端可在项目内路径直接访问。
- 结果：
  - 春节看板温度接口职责与路由归属回归到 spring 模块边界，避免前端跨项目 API 路径耦合。

## 结构同步（2026-02-15 春节气温接口增加温度原表兜底）

- 修改文件：`backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py`
- 调整内容：
  - `spring-dashboard/temperature/trend` 的日均温度查询增加兜底逻辑：  
    - 优先查 `calc_temperature_data`；  
    - 若为空，回退查 `temperature_data` 按天 `AVG(value)` 聚合。  
- 结果：
  - 避免因温度聚合视图未刷新导致接口返回空集，提升气温曲线可用性。

## 结构同步（2026-02-15 春节气温接口前端自动回退）

- 本轮后端接口与服务无新增改动。
- 前端为 spring 气温取数增加“主路径失败自动回退”机制：优先调用 spring 项目温度接口，异常时临时回退到 `daily_report_25_26` 轻量温度接口，降低发布切换窗口期空白风险。

## 结构同步（2026-02-15 春节气温链路增加老 dashboard 最终兜底）

- 本轮后端接口与服务无新增改动。
- 前端在现有回退机制上新增第3层兜底：当轻量温度接口不可用时，回退到历史 `daily_report_25_26` 的 `/dashboard` 接口，确保无需后端重启也能恢复气温曲线。

## 结构同步（2026-02-15 页面临时调试增强）

- 本轮后端接口与服务无新增改动。
- 前端新增温度链路调试可视化（默认开启），用于直接定位接口命中层级与数据映射状态，不影响后端协议。

## 结构同步（2026-02-15 温度图渲染强制可视化调试）

- 本轮后端接口与服务无新增改动。
- 前端温度图增加显式渲染参数与 ECharts 入参回显（`echartsPayload`），用于排查“数据存在但曲线不显示”的前端渲染异常。

## 结构同步（2026-02-15 EChart 组件渲染稳态修复）

- 本轮后端接口与服务无新增改动。
- 前端增强 EChart 组件初始化与尺寸监听（`nextTick` 应用 option + `ResizeObserver` + 强制 resize），用于提升温度图在布局切换场景下的可见性稳定性。

## 结构同步（2026-02-15 温度图样式回退）

- 本轮后端接口与服务无新增改动。
- 前端已将温度图视觉配置回退至既定展示样式，仅保留图表组件层稳定性修复。
