# -*- coding: utf-8 -*-
"""
配对交易简化版 - 统计套利入门
"""

import pandas as pd
import numpy as np
import baostock as bs
from statsmodels.tsa.stattools import coint, adfuller
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("🎓 配对交易策略教程 - 简化版")
print("="*70)

# 1. 获取数据
def get_data(code):
    lg = bs.login()
    rs = bs.query_history_k_data_plus(code, "date,close", start_date='2023-01-01', end_date='2023-12-31', frequency="d")
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    df = pd.DataFrame(data, columns=rs.fields)
    df['close'] = df['close'].astype(float)
    bs.logout()
    return df

# 2. 测试银行股配对
print("\n📊 测试银行股配对：工商银行 vs 建设银行")

stock1 = get_data('sh.601398')  # 工商银行
stock2 = get_data('sh.601939')  # 建设银行

# 合并数据
merged = pd.merge(stock1, stock2, on='date', suffixes=('_1', '_2'))
print(f"✅ 数据长度：{len(merged)} 天")

# 3. 协整检验
print("\n🔍 协整检验...")
p_value, _, _ = coint(merged['close_1'], merged['close_2'])
print(f"p 值：{p_value:.4f}")
print(f"协整关系：{'✅ 存在 (p<0.05)' if p_value < 0.05 else '❌ 不存在'}")

# 4. 计算对冲比率
X = merged['close_1'].values.reshape(-1, 1)
y = merged['close_2'].values
model = LinearRegression()
model.fit(X, y)
hedge_ratio = model.coef_[0]
print(f"对冲比率：{hedge_ratio:.4f}")

# 5. 计算价差
merged['spread'] = merged['close_2'] - hedge_ratio * merged['close_1']
merged['spread_mean'] = merged['spread'].rolling(20).mean()
merged['spread_std'] = merged['spread'].rolling(20).std()
merged['zscore'] = (merged['spread'] - merged['spread_mean']) / merged['spread_std']

# 6. 生成信号
merged['signal'] = 0
merged['position'] = 0
in_pos = False

for i in range(1, len(merged)):
    z = merged['zscore'].iloc[i]
    if not in_pos:
        if z > 2:  # 价差过高，做空价差
            merged.loc[merged.index[i], 'signal'] = -1
            in_pos = True
        elif z < -2:  # 价差过低，做多价差
            merged.loc[merged.index[i], 'signal'] = 1
            in_pos = True
    else:
        if abs(z) < 0.5:  # 回归平仓
            merged.loc[merged.index[i], 'signal'] = 0
            in_pos = False
    merged.loc[merged.index[i], 'position'] = 1 if in_pos else 0

trades = merged[merged['signal'] != 0]
print(f"\n📈 交易次数：{len(trades)}")

# 7. 简单收益估算
if len(trades) > 0:
    avg_trade_return = merged['spread_std'].mean() * 0.5  # 简化估算
    est_return = len(trades) / 2 * avg_trade_return / merged['close_1'].mean() * 100
    print(f"📊 估算收益：{est_return:.2f}%")

print("\n" + "="*70)
print("📚 配对交易核心逻辑")
print("="*70)
print("""
1. 找到两只协整的股票（长期走势相关）
2. 计算对冲比率（确定配比）
3. 监控价差（股票 2 - 比率×股票 1）
4. 价差>2σ：做空价差（空 2 多 1）
5. 价差<-2σ：做多价差（多 2 空 1）
6. 价差回归：平仓获利

优势：
✅ 市场中性（不依赖大盘涨跌）
✅ 双向对冲（风险较低）
✅ 稳定收益（赚取价差回归）

风险：
⚠️ 协整关系可能破裂
⚠️ 需要融券做空（A 股限制）
⚠️ 交易成本较高
""")

print("\n💡 建议：先用这个逻辑做模拟盘，熟悉后再实盘！")
