"""
策略模块 - 多因子策略引擎
"""

from .factor_strategy import (
    SignalType,
    Signal,
    FactorStrategy,
    STRATEGY_CONFIGS,
    create_strategy
)

from .p2_strategy import (
    P2SignalType,
    P2Signal,
    P2Strategy,
    create_p2_strategy
)

__all__ = [
    # 基础策略
    'SignalType',
    'Signal',
    'FactorStrategy',
    'STRATEGY_CONFIGS',
    'create_strategy',
    
    # P2 高级策略
    'P2SignalType',
    'P2Signal',
    'P2Strategy',
    'create_p2_strategy',
]
