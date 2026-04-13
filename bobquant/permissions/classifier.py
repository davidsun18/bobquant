# -*- coding: utf-8 -*-
"""
AI 分类器
用于交易审批的智能分类，根据交易特征自动决定是否询问用户
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = auto()       # 低风险
    NORMAL = auto()    # 普通风险
    HIGH = auto()      # 高风险
    CRITICAL = auto()  # 临界风险


@dataclass
class TradeFeatures:
    """交易特征"""
    symbol: str                    # 股票代码
    side: str                      # 买卖方向
    quantity: int                  # 数量
    price: float                   # 价格
    total_value: float             # 总金额
    board_type: str                # 板块类型
    is_new_stock: bool             # 是否新股
    price_change_pct: float        # 涨跌幅
    volume_ratio: float            # 量比
    turnover_rate: float           # 换手率
    strategy_type: str             # 策略类型
    holding_days: int              # 持仓天数 (卖出时)
    profit_rate: float             # 收益率 (卖出时)


class TradeClassifier:
    """
    交易分类器
    根据交易特征智能判断是否需要询问用户
    """
    
    def __init__(
        self,
        auto_approve_threshold: float = 10000.0,  # 自动批准金额阈值
        auto_deny_threshold: float = 100000.0,    # 自动拒绝金额阈值
        custom_rules: Optional[List[Callable]] = None
    ):
        """
        初始化分类器
        
        Args:
            auto_approve_threshold: 自动批准金额阈值 (元以下自动批准)
            auto_deny_threshold: 自动拒绝金额阈值 (元以上自动拒绝)
            custom_rules: 自定义规则函数列表
        """
        self.auto_approve_threshold = auto_approve_threshold
        self.auto_deny_threshold = auto_deny_threshold
        self.custom_rules = custom_rules or []
        
        # 板块风险系数
        self.board_risk_factors = {
            '主板': 1.0,
            '创业板': 1.5,
            '科创板': 2.0,
        }
        
        # 策略风险系数
        self.strategy_risk_factors = {
            'grid': 1.0,           # 网格交易 (低风险)
            'twap': 1.0,           # TWAP (低风险)
            'day_trading': 1.2,    # 日内交易 (中风险)
            'swing': 1.3,          # 波段交易 (中风险)
            'momentum': 1.5,       # 动量交易 (高风险)
            'breakout': 1.5,       # 突破交易 (高风险)
            'arbitrage': 1.1,      # 套利交易 (低风险)
        }
        
        logger.info("AI 分类器初始化")
    
    def classify(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        strategy: str = "",
        board_type: str = "主板",
        **kwargs
    ) -> Dict[str, Any]:
        """
        分类交易请求
        
        Args:
            symbol: 股票代码
            side: 买卖方向 (buy/sell)
            quantity: 数量
            price: 价格
            strategy: 策略名称
            board_type: 板块类型
            **kwargs: 其他特征参数
            
        Returns:
            dict: {'granted': bool, 'reason': str, 'risk_level': str}
        """
        # 计算总金额
        total_value = quantity * price
        
        # 提取特征
        features = TradeFeatures(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            total_value=total_value,
            board_type=board_type,
            is_new_stock=kwargs.get('is_new_stock', False),
            price_change_pct=kwargs.get('price_change_pct', 0.0),
            volume_ratio=kwargs.get('volume_ratio', 1.0),
            turnover_rate=kwargs.get('turnover_rate', 0.0),
            strategy_type=strategy,
            holding_days=kwargs.get('holding_days', 0),
            profit_rate=kwargs.get('profit_rate', 0.0),
        )
        
        # 计算风险分数
        risk_score = self._calculate_risk_score(features)
        risk_level = self._score_to_risk_level(risk_score)
        
        # 应用自定义规则
        for rule_func in self.custom_rules:
            try:
                result = rule_func(features)
                if result is not None:
                    logger.debug(f"自定义规则匹配：{rule_func.__name__}")
                    return result
            except Exception as e:
                logger.error(f"自定义规则执行错误：{e}")
        
        # 基于风险分数决策
        decision = self._make_decision(risk_score, risk_level, features)
        
        logger.info(
            f"分类结果：{symbol} {side} "
            f"风险分数={risk_score:.2f} 等级={risk_level.name} "
            f"决策={decision['granted']} 原因={decision['reason']}"
        )
        
        return decision
    
    def _calculate_risk_score(self, features: TradeFeatures) -> float:
        """
        计算风险分数 (0-100)
        
        分数越高表示风险越大
        """
        score = 0.0
        
        # 1. 金额风险 (0-30 分)
        if features.total_value < self.auto_approve_threshold:
            score += 5
        elif features.total_value < self.auto_approve_threshold * 10:
            score += 15
        elif features.total_value < self.auto_deny_threshold:
            score += 25
        else:
            score += 30
        
        # 2. 板块风险 (0-20 分)
        board_factor = self.board_risk_factors.get(features.board_type, 1.0)
        score += 10 * board_factor
        
        # 3. 策略风险 (0-20 分)
        strategy_factor = self.strategy_risk_factors.get(
            features.strategy_type.lower(), 1.2
        )
        score += 12 * strategy_factor
        
        # 4. 买卖方向风险 (0-10 分)
        if features.side.lower() == 'buy':
            # 买入风险较高
            score += 8
            # 新股买入风险更高
            if features.is_new_stock:
                score += 5
        else:
            # 卖出风险较低
            score += 3
            # 盈利卖出不增加风险
            if features.profit_rate > 0:
                score -= 2
        
        # 5. 市场波动风险 (0-20 分)
        # 涨跌幅过大增加风险
        if abs(features.price_change_pct) > 9:  # 涨停/跌停
            score += 15
        elif abs(features.price_change_pct) > 5:
            score += 10
        elif abs(features.price_change_pct) > 3:
            score += 5
        
        # 量比异常增加风险
        if features.volume_ratio > 5:
            score += 5
        elif features.volume_ratio < 0.2:
            score += 3
        
        # 6. 流动性风险 (0-10 分)
        if features.turnover_rate < 1:
            score += 8  # 低换手率，流动性差
        elif features.turnover_rate > 20:
            score += 5  # 过高换手率，可能异常
        
        return min(100, max(0, score))
    
    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """将分数转换为风险等级"""
        if score < 25:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.NORMAL
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _make_decision(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        features: TradeFeatures
    ) -> Dict[str, Any]:
        """基于风险分数做出决策"""
        
        # 低风险：自动批准
        if risk_level == RiskLevel.LOW:
            return {
                'granted': True,
                'reason': f"低风险交易 (分数={risk_score:.1f})",
                'risk_level': risk_level.name,
            }
        
        # 普通风险：根据金额决定
        if risk_level == RiskLevel.NORMAL:
            if features.total_value < self.auto_approve_threshold:
                return {
                    'granted': True,
                    'reason': f"普通风险但金额较小 ({features.total_value:.0f}元)",
                    'risk_level': risk_level.name,
                }
            else:
                return {
                    'granted': False,
                    'reason': f"普通风险交易，需要确认 (分数={risk_score:.1f})",
                    'risk_level': risk_level.name,
                }
        
        # 高风险：需要确认
        if risk_level == RiskLevel.HIGH:
            return {
                'granted': False,
                'reason': f"高风险交易，需要确认 (分数={risk_score:.1f})",
                'risk_level': risk_level.name,
            }
        
        # 临界风险：自动拒绝
        return {
            'granted': False,
            'reason': f"临界风险，建议重新评估 (分数={risk_score:.1f})",
            'risk_level': risk_level.name,
        }
    
    def add_custom_rule(self, rule_func: Callable):
        """
        添加自定义规则
        
        Args:
            rule_func: 规则函数，接收 TradeFeatures，返回 Dict 或 None
        """
        self.custom_rules.append(rule_func)
        logger.info(f"添加自定义规则：{rule_func.__name__}")
    
    def remove_custom_rule(self, rule_func: Callable):
        """移除自定义规则"""
        if rule_func in self.custom_rules:
            self.custom_rules.remove(rule_func)
            logger.info(f"移除自定义规则：{rule_func.__name__}")


# 预定义的自定义规则示例
def rule_new_stock_high_limit(features: TradeFeatures) -> Optional[Dict[str, Any]]:
    """
    规则：新股涨停不买入
    
    Returns:
        Dict if matched, None otherwise
    """
    if features.is_new_stock and features.price_change_pct >= 9.5 and features.side == 'buy':
        return {
            'granted': False,
            'reason': '新股涨停，不建议追高买入',
            'risk_level': 'HIGH',
        }
    return None


def rule_profit_take_auto_approve(features: TradeFeatures) -> Optional[Dict[str, Any]]:
    """
    规则：盈利超过 20% 的卖出自动批准
    
    Returns:
        Dict if matched, None otherwise
    """
    if features.side == 'sell' and features.profit_rate > 20:
        return {
            'granted': True,
            'reason': f'止盈卖出 (收益率={features.profit_rate:.1f}%)',
            'risk_level': 'LOW',
        }
    return None


def rule_loss_cut_auto_approve(features: TradeFeatures) -> Optional[Dict[str, Any]]:
    """
    规则：止损卖出自动批准
    
    Returns:
        Dict if matched, None otherwise
    """
    if features.side == 'sell' and features.profit_rate < -10:
        return {
            'granted': True,
            'reason': f'止损卖出 (收益率={features.profit_rate:.1f}%)',
            'risk_level': 'NORMAL',
        }
    return None


def rule_grid_trade_auto_approve(features: TradeFeatures) -> Optional[Dict[str, Any]]:
    """
    规则：网格交易自动批准
    
    Returns:
        Dict if matched, None otherwise
    """
    if features.strategy_type.lower() == 'grid' and features.total_value < 50000:
        return {
            'granted': True,
            'reason': '网格交易 (小额自动执行)',
            'risk_level': 'LOW',
        }
    return None
