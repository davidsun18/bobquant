#!/bin/bash
# BobQuant Streamlit 启动脚本

echo "============================================================"
echo "🚀 BobQuant Streamlit 可视化看板启动中..."
echo "============================================================"
echo ""
echo "📊 访问地址:"
echo "   本地访问：http://localhost:8501"
echo "   局域网访问：http://<本机 IP>:8501"
echo ""
echo "📄 功能列表:"
echo "   ✅ 账户概览 - 总资产、资金曲线、持仓明细"
echo "   ✅ 持仓分析 - 持仓占比、盈亏分布、K 线图"
echo "   ✅ 交易记录 - 历史交易、筛选统计"
echo "   ✅ 绩效分析 - 关键指标、月度收益"
echo "   ✅ 设置页面 - 配置信息、缓存管理"
echo ""
echo "============================================================"

cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant

# 启动 Streamlit
streamlit run web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
