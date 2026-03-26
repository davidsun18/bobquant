#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant v1.0 集成测试
测试 ML 预测 + 情绪指数 + 综合决策引擎
"""

import sys
import os

# 添加项目根目录到路径
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
os.chdir(base_dir)

# 使用绝对导入
from strategy.engine import DecisionEngine, MACDStrategy, BollingerStrategy
from data.provider import get_provider


def test_decision_engine():
    """测试综合决策引擎"""
    print("=" * 70)
    print("BobQuant v1.0 综合决策引擎测试")
    print("=" * 70)
    
    # 配置
    config = {
        'enable_ml': True,
        'enable_sentiment': True,
        'ml_signal_weight': 0.4,
        'ta_signal_weight': 0.6,
        'ml_lookback_days': 200,
        'ml_min_train_samples': 60,
        'ml_probability_threshold': 0.6,
        'ml_model_dir': 'ml/models',
        'base_position_pct': 60,
        'sentiment_high_threshold': 70,
        'sentiment_low_threshold': 30,
        'rsi_buy_max': 35,
        'rsi_sell_min': 70,
        'volume_confirm': True,
        'volume_ratio_buy': 1.5
    }
    
    # 初始化决策引擎
    print("\n🔧 初始化决策引擎...")
    engine = DecisionEngine(config)
    print("✅ 决策引擎就绪")
    
    # 获取测试数据
    print("\n📊 获取测试数据...")
    dp = get_provider('tencent')
    test_stock = 'sh.600000'
    df = dp.get_history(test_stock, days=200)
    
    if df is None or len(df) < 60:
        print(f"❌ 数据不足，跳过测试")
        return
    
    print(f"✅ 获取到 {len(df)} 天数据")
    
    # 获取最新报价
    quote = dp.get_quote(test_stock)
    if quote is None:
        quote = {
            'current': df['close'].iloc[-1],
            'open': df['open'].iloc[-1],
            'high': df['high'].iloc[-1],
            'low': df['low'].iloc[-1]
        }
    
    # 生成技术指标信号
    print("\n📐 生成技术指标信号...")
    
    ta_signals = []
    
    macd = MACDStrategy()
    macd_sig = macd.check(test_stock, '', quote, df, None, config)
    if macd_sig['signal']:
        ta_signals.append(macd_sig)
        print(f"  • MACD: {macd_sig['signal']} - {macd_sig['reason']}")
    
    bollinger = BollingerStrategy()
    bb_sig = bollinger.check(test_stock, '', quote, df, None, config)
    if bb_sig['signal']:
        ta_signals.append(bb_sig)
        print(f"  • 布林带：{bb_sig['signal']} - {bb_sig['reason']}")
    
    if not ta_signals:
        print("  ⚠️ 无技术指标信号")
    
    # 综合决策
    print("\n🧠 综合决策分析...")
    decision = engine.combine_signals(test_stock, '', quote, df, None, ta_signals)
    
    print(f"\n📊 决策结果:")
    print(f"  信号：{decision['signal'] if decision['signal'] else '无'}")
    print(f"  强度：{decision['strength']}")
    print(f"  置信度：{decision['confidence']*100:.0f}%")
    print(f"  原因：{decision['reason']}")
    
    # 信号源详情
    sources = decision['sources']
    if sources['ml']:
        ml = sources['ml']
        print(f"\n🤖 ML 预测:")
        print(f"  信号：{ml['signal']}")
        print(f"  强度：{ml['strength']}")
        if ml.get('ml_data'):
            print(f"  方向：{ml['ml_data']['direction']}")
            print(f"  概率：{ml['ml_data']['probability']*100:.1f}%")
            print(f"  置信度：{ml['ml_data']['confidence']}")
    
    # 情绪指数
    print("\n📈 情绪指数:")
    if engine.sentiment_controller:
        sentiment = engine.sentiment_controller.get_sentiment()
        print(f"  评分：{sentiment['score']:.1f}")
        print(f"  等级：{sentiment['level']}")
        print(f"  仓位上限：{engine.sentiment_controller.get_position_limit()}%")
    
    # 风险预警
    print("\n⚠️ 风险预警:")
    risk = engine.get_risk_warning()
    print(f"  风险等级：{risk['level']}")
    if risk['warnings']:
        for w in risk['warnings']:
            print(f"  {w}")
    if risk['suggestions']:
        print("  建议:")
        for s in risk['suggestions']:
            print(f"    • {s}")
    
    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == '__main__':
    test_decision_engine()
