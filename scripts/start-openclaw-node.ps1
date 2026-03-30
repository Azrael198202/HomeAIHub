param(
  [string]$GatewayHost = "127.0.0.1",
  [int]$GatewayPort = 18789,
  [string]$DisplayName = "HomeAIHub Mini Host",
  [switch]$Tls,
  [string]$GatewayToken = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command openclaw -ErrorAction SilentlyContinue)) {
  Write-Error "openclaw CLI not found. Install OpenClaw first, then rerun this script."
}

if ($GatewayToken) {
  $env:OPENCLAW_GATEWAY_TOKEN = $GatewayToken
}

Write-Host "Starting OpenClaw node:"
Write-Host "host=$GatewayHost port=$GatewayPort display=$DisplayName tls=$Tls"

$command = @(
  "node", "run",
  "--host", $GatewayHost,
  "--port", "$GatewayPort",
  "--display-name", $DisplayName
)

if ($Tls) {
  $command += "--tls"
}

& openclaw @command
