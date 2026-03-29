#!/usr/bin/env python3
"""
中频交易策略回测 - 优化版 (2023-2025)

优化点:
1. 放宽参数：RSI 25/75, 止损 -15%, 止盈 +20%
2. 补仓策略：-5%/-10%/-15% 补仓，单只最大 25%
3. 扩大股票池：15 只科技成长股
4. 详细记录：交易次数/日期/价格/手续费
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

# 股票池 (15 只科技成长股)
STOCK_POOL = [
    # 半导体 (5 只)
    ('sh.603986', '兆易创新', '半导体'),
    ('sz.002371', '北方华创', '半导体'),
    ('sh.603501', '韦尔股份', '半导体'),
    ('sh.688981', '中芯国际', '半导体'),
    ('sz.002156', '通富微电', '半导体'),
    
    # 科技 (5 只)
    ('sz.002415', '海康威视', '科技'),
    ('sh.601138', '工业富联', '科技'),
    ('sz.002049', '紫光国微', '科技'),
    ('sh.600584', '长电科技', '科技'),
    ('sz.002185', '华天科技', '科技'),
    
    # 新能源 (5 只)
    ('sz.300750', '宁德时代', '新能源'),
    ('sz.002594', '比亚迪', '新能源'),
    ('sh.601012', '隆基绿能', '新能源'),
    ('sz.300014', '亿纬锂能', '新能源'),
    ('sz.002709', '天赐材料', '新能源'),
]

# 优化策略参数
STRATEGY = {
    'rsi_buy': 25,           # RSI 超卖买入
    'rsi_sell': 75,          # RSI 超买卖出
    'stop_loss': -0.15,      # -15% 止损
    'take_profit': 0.20,     # +20% 止盈
    'grid_size': 0.02,       # 网格间距 2%
    
    # 补仓策略
    'add_position_levels': [-0.05, -0.10, -0.15],  # -5%/-10%/-15% 补仓
    'max_position_pct': 0.25,  # 单只最大 25% 仓位
    
    # 交易成本
    'commission': 0.0003,    # 手续费万分之三
    'stamp_duty': 0.001,     # 印花税千分之一 (卖出)
}


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


def calculate_indicators(df):
    """计算技术指标"""
    df = df.copy()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal_line']
    
    # 均线
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    
    # 网格基准
    df['grid_base'] = df['close'].rolling(window=20).mean()
    
    return df


def backtest_optimized(df, code, name):
    """
    优化版中频交易回测
    
    策略:
    1. RSI 25/75 波段
    2. -15% 止损，期间可补仓
    3. +20% 止盈
    4. 网格 2% 间距
    5. 单只最大 25% 仓位
    """
    if len(df) < 60:
        return None
    
    df = calculate_indicators(df)
    
    # 初始状态
    cash = INITIAL_CAPITAL
    positions = {}  # {code: {shares, avg_price, cost_basis, add_levels}}
    trades = []
    values = []
    
    total_commission = 0
    total_stamp_duty = 0
    
    # 每日检查
    for i in range(30, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        
        # 检查现有持仓
        for pos_code in list(positions.keys()):
            pos = positions[pos_code]
            pnl = (close - pos['avg_price']) / pos['avg_price']
            
            # 止损检查 (-15%)
            if pnl <= STRATEGY['stop_loss']:
                # 清仓止损
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
            
            # 止盈检查 (+20%)
            elif pnl >= STRATEGY['take_profit']:
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
                    'type': '止盈',
                    'price': close,
                    'shares': pos['shares'],
                    'pnl': pnl * 100,
                    'profit': profit,
                    'commission': commission,
                    'stamp_duty': stamp_duty
                })
                
                del positions[pos_code]
            
            # 补仓检查 (-5%/-10%/-15%)
            elif pnl in STRATEGY['add_position_levels'] or \
                 (pnl < 0 and abs(pnl) >= 0.05 and abs(pnl) < 0.15):
                # 检查是否已补仓
                add_level = int(abs(pnl) / 0.05)
                if add_level > pos.get('add_count', 0):
                    # 补仓 (加仓 5%)
                    add_cash = cash * 0.05
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
                            pos['add_count'] = add_level
                            
                            cash -= add_cost
                            total_commission += add_shares * close * STRATEGY['commission']
                            
                            trades.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'code': pos_code,
                                'type': '补仓',
                                'price': close,
                                'shares': add_shares,
                                'pnl': pnl * 100,
                                'commission': add_shares * close * STRATEGY['commission']
                            })
        
        # 检查买入信号 (无持仓时)
        rsi = df['rsi'].iloc[i]
        
        # RSI 超卖 (25 以下)
        rsi_buy = rsi < STRATEGY['rsi_buy']
        
        # MACD 金叉或接近金叉
        macd_buy = df['macd_hist'].iloc[i] > df['macd_hist'].iloc[i-1]
        
        # 趋势过滤 (放宽：不要求多头排列，只要不在暴跌中)
        not_crash = close > df['ma60'].iloc[i] * 0.9  # 不在 60 日线下方 10%
        
        if rsi_buy and macd_buy and not_crash and len(positions) < 5:
            # 检查单只股票仓位
            current_pos_value = sum(p['shares'] * close for p in positions.values())
            total_value = cash + current_pos_value
            
            # 新开仓位 20%
            target_value = total_value * 0.20
            
            # 检查是否已有该股票持仓
            if code not in positions:
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
                            'rsi': rsi,
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
    sell_trades = [t for t in trades if t.get('profit') is not None and t['type'] != '补仓']
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
        'sell_trades': len([t for t in trades if t['type'] in ['止盈', '止损', '期末平仓']]),
        'add_trades': len([t for t in trades if t['type'] == '补仓']),
        'total_commission': total_commission,
        'total_stamp_duty': total_stamp_duty,
        'total_cost': total_commission + total_stamp_duty,
        'trade_details': trades
    }


def backtest_year(year):
    """回测某一年"""
    print(f"\n{'='*70}")
    print(f"回测 {year} 年 (优化版)")
    print(f"{'='*70}")
    
    results = []
    
    for code, name, industry in STOCK_POOL:
        print(f"\n[{code}] {name} ({industry})...", end=' ')
        
        df = get_data(code, year)
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        result = backtest_optimized(df, code, name)
        
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
    print("回测汇总分析 (优化版)")
    print(f"{'='*70}")
    
    for year in YEARS:
        year_results = [r for r in all_results if r['year'] == year]
        
        if not year_results:
            continue
        
        # 统计
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
        
        # 最佳股票
        best = max(year_results, key=lambda x: x['return'])
        worst = min(year_results, key=lambda x: x['return'])
        
        print(f"  最佳：{best['name']} ({best['return']*100:+.1f}%)")
        print(f"  最差：{worst['name']} ({worst['return']*100:+.1f}%)")
    
    # 总体统计
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
    
    # 详细结果 (不保存交易明细，避免文件太大)
    for r in all_results:
        r.pop('trade_details', None)
    
    detailed_file = output_dir / 'mf_backtest_optimized.json'
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    # 汇总报告
    report_file = output_dir / 'mf_backtest_optimized_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 中频交易策略回测报告 (2023-2025) - 优化版\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 优化内容\n\n")
        f.write(f"- RSI: 25/75 (更极端信号)\n")
        f.write(f"- 止损：-15% (期间可补仓)\n")
        f.write(f"- 止盈：+20% (让利润奔跑)\n")
        f.write(f"- 仓位：20% 初始，最大 25%\n")
        f.write(f"- 网格：2% 间距\n")
        f.write(f"- 股票池：15 只科技成长股\n\n")
        
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
    print("中频交易策略回测 (2023-2025) - 优化版")
    print("="*70)
    print(f"\n策略参数:")
    print(f"  RSI: {STRATEGY['rsi_buy']}/{STRATEGY['rsi_sell']}")
    print(f"  止损：{STRATEGY['stop_loss']*100}%")
    print(f"  止盈：{STRATEGY['take_profit']*100}%")
    print(f"  仓位：初始 20%, 最大{STRATEGY['max_position_pct']*100}%")
    print(f"  网格：{STRATEGY['grid_size']*100}%")
    print(f"  股票池：{len(STOCK_POOL)}只")
    
    all_results = []
    
    for year in YEARS:
        results = backtest_year(year)
        all_results.extend(results)
    
    # 分析结果
    analyze_results(all_results)
    
    # 保存结果
    save_results(all_results)
    
    print(f"\n{'='*70}")
    print("回测完成！")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
