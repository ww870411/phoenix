FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_INDEX_URL=https://pypi.org/simple \
    PIP_EXTRA_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_TRUSTED_HOST=mirrors.aliyun.com

WORKDIR /app

# 切换阿里云 Debian APT 源（替代超时的中科大源），安装 postgresql-client
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -eu; \
    for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do \
        if [ -f "$source_file" ]; then \
            sed -i -e 's|https\?://deb\.debian\.org|https://mirrors.aliyun.com|g' \
                -e 's|https\?://security\.debian\.org|https://mirrors.aliyun.com|g' "$source_file"; \
        fi; \
    done \
    && apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends postgresql-client

# 使用 BuildKit 持久缓存挂载安装依赖（不增大镜像体积，且重编时已下载包秒级复用）
COPY backend/requirements.txt /tmp/backend_requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 -r /tmp/backend_requirements.txt

# 仅复制后端源码目录，避免无关文件打断构建缓存
COPY backend /app/backend

EXPOSE 8000

# 数据与配置目录（通过 Compose 绑定挂载到 /app/data）
VOLUME ["/app/data"]

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

