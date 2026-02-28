时间：2026-02-28
主题：monthly_data_pull 第三阶段 - 关系匹配界面与执行闭环

用户诉求：
- 保留原“源文件与底表对应关系”交互形式；
- 将 monthly_data_pull 做成真正可执行的在线导表模块。

后端实现：
1) 新增引擎
- backend/projects/monthly_data_pull/services/engine.py
- 能力：
  - 映射解析（识别源键/目标键、分组、源 sheet 需求）
  - 本月值写入（支持单元格与简单表达式）
  - 累计粘贴动作（推荐动作含“粘贴+累计”）
  - 输出目标副本到 outputs 目录

2) 扩展接口
- backend/projects/monthly_data_pull/api/workspace.py
- 新接口：
  - POST /monthly-data-pull/analyze-mapping
  - POST /monthly-data-pull/get-sheets
  - POST /monthly-data-pull/execute
  - GET /monthly-data-pull/download/{filename}
- 保留接口：workspace/files/upload/files list

前端实现：
1) API 扩展
- frontend/src/projects/daily_report_25_26/services/api.js
  - analyzeMonthlyDataPullMapping
  - getMonthlyDataPullSheets
  - executeMonthlyDataPull
  - buildMonthlyDataPullDownloadUrl

2) 页面重构
- frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
- 三步流程：
  - 上传映射解析
  - 按组显示源/目标关系卡并上传匹配文件与 sheet
  - 执行导表并下载输出

文档留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md

当前状态：
- monthly_data_pull 已具备在线导表最小闭环。
- 后续可继续接入：预检报告、LibreOffice 重算任务、累计差异报告强化。