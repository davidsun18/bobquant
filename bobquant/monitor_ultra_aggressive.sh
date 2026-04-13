#!/bin/bash
# ==========================================
# BobQuant 超激进模拟盘状态监控
# ==========================================

cd /home/openclaw/.openclaw/workspace/quant_strategies

echo "=========================================="
echo "📊 BobQuant 超激进模拟盘 v2.5 状态监控"
echo "=========================================="
echo ""

# 检查进程
echo "🔍 进程状态:"
PROC=$(ps aux | grep "ultra_aggressive" | grep -v grep)
if [ -n "$PROC" ]; then
    echo "$PROC"
    PID=$(echo "$PROC" | awk '{print $2}')
    echo ""
    
    # CPU/内存
    CPU=$(echo "$PROC" | awk '{print $3}')
    MEM=$(echo "$PROC" | awk '{print $4}')
    echo "  CPU: ${CPU}%"
    echo "  内存：${MEM}%"
    echo ""
    
    # 运行时间
    UPTIME=$(ps -p $PID -o etime= | xargs)
    echo "  运行时间：$UPTIME"
else
    echo "  🔴 未运行"
    echo ""
    echo "💡 启动命令:"
    echo "  ./bobquant/start_ultra_aggressive.sh"
fi

echo ""
echo "=========================================="
echo "📝 最新日志 (最后 20 行):"
echo "=========================================="
LOG_FILE=$(ls -t logs/sim_trading_ultra_aggressive/*.log 2>/dev/null | head -1)
if [ -n "$LOG_FILE" ]; then
    echo "日志文件：$LOG_FILE"
    echo ""
    tail -20 "$LOG_FILE" | grep -v "^$"
else
    echo "暂无日志文件"
fi

echo ""
echo "=========================================="
echo "📈 今日交易日志:"
echo "=========================================="
TODAY=$(date +%Y%m%d)
TRADE_LOG=$(ls -t logs/sim_trading_ultra_aggressive/*${TODAY}*.log 2>/dev/null | head -1)
if [ -n "$TRADE_LOG" ]; then
    echo "今日交易数：$(grep -c "trade_executed\|买入\|卖出" "$TRADE_LOG" 2>/dev/null || echo 0)"
    echo "止损次数：$(grep -c "stop_loss\|止损" "$TRADE_LOG" 2>/dev/null || echo 0)"
    echo "止盈次数：$(grep -c "take_profit\|止盈" "$TRADE_LOG" 2>/dev/null || echo 0)"
else
    echo "暂无今日交易记录"
fi

echo ""
echo "=========================================="
