"""
QuantaAlpha 增强策略三年回测 - 快速版
使用简化逻辑，快速生成结果
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
from bobquant_v2.indicator.technical import all_indicators
from bobquant_v2.indicator.qa_parser import compute_alpha158_20


# ===== 配置 =====
STOCK_POOL_PATH = '/home/openclaw/.openclaw/workspace/quant_strategies/bobquant/config/stock_pool_30_top.yaml'
OUTPUT_DIR = Path('/home/openclaw/.openclaw/workspace/quant_strategies/backtest_results')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [2023, 2024, 2025]


def load_stock_pool():
    with open(STOCK_POOL_PATH, 'r', encoding='utf-8') as f:
        pool = yaml.safe_load(f)
    return pool


def get_data_for_years(code, years):
    """一次性获取多年数据"""
    lg = bs.login()
    
    all_data = []
    for year in years:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=start_date, end_date=end_date, frequency="d"
        )
        
        while (rs.error_code == '0') and rs.next():
            row = rs.get_row_data()
            row[0] = datetime.strptime(row[0], '%Y-%m-%d')
            all_data.append(row)
    
    bs.logout()
    
    if len(all_data) < 200:
        return None
    
    df = pd.DataFrame(all_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df = df.astype({'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
    df = df.set_index('date').sort_index()
    
    return df


def simulate_trading(df, year):
    """
    简化版交易模拟
    基于 QuantaAlpha 因子打分
    """
    # 筛选该年数据
    df_year = df[(df.index.year == year)]
    
    if len(df_year) < 50:
        return None
    
    # 计算指标
    df_year = df_year.copy()
    df_year = all_indicators(df_year)
    df_year = compute_alpha158_20(df_year)
    
    # 模拟交易
    cash = 100000
    position = 0
    in_position = False
    buy_price = 0
    trades = []
    daily_values = []
    
    for i in range(20, len(df_year)):
        close = df_year['close'].iloc[i]
        
        # 计算 QuantaAlpha 打分
        score = 50
        
        # RSV5 (权重 25)
        if 'qa_rsv5' in df_year.columns:
            rsv5 = df_year['qa_rsv5'].iloc[i]
            if rsv5 < 0.2: score += 25
            elif rsv5 > 0.8: score -= 25
        
        # ROC10 (权重 30)
        if 'qa_roc10' in df_year.columns:
            roc10 = df_year['qa_roc10'].iloc[i] * 100
            if roc10 < -10: score += 30
            elif roc10 > 10: score -= 30
        
        # ROC5 (权重 15)
        if 'qa_roc5' in df_year.columns:
            roc5 = df_year['qa_roc5'].iloc[i] * 100
            if roc5 < -8: score += 15
            elif roc5 > 8: score -= 15
        
        # Volatility10 (权重 20)
        if 'qa_volatility10' in df_year.columns:
            vol10 = df_year['qa_volatility10'].iloc[i] * 100
            if vol10 > 8: score += 20
        
        # MA_Ratio (权重 20)
        if 'qa_ma_ratio5_10' in df_year.columns:
            ma_ratio = df_year['qa_ma_ratio5_10'].iloc[i] * 100
            if ma_ratio < -3: score += 20
            elif ma_ratio > 5: score -= 25
        
        # 交易信号
        if score >= 75 and not in_position:
            # 买入
            shares = int(cash * 0.95 / close / 100) * 100
            if shares >= 100:
                cash -= shares * close * 1.001
                position = shares
                in_position = True
                buy_price = close
                trades.append({'type': 'buy', 'price': close, 'score': score})
        
        elif score <= 35 and in_position:
            # 卖出
            profit = (close - buy_price) * position
            cash += position * close * 0.999
            trades.append({'type': 'sell', 'price': close, 'profit': profit})
            position = 0
            in_position = False
        
        # 账户价值
        if in_position:
            daily_value = cash + position * close
        else:
            daily_value = cash
        daily_values.append(daily_value)
    
    # 期末平仓
    if in_position:
        final_close = df_year['close'].iloc[-1]
        cash += position * final_close * 0.999
        trades.append({'type': 'sell', 'price': final_close})
    
    # 计算收益
    total_return = (cash - 100000) / 100000
    
    # 胜率
    sell_trades = [t for t in trades if t['type'] == 'sell' and 'profit' in t]
    win_trades = [t for t in sell_trades if t['profit'] > 0]
    win_rate = len(win_trades) / len(sell_trades) if sell_trades else 0
    
    # 夏普比率
    dv_series = pd.Series(daily_values)
    daily_returns = dv_series.pct_change().dropna()
    if len(daily_returns) > 10 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0
    
    # 最大回撤
    rolling_max = dv_series.expanding().max()
    drawdown = (dv_series - rolling_max) / rolling_max
    max_dd = abs(drawdown.min()) if len(drawdown) > 0 else 0
    
    return {
        'total_return': total_return,
        'win_rate': win_rate,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'num_trades': len([t for t in trades if t['type'] == 'sell']),
    }


def backtest_year(year, stock_pool):
    """回测某一年"""
    print(f"\n{'='*60}")
    print(f"回测 {year} 年")
    print(f"{'='*60}")
    
    results = []
    
    for i, stock in enumerate(stock_pool, 1):
        code = stock['code']
        name = stock['name']
        
        print(f"[{i:2d}/30] {name:<10} ({code})...", end=' ')
        
        # 获取数据
        df = get_data_for_years(code, [year])
        
        if df is None:
            print("⚠️ 数据不足")
            continue
        
        # 模拟交易
        result = simulate_trading(df, year)
        
        if result:
            results.append({
                'code': code,
                'name': name,
                'industry': stock.get('industry', ''),
                **result
            })
            print(f"收益 {result['total_return']*100:+6.1f}%, 胜率 {result['win_rate']*100:5.1f}%")
        else:
            print("❌ 模拟失败")
    
    return results


def analyze_results(all_results):
    """分析回测结果"""
    report = {
        'title': 'QuantaAlpha 增强策略三年回测报告 (2023-2025)',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'years': {},
        'summary': {},
    }
    
    all_returns = []
    all_win_rates = []
    all_sharpes = []
    all_drawdowns = []
    
    for year, results in all_results.items():
        if not results:
            continue
        
        df = pd.DataFrame(results)
        
        stats = {
            'total_stocks': len(results),
            'profitable': len([r for r in results if r['total_return'] > 0]),
            'avg_return': df['total_return'].mean(),
            'median_return': df['total_return'].median(),
            'best_return': df['total_return'].max(),
            'worst_return': df['total_return'].min(),
            'avg_win_rate': df['win_rate'].mean(),
            'avg_sharpe': df['sharpe_ratio'].mean(),
            'avg_drawdown': df['max_drawdown'].mean(),
            'avg_trades': df['num_trades'].mean(),
        }
        
        # Top 5
        top5 = df.nlargest(5, 'total_return')[['code', 'name', 'total_return', 'win_rate', 'sharpe_ratio']].to_dict('records')
        bottom5 = df.nsmallest(5, 'total_return')[['code', 'name', 'total_return', 'win_rate', 'sharpe_ratio']].to_dict('records')
        
        report['years'][year] = {
            'stats': stats,
            'top5': top5,
            'bottom5': bottom5,
            'results': results,
        }
        
        # 汇总
        all_returns.extend(df['total_return'].tolist())
        all_win_rates.extend(df['win_rate'].tolist())
        all_sharpes.extend(df['sharpe_ratio'].tolist())
        all_drawdowns.extend(df['max_drawdown'].tolist())
    
    # 总体统计
    report['summary'] = {
        'total_samples': len(all_returns),
        'positive_ratio': len([r for r in all_returns if r > 0]) / len(all_returns) if all_returns else 0,
        'avg_return': np.mean(all_returns),
        'median_return': np.median(all_returns),
        'avg_win_rate': np.mean(all_win_rates),
        'avg_sharpe': np.mean(all_sharpes),
        'avg_drawdown': np.mean(all_drawdowns),
        'best_stock': max(all_returns) if all_returns else 0,
        'worst_stock': min(all_returns) if all_returns else 0,
    }
    
    return report


def save_report(report):
    """保存报告"""
    # JSON
    def convert_numpy(obj):
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj) if isinstance(obj, np.floating) else int(obj)
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(v) for v in obj]
        return obj
    
    report_clean = convert_numpy(report)
    
    json_path = OUTPUT_DIR / 'quantaalpha_3year_backtest.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_clean, f, ensure_ascii=False, indent=2)
    
    # Markdown
    md_path = OUTPUT_DIR / 'quantaalpha_3year_backtest.md'
    md = generate_markdown(report)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return json_path, md_path


def generate_markdown(report):
    """生成 Markdown 报告"""
    md = f"""# QuantaAlpha 增强策略三年回测报告 (2023-2025)

**生成时间**: {report['generated_at']}

---

## 📊 总体表现

| 指标 | 数值 |
|------|------|
| 回测年份 | 2023, 2024, 2025 |
| 股票池 | 30 只龙头股 |
| 总样本数 | {report['summary']['total_samples']} 股·年 |
| 正收益比例 | {report['summary']['positive_ratio']*100:.1f}% |
| **平均总收益** | **{report['summary']['avg_return']*100:.2f}%** |
| 中位数收益 | {report['summary']['median_return']*100:.2f}% |
| 平均胜率 | {report['summary']['avg_win_rate']*100:.1f}% |
| 平均夏普比率 | {report['summary']['avg_sharpe']:.2f} |
| 平均最大回撤 | {report['summary']['avg_drawdown']*100:.2f}% |
| 最佳单股收益 | {report['summary']['best_stock']*100:.2f}% |
| 最差单股收益 | {report['summary']['worst_stock']*100:.2f}% |

---

## 📈 分年表现

"""
    
    for year in sorted(report['years'].keys()):
        year_data = report['years'][year]
        stats = year_data['stats']
        
        md += f"""### {year} 年

| 指标 | 数值 |
|------|------|
| 测试股票数 | {stats['total_stocks']} |
| 盈利股票 | {stats['profitable']} ({stats['profitable']/stats['total_stocks']*100:.1f}%) |
| **平均收益** | **{stats['avg_return']*100:.2f}%** |
| 中位数收益 | {stats['median_return']*100:.2f}% |
| 最佳收益 | {stats['best_return']*100:.2f}% |
| 最差收益 | {stats['worst_return']*100:.2f}% |
| 平均胜率 | {stats['avg_win_rate']*100:.1f}% |
| 平均夏普 | {stats['avg_sharpe']:.2f} |
| 平均回撤 | {stats['avg_drawdown']*100:.2f}% |
| 平均交易次数 | {stats['avg_trades']:.1f} |

#### 🏆 Top 5 股票

| 排名 | 代码 | 名称 | 总收益 | 胜率 | 夏普 |
|------|------|------|--------|------|------|
"""
        for i, s in enumerate(year_data['top5'], 1):
            md += f"| {i} | {s['code']} | {s['name']} | {s['total_return']*100:.2f}% | {s['win_rate']*100:.1f}% | {s['sharpe_ratio']:.2f} |\n"
        
        md += f"""
#### 📉 Bottom 5 股票

| 排名 | 代码 | 名称 | 总收益 | 胜率 | 夏普 |
|------|------|------|--------|------|------|
"""
        for i, s in enumerate(year_data['bottom5'], 1):
            md += f"| {i} | {s['code']} | {s['name']} | {s['total_return']*100:.2f}% | {s['win_rate']*100:.1f}% | {s['sharpe_ratio']:.2f} |\n"
        
        md += "\n---\n\n"
    
    # 年度对比
    md += """## 📊 年度对比

| 年份 | 平均收益 | 盈利比例 | 平均胜率 | 平均夏普 | 平均回撤 |
|------|----------|----------|----------|----------|----------|
"""
    for year in sorted(report['years'].keys()):
        stats = report['years'][year]['stats']
        md += f"| {year} | {stats['avg_return']*100:.2f}% | {stats['profitable']/stats['total_stocks']*100:.1f}% | {stats['avg_win_rate']*100:.1f}% | {stats['avg_sharpe']:.2f} | {stats['avg_drawdown']*100:.2f}% |\n"
    
    md += f"""
---

## 💡 策略分析

### QuantaAlpha 因子贡献

本次回测集成的 QuantaAlpha 因子:

1. **RSV5** (胜率 79%) - 超买超卖信号，±25 分
2. **ROC10** (IC=-0.34) - 均值回归信号，±30 分
3. **ROC5** (IC=-0.16) - 短期反向信号，±15 分
4. **Volatility10** (IC=+0.19) - 波动率溢价，+20 分
5. **MA_Ratio5_10** (IC=-0.31) - 均线偏离，±20/25 分

### 信号阈值

- **买入**: 综合评分 ≥ 75
- **卖出**: 综合评分 ≤ 35
- **基础分**: 50 分

### 优势

- ✅ 多因子综合打分，信号更可靠
- ✅ 融入均值回归逻辑，适合 A 股震荡市
- ✅ RSV 超买超卖胜率高达 79%
- ✅ 波动率因子捕捉风险溢价

### 风险提示

- ⚠️ 反向因子在强趋势市场可能失效
- ⚠️ 部分因子稳定性有待提高
- ⚠️ 需结合市场状态动态调整权重

---

## 📁 数据文件

- **JSON 数据**: `quantaalpha_3year_backtest.json`
- **Markdown 报告**: `quantaalpha_3year_backtest.md`

---

_报告生成时间：{report['generated_at']}_
_回测引擎：BobQuant V2 + QuantaAlpha 因子_
_数据来源：Baostock_
"""
    return md


if __name__ == '__main__':
    print("\n" + "="*60)
    print("QuantaAlpha 增强策略三年回测 (2023-2025)")
    print("简化快速版")
    print("="*60)
    
    # 加载股票池
    print("\n📊 加载股票池...")
    stock_pool = load_stock_pool()
    print(f"✅ 共 {len(stock_pool)} 只股票")
    
    # 按年回测
    all_results = {}
    
    for year in YEARS:
        results = backtest_year(year, stock_pool)
        all_results[year] = results
    
    # 生成报告
    print("\n" + "="*60)
    print("生成报告...")
    print("="*60)
    
    report = analyze_results(all_results)
    json_path, md_path = save_report(report)
    
    # 打印摘要
    print("\n" + "="*60)
    print("📊 回测摘要")
    print("="*60)
    
    s = report['summary']
    print(f"\n总样本数：{s['total_samples']} 股·年")
    print(f"正收益比例：{s['positive_ratio']*100:.1f}%")
    print(f"平均总收益：{s['avg_return']*100:.2f}%")
    print(f"平均胜率：{s['avg_win_rate']*100:.1f}%")
    print(f"平均夏普：{s['avg_sharpe']:.2f}")
    print(f"平均回撤：{s['avg_drawdown']*100:.2f}%")
    
    print("\n分年收益:")
    for year in sorted(report['years'].keys()):
        stats = report['years'][year]['stats']
        print(f"  {year}年：{stats['avg_return']*100:.2f}%")
    
    print("\n" + "="*60)
    print("✅ 回测完成！")
    print("="*60)
    print(f"\n报告位置:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    print()
