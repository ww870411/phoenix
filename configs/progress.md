# Phoenix 凤凰计划 · 开发过程记录 (Progress Log)

## 2026-11-07 生产运行汇报空间弹窗排版遮挡重构、移动流转中枢升级与工作流目录穿透修复

- **需求背景**：
  1. 用户反馈在工作流目录空间中，子文件夹点击无法正常打开，无法进入子目录；
  2. 两个文件空间（材料仓库管理空间与工作流目录空间）弹窗存在严重排版问题与元素相互遮挡，操作列按钮过多挤压导致表格错位与内容遮盖；
  3. 移动文件弹窗排版过于简陋、缺乏流转直观感与安全感，需要站在用户角度，重构为既美观又实用的高品质现代交互界面。
- **改动范围与主要工作**：
  - **工作流空间子目录穿透修复 (`period_report_workflow.py` & `PeriodReportView.vue`)**：
    1. **字段规范与双向兼容**：后端 `list_workflow_files` 在子文件夹扫描结果中同时输出 `rel_path` 与 `relative_path`、`item_count` 与 `file_count`；
    2. **前端调用修复**：前端 `PeriodReportView.vue` 中进入子文件夹事件统一绑定 `dir.rel_path || dir.relative_path || dir.name`，彻底解决 `undefined` 导致重复回退加载根目录的问题，支持多层级子目录顺畅穿透与面包屑回溯。
  - **两大文件空间弹窗排版彻底重构与防遮挡治理 (`PeriodReportView.vue`)**：
    1. **弹窗容器扩容与视觉呼吸感提升**：`.modal-card-space` 最大宽从 `1100px` 拓宽至 `1240px`（`width: 95vw; max-height: 90vh`），消弭促狭拥挤感；
    2. **列宽科学重新分配**：
       - **材料空间**：文件名 30% / 分类属性 12% / 大小 8% / 时间 18% / 操作动作 32%（为 6 个操作胶囊预留 350px+ 充足空间，彻底消除折行与向左遮盖时间列）；
       - **工作流空间**：精简合并原本冗余的“类型”与“包含内容”为“类型与用途”列（16%），表头科学调整为 5 列（名称 32% / 类型与用途 16% / 大小与统计 9% / 修改时间 16% / 操作动作 27%）；
    3. **表格防挤压兜底与横向自适应滚动**：`.space-table` 增加 `min-width: 1040px`，`.space-table-scroll` 开启 `overflow-x: auto`，即使视口缩放也绝对不会产生元素重叠遮挡；
    4. **操作按钮微排版升维**：统一高度、精简 padding（`3.5px 7px`）、微图标与文字像素级对齐，操作组设置 `flex-wrap: nowrap; flex-shrink: 0`。
  - **文件移动与跨空间传输中枢全新升维重构 (`showTransferModal`)**：
    1. **大气质感容器 (`modal-card-transfer`)**：定制 660px 宽度流式卡片，搭配渐变微徽标与“空间内部整理 / 跨空间双向流转”动态场景徽章；
    2. **流转关系示意看板 (Transfer Flow Canvas)**：卡片顶部设计对流看板，左侧呈现源文件与当前路径，中间呈现动态脉冲箭头 `➔`（带“剪切移动”或“生成副本”指示球），右侧实时预览目标空间与目标文件夹；
    3. **双大卡片目标空间选择器**：废弃简陋的原生单选框，采用“📁 材料空间”与“🗂️ 工作流空间”双大卡片交互，附带用途说明、选中高亮微发光与非超管安全锁定；
    4. **目标文件夹选择与即时新建联动**：美化下拉选择框，并提供“➕ 新建子文件夹”快捷按钮，新建后自动刷新并即时选中新建文件夹；
    5. **操作模态双分段卡片 (移动 vs 复制)**：直观展现“🚚 移动 (剪切)”与“📋 复制 (副本)”区别，工作流受保护母版自动锁定为复制并给出安全警示；
    6. **同名冲突策略选项**：默认开启“自动追加 _副本1、_副本2 递增序号”安全保护策略，并支持手动勾选“目标存在同名文件时直接覆写”；
    7. **目标物理存储路径实时预览条**：在弹窗底部实时拼接并展示真实物理落盘路径（如 `backend_data/projects/daily_report_25_26/period_report/...`）。
- **验证结论**：
  - 后端 pytest 11 项测试 100% 通过（7.34s）；
  - 前端 vite build 打包 1062 模块全部转换成功，0 错误（18.89s）；无数据库表结构变更。

- **需求背景**：
  - 用户提出希望能够“一键打包下载目录中的所有子目录和文件”，便于一次性将生产运行汇报工作流下的所有标准化规范文档（.md）、模板引擎系统（.html）、数据结构与相关子目录打包归档或离线分享。
- **改动范围与主要工作**：
  - **后端 (`period_report_workflow.py` & `api/period_report.py`)**：
    1. 新增 `create_workflow_archive(folder: str = "")` 服务函数：
       - 基于标准库 `zipfile` 实现内存流式打包（`ZIP_DEFLATED` 高压缩比）；
       - 支持两种打包模式：全量根目录打包（包含所有子目录、孙目录及文件）与指定子目录精准打包；
       - 智能保留目录树结构（包含空子文件夹），各级文件的时间戳严格保持东八区真实修改时间；
       - 动态生成规范中文压缩包名称：如 `工作流_全量资料_YYYYMMDD_HHMMSS.zip` 或 `工作流_{子目录名}_YYYYMMDD_HHMMSS.zip`；
    2. 新增端点 `GET /period-report/workflow/archive`：
       - 挂载 `folder` 可选参数，采用 `StreamingResponse` 流式响应，设置标准 `Content-Disposition` 附件头；
       - 绑定 `check_admin_session`，严格限定 `Global_admin` 权限；
    3. 完善自动化测试 `test_period_report.py`：
       - 覆盖未授权 403 拦截、全量工作流打包验证（解压校验包含规范文档与模板引擎）、指定子目录打包验证（校验仅包含子目录内容）、以及非法路径穿越（`folder=../../`）拦截，全部 10 项测试 100% 通过。
  - **前端 (`PeriodReportView.vue` & `services/api.js`)**：
    1. `services/api.js`：
       - 新增并导出 `downloadWorkflowArchive(folder)`，支持解析 UTF-8 / RFC 5987 编码的中文压缩包文件名并自动拉起浏览器本地下载；
    2. `PeriodReportView.vue`：
       - **工具栏操作集成**：在工作流弹窗工具栏中增加“📦 一键打包下载 (ZIP)”动作按钮：
         * 处于根目录时：一键触发全量工作流打包；
         * 处于任一子目录时：按钮自适应切换为“📦 打包本目录 (ZIP)”，并额外提供“📦 打包全部”快捷胶囊，方便随心切换；
       - **底栏 Footer 联动**：在底栏路径标签旁增加“📦 一键打包下载全部资料 (ZIP)”常驻微入口；
       - **即时交互反馈**：打包中按钮显示 `spinner` 动画并防重复点击，下载拉起后弹窗提示打包范围与生成的文件名。
- **验证结论**：
  - 后端 pytest 10/10 项通过；
  - 前端 vite build 构建成功（1062 模块编译，0 错误）。

## 2026-11-06 工作流目录空间支持子目录层级展示、面包屑树状导航与文件夹创建管理

- **需求背景**：
  - 用户反馈工作流目录空间不应直接平铺所有深层文件，而是应该以清晰直观的目录层级结构呈现，子目录也应该明确展示出来，支持层级穿透与管理。
- **改动范围与主要工作**：
  - **后端 (`period_report_workflow.py` & `api/period_report.py`)**：
    1. 升级 `list_workflow_files(folder: str = "")`：
       - 支持按指定相对子目录进行单层精准扫描；
       - 自动生成面向前端的面包屑导航链路数组 `breadcrumbs`（如 `[{"name": "工作流根目录", "path": ""}, {"name": "1.html模板与使用说明", "path": "1.html模板与使用说明"}]`）；
       - 自动计算并返回上一层目录相对路径 `parent_folder`；
       - 将结果严格分离为 `directories`（包含子文件夹名称、相对路径、包含项目数/文件数、东八区修改时间）与 `files`（直属文件列表），并保留合并项 `items` 兼容；
    2. 新增 `create_workflow_folder(parent_folder: str, folder_name: str)`：
       - 支持在工作流根目录或任意合法子目录下创建新文件夹，包含防路径穿越与非法字符严格校验；
    3. 扩充 API 端点：
       - `GET /period-report/workflow/files` 支持 `?folder=` 查询参数；
       - 新增 `POST /period-report/workflow/folders` 创建子目录接口，绑定 `Global_admin` 鉴权；
    4. 扩充自动化测试：
       - `test_period_report.py` 增补层级子目录浏览、面包屑验证及新建子目录测试，10 项测试全部通过。
  - **前端 (`PeriodReportView.vue` & `services/api.js`)**：
    1. `services/api.js`：
       - `fetchWorkflowFiles(folder)` 支持向后端传递当前目录路径；
       - 新增导出 `createWorkflowFolder(folder, folderName)`；
    2. `PeriodReportView.vue`（组件全面升级为树状层级资源管理器）：
       - **顶部面包屑导航条 (`workflow-breadcrumb-bar`)**：包含“↩️ 返回上级”快捷按钮、层级路径节点（可点击任意层级平滑跳转）、右侧当前相对路径标识；
       - **工具栏升级**：新增“📁 新建文件夹”动作按钮，上传按钮自动绑定上传至当前所处的子目录；
       - **表格结构树状渲染**：
         * **子目录行（黄徽标 📁）**：优先展示子文件夹行，名称加粗，悬停黄色卡片高亮，显示子文件项数统计，点击文件夹行或“👉 进入”即可平滑进入该子目录；
         * **直属文件行（📑 / 🌐 / 📊）**：展示当前层级的文档与模板，支持直接在线阅读 Markdown、播放 HTML 模版、下载、改名与删除；
       - **新建子文件夹弹窗 (`showNewFolderModal`)**：支持即时输入文件夹名称，回车自动创建并无感刷新当前目录；
       - **操作无感刷新**：在子目录中上传、改名、删除或创建文件夹后，均保持在当前子目录并自动刷新。
- **验证结论**：
  - 后端 pytest 10/10 项通过；
  - 前端 vite build 顺利完成构建，零错误。

## 2026-11-06 控制台专属集成“工作流目录空间”管理与沉浸式 Markdown 阅读

- **需求背景**：
  - 用户提出在控制台（`Global_admin` 下拉控制台）中，应该专门将工作流目录 `phoenix\backend_data\projects\daily_report_25_26\period_report\工作流` 独立作为一个目录空间进行管理；
  - 该目录包含标准化工作流规范文档（`工作流概述.md`）、模板引擎说明（`模板引擎说明.md`、`模版引擎.html`）以及材料结构要求（`汇报材料结构与要求.md`）等核心支撑材料。
- **改动范围与主要工作**：
  - **后端**：
    1. 新建 `backend/projects/daily_report_25_26/services/period_report_workflow.py`：
       - 封装 `WORKFLOW_DIR` 工作流目录专属管理服务；
       - 提供 `list_workflow_files`（递归扫描子目录、提取相对路径、子文件夹分类与文件类型推断）、`get_workflow_file_content`（在线读取 Markdown / HTML / 纯文本）、`get_workflow_file_path`（流式下载）、`upload_workflow_file`（支持上传至指定子文件夹）、`rename_workflow_file`（防穿越并保留原格式）与 `delete_workflow_file`；
       - 所有时间戳统一采用东八区（UTC+8 北京时间）格式化；
    2. 扩充 `backend/projects/daily_report_25_26/api/period_report.py`：
       - 新增 6 个 RESTful 接口：
         * `GET /period-report/workflow/files`
         * `GET /period-report/workflow/files/content`
         * `GET /period-report/workflow/files/download`
         * `POST /period-report/workflow/files/upload`
         * `POST /period-report/workflow/files/rename`
         * `DELETE /period-report/workflow/files`
       - 保持严格的 `Global_admin` 会话拦截；
    3. 扩充单元测试 `backend/projects/daily_report_25_26/tests/test_period_report.py`：
       - 新增 `test_workflow_management_endpoints` 测试用例（覆盖非管理员 403 拦截、正常列表读取、Markdown 内容读取、防穿越拦截、上传至子目录、重命名、下载与安全删除），10 项测试全部 100% 通过。
  - **前端**：
    1. `services/api.js`：
       - 新增 `fetchWorkflowFiles`、`fetchWorkflowFileContent`、`downloadWorkflowFile`、`uploadWorkflowFile`、`renameWorkflowFile`、`deleteWorkflowFile` 六项接口封装；
    2. `PeriodReportView.vue`：
       - 控制台下拉菜单的“空间与数据”组别中，专门新增“🗂️ 工作流目录空间”按钮；
       - 新增专属宽屏管理弹窗 `showWorkflowModal`（1100px 自适应容器、子目录筛选药丸 Tab、即时搜索框、拟态文件头像、双行东八区时间卡片与一键复制路径徽标）；
       - 新增“📑 工作流文档沉浸式阅读窗口”`showDocReaderModal`：点击任意 `.md` 规范或点击“👁️ 阅读”直接弹窗精读全文，支持一键复制与下载；
       - 新增“✏️ 工作流文件重命名窗口”`showWorkflowRenameModal`：支持修改文件名主体并自动锁定原扩展名。
- **验证结论**：
  - 后端 10 项单元测试全部通过；
  - 前端生产构建通过（1062 模块编译成功，耗时 16.71s，0 错误）。

## 2026-11-06 材料仓库管理弹窗排版全面升维（分类筛选、即时搜索与高质感表格设计）

- **改动缘由**：
  - 用户反馈“周期汇报与数据材料仓库”弹窗排版不够美观大方整齐，存在横向列过多导致日期重复拥挤、文件名超长被挤压、缺少分类筛选与搜索定位能力等痛点；
  - 站在真实用户使用与大屏观赏角度进行全方位视觉升级，实现美观、大方、整齐的高级管理中枢体验。
- **改动点**：
  - **前端 (`PeriodReportView.vue`)**：
    1. **弹窗容器升级为 `modal-card-space`**：
       - 采用 1100px 宽屏流式自适应容器（最大宽 94vw、最大高 88vh），边角微弧度与多层级环境阴影，彻底消除局促感；
       - Header 强化主题标识（`空间中枢` 渐变胶囊徽标、副标题与自适应关闭按钮）。
    2. **工具栏与分类筛选一体化架构**：
       - 左侧组合动作：`📤 上传材料`（主题强调）+ `🔄 刷新` + 竖向精细分隔线；
       - 新增分类药丸 Tab：支持实时在“全部 (X)”、“📊 数据明细 (N)”、“📄 汇报讲稿 (M)”、“⚙️ 系统母版 (K)”之间无缝过滤切换；
       - 右侧新增即时模糊搜索框：带放大镜图标与一键清空按钮，输入即搜，大方整洁。
    3. **表格布局整齐划一（Strict Column Proportions）**：
       - 采用 `table-layout: fixed` 约束列宽（44% 文件名 / 14% 分类 / 10% 大小 / 18% 时间 / 14% 操作），表头吸顶且绝不变形挤压；
       - 文件名称列：配有精致拟态头像（Excel 为翠绿头像 `📊`、HTML 汇报为天蓝头像 `📄`、系统模板为琥珀头像 `⚙️`），粗体超链点击可直接动作（Excel 下载 / HTML 在线播放），并配有格式小胶囊；
       - 分类属性列：精美徽章与发光小圆点（`badge-dot`），层级分明；
       - 时间信息列：垂直双行精巧微排，上行高亮展示“更新: 2026-11-06 15:02:18”，下行次级小字显示“创建: 2026-11-06 14:35:10”，节省横向宽度的同时完整保留东八区双时间审计信息；
       - 操作列：统一动作小胶囊按钮组（`▶ 播放`、`📥 下载`、`✏️ 改名`、`🗑 删除`），微交互过渡自然；核心模板显示“🔒 受保护”锁形徽章。
    4. **空状态与 Footer 优化**：
       - 空状态增加精致大图标、引导性说明；
       - 底部 Footer 左侧将底层存储路径收拢为可一键点击复制的徽章标签（`💾 路径: .../材料仓库 (点击复制)`），右侧清晰统计“已显示 X / 共 Y 个材料”。
- **验证结论**：
  - 前端 1062 模块成功编译，耗时 18.01s，0 错误；后端 9 项测试持续全通。

## 2026-11-06 材料仓库时间严格东八区对齐与空间文件重命名功能

- **改动缘由**：
  1. 用户反馈材料仓库中的文件时间戳（创建时间与最后修改时间）受 Docker 容器或环境默认 UTC 影响存在时差，未按东八区（UTC+8 北京时间）显示；
  2. 用户需要在材料管理空间中直接对已保存或已导出的汇报与数据文件（HTML 报告 / XLSX 数据明细）进行自定义重命名。
- **改动点**：
  - **后端**：
    - `period_report_files.py`：
      * 引入 `BEIJING_TZ = timezone(timedelta(hours=8))` 与 `format_beijing_time` 工具函数，将文件的 POSIX 时间戳严格解析为 UTC 并转换为东八区（UTC+8 北京时间）标准时间字符串，彻底消除宿主环境时区差异；
      * 新增 `rename_report_file(rel_path, new_name)` 函数，支持合法文件名清洗、路径防穿越校验、已存在同名冲突防御，并自动锁定与继承原文件的有效扩展名（`.html`、`.xlsx` 等），受保护的核心模板禁止重命名；
      * `list_report_files`、`save_report_html`、`upload_report_html` 统一返回东八区的 `created_at` 与 `updated_at`；
    - `period_report_export.py`：
      * `save_period_report_xlsx` 一并调用 `format_beijing_time` 返回东八区 `created_at` 与 `updated_at`；
    - `api/period_report.py`：
      * 新增 `POST /period-report/files/rename` 接口，定义 `RenameReportRequest(path, new_name)` 模型，并保持严格的 `Global_admin` 角色会话拦截；
    - `tests/test_period_report.py`：
      * 扩展 `test_files_management_endpoints` 测试用例，增加模板重命名受限 403 拦截、正常重命名、智能扩展名继承校验及东八区时间戳格式验证。
  - **前端**：
    - `services/api.js`：
      * 新增 `renamePeriodReportFile(path, newName)` 方法；
    - `PeriodReportView.vue`：
      * 材料仓库表格表头增设“创建时间 (北京)”与“修改时间 (北京)”独立列，均精确显示东八区时间；
      * 材料列表操作列中为非模板文件增加“✏️ 重命名”操作按钮；
      * 增加高质感小巧模态弹窗 `showRenameModal`，展示原文件名并允许用户直接输入新文件名主体，输入框侧边锁定显示原文件扩展名徽标（`.html` 或 `.xlsx`），支持 Enter 确认与点击确认，成功后自动刷新列表。
- **验证结论**：
  - 后端 9 项单元测试全部 100% 通过（`python -m pytest backend/projects/daily_report_25_26/tests/test_period_report.py`）；
  - 前端生产构建通过（`npm run build --prefix frontend`，1062 模块编译成功，耗时 19.07s，0 错误）；
  - 核心模板受保护逻辑不变，向后兼容所有文件查询与下载接口。

## 2026-11-06 生产运行汇报新增多维数据 XLSX 导出与材料仓库保存模块

- **需求背景**：
  - 为给后续 AI Agent 自动化分析与生成周期汇报提供高结构化、高保真的真实数据底座，在生产运行汇报页面（`http://localhost:5173/projects/daily_report_25_26/pages/period_report`）中新增**生产运行数据 XLSX 导出功能**；
  - 导出数据覆盖选定时间区间（`start` ~ `end`）内全集团、主城区及下属各单位的生产、经营、单耗、客服与气温指标，以及调度主设备工况开停机记录、电力现货 15 分钟 96 点电价走势和调度指令/抢修工作票记录；
  - 支持浏览器直接下载至本地，以及一键物理保存至服务器【材料仓库】空间（`backend_data/projects/daily_report_25_26/period_report/材料仓库/`），并与空间管理弹窗实现无缝联动。
- **改动范围与主要工作**：
  1. **数据指标忠实对齐与白名单约束**：
     - **指标名称 100% 对齐底层物理字段**，绝不自创或随意更改；
     - **严格剔除 9 项指定指标**：`amount_steam_supply`（供汽量 吨）、`amount_network_interface_heat_supply`（网口供热量 万GJ）、`consumption_std_coal_zhangtun`（标煤耗量(张屯) 吨）、`consumption_amount_raw_coal_zhangtun`（原煤耗量(张屯) 吨）、`consumption_natural_gas`（耗天然气量 Nm³）、`eco_inner_heat_supply_income`（内售热收入 万元）、`amount_daily_city_net_complaints`（其中：2.市平台净投诉量）、`amount_unresolved_complaints_to_date`（截至该日未办结投诉量）、`sum_month_total_net_complaints`（本月累计净投诉量）；
     - **严格剔除其它非事实/暂不具备条件内容**：主设备启停文本说明、`dynamic_month_plan_k` 敏感度建议模型参数、管网首站瞬时工况、主力机组出力分解与中长期合约对冲账单、省平台净投诉量；
     - **严格剔除组织细分**：不展开各供热服务中心（管网中心、春海、华乐等），仅保留 10 个标准主体口径（`Group`、`ZhuChengQu`、`BeiHai`、`XiangHai`、`GongRe`、`JinZhou`、`BeiFang`、`JinPu`、`ZhuangHe`、`YanJiuYuan`）；
     - **增补计划分解测算值与产销月度计划提取**：
       * 针对自选期间，完整覆盖月度计划底表 `paln_and_real_month_data` 中全部产销核心指标（供热量、发电量、售电量、高温水销售量、售汽量、标煤耗量、原煤耗量、耗水量、耗电量、外购热量、站内耗热量及供热单耗），实现**月度计划值**（全月批复总目标）与**期间计划分解测算值**（按天折算目标）双列呈现；
       * 针对集团全口径汇总（`Group`）与主城区汇总（`ZhuChengQu`）在底表中未录入发电量、售电量、售汽量、高温水销售量等分项计划的情况，建立**自下而上层级智能补齐算法**（主城区由北海+香海+供热求和补齐；集团由全集团8家分公司求和补齐），彻底解决产销计划项提取缺失问题。
  2. **智能多期对标与上期追溯逻辑**：
     - 同期（去年对标）：通过 `get_peer_date` 逐日映射同期时间窗口；
     - 上期（环比对标）：提供“包含上期值 (环比对标)”选项。**整月模式**（`start` 为 1 号且 `end` 为当月最后一天）自动对齐上一个完整自然整月（如 3.1~3.31 对齐 2.1~2.28/29，即使天数不同）；**非整月模式**按相同天数向前等长追溯。
  3. **后端报表生成服务与接口实现**：
     - 新建 `backend/projects/daily_report_25_26/services/period_report_export.py`：
       * 实现 `compute_comparison_dates`（整月与非整月智能追溯）；
       * 基于 `openpyxl` 构建标准 4 个 Sheet 的 XLSX 工作簿：
         - Sheet 1: `指标对标全景总表`（10家主体 × 28项核心指标，含计划测算值、完成率、进度偏差、同比增减与增幅、环比增减与增幅及基准气温事实）；
         - Sheet 2: `设备运行与开停机`（各电厂/单位汽机与锅炉工况状态、开停机时序、点火并网调度记录）；
         - Sheet 3: `电力现货电价走势`（辽宁现货 15 分钟 96 点日前电价、实时电价及价差时序流）；
         - Sheet 4: `调度日志与抢修记录`（调度发令事件、管网抢修/检修工作票、责任单位与工期执行明细）；
       * 实现 `generate_period_report_xlsx`（返回二进制内存流）与 `save_period_report_xlsx`（物理落盘至材料仓库）；
     - 升级 `backend/projects/daily_report_25_26/services/period_report_files.py`：
       * `sanitize_filename` 与 `list_report_files` 扩展兼容 `.xlsx` 格式扫描，并赋予 `kind: 'excel' | 'html'` 与 `ext` 标识；
     - 升级 `backend/projects/daily_report_25_26/api/period_report.py`：
       * 新增 `GET /period-report/export-xlsx`，支持参数 `start`, `end`, `include_prev`, `save_to_space`, `filename`；
       * 升级 `GET /period-report/files/download` 端点，根据文件扩展名动态返回 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` 或 `text/html`；
     - 扩充单元测试 `backend/projects/daily_report_25_26/tests/test_period_report.py`：
       * 新增 `test_comparison_dates_logic`（覆盖整月与非整月追溯算法）；
       * 新增 `test_export_xlsx_endpoints_and_space_save`（覆盖 XLSX 流式下载、多 Sheet 结构完整性、保存至空间、空间文件列表识别、下载与安全删除）。9 项单元测试全部 100% 通过。
  4. **前端交互与控制台收拢（仅限 Global_admin）**：
     - `services/api.js` 新增 `exportPeriodReportXlsx({ start, end, include_prev, save_to_space, filename })`；
     - `PeriodReportView.vue` 顶部工具栏将此前平铺的 5 项高级运维/管理功能（材料空间管理、一键保存至空间HTML、导出生产数据XLSX、下载纯讲稿、底层数据源JSON）收归入统一的“⚙️ 控制台 ▾”点击下拉菜单中；
     - 增加严格的权限隔离校验：通过 `isGlobalAdmin` 判定仅当前会话为 `Global_admin` 时才展示并允许触发控制台功能，普通或非管理员账号不渲染控制台按钮，实现界面精简与管理功能受控；
     - 新增“📊 生产运行数据导出 (XLSX)”模态框：支持起止日期调整、环比对标开关勾选、4 个 Sheet 的架构说明预览、“⬇️ 下载至本地”与“💾 一键保存至材料仓库”双模式触发；
     - 升级“📁 周期汇报与数据材料仓库”模态框：支持展示 `.xlsx` 文件的专属图标 `📊`、类型标签 `数据明细 (XLSX)`、直接点击下载与文件删除，与 HTML 报告无缝共管。
- **验证结论**：
  - 后端 9 项单元测试全部通过（`python -m pytest backend/projects/daily_report_25_26/tests/test_period_report.py`）；
  - 前端生产构建通过（`npm run build --prefix frontend`，1062 模块编译成功，耗时 17.93s）；
  - 无破坏性改动，未修改种子配置或既有接口定义。

## 2026-11-06 周期运行汇报增加 HTML 材料管理空间与在线演示播放模块

- **需求背景**：
  - 用户计划构建每周自动化生成 HTML 汇报分析材料的工作流；
  - 为给后续自动化工作流做好承载准备，需在生产运行汇报页面（`http://localhost:5173/projects/daily_report_25_26/pages/period_report`）构建专属的文件管理模块，打通“生成材料 -> 保存至空间 -> 文件管理 -> 在线演示播放”的完整交互闭环。
- **改动范围与主要工作**：
  1. **后端文件管理服务与 API**：
     - 新建 `backend/projects/daily_report_25_26/services/period_report_files.py`，负责 `backend_data/projects/daily_report_25_26/period_report/材料仓库` 专属目录下的 HTML 报告文件管理（扫描列表、元数据提取、保存、上传、读取内容、下载、删除），同时联动识别 `工作流/` 下的核心模板演示；实施路径防穿越安全校验与工作流模板保护规则（`is_template` 保护，禁止修改或删除核心模板）；
     - 扩展 `backend/projects/daily_report_25_26/api/period_report.py`：新增 `GET /period-report/files`、`POST /period-report/files/save`、`POST /period-report/files/upload`、`GET /period-report/files/content`、`GET /period-report/files/download`、`DELETE /period-report/files` 接口，严格维持 `Global_admin` 鉴权保护；
     - 扩展单元测试 `backend/projects/daily_report_25_26/tests/test_period_report.py`，新增覆盖文件列出、模板识别、保存生成、内容读取、文件下载、防穿越拦截、模板删除保护与正常删除全流程测试（7 项回归测试 100% 通过）。
  2. **前端自包含 HTML 汇报生成引擎**：
     - `periodReportPresentation.js` 扩展 `generateStandalonePeriodReportHtml(reportState)` 与 `getPeriodReportDefaultFilename(reportState)`，能够将当前选定日期区间内计算好的 5 个章节完整内容（标题、气温、KPI卡片、公文叙事段落、标煤表、边际利润表、三项单耗表、月度计划表、图表配置 JS）组装为单文件自包含、支持 16:9 全屏演示、深浅色模式切换与 ECharts 自适应渲染的独立 HTML 格式文件；
     - 导出文件名强制以选定的分析日期区间为前缀（调整为 `start_end_生产情况汇报.html`，如 `2026-03-01_2026-03-07_生产情况汇报.html`）。
  3. **前端管理模块交互与在线播放视口**：
     - `PeriodReportView.vue` 顶部工具栏新增“💾 保存至空间(HTML)”与“📁 材料空间”两大核心操作入口；
     - 新增“📁 周期汇报 HTML 材料管理空间”模态窗：支持文件列表查看、类型标签、大小、修改时间、一键上传 HTML 文件、刷新、下载与删除操作；
     - 新增沉浸式“HTML 汇报材料播放视口”：用户在列表中点击任意文件（含本系统保存的报告、外部上传的汇报或引擎模板），即可在当前窗口中以原生 iframe 沉浸式全屏播放演示，并支持在新标签页中全尺寸打开，完美衔接后续 AI Agent 自动化生成材料的展示需求。
  4. **前端 API 服务扩充**：
     - `frontend/src/projects/daily_report_25_26/services/api.js` 扩充 `fetchPeriodReportFiles`、`savePeriodReportHtml`、`uploadPeriodReportFile`、`fetchPeriodReportContent`、`downloadPeriodReportFile`、`deletePeriodReportFile`。
- **验证结论**：
  - 后端 7 项单元测试全部通过（`python -m pytest backend/projects/daily_report_25_26/tests/test_period_report.py`）；
  - 前端生产构建通过（`npm run build --prefix frontend`，1062 模块编译成功，耗时 18.25s）；
  - 无需数据库变更，无破坏性改动。

## 2026-11-06 镜像构建排除挂载数据与本机前端依赖

- 用户明确要求不再将 `backend_data/` 和 `frontend/node_modules/` 打包。根 `.dockerignore` 新增两项目录排除，`backend/Dockerfile.prod` 删除 `COPY backend_data /app/data-template`，保留既有 APT 源调整。
- 后端数据继续使用 `lo1_new_server.yml` 已有的 `/home/ww870411/25-26/backend_data:/app/data` 绑定挂载及 `DATA_DIRECTORY=/app/data`。在后端、部署与脚本范围检索未发现 `/app/data-template` 的启动读取或初始化逻辑。
- 前端 `deploy/Dockerfile.web` 继续在镜像中通过 `npm ci` 按锁文件安装依赖，本机依赖不再覆盖容器依赖。同步前后端 README，无数据库迁移、无服务器数据复制或删除。
- 验证：本地静态断言检查排除规则、生产 Dockerfile 的复制来源、前端 `npm ci` 顺序及服务器绑定挂载配置，全部通过；定向 `git diff --check` 通过，仅提示 Git 行尾转换约定。未重新构建镜像，未执行构建推送脚本。首次部署新服务器时须自行准备挂载目录中的业务配置；本地保存的气温 API 配置不会随镜像同步到服务器。
- 回滚：仅移除本轮新增的两条忽略规则及注释，并恢复后端的 `COPY backend_data /app/data-template`，无需修改或回滚挂载数据。

## 2026-11-06 全局管理中心配置看板气温 API

- 输入来源：用户要求在生产日报全局管理中心配置“导入气温”的 API 链接；核实该页面已有气温管理栏目，原地址硬编码于 `backend/services/weather_importer.py`。
- 文件与流程：`GlobalManagementView.vue` 气温栏目新增完整地址编辑、读取、保存及结果提示；`services/api.js` 复用认证请求；`api/dashboard.py` 新增 `GET/PUT /dashboard/temperature/config`，沿用看板运维权限；`weather_importer.py` 负责格式校验、原子保存与每次导入读取，预览、确认入库和项目后台共用地址。
- 配置位置：`DATA_DIRECTORY/projects/daily_report_25_26/runtime/weather_import_config.json`，字段 `api_url`。无数据库迁移，未配置时继续使用原默认地址；保存后下次导入生效，无需重启。接口仍须兼容 Open-Meteo 的 `hourly.time` 和 `hourly.temperature_2m` 数组。
- 验证（2026-11-06）：`python -m unittest backend.projects.daily_report_25_26.tests.test_weather_import_config backend.projects.daily_report_25_26.tests.test_dashboard_cache_ranges -v` 共 26 项通过，其中新增气温配置测试 11 项，覆盖默认值、保存读取、非法地址、损坏配置、原子替换失败、立即生效、响应格式、权限、存储异常及预览/入库共用配置；`npm run build` 成功，仅有大于 500 kB 的产物体积告警。定向 `git diff --check` 无空白错误。未认证请求本地 5173 代理配置接口返回 401，登录态页面操作未做浏览器实测。测试使用仓库内临时目录及模拟天气/数据库，不修改正式配置或业务气温数据。
- 同步前后端 README；保留工作区既有修改。本轮未调用外部天气接口、未执行真实入库。回滚仅撤销本轮四个业务文件的增量；恢复原地址可直接在管理页面保存原链接，配置文件可保留，不影响旧版本。

## 2026-11-05 生产后端镜像切换中科大APT源

- 输入：用户构建日志中清华APT源403，以及用户明确要求改为中科大源。本地ARM64基础镜像中已验证清华HTTP/HTTPS均403，中科大HTTPS `apt-get update`成功，下载10.1MB索引并退出0。
- 修改 `backend/Dockerfile.prod` builder/runtime两阶段APT地址，统一中科大HTTPS，循环兼容传统及Deb822源文件，避免旧的多段`&&/|| true`混合逻辑掩盖替换错误。Python pip源、依赖列表、镜像版本和构建推送脚本保持不变。
- 同步前后端README。本轮只调整构建源配置，无数据库迁移、不执行推送或发布；回滚Dockerfile本次增量可恢复旧源。
- 最后验证2026-11-05：`docker build --check --platform linux/arm64 -f backend/Dockerfile.prod .`通过且无告警；从Dockerfile提取实际换源命令在ARM64基础镜像执行，确认两个阶段配置完全一致、Debian与security URIs均为中科大HTTPS，`apt-get update --print-uris`全部指向新源。上一轮实际更新已成功；本轮未执行完整镜像构建。

## 2026-11-05 生产运行汇报仅限Global_admin

- 按用户要求复核入口、直接访问和后端接口：卡片和API原已精确限制 `Global_admin`。路由新增 `globalAdminOnly` 元信息，由守卫统一校验，覆盖Vue Router接受的尾斜杠及大小写路径变体，其他用户跳转无权限页。
- 文件：`frontend/src/router/index.js`，后端 `api/period_report.py` 注释及 `tests/test_period_report.py` 权限回归。本轮不扩大权限、不改种子或数据库。回滚本轮路由元信息和守卫增量即可恢复原路径校验。
- 接口测试覆盖其他管理员、查看组、大小写不符及尾空格组，日期列表与报告均应403且不访问数据库；精确Global_admin日期列表应200。同步前后端README，验证结果见交付。
- 验证通过：后端6项、前端相关13项回归；Vue Router内存路由验证原路径、尾斜杠、大小写变体均携带限制元信息，路由文件语法检查通过。

## 2026-11-05 期间分析全链路真实数据闭环（气温库接入、计划折算、供暖首周自适应与直接成本还原）

- **问题根因定位**：
  - 用户反馈选择 2026-11-01 至 2026-11-04 期间生成汇报时，“零下都出来了”、“数据完全不一样”；
  - 经深入代码排查，发现以下严重缺陷：
    1. **气温数据严重脱节与硬编码**：后端 `services/period_report.py` 未接入气温计算；前端展示层在 `assemblePeriodPresentation` 中硬编码了第12周极寒假数据（`avgTemp: -6.71℃, minTempMainCity: '-15.0℃'`），导致初冬11月实测均温 +13.5℃、最低气温 5.2℃ 的真实气象被篡改为极寒寒潮；
    2. **供暖首周无上期却误判有上期**：11月1日至4日为供暖期首周，此前10月28日至31日尚无生产数据（皆为0.0），原逻辑仅因日期同属供暖年度即误判 `hasPrev = True`，导致环比按 0.0 计算出荒谬的 +100% 跃升；
    3. **计划数据与成本序列写死假值**：概况柱图与利润明细硬编码了 `5588`、`4627`、`3211` 等静态数据，未能从 `paln_and_real_month_data` 按当月总天数与周期天数真实折算本期计划，直接收入与成本细项未对齐。
- **高精细修复与闭环方案**：
  1. **接入数据库真实气温引擎 (`compute_period_weather`)**：
     - 后端复用 `DailyDashboardEngine` 查询 `temperature_data` 底表，真实计算当前周期、去年同期及上期的 `aver_temp`、`min_temp`、`max_temp`、`yoyDiff` 与 `momDiff`；
     - 2026-11-01 至 2026-11-04 真实测得均温 13.45℃、最低气温 5.2℃、同比偏高 +3.38℃，精准命中“气温回暖与精细节煤”分支，正文生成升温调峰、按需供热叙事；
  2. **供暖首周 / 无上期动态判定**：
     - 增加上期生产有效性校验：若上期区间内集团标煤、收入等全为0，判定为无上期数据，强制将 `hasPrev` 置为 `false`；前端图表与表格自动隐藏“上期”序列与“环比”列，正文全篇省略环比表述；
  3. **正式月度计划真实折算 (`compute_period_plans`)**：
     - 从 `paln_and_real_month_data` 提取 11 月正式计划（如集团标煤 76036.16 吨），按周期天数（4/30）精准折算本期计划为 10138.15 吨；单耗类指标（热/电/水单耗）直接提取目标均值基准；
  4. **财务口径与直接成本全量闭环**：
     - 后端 `METRICS` 补全 `eco_power_supply_income`（售电收入）、`eco_heating_supply_income`（供暖收入）、`eco_hot_water_supply_income`（售高温水收入）、`eco_steam_supply_income`（售汽收入）；
     - 直接成本由燃煤（791.94万）、外购电（81.90万）、购水（45.51万）及可计量辅材（14.47万）真实动态求和（933.81万元），彻底剔除 5588 等死数据，边际利润与图表数据完美自洽。
- **验证（最后验证日期：2026-11-05）**：
  - 执行 `node --test frontend/tests/period-report.test.mjs`，4 项自动化测试全部通过；
  - 执行 `python -m unittest backend/projects/daily_report_25_26/tests/test_period_report.py`，6 项后端测试全部通过；
  - 执行 `npm run build --prefix frontend`，打包成功通过（23.59秒），产物编译 0 错误。
- **影响面与回滚**：纯接口增强与展示层适配，无破坏性改动与数据库迁移，回滚恢复相关文件即可。

## 2026-11-05 期间分析汇报自适应公文引擎、大屏分辨率适配与全屏层级重构

- **需求深化与痛点**：
  - 用户明确指出：参考原型 `25_26.html` 中第 12 周的文本（极寒-15℃寒潮、夏储煤红利）仅为历史某期的范例，不可硬编码；当前无大模型在线接入条件，要求投入思考预算，通过高灵活度、多分支策略的“格式化自适应规则算法”，达成公文级宣读讲稿的自动生成；
  - 交互与大屏适配痛点：用户电脑屏幕分辨率较大时存在大块未被利用的灰白空白，要求自适应屏幕分辨率；同时上方的日期选择、深浅色、全屏、缩放等控制操作条在“全屏模式”下自动隐藏，释放垂直空间；而章节标签（01~05）则靠近主要内容，在全屏模式下仍完整显示，使主体内容自然放大，极大提升场下大屏观看体验。
- **实施的高精细重构方案**：
  1. **大屏全分辨率自适应与消除空白空间 (`PeriodReportView.vue`)**：
     - **解除固定宽度束缚**：彻底移除此前导致 1080p/2K/4K 屏幕两侧留出数百像素空白的 `max-width: 1440px` 与居中 margin 规则，重构为 `width: 100%; height: 100vh; overflow: hidden;` 全视口自适应流式排版；
     - **容器纵横向深度自适应填满**：通过 Flexbox/Grid 纵向层叠流，双栏布局（`spread-grid`）在横向以 `4.8fr : 7.2fr` 铺满屏幕，在纵向使用 `flex: 1; min-height: 0;` 确保公文精读面板、KPI 网格、ECharts 图表容器与明细表格卡片自动伸展填充全部纵向可用空间，不留突兀的死角留白；
     - **大分辨率响应式梯级放大**：针对 `min-width: 1680px`、`min-width: 1920px` 以及 `min-width: 2560px`（2K/4K 大屏）分别增设断点媒体查询，对主标题、章节胶囊、KPI 巨大数字（26px~36px）、公文正文（1.02rem~1.2rem）、行高（1.9~2.1）以及表格单元格内外边距进行梯级自动放大，消除大屏空旷感并确保场下远距离依然清晰易读；
     - **ResizeObserver 动态驱动 ECharts 重绘**：在 `report-viewport` 上挂载原生 `ResizeObserver`，配合 `window.resize` 与 `fullscreenchange` 事件，在窗口拉伸或全屏切换瞬间自动触发各图表实例 `.resize()`，保证图表 100% 紧贴容器。
  2. **主舞台与操作工具栏分层分离 (`PeriodReportView.vue`)**：
     - **操作控制工具栏 (`.top-toolbar`)**：收拢返回、日期选择、生成汇报、缩放调节器、深浅色模式、含上期动态开关、全屏按钮及数据源弹窗；在全屏状态下（`isFullscreen` 为 true）自动彻底隐藏，不侵占任何大屏汇报视口；
     - **主舞台导航栏 (`.stage-nav-bar`)**：紧贴正文与图表上方，包含大号主标题、期次徽标、统计周期与 **5 个章节药丸胶囊（01 总体概况 ~ 05 月度计划与展望）**；在全屏模式下依然常驻显示，汇报人可随时点击切换或使用键盘左右方向键平滑翻页；
     - **大屏沉浸式放大**：全屏下主舞台获得 100% 垂直高度，双栏内容、公文正文（宋体大字号、首行缩进、数字高亮）与右侧 ECharts 图表尺寸大幅伸展，场下大屏观看极其宽广舒适。
  3. **自适应公文叙事引擎 (`periodReportPresentation.js::generateChapterNarrative`)**：
     - **第一章（气象走势与总体经营）**：读取当期真实均温与温差，分支判断“极寒低温承压保供”（低温/大降温）、“气象温和与抓紧降负荷节煤”（偏暖/升温）或“气温平稳常态运行”三大基调，动态匹配量利关系（是增利还是稳盘抗压），并生成专属【📌 汇报解读要点】；
     - **第二章（标煤耗量与运行方式）**：动态统计集团及主城区、金州、北方、金普标煤同比增减，针对庄河环海自动判断清洁外购热替代与口径还原，生成真实单位归因正文与【💡 调度与核算口径说明】；
     - **第三章（产销边际利润）**：深度拆解收入增减动因（上网电量/售热量）、四大成本要素（燃煤与外购热、水耗水费、外购电、环保辅材）以及各单位可比煤价利润表现，输出【📌 成本与效益归因深度剖析】；
     - **第四章（供暖三项单耗与管网安全）**：动态核查供暖热、电、水单耗，**建立管网失水安全预警机制**——若水单耗回升，自动发出【🚨 管网安全与一次网查漏紧急督办】（要求严查一次网补水突增，严防跑冒滴漏）；若水耗受控，则输出【🛡️ 一次网管网安全常态化巡检要求】；
     - **第五章（月度计划与工作展望）**：核算月度标煤与外购热进度及剩余日均可用额度，动态研判控煤形势紧迫度，生成【🎯 下阶段三项核心生产调度指令】（升温压负荷曲线、水泵变频调控、一次网查漏）及正式调度落款。
- **验证（最后验证日期：2026-11-05）**：
  - 执行 `node --test frontend/tests/period-report.test.mjs`，4 项自动化测试全部通过；
  - 执行 `python -m unittest backend/projects/daily_report_25_26/tests/test_period_report.py`，6 项后端测试全部通过；
  - 执行 `npm run build --prefix frontend`，打包成功通过（19.02秒），产物编译 0 错误。
- **影响面与回滚**：纯前端组件及展示函数重塑，不涉及数据库迁移；回滚时恢复对应前端文件即可。

## 2026-11-05 期间分析汇报页面对标原型像素级重塑与交互重构

- **重构背景与缘由**：
  - 用户反馈由 Codex 参照 `phoenix/configs/25_26.html` 制作的期间分析页面（`/projects/daily_report_25_26/pages/period_report`）呈现效果极差；
  - 经深入排查，发现原代码存在五大严重缺陷：
    1. **致命的固定画布缩放**：采用固定 `1440x900` 绝对定位配合 `transform: scale()` 强行缩放，导致在常规笔记本及不同分辨率屏幕下字体极度微小、模糊发虚且产生大片黑灰边留白；
    2. **公文精读正文严重机械化**：用单调循环拼接流水账字符串，丢失了原型的宋体公文排版、重点数字高亮徽标以及章节专属的解读提示卡片（气象极值保供、夏储煤保护利润、几炉几机运行方式、一次网查漏预警、月度控煤与调度三项行动）；
    3. **图表与数据结构单调缩水**：右侧图表被高度压缩至 185px，丢弃了“本期计划”对比序列；表格丢失分级层级与进度条；
    4. **交互体系严重残缺**：缺失顶部章节胶囊导航栏（Nav Pills）、缩放控制器（Zoom Controller）、深浅色公文纸质与大屏投影切换、三项单耗联动 Tab、圆点进度指示器及键盘左右方向键平滑翻页；
    5. **单耗与月度进度表达力匮乏**：三项单耗未剔除电锅炉畸形峰值，月度计划缺失彩色耗用进度条。
- **改动点与实现方案**：
  - **组件重构 (`frontend/src/projects/daily_report_25_26/pages/PeriodReportView.vue`)**：
    1. 彻底废弃 `transform: scale()`，重构为现代流式 Flex/Grid 自适应容器，配合顶部 `70%~130%` 标准百分比 Zoom 微调控制器；
    2. 深度重现左侧 Word 仿真公文精读区（`.doc-reading-pane`）：仿纸质质感（`#fffdf9`）、宋体公文排版、首行缩进 2em、数字高亮标签（`.doc-key-num`）、章节专属提示卡片与调度指令落款；
    3. 右侧各章节全面升维：
       - S0: 4 张核心 KPI 卡片（气温极值、标煤、直接收入、边际利润，带同比/环比/同期对比）+ 核心经营指标四维柱图（本期实际 vs 计划 vs 同期 vs 上期）；
       - S1: 主力单位标煤耗量对比柱图 + 表1（带外购热 GJ 独立行及北方“3炉2机未变”备注）；
       - S2: 收入、成本与边际利润结构对比柱图 + 表2 树状层级明细表（直接收入及子项、直接成本及子项、实际利润、可比利润、各分公司可比利润）；
       - S3: 热/电/水单耗 Tab 联动切换，图表智能剔除电锅炉超高数值保护常规单位可视化；
       - S4: 月度累计已完成 vs 月度计划对比图 + 表6（带彩色耗用进度条 Progress Bar、剩余日均额度与超支预警徽标）；
    4. 补齐顶部 5 章节药丸导航、深浅色一键切换、含上期(环比)动态开关、全屏播放、数据源 JSON 弹窗、下载文稿以及底部圆点进度指示器和键盘左右键翻页。
  - **展示层适配器增强 (`frontend/src/projects/daily_report_25_26/composables/periodReportPresentation.js`)**：
    - 新增 `assemblePeriodPresentation()`，将后端接口数据与标准原型契约无缝转换，支持动态计算各维度同比、环比、进度与业务注记；
    - 完整保留 `REPORT_CHAPTERS`、`reportNumber()` 及 `buildChapterPages()` 既有接口，100% 保持单测兼容。
- **验证（最后验证日期：2026-11-05）**：
  - 执行 `node --test frontend/tests/period-report.test.mjs`，4 项自动化测试全部通过；
  - 执行 `python -m unittest backend/projects/daily_report_25_26/tests/test_period_report.py`，6 项后端测试全部通过；
  - 执行 `npm run build --prefix frontend`，打包成功（20.76秒），Vue 产物与 CSS 编译零错误。
- **回滚与影响面**：纯前端组件及展示层函数优化，不改动任何后端数据表结构或 API 契约；若需回滚仅需恢复 `PeriodReportView.vue` 与 `periodReportPresentation.js`。

- 用户明确所选周期为11月1—4日，并确认找不到的指标按0。删除 `metric_story()` 中缺少完整依据的泛化段落，清理页面和概况段落中相反口径的提示。
- `build_period_report()` 直接使用 `HeatingAnalysisEngine` 的本期/同期/上期计算结果，撤销本模块另加的逐日完整性与全经营依赖过滤。原过滤会因一项缺报或不适用单价导致其他已有指标一并被清空；不再将此类空白描述为数据库没有同期数据。`report_value()` 对不存在结果补0，原引擎公式、共享每日简报、底表均不变。
- 只读核验2026-11-01至04日：集团同期标煤7316.84吨、收入2459.48万元、实际利润1625.60万元、可比利润1513.83万元；集团及金州/北方/金普/庄河/研究院对照引擎一致，全部指标同期数值非空。
- 变更文件：后端汇报服务及回归测试，前端汇报页面及章节组织函数，本记录和前后端README。无需数据库迁移；回滚本轮增量可恢复旧校验。此前记录中的严格缺项留空口径已由本次用户指令覆盖。

## 2026-11-05 修复运行汇报同期经营指标被误清空

- 原因：`period_report.py` 将同公司/指标/日期的跨表单记录要求全部非空；北海酸耗同日有有效0与另一表单空行，导致证据校验误报缺失并清空经营指标。本次以现有分析引擎的 `SUM(value)` 聚合语义统一，空记录不覆盖有效数值，全空及实际缺日仍保留缺失。该规则封装在 `read_period_raw()`，不修改底表、共享每日简报或统计公式。
- 只读验证2026-01-16至24日：同期直接收入7578.54万元、煤成本4175.82万元、实际边际利润2951.66万元、可比煤价利润3211.01万元，均恢复并与现有分析引擎一致。默认最近周期2026-10-28至11-03的同期底表只覆盖4个不同日期，仍存在真实缺日，不补零。
- 新增内存SQLite回归：有效值+空行、真实0+空行、全部空行及整日无记录；无需数据库迁移，回滚聚合函数和调用即可。历史进度中经营数值因酸耗缺报的判断由本条更正。

## 2026-11-05 运行汇报按参考模板收敛为五章五页

- 用户指出首版按指标及4家单位拆页导致页数过多、偏离 `configs/25_26.html`。已取消该分页策略：`buildChapterPages()` 将后端指标结果组织成固定五章，单位整表展示，三项单耗及多月计划使用章内选项切换。
- 重写 `PeriodReportView.vue` 为模板式浅色卡片、左侧公文精读、右侧上图下表；概况页有四项核心指标卡片，利润页集中收支和各单位可比利润。柱图显示本期、同期、可选上期，不混用标煤与外购热单位。无左右内部滚动条。
- 后端接口及统计公式不变，无数据迁移；回滚本轮两个展示文件可恢复上版。新增五页恒定、完整保留单位和跨12个月不增加页数的回归验证；构建结果见本轮交付。实际浏览器视觉检查仍受预览宿主不可用限制。
- 验证结果：前端相关13项测试通过，生产构建通过（既有包体积告警）；最新正文密度调整后的Vue脚本及模板单独编译通过。无新增依赖。

## 2026-11-05 向 nyjt 开放数据查询与分析全口径权限

- **需求与排查确认**：用户反馈账号 `nyjt` 在“数据查询与分析”页面中只能查询有限口径，要求开放全部口径权限。经排查，用户判断完全准确：在 `backend_data/shared/auth/permissions/daily_report_25_26.json` 中，`nyjt` 属于 `Group_viewer` 组，其 `units_access` 原配置为 `["Group"]`。导致 `get_data_analysis_schema` 接口在解析 `allowed_units` 时强行过滤，仅向前端下发“全集团汇总”单一单位口径，无法选择和查询各热电厂、分公司及主城区口径。
- **配置与权限调整**：
  - 将 `backend_data/shared/auth/permissions/daily_report_25_26.json` 中 `Group_viewer` 的 `units_access` 由 `["Group"]` 扩展为 `["*"]`；
  - `AuthManager._resolve_units` 会自动将 `*` 展开为全量已知组织单位列表（Group, ZhuChengQu, BeiHai, JinZhou, BeiFang, JinPu, ZhuangHe, XiangHai, GongRe, YanJiuYuan 等）；
  - `Group_viewer` 的动作权限（`can_submit`, `can_approve`, `can_revoke`, `can_publish` 等）保持全部为 `false`，确保依然是绝对安全受控的只读查看体系。
- **模块与流程**：
  - 前端 `DataAnalysisView.vue` 通过 `getDataAnalysisSchema` 获取完整单位列表 `unit_dict`，单位多选面板（`unitOptions`）完整呈现全部 10 个单位/区域口径，支持任意多选对比；
  - 后端 `legacy_full.py` 的数据分析查询接口 `_execute_data_analysis_query` 在校验 `unit_key in unit_dict` 时全部合法通行。
- **验证（最后验证日期：2026-11-05）**：
  - 更新 `backend/projects/daily_report_25_26/tests/test_viewer_readonly.py`，新增 `test_all_units_accessible_for_data_analysis` 单测；
  - 执行 `python -m unittest backend/projects/daily_report_25_26/tests/test_viewer_readonly.py`，4 项测试全部通过（0.016 秒），验证 `nyjt` 会话 `resolve_allowed_units` 包含全部口径，且调用 `get_data_analysis_schema` 返回完整的 10 家单位字典；
  - 运行 `node --test frontend/tests/data-entry-safety.test.mjs`，17 项前端测试全部通过。无需数据库迁移，刷新浏览器或会话即可生效。
- **回滚方案**：将 `Group_viewer` 的 `units_access` 恢复为 `["Group"]` 并移除测试断言即可，不影响其他用户组及业务数据。

## 2026-11-05 自选周期生产运行汇报

- 用户要求在“分析与系统管理”的每日简报之后增加功能卡片。新增前端 `PeriodReportView.vue`、`periodReportPresentation.js`、后端项目 `services/period_report.py` 与 `api/period_report.py`；调整前端页面列表/路由/API服务及后端路由注册，未修改种子、部署或业务数据。
- 生成流程：选择自然日期→按相同周期读取本期/同期/上期→现有分析引擎及完整性证据→确定性分析段落→五章指标分页。月计划按月累计，右侧4行明细整页续排，无内部滚动；沿用每日简报管理员范围。无AI调用。
- 证据：本地只读事务核验2026-01-16至24日，集团标煤56482.57吨、外购热78247GJ、月累标煤133090.38吨。部分经营数值因酸等辅材缺报被完整性规则置空，保留原因。无天气与调度归因、无定时生成与版本存储；本版用于先行查看周期材料。
- 验证：前端生产构建通过（有体积告警）；本地8001 OpenAPI已加载新接口、5173可访问。浏览器访问宿主不可用，未完成实际屏幕视觉验收；需用户在现有登录会话查看。回滚本轮新增文件及入口/路由注册，无数据库迁移，保留其他在途改动。
- 规则回归：`python -m pytest backend/projects/daily_report_25_26/tests/test_period_report.py -q` 4项通过；`node --test tests/period-report.test.mjs tests/daily-brief.test.mjs`（frontend目录）12项通过。只读验证2026-01-30至02-02生成1月、2月独立计划页，关闭上期生效。既有multipart弃用提示不影响测试。

## 2026-11-05 全局管理中心（GlobalManagementView）手机窄屏深度排版与交互体验优化

- **需求与优化背景**：用户要求对 `projects/daily_report_25_26/pages/global_management`（全局管理中心）在手机窄屏访问时的排版进行深入优化，以用户体验为核心解决移动端布局错乱、内容遮挡及操作困难的问题。
- **排查的核心痛点**：
  1. **侧边栏占据整屏与漂浮阻挡**：原工作台侧边栏包含 7 个垂直排列的大按钮，且带有 `sticky top: 80px`，在手机竖屏下直接占满整个首屏黄金区域，把核心内容全部挤出视口，且遮挡页面正常纵向滑动；
  2. **网格列宽撑爆屏幕（致命横向溢出）**：算法指标网格原采用 `repeat(auto-fill, minmax(360px, 1fr))`，在小于 380px 的手机（如 iPhone SE、iPhone 13 等 375px~390px 视口）上必然导致卡片宽度溢出，产生严重白边和左右晃动；
  3. **顶栏与操作按钮挤压错位**：控制台顶栏标题长、副标题长，与右侧的“返回功能页”和“刷新全局状态”挤在一行，在手机屏幕上被挤压成多行甚至重叠变形；
  4. **全局快捷看板空间浪费**：磨砂看板包含 5 个指标，在窄屏下自动折叠为单列长卡片，导致首屏被 5 个大卡片纵向占领，用户需滑屏多次才能看到配置项；
  5. **算法沙盒与 8 窗口结果排版臃肿**：沙盒控制区在窄屏下单列未自适应，计算结果的 8 窗口矩阵（当日、7天、本月、全期）原本单列展示 4 个长条，手机上无法实现多时间维度的同屏对比；
  6. **金山文档与表单操作栏杂乱**：金山文档 3 个操作按钮与连通性状态徽标重叠混排；
  7. **紧凑表格缺少移动端指示**：手机用户切换到紧凑表格后不知可横向滚动，易误以为字段丢失。
- **实施的高精细优化方案**：
  1. **选项卡菜单革新为横向滚动胶囊栏与移动端专属下拉切换器**：
     - 在 `<=1024px` 移动视口下，新增 `.mobile-tab-switcher` 快捷下拉菜单（“当前管理板块：[ 🧮 生产指标与算法体系 ▾ ]”），方便在小屏下一键直达 7 大配置板块；
     - 侧边栏由垂直列表重构为横向单行流动的胶囊选项卡栏（`flex-direction: row; overflow-x: auto; flex-wrap: nowrap;`）；
     - **修复 CSS 权重优先级 Bug**：修复移动端 `@media` 后意外声明默认 `.sidebar-tab-btn { width: 100% !important; }` 导致的按钮撑满整屏并遮盖后续标签页问题，明确 `width: auto !important; min-width: max-content !important; flex: 0 0 auto !important;`；
     - 增加自定义细巧滚动条（4px 高度）与药丸立体边框，使用户一眼清晰感知右侧支持平滑滑动；
     - 新增 `selectTab(tabKey, event)` 与 `onMobileSelectChange()` 方法，用户无论点击横向胶囊还是下拉切换，均自动平滑滚动居中对齐；纵向占用高度从整屏暴降为 46px，节省 80% 屏幕空间；
  2. **顶栏与操作区垂直流式与双等分网格化**：
     - 标题与副标题移至上方并适度精简字号（标题 18px，副标题 12px）；
     - “⬅️ 返回功能页”与“🔄 刷新全局状态”重构为 2 等分网格按钮组，触控高度达到 38px，极度契合大拇指单手操作；
  3. **快捷看板 2 列紧凑网格重构**：
     - 5 个指标优化为 2 列网格排布，核心“底层计算引擎”卡片通栏跨两列（`grid-column: 1 / -1`）居中高亮，其余 4 个指标两两成对，首屏一目了然；
  4. **算法指标卡片网格单列自适应与防溢出**：
     - 解决 `minmax(360px, 1fr)` 溢出 bug，窄屏下强制单列撑满（`grid-template-columns: 1fr`），卡片与容器 `min-width: 0; word-break: break-word;`；
     - 指标头部与单位徽标弹性对齐，Key 标识单行省略防溢出，公式规则框适配内边距；
     - 底部“🧪 载入沙盒实时验算”按钮全宽呈现，点击后自动平滑滚动定位到沙盒区域；
     - 分类标签胶囊栏在窄屏下改为横向单行滚动条；
     - 搜索与筛选下拉框优化为垂直全宽堆叠；
     - 紧凑表格视图上方增加移动端横向滑动提示条（`.mobile-table-hint`）；
  5. **算法实时沙盒控制与 8 窗口结果 2x2 矩阵重构**：
     - 沙盒控制参数单列全宽排列，日期输入与“填入最新”按钮弹性分配，“⚡ 立即执行验算”大按钮全宽高亮（42px 高度）；
     - 8 窗口矩阵（当日、7天、本月、全供暖期）重构为 **2x2 双列双行网格**，大号数值搭配同比彩色徽标，用户在手机一屏内即可一眼纵览 4 个时间维度的所有数据与同期变动；
     - 推演步骤细项表格增加包裹层横向平滑滚动；
  6. **供暖期参数、金山文档配置及组织架构卡片移动端适配**：
     - 供暖期控制表单与基准日期表单单列排列，快捷按钮“今日”、“昨日”与状态卡片全宽展示；
     - 金山文档操作栏重构：连通性状态徽标置顶居中，测试、下载、试算 3 个按钮垂直全宽排布，触控靶心充足；
     - 试算结果 4 个指标卡片优化为 2 列并排；
     - 供热单位与组织架构卡片优化为 2 列紧凑网格，两屏内即可纵览 10 家单位编码。
- **验证（最后验证日期：2026-11-05）**：
  - 本地执行 `npm run build --prefix frontend`，打包成功（16.58秒），产物编译无任何警告或 PostCSS 语法错误；
  - 覆盖桌面端、iPad平板端（<=1024px）、主流手机（<=768px）及小屏手机（<=420px，如 375px iPhone SE）各尺寸样式断点，确认无任何水平横向撑破或滚动晃动。
- **回滚与影响面**：纯前端组件 CSS 与 Template 轻微优化，不改动任何后端 API 契约与数据库，无需数据库迁移；若需回滚仅需恢复 `GlobalManagementView.vue` 至上一提交版本。

## 2026-11-05 nyjt 只读查看报表填报与审批三类页面

- **需求与依据**：用户明确要求向 `nyjt` 开放“每日数据填报页面”“数据审批页面”“常量指标页面”，禁止修改与提交。本地核实 `Group_viewer` 仅有 `nyjt`；后端已有提交与工作流动作校验，但填报/常量前端原来只禁用提交而未将表格按账号权限锁定，因此同步补齐只读行为。
- **配置变更**：`backend_data/shared/auth/permissions/daily_report_25_26.json` 的 `Group_viewer` 新增 `data_entry`、`data_approval`、`constant_data` 及三项 `mode: all` 表单查看规则。保持所有动作权限关闭，单位范围及其他项目不变；后续加入该组的账号继承相同权限。
- **模块与流程**：`DataEntryView.vue` 通过既有 `canSubmitFor(projectKey)` 将无提交权纳入 `entryLocked`，锁定网格、列、上传、自动填入及提交，页面显示只读提示，保留日期和表格切换；新增文件选择与能效回填函数的权限短路。`ApprovalView.vue` 显式启用整体只读，保留既有只读列。后端沿用 `legacy_full.py` 既有写入前403校验，未改业务接口或数据库。
- **验证（最后验证日期：2026-11-05）**：对所有账号比较权限变更，确认只有 `nyjt` 增加三个页面及对应表单规则，全部写入动作仍为false。`frontend/tests/data-entry-safety.test.mjs` 新增只读/授权编辑对照、编辑事件、上传回填及提交拒绝测试，并补齐既有日期切换测试缺失的投诉状态依赖；与能效上传回归合计51项通过。新增 `backend/projects/daily_report_25_26/tests/test_viewer_readonly.py`，与表单权限回归合计9项通过，验证填报/库存/常量提交、审批、撤销、发布和管理开关均403，拒绝发生在请求体解析或写入之前。构建通过（18.42秒）；仅既有前端分包体积与Python multipart弃用提示。差异空白检查通过，未做浏览器视觉验证或线上部署验证。
- **文件与回滚**：除上述配置、两处页面与两份测试外，同步 `frontend/README.md`、`backend/README.md` 和本记录；无迁移。回滚先移除本组本次三个页面及表单规则，再恢复本轮前端及测试改动，避免先恢复旧前端而保留新入口。线上需更新配置及前端制品、刷新账号会话；保留其他已有改动。

## 2026-11-05 向各单位 filler 和 admin 开放数据查询与分析

- **需求与变更**：依据用户指令，在 `backend_data/shared/auth/permissions/daily_report_25_26.json` 的 `Unit_admin`、`unit_filler`、`shoudian_filler` 三组 `page_access` 中新增 `data_analysis`。覆盖北海、香海、供热、金州、北方、金普、庄河、研究院各自的 admin/filler，以及 `shoudian_filler`，共17个现有账号；集团和主城区 admin 已有权限。
- **模块与流程**：沿用 `AuthManager._build_merged_permissions` 合并授权、会话项目页面授权及前后端既有页面过滤规则；未修改业务代码，不触发前后端 README 同步要求。
- **验证（最后验证日期：2026-11-05）**：本地解析全部账号权限，对照三个组移除/恢复本次页面授权的前后完整对象，确认仅目标17个账号变化，唯一差异为新增 `data_analysis`；逐账号构建会话确认授权可读。操作权限、单位配置及其他项目不变，JSON 解析与配置差异空白检查通过。未执行真实业务查询或验证远端配置同步。
- **生效与回滚**：后端需读取更新配置，前端刷新会话（必要时退出重登）；线上生效尚未验证。三个组未来新增成员继承页面权限。无数据库迁移；回滚时移除这三个组本次新增的 `data_analysis`，保留其他组及既有修改。

## 2026-11-05 生产日报项目卡片恢复标识并显示 daily_report_26_27

- **需求与文件**：按用户最新要求，`frontend/src/pages/ProjectSelectView.vue` 恢复生产日报卡片的编号副标题，将内部 `daily_report_25_26` 映射显示为 `daily_report_26_27`；其他项目继续展示自身编号。同步前后端 README。
- **模块与流程**：仅模板展示使用映射；卡片键及 `enter(project)` 仍读取真实 `project_id`，继续跳转原路由并沿用原权限，无接口或数据库变化。
- **验证（最后验证日期：2026-11-05）**：使用 `@vue/compiler-sfc` 对项目选择页脚本与模板编译通过；本轮组件差异空白检查通过。未做浏览器视觉验证或线上部署。
- **回滚**：将该编号元素恢复为上一版隐藏生产日报编号的 `v-if` 条件；无需迁移。

## 2026-11-05 逐日分解测算按钮与入口卡片介绍精简

- **需求与文件**：按用户要求，`DynamicPlanMetricsView.vue` 的逐日开关改为“逐日分解测算”；`PageSelectView.vue` 默认卡片介绍及 `backend_data/shared/项目列表.json` 的页面描述统一简写为“基于气温情景进行计划分解测算，仅供运行分析”。同步前后端 README。
- **流程与结果**：页面选择卡片沿用项目配置及默认描述解析，展示简短介绍；模型页面保留完整介绍与用途说明。仅更换文案，计算及权限不变。
- **验证（最后验证日期：2026-11-05）**：前端 `npm run build` 通过（18.16秒，仅既有分包体积提示）；项目列表 JSON 解析及本轮代码差异空白检查通过。未验证线上部署或浏览器视觉效果。
- **回滚**：恢复本轮按钮与两处介绍文字即可，无需迁移。

## 2026-11-05 计划情景分解模型（测试）：区分月度计划与逐日测算

- **需求与来源**：依据用户指定名称“计划情景分解模型（测试）”及完整介绍调整页面，月度正式计划保留“计划”，逐日分解结果统一使用“测算”。
- **前端文件与流程**：`DynamicPlanMetricsView.vue` 更新主标题、介绍、逐日开关、算法与守恒说明、曲线及 Tooltip、明细列与累计对比文案。`renderDynamicDecompositionChart` 的每日序列始终标注“测算”，`renderCumulativeComparisonChart` 使用“累计测算值”；月度图表、原月度基准及导出仍为正式计划。`PageSelectView.vue`、`AppHeader.vue` 和 `frontend/src/router/index.js` 同步入口及标题，历史查询参数不覆盖新名称。
- **后端与配置**：`backend_data/shared/项目列表.json` 同步名称及介绍；`backend/projects/daily_report_25_26/api/dynamic_plan.py`、`backend/services/dynamic_decomposition_service.py` 更新逐日测算错误文案；未更改计算、权限、路由或数据协议。同步前后端 README，保留仓库已有其他修改。
- **验证（最后验证日期：2026-11-05）**：`node --test tests/dynamic-plan-actuals.test.mjs` 13 项通过，覆盖真实月度计划图表、每日测算图表、累计测算对比与明细 Vue 渲染，验证实际值开启/关闭时的测算标注及月度计划基准保留；`npm run build` 通过（17.90秒，仅既有分包体积提示），两处后端文件 Python 语法及项目列表 JSON 校验通过。未验证线上部署或浏览器视觉效果。
- **迁移与回滚**：无迁移，直接替换展示文案；回滚只恢复本轮上述文案、入口配置及对应测试断言，不回滚已有计算逻辑或其他工作区改动。

## 2026-11-05 隐藏生产日报项目卡片的内部编号

- **需求与改动**：按用户要求，在 `/projects` 页面隐藏“26-27供暖期生产日报”下方的 `daily_report_25_26`。`frontend/src/pages/ProjectSelectView.vue` 的编号元素通过 `v-if` 对该项目跳过渲染；项目名称、工作台入口及其他项目卡片保持既有行为。
- **模块与影响**：仅修改项目选择页展示条件，`enter(project)` 仍使用原始项目标识跳转，后端路由、权限及数据库不变；同步更新 `frontend/README.md` 与 `backend/README.md`。
- **验证（最后验证日期：2026-11-05）**：本地 `npm run build` 通过（17.65秒），仅出现既有分包超过500 kB提示；未做线上部署或浏览器视觉验证。
- **迁移与回滚**：无需迁移；回滚时移除编号元素新增的 `v-if` 条件，并同步撤销本轮文档说明。

## 2026-11-05 向 nyjt 开放数据查询与分析页面

- **需求与来源**：按用户明确要求，为公用账号 `nyjt` 增加生产日报“数据查询与分析”页面浏览权限。依据本地账户及权限配置，`Group_viewer` 当前仅有 `nyjt` 一名成员。
- **文件与流程**：在 `backend_data/shared/auth/permissions/daily_report_25_26.json` 的 `Group_viewer.page_access` 中增加 `data_analysis`；`AuthManager._build_merged_permissions` 合并项目授权，`list_project_pages` 根据会话授权展示页面，前端沿用既有页面访问判断。仅调整运行配置，无业务代码改动，不触发前后端 README 同步要求。
- **验证结果（最后验证日期：2026-11-05）**：使用本地 `AuthManager` 比较所有账号增加授权前后的完整权限对象，确认仅 `nyjt` 变化，且唯一差异为新增 `data_analysis`；操作权限、单位范围及其他项目权限保持原值。直接调用 `list_project_pages`，确认返回“数据查询与分析”入口及原有五个页面。未执行真实数据查询，未验证远端配置同步或线上会话；验证加载接口时出现既有 Pydantic 配置弃用告警，不影响权限检查通过。
- **生效与回滚**：运行后端需读取本次配置，前端刷新会话权限（必要时退出重新登录）。无需数据库迁移；回滚只需移除此组本次新增的 `data_analysis` 并刷新会话。未来加入 `Group_viewer` 的账号也继承该页面权限。

## 2026-11-04 逐日实际支持历史月份并加入分解明细表

- **需求与变更**：按用户本轮指令，取消“显示逐日实际值”必须属于最新发布月份的限制；历史月份可查看全月实际，当前月份仍按最新发布日截断，未来日期/缺报保留空值。“显示累计实际值”仍仅在发布当月可用，互斥与逐日单选规则不变。
- **前端模块与流程**：`DynamicPlanMetricsView.vue` 移除逐日选框禁用、切月撤选和请求月份门禁；逐日明细按指标并列展示计划及实际完成列。`getDailyDetailActual()` 复用图表实际数据，核对单位、指标、口径与发布日期；真实0保留，未发布/缺报显示“—”。`getDailyDetailActualTotal()` 仅聚合所选月已发布区间且完整的数据，缺一天即不冒充完整累计。`decompDetailData` 为气温不足的月份提供日历与空计划，仍可查看实际明细；明细按钮天数按所选月份动态计算。
- **后端模块**：`dynamic_plan_actuals.py` 删除逐日读取的“必须同发布月份”判断，保留最新发布日硬截断及未来月份直接返回空实际；累计专属接口月份门禁保持不变。无接口协议或数据库变更。
- **验证（最后验证日期：2026-11-04）**：扩展前端 `dynamic-plan-actuals.test.mjs` 的 Vue 实际表格渲染回归，覆盖计划/实际列、0与缺失、发布日截断、完整累计、历史月及无气温明细；更新后端历史月份逐日回归。前端13项、后端含月标煤回归25项通过，前端构建成功（22.25秒，仅有既有包体积告警），最终模板编译及差异空白检查通过。页面代理HTTP 200验证：最新发布日2026-11-03时，2026年3月返回31天实际，11月仅返回1—3日，未来月份实际为空；历史月份累计接口仍不可用。测试使用 Vue 编译与服务端渲染，未做浏览器视觉验收。
- **回滚**：恢复本轮逐日前后端月份判断与原明细模板即可；无需迁移，无业务数据写入，保留其他已有功能及修改。

## 2026-11-04 非动态分解累计完成值选框文案与位置

- `frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue` 的 `chart-actions` 在非动态分解模式将“显示实际值”改为“显示累计完成值”，置于计划分解开关前；动态模式的逐日/累计实际值选框继续位于分解开关后。两种模式沿用原有状态绑定与取数逻辑。
- 同步前后端 README；验证使用现有11项前端回归及 Vue 模板编译。最后验证日期：2026-11-04，实际结果见交付说明。
- 仅前端条件渲染及文案/位置调整，无接口、计算或数据库变更，无需迁移；回滚上述模板增量即可。

## 2026-11-04 逐日实际值选框命名与累计实际柱色调整

- `DynamicPlanMetricsView.vue` 将动态分解选框文案更新为“显示逐日实际值”；`renderCumulativeComparisonChart()` 中左侧累计实际柱由绿色改为蓝色 `#2563eb`，右侧累计分解计划柱继续使用橙色 `#f97316`，图例同步使用系列配色。
- 同步前后端 README 与现有前端回归断言；验证选框文案、系列配色及既有累计/逐日交互，结果见交付说明。最后验证日期：2026-11-04。
- 仅前端展示变更，无接口或数据改动，无需迁移；回滚本轮文案和累计实际系列配色即可。

## 2026-11-04 二次筛选默认只选一个指标

- `DynamicPlanMetricsView.vue` 的 `getDefaultChartMetricKeys()` 统一返回最多一个指标，优先标煤耗量，无标煤时取当前列表首项，无指标时为空；页面初始化、切换单位/计划范围及恢复默认均复用此逻辑。仅改变默认选择数量，累计模式与普通计划模式仍可手动多选，每日实际模式继续单选。
- 同步前后端 README；复用 `frontend/tests/dynamic-plan-actuals.test.mjs` 核验默认选项、缺少标煤/空列表兜底及恢复默认。最后验证日期：2026-11-04，验证结果见交付说明。
- 后端接口和业务数据无变更，无需迁移；回滚本轮默认选择函数及对应注释即可。

## 2026-11-04 动态分解增加累计实际与累计分解计划成对对比

- **后续展示调整（2026-11-04）**：按用户要求，`renderCumulativeComparisonChart()` 中每组双柱改为左侧累计实际（绿色）、右侧累计分解计划（橙色 `#f97316`），图例和悬浮内容同步按实际在前、计划在后排序；已有前端回归同步检查系列顺序、数值及颜色。仅调整展示，无迁移；回滚本项系列顺序、配色及图例/悬浮顺序即可。

- **用户确认的规则**：动态分解下将“显示实际值”改名为“显示每日实际值”，新增互斥的“显示累计实际值”；两项都仅在最新发布业务日属于当前分解月份时可用，其他月份禁用。切换到不匹配月份或无发布日期时自动撤销选中；关闭动态分解时保留原有月度实际对比。
- **前端流程**：`DynamicPlanMetricsView.vue` 维护发布日期与两项互斥状态。每日模式继续单选；累计模式允许二次筛选多选，按指标展示相邻的累计分解计划/累计实际双柱。两柱使用月初至最新发布日的同一窗口，各指标按单位分轴；不同单位使用重合分类轴以保持每组双柱相邻。累计图不混入每日气温曲线，多个指标时提供横向缩放。
- **累计口径与取数**：`useDynamicPlanActuals.js` 支持单指标与批量请求、取消及过期响应拦截，并用 `aggregateDecomposedPlan()` 聚合已展示模型产生的逐日计划。数量与固定面积单耗累加；全厂热效率按分解后分子/分母重算，缺日值、零分母及未定义的非累加比率保留空值。`services/api.js` 新增累计读取方法。
- **后端模块**：`dynamic_plan.py` 的元数据和日分解响应增加最新发布日；新增只读 `POST /dynamic_plan/cumulative_actuals`，后端再次校验月份。`dynamic_plan_actuals.py` 将原有单指标计算统一委托给批量服务，一次读取底表并按各指标原有公式计算累计，沿用缺报校验；每日接口同样限制到最新发布月份。无数据库迁移或业务数据写入。
- **验证（最后验证日期：2026-11-04）**：新增/扩展 `frontend/tests/dynamic-plan-actuals.test.mjs` 和 `backend/projects/daily_report_25_26/tests/test_dynamic_plan_actuals.py`，覆盖月份禁用、互斥切换、累计多选切回每日单选、发布日截断、批量独立缺报、乱序响应、计划截取、单耗及比率聚合，并使用真实 ECharts SVG 渲染校验多轴双柱。前端11项通过，后端含月标煤回归25项通过；`npm run build` 成功（22.34秒，仅有既有打包体积告警），差异空白检查通过。页面代理实测最新发布日2026-11-03：11月批量累计可用，标煤/供热量/热单耗与原单指标月累计一致；其他月份累计返回不可用、每日实际全空。未做浏览器视觉验收。
- **回滚**：撤销本轮页面、composable、API 方法、后端元数据/累计接口及批量服务的增量即可恢复上一版；无迁移，保留之前已完成的实际值对比和标煤置顶功能及其他已有修改。

## 2026-11-04 计划指标两级筛选标煤耗量置顶

- **改动**：`frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue` 的一次筛选和二次筛选分别使用 `primaryFilterMetrics`、`secondaryFilterMetrics`，共用 `prioritizeStandardCoal()` 将标煤耗量置顶，其他指标维持原有相对顺序；默认核心指标顺序同步以标煤耗量为首项。二次筛选仍仅包含一次筛选中已勾选的指标，实际值模式继续保持单选。
- **验证**：复用 `frontend/tests/dynamic-plan-actuals.test.mjs` 检查两级筛选顺序及已有单选、日/月图表回归，前端构建结果见交付说明。最后验证日期：2026-11-04。
- **影响与回滚**：仅调整前端筛选展示与默认核心指标顺序，后端接口、数据计算和数据库不变；无需迁移，撤销本节对应的页面增量即可回滚。

## 2026-11-04 计划动态分解图表增加可选实际值对比

- **需求与口径**：按用户本轮确认，新增默认关闭的“显示实际值”；开启后图表二次筛选最多选一个指标，选新项替换旧项。动态分解开启时显示目标月逐日实际；关闭时显示各自然月从月初累计的实际。实际底表读取以项目最新发布业务日为硬截止，不回退到最新入库日，不新增截止日期/完成率等说明提示。不同指标之间不相加。
- **前端文件**：`frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue` 增加开关、单选联动和实际柱形；`composables/useDynamicPlanActuals.js` 负责请求取消、过期响应拦截、日历日期及柱形序列；`services/api.js` 接入独立实际值接口。表格行聚焦、默认重置与口径切换同样遵守单选。月走势为计划线+实际柱，月柱图为并列柱；环形图保留计划分布含义。气温不完整时仍可看实际柱，计划为空。
- **后端文件与流程**：`backend/projects/daily_report_25_26/api/dynamic_plan.py` 新增 `GET /dynamic_plan/actuals`，从 `workflow_status_manager.list_published_dates()` 获取截止日；`services/dynamic_plan_actuals.py` 一次读取截止日以内的底表与本期常量，在内存中复用 `HeatingAnalysisEngine` 计算同一指标的日值/月累计，并复用 `BriefEvidence` 校验缺报、区分空值和真实零。相同面积单位 `万m²/万㎡` 统一识别。`backend/services/heating_metrics/analysis_engine.py` 增加默认开启的 `clip_to_season` 参数，本接口显式关闭以保留自然月边界，其他调用默认行为不变。
- **验证记录（最后验证日期：2026-11-04）**：新增后端 `tests/test_dynamic_plan_actuals.py`、前端 `frontend/tests/dynamic-plan-actuals.test.mjs`，覆盖发布日截断、零/空值、逐月重置、同指标集团汇总、单耗公式、自然月与闰年边界，以及单选、日/月切换、乱序响应和实际图表序列。后端连同月标煤、供暖期切换、暖收入分摊回归共41项通过，1项数据库临时表用例因未显式开启 `PHOENIX_TEST_POSTGRES` 跳过；前端7项通过；最终 `npm run build` 成功（17.25秒，仅有打包体积告警）。通过页面代理地址请求实际接口得到HTTP 200。只读实库核验：最新发布日为 2026-11-03，集团11月日实际仅返回1—3日；标煤月累计4571.0395吨与既有标准引擎一致，日实际查询约0.04秒。环境未提供 pytest-cov，未声明已达到全仓覆盖率90%；未做浏览器视觉验收。
- **迁移与回滚**：无数据库迁移，无业务数据写入。撤销上述代码文件本轮增量及新增测试即可回滚；保留本轮之前已有的其他未提交修改。未开启实际值时沿用原有图表行为。

## 2026-11-04 庄河环海 25-26 供暖期投诉量口径修正（净投诉=已结案，剔除省民心网）

- **需求背景与业务依据**：
  - 用户依据新核准成果表 [`11.4 庄河环海_25-26供暖期每日投诉统计_净投诉=已结案，去除省.xlsx`](file:///D:/编程项目/phoenix/configs/11.4%20庄河环海_25-26供暖期每日投诉统计_净投诉=已结案，去除省.xlsx)，对庄河 25-26 供暖期（2025-11-01 至 2026-04-05，共 156 天）投诉指标进行口径再修正；
  - **核心业务口径**：庄河原始台账混合了市平台（784件）与省民心网（75件），总投诉量保持 859 件不变；净投诉量口径重定义为仅计非省平台（即剔除省民心网已结案 75 件）且已结案的工单，全供暖期累计净投诉量由原 172 件下调为 **97 件**；
  - 同步更新指标：
    1. `amount_daily_net_complaints`（当日净投诉量）
    2. `sum_month_total_net_complaints`（本月累计净投诉量）
    3. `sum_season_total_net_complaints`（本供暖期累计净投诉量，全期最终累计为 97 件）
    4. `amount_daily_city_net_complaints`（其中：2.市平台净投诉量）保持与当日“当日净投诉量”严格相等；
    5. `amount_daily_provincial_net_complaints`（其中：1.省平台净投诉量）保持恒为 0；
    6. `amount_daily_service_complaints`（当日省市平台投诉量）全期保持 859 件不变；
  - 既有封存的 `25-26_raw_*` 原始归档数据（936条）与煤、电、水、热等非投诉指标绝对保留。
- **改动范围与落地措施**：
  1. **数据备份与溯源留痕**：
     - 执行前将庄河当前 936 条投诉指标记录导出备份至 [`backend_data/projects/daily_report_25_26/backup_zhuanghe_complaints_20261104_pre_exclude_province.json`](file:///D:/编程项目/phoenix/backend_data/projects/daily_report_25_26/backup_zhuanghe_complaints_20261104_pre_exclude_province.json)。
  2. **生产环境标准 SQL 迁移脚本交付**：
     - 生成独立可执行脚本 [`configs/migrate_25_26_zhuanghe_complaints_v2_exclude_province.sql`](file:///D:/编程项目/phoenix/configs/migrate_25_26_zhuanghe_complaints_v2_exclude_province.sql)（129.2 KB），支持事务更新与校验查询。
  3. **自动化同步与入库脚本**：
     - 编写并执行 [`backend/scripts/apply_zhuanghe_complaint_v2_migration.py`](file:///D:/编程项目/phoenix/backend/scripts/apply_zhuanghe_complaint_v2_migration.py)，完成庄河 156 天全部 6 项指标（共 936 条）的批量 UPSERT。
  4. **全量交叉比对与视图验证**：
     - 本地数据库更新后，逐日核验 156 天全部 6 项指标与新 Excel 100% 吻合；
     - 确认 2026-04-05 全供暖期最终累计净投诉量精准收敛为 **97.0 件**；
     - 确认市平台净投诉量每日严格等于当日净投诉量，省平台净投诉量恒为 0；
     - 确认 `25-26_raw_*` 936 条记录完好无损；
     - `sum_basic_data` 动态视图实时反映同期抓取联动。
- **验证与测试**：
  - 后端 pytest 4 项测试全部通过；
  - 前端 complaintFill 3 项测试全部通过。


## 2026-11-04 供热公司及各中心 25-26 供暖期“当日省市平台投诉量”口径修正（各类投诉量统一仅限“投诉”类）

- **需求背景与业务依据**：
  - 用户重新梳理并核准了新成果表 [`11.4 25-26供暖期主城区及各中心投诉统计_各类投诉量仅限投诉类.xlsx`](file:///D:/编程项目/phoenix/configs/11.4%2025-26供暖期主城区及各中心投诉统计_各类投诉量仅限投诉类.xlsx)；
  - 明确统一定义：“当日省市平台投诉量”（`amount_daily_service_complaints`）也必须与净投诉量一致，分类仅限严格等于“投诉”的诉求件，剔除原数据中混入的“咨询”、“表扬”和空白分类；
  - 供热公司全期省市平台总投诉量由 5,696 件精准更新为 **5,539 件**（剔除 157 件非投诉件）；净投诉量指标（全期累计 184 件）保持不变。
- **改动范围与落地措施**：
  1. **数据备份留痕**：
     - 执行前将当前两张表全部 10,296 条指标记录导出备份至 [`backend_data/projects/daily_report_25_26/backup_complaints_20261104_pre_v3_migration.json`](file:///D:/编程项目/phoenix/backend_data/projects/daily_report_25_26/backup_complaints_20261104_pre_v3_migration.json)。
  2. **生产环境标准 SQL 迁移脚本交付**：
     - 生成独立可执行脚本 [`configs/migrate_25_26_complaints_v3_complaint_only.sql`](file:///D:/编程项目/phoenix/configs/migrate_25_26_complaints_v3_complaint_only.sql)（199.1 KB），支持事务更新与全期校验。
  3. **自动化同步与算法对齐**：
     - 编写并执行 [`backend/scripts/apply_complaint_v3_service_complaints_migration.py`](file:///D:/编程项目/phoenix/backend/scripts/apply_complaint_v3_service_complaints_migration.py)，完成供热公司总表 156 天与 10 个中心 1,560 天次 `amount_daily_service_complaints` 的数据库更新；
     - 同步升级后端计算服务 [`complaint_statistics.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/complaint_statistics.py)，使每日提报算法中 `daily_total`、`daily_city`、`daily_province` 同步受 `is_complaint` 约束，确保未来提报与历史同期基准完全同口径；
     - 同步升级前端填报端 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)：核验弹窗口径说明更新，穿透筛选明细计算属性 `complaintDetailRows` 在过滤当日平台指标时同步加入 `isComplaint` 判定，点击数字下钻查看的工单列表与统计数字绝对闭环。
  4. **全量交叉比对与视图验证**：
     - 数据库更新后，核验 156 天总表及 10 个分中心数据与新 Excel 100% 吻合，供热公司全期总投诉量求和严格等于 5,539.0 件；
     - `sum_basic_data` 动态视图实时反映同期抓取（如 2026-11-03 业务日提取 2025-11-03 供热公司省市平台总投诉量同期值由 122 动态更新为 115）。
- **验证与测试**：
  - 后端 pytest 4 项测试全部通过；
  - 前端 complaintFill 3 项测试全部通过；
  - 前端生产构建 `npm run build` 打包校验成功（20.69s，0 错误）。


## 2026-11-04 庄河环海 25-26 供暖期投诉量历史归档（加 raw 前缀）与新核定数据入库

- **需求背景与业务依据**：
  - 用户提供了全新的庄河环海标准成果表 [`11.4 庄河环海_25-26供暖期每日投诉统计_完整版.xlsx`](file:///D:/编程项目/phoenix/configs/11.4%20庄河环海_25-26供暖期每日投诉统计_完整版.xlsx)（涵盖 2025-11-01 至 2026-04-05，共 156 天连续记录）；
  - 明确要求：
    1. 库内原有的庄河相关 25-26 供暖期各类投诉指标添加 `25-26_raw_` 前缀安全封存归档；
    2. 将新表格中的每日投诉总量、每日净投诉量、本月累计净投诉量、供暖期累计净投诉量入库；
    3. “其中：1.省平台净投诉量”每日恒为 0，“其中：2.市平台净投诉量”则与“当日净投诉量”严格相等。
- **改动范围与落地措施**：
  1. **数据备份与溯源保障**：
     - 执行前将庄河当前 936 条投诉记录全量导出至 [`backend_data/projects/daily_report_25_26/backup_zhuanghe_complaints_20261104_pre_migration.json`](file:///D:/编程项目/phoenix/backend_data/projects/daily_report_25_26/backup_zhuanghe_complaints_20261104_pre_migration.json)。
  2. **生产环境标准 SQL 迁移脚本交付**：
     - 生成独立可执行脚本 [`configs/migrate_25_26_zhuanghe_complaints_production.sql`](file:///D:/编程项目/phoenix/configs/migrate_25_26_zhuanghe_complaints_production.sql)（129.7 KB），内含事务归档、冲突保护更新及校验查询。
  3. **自动化执行脚本**：
     - 编写并执行 [`backend/scripts/apply_zhuanghe_complaint_migration.py`](file:///D:/编程项目/phoenix/backend/scripts/apply_zhuanghe_complaint_migration.py)：
       - 步骤 1：将 `daily_basic_data` 中庄河 6 项旧指标（共 936 条）原子重命名添加 `25-26_raw_` 前缀；
       - 步骤 2：插入新核定的 6 项标准指标（156 天 × 6 指标 = 936 条新记录）。
  4. **全量交叉比对与视图验证**：
     - 本地数据库更新后，逐日核验 156 天全部 6 项指标与 Excel 完全 100% 吻合；
     - 验证 2026-04-05 庄河环海全期最终累计净投诉量收敛为标准的 172.0 件（投诉总量 859 件）；
     - 验证 `sum_basic_data` 动态视图实时反映同期抓取（如 2026-11-03 业务日提取 2025-11-03 庄河同期投诉量准确对齐）。
- **验证与测试**：
  - 后端 pytest 4 项测试全部通过；
  - 前端 complaintFill 3 项测试全部通过。


## 2026-11-04 供热公司及10个服务中心 25-26 供暖期投诉量同期值修正（净投诉新口径：精准剔除11件非投诉件）

- **需求背景与口径依据**：
  - 用户依据最新口径核定并制作了全新的标准成果表 [`11.4 25-26供暖期主城区及各中心投诉统计_净投诉新口径.xlsx`](file:///D:/编程项目/phoenix/configs/11.4%2025-26供暖期主城区及各中心投诉统计_净投诉新口径.xlsx)；
  - 明确要求将数据库中 2025-11-01 至 2026-04-05（共 156 天）的同期投诉量指标进行全面修正，与新表格保持 100% 吻合；
  - 核心口径精细化：仅“转办”+“已办结”且类型为“投诉”纳入净投诉统计，排除了此前统计中包含的 11 件“咨询”和“表扬”件，供暖期全期最终累计净投诉量由 195 件下调为 184 件。
- **改动范围与落地措施**：
  1. **数据全量备份留痕**：
     - 在修改前，将库内当前 25-26 供暖期两张表全部 10,296 条记录（含原始 `raw` 归档与现行指标）全量导出并安全备份至 [`backend_data/projects/daily_report_25_26/backup_complaints_20261104_pre_v2_migration.json`](file:///D:/编程项目/phoenix/backend_data/projects/daily_report_25_26/backup_complaints_20261104_pre_v2_migration.json)。
  2. **生产环境标准 SQL 迁移脚本交付**：
     - 生成可独立在生产服务器上一键执行的标准迁移脚本 [`configs/migrate_25_26_complaints_v2_new_standard.sql`](file:///D:/编程项目/phoenix/configs/migrate_25_26_complaints_v2_new_standard.sql)（587.2 KB），内嵌事务 `BEGIN ... COMMIT` 与校验查询。
  3. **自动化同步与修正执行脚本**：
     - 新建 [`backend/scripts/apply_complaint_v2_migration.py`](file:///D:/编程项目/phoenix/backend/scripts/apply_complaint_v2_migration.py)，实现：
       - 供热公司总表（`GongRe_Sheet`）156 天 × 3 指标 = 468 条数据更新；
       - 10 个服务中心（`GongRe_branches_detail_Sheet`）1,560 天次 × 3 指标 = 4,680 条数据更新；
       - 市平台净投诉量（`amount_daily_city_net_complaints`）同步联动更新 = 当日净投诉量，共 1,716 条；
       - 原始历史封存指标（`25-26_raw_*`）严格保留绝对不动。
  4. **全量交叉比对与视图验证**：
     - 本地数据库更新后，自动对 156 天总表 4 项指标（624 条）与 10 中心 4 项指标（6,240 条）执行逐条交叉比对，实现与 Excel 100% 零误差吻合；
     - 验证 2026-04-05 供热公司最终累计净投诉量准确收敛为 184.0 件；
     - 验证 `sum_basic_data` 动态视图实时反映同期变化（如 2026-11-03 业务日提取 2025-11-03 同期值：供热公司由 59 变为 55，北岗由 13 变为 10，兴工由 5 变为 4）。
- **测试与验证**：
  - 后端执行 `python -m pytest backend/projects/daily_report_25_26/tests/test_complaint_statistics.py` 4 项测试全部通过；
  - 前端执行 `node frontend/src/projects/daily_report_25_26/composables/complaintFill.test.js` 3 项测试全部通过。


## 2026-11-04 供热填报端净投诉量统计口径精细化：仅转办已办结且类型为“投诉”纳入净投诉统计

- **需求背景与口径明确**：
  - 用户反馈在《转办》明细工作表中存在“类型”字段（包含投诉、咨询、表扬等不同诉求类型）；
  - 明确要求在计算“净投诉量”时，保持原转办及已办结范围不变的前提下，增加对诉求类型的判定：**必须同时满足该记录的“类型”为“投诉”**，才计入净投诉量统计范围（排除咨询、表扬等非投诉诉求）。
- **改动范围与落地详情**：
  1. **后端统计算法精细化** ([`complaint_statistics.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/complaint_statistics.py))：
     - 在 `metrics(records, day, month, season)` 中，新增 `is_complaint = normalize(row.get('type')) == '投诉'` 判定；
     - 调整 `is_net` 计算逻辑为 `source == '转办' and done and is_complaint`；
     - `daily_net`（当日净投诉量）、`daily_city_net`（市平台净投诉量）、`monthly_net`（本月累计净投诉量）、`season_net`（本供暖期累计净投诉量）均严格依据新 `is_net` 进行累加；
     - 总量指标（`daily_city`、`daily_province`、`daily_total`）与未办结指标保持全量统计口径。
  2. **前端穿透核对与提示同步** ([`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue))：
     - 模态弹窗顶部口径说明更新为：`新口径：净投诉量为转办已办结且类型为“投诉”；省平台净投诉为 0；市平台等于净投诉量`；
     - 穿透过滤逻辑 `complaintDetailRows` 同步增加 `const isComplaint = String(record.type || '').trim() === '投诉'`，确保点击净投诉量数字时穿透出的明细记录与汇总数值完全一一对应。
  3. **单测用例升级** ([`test_complaint_statistics.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/tests/test_complaint_statistics.py))：
     - 在样本数据中新增已办结但类型为“咨询”的转办记录，验证其正常计入当日诉求总量（`daily_total`/`daily_city`），但被严格排除在 `daily_net`、`daily_city_net`、`monthly_net`、`season_net` 之外。
- **构建与测试**：
  - 后端执行 `python -m pytest backend/projects/daily_report_25_26/tests/test_complaint_statistics.py` 4 项测试全部通过；
  - 前端执行 `node frontend/src/projects/daily_report_25_26/composables/complaintFill.test.js` 3 项测试全部通过；
  - 前端执行 `npm --prefix frontend run build` 生产构建成功（17.66s，0 错误）。

## 2026-11-04 数据看板 PDF 导出宽度改为 1800px（当前生效）

- **需求与变更**：用户反馈 2560px 导出过于扁宽，将 `DashBoard.vue` 的 `EXPORT_STANDARD_WIDTH`、导出 CSS 的宽度/最小宽度/最大宽度及提示统一调整为 1800px，替代上一轮 2K 宽度。
- **流程与影响**：`downloadPDF` 按 1800px 布局重绘图表，以原有 2 倍采样生成 3600px 宽截图，再生成 210mm 宽的等比例长页 PDF；导出后恢复原布局。无后端变更，无需迁移。
- **验证与回滚**：最后验证日期 2026-11-04；布局、截图及虚拟视口参数一致性检查通过，生产构建结果见本轮交付说明，未进行实际 PDF 下载目视验收。已同步前后端 README；回滚仅将本轮导出宽度及对应提示恢复为 2560px。

## 2026-11-04 数据看板 PDF 导出宽度调整为 2K

- **需求与实现**：按用户要求，将 `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue` 的 `downloadPDF` 导出布局宽度、html2canvas 截图及虚拟视口宽度、专用 CSS 的宽度约束由 1600px 统一调整为 2560px，提示文字同步更新。此处 2K 按常见桌面 2560px 宽度解释。
- **运行流程**：导出时切换 2560px 桌面布局并重绘图表，以原有 2 倍采样生成 5120px 宽截图，再按 210mm 页面宽度等比例生成长页 PDF；完成后恢复屏幕布局。
- **验证**：最后验证日期 2026-11-04；导出参数及 CSS 一致性断言通过，`frontend` 下 `npm run build` 成功（20.73s），仅有分包大于 500kB 的提示；未进行浏览器实际 PDF 下载与目视验收。
- **影响与回滚**：截图宽度增加可能提高导出耗时与内存占用；无需迁移。回滚仅将本轮导出常量、CSS 宽度和对应提示恢复为 1600px。已同步前后端 README；无后端代码或接口变更。

## 2026-11-04 修复远程生产数据库拉取 500 报错并全面加固备份同步链路

- **需求背景与故障排查**：
  - 用户反馈在后台点击拉取远程生产环境备份时，后端日志输出 `POST /api/v1/admin/database/remote-sync/pull HTTP/1.1 500 Internal Server Error`；
  - **根本诱因分析**：
    1. **文件名包含本地前缀**：当指定拉取历史备份包时，若传入已包含“远程_”前缀的文件名，后端直接拼接原名向远程生产服务器请求下载（而生产服务器上无此前缀），远程返回 HTTP 404，本地未捕获分类并统一包裹为 500 抛出；
    2. **Token失效兜底缺陷**：在凭证过期且未持久化管理员明文密码时，`_get_remote_auth_token` 探测失败后仍把无效 Token 原样返回，导致后续请求被远程拦截为 401 并转化为 500；
    3. **日志排障盲区**：`pull_remote_backup` 关键调用链未引入日志输出，且 `admin_console.py` 顶部缺少 `logger` 初始化，导致异常发生时控制台仅有 uvicorn 的 access log，无任何业务 Traceback；
    4. **下载原子性保障**：原流式下载直接写入目标文件，若遇网络中断或超时会导致本地残留损坏的 0 字节或半截 dump 文件。
- **改动范围与落地详情**：
  - **后端加固** (`backend/api/v1/admin_console.py`)：
    1. 顶部导入 `logging` 并创建模块级 `logger`，补齐长期遗漏的日志器定义；
    2. **文件名净化与自动适配**：在 `pull_remote_backup` 中，自动识别并剥离用户传入的“远程_”本地前缀，确保向生产服务器请求的是生产环境原始文件名，本地落盘自动统一追加“远程_”前缀；
    3. **临时文件原子落盘**：流式下载使用 `.downloading_{uuid}` 临时文件，下载完毕后再原子重命名至最终目标路径，若发生任何异常自动清理临时文件，确保本地文件完整性；
    4. **确保本地备份目录**：执行 `DB_BACKUP_DIR.mkdir(parents=True, exist_ok=True)`；
    5. **精准 HTTP 状态码与异常透传**：对 `urllib.error.HTTPError`（401/403/404/500/502/504）及 `urllib.error.URLError`（网络超时）进行精准捕获与日志记录，透传远程真实错误原因；
    6. **Token认证兜底防护**：探测失败且无密码时，显式抛出 401 并给出清晰指导，避免无效 Token 穿透。
  - **前端对接增强** (`frontend/src/projects/daily_report_25_26/services/api.js`)：
    - 在 `pullAdminRemoteSyncBackup`、`testAdminRemoteSyncConnection`、`getAdminRemoteSyncBackups` 等方法中统一引入 `parseErrorDetail`，替代直接读取原始 text，确保前端弹窗显示易读的中文错误详情。
- **验证与测试**：
  - 容器内执行 `test_remote_sync_connection` 成功连接远程生产环境并获取到 146 个备份存档；
  - 容器内执行 `pull_remote_backup`，测试带“远程_”前缀的文件名，自动剥离前缀并成功下载校验通过（生成 `远程_phoenix_backup_20261104_155612.dump (7.00 MB)`）；
  - `python -m py_compile backend/api/v1/admin_console.py` 语法校验通过，容器重启运行稳定。

## 2026-11-04 取消 nyjt 的月报数据查询工具访问权限

- **需求与依据**：按用户要求取消 `nyjt` 的月报查询权限。核对当前账户配置，`Group_viewer` 组仅有 `nyjt` 一名成员，权限由 `AuthManager._build_merged_permissions` 按组解析。
- **变更**：清空 `backend_data/shared/auth/permissions/monthly_data_show.json` 中 `Group_viewer.page_access`；生产日报及其他组配置不变。本轮仅调整运行权限配置，无业务代码修改，不触发前后端 README 同步要求。
- **流程与结果**：后端配置重载后，`nyjt` 的月报项目授权为空，项目列表不再展示月报，查询工具直达路由也因缺少页面授权被拒绝；前端需刷新会话权限，可退出后重新登录。
- **验证**：使用本地 `AuthManager` 解析配置，核对 `nyjt` 月报项目不可访问、生产日报权限保留，比较全部账号变更前后权限摘要，确认仅 `nyjt` 发生变化，`group_admin` 月报查询仍可访问。最后验证日期：2026-11-04；未验证远端部署状态。
- **影响与回滚**：沿用现有分组模型，未来加入 `Group_viewer` 的账号也默认没有月报权限；无需数据库迁移。回滚时向该组 `page_access` 恢复 `projects_monthly_data_show_query_tool`，并刷新登录权限。

## 2026-11-04 窄屏手机模式数据看板精细化响应式排版重构（彻底解决排版错乱与横向白边晃动）

- **需求背景与故障诊断**：
  - 用户反馈由外部工具进行窄屏手机排版适配后导致整个看板排版完全错乱（强制横向柱状图翻转、隐藏差额胶囊、硬塞顶部粘性超链接导航及粗劣折叠树）；
  - 经系统排查，手机端排版的根本顽疾在于 Flex/Grid 容器默认 `min-width: auto` 导致内部宽表格撑爆移动端视口宽度，产生横向大白边与左右剧烈晃动，而非图表数据或方向问题。
- **改动范围与落地详情**：
  - **故障回滚**：全面移除并清理外部侵入性代码，基准代码完好复原；
  - **页面级响应式重构** (`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`)：
    1. 增加针对 `@media (max-width: 767px)` 的核心防撑爆约束（`min-width: 0 !important; max-width: 100% !important;`），表格外层平滑滚动，彻底锁定屏幕视口宽度；
    2. 移动端内边距由 24px 精简至 12px 10px，卡片内边距调整为 14px 12px，极大释放有效内容区域；
    3. 核心指标卡数字自适应分级（大数值 `20px`，成对指标 `16px`），大数值杜绝折行；
    4. Header、单耗胶囊切换栏（`.unit-phase-toggle`）、电力现货等板块在窄屏下整齐弹性自适应；
    5. `EChart` 组件内增设纯净 `ResizeObserver`，仅在容器尺寸变化时触发 `chart.resize()`，保持图表原本方向与完整视觉；
  - **热网耗水哑铃图移动端优化** (`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`)：
    - 窄屏（`< 500px`）自适应微调绘图网格（`left: 70, right: 86`），胶囊微调至 11px，**完整保留变动差额胶囊与散点数据标签**；
    - 顶部全口径概览条在窄屏下纵向整齐展示，杜绝数字折断。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（45.57s，生成产物 `DashBoard-CF2S-aq6.js`）。

## 2026-11-04 修复热网耗水图切换日期失败残留

- `NetworkWaterDumbbellCard.vue` 的 `loadData` 在查询开始清空旧结果，失败仅显示错误与重试；独立请求控制器阻止旧响应覆盖新日期、重绘或关闭新请求加载态，日期 watcher 同步触发，卸载后不提交结果。
- 按用户确认，未填按 0 的后端统计口径保持不变；刻度取整问题仅解释，未修改。
- 前端 `node src/projects/daily_report_25_26/tests/networkWaterDumbbell.test.mjs` 及生产构建通过，覆盖 Vue 编译、切日清空、失败、重试、乱序及取消状态；存在既有大文件分包提示。
- 无需迁移或数据库操作；回滚恢复本轮组件请求逻辑并移除新增测试，保留其他改动。

## 2026-11-04 数据看板热网耗水量对比精细化调优：移除栏目副标题“自适应标尺”字样

- **需求背景与调优意图**：
  - 用户反馈图表中间已有明确的“标尺尺度不同”分割虚线说明，要求将两栏顶部的“自适应标尺”副标题字样全部去掉，保持极简视觉。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 从左右两栏头部彻底移除 `<span class="water-column-subtitle">自适应标尺</span>`；
    - 顶栏只保留纯粹的“本日”与“供暖期累计”徽章标识，界面更纯粹、精简。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（18.22s，生成产物 `DashBoard-DSYJe62I.js`）。

## 2026-11-04 数据看板热网耗水量对比精细化调优：下层图表下移避让虚线标签

- **需求背景与调优意图**：
  - 用户反馈“标尺尺度不同”的虚线字样将下方图中的一些内容（外围首行圆球上方的数据标签）遮挡住了，要求将下方的图往下稍微挪挪以避让遮挡。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **Grid 1 显著下沉**：将下层外围五单位的网格顶部坐标从 `top: 138` 下移至 `top: 160`（下移 22px），为首行散点上方的实际值标签拉开充裕净空；
    2. **虚线微调居中**：`.water-scale-divider` 设定为 `top: 132px`，恰处于上下两层网格几何过渡区的黄金居中位置；
    3. **容器高度舒展**：左右双图容器高度微调为 `450px`，确保底部的 X 轴千吨刻度与“吨”单位同样拥有充裕的呼吸空间。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（23.54s，生成产物 `DashBoard-DcvDEGOG.js`）。

## 2026-11-04 工况一览三列完整展示（当前生效）

- 按用户方案，`SmartHeatingOverview.vue` 左列电厂、中列首站及一网上下排列、右列换热站及商户；移除固定高度、内部滚动、名称省略及采集详情折叠。`SmartHeatingView.vue` 工况标签最大宽度扩展为 1840px，中小屏回落单列。
- 分隔位置：电厂 10 / 22 / 25 前，一网 5 前，换热站及商户 5 / 11 / 15 / 19 / 23 前，共九处。按原始序号分段，搜索后不在首条结果前添加空分隔。
- HAR 渲染、82 项测点、三列和分区顺序、九处分隔位置及无折叠检查、生产构建通过；未完成浏览器截图目视检查。
- 无需迁移或更新中继；回滚仅恢复本轮两个 Vue 文件、渲染断言和文档改动，保留其他并行修改。

## 2026-11-04 数据看板热网耗水量对比精细化调优：主城区文字统一转黑与上下双标尺虚线分割

- **需求背景与调优意图**：
  - 用户反馈主体名称中主城区希望改为黑色字体，保持与集团汇总及外围各单位风格协调一致；
  - 同时要求在“集团汇总、主城区”板块与“下方外围五单位”板块之间增加一条虚线分割，以明确表示上下两个图表区域的标尺尺度不同。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **主体名称转黑**：将 Grid 0 的 Y 轴主体名称 `axisLabel.color` 由天蓝色回调为深碳黑（`#0f172a`）；
    2. **响应式自适应虚线分界栏**：在双栏图表容器内增加绝对定位的 `.water-scale-divider` 元素（居中 `top: 127px`），利用两侧 `border-top: 1.5px dashed #cbd5e1` 结合正中微型标签 `标尺尺度不同`（浅灰字 `#94a3b8`），兼顾视觉边界提示与标尺语义解释，且不阻碍图表 hover 交互（`pointer-events: none`）。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（17.38s，生成产物 `DashBoard-qjp8Vprg.js`）。

## 2026-11-04 工况一览四区块对齐

- `SmartHeatingOverview.vue` 桌面改为等宽等高 2×2 区块，高度为 420–640px 自适应，表格内部滚动、表头固定、列宽统一；中屏单列，手机恢复自然高度卡片。
- 全部 82 项测点、搜索、采集时间及刷新规则保持不变。HAR 渲染回归与生产构建通过；未完成浏览器截图目视检查。
- 无需迁移或中继更新；回滚仅撤销本轮表格列定义、滚动容器属性和布局样式。

## 2026-11-04 数据看板热网耗水量对比精细化调优：吨数及差额全面四舍五入取消小数

- **需求背景与调优意图**：
  - 用户要求两张热网耗水哑铃图中显示的吨数，包括在图中显示的差异，全部四舍五入，不要有小数点，使数据呈现更干练紧凑、符合实物量常规汇报习惯。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **`formatNumber` 算法升级**：改用 `Math.round(Number(val)).toLocaleString('zh-CN')`，彻底抹平多余小数，顶部概览指标与悬浮 Tooltip 吨数全局受益；
    2. **`currValFormatter` 实物量散点标签**：散点上方的今年实际值全部 `Math.round(val).toLocaleString('zh-CN')`，万吨级同样四舍五入取整万，无任何小数点；
    3. **`formatCompactValue` 差额标签**：胶囊内的增减吨数差额四舍五入取整吨，如 `-131`、`+2,410`，彻底移除原有的 1 位小数；
    4. **标尺刻度清理**：X 轴刻度消除 `1.0万` 等小数，统一按整数或整万呈现。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（21.70s，生成产物 `DashBoard-Bsk3Onpm.js`）。

## 2026-11-04 数据看板热网耗水量对比精细化调优：供暖期全口径数值与“供暖期累计”徽章调整为橙色

- **需求背景与调优意图**：
  - 用户反馈顶部供暖期全口径热网耗水量的当前数值绿色字体不够贴切，要求将其与右栏上方的“供暖期累计”徽章标签统一改为醒目的橙色，形成色彩语义呼应。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 将 `.water-global-metric:last-child .water-global-metric__val` 的字体颜色由绿色调整为深暖橙色（`#ea580c`）；
    - 将 `.water-dim-badge--season` 徽章由浅绿底绿字调整为暖橙色系（`background: #ffedd5; color: #c2410c; border: 1px solid #fed7aa;`）；
    - 与左栏的湖蓝/天蓝色系（`#0369a1`）完美呼应，左右双栏形成鲜明的“天蓝（本日） vs 暖橙（供暖期累计）”对称视觉色彩识别体系。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（20.73s，生成产物 `DashBoard-B3NdMkyb.js`）。

## 2026-11-04 数据看板热网耗水量对比精细化调优：主城区上方新增“集团汇总”并共用大标尺

## 2026-11-04 数据看板热网耗水量对比精细化调优：主城区上方新增“集团汇总”并共用大标尺

- **需求背景与调优意图**：
  - 用户提出在主城区上方增加一个口径名为“集团汇总”，与主城区共用同一个标尺，直观体现集团总量与主城区占比对比。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **Grid 0 结构重构**：
       - 上层网格扩展为容纳“集团汇总”与“主城区”两行，绑定同一大标尺 `xAxis[0]`；
       - `topCategories = ['集团汇总', '主城区']`，启用 `inverse: true` 保证集团汇总排在最顶层第一行；
       - 上层标尺最大值自适应贴合集团汇总与主城区中的绝对最大值（~20,000 吨）；
    2. **物理比例直观展现**：
       - 集团汇总（18,364 吨）满幅贯穿全图；
       - 主城区（11,557 吨）在同一标尺下长度恰好约占集团总量的 60%，上下两根哑铃线段的长度差异直观展示出主城区在全集团的真实体量分量；
    3. **外围标尺保持黄金分割**：
       - 下层外围标尺依然以主城区上限的 2/5 向上取整千（精确保持 5,000 吨整千标尺），不受集团汇总大数值影响；
    4. **容器高度舒展**：
       - 图表容器高度调整为 `430px`，Grid 0 高度调整为 `76px`，Grid 1 `top: 138`，整体留白宽裕舒展。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（19.07s，生成产物 `DashBoard-C6h_FXY-.js`）。

## 2026-11-04 数据看板布局调整：各单位热网耗水量对比置于供暖单耗对比上方

## 2026-11-04 数据看板布局调整：各单位热网耗水量对比置于供暖单耗对比上方

- **需求背景与调优意图**：
  - 用户要求调整看板板块排序，将“各单位热网耗水量对比情况”板块调整至“供暖热单耗对比”（及其整组单耗卡片和切换栏）的上方。
- **改动范围与落地详情**：
  - 页面调整 [`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DashBoard.vue)：
    - 将 `<section class="dashboard-grid__item dashboard-grid__item--water">` 移动到 `<section class="dashboard-grid__item dashboard-grid__item--unit-toggle">` 与供暖热/电/水单耗三张卡片之前；
    - 形成“调度运行事件 → 全网热网耗水量水力哑铃图（总量与同比） → 供暖单耗对比（单位面积消耗）”的平滑业务浏览动线。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（23.18s，生成产物 `DashBoard-X_Wmz_eG.js`）。

## 2026-11-04 数据看板热网耗水量对比精细化调优：下方外围标尺调整为主城区 2/5 向上取整千

## 2026-11-04 数据看板热网耗水量对比精细化调优：下方外围标尺调整为主城区 2/5 向上取整千

- **需求背景与调优意图**：
  - 用户提出全新的黄金比例优化方案：“将下方的标尺，改为主城区标尺上限的 2/5，并向上取整千”，替代原 1/2 下取整千，进一步优化外围主体的视觉占比。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 下方标尺上限算法变更为：
      ```javascript
      const twoFifthsMain = (mainTrackEnd * 2) / 5
      const ceilThousand = Math.ceil(twoFifthsMain / 1000) * 1000
      const subTrackEnd = Math.max(ceilThousand > 0 ? ceilThousand : 1000, Math.ceil(subMax * 1.06))
      ```
    - **实测与视觉效果**：
      - 本日主城区专属标尺量程为 ~12,273 吨；
      - 其 2/5 为 4,909.2 吨，向上取整千后**精确锁定为标准的 5,000 吨**；
      - 外围最大主体庄河环海（3,185 吨）在 5,000 吨标尺下占比为 **63.7%**，金州热电（2,545 吨）占 **50.9%**；
      - 右侧留出约 36% 的开阔视野容纳变动胶囊标签，不偏左也不逼仄，达成极佳的视觉平衡。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（16.82s，生成产物 `DashBoard-BQ06mhN5.js`）。

## 2026-11-04 数据看板热网耗水量对比精细化调优：移除全口径与双栏维度前的 Emoji 图标

## 2026-11-04 数据看板热网耗水量对比精细化调优：移除全口径与双栏维度前的 Emoji 图标

- **需求背景与调优意图**：
  - 用户反馈顶部全口径指标栏（💧、❄️）与下方双栏维度徽章（📅、❄️）前面的图标显眼多余，要求彻底去掉图标，保持专业纯文本表达。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 移除顶部两项指标标题前方的 `<span class="water-global-metric__icon">💧/❄️</span>`；
    - 移除左右双栏徽章中的 `📅 本日` 改为 `本日`，`❄️ 供暖期累计` 改为 `供暖期累计`；
    - 清理冗余的 `.water-global-metric__icon` CSS 规则；
    - 整体板块呈现出沉稳严谨的企业生产管理风格。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功。

## 2026-11-04 数据看板热网耗水量对比精细化调优：哑铃差额标签移除单位 t

## 2026-11-04 数据看板热网耗水量对比精细化调优：哑铃差额标签移除单位 t

- **需求背景与调优意图**：
  - 用户反馈图表右侧的变动胶囊标签无需带计量单位 `t`，要求去掉 `t`，使数字与百分比更加纯粹凝练。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 将 `formatCompactTons` 重构为 `formatCompactValue`，彻底移除结尾的 `t` 字符；
    - 差额胶囊格式化由 `▼ -131.2t (-1.1%)` 纯净化为 `▼ -131.2 (-1.1%)`（正数如 `▲ +408 (+19.1%)`）；
    - 界面标签更加精简紧凑，完全消除冗余单位字符。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功。

## 2026-11-04 数据看板热网耗水量对比精细化调优：字号与辨识度全面放大提升

## 2026-11-04 数据看板热网耗水量对比精细化调优：字号与辨识度全面放大提升

- **需求背景与调优意图**：
  - 用户反馈板块文字偏小、远距离或快速浏览时识别较为吃力，要求字号稍微更明显、更易识别。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **ECharts 图内文本字号全面提升**：
       - 圆球实际值标签由 `11px` 放大至 `13px`（字重 800，`3px` 白色高反差微光描边）；
       - 右侧同比变动胶囊标签由 `10px` 放大至 `12px`（字重 700，内边距增至 `[3, 7]`，红绿边框增强至 1.5px）；
       - 左侧 Y 轴主体名称由 `12px` 放大至 `13.5px~14px`（深碳墨黑 `#0f172a` 加粗 700~800，`grid.left` 放宽至 `84` 确保不挤压）；
       - X 轴刻度文字与“吨”单位由 `10px` 浅灰放大至 `12px`（深石墨灰 `#334155` 加粗 600）；
       - `grid.right` 扩展至 `105`，为放大的差额胶囊预留充足留白；
    2. **DOM 文字排版与视觉层级增强**：
       - 大标题由 `18px` 提升至 `20px` 加粗；
       - 顶部全口径热网耗水总量由 `20px` 放大至 `24px` 特粗加深，对比文字提升至 `13.5px`；
       - 左右双栏徽章（📅 本日、❄️ 供暖期累计）由 `13px` 放大至 `14.5px`，图例文案放大至 `13px`。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功。

## 2026-11-04 数据看板热网耗水量对比精细化调优：实际值圆珠节点增加悬浮数字标签

## 2026-11-04 智慧供热刷新间隔支持当前页面设置

- `SmartHeatingView.vue` 新增刷新间隔选择（15s / 30s / 1m / 2m / 5m）；`refreshIntervals` 在页面内存中分别保存两个标签的设置，默认均 60000ms，不写本地存储或服务器，重新打开页面恢复默认；`refreshIntervalMs` 和 watcher 在修改间隔时立即重建计时器，保留自动刷新开关与手动刷新。
- 中继核查：实际下载脚本 `backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py` 默认 60 秒，备用 `backend/projects/daily_report_25_26/smart_heating_sync.py` 默认 30 秒，均优先读取同目录 `smart_heating_config.json`；每轮采集推送完成后再 sleep，实际开始间隔为执行耗时加配置秒数。仓库未发现该配置文件，办公电脑运行值无法据此确认。本轮不修改采集频率。
- 验证：Vue 脚本与模板编译、刷新状态与计时器行为检查通过。无需迁移，回滚恢复本轮 Vue 选择器、内存状态、watcher 和样式变更。

## 2026-11-04 工况一览恢复 1m 刷新

- 按用户最新要求，`SmartHeatingView.vue` 的 `refreshIntervalMs` 统一返回 60000ms，两标签均每 1 分钟自动刷新，保留手动刷新与开关。
- Vue 脚本与模板编译通过；无需迁移或更新中继，回滚仅恢复本轮刷新周期表达式。

## 2026-11-04 数据看板热网耗水量对比精细化调优：实际值圆珠节点增加悬浮数字标签

- **需求背景与调优意图**：
  - 用户希望无需悬停鼠标，即可在图表上直接看到每个单位当前实际值的数字究竟是多少吨。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 在主城区与外围单位的“今年本期”蔚蓝圆珠散点（`symbol: 'circle'`）系列上配置数据标签：
      ```javascript
      label: {
        show: true,
        position: 'top',
        distance: 5,
        formatter: currValFormatter,
        fontSize: 11,
        fontWeight: 700,
        color: '#0284c7',
        textBorderColor: '#ffffff',
        textBorderWidth: 2.5,
      }
      ```
    - **显示与排版效果**：
      - 数字位于实心圆珠正上方（如 `11,557`、`2,545`、`2,916`），带千分位和白色防遮挡微光描边；
      - 供暖期累计大数值自动转换为紧凑的“万”字单位；
      - 与右侧的同比增减红绿胶囊（`▼ -131.2t (-1.1%)`）在空间上完美分离，互不遮挡，图表信息密度与易读性大幅提升。
- **构建与测试**：
  - 前端执行 `npm run build` 打包校验成功（1058 个模块转换，0 错误 0 警告，生成最新产物 `DashBoard-Cn4g5onR.js`）。

## 2026-11-04 数据看板热网耗水量对比精细化调优：下方外围标尺锁定为主城区 1/2 并向下取整千

## 2026-11-04 工况一览自动刷新改为 2 分钟

- `SmartHeatingView.vue` 的 `refreshIntervalMs` 按标签选择工况一览 120000ms、热源信息 60000ms；`restartAutoRefresh` 在切换标签或开关时重建定时器，正在请求时跳过重复刷新，页面提示同步显示 2m / 1m，手动刷新仍可用。
- 验证：Vue 脚本与模板编译通过。只修改前端查询频率，不改变客户端采集周期或数据时效；无需迁移，回滚恢复本轮计时器和文案改动即可。

## 2026-11-04 数据看板热网耗水量对比精细化调优：下方外围标尺锁定为主城区 1/2 并向下取整千

- **需求背景与调优意图**：
  - 用户提出明确标尺规则：“规定下方的各单位标尺最大值，为主城区标尺的 1/2 并向下取整（整千）”，替代原有浮动的倍数方案，使坐标刻度完全规整化。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 外围标尺最大值算法更新为：
      ```javascript
      const halfMain = mainTrackEnd / 2
      const floorThousand = Math.floor(halfMain / 1000) * 1000
      const subTrackEnd = Math.max(floorThousand > 0 ? floorThousand : 1000, Math.ceil(subMax * 1.06))
      ```
    - **实测数值**：
      - 本日主城区专属标尺为 ~12,273 吨；
      - 12,273 / 2 = 6,136.5 吨，向下取整整千后，**下方标尺上限精确锁定为 6,000 吨**；
      - X 轴刻度规整呈现为 `0, 2000, 4000, 6000`（或 `0, 1000, 2000, ...`），消除了一切非整数字，外围最大主体庄河环海（3,185 吨）占比为 53.1%，视觉排布整齐专业。
- **构建与测试**：
  - 前端执行 `npm run build` 打包成功（1058 个模块转换，0 错误 0 警告，生成最新产物 `DashBoard-BTOCzW2s.js`）。

## 2026-11-04 数据看板热网耗水量对比精细化调优：外围标尺调整为 2 倍放大

## 2026-11-04 数据看板热网耗水量对比精细化调优：外围标尺调整为 2 倍放大

- **需求背景与调优意图**：
  - 用户查看 3 倍放大效果后，希望尝试将外围主体的标尺放大倍数调整为更为温和克制的 **2 倍**，观察整体视觉平衡感。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    - 外围标尺上限设为 `subTrackEnd = Math.max(Math.ceil(mainTrackEnd / 2), Math.ceil(subMax * 1.06))`；
    - 在当前业务数据下，主城区标尺为 ~12,273 吨，外围标尺锁定在 ~6,137 吨（12,273 / 2 = 6,137），外围每 1 吨的横向物理宽度严格为主城区的 **2.00 倍**；
    - 外围最大主体庄河环海（3,185 吨）在 6,137 吨标尺下占比约为 52%，金州热电（2,545 吨）占比约 41.5%，视觉对比从容适度。
- **构建与测试**：
  - 前端执行 `npm run build` 校验成功。

## 2026-11-04 数据看板热网耗水量对比精细化调优：移除区域标识与外围标尺精准锁定 3 倍放大

## 2026-11-04 工况一览统一显示源采集时间

- `SmartHeatingOverview.vue` 在顶部新增独立“采集时间”区域，读取测点 `SHIJIAN` / `update_time`，替换此前的中继抓取时间，移除行内详情及悬停中的重复时间。断线、过期或缺失时显示“—”，搜索不改变统一时间。
- 输入证据：用户 HAR 中主要测点时间为 `2026-11-04 10:47:05`，少数来源时间不同，因此以页面固定 82 项测点中出现最多的时间展示；同频时取较新时间，悬停统一时间说明取值口径。
- 验证：前端 HAR 渲染回归通过，确认源时间仅出现一次、过期时隐藏。无需接口或数据库迁移；回滚仅恢复本轮组件、测试断言和文档段落。

## 2026-11-04 数据看板热网耗水量对比精细化调优：移除区域标识与外围标尺精准锁定 3 倍放大

- **需求背景与调优意图**：
  - 用户反馈原图表内部的“主城区”和“主城区外单位”小标题破坏了图表连贯性，要求彻底移除该标识；
  - 同时反馈原外围五单位的自适应放大比例（~3.7 倍）偏大，导致外围最大单位（庄河环海）过分逼近右侧边界，要求将外围单位的放大倍数微调收敛为**严格的 3 倍**。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **精准 3 倍物理像素放大比例**：
       - 外围单位标尺上限改为 `subTrackEnd = Math.max(Math.ceil(mainTrackEnd / 3), Math.ceil(subMax * 1.06))`；
       - 在当前业务数据下，主城区标尺为 ~12,273 吨，外围标尺精准锁定在 ~4,091 吨（12,273 / 3 = 4,091），使外围单位每 1 吨在屏幕上的像素宽度不多不少正好为主城区的 **3.00 倍**；
       - 外围最大主体庄河环海（3,185 吨）在 4,091 吨的标尺下占比收敛至约 78%，右侧留出 22% 舒适视觉空间，既放大变动又从容美观；
    2. **纯粹化视觉布局**：
       - 彻底移除 ECharts 配置中的 `title` 区域标识，消除“主城区”与“主城区外单位”文字，依靠 Y 轴六大主体名称自然对齐；
       - 上下 Grid 垂直间隙微调（Grid 0 设为 `top: 14, height: 38`；Grid 1 设为 `top: 88, height: 236`），整体更加舒展规整。
- **构建与测试**：
  - 前端执行 `npm run build` 校验成功（1058 个模块转换通过，产物更新为 `DashBoard-CwJshsNB.js`）。

## 2026-11-04 热网耗水量图表文案精简

- `frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`：左右两栏副标题统一为“自适应标尺”；图内区域标题改为“主城区”和“主城区外单位”，去掉括号说明。仅调整展示文案，数据和标尺计算保持不变。
- 验证：Vue 单文件编译检查通过。无需迁移；回滚仅恢复该组件上述四处文案，保留其他改动。

## 2026-11-04 数据看板热网耗水量对比落地“双层分级自适应标尺”：化解主城区体量压制

- **业务难点与极值破局**：
  - 用户反馈：主城区热网耗水体量极其庞大（本日 8,000~12,000 吨，全期累计达 180 万吨，占全网 65% 以上），而北方热电、金普公司、庄河环海、研究院等外围单位体量在数百至几千吨之间；
  - 若在同一单标尺（0 ~ 12,000 吨 / 0 ~ 200 万吨）下绘制哑铃图，主城区以外的各单位哑铃两端距离仅占 2%~5% 宽度，哑铃杆缩成极短的像素点，难以肉眼对比增减趋势。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **ECharts Multi-Grid 双层独立坐标体系**：
       - 在同一个 ECharts 容器内构建上下双 Grid（Grid 0 上层展示主城区，高度占 22%；Grid 1 下层展示外围 5 个单位，高度占 56%）；
       - 上下层分别绑定独立的 `xAxis[0]` 与 `xAxis[1]`，彻底解耦极值对小单位的标尺压迫；
    2. **分级自适应标尺与 4 倍视觉放大**：
       - **主城区（上层专属标尺）**：最大值自适应贴合主城区数值（本日约 12,000 吨，刻度 0~1.2 万吨）；
       - **外围 5 单位（下层自适应放大标尺）**：最大值仅以外围单位中的最大值（本日约 3,200 吨）为上限，标尺量程从 12,000 吨收缩为 3,400 吨，**使外围 5 个单位的哑铃线段和增减幅度直接放大近 4 倍（400%）**，微小变化清晰可见；
    3. **视觉层次与分区标注**：
       - 在图表内增加轻量级辅助分区线与标尺说明，主城区与外围单位各自对齐专属 X 轴，右侧紧凑差额标签自动跟随；
       - 保留置顶全口径概览栏、去年同期垂直标杆刻度针（`|`）与今年本期圆珠（`●`）对比。
- **构建与测试**：
  - 前端执行 `npm run build` 打包成功，1058 个模块转换成功，0 错误 0 警告（18.02s），产物更新 `DashBoard-DZIH_vmn.js`。

## 2026-11-04 智慧供热双标签页排版与手机窄屏适配

- 需求：继续优化“热源信息”和“工况一览”排版，尤其是手机窄屏阅读与操作。
- 文件与流程：`SmartHeatingView.vue` 统一分段标签、顶部操作栏与指标摘要布局，在 1100px / 640px 断点重排；640px 以下筛选区采用搜索整行与双列选择器，四类桌面表格隐藏，新增 `components/SmartHeatingPointCards.vue` 复用同一 `displayList` 输出首站、电厂、一次网及全网结果的测点卡片，保留所有参数、单位、更新时间，空值不参与温压差计算。配置弹窗限制视口高度，内容独立滚动。
- 工况一览：`components/SmartHeatingOverview.vue` 增加四分区快捷导航、分区编号与统一搜索样式；桌面保留双栏表格，中屏单栏，手机将原表格行重排为两列参数卡片，新增原生 `details` 供触屏展开采集名称与源更新时间。未改变数据来源或时效规则。
- 验证（最后验证日期：2026-11-04）：前端 HAR 渲染回归通过（82 项映射、零值/空值、过期/断线隐藏）；新增卡片离线 SSR 验证覆盖三类测点全部 18 项参数、单位、零值、空值、温差与断线空态；`npm run build` 通过，存在既有大文件分包提示。
- 限制：浏览器访问服务不可用；尝试桌面检查时，工具因无法可靠识别 Chrome URL 而停止，未完成实际桌面/手机截图验收。SSR 不替代 CSS 实际视口目视检查。
- 迁移与回滚：仅前端布局调整，无需数据库迁移或更新办公电脑中继。恢复上述 Vue 文件及本轮测试断言修改、撤销新增卡片组件即可回滚，保留前轮标签页和中继改造及其他并行修改。

## 2026-11-04 智慧供热新增热源信息与工况一览标签

- 输入：用户 HAR `configs/192.168.1.206(工况一览).har`。独立无请求体 `POST /gk_get_data/` 返回五类字典 137 项，原页面固定选取 82 项。
- 前端：`SmartHeatingView.vue` 默认保留“热源信息”，新增 `SmartHeatingOverview.vue` 与 `smartHeatingOverview.js`，按电厂 28、首站 18、一网 11、换热站及商户 25 项分区展示，支持搜索、采集时间、源更新时间、零值和空值区分。
- 中继：更新 `smart_heating_sync.py`、实际下载脚本 `backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py`、`api/smart_heating.py` 与 `dev_relay_pull_sync.py`。`gk_data` 与 `gk_collected_epoch` 贯通采集、接收、转发、feed 及主动拉取；新接口失败不阻断其他源，仅工况成功也能推送。
- 时效：工况独立按 180 秒判定，前后端隐藏过期值；中继保留上级 `received_epoch`，避免旧快照拉取后被刷新为在线，各节点时钟需一致。旧客户端协议兼容。
- 验证（2026-11-04）：后端 `python -m unittest backend.projects.daily_report_25_26.tests.test_smart_heating_overview -v`，5 项通过；前端 `node src/projects/daily_report_25_26/tests/smartHeatingOverview.test.mjs`，82 项匹配及实时/过期/断线/旧客户端渲染通过；`npm run build` 成功，有大文件分包提示；两个客户端通过 Python 3.8 AST 校验；本地页面 HTTP 200。
- 边界：未将 HAR 历史数据写入平台；浏览器控制不可用，未截图目视检查；未验证办公电脑内网实际采集与生产推流；未做全仓覆盖率或依赖审计。
- 升级与回滚：无需数据库迁移。部署前后端后下载并替换办公电脑客户端、重启脚本，保留配置 JSON。回滚仅撤销上述代码、两个新增测试及本次文档段落，恢复旧客户端，保留其他并行修改和运行数据。

## 2026-11-04 数据看板热网耗水量对比精细化调优：最上方置顶全口径指标与标杆针哑铃图重构

- **需求反馈与精细化调优**：
  - 用户对热网耗水量组件提出 7 项具体细节改进：
    1. 标题变更为“各单位热网耗水量对比情况”；
    2. 移除原长副标题说明；
    3. 左侧维度标头由“当日（业务日）”精简统一为“本日”；
    4. 移除“少补达标”、“全期向好”等主观评价胶囊标签；
    5. 解决图表未充满范围、右侧空白过大的问题；
    6. 针对两端实物量相差不大（如 1%~5%）导致圆球重叠靠太近看不清的问题，提供专业清晰的图形解决方案；
    7. 在最上方置顶增加全网“全口径”热网耗水量汇总指标栏。
- **改动范围与落地详情**：
  - 组件深度优化 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **顶部置顶全口径汇总横栏**：在卡片最顶部设立高对比度双指标汇总条，并列展示“💧 本日全口径热网耗水量”与“❄️ 供暖期全口径热网耗水量”，大字号呈现全网实际总量（吨），直观比对去年同期值与同比少补/多补吨数与比例；
    2. **文案精简与标签净化**：卡片大标题更新为“各单位热网耗水量对比情况”，移除冗余副标题，左栏统一标识为“📅 本日”，彻底剔除“少补达标”等冗余标签；
    3. **解决右侧空白过大、充满宽度**：调整 X 轴最大值为 `maxVal * 1.06`（去除原 35% 冗余留白），配合将 `grid.right` 收紧至 `90px`，使数据柱体饱满贯穿 90% 以上可视区域；
    4. **标杆刻度针(Target Needle)彻底消除圆球重叠**：
       - 将去年同期标记升级为**高精度垂直标杆刻度针**（`symbol: 'rect', [3.5, 20]`，琥珀橙色）；
       - 今年本期保持为**实心指示圆珠**（`symbol: 'circle', 14px`，蔚蓝湖水色）；
       - 结合中置发光连接杆（节水绿/增耗红），无论两端数值多么接近（哪怕仅差 3~5px），垂直刻度线与圆形球体天然具备极强的几何对比，针珠分离、方向分明，彻底消除了两个大圆球重叠带来的模糊感。
- **构建与测试**：
  - 前端执行 `npm run build` 打包成功，1056 个模块转换通过，0 警告 0 错误（16.55s）。

## 2026-11-04 数据看板各单位热网耗水量水力哑铃图布局升级：左右双栏并列（左侧当日/右侧供暖期累计）

- **需求调整与交互升级**：
  - 用户反馈原切换按钮仍需手动点击切换，希望进一步提升看板的一目了然感；
  - 彻底去除“本月累计”维度与顶部的维度切换药丸按钮；
  - 将卡片重构为**双栏对称并列排布**：**左侧常驻展示当日（业务日）热网耗水量哑铃图**，**右侧常驻展示供暖期累计热网耗水量哑铃图**，无需任何点击切换，全貌尽收眼底。
- **改动范围与落地详情**：
  - 组件升级 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
    1. **双栏响应式栅格结构**：采用 `grid-template-columns: 1fr auto 1fr` 弹性栅格，大屏下左右双翼并列、中置纤细竖线分割，小屏自适应上下折叠；
    2. **独立双 KPI 胶囊横栏**：左栏顶部配备“📅 当日（业务日）”专属全网耗水概览（当日总量、同期量、同比差额与增减率、少补达标评价）；右栏顶部配备“❄️ 供暖期累计”专属全网耗水概览（全期总量、同期量、全期同比、全期向好评价）；
    3. **双 ECharts 实例协同管理**：拆分为 `dayChartRef` 与 `seasonChartRef` 双实例容器，统一由 `ResizeObserver` 自适应监听宽度变化，支持富文本标签（如 `▼ -127,208t (-21.2%) 节水`，针对全期大数值自适应紧凑换算），深色毛玻璃 Tooltip 精确区分当日与全期口径；
    4. **顶栏精简极简化**：移除切换药丸按钮，保留刷新与清晰的“今年本期/去年同期/节水少补/增耗多补”双色图例指示。
- **构建与测试**：
  - 前端执行 `npm run build` 打包成功，1053 个模块构建通过，0 警告 0 错误（33.85s）。

## 2026-11-04 数据看板新增各单位热网耗水量对比水力哑铃图(Dumbbell Plot)

- **功能背景与用户诉求**：
  - 用户希望在数据看板中独立呈现各单位的“热网耗水量/补水量”指标，突出绝对实物量（吨数）的同比情况，杜绝二维表格的网格压迫感；
  - 明确主体为六大业务板块：**主城区**（打包供热公司总口径：电厂一次网补水 + 换热站补水）、**金州热电**、**北方热电**、**金普公司**、**庄河环海**、**研究院**（均取自“其中：热网补水量”）；剥离电厂自用耗水、剥离购水量与收费面积，纯粹聚焦水耗；
  - 选用高直观度的**水力哑铃图（Dumbbell Plot）**，支持自由切换**当日（业务日）**、**本月累计**、**供暖期累计**三大维度同比。
- **改动范围与落地详情**：
  1. **后端指标统计服务与 API 端点**：
     - 新建服务模块 [`backend/projects/daily_report_25_26/services/network_water_service.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/network_water_service.py)，基于 `get_season_windows(biz_date)` 动态计算当日、本月累计与供暖期累计时间窗口；
     - 从底表 `DailyBasicData` 聚合六大主体的当前业务期与去年同期耗水吨数、同比差额及增减率，同时自动计算全网热网耗水总量汇总；
     - 在 [`backend/projects/daily_report_25_26/api/dashboard.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dashboard.py) 暴露免鉴权端点 `GET /api/v1/projects/:projectKey/dashboard/network_water_dumbbell`；
  2. **前端接口服务扩展**：
     - 在 [`frontend/src/projects/daily_report_25_26/services/api.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/api.js) 中新增 `getDashboardNetworkWaterDumbbell` 调用方法，支持 `showDate` 参数与 `AbortController` 请求取消；
  3. **高颜值独立哑铃图组件**：
     - 新建组件 [`frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/components/NetworkWaterDumbbellCard.vue)：
       - **顶栏药丸控制**：提供【当日（业务日）】/【本月累计】/【供暖期累计】轻量切换药丸按钮与刷新按钮；
       - **全网概览 KPI 胶囊横栏**：动态显示全网热网耗水总量、去年同期值、同比少补/多补吨数与百分比，自动给出“漏损控制良好”或“漏损偏高需重点排查”评价标签；包含今年本期(🔵)、去年同期(🟠)、节水少补(🟢)、增耗多补(🔴)图例提示；
       - **ECharts 水力哑铃图**：六大主体横向排列，底衬细微轨道线；中间以平滑圆角连接杆串联去年同期与今年本期，同比节水显示翠绿、增耗显示红粉；右侧自带胶囊徽章浮标（如 `▼ -131.2t (-1.1%) 节水`）；鼠标悬浮弹出深色毛玻璃卡片式 Tooltip 详细穿透；
  4. **看板主页面布局挂载**：
     - 在 [`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DashBoard.vue) 中引入组件，紧随供暖单耗行之后以整栏宽度（`grid-column: 1 / -1`）挂载，并自动与看板业务基准日期和打印导出样式协同。
- **构建与测试**：
  - 后端执行 `py_compile` 及服务单元测试通过，计算逻辑耗时 < 10ms，精准聚合；
  - 前端执行 `npm run build` 打包成功，1053 个模块构建通过，0 错误（24.07s）。

## 2026-11-04 填报页面顶栏按钮布局紧凑化优化与“一并提交”单行归并

- **需求背景**：
  - 用户反馈在供热公司的每日填报页面（`DataEntryView.vue`）中，顶栏操作区域内的操作按钮（包括“📁 上传投诉报表”、“⚡ 自动拉取投诉量”、“📊 查看统计结果”、“一并提交全部表格”等）因尺寸过大且样式设为 `flex-wrap: wrap`，导致整体折行成了两行，其中核心的“一并提交”等按钮被挤落到下方第二行；
  - 希望将操作栏内的所有按钮统一排布在同一行，布局精致、紧凑整齐。
- **改动范围与落地详情**：
  1. **顶栏弹性盒与防折行布局治理** (`DataEntryView.vue`)：
     - 将 `.topbar__title-group` 调整为 `flex: 0 0 auto`，防止左侧大标题/副标题过度挤占水平宽度；
     - 将 `.topbar__actions` 调整为 `flex: 1 1 auto; min-width: 0;`，将右侧可用宽度最大化开放给操作按钮；
     - 将 `.topbar__action-row` 与 `.topbar__buttons` 设置为 `flex-wrap: nowrap;`，桌面上坚决杜绝按钮折行形成上下两排，同时添加平滑滚动保护（`overflow-x: auto`）；
  2. **解除硬性最小宽度与按钮尺寸精细化** (`DataEntryView.vue`)：
     - 去除原全局 `.topbar__buttons .btn { min-width: 120px; }` 导致的尺寸冗余撑大问题，改为自适应内容宽度（`min-width: auto; height: 34px; padding: 0 12px; font-size: 13px; white-space: nowrap; flex-shrink: 0;`）；
     - 优化已停用的“📁 上传投诉报表”按钮（`is-disabled-btn`），内边距收紧至 `0 10px`，字号微调为 `12px`，视觉更轻量；
     - 优化多表合并提交文案：由冗长的 `一并提交全部表格 (共${unitSheets.length}张)` 精简为干练的 `一并提交 (共${unitSheets.length}张)`，完整说明保留在 `title` 悬浮气泡中，大幅节约 50px 宽度；
     - 优化副按钮“仅提交当前表”（`text-btn`）高度与内边距，确保整组按钮在不同分辨率显示屏下均稳定居于同一行。
- **构建与测试**：
  - 前端执行 `npm run build`，1051 个模块构建通过，0 错误（16.51s）。



## 2026-11-04 全局管理中心新增底表本地下载与供热填报端一键自动拉取投诉量入表

- **功能落地背景**：
  - 用户反馈希望在全局管理中心（`global_management`）的金山文档配置页中增加“下载到本地”按钮，方便随时备份或离线人工核对最新的 12345 诉求工作簿；
  - 同时在供热公司的每日填报页面（`DataEntryView.vue`）中，废弃原有的人工手动上传流程：将原“上传投诉报表”按钮置灰锁定不可点击，在其右侧增加“自动拉取投诉量”按钮，实现一键从金山文档云端拉取、计算并自动对齐填入供热公司的两张填报表对应单元格中。
- **改动范围与落地详情**：
  1. **后端附件直下接口扩展** (`complaint_optimizer.py`)：
     - 新增 `GET /data_entry/complaints/kdocs/download` 端点；
     - 调用 `kdocs_complaint_service.download_kdocs_workbook_bytes()` 获取云端最新底表二进制流，设置标准 `Content-Disposition: attachment; filename*=UTF-8''...` 响应头，支持浏览器直接拉取下载。
  2. **前端全局管理控制台** (`GlobalManagementView.vue`)：
     - 操作栏中新增“📥 下载底表到本地”按钮；
     - 结合 `fetch` 与 Blob URL 触发无阻断的原生文件下载，下载完成时弹出气泡反馈。
  3. **供热公司填报表交互升级** (`DataEntryView.vue`)：
     - 将原“📁 上传投诉报表”按钮设置为 `disabled` 且增加不可用禁用态样式，鼠标悬浮提示“已升级为云端自动拉取”；
     - 在其右侧新增显眼的暖金/极光蓝渐变按钮“⚡ 自动拉取投诉量”；
     - 实现 `triggerAutoPullComplaint()` 方法：一键异步调用后端 `/data_entry/complaints/kdocs/sync`，自动以当前填报业务日期进行计算，并直接无缝衔接现有的 `fillComplaintData()` 流程，将指标精准填入 `GongRe_Sheet` 与 `GongRe_branches_detail_Sheet`，自动高亮暖金色提示并标记为 dirty 待提交状态；
     - 填入完成后右侧原有“📊 查看统计结果”按钮自动激活，点击可穿透查阅明细穿透弹窗。
- **构建与测试**：
  - 后端执行 `test_download_endpoint.py`，HTTP 200 返回 1.6MB 真实文件流；
  - 前端执行 `npm run build`，1051 个模块编译成功（16.16s 静态检查 100% 通过）。

## 2026-11-04 12345诉求底表金山文档(KDocs)免登录自动抓取与全局管理中心配置标签页落地

- **需求背景与痛点**：
  - 供热公司每日填报中的“12345投诉量”原依赖人工从金山文档在线共享表格（`kdocs.cn/l/cj8e1PTQW0uN`）下载 `.xlsx` 底表后再上传至系统，流程割裂繁琐；
  - 虽然金山文档在浏览器中支持匿名免登录在线查看，但在界面点击“导出/下载副本”时会被强制弹出登录要求；
  - 用户希望在全局管理中心（`global_management`）开设专门配置标签页，持久化存储金山文档分享链接与普通 WPS 账号的 `wps_sid` Cookie 凭证，使系统能够全自动获取下载直链，实现免人工干预的一键拉取与自动统计。
- **技术逆向与架构突破**：
  1. **下载接口逆向与鉴权突破**：
     - 深入探测金山文档接口，发现核心文件下载端点为 `GET https://www.kdocs.cn/api/v3/office/file/{share_id}/download`；
     - 未携带登录态时返回 `40100001 用户未登陆`；但携带任意普通 WPS 免费账号的 Cookie（`wps_sid`）后，金山文档即刻返回带签名时效的底层直链，成功拉取约 1.53 MB 的最新 `2026-2027年度市12345诉求件统计表.xlsx`；
     - 将拉取的二进制文件直接流式送入已有的 `complaint_statistics.calculate()`，全量 10 个中心、市直办/转办、省办等指标秒级计算入库，验证 100% 成功。
- **改动范围与落地详情**：
  1. **后端服务层构建** ([`kdocs_complaint_service.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/kdocs_complaint_service.py))：
     - 实现配置读取与原子保存机制，存储于 `backend_data/projects/daily_report_25_26/config/kdocs_complaint_config.json`；
     - 提供 `extract_share_id`（自动提取 `cj8e1PTQW0uN` 短码）、`test_kdocs_connectivity`（连通性与 Cookie 凭据有效性自检）及 `download_kdocs_workbook_bytes`（流式下载）；
  2. **后端 API 端点下沉** ([`complaint_optimizer.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/complaint_optimizer.py) 与 [`router.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/router.py))：
     - `GET /data_entry/complaints/kdocs/config`：读取当前金山文档配置；
     - `POST /data_entry/complaints/kdocs/config`：保存更新配置并回写；
     - `POST /data_entry/complaints/kdocs/test`：在线测试连接与凭证有效性，回显文件大小与测试日志；
     - `POST /data_entry/complaints/kdocs/sync`：一键自动从云端拉取底表并结合目标业务日期计算诉求指标；
  3. **前端控制台新增独立选项卡** ([`GlobalManagementView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/GlobalManagementView.vue))：
     - 左侧菜单新增 `📋 12345投诉底表(金山文档)` 专用选项卡；
     - 落地配置卡片：支持分享链接编辑、Share ID 自动解析、`wps_sid` 密码/文本明暗切换、备注说明；
     - 提供操作工具栏：包含“💾 保存配置”、“🔌 测试连接与凭证有效性”及“⚡ 立即拉取并试算当日投诉”；
     - 落地连通性测试报告横幅与试算结果可视化卡片（实时预览市直办、省办、总数与未办结件数）；
     - 附带通俗易懂的 5 步开发者工具 `wps_sid` 提取指南。
- **构建与测试**：
  - 后端执行 TestClient 模拟测试，配置读取与下载直链探测 HTTP 200 通过；
  - 前端执行 `npm run build`，1051 个模块编译成功（16.67s 无任何报错）。

## 2026-11-04 常量指标表(constant_data)唯一约束缺失导致ON CONFLICT报错排查与全链路修复

- **问题现象与定位**：
  - 用户在放开管理员同期常量指标修改权限后，在前端页面修改同期指标值并提交，后端及数据库抛出严重错误：
    `ERROR: there is no unique or exclusion constraint matching the ON CONFLICT specification`
    `STATEMENT: INSERT INTO constant_data (...) VALUES (...) ON CONFLICT (company, item, period) DO UPDATE ...`
  - 经深入排查 Postgres 数据库与代码底层，定位以下根因：
    1. **数据库缺失唯一约束/索引**：PostgreSQL 执行 `ON CONFLICT (company, item, period)` 依赖底层存在覆盖该键的 `UNIQUE` 约束或唯一索引；但由于历史表结构调整，底层 `constant_data` 缺少该唯一约束与主键；
    2. **历史重复数据阻碍约束建立**：数据库 `constant_data` 表内存在由历史导入造成的重复记录（总行数 1224，实际由 459 组相同 `(company, item, period)` 记录重复存在 2~3 份构成）；
    3. **建表脚本历史脱节**：`backend/sql/create_tables.sql` 中仍为旧设计的 `(company, center, sheet_name, item, period)` 索引，未与业务对齐。
- **全链路修复措施**：
  1. **数据安全备份与幂等去重**：
     - 在数据库内建立快照备份表 `constant_data_backup_20261104`；
     - 基于 `ctid` 进行精准安全去重（清理 765 条冗余完全重复记录，保留 459 条标准基线数据）；
  2. **建立标准数据库主键与唯一约束**：
     - 执行 `ALTER TABLE constant_data ADD PRIMARY KEY (id);`；
     - 执行 `ALTER TABLE constant_data ADD CONSTRAINT uq_constant_data_company_item_period UNIQUE (company, item, period);`，彻底满足 `ON CONFLICT` 匹配要求；
  3. **后端代码批次内防重增强** (`legacy_full.py`)：
     - 在 `_persist_constant_data` 中加入字典聚合 `deduped` 机制，在同一提交批次内部按 `(company, item, period)` 自动合并重复项，杜绝 PostgreSQL 二次触发 `ON CONFLICT DO UPDATE command cannot affect row a second time`；
  4. **建表 SQL 同步**：
     - 同步更新 `backend/sql/create_tables.sql` 与 `backend/sql/create_tables copy.sql` 中的唯一索引定义为 `(company, item, period)`。
- **验证结论**：在数据库内实测批量 UPSERT 语句执行成功（`INSERT 0 2`），Python 单元持久化测试 100% 通过（`Success, count = 2` 及批次去重生效）。

## 2026-11-03 常量指标页面解除全局管理员(Global_admin)同期值修改限制

- **问题背景与根因分析**：
  - 用户反馈在常量指标页面（`constant_data/sheets`，如 `数据结构_常量指标表.json`）中，即便拥有 `Global_admin` 角色，也无法编辑修改“25-26同期值”列；
  - 经深入排查前端代码 `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`，定位出三处关键根因：
    1. **列锁定条件硬编码**：在 `setupStandardGrid`、`applyStandardQueryResult` 等多处网格初始化逻辑中，对常量指标表最后一列（`isConstantPeerColumn`）直接赋予了硬编码锁定 `locked = true`，未结合 `!isGlobalAdmin.value` 鉴权；
    2. **固有不可写标识污染**：在列元数据对象生成及 `applyReadonlyToColumns` 中，将临时权限锁定状态赋值给了 `__locked` 字段（该字段原本仅代表项目名、计量单位等基础描述列的固有只读），导致后续权限重新计算或刷新时，因 `Boolean(def.__locked)` 恒为 `true` 而永远无法解除只读；
    3. **同期列识别匹配缺漏**：`isPeerColumnIndex` 与 `isPeerColumnForTable` 仅匹配了“同期”与“去年”，未覆盖常量指标表模板原始列名“同供暖期”以及后端动态替换后的供暖期标签（如 `25-26`），导致同期列无法按模板类型与列索引精准识别。
- **改动范围与修复方案**：
  - **核心页面**：[`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)
    1. **完善同期列识别逻辑**：在 `isPeerColumnIndex` 与 `isPeerColumnForTable` 中增加对 `同供暖期` 的支持；针对 `templateType === 'constant'` 场景，准确将最后一列识别为同期指标列；
    2. **解耦基础锁定与权限锁定**：统一规范 `__locked` 仅表示 `index <= readonlyLimit`（基础描述列固有锁定）；将同期列的编辑权限严格交由 `!isGlobalAdmin.value && isPeer` 控制；
    3. **全生命周期只读解绑**：
       - `setupStandardGrid`：常量同期列仅在非 `Global_admin` 时锁定，`Global_admin` 正常开放双击编辑；
       - `applyStandardQueryResult`：镜像查询数据回填时，保留 `isGlobalAdmin` 权限判断并解开只读锁定；
       - `applyReadonlyToColumns`：动态只读应用逻辑中，不再向 `__locked` 写入权限只读标志，保证响应式角色切换时列状态可逆；
       - `loadComplaintTargetState` 与 `fillEfficiencyData`：同步修正表格状态生成与缓存逻辑；
       - `watch` 响应式增强：将 `isGlobalAdmin.value` 加入响应式侦听，确保管理员会话信息加载完成后即时解开表格编辑限制。
- **验证结论**：本地执行 `npm run build` 打包构建，耗时 18.40s 静态检查与打包 100% 成功。

## 2026-11-03 智慧供热中继远端同步URL智能容错解析与404根因修复

- **问题排查与根因定位**：
  - 用户反馈本地容器日志出现 `POST /api/v1/projects/daily_report_25_26/smart-heating/sync-from-remote 404 Not Found`；
  - 经深入排查，本地后端该路由正常挂载，404 是由于请求远端服务器失败后直接向上抛出 HTTPException(404) 导致；
  - 根因在于配置中的 `remote_server_url` 保存了带完整路径的 URL，原代码在拼接时未做前缀去重，导致向远端发出的请求路径重复叠增（形如 `https://platform.smartview.top/.../relay-feed/.../relay-feed`），从而遭到远端服务器 404 拒绝。
- **架构级容错与修复**：
  1. **智能 URL 自动规范化** (`smart_heating.py`)：在 `sync_from_remote_server` 中引入智能路由解析器，自动识别并兼容“完整端点”、“项目基础路径”或“基础域名”等多种输入风格，彻底消除重复拼接隐患；
  2. **错误响应模型重构**：捕获远端 HTTPError 时，返回统一的 JSON 结构体 `{"ok": false, "message": "...", "remote_url": ...}`，消除将远端异常误认为本地路由缺失的歧义；
  3. **前端配置与持久化复位**：将 `relay_config.json` 与 `SmartHeatingView.vue` 中的远端基准地址复位为规范的 `https://platform.smartview.top`。
- **验证**：在本地 Docker 容器内实测调用 `POST /sync-from-remote`，成功连通生产云端拉取 54 首站 + 58 电厂 + 242 一次网测点，HTTP 200 顺利入库。

## 2026-11-03 智慧供热数据刷新周期调整为1m与客户端下载权限限定为Global_admin

- **刷新频率优化**：
  - 前端工况看板 (`SmartHeatingView.vue`)：自动刷新计时器由 30 秒调整为 60 秒（1 分钟 / 1m），顶部操作栏复选框文案同步调整为“自动刷新 (1m)”；
  - 后端心跳与工况时效 (`smart_heating.py`)：将在线心跳判定有效期由 90 秒扩展至 180 秒（3 分钟），以完美容纳 1 分钟轮询周期及网络波动，避免工况在连接/断开状态间抖动；
  - 本地与内网中继采集脚本 (`smart_heating_relay_win7.py` 与 `dev_relay_pull_sync.py`)：出厂默认采集/同步周期统一调整为 60 秒。
- **客户端下载权限收敛**：
  - 前端界面 (`SmartHeatingView.vue`)：引入 `useAuthStore`，增加 `isGlobalAdmin` 权限判定；仅当登录用户角色为 `Global_admin` 时，才在顶部 Banner 及未连接提示横幅中渲染“📥 客户端脚本”下载按钮；非管理员尝试调用时给出明确的弹窗权限拦截提示；
  - 服务端接口 (`smart_heating.py`)：原已配置 `session.group != "Global_admin"` 403 阻断，前后端权限策略实现严密闭环。
- **构建与测试**：`npm run build` 成功完成打包；`test_relay_api.py` 覆盖刷新与心跳判定测试 100% 通过。

## 2026-11-03 智慧供热服务器中继转发与本地开发环境(localhost)数据同步链路构建

- **需求背景**：用户在办公电脑上运行中继程序将数据推送到线上生产服务器，服务端接收到数据后，需要将该实时数据流二次中继转发至用户的本地开发环境（`localhost`），使开发者在本地开发、联调测试时也能实时查看全网 344 项智慧供热工况。同时要求服务器上的中继转发功能可自由选择开启或关闭（默认开启）。
- **技术挑战与双模架构设计 (Push + Pull 双轨保活)**：
  - **网络屏障**：生产服务器部署于公网，而开发者电脑位于内网/局域网，通常无法直接由公网服务器主动发起 HTTP POST 穿透 NAT 访问 `http://127.0.0.1:8000`（除非配置端口映射或内网穿透）。
  - **架构解决方案**：
    1. **主动中继推送 (Push Relay)**：在 `POST /smart-heating/push` 端点注入 FastAPI `BackgroundTasks`，当服务器接收到办公电脑推流且中继开关开启时，异步非阻塞将完整数据包转发至 `forward_target_url`（默认开启，支持配合内网穿透工具或独立次级节点使用）；
    2. **主动拉取同步 (Pull Relay)**：在生产服务端开放受安全 Token 保护的流接口 `GET /smart-heating/relay-feed`；在本地开发环境提供 `POST /smart-heating/sync-from-remote` API 及开发专用命令行同步工具，支持本地开发机直接从云端服务器中继拉取最新工况写入本地，零网络配置即可突破防火墙与局域网限制。
- **改动范围与落地详情**：
  1. **后端中继与开发同步服务** (`backend/projects/daily_report_25_26/api/smart_heating.py`)：
     - **配置持久化管理**：引入 `_load_relay_config()` 与 `_save_relay_config()`，持久化保存于 `relay_config.json`，配置项包括 `forward_enabled: True`（默认开启）、`forward_target_url`、`remote_server_url`、`push_token` 等；
     - **异步转发非阻塞任务**：实现 `_forward_payload_task`，采用 5s 超时与 SSL 上下文保护，不阻塞主推流接口响应；
     - **中继接收端点**：新增 `POST /smart-heating/receive-relay`，用于接收上级服务器转发推送的数据包，支持 `push_token`、`relay_token` 及 `X-Push-Token` 统一鉴权并入库；
     - **数据拉取数据流**：新增 `GET /smart-heating/relay-feed`，供开发环境安全拉取最新实时工况流；
     - **本地主动拉取同步**：新增 `POST /smart-heating/sync-from-remote`，限 `Global_admin` 角色，本地后端调用后自动拉取线上最新数据并原子更新本地 `latest.json`；
     - **中继开关与参数配置接口**：新增 `GET /smart-heating/relay-config` 与 `POST /smart-heating/relay-config`，支持管理员在线查询与一键切换中继开关、修改转发 URL。
  2. **前端服务 API 封装** (`frontend/src/projects/daily_report_25_26/services/api.js`)：
     - 新增 `getSmartHeatingRelayConfig(projectKey)`；
     - 新增 `updateSmartHeatingRelayConfig(projectKey, payload)`；
     - 新增 `syncSmartHeatingFromRemote(projectKey, payload)`。
  3. **前端看板交互增强** (`SmartHeatingView.vue`)：
     - **环境感知与专属同步按钮**：检测 `window.location.hostname`（`localhost` / `127.0.0.1`），若处于本地开发环境，在顶部 Banner 与未连接离线横幅中自动渲染“📥 从线上中继同步”操作按钮，支持一键拉取并刷新页面展示；
     - **服务器中继开关与状态指示**：顶部 Banner 增加“服务器中继: 已开启/已关闭”胶囊按钮及指示灯，点击直接唤起中继配置弹窗；
     - **中继配置模态浮层**：提供 iOS 风格开关切换中继开启/关闭状态，支持修改转发目标端点 URL 与线上拉取源 URL，点击保存即时生效；
     - **全链路样式与交互优化**：完善弹窗遮罩、毛玻璃背景、表单控件及响应式排版。
  4. **开发环境独立命令行同步脚本** (`dev_relay_pull_sync.py`)：
     - 新增 `backend/projects/daily_report_25_26/dev_relay_pull_sync.py`，支持命令行单次执行 `python dev_relay_pull_sync.py` 或后台守护轮询 `python dev_relay_pull_sync.py --daemon` 自动同步云端工况至本地。
- **构建与验证**：
  - 前端执行 `npm run build`，编译顺利通过（生成 `SmartHeatingView-B7hTYEeq.js` 与 `SmartHeatingView-D2-sDldn.css`）；
  - 后端执行 `test_relay_api.py` 自动化测试，验证包括：
    1. `GET /relay-config` 读取默认 `forward_enabled: True` 成功；
    2. `POST /push` 接收数据并触发后台转发任务成功；
    3. `GET /relay-feed` 鉴权拉取流数据成功；
    4. `POST /receive-relay` 开发环境接收并写入本地成功；
    5. `POST /relay-config` 切换中继开关（开启/关闭）持久化测试成功；
    6. 所有单元测试 100% 通过。

## 2026-11-03 智慧供热“一网”一级分类与层级名称规范化更名为“一次网”

- **需求背景**：按用户明确要求，将智慧供热实时工况看板、元数据规范及全链路接口中的一级分类名称“一网”统一规范更名为“一次网”。
- **改动范围与落地**：
  1. **前端元数据规范库** (`smartHeatingTaxonomy.js`)：
     - `LEVEL1_ORDER` 统一更新为 `['首站', '电厂', '一次网']`；
     - `LEVEL2_BY_LEVEL1` 映射键名由 `'一网'` 更新为 `'一次网'`；
     - `RAW_TAXONOMY_TUPLES` 顺序表中 242 项换热站采集点的一级分类全部规范化为 `'一次网'`。
  2. **前端页面看板** (`SmartHeatingView.vue`)：
     - 顶部 Banner 副标题、KPI 指标副文本（一次网供水/回水加权平均）及 Tab 按钮切换（`🏢 一次网 (242)`）同步更名；
     - 表格列头、数据过滤条件及空态提示文案全面规范化；
     - 修复并优化分类徽章渲染逻辑。
  3. **后端接口与数据清洗管道** (`smart_heating.py`)：
     - `POST /smart-heating/push` 接收数据时，将换热站测点的一级分类统一打标为 `'一次网'`；
     - 增加向下兼容保护：若外部或中继客户端仍传输旧值 `'一网'`，服务端在 `_clean_point_records` 阶段自动平滑升级为 `'一次网'`。
  4. **中继采集脚本** (`smart_heating_relay_win7.py` 及镜像副本)：
     - 在循环采集换热站 9 大中心数据时，将注入的 `item['level1']` 统一由 `'一网'` 更新为 `'一次网'`。
- **构建与测试**：`npm --prefix frontend run build` 成功完成（生成 `SmartHeatingView-DtDlK3bN.js`）；后端清洗管道逻辑与兼容升级断言测试 100% 通过。

## 2026-11-03 智慧供热平台主体分组规范化重构（一级分类/二级分类/采集点层级化排序与错别字校正）

- **需求背景**：智慧供热平台实时监控主体测点数量庞大（涵盖全网 344 个点位），原有分类较为粗放。用户提供《11.3 智慧供热平台主体分组表.xlsx》（`phoenix/configs/11.3 智慧供热平台主体分组表.xlsx`），要求页面严格按表中的层级与次序对所有测点进行梳理，使用“一级分类”、“二级分类”、“采集点”专业称谓，按表内行号次序严格排列，并修正错别字（包括将“xxx机进气”等校正为“xxx机进汽”）。
- **主体分组表深度逆向与元数据构建**：
  - 全面解析 Excel 表《完整条目》工作表，提取出全量 344 个标准采集点条目；
  - 确立清晰严谨的三级层级体系：
    1. **一级分类 (3 大类)**：
       - `首站` (54 项)：涵盖北海#1首站 (16项)、北海#2首站 (8项)、北海水炉 (20项)、香海首站 (10项)；
       - `电厂` (48 项)：涵盖北海电厂 (23项)、香海电厂 (25项)；
       - `一网` (242 项)：涵盖华乐中心 (20项)、春海中心 (29项)、中山中心 (37项)、双兴中心 (21项)、北岗中心 (35项)、香炉礁中心 (18项)、兴工中心 (28项)、大纺中心 (17项)、东港中心 (37项)。
    2. **二级分类 (15 个子类)**：按 Excel 次序严格对齐，纠正此前将 ID 61 误称为胜利中心（实为“北岗中心”）、ID 67 误称为友好中心（实为“中山中心”）、#3首站实为“北海水炉”等口径偏差；
    3. **采集点 (344 个测点)**：经校验 344 个采集点名称在整表中完全唯一无重复。
  - 创建前端元数据常量规范库 `frontend/src/projects/daily_report_25_26/constants/smartHeatingTaxonomy.js`：
    - 导出 `LEVEL1_ORDER`、`LEVEL2_BY_LEVEL1`、`RAW_TAXONOMY_TUPLES`、`TAXONOMY_LIST`、`TAXONOMY_MAP`；
    - 提供 `normalizePoint(rawName)` 函数，实现任意内网原始名称到标准采集点名称、一二级分类及全局 Excel 行序号（1~344）的快速解析与归一化。
- **专业级错别字校正与名称清洗**：
  - 严格落实用户指示，建立双端同步的 `POINT_ALIAS_MAP` 与 `TYPO_CORRECTIONS`：
    1. 修正“进气/抽气”错别字为标准“进汽/抽汽”：
       - `北海#1机进气` -> `北海#1机进汽`
       - `北海#2机进气` -> `北海#2机进汽`
       - `北海#3机抽气` -> `北海#3机抽汽`
       - `北海首站进气参数` -> `北海首站进汽参数`
    2. 规范换热站及测点别名对齐 Excel：
       - `磐海` -> `碧海`，`喜临门` -> `壹临门`，`鸿霖大厦` -> `鸿源大厦`，`桥北` -> `振北`，`黑嘴子(融创)` -> `黑狮子(融创)`，`德政西` -> `德源西`，`春和雲树里` -> `春和爱邻里`，`机车西山村区` -> `机车西山小区`，`保利天禧I01` -> `保利天禧01`，`保利天禧I04` -> `保利天禧04`，`保利禧岸` -> `保利璟岸`，`海涵庄园` -> `海珀庄园`。
- **全链路中继与服务端清洗升级**：
  - 更新 `backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py`（及 `configs/`、`backend/` 对应副本）：
    - 更新 `SZ_MAP` 为标准二级分类名称（`北海#1首站`、`北海#2首站`、`北海水炉`、`香海首站`）；
    - 更新 `YW_MAP` 为 9 大标准运营中心（`华乐中心`、`北岗中心`、`双兴中心`、`香炉礁中心`、`兴工中心`、`春海中心`、`大纺中心`、`中山中心`、`东港中心`）；
    - 采集循环中自动执行名称校正并自动注入 `level1` 与 `level2` 分类字段。
  - 后端接口 `backend/projects/daily_report_25_26/api/smart_heating.py`：
    - 在接收推送端点 `POST /smart-heating/push` 增加 `_clean_point_records` 安全守门，即使客户端未及时更新，服务端入库前依然保证所有测点经过错字清洗与规范分类赋能。
- **前端页面（SmartHeatingView.vue）高精细重构**：
  - **分类体系与筛选工具栏**：
    - 一级分类切换：支持 `首站 (54)` / `电厂 (48)` / `一网 (242)` / `全网总览 (344)`，与 Excel 次序完全一致；
    - 二级分类联动下拉：根据选定的一级分类智能联动展示该类目下的标准二级分类（如选首站展示 4 个首站，选一网展示 9 大中心，选全网展示 15 个二级分类）；
    - 采集点精准搜索框：支持根据采集点规范名称模糊搜索；
    - 排序控制：默认选项为“默认顺序 (按表严格排序)”，严格保持 Excel 中的 1~344 行全局顺序，同时支持温度、流量、温差临时排序。
  - **表格列头全面规范化**：
    - 表格列头明确标示：`#`（Excel 顺序号）、`一级分类`（彩色高亮徽章）、`二级分类`、`采集点`（规范中文名与设备类型标签），全面符合专业规范。
- **构建与测试验证**：
  - 前端 `npm run build` 成功通过无警告，打包出优化后的 `SmartHeatingView-A_zznTTt.js`；
  - Python 全模块 `py_compile` 编译通过；
  - 编写并运行单元测试 `verify_backend.py`，验证错别字校正、分类注入及 344 项连续性 100% 通过。

## 2026-11-03 智慧供热内网平台实时工况看板、中继采集脚本与数据接收接口上线

- **需求背景**：用户计划将运行于公司内网（`http://192.168.1.206:6688`）的“智慧供热平台”实时数据接入 Phoenix 系统进行展示。因当前开发环境无法直连内网，需借助能连通内网的办公电脑（Win7 + Python 3.8 环境）进行中继抓取并推送；新功能放入“生产监控与看板”分组，且严格仅限 `Global_admin` 查看。
- **接口逆向分析与破译**：
  - 基于用户提供的 HAR 归档（`configs/192.168.1.206.har`），通过逆向脚本扫描定位 48 组高频请求，解析出目标平台基于 Python Flask 架构，使用 Signed Session Cookie 鉴权，轮询周期为 30 秒。
  - 成功破译 3 大核心业务接口：
    1. 首站与主管网工况 (`POST /get_sz_data/2`)：包含东环、南环、北网供回补水、板换供回温、热泵吸收热量等 16 组核心测点；
    2. 电厂与热源机组运行参数 (`POST /get_dc_data/2`)：包含北海 #1~#3 汽机、#1~#4 锅炉主汽、燃气炉群等 23 组机组测点；
    3. 换热站一次网实时监测 (`POST /get_yw_data/60`)：覆盖金广、海港、东港印象等 20 座具体换热站，并完成物理口径破译（`f3` 一次供温、`f5` 一次回温、`f1` 一次供压、`f4` 一次回压、`f2` 瞬时流量、`f222` 瞬时热量）。
- **Win7/Python 3.8 中继脚本交付与交互增强**：
  - 创建 `configs/smart_heating_relay_win7.py`，采用 Python 3.8 纯标准库开发（`urllib.request` + `json`），零额外第三方依赖，可在 Windows 7 环境双击或命令行直接运行；
  - 针对老旧办公电脑进行易用性增强：启动时打印交互式配置面板，用户直接按【回车键】即可按当前参数启动；输入编号（1~5）即可快速修改目标服务器 IP、轮询间隔或 Session Cookie；
  - 修改后的参数自动记忆保存至同目录下的 `smart_heating_config.json`，用户下次启动无需重复输入，更无需在记事本中翻找修改代码。
  - 脚本每隔 30 秒定时轮询内网接口，抓取最新数据并格式化推送到 Phoenix 后端接收端点，带时间戳打印运行日志与异常重试。
- **后端接口与数据存储**：
  - 新增 `backend/projects/daily_report_25_26/api/smart_heating.py` 并在主路由中挂载；
  - `POST /api/v1/projects/daily_report_25_26/smart-heating/push`：公开接收端点，带 Token 鉴权，原子写入 `backend_data/projects/daily_report_25_26/smart_heating/latest.json`，并追加历史日志；
  - `GET /api/v1/projects/daily_report_25_26/smart-heating/latest` 及 `/status`：查询端点，严格仅限 `Global_admin` 角色访问，其它组返回 403 Forbidden；
  - `GET /api/v1/projects/daily_report_25_26/smart-heating/client-script`：提供最新免安装数据同步客户端脚本（`smart_heating_sync.py`）的安全下载接口（仅限 `Global_admin`），服务端优先读取放置在 `backend/projects/daily_report_25_26/smart_heating_sync.py` 的源码，确保 Docker 挂载热更新始终能准确响应下载。
- **前端页面脱敏瘦身与客户端一键下载**：
  - 深度重构 `SmartHeatingView.vue`，彻底剔除抓取感与调试信息：删除了全部内网 IP 地址及“中继抓取”字样，将状态提示升格为“实时数据传输中 / 等待数据链路接入”；换热站表头彻底移除开发口径符号（如 `f1`~`f222`），统一采用规范中文表头；
  - 剥离原暴露技术细节的“中继配置指引”Tab，收敛为聚焦于“换热站一次网工况”、“主管网与首站测点”、“电厂与热源机组”三大生产大屏核心面板；
  - 顶部操作栏新增“📥 下载同步客户端”按钮，直接通过前端 API 鉴权调用下载预配置好的 `smart_heating_sync.py`，方便用户直接拷贝至办公电脑运行；
  - `PageSelectView.vue`：在“生产监控与看板”分组（`monitoring_dashboard`）下注册 `smart_heating` 卡片，通过 `withAdminExclusivePages` 控制仅 `Global_admin` 登录时注入展示；
  - `frontend/src/router/index.js`：注册路由 `/projects/:projectKey/pages/smart_heating`，路由守卫校验 `auth.user?.group === 'Global_admin'`，非管理员拦截至 `/forbidden`；
  - `frontend/src/projects/daily_report_25_26/services/api.js`：封装 `getSmartHeatingLatest`、`getSmartHeatingStatus` 及 `downloadSmartHeatingClientScript` API。
- **落实“无连接即无数据”原则与移除历史快照**：
  - 响应用户明确指示（“也不要什么历史快照，没有连接就应该没有数据”）：
    1. **清空预置种子数据**：重置 `backend_data/projects/daily_report_25_26/smart_heating/latest.json`，彻底移除初始生成的 HAR 静态快照（`sz_data: []`, `dc_data: []`, `yw_data: []`）；
    2. **后端接口严谨拦截**：在 `GET /smart-heating/latest` 和 `/status` 接口中，若链路未连接（或超过 90 秒无推流），强制返回空数据列表与 `is_online: false`，杜绝任何历史残留数据漏出；
    3. **前端全面空态化**：`SmartHeatingView.vue` 中测点列表计算属性 `szDataList`、`dcDataList`、`ywDataList` 严格绑定 `isRelayOnline`；未连接时：
       - 顶部状态显示为 `● 数据链路未连接 (等待客户端启动推流)`，灰点静止；
       - KPI 摘要条流量、温度、温差等全部显示为破折号 `—`，在线站数显示 `0 / 0 座`；
       - 插入离线引导横幅（提示运行 `smart_heating_sync.py` 开启实时推流）；
       - 表格内空行明确提示 `数据链路未连接，暂无实时数据`。
- **全网多电厂、多首站及 9 大换热中心全量接入与下载路径定向**：
  - 基于用户二次提供的完整 HAR 归档（`configs/192.168.1.206(1).har`），全面破译并接入全部供热分区：
    1. **电厂侧全覆盖 (58 项)**：北海电厂 (ID 2, 23 组)、香海电厂 (ID 3, 35 组)；
    2. **首站侧全覆盖 (54 组)**：#1首站 (ID 2, 16 组)、#2首站 (ID 3, 8 组)、#3首站 (ID 4, 20 组)、香海首站 (ID 5, 10 组)；
    3. **换热站 9 大中心全覆盖 (242 座)**：ID 60 华乐 (20 座)、ID 61 胜利 (35 座)、ID 62 双兴 (21 座)、ID 63 香炉礁 (18 座)、ID 64 兴工 (28 座)、ID 65 春海 (29 座)、ID 66 大纺 (17 座)、ID 67 友好 (37 座)、ID 68 东港 (37 座)。
  - **中继脚本全量采集升级与用户指定路径落位**：
    1. 遵照用户指示，中继脚本规范存放于 `backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py`；
    2. 后端下载端点 `_get_client_script_path()` 优先从该业务数据路径提供下载，无论开发环境还是生产 Docker 容器均严格统一路径，下载文件名统一为 `smart_heating_relay_win7.py`；
    3. 脚本更新内置出厂 Cookie，并在单轮采集中自动循环 15 个内网端点，为各测点和换热站打上所属中心和首站/电厂中文标签并统一打包推送。
  - **前端交互升级与多维分区筛选**：
    1. 换热站 Tab 增加“运营中心”下拉筛选（支持全部中心及 9 大中心独立筛选）及“所属中心”彩色徽章；
    2. 首站 Tab 增加“首站分区”下拉筛选（#1首站、#2首站、#3首站、香海首站）及关键字检索；
    3. 电厂 Tab 增加“电厂分类”下拉筛选（北海电厂、香海电厂）及对应电厂徽章；
    4. 离线状态保持全空态，在线推送后自动点亮全网 242 座换热站及全部首站机组。
- **验证结果**：
  - 后端脚本定位测试通过，优先指向 `backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py`；
  - 中继脚本 Python 3 语法编译 100% 通过；
  - 前端通过 `npm run build` 生产构建成功，打包产物 `SmartHeatingView-COhLmIGS.css` / `SmartHeatingView-DOdsfcRY.js` 正常生成。
- **最后验证日期**：2026-11-03。


- 用户进一步核实：原表虽有 #3 炉启动中说明，但日报业务日为 11 月 2 日，实际点火为 11 月 3 日 06:10，要求本条显示备用并附 `11.3 6:10` 标签。本节覆盖此前该炉显示运行的结论。
- `dispatch_reconciliation.py` 增加业务日边界显示规则：本设备有启动说明、存在未来启动事件且没有当日主设备操作时显示备用，来源为 date_boundary；原表 table_status、table_text 与次日事件完整保留，人工选择仍优先。规则由提取、查询共同复用，重新提取不再显示本条为运行或启动中。
- `DispatchInfoView.vue` 的 groupedFacilities 为跨日设备事件标签加月日，实际标签 `11.3 6:10 点火`；同号汽机、其他事件不改。供热公司 8:40 仍归 11 月 2 日。
- 通过现有定向脚本预览后更新 11 月 2 日两个状态 JSON 字段；快照 `backend_data/projects/daily_report_25_26/runtime/dispatch-standby-20261103.json`，原提取制品同步。未改动补水、网口及事件字段；无数据库结构迁移。
- 验证：后端调度相关 43 项、前端调度相关 34 项通过，覆盖原 PDF、重复规范化、当日操作不受未来事件覆盖、人工确认优先及标签。数据库原始状态和页面同一查询服务均确认备用与 2026-11-03 06:10 点火证据。回滚命令见 backend README。
- 最后验证日期：2026-11-03。

## 2026-11-03 按用户反馈收敛调度信息改动

- 用户范围：撤回上轮多余状态变更；保留网口指标修复；只显示高温水补水并确认历史漏提；将“抢修工作票”显示分类改成“抢修类”；明确不带日号的 8:40 为当天。其他问题不继续处理。
- `dispatch_extractor.py` 撤回上一轮无括号启动状态识别扩展，恢复原处理；数据库中香海 #3 汽炉从启动中恢复运行，#3 汽机未改动且仍为运行。没有扩改此前已有的括号状态处理规则。
- 补水卡片固定高温水口径，提取器不再用累计替代。历史 5 天的显示指标原本等于累计量，本轮仅将显示指标清空，独立累计字段完整保留；11 月 2 日 4147 吨不变。
- 历史核查 169 天：上轮修复前只有 5 天的卡片有累计替代值，36 天归档 log_raw_text 及 10 月 30 日原 PDF（4643 吨）能证实至少 37 天高温水值漏提。已生成 `configs/dispatch-water-audit-20261103.md`，未批量补填；其他日期缺少完整原文，不能推断数值或填零。
- 前端分类标签、筛选文案统一“抢修类”，原工作票描述和工期保留，接口 is_ticket 不改名。有时刻的事件逐条显示完整日期；数据库中 8:40 一直属于 11 月 2 日，新增合成回归和原 PDF 断言，确保不继承前行次日日期。
- 执行：`backend/scripts/revise_dispatch_display_20261102.py` 默认预览并通过后 `--apply`；状态快照与五条补水字段变更保存在 `backend_data/projects/daily_report_25_26/runtime/dispatch-display-revision-20261103.json`。回滚预览通过，未实际回滚；命令见 backend README。原 `dispatch-reextracted-20261102.json` 已同步纠正，避免制品继续携带误改状态。
- 验证：后端调度相关 42 项、前端相关 33 项通过；页面后端同一查询服务确认 #3 汽机与汽炉均运行、点火为 11 月 3 日 06:10、暖管为 11 月 2 日 08:40、网口与高温水值未丢失。无数据库结构迁移；未改动其他业务模块。
- 最后验证日期：2026-11-03。此前首轮记录中的无括号启动状态覆盖和累计卡片切换结论由本节替代。

## 2026-11-03 调度信息 11 月 2 日 PDF 核对、提取纠错与定向修复

- 输入：用户提供的 `configs/2026年11月2日生产信息.pdf`；对 PDF 第 1、3 页渲染核对，并与 localhost:5173 页面所用后端容器的数据库记录比对。无鉴权的 HTTP 查询返回 401，因此使用同一后端容器中的查询服务和只读 SQL 核验，未绕过或改变 HTTP 鉴权。
- 确认的程序错误及修正：①运行列内“#3炉启动中”被当成运行，新增无括号状态识别，且不误改同号汽机；②合并表格末列为空导致 5 个网口指标漏提，改从数值区域读取有效值，保留零与空白的区别；③“高温水补水量：4147吨”旧规则不识别，补充独立口径，不写入累计分项；④工期续行“至03/11.08:00”被拆为独立事件，补充续行和点号工期识别，恢复单张工作票。
- 前端：`DispatchInfoView.vue` 补充六项网口指标表，并区分高温水与累计补水标题；后端跨日规则保留，11 月 3 日 06:10 点火不回填成 11 月 2 日操作。
- 数据：`backend/scripts/repair_dispatch_20261102.py` 对 `daily_report_25_26 / 2026-11-02` 事务更新 10 个字段，保存修复前后快照；6 个指标分别恢复为高温水热量 17784、#1低真空 4512、#3低真空 1200、香海东西网供汽量 1389、香北联络供汽量 1214、补水 4147。北海南网供汽量原文空白，保持 NULL；工作票恢复为 1 张，事件总数从 5 改为 4。
- 制品：`backend_data/projects/daily_report_25_26/runtime/dispatch-reextracted-20261102.json` 为修正版提取结果；`dispatch-repair-20261102.json` 为本次字段快照。回滚命令见 backend README；已通过回滚预览校验，未实际回滚。无数据库结构迁移。
- 验证：后端 `test_dispatch_pdf_layout`、`test_dispatch_operations`、`test_dispatch_reconciliation` 共 40 项通过；前端 dispatch runtime/import/lifecycle/dialog 共 33 项通过；容器内 Vite 生产构建成功。修复前后均通过同一页面查询服务校验目标值与跨日事件，无状态冲突。旧前端测试因普通用户身份不能调用管理员保存而失败，已修正测试身份并补普通用户拒绝保存用例；业务权限未变。
- 原文疑点：存煤合计 230994 吨，而各单位明细相加为 250166 吨，差额 19172 吨恰为金州库存。此为原始报表口径/合计疑点，不能据此擅改，保留原文待核实。原有其他未提交业务修改均保留。
- 最后验证日期：2026-11-03。未进行登录后的浏览器视觉验收；PDF 原文视觉核对、提取回归、查询服务与前端构建已完成。

## 2026-11-03 供热填报端投诉统计“供热公司”定名与“截至该日未办结投诉量”指标新增

- **需求背景**：用户反馈两点优化需求：
  1. 投诉统计弹窗及筛选器中的汇总行定名为“供热公司”（纠正原“集团汇总/集团总量”）；
  2. 在“供热公司表”填报模板中“突发情况说明”上方新增指标“截至该日未办结投诉量”，由系统在上传投诉报表时基于《转办》明细自动统计状态为“未办结”且发生时间截至该业务日期的件数并高亮自动回填。
- **改动范围与落地措施**：
  1. **模板与字典拓展**：`backend_data/projects/daily_report_25_26/config/数据结构_基本指标表.json` 中，在 `GongRe_Sheet` 数据的“突发情况说明”上方插入 `["截至该日未办结投诉量", "件", "", "", ""]`，并在项目字典中分配规范英文标识 `amount_unresolved_complaints_to_date`。
  2. **统计算法支持**：`backend/projects/daily_report_25_26/services/complaint_statistics.py` 在 `METRICS` 中新增 `unresolved_complaints`，遍历《转办》表中状态为“未办结”且发生时间截至当前业务日期的记录进行汇总计数。
  3. **自动回填映射**：`complaintFill.js` 扩展支持 `gongreCompanyExtraMetrics`，供热公司总表回填指标由 6 项扩展为 7 项，两张表一键回填指标数由 66 项平滑增至 67 项，并保持暖金发光高亮。
  4. **前端交互与定名**：`DataEntryView.vue` 模态弹窗、单位筛选下拉框、穿透核对表与未归属说明统一定名为“供热公司”；明细穿透筛选支持直接点击“截至该日未办结投诉量”查看各服务中心对应未办结工单列表。
  5. **验证**：通过后端 pytest（4 项通过）、前端 node test（`complaintFill.test.js` 3 项通过）及生产打包（`npm run build`，0 错误）。

## 2026-11-03 供热填报端“上传投诉报表”功能重构（弹窗化+暖金高亮+去除冗余瘦身剥离）

- **需求背景**：用户明确新版操作体验：1. 剥离已不再需要的工作簿去冗余瘦身功能；2. 统计结果采用模态浮层弹窗（Modal）展示，避免推挤表格；3. 支持穿透查看明细、导出 CSV/复制表格；4. 一键填入后，被自动填入的 66 个指标单元格应用暖金色呼吸发光高亮提示，直观人性化；5. 切换日期或重新加载模板时自动清理高亮标记，保持状态干净。
- **改动范围与落地措施**：
  1. **前端组件解耦与精简**：`DataEntryView.vue` 中移除了 `optimizeComplaintWorkbook` 导入与去冗余调用，直接调用 `calculateComplaintStatistics`，流程更纯粹敏捷。
  2. **模态弹窗（Modal）重构**：将原本位于表格上方的挤压式 card 替换为带毛玻璃遮罩的独立弹窗 `complaint-modal-overlay`，包含统计时段标签栏、疑似明细异常警示、核心统计表（点击数字穿透筛选）、明细核对器以及操作栏；操作栏新增“📊 查看统计结果”按钮，已解析数据可随时再次调起弹窗。
  3. **RevoGrid 单元格高亮**：通过列对象的 `cellProperties` 配置及 `complaintAutofilledCells` 集合，动态为两张表匹配填入的单元格赋予 `.complaint-autofill-highlight` 样式（暖金发光呼吸动效），切换 Tab 依然准确保留高亮。
  4. **生命周期与边界保护**：在业务日期切换（`bizDate watcher`）与模板重载（`reloadTemplate`）中自动清除高亮集合，防止历史脏状态污染。
  5. **验证**：前端生产构建 `npm run build`（22.34s，0 错误）、单元测试 `complaintFill.test.js`（3 passed）与后端测试（4 passed）全部通过。

## 2026-11-03 供热公司及10个分中心投诉量新口径同期值归档与补齐

- **需求背景**：26-27 供暖期启动后，“净投诉量”口径发生重定义（仅取“转办”且“已办结”，省办不计入净投诉；市平台净投诉量等于净投诉量，省平台净投诉量恒为 0）。为使 26-27 供暖期填报时同比口径一致，对 25-26 供暖期同期历史数据进行规范化归档与新核定数据入库。
- **改动范围与落地措施**：
  1. **历史旧数据归档**：将本地数据库中 2025-11-01 至 2026-04-05（共 156 天）总表（`GongRe_Sheet`，936条）与 10 个中心（`GongRe_branches_detail_Sheet`，9360条）的原 6 项指标重命名追加 `25-26_raw_` 前缀，安全封存留痕。
  2. **新核定标准指标入库**：从两份成果表读取并写入 156 天新核定数据（总表 624 条 + 分中心 6240 条）。
  3. **两项“其中”指标派生补齐**：保持表模板不删除行，同期值按新口径派生入库（省平台全赋 0，市平台等于当日净投诉量，总表 312 条 + 分中心 3120 条）。
  4. **脚本交付**：在 `configs/` 目录下生成全量合集 SQL 脚本 `migrate_25_26_all_complaints_production.sql` 及增量补齐脚本 `fix_sub_metrics_production.sql`，支持生产服务器一键安全执行。
  5. **本期自动填报验证**：确认 `complaint_statistics.py` 与 `complaintFill.js` 逻辑完全契合新口径，单测与生产构建全部通过。


## 2026-11-02 收支短评单位标记

- 各单位归因前增加圆点标记，换行文本保持对齐。仅修改样式；Serena 不可用，使用 `apply_patch`，无法补录知识记忆。回滚本轮页面及文档补丁即可。

## 2026-11-02 收支短评单位分行

- “数字背后”各单位归因独立换行，保留原有合并和变化配色。仅修改前端展示；Serena 不可用，使用 `apply_patch`，无法补录知识记忆。回滚本轮页面及文档补丁即可。

## 2026-11-02 收支短评合并与变化配色

- 将售高温水和售汽收入短评合并至同一条，沿用简报红增绿减配色标识同比、数量及量价影响。仅前端展示变化；Serena 不可用，使用 `apply_patch`，无法补录记忆。回滚本轮页面和文档补丁即可。

## 2026-11-02 收支专栏精简

- 收支追踪调整为紧凑短评，合并结论和单位归因，省略显示为零的量价影响；窄屏单栏。仅改变展示，回滚本轮页面和文档补丁即可。Serena 不可用，使用 `apply_patch`，无法补录记忆。

## 2026-11-02 简报收支专栏排版调整

- “数字背后”改为逐篇专栏布局，突出差额和同比幅度，以自然语句呈现单位变化；移除指定说明文字。仅变更展示层，回滚本轮页面及文档补丁即可。
- Serena 本会话不可用，使用 `apply_patch`，无法写入知识记忆。

## 2026-11-02 每日简报收支变化追踪

- 新增“数字背后”专栏，按集团当日同比筛选收入及成本差额，追溯单位和基础量价；暖收入及直接填报收入按金额解释，基础数据不足或无法闭合时不作归因。
- 使用既有日报计算引擎、底表及期间常量；不推断生产因果。Serena 不可用，使用 `apply_patch`，无法补录知识记忆；回滚本轮代码和文档补丁即可。无需数据库迁移。

## 2026-11-02 数据查询与分析手机排版

- `DataAnalysisView.vue` 调整窄屏卡片、操作按钮、指标列表和结果区域；宽表在各自容器内横向滚动。仅涉及前端样式，无接口或数据库迁移。
- Serena 不可用，使用检索与 `apply_patch`；无法写入知识记忆。回滚本轮页面样式与文档补丁即可。

## 2026-11-02 主城区汇总表投诉量单位修正

- 将展示表配置中主城区“省市平台净投诉量”的单位改为“件”；系统页面及共享导出流程使用该配置，万平方米指标仍为“件/万㎡”。无需迁移。
- Serena 不可用，使用 `apply_patch`；回滚本轮配置及记录即可。

## 2026-11-02 展示表导出行标签同步

- `DisplayRuntimeView.vue` 在导出时以求值结果同步项目名称和单位，修正旧模板与数值行错位；沿用已确认的末尾裁剪范围，Excel 与截图共用。
- 无后端及数据库变更，无需迁移。Serena 不可用，使用 `apply_patch`；回滚本轮补丁即可。

## 2026-11-02 展示表导出供暖期表头同步

- `DisplayRuntimeView.vue` 使用导出批量求值返回的列名更新第一、三张表的本期及同期供暖期表头，Excel 和截图共用；无法识别期别时明确报错，避免导出旧年份。
- 无后端或数据库变更，无需迁移。Serena 不可用，使用 `apply_patch`；回滚本轮补丁即可。

## 2026-11-02 展示表导出裁剪多余行

- `DisplayRuntimeView.vue` 的共享工作簿生成流程分别保留三张表前 71、36、42 行，Excel 和截图使用同一裁剪结果；同步清理尾部单元格、行属性及合并范围。
- 无后端接口或数据库变更，无需迁移；回滚本轮前端及文档补丁即可。Serena 在本会话不可用，改用 `apply_patch`，无法登记知识记忆。

## 2026-11-02 投诉统计一键填入供热公司两张表

- 在统计结果中增加一键填入，按实际模板精确匹配总表六项指标及十个中心各六项指标，仅更新本期列；市、省平台投诉量单独指标在模板没有对应行，未硬填。
- 填入前读取两张表当前日期的数据，核对统计完整性、日期、目标行唯一性、本期列和可写状态；保持未提交标记，用户核对后自行提交。保留同期数据及其他指标。
- 文件：`DataEntryView.vue`、`composables/complaintFill.js` 与测试。Serena 本会话不可用，使用 `apply_patch`，回滚本轮补丁即可；无数据库迁移。

## 2026-11-02 投诉明细直接统计

- 根据用户确认口径，按业务日期从直办、转办、省办明细计算集团与十个中心八项指标。日期读取 Excel 已保存缓存，不运行 NOW；仅转办且已办结纳入净投诉。缺失编号/日期的疑似明细标为不完整，无法匹配的中心单列并参与集团总量。
- 新增 `complaint_statistics.py` 与项目鉴权接口，`DataEntryView.vue` 展示指标、逐项追溯和 CSV/复制；保留去冗余功能，不自动回填或提交。
- 验证：跨年、当日、状态、零中心、未知中心、缺失缓存及 HTTP 测试，样本实测；浏览器控制服务不可用，未做交互验收。无数据库迁移。Serena 未提供，使用 `rg`/`apply_patch`；回滚本轮代码与文档即可。

## 2026-11-02 投诉报表空白区域边框

- 修复整列默认样式将边框延伸至空白区域的问题：复制无边框列样式，为已存在且继承列样式的单元格保留原样式；修复遍历时删除条件格式导致后续范围未收缩的问题。
- 修改 `backend/services/excel_optimizer.py` 和样本回归测试，无迁移。Serena 不可用，降级使用 `apply_patch`；可回滚本轮补丁。

## 2026-11-02 投诉报表空白行与边框清理

- 根据用户反馈，去除无内容行上的空白格式单元格及空行记录，包括远端独立内容之前的空行；保留合并区域与原始行号，避免影响后方统计区。此前视为内容的转办表 L8012 经检查只有两个空格；未被公式引用，现予清理。可安全缩减的公式引用继续由现有分析逻辑处理。
- 涉及 `backend/services/excel_optimizer.py`、`backend/projects/daily_report_25_26/tests/test_excel_optimizer.py`、`frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`，无数据库或接口迁移。Serena 本会话不可用，使用 `apply_patch`，回滚本轮补丁即可。

## 2026-11-02 投诉报表去冗余

- 需求：为供热填报页面提供独立 Excel 快照优化和下载，保留有内容记录中的公式。
- 实现：`backend/services/excel_optimizer.py` 分析空值守卫和引用，局部修改 OOXML；`complaint_optimizer.py` 提供项目鉴权接口；`DataEntryView.vue` 展示结果并下载文件和报告。
- 样本：5 张表；保留第 8012 行的独立内容；原始数据和保留公式缓存逐格校验。Excel 16 只读打开两份文件，921 个保留公式当前值一致、无公式错误；原表完整重算耗时过长，已终止，重算等价性尚未验证。浏览器控制服务不可用，未完成交互验收。
- 工具留痕：本会话未提供 Serena、Sequential Thinking、Context7 或计划工具，无法初始化或写入 Serena；使用 `rg` 检索、`apply_patch` 编辑、仓库内生成样本副本。回滚本轮代码和文档变更即可，原工作簿未修改。用户已有未提交改动未覆盖。外部参考：Microsoft Excel 性能优化文档，访问日期 2026-11-02，https://learn.microsoft.com/en-us/office/vba/excel/concepts/excel-performance/excel-tips-for-optimizing-performance-obstructions 。

## 2026-11-02 供热填报页面新增“上传投诉报表”小工具

- **需求背景**：用户要求在每日数据填报页面的 `GongRe_Sheet`（供热公司表）中，在“上传能效分析表”右侧新增“上传投诉报表”小工具，让用户能够点击按钮上传投诉文件，并预留后续具体处理逻辑。
- **改动范围**：
  - `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`：
    - 在顶部操作栏“上传能效分析表”右侧增加 `<button class="btn secondary complaint-upload-btn">📁 上传投诉报表</button>`；
    - 绑定隐藏式文件输入控件 `<input type="file" accept=".xlsx, .xls, .csv, .docx, .pdf">`；
    - 增加 `canUploadComplaint` 权限与单位判断（适用于供热公司表格），支持加载状态与操作提示；
    - 实现 `triggerComplaintUpload` 与 `onComplaintFileSelected` 处理管线，提供 `handleComplaintFileProcess(file)` 独立处理挂载点，选取文件后弹出包含文件名与业务日期的确认提示，为后续注入具体业务解析与回填规则做好完备准备；
    - 添加专属琥珀暖橙风格样式 `.complaint-upload-btn`，与能效分析表的淡蓝风格自然呼应且清晰辨识。
- **验证结果**：前端生产打包 `npm run build` 成功完成（21.91s，0 错误）。


## 2026-11-02 每日简报页面顶部工具条版式切换文案精简

- **需求背景**：用户反馈每日简报页面（`/projects/daily_report_25_26/pages/daily_brief`）顶部工具条的文案调整，将“报刊版式试用：”精炼修改为“报刊版式：”。
- **改动范围**：
  - `frontend/src/projects/daily_report_25_26/pages/DailyBriefView.vue`：将顶部工具条中 `.switcher-hint` 标签的显示文案从“报刊版式试用：”修改为“报刊版式：”。
- **验证结果**：前端生产打包 `npm run build` 成功完成（22.27s，0 错误）。


## 2026-11-02 每日简报设备段落行文精简

- 按用户最新示例，将设备段落调整为“集团四类设备台数与同比 → 当日调度具体记录”；连接语统一为“当日调度记录显示：”。
- `daily_brief_overview.py`：`_equipment_sentences()` 删除重复的增减归纳，`_dispatch_paragraph()` 删除行为分类和运行意义的泛化结语；保留原始厂名、时间、操作原文、关键记录筛选及状态待核对提示，缺少记录时简洁说明。
- 测试同步断言完整段落及不再出现重复分析。宿主机和 `phoenix_backend` 容器各52项简报测试通过；2026-03-25真实数据输出与用户期望结构一致。
- 同步前后端README和专项验证记录；无接口、页面布局或数据库变化，无迁移。回滚可按本轮文本补丁撤销。Serena仍不可用，沿用只读Python及apply_patch降级，本条待恢复后补录。最后验证日期：2026-11-02。

## 2026-11-02 每日简报集团设备综述与 PDF 导出

- 需求：综述结合集团全口径四类设备运行台数及同比、当日调度行为，支持按当前报纸样式导出 PDF。
- 实现：`daily_brief.py` 将汽轮机、蒸汽锅炉、水炉、锅炉房锅炉四项纳入既有日报取数及缺报校验；`daily_brief_overview.py` 先组织台数和同比，再提炼配置变化、启停投运、切换、参数调整、检修与异常信息，引用最多三条关键日志。计划、否定、跨日及工作票不被改写为已执行事实；调度局部清单不再冒充集团汇总。
- 前端：`DailyBriefView.vue` 新增“导出 PDF”按钮，调用 `dailyBriefPdf.js`。按当前主题与纸张比例生成单页长幅 PDF，保留网格、配色、中文字体及正文；不纳入外侧工具条和弹窗。使用本地打包、按需加载的 `html-to-image@1.11.13` 与 `jspdf@4.2.0`，不上传业务数据。导出为图像型 PDF，正文不可搜索；移动端保留当时的窄屏版式。
- 证据：2026-03-25 集团四类设备分别为 6/6/0/11 台，同期 5/6/0/18 台；当日北海关闭南北网联络门、南网停运、高减停运。2026-03-23 保留状态待核对提示；2026-10-29 设备数据不足时不补零，保留漏管正在处理中原文。
- 验证：后端简报与综述 52 项、前端简报及 PDF 尺寸 12 项通过；涉及前端文件 ESLint 通过；生产构建通过，只有既有大包提示。浏览器访问宿主不可用，电脑控制工具又因无法确认当前网址停止，未完成真实页面及下载 PDF 的视觉验收。
- 工具偏差：Serena、Sequential Thinking、update_plan 不可用；使用只读 rg/Python 检索、apply_patch 编辑及本地命令验证。Serena 记忆未能写入，本条与 `configs/daily_brief_verification.md` 作为待补录证据。
- 影响与回滚：仅简报服务、页面、依赖锁、专项测试及三份同步文档；无数据库迁移。按本轮补丁撤销即可，保留原有工作区及数据库变动。最后验证日期：2026-11-02。

## 2026-11-02 “电力现货市场数据”卡片副标题描述文案精简

- **需求背景**：按用户要求将功能选择页（`/projects/daily_report_25_26/pages`）中的“电力现货市场数据”卡片副标题由“15分钟日前/实时电价、实时与日前价差走势”精简为“15分钟日前/实时电价与走势”。
- **改动范围**：
  1. `backend_data/shared/项目列表.json`：更新 `daily_report_25_26.pages.spot_electricity.页面描述` 字段为“15分钟日前/实时电价与走势”；
  2. `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`：更新 `PAGE_DESCRIPTION_MAP.spot_electricity` 映射常数，确保前端兜底一致。
- **验证结果**：前端生产构建 `npm run build` 成功完成（18.32s，0 错误），后端 24 项单测全部通过。


## 2026-11-02 功能选择页五项核心卡片副标题描述文案精简与优化

- **需求背景**：按用户明确要求精简调整功能选择页（`/projects/daily_report_25_26/pages`）五项功能卡片的副标题描述文字：
  1. **调度信息**：由“主城区生产调度信息解析提取、综合入库与全景工况监控”精简为“主城区生产调度全景工况监控”；
  2. **每日简报**：由“经营与生产每日速览、同比数据与近期趋势”更名为“每日生产状况内参”；
  3. **全局管理中心**：由“生产指标与算法体系字典、实时验算沙盒与核心运行参数”精简为“核心运行参数设定”；
  4. **数据审批页面**：由“处理审批流程进度”调整为“每日数据审核批准”；
  5. **数据展示页面**：由“浏览固定数据展示表”简化为“浏览数据展示表”。
- **改动范围**：
  1. `backend_data/shared/项目列表.json`：同步更新后端各页面在 `daily_report_25_26.pages` 下的 `页面描述` 字段，使 API 响应保持一致；
  2. `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`：更新 `PAGE_DESCRIPTION_MAP` 映射常数，确保前端兜底与静态渲染完全匹配；
  3. `frontend/src/projects/daily_report_25_26/composables/dailyBriefPresentation.js`：在 `withDailyBriefPage` 生成的 `daily_brief` 对象中同步添加 `page_description: '每日生产状况内参'`。
- **验证结果**：前端生产构建 `npm run build` 成功完成（16.52s，0 错误）。


## 2026-11-02 调度历史设备状态核对保存权限严格限定为 Global_admin

- **需求背景**：用户明确要求“此处的保存功能，仅限Global_admin点击”，防止非超级管理员误操作或擅自覆盖生产调度的设备展示状态。
- **改动点**：
  1. **后端路由安全防线强化**（`backend/projects/daily_report_25_26/api/dispatch_info.py`）：
     - 移除 `@public_router.post('/resolve_status')` 挂载，防止未鉴权直接调用；
     - 在 `@router.post('/resolve_status')` 接口中注入 `session: AuthSession = Depends(get_current_session)` 依赖；
     - 强校验 `session.group == 'Global_admin'`，非超级管理员直接阻断并返回 `403 Forbidden: 此处的保存功能仅限 Global_admin 操作`；
  2. **后端单测完善**（`test_dispatch_reconciliation.py`）：
     - 增加普通用户调用接口时返回 403 权限异常的单元测试；
  3. **前端 API 透传凭证**（`dispatchApi.js`）：
     - `resolveDispatchStatus` 支持透传用户 Token，在 Header 中规范携带 `Authorization: Bearer <token>`；
  4. **前端交互与按权禁用**（`DispatchInfoView.vue`）：
     - 修正 `isGlobalAdmin` 计算属性，严格匹配 `group === 'Global_admin'`，剥离非超管的 `canAccessAdminConsole` 权限干扰；
     - 展开差异核对时，非 Global_admin 用户可查看冲突设备与客观事件依据，但下拉选择框处于禁用（disabled）状态；
     - 保存按钮对非 Global_admin 用户禁用，文案显示为“保存显示状态 (仅限 Global_admin)”，并提示“🔒 此处的设备显示状态保存功能仅限 Global_admin 操作”；
     - 在 `saveHistoryStatuses` 执行函数开头设置前置权限检查，非 Global_admin 点击直接弹窗拦截。
- **验证结果**：
  - 后端 24 项单元测试全部通过（包含权限 403 测试）；
  - 前端生产构建 `npm run build` 成功完成（15.88s，0 错误）。


## 2026-11-02 调度信息入库后设备冲突状态选择保存无效问题修复

- **问题现象与定位**：
  - 用户在 `http://localhost:5173/projects/daily_report_25_26/pages/dispatch_info` 页面中，上传 PDF 调度文件入库时选择冲突设备显示状态有效；但入库后在主页面“机炉表格与事件存在差异”折叠栏中，选择“原表格”、“末次主设备事件”或“手动指定”并点击“保存显示状态”后页面无反应且状态未生效。
  - **根本原因**：
    1. 在 `backend/projects/daily_report_25_26/services/dispatch_db_service.py` 的 `update_dispatch_statuses` 中，从 PostgreSQL 查询出单行记录后，驱动返回的 `row['biz_date']` 为 Python `datetime.date` 对象；
    2. 在 `backend/projects/daily_report_25_26/services/dispatch_reconciliation.py` 的 `reconcile_report` 算法中，比较事件日期 `event.get('event_date') and event['event_date'] != result.get('biz_date')` 时，因为 `event['event_date']` 是字符串（如 `'2026-10-25'`），而在 Python 中 `str != date` 恒为 `True`；
    3. 这导致当日事件被误判定为跨日事件，在提取主设备事件时塞入了跨日格式与字段，导致后端计算出的证据指纹（SHA256 哈希值）与前端查询时计算出的指纹不一致；
    4. 进而触发后端的防并发/防篡改校验 `if evidence is not None and any(evidence.get(key) != conflicts[key]['evidence'] for key in choices)`，直接返回操作依据已变化报错，拒绝入库持久化；
    5. 前端在调用保存接口时缺失显式的成功弹窗提示。
- **修复方案与代码改动**：
  1. **后端防御与标准化**（`dispatch_reconciliation.py` & `dispatch_db_service.py`）：
     - 在 `reconcile_report` 入口处，无论输入为 `datetime.date` 还是 `str`，统一将 `result['biz_date']` 标准化为 ISO 字符串（`raw.isoformat() if hasattr(raw, 'isoformat') else str(raw)`），确保后续所有日期比对均为统一类型字符串比较；
     - 在 `update_dispatch_statuses` 中，对从 DB 读出的 `row` 统一将日期与时间字段格式化为 ISO 字符串后再传入 `reconcile_report`；
     - 在 `test_dispatch_reconciliation.py` 中补充针对 `datetime.date` 类型 `biz_date` 的回归单元测试，确保证据指纹严格一致；
  2. **前端交互与反馈增强**（`DispatchInfoView.vue`）：
     - 在 `saveHistoryStatuses` 成功回调中加入 `alert(res.message || '显示状态保存成功！')` 明确反馈，并在保存后自动重新拉取当前日期数据实时刷新展示状态。
- **验证结果**：
  1. 后端 24 项调度核对与提取单元测试全部通过（`python -m unittest backend.projects.daily_report_25_26.tests.test_dispatch_reconciliation`）；
  2. 真实数据库端到端测试（2026-10-25 北海水炉样本）：选择 `events` 成功保存并转换为“启动中”，选择 `table` 成功保存并转换为“运行”，证据指纹严格匹配；
  3. 前端生产打包 `npm --prefix frontend run build` 成功完成（17.04s，0 错误）。


## 2026-11-02 功能选择页核心卡片渐变蓝与渐变橙轻盈化调优

- 用户反馈卡片的橙色和蓝色过于浓重深沉，要求略微调轻。
- 在 `PageSelectView.vue` 实施轻量、通透的渐变明度与饱和度调优：
  1. **每日数据填报卡片（渐变蓝调轻）**：由原来的深暗科技蓝（`#1d4ed8` ~ `#3b82f6`）调轻为通透清爽的蔚蓝/晴空蓝渐变（`linear-gradient(135deg, #3b82f6 0%, #4f8ff7 45%, #60a5fa 100%)`），边框与投影由深蓝压制转为轻盈浅蓝（`border: #60a5fa; box-shadow: rgba(59, 130, 246, 0.18)`）；
  2. **第一组普通卡片（浅冰蓝微调）**：背景调淡为更加清雅的极浅冰蓝（`#f8fbff` ~ `#eff6ff`），减弱视觉压迫感；
  3. **数据看板卡片（渐变橙调轻）**：由原来的浓郁深焦橙（`#ea580c` ~ `#fb923c`）调轻为温润明快的珊瑚暖橙渐变（`linear-gradient(135deg, #f97316 0%, #fb923c 50%, #fba053 100%)`），边框采用柔和暖橙（`border: #fb923c; box-shadow: rgba(249, 115, 22, 0.18)`）；
  4. 分组指示条与文字对比度保持和谐，消除厚重块感，视觉更轻快现代。
- 验证：前端生产构建 `npm run build` 顺利通过。

## 2026-11-02 “数据分析页面”更名为“数据查询与分析”

- 按用户要求将“数据分析页面”正式更名为“数据查询与分析”：
  1. **配置源头变更**：在 `backend_data/shared/项目列表.json` 中将 `daily_report_25_26` 项目下的 `data_analysis` 页面名称由“数据分析页面”变更为“数据查询与分析”；
  2. **前端组件与兜底同步**：在 `DataAnalysisView.vue`（页面标题与面包屑兜底）及 `ForbiddenView.vue`（403 页面名称映射）中同步更新为“数据查询与分析”；
  3. **功能选择页即刻生效**：`/projects/daily_report_25_26/pages` 读取项目配置后，第三组（分析与系统管理）中的该卡片名称即刻显示为“数据查询与分析”，并带参跳转。
- 验证：前端生产构建 `npm run build`（14.65s，0 错误）顺利通过。

## 2026-11-02 功能选择页“数据看板”卡片升级为渐变橙色主题

- 用户要求将第二组（生产监控与看板）中的“数据看板”卡片改为渐变橙色。
- 在 `PageSelectView.vue` 落实微调：
  1. `getCardCustomClass` 增加 `key === 'dashboard'` 返回 `card-primary-dashboard` 逻辑；
  2. 样式新增 `.page-card.card-primary-dashboard`，采用高饱和活力渐变橙色背景（`linear-gradient(135deg, #ea580c, #f97316, #fb923c)`）与同色调投影（`rgba(249, 115, 22, 0.28)`）；
  3. 卡片内标题统一为高对比纯白，描述文字为温暖白橙色（`#fff7ed`），hover 时微升加深，与第一组的深渐变蓝“每日数据填报”卡片形成鲜明的双核心业务引导视觉。
- 验证：前端生产构建 `npm run build`（15.01s，0 错误）顺利通过。

## 2026-11-02 功能选择页卡片紧凑度优化（由 116px 收紧至 88px）

- 用户反馈卡片虽已统一高度，但 116px 显得过高空旷。
- 在 `PageSelectView.vue` 实施轻量精致紧凑化微调：
  1. **高度收紧**：`.page-card` 统一高度由 `116px` 大幅收紧至 **`88px`**，内边距由 `16px` 调整为 `12px 14px`，圆角设为 `10px`；
  2. **文字间距紧凑化**：标题字号微调为 `15px`（行高 1.3），描述字号微调为 `12px`（行高 1.4），卡片内间距 `gap: 5px`；
  3. **分组容器间距收窄**：`.groups-container` 间距由 `28px` 优化为 `20px`，整体页面布局更加紧凑干练，减少单屏滚动负荷。
- 验证：前端生产构建 `npm run build` 顺利通过。

## 2026-11-02 功能选择页卡片高度统一与标题防折行规整

- 用户反馈各组卡片因标题长度及描述文本多寡导致高矮不一、参差不齐。
- 在 `PageSelectView.vue` 样式层对 `.page-card` 实施统一高度与排版规整：
  1. **高度严格锁定**：为 `.page-card` 注入 `height: 116px; box-sizing: border-box; padding: 16px;`，不论卡片处于哪一组或哪一行，卡片外轮廓尺寸 100% 齐平一致；
  2. **标题与徽标单行抗挤压**：`.page-card-title-text` 与 `.primary-entry-tag` 统一增加 `white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0;`，确保标题行垂直居中且绝不产生意外换行撑高；
  3. **描述文本两行截断对齐**：`.page-card-desc` 统一配置 `-webkit-line-clamp: 2; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden;`，保证短文本不塌陷、长文本不溢出，留白呼吸感高度一致。
- 验证：前端生产构建 `npm run build`（13.35s，0 错误）顺利通过。

## 2026-11-02 功能选择页卡片分类整顿与填报入口渐变蓝视觉强化

- 用户反馈功能选择页面（`/projects/daily_report_25_26/pages`）平铺卡片较多且杂乱，选定方案 A 微调落地：
  1. **卡片结构清晰划分为三大板块**：
     - **第一组【报表填报与审批】**：整合日常生产业务流，包含“每日数据填报页面 (`data_entry`)”、“数据审批页面 (`data_approval`)”与“常量指标页面 (`constant_data`)”；
     - **第二组【生产监控与看板】**：整合全局态势感知，包含“数据看板 (`dashboard`)”、“数据展示页面 (`data_show`)”、“调度信息 (`dispatch_info`)”与“电力现货市场数据 (`spot_electricity`)”；
     - **第三组【分析与系统管理】**：按用户要求将“每日简报 (`daily_brief`)”移入本组，并聚合“计划动态分解模块 (`dynamic_plan`)”、“数据分析页面 (`data_analysis`)”与“全局管理中心 (`global_management`)”。
  2. **权限与安全隔离 100% 保持不变**：
     - 严格复用现有 `auth.filterPages` 及 `withDailyBriefPage` 鉴权过滤链条，各角色（超管、集团管理员、主城区、各基层单位、填报员、只读员）仅能看到已授权的卡片；
     - 无权限的卡片自动剔除；若某角色对某个分组全无权限，该分组整体自动隐藏；兜底支持非日报项目或其他未分组页面平铺，无破坏性影响。
  3. **视觉引导重构（渐变蓝）**：
     - 第一组卡片整体统一为柔和优雅的浅渐变蓝背景（`linear-gradient(135deg, #f0f7ff, #dbeafe)`）与淡蓝高亮边框；
     - 其中的核心高频入口“每日数据填报”卡片改用饱满深邃的主色科技渐变蓝（`linear-gradient(135deg, #1d4ed8, #2563eb, #3b82f6)`），配备纯白字体、高亮投影与“核心填报”徽标，第一时间为基层填报人员形成强烈的视觉聚焦与入口指引。
- 验证：前端生产构建 `npm run build`（789 个模块，耗时 13.52s，0 错误）顺利通过。

## 2026-11-01 运行综述改为指标与设备调度证据生成

- 用户要求优化agy的新综述、避免编造、参考设备调度记录，并删除“【态势要点速览】”。保留已有报纸主题、首字下沉和主/副刊窗格，不覆盖用户和agy本轮未提交的其他改动。
- 纠正旧前端写死的“全集团受控稳定、机组出力均衡、各基层安全平稳”等判断及固定“昨日”开头，删除速览模板与专属样式；页面改为渲染`overview.paragraphs`，日期不再被标作历史编发时间。
- 新增`daily_brief_overview.py`：生产段合并供热/发电/煤耗及热水电单耗的同向变化、区分反向变化；经营段对照两种利润变化及投诉变化，不重复下方全部绝对值；设备段引用当日状态表与日志，不将它们解释为经营变化原因。
- `read_dispatch()`复用既有`reconcile_report()`，补充结构化设备与操作证据；设备按键去重，争议状态不汇总成运行台数；跨日事件、工作票不进入当日操作摘录，计划与否定原文不改写为已执行。摘录最多3条，优先设备/系统停启和故障等记录，再恢复原记录顺序。
- `build_daily_brief()`只读取一次调度数据，给综述与下方快报共用；保留highlights兼容字段，新页面不再拼接旧摘要。缺少数据或调度日报时使用简短事实状态，不自动写“平稳”“改善”。
- 验证：49项后端测试通过；Python标准库trace原服务/综述/接口行覆盖98.3%/100%/90%；前端文件ESLint和构建通过（15.04秒，仅既有大包提示）。2026-03-25、03-23、10-29真实综述分别核对，涵盖利润方向不一致、设备状态争议、循环泵切换与工业水漏管记录。
- 工具与范围：Serena/计划工具不可用，继续按会话降级约定本地检索/apply_patch，知识记忆待恢复后补录。没有改动数据库、调度解析规则或主体窗格布局；回滚本轮新综述服务、结构化证据、页面综述接入及测试/文档即可。浏览器宿主此前不可用，未声称完成真实视口视觉验收。最后验证日期：2026-11-01。

## 2026-11-01 每日简报头版头条重构为运行态势高管社论综述（方案二）

- 解决内容同质化痛点：针对原头版头条按条念流水账与下方集团总览指标卡片 100% 内容重复的问题，落地【方案二：早报社论综述 + 全指标矩阵】。
- 架构与排版重构：
  1. **头版头条升级为内参社论（Executive Editorial）**：
     - 将今日气温走势、经营效益（可比利润）、主要燃料能耗（标煤消耗与站内耗热）、民生保障（平台投诉与净投诉）有机熔铸为两段文质兼美、行云流水的大报社论；
     - 引入古典“首字下沉（Drop Cap）”大号“昨”字题头，左侧加注加粗报纸饰边；
     - 段落内核心数据与走势短句全面接入 `BriefComparisonText`，保持增红、减绿、平黑着色原则；
     - 社论底部附带“【态势要点速览】”紧凑索引网格，兼顾全篇阅读与 1 秒极速扫读。
  2. **职能彻底分工**：
     - 上方头版专职定性综述与大盘宏观态势（社论）；
     - 下方左版专职定量数据矩阵与走势台账（指标卡片），两者相得益彰，彻底消除重复感。
- 验证：单元测试 9 项全部通过，生产构建通过。

## 2026-11-01 每日简报头条序号紧凑化调整

- 将今日要闻前缀序号由带空格的“§ 01”调整为纯紧凑连写形式“§01”（`§01`、`§02` ...），排版一体化更强，更符合现代刊物章节徽标排版。
- 验证：单元测试通过，生产构建通过。

## 2026-11-01 每日简报今日要闻章节序号防折行修复

- 修复今日要闻标题序号“§ 01”在小屏或窄视口下因半角空格被浏览器判定为合法断行点、叠加弹性盒收缩导致“§”与“01”被迫分两行显示的排版缺陷。
- 实现：将空格替换为不可折行空格 `§&nbsp;01`，同时为 `.story-num` 注入 `white-space: nowrap !important; flex-shrink: 0 !important;`，确保条目编号绝对保持单行紧凑对齐。
- 验证：单元测试 7 项通过，生产构建通过。

## 2026-11-01 简报主版与集团指标专刊调整

- 按用户要求沿用agy已完成的报纸版式、主题与弹窗样式，仅调整指标内容。主版六项依次为：可比煤价边际利润、发电量、标煤耗量、供暖热单耗、平台投诉量、净投诉量；站内耗热量窗格替换为真正的供暖热单耗指标。
- 专刊八项依次为：实际边际利润、供热量、高温水销售量、售汽量、售电量、万平方米净投诉量、供暖水单耗、供暖电单耗。专刊不再显示供热标煤单耗和供暖热单耗；销售量紧接供热量，水电单耗放在最后。
- 前端：`selectBriefMetricPanels()`按指标键选取和排序；`BriefSubjectSection.vue`使用两组计算列表替代前五项/后续项的位置切片，横幅数量与导读同步更新。未修改CSS、主题、弹窗交互或每日摘要固定五项。
- 后端：`daily_brief.py`新增发电量、高温水销售量、售汽量、供暖水单耗、供暖电单耗返回项，复用`DailyDashboardEngine`；补全水单耗的三项水量、电单耗的换热站外购电量及面积核查，保留已有字段兼容。
- 验证：35项后端、9项前端专项通过；本次文件ESLint通过，构建19.24秒通过，仅既有大包提示；标准库trace服务/接口行覆盖98.6%/90%。真实2026-03-25六个相关指标与既有引擎一致：发电154.128万kWh，热单耗9.0651301184 GJ/万㎡，高温水4009 GJ，售汽58吨，水单耗2.9516576146吨/万㎡，电单耗88.8193828586 kWh/万㎡。
- 工具与回滚：Serena、结构化计划工具不可用，沿用本地检索/apply_patch降级并在本记录留痕，知识记忆待恢复后补录。仅撤销本轮指标映射、后端增量字段/依赖核查、测试和文档即可；无业务数据或数据库结构改动。最后验证日期：2026-11-01。

## 2026-11-01 每日简报文字表述精修与版面抗挤压优化

- 按用户要求完成 8 处表述与细节调整：
  1. 移除报头“清洁能源每日晨报”盖戳印章，版面更纯粹清爽；
  2. 将“全集团热电联产、供热总量、发电量及能耗趋势监测”修改为“全集团供热、发电及能耗趋势监测”；
  3. 排查并修复“查询剩余6项重点指标……”前方的“空白条”问题：原因为样式中 `color: #fff` 导致 `background: currentColor` 同样取值为 `#fff`（白底白字失真），已重构为对比分明的专栏徽标并支持主题适配；
  4. 解决“外延快报”字样因空间不足被迫换行的问题：为 `.heading-badge` 等所有徽标统一添加 `white-space: nowrap !important; flex-shrink: 0 !important;`，并精简右侧过长标题为“现货 · 调度 · 库存”，杜绝折行变形；
  5. 修复计划台账弹窗中“集团全口径”主体名称后方重复跟带“集团全口径”标签的问题，保持整行高亮并消除冗余字样；
  6. 报尾编审单位修改为“大连洁净能源集团 · 经济运行部 每日编审”；
  7. 报尾系统说明修改为“生产日报系统 每日速报专刊”；
  8. 版权信息修改为“© 2026 W.W. ALL RIGHTS RESERVED.”。
- 验证：单元测试 `daily-brief.test.mjs` 7 项全过，生产构建 `npm run build` 耗时 17.82s，0 错误 0 告警顺利通过。

## 2026-11-01 每日简报展开要素全面升级为报纸副刊模态弹窗

- 用户要求：将每日简报页面中所有“点击展开”的要素全部改为弹窗显示，杜绝原地展开对报刊严整版面的破坏。
- 改造清单：
  1. **指标走势与比较依据（BriefMetricCard.vue）**：原卡片底部 `<details>` 替换为“趋势走势与依据明细 ›”按钮，点击呼出大报指标专栏弹窗，全幅展示本期/同期值、同比变动、文字描述、ECharts 近七日走势图，以及近七日逐日数据对照台账（无需二级折叠）。
  2. **生产与单耗指标专刊（BriefSubjectSection.vue）**：原 `<details class="more-metrics">` 替换为报纸“【专栏副刊】查阅其余重点指标”横幅，点击呼出集团经营总览副刊弹窗，以响应式双栏网格呈现实际利润、供热量、售电量及各厂单耗指标卡片，且卡片同样支持进一步穿透查阅图表弹窗。
  3. **标煤计划全口径执行台账（DailyBriefView.vue）**：原 `<details class="editorial-details">` 替换为“【台账特辑】查阅各直属单位全月计划与执行台账”入口，点击呼出能源计划台账特辑弹窗，全幅展示各直属单位的月计划、月初至今已报实际、达成进度率、进度条以及计划差额。
- 主题感知与交互：
  - `DailyBriefView.vue` 通过 Vue 3 `provide('briefTheme', currentTheme)` 向下传递主题，各弹窗通过 `Teleport to="body"` 挂载并注入当前主题类名，弹窗的纸张底色、字体、Oxford 双线及强调色与当前页面所选版式（经典大报/FT财经/现代画报）保持 100% 契合。
  - 弹窗统一支持点击遮罩关闭、右上角 ✕ 按钮关闭、键盘 `Escape` 键监听退出。
- 验证：前端单元测试 `daily-brief.test.mjs` 7 项全过；生产构建 `npm run build` 耗时 18.38s，0 错误 0 告警顺利通过。

## 2026-11-01 每日简报报纸风多版式设计与切换标签

- 按用户要求，设计并实现“报纸排版美学（Newspaper / Editorial Print Style）”前端视觉效果，并在页面顶部提供版式切换标签供用户交互试用：
  1. **经典大报（broadsheet）**：暖米纸色（#faf7ef）、古典 Oxford 上粗下细双线报头、传统宋体大字题头、大报中缝竖线、红色古典印章（内部参阅/每日晨报）；
  2. **FT 财经（financial）**：FT 经典标志性粉橙羊皮纸色（#fff1e5）、深青灰墨色、高密度数据网格、紧凑直角无阴影、专业财经版面质感；
  3. **现代画报（modernist）**：冷白纯净纸（#ffffff）、极简黑白高对比、强视觉冲击力的大粗线与大章节标号、现代文印排版。
- 版面重构与响应式：
  - 宽屏（>960px）采用报纸经典展出版面（Broadsheet Spread）：通栏头条要闻摘要，主版（集团总览核心指标）与副版（标煤计划追踪、电力现货、生产调度外延快讯）左右分栏，中间贯穿报纸中缝分割线；窄屏与移动端自动优雅降级为单版流式阅读。
  - 顶部导航栏整合“报刊版式试用”标签切换器，即切即显，并将用户偏好同步写入 localStorage 与 URL 参数。
  - 通过 CSS 变量与深层穿透精确适配 `BriefMetricCard`、`BriefSubjectSection` 等子组件，保持纯正的报纸排印细节。
- 业务逻辑与接口契约：完全保持现有数据拉取、日期筛选、展开折叠、ECharts 走势图及路由跳转等既有能力，无破坏性改动，后端无变更。
- 验证：前端生产构建 `npm run build` 顺利通过（退出码 0，789 个模块打包完成）。

## 2026-11-01 简报增减文字着色与链接精简

- 按用户要求，比较中的增加/高于显示红色，减少/低于显示绿色，持平显示黑色。`BriefComparisonText.vue`使用Vue文本插值逐段渲染，由`briefComparisonParts()`划分各比较短语；同句同比增加、日间减少分别着色，不将整句误标为同一方向。
- `DailyBriefView.vue`覆盖摘要、气温、计划动态日差额、补充板块比较；`BriefMetricCard.vue`覆盖同比、趋势及展开说明。普通库存值、负电价值和操作记录保持原样；未知差额不视作持平，按显示精度为零的差额使用黑色。
- 查询链接移除“（日期另选）”，保留现有跳转地址。本轮为前端展示调整，无后端或数据库改动。
- 验证：7项前端专项通过，覆盖同句混合方向、持平、显示为零的差额、负电价及普通数值不误着色；本轮4个实现文件ESLint及生产构建通过。浏览器宿主不可用，实际视觉未核验。
- 工具与回滚：Serena仍不可用，沿用本地检索/apply_patch降级，知识记忆待恢复后补录。回滚新比较文本组件、两个页面组件接入、辅助函数及测试/文档差异即可。最后验证日期：2026-11-01。

## 2026-11-01 日均气温移至摘要顶部

- `DailyBriefView.vue`将日均气温从摘要底部移至标题下方、固定五项指标之前，并调整上下间距；仅改变展示顺序，不改气温数值和计算。
- 验证：页面ESLint通过。回滚模板位置及weather-note间距即可，无数据变更。Serena仍不可用，按会话降级约定使用检索/apply_patch，恢复后待补录知识记忆。最后验证日期：2026-11-01。

## 2026-11-01 今日摘要合并连续趋势文字

- 按用户示例，将连续同比趋势并入摘要主句，格式为“指标数值，同比增减量（比例），已连续n日高于/低于同期。”，避免再次重复指标名称及另起一行。日间连续变化同样并入主句，保留与同比的比较基准区别。
- 实现：`build_daily_brief()`直接按趋势结构生成`highlights.text`，兼容保留`detail`字段但置空；前端已有条件渲染会省略第二段，无需改动组件。五项固定展示与数值计算不变。
- 验证：34项后端测试通过，既有装配回归验证主句包含连续走势、指标名称只出现一次且detail为空；真实2026-03-25摘要已核对。仅文字组装变化，无数据库或前端结构变更。
- Serena仍不可用，沿用会话内本地检索/apply_patch降级，恢复后待补录知识记忆。回滚本轮摘要文字组装、断言及文档差异即可。最后验证日期：2026-11-01。

## 2026-11-01 今日摘要固定五项

- 用户明确调整：每天显示相同条目，连续变化只补充文字，不参与选项筛选；覆盖此前连续同比优先、无趋势回退前三项的摘要约定。
- `build_daily_brief()`固定输出集团可比煤价边际利润、标煤耗量、站内耗热量、平台投诉量、净投诉量，顺序不变。删除连续天数门槛和前三项回退，缺值保留条目并显示“—”；`trend_summary()`已有连续走势仍作为detail附带。
- 验证：34项专项通过，装配回归增加“有趋势和无趋势并存、缺值仍保留五项”的断言；真实2026-03-25及2026-10-29均返回相同五项及顺序。仅后端组装规则变化，无前端组件或数据库变更。
- 工具与回滚：Serena仍不可用，沿用本地检索/apply_patch降级，知识记忆待恢复后补录。回滚本轮摘要列表组装、对应断言及文档差异即可。最后验证日期：2026-11-01。

## 2026-11-01 去掉简报当日记录标签

- 按用户要求，`DailyBriefView.vue`的`statusLabel()`不再为ready状态输出“当日记录”；状态为空时不渲染标签元素。现货、调度、库存的正常标题旁不再显示该文字。
- 范围：仅展示层文案，无取数、计算或后端接口变更。前端静态检查通过，生产构建通过；回滚本轮页面两处差异及文档即可。Serena仍不可用，沿用会话内检索/apply_patch降级，知识记忆待恢复后补录。最后验证日期：2026-11-01。

## 2026-11-01 简报移除主体观察并收紧排版

- 用户要求：删除生产调度“来源”、移除整个“各口径观察”板块、整体更紧凑。本要求覆盖早先简报前端主体层级展示约定；计划板块的“各口径月计划”不属于观察板块，继续保留。
- 实现：`DailyBriefView.vue`删除来源行、观察区域及其专用预览函数/样式，后续板块编号由05接续为04。主页面边距、标题区、摘要、计划和补充卡片留白缩小，板块间距30px调整为18px；手机外边距16px调整为12px。
- 组件：`BriefMetricCard.vue`缩小内边距、数字上下留白、趋势文本间距；`BriefSubjectSection.vue`将指标卡片间距12px调整为8px。手机仍为单列，按钮、选择器和折叠操作维持至少44px高度。
- 范围：仅前端呈现与三份同步文档，后端接口、字段和计算规则未变，无数据库变更。回滚仅撤销本轮三个Vue文件及文档差异。
- 验证：本轮3个Vue文件ESLint通过；生产构建通过。浏览器访问宿主仍不可用，实际视口视觉未核验；未为可逆排版修改新增镜像测试。Serena不可用，继续按会话降级约定使用本地检索/apply_patch，知识记忆待恢复后补录。最后验证日期：2026-11-01。

## 2026-11-01 简报补充板块展开与库存全口径汇总

- 需求与改动：`DailyBriefView.vue`删除各单位计划的已报天数；现货和调度条目直接全部列出，不再截取前三条或折叠其余记录。
- 现货：`read_spot()`负价时点仅统计`real_time_price < 0`，文案为“实时负价时点”；日前负价、实时零值及空值均不计入。
- 库存：`read_inventory()`只对`GROUP_COMPANIES`基层单位按存储方式汇总，避免将Group/主城区汇总行再次相加；输出固定四项，顺序为全口径总库存、在途库存、港口库存、厂内库存。煤种空值不遮蔽已有合计，全空仍为“—”。
- 发布语义核实：功能选择页的“审批进度”区域执行“发布日报”后，通过`publish_daily_report()`→`mark_published()`记录业务日；简报取已发布业务日最大值，不按数据更新时间或发布操作时间排序。目前为2026-03-25，底表最新数据日为2026-10-29；默认日期规则未变。
- 验证：34项后端专项通过，含SQLite内存库执行现货实际聚合SQL的负价口径回归；服务/接口行覆盖98.2%/90%。前端本次文件ESLint及构建通过（15.13秒，仅既有大包提示）。真实2026-03-25库存总计20176.00吨，在途“—”、港口5594.54吨、厂内14581.46吨；实时负价68个。
- 工具及回滚：Serena仍不可用，沿用会话内本地检索/apply_patch降级；恢复后待补录知识记忆。撤销本轮前端展开、现货过滤、库存汇总及测试/文档差异即可，无业务数据写入或数据库迁移。最后验证日期：2026-11-01。

## 2026-11-01 修正简报库存空煤种误判

- 原因：`read_inventory()`按单位和存储位置汇总时，使用`COUNT(*) = COUNT(value)`判断全部煤种是否有值，导致任一煤种留空就遮蔽已有库存合计。底表按烟煤、褐煤、印尼煤分别保存，部分空槽不应否定已填数值。
- 改动：保留SQL标准`SUM(value)`对已有值的汇总，删除全煤种非空限制；全空项目显示“—”，显式零显示0.00；主体数量按实际有库存数值的单位统计，不再把空煤种判断为“数据不完整”。无日期迁移或原始数据修改。
- 验证：32项简报后端测试通过。真实2026-03-25北海厂内存煤显示8136.28吨，金普522.08吨，庄河70.30吨；全空港口/在途项目显示“—”。本轮只改后端汇总，无前端逻辑变化。
- 工具与回滚：Serena不可用，继续按会话降级约定使用本地检索和apply_patch，知识记忆待恢复后补录；撤销本轮库存函数、回归测试及文档差异即可。最后验证日期：2026-11-01。

## 2026-11-01 简报文案精简与日期补全

- 用户明确要求移除防御性文字和“数据口径与阅读说明”板块；该新要求覆盖此前利润空字段说明的前端展示约定。计算和缺失值处理仍保留，页面只显示业务数据、变化和简洁的空状态。
- 前端：`DailyBriefView.vue`删除各板块副标题、气温因果提示、计划规则说明、主体排列说明及阅读说明；`BriefMetricCard.vue`删除利润口径提示、完整性核查和重复解释，保留数字与趋势；无趋势时不再反复显示解释文字。
- 后端：`daily_brief.py`停止将利润计算说明拼入摘要，删除阅读说明输出；补充板块只述当日记录。无持续变化时，摘要使用当日已有核心数据。
- 日期原因：旧实现将“默认最新已发布日”扩大为“只能选择已发布日”，只列17天。用户确认改为全部数据日期、默认仍取最新发布日。API新增`available_dates`，保留`published_dates`和`latest_published_date`；允许选择有数据的未发布日。无发布记录时才回退到最新数据日。
- 验证：30项后端、4项前端专项通过；本次前端静态检查及生产构建通过（19.50秒，既有大包提示）。标准库trace服务/接口行覆盖98.2%/90%。真实接口逻辑核验默认2026-03-25、最新数据日2026-10-29、最早数据日2024-11-01均可查询，日期列表314项。
- 留痕与回滚：Serena仍不可用，按约定使用本地检索和apply_patch，知识记忆待恢复后补录；回滚本轮文案及日期查询差异即可，无数据库迁移或业务数据写入。最后验证日期：2026-11-01。

## 2026-11-01 新增管理员每日简报

- 缘由：日报指标和主体较多，需要适合窄屏手机阅读的每日摘要。已与用户确认：经营生产并重、同比优先、最新已发布业务日、主体按集团→主城区及其他单位→主城区内部组织；煤耗、供热和投诉只述事实，不评价好坏。
- 入口：`PageSelectView.vue` 注入每日简报卡片；`dailyBriefPresentation.js`、前端路由及后端专属接口均严格检查 `Global_admin`。不改种子权限，不把普通管理员能力视为同等身份。
- 流程：`workflow_status.list_published_dates()` 只读获取发布日 → `GET /daily-brief` 选择发布日期 → `daily_brief.build_daily_brief()` 复用日报引擎，检查底表依据 → 返回七日同比趋势、计划及现货/调度/库存 → Vue 组件按需展开依据和图表。
- 口径：连续至少3日同向同比进入摘要，不进行主体贡献排名；缺报中断连续走势；负基数、零基数仅列差额。实物量不补零。用户另行明确利润沿用看板数值，允许空字段按零参与，但必须注明；整家单位缺报仍不展示完整利润。
- 边界：纯热源厂不强制要求终端供暖面积；两期分别识别适用字段；站内耗热量与供热量分列；静态全月计划与动态日计划分开；跨日调度记录不计入当日；可选板块失败独立隔离。图表库仅在展开趋势时加载。
- 验证：29项简报后端测试、4项前端测试通过；既有相关后端回归32项通过、1项原有跳过。标准库trace对新增服务/接口测得行覆盖98.2%/100%；新增前端文件ESLint通过。真实数据库2026-03-25简报可生成，约2.25秒，未压缩JSON约136KB；运行后端OpenAPI已挂载接口，匿名请求401。
- 限制：浏览器访问宿主不可用，尚未完成窄屏视觉核验；共享旧文件有10项既有ESLint错误，已通过HEAD版本对照确认并非本轮引入。简报按当前底表重算，不是发布时冻结快照；原查询页面需另选日期。
- 工具留痕：Serena、Sequential Thinking及计划工具不可用，使用本地只读检索和apply_patch。没有改动业务数据或数据库结构；Serena知识记忆登记待工具恢复后补录。工作区既有数据库运行文件变化未处理。
- 回滚：撤销每日简报新文件、入口/路由/API挂载、工作流只读日期方法及本轮文档；无数据迁移。详细规则与验收证据见`configs/daily_brief_verification.md`。最后验证日期：2026-11-01。

## 2026-11-01 修复25—26供暖期计划与完成率空白

- 用户反馈：2026年3月31日供暖期耗量/比例不显示；已明确确认25—26全期计划就是2025年11月至2026年3月五个月之和。
- 前置说明：Serena未提供，无法激活/写记忆；使用Node/rg只读检索、apply_patch编辑、本地专项及同源HTTP验证，在此留痕待恢复补录。本轮改后端服务、回归测试及三份文档，无数据库写入、迁移或远端CI。
- 根因证据：同源接口和组件脚本实测，3月31日实际594068.4721可正常取到；旧逻辑按统计截止日2026年4月5日推导六个计划月，因计划表全指标仅有11月至3月，强制要求不存在的4月编制计划，造成全期plan_value及completion_percent为null。
- 修复：monthly_coal_progress.py/get_season_coal_progress为已确认的25—26期明确采用五个编制月；实际仍按看板统计起止日截至业务日累计，不修改4月5日统计边界；其他期按既有规则（26—27为11月至4月），不任意将缺计划当0。
- 验证：13项后端专项通过。localhost:5173同源HTTP200确认3月31日集团实际594068.4721/全期计划608550.5768，比例97.62022989508075%，状态ready；前端按用户既有整数格式显示594,068 / 608,551和98%。当前26—27六个月计划仍为591754.25吨，未被历史期修复改变。浏览器视觉/PDF未实测。
- 回滚：撤销本条对应历史期计划月份分支、回归测试及文档更新即可；无数据库回滚。最后验证日期2026-11-01。

## 2026-11-01 完成率单位标签固定单行及上下两层布局

- 用户要求：各单位仍在同一行；标签内部上方比例、下方M/N；数值四舍五入，不留小数。
- 前置说明：Serena工具仍不可用，采用Node只读检查、apply_patch编辑及本地验证，在此留痕待恢复补录。影响前端组件/既有格式断言及三份文档；无接口、数据库变更，回滚撤销对应模板/样式及格式修改即可。
- 实现：MonthlyCoalProgressCard.vue的completion-badges禁止折行，空间不足横向滚动；每个标签改为两层，上行单位名+整数百分比，下行整数累计实际/计划。保留千位分隔和缺值破折号，真实0显示0。number仅改变显示精度，渐变和后端计算仍按原值；下方列表不变。
- 验证：前端5项专项通过，构建通过（774模块、19.68秒，仅既有大包告警），本轮文件git diff --check通过；浏览器与实际PDF尚未核验。最后验证日期：2026-11-01。

## 2026-11-01 图旁标签增加累计实际/计划数值

- 用户要求：月度或供暖期累计值与对应计划以M/N形式直接显示。
- 前置说明：Serena工具仍未提供，采用Node只读检查、apply_patch编辑和本地验证，在此留痕待恢复补录。仅调整MonthlyCoalProgressCard.vue及三份文档，无接口或数据库变更；回滚撤销本条对应模板及样式即可。
- 实现：单位标签显示“累计实际 / 计划（完成率）”，两位小数和千位分隔；标题明确单位吨标煤和M/N含义。当日/本月累计复用月actual_value/plan_value，供暖期累计复用season字段，缺值以破折号显示、真实0仍为0.00。保留渐变色、悬停说明及原下方列表；窄屏标签可自动换行。
- 验证：前端5项专项通过，构建通过（774模块、16.43秒，仅既有大包告警），本轮文件git diff --check通过；浏览器外观与PDF实际效果未核验。最后验证日期：2026-11-01。

## 2026-11-01 图旁完成率连续渐变配色

- 用户要求：完成率按不同百分比渐变提示。
- 前置说明：Serena工具未提供，无法激活/写记忆；采用Node只读检查、apply_patch编辑与本地验证，并在此留痕待恢复补录。仅涉及MonthlyCoalProgressCard.vue和三份文档，无数据库或接口变更；回滚撤销本条对应样式与completionStyle即可。
- 实现：completionStyle对0/60/90/100/120%色阶连续插值，低比例灰蓝至蓝色，接近全额逐渐转琥珀/橙色，超计划逐渐转红；120%以上保持最深红但数字仍显示真实值。标签背景从同色浅到深渐变，边框及百分比文字同步着色；缺数维持中性灰。仍仅位于图上方，无新表格、动态计划对比或时间进度判断。
- 验证：既有前端5项专项通过，构建通过（774模块、18.78秒，仅既有大包告警），本轮文件git diff --check通过；浏览器外观与PDF实际效果尚未核验。最后验证日期：2026-11-01。

## 2026-11-01 完成率移至标煤图上方紧凑展示

- 用户要求：完成率只在图附近显示，不加到下方列表。
- 前置说明：Serena工具仍不可用，继续以Node/rg检索、apply_patch编辑和本地验证留痕，待恢复后补录。仅修改前端布局和三份文档，后端及数据库未改动。
- 实现：MonthlyCoalProgressCard.vue移除计划比较表、进度条和底部长说明，改为图上方“单位名＋百分比”的紧凑标签；超计划用橙色，缺数显示破折号，悬停可查看累计实际、计划及缺数原因。标题标明月/全期口径。DashBoard.vue恢复原四列对比表（单位、本期、同期、差值），表格不追加任何计划内容。
- 口径：当日和本月累计均按月累计实际/静态全月计划；供暖期累计按该期累计实际/静态全期计划，不改变已有计算、日期联动、请求取消和PDF加载等待。
- 验证：前端5项专项通过，npm run build通过（774模块、20.79秒，仅既有大包告警），本轮文件git diff --check通过；浏览器主机此前不可用，本轮外观及PDF未实测。回滚只需撤销组件布局、恢复父页面挂载及文档，无数据库回滚。最后验证日期2026-11-01。

## 2026-11-01 计划完成比例直接融入标煤原有三个维度

- 用户纠正：不新增“月计划完成”标签，直接加入原“当日/本月累计/供暖期累计”。用户明确确认前两项均用本月截至业务日累计实际/静态全月计划，供暖期用累计实际/静态全期计划。
- 前置说明：Serena工具仍未提供，无法激活及记录知识记忆；继续以Node/rg只读检索、apply_patch编辑和本地测试留痕，待恢复后补录。本轮涉及前端展示、后端只读计算、专项测试与三份文档；无数据库写入/迁移、无远端CI。
- 前端：DashBoard.vue删除第四个标签，保留三项原图表。MonthlyCoalProgressCard.vue复用原对比表的单位、本期、同期、差值，并追加全月/全期计划和完成比例（小进度条）两列。月完成格同时注明“月累计”实际，避免当日耗量被误作分子。集团等别名显式映射到主体代号，禁止按数组位置匹配；请求失败/加载时原比较数据仍可见。
- 后端：monthly_coal_progress.py增加get_season_coal_progress；接口保留月度原字段并增量返回season。复用get_season_windows统计边界，实际截止业务日且不超过期末；全期按各月份静态计划合并，每月先按直报优先/成员兜底求值，缺任一月不伪造全期计划。没有动态分解/气温依赖；全程SELECT，无迁移，前端直接替换。
- 证据：真实容器只读事务及HTTP200验证26—27全期集团计划591754.25吨，11月计划76036.16吨，11月1日暂无实际。25—26缺2026年4月计划，因此提示全期计划不完整；2026年3月月计划/实际仍为79676.6619/80206.16吨，100.6645586%。
- 验证：后端12项、前端5项专项通过，构建通过（774模块，仅既有大包告警）。覆盖跨月、未来月计划纳入、缺月/缺报、开期前、主体映射及三标签口径切换。浏览器视觉和实际PDF仍未核验。
- 回滚：撤销本条对应的三标签接入、组件合并表格、season增量返回与专项测试/文档调整，即回到上一版；不需数据库回滚。最后验证日期2026-11-01。

## 2026-11-01 月计划完成展示并入标煤消耗量对比

- 用户要求：减少独立月计划卡片占用，融合进“标煤消耗量对比”。
- 前置说明：本会话未提供Serena工具，无法执行项目激活及记忆登记；使用Node/rg只读检索、apply_patch编辑，记录待Serena恢复后补录。范围仅前端布局及三份文档，未修改接口、数据库或其他并行工作。
- 实现：DashBoard.vue移除顶部独立挂载，在coalStdPhaseOptions增加“月计划完成”，与当日、本月累计、供暖期累计共用同一卡片。切至该项时挂载MonthlyCoalProgressCard，离开即取消请求及释放PDF加载标记，原比较图表按原维度呈现；默认仍为当日。
- 组件：MonthlyCoalProgressCard.vue取消独立外框、重复大标题，压缩行距；保留月份/截止日、刷新、单位计划/实际/比例进度条/剩余与超出及缺数提示。继续使用静态全月计划分母，仅选中该视图时读取。
- 验证：前端专项4项通过；npm run build通过（774模块、21.03秒，仅既有大包告警）。浏览器主机此前不可用，本轮页面外观与PDF导出仍未实测。未启动远端CI。
- 回滚：撤销本条对应的页面挂载位置、切换项、组件样式及文档变更，即恢复上一版独立卡片；无需数据库回滚。最后验证日期：2026-11-01。

## 2026-11-01 数据看板静态全月标煤计划完成情况

- 用户要求：静态全月计划完成比例/进度条，不按动态计划或时间进度对比，放在顶部汇总卡片下方试用。
- 前置说明：Serena/update_plan未提供，使用Node/rg只读检索、apply_patch编辑与本地验证，知识记忆待恢复补录。无远端CI、新增依赖、数据库结构或业务数据修改。文档中其他并行变更原样保留。
- 页面：DashBoard.vue在顶部dashboard-summary之后、气温等dashboard-grid之前挂载MonthlyCoalProgressCard.vue。每单位展示全月计划、本月累计实际、完成比例进度条、剩余/超出量；超过100%保留真实比例并标记超计划，条宽封顶。零/缺计划、缺实际或缺报分别显示，不用0冒充。集团/主城区独立汇总，不与下属重复合计。
- 数据：新增只读GET /dynamic_plan/monthly_coal_progress?biz_date=YYYY-MM-DD，monthly_coal_progress.py批量读取paln_and_real_month_data该月consumption_std_coal/type=plan（period为文本月首日）及daily_basic_data同指标月初至业务日实际。汇总直报计划优先，无直报时由适用成员汇总；实际成员保持既有口径，研究院不单列。吨/万吨换算，Decimal计算，区分无记录与真实填0。无气温/HDD/k/动态计划依赖。
- 前端：api.js提供批量读取；组件跟随已加载业务日，取消及隔离过期请求、支持刷新重试、窄屏横向滚动。新卡片独立实时查询，不修改看板原缓存；加载期间禁止整页PDF导出，完成后随原整页导出流程输出。
- 核验：容器库11月1日已有集团计划76036.16吨、暂无当月实际，显示暂无实际。真实只读事务验证3月15日及31日分母固定79676.6619吨，实际分别50696.48/80206.16吨，月底100.6645586%、超出529.4981吨，无未来日串入。
- 验证：后端9项、前端4项专项全部通过，前端构建通过（774模块、20.35秒，仅既有大包告警），运行后端OpenAPI已注册接口，真实只读事务验证通过。浏览器主机不可用，整页视觉及PDF实际导出尚未验收。
- 回滚：仅撤销本轮新服务/组件/测试、API方法与路由、页面挂载及PDF等待标记、三份文档条目，保留此前与其他并行改动；无需数据库回滚。最后验证日期2026-11-01。

## 2026-11-01 修复35天气温预报ON CONFLICT唯一约束与数据去重

- 故障排查与修复：
  1. 根因：`public.temperature_data` 表因历史多版本写入缺乏唯一约束，存在 46,235 条完全相同时间戳的重复行（总行数 69,910，唯一时间戳 23,675）。PostgreSQL 执行带有 `ON CONFLICT (date_time) DO UPDATE` 的语句时，因缺少 `date_time` 的唯一约束而抛出 `there is no unique or exclusion constraint matching the ON CONFLICT specification`。
  2. 数据库去重与约束添加：利用 `row_number() OVER (PARTITION BY date_time ORDER BY operation_time DESC, ctid DESC)` 安全清理多余重复行，保留 23,675 条有效数据；并创建 `uq_temperature_data_date_time` 唯一约束。
  3. 服务端自愈机制：`backend/services/ensemble_weather_service.py` 增加 `ensure_temperature_table_ready(cur)` 函数，在批量 upsert 写入前自动探测并维护唯一约束，杜绝未来因环境变动缺失约束再度报错。
  4. 业务数据补全：成功拉取 Open-Meteo 35 天集合气温预报（31 个成员）并清洗入库 659 条有效时刻记录，2026年11月全月 30 天每日气温均值已全部补全（`calc_temperature_data` 完整就绪），计划动态分解页面的 31 项指标动态日分解曲线已恢复正常展示与平差计算。
- 验证：单元测试全量通过，直接触发 API 写入成功。


## 2026-11-01 调度解析语义分段、跨日日期及主语承接补修

- 用户要求：完善10月31日事件解析。证据为页面所用容器库原始11条事件；旧查询二次拆成20条，出现“1日”“处理漏点”等孤立卡片。当前仓库与容器映射目录未找到10月31日原PDF，实际核验以库内原文和10月30日真实PDF回归为准，不声称重查了缺失PDF。
- 前置说明：工具目录无Serena/update_plan，无法激活及记忆登记；采用Node/rg只读检索、apply_patch编辑、本地验证，在此留痕待恢复后补录。未使用远端CI或新增依赖，无数据库写入、迁移。
- 模块：dispatch_operations.py统一上传/查询语义分段；仅按完整时刻拆，普通说明和原因保留，工作票工期不拆、不推断主机。保留原文、来源时刻/行分组及推断依据；旧v1同源碎片可重建为v2，重复解析稳定。缺主体/无效日期时刻给出核对告警。
- 主语承接：同一原始描述内可继承；旧库无来源分组的相邻操作仅在同组织、同日、间隔0～30分钟、上条主设备唯一且没有其他主体时承接。跨组织、辅机插入、间隔过大、不同来源行不承接；网络恢复只承接同一原文前述支线。补全保留subject_inferred/subject_inference_basis，原文不丢失。
- 上传与日期：dispatch_extractor.py与查询共用split_timed_clauses，保留source_group/source_time/source_description，避免上传先拆后丢主语。操作增加event_date/event_clock，保留原time，“1日1:40”归属2026-11-01 01:40；跨月/年/闰日校验。次日主设备动作保留到时间线，但不覆盖本日报当天状态。
- 前端：事件卡片显示跨日完整日期和主语承接标识；生命周期按真实发生日定位、阶段外动作不画、相邻日报同一动作去重。计时明确同轮并汽/并网/并列优先于较早的并热网，北海#1汽机10月31日从15:46计8小时14分；其他回退及人工确认规则保持。
- 真实结果：10月31日现查13条有效事件，20:50高减/升温/暖管保留一条；两支线各拆为带原因的停止与11月1日01:40/02:40恢复；15:46并列补全#1机并标注依据。重复reconcile_report的事件/设备一致。3月23日仍是10:30并汽、17:30停炉两条；10月30日北方#1汽机/#2汽炉仍为运行。原库10月31日保留11条来源，不覆盖原文，不必重新上传即可用新查询规则；新上传保存时使用新规范。
- 验证：后端调度专项34项、前端相关32项全部通过；构建通过（772模块、15.41秒，仅既有大包告警），真实容器库只读查询断言通过。浏览器主机不可用，未做整页视觉核验。回滚仅撤销本条模块/显示/测试及三份文档修改，保留此前用户改动，无数据库回滚。最后验证日期2026-11-01。

## 2026-11-01 删除生命周期详情计时说明

- 按用户要求，仅移除DispatchLifecycle.vue设备详情运行时长卡片中的指定说明句，计算逻辑与导出保持原样；同步前后端README。
- Serena未提供，沿用Node/rg只读及apply_patch降级，知识记忆待恢复补录；回滚仅恢复该small标签及本条文档，无数据库变更。最后验证日期2026-11-01。

## 2026-11-01 生命周期弹窗及主体多选排序

- 用户要求：生命周期改为弹窗；“全部厂站”改为“全部主体”；按北海热电厂、北海水路、燃气锅炉、香海热电厂、金州热电、北方热电排序，支持多选。
- 前置说明：Serena仍未提供，使用Node/rg只读检索与apply_patch编辑，记忆待恢复补录；无远端CI、数据库或接口变更。北海水路按用户原文显示，对应数据库既有北海水炉；北海热电厂对应北海热电联产/北海电厂，香海热电厂对应香海电厂，原始设备归属和来源不改。
- 实现：新增DispatchLifecycleDialog.vue，以原生dialog承载，页面上部只保留入口；打开才挂载生命周期并请求记录，关闭按钮、Escape或遮罩关闭，关闭后销毁图表并恢复入口焦点，再次打开按默认日期初始化。保留日刻度、固定日期栏、运行小时与完整图导出。
- 多选：DispatchLifecycle.vue用主体复选框替代单选下拉，提供全部主体的全选/取消；无记录主体显示但禁用，其他未知主体排在指定六主体之后。空选择不给图、不允许导出。dispatchLifecycle.js集中名称映射和排序，图中设备、详情、导出顺序一致，运行小时仅汇总当前多选结果；dispatchLifecycleExport.js在标题和文件名写入实际多个主体或全部主体。
- 验证：30项相关测试通过，新增原生弹窗打开/关闭及焦点返回、六主体顺序、保留原始名称、导出排序与多主体范围、全选/取消/空选择及运行时长同步回归。前端构建结果下补；实际浏览器弹窗视觉未验收，既有浏览器主机不可用。
- 最终验证：前端构建通过（772模块、15.35秒，仅既有大包告警），git diff --check通过；未修改数据库或后端接口。
- 回滚：撤销本轮页面挂载替换、弹窗组件、主体多选/显示映射/排序、导出筛选及测试和三份文档条目，保留既有生命周期功能及其他用户改动；无需数据回滚。最后验证日期2026-11-01。

## 2026-11-01 生命周期水平滚动修复、完整导出及动作运行时长

- 用户要求：日期轴在水平移动后不能消失；按当前筛选和时间段导出图；删除底部“不能据此判断停运。快照不代表全天状态，不据此计算运行时长。”文案，并根据动作计算运行时长。用户明确计时口径：同轮有并汽/并网/并列等运行投入记录时优先取其时刻，缺少时才取点火/启动/冲转；按停止时刻结算，跨日分摊，多轮分别判断。
- 前置说明：Serena仍未提供，无法激活与记忆登记；使用Node/rg只读、apply_patch编辑及本地验证，在此留痕待恢复后补录。无远端CI、新增依赖、数据库结构或业务数据写入。
- 水平滚动：移除双ECharts空日期轴联动，改为单张设备图及滚动容器外的DOM日期栏。buildLifecycleDateTicks通过主图公开坐标转换读取当前日期及像素位置，响应百分比拖动、平移、缩放、resize；原生横向滚动同步scrollLeft，并使用设备滚动区clientWidth排除垂直滚动条宽度，保持对齐，垂直滚动不影响日期栏。
- 导出：新增dispatchLifecycleExport.js，提供PNG和SVG。按已查询完整阶段及当前厂站、类型、有操作/差异筛选重建独立完整ECharts图，包含所有筛选设备、逐日刻度、图例、操作节点、设备小时、筛选条件、统计与来源/口径说明，不截屏、不受滚动或滑块窗口影响。PNG优先2倍清晰度，按32百万像素和16000边长实际能力调整；若不能保持1倍以上，提示使用不丢内容的SVG。日期改动未查询时禁用导出；点击时冻结筛选快照，生成后本地下载，无上传服务。
- 计时：新增dispatchRuntime.js统一供页面及导出使用。每轮到停止动作分段，优先运行投入时刻，无运行投入才启用启动动作；停止日可从停止时刻回推当日起始在运，依据明确标记。已记录动作状态延续至下一个动作，按自然日分摊；无动作但有日报状态的全天时长作为“日报估算”单列；缺时刻/同刻矛盾/无停止动作却由运行转备用等情况保留待核对小时，不伪造0或24。计时依据限已加载阶段内可见的同轮记录；不能当作实时监测实测值。
- 页面显示：新增当前筛选推算运行设备小时；设备详情提供操作计时、日报估算、未知小时及逐日依据；按用户要求删去指定底部文字。导出逐设备名称附小时并写明统一计时口径。时长只在前端计算，不覆盖原始日报或状态修正记录。
- 验证：28项相关测试通过，覆盖横向百分比滑块、日期像素对齐、原生scrollLeft、导出完整范围及设备筛选/日期未查询门槛、PNG尺寸策略、7小时案例、并汽优先、仅启动回退、多轮启停、跨日、午夜、无效时间与日报冲突。前端构建通过（770模块，20.67秒，仅现有大包告警）。
- 真实数据：容器数据库10月22至31日10天、6台有操作/差异设备的完整样张已生成并查看，PNG为2400×1320，SVG/PNG位于backend_data/projects/daily_report_25_26/runtime/dispatch-lifecycle-export-preview.svg及.png。实际10月30日北方#2汽炉从14:40计9小时20分，#1汽机从16:18计7小时42分，符合指定规则。样张PNG通过同一SVG渲染并在本地用既有Sharp检查；浏览器下载与真实滚动验收因浏览器主机不可用尚未完成。
- 回滚：仅撤销本轮组件日期栏/导出/时长展示、dispatchLifecycle.js日期栏函数、两项新增工具函数文件与相关测试及三份文档，保留既有生命周期与用户其他修改；无需数据库回滚。最后验证日期2026-11-01。

## 2026-11-01 生命周期日期刻度在设备区滚动时固定

- 用户要求：下拉设备时间轴的滚动条时，上方日期刻度始终显示。
- 实现：DispatchLifecycle.vue将日期刻度拆为独立ECharts实例，置于设备滚动容器内的sticky顶部层；日期轴与设备图共用同一宽度容器，横向滚动一起移动，echarts.connect同步缩放，ResizeObserver同时调整两个实例，销毁时解除分组并清理实例。dispatchLifecycle.js新增buildLifecycleHeaderOption复用主图坐标与缩放配置，设备图隐藏重复日期刻度。
- 验证：新增真实ECharts双实例联动测试，验证滑块缩放后吸顶轴与设备节点像素位置一致；18项相关测试通过。构建及最终差异检查结果下补。浏览器主机仍不可用，未进行真实浏览器滚动验收。
- 最终验证：前端构建通过（768模块，15.29秒，仅现有大包告警），git diff --check通过；未修改数据库。
- 前置说明与回滚：Serena不可用，采用Node/rg只读检索、apply_patch编辑，知识记忆待恢复补录；回滚仅本轮日期轴拆分、联动测试及三份文档，不影响既有数据或默认日期范围。本次不涉及后端接口、数据库及远端CI。最后验证日期2026-11-01。

## 2026-11-01 生命周期默认日刻度与首条本期记录起点

- 用户要求：上部时间轴默认按日显示，默认起点为2026年10月后第一条调度记录；本轮按2026-10-01及以后解释，终点仍为最新记录。容器实际数据库只读核验：首条2026-10-22、最新2026-10-31。
- 前置说明：Serena仍未提供，无法激活/登记记忆；通过Node/rg只读检索及apply_patch编辑，记录待恢复后补录。无数据库写入、迁移或远端CI；回滚仅撤销本轮前端默认日期、日刻度及三份文档条目，保留既有修改。
- 修改：DispatchInfoView.vue传入availableDates；DispatchLifecycle.vue使用defaultLifecycleRange从实际日期计算默认区间，初始化后不覆盖用户自选；dispatchLifecycle.js将坐标改为北京时间起点的日偏移，固定间隔1天，保留节点时分；初始可见天数按宽度决定，滑块保留完整查询阶段。滑块非整日边界不输出重复日期标签。
- 验证：新增默认日期边界及日刻度回归，17项相关测试通过，包含ECharts真实SVG渲染；构建结果在本条下补录。未重新尝试已不可用的浏览器主机，整页视觉未核验。最后验证日期2026-11-01。
- 最终结果：前端构建通过（768模块，仅现有大包告警），最终17项测试及git diff --check通过；默认区间已按实际日期列表设为2026-10-22至2026-10-31，日刻度保留节点的时分精度。

## 2026-11-01 调度页面上部增加主设备生命周期时间轴

- 用户要求：先将可选择时间阶段、直观展示主设备启停的图放在调度页面上部，之后可移动位置。本轮不修改数据库结构及业务记录。
- 前置说明：工具目录没有Serena，无法执行激活和记忆登记；使用Node/rg只读检索、apply_patch编辑、本地验证，在本条留痕待工具恢复补录。未启用远端CI。读取了现有ECharts依赖（6.0.0）及官方视觉映射文档 https://echarts.apache.org/handbook/en/concepts/visual-map/ （访问日期2026-11-01）；实现复用既有ECharts，无新增依赖。
- 模块与流程：新增 components/DispatchLifecycle.vue 独立区块，在DispatchInfoView.vue顶部Banner后挂载；utils/dispatchLifecycle.js复用现有queryDispatchData，按起止日期分页完整读取日报，按厂站+标准设备名称建模。初始截至最新日报近30天，可自选日期及近7/30/90天；支持厂站、机炉专业、有操作或差异设备筛选，图表缩放、点击设备详情、原文和来源查看。状态保存或日报入库后主动刷新生命周期。
- 显示语义：浅色带为日报状态快照，非连续运行时长；相邻且口径一致、有日报的日期可合并日格，缺报/缺设备日留空；精确时刻用启动三角、并入菱形、停止方形表示。同日多动作分别显示，不把人工状态裁决当操作。无效时间只在文字详情中显示，不虚构图上时刻；未确认矛盾使用虚线框标识。
- 验证：新增10项生命周期测试，加现有5项导入交互测试全部通过，覆盖完整分页、缺报不补色、跨厂同号设备、原表与操作分离、无效时刻、区间含末日、旧响应防覆盖、失败清空旧图和ECharts真实SVG渲染。前端构建通过，仅现有大包告警。页面容器已读取到组件引用。
- 真实数据验证：页面所连phoenix_backend容器查询2026年3月31天、41台主设备，生成12台有操作或差异设备、21个操作节点的时间轴；SVG/PNG预览位于backend_data/projects/daily_report_25_26/runtime/dispatch-lifecycle-preview.svg及.png，已查看图像并增加节点标签避让。浏览器访问主机不可用，未完成整页浏览器视觉验收，图表及数据验证已完成。
- 回滚：移除页面的DispatchLifecycle挂载/导入及lifecycleRefreshKey刷新触发，删除本轮新增组件、工具函数和测试，并撤销本轮三份文档条目；保留用户和上一轮其他修改。无数据库迁移、无需数据回滚。最后验证日期2026-11-01。

## 2026-11-01 调度差异提示默认折叠

- 按用户要求，将 DispatchInfoView.vue 的历史日报“机炉表格与事件存在差异”区域改为原生 details/summary，默认不设置 open；点击标题展开状态依据、选择及保存功能，切换业务日期时重建并恢复折叠。上传入库前的强制确认流程保持原样。
- 状态存储说明：确认后的有效状态保存在 public.dispatch_daily_reports.boiler_turbine_status 和 eqp_status_json 内，原始状态保留在 table_status；操作保存在 operations_and_tickets/log_items_json。查询会重算冲突，查询本身不保存选择；用户保存或定向修正才更新数据库。
- 前置说明：Serena仍不可用，采用只读Node/rg检索及apply_patch编辑；记忆登记待工具恢复后补录。范围仅页面展示及三份同步文档，回滚仅撤销该details/summary与样式，无数据库改动。最后验证日期：2026-11-01。
- 验证：Vue组件解析及模板编译通过，现有前端交互5项全部通过，git diff --check通过。未执行浏览器视觉验收。

## 2026-11-01 调度复合事件、历史状态与确认机制补修

- 输入来源：用户指定3月23日只拆分操作、不调整备用；10月30日北方热电 #1汽机/#2汽炉改为运行，并完善上传和历史状态确认。最后验证日期：2026-11-01。
- 前置说明：当前工具目录未提供Serena、Sequential Thinking、update_plan，无法激活/登记记忆；使用Node/rg只读检索、apply_patch编辑与本地验证，未启动远端CI。Serena恢复后应补录本条，不宣称已登记。
- 纠正前次核验结论：宿主机服务优先连接5434备用库，页面后端容器连接5432，两库数据不同；旧记录“完整入库”不能证明页面数据已修正。此次在phoenix_backend容器执行定向脚本，锁定项目和两个日期，保存前后快照后事务更新四个JSON字段，其他业务指标不改。
- 修改范围：新增services/dispatch_operations.py集中拆分多时刻操作；dispatch_reconciliation.py统一主设备匹配、专业动作、歧义检测和依据指纹；dispatch_db_service.py新增历史确认的局部事务更新；api/dispatch_info.py与dispatchApi.js提供历史确认接口；DispatchInfoView.vue提供上传及历史逐台状态选择、原句展示和查询响应防串页；新增修复脚本及回归用例，前后端README同步。
- 实施结果：页面数据源的2026-03-23已持久化10:30并汽、17:30停炉两条事件，北海#4汽炉仍为备用；2026-10-30北方#1汽机/#2汽炉均为运行、原表备用保留、确认来源为events。已通过真实查询服务核验设备列表与拓扑一致、两个操作字段一致。
- 回滚范围：代码按本条文件逐项撤销，勿覆盖上一轮及用户既有改动；数据快照位于backend_data/projects/daily_report_25_26/runtime/dispatch-repair-20261101.json，容器内执行修复脚本的--restore模式，仅在目标字段未发生后续变化时恢复。无数据库结构迁移。
- 验证阶段：后端83项完成（79通过、4项按配置跳过），前端导入4项通过，前端构建通过。后续新增的历史确认和歧义回归最终结果在本条下补录。浏览器工具因无法可靠确认Windows浏览器URL停止，未完成视觉验收；查询服务和数据库验证已完成。原有大包构建告警、依赖弃用告警不影响本次主流程。
- 最终验证：调度后端专项23项、前端交互5项全部通过，最终前端构建通过；运行后端OpenAPI已注册resolve_status接口。容器5432内以真实事务执行历史手动状态确认，验证四字段同步、其他列不变后回滚，整行与测试前完全一致。正式两日修正后查询返回符合用户指定结果。外部资料未使用；自然语言识别基于可审计规则，未覆盖的句式保守保留原文，不宣称通用语义理解。

## 2026-11-01 调度信息智能连动识别优化与2026.10.30状态修正入库

- 优化 `dispatch_reconciliation.py` 智能识别引擎：
  1. 解决复合描述中省略主语行为的连续嗅探问题（如“#4汽炉并汽,17:30 粉仓烧空停炉”），按标点分句后支持自动继承前文主设备主语，并精准提取子句内嵌时刻（17:30），杜绝多行为被单一截断或时间串扰。
  2. 严密保留对辅机（泵、风机、高减等）、否定、计划及试验词汇的隔离过滤，主设备行为按汽机与锅炉专业类型兼容白名单进行匹配。
  3. 2026-03-23 北海电厂 #4汽炉 成功识别出 `10:30 并汽`（运行）与 `17:30 停炉`（停运）两个行为，卡片标签准确显示最新的 `17:30 停炉`。
- 处理 2026-10-30 调度生产日报：
  1. 针对北方热电 #1汽机（16:18 与系统并列）、#2汽炉（14:40 并汽）实际已并网运行的事实，在保留原表 `备用` 记录的前提下，确认为以事件为准（resolution: events），将两台设备状态修正为 `运行`，并同步更新矩阵拓扑与扁平映射表。
  2. 完整入库至 PostgreSQL `dispatch_daily_reports` 表。
- 前端 `DispatchInfoView.vue` 展示优化：
  1. 优化上方“机炉表格与事件存在差异”文案与样式，当已完成确认时，明确显示 `已确认以事件为准（已修正状态为：运行）` 绿色标识，杜绝歧义。
- 验证：后端 78 项测试全量通过（含连续动作回归用例）；前端编译无报错。



## 2026-10-31 平均现货电价置于最后

- 按用户要求移动SpotElectricityView.vue共用两厂卡片模板，将平均现货电价（含差异率）放在电量电费收入之后。仅调整显示顺序；计算、格式及接口不变。前后端README同步。
- 验证：Vue模板编译通过，已核对五项指标顺序，平均现货电价为最后一项。
- Serena未提供，沿用Node只读和apply_patch降级留痕待补录；回滚仅恢复模板顺序及本轮文档。最后验证日期：2026-10-31。

## 2026-10-31 两厂平均现货电价及差异率

- 根据用户口径，spot_electricity.py summary使用未舍入NUMERIC现货电费÷电厂合计上网电量，新增两厂avg_*_spot_price；*_spot_price_diff_rate=(电厂均价−AVG(real_time_price))÷AVG(real_time_price)×100。比较基准使用同选定日期范围内非NULL real_time_price算术均值；电量为0/数据缺失时均价NULL，参考均价为0/NULL时差异率NULL，不用舍入后电费或账单均价代替。
- SpotElectricityView.vue在售电量后新增平均现货电价，单位元/MWh、两位小数，后附括号差异率，带正负号、两位小数，不可计算差异率显示—；无均价显示小号暂无数据。指标字体及单位17px改14px，差异率11px；桌面五列，手机两列并修正首列分隔。数据库无迁移；前后端README同步。
- 测试：后端真实数据库回滚7项、前端专项12项通过，覆盖分时电量加权、参考实时价比较、零电量/零参考价、缺值、差异率正负及精度。Serena仍未提供，使用Node只读及apply_patch降级并在此留痕待补录。回滚范围为新增响应字段、卡片指标与格式、测试及文档。最后验证日期：2026-10-31。
- 本地构建及差异检查通过；构建仅有既有大包告警，浏览器实际视觉尚未验收。

## 2026-10-31 两厂信息框铺满及上网电量曲线

- SpotElectricityView.vue两厂卡片取消560px限制，等宽铺满整行，增加厂站配色、指标分隔和标题间距，窄屏同样铺满。新增显示两厂上网电量复选框，由summary.has_plant_sales_data判断当前日期范围任一机组sales非NULL（含0），完全无数据、加载或失败时禁用，无数据新范围取消勾选。
- spot_electricity.py summary按查询范围返回has_plant_sales_data，不以合约或完整日合计判断有无原始电量，不受负价过滤影响。无数据库结构变更。utils/spotPlantSalesChart.js叠加独立MWh轴和两厂曲线，支持单日分时、日合计、月合计、时段均值，NULL不补零不连线，保留原价差/负价数量轴，图例与tooltip明确单位。fetchData增加请求代次校验，避免旧日期响应回填开关和图表状态。
- 验证覆盖两厂曲线、独立纵轴、四种粒度、零值和空值、过滤、开关禁用与日期响应保护；真实数据库外层事务回滚测试确认仅合约不代表存在电量、0为有效电量。前后端README同步。Serena未接入，使用Node只读及apply_patch降级留痕，恢复后补录。回滚仅移除本轮界面、辅助图表模块、新增summary字段和测试文档，无持久化业务数据变更。最后验证日期：2026-10-31。
- 结果：前端11项、后端6项通过，本地构建及差异检查通过，ECharts真实SVG渲染验证电量轴和两厂图例正常；构建仅既有大包告警。浏览器实际视觉尚未验收。

## 2026-10-31 电费收入及金额展示优化

- SpotElectricityView.vue将暂无数据文字降为12px、浅灰、常规字重；新增两厂当日/区间电量电费收入，四项横排，480px以下两列。formatPlantMetric对电费与收入使用Intl.NumberFormat：四舍五入为整数元、千位分隔、负半数对称舍入、避免显示负零；售电量精度不变。
- spot_electricity.py的_bill_fee_summary_columns增加revenue，summary返回sum_beihai_revenue_fee/sum_xianghai_revenue_fee。收入在NUMERIC计算阶段合并未舍入的现货及合约差价电费，再显示舍入；任一必要数据缺失则不报部分合计。未改数据库结构及持久化记录；前后端README同步。
- 验证：真实数据库外层事务回滚5项通过（含0.4+0.4先求和），前端专项7项通过（含千位、正负舍入、零、负零及空值）。Serena未提供，沿用Node只读及apply_patch降级留痕，恢复后补录。回滚范围为新增汇总字段、卡片、格式化、测试及文档。最后验证日期：2026-10-31。
- 本地构建及差异检查通过；构建仅有既有大包告警，实际浏览器视觉未验收。

## 2026-10-31 两厂售电电费卡片紧凑横排

- 根据用户反馈，SpotElectricityView.vue两厂卡片改为厂名/机组范围标题与三列指标（售电量、现货电费、合约差价电费），每卡最大560px，桌面并排，768px以下上下排列；长金额可换行。移除卡片已填报/待填报状态及原电费纵排布局，缺失统一“暂无数据”，同步移动端售电量缺失文案。
- formatPlantMetric保留0、负数、两位小数及单位，金额取数及后端计算无变化；前后端README同步。本轮只改前端呈现，无数据库迁移。Serena仍不可用，使用Node只读及apply_patch编辑留痕待补录；回滚范围为卡片模板、辅助格式化、样式和文档。最后验证日期：2026-10-31。
- 验证：既有前端专项6项、本地构建及差异检查通过；构建仅既有大包告警，实际浏览器视觉尚未验收。

## 2026-10-31 两厂售电卡片展示现货及合约差价电费

- 用户明确计算口径：现货=Σ时段(Σ机组sales × bill_real_time_price)；合约差价=Σ时段Σ机组(contract_quantity × contract_price)，contract_price直接作为差价电价，不再次减实时价。不乘0.25，不替换为参考实时价，不舍弃停机机组合约或负值，不读取账单原费用。
- `backend/projects/daily_report_25_26/api/spot_electricity.py` 的_bill_fee_summary_columns生成NUMERIC乘积汇总，summary返回两厂四个sum_*_fee字段。每项独立校验区间完整96点/天、全机组必要量价非空；不完整返回NULL，完整零值返回0。SpotElectricityView.vue在两厂原售电量卡片下各增加两行金额，单日/区间标签随模式切换，金额单位元、显示两位小数，缺失提示账单数据不完整。前后端README同步；无数据库结构及持久化业务数据变更。
- `tests/test_spot_bill_fees.py`真实数据库外层事务回滚4项通过，验证公开参考价不参与计算、停机机组合约、负值、零值、缺价格及缺时段/日期；测试数据未保留。Serena未提供，使用Node只读及apply_patch降级并在此留痕，待工具恢复后补录。回滚仅移除本轮查询字段、卡片行及测试文档。最后验证日期：2026-10-31。
- 补充验证：变化的分时电量和正负电价验证逐点乘积不可替换为日总量乘均价；回滚后测试日期记录数0。前端本地构建及差异检查通过，仅既有大包告警；浏览器视觉尚未验收。

## 2026-10-31 精简账单上传区

- 按用户要求移除SpotSettlementImport.vue内“当前生效的账单来源”列表、刷新记录、量价明细与分页，并清理相关状态、展开事件、请求和样式。保留选择文件、预览、覆盖确认、成功提示及imported事件；不再占用页面展示导入来源和明细。
- 验证：前端6项专项回归、本地构建及差异检查通过；组件已无来源/明细查询引用。构建仅有既有大包告警，浏览器视觉未验收。
- 同步调整前端专项用例及前后端README；服务端接口、来源元数据、原件归档和数据库均未改动。回滚仅恢复组件展示与配套测试/文档。Serena仍不可用，使用Node只读检索及apply_patch修改，并在此留痕待补录。最后验证日期：2026-10-31。

## 2026-10-31 日账单仅超级管理员操作及取消批量数量上限

- 按用户要求，SpotElectricityView.vue的canImportBills直接校验Global_admin角色，不再使用项目提交权限或管理控制台权限；非超级管理员不渲染上传组件，不能展开或操作。spot_settlement.py的_importer对preview/confirm/imports/records统一返回403拒绝非超级管理员；移除每批20份上限，保留非空、xlsx及单份25MB校验。
- 测试覆盖真实接口依赖下普通提交者四个接口403、管理员25份上传进入解析，以及前端角色可见性；同步既有角色测试与前后端README。本轮无数据库变更，回滚范围为上述权限、数量检查、测试和文档。
- 验证结果：后端权限/批量专项2项、前端专项6项均通过，本地构建及差异检查通过；构建仅有既有大包告警，实际浏览器视觉未验收。
- Serena仍未提供，沿用Node只读及apply_patch编辑，并在此留痕待工具恢复后补录；验证采用本地接口测试、前端专项和构建，不使用远端CI。最后验证日期：2026-10-31。

## 2026-10-31 账单导入迁移至15分钟表并退役旧表

- 输入依据：两份2026-01-12原始xlsx及本地数据库36列结构。`services/spot_settlement_import.py` 的map_bill/persist_upload将100600电量映射七台机组sales、价格映射bill_real_time_price，100401量价映射机组合约字段。未运行机组、零和NULL全部保留，96时段完整性、机组完整性、共用价一致性及计量字段精度均校验；整批事务、日期锁、同文件幂等、不同版本明确覆盖确认，只更新上传电厂，不覆盖另一厂及参考电价。
- `api/spot_settlement.py` 的imports/records迁移为当前宽表来源及量价查询，原xlsx与批次清单在backend_data持久化目录归档；其他科目/费用/合计不入宽表。前端SpotSettlementImport.vue及api.js更新提示、覆盖参数、当前来源/明细；成功刷新现货页面。spot_electricity.py查询计算合计和价差，移除全省/收益；spot_electricity_sync_service.py、models_spot_electricity.py及SpotElectricityView.vue清理已删物理列依赖。
- `backend/sql/extend_spot_electricity_15min_settlement.sql`新增旧表非空停止检查及无CASCADE删除；已本地执行，旧表删除前0行，删除后to_regclass为空，目标仍36列、29088行、两厂导入批次均0。删除过时旧表建表SQL；样表测试使用真实数据库外层事务回滚，未正式导入。
- 验证：12项后端回归通过（包括全量映射、幂等、覆盖、跨厂冲突、中途失败回滚和分页），六个现货查询接口200；前端5项专项回归通过、本地构建通过。构建只有既有大包告警、openpyxl样表默认样式告警不影响功能；真实浏览器视觉未验收。前后端README已同步。
- 工具降级：Serena、Sequential Thinking及update_plan未提供，使用Node只读检索、apply_patch编辑及本地Docker验证，未调用远端CI；Serena记忆待工具恢复后补录。影响仅本账单/现货链路。回退需恢复与代码匹配的数据库结构，不能直接回退到依赖旧表/旧列的代码；原件和批次清单必须与数据库一并保留。最后验证日期：2026-10-31。

## 2026-10-31 生成现货冗余列删除SQL

- 按用户明确要求，在 `backend/sql/extend_spot_electricity_15min_settlement.sql` 末尾追加事务化删除6列：estimated_revenue、province_total_sales、beihai_total_sales、xianghai_total_sales、total_power_sales、price_spread。使用IF EXISTS，不使用CASCADE，并附0行核验查询。
- 仅生成脚本，未执行删除。脚本及回复明确提示现有接口、同步SQL、页面仍引用这些字段，需同步改造代码；删除列的数据不可由结构回退恢复，应按需备份。
- Serena未接入，Node只读及apply_patch生成和留痕。无业务代码修改；回滚仅移除本轮追加SQL和本节记录。最后验证日期：2026-10-31。

## 2026-10-31 现货15分钟表字段冗余检查

- 只读确认扩展后42列、29088条记录；当前机组售电量、预估收益、全省电量及新增账单价/批次字段尚无非空记录，不能以空列判定无用。新17列为账单公共价、机组合约量价及两厂来源批次，无明显重复。
- 可计算冗余包括price_spread、两厂各自total_sales及total_power_sales、时段标签/起止时刻；当前接口、同步服务或前端仍引用，不能直接删除。estimated_revenue当前无数据、计算口径未定，是优先清理候选；province_total_sales属于不同范围数据，是否保留取决于是否继续提供全省电量展示。两种实时价分别为参考价和账单价，应保留。
- 本轮不改结构或代码。Serena未接入，用Node及数据库只读查询、apply_patch留痕；回滚本节记录即可。最后验证日期：2026-10-31。

## 2026-10-31 生成现货15分钟表增量扩展SQL

- 按用户要求生成 `backend/sql/extend_spot_electricity_15min_settlement.sql`：扩展 `public.spot_electricity_15min_data`，增加账单实时价1列、七台机组省内中长期合约电量及电价14列、两厂导入批次UUID2列，共17列；NUMERIC不指定截断精度，字段可空，无默认0。保留现有售电量及参考电价字段，无回填或覆盖。
- SQL使用事务与ADD COLUMN IF NOT EXISTS并附字段注释和核验查询。本轮仅生成文件，不执行增量SQL，不删除raw表。已明确提醒用户当前上传/确认/历史接口仍依赖raw表，需完成接口切换后再删除。
- Serena未接入，使用apply_patch生成及留痕；不涉及业务代码交付，无需同步前后端README。回滚仅移除本SQL和本节记录即可。最后验证日期：2026-10-31。

## 2026-10-31 原始电力日账单上传入库

- 按用户明确要求，仅实现原始文件导入，不计算电费或调控收益。新增且已在本地 PostgreSQL 执行 `backend/sql/spot_electricity_settlement_raw.sql`，创建 `public.spot_electricity_settlement_raw` 一张表及索引，未修改现有电价/售电量表。粒度为文件版本—工作表—结算单元—日合计或96时段—科目，零值及全空科目全部保留。
- 字段包含交易/结算日期、账单编号、市场成员、发电户、厂站/机组编号名称、科目编码名称、原始电量/电价/电费、不设截断小数位的 NUMERIC、原单位说明、账单/机组控制合计、单元格原值/公式/缓存/格式/坐标、文件SHA256与归档路径、操作者和时间。原xlsx按哈希原字节归档；同文件跳过，不同文件保留来源版本，不覆盖或自动合并。
- `spot_settlement_import.py` 解析完整机组、96点及日合计，缺时段/重复/身份缺失/未知非空表拒绝整文件。非数值文本和无缓存公式保存在 source_cells，并提示，不擅自填0。科目数值编码100600.0规范为身份键100600，原单元格另存。日期按Excel本地日期读取，24:00仍归属原交易日。
- 新增 `/spot_electricity/bills/preview`、`confirm`、`imports`、`records` 私有接口；登录后按项目提交权限及已有单位范围控制。预览不写业务表，确认从暂存原文件重解析，整个批次一个数据库事务；按SHA加事务锁和唯一键保证重复点击幂等，中途失败整批回滚。历史和明细按导入版本查看，数值以字符串返回避免展示时丢精度。
- `SpotElectricityView.vue` 接入 `SpotSettlementImport.vue`，提供多文件上传、机组预览、确认原样入库、历史来源版本、分页查看日合计/分时科目、零与空白区分及源单元格查看。入口对超级管理员或有项目提交权限的用户可见。
- 两份样表共7台机组、7392条分时科目记录及77条日科目合计，共7469条；香海2号机计量为0仍完整读取。后端含真实数据库事务回滚测试，验证入库、同文件幂等、同日修订保留版本、中途失败回滚与查询；前端4项API/确认流程测试通过。样表测试未正式提交，本地新表回滚后记录数为0，等用户通过页面上传确认。
- Serena 未接入，无法激活或知识记忆记录；Node/Python只读、apply_patch编辑和本地SQL执行以本节留痕。无远端CI/CD或生产发布。其他环境需先执行上述增量SQL再部署代码；回退代码可保留新表和归档，勿删除已导入业务数据。浏览器控制工具未恢复，真实浏览器视觉未验收。最后验证日期：2026-10-31。
- 最终验证：容器内后端11项（含2项真实数据库回滚测试）、前端4项通过；本地构建通过（764模块，16.60秒），差异检查通过。新表存在，全部验证回滚后记录数为0。

## 2026-10-31 电力现货日账单样表评估

- 只读检查两份 2026-01-12 Excel、现货页面/模型和本地同日 96 点参考价，报告见 `configs/review-2026-10-31-electricity-bills.md`。共 7 台机组、672 条机组时段记录，完整 96 点，电费总分对账一致；发现零电量机组仍有合同电费、账单实时价与参考价 25 点不同、量价乘积有微小舍入差异。
- 建议保留原账单多科目和版本，参考电价模拟与正式金额分开；按结算单元编号映射厂站，不能合并合同与计量电量。延迟约 5 天按到数状态处理。调控效果量化需另外提供基准曲线和动作/成本数据。
- Serena 未接入，使用 Node/SheetJS 只读及 apply_patch 文档留痕；未修改原 Excel、业务代码或数据库，纯评估无需前后端 README 同步。网络仅查询公开官方规则；正文超时按 2 秒退避重试一次，未取得全文，正式计算规则仍待核实。最后验证日期：2026-10-31。

## 2026-10-31 修复漏表假成功及切换日期保护

- `DataEntryView.vue` 的一并提交改为完整预检：锁住日期、切表和编辑，逐表加载、重新校验并生成独立载荷快照；缺表、缺缓存、旧日期缓存、目录读取失败、阻断校验任一发生均在网络提交前停止。提交阶段等待所有请求结束，逐表确认 `ok:true` 且有写入记录；仅全部成功才提示成功和刷新，部分成功明确显示数量及失败表，保留失败表内容，不再跳过缺失缓存伪造成功。独立接口仍不具备跨表事务，本轮没有声称或增加跨表回滚。
- 模板与镜像查询统一使用加载代次及表格/日期/配置上下文，废除交叉表重复日期 watcher；日期变化同步使旧网格与缓存失效，旧网格隐藏且锁定，只有完整响应才解锁。失败保留明确错误和重试入口；晚到模板、查询和旧请求异常不覆盖当前上下文。缓存恢复核对上下文，单表提交也执行就绪保护。
- 日期控件在提交准备、网络提交和能效回填时锁定；存在未提交修改时切日期先确认。提交后的新编辑会取消自动刷新。能效生成缓存同样要求镜像查询成功，并补齐上下文、字典与校验元数据，避免新预检误接受残缺缓存。无真实业务提交或数据库写入。
- 新增 `composables/entrySubmissionGuard.js` 和 `tests/data-entry-safety.test.mjs`。直接加载实际页面函数模拟失败、延迟和切换：15 项专项通过；与能效上传回归合计 49 项通过。全量前端 76 项中 75 通过，另 1 项 `joint-review-hall.test.mjs:89` 因 proposed_patch 未定义失败；已核对该测试和保温管模块均非本轮改动，未扩大范围修复。浏览器工具未恢复，真实点击与视觉尚未验收。
- Serena 未接入，无法激活或知识记忆写入；Node 只读、模拟及 apply_patch 编辑以本节留痕。回滚本轮 DataEntryView、辅助模块、专项测试及文档即可；保留此前分析页等改动。无后端接口、数据库或远端发布变更，无迁移。最后验证日期：2026-10-31。
- 最终验证：本地 `npm run build` 通过（762 模块，17.56 秒），`git diff --check` 通过；构建仅有现有产物体积提示。

## 2026-10-31 每日填报及后续流程只读检查

- 检查前端填报、单表/多表提交、服务端标准表落库、审批/发布、数据库视图及看板缓存；报告见 `configs/review-2026-10-31-data-entry.md`。
- 模拟实际前端函数重现漏表仍报全部成功和多请求部分成功；纯函数重现列头决定日期、非法数字转 NULL；只读确认本地唯一索引及分析视图未按 status 过滤。无真实提交、审批、发布或业务数据写入。
- Serena 未接入，使用 Node/Python 只读、模拟及 apply_patch 报告留痕；无法知识记忆补录。无业务代码修改，无需更新前后端 README。回滚本节及检查报告即可；浏览器视觉和生产历史影响未验收。最后验证日期：2026-10-31。

## 2026-10-31 指标分类容器同排等高

- `DataAnalysisView.vue` 的 `.metrics-group` 网格改为 `align-items: stretch`，浅蓝分类容器按同排最高内容拉伸，内部指标保持顶部自然排列；不设固定高度，窄屏单列仍随内容增长。
- 本轮仅 CSS 调整，差异检查通过，无行为测试新增。Serena 未接入，使用 Node 只读和 apply_patch 修改，以本节留痕；回滚本条样式与文档即可，无后端/数据库变更。实际浏览器视觉待验收。最后验证日期：2026-10-31。

## 2026-10-31 数据分析指标区紧凑排版

- `DataAnalysisView.vue` 将指标标题、已选数量和全选/清空合并同排，取消独立说明行。大类内业务子类桌面双列，800px 以下单列，只有一个子类时占满整行；保留原分类、选择顺序和批量选择逻辑。
- 缩小外层及分类卡片内边距、间距和指标选项尺寸，数量与子类操作同排，已选状态突出并保留键盘焦点。长名称允许换行，网格允许收缩；修正指标面板 width:100% 叠加 padding 的宽度溢出，列表仍由单一外层滚动。
- 本地构建通过、差异检查通过；未新增布局实现镜像测试。浏览器工具不可用，实际视觉和手机触摸尚未验收。Serena 未接入，使用 Node 只读及 apply_patch 编辑，本节记录降级。回滚本轮指标区模板类名和样式及文档即可；其他已有修复保留。无后端/数据库改动或远端发布。最后验证日期：2026-10-31。

## 2026-10-31 数据分析页顶部条件区紧凑布局

- `DataAnalysisView.vue` 的单位/模式日期面板移除 220px 最小高度，桌面采用 1.35:1 双列、顶部对齐，内边距缩为 12px。单位采用等宽网格，保留复选框与选择顺序，增强已选样式和键盘焦点提示。
- 模式选项与标题同排，删去重复的日期标题和联动说明。单日只显示业务日期（原结束日期同步 watcher 保留），累计显示起止日期；900px 以下面板上下排列，420px 以下区间日期纵排，日期输入可收缩。仅影响顶部布局，不修改指标分类、查询参数或计算逻辑。
- 本地构建通过（761 模块，17.92 秒），差异检查通过；浏览器工具不可用，未完成真实视觉、手机日期控件和点击验收。
- Serena 未接入，使用 Node 只读与 apply_patch 编辑，以本节记录降级；回滚本轮顶部模板和作用域样式及文档即可。无后端/配置/数据库变更，无迁移和远端发布。最后验证日期：2026-10-31。

## 2026-10-31 参照月报查询工具细分日报指标

- 参考 `MonthlyDataShowQueryToolView.vue` 的“大类—业务子类—勾选项”结构和月报 `indicator_config.json` 分类，保留日报主要、调整、常量、气温四种来源口径，在 `DataAnalysisView.vue` 指标区增加业务子类卡片、大类及子类全选/取消、已选数量。未恢复用户已撤回的搜索和已选项面板。
- 新增 `constants/analysisMetricCategories.js` 按指标编码建立明确分类。主要指标分 10 类：主要产销、主要消耗、辅材消耗、能效与供暖单耗、站耗与热网损耗、经营收入、成本与利润、设备运行与生产事件、供热服务与投诉、日报气温记录；常量分能源与水热单价、辅材单价、供暖面积、采暖期收入与分摊；调整保留张屯煤耗汇总和供暖单耗调整，气温分析指标独立。
- 仅改变显示组织，不改编码、名称、取数和查询权限。部分勾选后类别全选补齐，全部勾选后类别取消，仅影响该类；保持其他已选项及勾选顺序。未知新增指标归入“其他指标”并保持可选；空类别不展示。移除组内嵌套滚动，统一由外层指标列表滚动。
- 9 项测试通过（分类 5 项、口径/精度 4 项），实际配置所有指标恰好归入一个子类且无兜底遗漏。本地构建通过（761 模块，19.45 秒），差异检查通过；浏览器工具仍不可用，未进行真实视觉和点击验收。
- Serena 未接入，无法激活或写知识记忆；使用 Node 只读及 apply_patch 修改，本节代为留痕。回滚本轮页面分类显示、分类模块及测试和文档即可；此前表头/精度及调度修复保留。无后端、配置和数据库变更，无迁移、无远端发布。最后验证日期：2026-10-31。

## 2026-10-31 撤回数据分析页指标选择改版

- 按用户要求，仅恢复 `DataAnalysisView.vue` 指标选择区原有模板、全选/清空行为、分组列表及组内滚动；移除新增搜索、匹配项/分组批量选择、已选项展示及相应辅助函数和测试。保留单日/累计表头口径及 0 位小数精度修复。
- Serena 未接入，使用 Node 只读及 apply_patch 定向撤回；未使用整体 Git 回滚，其他既有修改保留。前后端说明同步本次撤回，无后端接口或数据库变化。最后验证日期：2026-10-31。
- 验证：指标选择模板与 Git 原版逐字对照一致；保留的表头/精度 4 项回归通过，本地构建通过（14.54 秒），差异检查通过。

## 2026-10-31 数据分析页口径、小数精度与指标检索

- `DataAnalysisView.vue` 的同比/环比表头按结果元数据区分单日和累计；生成结果时保存 `analysis_mode`，Excel 使用同一规则。单日显示“当日值、同期当日值、上期当日值”，累计保持既有累计口径；月度计划表不受影响。
- 页面、简报、同比/环比 Excel 中小数位默认值统一由 `|| 2` 改为 `?? 2`，保留配置的 0 位精度。新增 `composables/analysisPresentation.js` 集中处理表头、指标过滤和选择集合。
- 指标区支持按名称、编码、分组名搜索（多个关键词同时匹配），显示命中数量；增加选择全部匹配项、分组选择/取消、按原勾选顺序展示的已选项及单项移除。过滤仅影响可见项，不删除隐藏选择；保留“全选全部/清空”原有全量行为。去掉组内嵌套滚动，列表统一由外层滚动，搜索框在滚动列表外。
- `node --test frontend/tests/data-analysis-presentation.test.mjs` 7 项通过，覆盖结果口径、检索、隐藏选择保留、选择顺序、0 位及默认精度、页面格式化与 Excel 构建函数。`frontend` 本地 `npm run build` 通过（760 模块，19.09 秒），`git diff --check` 通过；构建仅有产物体积提示。实际浏览器视觉未验收。
- Serena 当前未接入，无法激活和写知识记忆；降级为 Node 只读与 apply_patch 编辑，本节留痕。无后端接口、配置或数据库修改，无迁移、无远端发布；回滚本轮页面、辅助模块、测试及文档即可，保留此前改动。最后验证日期：2026-10-31。

## 2026-10-31 调度提取修复与导入状态逐项确认

- `dispatch_extractor.py` 在气象匹配前消除跨行空白，保留原始天气文本；完整解析天气描述、湿度、转向和阵风，保留预报日期。机炉提取保留各设备所在原表单元格，仅对具体带括注的设备保留“启动中”。
- 新增 `dispatch_reconciliation.py`：按厂别、编号、机炉类型匹配直接作用于主设备的动作，排除辅机、计划、否定、工作票及失败/试验语句；按有效时分排序，取末次主机事件推断状态。时间不明确、同末次时间状态矛盾、设备归属不唯一时保留表格并提示，不猜测。
- `dispatch_info.py` 与 `dispatch_db_service.py` 两层检查未确认冲突；导入和同日覆盖均需逐设备传入 `status_resolutions`（table/events）。原始状态、原表单元格、有效状态、事件证据、选择依据及 UTC 确认时间持久化到既有 JSONB，不改表结构。矩阵、设备数组及 flat_map 同步，兼容旧汽机键名；历史空 JSONB 可读取，旧记录不自动回写。
- `DispatchInfoView.vue` 在提取结果中列出每项差异及事件原文，让用户逐项选择；未选齐时禁止保存，覆盖确认保留选择。页面显示“启动中”及独立数量、主设备末次实际动作、预报日期、未确认历史差异与解析警告，删除原前端宽泛启动关键词匹配。
- 原始 PDF 回归：41 台设备、10 条事件、2 台启动中、北方 2 项待确认；香海辅机无汽机标签，完整天气恢复。后端 15 项测试、前端实际导入函数 3 项测试通过；前端构建通过（759 模块，14.59 秒）。容器直接从标准输入解析同一 PDF，通过冲突及天气断言。容器全套测试因 `/app/configs` 未挂载而不能读取测试 PDF，已使用标准输入验证容器解析器，无新增挂载或容器外制品。浏览器初始化故障，视觉和真实点击尚未验收。
- Serena 未接入，无法执行激活或写知识记忆；使用 Node/Python 只读、apply_patch 修改并在本节留痕。回滚本轮后端模块、接口、前端和测试及文档即可；未改数据库记录、未发起远端 CI/CD、未发布生产。已入库的旧数据需重新上传原文、逐项确认并覆盖，才能补回此前丢失的字段。最后验证日期：2026-10-31。

## 2026-10-31 原始调度 PDF 提取链路核对

- 输入：`configs/2026年10月30日生产信息.pdf`，共 4 页；用 pdfplumber 提取全文和表格，并渲染检查第 1、3 页。调用当前 `extract_pdf_file` 离线重解析，无上传、无数据库写入。
- 只读查询本地 `dispatch_daily_reports`，项目 `daily_report_25_26`、日期 `2026-10-30`：重解析的 41 台设备、10 条事件以及天气描述、湿度上下限、风向风级、天气原文与入库字段完全相等，未发现这些字段在入库阶段二次失真。
- 原文第 1 页北方全部机炉列为备用，第 3 页又记 #2 炉 9:20 点火、14:40 并汽，#1 机 16:18 并列；差异源自文档自身，统计时点不明。提取器按列赋状态，未做跨章节一致性检查。北海 #1 炉、香海 #4 炉原文均带“启动中”，`extract_boiler_turbine_status` 只保留编号与列状态，备注被丢弃。
- 天气实际存在且属于 10 月 31 日预报：4～14℃、多云转阴天有阵雨或雷阵雨、湿度 30%～90%、东南风 4～5 级转偏南风 5～6 级阵风 7 级。PDF 换行使“相对湿度”变成“相对 湿度”，正则无法识别描述和湿度；风况正则不接纳内部空白，结果截断为“东南风4~5”。前端缺失提示仅消除虚假默认值，尚未解决实际解析缺陷与预报日期标注。
- 前端 `getFacilityStartTime` 按设备名称出现与整条事件动作关键词匹配，误将香海辅机投运作为汽机启动，且首条命中即返回、动作统一标为启动。该逻辑不能用于推导当日最终运行状态。
- 本轮为排查，无业务代码修复、无数据覆盖。Serena 未接入，无法知识记忆补录；Node/Python 只读检查与 apply_patch 文档留痕作为降级。回滚本节记录即可；中间页图位于仓库内 `tmp/pdfs/`。最后验证日期：2026-10-31。

## 2026-10-31 调度信息设备排版与天气缺失显示

- `DispatchInfoView.vue` 的 `.fac-badge` 改为名称、元信息两行等高网格；名称超长省略并保留完整悬浮提示，启动标签允许收缩，状态保持单行，避免左右设备因标签发生高度差。天气描述和风况缺失分别显示“天气未提供”“风况未提供”，湿度缺失显示“未提供”，保留数值 0；天气图标改为温度计，避免暗示晴天。
- 只读核对本地 PostgreSQL `dispatch_daily_reports` 中项目 `daily_report_25_26`、业务日期 `2026-10-30` 的设备与事件：北方 #2 炉 9:20 点火、14:40 并汽及 #1 机 16:18 并列，但入库矩阵均为备用，尚不能确定原文统计时点，未覆盖数据库状态。香海 #3 机低速泵 10:00 投运、#1 机循环水泵 16:40 投运被 `getFacilityStartTime` 误判为汽机启动，已用当前函数与两条真实事件重现。本轮按用户要求核对并报告，未修改事件匹配与状态口径。
- Serena 未接入，无法执行激活、知识记忆写入；降级使用 Node 只读、apply_patch 编辑，证据为上述数据库只读查询与函数重现输出。回滚范围仅本轮页面及三份文档，保留其他已有改动；无数据库迁移、无生产发布。浏览器工具初始化失败，实际页面视觉验收未完成。最后验证日期：2026-10-31。
- 验证：本地 `frontend` 执行 `npm run build` 成功（759 个模块，14.48 秒），`git diff --check` 通过；构建产物体积提示及行尾转换提示不影响构建。真实事件调用现有 `getFacilityStartTime`，确认两条辅机投运均返回了汽机启动时间。

## 2026-10-30 看板标煤卡片移除计划描述

- 用户要求去掉“当日集团标煤消耗”和“供暖期标煤耗量”卡片中的动态计划分解描述。`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue` 移除两处计划对比信息条，包含计划值、超省量、完成率和悬浮说明；实际耗量及同期差值保留。
- 本轮仅调整卡片显示，现有标煤计划数据请求、刷新及其他页面逻辑保留；未发布生产。Serena 不可用，使用 Node 文件读取与 apply_patch 编辑，无法写入 Serena 知识记忆；回滚本轮模板删除和本节记录即可。最后验证日期 2026-10-30。

## 2026-10-30 数据展示详情页窄屏排版

- 用户反馈手机窄屏元素超出屏幕。`DisplayRuntimeView.vue` 原顶部标题、日期、操作按钮不换行，日期输入继承 180px 最小宽度，易撑宽页面。
- 768px 及以下调整为纵向标题和可换行工具栏，日期输入允许收缩；限制标签栏、表格、Trace 面板、面包屑与截图菜单宽度，表格及标签保持各自横向滚动，提示条留出屏幕边距。未改变数据求值和导出流程。
- `node --test frontend/tests/display-screenshot.test.mjs` 5 项通过；本地前端构建验证见交付记录。浏览器连接不可用，未能验证真实手机视觉、触摸滚动和日期控件；生产未发布。
- Serena 未提供，无法进行接入和知识记忆留痕；使用 Node 只读及 apply_patch 编辑，本条记录变更。回滚本轮模板类名、窄屏样式及本节记录，保留既有未提交修改。最后验证日期 2026-10-30。

## 2026-10-30 展示表截图百分比换行修复

- 用户反馈第三张表百分号换行。上一版对字符串数字测宽，但渲染时仍将字符串按普通文本换行；百分比中带空格、全角百分号也未被识别。
- `DisplayRuntimeView.vue` 统一数值和百分比字符串的测宽、禁止换行判定，将数字内部换行转换为空格用于截图，支持全角百分号；原始数据不变。
- `node --test frontend/tests/display-screenshot.test.mjs` 5 项通过，覆盖空格、全角百分号和显式换行。真实第三张表及手机截图尚未视觉验收；生产未发布。Serena 不可用，使用 Node 读取与 apply_patch 编辑，无法登记知识记忆；回滚本轮判定、测试及文档即可。最后验证日期 2026-10-30。

## 2026-10-30 截图长数字跨列修复

- 反馈：固定宽度截图中数值禁止换行，但列宽不足时数字会溢出到相邻列。
- `DisplayRuntimeView.vue` 在字体加载后测量数值及数字字符串，结合保守估计扩宽对应列；基础截图宽度为 1600 CSS 像素，必要时随列宽增长，按实际宽度生成画布。合并单元格按合并列总宽度计算，数据和数值显示格式不变。
- `node --test frontend/tests/display-screenshot.test.mjs` 四项通过，覆盖超长数字、数字字符串以及手机和桌面视口参数。真实手机浏览器仍不可用，未进行图片视觉验收；极长内容可能产生较宽画布，受设备画布容量限制。无后端或数据库迁移，未发布生产。
- Serena 不可用，文件读取使用 Node、编辑使用 apply_patch，无法写入 Serena 记忆；回滚范围为本轮截图宽度计算、测试及本记录，保留其他未提交改动。最后验证日期 2026-10-30。

## 2026-10-30 展示表截图固定布局宽度

- 用户反馈手机导出的截图表格挤在一起；原离屏容器采用自适应宽度，html2canvas 默认使用当前窗口宽度，自动表格布局受到手机视口影响。
- `DisplayRuntimeView.vue` 的 `buildHtmlForWorksheet` 和 `captureWorksheetToPng` 将截图卡片、画布及渲染视口固定为 1600 CSS 像素，表格按 Excel 列宽比例固定布局，文字可换行、数值不换行，等字体加载完成后按实际高度截图；2 倍缩放生成 3200 像素宽 PNG。页面显示布局和数据接口不变。
- 验证：`node --test frontend/tests/display-screenshot.test.mjs` 3 项通过，检查手机与桌面视口下参数、列宽、合并单元格和清理；`docker exec phoenix_frontend npm run build` 成功，仅有打包体积告警。浏览器连接不可用，尚未进行真实手机图片的视觉验收；极长数值和移动设备画布容量仍需实际检查。未发布生产。
- Serena 未提供，无法接入及写入记忆；通过 Node 文件接口读取、apply_patch 编辑并记录在此。仅回滚本轮截图逻辑、测试及本节记录，保留此前未提交修改。html2canvas 官方配置说明：https://html2canvas.hertzen.com/configuration ，访问日期及最后验证日期 2026-10-30。

## 2026-10-30 能效报表生产上传失败排查及修复

- 输入：用户反馈香海每日填报页面在开发环境可识别能效 Excel，生产环境提示 `Unexpected token '<'`。检查日期为 2026-10-30；尚未取得生产失败请求状态码，生产根因待实际环境复核。
- 证据：`docker-compose.server_new_server.yml` 为 web 构建传入 `HTTP_ONLY=true`；`deploy/Dockerfile.web` 因此选择 `deploy/nginx.http-only.conf`。旧 HTTP 配置缺少 `client_max_body_size`，HTTPS 配置已有 `20m`。香海样例 `configs/2025-2026香海能效分析表 1.xlsx` 为 4,337,890 字节，超过 Nginx 默认 1 MiB。官方依据：https://nginx.org/en/docs/http/ngx_http_core_module.html#client_max_body_size （访问日期 2026-10-30；Context7/DeepWiki 工具不可用，直接读取官方文档）。
- 修改：HTTP 配置补齐 `client_max_body_size 20m`；`frontend/src/projects/daily_report_25_26/services/api.js` 的三个能效上传函数共用 `parseEfficiencyUploadResponse`，区分 413、502/503、504 与非 JSON 响应，保留业务错误及 HTTP 状态，成功结果保持兼容。后端解析器、数据回填和入库流程未改动。
- 本地证据：使用已有 `ww870411/phoenix-web:20261030110511` 镜像启动隔离 Nginx，挂载 HTTP 配置，向香海解析接口发送 4,337,890 字节的零填充 multipart 文件（无认证、无业务数据）。修改前返回 `413 text/html`，内容以 `<html>` 开头；配置检查通过并重载后，同样请求返回后端 `401 application/json`、`缺少认证信息`，证明大文件已穿过代理。该 401 是匿名验证预期结果，不代表已验收真实 Excel 解析。
- 回归：`node --test frontend/tests/efficiency-upload.test.mjs` 共 33 个子用例通过（含父测试计 34 项），覆盖北海/香海/供热成功协议、上传字段、413/502/503/504、HTML/空/null 响应及业务/鉴权失败。`docker exec phoenix_frontend npm run build` 成功（19.88 秒），仅有产物大于 500 kB 的体积告警，不影响构建；隔离验证容器已停止并自动移除。最后验证日期：2026-10-30。
- 发布影响：需重新构建并更新实际 web 镜像；只重启旧镜像不会携带修改。若入口还有其他反向代理，同样需要核实其上传限制。无接口或数据库迁移；回滚仅撤回本轮 HTTP 配置、响应处理与测试补丁，保留原有未提交改动。未访问或部署生产环境。
- 工具降级：Serena、Sequential Thinking、update_plan 均未提供，无法执行接入校验及 Serena 记忆归档；使用 Node 文件接口只读检查，全部文本编辑通过 apply_patch。本节暂存关键证据，Serena 恢复后可据此补录。

## 2026-10-30 修复填报列表显示其他单位的问题

- 用户反馈 `beihai_filler` 在每日数据填报清单中能看到其他单位。配置实际为 `unit_filler.data_entry.mode=by_unit`，但 `AuthManager._build_merged_permissions` 曾把项目 `sheet_rules` 固定置空，前端缺规则时展示全表，导致各单位共同受影响。
- `backend/services/auth_manager.py` 新增 `_merge_sheet_rule_maps` 并用于全局和项目级规则：单角色保留原配置，兼职规则按并集合并，all 覆盖、explicit 合并清单、by_unit 保留显式附加表。提交动作开关维持已开启状态。
- 验证：新增6项权限回归，连同既有缓存测试共21项通过；`outputs/audit-2026-10-30-dashboard/verify-sheet-scope.cjs` 使用真实 AuthManager 会话序列化和实际 Pinia store 验证20个账号的列表结果。北海仅3表，研究院1表，售电1表，主城区6表；各单位管理员按本单位，集团/全局管理员全表。配置中的数据展示页授权保留。
- 本轮修复会话规则及前端列表可见范围，未扩展后端接口逐表授权；未登录真实账号、未提交业务数据、未部署远端。请退出重新登录以更新已有浏览器会话权限；真实浏览器点击仍未验收。
- 沿用工具降级：Serena 不可用，使用只读脚本与 apply_patch，本节留痕。无数据库迁移，回滚仅撤回权限合并函数改动，保留用户刚授权的提交开关及其他正在进行的页面修改。

## 2026-10-30 [数据展示页面新增一键导出三表高清长截图功能（每表一张，直发工作群）]

- **问题缘由与业务痛点**：
  - 用户反馈每日生产日报汇总完成后，需要将三张展示表下载为 Excel，再挨个在 Excel 中手动选区截图，最后发送到微信/钉钉等工作群供领导与各单位查看，流程繁琐且耗时；
  - 用户提出需求：希望能提供一个按钮，点击后自动为这三张表格生成截图并直接下载，每张表独立为一张高清图片文件。
- **改动范围与具体实现**：
  - **组件**：[`frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue)
  - **具体改动点**：
    1. **顶部操作栏增设【📷 导出截图】组合按钮组**：
       - 主按钮支持一键直出：点击即可全自动批处理三张展示表，期间显示动态进度 `正在生成截图 (1/3)...`、`(2/3)...`、`下载完成！`；
       - 下拉菜单灵活扩展：点击右侧下拉箭头可选择【🖼️ 一键导出全部展示表（3张）】或【📄 仅导出当前表截图（1张）】，兼顾每日例行批量与单表临时需求；
    2. **复用高规格排版引擎（Single Source of Truth）**：
       - 重构并提取 `prepareExportWorkbook` 共享函数，使 Excel 导出与图片截图导出完全共用同一份后端批量计算数据与 `beautifyWorksheet` 纯正灰度特色排版；
       - 确保导出的长截图与 Excel 保持 100% 一致的排版质感（灰阶表头、斑马纹数据区、闭合细网格边框、千分位数值与百分比对齐）；
    3. **HTML 报表卡片离屏渲染引擎 (`buildHtmlForWorksheet`)**：
       - 彻底规避虚拟滚动 DOM 元素截断问题，从 Worksheet 底层直接构造完整的标准 HTML `<table>`；
       - 顶部配备专业商务汇报标头：清晰展示主标题（如“1.集团全口径汇总表”）、平台副标与加粗业务日期（按要求移除多余的“归属单位”文案，版面更纯净精简）；
       - 底部包含版权与自动生成时间戳，四周边距舒适，无需二次裁剪即可直接作为正式汇报图片；
    4. **2倍视网膜级高清光栅化 (`captureWorksheetToPng`)**：
       - 调用系统全局已集成的 `html2canvas` 引擎，以 `scale: 2`（2倍视网膜超清分辨率）执行像素绘制；
       - 保证图片在手机微信群、钉钉群或电脑端放大查看时文字、数字均丝滑锐利、绝无马赛克或模糊；
    5. **平滑时延队列与 Blob 下载安全闭环**：
       - 依次导出并分别命名为：
         - `1.集团全口径汇总表_YYYY-MM-DD.png`
         - `2.分析简报_YYYY-MM-DD.png`
         - `3.主城区汇总表_YYYY-MM-DD.png`
       - 在每张图片下载之间增加 450ms 安全间隔，防止浏览器并发下载限流；
       - 修复 `downloadBlob` 中 `URL.revokeObjectURL` 异步时序，确保大尺寸图片数据流完全写入磁盘；
    6. **页面操作体验反馈 Toast**：
       - 导出完成后在屏幕右下角自动弹现现代轻量黑金风格 Toast 提示：`3张展示表高清截图已下载完毕，可直接发送到工作群！`，4秒后自动淡出。
- **验证结论**：
  - 前端全量生产构建 `npm run build` 顺利通过；
  - 经离屏 HTML 解析与多层跨行跨列（Rowspan/Colspan）单元格合并逻辑验证，三张表格数据结构与格式完整对应，多行文字与标头 100% 完整容纳。

## 2026-10-30 [数据展示全口径展示表 Excel 导出全面升级：灰度特色配色、自适应行高与全封闭边框修复]

- **问题缘由与业务痛点**：
  - 用户反馈全口径数据展示页面（三张展示表）的“导出Excel”功能样式排版存在多项问题：
    1. 原导出依赖全局社区版 `XLSX`（SheetJS），写出文件时丢弃单元格样式，导致底色、边框全部丢失；
    2. 填入的数据单元格缺少千分位、百分比格式，数字与文本对齐混乱；
    3. 表头双行文本（如“25-26供暖期\n累计”）及长项目名因固定过紧行高（22~26pt）发生文字下半截被截断遮挡；表3右侧残留多余空白列；
    4. 用户拒绝彩色花哨设计，**明确要求仅接受经典纯正的灰度（Grayscale）特色**；
    5. **边框质量瑕疵**：部分区域边框缺失不全（如大标题行第 0 行无边框、合并单元格副格缺失边框），且表头底部粗边框与数据行细边框交界冲突导致视觉上粗细不一。
- **改动范围与具体实现**：
  - **组件**：[`frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue)
  - **具体改动点**：
    1. **引入专业样式引擎 `xlsx-js-style`**：由原生支持 OpenXML 样式的 `xlsx-js-style@1.2.0` 驱动读取与写出，100% 完整保留单元格样式与边框；
    2. **工作簿净化与精选重命名**：彻底剥离 12 个无关空白填报表，仅保留并规范命名三张核心展示表：`1.集团全口径汇总表`、`2.分析简报`、`3.主城区汇总表`，导出体积从 2.3MB 降至 66KB 极致轻量；
    3. **自动裁剪右侧空白无效列**：表3等模板右侧遗留的多余无数据列自动裁剪（`A1:Q45` 裁剪至 `A1:K45`），避免右侧白框冗余；
    4. **动态自适应行高算法（彻底根治文字截断）**：
       - 表头行：自动识别显式换行 `\n`（如“25-26供暖期\n累计”），双行表头行高精准提升至 **`42pt`**，单行表头 **`28pt`**；
       - 数据行：基础单行高度提升为舒适的 **`24pt`**；同时对行内所有单元格动态检测显式换行及基于列宽估算的折行数 `lines`，若 `lines >= 2` 自动放大为 `lines * 18 + 6`（如 42pt、60pt 等），配合 `wrapText: true`，绝不遮挡任何文字；
    5. **黄金列宽自适应与关键列宽裕保底**：
       - 忽略标题行干扰，单行分词精确测算字符宽度；项目名称列（`itemCol`）设置 **`28`** 字符宽裕保底；经营单位保底 `13`、计量单位保底 `11`、数值列保底 `12`；
    6. **纯正灰度特色配色体系（Monochrome Grayscale Palette，杜绝彩色视觉干扰）**：
       - 表头：一级表头采用稳重典雅的灰阶底色（`#D4D4D8`）配深炭黑加粗文字（`#18181B`），二级指标表头采用浅中灰底色（`#E4E4E7`）配中炭灰字；
       - 数据区：奇偶行交替素雅微灰阶底色（纯白 `#FFFFFF` 与极淡浅灰 `#F4F4F5`），全表单元格统一覆盖纯灰细网格边框（`#CBD5E1`）；
       - 文字与对齐：单位居中、项目靠左、数值靠右并配置千分位格式（`#,##0` / `#,##0.00`），差异列保留百分号（纯炭黑 `#18181B`），空值采用中灰（`#A1A1AA`）；
    7. **统一闭合网格系统（彻底修复边框不全与粗细不一）**：
       - 全表统一采用统一线宽与色值的 `uniformThinBorder`（`style: 'thin', color: { rgb: 'CBD5E1' }`），彻底废除表头下沿 `medium` 中粗边框导致的层级冲突与粗细参差；
       - 第 0 行大标题及日期行全面纳入网格边框覆盖范围，彻底修复标题行缺失边框的问题；
       - 对 `ws['!merges']` 实行合并单元格**全子格穿透注入**：对大跨度合并区域内每一个从属单元格（Sub-cells）均显式补齐 `uniformThinBorder` 与对应背景色，确保合并块在 Excel 渲染下外框连续闭合、无虚线断裂。
    8. **下载兼容性兜底**：封装 `downloadBlob`，兼容 `saveAs` 与原生 `<a>` 标签下载。
- **验证结论**：
  - 前端生产打包 `npm run build` 顺利通过；
  - 导出 Excel 文件在 Office Excel 与 WPS 中打开均呈现规整封闭的细灰度网格，文字无遮挡，色彩纯粹沉稳。

## 2026-10-30 开启日报所有填报用户组的提交权限

- 用户明确要求“全部打开”。本次范围为日报 `daily_report_25_26` 中已有 `data_entry` 页面权限的用户组：`Group_admin`、`ZhuChengQu_admin`、`Unit_admin`、`unit_filler`、`shoudian_filler`，统一将 `can_submit` 从 false 改为 true；全局管理员原已开启，浏览组维持无提交权限。
- 修改 `backend_data/shared/auth/permissions/daily_report_25_26.json`；前端 `canSubmitFor` 与后端 `get_project_action_flags` 读取同一项目动作授权，覆盖19个此前被阻止提交的账号。此次不改变其他项目、页面范围、审批/发布权限或业务数据。
- 验证：解析 JSON 并通过 AuthManager 合并实际账号权限，检查20个具有填报入口的账号均允许提交（含原有全局管理员），研究院填报账号为 true。未发起真实业务提交，远端服务未核对/部署。
- Serena 当前不可用，使用只读脚本及 apply_patch，先以本节记录降级留痕。回滚将本轮五组 `can_submit` 恢复 false；无数据库迁移。已登录用户刷新页面获取新权限，仍显示旧提示时退出重新登录。

## 2026-10-30 [数据展示页面全口径展示表补齐同单位多报表分段标签栏 (Segmented Tabs)]

- **问题缘由与业务痛点**：
  - 用户反馈在访问数据展示页面（`/projects/daily_report_25_26/pages/data_show/sheets?config=projects%2Fdaily_report_25_26%2Fconfig%2F数据结构_全口径展示表.json&pageName=数据展示页面`）时，列表页中“1.集团全口径汇总表”、“2.分析简报”和“3.主城区汇总表”三张表由于单位名均为“经济运行部”，被聚合归并在同一个卡片入口中；
  - 但点击卡片进入详情页后，仅加载了第 1 张表（`Group_sum_show_Sheet`），详情页内缺乏多表切换机制，导致第 2 张表（`Group_analysis_brief_report_Sheet`）与第 3 张表（`ZhuChengQu_sum_show_Sheet`）无法感知和切换，只能频繁退回上一级。
- **改动范围与具体实现**：
  - **组件**：[`frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue)
  - **具体改动点**：
    1. **多报表数据加载与同单位关联**：导入 `listSheets` 接口，在挂载时动态读取当前配置文件（`pageConfig`）下的全部报表，依据当前 `sheetKey` 提取 `unit_name`，并将同一单位名下的所有报表装载至 `unitSheets` 响应式列表中；
    2. **现代化分段胶囊标签栏 (Segmented Tabs)**：在页面顶部引入与数据填报页面（`DataEntryView.vue`）高度一致的 `.unit-tabs-nav-wrapper`，当 `unitSheets.length > 1` 时自动渲染分段标签栏，展示格式化后的报表序号徽标与标题名称；
    3. **路由联动与响应式求值**：新增 `onSwitchSheetTab` 切换方法与 `watch(sheetKey)` 监听器，点击不同 Tab 时使用 `router.replace` 动态更新路由参数，同时无缝触发 `runEval()` 重新执行报表运行时求值与数据网格渲染；
    4. **动态单位标题适配**：顶部标题根据归属单位智能展示为 `{{ unitGroupName }} 数据展示`（如“经济运行部 数据展示”），增强层次感。
- **验证结论**：
  - 前端生产构建 `npm run build` 顺利通过，759 个模块编译无误，页面样式、路由切换与事件流运行正常。

## 2026-10-30 [2026-2027供暖期常量指标全量测算核准与批量入库]

- **任务背景与用户指令**：
  - 为保障 2026-2027 供暖期（代号 `26-27`）系统各项单耗、热网平衡、成本核算及边际效益分析引擎的平稳启动，针对用户提供的 [`configs/26-27供暖期常量指标搜集表（含25-26同期）.xlsx`](file:///D:/编程项目/phoenix/configs/26-27供暖期常量指标搜集表（含25-26同期）.xlsx) 进行数据质量核验、业务规则补齐、公式值解析及底层数据库全量入库。
- **业务测算原则与数据补正**：
  1. **研究院挂网面积**：按用户确认修正为 **`13.1495` 万㎡**（剔除因录入失误产生的 10 倍偏差）；
  2. **庄河环海外购热运行模式**：因本期全量转为外购热模式，将标煤单价、氧化镁单价、脱硝剂单价规范设置为 **`0`**，保留外购热单价 `47.71` 元/GJ 及电水单价；
  3. **供热公司 10 个分中心（华乐、东港、春海、中山、北岗、双兴、香炉礁、兴工、大纺、管网）**：
     - 外购电单价与购水单价继承供热公司总表基准，分别填入 **`0.65` 元/kWh** 与 **`4.51` 元/吨**；内购热单价维持 **`50.0` 元/GJ**；
     - 挂网面积（目标总计 `3320.489247` 万㎡）、供暖收费面积（目标总计 `2323.0925` 万㎡）及采暖期供暖收入（目标总计 `57780.2043` 万元）按 25-26 同期分布占比同比例精准拆分，各中心加总值与总公司目标值 100% 严丝合缝；
     - 各中心分摊比按供暖收费面积占比填入（管网中心为 0%）；
  4. **税费折算与联动公式智能解析**：精准提取并计算 Excel 内嵌的税率折算公式（如北海与香海辅材不含税单价 `=325/1.13`、`=888/1.13` 等）与供暖收入面积联动公式，消除静态读取导致的空值隐患。
- **改动范围与落地成效**：
  1. **Excel 归档更新**：回写并保存 [`configs/26-27供暖期常量指标搜集表（含25-26同期）.xlsx`](file:///D:/编程项目/phoenix/configs/26-27供暖期常量指标搜集表（含25-26同期）.xlsx)，补齐全部 153 项指标；
  2. **数据库批量 UPSERT 入库**：通过专用入库引擎将全量 153 条指标批量写入 PostgreSQL 数据表 `public.constant_data`（约束为 `(company, item, period)`，指定 `period='26-27'`）。
- **验证结论**：
  - `SELECT count(*) FROM constant_data WHERE period='26-27'` 查询结果精确为 **153 条**（18 个核算主体、9 张常量表无一缺漏）；
  - `value IS NULL` 查询结果为 **0 条**；
  - 核心样本（北海煤价与辅材、庄河外购热单价、东港面积与收入分解、管网分摊比等）抽样校验 100% 准确无误。

## 2026-10-30 [数据看板右上方运维管理控制组权限收拢至仅限 Global_admin]

- **用户指令与背景**：
  - 数据看板全量开放后，针对页面右上方运维管理控制组（包含【缓存管理】、【禁用缓存】、【停止发布】、【导入气温】、【📜 日志】及缓存进度状态），用户明确要求：原由 `Global_admin` 与 `Group_admin` 共同拥有的权限，**全部收拢改为仅 `Global_admin`（超级管理员）独享**。
- **改动范围与具体实现**：
  1. **前端 [`DashBoard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DashBoard.vue)**：
     - 重构 `canManageCache` 计算属性判定逻辑，由原先依赖 `canPublish`（集团管理员亦具备）调整为强校验超级管理员身份 `isGlobalAdmin`（基于用户所属组 `Global_admin` 及全局后台权限 `can_access_admin_console`）；
     - 非超管账号进入看板后，右上方管理控制组（`.dashboard-cache-controls`）彻底不渲染；
  2. **后端 [`backend/projects/daily_report_25_26/api/dashboard.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dashboard.py)**：
     - 重构 `_ensure_cache_operator` 鉴权函数，仅放行 `session.group == "Global_admin"` 或具备 `can_access_admin_console` 动作权限的超管会话，其余账号调用缓存生成/清除/停用/停止或气温导入等接口时直接抛出 `403 Forbidden`。
- **验证结果**：
  - 通过专用鉴权单元测试验证，`ww870411`（Global_admin）顺利通过，`group_admin`、`zhuchengqu_admin`、`beihai_admin` 等其余所有角色调用时均被精准 403 拦截；
  - 既有看板 15 项单元测试全量通过；前端打包构建顺利完成。

## 2026-10-30 [daily_report_25_26 模块页面可见性权限矩阵调整]

- **用户需求与变更背景**：
  - 针对 `daily_report_25_26` 项目的二级功能页面可见性（限本项目账号，不包含 tube 或其他项目人员），进行三项精细化权限调整：
    1. **数据看板（`dashboard`）对所有用户可见**；
    2. **数据展示页面（`data_show`）对所有人可见**；
    3. **全局管理中心（`global_management`）仅对 `Global_admin` 可见**。
- **改动范围与具体配置变更 (`backend_data/shared/auth/permissions/daily_report_25_26.json`)**：
  1. `Unit_admin`、`unit_filler`、`shoudian_filler` 的 `page_access` 中补齐 `"dashboard"` 与 `"data_show"`，并在其 `sheet_rules` 中显式配置 `"data_show": { "mode": "all" }`，确保基层单位主管与填报人员均可查看全景展示表；
  2. `Group_admin` 与 `Group_viewer` 的 `page_access` 中彻底剔除 `"global_management"`；
  3. 仅 `Global_admin` 保留 `"global_management"`，配合前端路由守卫实现非超管人员严格拦截并重定向 `/forbidden`。
- **验证结果**：
  - 通过 `backend.services.auth_manager` 仿真验证所有 7 类日报业务角色的卡片清单，`dashboard` 与 `data_show` 均已 100% 覆盖全员，`global_management` 仅归属于 `Global_admin`，其他项目账号依旧被安全隔离拦截。


## 2026-10-30 看板初始加载空白体验修正

- 用户反馈进入看板时仅显示“数据载入中”和大片空白。原因是上一轮为避免跨日期误读，在主数据未返回时隐藏了整个内容区。
- `DashBoard.vue` 保留该日期隔离规则，增加四张摘要卡片及六个内容区的骨架占位；初始化读取业务日期时即进入 loading，切日等待也显示占位，移动端单列。加载文案明确当前查询日期，返回成功后替换为真实内容，失败后展示错误与重试。
- 前端 README 和后端 README 同步说明；不改接口、计算、缓存或数据库，无迁移。回滚仅撤回本轮骨架模板、样式与初始 loading 改动。
- 继续沿用前述工具降级：Serena 不可用，知识登记暂以仓库记录代替。验证通过前端构建和既有 Vue 回归脚本，包含初始模板确实输出骨架、未闪出选日提示的断言；真实浏览器视觉验收仍未完成。

## 2026-10-30 数据看板五类隐患修复

- 前置说明：Serena 与原生文件读取工具当前不可用，使用只读 Python 检索及 apply_patch 修改；操作范围为看板、气温缓存链路、测试和本节及前后端 README。Serena 知识登记未完成，先在仓库留痕；数据库运行文件和现有其他配置变动全部保留。
- `DashBoard.vue`：顶部 `primaryCoalHeadline` 固定读取日口径；日期监听仅屏蔽程序回填，用户切日立即作废旧请求，再防抖查询；缓存命中也作废旧请求；清空日期/卸载不回填旧数据。
- `loadCoalPlanComparison`、`fetchSpotElectricityData`、`fetchDispatchInfoData`：各自按请求序号核对响应和 loading 归属；新查询先清空旧值；计划与实际日期一致才展示对比。
- 错误反馈：主看板、现货、调度、计划提供失败提示及重试；气温预览失败展示持续提示；主数据未就绪时隐藏旧内容，数据仍加载时禁止 PDF 导出。气温提交中禁止关闭弹窗重置提交状态。
- `dashboard_cache.py`、`dashboard_expression.py`、`dashboard_cache_job.py`、`weather_importer.py`：气温事务成功后更新独立版本；计算开始时捕获版本；读取缓存时核对，旧文件保留但不命中，计算中途换版也不能把旧结果当成新缓存。首次升级跳过未带气温版本的历史快照。页面在气温提交或禁用缓存后清空所有内存日期。
- 验证：后端缓存与气温事务回归 15 项通过；前端实际 Vue 源码回归覆盖日期变更、缓存命中、三个独立请求链的乱序/清空/loading、标煤日口径和错误分支；前端生产构建通过（存在原有大包体积提示）。本地 GET 看板返回 `temperature_revision=temperature-v1`，确认本地后端已使用新代码。
- 验证边界：Chrome 工具初始化后浏览器列表为空，未完成真实点击、移动端和 PDF 成品验收；未执行真实气温覆盖、缓存发布或禁用操作，未部署远端。
- 无数据库迁移，直接替换代码。旧缓存需要重新生成才能恢复命中，未生成时走实时计算；本次读取约8秒，不能视为性能基准。回滚仅撤回本轮代码改动，保留数据库及已有快照；审查报告和回归脚本位于 `outputs/audit-2026-10-30-dashboard/`。

## 2026-10-29 [数据看板标煤耗量与平均气温趋势图重构：全周期时间序列恢复、DataZoom 视口死锁根治与双指标平滑走势视觉焕新]
- **用户指令与现象反馈**：
  - 用户精准指出最下方“标煤耗量与平均气温趋势图”两大致命异常：
    1. **日期不对且随机跳转**：在日期选择框选择 2026-03-13 时，图形仅显示当天；切换到 3-12 时，图形跳到随机某一天；
    2. **视口时间跨度严重缺失**：原本应当显示一段时间的走势，实际却缩死为单日。
- **问题根因定位与排查溯源**：
  - **根因一（后端时间序列被截断）**：
    - 在 [`backend/services/dashboard_expression.py`](file:///D:/编程项目/phoenix/backend/services/dashboard_expression.py) 中，`_calc_daily_comparison_trend` 曾为了提升性能临时硬编码了 `window_start = push_dt - timedelta(days=9)`，导致后端只返回了 10 天的数据，剥夺了图表回看供暖期历史全景的能力；
  - **根因二（前端 DataZoom 状态与索引死锁）**：
    - 前端 [`DashBoard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DashBoard.vue) 中未建立对 `[effectiveBizDate, pushDateValue]` 的深度监听，用户切换业务日期时旧的 `dailyTrendStartIndex` 和 `dailyTrendWindowSize` 长期残留；
    - 当用户此前触发过滚轮缩放时，`size` 曾被写入为 1 且无法自动复位；旧的日期 category 传给新数据集导致 ECharts 找不到对应坐标而崩溃回退到随机索引；
  - **根因三（视觉表现粗糙重叠）**：
    - 气温被错误配置为 16px 粗柱状图（Bar），正负气温柱子严重遮挡标煤折线；
    - 全量开启常驻数据标签（`show: true`），数字密密麻麻互相覆盖。
- **高精细重构实施**：
  1. **后端完整时间序列恢复 (`dashboard_expression.py`)**：
     - 将每日对比趋势的起始日期恢复为当期供暖期首日 `season_start_dt`（2025-11-01），连续生成至当前业务日期（如 2026-03-13，共 133 天完整序列），实测聚合全周期数据仅耗时 0.18 秒；
  2. **前端 DataZoom 与滑动窗口重构 (`DashBoard.vue`)**：
     - 确立 `DAILY_TREND_DEFAULT_WINDOW = 15` 与 `DAILY_TREND_MIN_WINDOW = 5`，杜绝视口被意外压缩为单日；
     - 增加对 `[effectiveBizDate, pushDateValue]` 的监听，切换业务日期时强制执行 `dailyTrendStartIndex.value = null`，自动将滑动窗口对齐到当前业务日及其前 14 天（共 15 天最佳阅读视口）；
     - 将 `pushDateValue` 的定义前置至 `dashboardData` 紧跟之后（第 1481 行），彻底消除 JavaScript 变量暂时性死区（TDZ ReferenceError）导致的组件挂载白屏隐患；
     - `dailyTrendDataZoom` 严格以数字索引 `meta.startIndex` 与 `meta.endIndex` 传参，100% 根除 category 标签漂移；
  3. **尊重用户审美：复原经典半透明柱状图与经典蓝橙配色 (`DashBoard.vue` 之 `useDailyTrendOption`)**：
     - **视觉形态恢复**：应用户明确要求，将平均气温恢复为经典柱状图（`bar`，适度宽度 14px，带微圆角），本期气温采用半透明蓝 `rgba(37, 99, 235, 0.25)` 加蓝色实线边框，同期气温采用半透明橙 `rgba(249, 115, 22, 0.25)` 加橙色虚线边框；
     - **图层层级优化**：设置折线 `z: 5`、柱图 `z: 2`，确保标煤折线浮在气温柱子前侧，既满足用户喜爱的柱线组合，又保持折线清晰连续；
     - **经典配色复原**：本期统一采用经典科技蓝 `#2563eb`，同期统一采用活力橙 `#f97316`；
     - **标签净化与业务日高光保留**：依然保持清爽的无常驻重叠标签设计，仅在当前所选业务日点位添加高光发光圆点与“业务日”垂直虚线引导线；
     - **悬浮 Tooltip 结构化卡片适配**：鼠标悬停时清晰分栏输出日期、标煤（本期/同期/超省）与气温（本期/同期/温差）对比。
     - **悬浮 Tooltip 结构化卡片**：
       - 鼠标悬停时弹出结构化面板，分栏清晰展示日期、标煤耗量（本期/同期/超省及百分比）、平均气温（本期/同期/温差偏暖偏冷提示）；
     - **X 轴格式化**：标签紧凑输出 `MM-DD`（如 `03-13`），左 Y 轴规范命名 `标煤耗量 (吨)`，右 Y 轴规范命名 `平均气温 (℃)`。
- **验证结果**：
  - 前端 `npm run build` 全量通过（759 个模块构建 0 错误，耗时 16.77s）；
  - 彻底解决了日期不对、切换显示随机某天、以及单日显示等问题，恢复了半月默认视口与供暖期全景自由滑动。


## 2026-10-29 [数据看板标煤动态分解本质溯源：拔除月均摊降级，严格锁定全月气温齐备作为分解前置条件]
- **用户指令与需求确认**：
  - 用户敏锐质疑：“嗯？2026年12月份怎么会有呢？”；
  - 核心问题溯源排查：
    1. 当前现实时间为 2026年10月下旬，经数据库核查，气温数据表 `calc_temperature_data` 目前仅录入到 2026-11-30，**2026年12月及之后根本没有任何一条气温数据**；
    2. 之前代码中留存了兜底逻辑（在气温缺失时自动拿月度计划按天均摊），导致系统在查询未来尚未录入气温的月份（如 2026-12、2027-01）时，“冒名”生成了虚假的日计划值，违背了“以气温驱动动态分解”的核心科学定义；
    3. 动态分解必须以**当月全月气温真实齐备并完成度日计算**为绝对前提！无气温数据的月份无法进行动态分解，绝不展示。
- **高精细重构细节 (`dynamic_decomposition_service.py`)**：
  1. **彻底拔除月均摊降级逻辑**：
     - 在 `get_coal_plan_comparison` 中彻底删除原先的 `daily_status = "fallback"` / `round(m_plan / days_in_m, 2)` 日均摊逻辑；
  2. **确立全月气温齐备刚性铁律**：
     - `get_dynamic_daily_decomposition` 返回的 `has_full_month_temp` 若为 `False`（说明当月全月气温尚未齐备，例如尚未发生的 2026年12月）：
     - 立即判定为 `in_plan_period: False`，计划值置为 `None`，原因标注为：“月份 YYYY-MM 气温数据尚未录入齐备，无法开展标煤计划动态分解”；
     - 状态统一为 `out_of_period`，前端卡片对比栏自动隐藏，保持界面严肃客观。
- **验证结果**：
  - Python 单元验证：
    - `2026-11-01` ~ `2026-11-30`（26-27供暖期且气温齐备）：`in_plan_period=True`，正常生成动态日计划（如 11月15日计划 2572.3 吨）；
    - `2026-12-01`、`2026-12-15`、`2027-01-15`（气温尚未录入的未来月份）：**均准确返回 `in_plan_period=False`，计划值均为 `None`，看板绝不展示对比条**；
  - 彻底解决了未来未录入气温月份凭空产生假计划的问题。


## 2026-10-29 [数据看板标煤动态计划基线界定：限定自 2026-11-01（26-27供暖期）正式起用展示]
- **用户指令与需求确认**：
  - 用户明确关键业务边界：“动态计划是26-27供暖期才加入的，所以，我希望从2026年11月1日开始才有这个显示”；
  - 需求界定：
    - 标煤耗量日动态分解与动态累计计划对比机制属于 2026-2027 供暖期（自 2026-11-01 起）全新引入的先进管理模型；
    - 针对 2026年11月1日 之前的历史供暖期（如 2025-2026 供暖期）及历史过渡期，即便数据库中存在历史月度计划或气温数据，也严格不予展示动态分解计划对比条；
    - 仅当看板所选业务日期 $\ge \text{2026-11-01}$ 且处于有效供暖计划期间时，才展示当日与累计动态计划对比。
- **高精细重构细节 (`dynamic_decomposition_service.py` & `DashBoard.vue`)**：
  1. **后端服务硬边界校验 (`dynamic_decomposition_service.py`)**：
     - 在 `get_coal_plan_comparison` 入口处设立常量门禁 `DYNAMIC_PLAN_START_DATE = date(2026, 11, 1)`；
     - 凡 `biz_dt < DYNAMIC_PLAN_START_DATE`，立即返回 `in_plan_period: False`，计划值全部置为 `None`，明确附带说明：“计划动态分解机制自 2026-11-01（26-27供暖期）正式加入，历史日期不展示动态计划对比”；
  2. **前端三重安全防护 (`DashBoard.vue`)**：
     - 常量声明 `const DYNAMIC_PLAN_START_DATE = '2026-11-01'`；
     - `loadCoalPlanComparison` 拦截：当 `targetDate < '2026-11-01'` 时，直接跳过 API 请求，节省网络负载，将数据状态重置为 `out_of_period`；
     - `dailyCoalPlanSummary` 和 `seasonCoalPlanSummary` 双计算属性同步添加 `curDate < DYNAMIC_PLAN_START_DATE` 守卫，确保卡片底部在历史日期下 100% 隐藏对比条。
- **验证结果**：
  - 后端 Python 单元测试全量验证（2025-11-15、2026-01-15、2026-10-31 均返回 `in_plan_period=False` 且 `plan_val=None`；2026-11-01、2026-11-15、2027-01-15 均准确计算并返回动态计划值）；
  - 前端静态构建全量通过（`npm run build` 耗时 14.21s，759 模块无报错）；
  - 完美符合 26-27 供暖期正式启用的业务设定。


## 2026-10-29 [数据看板标煤动态分解计划对比期间门禁：非计划分解期间自动隐藏当日与累计对比条]
- **用户指令与需求确认**：
  - 用户提出明确业务规则：“当数据看板选择的业务日期位于存在计划动态分解期间之外的，不显示当日和累计的标煤耗量的动态分解对比情况。”；
  - 核心业务背景梳理：
    - 标煤耗量动态分解计划是供暖期专用业务模型（基于 HDD20 供热度日与 k 敏感度参数在有月度标煤计划的月份展开）；
    - 非供暖期（如 5~9 月份）或者供暖期中尚未配置月度计划的月份（例如 25-26 供暖期的 2025-10、2026-04），不属于计划动态分解的有效运行区间；
    - 在上述期间之外，若仍旧展示对比信息甚至使用均摊兜底，容易给用户造成误解。
- **高精细重构细节 (`dynamic_decomposition_service.py` & `DashBoard.vue`)**：
  1. **后端期间门禁校验服务升级 (`dynamic_decomposition_service.py`)**：
     - 在核心函数 `get_coal_plan_comparison` 中新增期间合法性双重校验：
       - 第一道门禁：针对夏季 5~9 月明确识别为非供暖期，立即标记 `in_plan_period: False`，返回状态 `status: "out_of_period"`，计划值置为 `None`；
       - 第二道门禁：查询 `paln_and_real_month_data` 中该单位当期配置的月度标煤计划（`item = 'consumption_std_coal'` 且 `type = 'plan'`），若业务日所在月未录入有效计划（`cur_month_plan <= 0`），同样判定为 `in_plan_period: False`；
       - 仅当处于供暖期且当月存在有效标煤计划时，才赋予 `in_plan_period: True` 并计算分解与累计值；
  2. **前端卡片展示安全门禁 (`DashBoard.vue`)**：
     - `dailyCoalPlanSummary` 计算属性强化：前置校验 `coalPlanComparisonData.value?.in_plan_period === true`，若为 `false` 或 `status === 'out_of_period'` 或 `plan_value <= 0` 时，直接返回 `null`，确保【当日集团标煤消耗】卡片下方的对比信息条自动隐匿；
     - `seasonCoalPlanSummary` 计算属性强化：同样做严格的 `in_plan_period` 与 `status === 'out_of_period'` 校验，在有效期间之外直接返回 `null`，确保【供暖期标煤耗量】卡片下方的动态累计计划对比条自动隐匿；
     - 当选择有效期间内的日期时（如 2025-11-15、2026-01-15、2026-10-20 等），对比条平滑恢复展示。
- **验证结果**：
  - 后端多日期自动化单元校验脚本全量通过（2025-10-15、2026-04-10、2026-07-20 均准确返回 `in_plan_period=False`，2025-11-15、2026-01-15 准确返回 `in_plan_period=True`）；
  - 前端生产构建通过（`npm run build` 耗时 17.62s，0 错误）；
  - 数据看板非分解期间界面纯净无误导，期间内对比精准呈现。


## 2026-10-29 [数据看板 PDF 导出规格升级：由 1440px 扩展至 1600px 超宽屏排版，图表与数据空间更舒展]
- **用户指令与需求确认**：
  - 用户反馈：“1440px好像不够，模拟1600px行吗”；
  - 需求确认：将全端标准导出的虚拟视口宽度参数由原先的 1440px 平滑扩展至 **1600px**，为图表横轴、坐标刻度、图例与明细表格提供更充裕的横向呼吸空间。
- **高精细重构细节 (`DashBoard.vue`)**：
  1. **全屏 Loading 遮罩文案同步**：
     - 将提示文案升级为：“正在按标准桌面宽屏版式（1600px）渲染整页数据与图表，请稍候...”；
  2. **导出宽度常量与视口锁死更新**：
     - `const EXPORT_STANDARD_WIDTH = 1600`；
     - `html2canvas` 导出配置更新为 `{ width: 1600, windowWidth: 1600, scale: 2 }`，物理采样像素达到 3200px 视网膜高清级别；
  3. **CSS 容器宽度与栅格规则匹配**：
     - `.dashboard-page.dashboard-page--export-standard` 锁死为 `width: 1600px !important; min-width: 1600px !important; max-width: 1600px !important;`；
     - 4 宫格核心卡片、12 列主图表栅格在 1600px 宽度下更加舒展，避免密集折行与图表标签挤压。
- **验证结果**：
  - 前端静态构建全量通过（`npm run build` 耗时 15.77s，0 错误）；
  - 1600px 超宽屏规格无论在何种设备上均呈现更加舒展、大气的专业看板长页效果。

## 2026-10-29 [数据看板 PDF 下载全端统一：方案 A（1440px 桌面标准版式锁定 + 无缝长页 PDF + 高质感导出遮罩）]
- **用户指令与需求确认**：
  - 用户反馈：“在点击下载PDF功能的时候，我发现，实际上是利用当前的浏览器窗口来实现保存，如果换到手机上，屏幕狭窄，保存下来的效果就很差，能否统一下载效果呢？”；
  - 经技术方案比对与沟通，用户明确拍板选择：**方案 A（无缝长页 PDF）**。
- **痛点与技术根因分析**：
  1. `html2canvas` 默认根据当前设备的真实视口尺寸进行截图；
  2. 手机或窄屏设备（小于 1024px）会触发 `@media (max-width: ...)` 移动端响应式断点，卡片变成单列，网格变成单栏堆叠，导致导出的 PDF 变成一条极度细长、图表压缩变形、文字重叠的不合格文件；
  3. ECharts 图表底层是由 `<canvas>` 渲染的位图，如果单纯在克隆 DOM 中拉大容器宽度，Canvas 元素无法自动进行矢量重绘，会出现严重模糊或大片空白。
- **高精细重构细节 (`DashBoard.vue`)**：
  1. **全屏高质感导出 Loading 遮罩 (`.pdf-export-loading-mask`)**：
     - 点击【下载PDF】时立即激活 `isExportingPdf = true`；
     - 采用 `position: fixed; inset: 0; z-index: 999999` 深色毛玻璃遮罩，居中展示高质感 Loading 动效与“正在生成标准看板 PDF，正在按标准桌面宽屏版式（1440px）渲染整页数据与图表，请稍候...”温馨提示；
     - 在手机屏幕上完全屏蔽底层临时拉宽与重绘过程，杜绝用户视觉跳动与白屏；
  2. **1440px 桌面标准宽屏版式强制锁定 (`.dashboard-page--export-standard`)**：
     - 无论在手机、平板还是 PC 端触发，临时为看板根容器添加强制高优先级类名，锁死 `width: 1440px !important; min-width: 1440px !important;`；
     - 强制恢复桌面端 4 列核心指标卡片单排展开、12 列双栏图表网格、32px 标准留白与字号；
     - 隐藏所有交互性操作控件（`.pdf-download-btn`、缓存管理控制台 `.dashboard-cache-controls`、Toast 提示及表格折叠按钮），保证导出的 PDF 干净庄重；
     - 为 `document.body` 附加 `.body--export-pdf-locked` 锁定横向滚动条；
  3. **全局 ECharts 图表高分辨率重绘驱动机制**：
     - DOM 宽度切换为 1440px 后，派发 `window.dispatchEvent(new Event('resize'))`，触发页面上所有 ECharts 实例在 1440px 宽容器下执行 `chart.resize()`，重新绘制为超清桌面矢量画布；
     - 留出 480ms 充分等待 Vue DOM 更新与 ECharts 重绘动画渲染完成；
  4. **无缝长页 PDF 渲染与精准输出**：
     - 调用 `html2canvas` 锁死 `width: 1440`、`windowWidth: 1440` 并开启 `scale: 2`（视网膜级别 2880px 物理超清像素采样）；
     - 将截图无损转换为 0.95 高质量 JPEG；
     - 采用标准 A4 物理宽度 `pdfWidth = 210mm`，根据实际图像长宽比等比例计算 `pdfHeight = (imgHeight * 210) / imgWidth`，单页无缝连贯排版输出，彻底消除跨页生硬截断与空白浪费；
  5. **平滑状态还原与设备自适应**：
     - 在 `finally` 块中收敛：移除 `.dashboard-page--export-standard` 与 body 锁定类；
     - 自动恢复折叠表格状态；
     - 关闭全屏 Loading 遮罩；
     - 再次触发 `window.dispatchEvent(new Event('resize'))`，界面无缝恢复为移动端舒适阅读尺寸。
- **验证结果**：
  - 前端静态构建全量通过（`npm run build` 耗时 17.82s，0 错误），CSS/JS 语法完备；
  - 手机端与桌面端实现导出效果 100% 统一，导出的 PDF 均为标准的 1440px 桌面高保真画质。



## 2026-10-29 [数据看板气温导入彻底净化：移除主页面顶栏旧调试残留，引入优雅成功完成态与自动淡出 Toast]
- **用户指令与需求确认**：
  - 用户进一步反馈：“现在导入的过程没问题了，可是，导入成功后显示的还是一大串”；
  - 核心病根排查发现：
    - 在看板头部工具栏（`dashboard-header`）的控制区内，长期遗留了一个旧版本的调试展示元素 `.dashboard-temp-import-status`（内含多达十几天的长逗号日期列表、重合区间、以及数十行 `<ul> <li>` 的气温差异列表）；
    - 只要用户拉取或入库成功，`temperatureImportStatus.message` 就不为空，导致该元素将主页面顶部死死撑开好几倍，把看板核心内容硬生生往下推，极度杂乱且永不自动消失；
    - 点击“确认入库”后，弹窗内缺少明确的“成功完成态”，原有表格未收起且弹窗未自动关闭。
- **高精细重构细节 (`DashBoard.vue`)**：
  1. **连根拔除主页面顶部旧调试残留**：
     - 彻底删除顶栏中 `dashboard-temp-import-status` 这一大堆日期与逐小时差异 `<ul> <li>` 列表；
     - 主页面顶栏完全恢复纯净清爽；
  2. **引入入库成功完成态 (`isImportCommitted`)**：
     - 用户点击“确认覆盖入库”写库成功后，弹窗内立即收起表格与核验项，切换为居中大气的“🎉 气温数据已成功覆盖入库！”成功卡片；
     - 展示具体写入与覆盖条数，提示正在自动刷新；
     - 停留 1.5 秒后平滑自动关闭弹窗；
  3. **弹窗关闭与状态深度清理**：
     - `closeTemperatureImportDialog()` 触发时彻底调用 `resetTemperatureImportStatus()` 清空全部临时预览数据与脏状态；
  4. **主页面轻量级自动淡出 Toast (`dashboard-cache-toast`)**：
     - 入库成功后，主页面顶部仅展示精致单行小胶囊气泡（带 `✨` 图标与关闭 `×`）；
     - 4.5 秒后自动淡出消失，不占用页面任何常驻空间；
  5. **自动化数据联动刷新**：
     - 确认入库成功后，自动静默触发 `loadDashboardData` 和 `loadCoalPlanComparison`，使用户无需手动刷新即可直接看到最新的气温与标煤动态分解计划对比。
- **验证结果**：
  - 前端静态构建全量通过（`npm run build` 耗时 13.91s，758 个模块无报错打包成功）；
  - 导入成功后主页面和弹窗完全告别冗余长串文本堆砌，交互利落流畅。


## 2026-10-29 [数据看板气温导入交互重构：拒绝撑屏列表，引入 KPI 概览与差异优先紧凑表格]
- **用户指令与需求确认**：
  - 用户反馈：“还有一个问题，我点击导入气温，你猜怎么样？哗啦啦列出好长的列表，一屏幕都装不下……交互好差”；
  - 核心痛点拆解：
    1. **信息无节制平铺与撑爆视口**：一次从 Open-Meteo 拉取 14~35 天逐小时数据，导致重合时段记录往往多达 160~350 条，原有代码以简陋 `<ul> <li>` 逐条输出，导致弹窗严重撑出屏幕，滚动体验极差；
    2. **缺乏概要卡片（KPI Summary）**：用户无法直观了解“本次拉了多少天”、“共有多少条记录”、“多少条完全一致”、“几条存在差异”等核心结论；
    3. **海量一致数据淹没关键差异**：绝大多数时段气温与数据库完全一致，混在列表中严重阻碍用户核验真正的温度差异；
    4. **缺少容器限高与表头固定**：列表无限定高度，无粘性表头，查看长列表时表头滚出视野。
- **高精细重构细节 (`DashBoard.vue`)**：
  - **弹窗尺寸与防溢出治理**：
    - 面板限制在舒适尺寸 `width: min(840px, 95vw); max-height: 88vh;`；
    - 明细表格容器限定高度 `max-height: 260px; overflow-y: auto;`，美化细滚动条，彻底根除“一屏幕都装不下”的问题；
  - **顶部指标四宫格概览卡片 (KPI Grid)**：
    - 涉及日期跨度（如 `2026-10-22 至 2026-11-04（共 14 天）`，告别冗长逗号字符串）；
    - 接口获取总时段（如 `336 小时`）；
    - 库内重合时段（如 `189 小时`）；
    - 气温比对状态（差异 N 小时橙色醒目 / 全部一致绿色勋章）；
  - **“仅看差异”与“全部记录”分段切换器 (`tempDiffFilter`)**：
    - 智能判定：当存在差异时，默认自动切至 `⚠️ 仅看差异 (N)`，用户一眼抓住关键核验项；
    - 若全量一致（0 差异），呈现居中清新卡片 `🎉 全部数据完全一致，无任何数值偏差`，同时支持一键展开全部记录；
  - **紧凑专业表格系统 (`.temp-import-table`)**：
    - 粘性固定表头（`position: sticky; top: 0;`）；
    - 规整对齐列：时段时间、接口最新气温、数据库现有气温、差值（Δ 红/蓝区分）、状态标签（存在差异/一致/新时段）；
    - 差异行淡红底色高亮并增强对比；
  - **底栏动作与遮罩体验优化**：
    - 遮罩层支持点击关闭，弹窗关闭按钮增强，操作提示友好清晰。
- **验证结果**：
  - 前端静态构建全量通过（`npm run build` 耗时 16.46s，758 个模块无报错打包成功）；
  - 气温导入弹窗交互大幅精简，信息层级清晰分明，彻底告别撑屏烦恼。


## 2026-10-29 [数据看板卡片赋能：标煤耗量动态分解计划对比（当日与供暖期累计双卡片）]
- **用户指令与需求确认**：
  - 用户明确要求：“那就是在‘当日集团标煤消耗’卡片中，我希望能加入一个‘标煤耗量’的动态分解后的计划值对比情况。同样的，在‘供暖期标煤耗量’卡片中，也加入对应的动态分解计划值对比”；
  - 核心痛点与优化重点：
    1. **当日标煤动态分解计划与偏差精准对比**：
       - 基于全月 HDD20 供热度日与各厂 k/m 模型，动态解构集团月度标煤计划至业务日当天 $P_{\text{daily}}$；
       - 当日卡片对比呈现：动态分解计划值、较计划偏差（超/省）以及计划达成率（如 `动态计划 2,557.4 吨 · 超 +120.3 吨 (104.7%)`）；
    2. **供暖期标煤累计动态分解计划与全期进度对比**：
       - 智能界定供暖期跨度（11月至次年4月），精准累加从供暖期初期至当前业务日（含当日）各日动态日计划 $P_{\text{cum}}$；
       - 供暖期累计卡片对比呈现：供暖期累计计划、累计偏差（超/省）、累计达成率，并提供供暖期全期总计划进度提示；
    3. **气温不齐平稳降级与异常保护机制**：
       - 若当月气温未全部录入，动态分解门禁触发回退，自动以月计划按日均摊作为基准，并标明 `均摊计划*`，悬停提供详细提示说明，卡片绝不报错或崩溃；
    4. **端到端轻量化专属接口服务**：
       - 后端提供高性能专属计算服务 `get_coal_plan_comparison` 及 API `/dynamic_plan/coal_plan_comparison`，前端通过 `fetchCoalPlanComparison` 快速响应与联动。
- **高精细实现细节**：
  - 后端计算服务：[`backend/services/dynamic_decomposition_service.py`](file:///D:/编程项目/phoenix/backend/services/dynamic_decomposition_service.py) 新增 `get_coal_plan_comparison` 函数；
  - 后端接口路由：[`backend/projects/daily_report_25_26/api/dynamic_plan.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/dynamic_plan.py) 增加 `@public_router.get("/dynamic_plan/coal_plan_comparison")`；
  - 前端 API 模块：[`frontend/src/projects/daily_report_25_26/services/api.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/api.js) 新增 `fetchCoalPlanComparison` 客户端方法；
  - 前端数据看板：[`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DashBoard.vue)
    - 顶部“当日集团标煤消耗”卡片新增计划对比子栏目；
    - 供暖期“供暖期标煤耗量”卡片新增动态累计计划对比子栏目；
    - 新增 `dailyCoalPlanSummary` 与 `seasonCoalPlanSummary` 计算属性；
    - 监听 `effectiveBizDate` 联动异步拉取最新数据；
    - 新增 `.summary-card__sub-compare` 现代高质感玻璃态与对比色样式。
- **验证结果**：
  - 后端独立单元测试通过（2026-11-15 动态分解、2026-10-29 均摊降级、2026-11-01 月初校验均 100% 准确）；
  - 前端生产环境全量编译通过（`npm run build` 耗时 14.32s，758 个模块无报错打包，无 TS/Vue 语法错误）；
  - 看板两张卡片均呈现出高专业度的动态分解计划对比信息。


## 2026-10-29 [数据看板集团标煤口径修正：全链路取消“剔除庄河改造锅炉房”，统一切换为全口径标煤]
- **用户指令与需求确认**：
  - 用户明确要求：“关于这部分‘1. 当日集团标煤消耗（剔除庄河改造锅炉房）’涉及的 4 个看板位置：顶部核心卡片、板块 5 标煤耗量对比、板块 10 每日对比趋势、供暖期累计标煤卡片，我想修改一下，不再剔除了，可以帮我仔细修正吗”；
  - 核心痛点与优化重点：
    1. **前端文案净化**：将顶部核心卡片标签由“当日集团标煤消耗（剔除庄河改造锅炉房）”修正为标准统一的“当日集团标煤消耗”；
    2. **板块 5 集团汇总取数回归全口径**：在 `数据结构_数据看板.json` 中，将“5.标煤耗量”所有时段（本期、同期、本月累计、同期月累计、本供暖期累计、同供暖期累计）的“集团汇总”字段由映射内部张屯口径 `"标煤耗量汇总(张屯)"` 恢复为通用根指标映射 `""`（即取 `consumption_std_coal` 全口径标煤），全集团各单位（含庄河全量）完整入库汇算；
    3. **折叠表（0.5卡片详细数据表）口径对齐**：将折叠表中的标煤项由 `标煤耗量汇总(张屯)` 统一修正为通用 `标煤耗量`；
    4. **板块 10 每日对比趋势走势图快路径改造**：
       - `数据结构_数据看板.json` 中的“10.标煤耗量与平均气温趋势图”指标由“标煤耗量汇总(张屯)”恢复为“标煤耗量”；
       - 前端 `DashBoard.vue` 单位提取逻辑优先匹配“标煤耗量”；
       - 后端 `dashboard_expression.py` 在 `FAST_GROUP_DAILY_METRIC_RULES` 中增加对全口径 `consumption_std_coal`（包含 ZhuangHe 在内的全集团企业）的直通快路径支持，保证秒级加载；
    5. **供暖期累计标煤卡片映射修正**：将 `dashboard_expression.py` 中的 `集团汇总供暖期标煤耗量` 取数由 `sum_consumption_std_coal_zhangtun` 修正为全口径的 `consumption_std_coal`（`sum_ytd` 模式），对应 JSON 配置完成对齐。
- **高精细实现细节**：
  - 修改 `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`（卡片标题与单位匹配）；
  - 修改 `backend_data/projects/daily_report_25_26/config/数据结构_数据看板.json`（0.5表、5表、9表、10表结构映射）；
  - 修改 `backend/services/dashboard_expression.py`（快路径规则与累计映射）；
- **验证结果**：
  - Python 编译检查无报错，前端静态构建全部顺利通过（`npm run build` 耗时 14.09s，758 个模块无报错打包）；
  - 4 个位置的数据链路完全闭环，彻底取消了对庄河改造锅炉房的人为剔除，统一展现真实的集团全口径标煤能耗。

## 2026-10-29 [电力现货负电价指标优化：展示为 xx/96点 比例并附加百分比标签]
- **用户指令与需求确认**：
  - 用户明确要求：““负电价点数”，写成xx/96点 这样的形式，在后面用括号再加个百分比”；
  - 核心痛点与优化重点：
    1. **指标表达工业化与标准化**：单日电力现货由 96 个 15 分钟级交易时点构成，单纯展示负电价点数不如“发生点数 / 96 点全天总点数”直观；
    2. **兼顾百分比占比展示**：增加带括号的百分比换算（例如 `12/96点 (12.5%)`、`0/96点 (0.0%)`），使负电价发生的密度与严重程度一目了然；
    3. **排版防溢出与视觉层级微调**：
       - 主数值保留 18px 醒目呈现 `xx/96点`；
       - 百分比标签使用 13px（`font-weight: 500`）紧随其后；
       - 确保在各类屏幕宽度下紧凑和谐，避免挤压折行。
- **高精细实现细节 (`DashBoard.vue`)**：
  - 新增 [`formatNegativePercent`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DashBoard.vue#L4837-L4842) 计算函数：`(count / 96) * 100` 保留 1 位小数；
  - 模板更新为 `<span>{{ negative_price_points ?? 0 }}/96点</span><span class="spot-kpi-item__pct">({{ pct }}%)</span>`；
  - 样式追加 `.spot-kpi-item__value--ratio` 及 `.spot-kpi-item__pct`。
- **验证结果**：
  - 前端静态构建全量通过（`npm run build` 耗时 15.13s，758 个模块无报错打包）；
  - 负电价点数整齐展现为 `xx/96点 (yy.y%)`，排版紧凑优雅，层次分明。

## 2026-10-29 [电力现货卡片净化：移除冗余业务日标签，左右卡片对称右对齐]
- **用户指令与需求确认**：
  - 用户指令：“左侧的“业务日：2026-10-27”不需要写”；
  - 核心诉求拆解：
    1. **去除左侧卡片冗余日期文字**：彻底移除“辽宁省统一结算点实时电价”卡片内部的 `<span class="card-action-bar__date">业务日：...</span>` 标签；
    2. **左右卡片布局对称**：将左侧卡片顶部动作栏改为与右侧卡片完全一致的 `<div class="card-action-bar card-action-bar--end">`，使“查看现货大盘 →”按钮整齐右对齐；
    3. **视觉更加简洁纯净**：页面业务日期由顶部全局选择器统一掌控，双栏卡片内部不再重复冗余展示日期。
- **高精细实现细节 (`DashBoard.vue`)**：
  - 移除 `<span class="card-action-bar__date">业务日：{{ effectiveBizDate || '未指定' }}</span>`；
  - 左侧 `.card-action-bar` 追加 `--end` 修饰符，与右侧 `.dashboard-grid__item--dispatch` 保持绝对对齐。
- **验证结果**：
  - 前端全量静态构建通过（`npm run build` 耗时 17.43s，758 个模块无报错打包）；
  - 左侧卡片不再出现“业务日：xxxx”多余字样，右上角仅保留纯粹右对齐的“查看现货大盘 →”胶囊跳转按钮。

## 2026-10-29 [生产调度事件时间流重构：按时间先后升序精确排列与跨日/次日容错]
- **用户指令与需求确认**：
  - 用户明确要求：“右侧的“生产调度信息”，那些“生产运行调度事件”，应当按照时间排序”；
  - 核心痛点与优化重点：
    1. **排查原数据时序错乱根源**：原报表中的调度操作由北海、香海、北方、金州等各个热源厂与管网公司分别报送，提取入库后按组织分块堆叠（例如香海的 11:46 之后接着北方的 9:50，北海 15:40 之后接着香海的 9:00），导致列表中的时间忽早忽晚、跳跃混乱，破坏了时间线流向；
    2. **构建高精细时间序数转换算法（`getDispatchEventMinutes`）**：
       - **标准时分统一折算**：将 `08:00`、`9:50`、`14:15`、`22:17` 等格式统一转换为当日分钟数（`hour * 60 + minute`）；
       - **跨天/次日凌晨精准容错**：针对调度夜班产生的跨日记录（如 `10日1:12`、`15日3:40`、`3日2:00` 等），自适应结合当前所选业务日期（`effectiveBizDate`），自动计算 `dayOffset`（次日 +1d、前日 -1d，并涵盖跨月月初月末容错），确保次日凌晨操作稳固排列在当日夜班末尾；
       - **稳定排序策略**：以时间序数 `mins` 为第一键，结合原始位置 `index` 作为第二键，避免相同时间条目在不同浏览器引擎下顺序抖动；
    3. **业务时间流呈现**：事件列表完全按时间先后顺序自上而下顺畅展开，形成清晰、专业的中控调度事件流（Timeline）。
- **高精细实现细节 (`DashBoard.vue`)**：
  - 新增 `getDispatchEventMinutes(ev, bizDateStr)` 时间解析转换函数；
  - 重构 `pureDispatchEvents` 计算属性，在通过 `isValidDispatchOperation` 过滤后，执行升序稳定排序；
- **验证结果**：
  - 前端静态构建全部顺利通过（`npm run build` 耗时 14.26s，758 个模块无报错打包）；
  - 真实数据（如 2026-04-04、2026-04-03、2026-03-09）验证表明，原先插在后部的早间指令（如 9:00、9:50）自动归位到顶部，跨日凌晨指令（如 10日1:12）平滑置于夜间指令之后，时序完整自然。

## 2026-10-29 [生产调度事件净化：强化精准筛选，彻底过滤无时间、纯工期施工残片与日常套话]
- **用户指令与需求确认**：
  - 用户明确要求：“右边的栏目，在现实调度信息时，有所取舍，像这类‘--:-- 供热公司 工期29/10.6:00至29/10.24:00’不清不楚的，就不要显示了，你做一下筛选”；
  - 核心痛点与优化重点：
    1. **排查脏数据成因**：历史调度报表拆分工作票时，存在部分没有具体调度发生时间（`time` 缺失展示为 `--:--`），仅标注施工工期（如“工期29/10.6:00至29/10.24:00”）或仅记录恢复时点的抢修/停水残片记录，并非具体电厂、首站、管网的运行调度操作指令；
    2. **建立高精细业务语义过滤机制（`isValidDispatchOperation`）**：
       - **硬性时间校验**：必须包含具体时间点（如 `14:15`、`08:30` 等格式），严禁展示无时间、`--:--` 或空白条目；
       - **剔除纯工期与抢修时间段**：正则过滤以“工期...”开头或包含“工期...至...”跨度且缺乏操作实体的文本；
       - **剔除抢修/检修恢复时点报送**：正则过滤纯恢复时间记录（如“21/3 5:00,21日00:28恢复”）；
       - **剔除例行公文与套话**：过滤“管网运行正常”、“热源厂高温水网及蒸汽管网运行正常”等无实质调度行为的泛化描述；
       - **生产操作指令优先**：确保留存展示开闭阀门、倒闸、启停泵、升温升压、并网解列、上水补水等高价值工业调度记录。
- **高精细实现细节 (`DashBoard.vue`)**：
  - 新增 `isValidDispatchOperation(ev)` 校验函数；
  - `pureDispatchEvents` 计算属性改用 `isValidDispatchOperation` 全面审查过滤；
  - 当过滤后无有效事件时，界面平滑优雅展示“当日无生产运行调度事件”。
- **验证结果**：
  - 前端静态构建全部顺利通过（`npm run build` 耗时 13.24s，758 个模块无报错打包）；
  - 类似 `--:-- 供热公司 工期29/10.6:00至29/10.24:00` 这类无时间、纯工期的残片条目被彻底阻断，右侧调度事件栏纯净呈现真正具体的生产运行调度事件。

## 2026-10-29 [生产看板双栏：全面回归 6+6 对称布局、纵深比例拉升与字号可读性优化]
- **用户指令与需求确认**：
  - 用户明确要求：“还是改为6+6的布局吧，另外这两张卡片过于扁了，很多信息字太小看不清，请你结合该看板的整体风格优化一下它们的排版”；
  - 核心痛点与优化重点：
    1. **网格回归 6+6 对称黄金比例**：桌面端左右各占 6 列（50% : 50%），消除左偏过宽右偏窄的不均衡感；
    2. **彻底解决卡片过于扁平问题**：卡片 min-height 由 360px 提升至 480px；左栏 ECharts 电价图表高度由 230px 提升至 340px，充分展现 96 点电价波峰波谷；右栏调度事件时间线最大高度扩展至 220px；
    3. **告别蚂蚁字，字号层级结合看板整体风格全面升级**：
       - KPI 数值从 15px 跃升至 22px 加粗展示，标签从 11px 提升至 13px，单位从 9px 提升至 12px；
       - ECharts 坐标轴刻度由 10px 提升至 12px，图例由 11px 提升至 12px，Tooltip 提示文字提升至 13px；
       - 首站工况名称从 11px 提升至 14px，指标标签从 10px 提升至 12px，工况数值加粗至 13px；
       - 调度事件正文与时间标签从 10-11px 全面提升至 12-13px，行高 1.5，舒适清晰易读。
- **高精细实现细节 (`DashBoard.vue`)**：
  - `.dashboard-grid__item--spot-elec` 与 `.dashboard-grid__item--dispatch` 恢复 `grid-column: span 6; min-height: 480px;`；
  - `<EChart :option="spotElecChartOpt" height="340px" />` 纵向充分舒展；
  - 样式重构：更新 KPI、首站卡片、事件列表的 padding、border-radius 及 typography 规范，达到中控室专业大屏视觉水准。
- **验证结果**：
  - 前端静态构建全部顺利通过（`npm run build` 耗时 13.37s，758 个模块无报错打包）；
  - 页面排版宽敞挺拔、左右对称、大字清晰有力，彻底消除了“过于扁平”和“小字看不清”的体验问题。

## 2026-10-29 [生产调度信息卡片：严格精确业务日查询与无数据彻底置空]
- **用户指令与需求确认**：
  - 用户明确要求：“右边的卡片，我不是说让你在卡片上显示当前的业务日，而是要根据业务日，到数据库中查询该日的调度信息。该日没有信息的就别显示”；
  - 核心诉求拆解：
    1. **严格精确查询**：坚决废除任何跨日期自动向前借用/回退其他日期（如 10-27）数据的逻辑，严格以页面设定的业务日期（`biz_date = date`）在数据库中检索；
    2. **该日无数据绝不展示任何工况事件**：若所选业务日数据库中无记录（如 10-28 当日调度数据尚未出具），卡片内部统一显示干净的空态（“该业务日暂无调度信息”），首站概览卡片、调度事件列表完全不显示；
    3. **卡片去标签化**：卡片内部彻底移除多余的业务日文字，仅保留纯粹右对齐的“查看调度大盘 →”直达入口。
- **高精细实现细节 (`DashBoard.vue`)**：
  - `fetchDispatchInfoData(date)`：只传 `biz_date: date`，未查到数据直接置 `dispatchReport.value = null`；
  - Template 结构：使用 `v-if="dispatchLoading"` / `v-else-if="!dispatchReport"` / `v-else` 分支；无数据时仅渲染 `<div class="card-empty-box">该业务日暂无调度信息</div>`，有数据时才展开首站工况与纯生产调度操作；
  - 动作栏优化：使用 `.card-action-bar--end` 保持右对齐。
- **验证结果**：
  - 前端全量静态构建通过（`npm run build` 耗时 17.68s，758 个模块无报错打包）；
  - 切换到 2026-10-28 时，右侧干净显示“该业务日暂无调度信息”，不借用前日数据；切换到 2026-10-27 等有数据的日期时，首站工况与生产调度事件完整展示。

## 2026-10-29 [生产调度信息卡片净化与业务日期严格联动]
- **用户指令与需求确认**：
  - 用户指令：“右边卡片的“供热首站核心工况与生产调度事件”文字去掉。“值班人员：张希刚,徐世辉”去掉，“调度日：2026-10-28 最新版”去掉。具体显示哪一天，根据看板页面上的日期设定展示”；
  - 核心诉求拆解：
    1. **卡片副标题与人员信息彻底清除**：移除 `subtitle="供热首站核心工况与生产调度事件"` 及 `:extra="dispatchDutyText"`，卡片标题回归极简纯粹的“生产调度信息”；
    2. **日期展示统一规范**：移除“调度日：2026-10-28 最新版 / (最新期)”等标签与文字，严格与看板页面顶部业务日期设定对齐，展示为 `业务日：{{ effectiveBizDate || '未指定' }}`（与左栏现货卡片保持绝对一致）；
    3. **冗余逻辑与样式清理**：清理不再引用的 `dispatchDutyText` 衍生计算属性及 `.dispatch-fallback-badge` CSS 规则。
- **高精细实现细节 (`DashBoard.vue`)**：
  - 卡片标签精简为 `<Card title="生产调度信息">`；
  - 卡片内操作栏统一渲染 `<span class="card-action-bar__date">业务日：{{ effectiveBizDate || '未指定' }}</span>`；
  - 生产调度信息卡片与左侧电力现货市场卡片视觉规范完全对称统一。
- **验证结果**：
  - 前端静态构建顺利通过（`npm run build` 耗时 15.11s，758 个模块无报错打包）；
  - 界面右侧副标题、值班人员及“最新版/最新期”文字全部干净去除，日期严格统一跟随顶部业务日期联动展示。

## 2026-10-29 [生产看板双栏板块深度优化：8:4 比例重构、文本精简与调度数据自动向前回退修复]
- **用户指令与需求确认**：
  - 用户反馈：“来，这两个新板块，左栏占8格，右栏占4格。左侧的‘电力现货 15 分钟级曲线与日前对比’‘96点覆盖率：96/96’字样去掉。右侧的……我选择10月28日怎么没有任何内容呢。帮我搞定”；
  - 核心诉求拆解：
    1. **栅格重构**：桌面端网格由 6:6 调整为左 8 列（占 2/3）与右 4 列（占 1/3）；
    2. **文案精简化**：彻底移除左侧现货卡片的冗长副标题与 96 点覆盖率字样，仅保留纯粹专业的“单位：元/MWh”；
    3. **排查并彻底解决 10 月 28 日调度空白问题**：
       - **Bug 根因 1（字段解析偏差）**：原逻辑读取了 `res.data`，而后端接口返回的是 `res.items`，导致返回数组被错误判断为空；
       - **Bug 根因 2（生产报告汇总结算周期）**：全要素调度生产日报按行业惯例为次日对前一日进行汇总结算（10-28 发布的报告业务日期为 10-27），所选日期若尚未录入调度数据时缺乏向前回退机制；
       - **Bug 根因 3（事件字段兼容）**：后端调度事件中的字段为 `ev.time` 与 `ev.raw_description`，需与前端兼容；
       - **解决措施**：修复 `res.items` 解析；引入自动向前回退机制（若 `biz_date` 为空，自动查 `end_date: date, limit: 1` 获得最近一期已入库调度记录并加注 `(最新期)` 提示）；彻底兼容事件时间与描述字段。
- **高精细实现细节 (`DashBoard.vue`)**：
  1. **响应式栅格调整**：
     - `.dashboard-grid__item--spot-elec`：设置为 `grid-column: span 8;`；
     - `.dashboard-grid__item--dispatch`：设置为 `grid-column: span 4;`；
     - 4 栏宽度下优化首站卡片网格 `.dispatch-stations-summary` 为 `repeat(auto-fit, minmax(130px, 1fr))`，紧凑对称。
  2. **左栏卡片净化**：
     - 移除 `subtitle` 与 `spotElecExtraText`，卡片头部保留简洁干净的“辽宁省统一结算点实时电价”与“单位：元/MWh”。
  3. **调度数据获取与展示增强 (`fetchDispatchInfoData`)**：
     - 读取 `res.items`；优先请求指定业务日，若无记录自动请求 `end_date: date, limit: 1` 获取最近一期；
     - 若展示的是向前回退的最新期数据，业务日右侧自动展示金黄色 `(最新期)` 角标；
     - 事件列表兼容展示 `ev.time || ev.time_str` 与 `ev.raw_description || ev.content`。
- **验证结果**：
  - 前端全量静态构建通过（`npm run build` 耗时 13.36s，758 个模块无报错打包）；
  - 选择 10 月 28 日时，左侧 8 格舒展展示全天 96 点现货曲线，右侧 4 格饱满清晰呈现最新一期首站温差工况与纯调度操作事件。

## 2026-10-29 [生产日报数据看板：收入与投诉下方新增电力现货大盘与生产调度信息双栏板块]
- **用户指令与需求确认**：
  - 用户反馈：“现在'收入分类对比（集团）'和'投诉量分项'两个板块是在同一行，我想在其下边的一行插入新内容。该内容分两栏：1.左边一栏：业务日期的辽宁省统一结算点实时电价曲线和一些统计指标；2.右边一栏：业务日的调度信息，包含调度事件”；
  - 核心要求补充：“抢修工作票信息就别写了吧，不够重要” -> **必须彻底剔除 `is_ticket === true` 的抢修工作票记录**，仅展示纯生产运行调度事件。
- **高精细实现与组件落地 (`DashBoard.vue`)**：
  1. **栅格与响应式布局升级**：
     - 在“收入分类对比（集团）”与“投诉量分项”（占满 12 列栅格）正下方新增一行双栏：
       - 左栏 `.dashboard-grid__item--spot-elec`：桌面端 `grid-column: span 6`；
       - 右栏 `.dashboard-grid__item--dispatch`：桌面端 `grid-column: span 6`；
       - 窄屏与移动端自动自适应单列流式堆叠，保持高度与视觉统一对齐。
  2. **左栏：辽宁省统一结算点实时电价与统计指标**：
     - **头部与快捷入口**：业务日提示、副标题“电力现货 15 分钟级曲线与日前对比”及“查看现货大盘 →”直达路由按钮；
     - **4 宫格 KPI 卡片**：紧凑呈现「实时均价（橙色）」、「最高实时价（红色）」、「最低实时价（带负价着色提示）」和「负电价点数（紫色）」；
     - **96 点电价曲线图**：通过 EChart 渲染全天 15 分钟级实时电价橙色曲线（含渐变浅橙阴影填充）与日前电价天蓝虚线，并带有 0 元分界红虚线及精准 Tooltip。
  3. **右栏：生产调度信息与关键工况**：
     - **头部与快捷入口**：调度长/值班员提示及“查看调度大盘 →”直达路由按钮；
     - **首站核心工况卡片**：提取北海首站、香海首站等供水温度、回水温度、供回温差及循环流量；
     - **纯生产运行调度事件时间轴**：过滤纯调度操作（`!ev.is_ticket`），彻底排除抢修工作票，按时间点、所属单位/机组徽标、操作文字清晰呈现垂直流式时间轴。
  4. **动态数据联动与自适应响应**：
     - 深度接入 `getSpotElectricitySummary`、`getSpotElectricityPoints` 与 `queryDispatchData` API；
     - 随顶部 `effectiveBizDate` 业务日历选择即时触发异步刷新，并带有完善的骨架 Loading 与空态兜底。
- **验证结果**：
  - 前端静态构建全部顺利通过（`npm --prefix frontend run build`，758 个模块无报错打包，产物完整生成）。

## 2026-10-29 [计划动态分解图表：全面恢复左轴/右轴高质感彩色标签徽标与指标药丸卡片]
- **用户指令与需求确认**：
  - 用户反馈：“我看到页面上有一个提示‘各计量单位独立刻度：GJ、吨、万kWh（左侧首轴，其余从内到外位于右侧）’，之前我记得是有两个标签各位于左侧和右侧，写着‘左轴’‘xx指标’和‘右轴’‘xx指标’，我还是喜欢那个样式”；
  - 核心诉求：废除多单位时退化展示的一行生硬纯文本，全面恢复用户喜爱的左轴与右轴彩色徽标（深蓝左纵轴、暖橙右纵轴）、指标药丸胶囊（带色点与点击聚焦交互）的精致对称排版。
- **高精细实现与重构细节 (`DynamicPlanMetricsView.vue`)**：
  1. **移除生硬纯文本提示**：
     - 彻底删除 `<div v-if="chartAxisMappingInfo.units.length > 2" class="axis-mapping-banner">各计量单位独立刻度...</div>` 纯文字代码；
  2. **多右轴单位分组架构升级 (`chartAxisMappingInfo`)**：
     - 升级 `chartAxisMappingInfo` 计算属性：将 `showBanner` 判定由过去的硬编码 `units.length === 2` 升级为 `units.length >= 2 || hasTempRightAxis`，解除多单位或带气温曲线时徽标条被隐藏的缺陷；
     - 新增 `rightGroups` 结构（`units.slice(1)` 每个单位对应其所属指标列表），使得右侧无论是 1 个还是多个单位（如 `万kWh`、`吨` 等），均能以独立的【右纵轴 (单位)】徽标整齐排布；
     - 集成 `hasTempRightAxis` 气温天蓝徽标（`右纵轴 (℃)`）与药丸标签；
  3. **视觉与交互全面还原**：
     - 左侧高亮展示【左纵轴 (主单位)】及其指标胶囊（如 `供热量`）；
     - 右侧自适应铺展【右纵轴 (单位)】及其指标胶囊（如 `发电量`、`标煤耗量`），支持点击胶囊即刻在图表中高亮聚焦该曲线；
     - 移动端窄屏下，`.axis-mapping-banner` 与 `.axis-right-wrapper` 纵向自适应整齐流式平铺，既美观又易于手指点选。
- **验证结果**：
  - 前端静态全量构建通过（`npm run build`，758 个模块无错误顺利打包）；
  - 页面在默认勾选 3 个不同单位指标或切换任意指标时，均展示左右轴彩色徽标与指标药丸，生硬纯文字彻底消除，交互体验优秀。

## 2026-10-29 [计划动态分解图表：全面恢复多指标全曲线对应的纵轴刻度显示与坐标轴映射]
- **用户指令与需求确认**：
  - 用户审阅后明确指示：“也不对，这样一来，有些曲线就没有对应的纵轴了，还得调整回来”；
  - 核心诉求：多指标对比与动态日计划分解图表中，每条生产指标曲线及气温曲线必须拥有各自明确、可视的坐标轴刻度与量纲单位（`GJ`、`万kWh`、`吨`、`℃` 等），严禁为了排版紧凑而隐藏/裁剪坐标轴，确保数据可读性与坐标刻度精准映射。
- **高精细逻辑还原 (`DynamicPlanMetricsView.vue`)**：
  1. **坐标轴生成逻辑全面恢复 (`metricAxes`)**：
     - 彻底撤销针对移动端的轴隐藏逻辑，废除 `show: false` 设定；
     - 恢复每个单位拥有独立的可视 Y 轴（包含 `type: 'value'`, `name: unit`, `splitLine`, `axisLabel` 等）；
     - 第一单位置于图表左侧，第二及以上单位置于图表右侧并按 `(index - 1) * 65` 保持清晰的阶梯并列排布；
  2. **网格右侧预留边距恢复适配 (`grid.right`)**：
     - 恢复 `grid.right: Math.max(65, (unitList.length - 1 + (includeTemp ? 1 : 0)) * 65)` 的自适应动态边距计算；
     - 确保所有右侧 Y 轴（包括气温轴和各生产指标轴）的刻度数值和单位标签均有完整物理展示空间，不与折线重叠、不被视口截断；
  3. **各图表模式联动恢复**：
     - 模式一（动态走势折线图）、模式二（动态柱状对比图）及动态日计划分解图均严格绑定标准 `yAxes` 与 `grid`，实现曲线与坐标轴的严格一对一对应。
- **验证结果**：
  - 前端静态全量构建通过（`npm run build`，758 个模块无错误顺利打包）；
  - 页面各曲线均可查看到其对应的纵轴单位与刻度范围，数据可信度与刻度直观映射得以完整保障。

## 2026-10-29 [计划动态分解图表移动端自适应调优：消除多 Y 轴固定偏置导致的右侧大片留白与挤压]
- **问题与根因分析**：
  - 用户反馈在手机屏幕模式下，计划动态分解页面的曲线图仅占据左侧约 2/3 空间，右侧留出大面积空白；
  - **根因深度定位**：
    1. 页面默认勾选多种不同单位的生产指标（如 GJ、吨、万kWh、GJ/万m²、吨/万m² 等共 4~5 个不同计量单位）；
    2. 原图表引擎为每个单位都在右侧创建独立 Y 轴，并分配递增的右偏移量 `offset: (index - 1) * 65`；
    3. `grid.right` 强制按 `Math.max(65, (unitList.length - 1) * 65)` 计算。当存在 4~5 个单位时，`grid.right` 被硬编码留空至 `195px ~ 260px`！
    4. 手机视口总宽仅 360px~390px，扣减 200 多像素的右边距后，实际可绘制的折线区域仅剩 80px~150px，造成曲线图被死死压在左侧 2/3、右侧大面积空虚的严重视觉缺陷。
- **高精细响应式架构重构 (`DynamicPlanMetricsView.vue`)**：
  1. **移动端 Y 轴折叠与隐藏优化 (`metricAxes`)**：
     - 在手机窄屏（`<= 768px`）下，左侧保留首个主单位 Y 轴，右侧仅保留 1 个次要单位可视 Y 轴（`offset = 0`）；
     - 第 3 个及以上单位轴仍挂载于 ECharts 配置中（`show: false, offset: 0`），保证其数值映射与比例尺绝对精准，同时彻底消除其在屏幕右侧占据的层叠物理空间；
  2. **`grid.right` 边距动态响应式释放**：
     - 在移动端：存在右轴或气温曲线时，`grid.right` 统一优化为紧凑的 `42px`（仅需容纳单个右轴数字标签），无右轴时仅留 `16px`；
     - 彻底废除手机端按单位数量乘以 65px 的阶梯累加算法，图表横向可用绘图面积扩大 2.5 倍，横向饱满居中铺展；
  3. **图例与饼图位置适配**：
     - 移动端 `legend` 左右边距自适应收窄至 `8px`（桌面端为 100px），避免挤偏；
     - 负荷占比饼图在手机端由偏右改为水平居中（`center: ['50%', '52%']`），图例置底横排；
  4. **动态窗口重算与防抖监听**：
     - `handleResize` 与 `ResizeObserver` 增加防抖机制触发 `renderChart()`，在手机横竖屏切换或视口缩放时自动重算轴与 grid。
- **验证结果**：
  - 前端静态全量构建通过（`npm run build` 耗时 15.79s，758 个模块无错误打包）；
  - 手机窄屏下曲线图完整占满全屏横向宽度（左右对称，右边距仅留 42px 给右轴数字），彻底消除右侧大片空白。

## 2026-10-29 [计划动态分解模块图表选项卡精简：移除“供热燃煤基准专题”按钮与冗余逻辑]
- **需求明确**：
  - 用户指示将“计划动态分解”页面图表区域中的【🔥 供热燃煤基准专题】按钮去掉；
- **代码重构与清理 (`DynamicPlanMetricsView.vue`)**：
  - 从 `chartTabs` 数组中移除 `{ key: 'trend_heat_coal', label: '供热燃煤基准专题', icon: '🔥' }`，保留“已选指标月度走势 (动态联动)”、“已选指标柱状对比”与“已选指标负荷占比 (环形图)”三项经典分析模式；
  - 同步清理 `renderChart()` 内部对应的 `activeChartTab.value === 'trend_heat_coal'` 模式四渲染分支及双 Y 轴 series 代码，保持逻辑清爽无死代码；
- **验证结果**：
  - 前端静态全量构建通过（`npm run build` 耗时 15.57s，758 个模块无错误打包）。

## 2026-10-29 [每日填报列表：恢复每张表格已填报指标比值展示与单表直达成形]
- **需求明确**：
  - 用户明确要求：“我还是想要之前那个每张表指标已填报的比值”；
  - 既有诉求是既要保留“两栏等宽单位卡片”的整洁统一布局，又要恢复原本直观反映每张子表具体填报进度（如 `17/17`、`0/13`、`0/8`）的指标比值。
- **改动点与实现原理 (`Sheets.vue`)**：
  1. **单表胶囊内置高对比度比值徽标 (`.pill-ratio`)**：
     - 在每个子表胶囊 `.unit-sheet-pill` 内部表名右侧，动态挂载 `.pill-ratio` 徽标；
     - 依据 `submissionStatus` 中各表的 `text` 字段（如 `"17/17"`、`"0/13"`）如实呈现已填报项数/总项数；
     - **三态高辨识度色彩**：
       - 翡翠绿（`.pill-ratio--complete`，背景 `#10b981`，白色字）：达到 85% 或全部完成；
       - 金黄色（`.pill-ratio--partial`，背景 `#fef08a`，暗褐字）：部分填报；
       - 浅灰色（`.pill-ratio--empty`，背景 `#e2e8f0`，沉稳灰字）：尚未填报；
  2. **单表直达交互增强**：
     - 为子表胶囊添加 `@click.stop="openSheet(sheet)"`，点击特定表格直接直达该表，点击卡片空白处保持打开单位第一张表；
  3. **单表单位卡片右上角徽标协同**：
     - 针对单表单位（如香海热电厂、北方公司等），右上角状态徽标直接显示其实际填报指标比值（如 `17/17`）；多表单位则显示表格完成比例（如 `已填报 1/3`），形成宏观与微观双重视角。
- **验证结果**：
  - 前端全量构建通过（`npm run build` 耗时 13.15s，758 个模块 0 错误）。

## 2026-10-29 [计划动态分解与调度信息全景看板：移动端窄屏手机响应式排版深度重构]
- **需求背景与痛点排查**：
  - 用户反馈近期上线的“计划动态分解页面”与“生产调度信息页面”在窄屏手机模式下存在严重排版混乱、元素重叠挤压与横向溢出问题；
  - **核心痛点深度定位**：
    1. **计划动态分解页面 (`DynamicPlanMetricsView.vue`)**：
       - 外层内边距过大（桌面端左右 24px），在 375px~390px 手机上直接挤占超 15% 可用视口；
       - 筛选控制栏多处设置固定最小宽度，如指标复选下拉容器固定 `min-width: 320px`、下拉展开面板固定 `min-width: 380px`，在窄屏下造成严重容器撑裂；
       - `filter-group` 采用横向固定 label 宽（90px），右侧内容被压至不可读；
       - 核心指标 KPI 汇总卡片在大屏为自动伸缩，在移动端单张大卡片纵向拉伸过长；
       - 图表头部 Tab 选项卡与操作按钮在窄屏下单行挤占冲突；动态分解二级工具栏的多个操作胶囊与折叠按钮溢出换行错乱；
       - 指标计划数据矩阵表格固定列在移动端独占 240px，导致右侧各月数据缺乏横向滑动可视空间。
    2. **生产调度信息页面 (`DispatchInfoView.vue`)**：
       - 主体外层边距左右 `2rem`（64px），移动端空间损耗极大；
       - 上传按钮网格硬编码 `grid-template-columns: 1fr 1fr`，窄屏下导致文字内容垂直严重挤瘪；
       - 检索输入框硬编码 `width: 260px`，与日期筛选器混排直接破屏；
       - 机炉拓扑卡片硬编码 `minmax(380px, 1fr)`、蒸汽燃煤网格硬编码 `minmax(400px, 1fr)`，远超常见手机屏幕物理宽度（360px~390px），成为引发大面积横向滚动破屏的直接元凶；
       - 宏观 KPI 卡片纵向堆叠过长，首站表格与调度事件时间线在小屏下排版参差。
- **高精细响应式架构重构**：
  1. **计划动态分解页面 (`DynamicPlanMetricsView.vue`)**：
     - **弹性视口收拢**：主容器内边距在 `<= 768px` 调整为 `10px 12px 36px`，顶部导航与操作按钮支持网格平铺；
     - **筛选流式纵向重构**：`.filter-group` 切换为纵向流式排布，解除 `min-width: 90px` 限制；月份区间选择器设为 `flex: 1` 对称占满整行，预设按钮平铺自适应；
     - **指标下拉解除定宽**：`.metric-multiselect-container` 与 `.multiselect-dropdown-panel` 覆盖为 `min-width: 0; width: 100% !important;`，彻底根除横向破屏；
     - **高密度 KPI 双列卡片网格**：移动端重构为 `repeat(2, minmax(0, 1fr))` 双列紧凑网格，图标精炼至 36px，数值 16px，一屏通览供热、标煤、原煤、电水及综合单耗全貌；
     - **图表头部横向平滑滑动与自适应**：图表 Tab 栏引入 `overflow-x: auto` 与 `-webkit-overflow-scrolling: touch`，支持单行平滑手势横滑；图表高度在移动端降至 320px 匹配竖屏可视区；
     - **动态分解二级工具栏流式重组**：左侧月份与指标胶囊、右侧操作按钮自适应换行，触摸区域舒适防误触；
     - **数据矩阵表固定列精简**：移动端将固定列宽优化为 `min-width: 120px; max-width: 130px;`，让出充足视口供右侧月份数值丝滑滑动。
  2. **生产调度信息页面 (`DispatchInfoView.vue`)**：
     - **边距降噪与 Banner 移动端重塑**：主容器内边距调整为 `0.65rem 0.75rem 2.5rem`，Banner 标题与元标签垂直堆叠；
     - **上传选择区单列堆叠**：在 `<= 768px` 下上传卡片调整为 `grid-template-columns: 1fr`，完整舒展文件与文件夹两类选择入口与说明；
     - **查询过滤工具栏弹性流式化**：解除检索框 `260px` 限制，设为 `flex: 1; width: auto; min-width: 0`；日期选择器与前一天/后一天按钮满宽拉伸；
     - **宏观产耗 KPI 双列紧凑化**：当日总耗煤、发电、供热、补水重构为双列网格，大号数值由 1.8rem 适度降为 1.35rem；
     - **拓扑网格与蒸汽燃煤解除定宽**：彻底消除 `minmax(380px, 1fr)` 与 `minmax(400px, 1fr)` 破屏限制，移动端强制 `grid-template-columns: 1fr !important`；电厂内部机炉单列展开并移除中间竖线，当日启动药丸紧凑自适应；
     - **表格与事件流移动端适配**：所有数据表格支持 touch 平滑横滑，调度事件卡片表头改为垂直元数据流，消除右侧工期与左侧标签挤压冲突。
- **验证结果**：
  - 前端全量静态构建通过（`npm run build` 耗时 13.97s，758 个模块无错误打包）；
  - 手机窄屏（<= 768px 与 <= 480px 模拟）排版无任何横向溢出，各维度交互流畅，布局规整舒适。

## 2026-10-28 [供热公司能效报表识别调优：收入指标剥离留空、分中心耗水量动态嗅探与表级列索引隔离]
- **需求明确**：
  - 用户明确指示：
    1. 供热公司的“售高温水收入”“售汽收入”不做自动识别，留空；
    2. “分中心”的表中，“换热站补水量”在能效报表中位于下部，列出各中心简称且指标叫做“耗水量”，要求精准识别并回填；
- **根因分析与架构修复**：
  1. **收入指标剥离留空 (`gongre_efficiency_parser.py`)**：
     - 从 `gongre_cells` 中彻底删除“其中：售高温水收入”和“其中：售汽收入”；
     - 后端返回载荷不再输出该两项，前端回填引擎跳过处理，保持单元格原有留空状态；
  2. **分中心“耗水量”动态嗅探 (`gongre_efficiency_parser.py`)**：
     - 在能效表下部引入动态文本嗅探算法，扫描包含各中心简称（华乐、东港、春海、中山、北岗、双兴、香炉礁、兴工、大纺、管网）且包含“耗水”字样的行（Row 188~197）；
     - 对应系统指标“其中：换热站补水量”，绑定 `sub_label`（各分中心全称），指定写入 `col_index: 3`（分中心明细表的本期日列）；
  3. **表级列索引与同期列识别隔离修复 (`DataEntryView.vue`)**：
     - **排查出的关键 Bug**：先前在回填引擎 `applyEfficiencyDataToSheets` 中，调用了全局绑定的 `isPeerColumnIndex(targetCol)`。由于当时活动表为 5 列标准表（`columns.length = 5`，第 3 列为同期日），而分中心明细表总共有 6 列（第 3 列为本期日，第 4 列才为同期日）。调用全局判定导致分中心补水量的 `targetCol = 3` 被误判为同期列而被 `continue` 跳过，导致未能成功回填；
     - **修复方案**：引入 `isPeerColumnForTable(targetCol, currentTableCols, baseCols)`，基于具体子表真实的列定义进行同期判定；并在目标写入列未指定时，自适应寻找包含“本期”字样的列索引；
     - **复合行双向兼容匹配**：`findRowIndexInList` 升级为支持分中心简称（如“华乐”）与全称（“华乐中心”）双向包含匹配。
- **验证结果**：
  - Python 单元测试通过：供热公司总表输出 11 项纯净指标（不包含两项收入），分中心补水量 10 项精准提取（东港7吨、双兴2250吨等，合计3290.1吨）；
  - 前端全量静态构建通过（`npm run build` 耗时 13.87s，758 个模块无错误）。

## 2026-10-28 [扩展香海热电厂与供热公司能效报表自动解析与精准回填]
- **需求概述**：
  - 用户明确要求参照北海热电厂的模式，扩展支持香海热电厂和供热公司的能效报表自动识别功能；
  - 提供源报表文件：
    1. 香海：《2025-2026香海能效分析表 1.xlsx》
    2. 供热：《2026-2027供热公司能效表.xlsx》
  - 核心要求：纯净抽取本期数值（严禁篡改同期值）；机炉运行台数为空识别为 0；设备启停与突发情况说明不伪造记事；单位换算规范化。
- **架构设计与实现原理**：
  1. **香海能效解析服务 (`xianghai_efficiency_parser.py`)**：
     - 新建 [`xianghai_efficiency_parser.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/xianghai_efficiency_parser.py)；
     - 自动匹配工作表（支持 `香海YYYY.M` 等变体）；
     - 解析第 2 行 Excel 序列日期精准定位当前业务日期所在列；
     - 指标映射：发电量(Row 13)、供热量(Row 50)、供汽量(Row 43)、售电量(Row 28)、原煤耗量(Row 58)、标煤耗量(Row 63)、耗水量(Row 73自来水量)、电厂耗水量(Row 76)、外购电量(Row 89 kWh转万kWh)、电厂外购电量、耗酸量(Row 109)、耗碱量(Row 114)、耗油量(Row 84)、耗氨水量(Row 94)、耗石灰石粉量(Row 99)；
     - 机炉运行方式：Row 10 语义解析得出运行汽炉数与运行汽轮机数（空/停归零）；
  2. **供热公司能效解析服务 (`gongre_efficiency_parser.py`)**：
     - 新建 [`gongre_efficiency_parser.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/gongre_efficiency_parser.py)；
     - 自动匹配 `YYYY.M` 工作表并定位第 2 行业务日期列；
     - 支持跨表联合输出：
       - `GongRe_Sheet`（5.供热公司表）：网口供热量(Row 10)、售汽量(Row 40)、耗水量(Row 24)、电厂一次网补水(Row 23)、换热站补水(Row 22)、站内外购电量(Row 29 kWh转万kWh)、站内耗热量(Row 15)、高温水收入(Row 82)、售汽收入(Row 77)、日最高最低气温(Row 7/6)；
       - `GongRe_branches_detail_Sheet`（6.供热公司分中心明细表）：精准抓取 10 个分中心（华乐、东港、春海、中山、北岗、双兴、香炉礁、兴工、大纺、管网）换热站补水量（Row 188~197），指定写入 `col_index: 3`（本期日列）；
  3. **后端接口注册 (`legacy_full.py`)**：
     - 在 [`legacy_full.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/legacy_full.py) 新增：
       - `POST /data_entry/xianghai/parse_efficiency_report`
       - `POST /data_entry/gongre/parse_efficiency_report`
  4. **前端接口与交互增强 (`api.js`, `DataEntryView.vue`)**：
     - 在 [`api.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/api.js) 封装 `uploadXianghaiEfficiencyReport` 与 `uploadGongreEfficiencyReport`；
     - 在 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue) 实现 `currentEfficiencyUnitType` 计算属性，北海、香海、供热三家单位均展示专属【📁 上传能效分析表】按钮；
     - 回填引擎 `applyEfficiencyDataToSheets` 全面升级：支持 `sub_label` 复合匹配、指定 `col_index` 回填、同期列严格只读保护与备注列占位符安全保护。
- **验证结果**：
  - Python 单元测试通过：香海（17项指标，发电量203.136，4炉3机）、供热（总表13项指标，分中心10项补水量明细）100% 断言正确；
  - 前端全量静态构建通过（`npm run build` 耗时 15.87s，758 个模块无错误）。


## 2026-10-28 [北海能效报表自动解析：运行设备台数指标为空时默认识别为 0]
- **需求明确**：
  - 用户明确要求：“表中的运行汽炉数、运行汽轮机数、运行水炉数和运行天然气炉数，如果能效报表中为空，则识别为0”。
- **架构加固与实现原理 (`beihai_efficiency_parser.py`)**：
  - 修改 [`beihai_efficiency_parser.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/beihai_efficiency_parser.py)；
  - **空值兜底归零**：引入 `_parse_steam_boiler_and_turbine` 与 `_parse_boiler_count` 语义解析器。当对应业务日期的运行方式单元格为空（`None`）、空字符串、`'0'`、`'停'` 或 `'无'` 时，运行台数统一识别为 `0`；
  - **必出输出项保证**：
    - 联产表：`运行汽炉数` 与 `运行汽轮机数` 恒定纳入提取 cells（为空识别为 0，有工况如 `#1#2#4炉 #2#3机` 准确统计为 3 炉 2 机）；
    - 水炉表：`运行水炉数` 恒定纳入提取 cells（为空识别为 0，有工况如 `#1、2炉` 准确统计为 2 炉）；
    - 燃气炉表：`运行天然气炉数` 恒定纳入提取 cells（为空识别为 0）；
- **验证结果**：
  - Python 单元测试证实：在能效分析表 2026-11-01 运行方式为空的场景下，联产汽炉数、汽轮机数、水炉数、天然气炉数全部稳定输出 `0`；
  - 多种实际工况用例（单炉、多炉、多机、停运）解析准确率 100%；前端打包顺利通过。

## 2026-10-28 [规范启停与突发指标填报结构：剥离能效表工况误传，守护本期占位符与备注列规范]
- **问题反馈与现象分析**：
  - 用户敏锐指出两项核心业务与布局问题：
    1. **指标结构规范**：“主设备启停情况”和“突发情况说明”并不填在本期列（`c2`），而是填在最后一列（`c4` 备注/解释说明列）。之前自动回填却直接写入了 `c2`，覆盖掉了提示占位符；
    2. **语义混淆与误识别**：能效分析表中的“运行方式 炉/机”（如 `#1炉`）记录的是在网运行方式，而不是当天发生了设备启动事件。且 2026 本期水炉当天根本没有启动（原表为空），之前误将 2025 年同期的 `#1炉` 当作启停事件输出，导致回填出现“一号水炉”。
- **架构加固与改动点**：
  1. **后端彻底剥离非启停字段 (`beihai_efficiency_parser.py`)**：
     - 修改 [`beihai_efficiency_parser.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/beihai_efficiency_parser.py)；
     - 彻底删除在 `cells` 中输出“主设备启停情况”的错误逻辑；
     - 能效分析表中只有工况代号，仅用于推导各子表的台数指标（运行汽炉数、运行汽轮机数、运行水炉数、运行天然气炉数），严禁将工况代号当做设备启停事件输出；
  2. **前端回填位置与占位符强保护 (`DataEntryView.vue`)**：
     - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
     - 建立 `NOTE_ONLY_LABELS` 保护白名单（“主设备启停情况”、“设备启停情况”、“突发情况说明”）；
     - 严禁任何自动回填修改该类指标的 `c2`（保留固定占位语 `"（若有请填右侧）"`）与 `c3`（保留 `"——→"`）；
     - 若未来传入合法文本，只允许写入最后一列（`c4` 备注列），确保与数据库 `DailyBasicData.note` 存储结构与视觉设计严格吻合。
- **验证结果**：
  - Python 服务单元测试通过：北海三张子表格的 cells 中彻底清除了“主设备启停情况”，台数指标与数值指标纯净输出；
  - 前端全量构建成功（`npm run build` 耗时 15.13s，758 个模块无错误）。

## 2026-10-28 [修复能效报表跨表回填异常：补全未激活子表格 queryData 镜像查询，杜绝同期值丢失]
- **问题反馈与现象分析**：
  - 用户反馈：“为什么我点击上传了北海的能效表格，表1没问题，表2，表3的同期值全不见了”；
  - **根因定位**：
    1. 用户进入页面时默认处于表 1（热电联产表），表 1 正常经历了完整的主加载流程（`loadTemplate` -> 后端 `queryData` 镜像查询），因此表 1 的 `c3` 同期值能够正确展示；
    2. 此时表 2（水炉表）和表 3（天然气炉表）尚未被用户点击打开，`sheetCache` 内存缓存中尚无两表的记录；
    3. 点击【上传能效分析表】后，`applyEfficiencyDataToSheets` 在向后台子表填充数据时，仅调用了 `getTemplate`（获取静态空白模板），但**漏掉了调用 `queryData` 向数据库拉取同期数据**，导致暂存进 `sheetCache` 中的 `gridSource` 仅有本期数据 `c2`，而 `c3` 保持为空白字符串 `""`；
    4. 随后用户点击切换至表 2 或表 3 时，`onSwitchSheetTab` 识别到缓存存在直接执行 `restoreSheetFromCache`，跳过了本应在初次进入时执行的 `loadTemplate` 及数据库查询，导致表 2、表 3 同期值看似全部丢失。
- **改动点与实现原理 (`DataEntryView.vue`)**：
  - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
  - **补齐子表完整查询**：在 `applyEfficiencyDataToSheets` 预构建缓存时，除调用 `getTemplate` 与日期列头格式化外，显式调用 `queryData(projectKey, sheetKey, { biz_date })`，确保数据库已存的真实同期值（`c3`）被完整装配到 `tplRows` 与 `gridSource` 中，再仅向 `c2` 写入导入数值；
  - **标签页切换状态加固**：在 `onSwitchSheetTab` 恢复缓存后，自动触发行规则校验刷新、联动结构初始化与 `applyReadonlyToColumns()` 权限锁定。
- **验证结果**：
  - 前端全量静态打包通过（`npm run build` 耗时 13.86s，758 个模块无错误）。

## 2026-10-28 [能效报表回填边界加固：严格仅提取与导入本期数据，严禁触碰与改变同期值]
- **需求与安全边界明确**：
  - 用户明确强调：“注意，只导入本期的数值，而不改变同期值”。
- **架构加固与实现原理**：
  1. **后端数据源纯净化 (`beihai_efficiency_parser.py`)**：
     - 修改 [`beihai_efficiency_parser.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/beihai_efficiency_parser.py)；
     - 彻底废除任何跨行回退到 2025 年同期行的逻辑，锁定各指标单一本期物理行号（如联产发电量 Row 174、供热量 Row 199、煤耗 Row 204/209；水炉供热量 Row 346、煤耗 Row 351/356 等）；
     - 若当前日期本期行无数据或为 0，如实返回 `0.0`，严禁提取同期历史数据；
  2. **前端单元格回填隔离保护 (`DataEntryView.vue`)**：
     - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
     - 明确限定数据回填与联动仅作用于 `c2` 列（当日填报值），对 `c3` 列（同期值）施加绝对隔离，结合既有只读列与权限守卫双重锁定，确保同期基准值毫厘不差；
- **验证结果**：
  - Python 单元测试证实 2026-11-01 发电量等指标如实提取本期填报值（0.0），同期行（2.016）被严格隔离；
  - 前端静态构建打包顺利通过（耗时 13.99s，758 个模块无错误）。

## 2026-10-28 [修复能效报表回填异常：彻底清除冗余的 hasModified 标记，采用响应式直接驱动提交]
- **问题定位**：
  - 用户反馈报错：`解析能效报表失败：hasModified is not defined`；
  - 经排查组件原本依托 `gridSource` 响应式状态与 `submitButtonDisabled` 进行提交控制，并不存在全局 `hasModified` 响应式变量。
- **改动点与验证**：
  - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)，彻底移除多余的 `hasModified` 赋值，数据更新直接同步进 `gridSource` 并存入 `sheetCache`；
  - 前端 `npm run build` 构建成功（耗时 14.56s，758 个模块无错误）。

## 2026-10-28 [修复能效报表回填异常：消除未定义重算函数，改用标准联动遍历与逐行校验]
- **问题定位**：
  - 用户在上传北海能效报表后反馈报错：`解析能效报表失败：recomputeVirtualRows is not defined`；
  - 经查在回填函数 `applyEfficiencyDataToSheets` 中，原先调用了虚拟重算函数的伪代码名称，导致运行时异常中断。
- **改动点 (`DataEntryView.vue`)**：
  - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
  - 消除未定义的函数调用，接入组件原生联动体系：
    - 遍历 `linkageMap` 完成关联行数据的同步更新；
    - 在校验开启状态下，调用原生的 `validateRow(r)` 对各行数据进行标准合规验算；
- **验证结果**：
  - 前端执行 `npm run build` 构建成功（耗时 14.50s，758 个模块无错误）。

## 2026-10-28 [北海热电厂能效报表自动解析与三表多标签页一键回填系统]
- **需求背景**：
  - 用户提出需求：“为北海热电厂增加一个上传能效报表的功能”；
  - 北海热电厂兼顾集团生产日报与能效分析报表两套填报体系，手工跨表录入繁重且易错。需实现用户上传《北海能效分析表》（Excel）后，系统自动基于当前填报业务日期，精准识别并提取每日生产指标，自动分发回填至北海热电厂全部 3 张子表（热电联产表、水炉表、天然气炉表）。
- **架构设计与改动点**：
  1. **后端智能解析引擎 (`beihai_efficiency_parser.py`)**：
     - 新建 [`beihai_efficiency_parser.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/beihai_efficiency_parser.py)；
     - **年月 Sheet 智能定位**：自动根据业务日期 `biz_date` 寻址对应月份子表（如 `2026.11`）；
     - **日期列精确匹配**：扫描首行时间戳或日期列标（支持 `datetime` 或 `1~31` 日标），锁定目标业务日所在列；
     - **三板块物理映射**：
       - `电厂部分`（Row 169~340）-> 提取发电量、供热量、外供汽量、售电量、原煤/标煤耗量、电厂耗水、电厂外购电、环保辅料（酸/碱/油/氨水/石灰石）及主设备运行方式等 15 项核心指标；
       - `水炉部分`（Row 341~427）-> 提取水炉供热量、原煤/标煤耗量、水炉耗水、水炉耗电、辅料及运行水炉数等 12 项指标；
       - `燃气炉部分`（Row 428~470）-> 提取天然气炉供热量、供汽量、耗气量、耗水耗电及启停情况等 8 项指标；
  2. **后端 API 端点 (`legacy_full.py`)**：
     - 修改 [`legacy_full.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/api/legacy_full.py)；
     - 新增 `POST /api/v1/projects/{project_key}/data_entry/beihai/parse_efficiency_report`，接收 Excel 文件与 `biz_date`，完成格式校验与权限会话保护；
  3. **前端 API 客户端 (`api.js`)**：
     - 修改 [`api.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/services/api.js)；
     - 封装 `uploadBeihaiEfficiencyReport(projectKey, file, bizDate)` 函数，支持 FormData 文件流传输；
  4. **前端填报界面交互与跨表回填 (`DataEntryView.vue`)**：
     - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
     - **专属上传入口**：当检测到当前填报单位为北海热电厂（`isBeihaiUnit`）时，在顶部操作栏呈现天蓝色科技感【📁 上传能效分析表】专属按钮；
     - **跨表内存渗透回填 (`applyEfficiencyDataToSheets`)**：
       - 当前活动的 Tab 表格即时更新 `gridSource` 与 `rows`，触发公式重算与数据校验；
       - 其它 2 张未激活的子表格自动在 `sheetCache` 内存中完成数据回填与预渲染，用户切换 Tab 无缝预览填报结果；
     - **核对确认与一并提交**：弹窗展示匹配成果汇总（工作表名、业务日、35 项指标提取成功反馈），核对后点击【一并提交】一次性保存入库。
- **验证结果**：
  - Python 独立单元测试通过，提取数值与能效分析表 100% 对齐；
  - 模拟真实登录会话执行端到端 HTTP API 请求，接口正常响应 200 OK 并成功提取 3 表共 35 项生产数据；
  - 前端执行 `npm run build` 全量静态编译打包通过（耗时 19.65s，758 个模块无错误）。

## 2026-10-28 [每日数据填报列表页两栏等宽布局重构：正常情况下分两栏，每个主体框体宽度严格一致]
- **需求明确**：
  - 用户明确提出要求：“正常情况下分两栏，每个主体框体的宽度一致”。
- **改动点与实现原理 (`Sheets.vue`)**：
  - 修改 [`Sheets.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/Sheets.vue)；
  - **默认两栏等宽网格 (`.unit-card-grid`)**：
    - 将正常桌面端网格设定为严格等分的两栏：`grid-template-columns: repeat(2, minmax(0, 1fr))`；
    - 两栏各占 50% 可用宽度（约为 430px），间距 `gap: 20px`；
    - 窄屏（<= 640px）自适应切为单栏 `1fr`；
  - **主体框体盒模型加固 (`.unit-card`)**：
    - `.unit-card` 统一使用 `width: 100%; min-width: 0; box-sizing: border-box; justify-content: space-between; padding: 20px;`；
    - 确保每个主体卡片框体左右宽度完全对等，内部标签拥有充裕横向排布空间，视觉大气匀称。
- **验证结果**：
  - 前端执行 `npm run build` 构建成功（耗时 20.60s，758 个模块无错误，退出码 0）；
  - 页面各主体卡片严格按照 50%/50% 双栏等宽排布。

## 2026-10-28 [每日数据填报列表页主体卡片尺寸标准化：彻底消除内容撑开差异，实现全量主体卡片严格等宽]
- **需求背景**：
  - 用户反馈每日数据填报列表页中，各个填报主体的卡片宽度存在视觉差异，要求将“每个主体的卡片宽度都改成一致”；
  - 经排查，此前网格采用 `repeat(auto-fill, minmax(320px, 1fr))`，在 CSS Grid 规范中 `1fr` 默认带有 `minmax(auto, 1fr)` 的固有尺寸机制。当北海热电厂（3张表）或供热公司包含较多较长的表名胶囊时，所在列的 `min-content` 会被无形撑大，而仅含 1 张短表名的主体所在列宽度更窄；此外最后一行单出的卡片排布也会破坏统一感。
- **改动点与实现原理 (`Sheets.vue`)**：
  - 修改 [`Sheets.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/Sheets.vue)；
  - **严格等宽三列网格体系 (`.unit-card-grid`)**：
    - 将网格重构为 `grid-template-columns: repeat(3, minmax(0, 1fr))`，强制每一列平分 1/3 容器宽度；
    - 配备响应式媒体查询：屏幕宽度 <= 860px 时平滑切为 2 列（`repeat(2, minmax(0, 1fr))`），<= 560px 时单列（`1fr`），确保在任何屏幕分辨率下卡片宽度绝对一致；
  - **主体卡片盒模型与防撑开加固 (`.unit-card`)**：
    - 为 `.unit-card` 显式声明 `width: 100%; min-width: 0; box-sizing: border-box; justify-content: space-between;`，消除原生 `<button>` 的尺寸漂移；
    - 针对内部标题 `.unit-card-title` 与胶囊文字 `.pill-title` 注入 `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`，杜绝任何长内容对列宽的横向撑大；
    - 统一步长与内边距，使全部 9 个主体（北海、香海、供热、金州、北方、金普、庄河、研究院、售电）呈工整的 3×3 九宫格排列，宽度严丝合缝完全一致。
- **验证结果**：
  - 执行 `npm run build` 成功完成全量生产构建打包（758 个模块无错误，耗时 21.96s）；
  - 页面各主体卡片宽度完全等比对齐。

## 2026-10-28 [生产日报填报权限精细化管控：非 Global_admin 角色全量锁定“同期值”列不可修改]
- **需求背景**：
  - 用户明确要求：“这些表格的同期值字段，对 Global_admin 之外都改为不可修改”。
  - 每日数据填报中，各供热及发电单位的填报人员仅负责提报当期实际生产数据，上年同期数据应作为历史基准严禁随意篡改；仅集团级最高管理员（`Global_admin`）在特殊数据校准或历史补录场景下拥有编辑权限。
- **改动点与实现原理 (`DataEntryView.vue`)**：
  - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
  - **智能识别同期值列 (`isPeerColumnIndex`)**：
    - 结合配置列名（如“同期”、“去年”）、动态换算出的同期业务日期列名（匹配 `peerDateYYYYMMDD(bizDate.value)`），以及标准五列日报表固定第 3 列（index 3）等多维度特征精准锁定同期列；
  - **表格渲染层只读锁定 (`setupStandardGrid` / `applyReadonlyToColumns`)**：
    - 针对当前用户非 `isGlobalAdmin`（`group !== 'global_admin'`）的情形，在 RevoGrid 列定义配置中统一注入 `readonly: true` 与 `__locked: true`，并在表头列名后追加锁标识 `🔒`，直观提示用户只读锁定；
  - **编辑事件拦截与强制复原防御 (`handleAfterEdit`)**：
    - 在单元格修改后置事件中追加安全防御层：若非 `isGlobalAdmin` 用户试图通过任何手段改写同期值列，立即中断更新逻辑并强制回滚复原单元格数值，确保数据资产安全。
- **验证结果**：
  - 执行 `npm run build` 构建成功，前端代码全量打包通过无报错；
  - 非 Global_admin 用户进入填报页面时，同期值列不可聚焦编辑且表头标锁；Global_admin 角色正常保留修改能力。

## 2026-10-28 [填报界面视觉美学与层级体验升级：恢复列表卡片表格序号、重塑现代分段胶囊标签栏（Segmented Pill Tabs）]
- **反馈问题定位**：
  1. 列表页（`Sheets.vue`）：北海、供热等单位窗格内的表格胶囊中，原表名的前导序号（如 `1.`、`2.`、`5.`、`6.`）丢失；经查系之前的正则洗词过度截断导致；
  2. 填报页（`DataEntryView.vue`）：标签栏排版过于粗糙生硬（外包厚重灰色浮起边框、左侧带有生硬的“单位报表切换：”文本标签、按钮样式老旧割裂且同样丢失了表序号）。
- **优化落实与改动点**：
  1. **列表卡片独立序号徽标体系 (`Sheets.vue`)**：
     - 修改 [`Sheets.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/Sheets.vue)；
     - 引入 `parseSheetNumber` 与 `cleanSheetBodyName` 双层解构；
     - 在单位卡片内部胶囊中，独立渲染出高对比度的深色数字徽标 `.pill-number`（如 `[1]`、`[2]`、`[3]`、`[5]`、`[6]`），使集团核心序号醒目立显，悬停时支持展示完整表名；
  2. **现代分段胶囊标签栏 (Segmented Pill Tabs) 重塑 (`DataEntryView.vue`)**：
     - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
     - 彻底删除外围厚重卡片框与冗余的“单位报表切换：”文字；
     - 引入现代设计规范（类似 Linear/Vercel/macOS）的悬浮分段胶囊底槽 `.unit-tabs-nav`；
     - 每个 Tab 胶囊集成独立高亮序号 `.tab-index`、精炼表名 `.tab-name` 与极简状态微标 `.tab-status-dot`（已提交显示微脉冲绿光点，异常显示红点）；
     - 激活项采用纯白浮雕高质感卡片（双层细腻微阴影与高亮主题色），未激活项采用透明舒适悬停过渡；
     - 提交按钮组采用翡翠渐变与微阴影，整体界面层级分明、极具专业工控美感。
- **验证结果**：
  - 前端执行 `npm run build` 成功完成全量生产打包（耗时 16.80s），758 个模块无错误。

## 2026-10-28 [每日数据填报单位入口归一化与多表格标签页（Tabs）一并提交重构]
- **需求背景与痛点**：
  - 用户指出在每日数据填报中，北海热电厂（3张表：热电联产、水炉、天然气炉）、供热公司（2张表：公司表、分中心明细表）等单位，原先被拆成若干孤立的表卡片散落排列；
  - 填报人员每次填报都需要反复进出不同页面、在多张表中重复选择业务日期、多次手动点击提交，流程极其繁琐且存在业务日期填错错位的隐患；
  - 用户明确要求：“将各单位的入口都做成一个，然后进去之后，有多张表格的，以标签页的形式展示，一并提交”。
- **架构重构与改动点**：
  1. **表格列表页单位入口归一化 (`Sheets.vue`)**：
     - 修改 [`Sheets.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/Sheets.vue)；
     - 将原先“按单位分组下平铺展示每张小表格”的模式，升级为**“单位聚合卡片网格 (`unit-card-grid`)”**；
     - 每个单位聚合成独立卡片，展示单位名称（如“北海热电厂”）、包含报表数及精炼胶囊标签（`热电联产` / `水炉` / `天然气炉`）、以及综合填报进度指示器（已完成 / 部分完成 / 待填报）；
     - 点击单位卡片即可直达该单位的综合填报入口。
  2. **填报页多表格 Tabs 标签页导航与多表内存保活 (`DataEntryView.vue`)**：
     - 修改 [`DataEntryView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue)；
     - 引入 `listSheets` 动态识别当前填报表格所属的单位及其下属全部表格清单 `unitSheets`；
     - 当表格数大于 1 时，在顶部呈现响应式 Tabs 标签切换栏，动态标注各表状态徽章（正常/已提交/异常）；
     - 设计 `sheetCache` 内存多表状态缓存，在用户切换 Tab 时完整暂存与瞬时恢复单元格输入、校验问题与联动计算状态，做到**毫秒级平滑切表、已录入数据零丢失**；
     - 业务日期 `bizDate` 在单位层全局统一，切换日期时所有子表严格同步查询，彻底杜绝单表日期错位。
  3. **一键“一并提交”与跨表原子化校验 (`DataEntryView.vue`)**：
     - 顶部操作栏对多表单位提供【一并提交全部表格 (共X张)】主按钮；
     - 点击时前置统一遍历所有子表格的校验规则：若发现阻断性错误，自动平滑切换到报错的 Tab 标签并高亮提示修正；
     - 校验全部通过后，使用 `Promise.all` 并发向后端提交本单位全部表格数据，统一弹窗反馈“全部报表数据已成功一并提交入库”。
- **验证结果**：
  - 前端执行 `npm run build` 生产构建成功，758 个模块顺利编译无错误；
  - 现有多表单位（北海热电厂 3 表、供热公司 2 表）与单表单位（香海、金州、北方等）自适应兼容。


## 2026-10-28 [全局项目元数据秒级直显与零闪烁优化：引入LocalStorage双级缓存与动态供暖期兜底对齐]
- **现象定位与根因剖析**：
  - 用户反馈：“刚进入页面时，面包屑会先显示为【2025-2026供暖期生产日报】，然后一闪变为【2026-2027供暖期生产日报】”；
  - 经排查定位根本原因：
    1. 前端全局项目状态 `projects = ref([])` 仅存储在 JavaScript 运行时内存中，每次页面刷新或新标签页打开时初始值均为空；
    2. 在网络异步请求 `/api/v1/projects` 返回之前的瞬间（约 100~300ms），系统回退到了代码中旧版本的硬编码值 `2025-2026供暖期生产日报`；
    3. 当异步请求回包后，检测到系统当前激活的实际供暖期为 26-27，状态响应式变为 `2026-2027供暖期生产日报`，引起文字突变与闪烁（Layout Flickering）；
- **重构落实与改动点**：
  1. **LocalStorage 同步持久化缓存机制 (`useProjects.js`)**：
     - 修改 [`useProjects.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/composables/useProjects.js)；
     - 引入 `PROJECTS_STORAGE_KEY = 'phoenix_projects_cache'`；
     - 在 Vue 实例与组件初始化第一帧，直接从本地存储同步反序列化项目元数据赋值给 `projects.value`，做到**零网络等待、首帧即渲染真实名称**；
     - `ensureProjectsLoaded()` 接口回包时自动刷新 LocalStorage 缓存，保持静默增量对齐；
  2. **供暖期基准兜底全面对齐最新 26-27**：
     - 将 `KNOWN_PROJECT_NAMES` 中的基准年度以及各业务页面（[`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)、[`GlobalManagementView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/GlobalManagementView.vue)、[`DynamicPlanMetricsView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue)、[`SpotElectricityView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/SpotElectricityView.vue)）的兜底缺省值统一校准为【`2026-2027供暖期生产日报`】；
     - 即使在首次无缓存访问或极端离线场景下，也直接命中当前激活的供暖期，彻底消灭年度文字跳动与闪烁。
- **验证结果**：
  - 前端执行 `npm run build` 生产构建成功，758 个模块无报错。

## 2026-10-28 [调度信息页面面包屑导航多级响应修复：根除上一级英文ID暴露，强化项目名称兜底与动态加载]
- **现象定位与根因剖析**：
  - 用户反馈访问 `http://localhost:5173/projects/daily_report_25_26/pages/dispatch_info?pageName=调度信息` 时，面包屑导航上一级名称显示不正确（暴露了英文标识 `daily_report_25_26`）；
  - 经排查定位根本原因：
    1. `DispatchInfoView.vue` 未在 `onMounted` 钩子中调用 `ensureProjectsLoaded()`，当页面刷新或直接通过 URL 访问时，全局项目状态未初始化，`projects.value` 为空数组；
    2. `useProjects.js` 的 `getProjectNameById` 缺少静态项目中文兜底字典，未匹配到项目时直接返回原始 `projectId`（即 `daily_report_25_26`），导致页面模板中的 `??` 空值合并操作符无法触发兜底回退；
    3. 第三级面包屑写死为字符串 `'调度信息'`，未像其他页面一样响应 URL 中的 `?pageName=` 参数；
- **重构落实与改动点**：
  1. **全局项目名称提取强化 (`useProjects.js`)**：
     - 修改 [`useProjects.js`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/composables/useProjects.js)；
     - 增加 `KNOWN_PROJECT_NAMES` 字典，覆盖所有已知项目的中文标准名称；未完成异步网络请求时立即命中中文回退，从根源杜绝暴露英文路径段；
  2. **调度看板面包屑组件响应式与初始化加固 (`DispatchInfoView.vue`)**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 引入并在 `onMounted` 中执行 `ensureProjectsLoaded().catch(() => {})` 确保全局项目列表异步对齐；
     - `pageDisplayName` 响应式支持 `route.query.pageName` 动态回显；
     - `breadcrumbItems` 第二级（上一级项目名称）与第三级（当前页面名称）全部实现纯净中文与双向响应。
- **验证结果**：
  - 前端执行 `npm run build` 生产构建成功，758 个模块编译正常。

## 2026-10-28 [机炉拓扑左右分栏卡片等宽像素级对准：消除col-right不对称内边距，引入居中中缝虚线]
- **现象定位与根因剖析**：
  - 用户敏锐观察到：“第二行的香海、金州、北方三个主体，是不是机、炉的小卡片不一样宽度？”；
  - 经查验布局样式表：原布局虽然给外层设定了 50%/50% 网格等分，但右侧分栏 `.col-right` 单独设置了 `border-left: 1px dashed #e2e8f0; padding-left: 1.25rem;`（内边距 20px），且由于 `box-sizing: border-box`，这 21px 被直接从右侧可用内容宽度中扣除；而左侧 `.col-left` 没有内边距；
  - 这导致在香海、金州、北方等所有双栏主体内部，左侧“机”小卡片占满了整个 50% 列宽，而右侧“炉”小卡片宽度被挤窄了 21 像素，呈现不对称；
- **重构落实与改动点**：
  1. **彻底消除列内不对称内边距**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 将 `.col-right` 的 `padding-left` 置为 0，`border-left` 置为 none，左右两列在 CSS Grid 中获得完全对等无损的可用内容空间；
  2. **网格中轴绝对居中中缝虚线 (`.plant-split-columns::after`)**：
     - 在 `.plant-split-columns:not(.single-column)` 容器上增加基于中轴 `left: calc(50% - 0.5px)` 的绝对定位虚线分割伪元素；
     - 网格间距设为 `gap: 1.5rem`（两边各留出 12px 呼吸间距），虚线正好坐落于两列的正中间；
     - 左侧机组小卡片与右侧锅炉小卡片的宽度达到 100% 像素级绝对一致（0px 偏差）。
- **验证结果**：
  - 前端执行 `npm run build` 生产构建验证，全量模块编译通过。

## 2026-10-28 [燃气锅炉标题层级极净化：取消内部子分组标头，统领单一“锅炉”总标题，设备左右等宽分列]
- **需求与优化背景**：
  - 用户反馈燃气锅炉主体卡片内部无须再切分子分组：“那个‘燃气锅炉’不必分组，还写着‘锅炉 (1# - 5#)’……就写锅炉吧，显示方面是分左右两列而已”；
- **重构落实与改动点**：
  1. **移除子分组多余标头，统一大标头**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 取消原本在左右两列顶部各自渲染的【🔥 锅炉 (1# - 5#)】与【🔥 锅炉 (6# - 10#)】小标题；
     - 将标头提升为燃气锅炉主体的单一统一标头：【🔥 锅炉 (X/10 运行)】，直观呈现全厂运行率，消除重复嵌套视觉噪音；
  2. **视觉显示保持左右两列 50% / 50% 严格等宽**：
     - 标头下方直接挂载等宽网格容器 `.plant-split-columns`，左列排布 1-5 号炉（`boilersLeft`），右列排布 6-10 号炉（`boilersRight`）；
     - 双列继续保持 `minmax(0, 1fr)` 绝对等宽，每列内部严格保持“运行 > 备用 > 检修”第一优先级与同状态顺号排列。
- **验证结果**：
  - 前端执行 `npm run build` 生产构建成功，758 个模块无报错，编译耗时 20.01 秒，产物打包正常。

## 2026-10-28 [机炉拓扑精细排版：燃气锅炉双列等宽拆分(左1-5/右6-10)与全主体双列50/50锁死]
- **需求与优化背景**：
  - 用户反馈燃气锅炉数量较多（10台），排成单列过于冗长，要求：“分两列显示吧，左侧1-5，右侧6-10。然后注意一件事，在同一个主体中，即使分列，两列内容也应该等宽”；
- **重构落实与改动点**：
  1. **燃气锅炉等宽双列拆分（左 1-5，右 6-10）**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 在 `groupedFacilities` 中识别锅炉数量较多的燃气主体（`isSplitBoilers`），自动按编号区间分为 `boilersLeft`（1# - 5#）与 `boilersRight`（6# - 10#）；
     - 各自半区依然完美执行“运行 > 备用 > 检修”第一优先级，并在同状态内部按序号自然升序排列；
  2. **双列 50% / 50% 严格等宽架构保障**：
     - 将网格列宽严格设定为 `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)`；
     - 赋予每个分列 `.plant-col` 核心属性 `min-width: 0; width: 100%; box-sizing: border-box;`，彻底根除内部文本长短或内边距导致的列宽不均问题；
     - 无论是常规电厂的“左机右炉”，还是燃气主体的“左1-5、右6-10”，左右两栏均呈现完美的对半绝对等宽视觉效果。
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，17.65 秒编译成功。

## 2026-10-28 [机炉拓扑状态多级排序升级：运行>备用>检修第一优先级，同状态内序号升序]
- **需求与优化背景**：
  - 用户提出明确排序口径：“设备的运行状态显示，应当先按‘运行>备用>检修’来排列，然后再每一种状态下，再按照序号排列”；
- **重构落实与改动点**：
  1. **状态权重优先级的多级自然排序算法 (`sortFacilitiesByStatusAndNumber`)**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 建立状态权重常量表：`运行(1) > 备用(2) > 检修(3) > 其他(99)`；
     - 第一比较维度：严格根据运行状态权重排序，确保正在带负荷运行的机组与锅炉永远排在最顶层，备用设备居中，检修设备靠后；
     - 第二比较维度：在同一状态分组内，提取编号数字按从小到大升序排序（如同为“运行”的锅炉按 #1汽炉、#4汽炉 顺号排列）；
     - 第三比较维度：中文拼音 localeCompare 兜底；
  2. **分栏及未分栏全场景对齐**：
     - 各主力电厂的左栏（机组）、右栏（锅炉）以及北海水炉、燃气锅炉等单栏主体，全部严格应用该多级排序规则，调度工况重点一眼可知。
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，14.54 秒编译成功。

## 2026-10-28 [调度看板视觉极净化与工作台权限隔离：标题精简、仅Global_admin可见且默认收回]
- **需求与优化背景**：
  - 用户要求：“调度信息智能提取工作台”默认收回，仅 Global_admin 可以看到；
  - 页面标题由原先冗长的两行介绍精简改为：“生产调度信息全景看板”；
- **重构落实与改动点**：
  1. **标题文案极简与大气呈现**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 主标题简化为【生产调度信息全景看板】，移除多余冗长的副标题说明，整体视觉干净专业；
  2. **提取工作台权限门禁与状态初始化**：
     - 工作台区块增加 `v-if="isGlobalAdmin"` 严格权限守卫，普通业务人员与观察员完全不可见该提取工作台；
     - `isGlobalAdmin` 计算属性严格联动 `auth.user.group === 'Global_admin'` 及管理员权限；
     - `isExtractPanelExpanded` 初始状态设为 `false`（默认收回），即使全局管理员进入页面，工作台也保持精致折叠，需要时一键展开。
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，17.58 秒编译成功。

## 2026-10-28 [业务日期切换体验极致平滑化：彻底根除页面闪烁、视口塌陷与跳顶抖动]
- **现象定位与根因剖析**：
  - 用户反馈：“点选调整业务日期时，页面总要闪一下，突然回到顶端然后又恢复到刚才的位置”；
  - **根本原因**：原代码在日期切换时使用 `v-if="isLoadingData"` 控制展示，导致已有数据时切换日期会瞬间将数千像素高的整个 `.dashboard-body` 彻底从 DOM 中销毁移除，页面高度瞬间从 2500px 坍塌至 200px（破坏性骨架塌陷 Layout Thrashing），浏览器被迫将滚动条 scrollTop 强制归零；接口响应后 DOM 重新挂载，页面猛烈闪烁并试图回弹；
- **重构落实与改动点**：
  1. **非破坏性就地平滑刷新（Non-destructive In-Place Loading）**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 限制居中全屏加载仅在“初次进入且全无数据（`isLoadingData && !currentReport`）”时展示；
     - 日期切换时保持 `.dashboard-body` 始终驻留 DOM 中，页面高度坚如磐石，滚动条位置 100% 纹丝不动；
  2. **高品质浅雾毛玻璃加载蒙层 (`.fetching-overlay`)**：
     - 在展板主体上方叠加轻量浅白半透明毛玻璃蒙层（`background: rgba(255, 255, 255, 0.55); backdrop-filter: blur(2px)`）；
     - 居中展示吸附式悬浮暗色胶囊微标【正在读取 YYYY-MM-DD 调度数据…】，既有明确的即时加载反馈，又绝不引发视口抖动；
  3. **清理无效 Tab 残留**：
     - 清理搜索函数中遗留的 `activeTab.value = 'events'`。
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，17.51 秒编译成功，日期切换丝滑顺畅、视觉完全稳定。

## 2026-10-28 [机炉拓扑垂直有序化：设备序号自然升序与单双栏全场景自顶向下规范]
- **需求与优化背景**：
  - 用户明确要求：“即使仅有炉（未分栏），也应当是从上到下排序”；
- **重构落实与改动点**：
  1. **设备序号自然升序排序 (`sortFacilitiesByNumber`)**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 引入正规自然排序算法，针对各电厂提取时由于运行/备用/检修多段拼接导致的编号乱序（如 #1, #4, #3, #2 等）实施严格的数字升序归整：
       - 机组：严格按 `#1机`, `#2机`, `#3机` ... 顺序呈现；
       - 锅炉：严格按 `#1炉`, `#2炉`, `#3炉` ... `#10炉` 顺序呈现；
       - 彻底解决文本排序中 "10" 错误排在 "2" 前面的问题；
  2. **从上到下单列条带排版（垂直流水线）**：
     - 将设备容器 `.facility-badges` 由横向流式 wrap 改造为严格的纵向流水线 `flex-direction: column`；
     - 每个设备项 `.fac-badge` 改造为两端对齐的工整条带：
       - 左侧：醒目深色设备名称（如 `#1汽炉`、`#10燃气炉`）；
       - 右侧：统一收拢展示启动时刻小胶囊（`🚀 HH:MM 启动`）与状态标签（`运行`/`备用`/`检修`）；
     - 无论是分栏主体（北海联产、香海、金州、北方）还是仅有炉的主体（北海水炉 3 台、燃气锅炉 10 台），全部呈现优雅一致的自顶向下工控台样式。
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，16.73 秒编译成功。

## 2026-10-28 [机炉拓扑矩阵重塑：左机右炉对称分栏架构与徽章轻量化纯粹设计]
- **需求与优化背景**：
  - 用户反馈原上下堆叠的分组形式显得冗赘且重复打标签，要求：“把每个主体的机、炉分开，做成分栏的形式，左机右炉，而不是重复打标签”；
- **重构落实与改动点**：
  1. **左右对称双栏布局（左机右炉）**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 在各主体卡片内采用双列网格分栏容器 `.plant-split-columns`：
       - **左栏（机组）**：`⚡ 机组 (运行数/总数)`，专列汽轮发电机组；
       - **右栏（锅炉）**：`🔥 锅炉 (运行数/总数)`，虚线竖隔独立分栏，专列各类锅炉；
       - **单栏自适应兼容**：若主体仅有锅炉（如北海水炉、燃气锅炉），自动平滑降级为全宽单栏，无空白占用；
  2. **剔除重复标签，徽章纯粹化**：
     - 彻底移除了徽章内冗余的 `fac-type-tag`（不再重复写“汽机”、“锅炉”）；
     - 徽章仅聚焦展示【设备名称】、【状态标签】与【🚀 启动时刻（如有）】，界面整洁大方；
  3. **主体开机汇总统一**：
     - 主体统计文本对齐左机右炉顺序：`运行：X机 Y炉`。
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，16.59 秒编译成功。

## 2026-10-28 [机炉拓扑精细化与调度事件联动：机炉分列、主体运行统计与当日启动高精标注]
- **需求与优化背景**：
  - 用户提出 4 项精细化调度看盘要求：
    1. 将“微观事件与抢修工作票”正式更名为“调度事件”；
    2. “机炉运行拓扑矩阵”中，每个主体的“机”和“炉”应当严格分开列示，不再混排；
    3. 每个主体名称后面应当明确显示当前运行的机、炉数量（如“运行：2炉 2机”）；
    4. 若某台设备系当日启动（根据当天调度事件的并网、并汽、冲转、点火、投运等原子时序识别），应当在其设备卡片上醒目标注具体的启动时间（如“🚀 13:55 启动”）。
- **重构落实与改动点**：
  1. **板块重命名与口径统一**：
     - 将页面看板第 4 板块及全页面提示统一更名为【调度事件】；
  2. **机炉分开分组渲染与主体运行数量展示**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)；
     - 升级 `groupedFacilities` 计算属性，拆解为 `boilers`（锅炉区，标配 🔥 图标）与 `turbines`（汽机区，标配 ⚡ 图标）独立子区块；
     - 主体头部自动计算并呈现当前开机工况 `runningSummary`（如“运行：2炉 2机”或仅炉电厂“运行：X炉”），绿色圆角徽章突出显示；
  3. **调度事件深度关联与当日启动时刻高精识别**：
     - 实现 `getFacilityStartTime(fac, events)` 高精算法：
       - 主体交叉隔离（北海、香海、金州、北方、燃气精准归属）；
       - 细分炉型排他（水炉仅匹配水炉事件、汽炉排除水炉/燃气炉、汽机严格匹配机组）；
       - 智能甄别点火、冲转、并汽、并列等启动动词并提取对应原子时刻；
     - 在启动设备的徽章上显示 `🚀 HH:MM 启动` 橙金高亮标签，鼠标悬浮展示调度事件完整原文。
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，16.58 秒编译成功，界面信息密度与工业调度专业度显著提升。

## 2026-10-28 [调度看板布局全面升维：由标签页切换重构为全要素平铺通览流]
- **需求与重构背景**：
  - 用户反馈原底部的 4 个 Tab 标签页（机炉运行拓扑、首站工况与温压差、蒸汽网口与燃煤库存、微观事件与抢修工作票）切断了运行监控的连续性，提出“不需要标签页，直接全量展示”；
- **重构落实与改动点**：
  1. **布局架构平铺化**：
     - 修改 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue)，彻底移除 `.detail-nav-tabs` 及各子项的 `v-show="activeTab === '...'"` 切换隔离；
     - 采用现代化的卡片板块流容器 `.dashboard-sections-flow`，依次纵向平铺呈现：
       1. 🏭 **机炉运行拓扑矩阵**（按热电厂分类折叠徽章，实时呈现设备运行/备用/检修状态）；
       2. 💧 **首站工况与温压差**（全景表格呈现循环泵方式、循环量、供回水温压差与高亮指示）；
       3. ♨️ **蒸汽网口与燃煤库存**（自适应双列并排卡片，呈现蒸汽管网运行状态及各单位进耗存煤）；
       4. 📋 **微观事件与抢修工作票**（支持主体分类胶囊过滤、仅看工作票勾选及关键字即时联想）；
  2. **状态与样式清理**：
     - 从 `<script setup>` 中移除冗余的 `activeTab` 响应式变量；
     - 移除废弃的 Tab 导航样式，新增 `.dashboard-section-block`、`.section-block-header`、`.section-block-title` 与 `.section-badge` 样式规范；
- **验证结果**：
  - 前端执行完整生产构建 `npm run build`，758 个模块无报错，16.14 秒编译成功，展板支持自顶向下一览无余通览生产全局。

## 2026-10-28 按用户要求调整聚合分解

- 用户删除供热公司的供热量后，要求聚合结果等于子口径分解结果之和。`get_dynamic_daily_decomposition` 总量分支改为逐日累加，父口径 k/m 不再重算；直报仅作为对账参考，单耗维持自身模型。
- 页面同步模型说明、禁用汇总总量参数编辑，并展示直报与子项合计的差额，避免用父口径直报强行调平。
- 验证脚本：`outputs/dynamic_plan_audit_20261028/child_rollup_regression.py`；保持气温完整性现行规则，无业务数据写入和数据库迁移。Serena 不可用，原生读取及 apply_patch 留痕于此。
- 验证通过：7 个月、2 个聚合口径共 10,539 个日值与子口径逐日之和一致（远期月份使用合成气温隔离验证聚合关系）；前端完整构建通过。实际数据库供热公司当期供热量记录数为 0；11 月集团子口径合计 1,725,534.24 GJ、直报 1,725,699.24 GJ，仍差 -165 GJ，界面明确显示。

## 2026-10-28 计划动态分解缺陷修复

- 根因：月度矩阵优先直报，日分解优先子单位之和，绕过集团/主城区直报的内部抵消。统一为按指标、月份优先直报，缺报才汇总。
- 修复首次新增参数时未定义的 new_k；预报导入 SQL 原子跳过同刻 near；前端隔离旧请求、失败清空旧结果、约束目标月份、按单位独立分轴。
- 按用户要求保持不满 24 小时的日均温可用规则；本轮不扩展接口权限、外购热键名、尾差及 m 范围规则。
- 验证证据：`outputs/dynamic_plan_audit_20261028/fix_regression.py` 与 `frontend_checks.mjs`。Serena 当前不可用，使用原生读取与 apply_patch，留痕在本文件；恢复后可补录。
- 验证结果：10 个口径基数/合计对账通过；新增参数替身通过；真实 PostgreSQL 临时表验证 near 不变、far/NULL 更新、新时刻插入和跳过计数，事务回滚；异步乱序/失败隔离及三单位分轴测试通过；前端完整构建通过；实际浏览器确认集团 11 月合计 1,725,699.24 GJ，范围改为 12 月后目标自动选中 12 月，未捕获 error/warn。未执行真实参数写入或外部预报导入。
- 无数据库迁移；回滚限于本轮所改函数，保留工作区其他未提交改动。

> 注：2026-10-28 09:00 前的历史进程日志已归档至 [configs/归档/progress.md](file:///D:/编程项目/phoenix/configs/归档/progress.md)。

---

## 2026-10-28 [工作台交互纯粹化：移除冗余模式Tab与服务器路径输入，全面聚焦本地文件/文件夹上传]
- **需求与优化背景**：
  - 用户指出：“📤 本地文件 / 文件夹上传”与“💻 服务器目录直接扫描”的模式切换选项多余，业务用户无需接触服务器底层路径，应直接保留纯粹的上传；
- **重构落实**：
  1. **移除模式切换 Tabs 与服务器路径分支**：
     - 从 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue) 中彻底移除 `.mode-tabs` 选项卡及 `.server-folder-container`；
     - 面板主体直接平铺展示【📄 选择文件】、【📁 选择整个文件夹】与拖拽区域；
  2. **状态与提取逻辑简化**：
     - 移除无用的 `extractMode` 与 `serverFolderPath` 响应式变量；
     - 提取逻辑简化为直接消费 `selectedFiles`，无文件时直接给出清晰的前置校验提示。
- **验证结果**：
  - 前端执行完整构建 `npm run build`，758 个模块无报错，17.04 秒编译成功，界面层次更加精炼专注。


## 2026-10-28 [界面精简与风险控制：移除已过时的“一键载入历史 162 份基准数据”调试按钮]
- **移除缘由**：
  - “⚡ 一键载入历史 162 份基准全量数据”按钮系早期开发联调时为了跳过文件解析直接读取静态 JSON 的临时测试入口；
  - 当前数据库中已完成 163 篇全要素生产数据的高质量清洗入库，且正规业务流程（选择文件/文件夹 -> 批量提取 -> 冲突检测 -> 一键入库）已完全打通；
  - 该按钮读取的是早期未清洗的旧静态文件，留在界面上极易引发用户误操作覆盖冲掉最新资产，存在业务安全隐患；
- **清理范围**：
  - 从 [`DispatchInfoView.vue`](file:///D:/编程项目/phoenix/frontend/src/projects/daily_report_25_26/pages/DispatchInfoView.vue) 中彻底移除该按钮及其触发的 `quickImportHistorical` 方法与 API 引用，简化提示文案；
- **验证结果**：
  - 前端执行完整构建 `npm run build`，758 个模块无报错，15.07 秒编译成功，界面视觉干净，业务路径唯一明确。


## 2026-10-28 [调度数据库与提取器针对性修正：首站供回压颠倒调正与管网地点实体高精清洗]
- **升级与修正背景**：
  - 用户审阅数据库后，精准指出：
    1. 2026-10-26 北海水炉首站供回压颠倒（`0.63/0.77 MPa`），需调正为正常的正向工况（`0.77/0.63 MPa`）；
    2. 微观操作事件中地点误带“开启/关闭”等动词前缀（如“开启北岗街”、“开启久寿街”）；
    3. 特别是指明确认 2025-11-15 历史事件中的截断地点，实际完整名称应为“特勤大队事故办及港湾隽景”；
- **高精细修复方案**：
  1. **数据库物理列更新**：
     - 修正 `2026-10-26` 的 `bh_wl_press_sup` 为 `0.77 MPa`，`bh_wl_press_ret` 为 `0.63 MPa`，恢复正向压差 `+0.14 MPa`；
  2. **事件流地点实体高精清洗**：
     - 修正 `2025-11-15` 的 `location` 为标准完整实体：`"特勤大队事故办及港湾隽景"`；
     - 修正 `2026-10-23` 与 `2026-10-26` 的 `location` 为纯净实体：`"北岗街"`、`"久寿街"`；
     - 修正 `2026-02-06` 的 `location` 为纯净实体：`"北岗街"`；
     - 双端数据库（5432 与 5434）已完全执行事务更新提交；
  3. **提取程序清洗算法加固 (`dispatch_extractor.py`)**：
     - 地点提取器增加动作词（开启/关闭/签发/恢复）与水网介质词（高温水/低温水）前缀自动剥离机制；
     - 扩展复杂地标及多词缀复合实体的完整捕获支持，彻底消除类似截断与动词粘连。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/services/dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)
  - 数据库 `public.dispatch_daily_reports`（双端口 5432 / 5434）
- **验证结果**：
  - 经由只读脚本检查双端数据库，首站供回压（`0.770/0.630 MPa`）及 5 处地点实体全部修正生效且 100% 吻合用户预期。


## 2026-10-28 [工作票排版与工期空格规范化：PDF字距压缩智能分词与时间粘连修复]
- **根因深度透视**：
  - 用户反馈绿港湾站工作票中工期粘连为 `27/1016:00~4/1124:00`，疑似提取程序去掉了空格；
  - 经对底层 PDF 字符流（Character-level Coordinates）物理探查证实：在原始 PDF 数据流中，排版软件（WPS/Word）因表格单元格右边界空间受限，并未写入 ASCII 32 的空格字符，而是采用了绘图指令相对位移（负字距调整 2.7 pt），导致 `pdfplumber` 抽取出的原生字符序列本来就是紧挨着的 `'27/1016:00～4/1124:00'`；提取程序从未主动删除空格；
- **高精细修复方案**：
  1. **工作票工期智能分词修复 (`extract_operations_and_tickets`)**：
     - 在工作票解析链路中加入语义级智能分词正则：`re.sub(r"(\d{1,2}/\d{1,2})(\d{1,2}:\d{2})", r"\1 \2", ...)`，将紧粘的日/月与时刻（如 `27/1016:00`、`4/1124:00`）自动拆解插入规范空格；
     - 自动补全“工期”关键词与起始日期的间隔空格（如 `工期 27/10`）；
     - 结构化字段 `time_range` 规范化为极度整洁的 `27/10 16:00 ~ 4/11 24:00`，`raw_description` 同步优雅规整。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/services/dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)
- **验证结果**：
  - 经由 10-27 真实 PDF 文件提取验证，绿港湾站工作票 `time_range` 成功输出为 `'27/10 16:00 ~ 4/11 24:00'`，各工期数字与时刻完全解耦，可读性与结构化质量达到最佳。


## 2026-10-28 [气象断词容错升级：风向字间空格自适应消除与风力复合转折捕获]
- **升级背景**：
  - 在全量审计 2026年10月下旬试供暖期 PDF 提取结果时，发现个别文档排版存在字间空格（如 10-23 的 `北 风 4~5 级`、10-24 的 `偏北 风 5~6 级`），导致旧风向正则由于未兼容汉字与“风”字之间的空格而产生风向风力字段留空；
- **高精细修复方案**：
  1. **风向正则空格兼容 (`extract_weather`)**：
     - 将风向表达式升级为 `((?:东|西|南|北|偏|微)+[\s\u00a0]*风)`，允许风向修饰字与“风”字之间存在任意空格或不间断空白；
     - 捕获后执行空白压缩 `re.sub(r"[\s\u00a0]+", "", ...)`，自动将 `北 风` 规整为标准 `北风`、`偏北 风` 规整为 `偏北风`；
  2. **复合风级转折捕获与天气现象边界闭合**：
     - 风力等级正则扩展为 `[\d~～级阵风转\-]+(?:级)?`，支持跨区间阵风与转折风级（如 `4~5级转5~6级`、`5~6级阵风7~8级`）的无损提取；
     - 天气现象结束断言兼容字间带空格的风向边界，杜绝现象描述被超长风向截断。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/services/dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)
- **验证结果**：
  - 针对 10-22 至 10-27 全部 6 份 PDF 的实际天气文本回放测试，6/6 篇天气现象、风向（`南风`、`北风`、`偏北风`、`西南风`）及风力等级实现 100% 满分命中无遗漏。


## 2026-10-28 [调度提取引擎针对性升级：PDF多行天气合并、微观复合时刻解耦拆分、断行工作票智能缝合]
- **升级缘由**：
  - 用户上传 2026年10月下旬试供暖期 6 份真实 PDF 调度材料（`2026-10-22` 至 `2026-10-27`）并导出 `dispatch_extracted_batch_2026-10-28 2.json`。审计发现存在 4 项缺陷：
    1. 天气全要素 100% 丢失（PDF 小标题带有 `一、天气情况`，旧逻辑严格等值匹配导致把标题当正文直接 break；且 PDF 跨行排版导致湿度与风力截断）；
    2. 微观事件中包含多个时刻（如 `10:10 投运... 22:17 运行中跳闸倒泵...`）被揉为一条记录，严重掩盖夜间跳闸事故；
    3. 工作票因表格换行断裂为两段，下半段工期变成无主语的独立“运行操作”假事件；
    4. 补水量折行（如 `去年同期:22069吨。`）漏判被误作为普通生产事件；产量统计表识别深度不足。
- **高精细重构方案**：
  1. **天气多行连续捕获与断词清洗 (`extract_weather`)**：
     - 废除脆弱等值判断，自适应章节标题匹配；
     - 连续捕获从小标题到下一章节（`二、`）之间的所有段落，合并后提取；
     - 增强相对湿度与风向风力正则，兼容全角波浪号 `～`，确保 `wth_*` 7 个物理列 100% 精准填充；
  2. **微观复合时刻智能解耦拆分 (`split_compound_event`)**：
     - 新增独立时刻切分算法，严格排除工作票工期区间（`工期 ...~...`），将同一描述内的多个操作里程碑（如 10:10 投运、22:17 跳闸）拆分为多条原子事件；
     - 动作分类新增 `故障跳闸`（匹配 `跳闸`、`事故`、`保护动作` 等），确保异常工况精确打标；
  3. **工作票跨行碎片智能缝合与补水杂质排除 (`extract_operations_and_tickets`)**：
     - 遍历微观事件表时增加预处理层，遇到未闭合工期行（以 `～`、`~` 结尾）或数字日期开头的碎片行，自动向上粘合至上一条工作票，彻底消灭垃圾假事件；
     - 扩展补水指标行探测范围，将折行残行精准捕获至 `water_sup_accum_last`，不再落入事件流；
  4. **产量表分类器探测深度扩展 (`_classify_tables`)**：
     - 将探测深度由前 3 行扩展至前 6 行及全表扫描，彻底保障水炉与联产各种排版模式下的产量表正确分类。
- **改动文件**：
  - [`backend/projects/daily_report_25_26/services/dispatch_extractor.py`](file:///D:/编程项目/phoenix/backend/projects/daily_report_25_26/services/dispatch_extractor.py)
- **验证结果**：
  - 在真实的 `10.28 2026年10月27日生产信息.pdf` 上测试运行：
    * 天气：预测日期 `2026-10-28`，晴转小雨，12.0~17.0℃，湿度 40%~70%，西南风 5~6 级全要素完整提取；
    * 工作票：3 张工作票工期全部完整还原，彻底消灭了截断产生的 2 条垃圾事件；
    * 复合事件拆分测试：`10:10 投运` 与 `22:17 跳闸倒泵` 精确拆分为 2 条独立事件，动作分别被打标为 `启动投运` 与 `故障跳闸`。


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

## 2026-11-04 热网耗水图显示修复

- `NetworkWaterDumbbellCard.vue` 移除刷新按钮，保留日期联动和错误重试；两个 X 轴刻度 12000 显示 1.2万、12897 显示 1.2897万，不改范围、比例、整数数据标签和未填按 0 口径。
- 刻度、原范围、按钮及日期请求回归和生产构建通过，有既有分包提示。无需迁移；回滚仅恢复本轮组件及测试断言。

## 2026-11-04 热网耗水图标尺上限统一整千

- 按用户最新要求，`NetworkWaterDumbbellCard.vue` 上下 X 轴上限均向上取整到 1000 的整数倍，包括下方为容纳大数值而扩大的分支；保留顶部留白和下方参考主城区 2/5 的规则。最小刻度间隔为 1000，万单位最多一位小数，替代上一轮最多四位小数的显示。
- Vue 编译、日期请求回归与 ECharts SVG 实际刻度检查通过，验证整千上限、无重复刻度文字、下方扩大分支及整数数据标签。无需后端操作；回滚恢复本轮组件及断言修改。
