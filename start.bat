@echo off
title 论文搜搜 - Starting...

set BACKEND=%~dp0backend

echo ============================================
echo   论文搜搜 - 启动中...
echo ============================================
echo.

REM Try conda env p first, then fall back to system python
set PYTHON=python
if exist "%USERPROFILE%\.conda\envs\p\python.exe" (
    set PYTHON=%USERPROFILE%\.conda\envs\p\python.exe
)
if exist "C:\Users\lenovo\.conda\envs\p\python.exe" (
    set PYTHON=C:\Users\lenovo\.conda\envs\p\python.exe
)

echo Starting server (port 8001)...
start "paperfind" /MIN cmd /c "cd /d "%BACKEND%" && "%PYTHON%" run.py"

timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   启动完成！
echo   浏览器访问: http://localhost:8001
echo ============================================
echo.
echo 关闭此窗口 - 服务继续运行。
echo 双击 stop.bat 停止服务。
echo.
pause
