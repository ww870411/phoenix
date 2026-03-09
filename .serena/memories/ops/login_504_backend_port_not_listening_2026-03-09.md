时间：2026-03-09
主题：线上登录 504 进一步收敛到 backend 容器 8000 端口未建立监听

新增用户回传证据：
- `docker ps -a` 显示线上运行的是正确的生产容器名：
  - phoenix-web
  - phoenix-backend
  - phoenix-db
- 三者同属 `25-26_phoenix_net`。
- `phoenix-web` 日志核心报错：
  - `upstream timed out (110: Operation timed out) while connecting to upstream`
  - upstream=`http://172.19.0.3:8000/api/v1/auth/login`
- 用户记录的 `phoenix-backend` 日志为空。

结论更新：
- 问题已不再是“容器不在同一网络”或“nginx 找不到 backend”。
- Nginx 已正确解析 backend 容器 IP，但与 172.19.0.3:8000 建立 TCP 连接时超时。
- 说明 Phoenix backend 容器虽然显示 Up，但其内部 8000 端口大概率未真正监听。
- 高概率场景：
  1) `uvicorn` 子进程未成功拉起；
  2) 应用导入阶段阻塞，父进程存活但服务未绑定端口；
  3) 生产命令带 `--reload` 导致容器内仅保留监控父进程，实际 worker 未就绪。

下一步服务器侧最短核查命令：
- `docker exec phoenix-backend ps -ef`
- `docker exec phoenix-backend ss -ltnp`
- `docker exec phoenix-backend curl http://127.0.0.1:8000/healthz`
- `docker inspect phoenix-backend --format '{{json .State}}'`

代码侧补充观察：
- `backend/Dockerfile.prod` 当前 CMD 为：
  - `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload`
- 对生产容器而言，`--reload` 不合理，后续可考虑去掉并补 backend healthcheck，但这属于防御性改进，不是当前线上故障的直接证据。