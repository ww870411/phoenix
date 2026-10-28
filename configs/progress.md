# Phoenix 凤凰计划 · 开发过程记录 (Progress Log)

> 注：2026-10-28 09:00 前的历史进程日志已归档至 [configs/归档/progress.md](file:///D:/编程项目/phoenix/configs/归档/progress.md)。

---

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
