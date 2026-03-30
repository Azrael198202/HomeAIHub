$ErrorActionPreference = "Stop"

Write-Host "Installing OpenClaw via official Windows PowerShell installer..."
Write-Host "Official command: iwr -useb https://openclaw.ai/install.ps1 | iex"

& ([scriptblock]::Create((iwr -useb https://openclaw.ai/install.ps1)))
