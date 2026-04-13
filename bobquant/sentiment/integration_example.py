# -*- coding: utf-8 -*-
"""
市场情绪分析集成示例
展示如何在策略引擎中使用 MarketSentimentAnalyzer

使用场景：
1. 在策略开仓前检查情绪状态
2. 根据情绪指数动态调整仓位
3. 在超买/超卖时发出预警
"""

from datetime import datetime
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentiment import MarketSentimentAnalyzer


class StrategyWithSentiment:
    """
    集成情绪分析的策略示例
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.sentiment_analyzer = MarketSentimentAnalyzer()
        
        # 情绪阈值配置
        self.overbought_threshold = self.config.get('overbought_threshold', 80)
        self.oversold_threshold = self.config.get('oversold_threshold', 20)
        
        # 仓位控制
        self.base_position = self.config.get('base_position', 60)  # 基础仓位%
        self.max_position = self.config.get('max_position', 90)    # 最大仓位%
        self.min_position = self.config.get('min_position', 30)    # 最小仓位%
    
    def should_open_position(self, signal):
        """
        根据情绪指数判断是否应该开仓
        
        Args:
            signal: 原始交易信号（包含 symbol, direction, strength 等）
            
        Returns:
            tuple: (should_open: bool, adjusted_size: int, reason: str)
        """
        # 获取当前情绪状态
        sentiment_data = self.sentiment_analyzer.get_sentiment_for_strategy()
        score = sentiment_data['composite_score']
        level = sentiment_data['sentiment_level']
        market_state = sentiment_data['market_state']
        
        # 1. 超买状态：禁止开多仓
        if score >= self.overbought_threshold and signal['direction'] == 'buy':
            return False, 0, f"市场超买（{score:.0f}分），禁止开多仓"
        
        # 2. 超卖状态：禁止开空仓（如果有做空）
        if score <= self.oversold_threshold and signal['direction'] == 'sell':
            return False, 0, f"市场超卖（{score:.0f}分），禁止开空仓"
        
        # 3. 根据情绪等级调整仓位
        position_limit = sentiment_data['position_limit']
        
        # 4. 计算调整后的仓位
        base_size = signal.get('size', 1000)
        
        # 情绪高涨时减仓，情绪低迷时加仓
        if level in ['extreme_high', 'high']:
            size_factor = 0.5  # 减半
        elif level == 'neutral':
            size_factor = 1.0  # 标准
        else:  # low, extreme_low
            size_factor = 1.2  # 增加 20%
        
        adjusted_size = int(base_size * size_factor)
        
        # 确保不超过仓位上限
        max_size = int(base_size * position_limit / 100)
        adjusted_size = min(adjusted_size, max_size)
        
        return True, adjusted_size, f"情绪{level}（{score:.0f}分），仓位调整至{adjusted_size}"
    
    def adjust_existing_position(self, current_position, symbol):
        """
        根据情绪指数调整现有仓位
        
        Args:
            current_position: 当前持仓
            symbol: 股票代码
            
        Returns:
            tuple: (action: str, size: int, reason: str)
        """
        sentiment_data = self.sentiment_analyzer.get_sentiment_for_strategy()
        score = sentiment_data['composite_score']
        level = sentiment_data['sentiment_level']
        
        # 极度高涨：建议减仓
        if level == 'extreme_high':
            reduce_size = int(current_position * 0.3)  # 减 30%
            return 'reduce', reduce_size, f"情绪极度高涨，减仓{reduce_size}股"
        
        # 极度低迷：建议加仓
        elif level == 'extreme_low':
            add_size = int(current_position * 0.2)  # 加 20%
            return 'add', add_size, f"情绪极度低迷，加仓{add_size}股"
        
        # 其他情况：维持
        return 'hold', 0, '维持现有仓位'
    
    def get_risk_alert(self):
        """
        获取风险预警
        
        Returns:
            dict: 风险预警信息
        """
        sentiment_data = self.sentiment_analyzer.get_sentiment_for_strategy()
        score = sentiment_data['composite_score']
        level = sentiment_data['sentiment_level']
        
        alerts = []
        alert_level = 'normal'
        
        if score >= self.overbought_threshold:
            alerts.append(f"⚠️ 市场超买（{score:.0f}分），警惕回调风险")
            alert_level = 'high'
        elif score >= 70:
            alerts.append(f"⚠️ 市场偏热（{score:.0f}分），注意风险")
            alert_level = 'medium'
        elif score <= self.oversold_threshold:
            alerts.append(f"💡 市场超卖（{score:.0f}分），可能是机会")
            alert_level = 'opportunity'
        elif score <= 30:
            alerts.append(f"💡 市场偏冷（{score:.0f}分），可关注机会")
            alert_level = 'low'
        
        return {
            'level': alert_level,
            'alerts': alerts,
            'score': score,
            'level_name': level
        }


# 使用示例
if __name__ == '__main__':
    print("=" * 70)
    print("市场情绪分析集成示例")
    print("=" * 70)
    
    # 创建策略实例
    config = {
        'overbought_threshold': 80,
        'oversold_threshold': 20,
        'base_position': 60,
        'max_position': 90,
        'min_position': 30
    }
    
    strategy = StrategyWithSentiment(config)
    
    # 模拟交易信号
    signal = {
        'symbol': 'sh600000',
        'direction': 'buy',
        'strength': 'strong',
        'size': 10000
    }
    
    # 1. 检查是否应该开仓
    print("\n1️⃣ 开仓决策")
    print("-" * 70)
    should_open, adjusted_size, reason = strategy.should_open_position(signal)
    print(f"原始信号：买入 {signal['size']} 股 {signal['symbol']}")
    print(f"决策：{'✅ 允许开仓' if should_open else '❌ 禁止开仓'}")
    if should_open:
        print(f"调整后仓位：{adjusted_size} 股")
    print(f"原因：{reason}")
    
    # 2. 调整现有仓位
    print("\n2️⃣ 仓位调整")
    print("-" * 70)
    current_position = 50000
    action, size, reason = strategy.adjust_existing_position(current_position, 'sh600000')
    print(f"当前持仓：{current_position} 股")
    print(f"操作：{action} {size} 股")
    print(f"原因：{reason}")
    
    # 3. 风险预警
    print("\n3️⃣ 风险预警")
    print("-" * 70)
    risk = strategy.get_risk_alert()
    print(f"预警等级：{risk['level']}")
    print(f"情绪评分：{risk['score']:.0f}")
    if risk['alerts']:
        print("预警信息:")
        for alert in risk['alerts']:
            print(f"  {alert}")
    
    # 4. 获取完整情绪报告
    print("\n4️⃣ 完整情绪报告")
    print("-" * 70)
    report = strategy.sentiment_analyzer.generate_report()
    print(report)
