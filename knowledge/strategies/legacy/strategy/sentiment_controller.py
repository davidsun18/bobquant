# -*- coding: utf-8 -*-
"""
市场情绪指数集成模块
用于全局仓位控制和风险预警
"""
from datetime import datetime
try:
    from ..sentiment import SentimentIndex
except ImportError:
    from sentiment import SentimentIndex


class SentimentController:
    """
    情绪指数控制器
    
    根据市场情绪评分动态调整：
    - 总仓位上限
    - 单只股票最大仓位
    - 开仓信号过滤
    - 风险预警
    """
    
    def __init__(self, config):
        self.config = config
        self.sentiment = SentimentIndex()
        
        # 仓位控制参数
        self.base_position = config.get('base_position_pct', 60)  # 基础仓位%
        self.min_position = config.get('min_position_pct', 30)   # 最小仓位%
        self.max_position = config.get('max_position_pct', 90)   # 最大仓位%
        
        # 情绪阈值
        self.high_threshold = config.get('sentiment_high_threshold', 70)   # 高涨阈值
        self.low_threshold = config.get('sentiment_low_threshold', 30)     # 低迷阈值
        
        # 缓存
        self._cache = None
        self._cache_date = None
    
    def get_sentiment(self, force_refresh=False):
        """
        获取情绪指数（带缓存）
        
        Args:
            force_refresh: 强制刷新缓存
            
        Returns:
            dict: 情绪指数结果
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 检查缓存
        if not force_refresh and self._cache and self._cache_date == today:
            return self._cache
        
        # 获取最新情绪指数
        self._cache = self.sentiment.calculate_sentiment_score()
        self._cache_date = today
        
        return self._cache
    
    def get_position_limit(self):
        """
        根据情绪指数获取当前仓位上限
        
        Returns:
            int: 仓位上限百分比
        """
        sentiment = self.get_sentiment()
        score = sentiment['score']
        level = sentiment['level']
        
        # 根据情绪等级调整仓位上限
        if level == 'extreme_high':
            # 极度高涨：大幅降低仓位
            limit = min(self.max_position, 40)
        elif level == 'high':
            # 高涨：适度降低仓位
            limit = min(self.max_position, 60)
        elif level == 'neutral':
            # 中性：标准仓位
            limit = self.base_position
        elif level == 'low':
            # 低迷：适度提高仓位
            limit = max(self.min_position, 75)
        else:  # extreme_low
            # 极度低迷：高仓位
            limit = max(self.min_position, 85)
        
        return limit
    
    def should_reduce_position(self, current_position_pct):
        """
        判断是否应该主动减仓
        
        Args:
            current_position_pct: 当前仓位百分比
            
        Returns:
            tuple: (should_reduce: bool, target_pct: int, reason: str)
        """
        sentiment = self.get_sentiment()
        score = sentiment['score']
        level = sentiment['level']
        limit = self.get_position_limit()
        
        # 如果当前仓位超过上限，建议减仓
        if current_position_pct > limit + 10:  # 超过上限 10% 才触发
            excess = current_position_pct - limit
            return True, limit, f"情绪{level}({score}分)，仓位超限{excess:.1f}%"
        
        return False, limit, ''
    
    def should_filter_buy(self, signal_strength):
        """
        判断是否应该过滤买入信号
        
        Args:
            signal_strength: 原始信号强度 ('strong'/'normal'/'weak')
            
        Returns:
            tuple: (should_filter: bool, reason: str)
        """
        sentiment = self.get_sentiment()
        score = sentiment['score']
        level = sentiment['level']
        
        # 情绪极度高涨时，过滤所有买入信号
        if level == 'extreme_high':
            return True, f"情绪极度高涨 ({score:.0f}分)，过滤买入信号"
        
        # 情绪高涨时，只保留强信号
        if level == 'high' and signal_strength != 'strong':
            return True, f"情绪高涨 ({score:.0f}分)，只保留强信号"
        
        # 情绪中性或低迷时，不过滤
        return False, ''
    
    def adjust_position_size(self, base_size, signal_strength):
        """
        根据情绪调整建仓规模
        
        Args:
            base_size: 基础建仓规模（股数或金额）
            signal_strength: 信号强度
            
        Returns:
            int: 调整后的建仓规模
        """
        sentiment = self.get_sentiment()
        score = sentiment['score']
        
        # 计算调整系数
        if score >= 70:
            factor = 0.5  # 高涨：减半
        elif score >= 50:
            factor = 1.0  # 中性：标准
        elif score >= 30:
            factor = 1.2  # 低迷：增加 20%
        else:
            factor = 1.5  # 极度低迷：增加 50%
        
        # 强信号可以适度增加
        if signal_strength == 'strong':
            factor = min(factor * 1.2, 2.0)
        
        adjusted = int(base_size * factor)
        
        # 确保至少 100 股（1 手）
        return max(adjusted, 100) if adjusted > 0 else 0
    
    def get_risk_warning(self):
        """
        获取风险预警信息
        
        Returns:
            dict: {
                'level': 'high'/'medium'/'low',
                'warnings': list of str,
                'suggestions': list of str
            }
        """
        sentiment = self.get_sentiment()
        score = sentiment['score']
        level = sentiment['level']
        divergence = sentiment.get('divergence_warning')
        
        warnings = []
        suggestions = []
        
        # 风险等级
        if level in ['extreme_high', 'high']:
            risk_level = 'high'
        elif level in ['neutral']:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # 生成预警
        if level == 'extreme_high':
            warnings.append("⚠️ 市场情绪极度高涨，警惕回调风险")
            suggestions.append("建议大幅降低仓位至 40% 以下")
            suggestions.append("避免追高，可考虑止盈")
        
        elif level == 'high':
            warnings.append("⚠️ 市场情绪高涨，注意风险")
            suggestions.append("建议降低仓位至 60% 左右")
            suggestions.append("只参与强信号交易")
        
        elif level == 'low':
            warnings.append("💡 市场情绪低迷，可能是机会")
            suggestions.append("可逐步加仓至 75%")
            suggestions.append("关注优质股票建仓机会")
        
        elif level == 'extreme_low':
            warnings.append("💡 市场情绪极度低迷，布局机会")
            suggestions.append("可提高仓位至 85%")
            suggestions.append("积极寻找买入机会")
        
        # 背离警告
        if divergence:
            warnings.append(divergence)
        
        return {
            'level': risk_level,
            'warnings': warnings,
            'suggestions': suggestions,
            'sentiment_score': score,
            'sentiment_level': level
        }
    
    def get_daily_report(self):
        """
        生成情绪指数日报
        
        Returns:
            str: 格式化的日报文本
        """
        sentiment = self.get_sentiment()
        risk = self.get_risk_warning()
        
        report = []
        report.append("📊 市场情绪日报")
        report.append("=" * 50)
        report.append(f"日期：{datetime.now().strftime('%Y-%m-%d')}")
        report.append(f"情绪评分：{sentiment['score']:.1f} / 100")
        report.append(f"情绪等级：{sentiment['level']}")
        report.append("")
        
        # 核心指标
        indicators = sentiment.get('indicators', {})
        if indicators:
            report.append("📋 核心指标:")
            report.append(f"  • 涨停家数：{indicators.get('limit_up_count', 'N/A')}")
            report.append(f"  • 跌停家数：{indicators.get('limit_down_count', 'N/A')}")
            report.append(f"  • 涨跌停比：{indicators.get('limit_up_down_ratio', 'N/A')}")
            report.append(f"  • 炸板率：{indicators.get('bomb_board_rate', 'N/A')}")
            report.append(f"  • 赚钱效应：{indicators.get('profit_effect', 0) * 100:.1f}%")
            report.append("")
        
        # 仓位建议
        pos = sentiment['position_suggestion']
        report.append("💡 仓位建议:")
        report.append(f"  • 建议仓位：{pos['suggested_position']}%")
        report.append(f"  • 操作：{pos['action']}")
        report.append(f"  • 风险：{pos['risk_level']}")
        report.append("")
        
        # 风险预警
        if risk['warnings']:
            report.append("⚠️ 风险预警:")
            for w in risk['warnings']:
                report.append(f"  {w}")
            report.append("")
        
        # 操作建议
        if risk['suggestions']:
            report.append("📌 操作建议:")
            for s in risk['suggestions']:
                report.append(f"  • {s}")
        
        report.append("=" * 50)
        
        return "\n".join(report)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("情绪指数控制器 - 测试")
    print("=" * 60)
    
    config = {
        'base_position_pct': 60,
        'min_position_pct': 30,
        'max_position_pct': 90,
        'sentiment_high_threshold': 70,
        'sentiment_low_threshold': 30
    }
    
    controller = SentimentController(config)
    
    # 1. 获取情绪指数
    sentiment = controller.get_sentiment()
    print(f"\n📊 情绪评分：{sentiment['score']:.1f}")
    print(f"📈 情绪等级：{sentiment['level']}")
    
    # 2. 仓位上限
    limit = controller.get_position_limit()
    print(f"\n💼 当前仓位上限：{limit}%")
    
    # 3. 信号过滤测试
    for strength in ['strong', 'normal', 'weak']:
        should_filter, reason = controller.should_filter_buy(strength)
        status = "❌ 过滤" if should_filter else "✅ 通过"
        print(f"   {strength} 信号：{status} {reason}")
    
    # 4. 风险预警
    risk = controller.get_risk_warning()
    print(f"\n⚠️ 风险等级：{risk['level']}")
    if risk['warnings']:
        print("预警:")
        for w in risk['warnings']:
            print(f"  {w}")
    
    # 5. 日报
    print("\n" + "=" * 60)
    print("📋 情绪日报:")
    print("=" * 60)
    print(controller.get_daily_report())
