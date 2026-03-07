# Phoenix Mobile Layout

## 目的
为 `phoenix` 项目的手机页面优化提供固定工作流，避免每次从头判断。

适用场景：
- 页面在手机宽度下出现按钮溢出、文字乱换行、顶部过高、表格难看、卡片过松
- 用户要求“保持 PC 效果，优化手机端”
- 需要在不动业务逻辑的前提下，做响应式布局修正

不适用场景：
- 用户要求重做整套视觉设计
- 需要新增复杂交互流程或重构数据结构
- 问题主要来自后端接口，而不是前端布局

## 项目约束
- 沟通、注释、文档统一中文
- 桌面端是默认基线：不要为了手机端破坏 PC 布局
- 优先小步修复，不做整页重写
- 每次改动后必须同步：
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`
- 必须写 Serena 记忆，说明范围、原因、验证结果

## 核心原则
1. 手机端优先“重排”，不是“缩放”
2. 顶部区域优先降高度，减少无意义空白
3. 单个按钮文字不拆字，但按钮组可以换层
4. 表格优先横滑，其次隐藏次要列，再考虑卡片化
5. 查询页优先收紧筛选区、摘要区、操作区
6. 复杂录入页允许横滑，不强行压成单列
7. 桌面端和移动端样式分开控制：桌面默认不改，只在窄屏断点覆盖

## 优化顺序
1. 先定位问题类型
2. 再判断属于哪类页面
3. 只改最小范围样式或模板结构
4. 构建验证
5. 浏览器手机视口复测
6. 同步文档与 Serena 留痕

## 问题分类
### 1. 顶部 Banner / Header 问题
表现：
- 品牌名、副标题、用户信息、按钮挤在一起
- 文案随机换行
- 顶部过高或过空

处理：
- 手机端把头部改为分层布局
- 品牌区固定两层：主标题 / 副标题
- 按钮区和用户信息独立成层
- 禁止单个按钮拆字：`white-space: nowrap`
- 不要用全局 `nowrap` 硬压所有元素

### 2. 按钮区问题
表现：
- 按钮溢出页面
- 文案拆成两行
- 手机端横向排布过满

处理：
- 手机断点下优先把按钮组改成纵向
- 如果保留横向，必须确保容器和按钮宽度逻辑一致
- 按钮文字统一：
  - `white-space: nowrap`
  - `word-break: keep-all`
  - `writing-mode: horizontal-tb`

### 3. 表格问题
表现：
- 列太多，手机上被压扁
- 容器宽度不够，按钮或表格溢出
- 可编辑网格难用

处理：
- 外层统一加横向滚动容器
- 设置合理 `min-width`
- 窄屏下压缩 padding、字号
- 对比表优先隐藏次要列
- RevoGrid 保留横滑，不强行改成单列

### 4. 查询页问题
表现：
- 筛选区太长
- 摘要卡片太大
- 顶部一打开就吃满一屏

处理：
- 收紧主容器 padding 和 section gap
- 压缩 summary 卡片高度和字号
- 下调多选区默认高度
- 查询按钮区手机端改为纵向

### 5. 桌面端被误伤
表现：
- PC 卡片太高
- 桌面按钮区过松
- 原本正常布局被移动端规则带坏

处理：
- 检查是否把手机规则写进了默认样式
- 只把新规则放进 `@media (max-width: ...)`
- 删除桌面端多余 `min-height`、`width: 100%`、`flex: 1` 等副作用规则

## 页面类型模板
### A. 入口页
适用：登录页、项目选择页、项目入口页

检查点：
- 顶部是否过高
- 卡片是否单列
- 按钮是否便于拇指点击
- 文案是否整齐

优先动作：
- 收紧视觉区高度
- 卡片改单列
- 按钮整行或双列紧凑布局
- 减少桌面端固定高度对手机端的影响

### B. 查询页
适用：月报查询页、分析筛选页

检查点：
- 筛选区是否过长
- 查询/重置按钮是否溢出
- 摘要卡片是否过大
- 表格是否可横滑

优先动作：
- 收紧筛选区高度
- 查询按钮区手机端纵向
- 摘要卡片缩小
- 表格容器加横滑

### C. 工作台页
适用：月报拉取页、带步骤卡的工具页

检查点：
- 顶部按钮是否太散
- 步骤卡是否过厚
- 预览区按钮是否断行或溢出

优先动作：
- 收紧主容器 padding
- 步骤卡减小内边距
- 操作按钮组改弹性或纵向

### D. 数据录入页
适用：DataEntry / Approval / Runtime 表格页

检查点：
- 顶部开关是否被拉成长条
- 项目信息与操作区间距是否异常
- 表格是否被压扁

优先动作：
- 顶部状态区改为紧凑横向换行
- 操作按钮区单独纵向
- 表格保留横滑和最小宽度
- 不增加多余解释性文案

### E. 看板 / 分析页
适用：Dashboard / DataAnalysis

检查点：
- 图表与表格并排是否过挤
- 对比表是否列太多
- 汇总折叠表是否可横滑

优先动作：
- 手机下改上下堆叠
- 对比表隐藏次要列
- 时间轴网格横滑
- 控制按钮改纵向或换层

## 固定工作流
### 第一步：定位
优先检查：
- 目标页面 `.vue` 文件
- 顶部区域：header、topbar、banner
- 按钮区：actions、toolbar、topbar-actions、preview-actions
- 表格区：table-wrap、result-table、RevoGrid 容器
- 断点：`@media (max-width: 900px)`、`768px`、`640px`

### 第二步：判断根因
常见根因：
- 容器横向 flex，但子项被设为 `width: 100%`
- 桌面端 `min-height` 误伤手机或 PC
- 手机端继续沿用桌面双栏布局
- 表格缺少外层横滑容器
- 按钮未限制单字不拆行

### 第三步：实施
修改原则：
- 优先改样式，不先动业务逻辑
- 模板结构只做最小重排
- 先修容器，再修子项
- 避免引入新的全局副作用

## 验证清单
每次改动后至少执行：
1. `frontend` 下 `npm run build`
2. 浏览器切到手机视口（推荐 390x844）
3. 检查以下项目：
- 顶部是否还挤在一起
- 按钮是否出界
- 按钮文字是否拆字
- 表格是否可横滑
- 移动端修正是否误伤 PC 布局

## 浏览器复测建议
- 登录页：检查视觉区高度与表单密度
- 项目选择页：检查卡片是否单列且桌面未变高
- 月报查询页：检查查询/重置按钮、摘要卡片、多选区高度
- 月报拉取页：检查顶部按钮和预览按钮是否整齐
- 数据填报页：检查项目说明、顶部开关、表格横滑
- Dashboard / DataAnalysis：检查头部、表格、图表堆叠

## 交付要求
最终回复必须说明：
- 做了什么
- 哪些文件在起作用
- 手机端是通过什么布局逻辑改善的
- 是否影响桌面端
- 是否完成构建验证

## 留痕要求
每次使用本 skill 做出有效修改后，必须同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`
- Serena memory

Serena memory 至少包含：
- 时间
- 页面名
- 触发问题
- 改动文件
- 解决策略
- 验证结果

## 推荐文件入口
高频文件：
- `frontend/src/projects/daily_report_25_26/components/AppHeader.vue`
- `frontend/src/pages/LoginView.vue`
- `frontend/src/pages/ProjectSelectView.vue`
- `frontend/src/pages/ProjectEntryView.vue`
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
- `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`
- `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
- `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`

## 使用方式建议
当用户提出以下类型问题时，优先使用本 skill：
- “手机上按钮跑出去了”
- “banner 乱换行”
- “表格在手机上太难看”
- “查询区太长”
- “手机改好了但桌面坏了”

一句话执行目标：
- 保住桌面端，压实手机端，优先重排，不优先缩放。
