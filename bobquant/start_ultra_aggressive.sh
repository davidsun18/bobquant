#!/bin/bash
# ==========================================
# BobQuant 超激进高频模拟盘启动脚本
# ==========================================

cd /home/openclaw/.openclaw/workspace/quant_strategies

echo "🚀 启动 BobQuant 超激进高频模拟盘 v2.5..."
echo "⚠️  警告：此配置极其激进，仅用于模拟盘！"
echo ""

# 停止旧进程
echo "🛑 停止旧进程..."
pkill -9 -f "sim_config_v2_5_ultra_aggressive" 2>/dev/null
sleep 1

# 创建日志目录
mkdir -p logs/sim_trading_ultra_aggressive

# 启动
LOG_FILE="logs/sim_trading_ultra_aggressive/ultra_$(date +%Y%m%d_%H%M%S).log"
echo "📝 日志文件：$LOG_FILE"
echo ""

nohup python3 -m bobquant.main \
  --config bobquant/config/sim_config_v2_5_ultra_aggressive.yaml \
  --mode simulation \
  > "$LOG_FILE" 2>&1 &

PID=$!
echo "✅ 进程已启动 (PID: $PID)"
echo ""

# 等待 3 秒检查状态
sleep 3
if ps -p $PID > /dev/null 2>&1; then
    echo "🟢 运行状态：正常"
    echo ""
    echo "📊 查看实时日志:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "🛑 停止命令:"
    echo "  pkill -f 'sim_config_v2_5_ultra_aggressive'"
else
    echo "🔴 启动失败，请检查日志"
    tail -20 "$LOG_FILE"
fi
