时间：2026-03-06
主题：后端 requirements 固定版本以减少 Docker 构建回溯

背景：
- 用户希望先解决构建慢问题中的“版本号未锁定”部分。
- 已有分析指向 backend/Dockerfile.prod 中 pip install -r requirements.txt 的解析慢点，尤其是 google-generativeai 链路触发的 grpcio-status 回溯。

变更文件：
- backend/requirements.txt
- configs/progress.md
- frontend/README.md
- backend/README.md

requirements.txt 变更：
- pydantic-settings==2.13.1
- passlib[bcrypt]==1.7.4
- python-jose[cryptography]==3.5.0
- python-multipart==0.0.22
- openpyxl==3.1.5
- psycopg2-binary==2.9.11
- httpx==0.28.1
- google-generativeai==0.8.6
- psutil==7.2.2
- paramiko==3.5.1
- grpcio==1.76.0
- grpcio-status==1.71.2

验证：
- 本机执行 python -m pip install --dry-run -r backend/requirements.txt 成功。
- 输出未出现版本冲突，并给出确定的安装集合。

结论：
- 这一步已完成“先锁版本，减少 pip 依赖回溯”的目标。
- 若 Docker clean build 仍明显偏慢，下一步优先应切到 Dockerfile.prod 的 pip/apt 镜像源与 BuildKit cache。