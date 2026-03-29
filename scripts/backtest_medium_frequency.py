#!/usr/bin/env python3
"""
中频交易策略回测 - 2023/2024/2025 年

策略:
- 网格策略：1% 间距
- 波段策略：RSI 35/65
- 动量策略：15 周期突破

回测年份：2023、2024、2025
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

# 中频交易股票池 (10 只)
STOCK_POOL = [
    ('sh.603986', '兆易创新', '半导体'),
    ('sz.002371', '北方华创', '半导体'),
    ('sh.603501', '韦尔股份', '半导体'),
    ('sh.688981', '中芯国际', '半导体'),
    ('sz.002156', '通富微电', '半导体'),
    ('sz.002415', '海康威视', '科技'),
    ('sh.601138', '工业富联', '科技'),
    ('sz.002049', '紫光国微', '科技'),
    ('sh.600584', '长电科技', '科技'),
    ('sz.002185', '华天科技', '科技'),
    ('sz.300750', '宁德时代', '新能源'),
    ('sz.002594', '比亚迪', '新能源'),
    ('sh.601012', '隆基绿能', '新能源'),
]

# 策略参数
GRID_SIZE = 0.01  # 网格间距 1%
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65
BREAKOUT_PERIOD = 15


def get_data(code, year):
    """获取某年数据"""
    lg = bs.login()
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    
    rs = bs.query_history_k_data_plus(
        code, 
        "date,open,high,low,close,volume",
        start_date=start, 
        end_date=end, 
        frequency="d"
    )
    
    data = []
    while (rs.error_code == '0') and rs.next():
        data.append(rs.get_row_data())
    
    bs.logout()
    
    if len(data) < 60:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    
    # 类型转换
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna()
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
    
    # 高低点 (动量突破)
    df['high_15'] = df['high'].rolling(window=BREAKOUT_PERIOD).max()
    df['low_15'] = df['low'].rolling(window=BREAKOUT_PERIOD).min()
    
    # 网格基准价 (20 日均线)
    df['grid_base'] = df['close'].rolling(window=20).mean()
    
    return df


def backtest_medium_frequency(df, code, name):
    """
    中频交易策略回测
    
    逻辑:
    1. 网格：价格偏离基准价 1% 触发
    2. 波段：RSI<35+MACD 金叉买入，RSI>65+MACD 死叉卖出
    3. 动量：突破 15 周期高点买入，跌破低点卖出
    """
    if len(df) < 60:
        return None
    
    df = calculate_indicators(df)
    
    # 初始状态
    cash = INITIAL_CAPITAL
    pos = 0
    in_pos = False
    buy_price = 0
    grid_base = 0
    
    trades = []
    values = []
    
    # 每日检查
    for i in range(30, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        
        # 更新网格基准
        if not in_pos:
            grid_base = df['grid_base'].iloc[i]
        
        # 检查止损止盈
        if in_pos:
            pnl = (close - buy_price) / buy_price
            
            # 止损 -3%
            if pnl <= -0.03:
                profit = (close - buy_price) * pos
                cash += pos * close * 0.999
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': '止损',
                    'price': close,
                    'shares': pos,
                    'profit': profit
                })
                pos = 0
                in_pos = False
            
            # 止盈 +8%
            elif pnl >= 0.08:
                profit = (close - buy_price) * pos
                cash += pos * close * 0.999
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': '止盈',
                    'price': close,
                    'shares': pos,
                    'profit': profit
                })
                pos = 0
                in_pos = False
        
        # 生成信号
        buy_signal = False
        sell_signal = False
        reason = []
        
        # 1. 网格策略
        if grid_base > 0:
            price_change = (close - grid_base) / grid_base
            if price_change <= -GRID_SIZE and not in_pos:
                buy_signal = True
                reason.append('网格超跌')
            elif price_change >= GRID_SIZE and in_pos:
                sell_signal = True
                reason.append('网格超涨')
        
        # 2. 波段策略
        if not in_pos:
            rsi_buy = df['rsi'].iloc[i] < RSI_OVERSOLD
            macd_buy = df['macd_hist'].iloc[i] > 0 and df['macd_hist'].iloc[i-1] <= 0
            if rsi_buy and macd_buy:
                buy_signal = True
                reason.append('波段金叉')
        else:
            rsi_sell = df['rsi'].iloc[i] > RSI_OVERBOUGHT
            macd_sell = df['macd_hist'].iloc[i] < 0 and df['macd_hist'].iloc[i-1] >= 0
            if rsi_sell and macd_sell:
                sell_signal = True
                reason.append('波段死叉')
        
        # 3. 动量策略
        if not in_pos and close > df['high_15'].iloc[i]:
            volume_confirm = df['volume'].iloc[i] > df['volume'].rolling(20).mean().iloc[i] * 1.3
            if volume_confirm:
                buy_signal = True
                reason.append('动量突破')
        elif in_pos and close < df['low_15'].iloc[i]:
            sell_signal = True
            reason.append('动量跌破')
        
        # 执行交易
        if buy_signal and not in_pos:
            # 买入 (10% 仓位)
            target_value = cash * 0.10
            shares = int(target_value / close / 100) * 100
            
            if shares >= 100:
                cost = shares * close * 1.001
                if cost <= cash:
                    cash -= cost
                    pos = shares
                    in_pos = True
                    buy_price = close
                    
                    trades.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'type': '买入',
                        'reason': ', '.join(reason),
                        'price': close,
                        'shares': shares
                    })
        
        elif sell_signal and in_pos:
            # 卖出
            profit = (close - buy_price) * pos
            cash += pos * close * 0.999
            
            trades.append({
                'date': date.strftime('%Y-%m-%d'),
                'type': '卖出',
                'reason': ', '.join(reason),
                'price': close,
                'shares': pos,
                'profit': profit
            })
            
            pos = 0
            in_pos = False
        
        # 记录总资产
        values.append(cash + (pos * close if in_pos else 0))
    
    # 期末平仓
    if in_pos and len(df) > 0:
        final_price = df['close'].iloc[-1]
        profit = (final_price - buy_price) * pos
        cash += pos * final_price * 0.999
        
        trades.append({
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'type': '期末平仓',
            'price': final_price,
            'shares': pos,
            'profit': profit
        })
    
    # 计算指标
    total_value = cash
    total_return = (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    # 胜率
    sell_trades = [t for t in trades if t.get('profit') is not None]
    profitable_trades = [t for t in sell_trades if t['profit'] > 0]
    win_rate = len(profitable_trades) / len(sell_trades) if sell_trades else 0
    
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
        'trades': len(trades),
        'trade_details': trades
    }


def backtest_year(year):
    """回测某一年"""
    print(f"\n{'='*70}")
    print(f"回测 {year} 年")
    print(f"{'='*70}")
    
    results = []
    
    for code, name, industry in STOCK_POOL:
        print(f"\n[{code}] {name} ({industry})...", end=' ')
        
        df = get_data(code, year)
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        result = backtest_medium_frequency(df, code, name)
        
        if result:
            results.append(result)
            print(f"收益 {result['return']*100:+6.1f}%, 胜率{result['win_rate']*100:.1f}%")
        else:
            print("❌ 回测失败")
    
    return results


def analyze_results(all_results):
    """分析回测结果"""
    print(f"\n{'='*70}")
    print("回测汇总分析")
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
        total_trades = sum([r['trades'] for r in year_results])
        
        print(f"\n{year}年:")
        print(f"  股票数：{len(year_results)}")
        print(f"  平均收益：{avg_return*100:+.1f}%")
        print(f"  平均胜率：{avg_win_rate*100:.1f}%")
        print(f"  平均夏普：{avg_sharpe:.2f}")
        print(f"  平均回撤：{avg_dd*100:.1f}%")
        print(f"  总交易数：{total_trades}")
        
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
    
    print(f"三年总收益：{total_return:.1f}%")
    print(f"年化收益：{(1 + total_return/100)**(1/3) - 1:.1f}%")


def save_results(all_results):
    """保存回测结果"""
    output_dir = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 详细结果
    detailed_file = output_dir / 'mf_backtest_2023_2025.json'
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    # 汇总报告
    report_file = output_dir / 'mf_backtest_summary.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 中频交易策略回测报告 (2023-2025)\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 策略参数\n\n")
        f.write(f"- 网格间距：{GRID_SIZE*100}%\n")
        f.write(f"- RSI 超卖：{RSI_OVERSOLD}\n")
        f.write(f"- RSI 超买：{RSI_OVERBOUGHT}\n")
        f.write(f"- 突破周期：{BREAKOUT_PERIOD}\n")
        f.write(f"- 初始资金：¥{INITIAL_CAPITAL:,.0f}\n\n")
        
        f.write("## 股票池\n\n")
        for code, name, industry in STOCK_POOL:
            f.write(f"- {code} {name} ({industry})\n")
        
        f.write("\n## 年度表现\n\n")
        
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
    print("中频交易策略回测 (2023-2025)")
    print("="*70)
    
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
