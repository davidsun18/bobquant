# -*- coding: utf-8 -*-
"""
FinRL 强化学习代理
基于 FinRL 和 Stable Baselines3 实现 DRL 交易策略

功能：
- 状态空间：持仓、资金、技术指标
- 动作空间：买入/卖出/持有
- 奖励函数：Sharpe 比率
- 训练接口：支持 PPO/A2C/DQN
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum
import gymnasium as gym
from gymnasium import spaces
import warnings

# Stable Baselines3
try:
    from stable_baselines3 import PPO, A2C, DQN
    from stable_baselines3.common.env_checker import check_env
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
    from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
    from stable_baselines3.common.monitor import Monitor
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    warnings.warn("Stable Baselines3 未安装，部分功能不可用")

# FinRL
try:
    import finrl
    FINRL_AVAILABLE = True
except ImportError:
    FINRL_AVAILABLE = False
    warnings.warn("FinRL 未安装")


class RLAlgorithm(Enum):
    """强化学习算法枚举"""
    PPO = "ppo"
    A2C = "a2c"
    DQN = "dqn"


class StockTradingEnv(gym.Env):
    """
    股票交易环境
    
    状态空间：
    - 账户状态：现金、持仓价值、总资产
    - 持仓信息：每只股票的持仓数量
    - 技术指标：MACD、RSI、布林带等
    - 市场价格：当前价格、收益率
    
    动作空间：
    - 离散动作：0=持有，1=买入，2=卖出
    - 或连续动作：[-1, 1] 表示卖出到买入的强度
    
    奖励函数：
    - 基于 Sharpe 比率
    - 考虑交易成本
    """
    
    metadata = {'render_modes': ['human', 'rgb_array']}
    
    def __init__(
        self,
        df: pd.DataFrame,
        stock_codes: List[str],
        initial_capital: float = 1_000_000,
        max_stocks: int = 10,
        max_position_pct: float = 0.10,
        commission_rate: float = 0.0005,
        stamp_duty_rate: float = 0.001,
        window_size: int = 60,
        reward_type: str = 'sharpe',
        discrete_actions: bool = True,
    ):
        super().__init__()
        
        self.df = df.reset_index(drop=True)
        self.stock_codes = stock_codes
        self.n_stocks = len(stock_codes)
        self.initial_capital = initial_capital
        self.max_stocks = max_stocks
        self.max_position_pct = max_position_pct
        self.commission_rate = commission_rate
        self.stamp_duty_rate = stamp_duty_rate
        self.window_size = window_size
        self.reward_type = reward_type
        self.discrete_actions = discrete_actions
        
        # 技术指标列
        self.indicator_cols = [
            'macd', 'macd_signal', 'macd_hist',
            'rsi', 'bollinger_upper', 'bollinger_lower', 'bollinger_mid',
            'sma_20', 'sma_60', 'ema_12', 'ema_26'
        ]
        
        # 价格列
        self.price_cols = ['close', 'open', 'high', 'low', 'volume']
        
        # 状态空间维度
        # 账户状态 (3) + 持仓信息 (n_stocks) + 技术指标 (n_indicators * n_stocks) + 价格特征 (5 * n_stocks)
        n_indicators = len(self.indicator_cols)
        n_price_features = len(self.price_cols)
        self.state_dim = 3 + self.n_stocks + (n_indicators + n_price_features) * self.n_stocks
        
        # 动作空间
        if discrete_actions:
            # 每只股票 3 个动作：持有、买入、卖出
            self.action_space = spaces.Discrete(3 ** self.n_stocks)
        else:
            # 连续动作：[-1, 1] 表示卖出强度到买入强度
            self.action_space = spaces.Box(
                low=-1.0, high=1.0, shape=(self.n_stocks,), dtype=np.float32
            )
        
        # 观测空间
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.state_dim,), dtype=np.float32
        )
        
        # 状态变量
        self.current_step = 0
        self.cash = initial_capital
        self.shares_held = np.zeros(self.n_stocks)
        self.portfolio_value = initial_capital
        self.portfolio_values = [initial_capital]
        self.trades = []
        
        # 归一化参数
        self.price_mean = None
        self.price_std = None
        
    def _get_state(self) -> np.ndarray:
        """获取当前状态"""
        # 确保 current_step 不越界
        if self.current_step >= len(self.df):
            self.current_step = len(self.df) - 1
        
        start_idx = max(0, self.current_step - self.window_size)
        
        if start_idx < self.window_size:
            # 初始窗口，用前 window_size 条数据
            data = self.df.iloc[:min(self.window_size, len(self.df))]
        else:
            data = self.df.iloc[start_idx:self.current_step]
        
        current_data = self.df.iloc[self.current_step]
        
        # 1. 账户状态 (3 维)
        account_state = np.array([
            self.cash / self.initial_capital,  # 现金比例
            self.portfolio_value / self.initial_capital,  # 总资产比例
            np.sum(self.shares_held) / self.max_stocks  # 持仓比例
        ])
        
        # 2. 持仓信息 (n_stocks 维)
        position_info = self.shares_held / (self.initial_capital / current_data['close'])
        
        # 3. 技术指标 (n_indicators * n_stocks 维)
        indicators = []
        for i in range(self.n_stocks):
            stock_data = current_data
            for col in self.indicator_cols:
                val = stock_data.get(col, 0)
                if pd.isna(val):
                    val = 0
                indicators.append(val)
        
        # 4. 价格特征 (5 * n_stocks 维)
        price_features = []
        for i in range(self.n_stocks):
            stock_data = current_data
            for col in self.price_cols:
                val = stock_data.get(col, 0)
                if pd.isna(val):
                    val = 0
                price_features.append(val)
        
        # 合并状态
        state = np.concatenate([
            account_state,
            position_info,
            np.array(indicators),
            np.array(price_features)
        ])
        
        return state.astype(np.float32)
    
    def _calculate_reward(self, action: int, prev_value: float) -> float:
        """
        计算奖励
        
        基于 Sharpe 比率：
        reward = (current_return - risk_free_rate) / std(returns)
        
        考虑交易成本惩罚
        """
        current_value = self._calculate_portfolio_value()
        
        # 简单收益率
        simple_return = (current_value - prev_value) / prev_value if prev_value > 0 else 0
        
        # Sharpe 比率奖励（使用滚动窗口）
        if len(self.portfolio_values) > 2:
            returns = np.diff(self.portfolio_values) / np.array(self.portfolio_values[:-1])
            if np.std(returns) > 0:
                sharpe = (np.mean(returns) - 0.02/252) / np.std(returns)  # 假设年化无风险利率 2%
                reward = sharpe
            else:
                reward = simple_return
        else:
            reward = simple_return
        
        # 交易成本惩罚
        if action != 0:  # 有交易
            reward -= 0.001  # 小额惩罚鼓励减少频繁交易
        
        return reward
    
    def _calculate_portfolio_value(self) -> float:
        """计算当前投资组合价值"""
        if self.current_step >= len(self.df):
            return self.cash
        
        current_data = self.df.iloc[self.current_step]
        stock_value = 0
        
        for i in range(self.n_stocks):
            price = current_data['close']
            stock_value += self.shares_held[i] * price
        
        self.portfolio_value = self.cash + stock_value
        return self.portfolio_value
    
    def _execute_action(self, action: Union[int, np.ndarray]) -> float:
        """
        执行动作
        
        离散动作：0=持有，1=买入，2=卖出
        连续动作：[-1, 1] 表示卖出到买入的强度
        """
        cost = 0
        
        if self.discrete_actions:
            # 解码离散动作
            actions = []
            temp = action
            for _ in range(self.n_stocks):
                actions.append(temp % 3)
                temp //= 3
            
            for i in range(self.n_stocks):
                action_code = actions[i]
                if action_code == 1:  # 买入
                    self._buy_stock(i)
                elif action_code == 2:  # 卖出
                    self._sell_stock(i)
        else:
            # 连续动作
            for i in range(self.n_stocks):
                action_strength = action[i]
                if action_strength > 0.1:  # 买入
                    self._buy_stock(i, strength=action_strength)
                elif action_strength < -0.1:  # 卖出
                    self._sell_stock(i, strength=abs(action_strength))
        
        return cost
    
    def _buy_stock(self, idx: int, strength: float = 1.0):
        """买入股票"""
        if self.current_step >= len(self.df):
            return
        
        current_data = self.df.iloc[self.current_step]
        price = current_data['close']
        
        # 计算可买入的最大数量
        max_buy_value = self.cash * self.max_position_pct
        max_shares = int(max_buy_value / price / 100) * 100  # A 股最小交易单位 100 股
        
        if max_shares <= 0:
            return
        
        # 根据动作强度调整买入量
        shares_to_buy = int(max_shares * strength)
        shares_to_buy = max(100, shares_to_buy)  # 至少买入 100 股
        
        cost = shares_to_buy * price * (1 + self.commission_rate)
        
        if cost <= self.cash:
            self.cash -= cost
            self.shares_held[idx] += shares_to_buy
            self.trades.append({
                'step': self.current_step,
                'action': 'buy',
                'stock_idx': idx,
                'shares': shares_to_buy,
                'price': price,
                'cost': cost
            })
    
    def _sell_stock(self, idx: int, strength: float = 1.0):
        """卖出股票"""
        if self.current_step >= len(self.df) or self.shares_held[idx] <= 0:
            return
        
        current_data = self.df.iloc[self.current_step]
        price = current_data['close']
        
        # 根据动作强度调整卖出量
        shares_to_sell = int(self.shares_held[idx] * strength)
        shares_to_sell = max(100, shares_to_sell)  # 至少卖出 100 股
        shares_to_sell = min(shares_to_sell, self.shares_held[idx])  # 不能超过持仓
        
        if shares_to_sell <= 0:
            return
        
        revenue = shares_to_sell * price * (1 - self.commission_rate - self.stamp_duty_rate)
        self.cash += revenue
        self.shares_held[idx] -= shares_to_sell
        
        self.trades.append({
            'step': self.current_step,
            'action': 'sell',
            'stock_idx': idx,
            'shares': shares_to_sell,
            'price': price,
            'revenue': revenue
        })
    
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        """重置环境"""
        super().reset(seed=seed)
        
        # 确保有足够的数据
        min_start = self.window_size
        max_start = max(min_start, len(self.df) - 10)  # 至少留 10 步用于交易
        
        if max_start <= min_start:
            # 数据太少，调整 window_size
            self.current_step = max(1, len(self.df) // 2)
        else:
            self.current_step = min_start
        
        self.cash = self.initial_capital
        self.shares_held = np.zeros(self.n_stocks)
        self.portfolio_value = self.initial_capital
        self.portfolio_values = [self.initial_capital] * min(self.window_size, self.current_step)
        self.trades = []
        
        state = self._get_state()
        info = {'portfolio_value': self.portfolio_value}
        
        return state, info
    
    def step(self, action: Union[int, np.ndarray]) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """执行一步"""
        prev_value = self._calculate_portfolio_value()
        
        # 执行动作
        self._execute_action(action)
        
        # 前进一步
        self.current_step += 1
        
        # 计算新价值
        current_value = self._calculate_portfolio_value()
        self.portfolio_values.append(current_value)
        
        # 计算奖励
        reward = self._calculate_reward(action, prev_value)
        
        # 检查是否结束
        terminated = self.current_step >= len(self.df) - 1
        truncated = False
        
        # 破产检查
        if self.portfolio_value < self.initial_capital * 0.5:  # 亏损超过 50%
            terminated = True
        
        state = self._get_state()
        info = {
            'portfolio_value': self.portfolio_value,
            'cash': self.cash,
            'shares_held': self.shares_held.copy(),
            'trades': len(self.trades),
            'step': self.current_step
        }
        
        return state, reward, terminated, truncated, info
    
    def render(self, mode='human'):
        """渲染环境"""
        if mode == 'human':
            print(f"Step: {self.current_step}")
            print(f"Portfolio Value: {self.portfolio_value:.2f}")
            print(f"Cash: {self.cash:.2f}")
            print(f"Shares Held: {self.shares_held}")
            print("-" * 50)


class FinRLAgent:
    """
    FinRL 强化学习代理
    
    功能：
    - 数据预处理
    - 环境创建
    - 模型训练
    - 模型预测
    - 性能评估
    """
    
    def __init__(
        self,
        algorithm: RLAlgorithm = RLAlgorithm.PPO,
        initial_capital: float = 1_000_000,
        max_stocks: int = 10,
        max_position_pct: float = 0.10,
        commission_rate: float = 0.0005,
        stamp_duty_rate: float = 0.001,
        window_size: int = 60,
        verbose: int = 1,
    ):
        self.algorithm = algorithm
        self.initial_capital = initial_capital
        self.max_stocks = max_stocks
        self.max_position_pct = max_position_pct
        self.commission_rate = commission_rate
        self.stamp_duty_rate = stamp_duty_rate
        self.window_size = window_size
        self.verbose = verbose
        
        self.model = None
        self.env = None
        self.eval_env = None
        self.training_history = []
        
        if not SB3_AVAILABLE:
            raise ImportError("Stable Baselines3 未安装，请运行：pip install stable-baselines3[extra]")
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        stock_codes: List[str],
        add_indicators: bool = True
    ) -> pd.DataFrame:
        """
        准备训练数据
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
            stock_codes: 股票代码列表
            add_indicators: 是否添加技术指标
        
        Returns:
            处理后的 DataFrame
        """
        data = df.copy()
        
        if add_indicators:
            # 添加技术指标
            data = self._add_technical_indicators(data)
        
        return data
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加技术指标"""
        data = df.copy()
        
        # MACD
        exp1 = data['close'].ewm(span=12, adjust=False)
        exp2 = data['close'].ewm(span=26, adjust=False)
        data['macd'] = exp1.mean() - exp2.mean()
        data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
        data['macd_hist'] = data['macd'] - data['macd_signal']
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        data['bollinger_mid'] = data['close'].rolling(window=20).mean()
        data['bollinger_std'] = data['close'].rolling(window=20).std()
        data['bollinger_upper'] = data['bollinger_mid'] + 2 * data['bollinger_std']
        data['bollinger_lower'] = data['bollinger_mid'] - 2 * data['bollinger_std']
        
        # 移动平均线
        data['sma_20'] = data['close'].rolling(window=20).mean()
        data['sma_60'] = data['close'].rolling(window=60).mean()
        data['ema_12'] = data['close'].ewm(span=12, adjust=False).mean()
        data['ema_26'] = data['close'].ewm(span=26, adjust=False).mean()
        
        # 填充 NaN 值
        data = data.fillna(method='bfill').fillna(method='ffill').fillna(0)
        
        return data
    
    def create_environment(
        self,
        df: pd.DataFrame,
        stock_codes: List[str],
        is_eval: bool = False
    ) -> StockTradingEnv:
        """创建交易环境"""
        env = StockTradingEnv(
            df=df,
            stock_codes=stock_codes,
            initial_capital=self.initial_capital,
            max_stocks=self.max_stocks,
            max_position_pct=self.max_position_pct,
            commission_rate=self.commission_rate,
            stamp_duty_rate=self.stamp_duty_rate,
            window_size=self.window_size,
            discrete_actions=True,
        )
        
        return env
    
    def train(
        self,
        df: pd.DataFrame,
        stock_codes: List[str],
        total_timesteps: int = 10000,
        eval_freq: int = 1000,
        n_eval_episodes: int = 5,
        save_path: Optional[str] = None,
        **model_kwargs
    ) -> Dict:
        """
        训练模型
        
        Args:
            df: 训练数据
            stock_codes: 股票代码列表
            total_timesteps: 总训练步数
            eval_freq: 评估频率
            n_eval_episodes: 评估回合数
            save_path: 模型保存路径
            **model_kwargs: 模型参数
        
        Returns:
            训练历史
        """
        # 准备数据
        train_data = self.prepare_data(df, stock_codes)
        
        # 创建环境
        self.env = self.create_environment(train_data, stock_codes)
        self.env = Monitor(self.env)
        vec_env = DummyVecEnv([lambda: self.env])
        
        # 创建评估环境（确保有足够数据）
        eval_size = max(int(len(train_data)*0.2), self.window_size + 20)
        eval_data = train_data.iloc[-eval_size:]  # 后 20% 作为评估集
        self.eval_env = self.create_environment(eval_data, stock_codes)
        self.eval_env = Monitor(self.eval_env)
        
        # 创建模型
        self.model = self._create_model(vec_env, **model_kwargs)
        
        # 创建评估回调
        eval_callback = EvalCallback(
            self.eval_env,
            best_model_save_path=save_path,
            log_path=save_path,
            eval_freq=eval_freq,
            n_eval_episodes=n_eval_episodes,
            deterministic=True,
            render=False,
        )
        
        # 训练
        if self.verbose >= 1:
            print(f"开始训练 {self.algorithm.value} 模型...")
            print(f"总步数：{total_timesteps}")
            print(f"状态空间维度：{self.env.observation_space.shape[0]}")
            print(f"动作空间：{self.env.action_space}")
        
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=eval_callback,
            progress_bar=self.verbose >= 1,
        )
        
        # 保存模型
        if save_path:
            self.model.save(f"{save_path}/{self.algorithm.value}_model")
            if self.verbose >= 1:
                print(f"模型已保存到：{save_path}")
        
        # 获取真实环境（Monitor 包装后需要 unwrap）
        real_env = self.env.env if hasattr(self.env, 'env') else self.env
        
        # 训练结果
        results = {
            'algorithm': self.algorithm.value,
            'total_timesteps': total_timesteps,
            'final_portfolio_value': real_env.portfolio_value,
            'total_trades': len(real_env.trades),
            'sharpe_ratio': self._calculate_sharpe(real_env.portfolio_values),
        }
        
        self.training_history.append(results)
        
        if self.verbose >= 1:
            print(f"\n训练完成!")
            print(f"最终资产：{results['final_portfolio_value']:.2f}")
            print(f"总交易次数：{results['total_trades']}")
            print(f"Sharpe 比率：{results['sharpe_ratio']:.4f}")
        
        return results
    
    def _create_model(self, env, **kwargs):
        """创建模型"""
        # 默认参数
        default_kwargs = {
            'learning_rate': 3e-4,
            'n_steps': 2048,
            'batch_size': 64,
            'n_epochs': 10,
            'gamma': 0.99,
            'gae_lambda': 0.95,
            'clip_range': 0.2,
            'verbose': 0,
        }
        
        # 合并参数
        for key, value in kwargs.items():
            default_kwargs[key] = value
        
        if self.algorithm == RLAlgorithm.PPO:
            return PPO("MlpPolicy", env, **default_kwargs)
        elif self.algorithm == RLAlgorithm.A2C:
            return A2C("MlpPolicy", env, **default_kwargs)
        elif self.algorithm == RLAlgorithm.DQN:
            # DQN 参数
            dqn_kwargs = {
                'learning_rate': 1e-4,
                'buffer_size': 100000,
                'learning_starts': 1000,
                'batch_size': 64,
                'gamma': 0.99,
                'target_update_interval': 1000,
                'exploration_fraction': 0.1,
                'exploration_final_eps': 0.05,
                'verbose': 0,
            }
            for key, value in kwargs.items():
                dqn_kwargs[key] = value
            return DQN("MlpPolicy", env, **dqn_kwargs)
        else:
            raise ValueError(f"不支持的算法：{self.algorithm}")
    
    def predict(
        self,
        df: pd.DataFrame,
        stock_codes: List[str],
        n_steps: Optional[int] = None
    ) -> Tuple[List[int], Dict]:
        """
        使用训练好的模型进行预测
        
        Args:
            df: 数据
            stock_codes: 股票代码列表
            n_steps: 预测步数（None 表示全部）
        
        Returns:
            动作列表和详细信息
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用 train() 方法")
        
        # 准备数据
        data = self.prepare_data(df, stock_codes)
        
        # 创建环境
        env = self.create_environment(data, stock_codes)
        obs, _ = env.reset()
        
        actions = []
        details = {
            'portfolio_values': [],
            'cash': [],
            'trades': []
        }
        
        max_steps = n_steps if n_steps else len(data) - env.window_size
        
        for i in range(max_steps):
            action, _ = self.model.predict(obs, deterministic=True)
            actions.append(int(action))
            
            obs, reward, terminated, truncated, info = env.step(action)
            
            details['portfolio_values'].append(env.portfolio_value)
            details['cash'].append(env.cash)
            
            if terminated or truncated:
                break
        
        details['final_value'] = env.portfolio_value
        details['total_trades'] = len(env.trades)
        details['sharpe_ratio'] = self._calculate_sharpe(details['portfolio_values'])
        
        return actions, details
    
    def _calculate_sharpe(self, portfolio_values: List[float], risk_free_rate: float = 0.02) -> float:
        """计算 Sharpe 比率"""
        if len(portfolio_values) < 2:
            return 0.0
        
        returns = np.diff(portfolio_values) / np.array(portfolio_values[:-1])
        
        if np.std(returns) == 0:
            return 0.0
        
        # 年化 Sharpe 比率（假设 252 个交易日）
        sharpe = (np.mean(returns) - risk_free_rate/252) / np.std(returns) * np.sqrt(252)
        
        return sharpe
    
    def evaluate_strategy(
        self,
        df: pd.DataFrame,
        stock_codes: List[str],
        benchmark: Optional[pd.Series] = None
    ) -> Dict:
        """
        评估策略性能
        
        Args:
            df: 测试数据
            stock_codes: 股票代码列表
            benchmark: 基准收益率（如大盘指数）
        
        Returns:
            评估指标
        """
        _, details = self.predict(df, stock_codes)
        
        portfolio_values = np.array(details['portfolio_values'])
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        
        metrics = {
            'total_return': (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0],
            'sharpe_ratio': self._calculate_sharpe(portfolio_values.tolist()),
            'max_drawdown': self._calculate_max_drawdown(portfolio_values),
            'volatility': np.std(returns) * np.sqrt(252),
            'total_trades': details['total_trades'],
            'final_value': details['final_value'],
        }
        
        # 如果提供了基准，计算 Alpha 和 Beta
        if benchmark is not None and len(benchmark) == len(returns):
            benchmark_returns = benchmark.pct_change().dropna().values
            if len(benchmark_returns) == len(returns):
                metrics['alpha'], metrics['beta'] = self._calculate_alpha_beta(
                    returns, benchmark_returns
                )
        
        return metrics
    
    def _calculate_max_drawdown(self, portfolio_values: np.ndarray) -> float:
        """计算最大回撤"""
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (peak - portfolio_values) / peak
        return np.max(drawdown)
    
    def _calculate_alpha_beta(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> Tuple[float, float]:
        """计算 Alpha 和 Beta"""
        if len(returns) != len(benchmark_returns):
            return 0.0, 1.0
        
        # 简单线性回归
        covariance = np.cov(returns, benchmark_returns)[0, 1]
        variance = np.var(benchmark_returns)
        
        beta = covariance / variance if variance > 0 else 1.0
        alpha = np.mean(returns) - beta * np.mean(benchmark_returns)
        
        # 年化
        alpha = alpha * 252
        
        return alpha, beta


# 便捷函数
def create_rl_agent(
    algorithm: str = 'ppo',
    **kwargs
) -> FinRLAgent:
    """创建 RL 代理的便捷函数"""
    algo_map = {
        'ppo': RLAlgorithm.PPO,
        'a2c': RLAlgorithm.A2C,
        'dqn': RLAlgorithm.DQN,
    }
    
    algo = algo_map.get(algorithm.lower(), RLAlgorithm.PPO)
    
    return FinRLAgent(algorithm=algo, **kwargs)


if __name__ == '__main__':
    # 简单测试
    print("FinRL Agent 模块加载成功!")
    print(f"Stable Baselines3 可用：{SB3_AVAILABLE}")
    print(f"FinRL 可用：{FINRL_AVAILABLE}")
