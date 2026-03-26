"""
三大系统集成演示脚本
展示情绪指数 + ML 预测 + 现有策略引擎的协同工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentiment import SentimentIndex
from ml import MLPredictor
import pandas as pd
import numpy as np
from datetime import datetime


def generate_mock_data():
    """生成模拟股票数据用于演示"""
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=200, freq='D')
    
    # 生成价格走势
    close = 50 + np.cumsum(np.random.randn(200) * 0.5)
    
    df = pd.DataFrame({
        'date': dates,
        'open': close + np.random.uniform(-1, 1, 200),
        'high': close + np.abs(np.random.randn(200)),
        'low': close - np.abs(np.random.randn(200)),
        'close': close,
        'volume': np.random.uniform(1000000, 10000000, 200)
    })
    df.set_index('date', inplace=True)
    return df


def main():
    print("=" * 70)
    print("⚡ BobQuant 三大系统集成演示")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 初始化模块
    sentiment = SentimentIndex()
    ml_predictor = MLPredictor()
    
    # 生成数据
    print("📊 准备市场数据...")
    market_data = generate_mock_data()
    print(f"   数据范围：{market_data.index[0].date()} ~ {market_data.index[-1].date()}")
    print(f"   样本数：{len(market_data)}")
    print()
    
    # ========== 1. 情绪指数系统 ==========
    print("━" * 70)
    print("1️⃣ AI-Agent-Alpha 情绪指数系统")
    print("━" * 70)
    
    sentiment_result = sentiment.calculate_sentiment_score()
    
    score = sentiment_result['score']
    level = sentiment_result['level']
    
    # 显示情绪等级图标
    level_icons = {
        'extreme_high': '🔥',
        'high': '📈',
        'neutral': '➡️',
        'low': '📉',
        'extreme_low': '❄️'
    }
    
    print(f"{level_icons.get(level, '📊')} 情绪评分：{score} / 100")
    print(f"   情绪等级：{level}")
    
    # 显示核心指标
    indicators = sentiment_result.get('indicators', {})
    if indicators:
        print(f"\n📋 核心指标:")
        print(f"   • 涨停家数：{indicators.get('limit_up_count', 'N/A')}")
        print(f"   • 跌停家数：{indicators.get('limit_down_count', 'N/A')}")
        print(f"   • 涨跌停比：{indicators.get('limit_up_down_ratio', 'N/A')}")
        print(f"   • 炸板率：{indicators.get('bomb_board_rate', 'N/A')}")
        print(f"   • 赚钱效应：{indicators.get('profit_effect', 0) * 100:.1f}%")
    
    # 仓位建议
    pos = sentiment_result['position_suggestion']
    print(f"\n💡 仓位建议:")
    print(f"   • 建议仓位：{pos['suggested_position']}%")
    print(f"   • 操作：{pos['action']}")
    print(f"   • 风险等级：{pos['risk_level']}")
    print(f"   • 原因：{pos['reason']}")
    
    if sentiment_result.get('divergence_warning'):
        print(f"\n⚠️ 背离警告：{sentiment_result['divergence_warning']}")
    
    print()
    
    # ========== 2. ML 预测模块 ==========
    print("━" * 70)
    print("2️⃣ ML 股票预测算法库")
    print("━" * 70)
    
    # 特征工程
    features = ml_predictor.prepare_features(market_data)
    print(f"📐 特征工程完成：{len(features.columns)} 个特征")
    
    # 训练模型
    print(f"\n🤖 训练随机森林分类器...")
    train_result = ml_predictor.train_classifier(features, 'rf')
    
    if train_result['success']:
        print(f"   ✅ 训练完成")
        print(f"   • 训练样本：{train_result['train_samples']}")
        print(f"   • 测试样本：{train_result['test_samples']}")
        print(f"   • 准确率：{train_result['accuracy']*100:.2f}%")
    else:
        print(f"   ❌ 训练失败：{train_result['error']}")
    
    # 预测方向
    print(f"\n🔮 预测明日涨跌...")
    direction_pred = ml_predictor.predict_direction(features, 'rf')
    
    if direction_pred['success']:
        direction_icon = "📈" if direction_pred['prediction'] == 'up' else "📉"
        print(f"   {direction_icon} 预测：{direction_pred['prediction']}")
        print(f"   • 概率：{direction_pred['probability']*100:.1f}%")
        print(f"   • 置信度：{direction_pred['confidence']}")
    else:
        print(f"   ❌ 预测失败：{direction_pred['error']}")
    
    print()
    
    # ========== 3. 综合决策 ==========
    print("━" * 70)
    print("3️⃣ 综合决策引擎")
    print("━" * 70)
    
    # 基于情绪和 ML 预测生成综合信号
    ml_signal = 1 if direction_pred.get('prediction') == 'up' else -1
    ml_confidence = direction_pred.get('probability', 0.5)
    
    # 情绪调整因子
    if score > 70:
        sentiment_factor = 0.8  # 情绪高涨，降低仓位
    elif score < 30:
        sentiment_factor = 1.2  # 情绪低迷，增加仓位
    else:
        sentiment_factor = 1.0
    
    # 综合信号强度
    signal_strength = ml_signal * ml_confidence * sentiment_factor
    
    print(f"📊 信号分析:")
    print(f"   • ML 信号：{'看涨' if ml_signal > 0 else '看跌'} (置信度：{ml_confidence*100:.1f}%)")
    print(f"   • 情绪因子：{sentiment_factor:.2f}x")
    print(f"   • 综合信号强度：{signal_strength:.3f}")
    
    # 生成交易建议
    print(f"\n💼 交易建议:")
    
    if signal_strength > 0.6:
        print(f"   ✅ 强烈建议买入")
        position = min(pos['suggested_position'] + 10, 100)
        print(f"   📌 建议仓位：{position}%")
    elif signal_strength > 0.3:
        print(f"   ✅ 建议买入")
        position = pos['suggested_position']
        print(f"   📌 建议仓位：{position}%")
    elif signal_strength > -0.3:
        print(f"   ⏸️ 观望")
        print(f"   📌 建议仓位：{position}%")
    elif signal_strength > -0.6:
        print(f"   ⚠️ 建议减仓")
        position = max(pos['suggested_position'] - 10, 0)
        print(f"   📌 建议仓位：{position}%")
    else:
        print(f"   ❌ 强烈建议卖出")
        print(f"   📌 建议仓位：0%")
    
    print()
    
    # ========== 4. RQAlpha 架构参考 ==========
    print("━" * 70)
    print("3️⃣ RQAlpha 架构参考")
    print("━" * 70)
    
    print("📚 架构设计理念:")
    print(f"   • 事件驱动：参考 RQAlpha 的事件总线设计")
    print(f"   • 模块化：情绪/ML/策略独立模块，可插拔")
    print(f"   • 扩展性：Mod Hook 接口，便于对接第三方")
    print(f"   • 风控前置：交易前风控校验")
    
    print(f"\n🔄 事件流:")
    print(f"   市场数据 → 情绪分析 → ML 预测 → 策略信号 → 风控 → 执行")
    
    print()
    
    # ========== 总结 ==========
    print("=" * 70)
    print("📋 集成总结")
    print("=" * 70)
    
    print("""
✅ 已完成集成:
   1. AI-Agent-Alpha 情绪指数系统 → bobquant/sentiment/
   2. ML 股票预测算法库 → bobquant/ml/
   3. RQAlpha 架构参考 → 设计理念融入现有系统

📁 模块位置:
   • 情绪指数：bobquant/sentiment/sentiment_index.py
   • ML 预测：bobquant/ml/predictor.py
   • 集成演示：bobquant/integration_demo.py

🚀 下一步:
   1. 将情绪分数集成到策略引擎 (仓位控制)
   2. 将 ML 预测集成到信号生成 (买卖信号)
   3. 完善事件驱动架构
   4. 添加更多 ML 模型 (LSTM/Prophet/SVM)
   5. 实盘数据对接 (替换模拟数据)

⚠️ 注意事项:
   • 当前使用模拟数据，需对接真实数据源
   • LSTM 需要安装 tensorflow: pip install tensorflow
   • ML 模型需要充分训练和回测验证
   • 情绪指数需要全市场数据支持
""")
    
    print("=" * 70)


if __name__ == '__main__':
    main()
