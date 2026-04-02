$ErrorActionPreference = "Stop"

param(
    [ValidateSet("develop", "stage", "prod")]
    [string]$Environment = "develop"
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repoRoot "box\env\.env.$Environment"

if (-not (Test-Path $envFile)) {
    throw "Environment file not found: $envFile"
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }
    $parts = $line -split "=", 2
    if ($parts.Length -eq 2) {
        [System.Environment]::SetEnvironmentVariable($parts[0], $parts[1], "Process")
    }
}

Set-Location $repoRoot
Write-Host "Starting box with environment: $Environment"
Write-Host "Loaded env file: $envFile"
python -m box
