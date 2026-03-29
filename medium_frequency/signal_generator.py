#!/usr/bin/env python3
"""
信号生成器

功能:
- 网格策略信号
- 波段策略信号
- 动量策略信号
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = 'buy'
    SELL = 'sell'
    HOLD = 'hold'


class StrategyType(Enum):
    """策略类型"""
    GRID = 'grid'           # 网格
    SWING = 'swing'         # 波段
    MOMENTUM = 'momentum'   # 动量


class Signal:
    """交易信号"""
    
    def __init__(
        self,
        code: str,
        name: str,
        signal_type: SignalType,
        strategy: StrategyType,
        price: float,
        confidence: float = 0.5,
        reasons: List[str] = None,
        target_position: float = 0.0
    ):
        self.code = code
        self.name = name
        self.signal_type = signal_type
        self.strategy = strategy
        self.price = price
        self.confidence = confidence  # 0-1
        self.reasons = reasons or []
        self.target_position = target_position  # 目标仓位比例
        self.timestamp = pd.Timestamp.now()
    
    def __repr__(self):
        return (
            f"Signal({self.code}, {self.signal_type.value}, "
            f"{self.strategy.value}, ¥{self.price:.2f}, "
            f"confidence={self.confidence:.2f})"
        )


class SignalGenerator:
    """信号生成器"""
    
    def __init__(self, config: dict = None):
        """
        Args:
            config: 策略配置
        """
        self.config = config or {}
        
        # 网格策略配置
        self.grid_size = self.config.get('grid_size', 0.01)  # 1% 网格间距
        self.position_per_grid = self.config.get('position_per_grid', 0.03)  # 3%/格
        self.max_grids = self.config.get('max_grids', 10)
        
        # 波段策略配置
        self.rsi_oversold = self.config.get('rsi_oversold', 30)
        self.rsi_overbought = self.config.get('rsi_overbought', 70)
        self.macd_fast = self.config.get('macd_fast', 12)
        self.macd_slow = self.config.get('macd_slow', 26)
        self.macd_signal = self.config.get('macd_signal', 9)
        
        # 动量策略配置
        self.breakout_period = self.config.get('breakout_period', 20)
        self.volume_confirm = self.config.get('volume_confirm', 1.5)
        
        # 股票基准价缓存 (用于网格计算)
        self._base_prices: Dict[str, float] = {}
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        code: str,
        name: str,
        current_price: float,
        position: float = 0.0,
        strategies: List[StrategyType] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            df: K 线数据 (DataFrame with OHLCV)
            code: 股票代码
            name: 股票名称
            current_price: 当前价格
            position: 当前仓位 (0-1)
            strategies: 启用的策略列表
        
        Returns:
            信号列表
        """
        if strategies is None:
            strategies = [StrategyType.GRID, StrategyType.SWING, StrategyType.MOMENTUM]
        
        signals = []
        
        # 确保有足够的 K 线数据
        if len(df) < 30:
            return signals
        
        # 计算指标
        df = self._calculate_indicators(df)
        
        # 网格策略
        if StrategyType.GRID in strategies:
            signal = self._grid_strategy(
                code, name, current_price, position
            )
            if signal:
                signals.append(signal)
        
        # 波段策略
        if StrategyType.SWING in strategies:
            signal = self._swing_strategy(
                code, name, df, current_price, position
            )
            if signal:
                signals.append(signal)
        
        # 动量策略
        if StrategyType.MOMENTUM in strategies:
            signal = self._momentum_strategy(
                code, name, df, current_price, position
            )
            if signal:
                signals.append(signal)
        
        return signals
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = df.copy()
        
        # MACD
        exp1 = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal_line'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['signal_line']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['std20'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['ma20'] + (df['std20'] * 2)
        df['bb_lower'] = df['ma20'] - (df['std20'] * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-12)
        
        # 成交量均线
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # 高低点 (用于动量突破)
        df['high_20'] = df['high'].rolling(window=self.breakout_period).max()
        df['low_20'] = df['low'].rolling(window=self.breakout_period).min()
        
        return df
    
    def _grid_strategy(
        self,
        code: str,
        name: str,
        current_price: float,
        position: float
    ) -> Optional[Signal]:
        """
        网格策略
        
        逻辑:
        - 价格每下跌 1 格，买入 1 格
        - 价格每上涨 1 格，卖出 1 格
        """
        # 设置基准价 (首次获取)
        if code not in self._base_prices:
            self._base_prices[code] = current_price
            return None
        
        base_price = self._base_prices[code]
        
        # 计算网格位置
        price_change = (current_price - base_price) / base_price
        grid_position = int(price_change / self.grid_size)
        
        reasons = []
        
        # 买入信号 (价格下跌超过网格)
        if grid_position < 0 and abs(grid_position) <= self.max_grids:
            target_position = min(
                position + self.position_per_grid,
                self.max_grids * self.position_per_grid
            )
            
            reasons.append(f"网格买入 (第{abs(grid_position)}格)")
            reasons.append(f"价格变动：{price_change*100:.2f}%")
            
            return Signal(
                code=code,
                name=name,
                signal_type=SignalType.BUY,
                strategy=StrategyType.GRID,
                price=current_price,
                confidence=0.7,
                reasons=reasons,
                target_position=target_position
            )
        
        # 卖出信号 (价格上涨超过网格)
        elif grid_position > 0 and position > 0:
            target_position = max(
                position - self.position_per_grid,
                0
            )
            
            reasons.append(f"网格卖出 (第{grid_position}格)")
            reasons.append(f"价格变动：{price_change*100:.2f}%")
            
            return Signal(
                code=code,
                name=name,
                signal_type=SignalType.SELL,
                strategy=StrategyType.GRID,
                price=current_price,
                confidence=0.7,
                reasons=reasons,
                target_position=target_position
            )
        
        return None
    
    def _swing_strategy(
        self,
        code: str,
        name: str,
        df: pd.DataFrame,
        current_price: float,
        position: float
    ) -> Optional[Signal]:
        """
        波段策略
        
        逻辑:
        - RSI<30 + MACD 金叉 → 买入
        - RSI>70 + MACD 死叉 → 卖出
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        reasons = []
        
        # 买入条件
        buy_signal = (
            latest['rsi'] < self.rsi_oversold and
            latest['macd_hist'] > 0 and
            prev['macd_hist'] <= 0  # MACD 金叉
        )
        
        if buy_signal and position < 0.10:  # 仓位低时才买入
            reasons.append(f"RSI 超卖 ({latest['rsi']:.1f})")
            reasons.append(f"MACD 金叉")
            reasons.append(f"布林带位置：{latest['bb_position']:.2f}")
            
            return Signal(
                code=code,
                name=name,
                signal_type=SignalType.BUY,
                strategy=StrategyType.SWING,
                price=current_price,
                confidence=0.75,
                reasons=reasons,
                target_position=0.08
            )
        
        # 卖出条件
        sell_signal = (
            latest['rsi'] > self.rsi_overbought and
            latest['macd_hist'] < 0 and
            prev['macd_hist'] >= 0  # MACD 死叉
        )
        
        if sell_signal and position > 0:
            reasons.append(f"RSI 超买 ({latest['rsi']:.1f})")
            reasons.append(f"MACD 死叉")
            reasons.append(f"布林带位置：{latest['bb_position']:.2f}")
            
            return Signal(
                code=code,
                name=name,
                signal_type=SignalType.SELL,
                strategy=StrategyType.SWING,
                price=current_price,
                confidence=0.75,
                reasons=reasons,
                target_position=0.0
            )
        
        return None
    
    def _momentum_strategy(
        self,
        code: str,
        name: str,
        df: pd.DataFrame,
        current_price: float,
        position: float
    ) -> Optional[Signal]:
        """
        动量突破策略
        
        逻辑:
        - 突破 20 周期高点 + 成交量放大 → 买入
        - 跌破 20 周期低点 → 卖出
        """
        latest = df.iloc[-1]
        
        reasons = []
        
        # 向上突破
        if current_price > latest['high_20']:
            volume_confirm = latest['volume_ratio'] > self.volume_confirm
            
            if volume_confirm and position < 0.10:
                reasons.append(f"突破 20 周期高点 ({latest['high_20']:.2f})")
                reasons.append(f"成交量放大 ({latest['volume_ratio']:.1f}x)")
                
                return Signal(
                    code=code,
                    name=name,
                    signal_type=SignalType.BUY,
                    strategy=StrategyType.MOMENTUM,
                    price=current_price,
                    confidence=0.70 if volume_confirm else 0.50,
                    reasons=reasons,
                    target_position=0.06
                )
        
        # 向下跌破
        elif current_price < latest['low_20'] and position > 0:
            reasons.append(f"跌破 20 周期低点 ({latest['low_20']:.2f})")
            
            return Signal(
                code=code,
                name=name,
                signal_type=SignalType.SELL,
                strategy=StrategyType.MOMENTUM,
                price=current_price,
                confidence=0.65,
                reasons=reasons,
                target_position=0.0
            )
        
        return None
    
    def update_base_price(self, code: str, price: float):
        """更新基准价 (用于网格策略)"""
        self._base_prices[code] = price
    
    def clear_base_prices(self):
        """清空基准价缓存"""
        self._base_prices.clear()


# ========== 测试 ==========
if __name__ == '__main__':
    print("="*60)
    print("测试信号生成器")
    print("="*60)
    
    import sys
    sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')
    from medium_frequency.data_fetcher import MinuteDataFetcher
    
    # 配置
    config = {
        'grid_size': 0.01,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
    }
    
    generator = SignalGenerator(config)
    fetcher = MinuteDataFetcher()
    
    # 测试股票
    code = 'sh.600519'
    name = '贵州茅台'
    
    print(f"\n【1】获取 {code} 数据")
    df = fetcher.get_minute_kline(code, period=5, limit=50)
    
    if df is not None:
        print(f"  ✅ 数据量：{len(df)}条")
        print(f"  最新价：¥{df['close'].iloc[-1]:.2f}")
        
        print(f"\n【2】生成信号")
        signals = generator.generate_signals(
            df=df,
            code=code,
            name=name,
            current_price=df['close'].iloc[-1],
            position=0.05,
            strategies=[StrategyType.SWING, StrategyType.MOMENTUM]
        )
        
        if signals:
            for signal in signals:
                print(f"  {signal}")
                for reason in signal.reasons:
                    print(f"    - {reason}")
        else:
            print(f"  暂无信号")
    else:
        print(f"  ❌ 数据获取失败")
    
    print("\n✅ 测试完成")
