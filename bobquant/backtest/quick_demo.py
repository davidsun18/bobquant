#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 回测快速演示 - 独立版本（无外部依赖）
"""
import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 60)
print("🚀 BobQuant 回测系统 v2.0 - 快速演示")
print("=" * 60)

# 生成模拟数据
np.random.seed(42)
start_date = '2024-01-01'
end_date = '2024-12-31'
dates = pd.date_range(start_date, end_date, freq='B')
n = len(dates)

print(f"\n📊 回测配置:")
print(f"  初始资金：1,000,000 元")
print(f"  股票池：5 只股票（工商银行、贵州茅台、工业富联、比亚迪、恒瑞医药）")
print(f"  时间段：{start_date} → {end_date}")
print(f"  交易日：{n} 天")
print(f"  策略：双 MACD + 布林带混合")

# 生成 5 只股票的模拟价格
stocks = {
    '工商银行': {'base': 5, 'vol': 0.015},
    '贵州茅台': {'base': 1700, 'vol': 0.02},
    '工业富联': {'base': 20, 'vol': 0.025},
    '比亚迪': {'base': 200, 'vol': 0.03},
    '恒瑞医药': {'base': 80, 'vol': 0.022}
}

data = {}
for name, config in stocks.items():
    trend = np.linspace(0, 0.15, n)  # 15% 年化趋势
    noise = np.cumsum(np.random.randn(n) * config['vol'])
    close = config['base'] * (1 + trend + noise)
    data[name] = pd.DataFrame({
        'date': dates,
        'close': close,
        'volume': np.random.randint(1000000, 10000000, n)
    })

print("\n⚙️  正在运行回测...")

# 简化回测逻辑
capital = 1000000
positions = {}
trades = []
equity_curve = []
daily_returns = []

def calc_dual_macd(df):
    """简化版双 MACD 计算"""
    close = df['close']
    
    # 短周期 MACD (6,13,5)
    ema_fast = close.ewm(span=6, adjust=False).mean()
    ema_slow = close.ewm(span=13, adjust=False).mean()
    short_macd = ema_fast - ema_slow
    short_signal = short_macd.ewm(span=5, adjust=False).mean()
    
    # 长周期 MACD (24,52,18)
    ema_fast_l = close.ewm(span=24, adjust=False).mean()
    ema_slow_l = close.ewm(span=52, adjust=False).mean()
    long_macd = ema_fast_l - ema_slow_l
    long_signal = long_macd.ewm(span=18, adjust=False).mean()
    
    # 双确认信号
    dual_golden = (short_macd > short_signal) & (long_macd > long_signal) & \
                  (short_macd.shift(1) <= short_signal.shift(1)) & \
                  (long_macd.shift(1) <= long_signal.shift(1))
    
    dual_death = (short_macd < short_signal) & (long_macd < long_signal) & \
                 (short_macd.shift(1) >= short_signal.shift(1)) & \
                 (long_macd.shift(1) >= long_signal.shift(1))
    
    return dual_golden, dual_death

prev_equity = capital

for i, date in enumerate(dates):
    if i < 30:  # 跳过前 30 天（数据不足）
        continue
    
    # 检查每只股票
    for name, df in data.items():
        hist = df.iloc[:i+1].copy()
        
        dual_golden, dual_death = calc_dual_macd(hist)
        
        latest_golden = dual_golden.iloc[-1]
        latest_death = dual_death.iloc[-1]
        
        price = df.iloc[i]['close']
        
        # 买入信号
        if latest_golden and name not in positions:
            position_size = capital * 0.15 / price  # 15% 仓位
            shares = int(position_size / 100) * 100
            if shares >= 100 and capital >= shares * price * 1.0005:
                cost = shares * price * 1.0005
                positions[name] = {'shares': shares, 'avg_price': price}
                capital -= cost
                trades.append({'date': date, 'stock': name, 'action': 'buy', 'price': price, 'shares': shares})
        
        # 卖出信号
        elif latest_death and name in positions:
            pos = positions[name]
            revenue = pos['shares'] * price * 0.999
            profit = revenue - pos['shares'] * pos['avg_price']
            capital += revenue
            trades.append({'date': date, 'stock': name, 'action': 'sell', 'price': price, 'shares': pos['shares'], 'profit': profit})
            del positions[name]
    
    # 计算权益
    pos_value = sum(
        pos['shares'] * data[name].iloc[i]['close']
        for name, pos in positions.items()
    )
    current_equity = capital + pos_value
    equity_curve.append({'date': date, 'equity': current_equity})
    
    # 日收益率
    if prev_equity > 0:
        daily_returns.append((current_equity - prev_equity) / prev_equity)
    prev_equity = current_equity
    
    # 进度
    if (i + 1) % 50 == 0:
        print(f"   进度：{i+1}/{n} 交易日，权益：{current_equity:,.0f} ({(current_equity/1000000-1)*100:+.1f}%)")

# 计算指标
final_equity = equity_curve[-1]['equity']
total_return = (final_equity - 1000000) / 1000000

days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
years = days / 365.25
annual_return = (1 + total_return) ** (1 / years) - 1

# 最大回撤
peak = equity_curve[0]['equity']
max_dd = 0
for e in equity_curve:
    if e['equity'] > peak:
        peak = e['equity']
    dd = (peak - e['equity']) / peak
    if dd > max_dd:
        max_dd = dd

# 夏普比率
if len(daily_returns) > 2:
    ret = pd.Series(daily_returns)
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
else:
    sharpe = 0

# 胜率
sell_trades = [t for t in trades if t['action'] == 'sell']
win_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
win_rate = len(win_trades) / max(len(sell_trades), 1)

# 打印结果
print("\n" + "=" * 60)
print("📊 回测结果摘要")
print("=" * 60)

print(f"\n💰 收益指标:")
print(f"  初始资金：  1,000,000 元")
print(f"  最终权益：  {final_equity:,.0f} 元")
print(f"  总收益率：  {total_return*100:+.2f}%")
print(f"  年化收益：  {annual_return*100:+.2f}%")

print(f"\n📉 风险指标:")
print(f"  最大回撤：  {max_dd*100:.2f}%")
print(f"  夏普比率：  {sharpe:.2f}")

print(f"\n📈 交易统计:")
print(f"  总交易次数：{len(trades)}")
print(f"  买入次数：  {len([t for t in trades if t['action'] == 'buy'])}")
print(f"  卖出次数：  {len(sell_trades)}")
print(f"  盈利次数：  {len(win_trades)}")
print(f"  胜率：      {win_rate*100:.1f}%")

print("\n" + "=" * 60)
print("🎯 vs Emily 建议目标:")
targets = {'annual_return': 0.15, 'max_drawdown': 0.25, 'sharpe_ratio': 1.2, 'win_rate': 0.55}

print(f"  年化收益：  {annual_return*100:+.2f}% {'✅' if annual_return >= targets['annual_return'] else '⚠️'} (目标 ≥{targets['annual_return']*100:.0f}%)")
print(f"  最大回撤：  {max_dd*100:.2f}% {'✅' if max_dd <= targets['max_drawdown'] else '⚠️'} (目标 ≤{targets['max_drawdown']*100:.0f}%)")
print(f"  夏普比率：  {sharpe:.2f} {'✅' if sharpe >= targets['sharpe_ratio'] else '⚠️'} (目标 ≥{targets['sharpe_ratio']:.1f})")
print(f"  胜率：      {win_rate*100:.1f}% {'✅' if win_rate >= targets['win_rate'] else '⚠️'} (目标 ≥{targets['win_rate']*100:.0f}%)")

print("\n" + "=" * 60)
print("✅ 回测演示完成！")
print("=" * 60)
