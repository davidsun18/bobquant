# -*- coding: utf-8 -*-
"""
MACD 策略终极优化版 - 加入止盈 + 动态止损 + 参数优化
改进点：
1. 止盈机制：赚到钱落袋为安
2. 动态止损：根据 ATR 波动率调整
3. 参数优化：测试不同均线组合
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import baostock as bs
from itertools import product

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

# ==================== 2. 计算 ATR（平均真实波幅）====================
def calculate_atr(df, period=14):
    """计算 ATR 指标，用于动态止损"""
    df = df.copy()
    
    # 计算真实波幅 TR
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    # 计算 ATR
    df['atr'] = df['tr'].rolling(window=period, min_periods=1).mean()
    
    return df

# ==================== 3. 计算终极优化版 MACD ====================
def calculate_ultimate_macd(df, ma1=12, ma2=26, volume_window=20, 
                           stop_loss=0.05, take_profit=0.10, use_atr=True, atr_multiplier=2.5):
    """
    终极优化版 MACD，加入：
    - 趋势过滤（ma2 向上）
    - 成交量确认（放量）
    - 动态止损（基于 ATR）
    - 止盈机制
    """
    df = df.copy()
    
    # --- 基础 MACD 计算 ---
    df['ma1'] = df['close'].rolling(window=ma1, min_periods=1).mean()
    df['ma2'] = df['close'].rolling(window=ma2, min_periods=1).mean()
    df['oscillator'] = df['ma1'] - df['ma2']
    
    # --- 计算 ATR ---
    if use_atr:
        df = calculate_atr(df)
    
    # --- 过滤条件 1: 趋势过滤 ---
    df['ma2_slope'] = df['ma2'] - df['ma2'].shift(5)
    df['trend_ok'] = df['ma2_slope'] > 0
    
    # --- 过滤条件 2: 成交量确认 ---
    df['volume_ma'] = df['volume'].rolling(window=volume_window, min_periods=1).mean()
    df['volume_ok'] = df['volume'] > df['volume_ma']
    
    # --- 生成基础持仓信号 ---
    df['positions'] = 0
    df.loc[ma2:, 'positions'] = np.where(
        (df.loc[ma2:, 'ma1'] >= df.loc[ma2:, 'ma2']), 
        1, 0
    )
    
    # --- 应用过滤条件 ---
    df['filtered_positions'] = df['positions'] & df['trend_ok'] & df['volume_ok']
    df['filtered_positions'] = df['filtered_positions'].astype(int)
    
    # --- 交易信号 + 止损止盈 ---
    df['signals'] = 0
    df['stop_loss_triggered'] = False
    df['take_profit_triggered'] = False
    df['entry_price'] = np.nan
    df['highest_price_since_entry'] = np.nan
    
    in_position = False
    entry_price = 0
    highest_price = 0
    
    for i in range(1, len(df)):
        current_close = df['close'].iloc[i]
        current_high = df['high'].iloc[i]
        current_atr = df['atr'].iloc[i] if use_atr else 0
        
        # 动态止损：基于 ATR 或固定比例
        if use_atr and current_atr > 0:
            dynamic_stop_loss = entry_price - (atr_multiplier * current_atr)
        else:
            dynamic_stop_loss = entry_price * (1 - stop_loss)
        
        # 动态止盈：移动止盈（跟踪止损）
        if in_position and current_high > highest_price:
            highest_price = current_high
        
        trailing_stop = highest_price * (1 - take_profit / 2) if highest_price > 0 else 0
        
        if df['filtered_positions'].iloc[i] == 1 and not in_position:  # 买入信号
            in_position = True
            entry_price = current_close
            highest_price = current_high
            df.loc[df.index[i], 'signals'] = 1
            df.loc[df.index[i], 'entry_price'] = entry_price
        
        elif in_position:
            df.loc[df.index[i], 'entry_price'] = entry_price
            df.loc[df.index[i], 'highest_price_since_entry'] = highest_price
            
            # 检查止损
            if current_close < dynamic_stop_loss:
                df.loc[df.index[i], 'stop_loss_triggered'] = True
                df.loc[df.index[i], 'signals'] = -1
                in_position = False
                entry_price = 0
                highest_price = 0
            
            # 检查止盈（移动止盈）
            elif take_profit > 0 and highest_price > entry_price * (1 + take_profit / 2):
                if current_close < trailing_stop:
                    df.loc[df.index[i], 'take_profit_triggered'] = True
                    df.loc[df.index[i], 'signals'] = -1
                    in_position = False
                    entry_price = 0
                    highest_price = 0
            
            # 基础止盈
            elif take_profit > 0 and current_close >= entry_price * (1 + take_profit):
                df.loc[df.index[i], 'take_profit_triggered'] = True
                df.loc[df.index[i], 'signals'] = -1
                in_position = False
                entry_price = 0
                highest_price = 0
            
            # 基础卖出信号
            elif df['filtered_positions'].iloc[i] == 0:
                df.loc[df.index[i], 'signals'] = -1
                in_position = False
                entry_price = 0
                highest_price = 0
    
    return df

# ==================== 4. 回测统计 ====================
def backtest_stats(df, code, stop_loss=0.05, take_profit=0.10):
    """计算回测统计"""
    trades = df[df['signals'] != 0].copy()
    
    print("\n" + "="*70)
    print(f"📊 {code} 终极优化版 MACD 回测统计")
    print("="*70)
    print(f"总交易日数：{len(df)}")
    print(f"总交易次数：{len(trades)}")
    print(f"买入次数：{len(trades[trades['signals'] == 1])}")
    print(f"卖出次数：{len(trades[trades['signals'] == -1])}")
    
    # 止损止盈统计
    stop_loss_count = df[df['stop_loss_triggered'] == True].shape[0]
    take_profit_count = df[df['take_profit_triggered'] == True].shape[0]
    print(f"\n🛡️ 风控统计:")
    print(f"  止损触发次数：{stop_loss_count}")
    print(f"  止盈触发次数：{take_profit_count}")
    
    # 过滤条件统计
    trend_filtered = (df['positions'] == 1) & (df['trend_ok'] == False)
    volume_filtered = (df['positions'] == 1) & (df['volume_ok'] == False)
    print(f"\n🔍 过滤掉的信号:")
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
    
    # 计算夏普比率
    daily_rf = 0.03 / 252
    excess_returns = df['strategy_returns'] - daily_rf
    sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
    
    # 计算卡玛比率
    calmar = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    print(f"\n📈 收益指标:")
    print(f"  策略总收益：{total_return:.2%}")
    print(f"  买入持有收益：{buy_hold_return:.2%}")
    print(f"  超额收益：{total_return - buy_hold_return:.2%}")
    print(f"  最大回撤：{max_drawdown:.2%}")
    print(f"  夏普比率：{sharpe:.2f}")
    print(f"  卡玛比率：{calmar:.2f}")
    
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
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            print(f"\n🎯 交易质量:")
            print(f"  胜率：{win_rate:.2%}")
            print(f"  平均盈利：{avg_win:.2%}")
            print(f"  平均亏损：{avg_loss:.2%}")
            print(f"  盈亏比：{profit_factor:.2f}")
            
            # 最大单笔盈利/亏损
            max_win = max(trade_returns) if trade_returns else 0
            max_loss = min(trade_returns) if trade_returns else 0
            print(f"  最大单笔盈利：{max_win:.2%}")
            print(f"  最大单笔亏损：{max_loss:.2%}")
    
    return df

# ==================== 5. 参数优化 ====================
def optimize_parameters(code, start_date, end_date):
    """测试不同均线参数组合"""
    print("\n" + "="*70)
    print("🔧 参数优化测试")
    print("="*70)
    
    df = get_stock_data(code, start_date, end_date)
    df = calculate_atr(df)
    
    results = []
    
    # 测试不同的均线组合
    ma1_list = [8, 10, 12, 15]
    ma2_list = [20, 21, 26, 30]
    
    for ma1, ma2 in product(ma1_list, ma2_list):
        if ma1 >= ma2:
            continue
            
        test_df = df.copy()
        test_df = calculate_ultimate_macd(test_df, ma1=ma1, ma2=ma2, 
                                         stop_loss=0.05, take_profit=0.10, use_atr=True)
        
        test_df['returns'] = test_df['close'].pct_change()
        test_df['strategy_returns'] = test_df['filtered_positions'].shift(1) * test_df['returns']
        
        total_return = (1 + test_df['strategy_returns']).prod() - 1
        
        # 计算最大回撤
        cumulative = (1 + test_df['strategy_returns']).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        sharpe = np.sqrt(252) * (test_df['strategy_returns'].mean() - 0.03/252) / test_df['strategy_returns'].std()
        
        results.append({
            'ma1': ma1,
            'ma2': ma2,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe': sharpe
        })
    
    # 转换为 DataFrame 并排序
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('total_return', ascending=False)
    
    print("\n前 5 名参数组合:")
    print(results_df.head(10).to_string(index=False))
    
    best = results_df.iloc[0]
    print(f"\n🏆 最佳参数：MA1={best['ma1']}, MA2={best['ma2']}")
    print(f"   收益率：{best['total_return']:.2%}")
    print(f"   最大回撤：{best['max_drawdown']:.2%}")
    print(f"   夏普比率：{best['sharpe']:.2f}")
    
    return int(best['ma1']), int(best['ma2'])

# ==================== 6. 绘图 ====================
def plot_results(df, code, ma1, ma2):
    """绘制回测结果（5 个子图）"""
    fig = plt.figure(figsize=(16, 14))
    
    # 图 1：价格 + 买卖点
    ax1 = plt.subplot(5, 1, 1)
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    
    buy_idx = df[df['signals'] == 1].index
    sell_idx = df[df['signals'] == -1].index
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
    
    ax1.set_title(f'{code} 终极优化版 MACD 策略回测 (MA1={ma1}, MA2={ma2})', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', ncol=4)
    ax1.grid(True, alpha=0.3)
    
    # 图 2：均线系统
    ax2 = plt.subplot(5, 1, 2, sharex=ax1)
    ax2.plot(df['date'], df['ma1'], label=f'MA1({ma1})', linewidth=1.5)
    ax2.plot(df['date'], df['ma2'], label=f'MA2({ma2})', linewidth=1.5, linestyle='--')
    ax2.fill_between(df['date'], df['ma2'], df['ma2'].max(), 
                    where=df['trend_ok'], alpha=0.3, color='green', label='趋势向好')
    ax2.fill_between(df['date'], df['ma2'], df['ma2'].min(), 
                    where=~df['trend_ok'], alpha=0.3, color='red', label='趋势向差')
    ax2.legend(loc='upper left', ncol=2)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('均线系统 + 趋势过滤')
    
    # 图 3：成交量
    ax3 = plt.subplot(5, 1, 3, sharex=ax1)
    ax3.bar(df['date'], df['volume'], alpha=0.7, color='#999', label='成交量')
    ax3.plot(df['date'], df['volume_ma'], label='20 日均量', linewidth=2, color='blue')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('成交量确认')
    
    # 图 4：ATR + 止损止盈
    ax4 = plt.subplot(5, 1, 4, sharex=ax1)
    ax4.plot(df['date'], df['atr'], label='ATR(14)', linewidth=1.5, color='purple')
    ax4.fill_between(df['date'], df['atr'], df['atr'].max(), 
                    alpha=0.3, color='purple', label='高波动')
    ax4.fill_between(df['date'], df['atr'], 0, 
                    where=df['atr'] < df['atr'].median(), alpha=0.3, color='cyan', label='低波动')
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.set_title('ATR 波动率（用于动态止损）')
    
    # 图 5：MACD 振荡器 + 持仓
    ax5 = plt.subplot(5, 1, 5, sharex=ax1)
    colors = np.where(df['oscillator'] >= 0, '#ff6b6b', '#4ecdc4')
    ax5.bar(df['date'], df['oscillator'], color=colors, alpha=0.8, label='MACD 振荡器')
    ax5.axhline(0, color='black', linewidth=0.8)
    
    ax5_twin = ax5.twinx()
    ax5_twin.plot(df['date'], df['filtered_positions'], label='持仓状态', 
                 linewidth=2, color='purple', linestyle='-')
    ax5_twin.set_ylim(-0.1, 1.1)
    ax5_twin.set_yticks([])
    
    ax5.legend(loc='upper left')
    ax5_twin.legend(loc='upper right')
    ax5.grid(True, alpha=0.3)
    ax5.set_title('MACD 振荡器 + 持仓状态')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_macd_ultimate.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：{code}_macd_ultimate.png")
    plt.show()

# ==================== 7. 主函数 ====================
if __name__ == '__main__':
    # 参数设置
    CODE = 'sh.600000'  # 浦发银行
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    STOP_LOSS = 0.05      # 基础止损 5%
    TAKE_PROFIT = 0.10    # 止盈 10%
    USE_ATR = True        # 使用动态止损
    ATR_MULTIPLIER = 2.5  # ATR 倍数
    
    print(f"🚀 开始终极优化版 MACD 策略回测：{CODE}")
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    print(f"基础参数：止损={STOP_LOSS*100}%, 止盈={TAKE_PROFIT*100}%")
    print(f"动态止损：ATR × {ATR_MULTIPLIER}")
    
    # 第一步：参数优化
    best_ma1, best_ma2 = optimize_parameters(CODE, START_DATE, END_DATE)
    
    # 第二步：用最优参数回测
    print(f"\n{'='*70}")
    print(f"使用最优参数回测：MA1={best_ma1}, MA2={best_ma2}")
    print(f"{'='*70}")
    
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"✅ 数据获取完成，共 {len(df)} 个交易日")
    
    df = calculate_ultimate_macd(df, ma1=best_ma1, ma2=best_ma2, 
                                stop_loss=STOP_LOSS, take_profit=TAKE_PROFIT, 
                                use_atr=USE_ATR, atr_multiplier=ATR_MULTIPLIER)
    
    df = backtest_stats(df, CODE, STOP_LOSS, TAKE_PROFIT)
    
    plot_results(df, CODE, best_ma1, best_ma2)
