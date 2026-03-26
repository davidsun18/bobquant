#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
早盘预览报告
生成情绪日报 + ML 预测信号
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.sentiment_controller import SentimentController
from strategy.ml_strategy import MLStrategy
from data.provider import get_provider


def generate_morning_preview():
    """生成早盘预览报告"""
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    print("=" * 70)
    print(f"📊 BobQuant v1.0 早盘预览")
    print(f"时间：{today}")
    print("=" * 70)
    
    # ========== 1. 情绪指数 ==========
    print("\n" + "=" * 70)
    print("1️⃣ 市场情绪指数")
    print("=" * 70)
    
    controller = SentimentController({})
    sentiment = controller.get_sentiment(force_refresh=True)
    
    score = sentiment['score']
    level = sentiment['level']
    
    # 情绪图标
    level_icons = {
        'extreme_high': '🔥',
        'high': '📈',
        'neutral': '➡️',
        'low': '📉',
        'extreme_low': '❄️'
    }
    
    print(f"\n{level_icons.get(level, '📊')} 情绪评分：{score:.1f} / 100")
    print(f"📈 情绪等级：{level}")
    
    # 核心指标
    indicators = sentiment.get('indicators', {})
    if indicators:
        print(f"\n📋 核心指标:")
        print(f"  • 涨停家数：{indicators.get('limit_up_count', 'N/A')}")
        print(f"  • 跌停家数：{indicators.get('limit_down_count', 'N/A')}")
        print(f"  • 涨跌停比：{indicators.get('limit_up_down_ratio', 'N/A')}")
        print(f"  • 炸板率：{indicators.get('bomb_board_rate', 'N/A')}")
        print(f"  • 赚钱效应：{indicators.get('profit_effect', 0) * 100:.1f}%")
    
    # 仓位建议
    pos = sentiment['position_suggestion']
    print(f"\n💡 仓位建议:")
    print(f"  • 建议仓位：{pos['suggested_position']}%")
    print(f"  • 操作：{pos['action']}")
    print(f"  • 风险：{pos['risk_level']}")
    print(f"  • 原因：{pos['reason']}")
    
    # 仓位上限
    limit = controller.get_position_limit()
    print(f"\n📌 今日仓位上限：{limit}%")
    
    # 风险预警
    risk = controller.get_risk_warning()
    if risk['warnings']:
        print(f"\n⚠️ 风险预警:")
        for w in risk['warnings']:
            print(f"  {w}")
    if risk['suggestions']:
        print(f"\n📌 操作建议:")
        for s in risk['suggestions']:
            print(f"  • {s}")
    
    # ========== 2. ML 预测信号 ==========
    print("\n" + "=" * 70)
    print("2️⃣ ML 预测信号 (股票池前 20 只)")
    print("=" * 70)
    
    # 加载股票池
    from config import get_settings
    s = get_settings()
    stock_pool = s.stock_pool[:20]  # 前 20 只
    
    config = {
        'ml_lookback_days': 200,
        'ml_min_train_samples': 60,
        'ml_probability_threshold': 0.6,
        'ml_model_dir': 'ml/models'
    }
    
    strategy = MLStrategy(config)
    dp = get_provider('tencent')
    
    predictions = {
        'buy_strong': [],
        'buy_normal': [],
        'sell_strong': [],
        'sell_normal': [],
        'none': []
    }
    
    print(f"\n🔄 正在分析 {len(stock_pool)} 只股票...")
    
    for stock in stock_pool:
        code = stock['code']
        name = stock['name']
        
        try:
            df = dp.get_history(code, days=200)
            if df is None or len(df) < 60:
                continue
            
            quote = {'current': df['close'].iloc[-1]}
            result = strategy.check(code, name, quote, df, None, config)
            
            if result['signal'] == 'buy':
                if result['strength'] == 'strong':
                    predictions['buy_strong'].append((code, name, result))
                else:
                    predictions['buy_normal'].append((code, name, result))
            elif result['signal'] == 'sell':
                if result['strength'] == 'strong':
                    predictions['sell_strong'].append((code, name, result))
                else:
                    predictions['sell_normal'].append((code, name, result))
            else:
                predictions['none'].append((code, name, result))
                
        except Exception as e:
            continue
    
    # 显示结果
    if predictions['buy_strong']:
        print(f"\n📈 强烈建议买入 ({len(predictions['buy_strong'])}只):")
        for code, name, result in predictions['buy_strong']:
            ml = result.get('ml_data', {})
            prob = ml.get('probability', 0) * 100
            print(f"  • {name}({code}): 概率{prob:.1f}% - {result['reason']}")
    
    if predictions['buy_normal']:
        print(f"\n📈 建议买入 ({len(predictions['buy_normal'])}只):")
        for code, name, result in predictions['buy_normal']:
            ml = result.get('ml_data', {})
            prob = ml.get('probability', 0) * 100
            print(f"  • {name}({code}): 概率{prob:.1f}% - {result['reason']}")
    
    if predictions['sell_strong']:
        print(f"\n📉 强烈建议卖出 ({len(predictions['sell_strong'])}只):")
        for code, name, result in predictions['sell_strong']:
            ml = result.get('ml_data', {})
            prob = ml.get('probability', 0) * 100
            print(f"  • {name}({code}): 概率{prob:.1f}% - {result['reason']}")
    
    if predictions['sell_normal']:
        print(f"\n📉 建议卖出 ({len(predictions['sell_normal'])}只):")
        for code, name, result in predictions['sell_normal']:
            ml = result.get('ml_data', {})
            prob = ml.get('probability', 0) * 100
            print(f"  • {name}({code}): 概率{prob:.1f}% - {result['reason']}")
    
    # 统计
    total = len(stock_pool)
    buy_count = len(predictions['buy_strong']) + len(predictions['buy_normal'])
    sell_count = len(predictions['sell_strong']) + len(predictions['sell_normal'])
    none_count = len(predictions['none'])
    
    print(f"\n📊 信号统计:")
    print(f"  买入信号：{buy_count}只 ({buy_count/total*100:.1f}%)")
    print(f"  卖出信号：{sell_count}只 ({sell_count/total*100:.1f}%)")
    print(f"  无信号：{none_count}只 ({none_count/total*100:.1f}%)")
    
    # ========== 3. 综合策略 ==========
    print("\n" + "=" * 70)
    print("3️⃣ 综合策略建议")
    print("=" * 70)
    
    print(f"\n📋 今日策略:")
    
    # 根据情绪和 ML 信号给出建议
    if score > 70:
        print(f"  ⚠️ 情绪高涨，建议降低仓位")
        print(f"  📌 只参与强烈买入信号")
    elif score > 50:
        print(f"  ✅ 情绪中性偏多，可适度参与")
        print(f"  📌 优先选择强烈买入信号")
    elif score > 30:
        print(f"  💡 情绪中性偏空，谨慎参与")
        print(f"  📌 控制仓位，快进快出")
    else:
        print(f"  💡 情绪低迷，可能是机会")
        print(f"  📌 可适度加仓优质股")
    
    # 结合 ML 信号
    if buy_count > sell_count * 2:
        print(f"\n📈 ML 信号偏多，可积极一些")
    elif sell_count > buy_count * 2:
        print(f"\n📉 ML 信号偏空，谨慎为主")
    else:
        print(f"\n➡️ ML 信号分化，精选个股")
    
    print("\n" + "=" * 70)
    print("🕐 9:25 自动开始交易")
    print("=" * 70)
    
    # 保存报告
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f'morning_preview_{datetime.now().strftime("%Y%m%d")}.md')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# BobQuant v1.0 早盘预览\n\n")
        f.write(f"**时间**: {today}\n\n")
        f.write(f"## 情绪指数\n\n")
        f.write(f"- 评分：{score:.1f}\n")
        f.write(f"- 等级：{level}\n")
        f.write(f"- 仓位上限：{limit}%\n")
    
    print(f"\n📁 报告已保存：{report_file}")


if __name__ == '__main__':
    generate_morning_preview()
