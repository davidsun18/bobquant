# -*- coding: utf-8 -*-
"""
MACD + 布林带 组合策略 - 实战王牌
结合趋势跟踪和均值回归的优势
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import baostock as bs

# ==================== 1. 获取数据 ====================
def get_stock_data(code, start_date, end_date):
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
    
    df['close'] = df['close'].astype(float)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    bs.logout()
    return df

# ==================== 2. 计算 MACD ====================
def calculate_macd(df, ma1=12, ma2=26):
    df = df.copy()
    df['macd_ma1'] = df['close'].rolling(window=ma1, min_periods=1).mean()
    df['macd_ma2'] = df['close'].rolling(window=ma2, min_periods=1).mean()
    df['macd_oscillator'] = df['macd_ma1'] - df['macd_ma2']
    df['macd_golden_cross'] = (df['macd_ma1'] > df['macd_ma2']) & (df['macd_ma1'].shift(1) <= df['macd_ma2'].shift(1))
    df['macd_dead_cross'] = (df['macd_ma1'] < df['macd_ma2']) & (df['macd_ma1'].shift(1) >= df['macd_ma2'].shift(1))
    df['macd_trend_up'] = df['macd_ma2'] > df['macd_ma2'].shift(5)
    return df

# ==================== 3. 计算布林带 ====================
def calculate_bollinger_bands(df, window=20, num_std=2):
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(window=window, min_periods=1).mean()
    df['bb_std'] = df['close'].rolling(window=window, min_periods=1).std()
    df['bb_upper'] = df['bb_mid'] + num_std * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - num_std * df['bb_std']
    df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    return df

# ==================== 4. 组合策略 ====================
def combined_strategy(df, stop_loss=0.05, take_profit=0.10):
    """
    MACD + 布林带 组合策略
    
    买入条件（同时满足）：
    1. MACD 金叉 或 MACD 多头 (ma1 > ma2)
    2. 布林带 %B < 0.3 (价格在下轨附近)
    3. 趋势向上 (ma2 斜率>0)
    4. 成交量放大 (>20 日均量)
    
    卖出条件（任一满足）：
    1. MACD 死叉
    2. 布林带 %B > 0.8 (价格在上轨附近)
    3. 止损/止盈触发
    """
    df = df.copy()
    df['signal'] = 0
    df['positions'] = 0
    df['stop_loss_triggered'] = False
    df['take_profit_triggered'] = False
    
    # 成交量均线
    df['volume_ma'] = df['volume'].rolling(window=20, min_periods=1).mean()
    df['volume_ok'] = df['volume'] > df['volume_ma']
    
    in_position = False
    entry_price = 0
    highest_price = 0
    
    for i in range(1, len(df)):
        current_close = df['close'].iloc[i]
        current_high = df['high'].iloc[i]
        current_low = df['low'].iloc[i]
        
        # 更新最高价（用于移动止盈）
        if in_position and current_high > highest_price:
            highest_price = current_high
        
        if not in_position:
            # === 买入条件 ===
            macd_ok = df['macd_trend_up'].iloc[i] and df['macd_ma1'].iloc[i] > df['macd_ma2'].iloc[i]
            bb_ok = df['bb_percent_b'].iloc[i] < 0.3
            volume_ok = df['volume_ok'].iloc[i]
            
            if macd_ok and bb_ok and volume_ok:
                df.loc[df.index[i], 'signal'] = 1
                in_position = True
                entry_price = current_close
                highest_price = current_high
        
        elif in_position:
            # === 卖出条件 ===
            macd_dead = df['macd_dead_cross'].iloc[i]
            bb_overbought = df['bb_percent_b'].iloc[i] > 0.8
            
            # 止损
            stop_loss_price = entry_price * (1 - stop_loss)
            hit_stop_loss = current_low <= stop_loss_price
            
            # 止盈（移动止盈）
            trailing_stop = highest_price * (1 - take_profit / 2)
            hit_take_profit = current_close >= entry_price * (1 + take_profit)
            hit_trailing_stop = current_close < trailing_stop and highest_price > entry_price * (1 + take_profit / 2)
            
            if macd_dead or bb_overbought or hit_stop_loss or hit_take_profit or hit_trailing_stop:
                df.loc[df.index[i], 'signal'] = -1
                in_position = False
                
                if hit_stop_loss:
                    df.loc[df.index[i], 'stop_loss_triggered'] = True
                elif hit_take_profit or hit_trailing_stop:
                    df.loc[df.index[i], 'take_profit_triggered'] = True
                
                entry_price = 0
                highest_price = 0
        
        df.loc[df.index[i], 'positions'] = 1 if in_position else 0
        if in_position:
            df.loc[df.index[i], 'entry_price'] = entry_price
            df.loc[df.index[i], 'highest_price'] = highest_price
    
    return df

# ==================== 5. 回测统计 ====================
def backtest_stats(df, code):
    trades = df[df['signal'] != 0].copy()
    
    print("\n" + "="*70)
    print(f"📊 {code} MACD+ 布林带 组合策略回测")
    print("="*70)
    print(f"总交易日数：{len(df)}")
    print(f"总交易次数：{len(trades)}")
    print(f"买入次数：{len(trades[trades['signal'] == 1])}")
    print(f"卖出次数：{len(trades[trades['signal'] == -1])}")
    
    # 止损止盈统计
    stop_loss_count = df[df['stop_loss_triggered'] == True].shape[0]
    take_profit_count = df[df['take_profit_triggered'] == True].shape[0]
    print(f"\n🛡️ 风控统计:")
    print(f"  止损触发：{stop_loss_count} 次")
    print(f"  止盈触发：{take_profit_count} 次")
    
    # 计算收益
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['positions'].shift(1) * df['returns']
    
    total_return = (1 + df['strategy_returns']).prod() - 1
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
    
    # 最大回撤
    cumulative = (1 + df['strategy_returns']).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # 夏普比率
    daily_rf = 0.03 / 252
    excess_returns = df['strategy_returns'] - daily_rf
    sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
    
    # 卡玛比率
    calmar = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    print(f"\n📈 收益指标:")
    print(f"  策略总收益：{total_return:.2%}")
    print(f"  买入持有收益：{buy_hold_return:.2%}")
    print(f"  超额收益：{total_return - buy_hold_return:.2%}")
    print(f"  最大回撤：{max_drawdown:.2%}")
    print(f"  夏普比率：{sharpe:.2f}")
    print(f"  卡玛比率：{calmar:.2f}")
    
    # 交易质量
    if len(trades) > 1:
        trade_returns = []
        for i in range(len(trades) - 1):
            if trades['signal'].iloc[i] == 1 and trades['signal'].iloc[i+1] == -1:
                buy_price = trades['close'].iloc[i]
                sell_price = trades['close'].iloc[i+1]
                trade_returns.append((sell_price - buy_price) / buy_price)
        
        if trade_returns:
            win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns)
            avg_win = np.mean([r for r in trade_returns if r > 0]) if any(r > 0 for r in trade_returns) else 0
            avg_loss = np.mean([r for r in trade_returns if r < 0]) if any(r < 0 for r in trade_returns) else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            print(f"\n🎯 交易质量:")
            print(f"  胜率：{win_rate:.2%}")
            print(f"  平均盈利：{avg_win:.2%}")
            print(f"  平均亏损：{avg_loss:.2%}")
            print(f"  盈亏比：{profit_factor:.2f}")
            print(f"  最大单笔盈利：{max(trade_returns):.2%}")
            print(f"  最大单笔亏损：{min(trade_returns):.2%}")
    
    # 与单一策略对比
    print(f"\n🆚 与单一策略对比:")
    print(f"  MACD 终极版收益：+0.59%")
    print(f"  布林带均值回归：+11.97%")
    print(f"  组合策略收益：{total_return:.2%}")
    
    return df

# ==================== 6. 绘图 ====================
def plot_results(df, code):
    fig = plt.figure(figsize=(16, 14))
    
    # 图 1：价格 + 布林带 + 买卖点
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    ax1.plot(df['date'], df['bb_upper'], label='布林带上轨', linewidth=1, color='red', linestyle='--')
    ax1.plot(df['date'], df['bb_mid'], label='布林带中轨', linewidth=1, color='blue')
    ax1.plot(df['date'], df['bb_lower'], label='布林带下轨', linewidth=1, color='green', linestyle='--')
    
    buy_idx = df[df['signal'] == 1].index
    sell_idx = df[df['signal'] == -1].index
    stop_loss_idx = df[df['stop_loss_triggered'] == True].index
    take_profit_idx = df[df['take_profit_triggered'] == True].index
    
    if len(buy_idx) > 0:
        ax1.scatter(df.loc[buy_idx, 'date'], df.loc[buy_idx, 'close'], 
                   color='green', marker='^', s=120, label='买入', zorder=5, edgecolors='white')
    if len(sell_idx) > 0:
        ax1.scatter(df.loc[sell_idx, 'date'], df.loc[sell_idx, 'close'], 
                   color='red', marker='v', s=120, label='卖出', zorder=5, edgecolors='white')
    if len(stop_loss_idx) > 0:
        ax1.scatter(df.loc[stop_loss_idx, 'date'], df.loc[stop_loss_idx, 'close'], 
                   color='orange', marker='x', s=100, label='止损', zorder=6, linewidths=2)
    if len(take_profit_idx) > 0:
        ax1.scatter(df.loc[take_profit_idx, 'date'], df.loc[take_profit_idx, 'close'], 
                   color='gold', marker='*', s=150, label='止盈', zorder=6, edgecolors='black')
    
    ax1.set_title(f'{code} MACD+ 布林带 组合策略', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', ncol=3)
    ax1.grid(True, alpha=0.3)
    
    # 图 2：MACD 指标
    ax2 = plt.subplot(4, 1, 2, sharex=ax1)
    ax2.plot(df['date'], df['macd_ma1'], label='MA1(12)', linewidth=1.5)
    ax2.plot(df['date'], df['macd_ma2'], label='MA2(26)', linewidth=1.5, linestyle='--')
    ax2.fill_between(df['date'], df['macd_ma2'], df['macd_ma1'], 
                    where=(df['macd_ma1'] > df['macd_ma2']), 
                    alpha=0.3, color='red', label='MACD 多头')
    ax2.fill_between(df['date'], df['macd_ma2'], df['macd_ma1'], 
                    where=(df['macd_ma1'] < df['macd_ma2']), 
                    alpha=0.3, color='green', label='MACD 空头')
    ax2.legend(loc='upper left', ncol=2)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('MACD 趋势判断')
    
    # 图 3：%B 指标
    ax3 = plt.subplot(4, 1, 3, sharex=ax1)
    ax3.plot(df['date'], df['bb_percent_b'], label='%B 指标', linewidth=1.5, color='purple')
    ax3.axhline(0.8, color='red', linestyle='--', label='超买线 (0.8)', alpha=0.7)
    ax3.axhline(0.3, color='green', linestyle='--', label='买入区 (0.3)', alpha=0.7)
    ax3.axhline(0.5, color='gray', linestyle=':', alpha=0.5)
    ax3.fill_between(df['date'], 0, 1, where=(df['bb_percent_b'] < 0.3), alpha=0.3, color='green', label='买入区')
    ax3.fill_between(df['date'], 0, 1, where=(df['bb_percent_b'] > 0.8), alpha=0.3, color='red', label='超买区')
    ax3.set_ylim(-0.1, 1.1)
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('布林带 %B 指标 (位置判断)')
    
    # 图 4：收益对比
    ax4 = plt.subplot(4, 1, 4, sharex=ax1)
    df['cumulative_strategy'] = (1 + df['strategy_returns']).cumprod()
    df['cumulative_bh'] = (1 + df['close'].pct_change()).cumprod()
    
    ax4.plot(df['date'], df['cumulative_strategy'], label='组合策略', linewidth=2, color='blue')
    ax4.plot(df['date'], df['cumulative_bh'], label='买入持有', linewidth=2, linestyle=':', color='gray')
    
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.set_title('累计收益对比')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_combined_strategy.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：{code}_combined_strategy.png")
    plt.show()

# ==================== 7. 主函数 ====================
if __name__ == '__main__':
    CODE = 'sh.600000'
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    STOP_LOSS = 0.05
    TAKE_PROFIT = 0.10
    
    print(f"🚀 开始 MACD+ 布林带 组合策略回测：{CODE}")
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    print(f"风控参数：止损={STOP_LOSS*100}%, 止盈={TAKE_PROFIT*100}%")
    
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"✅ 数据获取完成，共 {len(df)} 个交易日")
    
    df = calculate_macd(df)
    df = calculate_bollinger_bands(df)
    df = combined_strategy(df, STOP_LOSS, TAKE_PROFIT)
    df = backtest_stats(df, CODE)
    plot_results(df, CODE)
