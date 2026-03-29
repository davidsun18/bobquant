#!/usr/bin/env python3
"""
日线策略回测 - 2023/2024/2025 年

验证日线策略真实收益水平
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

# 日线策略参数
STRATEGY = {
    # 双 MACD
    'macd_short': (6, 13, 5),
    'macd_long': (24, 52, 18),
    
    # 布林带
    'boll_window': 20,
    'boll_std': 2,
    
    # RSI 过滤
    'rsi_buy_max': 35,
    'rsi_sell_min': 70,
    
    # 仓位管理
    'max_position_pct': 0.10,  # 单只最大 10%
    'max_stocks': 10,          # 最大持仓 10 只
    
    # 金字塔加仓
    'pyramid_levels': [0.03, 0.05, 0.07],  # 下跌 3%/5%/7% 加仓
    
    # 止损止盈
    'stop_loss': -0.08,  # -8% 止损
    'take_profit_levels': [
        {'threshold': 0.05, 'sell_ratio': 0.33},   # +5% 卖 33%
        {'threshold': 0.10, 'sell_ratio': 0.50},   # +10% 卖 50%
        {'threshold': 0.15, 'sell_ratio': 1.00},   # +15% 清仓
    ],
    
    # 大盘风控
    'index_code': 'sh.000001',
    'ma20_line': 20,
    'max_position_bear': 0.50,  # 跌破 20 日线仓位≤50%
    
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
    
    return df


def calculate_indicators(df):
    """计算技术指标"""
    df = df.copy()
    
    # 双 MACD
    # 短周期
    exp1_fast = df['close'].ewm(span=STRATEGY['macd_short'][0], adjust=False).mean()
    exp2_fast = df['close'].ewm(span=STRATEGY['macd_short'][1], adjust=False).mean()
    df['macd_fast'] = exp1_fast - exp2_fast
    df['signal_fast'] = df['macd_fast'].ewm(span=STRATEGY['macd_short'][2], adjust=False).mean()
    df['hist_fast'] = df['macd_fast'] - df['signal_fast']
    
    # 长周期
    exp1_slow = df['close'].ewm(span=STRATEGY['macd_long'][0], adjust=False).mean()
    exp2_slow = df['close'].ewm(span=STRATEGY['macd_long'][1], adjust=False).mean()
    df['macd_slow'] = exp1_slow - exp2_slow
    df['signal_slow'] = df['macd_slow'].ewm(span=STRATEGY['macd_long'][2], adjust=False).mean()
    df['hist_slow'] = df['macd_slow'] - df['signal_slow']
    
    # 布林带
    df['ma20'] = df['close'].rolling(STRATEGY['boll_window']).mean()
    df['std20'] = df['close'].rolling(STRATEGY['boll_window']).std()
    df['boll_upper'] = df['ma20'] + (df['std20'] * STRATEGY['boll_std'])
    df['boll_lower'] = df['ma20'] - (df['std20'] * STRATEGY['boll_std'])
    df['boll_position'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'] + 1e-12)
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df


def backtest_day_trading(df, index_df, code, name):
    """
    日线策略回测
    
    逻辑:
    1. 双 MACD 金叉 + 布林带下轨 → 买入
    2. 双 MACD 死叉 + 布林带上轨 → 卖出
    3. RSI 过滤 (超卖买，超买卖)
    4. 金字塔加仓
    5. 分批止盈
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
    
    for i in range(30, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        
        # 大盘状态
        in_bear_market = False
        if index_df is not None and date in index_df.index:
            index_close = index_df['close'].loc[date]
            index_ma20 = index_df['ma20'].loc[date]
            if index_close < index_ma20:
                in_bear_market = True
        
        # 检查现有持仓
        for pos_code in list(positions.keys()):
            pos = positions[pos_code]
            pnl = (close - pos['avg_price']) / pos['avg_price']
            
            # 止损检查 (-8%)
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
            
            # 金字塔加仓
            for j, add_pct in enumerate(STRATEGY['pyramid_levels']):
                if pnl <= -add_pct and pos.get('add_count', 0) <= j:
                    add_cash = pos['cost_basis'] * 0.3  # 加仓 30%
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
                                'type': '金字塔加仓',
                                'price': close,
                                'shares': add_shares,
                                'pnl': pnl * 100,
                                'commission': add_shares * close * STRATEGY['commission']
                            })
        
        # 检查买入信号
        # 双 MACD 金叉
        macd_buy = (
            df['hist_fast'].iloc[i] > 0 and df['hist_fast'].iloc[i-1] <= 0 and
            df['hist_slow'].iloc[i] > 0 and df['hist_slow'].iloc[i-1] <= 0
        )
        
        # 布林带下轨
        boll_buy = df['boll_position'].iloc[i] < 0.2
        
        # RSI 超卖
        rsi_buy = df['rsi'].iloc[i] < STRATEGY['rsi_buy_max']
        
        # 大盘风控
        max_position = STRATEGY['max_position_pct']
        if in_bear_market:
            max_position = STRATEGY['max_position_pct'] * STRATEGY['max_position_bear']
        
        # 买入信号 (放宽条件：满足 2 个即可)
        buy_signals = sum([macd_buy, boll_buy, rsi_buy])
        if buy_signals >= 2 and code not in positions and len(positions) < STRATEGY['max_stocks']:
            target_value = cash * max_position
            shares = int(target_value / close / 100) * 100
            
            if shares >= 100:
                cost = shares * close * (1 + STRATEGY['commission'])
                
                if cash >= cost:
                    cash -= cost
                    
                    positions[code] = {
                        'shares': shares,
                        'avg_price': close,
                        'cost_basis': cost,
                        'add_count': 0
                    }
                    
                    total_commission += shares * close * STRATEGY['commission']
                    
                    trades.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'code': code,
                        'type': '买入',
                        'price': close,
                        'shares': shares,
                        'rsi': df['rsi'].iloc[i],
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
    
    sell_trades = [t for t in trades if t.get('profit') is not None and t['type'] not in ['加仓', '金字塔加仓']]
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
        'buy_trades': len([t for t in trades if t['type'] == '买入']),
        'sell_trades': len([t for t in trades if '止盈' in t['type'] or t['type'] in ['止损', '期末平仓']]),
        'add_trades': len([t for t in trades if '加仓' in t['type']]),
        'total_commission': total_commission,
        'total_stamp_duty': total_stamp_duty,
        'total_cost': total_commission + total_stamp_duty,
        'trade_details': trades
    }


def backtest_year(year):
    """回测某一年"""
    print(f"\n{'='*70}")
    print(f"回测 {year} 年 (日线策略)")
    print(f"{'='*70}")
    
    index_df = get_index_data(year)
    
    results = []
    
    for code, name, industry in STOCK_POOL:
        print(f"\n[{code}] {name} ({industry})...", end=' ')
        
        df = get_data(code, year)
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        result = backtest_day_trading(df, index_df, code, name)
        
        if result:
            results.append(result)
            print(f"收益{result['return']*100:+.1f}%, 胜率{result['win_rate']*100:.0f}%, "
                  f"交易{result['total_trades']}次，费用¥{result['total_cost']:.0f}")
        else:
            print("❌ 回测失败")
    
    return results


def analyze_results(all_results):
    """分析回测结果"""
    print(f"\n{'='*70}")
    print("回测汇总分析 (日线策略)")
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
        
        print(f"\n{year}年:")
        print(f"  股票数：{len(year_results)}")
        print(f"  平均收益：{avg_return*100:+.1f}%")
        print(f"  平均胜率：{avg_win_rate*100:.1f}%")
        print(f"  平均夏普：{avg_sharpe:.2f}")
        print(f"  平均回撤：{avg_dd*100:.1f}%")
        print(f"  总交易数：{total_trades}")
        print(f"  总费用：¥{total_cost:,.0f}")
        
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
    
    print(f"三年总收益：{total_return:.1f}%")
    print(f"年化收益：{(1 + total_return/100)**(1/3) - 1:.1f}%")
    print(f"总交易次数：{all_trades}")
    print(f"总交易费用：¥{all_cost:,.0f}")
    print(f"平均胜率：{np.mean([r['win_rate'] for r in all_results])*100:.1f}%")


def save_results(all_results):
    """保存回测结果"""
    output_dir = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for r in all_results:
        r.pop('trade_details', None)
    
    detailed_file = output_dir / 'day_trading_backtest_2023_2025.json'
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    report_file = output_dir / 'DAY_TRADING_BACKTEST_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 日线策略回测报告 (2023-2025)\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 策略参数\n\n")
        f.write(f"- 双 MACD: {STRATEGY['macd_short']} / {STRATEGY['macd_long']}\n")
        f.write(f"- 布林带：{STRATEGY['boll_window']} 周期，{STRATEGY['boll_std']} 标准差\n")
        f.write(f"- RSI 过滤：< {STRATEGY['rsi_buy_max']} 买入\n")
        f.write(f"- 仓位：单只最大{STRATEGY['max_position_pct']*100}%\n")
        f.write(f"- 止损：{STRATEGY['stop_loss']*100}%\n")
        f.write(f"- 止盈：分批 ({[l['threshold']*100 for l in STRATEGY['take_profit_levels']]})\n\n")
        
        f.write("## 股票池\n\n")
        for code, name, industry in STOCK_POOL:
            f.write(f"- {code} {name} ({industry})\n")
        
        f.write("\n## 回测结果\n\n")
        
        for year in YEARS:
            year_results = [r for r in all_results if r['year'] == year]
            if year_results:
                avg_return = np.mean([r['return'] for r in year_results])
                avg_win_rate = np.mean([r['win_rate'] for r in year_results])
                
                f.write(f"### {year}年\n\n")
                f.write(f"- 平均收益：{avg_return*100:+.1f}%\n")
                f.write(f"- 平均胜率：{avg_win_rate*100:.1f}%\n\n")
    
    print(f"\n✅ 结果已保存:")
    print(f"  详细：{detailed_file}")
    print(f"  报告：{report_file}")


def main():
    """主函数"""
    print("="*70)
    print("日线策略回测 (2023-2025)")
    print("="*70)
    print(f"\n策略参数:")
    print(f"  双 MACD: {STRATEGY['macd_short']} / {STRATEGY['macd_long']}")
    print(f"  布林带：{STRATEGY['boll_window']} 周期")
    print(f"  止损：{STRATEGY['stop_loss']*100}%")
    print(f"  止盈：分批{[l['threshold']*100 for l in STRATEGY['take_profit_levels']]}")
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
