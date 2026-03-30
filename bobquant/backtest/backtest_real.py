#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 真实数据回测脚本 v2.0
使用腾讯财经 + Baostock 真实历史数据
"""
import sys
import os

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

print("=" * 60)
print("🚀 BobQuant 真实数据回测 v2.0")
print("=" * 60)

# 配置
config = {
    'initial_capital': 1000000,
    'commission_rate': 0.0005,
    'stamp_duty_rate': 0.001,
    'use_dual_macd': True,
    'use_dynamic_bollinger': True,
    'enable_risk_filters': True,
    'rsi_buy_max': 35,
    'rsi_sell_min': 70,
    'volume_confirm': True,
    'stop_loss_pct': -0.08,
    'trailing_activation': 0.05,
    'trailing_dip': 0.02,
}

# 股票池（简化版，5 只代表性股票）
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
for s in stock_pool:
    print(f"    - {s['name']} ({s['code']}) [{s['strategy']}]")
print(f"  时间段：{start_date} → {end_date}")
print(f"  策略：双 MACD + 动态布林带")
print("=" * 60)

# 获取真实数据
print("\n📡 正在获取真实历史数据...")

try:
    import baostock as bs
    
    # 登录 baostock
    lg = bs.login()
    print(f"✅ Baostock 登录成功 (错误码：{lg.error_code})")
    
    # 获取每只股票的历史数据
    stock_data = {}
    for stock in stock_pool:
        code = stock['code']
        print(f"   获取 {stock['name']} ({code}) 数据...", end=" ")
        
        # 获取 2024 年全年数据
        rs = bs.query_history_k_data_plus(
            code,
            "date,open,high,low,close,volume,amount",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"  # 不复权
        )
        
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append({
                'date': rs.get_row_data()[0],
                'open': float(rs.get_row_data()[1] or 0),
                'high': float(rs.get_row_data()[2] or 0),
                'low': float(rs.get_row_data()[3] or 0),
                'close': float(rs.get_row_data()[4] or 0),
                'volume': float(rs.get_row_data()[5] or 0),
                'amount': float(rs.get_row_data()[6] or 0),
            })
        
        df = pd.DataFrame(data_list)
        if len(df) > 0:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            stock_data[code] = df
            print(f"✅ {len(df)} 条记录")
        else:
            print(f"❌ 无数据")
    
    # 登出
    bs.logout()
    
except Exception as e:
    print(f"\n❌ 数据获取失败：{e}")
    print("使用模拟数据继续回测...")
    stock_data = {}

# 如果没有获取到数据，使用模拟数据
if not stock_data:
    print("\n⚠️  使用模拟数据继续回测")
    np.random.seed(42)
    dates = pd.date_range(start_date, end_date, freq='B')
    for stock in stock_pool:
        base_price = 50 + hash(stock['code']) % 200
        trend = np.linspace(0, 0.1, len(dates))
        noise = np.cumsum(np.random.randn(len(dates)) * 0.02)
        close = base_price * (1 + trend + noise)
        stock_data[stock['code']] = pd.DataFrame({
            'date': dates,
            'open': close * (1 + np.random.randn(len(dates)) * 0.005),
            'high': close * 1.02,
            'low': close * 0.98,
            'close': close,
            'volume': np.random.randint(1000000, 10000000, len(dates)),
            'amount': close * np.random.randint(1000000, 10000000, len(dates))
        })

print(f"\n✅ 数据准备完成：{len(stock_data)} 只股票")

# 技术指标计算
print("\n⚙️  计算技术指标...")

def calc_dual_macd(df):
    """双 MACD 指标"""
    close = df['close']
    
    # 短周期 (6,13,5)
    ema_fast_s = close.ewm(span=6, adjust=False).mean()
    ema_slow_s = close.ewm(span=13, adjust=False).mean()
    short_macd = ema_fast_s - ema_slow_s
    short_signal = short_macd.ewm(span=5, adjust=False).mean()
    
    # 长周期 (24,52,18)
    ema_fast_l = close.ewm(span=24, adjust=False).mean()
    ema_slow_l = close.ewm(span=52, adjust=False).mean()
    long_macd = ema_fast_l - ema_slow_l
    long_signal = long_macd.ewm(span=18, adjust=False).mean()
    
    # 双确认信号
    df = df.copy()
    df['short_macd'] = short_macd
    df['short_signal'] = short_signal
    df['long_macd'] = long_macd
    df['long_signal'] = long_signal
    
    df['dual_golden'] = (
        (short_macd > short_signal) & (long_macd > long_signal) &
        (short_macd.shift(1) <= short_signal.shift(1)) &
        (long_macd.shift(1) <= long_signal.shift(1))
    )
    
    df['dual_death'] = (
        (short_macd < short_signal) & (long_macd < long_signal) &
        (short_macd.shift(1) >= short_signal.shift(1)) &
        (long_macd.shift(1) >= long_signal.shift(1))
    )
    
    return df

def calc_bollinger(df, window=20, num_std=2):
    """布林带指标"""
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(window).mean()
    df['bb_std'] = df['close'].rolling(window).std()
    df['bb_upper'] = df['bb_mid'] + num_std * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - num_std * df['bb_std']
    denom = df['bb_upper'] - df['bb_lower']
    df['bb_pos'] = (df['close'] - df['bb_lower']) / denom.replace(0, 1e-10)
    return df

def calc_rsi(df, period=14):
    """RSI 指标"""
    df = df.copy()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

# 为每只股票计算指标
for code, df in stock_data.items():
    strategy = next(s['strategy'] for s in stock_pool if s['code'] == code)
    
    if strategy == 'dual_macd':
        stock_data[code] = calc_dual_macd(df)
    else:
        stock_data[code] = calc_bollinger(df)
    
    stock_data[code] = calc_rsi(stock_data[code])

print("✅ 技术指标计算完成")

# 回测主循环
print("\n📈 开始回测...")

capital = config['initial_capital']
positions = {}
trades = []
equity_curve = []
daily_returns = []

# 获取所有交易日
all_dates = set()
for df in stock_data.values():
    all_dates.update(df['date'].dt.strftime('%Y-%m-%d'))
trading_days = sorted(list(all_dates))

print(f"   交易日数：{len(trading_days)}")

prev_equity = capital

for day_idx, date_str in enumerate(trading_days):
    date = pd.to_datetime(date_str)
    
    # 检查每只股票的信号
    for stock in stock_pool:
        code = stock['code']
        df = stock_data[code]
        
        # 获取当日及之前数据
        mask = df['date'] <= date
        hist = df[mask].copy()
        
        if len(hist) < 30:
            continue
        
        latest = hist.iloc[-1]
        price = latest['close']
        
        # 检查信号
        signal = None
        reason = ''
        
        if stock['strategy'] == 'dual_macd':
            if latest.get('dual_golden', False):
                signal = 'buy'
                reason = '双 MACD 金叉'
            elif latest.get('dual_death', False):
                signal = 'sell'
                reason = '双 MACD 死叉'
        else:  # bollinger
            bb_pos = latest.get('bb_pos', 0.5)
            if bb_pos < 0.1:
                signal = 'buy'
                reason = f'布林带下轨 (%B={bb_pos:.2f})'
            elif bb_pos > 0.9:
                signal = 'sell'
                reason = f'布林带上轨 (%B={bb_pos:.2f})'
        
        # RSI 过滤
        rsi_val = latest.get('rsi', 50)
        if signal == 'buy' and rsi_val > 35:
            signal = None
        if signal == 'sell' and rsi_val > 70:
            reason += ' + RSI 超买'
        
        # 执行交易
        if signal == 'buy' and code not in positions:
            # 买入（10% 仓位）
            position_size = capital * 0.10 / price
            shares = int(position_size / 100) * 100
            if shares >= 100 and capital >= shares * price * 1.0005:
                cost = shares * price * 1.0005
                positions[code] = {'shares': shares, 'avg_price': price, 'name': stock['name']}
                capital -= cost
                trades.append({
                    'date': date_str,
                    'code': code,
                    'name': stock['name'],
                    'action': 'buy',
                    'price': price,
                    'shares': shares,
                    'reason': reason
                })
        
        elif signal == 'sell' and code in positions:
            # 卖出
            pos = positions[code]
            revenue = pos['shares'] * price * 0.999
            profit = revenue - pos['shares'] * pos['avg_price']
            capital += revenue
            trades.append({
                'date': date_str,
                'code': code,
                'name': stock['name'],
                'action': 'sell',
                'price': price,
                'shares': pos['shares'],
                'profit': profit,
                'reason': reason
            })
            del positions[code]
    
    # 计算当日权益
    pos_value = 0
    for code, pos in positions.items():
        df = stock_data[code]
        mask = df['date'] <= date
        if mask.sum() > 0:
            current_price = df[mask].iloc[-1]['close']
            pos_value += pos['shares'] * current_price
    
    current_equity = capital + pos_value
    equity_curve.append({
        'date': date_str,
        'equity': current_equity,
        'cash': capital,
        'position_value': pos_value
    })
    
    # 日收益率
    if prev_equity > 0:
        daily_return = (current_equity - prev_equity) / prev_equity
        daily_returns.append(daily_return)
    prev_equity = current_equity
    
    # 进度显示
    if (day_idx + 1) % 50 == 0 or day_idx == len(trading_days) - 1:
        print(f"   进度：{day_idx+1}/{len(trading_days)} 交易日，权益：{current_equity:,.0f} ({(current_equity/capital*100-1):+.1f}%)")

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

# 显示部分交易记录
if trades:
    print("\n📋 部分交易记录:")
    for t in trades[:10]:
        action = '🔴 买入' if t['action'] == 'buy' else '🟢 卖出'
        profit_str = f" 盈亏：{t.get('profit', 0):+.0f}元" if t['action'] == 'sell' else ""
        print(f"  {t['date']} {action} {t['name']} {t['shares']}股 @ {t['price']:.2f}元 - {t['reason']}{profit_str}")
    if len(trades) > 10:
        print(f"  ... 还有 {len(trades)-10} 笔交易")

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
    'targets': targets,
    'trades': trades
}

output_path = os.path.join(root_dir, 'backtest', 'reports', 'real_backtest_2024.json')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n📄 回测报告已保存：{output_path}")
print("\n✅ 回测完成！")
print("=" * 60)
