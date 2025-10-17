常用命令（Windows，本地开发）：

后端
- 创建虚拟环境（如需）：`python -m venv .venv && .venv\\Scripts\\activate`
- 安装依赖：`pip install -r requirements.txt`（如有）
- 本地运行：`uvicorn backend.main:app --reload --port 8000`
- 健康检查：`curl http://127.0.0.1:8000/healthz`
- v1 Ping：`curl http://127.0.0.1:8000/api/v1/ping`

前端
- 安装依赖：`npm install`
- 开发模式：`npm run dev`（默认端口 5173）
- 构建产物：`npm run build`；预览：`npm run preview`

容器（如使用）
- 启动：`docker compose up -d`
- 查看：`docker compose ps`
- 关闭：`docker compose down`

注意：请以仓库内实际脚本/锁文件为准（如 `package.json`、`Dockerfile`）。