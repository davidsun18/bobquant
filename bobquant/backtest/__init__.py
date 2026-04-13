# BobQuant 回测模块 v2.0

from .engine import BacktestEngine, run_backtest
from .backtrader_engine import BacktraderEngine, run_backtrader_backtest, compare_engines
from .vectorbt_backtest import VectorBTBacktest, run_vectorbt_backtest

__all__ = [
    'BacktestEngine',
    'run_backtest',
    'BacktraderEngine',
    'run_backtrader_backtest',
    'VectorBTBacktest',
    'run_vectorbt_backtest',
    'compare_engines'
]
