## 2025-12-10 数据分析筛选布局优化
- 位置：frontend/src/daily_report_25_26/pages/DataAnalysisView.vue。
- 新增 form-layout/form-grid--top 容器，将“单位选择（多选）”与“分析模式”固定在第一行两列，`form-panel--metrics` 让“指标选择（多选）”独占下一行的全宽滚动区域。
- CSS 增补于同文件 `<style scoped>` 区域，min-width 320px 保证宽屏时两列并排，窄屏自动折行。
- README（frontend/backend）与 configs/progress.md 均新增 2025-12-10 小结，注明此次为前端交互优化，无后端接口变更。