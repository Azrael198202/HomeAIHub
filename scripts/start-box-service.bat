@echo off
setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

if "%~1"=="" (
  set "BOX_ENV=develop"
) else (
  set "BOX_ENV=%~1"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\scripts\start-box-service.ps1" -Environment %BOX_ENV%
