"""
P2高级策略引擎
在P0+P1基础上，增加P2因子的精细化筛选
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from .factor_strategy import FactorStrategy, Signal, SignalType


class P2SignalType(Enum):
    """P2增强信号类型"""
    STRONG_BUY = "strong_buy"      # 强烈买入
    BUY = "buy"                     # 买入
    WEAK_BUY = "weak_buy"         # 试探性买入
    HOLD = "hold"                  # 观望
    WEAK_SELL = "weak_sell"       # 试探性卖出
    SELL = "sell"                  # 卖出
    STRONG_SELL = "strong_sell"   # 强烈卖出


@dataclass
class P2Signal:
    """P2增强信号"""
    code: str
    name: str
    signal: P2SignalType
    p1_score: int          # P1基础评分
    p2_adjustment: int     # P2调整分数
    final_score: int       # 最终评分
    reasons: list          # 所有理由
    risk_level: str        # 'low', 'medium', 'high'
    suggested_position: float  # 建议仓位比例 0-1


class P2Strategy(FactorStrategy):
    """
    P2高级策略
    
    继承P1策略，增加P2因子的精细化判断
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        
        # P2配置
        self.p2_config = {
            'min_trend_score': 40,      # 最小趋势强度
            'max_volatility': 50,       # 最大波动率(%)
            'require_money_inflow': False,  # 是否要求资金流入
            'min_pattern_score': 20,    # 最小形态得分
            'require_timeframe_align': False,  # 是否要求多周期一致
        }
        
        if config:
            self.p2_config.update(config.get('p2', {}))
    
    def analyze_p2(self, code: str, name: str, df, quote: Dict) -> P2Signal:
        """
        P2级别分析
        
        1. 先进行P1分析
        2. 计算P2因子
        3. 综合判断
        """
        from ..indicator.technical import all_indicators, generate_signals
        from ..indicator.advanced import AdvancedFactors, generate_p2_signals
        
        # 步骤1: P1分析
        p1_signal = self.analyze(code, name, df, quote)
        
        # 步骤2: 计算所有指标 (P0+P1+P2)
        df = all_indicators(df)
        df = AdvancedFactors.all_p2_factors(df)
        
        # 步骤3: 生成P2信号
        p2_signals = generate_p2_signals(df)
        
        # 步骤4: 综合评分
        p1_score = p1_signal.score
        p2_adjustment = self._calculate_p2_adjustment(p2_signals)
        final_score = max(0, min(100, p1_score + p2_adjustment))
        
        # 步骤5: 确定信号类型
        signal_type = self._determine_p2_signal(final_score, p2_signals)
        
        # 步骤6: 风险评估
        risk_level = self._assess_risk(p2_signals)
        
        # 步骤7: 仓位建议
        suggested_position = self._calculate_position(final_score, risk_level)
        
        # 合并理由
        all_reasons = p1_signal.reasons.copy()
        all_reasons.extend(self._get_p2_reasons(p2_signals))
        
        return P2Signal(
            code=code,
            name=name,
            signal=signal_type,
            p1_score=p1_score,
            p2_adjustment=p2_adjustment,
            final_score=final_score,
            reasons=all_reasons,
            risk_level=risk_level,
            suggested_position=suggested_position
        )
    
    def _calculate_p2_adjustment(self, p2_signals: Dict) -> int:
        """计算P2调整分数"""
        adjustment = 0
        
        # 趋势强度调整
        trend_score = p2_signals.get('trend_strength', 50)
        if trend_score > 70:
            adjustment += 10
        elif trend_score < 30:
            adjustment -= 10
        
        # 波动率调整
        if p2_signals.get('vol_squeeze', False):
            adjustment += 5
        
        # 资金流向调整
        if p2_signals.get('money_inflow', False):
            adjustment += 8
        
        # 技术形态调整
        pattern_score = p2_signals.get('pattern_score', 0)
        if pattern_score > 30:
            adjustment += 8
        elif pattern_score < -30:
            adjustment -= 8
        
        # 多时间周期调整
        if p2_signals.get('bullish_alignment', False):
            adjustment += 10
        elif p2_signals.get('bearish_alignment', False):
            adjustment -= 10
        
        return adjustment
    
    def _determine_p2_signal(self, final_score: int, p2_signals: Dict) -> P2SignalType:
        """确定P2信号类型"""
        
        # 根据最终评分确定
        if final_score >= 85:
            return P2SignalType.STRONG_BUY
        elif final_score >= 70:
            return P2SignalType.BUY
        elif final_score >= 55:
            return P2SignalType.WEAK_BUY
        elif final_score >= 45:
            return P2SignalType.HOLD
        elif final_score >= 30:
            return P2SignalType.WEAK_SELL
        elif final_score >= 15:
            return P2SignalType.SELL
        else:
            return P2SignalType.STRONG_SELL
    
    def _assess_risk(self, p2_signals: Dict) -> str:
        """评估风险等级"""
        risk_score = 0
        
        # 波动率风险
        if p2_signals.get('vol_state') == 'high':
            risk_score += 30
        
        # 趋势风险
        if p2_signals.get('trend_quality') == 'weak':
            risk_score += 20
        
        # 资金流出风险
        if p2_signals.get('money_inflow', False) is False:
            risk_score += 15
        
        # 形态风险
        if p2_signals.get('pattern_score', 0) < -20:
            risk_score += 15
        
        # 多周期风险
        if p2_signals.get('bearish_alignment', False):
            risk_score += 20
        
        if risk_score >= 60:
            return 'high'
        elif risk_score >= 30:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_position(self, final_score: int, risk_level: str) -> float:
        """计算建议仓位"""
        # 基础仓位
        if final_score >= 80:
            base_position = 1.0
        elif final_score >= 70:
            base_position = 0.8
        elif final_score >= 60:
            base_position = 0.6
        elif final_score >= 50:
            base_position = 0.4
        elif final_score >= 40:
            base_position = 0.2
        else:
            base_position = 0.0
        
        # 风险调整
        risk_factor = {'low': 1.0, 'medium': 0.7, 'high': 0.4}
        adjusted_position = base_position * risk_factor.get(risk_level, 0.5)
        
        return round(adjusted_position, 2)
    
    def _get_p2_reasons(self, p2_signals: Dict) -> list:
        """获取P2理由"""
        reasons = []
        
        # 趋势强度
        if p2_signals.get('trend_quality') == 'strong':
            reasons.append(f"趋势强度:{p2_signals['trend_strength']:.0f}")
        
        # 波动率
        if p2_signals.get('vol_squeeze', False):
            reasons.append("波动率收缩")
        
        # 资金流向
        if p2_signals.get('money_inflow', False):
            reasons.append(f"资金流入(MFI:{p2_signals['mfi']:.0f})")
        
        # 技术形态
        if p2_signals.get('has_hammer', False):
            reasons.append("锤子线")
        if p2_signals.get('has_engulfing', False):
            reasons.append("吞没形态")
        if p2_signals.get('has_star', False):
            reasons.append("星线形态")
        
        # 多时间周期
        if p2_signals.get('bullish_alignment', False):
            reasons.append("多周期多头排列")
        
        return reasons
    
    def filter_p2_signals(self, signals: list, min_score: int = 60, max_risk: str = 'medium') -> list:
        """
        过滤P2信号
        
        Args:
            signals: P2Signal列表
            min_score: 最低分数
            max_risk: 最高风险等级 ('low', 'medium', 'high')
        """
        risk_order = {'low': 0, 'medium': 1, 'high': 2}
        max_risk_level = risk_order.get(max_risk, 1)
        
        filtered = []
        for signal in signals:
            # 分数要求
            if signal.final_score < min_score:
                continue
            
            # 风险要求
            if risk_order.get(signal.risk_level, 3) > max_risk_level:
                continue
            
            # 只保留买入信号
            if signal.signal in [P2SignalType.STRONG_BUY, P2SignalType.BUY, P2SignalType.WEAK_BUY]:
                filtered.append(signal)
        
        # 按分数排序
        filtered.sort(key=lambda x: x.final_score, reverse=True)
        
        return filtered


def create_p2_strategy(style: str = 'balanced', p2_config: Dict = None) -> P2Strategy:
    """
    创建P2策略
    
    Args:
        style: 'conservative'/'balanced'/'aggressive'
        p2_config: P2专属配置
    """
    from .factor_strategy import STRATEGY_CONFIGS
    
    config = STRATEGY_CONFIGS.get(style, STRATEGY_CONFIGS['balanced']).copy()
    
    if p2_config:
        config['p2'] = p2_config
    
    return P2Strategy(config)
