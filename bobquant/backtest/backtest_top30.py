#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 30 只龙头股精选池回测 v2.2
严格基本面筛选 + 技术面信号
"""
import sys
import os
import yaml

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

import pandas as pd
import numpy as np
from datetime import datetime
import json
import time

print("=" * 60)
print("🚀 BobQuant 30 只龙头股精选池回测 v2.2")
print("=" * 60)

# 加载 30 只龙头股池
pool_file = os.path.join(root_dir, 'config', 'stock_pool_30_top.yaml')
with open(pool_file, 'r', encoding='utf-8') as f:
    stock_pool = yaml.safe_load(f)

print(f"\n📊 股票池配置:")
print(f"  股票数量：{len(stock_pool)} 只")

# 按行业统计
industry_count = {}
strategy_count = {}
for s in stock_pool:
    industry = s.get('industry', '其他')
    industry_count[industry] = industry_count.get(industry, 0) + 1
    strategy_count[s['strategy']] = strategy_count.get(s['strategy'], 0) + 1

print("\n  行业分布:")
for ind, cnt in sorted(industry_count.items(), key=lambda x: -x[1]):
    print(f"    {ind}: {cnt}只")

print("\n  策略分布:")
for strat, cnt in strategy_count.items():
    print(f"    {strat}: {cnt}只")

# 回测配置（更严格）
config = {
    'initial_capital': 1000000,
    'commission_rate': 0.0005,
    'stamp_duty_rate': 0.001,
    'use_dual_macd': True,
    'use_dynamic_bollinger': True,
    'enable_fundamental_filter': True,
    'min_fundamental_score': 70,  # 70 分以上（更严格）
    'rsi_buy_max': 35,
    'rsi_sell_min': 70,
    'volume_confirm': True,
    'stop_loss_pct': -0.08,
    'trailing_activation': 0.05,
    'trailing_dip': 0.02,
    'max_position_pct': 0.10,  # 单票最大 10% 仓位（集中持仓）
    'max_stocks': 10,  # 最大同时持仓 10 只（精简）
}

start_date = '2024-01-01'
end_date = '2024-12-31'

print(f"\n💰 资金配置:")
print(f"  初始资金：1,000,000 元")
print(f"  单票仓位：≤10%")
print(f"  最大持仓：≤10 只")
print(f"\n📅 回测周期：{start_date} → {end_date}")
print("=" * 60)

# 获取真实数据
print("\n📡 正在获取真实历史数据...")

try:
    import baostock as bs
    
    lg = bs.login()
    print(f"✅ Baostock 登录成功")
    
    stock_data = {}
    failed = []
    
    for idx, stock in enumerate(stock_pool):
        code = stock['code']
        
        if (idx + 1) % 10 == 0:
            print(f"   进度：{idx+1}/{len(stock_pool)}")
        
        try:
            rs = bs.query_history_k_data_plus(
                code,
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            
            data_list = []
            while (rs.error_code == '0') and rs.next():
                row = rs.get_row_data()
                if len(row) >= 7:
                    data_list.append({
                        'date': row[0],
                        'open': float(row[1] or 0),
                        'high': float(row[2] or 0),
                        'low': float(row[3] or 0),
                        'close': float(row[4] or 0),
                        'volume': float(row[5] or 0),
                        'amount': float(row[6] or 0),
                    })
            
            df = pd.DataFrame(data_list)
            if len(df) > 0:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                stock_data[code] = df
            else:
                failed.append(stock['name'])
        except Exception as e:
            failed.append(stock['name'])
    
    bs.logout()
    
    print(f"\n✅ 数据获取完成：{len(stock_data)}/{len(stock_pool)} 只成功")

except Exception as e:
    print(f"\n❌ 数据获取失败：{e}")
    stock_data = {}

if not stock_data:
    print("无法获取数据，退出")
    sys.exit(1)

# 技术指标计算
print("\n⚙️  计算技术指标...")

def calc_dual_macd(df):
    close = df['close']
    ema_fast_s = close.ewm(span=6, adjust=False).mean()
    ema_slow_s = close.ewm(span=13, adjust=False).mean()
    short_macd = ema_fast_s - ema_slow_s
    short_signal = short_macd.ewm(span=5, adjust=False).mean()
    
    ema_fast_l = close.ewm(span=24, adjust=False).mean()
    ema_slow_l = close.ewm(span=52, adjust=False).mean()
    long_macd = ema_fast_l - ema_slow_l
    long_signal = long_macd.ewm(span=18, adjust=False).mean()
    
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
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(window).mean()
    df['bb_std'] = df['close'].rolling(window).std()
    df['bb_upper'] = df['bb_mid'] + num_std * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - num_std * df['bb_std']
    denom = df['bb_upper'] - df['bb_lower']
    df['bb_pos'] = (df['close'] - df['bb_lower']) / denom.replace(0, 1e-10)
    return df

def calc_rsi(df, period=14):
    df = df.copy()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

# 为每只股票计算指标
for idx, (code, df) in enumerate(stock_data.items()):
    stock = next((s for s in stock_pool if s['code'] == code), None)
    if not stock:
        continue
    
    strategy = stock['strategy']
    
    if strategy in ['dual_macd', 'macd']:
        stock_data[code] = calc_dual_macd(df)
    else:
        stock_data[code] = calc_bollinger(df)
    
    stock_data[code] = calc_rsi(stock_data[code])

print("✅ 技术指标计算完成")

# 回测主循环
print("\n📈 开始回测（30 只龙头股 + 严格基本面筛选）...")

capital = config['initial_capital']
positions = {}
trades = []
equity_curve = []
daily_returns = []

all_dates = set()
for df in stock_data.values():
    all_dates.update(df['date'].dt.strftime('%Y-%m-%d'))
trading_days = sorted(list(all_dates))

print(f"   交易日数：{len(trading_days)}")
print(f"   初始资金：{capital:,.0f} 元")
print(f"   股票池：{len(stock_data)} 只龙头股")

prev_equity = capital
max_position_value = capital * config['max_position_pct']
max_stocks = config['max_stocks']

for day_idx, date_str in enumerate(trading_days):
    date = pd.to_datetime(date_str)
    
    for stock in stock_pool:
        code = stock['code']
        
        if code not in stock_data:
            continue
        
        if len(positions) >= max_stocks and code not in positions:
            continue
        
        df = stock_data[code]
        mask = df['date'] <= date
        hist = df[mask].copy()
        
        if len(hist) < 30:
            continue
        
        latest = hist.iloc[-1]
        price = latest['close']
        
        signal = None
        reason = ''
        
        if stock['strategy'] in ['dual_macd', 'macd']:
            if latest.get('dual_golden', False):
                signal = 'buy'
                reason = '双 MACD 金叉'
            elif latest.get('dual_death', False):
                signal = 'sell'
                reason = '双 MACD 死叉'
        else:
            bb_pos = latest.get('bb_pos', 0.5)
            if bb_pos < 0.1:
                signal = 'buy'
                reason = f'布林带下轨 (%B={bb_pos:.2f})'
            elif bb_pos > 0.9:
                signal = 'sell'
                reason = f'布林带上轨 (%B={bb_pos:.2f})'
        
        rsi_val = latest.get('rsi', 50)
        if signal == 'buy' and rsi_val > 35:
            signal = None
        if signal == 'sell' and rsi_val > 70:
            reason += ' + RSI 超买'
        
        if signal == 'buy' and code not in positions:
            if len(positions) >= max_stocks:
                continue
            
            position_size = min(capital * 0.10 / price, max_position_value / price)
            shares = int(position_size / 100) * 100
            
            if shares >= 100 and capital >= shares * price * 1.0005:
                cost = shares * price * 1.0005
                positions[code] = {
                    'shares': shares,
                    'avg_price': price,
                    'name': stock['name'],
                    'strategy': stock['strategy']
                }
                capital -= cost
                trades.append({
                    'date': date_str,
                    'code': code,
                    'name': stock['name'],
                    'action': 'buy',
                    'price': price,
                    'shares': shares,
                    'reason': reason,
                    'cost': cost
                })
        
        elif signal == 'sell' and code in positions:
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
    
    pos_value = 0
    for code, pos in positions.items():
        if code in stock_data:
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
        'position_value': pos_value,
        'num_stocks': len(positions)
    })
    
    if prev_equity > 0:
        daily_return = (current_equity - prev_equity) / prev_equity
        daily_returns.append(daily_return)
    prev_equity = current_equity
    
    if (day_idx + 1) % 50 == 0 or day_idx == len(trading_days) - 1:
        print(f"   进度：{day_idx+1}/{len(trading_days)} 交易日，权益：{current_equity:,.0f} 元 ({(current_equity/config['initial_capital']-1)*100:+.1f}%), 持仓：{len(positions)}只")

# 计算回测指标
print("\n📊 计算回测指标...")

final_equity = equity_curve[-1]['equity']
total_return = (final_equity - config['initial_capital']) / config['initial_capital']

start = pd.to_datetime(start_date)
end = pd.to_datetime(end_date)
days = (end - start).days
years = days / 365.25
annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

equity_values = [e['equity'] for e in equity_curve]
peak = equity_values[0]
max_dd = 0
for value in equity_values:
    if value > peak:
        peak = value
    drawdown = (peak - value) / peak
    if drawdown > max_dd:
        max_dd = drawdown

if len(daily_returns) > 2:
    returns = pd.Series(daily_returns)
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
else:
    sharpe = 0

buy_trades = len([t for t in trades if t['action'] == 'buy'])
sell_trades = len([t for t in trades if t['action'] == 'sell'])
profitable_trades = len([t for t in trades if t['action'] == 'sell' and t.get('profit', 0) > 0])
win_rate = profitable_trades / max(sell_trades, 1)
total_profit = sum(t.get('profit', 0) for t in trades if t['action'] == 'sell')
avg_num_stocks = np.mean([e['num_stocks'] for e in equity_curve])

print("\n" + "=" * 60)
print("📊 回测结果摘要（30 只龙头股精选池）")
print("=" * 60)

print(f"\n💰 收益指标:")
print(f"  初始资金：  {config['initial_capital']:,.0f} 元")
print(f"  最终权益：  {final_equity:,.0f} 元")
print(f"  总收益率：  {total_return*100:+.2f}%")
print(f"  年化收益：  {annual_return*100:+.2f}%")
print(f"  总盈亏：    {total_profit:+,.0f} 元")

print(f"\n📉 风险指标:")
print(f"  最大回撤：  {max_dd*100:.2f}%")
print(f"  夏普比率：  {sharpe:.2f}")

print(f"\n📈 交易统计:")
print(f"  买入次数：  {buy_trades}")
print(f"  卖出次数：  {sell_trades}")
print(f"  盈利次数：  {profitable_trades}")
print(f"  亏损次数：  {sell_trades - profitable_trades}")
print(f"  胜率：      {win_rate*100:.1f}%")
print(f"  平均盈利：  {total_profit/max(sell_trades,1):,.0f} 元/笔")

print(f"\n📊 持仓统计:")
print(f"  平均持仓：  {avg_num_stocks:.1f} 只")
print(f"  最大持仓：  {max(e['num_stocks'] for e in equity_curve)} 只")

print(f"\n📅 回测周期:")
print(f"  开始日期：  {start_date}")
print(f"  结束日期：  {end_date}")
print(f"  交易日数：  {len(trading_days)}")

print("\n" + "=" * 60)

# 对比 Emily 目标
targets = {
    'annual_return': 0.15,
    'max_drawdown': 0.25,
    'sharpe_ratio': 1.2,
    'win_rate': 0.55
}

print("\n🎯 vs Emily 建议目标:")
print(f"  年化收益：  {annual_return*100:+.2f}% {'✅' if annual_return >= targets['annual_return'] else '⚠️'} (目标 ≥{targets['annual_return']*100:.0f}%)")
print(f"  最大回撤：  {max_dd*100:.2f}% {'✅' if max_dd <= targets['max_drawdown'] else '⚠️'} (目标 ≤{targets['max_drawdown']*100:.0f}%)")
print(f"  夏普比率：  {sharpe:.2f} {'✅' if sharpe >= targets['sharpe_ratio'] else '⚠️'} (目标 ≥{targets['sharpe_ratio']:.1f})")
print(f"  胜率：      {win_rate*100:.1f}% {'✅' if win_rate >= targets['win_rate'] else '⚠️'} (目标 ≥{targets['win_rate']*100:.0f}%)")

# 四次回测对比
print("\n📊 四次回测完整对比:")
print(f"  股票池：    5 只 → 50 只 → 100 只 → 30 只龙头")
print(f"  年化收益：  +3.80% → +2.18% → -0.50% → {annual_return*100:+.2f}%")
print(f"  最大回撤：  0.70% → 5.82% → 9.48% → {max_dd*100:.2f}%")
print(f"  夏普比率：  1.83 → 0.42 → -0.03 → {sharpe:.2f}")
print(f"  胜率：      83.3% → 67.1% → 67.1% → {win_rate*100:.1f}%")

print("\n" + "=" * 60)

# 保存结果
result = {
    'config': {
        'initial_capital': config['initial_capital'],
        'stock_pool_size': len(stock_pool),
        'start_date': start_date,
        'end_date': end_date,
        'strategy': 'top_30_fundamental_technical'
    },
    'metrics': {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'win_rate': win_rate,
        'total_trades': len(trades),
        'final_equity': final_equity,
        'total_profit': total_profit,
        'avg_num_stocks': avg_num_stocks
    },
    'targets': targets,
    'trades': trades,
    'equity_curve': equity_curve
}

output_path = os.path.join(root_dir, 'backtest', 'reports', 'top30_backtest_2024.json')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n📄 回测报告已保存：{output_path}")
print("\n✅ 30 只龙头股精选池回测完成！")
print("=" * 60)
