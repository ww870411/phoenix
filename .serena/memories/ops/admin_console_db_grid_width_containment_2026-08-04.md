时间：2026-08-04
主题：修复全局后台数据库大表撑宽页面

用户反馈：
- 选择列数较多或列宽较大的表后，整个全局后台页面被撑宽。
- 期望页面宽度保持不变，仅数据库表编辑区域水平滚动。

根因：
- RevoGrid 列总宽度通过 CSS Grid/Flex 子项默认 min-width:auto 的最小内容宽度向父级传播。
- db-grid-wrap 原使用 overflow:hidden，没有明确承担水平滚动。

变更文件：
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
1. admin-console-main、top-shell、content-block、db-editor-card 增加 width/max-width:100%、min-width:0、box-sizing:border-box 的收缩链路。
2. db-editor-card 使用 overflow:hidden，阻止大表宽度影响页面。
3. db-grid-wrap 使用 width/max-width:100%、min-width:0、overflow-x:auto、overflow-y:hidden、contain:inline-size。
4. db-data-grid 增加 min-width:0、max-width:100%。
5. 列宽算法、RevoGrid 编辑、抽屉和后端保存协议未改变。

验证：
- frontend npm run build 通过。
- Vite 7.1.10，139 modules transformed，built in 6.12s，零编译错误。
- git diff --check 无空白错误，仅有现有 CRLF/LF 策略提示。
- 浏览器自动化仍不可用，需用户在登录态大表下确认视觉滚动手感。

回滚：
- 删除上述六个 CSS 规则中的新增宽度/overflow/contain 属性即可；无后端或数据库迁移。