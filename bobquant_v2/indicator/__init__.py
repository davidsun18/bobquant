"""
指标模块 - 技术指标和高级因子
"""

from .technical import (
    TechnicalIndicator,
    ma, macd, rsi, volume_ma,
    bollinger, kdj, atr, momentum,
    all_indicators, generate_signals
)

from .advanced import (
    AdvancedFactors,
    generate_p2_signals
)

from .qa_parser import (
    compute_alpha158_20,
    QAExpressionParser,
    compute_factor,
    compute_factors
)

__all__ = [
    # 技术指标
    'TechnicalIndicator',
    'ma', 'macd', 'rsi', 'volume_ma',
    'bollinger', 'kdj', 'atr', 'momentum',
    'all_indicators', 'generate_signals',
    
    # 高级因子
    'AdvancedFactors',
    'generate_p2_signals',
    
    # QuantaAlpha 解析器
    'compute_alpha158_20',
    'QAExpressionParser',
    'compute_factor',
    'compute_factors',
]
