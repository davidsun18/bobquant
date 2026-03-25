"""
机器学习股票预测模块
参考：A-stock-prediction-algorithm-based-on-machine-learning
https://github.com/moyuweiqing/A-stock-prediction-algorithm-based-on-machine-learning

功能：
- LSTM 价格预测
- Prophet 时间序列预测
- SVM/随机森林分类
- 特征工程
- 模型训练与保存
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os
import json
from pathlib import Path

# 尝试导入 ML 库 (如果未安装则降级到简单模型)
try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.svm import SVC
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[ML] 警告：sklearn 未安装，部分功能不可用")

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("[ML] 警告：tensorflow 未安装，LSTM 预测不可用")


class MLPredictor:
    """机器学习股票预测器"""
    
    def __init__(self, model_dir: str = None):
        """
        初始化预测器
        
        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = model_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ml', 'models'
        )
        
        # 确保模型目录存在
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        
        self.models = {}
        self.scalers = {}
        self.lookback_days = 60  # 回溯天数
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特征工程
        
        Args:
            df: 原始行情数据 (包含 open/high/low/close/volume)
            
        Returns:
            DataFrame: 包含技术特征的数据
        """
        features = df.copy()
        
        # 1. 移动平均线
        features['ma5'] = df['close'].rolling(window=5).mean()
        features['ma10'] = df['close'].rolling(window=10).mean()
        features['ma20'] = df['close'].rolling(window=20).mean()
        
        # 2. MACD
        exp1 = df['close'].ewm(span=12, adjust=False)
        exp2 = df['close'].ewm(span=26, adjust=False)
        macd_line = exp1.mean() - exp2.mean()
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        features['macd'] = macd_line
        features['macd_signal'] = signal_line
        features['macd_hist'] = macd_line - signal_line
        
        # 3. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. 布林带
        features['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        features['bb_upper'] = features['bb_middle'] + (bb_std * 2)
        features['bb_lower'] = features['bb_middle'] - (bb_std * 2)
        features['bb_pct'] = (df['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # 5. 成交量特征
        features['volume_ma5'] = df['volume'].rolling(window=5).mean()
        features['volume_ratio'] = df['volume'] / features['volume_ma5']
        
        # 6. 价格变化
        features['returns'] = df['close'].pct_change()
        features['high_low_range'] = (df['high'] - df['low']) / df['close']
        
        # 7. 目标变量 (T+1 是否上涨)
        features['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # 删除 NaN 值
        features = features.dropna()
        
        return features
    
    def train_lstm(self, df: pd.DataFrame, epochs: int = 50) -> Dict:
        """
        训练 LSTM 价格预测模型
        
        Args:
            df: 特征数据
            epochs: 训练轮数
            
        Returns:
            dict: 训练结果
        """
        if not TENSORFLOW_AVAILABLE:
            return {'success': False, 'error': 'TensorFlow 未安装'}
        
        try:
            # 准备数据
            feature_cols = ['close', 'ma5', 'ma10', 'macd', 'rsi', 'volume_ratio', 'returns']
            data = df[feature_cols].values
            
            # 归一化
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(data)
            self.scalers['lstm'] = scaler
            
            # 创建序列数据
            X, y = [], []
            for i in range(self.lookback_days, len(scaled_data)):
                X.append(scaled_data[i-self.lookback_days:i])
                y.append(scaled_data[i, 0])  # 预测收盘价
            
            X = np.array(X)
            y = np.array(y)
            
            # 划分训练集测试集
            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # 构建 LSTM 模型
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(self.lookback_days, len(feature_cols))),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
            
            # 训练
            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=32,
                validation_data=(X_test, y_test),
                verbose=0
            )
            
            # 保存模型
            model.save(os.path.join(self.model_dir, 'lstm_model.h5'))
            self.models['lstm'] = model
            
            # 计算测试集准确率
            predictions = model.predict(X_test, verbose=0)
            mse = np.mean((predictions.flatten() - y_test) ** 2)
            
            return {
                'success': True,
                'model_type': 'LSTM',
                'train_samples': len(X_train),
                'test_samples': len(X_test),
                'mse': float(mse),
                'epochs_trained': epochs,
                'loss_history': [float(h) for h in history.history['loss'][-5:]]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def train_classifier(self, df: pd.DataFrame, model_type: str = 'rf') -> Dict:
        """
        训练分类模型 (预测涨跌)
        
        Args:
            df: 特征数据
            model_type: 'rf' (随机森林) 或 'svm'
            
        Returns:
            dict: 训练结果
        """
        if not SKLEARN_AVAILABLE:
            return {'success': False, 'error': 'sklearn 未安装'}
        
        try:
            # 特征列
            feature_cols = ['ma5', 'ma10', 'ma20', 'macd', 'rsi', 'bb_pct', 
                           'volume_ratio', 'returns', 'high_low_range']
            
            X = df[feature_cols].values
            y = df['target'].values
            
            # 划分数据集
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # 选择模型
            if model_type == 'svm':
                model = SVC(kernel='rbf', C=1.0, probability=True)
            else:  # 随机森林
                model = RandomForestClassifier(
                    n_estimators=100, 
                    max_depth=10,
                    random_state=42
                )
            
            # 训练
            model.fit(X_train, y_train)
            
            # 评估
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # 保存模型
            model_name = f'{model_type}_classifier.pkl'
            import pickle
            with open(os.path.join(self.model_dir, model_name), 'wb') as f:
                pickle.dump(model, f)
            
            self.models[model_type] = model
            
            return {
                'success': True,
                'model_type': model_type.upper(),
                'train_samples': len(X_train),
                'test_samples': len(X_test),
                'accuracy': float(accuracy),
                'classification_report': classification_report(y_test, y_pred, output_dict=True)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def predict_price(self, df: pd.DataFrame, days: int = 5) -> Dict:
        """
        预测未来价格
        
        Args:
            df: 历史数据
            days: 预测天数
            
        Returns:
            dict: 预测结果
        """
        if 'lstm' not in self.models:
            # 尝试加载模型
            model_path = os.path.join(self.model_dir, 'lstm_model.h5')
            if TENSORFLOW_AVAILABLE and os.path.exists(model_path):
                from tensorflow.keras.models import load_model
                self.models['lstm'] = load_model(model_path)
            else:
                return {'success': False, 'error': 'LSTM 模型未训练'}
        
        try:
            model = self.models['lstm']
            scaler = self.scalers.get('lstm')
            
            # 准备最后 N 天的数据
            feature_cols = ['close', 'ma5', 'ma10', 'macd', 'rsi', 'volume_ratio', 'returns']
            last_data = df[feature_cols].tail(self.lookback_days).values
            
            if scaler:
                last_scaled = scaler.transform(last_data)
            else:
                last_scaled = last_data
            
            predictions = []
            current_input = last_scaled.reshape(1, self.lookback_days, len(feature_cols))
            
            for _ in range(days):
                pred = model.predict(current_input, verbose=0)[0, 0]
                predictions.append(float(pred))
                
                # 更新输入 (简单处理：用预测值替换最后一个值)
                current_input = np.roll(current_input, -1, axis=1)
                current_input[0, -1, 0] = pred  # 更新收盘价
            
            return {
                'success': True,
                'predictions': predictions,
                'current_price': float(df['close'].iloc[-1]),
                'trend': 'up' if predictions[-1] > predictions[0] else 'down'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def predict_direction(self, df: pd.DataFrame, model_type: str = 'rf') -> Dict:
        """
        预测明日涨跌方向
        
        Args:
            df: 历史数据
            model_type: 'rf' 或 'svm'
            
        Returns:
            dict: 预测结果
        """
        if model_type not in self.models:
            # 尝试加载模型
            import pickle
            model_path = os.path.join(self.model_dir, f'{model_type}_classifier.pkl')
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.models[model_type] = pickle.load(f)
            else:
                return {'success': False, 'error': f'{model_type.upper()} 模型未训练'}
        
        try:
            model = self.models[model_type]
            
            # 准备特征
            features = self.prepare_features(df)
            feature_cols = ['ma5', 'ma10', 'ma20', 'macd', 'rsi', 'bb_pct', 
                           'volume_ratio', 'returns', 'high_low_range']
            
            last_features = features[feature_cols].iloc[-1:].values
            
            # 预测
            prediction = model.predict(last_features)[0]
            probability = model.predict_proba(last_features)[0]
            
            return {
                'success': True,
                'prediction': 'up' if prediction == 1 else 'down',
                'probability': float(max(probability)),
                'confidence': 'high' if max(probability) > 0.7 else 'medium' if max(probability) > 0.55 else 'low'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("机器学习预测模块 - 测试")
    print("=" * 60)
    
    # 生成模拟数据
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=200, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'open': np.random.uniform(10, 100, 200),
        'high': np.random.uniform(10, 100, 200),
        'low': np.random.uniform(10, 100, 200),
        'close': np.random.uniform(10, 100, 200),
        'volume': np.random.uniform(1000000, 10000000, 200)
    })
    df.set_index('date', inplace=True)
    
    predictor = MLPredictor()
    
    # 1. 特征工程
    print("\n1️⃣ 特征工程")
    features = predictor.prepare_features(df)
    print(f"   原始特征数：{len(df.columns)}")
    print(f"   处理后特征数：{len(features.columns)}")
    print(f"   有效样本数：{len(features)}")
    
    # 2. 训练分类模型
    if SKLEARN_AVAILABLE:
        print("\n2️⃣ 训练随机森林分类器")
        result = predictor.train_classifier(features, 'rf')
        if result['success']:
            print(f"   ✅ 训练完成")
            print(f"   训练样本：{result['train_samples']}")
            print(f"   测试样本：{result['test_samples']}")
            print(f"   准确率：{result['accuracy']*100:.2f}%")
        else:
            print(f"   ❌ 训练失败：{result['error']}")
    
    # 3. 预测方向
    print("\n3️⃣ 预测明日涨跌")
    if SKLEARN_AVAILABLE:
        pred = predictor.predict_direction(features, 'rf')
        if pred['success']:
            direction = "📈 上涨" if pred['prediction'] == 'up' else "📉 下跌"
            print(f"   预测：{direction}")
            print(f"   概率：{pred['probability']*100:.1f}%")
            print(f"   置信度：{pred['confidence']}")
    else:
        print("   ⚠️ sklearn 未安装，跳过")
    
    print("\n" + "=" * 60)
