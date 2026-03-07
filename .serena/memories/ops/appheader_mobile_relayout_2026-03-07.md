时间：2026-03-07
主题：全局 AppHeader 手机端重排

背景：
- 用户反馈手机端 banner 经过前一次 nowrap 修正后，元素都挤在一起，观感不好。
- 结论：问题不在于是否换行，而在于头部仍沿用桌面端横向布局，手机端缺少真正的分层重排。

变更文件：
- frontend/src/projects/daily_report_25_26/components/AppHeader.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实际修改：
- 模板层：品牌区新增 brand-text 容器，将集团名与平台名固定为上下两层。
- 样式层：
  - brand 改为对齐中心，brand-text 为纵向排列。
  - <=640px 下将 app-header__inner 改为纵向分层布局。
  - nav 区允许整体换层与换行，但按钮和文字本身仍保持不拆字。
  - user-info 在手机端提升为独立一行信息。

结果：
- 手机端头部从“所有元素挤一行”改为“品牌层 + 操作层”的结构。
- 桌面端头部结构保持原样。

验证：
- frontend 目录执行 npm run build，2026-03-07 构建通过。