"""
V3 策略回测对比 (V1 vs V2 vs V3)
"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import baostock as bs

# 导入 V3 策略
from bobquant_v2.strategy.enhanced_strategy_v3 import EnhancedStrategyV3, update_market_state

OUTPUT_DIR = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 股票池 (精选 15 只，加快回测)
STOCK_POOL = [
    ('sh.600036', '招商银行', '银行'),
    ('sh.601398', '工商银行', '银行'),
    ('sh.600519', '贵州茅台', '白酒'),
    ('sz.000568', '泸州老窖', '白酒'),
    ('sz.002415', '海康威视', '科技'),
    ('sh.601138', '工业富联', '科技'),
    ('sz.002371', '北方华创', '半导体'),
    ('sh.603986', '兆易创新', '半导体'),
    ('sz.300750', '宁德时代', '新能源'),
    ('sz.002594', '比亚迪', '新能源'),
    ('sh.601012', '隆基绿能', '光伏'),
    ('sh.600276', '恒瑞医药', '医药'),
    ('sz.000333', '美的集团', '家电'),
    ('sh.601899', '紫金矿业', '有色'),
    ('sh.601088', '中国神华', '煤炭'),
]

YEARS = [2023, 2024, 2025]


def get_data(code, year):
    """获取数据"""
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=f"{year}-01-01", end_date=f"{year}-12-31", frequency="d"
    )
    
    data = []
    while (rs.error_code == '0') and rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    if len(data) < 50:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date').sort_index()


def simulate_v1(df):
    """V1 原策略"""
    if len(df) < 60:
        return None
    
    df = df.copy()
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['roc5'] = df['close'].pct_change(5)
    df['roc10'] = df['close'].pct_change(10)
    df['vol10'] = df['close'].rolling(10).std() / df['close']
    
    low_5 = df['low'].rolling(5).min()
    high_5 = df['high'].rolling(5).max()
    df['rsv5'] = (df['close'] - low_5) / (high_5 - low_5 + 1e-12)
    
    cash = 100000
    pos = 0
    in_pos = False
    buy_price = 0
    values = []
    trades = []
    
    for i in range(25, len(df)):
        close = df['close'].iloc[i]
        
        score = 50
        if df['rsv5'].iloc[i] < 0.2: score += 25
        elif df['rsv5'].iloc[i] > 0.8: score -= 25
        if df['roc10'].iloc[i] < -0.1: score += 30
        elif df['roc10'].iloc[i] > 0.1: score -= 30
        if df['roc5'].iloc[i] < -0.08: score += 15
        elif df['roc5'].iloc[i] > 0.08: score -= 15
        if df['vol10'].iloc[i] > 0.08: score += 20
        
        ma_ratio = (df['ma5'].iloc[i] / df['ma10'].iloc[i] - 1) * 100
        if ma_ratio < -3: score += 20
        elif ma_ratio > 5: score -= 25
        
        if score >= 75 and not in_pos:
            shares = int(cash * 0.95 / close / 100) * 100
            if shares >= 100:
                cash -= shares * close * 1.001
                pos = shares
                in_pos = True
                buy_price = close
                trades.append('B')
        elif score <= 35 and in_pos:
            cash += pos * close * 0.999
            trades.append('S')
            pos = 0
            in_pos = False
        
        values.append(cash + pos * close if in_pos else cash)
    
    if in_pos:
        cash += pos * df['close'].iloc[-1] * 0.999
    
    ret = (cash - 100000) / 100000
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 and rets.std() > 0 else 0
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    return {'return': ret, 'sharpe': sharpe, 'drawdown': max_dd, 'trades': len([t for t in trades if t == 'S'])}


def simulate_v2(df):
    """V2 优化策略"""
    if len(df) < 60:
        return None
    
    df = df.copy()
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['roc5'] = df['close'].pct_change(5)
    df['roc10'] = df['close'].pct_change(10)
    df['vol10'] = df['close'].rolling(10).std() / df['close']
    
    low_5 = df['low'].rolling(5).min()
    high_5 = df['high'].rolling(5).max()
    df['rsv5'] = (df['close'] - low_5) / (high_5 - low_5 + 1e-12)
    
    cash = 100000
    pos = 0
    in_pos = False
    buy_price = 0
    values = []
    trades = []
    stop_count = 0
    profit_count = 0
    
    for i in range(25, len(df)):
        close = df['close'].iloc[i]
        
        # 止损止盈
        if in_pos:
            pnl = (close - buy_price) / buy_price
            if pnl <= -0.10:
                cash += pos * close * 0.999
                trades.append('SL')
                stop_count += 1
                pos = 0
                in_pos = False
            elif pnl >= 0.30:
                cash += pos * close * 0.999
                trades.append('TP')
                profit_count += 1
                pos = 0
                in_pos = False
        
        score = 50
        if df['rsv5'].iloc[i] < 0.15: score += 30
        elif df['rsv5'].iloc[i] > 0.85: score -= 30
        if df['roc10'].iloc[i] < -0.08: score += 35
        elif df['roc10'].iloc[i] > 0.08: score -= 35
        if df['roc5'].iloc[i] < -0.06: score += 20
        elif df['roc5'].iloc[i] > 0.06: score -= 20
        if df['vol10'].iloc[i] > 0.06: score += 25
        
        ma_ratio = (df['ma5'].iloc[i] / df['ma10'].iloc[i] - 1) * 100
        if ma_ratio < -2: score += 25
        elif ma_ratio > 4: score -= 25
        
        if score >= 70 and not in_pos:
            shares = int(cash * 0.95 / close / 100) * 100
            if shares >= 100:
                cash -= shares * close * 1.001
                pos = shares
                in_pos = True
                buy_price = close
                trades.append('B')
        elif score <= 40 and in_pos:
            cash += pos * close * 0.999
            trades.append('S')
            pos = 0
            in_pos = False
        
        values.append(cash + pos * close if in_pos else cash)
    
    if in_pos:
        cash += pos * df['close'].iloc[-1] * 0.999
    
    ret = (cash - 100000) / 100000
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 and rets.std() > 0 else 0
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    return {
        'return': ret, 'sharpe': sharpe, 'drawdown': max_dd,
        'trades': len([t for t in trades if t in ['S', 'SL', 'TP']]),
        'stop_losses': stop_count, 'take_profits': profit_count,
    }


def simulate_v3(df, industry):
    """V3 修复冲突版"""
    from bobquant_v2.strategy.enhanced_strategy_v3 import EnhancedStrategyV3, get_market_adjustment
    
    if len(df) < 60:
        return None
    
    strategy = EnhancedStrategyV3()
    
    df = df.copy()
    
    cash = 100000
    pos = 0
    in_pos = False
    buy_price = 0
    buy_date = None
    values = []
    trades = []
    stop_count = 0
    profit_count = 0
    
    for i in range(25, len(df)):
        date = df.index[i]
        close = df['close'].iloc[i]
        
        # 持仓信息
        position = None
        if in_pos:
            pnl = (close - buy_price) / buy_price
            days = (date - buy_date).days
            position = {'code': 'test', 'pnl': pnl, 'days': days}
        
        # 止损止盈 (动态)
        if in_pos:
            stop, reason = strategy.check_stop_loss(buy_price, close, position['days'])
            if stop:
                cash += pos * close * 0.999
                trades.append(reason)
                if reason == 'stop_loss': stop_count += 1
                elif reason == 'take_profit': profit_count += 1
                pos = 0
                in_pos = False
        
        # 生成信号 (V3)
        try:
            signal = strategy.analyze('test', 'test', df.iloc[:i+1].copy(), {'current': close}, industry, position)
        except:
            continue
        
        from bobquant_v2.strategy.factor_strategy import SignalType
        if signal.signal in [SignalType.BUY, SignalType.STRONG_BUY] and not in_pos:
            shares = int(cash * 0.95 / close / 100) * 100
            if shares >= 100:
                cash -= shares * close * 1.001
                pos = shares
                in_pos = True
                buy_price = close
                buy_date = date
                trades.append('B')
        
        values.append(cash + pos * close if in_pos else cash)
    
    if in_pos:
        cash += pos * df['close'].iloc[-1] * 0.999
    
    ret = (cash - 100000) / 100000
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 and rets.std() > 0 else 0
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    return {
        'return': ret, 'sharpe': sharpe, 'drawdown': max_dd,
        'trades': len([t for t in trades if t in ['S', 'stop_loss', 'take_profit']]),
        'stop_losses': stop_count, 'take_profits': profit_count,
    }


def backtest_year(year):
    """回测某年"""
    print(f"\n{'='*80}")
    print(f"回测 {year} 年")
    print(f"{'='*80}")
    
    results = []
    
    for i, (code, name, industry) in enumerate(STOCK_POOL, 1):
        print(f"[{i:2d}/15] {name:<10}...", end=' ')
        
        df = get_data(code, year)
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        v1 = simulate_v1(df)
        v2 = simulate_v2(df)
        v3 = simulate_v3(df, industry)
        
        if v1 and v2 and v3:
            results.append({
                'code': code, 'name': name, 'industry': industry,
                'v1_ret': v1['return'], 'v2_ret': v2['return'], 'v3_ret': v3['return'],
                'v1_sharpe': v1['sharpe'], 'v2_sharpe': v2['sharpe'], 'v3_sharpe': v3['sharpe'],
                'v1_dd': v1['drawdown'], 'v2_dd': v2['drawdown'], 'v3_dd': v3['drawdown'],
                'v1_trades': v1['trades'], 'v2_trades': v2['trades'], 'v3_trades': v3['trades'],
                'v2_stops': v2['stop_losses'], 'v3_stops': v3['stop_losses'],
                'v2_profits': v2['take_profits'], 'v3_profits': v3['take_profits'],
            })
            
            v1_str = f"{v1['return']*100:+6.1f}%"
            v2_str = f"{v2['return']*100:+6.1f}%"
            v3_str = f"{v3['return']*100:+6.1f}%"
            
            # 标记最佳
            best = max(v1['return'], v2['return'], v3['return'])
            markers = []
            if v1['return'] == best: markers.append('V1')
            if v2['return'] == best: markers.append('V2')
            if v3['return'] == best: markers.append('V3⭐')
            
            print(f"V1:{v1_str} V2:{v2_str} V3:{v3_str} {'['+','.join(markers)+']'}")
        else:
            print("❌ 失败")
    
    return results


def analyze(all_results):
    """分析结果"""
    report = {
        'title': 'V3 策略回测对比 (V1 vs V2 vs V3)',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'years': {},
        'summary': {},
    }
    
    all_v1, all_v2, all_v3 = [], [], []
    
    for year, results in all_results.items():
        df = pd.DataFrame(results)
        
        stats = {
            'count': len(results),
            'v1_avg': df['v1_ret'].mean(),
            'v2_avg': df['v2_ret'].mean(),
            'v3_avg': df['v3_ret'].mean(),
            'v1_sharpe': df['v1_sharpe'].mean(),
            'v2_sharpe': df['v2_sharpe'].mean(),
            'v3_sharpe': df['v3_sharpe'].mean(),
            'v1_dd': df['v1_dd'].mean(),
            'v2_dd': df['v2_dd'].mean(),
            'v3_dd': df['v3_dd'].mean(),
            'v1_trades': df['v1_trades'].mean(),
            'v2_trades': df['v2_trades'].mean(),
            'v3_trades': df['v3_trades'].mean(),
            'v2_total_stops': df['v2_stops'].sum(),
            'v3_total_stops': df['v3_stops'].sum(),
            'v2_total_profits': df['v2_profits'].sum(),
            'v3_total_profits': df['v3_profits'].sum(),
        }
        
        # 胜率
        stats['v1_win'] = len([r for r in results if r['v1_ret'] > 0]) / len(results)
        stats['v2_win'] = len([r for r in results if r['v2_ret'] > 0]) / len(results)
        stats['v3_win'] = len([r for r in results if r['v3_ret'] > 0]) / len(results)
        
        # 改进
        stats['v2_improve'] = stats['v2_avg'] - stats['v1_avg']
        stats['v3_improve'] = stats['v3_avg'] - stats['v1_avg']
        stats['v3_vs_v2'] = stats['v3_avg'] - stats['v2_avg']
        
        report['years'][year] = {'stats': stats, 'results': results}
        
        all_v1.extend(df['v1_ret'].tolist())
        all_v2.extend(df['v2_ret'].tolist())
        all_v3.extend(df['v3_ret'].tolist())
    
    # 汇总
    report['summary'] = {
        'total': len(all_v1),
        'v1_avg': np.mean(all_v1),
        'v2_avg': np.mean(all_v2),
        'v3_avg': np.mean(all_v3),
        'v1_win': len([r for r in all_v1 if r > 0]) / len(all_v1),
        'v2_win': len([r for r in all_v2 if r > 0]) / len(all_v2),
        'v3_win': len([r for r in all_v3 if r > 0]) / len(all_v3),
    }
    
    return report


def save_report(report):
    """保存报告"""
    md = f"""# V3 策略回测对比 (V1 vs V2 vs V3)

**生成时间**: {report['time']}

---

## 📊 总体对比

| 指标 | V1 (原策略) | V2 (优化) | V3 (修复) | V3 改进 |
|------|:----------:|:--------:|:--------:|:------:|
| 平均收益 | {report['summary']['v1_avg']*100:.2f}% | {report['summary']['v2_avg']*100:.2f}% | **{report['summary']['v3_avg']*100:.2f}%** | - |
| 胜率 | {report['summary']['v1_win']*100:.1f}% | {report['summary']['v2_win']*100:.1f}% | **{report['summary']['v3_win']*100:.1f}%** | - |
| 样本数 | {report['summary']['total']} | {report['summary']['total']} | {report['summary']['total']} | - |

---

## 📈 分年对比

"""
    
    for year in sorted(report['years'].keys()):
        s = report['years'][year]['stats']
        
        md += f"""### {year} 年

| 指标 | V1 | V2 | V3 | 最佳 |
|------|:---:|:---:|:---:|:----:|
| 平均收益 | {s['v1_avg']*100:.2f}% | {s['v2_avg']*100:.2f}% | **{s['v3_avg']*100:.2f}%** | V{s['v3_avg']>=max(s['v1_avg'],s['v2_avg']) and '3' or ('2' if s['v2_avg']>s['v1_avg'] else '1')} |
| 胜率 | {s['v1_win']*100:.1f}% | {s['v2_win']*100:.1f}% | **{s['v3_win']*100:.1f}%** | - |
| 夏普比率 | {s['v1_sharpe']:.2f} | {s['v2_sharpe']:.2f} | **{s['v3_sharpe']:.2f}** | - |
| 最大回撤 | {s['v1_dd']*100:.2f}% | {s['v2_dd']*100:.2f}% | **{s['v3_dd']*100:.2f}%** | - |
| 平均交易 | {s['v1_trades']:.1f} | {s['v2_trades']:.1f} | **{s['v3_trades']:.1f}** | - |
| 止损次数 | - | {s['v2_total_stops']} | {s['v3_total_stops']} | - |
| 止盈次数 | - | {s['v2_total_profits']} | {s['v3_total_profits']} | - |

---

"""
    
    md += f"""## 💡 V3 修复内容

### 修复的逻辑冲突

1. **Volatility 逻辑错误** 
   - V2: `if vol>6: +25; elif vol>12: +10` (第二个条件永不执行)
   - V3: `if 6<vol≤12: +20; elif vol>12: -15` (正确区分)

2. **市场状态被覆盖**
   - V2: `self.market_state` 被每只股票覆盖
   - V3: 全局 `GLOBAL_MARKET_STATE` 独立计算

3. **RSV5 vs ROC10 冗余**
   - V2: RSV5(+30) + ROC10(+35) + ROC5(+20) = 85 分重复计算
   - V3: 移除 ROC5，RSV5/ROC10 各 +25 分

4. **行业权重无效**
   - V2: 缩放分数无法逆转强信号
   - V3: 调整行业阈值 (白酒 70→75)

5. **缺少持仓检查**
   - V2: 可能越跌越买
   - V3: 亏损>5% 禁止加仓

### 新增功能

- **动态止损止盈**: 根据持仓天数调整阈值
- **全局市场状态**: 独立计算，不被单只股票影响
- **行业阈值**: 不同行业不同买卖门槛

---

_生成：{report['time']}_
"""
    
    path = OUTPUT_DIR / 'v3_backtest_comparison.md'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return path


if __name__ == '__main__':
    print("\n" + "="*80)
    print("V3 策略回测对比 (V1 vs V2 vs V3)")
    print("="*80)
    
    results = {}
    for year in YEARS:
        results[year] = backtest_year(year)
    
    print("\n生成报告...")
    report = analyze(results)
    path = save_report(report)
    
    s = report['summary']
    print(f"\n{'='*80}")
    print("对比摘要")
    print(f"{'='*80}")
    print(f"V1 平均：{s['v1_avg']*100:.2f}% (胜率 {s['v1_win']*100:.1f}%)")
    print(f"V2 平均：{s['v2_avg']*100:.2f}% (胜率 {s['v2_win']*100:.1f}%)")
    print(f"V3 平均：{s['v3_avg']*100:.2f}% (胜率 {s['v3_win']*100:.1f}%)")
    print(f"\n报告：{path}")
    print("✅ 完成!\n")
