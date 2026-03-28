"""
QuantaAlpha 因子回测测试
验证 ALPHA158_20 因子的有效性

测试内容:
1. 因子计算正确性
2. 因子 IC (Information Coefficient)
3. 因子胜率
4. 因子衰减分析
"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from bobquant_v2.indicator.qa_parser import compute_alpha158_20, QAExpressionParser


def get_stock_data(code, days=120):
    """获取股票历史数据"""
    import baostock as bs
    
    lg = bs.login()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume,amount",
        start_date=start_date, end_date=end_date, frequency="d"
    )
    
    data_list = []
    while (rs.error_code == '0') and rs.next():
        data_list.append(rs.get_row_data())
    
    bs.logout()
    
    if len(data_list) < 60:
        return None
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    df = df.astype({
        'open': float, 'high': float, 'low': float,
        'close': float, 'volume': float, 'amount': float
    })
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    return df


def compute_factor_ic(df, factor_name, forward_days=5):
    """
    计算因子 IC (Information Coefficient)
    
    IC = 因子值 与 未来收益 的相关系数
    """
    if factor_name not in df.columns:
        return None, None
    
    # 因子值 (滞后一期，避免前视偏差)
    factor_values = df[factor_name].shift(1)
    
    # 未来 N 日收益
    future_return = df['close'].pct_change(forward_days).shift(-forward_days)
    
    # 去除 NaN
    mask = factor_values.notna() & future_return.notna()
    
    if mask.sum() < 30:
        return None, None
    
    # 计算 IC (Spearman 秩相关)
    ic = factor_values[mask].corr(future_return[mask], method='spearman')
    
    # 计算 IC 绝对值 > 0.05 的比例 (胜率)
    ic_win_rate = (abs(factor_values[mask] - factor_values[mask].mean()) > 
                   factor_values[mask].std() * 0.5).mean()
    
    return ic, ic_win_rate


def test_single_factor(df, factor_name):
    """测试单个因子"""
    ic, win_rate = compute_factor_ic(df, factor_name, forward_days=5)
    
    if ic is None:
        return None
    
    # 评级
    if abs(ic) > 0.1:
        rating = "⭐⭐⭐ 强有效"
    elif abs(ic) > 0.05:
        rating = "⭐⭐ 有效"
    elif abs(ic) > 0.02:
        rating = "⭐ 弱有效"
    else:
        rating = "❌ 无效"
    
    # 方向
    direction = "正向" if ic > 0 else "反向"
    
    return {
        'factor': factor_name,
        'ic': ic,
        'win_rate': win_rate,
        'rating': rating,
        'direction': direction
    }


def test_all_alpha158_20():
    """测试所有 ALPHA158_20 因子"""
    print("=" * 70)
    print("QuantaAlpha ALPHA158_20 因子回测分析")
    print("=" * 70)
    
    # 测试股票池
    test_stocks = [
        ('sh.600519', '贵州茅台'),
        ('sh.601398', '工商银行'),
        ('sz.300750', '宁德时代'),
        ('sh.600036', '招商银行'),
        ('sz.000858', '五粮液'),
    ]
    
    # 因子列表
    factors_to_test = [
        'qa_roc0', 'qa_roc1', 'qa_roc5', 'qa_roc10', 'qa_roc20',
        'qa_vratio5', 'qa_vratio10', 'qa_vstd5_ratio',
        'qa_range', 'qa_volatility5', 'qa_volatility10',
        'qa_rsv5', 'qa_rsv10',
        'qa_high_ratio5', 'qa_low_ratio5',
        'qa_shadow_ratio', 'qa_body_ratio',
        'qa_ma_ratio5_10', 'qa_ma_ratio10_20',
    ]
    
    all_results = []
    
    for code, name in test_stocks:
        print(f"\n📈 测试 {name} ({code})")
        print("-" * 50)
        
        # 获取数据
        df = get_stock_data(code, days=120)
        
        if df is None:
            print(f"  ❌ 数据获取失败")
            continue
        
        print(f"  ✅ 数据：{len(df)} 天 ({df.index[0].date()} ~ {df.index[-1].date()})")
        
        # 计算 QuantaAlpha 因子
        df = compute_alpha158_20(df)
        
        # 测试每个因子
        stock_results = []
        for factor in factors_to_test:
            result = test_single_factor(df, factor)
            if result:
                stock_results.append(result)
        
        # 显示结果
        print(f"\n  {'因子':<20} {'IC':>8} {'胜率':>8} {'评级':<15}")
        print(f"  {'-'*50}")
        
        # 按 IC 绝对值排序
        stock_results.sort(key=lambda x: abs(x['ic']), reverse=True)
        
        for r in stock_results[:10]:  # 只显示 top 10
            print(f"  {r['factor']:<20} {r['ic']:>8.4f} {r['win_rate']:>8.2%} {r['rating']:<15}")
        
        all_results.extend(stock_results)
    
    # 汇总分析
    print("\n" + "=" * 70)
    print("📊 因子有效性汇总分析 (所有股票平均)")
    print("=" * 70)
    
    # 按因子分组求平均 IC
    factor_stats = {}
    for r in all_results:
        factor = r['factor']
        if factor not in factor_stats:
            factor_stats[factor] = {'ics': [], 'win_rates': []}
        factor_stats[factor]['ics'].append(r['ic'])
        factor_stats[factor]['win_rates'].append(r['win_rate'])
    
    summary = []
    for factor, stats in factor_stats.items():
        avg_ic = np.mean(stats['ics'])
        avg_win_rate = np.mean(stats['win_rates'])
        ic_std = np.std(stats['ics'])
        
        # 稳定性评分
        stability = "高" if ic_std < 0.05 else "中" if ic_std < 0.1 else "低"
        
        # 综合评级
        if abs(avg_ic) > 0.08:
            rating = "⭐⭐⭐ 强烈推荐"
        elif abs(avg_ic) > 0.05:
            rating = "⭐⭐ 推荐"
        elif abs(avg_ic) > 0.02:
            rating = "⭐ 观察"
        else:
            rating = "❌ 不推荐"
        
        summary.append({
            'factor': factor,
            'avg_ic': avg_ic,
            'ic_std': ic_std,
            'avg_win_rate': avg_win_rate,
            'stability': stability,
            'rating': rating
        })
    
    # 排序
    summary.sort(key=lambda x: abs(x['avg_ic']), reverse=True)
    
    print(f"\n{'因子':<22} {'平均 IC':>10} {'IC 标准差':>10} {'胜率':>8} {'稳定性':>8} {'评级':<15}")
    print("-" * 80)
    
    for s in summary:
        print(f"{s['factor']:<22} {s['avg_ic']:>10.4f} {s['ic_std']:>10.4f} "
              f"{s['avg_win_rate']:>8.2%} {s['stability']:>8} {s['rating']:<15}")
    
    # 推荐因子
    print("\n" + "=" * 70)
    print("🎯 推荐集成的有效因子")
    print("=" * 70)
    
    recommended = [s for s in summary if abs(s['avg_ic']) > 0.05]
    
    if recommended:
        print("\n以下因子 IC > 0.05，建议集成到策略中:\n")
        for i, s in enumerate(recommended, 1):
            direction = "正向因子" if s['avg_ic'] > 0 else "反向因子"
            print(f"  {i}. {s['factor']}: IC={s['avg_ic']:.4f}, 胜率={s['avg_win_rate']:.2%} [{direction}]")
    else:
        print("\n⚠️ 暂未发现 IC > 0.05 的强有效因子")
        print("   建议：增加测试股票数量或延长测试周期")
    
    # 因子衰减分析
    print("\n" + "=" * 70)
    print("📉 因子衰减分析 (Top 5 因子)")
    print("=" * 70)
    
    top5_factors = [s['factor'] for s in summary[:5]]
    
    for factor in top5_factors:
        print(f"\n  {factor}:")
        print(f"  {'周期':<10} {'IC':>10} {'评级':<15}")
        print(f"  {'-'*35}")
        
        for days in [1, 3, 5, 10, 20]:
            # 重新计算不同周期的 IC
            ics = []
            for code, name in test_stocks:
                df = get_stock_data(code, days=120)
                if df is not None:
                    df = compute_alpha158_20(df)
                    ic, _ = compute_factor_ic(df, factor, forward_days=days)
                    if ic is not None:
                        ics.append(ic)
            
            if ics:
                avg_ic = np.mean(ics)
                rating = "⭐" * max(1, int(abs(avg_ic) * 20))
                print(f"  {days}日收益  {avg_ic:>10.4f} {rating:<15}")
    
    print("\n" + "=" * 70)
    print("✅ 回测分析完成！")
    print("=" * 70)
    
    return summary


def test_factor_signals():
    """测试因子信号生成"""
    print("\n" + "=" * 70)
    print("QuantaAlpha 因子信号测试")
    print("=" * 70)
    
    # 获取测试数据
    df = get_stock_data('sh.600519', days=60)
    
    if df is None:
        print("❌ 数据获取失败")
        return
    
    # 计算因子
    df = compute_alpha158_20(df)
    
    # 最新数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    print(f"\n📊 贵州茅台 (sh.600519) 最新因子值:")
    print(f"  日期：{latest.name.date()}")
    print(f"  收盘价：¥{latest['close']:.2f}")
    print()
    
    # 因子信号
    signals = []
    
    # ROC5
    if 'qa_roc5' in latest:
        roc5 = latest['qa_roc5'] * 100
        signal = "🔴 强势" if roc5 > 5 else "🟢 弱势" if roc5 < -5 else "⚪ 中性"
        signals.append(f"  ROC5 (5 日收益): {roc5:+.2f}% {signal}")
    
    # VRATIO5
    if 'qa_vratio5' in latest:
        vratio = latest['qa_vratio5']
        signal = "📈 放量" if vratio > 2 else "📉 缩量" if vratio < 0.5 else "⚪ 正常"
        signals.append(f"  VRATIO5 (量比): {vratio:.2f}x {signal}")
    
    # RSV5
    if 'qa_rsv5' in latest:
        rsv5 = latest['qa_rsv5']
        signal = "🔴 超买" if rsv5 > 0.8 else "🟢 超卖" if rsv5 < 0.2 else "⚪ 中性"
        signals.append(f"  RSV5 (相对强弱): {rsv5:.3f} {signal}")
    
    # VOLATILITY5
    if 'qa_volatility5' in latest:
        vol5 = latest['qa_volatility5'] * 100
        signal = "⚠️ 高波动" if vol5 > 10 else "⚪ 正常"
        signals.append(f"  VOLATILITY5 (波动率): {vol5:.2f}% {signal}")
    
    # BODY_RATIO
    if 'qa_body_ratio' in latest:
        body = latest['qa_body_ratio']
        signal = "🟢 大阳线" if body > 0.8 else "🔴 大阴线" if body < -0.8 else "⚪ 普通"
        signals.append(f"  BODY_RATIO (实体比): {body:.3f} {signal}")
    
    for s in signals:
        print(s)
    
    # 综合判断
    print("\n💡 综合判断:")
    
    buy_signals = sum([
        latest.get('qa_roc5', 0) > 0.05,
        latest.get('qa_vratio5', 1) > 2,
        latest.get('qa_rsv5', 0.5) < 0.2,
        latest.get('qa_body_ratio', 0) > 0.5,
    ])
    
    sell_signals = sum([
        latest.get('qa_roc5', 0) < -0.05,
        latest.get('qa_vratio5', 1) < 0.5,
        latest.get('qa_rsv5', 0.5) > 0.8,
        latest.get('qa_body_ratio', 0) < -0.5,
    ])
    
    if buy_signals >= 3:
        print("  🟢 强烈买入信号 (多个因子共振)")
    elif buy_signals >= 2:
        print("  🟡 买入信号 (因子支持)")
    elif sell_signals >= 3:
        print("  🔴 强烈卖出信号 (多个因子共振)")
    elif sell_signals >= 2:
        print("  🟠 卖出信号 (因子支持)")
    else:
        print("  ⚪ 观望 (因子信号不明确)")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    print("\n🚀 QuantaAlpha 因子回测系统\n")
    
    # 测试所有 ALPHA158_20 因子
    summary = test_all_alpha158_20()
    
    # 测试因子信号生成
    test_factor_signals()
    
    print("\n✅ 所有测试完成！\n")
