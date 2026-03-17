时间：2026-03-17
任务：将 daily_report_25_26 数据看板缓存发布执行器从线程模型切换为多进程模型，并保持现有 API 兼容。
变更文件：
1) backend/services/dashboard_cache_job.py
2) backend/projects/daily_report_25_26/api/dashboard.py
3) backend/api/v1/admin_console.py
降级说明：原计划使用 apply_patch 修改调用点，但在 Windows 沙箱下连续两次出现 setup refresh failed，随后按仓库降级规则改用 desktop-commander edit_block 完成精确替换。
实现摘要：
- 发布任务由 Thread 改为 multiprocessing.Process；
- 任务状态从进程内内存改为 runtime 目录下的 dashboard_cache_publish_state.json；
- 取消信号改为 dashboard_cache_publish_cancel.flag；
- 运行互斥改为 dashboard_cache_publish.lock，避免重复启动；
- snapshot/request_cancel 改为显式接收 project_key，通过状态文件跨进程读取；
- 保留 start/snapshot/request_cancel 的接口返回结构，前端轮询链路无需改动。
验证：
- py_compile 校验通过：dashboard_cache_job.py、dashboard.py、admin_console.py；
- 状态文件层验证通过：可返回 running 状态和子进程 pid；
- 新进程 snapshot 能识别并清理已退出进程的 stale running 状态。
限制说明：
- 当前阶段主要解决“发布任务不再绑死在线程内存状态、为多核执行做基础设施准备”；
- 单日发布想真正吃满多核，下一步仍需继续把 evaluate_dashboard 内部板块进一步做进程级并行。