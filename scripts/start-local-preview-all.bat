@echo off
setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

start "HomeAIHub Box Preview" cmd /k "%REPO_ROOT%\scripts\start-local-preview-box.bat"
start "HomeAIHub Gateway Preview" cmd /k "%REPO_ROOT%\scripts\start-local-preview-gateway.bat"

echo.
echo HomeAIHub local preview is starting.
echo Mobile:    http://127.0.0.1:8080/mobile
echo Dashboard: http://127.0.0.1:8080/dashboard
echo Box API:   http://127.0.0.1:8090/health
echo.
pause
