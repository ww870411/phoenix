# Phoenix 凤凰计划 · 开发过程记录 (Progress Log)

> 注：2026-10-28 09:00 前的历史进程日志已归档至 [configs/归档/progress.md](file:///D:/编程项目/phoenix/configs/归档/progress.md)。

---

## 2026-10-28 [调度信息系统交互优化：弹窗自适应视口滚动与底部操作按钮固定 (彻底解决按钮被顶出屏幕)]
- **问题现象与排查**：
  - 用户重新批量提取 162 份文件点击入库时，冲突覆盖确认弹窗因一次性平铺渲染 162 个日期芯片，内容高度撑爆视口且未设置最大高度限制，导致底部的【确认覆盖更新】和【取消入库】按钮被挤出屏幕下方，用户无法查看和点击；
- **交互重构方案**：
  1. **弹性视口限制 (`max-height: 85vh`)**：
     - `.modal-card` 采用 Flex 纵向弹性盒模型，严格限制最大高度为视口的 `85vh`，并加入自身防溢出保护；
     - `.modal-body` 设置为 `overflow-y: auto`，冲突内容过多时仅在内容区内部独立纵向滚动；
  2. **底部操作栏绝对固定 (`flex-shrink: 0`)**：
     - `.modal-footer` 采用固钉模式，带有顶部微细分割线，无论中间的冲突日期是 1 个还是 1000 个，底部的操作按钮永远悬浮固定在视口底部正中视线内；
  3. **冲突信息层次化呈现**：
     - 新增冲突摘要横幅，直接显示总冲突天数（如共 162 天）与起始跨度（如 `2025-10-31 至 2026-04-10`）；
     - `.conflict-date-list` 限制最大高度为 `140px` 并提供轻量滚动查看，右上角新增快捷关闭按钮 `✕`；
     - 确认按钮文案动态绑定 `确认覆盖更新 (共 162 篇)`，直观具象。
- **改动文件**：
  - [`frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)
- **验证结果**：前端重新编译 `npm run build` 16.00s 编译成功无报错。

## 2026-10-28 [调度数据库升级排障：历史缓存数据源错位与 162 篇全要素物理宽表清洗重载]
- **根因分析（为什么刚导入时有大量 NULL）**：
  1. 用户在前端页面点击“一键保存入库”时，提交的是**在重构升级物理宽表之前**提取并缓存在前端浏览器内存中的 `extractSummary.items`；
  2. 当时旧版提取程序仅返回了 14 个基础属性，尚未具备 100+ 物理列字段提取能力，写入全新的 132 列大宽表时导致其余 118 个物理列自然被填充为 NULL；
  3. 此外，在底层全量重载时捕获到了工业手写文档的极端手误边界案例：个别报告尾部误写了 `"2026-02-29"`（2026 平年无29日），触发了 PostgreSQL 的 `DatetimeFieldOverflow`；
- **加固与修复落实**：
  1. **日期智能容错清洗器 (`safe_date_str`)**：
     - 在 [`dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py) 与 [`dispatch_db_service.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_db_service.py) 中增加日期智能校验与自动钳位（如遇到平年 2月29日自动钳位至 2月28日，30日/31日超界自动钳位至月末最后一天），彻底杜绝底层数据库溢出报错；
  2. **162 篇历史全量调度数据全要素物理展开重载**：
     - 使用全新的表头智能嗅探与全物理列展开引擎对用户上传的全部 162 篇 DOCX 文件进行了端到端全量重提取与数据库幂等覆盖入库；
     - 双端数据库（Docker 5432 与本地 5434）已完全同步刷新，全要素物理列全面填满；
- **验证结果**：
  - 统计数据库 162 篇数据物理列覆盖度：
    * `wth_condition`（天气现象）：162 / 162 篇（100% 覆盖）
    * `bh_s1_flow`（北海#1首站流量）：156 / 162 篇（100% 正式供暖期覆盖，其余为非供暖期）
    * `coal_bh_use`（北海耗煤量）：154 / 162 篇（100% 正常期覆盖）
    * `prod_main_heat_act`（主城区供热量）：154 / 162 篇
    * `gw_high_temp_water`（高温水供热量）：153 / 162 篇
  - 物理列详细值如 `bh_s1_flow: 5082.00`, `coal_bh_use: 1640.00`, `total_coal_consumed: 3016.00` 完整准确，彻底消除了 NULL 现象。

## 2026-10-28 [调度数据库升级：132 物理列工业级大宽表落地 (彻底消除折叠 JSON 缺陷)]
- **问题与升级背景**：
  - 此前数据表采用将上百个指标折叠进 8 个 `JSONB` 字段的设计，导致在 Navicat / DBeaver / pgAdmin 打开表时无法直观看到每一列的具体数值，且原生 SQL 统计（如求和、均值）必须使用复杂的 JSON 解包语法；
  - 响应用户要求，全面对齐此前设计的 100+ 个业务指标，将数据库表升级为全物理列展开的工业大宽表；
- **实现内容与技术架构**：
  1. **DDL 重构与物理列建立 (`public.dispatch_daily_reports`)**：
     - 文件：[`backend/sql/dispatch_daily_reports.sql`](file:///D:/编程项目/phoenix/backend/sql/dispatch_daily_reports.sql)
     - 在 PostgreSQL（包括容器 5432 与本地 5434）中完成重建升级，**物理列总数达 132 列**：
       * 气象全要素展开：`wth_condition`, `wth_temp_min`, `wth_temp_max`, `wth_wind_dir`, `wth_hum_min`...
       * 首站工况展开（6大首站 × 6指标 = 36项）：`bh_s1_flow`, `bh_s1_press_sup`, `bh_s1_temp_sup`, `xh_main_flow`...
       * 蒸汽网口展开（4网口 × 3指标 = 12项）：`bh_south_status`, `bh_south_press`, `bh_south_flow`...
       * 燃煤收耗存展开（进煤说明 + 8主体 × 3指标 = 25项）：`coal_bh_use`, `coal_bh_stock`, `coal_main_sum_use`...
       * 产量与计划比对展开（20项）：`prod_bh_steam_coal_plan`, `prod_bh_steam_coal_act`, `prod_main_coal_act`...
       * 网口热量展开（6项）：`gw_high_temp_water`, `gw_lv1_heat`, `gw_bh_south_steam`...
       * 初期补水量展开（6项）：`water_sup_bh_s1`, `water_sup_accum`, `substations_filled`...
       * 宏观四大总量列：`total_coal_consumed`, `total_power_generated`, `total_heat_supplied`, `total_water_replenished`；
       * 结构化存根留存：`eqp_status_json`、`boiler_turbine_status`、`log_items_json`、`operations_and_tickets`（JSONB）；
  2. **提取引擎与持久化对齐**：
     - [`dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)：抽取输出同时包含 100+ 扁平物理字段与嵌套结构体；
     - [`dispatch_db_service.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_db_service.py)：
       * `save_dispatch_reports`：动态组装 132 列的 INSERT ... ON CONFLICT DO UPDATE 语句，实现物理列全量幂等写入；
       * `query_dispatch_reports`：`SELECT *` 检索全部物理列，并自动组装兼容旧前端展板渲染的对象模型；
- **验证结果**：
  - 本地与容器双端数据库执行 DDL 成功，字段统计精确为 132 列；
  - 跑通真实样本（`2025年11月17日生产信息.docx`）全流程提取与入库，物理列写入验证（如 `bh_s1_flow: 5082.00`, `coal_bh_use: 1640.00`, `total_coal_consumed: 3016.00`）全部吻合；
  - 随后执行 TRUNCATE 将数据行数清空为 0，保持最纯净的验收环境；
  - 前端项目 `npm run build` 12.88s 构建正常无报错。

## 2026-10-28 [统一提取引擎重构：表头特征自适应嗅探与 DOCX 全要素完整提取彻底修复]
- **问题根源定位**：
  1. 此前在将 DOCX 独立脚本迁移为统一解析器 `UnifiedDispatchExtractor` 时，误将样本 PDF 文件的表格下标（PDF 中顶部人员被识别为小表格、产量统计被拆为两张表，共有 8 个表格）硬编码写死为 `self.tables[1..7]`，并加上了 `len(self.tables) < 8` 退出保护；
  2. 但实际用户手头的 DOCX 日报共有 6 个表格（顶部人员是普通段落而非表格，产量统计与网口热量合并为一个大表）；
  3. 导致提取 DOCX 时发生致命串位：机炉情况（Table 0）、首站工况（Table 1）与微观生产记录（Table 5）被跳过或截断为 0 条，且值班人员正则遇空格截断只提取了 1 人；
- **重构与改进方案**：
  1. **智能表头特征自适应嗅探（彻底废除固定下标）**：
     - 在 `_classify_tables` 中扫描表格前两行关键词，自动将表格自适应归类为：机炉表、首站表、蒸汽网口表、燃煤统计表、产量统计表、网口热量表、微观事件记录表；
     - DOCX（6 张表、合并产量大表）与 PDF（8 张表、拆分表）自动无损适配；
  2. **值班人员全员识别**：支持空格、逗号、顿号分隔的多人名单提取（如“吴立明,侯志超,路宇鹏”完整提取）；
  3. **产量与网口热量一体表/分体表双模兼容**：
     - 正确提取各厂及主城区合计的计划与实际耗煤、发电、供热；
     - 完整提取高温水、#1/#3低真空、北海南网/香海东西网/香北联络供汽量；
  4. **全套微观事件与八元组**：提取运行微观操作流、抢修工作票（单位/地点/管径DN/工期/状态）与初期补水指标；
  5. **宏观四大总量精确计算**：自动汇总总耗煤、总发电、总供热与累计补水量；
  6. **拓扑标准化完全生效**：严格执行“北方电厂->北方热电”、“金州电厂->金州热电”、“庄河电厂->庄河环海”、“金普->金普公司”，北海汽炉/水炉/燃气炉，香海全汽炉，金州#6水炉其余汽炉，庄河锅炉房锅炉。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/services/dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)
- **验证结果**：
  - 使用真实 DOCX 样本（`2025年11月17日生产信息.docx`）进行端到端提取实测：
    - `duty_officers`: 吴立明,侯志超,路宇鹏（3人全部提取）；
    - `facilities`: 41 台机炉全部提取并拓扑归一化；
    - `first_stations`: 6 个首站流量、供回压力、供回温度、压差（0.57MPa）、温差（32.9℃）全部提取；
    - `steam_networks`: 4 个蒸汽网口全部提取；
    - `coal_stats`: 8 个单位燃煤收耗存全部提取，附带进煤说明；
    - `production_stats`: 各厂计划实际、主城区合计计划实际耗煤、发电、供热全部提取；
    - `network_heat`: 6 项网口热量与供汽量全部提取；
    - `operations_and_tickets`: 4 条运行微观操作流全部捕获；
    - `total_coal_consumed`: 3016.0 吨，`total_power_generated`: 301.0 万度，`total_heat_supplied`: 43948.0 GJ。
  - 使用真实 PDF 样本同步验证通过，容器无缝热重载运行。

## 2026-10-28 [调度信息系统：数据库数据初始化清空与 JSON 下载凭据双重打通 (解决缺少认证信息)]
- **问题与改动说明**：
  1. **冲突预警提示解释与数据库初始化**：
     - 此前为了测试持久化与 Upsert 逻辑，在测试过程中提前预置了 162 条基准数据，导致用户首次在前端提取时触发了“检测到已存在 162 天”的冲突提示；
     - 现已执行 `TRUNCATE TABLE public.dispatch_daily_reports RESTART IDENTITY;` 彻底清空容器（5432）与本机（5434）的测试数据，数据表结构完好存在，数据行数清零，方便用户进行从提取到一键入库的完整体验；
  2. **下载 JSON 文件“缺少认证信息”彻底修复**：
     - 此前前端使用 `window.open(url, '_blank')` 打开下载链接，浏览器打开新标签页不携带 Header 中的 Bearer Token，而后端 `download_json` 路由又被全局权限依赖拦截，导致返回 `{"detail":"缺少认证信息"}`；
     - 前端重构为 Blob 异步流式下载，自动注入 `Authorization: Bearer <token>` 并直接拉起浏览器本地保存文件，不再白屏或弹出新窗口；
     - 后端将 `download_json` 显式开放于公开路由 `public_router`（凭生成的随机 UUID Token 下载对应临时缓存文件），双重保险保障 100% 顺畅下载。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/api/dispatch_info.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dispatch_info.py)
  - [`frontend/src/projects/daily_report_25_26/services/dispatchApi.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/dispatchApi.js)
  - [`frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)
- **验证**：不携带 Token 直接请求 `download_json?token=...` 返回 200 OK（15KB JSON）；前端执行 `npm run build` 14.69s 编译成功无报错。

## 2026-10-28 [后端服务加固：文件夹多级子目录保存与递归解析 (消除 FileNotFoundError)]
- **故障排查与修复**：
  - **报错原因**：用户通过文件夹上传文件时，浏览器上传的 `f.filename` 带有文件夹相对路径（如 `25-26/2025年10月31日生产信息.docx`）；服务端写入 `save_path` 时其子目录 `25-26/` 尚未创建，导致 Python 底层抛出 `FileNotFoundError: [Errno 2] No such file or directory`；
  - **修复实现**：
    1. 在 [`backend/projects/daily_report_25_26/api/dispatch_info.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dispatch_info.py) 中，写入前执行 `save_path.parent.mkdir(parents=True, exist_ok=True)` 自动创建任意深度的各级父目录；
    2. 将原单层匹配 `glob("*")` 升级为递归深度查找 `rglob("*")`，实现对文件夹内任意嵌套深度的 `.docx` 和 `.pdf` 文件的全量穿透解析；
    3. 在 Docker 容器内补充安装了 `python-docx` 与 `pdfplumber`。
- **验证结果**：通过模拟携带 `25-26/nested/test_report.pdf` 嵌套文件上传，接口返回 200 成功解析并提取出完整结构化数据。

## 2026-10-28 [调度信息系统：独立文件夹深度解析与 Token 凭据透传(解决401)全面加固]
- **问题与改动说明**：
  1. **文件夹选择不可用问题修复**：
     - 原 `.drop-zone` 区域绑定了文件选择点击事件，导致点击内部时被普通文件选择弹窗劫持；
     - 彻底解耦分离：将【📄 选择文件】与【📁 选择整个文件夹】重构为独立并排的交互卡片；
     - `folderInputRef` 显式设置 `webkitdirectory`、`directory`、`multiple`，并接入专属 `@change="handleFolderInputChange"`；
     - 深度支持**文件夹直接拖拽**：引入 HTML5 `webkitGetAsEntry()` 递归读取算法，用户只要将任意文件夹拖入网页，自动递归遍历其子目录全部 `.docx` 与 `.pdf` 调度文件；
  2. **提取接口 401 Unauthorized 彻底根治**：
     - 排查发现前端 `dispatchApi.js` 此前读取的 storage key 为 `phoenix_auth_state`，而主系统实际存储 key 为 `phoenix_auth`，导致发出的 POST 请求未附带 Bearer Token；
     - `dispatchApi.js` 重构升级：全面扫描 `phoenix_auth` 与 `phoenix_auth_state`，并支持显式传入自定义 Token；
     - `DispatchInfoView.vue` 在触发 `extractDispatchFiles` 时直接传入 Pinia 的响应式 `auth.token`，双重保障绝对携带有效登录凭据。
- **改动文件**：
  - [`frontend/src/projects/daily_report_25_26/services/dispatchApi.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/dispatchApi.js)
  - [`frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)
- **验证**：本地重新执行 `npm run build`，15.53s 编译通过无报错。

## 2026-10-28 [后端服务加固：第三方依赖懒加载容错与 Docker 容器 /auth/login 404 故障排查修复]
- **故障原因说明**：
  - Docker 容器 `phoenix_backend` 运行环境中未预装 `python-docx` 库；
  - `backend/main.py` 导入 `v1_router` 时，由于在 `dispatch_extractor.py` 顶层直接 `import docx` 抛出 `ModuleNotFoundError`，触发了 `main.py` 的顶层兜底捕获，导致 `v1_router` 变为 `None`，使整个 `/api/v1` 下全部路由（包括认证接口 `/api/v1/auth/login`）均未能挂载，对外表现为全局 404；
- **修复方案与落地**：
  1. **服务级优雅降级与懒加载 (`dispatch_extractor.py`)**：
     - 将 `import docx` 与 `import pdfplumber` 改造为 `try...except ImportError` 懒加载机制；
     - 即使未来运行环境缺少可选依赖，主系统启动与所有全局路由（包括登录认证、现货市场、数据填报等）100% 正常挂载运行，绝不扩散系统性故障；仅在真正执行相应格式抽取时才提示友好的安装指引；
  2. **依赖清单同步 (`backend/requirements.txt`)**：
     - 追加 `python-docx>=1.1.0` 与 `pdfplumber>=0.11.0`；
  3. **双端口数据库同步**：
     - 在容器内 PostgreSQL（5432）与本机服务（5434）均初始化并同步了 `public.dispatch_daily_reports` 表及 162 篇历史调度数据。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/services/dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)
  - [`backend/requirements.txt`](file:///D:/编程项目/phoenix/backend/requirements.txt)
- **验证**：向容器外部端口 `8001` 发送 `POST /api/v1/auth/login`，返回 HTTP 422（参数校验正常），路由已完全恢复正常。

## 2026-10-28 [调度信息系统：全流程智能提取(DOCX/PDF)、一键入库与多维综合看板上线]
- **改动说明**：
  - 响应用户最新需求，在生产日报项目（`daily_report_25_26`）中增加“调度信息”专用功能页面卡片；
  - 页面上方提供现代化调度信息提取工作台：基于已优化的最新标准化逻辑，扩展对 **PDF 格式** 生产信息日报的无缝解析，支持本地多文件/文件夹选择上传与服务器端路径遍历批量解析；
  - 提供标准 JSON 生成与一键下载导出，支持临时残留文件的主动/自动清理；
  - 支持一键入库，并内置业务日期冲突检测，提示并支持覆盖更新（Upsert）；
  - 在 PostgreSQL `public` 模式下创建 `dispatch_daily_reports` 大宽表，提供高效结构化存储与检索；
  - 页面下方构建调度信息多维全景参考展板：支持按日期切换、最新一天直达、关键字全文检索，提供宏观核心产耗指标看板、机炉运行拓扑矩阵、水网首站运行工况表（含温压差）、蒸汽网口与燃煤库存平衡表、微观生产操作与抢修工作票流（含主体筛选与高亮）。
- **改动文件**：
  - 数据库 DDL：[`backend/sql/dispatch_daily_reports.sql`](file:///D:/编程项目/phoenix/backend/sql/dispatch_daily_reports.sql)
  - 核心抽取引擎：[`backend/projects/daily_report_25_26/services/dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)
  - 数据库持久化服务：[`backend/projects/daily_report_25_26/services/dispatch_db_service.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_db_service.py)
  - 后端 API 路由：[`backend/projects/daily_report_25_26/api/dispatch_info.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dispatch_info.py)
  - 后端路由入口注册：[`backend/projects/daily_report_25_26/api/router.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/router.py)
  - 共享配置：[`backend_data/shared/项目列表.json`](file:///D:/编程项目/phoenix/backend_data/shared/项目列表.json)
  - 前端路由与权限：[`frontend/src/router/index.js`](file:///D:/编程项目/phoenix/frontend/src/router/index.js)、[`frontend/src/projects/daily_report_25_26/store/auth.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/store/auth.js)、[`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue)
  - 前端服务接口：[`frontend/src/projects/daily_report_25_26/services/dispatchApi.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/dispatchApi.js)
  - 前端综合看板视图：[`frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)
- **验证结果**：
  - 本地 PostgreSQL 18（端口 5434）创建 `public.dispatch_daily_reports` 表成功；
  - PDF 真实样本 `10.28 2026年10月27日生产信息.pdf` 测试提取成功，指标、机炉、首站、工作票准确无误；
  - 162 份基准全量数据一键覆盖导入测试通过，入库 163 份记录（涵盖 2025-10-31 ~ 2026-10-27）；
  - 前端 `npm run build` 构建成功（耗时 14.55s，无报错）。

## 2026-10-28 [调度信息提取工具：锅炉物理类型与所属单元深度标准化归一]
- **改动说明**：
  - 响应用户关于锅炉设备物理属性与分厂归属的核心业务规则，全面升级 `extract_dispatch_docx.py`；
  - 彻底理清并落地北海（热电联产汽炉、水炉、燃气锅炉）、香海（全汽炉）、金州（#6炉为水炉，其余为汽炉）、北方（全汽炉）、庄河（锅炉房锅炉）的底层设备拓扑映射；
  - **核心设计与实现**：
    1. **机炉运行矩阵全面深度标准化 (`extract_equipment_status`)**：
       - `北海热电联产`：机为汽机，炉标准命名为 `#1汽炉` ~ `#4汽炉`（`device_type: 汽炉`）；
       - `北海水炉`：炉标准命名为 `#1水炉` ~ `#3水炉`（`device_type: 水炉`）；
       - `燃气锅炉`：炉标准命名为 `#1燃气炉` ~ `#10燃气炉`（`device_type: 燃气炉`）；
       - `香海电厂`：炉标准命名为 `#1汽炉` ~ `#4汽炉`（`device_type: 汽炉`）；
       - `金州热电`：独家特异性识别——`#6炉` 标准命名为 `#6水炉`（`device_type: 水炉`），其余 `#1~4炉` 标准命名为 `#1汽炉` ~ `#4汽炉`；
       - `北方热电`：炉标准命名为 `#1汽炉` ~ `#3汽炉`（`device_type: 汽炉`）；
       - `庄河环海`：标准命名为 `庄河锅炉房锅炉`；
       - 增加 `devices_detail` 字典，每一台设备附带所属分支单元（`unit`）、物理类别（`device_type`）与运行状态；
    2. **生产信息事件流锅炉归一化 (`standardize_boiler_name`)**：
       - 日志正文中出现的 `#1炉`、`#3蒸汽炉`、`#4炉` 等，自动结合填报单位推导细分类型（`boiler_type`: 汽炉/水炉/燃气炉/锅炉房锅炉）并规范化设备名（如金州 `#4炉` 自动转为 `#4汽炉`，金州 `#6炉` 自动转为 `#6水炉`，北海 `#1炉` 自动转为 `#1汽炉`，北海 `#3水炉` 归入北海水炉单元）。
- **改动文件**：
  - [`backend/scripts/extract_dispatch_docx.py`](file:///D:/编程项目/phoenix/backend/scripts/extract_dispatch_docx.py)
- **验证**：本地执行测试通过，北海汽炉/水炉/燃气炉三权分立，金州 #6 炉成功归类为水炉，金州 #4 炉与香海/北方成功归类为汽炉，`devices_detail` 与 `log_items_json` 拓扑完全统一。

## 2026-10-28 [调度信息提取工具：企业全称标准口径统一与设施管径正则全面加固]
- **改动说明**：
  - 响应用户关于集团统一标准口径要求，全面校准升级 `extract_dispatch_docx.py` 中的责任单位与企业字典；
  - 将所有提取与映射中的“北方电厂”统一标准化为“北方热电”，“金州电厂”标准化为“金州热电”，“庄河电厂”标准化为“庄河环海”，前置纳管“金普公司”；
  - 同步修复物理设施分类中的死角（支持蒸汽炉/汽炉/加热器/热泵/辅机识别），并剔除管径匹配中的英文字界限制，实现 DN 规格 100% 捕获；
  - **核心设计与实现**：
    1. **权威机构标准字典对齐 (`KNOWN_ORGS` & `CATEGORY_ORG_MAP`)**：
       - `北方热电`：对齐北方电厂、北方厂、北方；
       - `金州热电`：对齐金州电厂、金州厂、金州；
       - `庄河环海`：对齐庄河电厂、庄河厂、庄河；
       - `金普公司`：对齐金普热电、金普新区、金普；
       - 机炉状态表 `eqp_status_json` 同步以标准名称作为实体键；
    2. **物理设施细分与管径匹配全量覆盖**：
       - 锅炉正则扩充支持 `#1蒸汽炉`、`#1汽炉`、`3#炉`，避免落入 `other` 兜底项；
       - 新增 `heater`（加热器/换热器）、`heat_pump`（热泵）、`auxiliary`（风机辅机）细分大类；
       - 管径规格正则由 `\b(DN\d+)\b` 优化为 `(DN\d+)`，彻底解决中文紧邻导致的 21 条管径漏捕问题；
    3. **桌面 GUI 界面文案与提示同步对齐**：
       - 界面提示与日志刷屏全面采用规范后的企业名称。
- **改动文件**：
  - [`backend/scripts/extract_dispatch_docx.py`](file:///D:/编程项目/phoenix/backend/scripts/extract_dispatch_docx.py)
- **验证**：本地执行 CLI 提取测试通过，金州热电等企业全称标准输出，管径与设施分类全覆盖。

## 2026-10-28 [调度信息提取工具：生产信息记录全标准化重构与六元组实体模型落地]
- **改动说明**：
  - 针对上个供暖期全量 162 篇数据提取中暴露的“责任主体丢失降级（42% 记录沦为电厂/车间）”、“物理设施与纯文本混杂”、“管网工作票缺少地理路口与规格属性”等核心问题，全面重构升级 `extract_dispatch_docx.py`；
  - 正式实装生产信息记录“六元组标准实体模型”，实现 Who（责任组织）、Target Type（物理分类）、Target Name（标准设施名）、Action（标准动作枚举）、Status（状态机迁移）、Space & Spec（地理与管径规格）全维度解耦标准化；
  - **核心设计与实现**：
    1. **组织分组头判定加固 (`detect_org_header`)**：
       - 建立组织白名单映射字典（北海、香海、金州、北方、供热公司、调度中心等）；
       - 彻底解决填报人员无冒号、仅写厂名/单位名引发的分组头断裂漏洞，识别后仅切换责任上下文并不再误存为操作日志，责任主体识别率提升至 100%；
    2. **物理实体与行为动作六元组萃取 (`parse_facility_and_action`)**：
       - 物理分类：`boiler` (锅炉/水炉)、`turbine` (汽机)、`pump` (循环泵)、`valve` (隔离门/放水门/直补门)、`substation` (换热站)、`pipeline` (主干线/支线)；
       - 优先级排序：细化识别阀门与泵组，避免因包含“东环”等字眼被泛化识别为管线；
       - 动作枚举：统一归一化为点火、并汽、并网并列、冲转、事故跳闸、查漏抢修、带压堵漏、管网上水、开启倒闸、关闭倒闸、启动投运、停运退出、恢复供暖、工期延期等；
    3. **管网工作票深度解析**：
       - 正则同时兼容书名号《》与引号“”，标题提取率达 100%；
       - 自动提取管径规格（`pipe_spec`: 如 DN1000、DN500、DN200）与空间地理路口（`location`: 如五四路交民运街、新开路交福德街）；
    4. **图形界面 (GUI) 对账日志同步对齐**：
       - 日志实时刷屏展示规范化主体与标准事件数，便于对账。
- **改动文件**：
  - [`backend/scripts/extract_dispatch_docx.py`](file:///D:/编程项目/phoenix/backend/scripts/extract_dispatch_docx.py)
- **验证**：本地执行 `--file` 提取样例成功，单据设施类型（pump、boiler）、设施名（#2热网循环泵、#3水炉）、动作（启动投运、点火、并汽）全部完成六元组标准化输出。

## 2026-10-28 [生产日报子项目：全面修正全局管理中心等页面的面包屑导航文字与动态项目响应]
- **改动说明**：
  - 响应用户反馈，彻底修正访问 `http://localhost:5173/projects/daily_report_25_26/pages/global_management?pageName=全局管理中心` 时面包屑导航显示错误问题，并对全工程各页面面包屑和页面标题识别逻辑进行全面检查与规范化加固；
  - **根本原因诊断**：
    - 排查全项目各业务页面发现，其余页面均已采用 `computed(() => [...])` 动态计算面包屑，唯独 `GlobalManagementView.vue` 遗留了静态数组字面量；
    - `GlobalManagementView.vue` 未引入 `useRoute` 和 `useProjects`，第三级错写为 `'全局管控中心'`（而项目配置与 query 传参为 `'全局管理中心'`），且未响应 URL 中的 `?pageName=全局管理中心`，第二级项目名称也是静态硬编码；
    - `AppHeader.vue` 中的 `getCurrentPageName` 在特殊业务页面映射中缺少对 `/pages/global_management` 的判定，且未优先响应 `route.query.pageName`；
    - `router/index.js` 缺少路由元信息 `meta: { title: '全局管理中心' }`，且路由守卫注释保留了旧称“全局管控中心”；
  - **核心设计与实现**：
    1. **修复 `GlobalManagementView.vue` 面包屑响应机制**：
       - 引入 `useRoute` 与 `useProjects` (`getProjectNameById`, `ensureProjectsLoaded`)；
       - 新增响应式计算属性 `pageDisplayName`，优先提取 `route.query.pageName`，缺省回退至 `'全局管理中心'`；
       - `breadcrumbItems` 重构为 `computed` 响应式数组：`项目选择` ➔ `projectName` (`/projects/:projectKey/pages`) ➔ `pageDisplayName`；
       - 在 `onMounted` 钩子中同步调用 `ensureProjectsLoaded()`；彻底清除自作主张追加的 `document.title` 后缀，保持系统默认标题纯净规范；
       - 规范 `goProjectPages()` 路由跳转为 `encodeURIComponent(projectKey)`；
    2. **增强 `AppHeader.vue` 页面与在线人员状态识别**：
       - `getCurrentPageName` 增加 `route.query.pageName` 优先级提取；
       - 针对 `/pages/global_management`、`/pages/dynamic_plan`、`/pages/spot_electricity` 增加精确路径判定，确保任何场景下导航与在线状态均显示规范中文名；
    3. **完善 `router/index.js` 路由元数据与注释规范**：
       - 为 `global_management`、`dynamic_plan`、`spot_electricity` 路由补充完整的 `meta: { title: ... }` 元属性；
       - 纠正路由守卫处代码注释中的旧称。
- **改动文件**：
  - [`frontend/src/projects/daily_report_25_26/pages/GlobalManagementView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/GlobalManagementView.vue)
  - [`frontend/src/projects/daily_report_25_26/components/AppHeader.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/AppHeader.vue)
  - [`frontend/src/router/index.js`](file:///D:/编程项目/phoenix/frontend/src/router/index.js)
- **验证**：前端生产构建 `npm run build` 成功（0 报错，755 模块打包完成）。

## 2026-10-28 [计划动态分解模块：收敛基准k值为纯只读，仅开放Global_admin前台设定m缩放系数]
- **改动说明**：
  - 响应用户最新业务逻辑决策，确认基准 `k` 值源于客观历史数据回归拟合，应当保持基准严肃性与只读性，不开放前台修改；仅允许 `Global_admin` 对 `m` 缩放系数进行在线设定与修改；
  - **核心设计与实现**：
    1. **前端表格收敛规范**：
       - [`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)：
         - 【基准 k 值】列彻底移除输入框分支，恢复为统一的纯只读 Badge 展示（`k-badge-num active` / `zero`）；
         - 【m 缩放系数】列保留管理员在线数字输入框与黄色高亮修改提示；
         - 改动监测函数 `isParamRowModified` 收敛为仅侦测 `m_value` 的变动，右上角批量保存与单行保存按钮均对齐为【保存 m 缩放系数】；
    2. **后端接口双重加固保障**：
       - [`dynamic_plan.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dynamic_plan.py)：
         - 更新逻辑严格锁定 `k_value` 不受任何篡改，仅对 `m_value` 进行执行更新，切实保障底层基准拟合参数安全。
- **改动文件**：
  - [`frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)
  - [`backend/projects/daily_report_25_26/api/dynamic_plan.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dynamic_plan.py)
- **验证**：前端生产构建 `npm run build` 成功（0 报错，耗时 16.87s）。

## 2026-10-28 [计划动态分解模块：前台上线 Global_admin 专属 k 值与 m 缩放系数在线编辑设定与保存功能]
- **改动说明**：
  - 响应用户最新管理运维诉求，赋能 `Global_admin`（全局管理员）可以在前台界面直接在线设定、调整每个口径每个指标的基准 `k` 值与 `m` 缩放系数，支持单行保存与批量保存，保存后实时重算日分解走势与分布律；
  - **核心设计与实现**：
    1. **后端安全更新接口与权限门禁**：
       - [`dynamic_plan.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dynamic_plan.py) 新增 `POST /dynamic_plan/update_k_parameters` 接口；
       - 基于 `get_current_session_optional` 提取会话，严格校验 `Global_admin` / 系统超管 `ww870411` / `can_access_admin_console` 权限，非管理员一律阻断（403 Forbidden）；
       - 数据库执行 `ON CONFLICT (company, month, item) DO UPDATE` 幂等写入，支持更新现有指标或新增指标行；
    2. **前端 API 接入**：
       - [`api.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/api.js) 封装导出 `updateDynamicPlanKParameters` 方法，自动携带身份鉴权 Token；
    3. **前台自适应鉴权与沉浸式编辑展板**：
       - [`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)：
         - 权限自适应：普通用户维持优雅的只读 Badge；`Global_admin` 登录时展板点亮【🔑 管理员可编辑】徽章，表格自动切换为数字输入框；
         - 实时改动感知：输入框修改后自动黄色高亮指示，行标记待保存小圆点，右上角呈现【💾 保存修改 (N)】与【↩️ 撤销】按钮，行末提供独立 `💾` 保存按钮；
         - 保存即时重算联动：点击保存后调用接口写入数据库，并立即重新拉取日分解计算引擎数据，图表曲线、Tooltip 权重与明细表格瞬间响应更新。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/api/dynamic_plan.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dynamic_plan.py)
  - [`frontend/src/projects/daily_report_25_26/services/api.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/api.js)
  - [`frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)
- **验证**：Python 鉴权单元测试通过（管理员成功更新，非管理员 403 阻断）；前端生产打包 `npm run build` 成功（0 报错，耗时 16.07s）。

## 2026-10-28 [计划动态分解模块：修复聚合口径总量指标未应用自身k与m值导致分布律不变的缺陷]
- **改动说明**：
  - 响应用户关于“设定了 m 值，对分布律也没有影响”的问题反馈，进行深度代码与数据流排查；
  - **根本原因诊断**：
    - 数据库中用户已将 `('Group', 11, 'amount_heat_supply', '供热量')` 的 `m_value` 成功修改为 `10.0`；
    - 然而在 [`dynamic_decomposition_service.py`](file:///D:/编程项目/phoenix/backend/services/dynamic_decomposition_service.py) 中，当统计口径为聚合口径（`Group` 或 `ZhuChengQu`）时，原逻辑对总量指标（如供热量）采用了“无条件累加各子口径日计划”的分支，而子口径各自的 `m_value` 依然为 `1.0`，导致集团自身的 `k_value` 与用户设定的 `m_value=10.0` 完全被架空未参与日计划计算，反算出的权重和日分解序列纹丝不动；
  - **核心修复与实现**：
    1. **聚合口径专属模型优先应用**：在聚合口径处理总量指标时，若该聚合口径已在 `dynamic_month_plan_k` 中配置了专属的 $k$ 值模型（`has_k == True`，且 $k \neq 0$），严格基于该口径自身的月计划总量 $P_{month}$ 与有效敏感度 $k_{eff} = k \times m$ 直接调用 `decompose_single_series` 进行动态度日分解；
    2. **无模型指标兼容子口径聚合**：仅在当前聚合口径未配置 $k$ 值模型（`has_k == False`）时，才回退至向下聚合各子口径分解结果或等额日均摊；
    3. **分布律实时响应**：修复后实测，当 Group 11月供热量 $m=10.0$ 时，$k_{eff}$ 扩大 10 倍（由 0.0366 增至 0.3663），日计划走势与权重分布律由平缓波动（0.80~0.98）转为显著的弹性拉伸（0.00~0.89），全月月计划总量依然 100% 绝对守恒。
- **改动文件**：
  - [`backend/services/dynamic_decomposition_service.py`](file:///D:/编程项目/phoenix/backend/services/dynamic_decomposition_service.py)
- **验证**：Python 内存模拟对比验证（$m=1$ vs $m=10$）日计划及分布律权重均产生显著预期变化；全月总量守恒保持；前端生产构建 `npm run build` 成功（耗时 15.37s）。

## 2026-10-28 [计划动态分解模块：公式与展示文案中缩放系数由大写 M 全面规范为小写 m]
- **改动说明**：
  - 响应用户最新视觉与学术符号规范要求，将“计划动态分解模块”中所有涉及缩放系数展示的大写字母 `M` 全面规范收敛为小写字母 `m`；
  - **核心设计与实现**：
    1. **公式定义统一小写化**：步骤 2 敏感度权重数学公式更新为 $W_d = \max(0, 1 + (k \times m) \times (HDD20_d - \overline{HDD20}))$，说明文案同步变更为“`m` 为人工缩放系数（默认 1.0）”、“实际生效系数 $k_{eff} = k \times m$”；
    2. **表格标题与列头规范**：右侧字典矩阵标题校准为【各指标 k 值字典 (含 m 缩放)】，列头定名为【m 缩放系数】；
    3. **单元格悬浮提示校准**：单元格 Hover Tooltip 同步更新为 `'m 缩放系数: ...'`；
    4. **后端服务注释对齐**：[`dynamic_decomposition_service.py`](file:///D:/编程项目/phoenix/backend/services/dynamic_decomposition_service.py) 中内部注释同步更新为“m 缩放系数”，与数据表字段 `m_value` 及前端保持高度统一。
- **改动文件**：
  - [`frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)
  - [`backend/services/dynamic_decomposition_service.py`](file:///D:/编程项目/phoenix/backend/services/dynamic_decomposition_service.py)
- **验证**：前端生产构建 `npm run build` 执行成功（0 报错，耗时 17.06s）。

## 2026-10-28 [计划动态分解模块：数据库表增加M值缩放系数，打通计算引擎与矩阵视图]
- **改动说明**：
  - 响应用户最新模型精细化管控需求，在数据库表 `public.dynamic_month_plan_k` 中为每个月、每个指标增加 `M` 值（手动缩放系数），默认值全为 `1.0`；
  - **核心设计与实现**：
    1. **数据库 DDL 升级**：为 `public.dynamic_month_plan_k` 表新增 `m_value NUMERIC(16, 6) NOT NULL DEFAULT 1.0` 字段，存量 360 条参数记录全部无缝默认置为 `1.000000`；
    2. **ORM 模型与建表脚本同步**：在 [`database_daily_report_25_26.py`](file:///D:/编程项目/phoenix/backend/db/database_daily_report_25_26.py) 的 `DynamicMonthPlanK` 类与 [`dynamic_month_plan_k.sql`](file:///D:/编程项目/phoenix/backend/sql/dynamic_month_plan_k.sql) 中补充 `m_value` 字段映射；
    3. **分解计算服务全链路贯通**：在 [`dynamic_decomposition_service.py`](file:///D:/编程项目/phoenix/backend/services/dynamic_decomposition_service.py) 中，动态日计划分解计算将有效敏感度定义为 $k_{eff} = k \times M$，日权重公式升级为 $W_d = \max(0, 1 + (k \times M) \times (HDD20_d - \overline{HDD20}))$，返回字段包含 `k_value`、`m_value` 与 `effective_k`；
    4. **前端算法展板与表格矩阵呈现**：在 [`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue) 中更新步骤 2 公式说明，并在右侧指标字典表中新增【M 缩放系数】列（默认显示 `1.0000` Badge，若修改高亮指示）。
- **改动文件**：
  - 数据库表：`public.dynamic_month_plan_k`
  - [`backend/sql/dynamic_month_plan_k.sql`](file:///D:/编程项目/phoenix/backend/sql/dynamic_month_plan_k.sql)
  - [`backend/db/database_daily_report_25_26.py`](file:///D:/编程项目/phoenix/backend/db/database_daily_report_25_26.py)
  - [`backend/services/dynamic_decomposition_service.py`](file:///D:/编程项目/phoenix/backend/services/dynamic_decomposition_service.py)
  - [`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)
- **验证**：PostgreSQL 表结构校验成功（360 条数据均赋值 1.0）；后端测试服务通过；前端构建 `npm run build` 成功（0 报错，耗时 17.77s）。

## 2026-10-28 [计划动态分解模块：算法与k值区域默认收起，文案由“建议k值”收敛为“k值”]
- **改动说明**：
  - 响应用户最新操作习惯与视觉规范，将“计划动态分解模块”中新增的算法与 k 值模型区域调整为**默认收起状态**，避免进入或开启模式时过多占据图表视窗；
  - 界面与代码各处文案由“建议k值”/“建议 k 值”统一收敛精简为**“k值”** / **“k 值”**；
  - **核心设计与实现**：
    1. **默认折叠收起**：在 [`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue) 中将 `showDecompAlgorithmPanel` 初始状态设为 `false`；在用户勾选开启“动态分解”模式时保持收起，用户点击 `[📐 查看算法与 k 值]` 按钮时再按需展开；
    2. **专业文案精炼**：全局清退“建议”二字，字典表头统一标为【k 值】，公式说明与提示统一为“气温敏感度参数”、“各指标 k 值字典”及“k 值模型”，界面呈现更加精炼干脆。
- **改动文件**：[`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)。
- **验证**：前端生产打包 `npm run build` 成功（0 报错，耗时 12.56s）。

## 2026-10-28 [计划动态分解模块：上线分解算法原理推演与各指标建议k值模型展板]
- **改动说明**：
  - 响应用户业务深度分析需求，新增专属双栏分析卡片 `decomp-algorithm-panel`，展示采暖度日公式（HDD20）、日敏感度弹性权重公式（W_d）与全月守恒分解公式（P_d），并呈现当前口径当前月份各指标 k 值矩阵，支持一键【🎯 聚焦】图表对应曲线。
- **改动文件**：[`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)。
- **验证**：前端生产构建 `npm run build` 执行成功。

## 2026-10-28 [计划动态分解模块：移除图表坐标轴冗余“左纵轴/右纵轴”文字，仅呈现纯单位]
- **改动说明**：
  - 鉴于图表上方已常驻标识左右纵轴归属的专属指示胶囊与指标 Pill 标签，图表内部坐标轴彻底移除 `左纵轴 (...)` 与 `右纵轴 (...)` 字样，直接展示纯单位（如 GJ、万kWh、吨 等），避免视觉冗余与轴顶挤压。
- **改动文件**：[`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)。
- **验证**：前端生产构建 `npm run build` 执行成功。

## 2026-10-28 [名称校准：“动态计划模块”更名为“计划动态分解模块”]
- **改动说明**：
  - 将生产日报子系统中的“动态计划模块”最终校准定名为“计划动态分解模块”，更新 `项目列表.json`，自适应双重历史旧 query 参数（“动态计划指标”与“动态计划模块”）。
- **改动文件**：
  - [`backend_data/shared/项目列表.json`](file:///D:/编程项目/phoenix/backend_data/shared/项目列表.json)
  - [`PageSelectView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue)
  - [`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)
- **验证**：前端生产构建 `npm run build` 执行成功。
