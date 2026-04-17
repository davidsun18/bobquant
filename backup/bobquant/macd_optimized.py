# -*- coding: utf-8 -*-
"""
MACD 策略优化版 - 加入过滤条件和止损
改进点：
1. 趋势过滤：只在长期均线向上时做多
2. 成交量确认：放量时信号才有效
3. 止损机制：控制单笔亏损
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

# ==================== 2. 计算优化版 MACD ====================
def calculate_optimized_macd(df, ma1=12, ma2=26, volume_window=20, stop_loss=0.05):
    """
    优化版 MACD，加入：
    - 趋势过滤（ma2 向上）
    - 成交量确认（放量）
    - 止损机制
    """
    df = df.copy()
    
    # --- 基础 MACD 计算 ---
    df['ma1'] = df['close'].rolling(window=ma1, min_periods=1).mean()
    df['ma2'] = df['close'].rolling(window=ma2, min_periods=1).mean()
    df['oscillator'] = df['ma1'] - df['ma2']
    
    # --- 过滤条件 1: 趋势过滤 ---
    # ma2 斜率向上（当前 ma2 > 前 5 日 ma2）
    df['ma2_slope'] = df['ma2'] - df['ma2'].shift(5)
    df['trend_ok'] = df['ma2_slope'] > 0
    
    # --- 过滤条件 2: 成交量确认 ---
    # 当日成交量 > 过去 20 日平均成交量
    df['volume_ma'] = df['volume'].rolling(window=volume_window, min_periods=1).mean()
    df['volume_ok'] = df['volume'] > df['volume_ma']
    
    # --- 生成基础持仓信号 ---
    df['positions'] = 0
    df.loc[ma2:, 'positions'] = np.where(
        (df.loc[ma2:, 'ma1'] >= df.loc[ma2:, 'ma2']), 
        1, 0
    )
    
    # --- 应用过滤条件 ---
    # 只有趋势向上 + 放量时才持仓
    df['filtered_positions'] = df['positions'] & df['trend_ok'] & df['volume_ok']
    df['filtered_positions'] = df['filtered_positions'].astype(int)
    
    # --- 交易信号 ---
    df['signals'] = df['filtered_positions'].diff()
    
    # --- 止损机制 ---
    df['stop_loss_triggered'] = False
    df['entry_price'] = np.nan
    
    # 记录入场价和计算止损
    in_position = False
    entry_price = 0
    
    for i in range(1, len(df)):
        if df['signals'].iloc[i] == 1:  # 买入信号
            in_position = True
            entry_price = df['close'].iloc[i]
            df.loc[df.index[i], 'entry_price'] = entry_price
        
        elif df['signals'].iloc[i] == -1:  # 卖出信号
            in_position = False
            entry_price = 0
        
        # 检查止损
        if in_position and entry_price > 0:
            df.loc[df.index[i], 'entry_price'] = entry_price
            if df['close'].iloc[i] < entry_price * (1 - stop_loss):
                df.loc[df.index[i], 'stop_loss_triggered'] = True
                df.loc[df.index[i], 'signals'] = -1  # 触发止损卖出
                in_position = False
                entry_price = 0
    
    return df

# ==================== 3. 回测统计 ====================
def backtest_stats(df, stop_loss=0.05):
    """计算回测统计"""
    trades = df[df['signals'] != 0].copy()
    
    print("\n" + "="*60)
    print("📊 优化版 MACD 回测统计")
    print("="*60)
    print(f"总交易日数：{len(df)}")
    print(f"总交易次数：{len(trades)}")
    print(f"买入次数：{len(trades[trades['signals'] == 1])}")
    print(f"卖出次数：{len(trades[trades['signals'] == -1])}")
    
    # 止损统计
    stop_loss_count = df[df['stop_loss_triggered'] == True].shape[0]
    print(f"止损触发次数：{stop_loss_count}")
    
    # 过滤条件统计
    trend_filtered = (df['positions'] == 1) & (df['trend_ok'] == False)
    volume_filtered = (df['positions'] == 1) & (df['volume_ok'] == False)
    print(f"\n过滤掉的信号:")
    print(f"  - 趋势不好被过滤：{trend_filtered.sum()} 天")
    print(f"  - 成交量不足被过滤：{volume_filtered.sum()} 天")
    
    # 计算收益
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['filtered_positions'].shift(1) * df['returns']
    
    total_return = (1 + df['strategy_returns']).prod() - 1
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
    
    # 计算最大回撤
    cumulative = (1 + df['strategy_returns']).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # 计算夏普比率（假设无风险利率 3%）
    daily_rf = 0.03 / 252
    excess_returns = df['strategy_returns'] - daily_rf
    sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
    
    print(f"\n📈 收益指标:")
    print(f"  策略总收益：{total_return:.2%}")
    print(f"  买入持有收益：{buy_hold_return:.2%}")
    print(f"  超额收益：{total_return - buy_hold_return:.2%}")
    print(f"  最大回撤：{max_drawdown:.2%}")
    print(f"  夏普比率：{sharpe:.2f}")
    
    # 计算胜率
    if len(trades) > 1:
        trade_returns = []
        for i in range(len(trades) - 1):
            if trades['signals'].iloc[i] == 1 and trades['signals'].iloc[i+1] == -1:
                buy_price = trades['close'].iloc[i]
                sell_price = trades['close'].iloc[i+1]
                trade_returns.append((sell_price - buy_price) / buy_price)
        
        if trade_returns:
            win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns)
            avg_win = np.mean([r for r in trade_returns if r > 0]) if any(r > 0 for r in trade_returns) else 0
            avg_loss = np.mean([r for r in trade_returns if r < 0]) if any(r < 0 for r in trade_returns) else 0
            print(f"\n🎯 交易质量:")
            print(f"  胜率：{win_rate:.2%}")
            print(f"  平均盈利：{avg_win:.2%}")
            print(f"  平均亏损：{avg_loss:.2%}")
            print(f"  盈亏比：{abs(avg_win / avg_loss) if avg_loss != 0 else 'N/A':.2f}")
    
    return df

# ==================== 4. 绘图 ====================
def plot_results(df, code):
    """绘制回测结果（4 个子图）"""
    fig, axs = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    
    # 图 1：价格 + 买卖点
    axs[0].plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    
    # 标记买卖点
    buy_idx = df[df['signals'] == 1].index
    sell_idx = df[df['signals'] == -1].index
    stop_loss_idx = df[df['stop_loss_triggered'] == True].index
    
    if len(buy_idx) > 0:
        axs[0].scatter(df.loc[buy_idx, 'date'], df.loc[buy_idx, 'close'], 
                      color='green', marker='^', s=120, label='买入', zorder=5, edgecolors='white')
    if len(sell_idx) > 0:
        axs[0].scatter(df.loc[sell_idx, 'date'], df.loc[sell_idx, 'close'], 
                      color='red', marker='v', s=120, label='卖出', zorder=5, edgecolors='white')
    if len(stop_loss_idx) > 0:
        axs[0].scatter(df.loc[stop_loss_idx, 'date'], df.loc[stop_loss_idx, 'close'], 
                      color='orange', marker='x', s=100, label='止损', zorder=6, linewidths=2)
    
    axs[0].set_title(f'{code} 优化版 MACD 策略回测', fontsize=14, fontweight='bold')
    axs[0].legend(loc='upper left')
    axs[0].grid(True, alpha=0.3)
    
    # 图 2：均线 + 趋势过滤
    axs[1].plot(df['date'], df['ma1'], label='MA1(12)', linewidth=1.5)
    axs[1].plot(df['date'], df['ma2'], label='MA2(26)', linewidth=1.5, linestyle='--')
    axs[1].fill_between(df['date'], df['ma2'], df['ma2'].max(), 
                       where=df['trend_ok'], alpha=0.3, color='green', label='趋势向好')
    axs[1].fill_between(df['date'], df['ma2'], df['ma2'].min(), 
                       where=~df['trend_ok'], alpha=0.3, color='red', label='趋势向差')
    axs[1].legend(loc='upper left')
    axs[1].grid(True, alpha=0.3)
    axs[1].set_title('均线系统 + 趋势过滤')
    
    # 图 3：成交量
    axs[2].bar(df['date'], df['volume'], alpha=0.7, color='#999', label='成交量')
    axs[2].plot(df['date'], df['volume_ma'], label='20 日均量', linewidth=2, color='blue')
    axs[2].fill_between(df['date'], df['volume_ma'], df['volume'].max(), 
                       where=df['volume_ok'], alpha=0.3, color='green', label='放量')
    axs[2].legend(loc='upper left')
    axs[2].grid(True, alpha=0.3)
    axs[2].set_title('成交量确认')
    
    # 图 4：MACD 振荡器 + 持仓
    colors = np.where(df['oscillator'] >= 0, '#ff6b6b', '#4ecdc4')
    axs[3].bar(df['date'], df['oscillator'], color=colors, alpha=0.8, label='MACD 振荡器')
    axs[3].axhline(0, color='black', linewidth=0.8)
    
    # 叠加持仓状态
    ax3_twin = axs[3].twinx()
    ax3_twin.plot(df['date'], df['filtered_positions'], label='持仓状态', 
                 linewidth=2, color='purple', linestyle='-')
    ax3_twin.set_ylim(-0.1, 1.1)
    ax3_twin.set_yticks([])
    
    axs[3].legend(loc='upper left')
    ax3_twin.legend(loc='upper right')
    axs[3].grid(True, alpha=0.3)
    axs[3].set_title('MACD 振荡器 + 持仓状态')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_macd_optimized.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：{code}_macd_optimized.png")
    plt.show()

# ==================== 5. 主函数 ====================
if __name__ == '__main__':
    # 参数设置
    CODE = 'sh.600000'  # 浦发银行
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    MA1 = 12
    MA2 = 26
    VOLUME_WINDOW = 20  # 成交量均线周期
    STOP_LOSS = 0.05    # 止损比例 5%
    
    print(f"🚀 开始优化版 MACD 策略回测：{CODE}")
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    print(f"均线参数：MA1={MA1}, MA2={MA2}")
    print(f"过滤条件：趋势过滤 + 成交量确认")
    print(f"止损设置：{STOP_LOSS*100}%")
    
    # 获取数据
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"✅ 数据获取完成，共 {len(df)} 个交易日")
    
    # 计算优化版 MACD
    df = calculate_optimized_macd(df, MA1, MA2, VOLUME_WINDOW, STOP_LOSS)
    
    # 回测统计
    df = backtest_stats(df, STOP_LOSS)
    
    # 绘图
    plot_results(df, CODE)
