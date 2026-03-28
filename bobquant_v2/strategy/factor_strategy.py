"""
多因子策略引擎
基于P0+P1因子构建交易策略
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class Signal:
    """交易信号"""
    code: str
    name: str
    signal: SignalType
    score: int  # 0-100
    reasons: List[str]
    confidence: str  # 'high', 'medium', 'low'


class FactorStrategy:
    """
    多因子策略
    
    综合P0+P1因子生成交易信号
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 默认配置
        self.rsi_buy_threshold = self.config.get('rsi_buy', 30)
        self.rsi_sell_threshold = self.config.get('rsi_sell', 70)
        self.score_buy_threshold = self.config.get('score_buy', 70)
        self.score_sell_threshold = self.config.get('score_sell', 30)
        self.volume_ratio_threshold = self.config.get('volume_ratio', 1.2)
    
    def analyze(self, code: str, name: str, df, quote: Dict) -> Signal:
        """
        分析股票，生成信号
        
        Args:
            code: 股票代码
            name: 股票名称
            df: K线数据
            quote: 实时行情
        
        Returns:
            Signal对象
        """
        from ..indicator.technical import all_indicators, generate_signals
        from ..indicator.qa_parser import compute_alpha158_20
        
        # 计算所有技术指标 (P0+P1+P2)
        df = all_indicators(df)
        
        # 计算 QuantaAlpha ALPHA158_20 因子
        df = compute_alpha158_20(df)
        
        # 生成信号
        signals = generate_signals(df)
        
        if not signals:
            return Signal(code, name, SignalType.HOLD, 50, [], 'low')
        
        # 分析理由
        reasons = []
        
        # MACD分析
        if signals['macd_signal'] == 'buy':
            reasons.append('MACD金叉')
        elif signals['macd_signal'] == 'sell':
            reasons.append('MACD死叉')
        
        # RSI分析
        if signals['rsi_signal'] == 'oversold':
            reasons.append(f"RSI超卖({df['rsi'].iloc[-1]:.1f})")
        elif signals['rsi_signal'] == 'overbought':
            reasons.append(f"RSI超买({df['rsi'].iloc[-1]:.1f})")
        
        # KDJ分析
        if signals['kdj_signal'] == 'buy':
            reasons.append('KDJ金叉')
        elif signals['kdj_signal'] == 'sell':
            reasons.append('KDJ死叉')
        
        # 布林带分析
        if signals['boll_signal'] == 'break_upper':
            reasons.append('突破布林上轨')
        elif signals['boll_signal'] == 'break_lower':
            reasons.append('跌破布林下轨')
        elif signals['boll_signal'] == 'squeeze':
            reasons.append('布林带收口')
        
        # 成交量分析
        if 'volume_ratio' in df.columns:
            vol_ratio = df['volume_ratio'].iloc[-1]
            if vol_ratio > self.volume_ratio_threshold:
                reasons.append(f'放量({vol_ratio:.1f}x)')
        
        # 动量分析
        if 'mom5' in df.columns:
            mom5 = df['mom5'].iloc[-1]
            if mom5 > 3:
                reasons.append(f'5日涨幅{mom5:.1f}%')
            elif mom5 < -3:
                reasons.append(f'5日跌幅{abs(mom5):.1f}%')
        
                # ===== QuantaAlpha 因子分析 (回测验证有效) =====
        # 基于 78 天回测，5 只股票验证
        
        # 从基础分开始调整
        score = signals['composite_score']
        
        # RSV5 超买超卖 (胜率 79.12%！IC=-0.17)
        if 'qa_rsv5' in df.columns:
            rsv5 = df['qa_rsv5'].iloc[-1]
            if rsv5 < 0.2:
                reasons.append(f'RSV5 超卖 (胜率 79%!)')
                score += 25  # 超卖买入信号
            elif rsv5 > 0.8:
                reasons.append(f'RSV5 超买 (风险)')
                score -= 25  # 超买卖出信号
        
        # ROC10 反向信号 (IC=-0.34 最强因子)
        if 'qa_roc10' in df.columns:
            roc10 = df['qa_roc10'].iloc[-1] * 100
            if roc10 < -10:
                reasons.append(f'ROC10 大跌 ({roc10:.1f}%, 预期反弹)')
                score += 30  # 过去大跌，预期均值回归
            elif roc10 > 10:
                reasons.append(f'ROC10 大涨 ({roc10:.1f}%, 预期回调)')
                score -= 30  # 过去大涨，预期回调
        
        # ROC5 反向信号 (IC=-0.16)
        if 'qa_roc5' in df.columns:
            roc5 = df['qa_roc5'].iloc[-1] * 100
            if roc5 < -8:
                reasons.append(f'ROC5 超跌 ({roc5:.1f}%)')
                score += 15
            elif roc5 > 8:
                reasons.append(f'ROC5 超涨 ({roc5:.1f}%)')
                score -= 15
        
        # 波动率正向信号 (IC=+0.19)
        if 'qa_volatility10' in df.columns:
            vol10 = df['qa_volatility10'].iloc[-1] * 100
            if vol10 > 8:
                reasons.append(f'高波动 ({vol10:.1f}%)')
                score += 20  # 高波动率股票预期收益更高
        
        # 均线比率反向 (IC=-0.31)
        if 'qa_ma_ratio5_10' in df.columns:
            ma_ratio = df['qa_ma_ratio5_10'].iloc[-1] * 100
            if ma_ratio < -3:
                reasons.append(f'均线低估 (预期修复)')
                score += 20
            elif ma_ratio > 5:
                reasons.append(f'均线高估 (预期回调)')
                score -= 25

# 确定信号类型
        score = signals['composite_score']
        
        if score >= 80:
            signal_type = SignalType.STRONG_BUY
            confidence = 'high'
        elif score >= self.score_buy_threshold:
            signal_type = SignalType.BUY
            confidence = 'medium'
        elif score <= 20:
            signal_type = SignalType.STRONG_SELL
            confidence = 'high'
        elif score <= self.score_sell_threshold:
            signal_type = SignalType.SELL
            confidence = 'medium'
        else:
            signal_type = SignalType.HOLD
            confidence = 'low'
        
        return Signal(
            code=code,
            name=name,
            signal=signal_type,
            score=score,
            reasons=reasons,
            confidence=confidence
        )
    
    def filter_signals(self, signals: List[Signal], min_score: int = 60) -> List[Signal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            min_score: 最低分数
        
        Returns:
            过滤后的信号列表
        """
        # 只保留买入信号，且分数达标
        buy_signals = [s for s in signals 
                      if s.signal in [SignalType.BUY, SignalType.STRONG_BUY] 
                      and s.score >= min_score]
        
        # 按分数排序
        buy_signals.sort(key=lambda x: x.score, reverse=True)
        
        return buy_signals
    
    def get_position_suggestion(self, signal: Signal, current_pos: Dict = None) -> Dict:
        """
        获取仓位建议
        
        Args:
            signal: 交易信号
            current_pos: 当前持仓
        
        Returns:
            {'action': 'buy'/'sell'/'hold', 'shares': int, 'reason': str}
        """
        if signal.signal in [SignalType.STRONG_BUY, SignalType.BUY]:
            # 买入建议
            if signal.confidence == 'high':
                shares = 1000  # 强信号多买
            else:
                shares = 500   # 普通信号少买
            
            return {
                'action': 'buy',
                'shares': shares,
                'reason': f"{signal.name}: {', '.join(signal.reasons)} (评分:{signal.score})"
            }
        
        elif signal.signal in [SignalType.STRONG_SELL, SignalType.SELL]:
            # 卖出建议
            if current_pos and current_pos.get('shares', 0) > 0:
                return {
                    'action': 'sell',
                    'shares': current_pos['shares'],
                    'reason': f"{signal.name}: {', '.join(signal.reasons)} (评分:{signal.score})"
                }
        
        return {'action': 'hold', 'shares': 0, 'reason': '无明确信号'}


# 预定义策略配置
STRATEGY_CONFIGS = {
    'conservative': {
        # 保守策略：严格条件
        'rsi_buy': 25,
        'rsi_sell': 75,
        'score_buy': 75,
        'score_sell': 25,
        'volume_ratio': 1.5
    },
    'balanced': {
        # 平衡策略：适中条件
        'rsi_buy': 30,
        'rsi_sell': 70,
        'score_buy': 70,
        'score_sell': 30,
        'volume_ratio': 1.2
    },
    'aggressive': {
        # 激进策略：宽松条件
        'rsi_buy': 35,
        'rsi_sell': 65,
        'score_buy': 60,
        'score_sell': 40,
        'volume_ratio': 1.0
    }
}


def create_strategy(style: str = 'balanced') -> FactorStrategy:
    """
    创建策略实例
    
    Args:
        style: 'conservative'/'balanced'/'aggressive'
    """
    config = STRATEGY_CONFIGS.get(style, STRATEGY_CONFIGS['balanced'])
    return FactorStrategy(config)
