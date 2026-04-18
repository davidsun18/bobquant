#!/bin/bash
# BobQuant Dashboard 启动脚本

set -e

WORKSPACE="/home/openclaw/.openclaw/workspace"
LOG_DIR="${WORKSPACE}/logs"

echo "======================================"
echo "  BobQuant Dashboard 启动"
echo "======================================"
echo ""

# 确保日志目录存在
mkdir -p "${LOG_DIR}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到 Python3"
    exit 1
fi

echo "Python 版本：$(python3 --version)"
echo ""

# 检查依赖
echo "检查依赖..."
python3 -c "import fastapi" 2>/dev/null && echo "  ✓ FastAPI" || echo "  ✗ FastAPI (未安装)"
python3 -c "import uvicorn" 2>/dev/null && echo "  ✓ Uvicorn" || echo "  ✗ Uvicorn (未安装)"
python3 -c "import pandas" 2>/dev/null && echo "  ✓ Pandas" || echo "  ✗ Pandas (未安装)"
echo ""

# 启动 Dashboard
echo "启动 Dashboard..."
echo "  API: http://localhost:8500"
echo "  Dashboard: http://localhost:8500/dashboard"
echo "  WebSocket: ws://localhost:8500/ws"
echo ""

cd "${WORKSPACE}/dashboard"
exec python3 main.py
