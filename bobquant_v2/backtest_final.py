"""
QuantaAlpha 三年回测 - 最终版
修复数据问题，生成完整报告
"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import pandas as pd
import numpy as np
from datetime import datetime
import yaml
import json
from pathlib import Path
import baostock as bs

OUTPUT_DIR = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 股票池 (硬编码，避免 YAML 问题)
STOCK_POOL = [
    {'code': 'sh.600036', 'name': '招商银行', 'industry': '银行'},
    {'code': 'sh.601398', 'name': '工商银行', 'industry': '银行'},
    {'code': 'sh.601288', 'name': '农业银行', 'industry': '银行'},
    {'code': 'sh.601318', 'name': '中国平安', 'industry': '保险'},
    {'code': 'sh.601688', 'name': '华泰证券', 'industry': '证券'},
    {'code': 'sh.600519', 'name': '贵州茅台', 'industry': '白酒'},
    {'code': 'sh.000858', 'name': '五粮液', 'industry': '白酒'},
    {'code': 'sz.000568', 'name': '泸州老窖', 'industry': '白酒'},
    {'code': 'sh.600809', 'name': '山西汾酒', 'industry': '白酒'},
    {'code': 'sz.002415', 'name': '海康威视', 'industry': '科技'},
    {'code': 'sh.601138', 'name': '工业富联', 'industry': '科技'},
    {'code': 'sz.002371', 'name': '北方华创', 'industry': '半导体'},
    {'code': 'sh.603986', 'name': '兆易创新', 'industry': '半导体'},
    {'code': 'sh.603501', 'name': '韦尔股份', 'industry': '半导体'},
    {'code': 'sz.300750', 'name': '宁德时代', 'industry': '新能源'},
    {'code': 'sz.002594', 'name': '比亚迪', 'industry': '新能源'},
    {'code': 'sh.601012', 'name': '隆基绿能', 'industry': '光伏'},
    {'code': 'sz.002460', 'name': '赣锋锂业', 'industry': '锂业'},
    {'code': 'sz.002812', 'name': '恩捷股份', 'industry': '锂电'},
    {'code': 'sh.600276', 'name': '恒瑞医药', 'industry': '医药'},
    {'code': 'sz.300760', 'name': '迈瑞医疗', 'industry': '医疗'},
    {'code': 'sh.600436', 'name': '片仔癀', 'industry': '中药'},
    {'code': 'sh.603259', 'name': '药明康德', 'industry': 'CXO'},
    {'code': 'sz.000333', 'name': '美的集团', 'industry': '家电'},
    {'code': 'sz.000651', 'name': '格力电器', 'industry': '家电'},
    {'code': 'sh.600690', 'name': '海尔智家', 'industry': '家电'},
    {'code': 'sh.600887', 'name': '伊利股份', 'industry': '食品'},
    {'code': 'sh.601899', 'name': '紫金矿业', 'industry': '有色'},
    {'code': 'sh.601088', 'name': '中国神华', 'industry': '煤炭'},
    {'code': 'sh.600028', 'name': '中国石化', 'industry': '石化'},
]

YEARS = [2023, 2024, 2025]


def get_data(code, year):
    """获取某年数据"""
    lg = bs.login()
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=start, end_date=end, frequency="d"
    )
    
    data = []
    while (rs.error_code == '0') and rs.next():
        data.append(rs.get_row_data())
    
    bs.logout()
    
    if len(data) < 50:
        return None
    
    df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    
    # 安全转换类型
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    return df


def simulate(df):
    """简化模拟交易"""
    if len(df) < 60:
        return None
    
    # 计算简单指标
    df = df.copy()
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ROC
    df['roc5'] = df['close'].pct_change(5)
    df['roc10'] = df['close'].pct_change(10)
    
    # 波动率
    df['vol10'] = df['close'].rolling(10).std() / df['close']
    
    # RSV
    low_5 = df['low'].rolling(5).min()
    high_5 = df['high'].rolling(5).max()
    df['rsv5'] = (df['close'] - low_5) / (high_5 - low_5 + 1e-12)
    
    # 模拟
    cash = 100000
    pos = 0
    in_pos = False
    buy_price = 0
    trades = []  # 记录交易类型 'B'或'S'
    trade_profits = []  # 记录每笔交易的盈亏
    values = []
    
    for i in range(25, len(df)):
        close = df['close'].iloc[i]
        
        # 打分
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
        
        # 交易
        if score >= 75 and not in_pos:
            shares = int(cash * 0.95 / close / 100) * 100
            if shares >= 100:
                cash -= shares * close * 1.001
                pos = shares
                in_pos = True
                buy_price = close
                trades.append('B')
        
        elif score <= 35 and in_pos:
            profit = (close - buy_price) * pos
            cash += pos * close * 0.999
            trade_profits.append(profit)  # 记录盈亏
            trades.append('S')
            pos = 0
            in_pos = False
        
        values.append(cash + pos * close if in_pos else cash)
    
    # 平仓
    if in_pos:
        cash += pos * df['close'].iloc[-1] * 0.999
    
    ret = (cash - 100000) / 100000
    
    # 胜率（根据实际交易记录计算）
    sells = len([t for t in trades if t == 'S'])
    wins = len([p for p in trade_profits if p > 0])
    win_rate = wins / sells if sells > 0 else 0.0
    
    # 夏普
    vals = pd.Series(values)
    rets = vals.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if len(rets) > 10 and rets.std() > 0 else 0
    
    # 回撤
    roll_max = vals.expanding().max()
    dd = (vals - roll_max) / roll_max
    max_dd = abs(dd.min()) if len(dd) > 0 else 0
    
    return {
        'return': ret,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'drawdown': max_dd,
        'trades': sells,
    }


def backtest_year(year):
    print(f"\n{'='*60}")
    print(f"回测 {year} 年")
    print(f"{'='*60}")
    
    results = []
    
    for i, stock in enumerate(STOCK_POOL, 1):
        code = stock['code']
        name = stock['name']
        
        print(f"[{i:2d}/30] {name:<10}...", end=' ')
        
        df = get_data(code, year)
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        res = simulate(df)
        
        if res:
            results.append({
                'code': code,
                'name': name,
                'industry': stock['industry'],
                **res
            })
            print(f"收益 {res['return']*100:+6.1f}%")
        else:
            print("❌ 失败")
    
    return results


def analyze(all_results):
    report = {
        'title': 'QuantaAlpha 增强策略三年回测报告 (2023-2025)',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'years': {},
        'summary': {},
    }
    
    all_ret = []
    
    for year, results in all_results.items():
        if not results:
            continue
        
        df = pd.DataFrame(results)
        
        stats = {
            'count': len(results),
            'profitable': len([r for r in results if r['return'] > 0]),
            'avg_ret': df['return'].mean(),
            'median_ret': df['return'].median(),
            'best': df['return'].max(),
            'worst': df['return'].min(),
            'avg_wr': df['win_rate'].mean(),
            'avg_sharpe': df['sharpe'].mean(),
            'avg_dd': df['drawdown'].mean(),
        }
        
        top5 = df.nlargest(5, 'return')[['code', 'name', 'return', 'win_rate', 'sharpe']].to_dict('records')
        bot5 = df.nsmallest(5, 'return')[['code', 'name', 'return', 'win_rate', 'sharpe']].to_dict('records')
        
        report['years'][year] = {'stats': stats, 'top5': top5, 'bot5': bot5, 'results': results}
        all_ret.extend(df['return'].tolist())
    
    report['summary'] = {
        'total': len(all_ret),
        'positive': len([r for r in all_ret if r > 0]) / len(all_ret) if all_ret else 0,
        'avg_ret': np.mean(all_ret),
        'median_ret': np.median(all_ret),
        'best': max(all_ret) if all_ret else 0,
        'worst': min(all_ret) if all_ret else 0,
    }
    
    return report


def save_md(report):
    md = f"""# QuantaAlpha 增强策略三年回测报告 (2023-2025)

**生成时间**: {report['time']}

---

## 📊 总体表现

| 指标 | 数值 |
|------|------|
| 回测年份 | 2023, 2024, 2025 |
| 股票池 | 30 只龙头股 |
| 总样本 | {report['summary']['total']} 股·年 |
| 正收益比 | {report['summary']['positive']*100:.1f}% |
| **平均收益** | **{report['summary']['avg_ret']*100:.2f}%** |
| 中位收益 | {report['summary']['median_ret']*100:.2f}% |
| 最佳股票 | {report['summary']['best']*100:.2f}% |
| 最差股票 | {report['summary']['worst']*100:.2f}% |

---

## 📈 分年表现

"""
    for year in sorted(report['years'].keys()):
        yd = report['years'][year]
        s = yd['stats']
        
        md += f"""### {year} 年

| 指标 | 数值 |
|------|------|
| 股票数 | {s['count']} |
| 盈利 | {s['profitable']} ({s['profitable']/s['count']*100:.1f}%) |
| **平均收益** | **{s['avg_ret']*100:.2f}%** |
| 最佳 | {s['best']*100:.2f}% |
| 最差 | {s['worst']*100:.2f}% |

#### Top 5

| # | 代码 | 名称 | 收益 | 胜率 | 夏普 |
|---|------|------|------|------|------|
"""
        for i, st in enumerate(yd['top5'], 1):
            md += f"| {i} | {st['code']} | {st['name']} | {st['return']*100:.2f}% | {st['win_rate']*100:.1f}% | {st['sharpe']:.2f} |\n"
        
        md += "\n#### Bottom 5\n\n| # | 代码 | 名称 | 收益 | 胜率 | 夏普 |\n|---|---|---|---|---|---|\n"
        for i, st in enumerate(yd['bot5'], 1):
            md += f"| {i} | {st['code']} | {st['name']} | {st['return']*100:.2f}% | {st['win_rate']*100:.1f}% | {st['sharpe']:.2f} |\n"
        
        md += "\n---\n\n"
    
    md += """## 💡 策略说明

### QuantaAlpha 因子

1. **RSV5** (胜率 79%) - 超买超卖
2. **ROC10** (IC=-0.34) - 均值回归
3. **ROC5** (IC=-0.16) - 短期反向
4. **Volatility10** (IC=+0.19) - 波动率
5. **MA_Ratio** (IC=-0.31) - 均线偏离

### 信号

- **买入**: 评分 ≥ 75
- **卖出**: 评分 ≤ 35

---

_生成：{report['time']}_
"""
    
    path = OUTPUT_DIR / 'backtest_2023_2025.md'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return path


if __name__ == '__main__':
    print("\n" + "="*60)
    print("QuantaAlpha 三年回测 (2023-2025)")
    print("="*60)
    
    results = {}
    for year in YEARS:
        results[year] = backtest_year(year)
    
    print("\n生成报告...")
    report = analyze(results)
    path = save_md(report)
    
    s = report['summary']
    print(f"\n{'='*60}")
    print("摘要")
    print(f"{'='*60}")
    print(f"样本：{s['total']} 股·年")
    print(f"正收益：{s['positive']*100:.1f}%")
    print(f"平均收益：{s['avg_ret']*100:.2f}%")
    print(f"最佳：{s['best']*100:.2f}%")
    print(f"最差：{s['worst']*100:.2f}%")
    print(f"\n报告：{path}")
    print("✅ 完成!\n")
