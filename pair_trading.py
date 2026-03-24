# -*- coding: utf-8 -*-
"""
配对交易 (Pair Trading) - 统计套利入门
找到"情侣股"，做多弱势 + 做空强势，市场中性策略
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import baostock as bs
from statsmodels.tsa.stattools import coint, adfuller
import warnings
warnings.filterwarnings('ignore')

# ==================== 1. 获取数据 ====================
def get_stock_data(code, start_date, end_date):
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code,
        "date,close",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    df = pd.DataFrame(data_list, columns=rs.fields)
    df['close'] = df['close'].astype(float)
    bs.logout()
    return df

# ==================== 2. 协整检验 ====================
def cointegration_test(stock1_data, stock2_data):
    """
    Engle-Granger 两步法协整检验
    返回：
    - p_value: 协整检验 p 值 (<0.05 表示存在协整关系)
    - hedge_ratio: 对冲比率（股票 2 的数量/股票 1 的数量）
    - spread: 价差序列
    """
    # 第一步：回归计算对冲比率
    from sklearn.linear_model import LinearRegression
    
    X = stock1_data['close'].values.reshape(-1, 1)
    y = stock2_data['close'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    hedge_ratio = model.coef_[0]  # 对冲比率
    spread = y - model.predict(X)  # 价差 = 股票 2 - 对冲比率 × 股票 1
    
    # 第二步：ADF 检验价差是否平稳
    adf_result = adfuller(spread, maxlag=1, autolag='AIC')
    p_value = adf_result[1]
    
    return p_value, hedge_ratio, spread

# ==================== 3. 寻找最佳配对 ====================
def find_best_pairs(stock_pool, start_date, end_date, pvalue_threshold=0.05):
    """
    在股票池中寻找协整关系最强的配对
    """
    print("="*70)
    print("🔍 寻找最佳配对")
    print("="*70)
    
    # 获取所有股票数据
    stock_data = {}
    for code, name in stock_pool:
        df = get_stock_data(code, start_date, end_date)
        if len(df) > 30:
            stock_data[code] = {'name': name, 'data': df}
    
    print(f"✅ 成功获取 {len(stock_data)} 只股票数据")
    
    # 两两检验协整关系
    results = []
    codes = list(stock_data.keys())
    
    for i in range(len(codes)):
        for j in range(i+1, len(codes)):
            code1, code2 = codes[i], codes[j]
            
            # 对齐日期
            merged = pd.merge(
                stock_data[code1]['data'].rename(columns={'close': 'price1'}),
                stock_data[code2]['data'].rename(columns={'close': 'price2'}),
                on='date'
            )
            
            if len(merged) < 60:
                continue
            
            # 协整检验
            p_value, hedge_ratio, spread = cointegration_test(
                merged.rename(columns={'price1': 'close'}),
                merged.rename(columns={'price2': 'close'})
            )
            
            # 计算相关性
            correlation = merged['price1'].corr(merged['price2'])
            
            # 计算价差统计
            spread_mean = spread.mean()
            spread_std = spread.std()
            
            results.append({
                '股票 1': f"{code1}({stock_data[code1]['name']})",
                '股票 2': f"{code2}({stock_data[code2]['name']})",
                'p_value': p_value,
                '协整': '✅' if p_value < pvalue_threshold else '❌',
                '相关性': correlation,
                '对冲比率': hedge_ratio,
                '价差均值': spread_mean,
                '价差标准差': spread_std,
                '数据长度': len(merged)
            })
    
    results_df = pd.DataFrame(results)
    
    # 筛选协整配对
    coint_pairs = results_df[results_df['p_value'] < pvalue_threshold]
    coint_pairs = coint_pairs.sort_values('p_value')
    
    print(f"\n📊 检验结果:")
    print(f"  总配对数：{len(results_df)}")
    print(f"  协整配对：{len(coint_pairs)} (p<0.05)")
    
    if len(coint_pairs) > 0:
        print(f"\n🏆 最佳配对 (按 p 值排序):")
        print(coint_pairs.head(10).to_string(index=False))
    else:
        print(f"\n⚠️ 未找到协整配对，尝试放宽阈值...")
    
    return results_df, coint_pairs

# ==================== 4. 配对交易策略 ====================
def pair_trading_strategy(stock1_data, stock2_data, hedge_ratio, 
                         entry_threshold=2.0, exit_threshold=0.5):
    """
    配对交易策略
    - 当价差 > 2σ 时：做空价差（做空股票 2 + 做多股票 1）
    - 当价差 < -2σ 时：做多价差（做多股票 2 + 做空股票 1）
    - 当价差回归 0.5σ 时：平仓
    """
    # 对齐日期
    merged = pd.merge(
        stock1_data.rename(columns={'close': 'price1'}),
        stock2_data.rename(columns={'close': 'price2'}),
        on='date'
    ).reset_index(drop=True)
    
    if len(merged) < 60:
        return None
    
    # 计算价差
    merged['spread'] = merged['price2'] - hedge_ratio * merged['price1']
    merged['spread_mean'] = merged['spread'].rolling(window=20, min_periods=1).mean()
    merged['spread_std'] = merged['spread'].rolling(window=20, min_periods=1).std()
    merged['spread_zscore'] = (merged['spread'] - merged['spread_mean']) / merged['spread_std']
    
    # 生成交易信号
    merged['signal'] = 0
    merged['positions'] = 0
    
    in_position = False
    position_type = None  # 'long_spread' or 'short_spread'
    
    for i in range(1, len(merged)):
        zscore = merged['spread_zscore'].iloc[i]
        
        if not in_position:
            # 价差过高：做空价差（做空股票 2 + 做多股票 1）
            if zscore > entry_threshold:
                merged.loc[merged.index[i], 'signal'] = -1
                in_position = True
                position_type = 'short_spread'
            # 价差过低：做多价差（做多股票 2 + 做空股票 1）
            elif zscore < -entry_threshold:
                merged.loc[merged.index[i], 'signal'] = 1
                in_position = True
                position_type = 'long_spread'
        else:
            # 平仓条件：价差回归
            if abs(zscore) < exit_threshold:
                merged.loc[merged.index[i], 'signal'] = -position_type.split('_')[0]
                in_position = False
                position_type = None
        
        merged.loc[merged.index[i], 'positions'] = 1 if in_position else 0
    
    return merged

# ==================== 5. 回测统计 ====================
def backtest_pair_trading(merged, code1, code2):
    """回测配对交易策略"""
    print("\n" + "="*70)
    print(f"📊 {code1} vs {code2} 配对交易回测")
    print("="*70)
    
    trades = merged[merged['signal'] != 0]
    
    print(f"总交易日数：{len(merged)}")
    print(f"总交易次数：{len(trades)}")
    
    # 计算收益（简化：假设多空各 50% 仓位）
    merged['returns1'] = merged['price1'].pct_change()
    merged['returns2'] = merged['price2'].pct_change()
    
    # 配对交易收益 = 股票 2 收益 - 对冲比率 × 股票 1 收益
    merged['spread_return'] = merged['returns2'] - merged['hedge_ratio'] * merged['returns1'] if 'hedge_ratio' in merged else 0
    merged['strategy_returns'] = merged['positions'].shift(1) * merged['spread_return'].abs() * 0.5  # 简化
    
    total_return = (1 + merged['strategy_returns']).prod() - 1
    
    # 最大回撤
    if len(merged['strategy_returns'].dropna()) > 0:
        cumulative = (1 + merged['strategy_returns']).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        # 夏普比率
        excess = merged['strategy_returns'].dropna() - 0.03/252
        sharpe = np.sqrt(252) * excess.mean() / excess.std() if excess.std() > 0 else 0
    else:
        max_dd = 0
        sharpe = 0
    
    print(f"\n📈 收益指标:")
    print(f"  策略总收益：{total_return:.2%}")
    print(f"  最大回撤：{max_dd:.2%}")
    print(f"  夏普比率：{sharpe:.2f}")
    
    return {
        'total_return': total_return,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'trades': len(trades)
    }

# ==================== 6. 绘图 ====================
def plot_pair_trading(merged, code1, code2, hedge_ratio):
    """绘制配对交易结果"""
    fig = plt.figure(figsize=(16, 12))
    
    # 图 1：两只股票价格
    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(merged['date'], merged['price1'], label=f'{code1}', linewidth=1.5)
    ax1.plot(merged['date'], merged['price2'], label=f'{code2}', linewidth=1.5)
    ax1.set_title(f'{code1} vs {code2} 价格走势 (对冲比率={hedge_ratio:.2f})', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 图 2：价差 + 交易信号
    ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    ax2.plot(merged['date'], merged['spread'], label='价差', linewidth=1.5, color='purple')
    ax2.plot(merged['date'], merged['spread_mean'], label='20 日均值', linewidth=1, linestyle='--', color='blue')
    ax2.fill_between(merged['date'], merged['spread_mean'] + 2*merged['spread_std'], 
                    merged['spread_mean'] - 2*merged['spread_std'], 
                    alpha=0.3, color='gray', label='±2σ 区间')
    
    # 标记交易信号
    buy_idx = merged[merged['signal'] == 1].index
    sell_idx = merged[merged['signal'] == -1].index
    
    if len(buy_idx) > 0:
        ax2.scatter(merged.loc[buy_idx, 'date'], merged.loc[buy_idx, 'spread'], 
                   color='green', marker='^', s=120, label='做多价差', zorder=5, edgecolors='white')
    if len(sell_idx) > 0:
        ax2.scatter(merged.loc[sell_idx, 'date'], merged.loc[sell_idx, 'spread'], 
                   color='red', marker='v', s=120, label='做空价差', zorder=5, edgecolors='white')
    
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('价差序列 + 交易信号')
    
    # 图 3：Z-Score
    ax3 = plt.subplot(3, 1, 3, sharex=ax1)
    ax3.plot(merged['date'], merged['spread_zscore'], label='Z-Score', linewidth=1.5, color='orange')
    ax3.axhline(2, color='red', linestyle='--', label='开仓线 (2σ)', alpha=0.7)
    ax3.axhline(-2, color='red', linestyle='--', alpha=0.7)
    ax3.axhline(0.5, color='green', linestyle=':', label='平仓线 (0.5σ)', alpha=0.7)
    ax3.axhline(-0.5, color='green', linestyle=':', alpha=0.7)
    ax3.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('价差 Z-Score (标准化)')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/pair_trading_{code1}_{code2}.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：pair_trading_{code1}_{code2}.png")
    plt.show()

# ==================== 7. 主函数 ====================
if __name__ == '__main__':
    # 股票池（选择可能相关的股票）
    STOCK_POOL = [
        # 银行
        ('sh.600000', '浦发银行'),
        ('sh.600036', '招商银行'),
        ('sh.601398', '工商银行'),
        ('sh.601288', '农业银行'),
        
        # 白酒
        ('sh.600519', '贵州茅台'),
        ('sh.000858', '五粮液'),
        ('sz.000568', '泸州老窖'),
        
        # 券商
        ('sh.600030', '中信证券'),
        ('sh.601688', '华泰证券'),
    ]
    
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    print("="*70)
    print("🎓 配对交易策略教程")
    print("="*70)
    
    # 1. 寻找最佳配对
    results_df, coint_pairs = find_best_pairs(STOCK_POOL, START_DATE, END_DATE)
    
    if len(coint_pairs) > 0:
        # 2. 选择最佳配对进行回测
        best_pair = coint_pairs.iloc[0]
        print(f"\n🎯 选择最佳配对进行回测:")
        print(f"  {best_pair['股票 1']} vs {best_pair['股票 2']}")
        print(f"  p 值：{best_pair['p_value']:.4f}")
        print(f"  相关性：{best_pair['相关性']:.3f}")
        print(f"  对冲比率：{best_pair['对冲比率']:.3f}")
        
        # 提取代码
        code1 = best_pair['股票 1'].split('(')[0]
        code2 = best_pair['股票 2'].split('(')[0]
        
        # 获取数据
        stock1_data = get_stock_data(code1, START_DATE, END_DATE)
        stock2_data = get_stock_data(code2, START_DATE, END_DATE)
        
        # 对齐日期
        merged = pd.merge(stock1_data, stock2_data, on='date', suffixes=('_1', '_2'))
        merged['hedge_ratio'] = best_pair['对冲比率']
        
        # 3. 运行策略
        print("\n📈 运行配对交易策略...")
        strategy_result = pair_trading_strategy(
            stock1_data.rename(columns={'close': f'price1'}),
            stock2_data.rename(columns={'close': f'price2'}),
            best_pair['对冲比率']
        )
        
        if strategy_result is not None:
            # 4. 回测统计
            stats = backtest_pair_trading(strategy_result, code1, code2)
            
            # 5. 绘图
            plot_pair_trading(strategy_result, code1, code2, best_pair['对冲比率'])
    
    print("\n" + "="*70)
    print("📚 学习要点")
    print("="*70)
    print("""
1. 协整检验：找到长期相关的股票对
2. 对冲比率：确定两只股票的配比
3. 价差交易：做多弱势 + 做空强势
4. 市场中性：不依赖大盘涨跌
5. 风险控制：价差可能不回归（协整关系破裂）
    """)
