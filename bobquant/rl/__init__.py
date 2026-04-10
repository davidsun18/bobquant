"""
强化学习模块 - 基于 FinRL 和 Stable Baselines3

使用方式:
    from bobquant.rl import FinRLAgent, StockTradingEnv, RLAlgorithm
    env = StockTradingEnv(stock_data, initial_capital=1000000)
    agent = FinRLAgent(env, algorithm=RLAlgorithm.PPO)
    agent.train(total_timesteps=10000)
"""

from .finrl_agent import (
    FinRLAgent,
    StockTradingEnv,
    RLAlgorithm
)

__all__ = ['FinRLAgent', 'StockTradingEnv', 'RLAlgorithm']
