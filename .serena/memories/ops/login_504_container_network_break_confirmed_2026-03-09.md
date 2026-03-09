时间：2026-03-09
主题：线上登录 504 最终收敛为 Docker 同网容器间访问异常

新增用户回传证据：
- `docker top phoenix-backend` 显示 uvicorn 主进程与 reload 子进程存在。
- `docker logs phoenix-backend` 显示：
  - `Uvicorn running on http://0.0.0.0:8000`
  - `Application startup complete`
- 容器内 Python 自检：
  - `socket.connect_ex(('127.0.0.1', 8000)) == 0`
  - `urllib.request.urlopen('http://127.0.0.1:8000/healthz')` 正常返回健康检查 JSON。

更新后的结论：
- `phoenix-backend` 容器内部服务已经正常启动，端口 8000 也已监听。
- `phoenix-web` 侧此前报错仍为：
  - `upstream timed out while connecting to upstream`
  - upstream=`http://172.19.0.3:8000/api/v1/auth/login`
- 因此最终故障点不是 FastAPI 代码或端口未监听，而是同一 Docker 网络内 `phoenix-web -> phoenix-backend` 的容器间访问异常。

高优先级下一步：
1. 从 `phoenix-web` 容器内直接请求 `http://backend:8000/healthz` 验证。
2. 若失败，优先重建生产 compose 栈与其 network。
3. 代码层面后续可考虑移除 `backend/Dockerfile.prod` 的 `--reload` 作为硬化措施，但不是本次 504 的直接根因。