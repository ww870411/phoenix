时间：2026-02-25
主题：DataAnalysisView 白屏修复（isGlobalAdmin 未定义）

变更文件：
1) frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

根因：
- aiFeatureAccessible 计算属性仍引用旧变量 isGlobalAdmin，运行时报 ReferenceError 导致页面白屏。

修复：
- 改为使用当前权限计算变量 canConfigureAiSettings：
  aiFeatureAccessible = canConfigureAiSettings || allowNonAdminAiReport。

验证：
- frontend npm run build 通过。