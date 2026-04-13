#!/bin/bash
# BobQuant 统一导航页启动脚本

echo "============================================================"
echo "🚀 BobQuant 导航页启动中..."
echo "============================================================"
echo ""
echo "📊 访问地址:"
echo "   导航页：http://localhost:8502"
echo ""
echo "🔗 链接到:"
echo "   - Streamlit 看板：http://localhost:8501"
echo "   - Plotly Dash 看板：http://localhost:8050"
echo ""
echo "============================================================"

cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant/web

# 启动简单的 HTTP 服务器
python3 -m http.server 8502
