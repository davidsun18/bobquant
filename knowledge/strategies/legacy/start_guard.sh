#!/bin/bash
# BobQuant 模拟盘开机自启脚本 v2.2.12

LOG_DIR="/home/openclaw/.openclaw/workspace/quant_strategies/bobquant/logs/sim_trading"
MAIN_PY="/home/openclaw/.openclaw/workspace/quant_strategies/bobquant/main.py"
CONFIG="/home/openclaw/.openclaw/workspace/quant_strategies/bobquant/config/sim_config_v2_2.yaml"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 检查是否已经在运行
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "$(date): 模拟盘已在运行" >> "$LOG_DIR/guard.log"
    exit 0
fi

# 启动模拟盘
echo "$(date): 启动 BobQuant 模拟盘 v2.2.12" >> "$LOG_DIR/guard.log"
nohup python3 "$MAIN_PY" --config "$CONFIG" --mode simulation >> "$LOG_DIR/sim_$(date +\%Y\%m\%d).log" 2>&1 &
echo "$(date): 模拟盘已启动 (PID: $!)" >> "$LOG_DIR/guard.log"
