# -*- coding: utf-8 -*-
"""
RSI 策略详解 - 相对强弱指数
经典震荡指标，判断超买超卖
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
        "date,open,high,low,close,volume",
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

# ==================== 2. 计算 RSI ====================
def calculate_rsi(df, window=14):
    """
    RSI 计算公式：
    RSI = 100 - (100 / (1 + RS))
    RS = 平均涨幅 / 平均跌幅
    
    解读：
    - RSI > 70: 超买区，考虑卖出
    - RSI < 30: 超卖区，考虑买入
    - RSI = 50: 中性
    """
    df = df.copy()
    
    # 计算价格变化
    df['delta'] = df['close'].diff()
    
    # 分离涨跌
    df['gain'] = df['delta'].apply(lambda x: x if x > 0 else 0)
    df['loss'] = df['delta'].apply(lambda x: abs(x) if x < 0 else 0)
    
    # 计算平均涨跌幅度
    df['avg_gain'] = df['gain'].rolling(window=window, min_periods=1).mean()
    df['avg_loss'] = df['loss'].rolling(window=window, min_periods=1).mean()
    
    # 计算 RS 和 RSI
    df['rs'] = df['avg_gain'] / df['avg_loss']
    df['rsi'] = 100 - (100 / (1 + df['rs']))
    
    # 处理除零
    df['rsi'] = df['rsi'].fillna(50)
    
    return df

# ==================== 3. RSI 策略 1: 基础超买超卖 ====================
def strategy_basic_rsi(df, oversold=30, overbought=70):
    """
    基础 RSI 策略
    - RSI < 30 超卖，买入
    - RSI > 70 超买，卖出
    """
    df = df.copy()
    df['signal'] = 0
    df['positions'] = 0
    
    in_position = False
    
    for i in range(1, len(df)):
        if not in_position:
            # 超卖区买入
            if df['rsi'].iloc[i] < oversold:
                df.loc[df.index[i], 'signal'] = 1
                in_position = True
        else:
            # 超买区卖出
            if df['rsi'].iloc[i] > overbought:
                df.loc[df.index[i], 'signal'] = -1
                in_position = False
        
        df.loc[df.index[i], 'positions'] = 1 if in_position else 0
    
    return df

# ==================== 4. RSI 策略 2: RSI 背离 ====================
def strategy_rsi_divergence(df, lookback=5):
    """
    RSI 背离策略
    - 底背离：价格创新低，RSI 未创新低 → 买入
    - 顶背离：价格创新高，RSI 未创新高 → 卖出
    """
    df = df.copy()
    df['signal_div'] = 0
    df['positions_div'] = 0
    
    in_position = False
    
    for i in range(lookback, len(df)):
        # 当前价格/RSI
        current_price = df['close'].iloc[i]
        current_rsi = df['rsi'].iloc[i]
        
        # 过去 lookback 天的最低/最高
        prev_price_low = df['close'].iloc[i-lookback:i].min()
        prev_rsi_low = df['rsi'].iloc[i-lookback:i].min()
        prev_price_high = df['close'].iloc[i-lookback:i].max()
        prev_rsi_high = df['rsi'].iloc[i-lookback:i].max()
        
        if not in_position:
            # 底背离：价格创新低，RSI 未创新低
            if current_price < prev_price_low and current_rsi > prev_rsi_low:
                df.loc[df.index[i], 'signal_div'] = 1
                in_position = True
        else:
            # 顶背离：价格创新高，RSI 未创新高
            if current_price > prev_price_high and current_rsi < prev_rsi_high:
                df.loc[df.index[i], 'signal_div'] = -1
                in_position = False
        
        df.loc[df.index[i], 'positions_div'] = 1 if in_position else 0
    
    return df

# ==================== 5. RSI 策略 3: RSI + 趋势过滤 ====================
def strategy_rsi_with_trend(df, ma_window=50):
    """
    RSI + 趋势过滤
    - 只在上升趋势中做多（价格>50 日均线）
    - RSI < 30 买入，RSI > 60 卖出（降低超买阈值）
    """
    df = df.copy()
    df['ma50'] = df['close'].rolling(window=ma_window, min_periods=1).mean()
    df['signal_trend'] = 0
    df['positions_trend'] = 0
    
    in_position = False
    uptrend = False
    
    for i in range(1, len(df)):
        # 判断趋势
        uptrend = df['close'].iloc[i] > df['ma50'].iloc[i]
        
        if not in_position:
            # 上升趋势 + RSI 超卖
            if uptrend and df['rsi'].iloc[i] < 30:
                df.loc[df.index[i], 'signal_trend'] = 1
                in_position = True
        else:
            # RSI 超买 或 趋势反转
            if df['rsi'].iloc[i] > 60 or not uptrend:
                df.loc[df.index[i], 'signal_trend'] = -1
                in_position = False
        
        df.loc[df.index[i], 'positions_trend'] = 1 if in_position else 0
    
    return df

# ==================== 6. 回测统计 ====================
def backtest_all(df, code):
    print("\n" + "="*70)
    print(f"📊 {code} RSI 策略对比")
    print("="*70)
    
    results = []
    
    strategies = [
        ('基础超买超卖', 'signal', 'positions'),
        ('RSI 背离', 'signal_div', 'positions_div'),
        ('RSI+ 趋势', 'signal_trend', 'positions_trend')
    ]
    
    df['returns'] = df['close'].pct_change()
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
    
    for name, signal_col, position_col in strategies:
        if position_col not in df.columns:
            continue
        
        df[f'strategy_{name}'] = df[position_col].shift(1) * df['returns']
        
        total_return = (1 + df[f'strategy_{name}']).prod() - 1
        
        # 最大回撤
        cumulative = (1 + df[f'strategy_{name}']).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        # 夏普比率
        excess = df[f'strategy_{name}'] - 0.03/252
        sharpe = np.sqrt(252) * excess.mean() / excess.std() if excess.std() > 0 else 0
        
        # 交易次数
        trades = len(df[df[signal_col] != 0])
        
        results.append({
            '策略': name,
            '总收益': total_return,
            '超额收益': total_return - buy_hold_return,
            '最大回撤': max_dd,
            '夏普比率': sharpe,
            '交易次数': trades
        })
    
    results_df = pd.DataFrame(results)
    print("\n策略对比:")
    print(results_df.to_string(index=False))
    
    # 最佳策略
    best = results_df.loc[results_df['总收益'].idxmax()]
    print(f"\n🏆 最佳策略：{best['策略']}")
    print(f"   总收益：{best['总收益']:.2%}")
    print(f"   夏普比率：{best['夏普比率']:.2f}")
    
    # 与 MACD/布林带对比
    print(f"\n🆚 与之前策略对比:")
    print(f"  MACD 终极版：+0.59%")
    print(f"  布林带均值回归：+11.97%")
    print(f"  RSI 最佳：{best['总收益']:.2%}")
    
    return results_df

# ==================== 7. 绘图 ====================
def plot_results(df, code):
    fig = plt.figure(figsize=(16, 16))
    
    # 图 1：价格 + 买卖点
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    
    buy_idx = df[df['signal'] == 1].index
    sell_idx = df[df['signal'] == -1].index
    
    if len(buy_idx) > 0:
        ax1.scatter(df.loc[buy_idx, 'date'], df.loc[buy_idx, 'close'], 
                   color='green', marker='^', s=120, label='买入 (RSI 超卖)', zorder=5, edgecolors='white')
    if len(sell_idx) > 0:
        ax1.scatter(df.loc[sell_idx, 'date'], df.loc[sell_idx, 'close'], 
                   color='red', marker='v', s=120, label='卖出 (RSI 超买)', zorder=5, edgecolors='white')
    
    ax1.set_title(f'{code} RSI 策略回测', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 图 2：RSI 指标
    ax2 = plt.subplot(4, 1, 2, sharex=ax1)
    ax2.plot(df['date'], df['rsi'], label='RSI(14)', linewidth=1.5, color='purple')
    ax2.axhline(70, color='red', linestyle='--', label='超买线 (70)', alpha=0.7)
    ax2.axhline(30, color='green', linestyle='--', label='超卖线 (30)', alpha=0.7)
    ax2.axhline(50, color='gray', linestyle=':', alpha=0.5)
    ax2.fill_between(df['date'], 70, 100, alpha=0.3, color='red', label='超买区')
    ax2.fill_between(df['date'], 0, 30, alpha=0.3, color='green', label='超卖区')
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('RSI 指标 (相对强弱)')
    
    # 图 3：RSI 背离检测
    ax3 = plt.subplot(4, 1, 3, sharex=ax1)
    ax3.plot(df['date'], df['close'], label='收盘价', linewidth=1, color='#333')
    ax3.plot(df['date'], df['rsi']/2, label='RSI(缩放)', linewidth=1, color='purple', linestyle='--')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('价格 vs RSI (背离检测)')
    
    # 图 4：收益对比
    ax4 = plt.subplot(4, 1, 4, sharex=ax1)
    for col in ['strategy_基础超买超卖', 'strategy_RSI 背离', 'strategy_RSI+ 趋势']:
        if col in df.columns:
            cumulative = (1 + df[col]).cumprod()
            ax4.plot(df['date'], cumulative, label=col.replace('strategy_', ''), linewidth=2)
    
    df['cumulative_bh'] = (1 + df['close'].pct_change()).cumprod()
    ax4.plot(df['date'], df['cumulative_bh'], label='买入持有', linewidth=2, linestyle=':', color='gray')
    
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.set_title('策略累计收益对比')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_rsi_strategy.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：{code}_rsi_strategy.png")
    plt.show()

# ==================== 8. 主函数 ====================
if __name__ == '__main__':
    CODE = 'sh.600000'
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    print(f"🚀 开始 RSI 策略回测：{CODE}")
    
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"✅ 数据获取完成，共 {len(df)} 个交易日")
    
    df = calculate_rsi(df)
    df = strategy_basic_rsi(df)
    df = strategy_rsi_divergence(df)
    df = strategy_rsi_with_trend(df)
    
    results = backtest_all(df, CODE)
    plot_results(df, CODE)
