#!/bin/bash
# BobQuant v1.0 快速启动脚本

echo "⚡ BobQuant v1.0 启动中..."
echo ""

cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant

# 检查依赖
echo "🔧 检查依赖..."
python3 -c "import pandas, numpy, sklearn, tensorflow" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少依赖，请运行：pip3 install pandas numpy scikit-learn tensorflow"
    exit 1
fi
echo "✅ 依赖检查通过"

# 显示配置
echo ""
echo "📋 配置信息:"
python3 -c "
from config import get_settings
s = get_settings()
print(f'  模式：模拟盘')
print(f'  初始资金：¥{s.initial_capital:,}')
print(f'  股票池：{len(s.stock_pool)} 只')
print(f'  ML 预测：{s.get(\"ml.enabled\", True)}')
print(f'  情绪指数：{s.get(\"sentiment.enabled\", True)}')
"

# 启动
echo ""
echo "🚀 启动交易引擎..."
echo "按 Ctrl+C 停止"
echo ""

python3 -m bobquant.main
