# -*- coding: utf-8 -*-
"""
MACD 策略简化版 - 适合新手学习
使用 Baostock 获取 A 股数据
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
    bs.logout()
    return df

# ==================== 2. 计算 MACD ====================
def calculate_macd(df, ma1=12, ma2=26):
    """计算 MACD 指标"""
    df = df.copy()
    
    # 计算双均线
    df['ma1'] = df['close'].rolling(window=ma1, min_periods=1).mean()
    df['ma2'] = df['close'].rolling(window=ma2, min_periods=1).mean()
    
    # MACD 振荡器
    df['oscillator'] = df['ma1'] - df['ma2']
    
    # 生成持仓信号
    df['positions'] = 0
    df.loc[ma1:, 'positions'] = np.where(
        df.loc[ma1:, 'ma1'] >= df.loc[ma1:, 'ma2'], 
        1, 0
    )
    
    # 交易信号
    df['signals'] = df['positions'].diff()
    
    return df

# ==================== 3. 回测统计 ====================
def backtest_stats(df):
    """计算回测统计"""
    # 只计算有信号的部分
    trades = df[df['signals'] != 0]
    
    print("\n" + "="*50)
    print("📊 回测统计")
    print("="*50)
    print(f"总交易日数：{len(df)}")
    print(f"交易次数：{len(trades)}")
    print(f"买入次数：{len(trades[trades['signals'] == 1])}")
    print(f"卖出次数：{len(trades[trades['signals'] == -1])}")
    
    # 计算收益
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['positions'].shift(1) * df['returns']
    
    total_return = (1 + df['strategy_returns']).prod() - 1
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
    
    print(f"\n策略总收益：{total_return:.2%}")
    print(f"买入持有收益：{buy_hold_return:.2%}")
    print(f"超额收益：{total_return - buy_hold_return:.2%}")
    
    return df

# ==================== 4. 绘图 ====================
def plot_results(df, code):
    """绘制回测结果"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # 图 1：价格 + 买卖点
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1)
    
    # 标记买卖点
    buy_idx = df[df['signals'] == 1].index
    sell_idx = df[df['signals'] == -1].index
    
    if len(buy_idx) > 0:
        ax1.scatter(df.loc[buy_idx, 'date'], df.loc[buy_idx, 'close'], 
                   color='green', marker='^', s=100, label='买入', zorder=5)
    if len(sell_idx) > 0:
        ax1.scatter(df.loc[sell_idx, 'date'], df.loc[sell_idx, 'close'], 
                   color='red', marker='v', s=100, label='卖出', zorder=5)
    
    ax1.set_title(f'{code} MACD 策略回测')
    ax1.legend()
    ax1.grid(True)
    
    # 图 2：MACD 振荡器
    ax2.bar(df['date'], df['oscillator'], color=np.where(df['oscillator'] >= 0, 'red', 'green'), 
            alpha=0.7, label='MACD 振荡器')
    ax2.axhline(0, color='black', linewidth=0.5)
    ax2.legend()
    ax2.grid(True)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_macd_result.png', dpi=150)
    print(f"\n✅ 图表已保存：{code}_macd_result.png")
    plt.show()

# ==================== 5. 主函数 ====================
if __name__ == '__main__':
    # 参数设置
    CODE = 'sh.600000'  # 浦发银行
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    MA1 = 12
    MA2 = 26
    
    print(f"🚀 开始 MACD 策略回测：{CODE}")
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    print(f"均线参数：MA1={MA1}, MA2={MA2}")
    
    # 获取数据
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"✅ 数据获取完成，共 {len(df)} 个交易日")
    
    # 计算 MACD
    df = calculate_macd(df, MA1, MA2)
    
    # 回测统计
    df = backtest_stats(df)
    
    # 绘图
    plot_results(df, CODE)
