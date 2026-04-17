#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 回测演示脚本 v2.0
使用模拟数据演示回测效果（无需真实数据源）
"""
import sys
import os
import json

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest.engine import BacktestEngine

print("=" * 60)
print("🚀 BobQuant 回测系统 v2.0 - 演示模式")
print("=" * 60)

# 配置
config = {
    'initial_capital': 1000000,
    'commission_rate': 0.0005,
    'stamp_duty_rate': 0.001,
    'use_dual_macd': True,
    'rsi_buy_max': 35,
    'rsi_sell_min': 70,
    'volume_confirm': True,
    'stop_loss_pct': -0.08,
}

# 简化股票池（演示用）
stock_pool = [
    {'code': 'sh.601398', 'name': '工商银行', 'strategy': 'bollinger'},
    {'code': 'sh.600519', 'name': '贵州茅台', 'strategy': 'bollinger'},
    {'code': 'sh.601138', 'name': '工业富联', 'strategy': 'dual_macd'},
    {'code': 'sz.002594', 'name': '比亚迪', 'strategy': 'dual_macd'},
    {'code': 'sh.600276', 'name': '恒瑞医药', 'strategy': 'dual_macd'},
]

start_date = '2024-01-01'
end_date = '2024-12-31'

print(f"\n📊 回测配置:")
print(f"  初始资金：1,000,000 元")
print(f"  股票池：{len(stock_pool)} 只股票")
print(f"  时间段：{start_date} → {end_date}")
print(f"  策略：双 MACD + 布林带混合")
print("\n" + "=" * 60)

# 创建回测引擎
engine = BacktestEngine(config)

# 生成模拟数据进行回测
print("\n⚙️  正在生成模拟数据并运行回测...")

# 为每只股票生成模拟行情
np.random.seed(42)  # 固定随机种子保证可重复性

def generate_mock_data(start_date, end_date, base_price=100, volatility=0.02):
    """生成模拟 K 线数据"""
    dates = pd.date_range(start_date, end_date, freq='B')  # 工作日
    n = len(dates)
    
    # 生成价格序列（随机游走 + 趋势）
    trend = np.linspace(0, 0.2, n)  # 20% 年化趋势
    noise = np.cumsum(np.random.randn(n) * volatility)
    close = base_price * (1 + trend + noise)
    
    # 生成 OHLCV
    open_price = close * (1 + np.random.randn(n) * 0.005)
    high = np.maximum(open_price, close) * (1 + np.abs(np.random.randn(n) * 0.01))
    low = np.minimum(open_price, close) * (1 - np.abs(np.random.randn(n) * 0.01))
    volume = np.random.randint(1000000, 10000000, n)
    
    df = pd.DataFrame({
        'time': dates.strftime('%Y-%m-%d'),
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    
    return df

# 为每只股票生成数据
mock_data = {}
for i, stock in enumerate(stock_pool):
    base_price = 50 + i * 30  # 不同股票不同基准价
    mock_data[stock['code']] = generate_mock_data(start_date, end_date, base_price)

print(f"✅ 数据生成完成：{len(mock_data)} 只股票")

# 模拟回测过程（简化版）
print("\n📈 回测进行中...")

trades = []
equity_curve = []
capital = config['initial_capital']
positions = {}

# 逐日回测
trading_days = pd.date_range(start_date, end_date, freq='B')
print(f"   交易日数：{len(trading_days)}")

prev_equity = capital
daily_returns = []

for day_idx, date in enumerate(trading_days):
    date_str = date.strftime('%Y-%m-%d')
    
    # 检查每只股票的信号
    for stock in stock_pool:
        code = stock['code']
        df = mock_data[code]
        
        # 获取截至当日的历史数据
        mask = df['time'] <= date_str
        hist_df = df[mask].copy()
        
        if len(hist_df) < 30:
            continue
        
        # 计算技术指标
        from indicator import technical as ta
        hist_df = ta.dual_macd(hist_df)
        hist_df = ta.rsi(hist_df)
        
        latest = hist_df.iloc[-1]
        prev = hist_df.iloc[-2]
        
        # 检查双 MACD 信号
        signal = None
        if latest.get('dual_golden', False):
            signal = 'buy'
        elif latest.get('dual_death', False):
            signal = 'sell'
        
        # 执行交易（简化）
        if signal == 'buy' and code not in positions:
            # 买入
            price = latest['close']
            position_size = capital * 0.1 / price  # 10% 仓位
            shares = int(position_size / 100) * 100
            if shares >= 100 and capital >= shares * price * 1.0005:
                positions[code] = {'shares': shares, 'avg_price': price}
                capital -= shares * price * 1.0005
                trades.append({
                    'date': date_str,
                    'code': code,
                    'action': 'buy',
                    'price': price,
                    'shares': shares
                })
        
        elif signal == 'sell' and code in positions:
            # 卖出
            pos = positions[code]
            price = latest['close']
            revenue = pos['shares'] * price * 0.999
            capital += revenue
            profit = revenue - pos['shares'] * pos['avg_price']
            trades.append({
                'date': date_str,
                'code': code,
                'action': 'sell',
                'price': price,
                'shares': pos['shares'],
                'profit': profit
            })
            del positions[code]
    
    # 计算当日权益
    position_value = sum(
        pos['shares'] * mock_data[code][mock_data[code]['time'] <= date_str].iloc[-1]['close']
        for code, pos in positions.items()
        if len(mock_data[code][mock_data[code]['time'] <= date_str]) > 0
    )
    current_equity = capital + position_value
    equity_curve.append({
        'date': date_str,
        'equity': current_equity,
        'cash': capital,
        'position_value': position_value
    })
    
    # 计算日收益率
    if prev_equity > 0:
        daily_return = (current_equity - prev_equity) / prev_equity
        daily_returns.append(daily_return)
    prev_equity = current_equity
    
    # 进度显示
    if (day_idx + 1) % 50 == 0 or day_idx == len(trading_days) - 1:
        print(f"   进度：{day_idx+1}/{len(trading_days)} 交易日，权益：{current_equity:,.0f} ({(current_equity/capital-1)*100:+.1f}%)")

# 计算回测指标
print("\n📊 计算回测指标...")

final_equity = equity_curve[-1]['equity']
total_return = (final_equity - config['initial_capital']) / config['initial_capital']

# 年化收益率
start = pd.to_datetime(start_date)
end = pd.to_datetime(end_date)
days = (end - start).days
years = days / 365.25
annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

# 最大回撤
equity_values = [e['equity'] for e in equity_curve]
peak = equity_values[0]
max_dd = 0
for value in equity_values:
    if value > peak:
        peak = value
    drawdown = (peak - value) / peak
    if drawdown > max_dd:
        max_dd = drawdown

# 夏普比率
if len(daily_returns) > 2:
    returns = pd.Series(daily_returns)
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
else:
    sharpe = 0

# 交易统计
buy_trades = len([t for t in trades if t['action'] == 'buy'])
sell_trades = len([t for t in trades if t['action'] == 'sell'])
profitable_trades = len([t for t in trades if t['action'] == 'sell' and t.get('profit', 0) > 0])
win_rate = profitable_trades / max(sell_trades, 1)

# 打印结果
print("\n" + "=" * 60)
print("📊 回测结果摘要")
print("=" * 60)

print(f"\n💰 收益指标:")
print(f"  初始资金：  {config['initial_capital']:,.0f} 元")
print(f"  最终权益：  {final_equity:,.0f} 元")
print(f"  总收益率：  {total_return*100:+.2f}%")
print(f"  年化收益：  {annual_return*100:+.2f}%")

print(f"\n📉 风险指标:")
print(f"  最大回撤：  {max_dd*100:.2f}%")
print(f"  夏普比率：  {sharpe:.2f}")

print(f"\n📈 交易统计:")
print(f"  买入次数：  {buy_trades}")
print(f"  卖出次数：  {sell_trades}")
print(f"  盈利次数：  {profitable_trades}")
print(f"  胜率：      {win_rate*100:.1f}%")

print(f"\n📅 回测周期:")
print(f"  开始日期：  {start_date}")
print(f"  结束日期：  {end_date}")
print(f"  交易日数：  {len(trading_days)}")

print("\n" + "=" * 60)

# 对比 Emily 建议的目标
print("\n🎯 vs Emily 建议目标:")
targets = {
    'annual_return': 0.15,
    'max_drawdown': 0.25,
    'sharpe_ratio': 1.2,
    'win_rate': 0.55
}

print(f"  年化收益：  {annual_return*100:+.2f}% {'✅' if annual_return >= targets['annual_return'] else '⚠️'} (目标 ≥{targets['annual_return']*100:.0f}%)")
print(f"  最大回撤：  {max_dd*100:.2f}% {'✅' if max_dd <= targets['max_drawdown'] else '⚠️'} (目标 ≤{targets['max_drawdown']*100:.0f}%)")
print(f"  夏普比率：  {sharpe:.2f} {'✅' if sharpe >= targets['sharpe_ratio'] else '⚠️'} (目标 ≥{targets['sharpe_ratio']:.1f})")
print(f"  胜率：      {win_rate*100:.1f}% {'✅' if win_rate >= targets['win_rate'] else '⚠️'} (目标 ≥{targets['win_rate']*100:.0f}%)")

print("\n" + "=" * 60)

# 保存结果
result = {
    'config': {
        'initial_capital': config['initial_capital'],
        'stock_pool_size': len(stock_pool),
        'start_date': start_date,
        'end_date': end_date,
        'strategy': 'dual_macd + bollinger'
    },
    'metrics': {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'win_rate': win_rate,
        'total_trades': len(trades),
        'final_equity': final_equity
    },
    'targets': targets
}

output_path = os.path.join(root_dir, 'backtest', 'reports', 'demo_backtest_result.json')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n📄 回测报告已保存：{output_path}")
print("\n✅ 回测演示完成！")
print("=" * 60)
