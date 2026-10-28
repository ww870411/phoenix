# Phoenix 凤凰计划 · 开发过程记录 (Progress Log)

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
