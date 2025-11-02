param(
  [string]$Timestamp
)

$ErrorActionPreference = "Stop"

# --- 基本环境 ---
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "[错误] 未找到 docker 命令，请先安装 Docker Desktop / CLI。"
}

# 时间戳（可传参覆盖）
if (-not $Timestamp) { $Timestamp = Get-Date -Format "yyyyMMddHHmmss" }

# 镜像命名
$RegistryUser   = $env:REGISTRY_USER; if (-not $RegistryUser) { $RegistryUser = "ww870411" }
$BACKEND_IMAGE  = if ($env:BACKEND_IMAGE)  { $env:BACKEND_IMAGE }  else { "$RegistryUser/phoenix-backend:$Timestamp" }
$WEB_IMAGE      = if ($env:WEB_IMAGE)      { $env:WEB_IMAGE }      else { "$RegistryUser/phoenix-web:$Timestamp" }
$WEB_HTTP_IMAGE = if ($env:WEB_HTTP_IMAGE) { $env:WEB_HTTP_IMAGE } else { "$RegistryUser/phoenix-web-http:$Timestamp" }

# 是否无缓存构建前端
$FrontendBuildCacheArgs = @()
if ($env:NO_CACHE -eq "1") { $FrontendBuildCacheArgs += "--no-cache" }

# ------- 构建参数 -------
$BuildArgs = @("--build-arg", "BUILD_TIMESTAMP=$Timestamp")


function Divider([string]$Title) { Write-Host ""; Write-Host "========== $Title ==========" }

function Invoke-Retry([scriptblock]$Action, [int]$Attempts = 3, [int]$DelaySeconds = 6, [string]$Name = "task") {
  for ($i = 1; $i -le $Attempts; $i++) {
    try {
      & $Action
      if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "exit=$LASTEXITCODE" }
      return
    } catch {
      if ($i -eq $Attempts) { throw "[失败] $Name 第 $i 次：$($_.Exception.Message)" }
      Write-Warning "[重试] $Name 第 $i 次失败，$DelaySeconds 秒后重试"
      Start-Sleep -Seconds $DelaySeconds
    }
  }
}

# ---------------- 后端 ----------------
# 预拉基础镜像，降低网络抖动导致的失败
Divider "预拉基础镜像"
Invoke-Retry { docker pull python:3.12-slim } -Name "pull python"
Invoke-Retry { docker pull node:20-alpine } -Name "pull node"
Invoke-Retry { docker pull nginx:1.27-alpine } -Name "pull nginx"

Divider "构建后端镜像 $BACKEND_IMAGE"
Invoke-Retry { docker build `
  --pull `
  --file "$ProjectRoot/backend/Dockerfile.prod" `
  --tag  "$BACKEND_IMAGE" `
  $BuildArgs `
  "$ProjectRoot" } -Name "build backend"

Divider "推送后端镜像 $BACKEND_IMAGE"
Invoke-Retry { docker push "$BACKEND_IMAGE" } -Name "push backend"

# 前端可选 API 基址（仅当设置时传入）
$FrontendApiArgs = @()
if ($env:VITE_API_BASE) { $FrontendApiArgs += @("--build-arg", "VITE_API_BASE=$env:VITE_API_BASE") }

# ---------------- 前端（HTTPS版） ----------------
Divider "构建前端镜像 $WEB_IMAGE"
Invoke-Retry { docker build `
  --pull `
  $FrontendBuildCacheArgs `
  --file "$ProjectRoot/deploy/Dockerfile.web" `
  --tag  "$WEB_IMAGE" `
  $BuildArgs `
  $FrontendApiArgs `
  "$ProjectRoot" } -Name "build web"

Divider "推送前端镜像 $WEB_IMAGE"
Invoke-Retry { docker push "$WEB_IMAGE" } -Name "push web"


Divider "镜像推送完成"
Write-Host "部署提示："
Write-Host "  BACKEND_IMAGE=$BACKEND_IMAGE"
Write-Host "  WEB_IMAGE=$WEB_IMAGE"
Write-Host ""
Write-Host "若先前构建被污染，首次请执行： `$env:NO_CACHE='1'; .\ww.ps1"
