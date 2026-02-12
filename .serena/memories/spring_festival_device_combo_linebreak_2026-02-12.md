时间：2026-02-12
需求：设备表中汽炉与汽轮机数量换行显示，便于左右对应。
改动：SpringFestivalDashboardView.vue 调整样式：device-combo-cell 改为列布局；combo-item 设置 min-width 与 justify-content: space-between，组合项逐行展示。
验证：frontend npm run build 通过。
留痕：configs/progress.md、frontend/README.md、backend/README.md 已同步。