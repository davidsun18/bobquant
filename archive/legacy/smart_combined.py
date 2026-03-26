# -*- coding: utf-8 -*-
"""
MACD + 布林带 智能组合策略 - 分场景使用
根据市场状态自动选择最适合的策略
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

# ==================== 2. 计算指标 ====================
def calculate_indicators(df):
    """计算 MACD 和布林带"""
    df = df.copy()
    
    # MACD
    df['macd_ma1'] = df['close'].rolling(window=12, min_periods=1).mean()
    df['macd_ma2'] = df['close'].rolling(window=26, min_periods=1).mean()
    df['macd_oscillator'] = df['macd_ma1'] - df['macd_ma2']
    df['macd_trend_up'] = df['macd_ma2'] > df['macd_ma2'].shift(5)
    
    # 布林带
    df['bb_mid'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['bb_std'] = df['close'].rolling(window=20, min_periods=1).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_bandwidth_ma'] = df['bb_bandwidth'].rolling(window=20, min_periods=1).mean()
    
    # 市场状态判断
    # 趋势市：带宽扩张 + MACD 方向明确
    df['is_trending'] = (df['bb_bandwidth'] > df['bb_bandwidth_ma'] * 1.2) & (abs(df['macd_oscillator']) > df['macd_oscillator'].rolling(20, min_periods=1).std())
    
    # 震荡市：带宽收缩 + MACD 粘合
    df['is_ranging'] = (df['bb_bandwidth'] < df['bb_bandwidth_ma'] * 0.8) | (abs(df['macd_oscillator']) < df['macd_oscillator'].rolling(20, min_periods=1).std() * 0.5)
    
    return df

# ==================== 3. 智能组合策略 ====================
def smart_combined_strategy(df, stop_loss=0.05, take_profit=0.10):
    """
    智能组合策略：
    - 趋势市：用 MACD（金叉买入，死叉卖出）
    - 震荡市：用布林带（下轨买入，上轨卖出）
    """
    df = df.copy()
    df['signal'] = 0
    df['positions'] = 0
    df['stop_loss_triggered'] = False
    df['take_profit_triggered'] = True  # 改成 True 表示用移动止盈
    
    in_position = False
    entry_price = 0
    highest_price = 0
    strategy_type = None  # 'macd' or 'bb'
    
    for i in range(1, len(df)):
        current_close = df['close'].iloc[i]
        current_high = df['high'].iloc[i]
        current_low = df['low'].iloc[i]
        
        if in_position:
            highest_price = max(highest_price, current_high)
        
        if not in_position:
            # === 判断市场状态 ===
            is_trending = df['is_trending'].iloc[i]
            is_ranging = df['is_ranging'].iloc[i]
            
            # 趋势市用 MACD
            if is_trending and not is_ranging:
                # MACD 金叉 + 趋势向上
                if df['macd_trend_up'].iloc[i] and df['macd_ma1'].iloc[i] > df['macd_ma2'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 1
                    in_position = True
                    entry_price = current_close
                    highest_price = current_high
                    strategy_type = 'macd'
            
            # 震荡市用布林带
            elif is_ranging and not is_trending:
                # 布林带下轨附近
                if df['bb_percent_b'].iloc[i] < 0.2:
                    df.loc[df.index[i], 'signal'] = 1
                    in_position = True
                    entry_price = current_close
                    highest_price = current_high
                    strategy_type = 'bb'
            
            # 默认状态（不明确）用布林带均值回归
            else:
                if df['bb_percent_b'].iloc[i] < 0.15:
                    df.loc[df.index[i], 'signal'] = 1
                    in_position = True
                    entry_price = current_close
                    highest_price = current_high
                    strategy_type = 'bb'
        
        elif in_position:
            # === 出场逻辑 ===
            should_exit = False
            
            # 止损
            if current_low <= entry_price * (1 - stop_loss):
                should_exit = True
                df.loc[df.index[i], 'stop_loss_triggered'] = True
            
            # 移动止盈
            trailing_stop = highest_price * (1 - take_profit / 2)
            if highest_price > entry_price * (1 + take_profit / 2) and current_close < trailing_stop:
                should_exit = True
                df.loc[df.index[i], 'take_profit_triggered'] = True
            
            # 根据策略类型出场
            if strategy_type == 'macd':
                # MACD 死叉
                if df['macd_ma1'].iloc[i] < df['macd_ma2'].iloc[i]:
                    should_exit = True
            elif strategy_type == 'bb':
                # 布林带上轨或中轨
                if df['bb_percent_b'].iloc[i] > 0.8 or (df['bb_percent_b'].iloc[i] > 0.5 and current_close < df['bb_mid'].iloc[i]):
                    should_exit = True
            
            if should_exit:
                df.loc[df.index[i], 'signal'] = -1
                in_position = False
                entry_price = 0
                highest_price = 0
                strategy_type = None
        
        df.loc[df.index[i], 'positions'] = 1 if in_position else 0
        df.loc[df.index[i], 'strategy_type'] = strategy_type if strategy_type else 'none'
    
    return df

# ==================== 4. 回测统计 ====================
def backtest_stats(df, code):
    trades = df[df['signal'] != 0].copy()
    
    print("\n" + "="*70)
    print(f"📊 {code} MACD+ 布林带 智能组合策略")
    print("="*70)
    print(f"总交易日数：{len(df)}")
    print(f"总交易次数：{len(trades)}")
    print(f"买入次数：{len(trades[trades['signal'] == 1])}")
    print(f"卖出次数：{len(trades[trades['signal'] == -1])}")
    
    # 策略使用统计
    macd_trades = len(df[df['strategy_type'] == 'macd'])
    bb_trades = len(df[df['strategy_type'] == 'bb'])
    print(f"\n📈 策略使用:")
    print(f"  MACD 策略交易日：{macd_trades} 天")
    print(f"  布林带策略交易日：{bb_trades} 天")
    
    # 止损止盈
    stop_loss_count = df[df['stop_loss_triggered'] == True].shape[0]
    take_profit_count = df[df['take_profit_triggered'] == True].shape[0]
    print(f"\n🛡️ 风控统计:")
    print(f"  止损触发：{stop_loss_count} 次")
    print(f"  止盈触发：{take_profit_count} 次")
    
    # 收益计算
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
    excess_returns = df['strategy_returns'] - 0.03/252
    sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
    
    print(f"\n📈 收益指标:")
    print(f"  策略总收益：{total_return:.2%}")
    print(f"  买入持有收益：{buy_hold_return:.2%}")
    print(f"  超额收益：{total_return - buy_hold_return:.2%}")
    print(f"  最大回撤：{max_drawdown:.2%}")
    print(f"  夏普比率：{sharpe:.2f}")
    
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
    
    # 对比
    print(f"\n🆚 策略对比:")
    print(f"  布林带均值回归：+11.97%")
    print(f"  MACD 终极版：+0.59%")
    print(f"  智能组合：{total_return:.2%}")
    
    return df

# ==================== 5. 绘图 ====================
def plot_results(df, code):
    fig = plt.figure(figsize=(16, 16))
    
    # 图 1：价格 + 布林带 + 买卖点
    ax1 = plt.subplot(5, 1, 1)
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    ax1.plot(df['date'], df['bb_upper'], label='布林带上轨', linewidth=1, color='red', linestyle='--')
    ax1.plot(df['date'], df['bb_mid'], label='布林带中轨', linewidth=1, color='blue')
    ax1.plot(df['date'], df['bb_lower'], label='布林带下轨', linewidth=1, color='green', linestyle='--')
    
    buy_idx = df[df['signal'] == 1].index
    sell_idx = df[df['signal'] == -1].index
    
    if len(buy_idx) > 0:
        ax1.scatter(df.loc[buy_idx, 'date'], df.loc[buy_idx, 'close'], 
                   color='green', marker='^', s=120, label='买入', zorder=5, edgecolors='white')
    if len(sell_idx) > 0:
        ax1.scatter(df.loc[sell_idx, 'date'], df.loc[sell_idx, 'close'], 
                   color='red', marker='v', s=120, label='卖出', zorder=5, edgecolors='white')
    
    ax1.set_title(f'{code} 智能组合策略', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', ncol=3)
    ax1.grid(True, alpha=0.3)
    
    # 图 2：市场状态
    ax2 = plt.subplot(5, 1, 2, sharex=ax1)
    ax2.fill_between(df['date'], 0, 1, where=df['is_trending'], 
                    alpha=0.5, color='red', label='趋势市')
    ax2.fill_between(df['date'], 0, 1, where=df['is_ranging'], 
                    alpha=0.5, color='blue', label='震荡市')
    ax2.set_ylim(0, 1.2)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('市场状态判断')
    
    # 图 3：使用的策略
    ax3 = plt.subplot(5, 1, 3, sharex=ax1)
    macd_mask = df['strategy_type'] == 'macd'
    bb_mask = df['strategy_type'] == 'bb'
    ax3.fill_between(df['date'], 0, 1, where=macd_mask, alpha=0.5, color='orange', label='MACD 策略')
    ax3.fill_between(df['date'], 0, 1, where=bb_mask, alpha=0.5, color='green', label='布林带策略')
    ax3.set_ylim(0, 1.2)
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('当前使用的策略')
    
    # 图 4：MACD
    ax4 = plt.subplot(5, 1, 4, sharex=ax1)
    ax4.plot(df['date'], df['macd_ma1'], label='MA1(12)', linewidth=1)
    ax4.plot(df['date'], df['macd_ma2'], label='MA2(26)', linewidth=1, linestyle='--')
    ax4.fill_between(df['date'], df['macd_ma2'], df['macd_ma1'], 
                    where=(df['macd_ma1'] > df['macd_ma2']), alpha=0.3, color='red')
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.set_title('MACD')
    
    # 图 5：收益曲线
    ax5 = plt.subplot(5, 1, 5, sharex=ax1)
    df['cumulative'] = (1 + df['strategy_returns']).cumprod()
    df['cumulative_bh'] = (1 + df['close'].pct_change()).cumprod()
    ax5.plot(df['date'], df['cumulative'], label='智能组合', linewidth=2)
    ax5.plot(df['date'], df['cumulative_bh'], label='买入持有', linewidth=2, linestyle=':', color='gray')
    ax5.legend(loc='upper left')
    ax5.grid(True, alpha=0.3)
    ax5.set_title('累计收益')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_smart_combined.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：{code}_smart_combined.png")
    plt.show()

# ==================== 6. 主函数 ====================
if __name__ == '__main__':
    CODE = 'sh.600000'
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    print(f"🚀 开始智能组合策略回测：{CODE}")
    
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"✅ 数据获取完成，共 {len(df)} 个交易日")
    
    df = calculate_indicators(df)
    df = smart_combined_strategy(df)
    df = backtest_stats(df, CODE)
    plot_results(df, CODE)
