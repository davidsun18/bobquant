#!/bin/bash
# BobQuant 模拟盘启动脚本 v2.2（30 只龙头股）

echo "============================================================"
echo "🚀 BobQuant 模拟盘 v2.2 启动中..."
echo "============================================================"
echo ""

# 进入项目目录
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant

# 检查 Python 环境
echo "📋 检查环境..."
python3 --version
echo ""

# 检查配置文件
echo "📄 检查配置文件..."
if [ -f "config/sim_config_v2_2.yaml" ]; then
    echo "✅ 配置文件：config/sim_config_v2_2.yaml"
else
    echo "❌ 配置文件不存在！"
    exit 1
fi

# 检查股票池
echo "📊 检查股票池..."
if [ -f "config/stock_pool_30_top.yaml" ]; then
    echo "✅ 股票池：config/stock_pool_30_top.yaml (30 只龙头股)"
else
    echo "❌ 股票池不存在！"
    exit 1
fi

# 检查日志目录
echo "📁 检查日志目录..."
mkdir -p logs/sim_trading
echo "✅ 日志目录：logs/sim_trading"
echo ""

# 显示配置摘要
echo "============================================================"
echo "📋 模拟盘配置摘要"
echo "============================================================"
echo "  版本：v2.2 (30 只龙头股精选池)"
echo "  初始资金：1,000,000 元"
echo "  单票仓位：≤10%"
echo "  最大持仓：≤10 只"
echo "  股票池：30 只龙头股"
echo "  基本面筛选：ROE≥12%、PE≤30、市值≥200 亿"
echo "  策略：双 MACD + 布林带"
echo "  止损：-8%"
echo "  止盈：5%/10%/15% 分批"
echo "  大盘风控：启用"
echo "============================================================"
echo ""

# 启动模拟盘主程序
echo "🚀 启动模拟盘主程序..."
echo ""

python3 -m bobquant.main --config config/sim_config_v2_2.yaml --mode simulation

# 如果主程序退出，检查退出码
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 模拟盘正常退出"
else
    echo ""
    echo "⚠️  模拟盘异常退出，检查日志：logs/sim_trading/"
fi

echo ""
echo "============================================================"
