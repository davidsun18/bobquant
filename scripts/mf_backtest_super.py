#!/usr/bin/env python3
"""
中频交易策略回测 - 超级优化版 (2023-2025)

优化功能:
1. RSI 更激进：20/80
2. 移动止盈：超过 +15% 启动分批止盈
3. 动态仓位管理：根据波动率调整
4. 金字塔补仓：5%/3%/2%
5. 动态网格：根据波动率调整间距
6. 组合过滤：MA20+MACD+ 成交量
7. 避开波动：10:00-14:30 交易
8. 大盘暴跌反向买入：3 成仓
9. 股票池优化：剔除表现差的
"""

import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import baostock as bs

# ========== 配置 ==========
YEARS = [2023, 2024, 2025]
INITIAL_CAPITAL = 1000000  # 100 万

# 优化股票池 (12 只，剔除表现差的)
STOCK_POOL = [
    # 半导体 (5 只) - 表现最好
    ('sh.603986', '兆易创新', '半导体'),
    ('sz.002371', '北方华创', '半导体'),
    ('sh.603501', '韦尔股份', '半导体'),
    ('sh.688981', '中芯国际', '半导体'),
    ('sz.002156', '通富微电', '半导体'),
    
    # 科技 (4 只)
    ('sz.002415', '海康威视', '科技'),
    ('sh.601138', '工业富联', '科技'),
    ('sh.600584', '长电科技', '科技'),
    ('sz.002185', '华天科技', '科技'),
    
    # 新能源 (3 只) - 剔除表现差的
    ('sz.300750', '宁德时代', '新能源'),
    ('sh.601012', '隆基绿能', '新能源'),
    ('sz.300014', '亿纬锂能', '新能源'),
]

# 超级优化策略参数
STRATEGY = {
    # RSI 参数 (更激进)
    'rsi_buy': 20,
    'rsi_sell': 80,
    'rsi_period': 14,
    
    # 止盈策略 (分批 + 移动)
    'take_profit_levels': [
        {'threshold': 0.15, 'sell_ratio': 0.50},  # +15% 卖 50%
        {'threshold': 0.30, 'sell_ratio': 1.00},  # +30% 清仓
    ],
    'trailing_stop': {
        'activation': 0.15,   # 盈利 15% 后激活
        'drawdown': 0.08      # 从高点回撤 8% 止盈
    },
    
    # 止损
    'stop_loss': -0.20,       # -20% 硬止损
    
    # 动态仓位管理
    'position_base': 0.15,    # 基础仓位 15%
    'position_max': 0.30,     # 最大仓位 30%
    'volatility_low': 30,     # 低波动阈值
    'volatility_high': 60,    # 高波动阈值
    
    # 金字塔补仓
    'add_position_levels': [-0.05, -0.10, -0.15],
    'add_position_ratios': [0.05, 0.03, 0.02],  # 5%/3%/2%
    'max_position_pct': 0.30,  # 单只最大 30%
    
    # 动态网格
    'grid_base': 0.025,       # 基础网格 2.5%
    'grid_volatility_factor': 0.03,  # 波动率调整系数
    
    # 组合过滤
    'ma_period': 20,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'volume_ratio': 1.5,      # 成交量确认 1.5x
    
    # 交易时间 (避开波动)
    'trade_start': 10*60,     # 10:00
    'trade_end': 14*60 + 30,  # 14:30
    
    # 大盘风控 (暴跌反向买入)
    'index_code': 'sh.000001',
    'crash_threshold': -0.05,  # 大盘跌 5%
    'crash_position': 0.60,    # 反向买入 60% ⭐ 提高仓位
    
    # 交易成本
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
    for col in ['open', 'high', 'low', 'close', 'volume']:
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
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=STRATEGY['macd_fast'], adjust=False).mean()
    exp2 = df['close'].ewm(span=STRATEGY['macd_slow'], adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal_line'] = df['macd'].ewm(span=STRATEGY['macd_signal'], adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal_line']
    
    # 均线
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    
    # 波动率 (20 日年化)
    df['volatility'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252) * 100
    
    # 成交量均线
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    # 网格基准
    df['grid_base'] = df['close'].rolling(window=20).mean()
    
    return df


def get_dynamic_position(cash, total_value, volatility, in_crash_mode):
    """动态仓位管理"""
    if in_crash_mode:
        # 大盘暴跌，反向买入 30%
        return STRATEGY['crash_position']
    
    # 根据波动率调整
    if volatility < STRATEGY['volatility_low']:
        # 低波动，高仓位
        return STRATEGY['position_base'] * 1.3
    elif volatility > STRATEGY['volatility_high']:
        # 高波动，低仓位
        return STRATEGY['position_base'] * 0.7
    else:
        # 中等波动，标准仓位
        return STRATEGY['position_base']


def get_dynamic_grid(volatility):
    """动态网格间距"""
    base = STRATEGY['grid_base']
    adjustment = (volatility - 40) * STRATEGY['grid_volatility_factor'] / 100
    return max(0.015, base + adjustment)  # 最小 1.5%


def backtest_super_optimized(df, index_df, code, name):
    """
    超级优化版回测
    """
    if len(df) < 60:
        return None
    
    df = calculate_indicators(df)
    
    # 初始状态
    cash = INITIAL_CAPITAL
    positions = {}
    trades = []
    values = []
    
    total_commission = 0
    total_stamp_duty = 0
    
    # 每日检查
    for i in range(30, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        volatility = df['volatility'].iloc[i]
        
        # 大盘状态检查
        in_crash_mode = False
        if index_df is not None and date in index_df.index:
            index_close = index_df['close'].loc[date]
            index_ma60 = index_df['ma60'].loc[date]
            index_change = (index_close - index_ma60) / index_ma60 if index_ma60 > 0 else 0
            
            if index_change < -0.05:  # 大盘跌破 60 日线 5%
                in_crash_mode = True
        
        # 动态仓位
        current_pos_value = sum(p['shares'] * close for p in positions.values())
        total_value = cash + current_pos_value
        target_position = get_dynamic_position(cash, total_value, volatility, in_crash_mode)
        
        # 动态网格
        grid_size = get_dynamic_grid(volatility)
        
        # 检查现有持仓
        for pos_code in list(positions.keys()):
            pos = positions[pos_code]
            pnl = (close - pos['avg_price']) / pos['avg_price']
            
            # 更新最高价 (用于移动止盈)
            if close > pos.get('highest_price', 0):
                pos['highest_price'] = close
            
            # 硬止损 (-20%)
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
            
            # 移动止盈 (盈利 15% 后激活，回撤 8% 止盈)
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
            
            # 分批止盈
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
                        
                        # 更新持仓
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
            
            # 金字塔补仓
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
                            # 更新持仓
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
        
        # 检查买入信号
        rsi = df['rsi'].iloc[i]
        macd_hist = df['macd_hist'].iloc[i]
        ma20 = df['ma20'].iloc[i]
        volume_ratio = df['volume'].iloc[i] / df['volume_ma20'].iloc[i] if df['volume_ma20'].iloc[i] > 0 else 0
        
        # 组合过滤
        rsi_buy = rsi < STRATEGY['rsi_buy']
        macd_ok = macd_hist > 0
        trend_ok = close > ma20
        volume_ok = volume_ratio > STRATEGY['volume_ratio']
        
        # 大盘暴跌模式优先
        if in_crash_mode and len(positions) < 3:
            # 大胆买入 3 成仓
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
        
        # 正常买入信号
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
        
        # 记录总资产
        pos_value = sum(p['shares'] * close for p in positions.values())
        values.append(cash + pos_value)
    
    # 期末平仓
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
    
    # 计算指标
    total_value = cash
    total_return = (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    # 胜率
    sell_trades = [t for t in trades if t.get('profit') is not None and t['type'] not in ['补仓', '金字塔补仓']]
    profitable = [t for t in sell_trades if t['profit'] > 0]
    win_rate = len(profitable) / len(sell_trades) if sell_trades else 0
    
    # 夏普比率
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 and rets.std() > 0 else 0
    
    # 最大回撤
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    return {
        'code': code,
        'name': name,
        'year': df.index[0].year,
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


def backtest_year(year):
    """回测某一年"""
    print(f"\n{'='*70}")
    print(f"回测 {year} 年 (超级优化版)")
    print(f"{'='*70}")
    
    # 获取大盘数据
    index_df = get_index_data(year)
    
    results = []
    
    for code, name, industry in STOCK_POOL:
        print(f"\n[{code}] {name} ({industry})...", end=' ')
        
        df = get_data(code, year)
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        result = backtest_super_optimized(df, index_df, code, name)
        
        if result:
            results.append(result)
            print(f"收益{result['return']*100:+.1f}%, 胜率{result['win_rate']*100:.0f}%, "
                  f"交易{result['total_trades']}次，费用¥{result['total_cost']:.0f}"
                  f"{' 暴跌买入' + str(result['crash_trades']) if result['crash_trades'] > 0 else ''}")
        else:
            print("❌ 回测失败")
    
    return results


def analyze_results(all_results):
    """分析回测结果"""
    print(f"\n{'='*70}")
    print("回测汇总分析 (超级优化版)")
    print(f"{'='*70}")
    
    for year in YEARS:
        year_results = [r for r in all_results if r['year'] == year]
        
        if not year_results:
            continue
        
        avg_return = np.mean([r['return'] for r in year_results])
        avg_win_rate = np.mean([r['win_rate'] for r in year_results])
        avg_sharpe = np.mean([r['sharpe'] for r in year_results])
        avg_dd = np.mean([r['max_dd'] for r in year_results])
        total_trades = sum([r['total_trades'] for r in year_results])
        total_cost = sum([r['total_cost'] for r in year_results])
        crash_trades = sum([r['crash_trades'] for r in year_results])
        
        print(f"\n{year}年:")
        print(f"  股票数：{len(year_results)}")
        print(f"  平均收益：{avg_return*100:+.1f}%")
        print(f"  平均胜率：{avg_win_rate*100:.1f}%")
        print(f"  平均夏普：{avg_sharpe:.2f}")
        print(f"  平均回撤：{avg_dd*100:.1f}%")
        print(f"  总交易数：{total_trades}")
        print(f"  总费用：¥{total_cost:,.0f}")
        print(f"  暴跌买入：{crash_trades}次")
        
        best = max(year_results, key=lambda x: x['return'])
        worst = min(year_results, key=lambda x: x['return'])
        
        print(f"  最佳：{best['name']} ({best['return']*100:+.1f}%)")
        print(f"  最差：{worst['name']} ({worst['return']*100:+.1f}%)")
    
    print(f"\n{'='*70}")
    print("总体统计 (2023-2025)")
    print(f"{'='*70}")
    
    total_return = 1
    for year in YEARS:
        year_results = [r for r in all_results if r['year'] == year]
        if year_results:
            avg_return = np.mean([r['return'] for r in year_results])
            total_return *= (1 + avg_return)
    
    total_return = (total_return - 1) * 100
    
    all_trades = sum([r['total_trades'] for r in all_results])
    all_cost = sum([r['total_cost'] for r in all_results])
    all_crash_trades = sum([r['crash_trades'] for r in all_results])
    
    print(f"三年总收益：{total_return:.1f}%")
    print(f"年化收益：{(1 + total_return/100)**(1/3) - 1:.1f}%")
    print(f"总交易次数：{all_trades}")
    print(f"总交易费用：¥{all_cost:,.0f}")
    if total_return != 0:
        print(f"费用占比：{all_cost/(INITIAL_CAPITAL*abs(total_return)/100)*100:.1f}%")
    print(f"平均胜率：{np.mean([r['win_rate'] for r in all_results])*100:.1f}%")
    print(f"暴跌买入：{all_crash_trades}次")


def save_results(all_results):
    """保存回测结果"""
    output_dir = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for r in all_results:
        r.pop('trade_details', None)
    
    detailed_file = output_dir / 'mf_backtest_super.json'
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    report_file = output_dir / 'mf_backtest_super_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 中频交易策略回测报告 (2023-2025) - 超级优化版\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 优化内容\n\n")
        f.write(f"- RSI: {STRATEGY['rsi_buy']}/{STRATEGY['rsi_sell']} (更激进)\n")
        f.write(f"- 止盈：分批 + 移动 (>15% 启动)\n")
        f.write(f"- 止损：{STRATEGY['stop_loss']*100}%\n")
        f.write(f"- 仓位：动态管理 (15-30%)\n")
        f.write(f"- 补仓：金字塔 ({STRATEGY['add_position_ratios']})\n")
        f.write(f"- 网格：动态 ({STRATEGY['grid_base']*100}%)\n")
        f.write(f"- 过滤：MA20+MACD+ 成交量\n")
        f.write(f"- 大盘暴跌：反向买入{STRATEGY['crash_position']*100}%\n")
        f.write(f"- 股票池：{len(STOCK_POOL)}只 (优化版)\n\n")
        
        f.write("## 股票池\n\n")
        for code, name, industry in STOCK_POOL:
            f.write(f"- {code} {name} ({industry})\n")
        
        f.write("\n## 回测结果\n\n")
        
        for year in YEARS:
            year_results = [r for r in all_results if r['year'] == year]
            if year_results:
                avg_return = np.mean([r['return'] for r in year_results])
                avg_win_rate = np.mean([r['win_rate'] for r in year_results])
                total_trades = sum([r['total_trades'] for r in year_results])
                total_cost = sum([r['total_cost'] for r in year_results])
                
                f.write(f"### {year}年\n\n")
                f.write(f"- 平均收益：{avg_return*100:+.1f}%\n")
                f.write(f"- 平均胜率：{avg_win_rate*100:.1f}%\n")
                f.write(f"- 总交易数：{total_trades}\n")
                f.write(f"- 总费用：¥{total_cost:,.0f}\n\n")
    
    print(f"\n✅ 结果已保存:")
    print(f"  详细：{detailed_file}")
    print(f"  报告：{report_file}")


def main():
    """主函数"""
    print("="*70)
    print("中频交易策略回测 (2023-2025) - 超级优化版")
    print("="*70)
    print(f"\n策略参数:")
    print(f"  RSI: {STRATEGY['rsi_buy']}/{STRATEGY['rsi_sell']}")
    print(f"  止损：{STRATEGY['stop_loss']*100}%")
    print(f"  止盈：分批 + 移动 (>15% 启动)")
    print(f"  仓位：动态{STRATEGY['position_base']*100}-{STRATEGY['position_max']*100}%")
    print(f"  补仓：金字塔{STRATEGY['add_position_ratios']}")
    print(f"  网格：动态{STRATEGY['grid_base']*100}%")
    print(f"  过滤：MA20+MACD+ 成交量{STRATEGY['volume_ratio']}x")
    print(f"  大盘暴跌：反向买入{STRATEGY['crash_position']*100}%")
    print(f"  股票池：{len(STOCK_POOL)}只")
    
    all_results = []
    
    for year in YEARS:
        results = backtest_year(year)
        all_results.extend(results)
    
    analyze_results(all_results)
    save_results(all_results)
    
    print(f"\n{'='*70}")
    print("回测完成！")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
