import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="BobQuant 超激进模拟盘", layout="wide")
st.title("🚀 BobQuant 超激进高频模拟盘")
st.write(f"**更新时间**: {datetime.now()}")

# 超激进配置信息
st.subheader("⚡ 配置信息")
config = {
    "版本": "v2.5.0-ultra-aggressive",
    "检查间隔": "2 秒",
    "做 T 阈值": "0.05%",
    "最大交易": "10 笔/分钟",
    "股票池": "30 只龙头股",
    "初始资金": "¥1,000,000"
}
col1, col2, col3 = st.columns(3)
for i, (k, v) in enumerate(config.items()):
    if i % 3 == 0:
        col1.metric(k, v)
    elif i % 3 == 1:
        col2.metric(k, v)
    else:
        col3.metric(k, v)

# 进程状态
st.subheader("🟢 运行状态")
import subprocess
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
ultra_process = [line for line in result.stdout.split('\n') if 'ultra_aggressive' in line and 'grep' not in line]
if ultra_process:
    st.success("✅ 超激进模拟盘运行中")
    st.code(ultra_process[0])
else:
    st.error("❌ 超激进模拟盘未运行")

# 账户信息
st.subheader("💰 账户信息")
account_file = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json'
if os.path.exists(account_file):
    with open(account_file, 'r') as f:
        account = json.load(f)
    col1, col2, col3 = st.columns(3)
    col1.metric("总资产", f"¥{account.get('total', 0):,}")
    col2.metric("现金", f"¥{account.get('cash', 0):,}")
    col3.metric("持仓", f"¥{account.get('positions_value', 0):,}")
    st.write(f"**持仓数量**: {len(account.get('positions', {}))} 只")
else:
    st.warning("⚠️ 账户文件不存在")

# 日志
st.subheader("📝 最新日志")
log_file = '/home/openclaw/.openclaw/workspace/quant_strategies/logs/bobquant_20260414.log'
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
    # 显示最后 20 行
    recent = [l for l in lines[-30:] if 'INFO' in l or 'ERROR' in l or 'WARNING' in l]
    st.code(''.join(recent[-15:]), language='text')
else:
    st.warning("⚠️ 日志文件不存在")

st.divider()
st.caption("访问地址：http://112.9.38.62:8501 | 服务器：david")
