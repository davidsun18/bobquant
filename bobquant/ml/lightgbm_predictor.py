# -*- coding: utf-8 -*-
"""
BobQuant LightGBM 预测模型

功能：
- 特征工程（集成技术指标）
- 模型训练（LightGBM 分类/回归）
- 预测接口
- 特征重要性分析

使用方式：
    from bobquant.ml.lightgbm_predictor import LightGBMPredictor
    
    predictor = LightGBMPredictor()
    predictor.train(stock_data, target_type='classification')
    predictions = predictor.predict(stock_data)
    importance = predictor.get_feature_importance()
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import sys
import os
import json
from pathlib import Path
import pickle

# 尝试导入 LightGBM
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("[LightGBM] 警告：lightgbm 未安装")

# 尝试导入 sklearn
try:
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    from sklearn.model_selection import train_test_split, TimeSeriesSplit
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[LightGBM] 警告：sklearn 未安装")


class LightGBMPredictor:
    """LightGBM 股票预测器"""
    
    def __init__(self, model_dir: str = None, model_name: str = 'lightgbm_model'):
        """
        初始化预测器
        
        Args:
            model_dir: 模型保存目录
            model_name: 模型名称
        """
        if not LIGHTGBM_AVAILABLE:
            raise ImportError("LightGBM 未安装，请运行：pip3 install lightgbm")
        
        self.model_dir = model_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ml', 'models'
        )
        self.model_name = model_name
        
        # 确保模型目录存在
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.feature_names = []
        self.scaler = StandardScaler()
        self.lookback_days = 60  # 回溯天数
        self.default_params = {
            'objective': 'binary',  # 二分类：涨跌预测
            'metric': ['auc', 'binary_logloss'],
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'n_estimators': 1000,
            'early_stopping_rounds': 50,
            'random_state': 42,
            'n_jobs': -1
        }
        
        self.training_history = []
        self.feature_importance_df = None
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特征工程 - 生成技术指标特征
        
        Args:
            df: 原始行情数据 (包含 open/high/low/close/volume)
            
        Returns:
            DataFrame: 包含技术特征的数据
        """
        # 确保使用数值列，排除日期列
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df_numeric = df[numeric_cols].copy()
        
        features = df_numeric.copy()
        
        # ========== 1. 移动平均线 ==========
        for window in [5, 10, 20, 60]:
            features[f'ma{window}'] = df['close'].rolling(window=window).mean()
            features[f'ma{window}_ratio'] = df['close'] / features[f'ma{window}'] - 1
        
        # 均线乖离率
        features['ma5_10_diff'] = features['ma5'] - features['ma10']
        features['ma10_20_diff'] = features['ma10'] - features['ma20']
        
        # ========== 2. MACD ==========
        exp1 = df['close'].ewm(span=12, adjust=False)
        exp2 = df['close'].ewm(span=26, adjust=False)
        macd_line = exp1.mean() - exp2.mean()
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        features['macd'] = macd_line
        features['macd_signal'] = signal_line
        features['macd_hist'] = macd_line - signal_line
        features['macd_ratio'] = macd_line / df['close']
        
        # ========== 3. RSI ==========
        for window in [6, 12, 24]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            features[f'rsi{window}'] = 100 - (100 / (1 + rs))
        
        # ========== 4. 布林带 ==========
        features['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        features['bb_upper'] = features['bb_middle'] + 2 * bb_std
        features['bb_lower'] = features['bb_middle'] - 2 * bb_std
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / features['bb_middle']
        features['bb_position'] = (df['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # ========== 5. 成交量特征 ==========
        features['volume_ma5'] = df['volume'].rolling(window=5).mean()
        features['volume_ma20'] = df['volume'].rolling(window=20).mean()
        features['volume_ratio'] = df['volume'] / features['volume_ma5']
        features['volume_change'] = df['volume'].pct_change()
        
        # ========== 6. 价格动量 ==========
        for window in [1, 3, 5, 10, 20]:
            features[f'return_{window}d'] = df['close'].pct_change(periods=window)
        
        # ========== 7. 波动率特征 ==========
        for window in [5, 10, 20]:
            features[f'volatility_{window}d'] = df['close'].pct_change().rolling(window=window).std()
        
        # ========== 8. KDJ 指标 ==========
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        features['kdj_k'] = rsv.rolling(window=3).mean()
        features['kdj_d'] = features['kdj_k'].rolling(window=3).mean()
        features['kdj_j'] = 3 * features['kdj_k'] - 2 * features['kdj_d']
        
        # ========== 9. 价格位置特征 ==========
        features['high_low_ratio'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-9)
        features['price_range'] = (df['high'] - df['low']) / df['close']
        
        # ========== 10. 滞后特征 ==========
        for lag in [1, 2, 3, 5]:
            features[f'close_lag{lag}'] = df['close'].shift(lag)
            features[f'return_lag{lag}'] = features['return_1d'].shift(lag)
        
        # ========== 11. 目标变量（用于训练） ==========
        # 未来 5 日收益率
        features['target_return_5d'] = df['close'].shift(-5) / df['close'] - 1
        # 涨跌分类（1=涨，0=跌）
        features['target_binary'] = (features['target_return_5d'] > 0).astype(int)
        
        return features
    
    def create_target(self, df: pd.DataFrame, target_type: str = 'classification', 
                      horizon: int = 5, threshold: float = 0.0) -> pd.Series:
        """
        创建目标变量
        
        Args:
            df: 行情数据
            target_type: 'classification' (分类) 或 'regression' (回归)
            horizon: 预测 horizon（天数）
            threshold: 分类阈值（仅分类模式）
            
        Returns:
            target: 目标变量序列
        """
        future_return = df['close'].shift(-horizon) / df['close'] - 1
        
        if target_type == 'classification':
            # 二分类：涨跌预测
            target = (future_return > threshold).astype(int)
        else:
            # 回归：预测收益率
            target = future_return
        
        return target
    
    def train(self, df: pd.DataFrame, target_type: str = 'classification',
              test_size: float = 0.2, params: Dict = None) -> Dict:
        """
        训练模型
        
        Args:
            df: 训练数据（包含 OHLCV）
            target_type: 'classification' 或 'regression'
            test_size: 测试集比例
            params: LightGBM 参数（可选，覆盖默认参数）
            
        Returns:
            训练结果字典（包含评估指标）
        """
        print(f"[LightGBM] 开始训练模型 (target_type={target_type})")
        
        # 1. 特征工程
        features_df = self.prepare_features(df)
        
        # 2. 删除缺失值
        features_df = features_df.dropna()
        
        if len(features_df) < 100:
            raise ValueError(f"数据量不足 ({len(features_df)} 条)，需要至少 100 条")
        
        # 3. 准备特征和标签
        feature_cols = [col for col in features_df.columns 
                       if col not in ['target_return_5d', 'target_binary'] 
                       and not col.startswith('target_')]
        
        X = features_df[feature_cols].values.astype(np.float64)
        
        # 创建目标变量
        y = self.create_target(df, target_type, horizon=5)
        y = y.dropna()
        
        # 对齐 X 和 y 的长度
        min_len = min(len(X), len(y))
        X = X[-min_len:]
        y = y.values[-min_len:]
        
        # 对齐 X 和 y
        min_len = min(len(X), len(y))
        X = X[-min_len:]
        y = y[-min_len:]
        
        self.feature_names = feature_cols
        
        # 4. 特征标准化
        X_scaled = self.scaler.fit_transform(X)
        
        # 5. 时间序列分割（保持时间顺序）
        split_idx = int(len(X_scaled) * (1 - test_size))
        X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        print(f"[LightGBM] 训练集：{len(X_train)} 条，测试集：{len(X_test)} 条")
        
        # 6. 设置模型参数
        if params is None:
            params = self.default_params.copy()
        else:
            params = {**self.default_params, **params}
        
        # 根据任务类型调整目标函数
        if target_type == 'regression':
            params['objective'] = 'regression'
            params['metric'] = ['rmse', 'mae']
        
        # 7. 创建数据集
        train_data = lgb.Dataset(X_train, label=y_train, feature_name=self.feature_names)
        test_data = lgb.Dataset(X_test, label=y_test, feature_name=self.feature_names, reference=train_data)
        
        # 8. 训练模型
        self.model = lgb.train(
            params,
            train_data,
            valid_sets=[train_data, test_data],
            valid_names=['train', 'valid'],
            num_boost_round=params.get('n_estimators', 1000),
            callbacks=[
                lgb.early_stopping(params.get('early_stopping_rounds', 50)),
                lgb.log_evaluation(period=100)
            ]
        )
        
        # 9. 预测并评估
        y_pred_proba = self.model.predict(X_test)
        
        if target_type == 'classification':
            y_pred = (y_pred_proba > 0.5).astype(int)
            
            # 分类指标
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            results = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'auc': params.get('metric', ['auc'])[0]
            }
            
            print(f"\n[LightGBM] 分类结果:")
            print(f"  准确率 (Accuracy): {accuracy:.4f}")
            print(f"  精确率 (Precision): {precision:.4f}")
            print(f"  召回率 (Recall): {recall:.4f}")
            print(f"  F1 分数：{f1:.4f}")
            
        else:
            # 回归指标
            y_pred = y_pred_proba
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            results = {
                'rmse': rmse,
                'mae': mae,
                'r2': r2
            }
            
            print(f"\n[LightGBM] 回归结果:")
            print(f"  RMSE: {rmse:.6f}")
            print(f"  MAE: {mae:.6f}")
            print(f"  R²: {r2:.4f}")
        
        # 10. 特征重要性
        self.feature_importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importance(importance_type='gain')
        }).sort_values('importance', ascending=False)
        
        print(f"\n[LightGBM] Top 10 重要特征:")
        for idx, row in self.feature_importance_df.head(10).iterrows():
            print(f"  {row['feature']}: {row['importance']:.2f}")
        
        # 11. 保存模型
        self.save_model()
        
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'target_type': target_type,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'results': results
        })
        
        return results
    
    def predict(self, df: pd.DataFrame, target_type: str = 'classification') -> np.ndarray:
        """
        预测
        
        Args:
            df: 预测数据（包含 OHLCV）
            target_type: 'classification' 或 'regression'
            
        Returns:
            预测结果（概率或类别）
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用 train() 方法")
        
        # 特征工程
        features_df = self.prepare_features(df)
        features_df = features_df.dropna()
        
        # 提取特征
        X = features_df[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        
        # 预测
        predictions = self.model.predict(X_scaled)
        
        if target_type == 'classification':
            predictions = (predictions > 0.5).astype(int)
        
        return predictions
    
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """
        预测概率（仅分类任务）
        
        Args:
            df: 预测数据
            
        Returns:
            上涨概率
        """
        if self.model is None:
            raise ValueError("模型未训练")
        
        features_df = self.prepare_features(df)
        features_df = features_df.dropna()
        
        X = features_df[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        
        return self.model.predict(X_scaled)
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        获取特征重要性
        
        Args:
            top_n: 返回前 N 个特征
            
        Returns:
            DataFrame: 特征重要性排名
        """
        if self.feature_importance_df is None:
            raise ValueError("模型未训练，无法获取特征重要性")
        
        return self.feature_importance_df.head(top_n)
    
    def save_model(self, model_name: str = None):
        """
        保存模型
        
        Args:
            model_name: 模型名称（可选）
        """
        name = model_name or self.model_name
        model_path = os.path.join(self.model_dir, f'{name}.pkl')
        
        # 保存 LightGBM 模型
        self.model.save_model(os.path.join(self.model_dir, f'{name}.txt'))
        
        # 保存 scaler 和特征名
        with open(model_path, 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'training_history': self.training_history
            }, f)
        
        print(f"[LightGBM] 模型已保存：{model_path}")
    
    def load_model(self, model_name: str = None):
        """
        加载模型
        
        Args:
            model_name: 模型名称
        """
        name = model_name or self.model_name
        model_path = os.path.join(self.model_dir, f'{name}.pkl')
        model_txt_path = os.path.join(self.model_dir, f'{name}.txt')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在：{model_path}")
        
        # 加载 scaler 和特征名
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            self.training_history = data['training_history']
        
        # 加载 LightGBM 模型
        self.model = lgb.Booster(model_file=model_txt_path)
        
        print(f"[LightGBM] 模型已加载：{model_path}")
    
    def plot_feature_importance(self, top_n: int = 20, save_path: str = None):
        """
        绘制特征重要性图（需要 matplotlib）
        
        Args:
            top_n: 显示前 N 个特征
            save_path: 保存路径（可选）
        """
        try:
            import matplotlib.pyplot as plt
            
            importance_df = self.get_feature_importance(top_n)
            
            plt.figure(figsize=(10, 8))
            plt.barh(range(len(importance_df)), importance_df['importance'].values)
            plt.yticks(range(len(importance_df)), importance_df['feature'].values)
            plt.xlabel('重要性 (Gain)')
            plt.title('LightGBM 特征重要性')
            plt.gca().invert_yaxis()
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                print(f"[LightGBM] 特征重要性图已保存：{save_path}")
            else:
                plt.show()
                
        except ImportError:
            print("[LightGBM] matplotlib 未安装，无法绘图")


# ========== 测试函数 ==========

def generate_mock_stock_data(n_days: int = 500, seed: int = 42) -> pd.DataFrame:
    """
    生成模拟股票数据用于测试
    
    Args:
        n_days: 天数
        seed: 随机种子
        
    Returns:
        DataFrame: 包含 OHLCV 的模拟数据（不含 date 列）
    """
    np.random.seed(seed)
    
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    
    # 生成随机游走价格
    returns = np.random.randn(n_days) * 0.02  # 日收益率
    price = 100 * np.cumprod(1 + returns)
    
    # 生成 OHLCV（不包含 date 列，避免类型问题）
    df = pd.DataFrame({
        'open': price * (1 + np.random.randn(n_days) * 0.01),
        'high': price * (1 + np.abs(np.random.randn(n_days) * 0.02)),
        'low': price * (1 - np.abs(np.random.randn(n_days) * 0.02)),
        'close': price,
        'volume': np.random.randint(1000000, 10000000, n_days)
    }, index=dates)
    
    # 确保 high >= close, open, low
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def test_lightgbm_predictor(stock_codes: List[str] = None, use_mock_data: bool = True):
    """
    测试 LightGBM 预测器
    
    Args:
        stock_codes: 股票代码列表
        use_mock_data: 是否使用模拟数据（True=模拟，False=真实数据）
    """
    import sys
    sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')
    
    if not use_mock_data:
        from bobquant.data.akshare_provider import AkshareProvider
    
    if stock_codes is None:
        # 默认测试 5 只股票
        stock_codes = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
    
    print("=" * 60)
    print("LightGBM 预测模型测试")
    print("=" * 60)
    
    all_results = {}
    all_importance = []
    
    # 创建数据提供者（仅当使用真实数据时）
    if not use_mock_data:
        provider = AkshareProvider()
    
    for stock_code in stock_codes:
        print(f"\n{'='*60}")
        print(f"测试股票：{stock_code}")
        print(f"{'='*60}")
        
        try:
            if use_mock_data:
                # 使用模拟数据
                df = generate_mock_stock_data(n_days=500)
                print(f"[{stock_code}] 使用模拟数据：{len(df)} 条")
            else:
                # 获取真实历史数据（过去 2 年）
                df = provider.get_history(stock_code, days=730)
                
                if df is None or len(df) < 200:
                    print(f"[{stock_code}] 数据不足，跳过")
                    continue
                
                print(f"数据量：{len(df)} 条 ({df['date'].min()} ~ {df['date'].max()})")
            
            # 创建预测器
            predictor = LightGBMPredictor(model_name=f'lightgbm_{stock_code.replace(".", "_")}')
            
            # 训练模型
            results = predictor.train(df, target_type='classification')
            
            # 获取特征重要性
            importance = predictor.get_feature_importance(top_n=10)
            
            # 预测最新数据（需要足够的数据来计算特征）
            latest_data = df.tail(100)  # 最近 100 天
            predictions = predictor.predict(latest_data)
            probas = predictor.predict_proba(latest_data)
            
            if len(predictions) > 0:
                # 统计预测结果
                pred_up = np.sum(predictions == 1)
                pred_down = np.sum(predictions == 0)
                
                print(f"\n最新数据预测:")
                print(f"  上涨概率：{pred_up}/{len(predictions)} ({pred_up/len(predictions)*100:.1f}%)")
                print(f"  下跌概率：{pred_down}/{len(predictions)} ({pred_down/len(predictions)*100:.1f}%)")
            else:
                print(f"\n最新数据预测：数据不足，无法预测")
                pred_up = 0
            
            # 保存结果
            all_results[stock_code] = {
                'accuracy': results['accuracy'],
                'precision': results['precision'],
                'recall': results['recall'],
                'f1_score': results['f1_score'],
                'pred_up_ratio': pred_up / len(predictions)
            }
            
            all_importance.append(importance)
            
        except Exception as e:
            print(f"[{stock_code}] 测试失败：{str(e)}")
            import traceback
            traceback.print_exc()
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("测试汇总")
    print(f"{'='*60}")
    
    if all_results:
        avg_accuracy = np.mean([r['accuracy'] for r in all_results.values()])
        avg_precision = np.mean([r['precision'] for r in all_results.values()])
        avg_f1 = np.mean([r['f1_score'] for r in all_results.values()])
        
        print(f"\n平均指标 (5 只股票):")
        print(f"  平均准确率：{avg_accuracy:.4f}")
        print(f"  平均精确率：{avg_precision:.4f}")
        print(f"  平均 F1 分数：{avg_f1:.4f}")
        
        print(f"\n各股票表现:")
        for code, result in all_results.items():
            print(f"  {code}: Accuracy={result['accuracy']:.4f}, "
                  f"Precision={result['precision']:.4f}, F1={result['f1_score']:.4f}")
        
        # 综合特征重要性
        print(f"\n综合特征重要性 (Top 10):")
        if all_importance:
            # 合并所有股票的特征重要性
            combined_importance = pd.concat(all_importance)
            avg_importance = combined_importance.groupby('feature')['importance'].mean().sort_values(ascending=False)
            
            for idx, (feature, imp) in enumerate(avg_importance.head(10).items()):
                print(f"  {idx+1}. {feature}: {imp:.2f}")
    
    return all_results


if __name__ == '__main__':
    # 运行测试
    test_lightgbm_predictor()
