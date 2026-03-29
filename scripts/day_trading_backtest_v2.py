#!/usr/bin/env python3
"""
日线策略回测 - 优化版 v2.0 (2023-2025)

优化内容:
1. 止盈：移动止盈 (+20% 激活，回撤 10%)
2. 止损：移动止损 (-15%→成本价→+10%)
3. 暴跌买入：30% + 次日 20% + 第三日 10%
4. 买入条件：3 条件 + 成交量确认
5. 仓位管理：动态仓位 (根据胜率)
6. 总持仓：5-8 只
7. 补仓：金字塔
8. 策略逻辑：趋势跟踪 (均线金叉 + RSI)
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
INITIAL_CAPITAL = 1000000  # 100 万

# 日线策略股票池 (30 只龙头)
STOCK_POOL = [
    # 银行金融 (5 只)
    ('sh.600036', '招商银行', '银行'),
    ('sh.601398', '工商银行', '银行'),
    ('sh.601288', '农业银行', '银行'),
    ('sh.601318', '中国平安', '保险'),
    ('sh.601688', '华泰证券', '证券'),
    
    # 白酒饮料 (4 只)
    ('sh.600519', '贵州茅台', '白酒'),
    ('sh.000858', '五粮液', '白酒'),
    ('sz.000568', '泸州老窖', '白酒'),
    ('sh.600809', '山西汾酒', '白酒'),
    
    # 消费 (5 只)
    ('sz.000333', '美的集团', '家电'),
    ('sz.000651', '格力电器', '家电'),
    ('sh.600887', '伊利股份', '食品'),
    ('sh.600690', '海尔智家', '家电'),
    ('sh.601888', '中国中免', '消费'),
    
    # 医药 (5 只)
    ('sh.600276', '恒瑞医药', '医药'),
    ('sz.300760', '迈瑞医疗', '医疗'),
    ('sh.600436', '片仔癀', '中药'),
    ('sh.603259', '药明康德', 'CXO'),
    ('sz.000538', '云南白药', '医药'),
    
    # 周期/科技 (11 只)
    ('sh.601088', '中国神华', '煤炭'),
    ('sh.600028', '中国石化', '石化'),
    ('sh.600309', '万华化学', '化工'),
    ('sh.600547', '山东黄金', '有色'),
    ('sh.601012', '隆基绿能', '光伏'),
    ('sz.300750', '宁德时代', '新能源'),
    ('sz.002594', '比亚迪', '新能源'),
    ('sh.601138', '工业富联', '科技'),
    ('sz.002415', '海康威视', '科技'),
    ('sh.600584', '长电科技', '科技'),
    ('sh.688981', '中芯国际', '半导体'),
]

# 优化策略参数 v2.0
STRATEGY = {
    # 趋势跟踪
    'ma_fast': 20,
    'ma_slow': 60,
    
    # RSI 过滤
    'rsi_buy_max': 40,
    'rsi_sell_min': 70,
    'rsi_period': 14,
    
    # 成交量确认
    'volume_ratio': 1.5,
    
    # 仓位管理 (动态)
    'base_position': 0.15,      # 基础仓位 15%
    'max_position_single': 0.30, # 单只最大 30%
    'min_stocks': 5,            # 最小持仓 5 只
    'max_stocks': 8,            # 最大持仓 8 只
    
    # 动态仓位 (根据胜率)
    'win_rate_high': 0.60,      # 胜率>60%
    'win_rate_mid': 0.50,       # 胜率>50%
    
    # 移动止盈
    'take_profit_activation': 0.20,  # 盈利 20% 后激活
    'take_profit_drawdown': 0.10,    # 回撤 10% 止盈
    
    # 移动止损
    'stop_loss_initial': -0.15,      # 初始止损 -15%
    'stop_profit_level1': 0.10,      # 盈利 10% 后止损上移成本价
    'stop_profit_level2': 0.20,      # 盈利 20% 后止损上移 +10%
    
    # 金字塔补仓
    'pyramid_levels': [-0.08, -0.15],  # -8%/-15% 补仓
    'pyramid_ratios': [0.50, 0.30],    # 补 50%/30%
    
    # 暴跌买入
    'crash_buy_day1': 0.30,   # 第 1 天 30%
    'crash_buy_day2': 0.20,   # 第 2 天 20%
    'crash_buy_day3': 0.10,   # 第 3 天 10%
    'crash_threshold': -0.05, # 大盘跌 5% 触发
    
    # 大盘风控
    'index_code': 'sh.000001',
    'ma20_line': 20,
    
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
    
    # 均线 (趋势跟踪)
    df['ma20'] = df['close'].rolling(STRATEGY['ma_fast']).mean()
    df['ma60'] = df['close'].rolling(STRATEGY['ma_slow']).mean()
    
    # 均线金叉/死叉
    df['ma_golden'] = (df['ma20'] > df['ma60']) & (df['ma20'].shift(1) <= df['ma60'].shift(1))
    df['ma_dead'] = (df['ma20'] < df['ma60']) & (df['ma20'].shift(1) >= df['ma60'].shift(1))
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=STRATEGY['rsi_period']).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 成交量均线
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    # 布林带 (辅助)
    df['ma20_std'] = df['close'].rolling(20).std()
    df['boll_upper'] = df['ma20'] + (df['ma20_std'] * 2)
    df['boll_lower'] = df['ma20'] - (df['ma20_std'] * 2)
    
    return df


def backtest_day_trading_v2(df, index_df, code, name):
    """
    日线策略 v2.0 回测
    
    逻辑:
    1. 趋势跟踪：ma20>ma60 金叉 + RSI<40 + 成交量>1.5x → 买入
    2. 移动止盈：盈利>20% 后激活，回撤 10% 止盈
    3. 移动止损：-15% → 成本价 → +10%
    4. 暴跌买入：30% + 20% + 10%
    5. 动态仓位：根据胜率调整
    6. 金字塔补仓：-8%/50%, -15%/30%
    """
    if len(df) < 60:
        return None
    
    df = calculate_indicators(df)
    
    cash = INITIAL_CAPITAL
    positions = {}
    trades = []
    values = []
    
    total_commission = 0
    total_stamp_duty = 0
    
    # 暴跌买入跟踪
    crash_buy_days = {}  # {code: [day1, day2, day3]}
    
    # 历史胜率 (用于动态仓位)
    historical_win_rate = 0.50  # 初始 50%
    total_trades_count = 0
    profitable_trades_count = 0
    
    for i in range(60, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        
        # 大盘状态
        in_bear_market = False
        index_change = 0
        if index_df is not None and date in index_df.index:
            index_close = index_df['close'].loc[date]
            index_ma60 = index_df['ma60'].loc[date]
            index_change = (index_close - index_ma60) / index_ma60 if index_ma60 > 0 else 0
            
            if index_close < index_df['ma20'].loc[date]:
                in_bear_market = True
        
        # 检查暴跌买入
        if index_change < STRATEGY['crash_threshold']:
            if code not in crash_buy_days:
                crash_buy_days[code] = [0, 0, 0]
            
            # 第 1 天暴跌
            if crash_buy_days[code][0] == 0:
                crash_buy_days[code] = [1, 0, 0]
            # 第 2 天继续暴跌
            elif crash_buy_days[code][0] == 1 and crash_buy_days[code][1] == 0:
                crash_buy_days[code][1] = 1
            # 第 3 天继续暴跌
            elif crash_buy_days[code][1] == 1 and crash_buy_days[code][2] == 0:
                crash_buy_days[code][2] = 1
        
        # 检查现有持仓
        for pos_code in list(positions.keys()):
            pos = positions[pos_code]
            pnl = (close - pos['avg_price']) / pos['avg_price']
            
            # 更新最高价 (用于移动止盈/止损)
            if close > pos.get('highest_price', pos['avg_price']):
                pos['highest_price'] = close
            
            # 移动止盈 (盈利>20% 后激活，回撤 10% 止盈)
            if pos.get('highest_price', 0) > pos['avg_price'] * (1 + STRATEGY['take_profit_activation']):
                highest = pos['highest_price']
                drawdown = (close - highest) / highest
                
                if drawdown <= -STRATEGY['take_profit_drawdown']:
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
                    
                    # 更新胜率
                    total_trades_count += 1
                    if profit > 0:
                        profitable_trades_count += 1
                    historical_win_rate = profitable_trades_count / total_trades_count if total_trades_count > 0 else 0.50
                    
                    del positions[pos_code]
                    continue
            
            # 移动止损
            current_stop_loss = STRATEGY['stop_loss_initial']
            
            # 盈利 10% 后，止损上移至成本价
            if pos.get('highest_price', 0) > pos['avg_price'] * (1 + STRATEGY['stop_profit_level1']):
                current_stop_loss = 0  # 成本价
            
            # 盈利 20% 后，止损上移至 +10%
            if pos.get('highest_price', 0) > pos['avg_price'] * (1 + STRATEGY['stop_profit_level2']):
                current_stop_loss = 0.10  # +10%
            
            if pnl <= current_stop_loss:
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
                    'type': '移动止损',
                    'price': close,
                    'shares': pos['shares'],
                    'pnl': pnl * 100,
                    'profit': profit,
                    'commission': commission,
                    'stamp_duty': stamp_duty
                })
                
                # 更新胜率
                total_trades_count += 1
                if profit > 0:
                    profitable_trades_count += 1
                historical_win_rate = profitable_trades_count / total_trades_count if total_trades_count > 0 else 0.50
                
                del positions[pos_code]
                continue
            
            # 金字塔补仓
            for j, (level, ratio) in enumerate(zip(
                STRATEGY['pyramid_levels'],
                STRATEGY['pyramid_ratios']
            )):
                if pnl <= level and pos.get('add_count', 0) <= j:
                    add_cash = pos['cost_basis'] * ratio
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
        
        # 动态仓位管理 (根据胜率)
        if historical_win_rate >= STRATEGY['win_rate_high']:
            target_position = STRATEGY['base_position'] * 1.3  # 20%
        elif historical_win_rate >= STRATEGY['win_rate_mid']:
            target_position = STRATEGY['base_position']  # 15%
        else:
            target_position = STRATEGY['base_position'] * 0.7  # 10%
        
        # 暴跌买入 (30% + 20% + 10%)
        if code in crash_buy_days and code not in positions:
            crash_day = sum(crash_buy_days[code])
            
            if crash_day >= 1 and crash_buy_days[code][0] == 1:
                crash_position = STRATEGY['crash_buy_day1']
            elif crash_day >= 2 and crash_buy_days[code][1] == 1:
                crash_position = STRATEGY['crash_buy_day2']
            elif crash_day >= 3 and crash_buy_days[code][2] == 1:
                crash_position = STRATEGY['crash_buy_day3']
            else:
                crash_position = 0
            
            if crash_position > 0:
                target_value = cash * crash_position
                shares = int(target_value / close / 100) * 100
                
                if shares >= 100:
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
                            'type': f'暴跌买入第{crash_day}天',
                            'price': close,
                            'shares': shares,
                            'crash_day': crash_day,
                            'commission': shares * close * STRATEGY['commission']
                        })
        
        # 趋势跟踪买入
        ma_golden = df['ma_golden'].iloc[i]
        rsi_buy = df['rsi'].iloc[i] < STRATEGY['rsi_buy_max']
        volume_ok = df['volume'].iloc[i] > df['volume_ma20'].iloc[i] * STRATEGY['volume_ratio']
        trend_ok = df['ma20'].iloc[i] > df['ma60'].iloc[i]
        
        # 买入条件：3 个条件 + 成交量确认
        if ma_golden and rsi_buy and trend_ok and volume_ok:
            if code not in positions and len(positions) < STRATEGY['max_stocks']:
                target_value = cash * target_position
                shares = int(target_value / close / 100) * 100
                
                if shares >= 100:
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
                            'type': '趋势跟踪买入',
                            'price': close,
                            'shares': shares,
                            'rsi': df['rsi'].iloc[i],
                            'volume_ratio': df['volume'].iloc[i] / df['volume_ma20'].iloc[i],
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
        'year': df.index[0].year,
        'initial': INITIAL_CAPITAL,
        'final': total_value,
        'return': total_return,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'total_trades': len(trades),
        'buy_trades': len([t for t in trades if '买入' in t['type']]),
        'sell_trades': len([t for t in trades if '止盈' in t['type'] or '止损' in t['type'] or t['type'] == '期末平仓']),
        'add_trades': len([t for t in trades if '补仓' in t['type']]),
        'crash_trades': len([t for t in trades if '暴跌' in t['type']]),
        'total_commission': total_commission,
        'total_stamp_duty': total_stamp_duty,
        'total_cost': total_commission + total_stamp_duty,
        'trade_details': trades
    }


def backtest_year(year):
    """回测某一年"""
    print(f"\n{'='*70}")
    print(f"回测 {year} 年 (日线策略 v2.0)")
    print(f"{'='*70}")
    
    index_df = get_index_data(year)
    
    results = []
    
    for code, name, industry in STOCK_POOL:
        print(f"\n[{code}] {name} ({industry})...", end=' ')
        
        df = get_data(code, year)
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        result = backtest_day_trading_v2(df, index_df, code, name)
        
        if result:
            results.append(result)
            crash_info = f" 暴跌{result['crash_trades']}次" if result['crash_trades'] > 0 else ""
            print(f"收益{result['return']*100:+.1f}%, 胜率{result['win_rate']*100:.0f}%, "
                  f"交易{result['total_trades']}次，费用¥{result['total_cost']:.0f}{crash_info}")
        else:
            print("❌ 回测失败")
    
    return results


def analyze_results(all_results):
    """分析回测结果"""
    print(f"\n{'='*70}")
    print("回测汇总分析 (日线策略 v2.0)")
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
    print(f"费用占比：{all_cost/(INITIAL_CAPITAL*abs(total_return)/100)*100:.1f}%" if total_return != 0 else "")
    print(f"平均胜率：{np.mean([r['win_rate'] for r in all_results])*100:.1f}%")
    print(f"暴跌买入：{all_crash_trades}次")


def save_results(all_results):
    """保存回测结果"""
    output_dir = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for r in all_results:
        r.pop('trade_details', None)
    
    detailed_file = output_dir / 'day_trading_backtest_v2_2023_2025.json'
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    report_file = output_dir / 'DAY_TRADING_BACKTEST_V2_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 日线策略回测报告 (2023-2025) - 优化版 v2.0\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 优化内容\n\n")
        f.write(f"- 止盈：移动止盈 (>20% 激活，回撤 10%)\n")
        f.write(f"- 止损：移动止损 (-15% → 成本价 → +10%)\n")
        f.write(f"- 暴跌买入：30% + 20% + 10%\n")
        f.write(f"- 买入条件：趋势跟踪 + RSI + 成交量\n")
        f.write(f"- 仓位管理：动态 (根据胜率)\n")
        f.write(f"- 总持仓：{STRATEGY['min_stocks']}-{STRATEGY['max_stocks']}只\n")
        f.write(f"- 补仓：金字塔{STRATEGY['pyramid_ratios']}\n\n")
        
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
    print("日线策略回测 (2023-2025) - 优化版 v2.0")
    print("="*70)
    print(f"\n策略参数:")
    print(f"  趋势跟踪：MA{STRATEGY['ma_fast']}/MA{STRATEGY['ma_slow']}")
    print(f"  止盈：移动 (>20% 激活，回撤 10%)\n")
    print(f"  止损：移动 (-15% → 成本价 → +10%)\n")
    print(f"  暴跌买入：{STRATEGY['crash_buy_day1']*100}% + {STRATEGY['crash_buy_day2']*100}% + {STRATEGY['crash_buy_day3']*100}%\n")
    print(f"  仓位：动态{STRATEGY['base_position']*100}% (根据胜率)")
    print(f"  持仓：{STRATEGY['min_stocks']}-{STRATEGY['max_stocks']}只")
    print(f"  补仓：金字塔{STRATEGY['pyramid_ratios']}")
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
