Param(
    [string]$Tag
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
if (-not $ProjectRoot) {
    throw "无法确定脚本所在目录。"
}

$DockerBin = if ($env:DOCKER_BIN) { $env:DOCKER_BIN } else { "docker" }
if (-not (Get-Command -Name $DockerBin -ErrorAction SilentlyContinue)) {
    throw "[错误] 未找到 docker 命令，请先安装 Docker 或设置 DOCKER_BIN 环境变量。"
}

$timestamp = if ($Tag) { $Tag } else { Get-Date -Format "yyyyMMddHHmmss" }
$registryUser = if ($env:REGISTRY_USER -and $env:REGISTRY_USER.Trim()) { $env:REGISTRY_USER } else { "ww870411" }

$backendImage = if ($env:BACKEND_IMAGE -and $env:BACKEND_IMAGE.Trim()) { $env:BACKEND_IMAGE } else { "$registryUser/phoenix-backend:$timestamp" }
$webImage = if ($env:WEB_IMAGE -and $env:WEB_IMAGE.Trim()) { $env:WEB_IMAGE } else { "$registryUser/phoenix-web:$timestamp" }
$webHttpImage = if ($env:WEB_HTTP_IMAGE -and $env:WEB_HTTP_IMAGE.Trim()) { $env:WEB_HTTP_IMAGE } else { "$registryUser/phoenix-web-http:$timestamp" }

$viteApiBase = if ($env:VITE_API_BASE -and $env:VITE_API_BASE.Trim()) { $env:VITE_API_BASE } else { "/api/v1" }
$buildArgs = @("--build-arg", "BUILD_TIMESTAMP=$timestamp")

function Write-Divider {
    param([string]$Message)
    Write-Host ""
    Write-Host "========== $Message =========="
}

Write-Divider "构建后端镜像 $backendImage"
& $DockerBin build `
    --file (Join-Path $ProjectRoot "backend/Dockerfile.prod") `
    --tag $backendImage `
    $buildArgs `
    $ProjectRoot

Write-Divider "推送后端镜像 $backendImage"
& $DockerBin push $backendImage

Write-Divider "构建前端镜像 $webImage"
& $DockerBin build `
    --file (Join-Path $ProjectRoot "deploy/Dockerfile.web") `
    --tag $webImage `
    $buildArgs `
    --build-arg "VITE_API_BASE=$viteApiBase" `
    $ProjectRoot

Write-Divider "推送前端镜像 $webImage"
& $DockerBin push $webImage

Write-Divider "构建 HTTP-only 前端镜像 $webHttpImage"
& $DockerBin build `
    --file (Join-Path $ProjectRoot "deploy/Dockerfile.web") `
    --tag $webHttpImage `
    $buildArgs `
    --build-arg "VITE_API_BASE=$viteApiBase" `
    --build-arg "HTTP_ONLY=true" `
    $ProjectRoot

Write-Divider "推送 HTTP-only 前端镜像 $webHttpImage"
& $DockerBin push $webHttpImage

Write-Divider "镜像推送完成"
Write-Host "后续可在服务器设置下列变量或更新 docker compose："
Write-Host ("  BACKEND_IMAGE={0}" -f $backendImage)
Write-Host ("  WEB_IMAGE={0}" -f $webImage)
Write-Host ("  WEB_HTTP_IMAGE={0}" -f $webHttpImage)
