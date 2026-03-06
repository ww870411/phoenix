时间：2026-03-06
主题：Banner 与按钮文字换行规整修正

现象：
- 顶部 banner 文案在窄屏下存在不整齐换行。
- 部分按钮文字在手机宽度下被拆成两行，视觉较乱。

修正范围：
- frontend/src/projects/daily_report_25_26/components/AppHeader.vue
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue

修正内容：
1. AppHeader.vue
- 为 brand-name、brand-sub、user-info、nav 按钮增加 white-space: nowrap 与 word-break: keep-all。
- 为按钮增加 writing-mode: horizontal-tb，避免异常纵排或拆字。
- 收紧 <=640px 下的头部 padding、gap、字号和按钮内边距，降低换行概率。

2. MonthlyDataShowQueryToolView.vue
- 为 .btn 增加单行文本约束（nowrap / keep-all / horizontal-tb）。
- section-actions 改为默认不换行，极窄屏下仍保持受控的弹性宽度，避免按钮字面被拆成两行。

3. MonthlyDataPullEntryView.vue
- 为 .btn 与 .result-download 增加单行文本约束。

验证：
- frontend 目录执行 npm run build，2026-03-06 构建通过。

影响范围：
- 仅前端文字换行与按钮排版样式层，无功能逻辑变更。