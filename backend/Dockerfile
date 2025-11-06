FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 可选：加速国内源（按需启用）
# RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制代码与依赖文件
COPY . /app

# 安装依赖（若未来添加 requirements.txt/pyproject.toml，可改为更严谨的安装方式）
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic "sqlalchemy>=2.0" psycopg2-binary openpyxl

EXPOSE 8000

# 数据与配置目录（通过 Compose 绑定挂载到 /app/data）
VOLUME ["/app/data"]

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

