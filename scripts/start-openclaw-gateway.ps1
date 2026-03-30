$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prepareScript = Join-Path $repoRoot "scripts\prepare-openclaw-config.ps1"
& $prepareScript

$configPath = Join-Path $repoRoot "gateway\openclaw_gateway\config\openclaw.local.json5"

if (-not (Get-Command openclaw -ErrorAction SilentlyContinue)) {
  Write-Error "openclaw CLI not found. Install OpenClaw first, then rerun this script."
}

$env:OPENCLAW_CONFIG = $configPath
Write-Host "Starting OpenClaw Gateway with config:"
Write-Host $configPath
openclaw gateway
