#!/usr/bin/env bash
set -euo pipefail

# 项目根目录（脚本所在位置）
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"

if ! command -v "${DOCKER_BIN}" >/dev/null 2>&1; then
  echo "[错误] 未找到 docker 命令，请先安装 Docker 或设置 DOCKER_BIN 环境变量。" >&2
  exit 1
fi

# 镜像标签：优先使用第一个脚本参数，否则按当前时间生成
TIMESTAMP="${1:-$(date +%Y%m%d%H%M%S)}"
REGISTRY_USER="${REGISTRY_USER:-ww870411}"

# 允许通过环境变量覆盖最终镜像名称
BACKEND_IMAGE="${BACKEND_IMAGE:-${REGISTRY_USER}/phoenix-backend:${TIMESTAMP}}"
WEB_IMAGE="${WEB_IMAGE:-${REGISTRY_USER}/phoenix-web:${TIMESTAMP}}"
WEB_HTTP_IMAGE="${WEB_HTTP_IMAGE:-${REGISTRY_USER}/phoenix-web-http:${TIMESTAMP}}"

# 控制前端打包时的 API 基础路径，可在运行脚本前通过 export VITE_API_BASE=... 自定义
VITE_API_BASE="${VITE_API_BASE:-/api/v1}"

# 所有构建均写入构建时间，便于追溯
BUILD_ARGS=("--build-arg" "BUILD_TIMESTAMP=${TIMESTAMP}")

print_divider() {
  printf '\n========== %s ==========' "$1"
  printf '\n'
}

# 后端镜像构建与推送
print_divider "构建后端镜像 ${BACKEND_IMAGE}"
"${DOCKER_BIN}" build \
  --file "${PROJECT_ROOT}/backend/Dockerfile.prod" \
  --tag "${BACKEND_IMAGE}" \
  "${BUILD_ARGS[@]}" \
  "${PROJECT_ROOT}"

print_divider "推送后端镜像 ${BACKEND_IMAGE}"
"${DOCKER_BIN}" push "${BACKEND_IMAGE}"

# 前端 HTTPS 版本镜像（默认 nginx.prod.conf，80/443）
print_divider "构建前端镜像 ${WEB_IMAGE}"
"${DOCKER_BIN}" build \
  --file "${PROJECT_ROOT}/deploy/Dockerfile.web" \
  --tag "${WEB_IMAGE}" \
  "${BUILD_ARGS[@]}" \
  --build-arg "VITE_API_BASE=${VITE_API_BASE}" \
  "${PROJECT_ROOT}"

print_divider "推送前端镜像 ${WEB_IMAGE}"
"${DOCKER_BIN}" push "${WEB_IMAGE}"

# 前端 HTTP-only 版本镜像（certbot 初次申请/更新证书时使用）
print_divider "构建 HTTP-only 前端镜像 ${WEB_HTTP_IMAGE}"
"${DOCKER_BIN}" build \
  --file "${PROJECT_ROOT}/deploy/Dockerfile.web" \
  --tag "${WEB_HTTP_IMAGE}" \
  "${BUILD_ARGS[@]}" \
  --build-arg "VITE_API_BASE=${VITE_API_BASE}" \
  --build-arg "HTTP_ONLY=true" \
  "${PROJECT_ROOT}"

print_divider "推送 HTTP-only 前端镜像 ${WEB_HTTP_IMAGE}"
"${DOCKER_BIN}" push "${WEB_HTTP_IMAGE}"

print_divider "镜像推送完成"
printf "后续请在服务器上设置如下变量或更新 docker compose：\n"
printf "  BACKEND_IMAGE=%s\n" "${BACKEND_IMAGE}"
printf "  WEB_IMAGE=%s\n" "${WEB_IMAGE}"
printf "  WEB_HTTP_IMAGE=%s\n" "${WEB_HTTP_IMAGE}"
