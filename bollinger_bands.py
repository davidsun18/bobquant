# -*- coding: utf-8 -*-
"""
布林带 (Bollinger Bands) 策略 - 震荡市神器
包含 3 种经典玩法：
1. 均值回归 - 触及下轨买入，触及上轨卖出
2. 布林带缩口 - 波动率收缩后突破
3. 布林带扩张 - 趋势跟随
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import baostock as bs

# ==================== 1. 获取数据 ====================
def get_stock_data(code, start_date, end_date):
    """使用 Baostock 获取股票数据"""
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code,
        "date,open,high,low,close,volume,turn",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    df = pd.DataFrame(data_list, columns=rs.fields)
    
    # 转换数据类型
    df['close'] = df['close'].astype(float)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    bs.logout()
    return df

# ==================== 2. 计算布林带 ====================
def calculate_bollinger_bands(df, window=20, num_std=2):
    """
    计算布林带
    - 中轨 = window 日均线
    - 上轨 = 中轨 + num_std * 标准差
    - 下轨 = 中轨 - num_std * 标准差
    - 带宽 = (上轨 - 下轨) / 中轨 (衡量波动率)
    - %B = (收盘价 - 下轨) / (上轨 - 下轨) (衡量价格位置)
    """
    df = df.copy()
    
    # 中轨
    df['bb_mid'] = df['close'].rolling(window=window, min_periods=1).mean()
    
    # 标准差
    df['bb_std'] = df['close'].rolling(window=window, min_periods=1).std()
    
    # 上轨和下轨
    df['bb_upper'] = df['bb_mid'] + num_std * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - num_std * df['bb_std']
    
    # 带宽 (Bandwidth) - 衡量波动率
    df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    
    # %B 指标 - 价格在布林带中的位置 (0-1 之间)
    df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    return df

# ==================== 3. 策略 1: 均值回归 ====================
def strategy_mean_reversion(df):
    """
    均值回归策略
    - 当价格触及下轨 (%B < 0.1) 时买入
    - 当价格触及上轨 (%B > 0.9) 时卖出
    - 当价格回归中轨时平仓
    """
    df = df.copy()
    df['signal_mr'] = 0
    df['positions_mr'] = 0
    
    in_position = False
    
    for i in range(1, len(df)):
        if not in_position:
            # 触及下轨，买入
            if df['bb_percent_b'].iloc[i] < 0.1:
                df.loc[df.index[i], 'signal_mr'] = 1
                in_position = True
        else:
            # 触及上轨或回归中轨，卖出
            if df['bb_percent_b'].iloc[i] > 0.9 or df['close'].iloc[i] >= df['bb_mid'].iloc[i]:
                df.loc[df.index[i], 'signal_mr'] = -1
                in_position = False
        
        df.loc[df.index[i], 'positions_mr'] = 1 if in_position else 0
    
    return df

# ==================== 4. 策略 2: 布林带缩口突破 ====================
def strategy_squeeze_breakout(df, squeeze_threshold=0.05, lookback=60):
    """
    布林带缩口突破策略
    - 缩口：带宽处于过去 60 天的最低 10% 分位
    - 向上突破：收盘价 > 上轨，买入
    - 向下跌破：收盘价 < 下轨，卖出/做空
    """
    df = df.copy()
    df['signal_squeeze'] = 0
    df['positions_squeeze'] = 0
    
    # 计算带宽的历史分位数
    df['bb_bandwidth_percentile'] = df['bb_bandwidth'].rolling(window=lookback, min_periods=1).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() > x.min() else 0.5
    )
    
    in_position = False
    position_direction = 0  # 1=多仓，-1=空仓
    
    for i in range(1, len(df)):
        is_squeeze = df['bb_bandwidth_percentile'].iloc[i] < 0.1  # 缩口
        
        if not in_position:
            # 缩口后向上突破
            if is_squeeze and df['close'].iloc[i] > df['bb_upper'].iloc[i]:
                df.loc[df.index[i], 'signal_squeeze'] = 1
                in_position = True
                position_direction = 1
            # 缩口后向下跌破
            elif is_squeeze and df['close'].iloc[i] < df['bb_lower'].iloc[i]:
                df.loc[df.index[i], 'signal_squeeze'] = -1
                in_position = True
                position_direction = -1
        else:
            # 回归中轨平仓
            if position_direction == 1 and df['close'].iloc[i] < df['bb_mid'].iloc[i]:
                df.loc[df.index[i], 'signal_squeeze'] = -1
                in_position = False
                position_direction = 0
            elif position_direction == -1 and df['close'].iloc[i] > df['bb_mid'].iloc[i]:
                df.loc[df.index[i], 'signal_squeeze'] = 1
                in_position = False
                position_direction = 0
    
    df['positions_squeeze'] = abs(df['positions_squeeze'].shift(1).fillna(0) + df['signal_squeeze'])
    df['positions_squeeze'] = np.where(df['positions_squeeze'] > 0, 1, 0)
    
    return df

# ==================== 5. 策略 3: 布林带扩张趋势跟随 ====================
def strategy_expansion_trend(df, expansion_threshold=1.5):
    """
    布林带扩张趋势跟随策略
    - 扩张：带宽 > 过去 20 天平均带宽的 1.5 倍
    - 价格触及上轨 + 扩张 = 强势上涨，买入
    - 价格触及下轨 + 扩张 = 强势下跌，卖出
    """
    df = df.copy()
    df['signal_expansion'] = 0
    df['positions_expansion'] = 0
    
    # 计算带宽的移动平均
    df['bb_bandwidth_ma'] = df['bb_bandwidth'].rolling(window=20, min_periods=1).mean()
    df['is_expansion'] = df['bb_bandwidth'] > (df['bb_bandwidth_ma'] * expansion_threshold)
    
    in_position = False
    
    for i in range(1, len(df)):
        if not in_position:
            # 扩张 + 触及上轨 = 强势上涨
            if df['is_expansion'].iloc[i] and df['bb_percent_b'].iloc[i] > 0.8:
                df.loc[df.index[i], 'signal_expansion'] = 1
                in_position = True
            # 扩张 + 触及下轨 = 强势下跌 (做空)
            elif df['is_expansion'].iloc[i] and df['bb_percent_b'].iloc[i] < 0.2:
                df.loc[df.index[i], 'signal_expansion'] = -1
                in_position = True
        else:
            # %B 回归中性区域平仓
            if 0.3 < df['bb_percent_b'].iloc[i] < 0.7:
                df.loc[df.index[i], 'signal_expansion'] = -1 if df['signal_expansion'].iloc[i] == 0 else 0
                in_position = False
    
    df['positions_expansion'] = 0
    df.loc[df['signal_expansion'] != 0, 'positions_expansion'] = 1
    df['positions_expansion'] = df['positions_expansion'].cumsum() % 2
    
    return df

# ==================== 6. 回测统计 ====================
def backtest_all_strategies(df, code):
    """回测所有策略并对比"""
    print("\n" + "="*70)
    print(f"📊 {code} 布林带策略对比")
    print("="*70)
    
    results = []
    
    strategies = [
        ('均值回归', 'signal_mr', 'positions_mr'),
        ('缩口突破', 'signal_squeeze', 'positions_squeeze'),
        ('扩张趋势', 'signal_expansion', 'positions_expansion')
    ]
    
    for name, signal_col, position_col in strategies:
        df['returns'] = df['close'].pct_change()
        df[f'strategy_returns_{name}'] = df[position_col].shift(1) * df['returns']
        
        total_return = (1 + df[f'strategy_returns_{name}']).prod() - 1
        buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
        
        # 最大回撤
        cumulative = (1 + df[f'strategy_returns_{name}']).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 夏普比率
        excess_returns = df[f'strategy_returns_{name}'] - 0.03/252
        sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
        
        # 交易次数
        trades = df[df[signal_col] != 0]
        buy_trades = len(trades[trades[signal_col] == 1])
        sell_trades = len(trades[trades[signal_col] == -1])
        
        results.append({
            '策略': name,
            '总收益': total_return,
            '买入持有': buy_hold_return,
            '超额收益': total_return - buy_hold_return,
            '最大回撤': max_drawdown,
            '夏普比率': sharpe,
            '买入次数': buy_trades,
            '卖出次数': sell_trades
        })
    
    # 打印结果
    results_df = pd.DataFrame(results)
    print("\n策略对比:")
    print(results_df.to_string(index=False))
    
    # 找出最佳策略
    best = results_df.loc[results_df['总收益'].idxmax()]
    print(f"\n🏆 最佳策略：{best['策略']}")
    print(f"   总收益：{best['总收益']:.2%}")
    print(f"   超额收益：{best['超额收益']:.2%}")
    print(f"   夏普比率：{best['夏普比率']:.2f}")
    
    return results_df

# ==================== 7. 绘图 ====================
def plot_results(df, code):
    """绘制布林带策略结果"""
    fig = plt.figure(figsize=(16, 16))
    
    # 图 1：价格 + 布林带
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    ax1.plot(df['date'], df['bb_upper'], label='上轨', linewidth=1.5, color='red', linestyle='--')
    ax1.plot(df['date'], df['bb_mid'], label='中轨 (20 日均线)', linewidth=1.5, color='blue')
    ax1.plot(df['date'], df['bb_lower'], label='下轨', linewidth=1.5, color='green', linestyle='--')
    
    # 填充布林带区域
    ax1.fill_between(df['date'], df['bb_lower'], df['bb_upper'], alpha=0.2, color='gray', label='布林带')
    
    # 标记买卖点 (均值回归策略)
    buy_idx = df[df['signal_mr'] == 1].index
    sell_idx = df[df['signal_mr'] == -1].index
    
    if len(buy_idx) > 0:
        ax1.scatter(df.loc[buy_idx, 'date'], df.loc[buy_idx, 'close'], 
                   color='green', marker='^', s=120, label='买入 (均值回归)', zorder=5, edgecolors='white')
    if len(sell_idx) > 0:
        ax1.scatter(df.loc[sell_idx, 'date'], df.loc[sell_idx, 'close'], 
                   color='red', marker='v', s=120, label='卖出 (均值回归)', zorder=5, edgecolors='white')
    
    ax1.set_title(f'{code} 布林带策略回测', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', ncol=3)
    ax1.grid(True, alpha=0.3)
    
    # 图 2：%B 指标
    ax2 = plt.subplot(4, 1, 2, sharex=ax1)
    ax2.plot(df['date'], df['bb_percent_b'], label='%B 指标', linewidth=1.5, color='purple')
    ax2.axhline(0.9, color='red', linestyle='--', label='超买线 (0.9)', alpha=0.7)
    ax2.axhline(0.1, color='green', linestyle='--', label='超卖线 (0.1)', alpha=0.7)
    ax2.axhline(0.5, color='gray', linestyle=':', alpha=0.5)
    ax2.fill_between(df['date'], 0, 1, where=(df['bb_percent_b'] > 0.9), alpha=0.3, color='red', label='超买区')
    ax2.fill_between(df['date'], 0, 1, where=(df['bb_percent_b'] < 0.1), alpha=0.3, color='green', label='超卖区')
    ax2.set_ylim(-0.1, 1.1)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('%B 指标 (价格在布林带中的位置)')
    
    # 图 3：带宽 (波动率)
    ax3 = plt.subplot(4, 1, 3, sharex=ax1)
    ax3.plot(df['date'], df['bb_bandwidth'], label='带宽', linewidth=1.5, color='orange')
    ax3.plot(df['date'], df['bb_bandwidth_ma'], label='带宽 20 日均线', linewidth=1.5, color='blue', linestyle='--')
    ax3.axhline(df['bb_bandwidth'].quantile(0.1), color='red', linestyle=':', label='缩口阈值 (10% 分位)', alpha=0.7)
    ax3.fill_between(df['date'], df['bb_bandwidth'].min(), df['bb_bandwidth'].max(), 
                    where=(df['bb_bandwidth'] < df['bb_bandwidth'].quantile(0.1)), 
                    alpha=0.3, color='red', label='缩口区')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('带宽 (衡量波动率 - 缩口预示大行情)')
    
    # 图 4：三种策略收益对比
    ax4 = plt.subplot(4, 1, 4, sharex=ax1)
    df['cumulative_mr'] = (1 + df['strategy_returns_均值回归']).cumprod()
    df['cumulative_squeeze'] = (1 + df['strategy_returns_缩口突破']).cumprod()
    df['cumulative_expansion'] = (1 + df['strategy_returns_扩张趋势']).cumprod()
    df['cumulative_bh'] = (1 + df['close'].pct_change()).cumprod()
    
    ax4.plot(df['date'], df['cumulative_mr'], label='均值回归策略', linewidth=2)
    ax4.plot(df['date'], df['cumulative_squeeze'], label='缩口突破策略', linewidth=2)
    ax4.plot(df['date'], df['cumulative_expansion'], label='扩张趋势策略', linewidth=2)
    ax4.plot(df['date'], df['cumulative_bh'], label='买入持有', linewidth=2, linestyle=':', color='gray')
    
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.set_title('三种策略累计收益对比')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_bollinger_bands.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：{code}_bollinger_bands.png")
    plt.show()

# ==================== 8. 主函数 ====================
if __name__ == '__main__':
    # 参数设置
    CODE = 'sh.600000'  # 浦发银行
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    BB_WINDOW = 20       # 布林带周期
    BB_NUM_STD = 2       # 标准差倍数
    
    print(f"🚀 开始布林带策略回测：{CODE}")
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    print(f"布林带参数：窗口={BB_WINDOW}, 标准差={BB_NUM_STD}")
    
    # 获取数据
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"✅ 数据获取完成，共 {len(df)} 个交易日")
    
    # 计算布林带
    df = calculate_bollinger_bands(df, BB_WINDOW, BB_NUM_STD)
    
    # 运行三种策略
    print("\n📈 运行策略...")
    df = strategy_mean_reversion(df)
    df = strategy_squeeze_breakout(df)
    df = strategy_expansion_trend(df)
    
    # 回测统计
    results = backtest_all_strategies(df, CODE)
    
    # 绘图
    plot_results(df, CODE)
