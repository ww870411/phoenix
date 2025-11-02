#!/usr/bin/env bash
set -euo pipefail

# =========================
# Phoenix build & push script
# =========================

# 项目根目录（脚本所在位置）
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"

if ! command -v "${DOCKER_BIN}" >/dev/null 2>&1; then
  echo "[错误] 未找到 docker 命令，请先安装 Docker 或设置 DOCKER_BIN 环境变量。" >&2
  exit 1
fi

# 可选：NO_CACHE=1 时，前端镜像构建加 --no-cache（用于清理被污染的构建层）
NO_CACHE="${NO_CACHE:-0}"
if [[ "${NO_CACHE}" == "1" ]]; then
  FRONTEND_BUILD_CACHE_ARGS=(--no-cache)
else
  FRONTEND_BUILD_CACHE_ARGS=()
fi

# 镜像标签：优先使用第一个脚本参数，否则按当前时间生成
TIMESTAMP="${1:-$(date +%Y%m%d%H%M%S)}"
REGISTRY_USER="${REGISTRY_USER:-ww870411}"

# 允许通过环境变量覆盖最终镜像名称
BACKEND_IMAGE="${BACKEND_IMAGE:-${REGISTRY_USER}/phoenix-backend:${TIMESTAMP}}"
WEB_IMAGE="${WEB_IMAGE:-${REGISTRY_USER}/phoenix-web:${TIMESTAMP}}"
WEB_HTTP_IMAGE="${WEB_HTTP_IMAGE:-${REGISTRY_USER}/phoenix-web-http:${TIMESTAMP}}"

# -------- API 基础路径处理（修正：不再 unset，允许外部 export 覆盖） --------
DEFAULT_API_BASE="/api/v1"
RAW_VITE_API_BASE="${VITE_API_BASE:-${DEFAULT_API_BASE}}"

sanitize_api_base() {
  local value="$1"
  local lowered="${value,,}"

  # 空值 → 默认
  if [[ -z "${value}" ]]; then
    printf "%s" "${DEFAULT_API_BASE}"
    return
  fi

  # 显式阻断 file:// 或 Windows 盘符路径
  if [[ "${lowered}" == file:* ]] || [[ "${value}" =~ ^[A-Za-z]:[\\/].* ]]; then
    printf '\n[警告] 检测到无效的 VITE_API_BASE=%s，已重置为 %s\n' "${value}" "${DEFAULT_API_BASE}" >&2
    printf "%s" "${DEFAULT_API_BASE}"
    return
  fi

  # 仅允许 http(s):// 或以 / 开头，其余回退默认
  if [[ ! "${value}" =~ ^https?:// ]] && [[ ! "${value}" =~ ^/ ]]; then
    printf '\n[警告] 检测到不受支持的 VITE_API_BASE=%s，已重置为 %s\n' "${value}" "${DEFAULT_API_BASE}" >&2
    printf "%s" "${DEFAULT_API_BASE}"
    return
  fi

  # 去除末尾多余的 /（避免双斜杠）
  printf "%s" "${value%/}"
}

VITE_API_BASE="$(sanitize_api_base "${RAW_VITE_API_BASE}")"
printf '\n[信息] 本次构建使用的 VITE_API_BASE=%s\n' "${VITE_API_BASE}"

# 所有构建均写入构建时间，便于追溯
BUILD_ARGS=("--build-arg" "BUILD_TIMESTAMP=${TIMESTAMP}")

# latest 辅助
derive_latest_ref() {
  local image="$1"
  if [[ "${image}" == *":"* ]]; then
    printf "%s:latest" "${image%:*}"
  else
    printf "%s:latest" "${image}"
  fi
}

tag_and_push_latest() {
  local source_image="$1"
  local latest_ref
  latest_ref="$(derive_latest_ref "${source_image}")"
  printf '\n[信息] 将 %s 同步为 latest 标签 %s\n' "${source_image}" "${latest_ref}"
  "${DOCKER_BIN}" tag "${source_image}" "${latest_ref}"
  "${DOCKER_BIN}" push "${latest_ref}"
}

print_divider() {
  printf '\n========== %s ==========\n' "$1"
}

# 在 MSYS/Git Bash 下，精确禁止把 VITE_API_BASE 当路径改写
with_msys_guard() {
  if [[ -n "${MSYSTEM:-}" ]]; then
    MSYS2_ARG_CONV_EXCL="*VITE_API_BASE*" "$@"
  else
    "$@"
  fi
}

# ------------------------
# 后端镜像构建与推送
# ------------------------
print_divider "构建后端镜像 ${BACKEND_IMAGE}"
"${DOCKER_BIN}" build \
  --file "${PROJECT_ROOT}/backend/Dockerfile.prod" \
  --tag "${BACKEND_IMAGE}" \
  "${BUILD_ARGS[@]}" \
  "${PROJECT_ROOT}"

print_divider "推送后端镜像 ${BACKEND_IMAGE}"
"${DOCKER_BIN}" push "${BACKEND_IMAGE}"
tag_and_push_latest "${BACKEND_IMAGE}"

# ------------------------
# 前端 HTTPS 版本镜像（默认 nginx.prod.conf，80/443）
# ------------------------
print_divider "构建前端镜像 ${WEB_IMAGE}"
with_msys_guard "${DOCKER_BIN}" build \
  "${FRONTEND_BUILD_CACHE_ARGS[@]}" \
  --file "${PROJECT_ROOT}/deploy/Dockerfile.web" \
  --tag "${WEB_IMAGE}" \
  "${BUILD_ARGS[@]}" \
  --build-arg "VITE_API_BASE=${VITE_API_BASE}" \
  "${PROJECT_ROOT}"

print_divider "推送前端镜像 ${WEB_IMAGE}"
"${DOCKER_BIN}" push "${WEB_IMAGE}"
tag_and_push_latest "${WEB_IMAGE}"

# ------------------------
# 前端 HTTP-only 版本镜像（certbot 初次申请/更新证书时使用）
# ------------------------
print_divider "构建 HTTP-only 前端镜像 ${WEB_HTTP_IMAGE}"
with_msys_guard "${DOCKER_BIN}" build \
  "${FRONTEND_BUILD_CACHE_ARGS[@]}" \
  --file "${PROJECT_ROOT}/deploy/Dockerfile.web" \
  --tag "${WEB_HTTP_IMAGE}" \
  "${BUILD_ARGS[@]}" \
  --build-arg "VITE_API_BASE=${VITE_API_BASE}" \
  --build-arg "HTTP_ONLY=true" \
  "${PROJECT_ROOT}"

print_divider "推送 HTTP-only 前端镜像 ${WEB_HTTP_IMAGE}"
"${DOCKER_BIN}" push "${WEB_HTTP_IMAGE}"
tag_and_push_latest "${WEB_HTTP_IMAGE}"

print_divider "镜像推送完成"
printf "后续请在服务器上设置如下变量或更新 docker compose（如 ww-http-only.yml）：\n"
printf "  BACKEND_IMAGE=%s\n" "${BACKEND_IMAGE}"
printf "  WEB_IMAGE=%s\n" "${WEB_IMAGE}"
printf "  WEB_HTTP_IMAGE=%s\n" "${WEB_HTTP_IMAGE}"

# 友好提示：首次从 Windows 修复该问题，建议临时加 NO_CACHE=1 以避免旧层缓存污染：
#   NO_CACHE=1 ./ww.bash
