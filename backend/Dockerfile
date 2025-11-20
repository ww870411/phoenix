FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 可选：加速国内源（按需启用）
# RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制依赖文件并优先安装，便于充分利用缓存
COPY backend/requirements.txt /tmp/backend_requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend_requirements.txt

# 再复制全部源代码
COPY . /app

EXPOSE 8000

# 数据与配置目录（通过 Compose 绑定挂载到 /app/data）
VOLUME ["/app/data"]

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

