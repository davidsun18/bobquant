# -*- coding: utf-8 -*-
"""
批量回测工具 - 实战应用
一次性测试多只股票，自动选出最佳策略
"""

import pandas as pd
import numpy as np
import baostock as bs
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==================== 1. 股票池 ====================
STOCK_POOL = [
    # 银行
    ('sh.600000', '浦发银行'),
    ('sh.600036', '招商银行'),
    ('sh.601398', '工商银行'),
    
    # 白酒
    ('sh.600519', '贵州茅台'),
    ('sh.000858', '五粮液'),
    ('sz.000568', '泸州老窖'),
    
    # 科技
    ('sz.300750', '宁德时代'),
    ('sz.002594', '比亚迪'),
    ('sh.601138', '工业富联'),
    
    # 消费
    ('sh.600276', '恒瑞医药'),
    ('sz.000333', '美的集团'),
    ('sh.600887', '伊利股份'),
]

# ==================== 2. 获取数据 ====================
def get_stock_data(code, start_date, end_date):
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code,
        "date,open,high,low,close,volume",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    df = pd.DataFrame(data_list, columns=rs.fields)
    
    if len(df) == 0:
        bs.logout()
        return None
    
    df['close'] = df['close'].astype(float)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    bs.logout()
    return df

# ==================== 3. 计算 MACD ====================
def calculate_macd(df):
    df = df.copy()
    df['ma1'] = df['close'].rolling(window=12, min_periods=1).mean()
    df['ma2'] = df['close'].rolling(window=26, min_periods=1).mean()
    df['positions'] = np.where(df['ma1'] >= df['ma2'], 1, 0)
    return df

# ==================== 4. 计算布林带 ====================
def calculate_bollinger(df):
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['bb_std'] = df['close'].rolling(window=20, min_periods=1).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_positions'] = np.where(df['bb_percent_b'] < 0.2, 1, 0)
    return df

# ==================== 5. 回测统计 ====================
def backtest(df, positions_col):
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df[positions_col].shift(1) * df['returns']
    
    if len(df) < 2:
        return None
    
    total_return = (1 + df['strategy_returns']).prod() - 1
    buy_hold = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
    
    # 最大回撤
    cumulative = (1 + df['strategy_returns']).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_dd = drawdown.min()
    
    # 夏普比率
    excess = df['strategy_returns'] - 0.03/252
    sharpe = np.sqrt(252) * excess.mean() / excess.std() if excess.std() > 0 else 0
    
    return {
        'total_return': total_return,
        'buy_hold': buy_hold,
        'excess': total_return - buy_hold,
        'max_drawdown': max_dd,
        'sharpe': sharpe
    }

# ==================== 6. 主函数 ====================
def batch_backtest(start_date='2023-01-01', end_date='2023-12-31'):
    print("="*80)
    print("🚀 批量回测工具 - 股票池策略对比")
    print("="*80)
    print(f"时间范围：{start_date} 至 {end_date}")
    print(f"股票数量：{len(STOCK_POOL)}")
    print("="*80)
    
    results = []
    
    for code, name in STOCK_POOL:
        print(f"\n📈 测试 {code} {name}...")
        
        df = get_stock_data(code, start_date, end_date)
        if df is None or len(df) < 30:
            print(f"  ⚠️ 数据不足，跳过")
            continue
        
        # 计算指标
        df = calculate_macd(df)
        df = calculate_bollinger(df)
        
        # 回测
        macd_stats = backtest(df, 'positions')
        bb_stats = backtest(df, 'bb_positions')
        
        if macd_stats is None or bb_stats is None:
            print(f"  ⚠️ 回测失败，跳过")
            continue
        
        # 选出最佳策略
        best_strategy = 'MACD' if macd_stats['total_return'] > bb_stats['total_return'] else '布林带'
        best_return = max(macd_stats['total_return'], bb_stats['total_return'])
        
        result = {
            '代码': code,
            '名称': name,
            '交易日数': len(df),
            'MACD 收益': macd_stats['total_return'],
            'MACD 超额': macd_stats['excess'],
            'MACD 回撤': macd_stats['max_drawdown'],
            'MACD 夏普': macd_stats['sharpe'],
            '布林带收益': bb_stats['total_return'],
            '布林带超额': bb_stats['excess'],
            '布林带回撤': bb_stats['max_drawdown'],
            '布林带夏普': bb_stats['sharpe'],
            '最佳策略': best_strategy,
            '最佳收益': best_return
        }
        
        results.append(result)
        
        # 打印摘要
        macd_symbol = '🏆' if best_strategy == 'MACD' else ''
        bb_symbol = '🏆' if best_strategy == '布林带' else ''
        
        print(f"  MACD:    {macd_stats['total_return']:7.2%} (超额{macd_stats['excess']:6.2%}, 夏普{macd_stats['sharpe']:5.2f}) {macd_symbol}")
        print(f"  布林带：  {bb_stats['total_return']:7.2%} (超额{bb_stats['excess']:6.2%}, 夏普{bb_stats['sharpe']:5.2f}) {bb_symbol}")
    
    # 汇总报告
    results_df = pd.DataFrame(results)
    
    print("\n" + "="*80)
    print("📊 汇总报告")
    print("="*80)
    print(results_df.to_string(index=False))
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'/home/openclaw/.openclaw/workspace/quant_strategies/batch_backtest_{timestamp}.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ 结果已保存：{output_file}")
    
    # 统计分析
    print("\n" + "="*80)
    print("📈 统计分析")
    print("="*80)
    
    macd_wins = (results_df['MACD 收益'] > results_df['布林带收益']).sum()
    bb_wins = len(results_df) - macd_wins
    
    print(f"MACD 胜出：{macd_wins} 只股票 ({macd_wins/len(results_df)*100:.1f}%)")
    print(f"布林带胜出：{bb_wins} 只股票 ({bb_wins/len(results_df)*100:.1f}%)")
    
    # 最佳策略分布
    print(f"\n🏆 各策略最佳收益:")
    print(f"  MACD 最高：{results_df['MACD 收益'].max():.2%} ({results_df.loc[results_df['MACD 收益'].idxmax(), '名称']})")
    print(f"  布林带最高：{results_df['布林带收益'].max():.2%} ({results_df.loc[results_df['布林带收益'].idxmax(), '名称']})")
    
    # 按行业分析
    print(f"\n📊 按行业统计:")
    industries = {
        '银行': ['sh.600000', 'sh.600036', 'sh.601398'],
        '白酒': ['sh.600519', 'sh.000858', 'sz.000568'],
        '科技': ['sz.300750', 'sz.002594', 'sh.601138'],
        '消费': ['sh.600276', 'sz.000333', 'sh.600887']
    }
    
    for industry, codes in industries.items():
        industry_df = results_df[results_df['代码'].isin(codes)]
        if len(industry_df) > 0:
            macd_avg = industry_df['MACD 收益'].mean()
            bb_avg = industry_df['布林带收益'].mean()
            best = 'MACD' if macd_avg > bb_avg else '布林带'
            print(f"  {industry}: MACD 平均{macd_avg:.2%} vs 布林带平均{bb_avg:.2%} → {best} 更优")
    
    # 生成推荐
    print(f"\n💡 策略推荐:")
    for _, row in results_df.iterrows():
        print(f"  {row['名称']}: 使用 {row['最佳策略']} (预期收益{row['最佳收益']:.2%})")
    
    return results_df

# ==================== 7. 运行 ====================
if __name__ == '__main__':
    results = batch_backtest()
