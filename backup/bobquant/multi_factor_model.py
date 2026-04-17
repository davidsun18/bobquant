# -*- coding: utf-8 -*-
"""
多因子模型 - 机构常用的量化方法
把多个指标组合成打分系统，综合决策
"""

import pandas as pd
import numpy as np
import baostock as bs
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

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

# ==================== 2. 计算多个因子 ====================
def calculate_factors(df):
    """
    计算 5 个经典因子：
    1. 动量因子 (MACD)
    2. 波动因子 (布林带位置)
    3. 超买超卖因子 (RSI)
    4. 成交量因子 (量比)
    5. 趋势因子 (均线排列)
    """
    df = df.copy()
    
    # === 因子 1: MACD 动量 ===
    df['ma1'] = df['close'].rolling(12).mean()
    df['ma2'] = df['close'].rolling(26).mean()
    df['macd_signal'] = np.where(df['ma1'] > df['ma2'], 1, -1)
    
    # === 因子 2: 布林带位置 ===
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_signal'] = np.where(df['bb_position'] < 0.2, 1, np.where(df['bb_position'] > 0.8, -1, 0))
    
    # === 因子 3: RSI 超买超卖 ===
    df['delta'] = df['close'].diff()
    df['gain'] = df['delta'].apply(lambda x: x if x > 0 else 0)
    df['loss'] = df['delta'].apply(lambda x: abs(x) if x < 0 else 0)
    df['avg_gain'] = df['gain'].rolling(14).mean()
    df['avg_loss'] = df['loss'].rolling(14).mean()
    df['rs'] = df['avg_gain'] / df['avg_loss']
    df['rsi'] = 100 - (100 / (1 + df['rs']))
    df['rsi_signal'] = np.where(df['rsi'] < 30, 1, np.where(df['rsi'] > 70, -1, 0))
    
    # === 因子 4: 成交量因子 ===
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    df['volume_signal'] = np.where(df['volume_ratio'] > 1.5, 1, np.where(df['volume_ratio'] < 0.7, -1, 0))
    
    # === 因子 5: 趋势因子 ===
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['trend_score'] = (
        (df['ma5'] > df['ma10']).astype(int) +
        (df['ma10'] > df['ma20']).astype(int) +
        (df['close'] > df['ma20']).astype(int)
    )
    df['trend_signal'] = np.where(df['trend_score'] >= 2, 1, -1)
    
    return df

# ==================== 3. 多因子打分 ====================
def multi_factor_score(df, weights=None):
    """
    多因子打分系统
    可以等权重，也可以自定义权重
    """
    df = df.copy()
    
    if weights is None:
        # 等权重
        weights = {
            'macd_signal': 0.2,
            'bb_signal': 0.2,
            'rsi_signal': 0.2,
            'volume_signal': 0.2,
            'trend_signal': 0.2
        }
    
    # 计算综合得分
    df['total_score'] = (
        df['macd_signal'] * weights['macd_signal'] +
        df['bb_signal'] * weights['bb_signal'] +
        df['rsi_signal'] * weights['rsi_signal'] +
        df['volume_signal'] * weights['volume_signal'] +
        df['trend_signal'] * weights['trend_signal']
    )
    
    # 根据得分生成信号
    # 得分 > 0.3: 买入，得分 < -0.3: 卖出，其他：持仓不变
    df['signal'] = 0
    df.loc[df['total_score'] > 0.3, 'signal'] = 1
    df.loc[df['total_score'] < -0.3, 'signal'] = -1
    
    # 生成持仓
    df['positions'] = 0
    in_position = False
    
    for i in range(1, len(df)):
        if df['signal'].iloc[i] == 1:
            in_position = True
        elif df['signal'].iloc[i] == -1:
            in_position = False
        df.loc[df.index[i], 'positions'] = 1 if in_position else 0
    
    return df

# ==================== 4. 回测统计 ====================
def backtest(df, code):
    print("\n" + "="*70)
    print(f"📊 {code} 多因子模型回测")
    print("="*70)
    
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['positions'].shift(1) * df['returns']
    
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
    
    # 交易次数
    trades = len(df[df['signal'] != 0])
    
    # 胜率
    trade_returns = []
    signals = df[df['signal'] != 0].index
    for i in range(len(signals) - 1):
        if df.loc[signals[i], 'signal'] == 1 and df.loc[signals[i+1], 'signal'] == -1:
            ret = (df['close'].iloc[signals.get_loc(signals[i+1])] - 
                   df['close'].iloc[signals.get_loc(signals[i])]) / df['close'].iloc[signals.get_loc(signals[i])]
            trade_returns.append(ret)
    
    win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns) if trade_returns else 0
    
    print(f"总交易日数：{len(df)}")
    print(f"交易次数：{trades}")
    print(f"\n📈 收益指标:")
    print(f"  策略总收益：{total_return:.2%}")
    print(f"  买入持有收益：{buy_hold:.2%}")
    print(f"  超额收益：{total_return - buy_hold:.2%}")
    print(f"  最大回撤：{max_dd:.2%}")
    print(f"  夏普比率：{sharpe:.2f}")
    print(f"\n🎯 交易质量:")
    print(f"  胜率：{win_rate:.2%}")
    if trade_returns:
        print(f"  平均盈利：{np.mean([r for r in trade_returns if r > 0]):.2%}")
        print(f"  平均亏损：{np.mean([r for r in trade_returns if r < 0]):.2%}")
    
    # 与单一策略对比
    print(f"\n🆚 与单一策略对比:")
    print(f"  MACD 终极版：+0.59%")
    print(f"  布林带均值回归：+11.97%")
    print(f"  多因子模型：{total_return:.2%}")
    
    return {
        'total_return': total_return,
        'buy_hold': buy_hold,
        'excess': total_return - buy_hold,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'win_rate': win_rate
    }

# ==================== 5. 因子有效性分析 ====================
def factor_analysis(df):
    """分析每个因子的有效性"""
    print("\n" + "="*70)
    print("📊 因子有效性分析")
    print("="*70)
    
    factors = ['macd_signal', 'bb_signal', 'rsi_signal', 'volume_signal', 'trend_signal']
    
    results = []
    for factor in factors:
        # 计算因子 IC（信息系数）
        df['factor_ret'] = df[factor] * df['close'].pct_change().shift(-1)
        ic = df['factor_ret'].corr(df[factor])
        
        results.append({
            '因子': factor.replace('_signal', ''),
            'IC': ic,
            '有效性': '✅' if abs(ic) > 0.02 else '⚠️'
        })
    
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    best_factor = results_df.loc[results_df['IC'].abs().idxmax()]
    print(f"\n🏆 最有效因子：{best_factor['因子']} (IC={best_factor['IC']:.4f})")
    
    return results_df

# ==================== 6. 绘图 ====================
def plot_results(df, code):
    fig = plt.figure(figsize=(16, 12))
    
    # 图 1：价格 + 买卖点
    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    
    buy_idx = df[df['signal'] == 1].index
    sell_idx = df[df['signal'] == -1].index
    
    if len(buy_idx) > 0:
        ax1.scatter(df.loc[buy_idx, 'date'], df.loc[buy_idx, 'close'], 
                   color='green', marker='^', s=120, label='买入', zorder=5, edgecolors='white')
    if len(sell_idx) > 0:
        ax1.scatter(df.loc[sell_idx, 'date'], df.loc[sell_idx, 'close'], 
                   color='red', marker='v', s=120, label='卖出', zorder=5, edgecolors='white')
    
    ax1.set_title(f'{code} 多因子模型策略', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 图 2：综合得分
    ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    ax2.plot(df['date'], df['total_score'], label='综合得分', linewidth=1.5, color='purple')
    ax2.axhline(0.3, color='green', linestyle='--', label='买入线 (0.3)', alpha=0.7)
    ax2.axhline(-0.3, color='red', linestyle='--', label='卖出线 (-0.3)', alpha=0.7)
    ax2.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax2.fill_between(df['date'], -0.3, 0.3, alpha=0.2, color='gray', label='观望区')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('多因子综合得分')
    
    # 图 3：收益曲线
    ax3 = plt.subplot(3, 1, 3, sharex=ax1)
    df['cumulative'] = (1 + df['strategy_returns']).cumprod()
    df['cumulative_bh'] = (1 + df['close'].pct_change()).cumprod()
    ax3.plot(df['date'], df['cumulative'], label='多因子策略', linewidth=2)
    ax3.plot(df['date'], df['cumulative_bh'], label='买入持有', linewidth=2, linestyle=':', color='gray')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_title('累计收益对比')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/{code}_multi_factor.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：{code}_multi_factor.png")
    plt.show()

# ==================== 7. 主函数 ====================
if __name__ == '__main__':
    CODE = 'sh.600000'
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    print("="*70)
    print("🎓 多因子模型教程")
    print("="*70)
    print(f"回测标的：{CODE}")
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    
    df = get_stock_data(CODE, START_DATE, END_DATE)
    print(f"\n✅ 数据获取完成，共 {len(df)} 个交易日")
    
    # 计算因子
    df = calculate_factors(df)
    print("✅ 因子计算完成")
    
    # 多因子打分
    df = multi_factor_score(df)
    print("✅ 多因子打分完成")
    
    # 因子分析
    factor_analysis(df)
    
    # 回测
    stats = backtest(df, CODE)
    
    # 绘图
    plot_results(df, CODE)
    
    print("\n" + "="*70)
    print("📚 多因子模型核心优势")
    print("="*70)
    print("""
1. 分散风险：不依赖单一指标
2. 更稳定：多个信号互相验证
3. 可解释：知道每个因子的贡献
4. 易优化：可以调整因子权重
5. 机构常用：专业量化基金的标准方法

下一步：
- 尝试不同因子组合
- 优化因子权重
- 加入基本面因子（PE、PB 等）
- 批量测试多只股票
    """)
