# -*- coding: utf-8 -*-
"""
market_regime.py - 市场状态识别模块

基于沪深300指数的ADX和波动率分位数，判断市场状态并返回参数调整系数。

四级状态:
- normal: 正常交易
- warning: 预警，减少仓位
- soft_circuit_break: 软熔断，大幅收缩
- hard_circuit_break: 硬熔断，停止所有买入
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("quant_engine.regime")


class RegimeState(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    SOFT_CIRCUIT_BREAK = "soft_circuit_break"
    HARD_CIRCUIT_BREAK = "hard_circuit_break"


@dataclass
class RegimeParams:
    max_position_per_stock: float
    initial_position: float
    grid_spacing_multiplier: float
    max_grids: int
    stop_loss_multiplier: float  # 止损乘数


DEFAULT_PARAMS = {
    RegimeState.NORMAL: RegimeParams(
        max_position_per_stock=0.30,
        initial_position=0.45,
        grid_spacing_multiplier=1.0,
        max_grids=5,
        stop_loss_multiplier=1.0,
    ),
    RegimeState.WARNING: RegimeParams(
        max_position_per_stock=0.20,
        initial_position=0.35,
        grid_spacing_multiplier=1.3,
        max_grids=4,
        stop_loss_multiplier=0.8,
    ),
    RegimeState.SOFT_CIRCUIT_BREAK: RegimeParams(
        max_position_per_stock=0.10,
        initial_position=0.20,
        grid_spacing_multiplier=1.8,
        max_grids=3,
        stop_loss_multiplier=0.6,
    ),
    RegimeState.HARD_CIRCUIT_BREAK: RegimeParams(
        max_position_per_stock=0.0,
        initial_position=0.0,
        grid_spacing_multiplier=0.0,
        max_grids=0,
        stop_loss_multiplier=0.5,
    ),
}


class RegimeFilter:
    """市场状态过滤器"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        rf = self.config.get("regime_filter", {})

        self.adx_normal_max = rf.get("adx_normal_max", 25)
        self.adx_warning_max = rf.get("adx_warning_max", 35)
        self.vol_normal_low = rf.get("vol_normal_low", 0.30)
        self.vol_normal_high = rf.get("vol_normal_high", 0.70)
        self.vol_extreme_low = rf.get("vol_extreme_low", 0.15)
        self.vol_extreme_high = rf.get("vol_extreme_high", 0.85)
        self.smoothing_days = rf.get("smoothing_days", 3)
        self.confirm_days = rf.get("confirm_days", 2)
        self.hard_stop_index_drop = rf.get("hard_stop_index_drop", 0.05)
        self.hard_stop_limit_down_count = rf.get("hard_stop_limit_down_count", 200)

        self._adx_history: list = []
        self._vol_pct_history: list = []
        self._confirmed_state = RegimeState.NORMAL
        self._consecutive_days = 0

    def _compute_volatility(self, close: pd.Series, period: int = 60) -> Tuple[float, float]:
        """计算60日年化波动率和其在252日历史中的分位数"""
        returns = close.pct_change().dropna()
        vol = returns.rolling(period).std() * np.sqrt(252)
        if vol.empty or pd.isna(vol.iloc[-1]):
            return 0.20, 0.50
        current_vol = vol.iloc[-1]
        vol_hist = vol.dropna().iloc[-252:]
        if len(vol_hist) < 50:
            return current_vol, 0.50
        vol_pct = (vol_hist < current_vol).mean()
        return current_vol, vol_pct

    def _compute_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """近似ADX计算"""
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        if adx.empty or pd.isna(adx.iloc[-1]):
            return 25.0
        return adx.iloc[-1]

    def _apply_smoothing(self, adx: float, vol_pct: float) -> Tuple[float, float]:
        self._adx_history.append(adx)
        self._vol_pct_history.append(vol_pct)
        if len(self._adx_history) > self.smoothing_days:
            self._adx_history = self._adx_history[-self.smoothing_days:]
        if len(self._vol_pct_history) > self.smoothing_days:
            self._vol_pct_history = self._vol_pct_history[-self.smoothing_days:]
        return np.mean(self._adx_history), np.mean(self._vol_pct_history)

    def _check_state_transition(self, new_state: RegimeState) -> RegimeState:
        if new_state == self._confirmed_state:
            self._consecutive_days += 1
        else:
            self._consecutive_days = 1
        if new_state == RegimeState.HARD_CIRCUIT_BREAK:
            self._confirmed_state = new_state
            return new_state
        if self._consecutive_days >= self.confirm_days:
            if self._confirmed_state != new_state:
                logger.warning(f"市场状态切换: {self._confirmed_state.value} -> {new_state.value}")
            self._confirmed_state = new_state
        return self._confirmed_state

    def _classify(self, adx: float, vol_pct: float) -> RegimeState:
        if adx > self.adx_warning_max or vol_pct < self.vol_extreme_low or vol_pct > self.vol_extreme_high:
            return RegimeState.SOFT_CIRCUIT_BREAK
        if adx > self.adx_normal_max or vol_pct < self.vol_normal_low or vol_pct > self.vol_normal_high:
            return RegimeState.WARNING
        return RegimeState.NORMAL

    def check(self, benchmark_data: dict) -> dict:
        """
        检查市场状态

        Parameters:
            benchmark_data: {
                "close": pd.Series (收盘价),
                "high": pd.Series (最高价),
                "low": pd.Series (最低价),
                "volume": pd.Series (成交量, optional),
                "index_daily_return": float (单日收益率, optional),
                "limit_down_count": int (跌停家数, optional),
            }

        Returns:
            {
                "state": str,
                "params": RegimeParams,
                "can_open_new": bool,
                "can_buy": bool,
                "adx": float,
                "vol_current": float,
                "vol_percentile": float,
            }
        """
        close = benchmark_data.get("close")
        if close is None or len(close) < 100:
            params = DEFAULT_PARAMS[RegimeState.NORMAL]
            return {
                "state": RegimeState.NORMAL.value,
                "params": params,
                "can_open_new": True,
                "can_buy": True,
                "adx": 25.0,
                "vol_current": 0.20,
                "vol_percentile": 0.50,
            }

        vol_current, vol_pct = self._compute_volatility(close)
        high = benchmark_data.get("high", close)
        low = benchmark_data.get("low", close)
        adx = self._compute_adx(high, low, close)
        smooth_adx, smooth_vol_pct = self._apply_smoothing(adx, vol_pct)

        # 硬底线检查
        index_return = benchmark_data.get("index_daily_return", 0.0)
        limit_down_count = benchmark_data.get("limit_down_count", 0)
        hard_stop = (
            index_return <= -self.hard_stop_index_drop
            and limit_down_count > self.hard_stop_limit_down_count
        )

        if hard_stop:
            state = RegimeState.HARD_CIRCUIT_BREAK
            self._confirmed_state = state
            self._consecutive_days = 0
        else:
            raw_state = self._classify(smooth_adx, smooth_vol_pct)
            state = self._check_state_transition(raw_state)

        params = DEFAULT_PARAMS.get(state, DEFAULT_PARAMS[RegimeState.NORMAL])
        can_open_new = state == RegimeState.NORMAL
        can_buy = state in (RegimeState.NORMAL, RegimeState.WARNING)

        state_labels = {
            RegimeState.NORMAL: "正常",
            RegimeState.WARNING: "预警",
            RegimeState.SOFT_CIRCUIT_BREAK: "软熔断",
            RegimeState.HARD_CIRCUIT_BREAK: "硬熔断",
        }
        log_msg = (
            f"市场状态: {state_labels[state]} | "
            f"ADX={smooth_adx:.1f}, 波动率={vol_current:.1%}, "
            f"波动率分位={smooth_vol_pct:.0%} | "
            f"max_pos={params.max_position_per_stock:.0%}, "
            f"spacing={params.grid_spacing_multiplier:.1f}x, "
            f"stop_mult={params.stop_loss_multiplier:.1f}x"
        )

        if state == RegimeState.HARD_CIRCUIT_BREAK:
            logger.critical(log_msg)
        elif state == RegimeState.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return {
            "state": state.value,
            "params": params,
            "can_open_new": can_open_new,
            "can_buy": can_buy,
            "adx": smooth_adx,
            "vol_current": vol_current,
            "vol_percentile": smooth_vol_pct,
        }

    def reset(self):
        self._adx_history.clear()
        self._vol_pct_history.clear()
        self._confirmed_state = RegimeState.NORMAL
        self._consecutive_days = 0
