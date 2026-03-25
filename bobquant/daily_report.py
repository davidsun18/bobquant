#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant v1.0 每日优化报告
生成当日交易总结和优化建议
"""

import sys
import os
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings
from data.provider import get_provider


def generate_daily_report():
    """生成每日报告"""
    s = get_settings()
    today = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 70)
    print(f"📊 BobQuant v1.0 每日优化报告")
    print(f"日期：{today}")
    print("=" * 70)
    
    # 1. 读取交易日志
    print("\n📋 今日交易汇总:")
    # TODO: 从交易日志解析
    
    # 2. 情绪指数回顾
    from strategy.sentiment_controller import SentimentController
    controller = SentimentController({})
    sentiment = controller.get_sentiment()
    
    print(f"\n📈 情绪指数:")
    print(f"  评分：{sentiment['score']:.1f}")
    print(f"  等级：{sentiment['level']}")
    
    # 3. ML 预测准确率统计
    print(f"\n🤖 ML 预测:")
    # TODO: 统计今日预测与实际走势对比
    
    # 4. 优化建议
    print(f"\n💡 优化建议:")
    
    if sentiment['score'] > 70:
        print(f"  ⚠️ 情绪高涨，建议降低仓位上限")
    elif sentiment['score'] < 30:
        print(f"  💡 情绪低迷，可适度加仓")
    else:
        print(f"  ✅ 情绪中性，维持现有策略")
    
    # 5. 明日策略
    print(f"\n📅 明日策略重点:")
    print(f"  1. 观察 ML 预测准确率")
    print(f"  2. 监控情绪指数变化")
    print(f"  3. 根据实际表现调整参数")
    
    print("\n" + "=" * 70)
    
    # 保存报告
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f'daily_report_{today}.md')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# BobQuant v1.0 每日优化报告\n\n")
        f.write(f"**日期**: {today}\n\n")
        f.write(f"## 情绪指数\n\n")
        f.write(f"- 评分：{sentiment['score']:.1f}\n")
        f.write(f"- 等级：{sentiment['level']}\n")
    
    print(f"📁 报告已保存：{report_file}")


if __name__ == '__main__':
    generate_daily_report()
