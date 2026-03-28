#!/bin/bash
# ==========================================
# 量化模拟盘 - 一键启动脚本
# ==========================================
# 用法：./start_all.sh
# ==========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "🚀 量化模拟盘启动脚本"
echo "=========================================="
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查是否已运行
check_process() {
    local name=$1
    local pattern=$2
    local pid=$(ps aux | grep "$pattern" | grep -v grep | awk '{print $2}')
    if [ -n "$pid" ]; then
        echo "✅ $name 已运行 (PID: $pid)"
        return 0
    else
        echo "⏸️ $name 未运行"
        return 1
    fi
}

# 启动进程
start_process() {
    local name=$1
    local cmd=$2
    local log_file=$3
    
    echo "🔄 启动 $name..."
    cd "$SCRIPT_DIR"
    nohup $cmd > "$log_file" 2>&1 &
    sleep 2
    
    if pgrep -f "$2" > /dev/null; then
        echo "✅ $name 启动成功 (PID: $(pgrep -f "$2" | head -1))"
        return 0
    else
        echo "❌ $name 启动失败"
        return 1
    fi
}

echo "📊 检查进程状态..."
echo ""

# 1. 检查并启动 Web UI
if ! check_process "Web UI" "web_ui.py"; then
    start_process "Web UI" "python3 web_ui.py" "$LOG_DIR/web_ui.log"
fi

# 2. 检查并启动 Streamlit (如果有)
STREAMLIT_APP="$SCRIPT_DIR/bobquant_v2/web/app.py"
if [ -f "$STREAMLIT_APP" ]; then
    if ! check_process "Streamlit" "streamlit_app\|streamlit run"; then
        start_process "Streamlit" "streamlit run $STREAMLIT_APP --server.port 8501 --server.address 0.0.0.0" "$LOG_DIR/streamlit.log"
    fi
else
    echo "⚠️  Streamlit 应用不存在，跳过"
fi

# 3. 检查并启动 BobQuant 主进程
if ! check_process "BobQuant" "bobquant/main.py"; then
    start_process "BobQuant" "python3 bobquant/main.py --config bobquant/config/sim_config_v2_2.yaml --mode simulation" "$LOG_DIR/bobquant.log"
fi

# 4. 检查并启动 V2 策略进程 (如果有)
if [ -f "$SCRIPT_DIR/bobquant_v2/run_v2_strategy.py" ]; then
    if ! check_process "V2 策略" "run_v2_strategy"; then
        start_process "V2 策略" "python3 bobquant_v2/run_v2_strategy.py" "$LOG_DIR/v2_strategy.log"
    fi
fi

echo ""
echo "=========================================="
echo "✅ 所有服务启动完成"
echo "=========================================="
echo ""

# 显示访问地址
echo "🌐 访问地址:"
echo "   Web UI: http://localhost:5000"
echo "   本机 IP: http://$(hostname -I | awk '{print $1}'):5000"
echo ""

# 显示进程状态
echo "📋 进程状态:"
ps aux | grep -E "web_ui|bobquant|streamlit" | grep -v grep | awk '{print "   PID: "$2" - "$11" "$12}'
echo ""

# 显示日志查看命令
echo "📝 查看日志:"
echo "   tail -f $LOG_DIR/web_ui.log"
echo "   tail -f $LOG_DIR/bobquant.log"
echo ""

echo "⏹️  停止服务："
echo "   ./stop_all.sh"
echo ""
