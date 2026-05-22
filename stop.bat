@echo off
echo ============================================
echo   论文搜搜 - 停止服务
echo ============================================

echo Stopping server...
taskkill /FI "WINDOWTITLE eq paperfind*" /F 2>nul

echo.
echo 服务已停止。
timeout /t 3 /nobreak >nul
