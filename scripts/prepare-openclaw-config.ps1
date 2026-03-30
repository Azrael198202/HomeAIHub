$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$templatePath = Join-Path $repoRoot "gateway\openclaw_gateway\config\openclaw.template.json5"
$outputPath = Join-Path $repoRoot "gateway\openclaw_gateway\config\openclaw.local.json5"

$template = Get-Content -LiteralPath $templatePath -Raw
$normalizedRoot = $repoRoot.Replace("\", "/")
$content = $template.Replace("__PROJECT_ROOT__", $normalizedRoot)

Set-Content -LiteralPath $outputPath -Value $content -Encoding UTF8
Write-Host "Generated OpenClaw config:"
Write-Host $outputPath
