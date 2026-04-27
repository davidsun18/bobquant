# -*- coding: utf-8 -*-
"""
atr_stop.py - ATR 动态止损模块

替代固定 8% 止损，使用 ATR 倍数计算动态止损价。

止损价 = 成本价 - ATR倍数 × ATR(20)
默认 ATR倍数 = 2.0

特性:
- 止损价只升不降 (trailing stop)
- 市场波动大时自动放宽，波动小时自动收紧
- 与市场状态联动 (RegimeParams.stop_loss_multiplier)
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("quant_engine.atr_stop")


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """计算 ATR (Average True Range)"""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr


class ATRStopLoss:
    """ATR 动态止损管理器"""

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("atr_stop", {})
        self.atr_period = cfg.get("atr_period", 20)
        self.atr_multiplier = cfg.get("atr_multiplier", 2.0)
        self.trailing = cfg.get("trailing", True)  # 止损价只升不降
        self.min_stop_pct = cfg.get("min_stop_pct", 0.03)  # 最小止损 3%

    def calculate_stop_price(
        self,
        cost_price: float,
        current_price: float,
        atr_value: float,
        stop_loss_multiplier: float = 1.0,
        current_stop: Optional[float] = None,
    ) -> Tuple[float, bool]:
        """
        计算当前止损价

        Parameters:
            cost_price: 持仓成本价
            current_price: 当前价格
            atr_value: 当前 ATR(20)
            stop_loss_multiplier: 市场状态调节系数
            current_stop: 当前已记录的止损价 (用于 trailing)

        Returns:
            (stop_price, triggered): 止损价, 是否已触发
        """
        if atr_value <= 0 or cost_price <= 0:
            # 回退: 使用固定比例
            fallback = cost_price * (1 - self.min_stop_pct)
            return fallback, current_price <= fallback

        effective_mult = self.atr_multiplier * stop_loss_multiplier
        stop_price = cost_price - effective_mult * atr_value

        # 最低止损限制
        min_stop = cost_price * (1 - self.min_stop_pct)
        stop_price = max(stop_price, min_stop)

        # Trailing: 止损价只升不降
        if self.trailing and current_stop is not None:
            # 如果成本价已经更新 (加仓)，重新计算但不得低于旧止损
            if current_price > cost_price:
                trailing_stop = current_price - effective_mult * atr_value
                trailing_stop = max(trailing_stop, min_stop)
                stop_price = max(stop_price, trailing_stop, current_stop)
            else:
                stop_price = max(stop_price, current_stop)

        triggered = current_price <= stop_price
        return stop_price, triggered

    def calculate_position_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> float:
        """便捷方法: 从价格序列计算当前 ATR"""
        atr = compute_atr(high, low, close, self.atr_period)
        if atr.empty or pd.isna(atr.iloc[-1]):
            return 0.0
        return atr.iloc[-1]
