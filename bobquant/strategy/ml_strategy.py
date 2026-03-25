# -*- coding: utf-8 -*-
"""
机器学习策略模块
基于历史数据预测明日涨跌，生成买卖信号
"""
from datetime import datetime
try:
    from ..ml import MLPredictor
    from ..data.provider import get_provider
except ImportError:
    from ml import MLPredictor
    from data.provider import get_provider
import os


class MLStrategy:
    """
    机器学习预测策略
    
    使用随机森林/LSTM 等模型预测股票涨跌方向
    信号强度基于预测概率和置信度
    """
    
    name = "ml_predictor"
    
    def __init__(self, config):
        self.config = config
        self.predictor = MLPredictor(
            model_dir=config.get('ml_model_dir', 'ml/models')
        )
        self.data_provider = get_provider('tencent')
        self.lookback_days = config.get('ml_lookback_days', 200)
        self.min_train_samples = config.get('ml_min_train_samples', 60)
        self.probability_threshold = config.get('ml_probability_threshold', 0.6)
        
        # 缓存预测结果（避免重复计算）
        self._cache = {}
        self._cache_date = None
    
    def _ensure_cache_date(self):
        """确保缓存是今日数据"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self._cache_date != today:
            self._cache = {}
            self._cache_date = today
    
    def check(self, code, name, quote, df, pos, config):
        """
        检查 ML 预测信号
        
        返回:
          {'signal': 'buy'/'sell'/None, 'reason': str, 'strength': 'normal'/'strong'/'weak'}
        """
        self._ensure_cache_date()
        
        # 检查缓存
        cache_key = code
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 1. 获取历史数据
        if df is None or len(df) < self.min_train_samples:
            result = {'signal': None, 'reason': f'数据不足 ({len(df) if df is not None else 0} < {self.min_train_samples})'}
            self._cache[cache_key] = result
            return result
        
        # 2. 准备特征
        try:
            features = self.predictor.prepare_features(df)
            if len(features) < self.min_train_samples:
                result = {'signal': None, 'reason': f'特征数据不足 ({len(features)} < {self.min_train_samples})'}
                self._cache[cache_key] = result
                return result
        except Exception as e:
            result = {'signal': None, 'reason': f'特征工程失败：{str(e)}'}
            self._cache[cache_key] = result
            return result
        
        # 3. 训练模型（或加载已训练模型）
        try:
            # 检查是否有已保存的模型
            import os
            model_path = os.path.join(self.predictor.model_dir, 'rf_classifier.pkl')
            
            if os.path.exists(model_path):
                # 加载已有模型
                import pickle
                with open(model_path, 'rb') as f:
                    self.predictor.models['rf'] = pickle.load(f)
            else:
                # 训练新模型
                train_result = self.predictor.train_classifier(features, 'rf')
                if not train_result['success']:
                    result = {'signal': None, 'reason': f'模型训练失败：{train_result.get("error", "未知错误")}'}
                    self._cache[cache_key] = result
                    return result
        except Exception as e:
            result = {'signal': None, 'reason': f'模型加载/训练失败：{str(e)}'}
            self._cache[cache_key] = result
            return result
        
        # 4. 预测方向
        try:
            pred = self.predictor.predict_direction(features, 'rf')
            if not pred['success']:
                result = {'signal': None, 'reason': f'预测失败：{pred.get("error", "未知错误")}'}
                self._cache[cache_key] = result
                return result
        except Exception as e:
            result = {'signal': None, 'reason': f'预测异常：{str(e)}'}
            self._cache[cache_key] = result
            return result
        
        # 5. 生成信号
        direction = pred['prediction']
        probability = pred['probability']
        confidence = pred['confidence']
        
        # 概率阈值过滤
        if probability < self.probability_threshold:
            result = {
                'signal': None,
                'reason': f'预测概率过低 ({probability*100:.1f}% < {self.probability_threshold*100:.0f}%)',
                'filtered': True
            }
            self._cache[cache_key] = result
            return result
        
        # 确定信号强度
        if probability >= 0.8 and confidence == 'high':
            strength = 'strong'
        elif probability >= 0.7 or confidence == 'high':
            strength = 'normal'
        else:
            strength = 'weak'
        
        # 生成信号
        if direction == 'up':
            signal = 'buy'
            reason = f'ML 预测上涨 (概率{probability*100:.1f}%, {confidence})'
        else:
            signal = 'sell'
            reason = f'ML 预测下跌 (概率{probability*100:.1f}%, {confidence})'
        
        result = {
            'signal': signal,
            'reason': reason,
            'strength': strength,
            'ml_data': {
                'direction': direction,
                'probability': probability,
                'confidence': confidence
            }
        }
        
        self._cache[cache_key] = result
        return result
    
    def get_all_predictions(self, stock_pool):
        """
        获取股票池所有股票的预测结果
        
        Args:
            stock_pool: 股票代码列表
            
        Returns:
            dict: {code: prediction_dict}
        """
        predictions = {}
        
        for code in stock_pool:
            try:
                # 获取历史数据
                df = self.data_provider.get_history(code, days=self.lookback_days)
                if df is None or len(df) < self.min_train_samples:
                    continue
                
                # 获取模拟报价（用于 check 方法）
                quote = {
                    'current': df['close'].iloc[-1],
                    'open': df['open'].iloc[-1],
                    'high': df['high'].iloc[-1],
                    'low': df['low'].iloc[-1]
                }
                
                # 调用 check 方法
                result = self.check(code, '', quote, df, None, self.config)
                
                if result['signal']:
                    predictions[code] = result
                    
            except Exception as e:
                print(f"[ML] 预测失败 {code}: {e}")
                continue
        
        return predictions


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("ML 策略模块 - 测试")
    print("=" * 60)
    
    # 模拟配置
    config = {
        'ml_lookback_days': 200,
        'ml_min_train_samples': 60,
        'ml_probability_threshold': 0.6,
        'ml_model_dir': 'ml/models'
    }
    
    strategy = MLStrategy(config)
    
    # 测试单只股票
    from data.provider import DataProvider
    dp = DataProvider()
    
    test_stock = 'sh.600000'
    print(f"\n📊 测试股票：{test_stock}")
    
    df = dp.get_history(test_stock, days=200)
    if df is not None:
        quote = {
            'current': df['close'].iloc[-1],
            'open': df['open'].iloc[-1],
            'high': df['high'].iloc[-1],
            'low': df['low'].iloc[-1]
        }
        
        result = strategy.check(test_stock, '', quote, df, None, config)
        
        print(f"信号：{result.get('signal', '无')}")
        print(f"原因：{result.get('reason', '')}")
        print(f"强度：{result.get('strength', 'N/A')}")
        
        if result.get('ml_data'):
            ml = result['ml_data']
            print(f"\nML 详情:")
            print(f"  预测：{ml['direction']}")
            print(f"  概率：{ml['probability']*100:.1f}%")
            print(f"  置信度：{ml['confidence']}")
    else:
        print("❌ 数据获取失败")
    
    print("\n" + "=" * 60)
