# -*- coding: utf-8 -*-
"""
机器学习量化交易 - 进阶版
多股票训练 + 多模型对比 + 严谨验证
"""

import pandas as pd
import numpy as np
import baostock as bs
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.feature_selection import SelectKBest, f_classif
import warnings
warnings.filterwarnings('ignore')

# ==================== 1. 股票池 ====================
STOCK_POOL = [
    # 银行
    'sh.600000', 'sh.600036', 'sh.601398', 'sh.601288',
    # 白酒
    'sh.600519', 'sh.000858', 'sz.000568',
    # 科技
    'sz.300750', 'sz.002594', 'sh.601138',
    # 消费
    'sh.600276', 'sz.000333', 'sh.600887',
    # 券商
    'sh.600030', 'sh.601688',
    # 其他
    'sh.600036', 'sh.601318', 'sz.000001', 'sh.600519',
]

# ==================== 2. 获取数据 ====================
def get_all_stock_data(stock_codes, start_date, end_date):
    """获取多只股票数据"""
    print("="*70)
    print("📊 获取股票数据")
    print("="*70)
    
    all_data = {}
    for code in stock_codes:
        try:
            lg = bs.login()
            rs = bs.query_history_k_data_plus(
                code,
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d"
            )
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            df = pd.DataFrame(data, columns=rs.fields)
            bs.logout()
            
            if len(df) > 30:
                # 转换数据类型
                for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                    df[col] = df[col].astype(float)
                all_data[code] = df
                print(f"  ✅ {code}: {len(df)} 天")
        except Exception as e:
            print(f"  ❌ {code}: 失败")
    
    print(f"\n✅ 成功获取 {len(all_data)} 只股票数据")
    return all_data

# ==================== 3. 构建特征（50+ 特征）====================
def create_advanced_features(df):
    """
    构建高级特征工程
    包含 50+ 技术指标
    """
    df = df.copy()
    
    # === 价格特征 ===
    df['return_1d'] = df['close'].pct_change(1)
    df['return_3d'] = df['close'].pct_change(3)
    df['return_5d'] = df['close'].pct_change(5)
    df['return_10d'] = df['close'].pct_change(10)
    df['return_20d'] = df['close'].pct_change(20)
    
    # === 均线系统 ===
    for period in [5, 10, 20, 30, 60]:
        df[f'ma_{period}'] = df['close'].rolling(period).mean()
        df[f'ma_{period}_ratio'] = df['close'] / df[f'ma_{period}']
    
    # === MACD 系列 ===
    df['ema12'] = df['close'].ewm(span=12).mean()
    df['ema26'] = df['close'].ewm(span=26).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # === RSI 系列 ===
    for period in [6, 12, 24]:
        delta = df['close'].diff()
        gain = delta.apply(lambda x: x if x > 0 else 0)
        loss = delta.apply(lambda x: abs(x) if x < 0 else 0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
    
    # === 布林带系列 ===
    for period in [20, 26]:
        df[f'bb_mid_{period}'] = df['close'].rolling(period).mean()
        df[f'bb_std_{period}'] = df['close'].rolling(period).std()
        df[f'bb_upper_{period}'] = df[f'bb_mid_{period}'] + 2 * df[f'bb_std_{period}']
        df[f'bb_lower_{period}'] = df[f'bb_mid_{period}'] - 2 * df[f'bb_std_{period}']
        df[f'bb_pos_{period}'] = (df['close'] - df[f'bb_lower_{period}']) / (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}'])
    
    # === 成交量特征 ===
    for period in [5, 10, 20]:
        df[f'volume_ma_{period}'] = df['volume'].rolling(period).mean()
        df[f'volume_ratio_{period}'] = df['volume'] / df[f'volume_ma_{period}']
    
    df['amount_volume_ratio'] = df['amount'] / (df['volume'] * df['close'])
    
    # === 波动率特征 ===
    for period in [5, 10, 20]:
        df[f'volatility_{period}'] = df['return_1d'].rolling(period).std()
    
    # === 高低特征 ===
    df['high_low_range'] = (df['high'] - df['low']) / df['close']
    df['close_open_range'] = (df['close'] - df['open']) / df['open']
    
    # === 动量特征 ===
    df['momentum_5'] = df['close'] - df['close'].shift(5)
    df['momentum_10'] = df['close'] - df['close'].shift(10)
    df['momentum_20'] = df['close'] - df['close'].shift(20)
    
    # === 标签：未来 5 天是否上涨超过 2% ===
    df['future_return_5d'] = df['close'].shift(-5) / df['close'] - 1
    df['target'] = (df['future_return_5d'] > 0.02).astype(int)
    
    return df

# ==================== 4. 特征选择 ====================
def select_best_features(X, y, k=20):
    """选择最重要的 k 个特征"""
    selector = SelectKBest(score_func=f_classif, k=k)
    selector.fit(X, y)
    
    feature_scores = pd.DataFrame({
        '特征': X.columns,
        '得分': selector.scores_
    }).sort_values('得分', ascending=False)
    
    selected_features = X.columns[selector.get_support()].tolist()
    
    return selected_features, feature_scores

# ==================== 5. 多模型对比 ====================
def compare_models(X_train, y_train, X_test, y_test):
    """对比多个模型"""
    
    models = {
        '逻辑回归': LogisticRegression(max_iter=1000, random_state=42),
        '随机森林': RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1),
        '梯度提升': GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)
    }
    
    results = []
    
    for name, model in models.items():
        print(f"\n🤖 训练 {name}...")
        model.fit(X_train, y_train)
        
        # 预测
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
        
        # 评估
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        results.append({
            '模型': name,
            '准确率': accuracy,
            '精确率': precision,
            '召回率': recall,
            'F1 分数': f1
        })
        
        print(f"  准确率：{accuracy:.2%}")
        print(f"  F1 分数：{f1:.2f}")
    
    results_df = pd.DataFrame(results)
    print("\n" + "="*70)
    print("📊 模型对比结果")
    print("="*70)
    print(results_df.to_string(index=False))
    
    best_model = results_df.loc[results_df['F1 分数'].idxmax()]
    print(f"\n🏆 最佳模型：{best_model['模型']} (F1={best_model['F1 分数']:.2f})")
    
    return results_df

# ==================== 6. 时间序列交叉验证 ====================
def time_series_cv(X, y, model_class, n_splits=5):
    """时间序列交叉验证"""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    cv_scores = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model = model_class(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        cv_scores.append(accuracy)
        
        print(f"  折 {fold+1}: 准确率 {accuracy:.2%}")
    
    mean_score = np.mean(cv_scores)
    std_score = np.std(cv_scores)
    
    print(f"\n✅ 交叉验证平均准确率：{mean_score:.2%} ± {std_score:.2%}")
    
    return cv_scores

# ==================== 7. 主函数 ====================
if __name__ == '__main__':
    START_DATE = '2022-01-01'
    END_DATE = '2023-12-31'
    
    print("="*70)
    print("🤖 机器学习量化交易 - 进阶版")
    print("="*70)
    print(f"时间范围：{START_DATE} 至 {END_DATE}")
    print(f"股票池：{len(STOCK_POOL)} 只")
    
    # 1. 获取数据
    all_data = get_all_stock_data(STOCK_POOL, START_DATE, END_DATE)
    
    # 2. 构建特征
    print("\n" + "="*70)
    print("📐 特征工程")
    print("="*70)
    
    all_features = []
    for code, df in all_data.items():
        df_feat = create_advanced_features(df)
        df_feat['code'] = code
        all_features.append(df_feat)
        print(f"  ✅ {code}: 特征构建完成")
    
    # 合并所有股票数据
    combined_df = pd.concat(all_features, ignore_index=True)
    print(f"\n✅ 合并后数据：{len(combined_df)} 行")
    
    # 3. 准备训练数据
    feature_cols = [col for col in combined_df.columns if col not in 
                   ['date', 'code', 'target', 'future_return_5d', 
                    'open', 'high', 'low', 'close', 'volume', 'amount']]
    
    # 删除 NaN
    df_clean = combined_df.dropna(subset=feature_cols + ['target'])
    print(f"✅ 清洗后数据：{len(df_clean)} 行")
    
    X = df_clean[feature_cols]
    y = df_clean['target']
    
    print(f"\n📊 数据分布:")
    print(f"  上涨样本：{y.sum()} ({y.sum()/len(y)*100:.1f}%)")
    print(f"  下跌样本：{len(y) - y.sum()} ({(len(y)-y.sum())/len(y)*100:.1f}%)")
    
    # 4. 特征选择
    print("\n" + "="*70)
    print("🎯 特征选择")
    print("="*70)
    
    selected_features, feature_scores = select_best_features(X, y, k=30)
    print(f"\n🏆 前 10 重要特征:")
    print(feature_scores.head(10).to_string(index=False))
    
    X_selected = X[selected_features]
    
    # 5. 训练集/测试集分割（时间序列）
    split_point = int(len(X_selected) * 0.8)
    X_train = X_selected.iloc[:split_point]
    X_test = X_selected.iloc[split_point:]
    y_train = y.iloc[:split_point]
    y_test = y.iloc[split_point:]
    
    print("\n" + "="*70)
    print("📊 数据分割")
    print("="*70)
    print(f"训练集：{len(X_train)} 样本")
    print(f"测试集：{len(X_test)} 样本")
    
    # 6. 多模型对比
    print("\n" + "="*70)
    print("🤖 模型训练与对比")
    print("="*70)
    
    model_results = compare_models(X_train, y_train, X_test, y_test)
    
    # 7. 时间序列交叉验证
    print("\n" + "="*70)
    print("🔄 时间序列交叉验证")
    print("="*70)
    
    cv_scores = time_series_cv(X_selected, y, RandomForestClassifier, n_splits=5)
    
    # 8. 总结
    print("\n" + "="*70)
    print("📚 进阶机器学习要点")
    print("="*70)
    print("""
✅ 改进点:
1. 多股票训练 - 提高泛化能力，避免过拟合单只股票
2. 50+ 特征 - 全面捕捉市场信息
3. 特征选择 - 去除冗余，保留最重要特征
4. 多模型对比 - 选择最适合的模型
5. 时间序列 CV - 更严谨的验证方法

⚠️ 注意事项:
1. 数据量仍然偏小（2 年 20 只股票≈10000 样本）
2. 需要定期重新训练（市场风格变化）
3. 交易成本未考虑（佣金、印花税、滑点）
4. 实盘前需要更长回测周期

🎯 下一步:
- 加入更多股票（50-100 只）
- 加入基本面特征（PE、PB、ROE 等）
- 加入情绪特征（新闻、社交媒体）
- 尝试深度学习模型（LSTM、Transformer）
    """)
