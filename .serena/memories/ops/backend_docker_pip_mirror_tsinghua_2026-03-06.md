时间：2026-03-06
主题：后端 Docker 构建切换 pip 国内镜像源

目标：
- 解决 lo1_new_server.ps1 构建链路中 backend/Dockerfile.prod 的 pip 下载速度慢问题，优先通过镜像源切换降低网络等待时间。

变更文件：
- backend/Dockerfile.prod
- configs/progress.md
- frontend/README.md
- backend/README.md

实际修改：
- 在 backend/Dockerfile.prod 的 builder 阶段 ENV 中新增：
  - PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
  - PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

影响：
- Docker 构建里的 pip install --prefix=/install -r requirements.txt 默认走清华 PyPI 镜像。
- 本轮未改 apt 源、未启用 BuildKit cache、未调整 lo1_new_server.ps1 本身。

验证：
- 本次为 Dockerfile 静态修改，未执行实际 docker build。
- 用户后续可直接用 ./lo1_new_server.ps1 观察 backend 依赖下载阶段耗时变化。