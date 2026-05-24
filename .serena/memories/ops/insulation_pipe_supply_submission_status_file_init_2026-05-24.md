时间：2026-05-24
主题：初始化 insulation_pipe_supply_2026 换热站提交状态独立运行态文件。

本次变更：
- 新增文件：`backend_data/projects/insulation_pipe_supply_2026/station_submission_status.json`
- 初始结构：
```json
{
  "latest_submissions": [],
  "history_submissions": []
}
```

设计口径：
- 该文件不属于主配置，不再写入 `tube_config.json`
- 仅用于记录各换热站“填报完毕提交”状态
- `latest_submissions`：系统判断当前站点提交状态时只读取这一块
- `history_submissions`：保存被新提交挤下来的旧记录

当前范围：
- 仅完成文件初始化
- 尚未接入需求侧提交按钮
- 尚未接入提交前置校验
- 尚未接入全局管理页状态展示与写入逻辑

同步文档：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`