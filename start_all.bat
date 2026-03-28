@echo off
chcp 65001 >nul
echo ========================================
echo BobQuant 量化系统 - Windows 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10
    echo 下载地址：https://www.python.org/downloads/release/python-31011/
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show pandas >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
) else (
    echo 依赖已安装
)

echo.
echo [2/3] 启动 Web UI...
start http://localhost:5000
python web_ui.py

echo.
echo [3/3] Web UI 已关闭
pause
