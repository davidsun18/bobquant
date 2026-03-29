#!/usr/bin/env python3
"""
中频交易策略回测 - 简化快速版
"""

import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import baostock as bs

# 配置
YEARS = [2023, 2024, 2025]
INITIAL_CAPITAL = 1000000

# 测试股票 (3 只代表性)
TEST_STOCKS = [
    ('sh.603986', '兆易创新'),
    ('sz.300750', '宁德时代'),
    ('sz.002415', '海康威视'),
]

def get_data(code, year):
    """获取年度数据"""
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code, 
        "date,open,high,low,close,volume",
        start_date=f"{year}-01-01",
        end_date=f"{year}-12-31",
        frequency="d"
    )
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    if len(data) < 60:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col])
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    return df

def backtest(df, code, name):
    """简化回测"""
    if len(df) < 60:
        return None
    
    # 计算 RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain/loss))
    
    # 简化策略：RSI<35 买入，RSI>65 卖出
    cash = INITIAL_CAPITAL
    pos = 0
    in_pos = False
    buy_price = 0
    trades = []
    values = []
    
    for i in range(30, len(df)):
        close = df['close'].iloc[i]
        rsi = df['rsi'].iloc[i]
        
        # 止损止盈
        if in_pos:
            pnl = (close - buy_price) / buy_price
            if pnl <= -0.03:  # -3% 止损
                profit = (close - buy_price) * pos
                cash += pos * close * 0.999
                trades.append({'type': '止损', 'profit': profit})
                pos = 0
                in_pos = False
            elif pnl >= 0.08:  # +8% 止盈
                profit = (close - buy_price) * pos
                cash += pos * close * 0.999
                trades.append({'type': '止盈', 'profit': profit})
                pos = 0
                in_pos = False
        
        # 买卖信号
        if not in_pos and rsi < 35:
            shares = int(cash * 0.1 / close / 100) * 100
            if shares >= 100:
                cash -= shares * close * 1.001
                pos = shares
                in_pos = True
                buy_price = close
                trades.append({'type': '买入', 'rsi': rsi})
        
        elif in_pos and rsi > 65:
            profit = (close - buy_price) * pos
            cash += pos * close * 0.999
            trades.append({'type': '卖出', 'profit': profit, 'rsi': rsi})
            pos = 0
            in_pos = False
        
        values.append(cash + pos * close if in_pos else cash)
    
    # 平仓
    if in_pos:
        cash += pos * df['close'].iloc[-1] * 0.999
    
    # 统计
    total_return = (cash - INITIAL_CAPITAL) / INITIAL_CAPITAL
    sell_trades = [t for t in trades if t.get('profit') is not None]
    wins = [t for t in sell_trades if t['profit'] > 0]
    win_rate = len(wins) / len(sell_trades) if sell_trades else 0
    
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 else 0
    
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    return {
        'code': code,
        'name': name,
        'year': df.index[0].year,
        'return': total_return,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'trades': len(trades)
    }

def main():
    print("="*60)
    print("中频交易策略回测 (2023-2025) - 简化版")
    print("="*60)
    
    all_results = []
    
    for year in YEARS:
        print(f"\n【{year}年】")
        
        for code, name in TEST_STOCKS:
            print(f"\n{code} {name}...", end=' ')
            
            df = get_data(code, year)
            if df is None:
                print("数据不足")
                continue
            
            result = backtest(df, code, name)
            if result:
                all_results.append(result)
                print(f"收益{result['return']*100:+.1f}%, 胜率{result['win_rate']*100:.0f}%")
            else:
                print("回测失败")
        
        # 年度汇总
        year_results = [r for r in all_results if r['year'] == year]
        if year_results:
            avg_return = np.mean([r['return'] for r in year_results])
            print(f"\n{year}年平均收益：{avg_return*100:+.1f}%")
    
    # 总汇总
    print("\n" + "="*60)
    print("回测汇总")
    print("="*60)
    
    for year in YEARS:
        year_results = [r for r in all_results if r['year'] == year]
        if year_results:
            avg_return = np.mean([r['return'] for r in year_results])
            avg_win = np.mean([r['win_rate'] for r in year_results])
            print(f"{year}年：平均{avg_return*100:+.1f}%, 胜率{avg_win*100:.0f}%")
    
    # 保存
    output_dir = Path('backtest_results')
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / 'mf_backtest_quick.json', 'w') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 结果已保存：backtest_results/mf_backtest_quick.json")

if __name__ == '__main__':
    main()
