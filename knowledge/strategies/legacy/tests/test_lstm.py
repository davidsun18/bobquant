#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LSTM 价格预测测试
测试 TensorFlow LSTM 模型的价格预测功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml import MLPredictor
from data.provider import get_provider
import pandas as pd
import numpy as np


def test_lstm():
    """测试 LSTM 价格预测"""
    print("=" * 70)
    print("LSTM 价格预测测试")
    print("=" * 70)
    
    # 获取测试数据
    print("\n📊 获取测试数据...")
    dp = get_provider('tencent')
    test_stock = 'sh.600000'
    df = dp.get_history(test_stock, days=200)
    
    if df is None or len(df) < 60:
        print(f"❌ 数据不足")
        return
    
    print(f"✅ 获取到 {len(df)} 天数据")
    print(f"   最新收盘价：¥{df['close'].iloc[-1]:.2f}")
    
    # 准备特征
    print("\n📐 特征工程...")
    predictor = MLPredictor()
    features = predictor.prepare_features(df)
    print(f"✅ 生成 {len(features.columns)} 个特征")
    
    # 训练 LSTM 模型
    print("\n🤖 训练 LSTM 模型...")
    print("   (首次训练约需 30-60 秒)")
    
    result = predictor.train_lstm(features, epochs=30)
    
    if result['success']:
        print(f"✅ LSTM 训练完成")
        print(f"   训练样本：{result['train_samples']}")
        print(f"   测试样本：{result['test_samples']}")
        print(f"   MSE: {result['mse']:.6f}")
        print(f"   训练轮数：{result['epochs_trained']}")
        
        # 显示损失下降趋势
        if 'loss_history' in result:
            print(f"   损失趋势：{result['loss_history'][0]:.4f} → {result['loss_history'][-1]:.4f}")
    else:
        print(f"❌ 训练失败：{result.get('error', '未知错误')}")
        return
    
    # 价格预测
    print("\n🔮 预测未来 5 天价格...")
    pred = predictor.predict_price(features, days=5)
    
    if pred['success']:
        print(f"✅ 价格预测完成")
        print(f"   当前价格：¥{pred['current_price']:.2f}")
        print(f"   预测趋势：{'📈 上涨' if pred['trend'] == 'up' else '📉 下跌'}")
        print(f"\n   预测详情:")
        for i, price in enumerate(pred['predictions'], 1):
            change = (price - pred['current_price']) / pred['current_price'] * 100
            arrow = '↑' if change > 0 else '↓'
            print(f"     第{i}天：¥{price:.2f} ({arrow} {abs(change):.2f}%)")
    else:
        print(f"❌ 预测失败：{pred.get('error', '未知错误')}")
    
    # 方向预测
    print("\n🔮 预测明日涨跌方向...")
    direction = predictor.predict_direction(features, 'rf')
    
    if direction['success']:
        icon = "📈" if direction['prediction'] == 'up' else "📉"
        print(f"{icon} 预测：{direction['prediction']}")
        print(f"   概率：{direction['probability']*100:.1f}%")
        print(f"   置信度：{direction['confidence']}")
    else:
        print(f"❌ 预测失败：{direction.get('error', '未知错误')}")
    
    print("\n" + "=" * 70)
    print("✅ LSTM 测试完成")
    print("=" * 70)


if __name__ == '__main__':
    test_lstm()
