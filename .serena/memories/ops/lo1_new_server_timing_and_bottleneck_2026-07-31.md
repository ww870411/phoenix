# 新服务器部署脚本阶段计时与实测瓶颈

日期：2026-07-31（Asia/Hong_Kong）

## 变更
- 修改 `lo1_new_server.ps1`：后端构建、前端构建、后端推送、前端推送均经 `Invoke-TimedPhase` 计时并输出退出码。
- 新增 `Show-PhaseSummary`，部署结束显示阶段表、最长阶段和总耗时。
- 两个 Docker 构建启用 `--progress=plain`，保留逐层耗时证据。

## 实测
- 标签：`20260731205209`，镜像均已推送至 Docker Hub。
- 后端 ARM64 构建：6.0 秒；`pip install` 和 apt 层均为 CACHED。
- 前端 ARM64 构建：139.5 秒；构建上下文 187.03MB，Vite 生产构建 106 秒。
- 后端推送：15.2 秒；前端推送：11.7 秒；总计 172.5 秒。
- 结论：当前瓶颈是前端 ARM64 环境内的 Vite 生产构建，不是后端依赖安装或 Docker Hub 上传。
- 未执行服务器侧 `docker-compose -f lo1_new_server.yml up -d`。