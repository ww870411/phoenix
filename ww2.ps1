param(
  [string]$Timestamp
)

$ErrorActionPreference = "Stop"

# 项目根目录
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# 时间戳（可传参覆盖，否则自动生成）
if (-not $Timestamp) { $Timestamp = Get-Date -Format "yyyyMMddHHmmss" }

# Docker Hub 用户名
$RegistryUser = $env:REGISTRY_USER; if (-not $RegistryUser) { $RegistryUser = "ww870411" }

# 镜像名
$BACKEND_IMAGE = "$RegistryUser/phoenix-backend:$Timestamp"
$WEB_IMAGE     = "$RegistryUser/phoenix-web-http:$Timestamp"

# Build arg，只保留时间戳
$BuildArgs = @("--build-arg", "BUILD_TIMESTAMP=$Timestamp")

# ------- 后端 -------
Write-Host "== 构建后端镜像 $BACKEND_IMAGE =="
docker build `
  --file "$ProjectRoot/backend/Dockerfile.prod" `
  --tag  "$BACKEND_IMAGE" `
  $BuildArgs `
  "$ProjectRoot"

Write-Host "== 推送后端镜像 $BACKEND_IMAGE =="
docker push "$BACKEND_IMAGE"

# ------- 前端 (仅HTTP) -------
Write-Host "== 构建前端镜像 $WEB_IMAGE =="
docker build `
  --file "$ProjectRoot/deploy/Dockerfile.web" `
  --tag  "$WEB_IMAGE" `
  $BuildArgs `
  "$ProjectRoot"

Write-Host "== 推送前端镜像 $WEB_IMAGE =="
docker push "$WEB_IMAGE"

Write-Host "== 全部镜像推送完成 =="
Write-Host "部署提示："
Write-Host "  BACKEND_IMAGE=$BACKEND_IMAGE"
Write-Host "  WEB_IMAGE=$WEB_IMAGE"
