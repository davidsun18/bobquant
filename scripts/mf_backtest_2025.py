#!/usr/bin/env python3
"""
中频交易策略回测 - 2025 年单独回测 (超级优化版)

详细记录每笔交易，生成详细报告
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
YEAR = 2025
INITIAL_CAPITAL = 1000000

# 股票池 (12 只)
STOCK_POOL = [
    ('sh.603986', '兆易创新', '半导体'),
    ('sz.002371', '北方华创', '半导体'),
    ('sh.603501', '韦尔股份', '半导体'),
    ('sh.688981', '中芯国际', '半导体'),
    ('sz.002156', '通富微电', '半导体'),
    ('sz.002415', '海康威视', '科技'),
    ('sh.601138', '工业富联', '科技'),
    ('sh.600584', '长电科技', '科技'),
    ('sz.002185', '华天科技', '科技'),
    ('sz.300750', '宁德时代', '新能源'),
    ('sh.601012', '隆基绿能', '新能源'),
    ('sz.300014', '亿纬锂能', '新能源'),
]

# 策略参数
STRATEGY = {
    'rsi_buy': 20,
    'rsi_sell': 80,
    'rsi_period': 14,
    'take_profit_levels': [
        {'threshold': 0.15, 'sell_ratio': 0.50},
        {'threshold': 0.30, 'sell_ratio': 1.00},
    ],
    'trailing_stop': {
        'activation': 0.15,
        'drawdown': 0.08
    },
    'stop_loss': -0.20,
    'position_base': 0.15,
    'position_max': 0.30,
    'volatility_low': 30,
    'volatility_high': 60,
    'add_position_levels': [-0.05, -0.10, -0.15],
    'add_position_ratios': [0.05, 0.03, 0.02],
    'max_position_pct': 0.30,
    'grid_base': 0.025,
    'grid_volatility_factor': 0.03,
    'ma_period': 20,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'volume_ratio': 1.5,
    'index_code': 'sh.000001',
    'crash_threshold': -0.05,
    'crash_position': 0.30,
    'commission': 0.0003,
    'stamp_duty': 0.001,
}


def get_data(code, year):
    """获取年度数据"""
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code, 
        "date,open,high,low,close,volume,amount",
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
    
    df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
        df[col] = pd.to_numeric(df[col])
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    return df


def get_index_data(year):
    """获取大盘数据"""
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        'sh.000001',
        "date,close",
        start_date=f"{year}-01-01",
        end_date=f"{year}-12-31",
        frequency="d"
    )
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    if not data:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'close'])
    df['close'] = pd.to_numeric(df['close'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    return df


def calculate_indicators(df):
    """计算技术指标"""
    df = df.copy()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    exp1 = df['close'].ewm(span=STRATEGY['macd_fast'], adjust=False).mean()
    exp2 = df['close'].ewm(span=STRATEGY['macd_slow'], adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal_line'] = df['macd'].ewm(span=STRATEGY['macd_signal'], adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal_line']
    
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    df['volatility'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252) * 100
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    df['grid_base'] = df['close'].rolling(window=20).mean()
    
    return df


def backtest_2025(df, index_df, code, name):
    """2025 年回测"""
    if len(df) < 60:
        return None
    
    df = calculate_indicators(df)
    
    cash = INITIAL_CAPITAL
    positions = {}
    trades = []
    values = []
    
    total_commission = 0
    total_stamp_duty = 0
    
    for i in range(30, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        volatility = df['volatility'].iloc[i]
        
        in_crash_mode = False
        if index_df is not None and date in index_df.index:
            index_close = index_df['close'].loc[date]
            index_ma60 = index_df['ma60'].loc[date]
            index_change = (index_close - index_ma60) / index_ma60 if index_ma60 > 0 else 0
            
            if index_change < -0.05:
                in_crash_mode = True
        
        current_pos_value = sum(p['shares'] * close for p in positions.values())
        total_value = cash + current_pos_value
        target_position = STRATEGY['position_base']
        
        if in_crash_mode:
            target_position = STRATEGY['crash_position']
        elif volatility < STRATEGY['volatility_low']:
            target_position = STRATEGY['position_base'] * 1.3
        elif volatility > STRATEGY['volatility_high']:
            target_position = STRATEGY['position_base'] * 0.7
        
        grid_size = max(0.015, STRATEGY['grid_base'] + (volatility - 40) * STRATEGY['grid_volatility_factor'] / 100)
        
        for pos_code in list(positions.keys()):
            pos = positions[pos_code]
            pnl = (close - pos['avg_price']) / pos['avg_price']
            
            if close > pos.get('highest_price', 0):
                pos['highest_price'] = close
            
            if pnl <= STRATEGY['stop_loss']:
                sell_value = pos['shares'] * close
                commission = sell_value * STRATEGY['commission']
                stamp_duty = sell_value * STRATEGY['stamp_duty']
                cash += sell_value - commission - stamp_duty
                
                total_commission += commission
                total_stamp_duty += stamp_duty
                
                profit = sell_value - pos['cost_basis'] - commission - stamp_duty
                
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'code': pos_code,
                    'type': '止损',
                    'price': close,
                    'shares': pos['shares'],
                    'pnl': pnl * 100,
                    'profit': profit,
                    'commission': commission,
                    'stamp_duty': stamp_duty
                })
                
                del positions[pos_code]
                continue
            
            if pos.get('highest_price', 0) > pos['avg_price'] * 1.15:
                highest = pos['highest_price']
                drawdown = (close - highest) / highest
                
                if drawdown <= -STRATEGY['trailing_stop']['drawdown']:
                    sell_value = pos['shares'] * close
                    commission = sell_value * STRATEGY['commission']
                    stamp_duty = sell_value * STRATEGY['stamp_duty']
                    cash += sell_value - commission - stamp_duty
                    
                    total_commission += commission
                    total_stamp_duty += stamp_duty
                    
                    profit = sell_value - pos['cost_basis'] - commission - stamp_duty
                    
                    trades.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'code': pos_code,
                        'type': '移动止盈',
                        'price': close,
                        'shares': pos['shares'],
                        'pnl': pnl * 100,
                        'profit': profit,
                        'commission': commission,
                        'stamp_duty': stamp_duty
                    })
                    
                    del positions[pos_code]
                    continue
            
            for level in STRATEGY['take_profit_levels']:
                if pnl >= level['threshold'] and not pos.get(f'sold_{level["threshold"]}', False):
                    sell_ratio = level['sell_ratio']
                    sell_shares = int(pos['shares'] * sell_ratio)
                    
                    if sell_shares >= 100:
                        sell_value = sell_shares * close
                        commission = sell_value * STRATEGY['commission']
                        stamp_duty = sell_value * STRATEGY['stamp_duty']
                        cash += sell_value - commission - stamp_duty
                        
                        total_commission += commission
                        total_stamp_duty += stamp_duty
                        
                        pos['shares'] -= sell_shares
                        pos[f'sold_{level["threshold"]}'] = True
                        
                        trades.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'code': pos_code,
                            'type': f'分批止盈{int(sell_ratio*100)}%',
                            'price': close,
                            'shares': sell_shares,
                            'pnl': pnl * 100,
                            'profit': (close - pos['avg_price']) * sell_shares - commission - stamp_duty,
                            'commission': commission,
                            'stamp_duty': stamp_duty
                        })
            
            for j, (level, ratio) in enumerate(zip(
                STRATEGY['add_position_levels'],
                STRATEGY['add_position_ratios']
            )):
                if pnl <= level and pos.get('add_count', 0) <= j:
                    add_cash = total_value * ratio
                    add_shares = int(add_cash / close / 100) * 100
                    
                    if add_shares >= 100:
                        add_cost = add_shares * close * (1 + STRATEGY['commission'])
                        
                        if cash >= add_cost:
                            old_value = pos['shares'] * pos['avg_price']
                            new_value = add_shares * close
                            pos['shares'] += add_shares
                            pos['avg_price'] = (old_value + new_value) / pos['shares']
                            pos['cost_basis'] += add_cost
                            pos['add_count'] = j + 1
                            
                            cash -= add_cost
                            total_commission += add_shares * close * STRATEGY['commission']
                            
                            trades.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'code': pos_code,
                                'type': '金字塔补仓',
                                'price': close,
                                'shares': add_shares,
                                'pnl': pnl * 100,
                                'commission': add_shares * close * STRATEGY['commission']
                            })
        
        rsi = df['rsi'].iloc[i]
        macd_hist = df['macd_hist'].iloc[i]
        ma20 = df['ma20'].iloc[i]
        volume_ratio = df['volume'].iloc[i] / df['volume_ma20'].iloc[i] if df['volume_ma20'].iloc[i] > 0 else 0
        
        rsi_buy = rsi < STRATEGY['rsi_buy']
        macd_ok = macd_hist > 0
        trend_ok = close > ma20
        volume_ok = volume_ratio > STRATEGY['volume_ratio']
        
        if in_crash_mode and len(positions) < 3:
            target_value = total_value * STRATEGY['crash_position']
            shares = int(target_value / close / 100) * 100
            
            if shares >= 100 and code not in positions:
                cost = shares * close * (1 + STRATEGY['commission'])
                
                if cash >= cost:
                    cash -= cost
                    
                    positions[code] = {
                        'shares': shares,
                        'avg_price': close,
                        'cost_basis': cost,
                        'add_count': 0,
                        'highest_price': close
                    }
                    
                    total_commission += shares * close * STRATEGY['commission']
                    
                    trades.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'code': code,
                        'type': '大盘暴跌买入',
                        'price': close,
                        'shares': shares,
                        'rsi': rsi,
                        'commission': shares * close * STRATEGY['commission']
                    })
        
        elif rsi_buy and macd_ok and trend_ok and volume_ok and len(positions) < 5:
            target_value = total_value * target_position
            shares = int(target_value / close / 100) * 100
            
            if shares >= 100 and code not in positions:
                cost = shares * close * (1 + STRATEGY['commission'])
                
                if cash >= cost:
                    cash -= cost
                    
                    positions[code] = {
                        'shares': shares,
                        'avg_price': close,
                        'cost_basis': cost,
                        'add_count': 0,
                        'highest_price': close
                    }
                    
                    total_commission += shares * close * STRATEGY['commission']
                    
                    trades.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'code': code,
                        'type': '买入',
                        'price': close,
                        'shares': shares,
                        'rsi': rsi,
                        'volume_ratio': volume_ratio,
                        'commission': shares * close * STRATEGY['commission']
                    })
        
        pos_value = sum(p['shares'] * close for p in positions.values())
        values.append(cash + pos_value)
    
    if positions:
        final_price = df['close'].iloc[-1]
        final_date = df.index[-1]
        
        for pos_code, pos in positions.items():
            sell_value = pos['shares'] * final_price
            commission = sell_value * STRATEGY['commission']
            stamp_duty = sell_value * STRATEGY['stamp_duty']
            cash += sell_value - commission - stamp_duty
            
            total_commission += commission
            total_stamp_duty += stamp_duty
            
            profit = sell_value - pos['cost_basis'] - commission - stamp_duty
            
            trades.append({
                'date': final_date.strftime('%Y-%m-%d'),
                'code': pos_code,
                'type': '期末平仓',
                'price': final_price,
                'shares': pos['shares'],
                'profit': profit,
                'commission': commission,
                'stamp_duty': stamp_duty
            })
    
    total_value = cash
    total_return = (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    sell_trades = [t for t in trades if t.get('profit') is not None and t['type'] not in ['补仓', '金字塔补仓']]
    profitable = [t for t in sell_trades if t['profit'] > 0]
    win_rate = len(profitable) / len(sell_trades) if sell_trades else 0
    
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 and rets.std() > 0 else 0
    
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    return {
        'code': code,
        'name': name,
        'year': YEAR,
        'initial': INITIAL_CAPITAL,
        'final': total_value,
        'return': total_return,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'total_trades': len(trades),
        'buy_trades': len([t for t in trades if t['type'] == '买入']),
        'sell_trades': len([t for t in trades if '止盈' in t['type'] or t['type'] in ['止损', '期末平仓']]),
        'add_trades': len([t for t in trades if '补仓' in t['type']]),
        'crash_trades': len([t for t in trades if t['type'] == '大盘暴跌买入']),
        'total_commission': total_commission,
        'total_stamp_duty': total_stamp_duty,
        'total_cost': total_commission + total_stamp_duty,
        'trade_details': trades
    }


def main():
    """主函数"""
    print("="*70)
    print(f"中频交易策略回测 ({YEAR}年) - 超级优化版")
    print("="*70)
    
    index_df = get_index_data(YEAR)
    
    results = []
    
    for code, name, industry in STOCK_POOL:
        print(f"\n[{code}] {name} ({industry})...", end=' ')
        
        df = get_data(code, YEAR)
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        result = backtest_2025(df, index_df, code, name)
        
        if result:
            results.append(result)
            print(f"收益{result['return']*100:+.1f}%, 胜率{result['win_rate']*100:.0f}%, "
                  f"交易{result['total_trades']}次，费用¥{result['total_cost']:.0f}"
                  f"{' 暴跌买入' + str(result['crash_trades']) if result['crash_trades'] > 0 else ''}")
        else:
            print("❌ 回测失败")
    
    print(f"\n{'='*70}")
    print(f"{YEAR}年汇总")
    print(f"{'='*70}")
    
    avg_return = np.mean([r['return'] for r in results]) if results else 0
    avg_win_rate = np.mean([r['win_rate'] for r in results]) if results else 0
    avg_sharpe = np.mean([r['sharpe'] for r in results]) if results else 0
    avg_dd = np.mean([r['max_dd'] for r in results]) if results else 0
    total_trades = sum([r['total_trades'] for r in results]) if results else 0
    total_cost = sum([r['total_cost'] for r in results]) if results else 0
    crash_trades = sum([r['crash_trades'] for r in results]) if results else 0
    
    print(f"股票数：{len(results)}")
    print(f"平均收益：{avg_return*100:+.1f}%")
    print(f"平均胜率：{avg_win_rate*100:.1f}%")
    print(f"平均夏普：{avg_sharpe:.2f}")
    print(f"平均回撤：{avg_dd*100:.1f}%")
    print(f"总交易数：{total_trades}")
    print(f"总费用：¥{total_cost:,.0f}")
    print(f"暴跌买入：{crash_trades}次")
    
    if results:
        best = max(results, key=lambda x: x['return'])
        worst = min(results, key=lambda x: x['return'])
        print(f"最佳：{best['name']} ({best['return']*100:+.1f}%)")
        print(f"最差：{worst['name']} ({worst['return']*100:+.1f}%)")
    
    output_dir = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for r in results:
        r.pop('trade_details', None)
    
    with open(output_dir / f'mf_backtest_{YEAR}_super.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 结果已保存：backtest_results/mf_backtest_{YEAR}_super.json")
    print("="*70)


if __name__ == '__main__':
    main()
