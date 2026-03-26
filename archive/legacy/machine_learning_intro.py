# -*- coding: utf-8 -*-
"""
机器学习量化交易入门
用随机森林预测明天涨跌
"""

import pandas as pd
import numpy as np
import baostock as bs
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("🤖 机器学习量化交易教程")
print("="*70)

# ==================== 1. 获取数据 ====================
def get_data(code, start_date, end_date):
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
    df['close'] = df['close'].astype(float)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    bs.logout()
    return df

# ==================== 2. 构建特征 ====================
def create_features(df):
    """
    构建机器学习特征
    """
    df = df.copy()
    
    # === 技术指标特征 ===
    # MACD
    df['ma1'] = df['close'].rolling(12).mean()
    df['ma2'] = df['close'].rolling(26).mean()
    df['macd'] = df['ma1'] - df['ma2']
    
    # RSI
    df['delta'] = df['close'].diff()
    df['gain'] = df['delta'].apply(lambda x: x if x > 0 else 0)
    df['loss'] = df['delta'].apply(lambda x: abs(x) if x < 0 else 0)
    df['avg_gain'] = df['gain'].rolling(14).mean()
    df['avg_loss'] = df['loss'].rolling(14).mean()
    df['rs'] = df['avg_gain'] / df['avg_loss']
    df['rsi'] = 100 - (100 / (1 + df['rs']))
    
    # 布林带
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # 成交量
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    
    # 动量
    df['momentum_5'] = df['close'].pct_change(5)
    df['momentum_10'] = df['close'].pct_change(10)
    
    # 波动率
    df['volatility'] = df['close'].pct_change().rolling(20).std()
    
    # === 价格特征 ===
    df['return_1d'] = df['close'].pct_change()
    df['return_3d'] = df['close'].pct_change(3)
    df['return_5d'] = df['close'].pct_change(5)
    
    # === 标签：明天是否上涨 ===
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    return df

# ==================== 3. 训练模型 ====================
def train_model(df):
    """训练随机森林模型"""
    
    # 特征列表
    feature_cols = [
        'macd', 'rsi', 'bb_position', 'volume_ratio',
        'momentum_5', 'momentum_10', 'volatility',
        'return_1d', 'return_3d', 'return_5d'
    ]
    
    # 删除 NaN
    df_clean = df.dropna()
    
    if len(df_clean) < 100:
        print("⚠️ 数据不足")
        return None, None, None
    
    X = df_clean[feature_cols]
    y = df_clean['target']
    
    # 训练集/测试集分割（80%/20%）
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False
    )
    
    print(f"\n📊 数据集划分:")
    print(f"  训练集：{len(X_train)} 样本")
    print(f"  测试集：{len(X_test)} 样本")
    
    # 训练随机森林
    print("\n🤖 训练随机森林模型...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_split=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # 测试集评估
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n✅ 模型准确率：{accuracy:.2%}")
    print(f"\n📊 分类报告:")
    print(classification_report(y_test, y_pred, target_names=['跌', '涨']))
    
    # 特征重要性
    feature_importance = pd.DataFrame({
        '特征': feature_cols,
        '重要性': model.feature_importances_
    }).sort_values('重要性', ascending=False)
    
    print(f"\n🏆 特征重要性排名:")
    print(feature_importance.to_string(index=False))
    
    return model, feature_cols, feature_importance

# ==================== 4. 回测策略 ====================
def backtest_strategy(df, model, feature_cols):
    """用模型预测进行回测"""
    
    df = df.copy()
    df_clean = df.dropna()
    
    # 预测
    X = df_clean[feature_cols]
    df_clean['prediction'] = model.predict(X)
    df_clean['prob_up'] = model.predict_proba(X)[:, 1]  # 上涨概率
    
    # 策略：预测上涨时持仓
    df_clean['positions'] = df_clean['prediction']
    df_clean['strategy_returns'] = df_clean['positions'].shift(1) * df_clean['return_1d']
    
    # 计算收益
    total_return = (1 + df_clean['strategy_returns']).prod() - 1
    buy_hold = (df_clean['close'].iloc[-1] / df_clean['close'].iloc[0]) - 1
    
    # 最大回撤
    cumulative = (1 + df_clean['strategy_returns']).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_dd = drawdown.min()
    
    # 夏普比率
    excess = df_clean['strategy_returns'] - 0.03/252
    sharpe = np.sqrt(252) * excess.mean() / excess.std() if excess.std() > 0 else 0
    
    print("\n" + "="*70)
    print("📊 机器学习策略回测")
    print("="*70)
    print(f"策略总收益：{total_return:.2%}")
    print(f"买入持有收益：{buy_hold:.2%}")
    print(f"超额收益：{total_return - buy_hold:.2%}")
    print(f"最大回撤：{max_dd:.2%}")
    print(f"夏普比率：{sharpe:.2f}")
    
    # 与经典策略对比
    print(f"\n🆚 与经典策略对比:")
    print(f"  MACD 终极版：+0.59%")
    print(f"  布林带均值回归：+11.97%")
    print(f"  多因子模型：-8.52%")
    print(f"  机器学习：{total_return:.2%}")
    
    return df_clean, total_return

# ==================== 5. 绘图 ====================
def plot_results(df, df_ml):
    fig = plt.figure(figsize=(16, 10))
    
    # 图 1：价格 + 预测信号
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(df['date'], df['close'], label='收盘价', linewidth=1.5, color='#333')
    
    # 标记预测正确的点
    correct_up = df_ml[(df_ml['prediction'] == 1) & (df_ml['return_1d'].shift(-1) > 0)].index
    correct_down = df_ml[(df_ml['prediction'] == 0) & (df_ml['return_1d'].shift(-1) <= 0)].index
    
    if len(correct_up) > 0:
        ax1.scatter(df.loc[correct_up, 'date'], df.loc[correct_up, 'close'], 
                   color='green', alpha=0.5, s=50, label='预测上涨✓', zorder=5)
    if len(correct_down) > 0:
        ax1.scatter(df.loc[correct_down, 'date'], df.loc[correct_down, 'close'], 
                   color='red', alpha=0.5, s=50, label='预测下跌✓', zorder=5)
    
    ax1.set_title('机器学习预测结果', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 图 2：预测概率 + 收益曲线
    ax2 = plt.subplot(2, 1, 2, sharex=ax1)
    df_ml['cumulative'] = (1 + df_ml['strategy_returns']).cumprod()
    df_ml['cumulative_bh'] = (1 + df_ml['return_1d']).cumprod()
    
    ax2.plot(df_ml['date'], df_ml['cumulative'], label='机器学习策略', linewidth=2)
    ax2.plot(df_ml['date'], df_ml['cumulative_bh'], label='买入持有', linewidth=2, linestyle=':', color='gray')
    
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title('累计收益对比')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'/home/openclaw/.openclaw/workspace/quant_strategies/machine_learning_result.png', dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存：machine_learning_result.png")
    plt.show()

# ==================== 6. 主函数 ====================
if __name__ == '__main__':
    CODE = 'sh.600000'
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    print(f"回测标的：{CODE}")
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    
    # 获取数据
    df = get_data(CODE, START_DATE, END_DATE)
    print(f"\n✅ 数据获取完成，共 {len(df)} 个交易日")
    
    # 构建特征
    df = create_features(df)
    print("✅ 特征构建完成")
    
    # 训练模型
    model, feature_cols, feature_importance = train_model(df)
    
    if model is not None:
        # 回测
        df_ml, total_return = backtest_strategy(df, model, feature_cols)
        
        # 绘图
        plot_results(df, df_ml)
        
        print("\n" + "="*70)
        print("📚 机器学习量化核心要点")
        print("="*70)
        print("""
1. 特征工程：把技术指标变成机器学习特征
2. 标签定义：预测明天涨跌（二分类）
3. 模型选择：随机森林（简单有效）
4. 数据分割：时间序列不能随机 shuffle
5. 过拟合风险：训练集表现好≠测试集好

优势：
✅ 自动学习规律
✅ 可以处理复杂非线性关系
✅ 可以加入大量特征

风险：
⚠️ 过拟合（记住历史而非学习规律）
⚠️ 市场风格变化快
⚠️ 需要大量数据

建议：
- 用更多股票训练（提高泛化能力）
- 定期重新训练（适应市场变化）
- 结合传统策略（不要完全依赖 ML）
        """)
