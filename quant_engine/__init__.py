# -*- coding: utf-8 -*-
"""
BobQuant 量化交易引擎 v2.1 - 自学习版

核心模块:
- market_regime: 市场状态识别 (RegimeFilter)
- risk_control: 双级熔断风控
- grid_engine: 动态网格交易引擎
- atr_stop: ATR 动态止损
- signal_generator: 统一信号生成器
- position_manager: 持仓管理 (T+1 合规)
- trading_engine: 主引擎

自学习模块 (v2.1 新增):
- experience_lib: 经验库（决策快照 + 经验条目）
- review_agent: 自动复盘 Agent
- experience_injector: 经验注入器（信号生成时召回历史经验）
- feedback_loop: 规则自适应反馈闭环
"""
__version__ = "2.1.0"

from .trading_engine import TradingEngine
from .market_regime import RegimeFilter, RegimeState
from .risk_control import RiskControlManager
from .signal_generator import SignalGenerator
from .position_manager import PositionManager

__all__ = [
    "TradingEngine",
    "RegimeFilter",
    "RegimeState",
    "RiskControlManager",
    "SignalGenerator",
    "PositionManager",
]
