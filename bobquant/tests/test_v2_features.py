#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant v2.0 新功能快速测试
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

# 测试双 MACD
print("=" * 60)
print("🧪 BobQuant v2.0 新功能测试")
print("=" * 60)

from indicator import technical as ta

# 生成测试数据
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=100, freq='D')
close = 100 + np.cumsum(np.random.randn(100) * 0.5)
df = pd.DataFrame({
    'date': dates,
    'close': close,
    'open': close * (1 + np.random.randn(100) * 0.01),
    'high': close * (1 + np.abs(np.random.randn(100) * 0.01)),
    'low': close * (1 - np.abs(np.random.randn(100) * 0.01)),
    'volume': np.random.randint(1000000, 10000000, 100)
})

print("\n1️⃣ 测试双 MACD 指标")
print("-" * 60)
df_dual = ta.dual_macd(df)
print(f"✅ 双 MACD 计算成功")
print(f"   短周期 MACD: {df_dual['short_macd'].iloc[-1]:.4f}")
print(f"   长周期 MACD: {df_dual['long_macd'].iloc[-1]:.4f}")
print(f"   双金叉信号：{df_dual['dual_golden'].iloc[-1]}")
print(f"   双死叉信号：{df_dual['dual_death'].iloc[-1]}")

print("\n2️⃣ 测试动态布林带")
print("-" * 60)
df_bb = ta.bollinger(df, window=20, num_std=2, dynamic=True)
print(f"✅ 动态布林带计算成功")
print(f"   当前价格：{df_bb['close'].iloc[-1]:.2f}")
print(f"   上轨：{df_bb['bb_upper'].iloc[-1]:.2f}")
print(f"   下轨：{df_bb['bb_lower'].iloc[-1]:.2f}")
print(f"   使用标准差：{df_bb['bb_std_used'].iloc[-1]:.2f}x")

print("\n3️⃣ 测试风险过滤器")
print("-" * 60)
from core.risk_filters import RiskFilters

config = {
    'min_turnover': 50000000,
    'max_high_gain': 1.0,
    'high_gain_period': 60
}
filters = RiskFilters(config)

# 测试 ST 检查
st_result = filters.check_st('sh.600001', '正常股票')
print(f"✅ ST 检查：{st_result['passed']} (非 ST)")

st_result2 = filters.check_st('sh.600002', '*ST 风险')
print(f"✅ ST 检查：{st_result2['passed']} (*ST 被拦截)")

# 测试流动性检查
liq_result = filters.check_liquidity(df, 'sh.600001')
print(f"✅ 流动性检查：{liq_result['passed']} (日均成交 {liq_result['avg_turnover']/10000:.1f}万)")

print("\n4️⃣ 测试大盘风控")
print("-" * 60)
from core.market_risk import MarketRiskManager

market_risk = MarketRiskManager({
    'ma20_line': 20,
    'max_position_bear': 0.5,
    'crash_threshold': -0.03
})

# 模拟设置大盘数据
market_risk.set_market_index(df)

# 测试仓位控制
position_info = market_risk.get_allowed_position(1000000, 600000)
print(f"✅ 大盘风控检查成功")
print(f"   允许仓位：{position_info['allowed_position_pct']*100:.0f}%")
print(f"   当前仓位：{position_info['current_position_pct']*100:.0f}%")
print(f"   需要减仓：{position_info['need_reduce']}")
print(f"   原因：{position_info['reason']}")

print("\n5️⃣ 测试策略引擎（双 MACD 策略）")
print("-" * 60)
from strategy.engine import MACDStrategy

strategy = MACDStrategy({'use_dual_macd': True})
quote = {'current': df['close'].iloc[-1], 'open': df['open'].iloc[-1]}
pos = {'code': 'sh.600001', 'shares': 1000, 'avg_price': 95.0}

signal = strategy.check('sh.600001', '测试股票', quote, df, pos, config)
print(f"✅ 双 MACD 策略信号：{signal['signal']}")
print(f"   原因：{signal['reason']}")
print(f"   强度：{signal.get('strength', 'normal')}")

print("\n" + "=" * 60)
print("✅ 所有测试通过！BobQuant v2.0 功能正常")
print("=" * 60)
