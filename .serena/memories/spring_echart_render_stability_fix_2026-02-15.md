时间戳：2026-02-15
证据：用户提供 2.16 气温调试信息2，显示 temperature 数据/echartsPayload 完整，但图仍空白。

判断：
- 数据链路正常，问题集中在 EChart 实例渲染时序或容器尺寸更新。

修复：
- 文件：frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- EChart 组件改动：
  1) setOption 后 requestAnimationFrame + resize
  2) ensureChart 中 nextTick 后应用 option
  3) 新增 ResizeObserver 监听容器尺寸变化并触发 resize
- 调试字段新增：chartLibraryReady、hasWindowEcharts

结果：
- 提升图表挂载与布局变化时的渲染稳定性，降低“有数据无曲线”风险。