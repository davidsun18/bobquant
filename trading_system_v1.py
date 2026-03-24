# -*- coding: utf-8 -*-
"""
完整量化交易系统 v1.0
集成所有策略，自动生成交易信号
"""

import pandas as pd
import numpy as np
import baostock as bs
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==================== 配置 ====================
CONFIG = {
    'stock_pool': [
        # 银行
        ('sh.600000', '浦发银行', 'bollinger'),
        ('sh.600036', '招商银行', 'bollinger'),
        ('sh.601398', '工商银行', 'bollinger'),
        ('sh.601288', '农业银行', 'bollinger'),
        
        # 科技
        ('sz.300750', '宁德时代', 'macd'),
        ('sz.002594', '比亚迪', 'macd'),
        ('sh.601138', '工业富联', 'macd'),
        
        # 消费
        ('sz.000333', '美的集团', 'bollinger'),
        ('sh.600887', '伊利股份', 'bollinger'),
        ('sh.600276', '恒瑞医药', 'macd'),
        
        # 白酒
        ('sh.600519', '贵州茅台', 'bollinger'),
        ('sh.000858', '五粮液', 'macd'),
    ],
    'start_date': '2023-01-01',
    'end_date': datetime.now().strftime('%Y-%m-%d'),
    'output_dir': '/home/openclaw/.openclaw/workspace/quant_strategies/signals/'
}

# ==================== 1. 获取数据 ====================
def get_stock_data(code, start_date, end_date):
    """获取单只股票数据"""
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        code,
        "date,open,high,low,close,volume",
        start_date=start_date,
        end_date=end_date,
        frequency="d"
    )
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    df = pd.DataFrame(data, columns=rs.fields)
    bs.logout()
    
    if len(df) > 0:
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
    return df

# ==================== 2. MACD 策略 ====================
def macd_strategy(df):
    """MACD 策略信号"""
    df = df.copy()
    df['ma1'] = df['close'].rolling(12).mean()
    df['ma2'] = df['close'].rolling(26).mean()
    df['trend_up'] = df['ma2'] > df['ma2'].shift(5)
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ok'] = df['volume'] > df['volume_ma']
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    signal = '观望'
    reason = ''
    
    # 金叉 + 趋势向上 + 放量 = 买入
    if (latest['ma1'] > latest['ma2'] and prev['ma1'] <= prev['ma2'] and 
        latest['trend_up'] and latest['volume_ok']):
        signal = '买入'
        reason = 'MACD 金叉 + 趋势向上 + 放量'
    
    # 死叉 = 卖出
    elif latest['ma1'] < latest['ma2'] and prev['ma1'] >= prev['ma2']:
        signal = '卖出'
        reason = 'MACD 死叉'
    
    return {
        '策略': 'MACD',
        '信号': signal,
        '理由': reason,
        '当前价': latest['close'],
        'MA1': latest['ma1'],
        'MA2': latest['ma2'],
        '趋势': '向上' if latest['trend_up'] else '向下'
    }

# ==================== 3. 布林带策略 ====================
def bollinger_strategy(df):
    """布林带均值回归策略"""
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_pos'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    latest = df.iloc[-1]
    
    signal = '观望'
    reason = ''
    
    # 触及下轨 = 买入
    if latest['bb_pos'] < 0.1:
        signal = '买入'
        reason = f'布林带下轨附近 (%B={latest["bb_pos"]:.2f})'
    
    # 触及上轨 = 卖出
    elif latest['bb_pos'] > 0.9:
        signal = '卖出'
        reason = f'布林带上轨附近 (%B={latest["bb_pos"]:.2f})'
    
    # 回归中轨 = 平仓
    elif 0.4 < latest['bb_pos'] < 0.6:
        signal = '平仓'
        reason = '价格回归中轨'
    
    return {
        '策略': '布林带',
        '信号': signal,
        '理由': reason,
        '当前价': latest['close'],
        '%B': latest['bb_pos'],
        '上轨': latest['bb_upper'],
        '中轨': latest['bb_mid'],
        '下轨': latest['bb_lower']
    }

# ==================== 4. RSI 策略 ====================
def rsi_strategy(df):
    """RSI 超买超卖策略"""
    df = df.copy()
    delta = df['close'].diff()
    gain = delta.apply(lambda x: x if x > 0 else 0)
    loss = delta.apply(lambda x: abs(x) if x < 0 else 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    latest = df.iloc[-1]
    
    signal = '观望'
    reason = ''
    
    if latest['rsi'] < 30:
        signal = '买入'
        reason = f'RSI 超卖 ({latest["rsi"]:.1f})'
    elif latest['rsi'] > 70:
        signal = '卖出'
        reason = f'RSI 超买 ({latest["rsi"]:.1f})'
    
    return {
        '策略': 'RSI',
        '信号': signal,
        '理由': reason,
        '当前价': latest['close'],
        'RSI': latest['rsi']
    }

# ==================== 5. 综合信号 ====================
def generate_signals(code, name, recommended_strategy):
    """生成综合信号"""
    df = get_stock_data(code, CONFIG['start_date'], CONFIG['end_date'])
    
    if len(df) < 30:
        return None
    
    # 运行所有策略
    macd_sig = macd_strategy(df)
    bb_sig = bollinger_strategy(df)
    rsi_sig = rsi_strategy(df)
    
    # 综合判断
    signals = [macd_sig, bb_sig, rsi_sig]
    buy_count = sum(1 for s in signals if s['信号'] == '买入')
    sell_count = sum(1 for s in signals if s['信号'] == '卖出')
    
    # 最终信号
    if buy_count >= 2:
        final_signal = '强烈买入'
        confidence = '⭐⭐⭐⭐⭐' if buy_count == 3 else '⭐⭐⭐⭐'
    elif buy_count == 1:
        final_signal = '谨慎买入'
        confidence = '⭐⭐⭐'
    elif sell_count >= 2:
        final_signal = '强烈卖出'
        confidence = '⭐⭐⭐⭐⭐' if sell_count == 3 else '⭐⭐⭐⭐'
    elif sell_count == 1:
        final_signal = '谨慎卖出'
        confidence = '⭐⭐⭐'
    else:
        final_signal = '观望'
        confidence = '⭐⭐'
    
    return {
        '代码': code,
        '名称': name,
        '推荐策略': recommended_strategy,
        '最终信号': final_signal,
        '置信度': confidence,
        '买入信号': buy_count,
        '卖出信号': sell_count,
        'MACD': macd_sig['信号'],
        '布林带': bb_sig['信号'],
        'RSI': rsi_sig['信号'],
        '当前价': f"{df.iloc[-1]['close']:.2f}",
        '日期': df.iloc[-1]['date']
    }

# ==================== 6. 生成报告 ====================
def generate_report():
    """生成交易信号报告"""
    print("="*80)
    print("📊 量化交易系统 - 每日信号")
    print("="*80)
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"股票池：{len(CONFIG['stock_pool'])} 只")
    print("="*80)
    
    all_signals = []
    
    for code, name, strategy in CONFIG['stock_pool']:
        print(f"\n📈 分析 {code} {name}...")
        signal = generate_signals(code, name, strategy)
        if signal:
            all_signals.append(signal)
            
            # 打印摘要
            sig_emoji = '🟢' if '买入' in signal['最终信号'] else '🔴' if '卖出' in signal['最终信号'] else '⚪'
            print(f"  {sig_emoji} {signal['最终信号']} ({signal['置信度']})")
            print(f"     MACD:{signal['MACD']} | 布林带:{signal['布林带']} | RSI:{signal['RSI']}")
    
    # 转换为 DataFrame
    df_signals = pd.DataFrame(all_signals)
    
    # 保存 CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"{CONFIG['output_dir']}signals_{timestamp}.csv"
    df_signals.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    # 打印汇总
    print("\n" + "="*80)
    print("📊 信号汇总")
    print("="*80)
    
    buy_signals = df_signals[df_signals['最终信号'].str.contains('买入', na=False)]
    sell_signals = df_signals[df_signals['最终信号'].str.contains('卖出', na=False)]
    
    print(f"\n🟢 买入信号：{len(buy_signals)} 只")
    if len(buy_signals) > 0:
        for _, row in buy_signals.iterrows():
            print(f"  {row['代码']} {row['名称']} - {row['最终信号']} {row['置信度']}")
    
    print(f"\n🔴 卖出信号：{len(sell_signals)} 只")
    if len(sell_signals) > 0:
        for _, row in sell_signals.iterrows():
            print(f"  {row['代码']} {row['名称']} - {row['最终信号']} {row['置信度']}")
    
    print(f"\n⚪ 观望：{len(df_signals) - len(buy_signals) - len(sell_signals)} 只")
    
    print(f"\n💾 报告已保存：{csv_file}")
    
    # 生成可视化
    plot_signals(df_signals)
    
    return df_signals

# ==================== 7. 可视化 ====================
def plot_signals(df_signals):
    """生成信号分布图"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 图 1：信号分布
    ax1 = axes[0, 0]
    signal_counts = df_signals['最终信号'].value_counts()
    colors = {'强烈买入': 'green', '谨慎买入': 'lightgreen', '观望': 'gray', 
              '谨慎卖出': 'orange', '强烈卖出': 'red'}
    signal_counts.plot(kind='bar', ax=ax1, color=[colors.get(x, 'gray') for x in signal_counts.index])
    ax1.set_title('信号分布')
    ax1.tick_params(axis='x', rotation=45)
    
    # 图 2：策略对比
    ax2 = axes[0, 1]
    strategy_perf = {
        'MACD': (df_signals['MACD'] == '买入').sum(),
        '布林带': (df_signals['布林带'] == '买入').sum(),
        'RSI': (df_signals['RSI'] == '买入').sum()
    }
    ax2.bar(strategy_perf.keys(), strategy_perf.values(), color=['blue', 'green', 'purple'])
    ax2.set_title('各策略买入信号数量')
    ax2.tick_params(axis='x', rotation=45)
    
    # 图 3：置信度分布
    ax3 = axes[1, 0]
    conf_counts = df_signals['置信度'].value_counts()
    conf_counts.plot(kind='pie', ax=ax3, autopct='%1.1f%%')
    ax3.set_title('置信度分布')
    
    # 图 4：板块分布
    ax4 = axes[1, 1]
    sectors = {
        '银行': ['sh.600000', 'sh.600036', 'sh.601398', 'sh.601288'],
        '科技': ['sz.300750', 'sz.002594', 'sh.601138'],
        '消费': ['sz.000333', 'sh.600887', 'sh.600276'],
        '白酒': ['sh.600519', 'sh.000858']
    }
    
    sector_signals = {}
    for sector, codes in sectors.items():
        sector_df = df_signals[df_signals['代码'].isin(codes)]
        if len(sector_df) > 0:
            buy_ratio = (sector_df['最终信号'].str.contains('买入')).sum() / len(sector_df)
            sector_signals[sector] = buy_ratio * 100
    
    ax4.bar(sector_signals.keys(), sector_signals.values(), color='coral')
    ax4.set_title('板块买入信号比例 (%)')
    ax4.tick_params(axis='x', rotation=45)
    ax4.set_ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig(f"{CONFIG['output_dir']}signals_dashboard.png", dpi=150, bbox_inches='tight')
    print(f"📊 图表已保存：signals_dashboard.png")
    plt.show()

# ==================== 8. 主函数 ====================
if __name__ == '__main__':
    import os
    os.makedirs(CONFIG['output_dir'], exist_ok=True)
    
    signals = generate_report()
    
    print("\n" + "="*80)
    print("📚 使用说明")
    print("="*80)
    print("""
✅ 系统功能:
1. 自动获取最新数据
2. 运行 3 个策略 (MACD/布林带/RSI)
3. 综合判断生成信号
4. 保存 CSV 报告和可视化图表

📊 信号解读:
- 强烈买入 (⭐⭐⭐⭐⭐): 3 个策略都看涨
- 谨慎买入 (⭐⭐⭐): 1-2 个策略看涨
- 观望 (⭐⭐): 信号不一致
- 谨慎卖出 (⭐⭐⭐): 1-2 个策略看跌
- 强烈卖出 (⭐⭐⭐⭐⭐): 3 个策略都看跌

⚠️ 风险提示:
1. 本系统仅供参考，不构成投资建议
2. 建议结合基本面分析
3. 设置好止损位 (建议 5-8%)
4. 控制仓位 (单只股票不超过 20%)

🔄 定期运行:
- 每日收盘后运行一次
- 周末复盘本周信号
- 每月调整股票池
    """)
