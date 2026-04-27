# -*- coding: utf-8 -*-
"""
grid_engine.py - 动态网格交易引擎

ATR 自适应网格间距，结合市场状态调节。
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("quant_engine.grid")


@dataclass
class GridSignal:
    code: str
    direction: str  # "buy" | "sell"
    price: float
    quantity: int
    grid_level: int
    reason: str


@dataclass
class GridParams:
    spacing_pct: float
    n_grids: int
    upper_rail: float
    lower_rail: float


class GridEngine:
    """动态网格交易引擎"""

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("grid", {})
        self.base_spacing = cfg.get("base_spacing", 0.02)  # 2%
        self.min_spacing = cfg.get("min_spacing", 0.015)   # 1.5%
        self.max_spacing = cfg.get("max_spacing", 0.035)   # 3.5%
        self.max_grids = cfg.get("max_grids", 5)
        self.grid_amount = cfg.get("grid_amount", 10000)
        self.atr_period = cfg.get("atr_period", 20)
        self.rail_z = cfg.get("rail_z", 2.0)
        self.t1_min_spacing_coef = cfg.get("t1_min_spacing_coef", 1.5)

    def calc_spacing(self, volatility_60d: float, daily_vol: Optional[float] = None,
                     spacing_mult: float = 1.0) -> float:
        """波动率自适应间距"""
        # 波动率比率调整
        vol_ratio = volatility_60d / 0.25  # target vol = 25%
        spacing = self.base_spacing * np.clip(vol_ratio, 0.8, 1.2)

        # T+1 最小间距约束
        if daily_vol is not None and daily_vol > 0:
            t1_min = self.t1_min_spacing_coef * daily_vol
            spacing = max(spacing, t1_min)

        spacing = np.clip(spacing, self.min_spacing, self.max_spacing)
        return spacing * spacing_mult

    def calc_grid_params(self, ref_price: float, atr_20: float,
                         volatility_60d: float, spacing_mult: float = 1.0,
                         max_grids_override: Optional[int] = None) -> GridParams:
        """计算网格参数"""
        daily_vol = volatility_60d / np.sqrt(252) if volatility_60d > 0 else 0.02
        spacing = self.calc_spacing(volatility_60d, daily_vol, spacing_mult)

        upper_rail = ref_price + self.rail_z * atr_20
        lower_rail = ref_price - self.rail_z * atr_20
        rail_pct = self.rail_z * atr_20 / ref_price if ref_price > 0 else 0.0

        n_grids = max(3, int(2 * rail_pct / spacing))
        n_grids = min(n_grids, max_grids_override or self.max_grids)

        return GridParams(
            spacing_pct=spacing,
            n_grids=n_grids,
            upper_rail=upper_rail,
            lower_rail=lower_rail,
        )

    def generate_signals(self, code: str, ref_price: float, atr_20: float,
                         volatility_60d: float, current_position: int,
                         available_position: int, cash: float,
                         spacing_mult: float = 1.0,
                         max_grids_override: Optional[int] = None,
                         can_buy: bool = True,
                         can_open_new: bool = True) -> List[GridSignal]:
        """生成网格信号"""
        signals = []
        params = self.calc_grid_params(ref_price, atr_20, volatility_60d,
                                       spacing_mult, max_grids_override)

        if params.spacing_pct <= 0:
            return signals

        position_value = current_position * ref_price
        max_pos_value = cash * 0.30  # 单股最大 30% (由 regime 调节)

        # 买入信号
        if can_buy:
            for i in range(1, params.n_grids + 1):
                buy_price = ref_price * (1 - params.spacing_pct * i)
                if buy_price <= 0:
                    continue
                if not can_open_new and position_value <= 0:
                    break
                if position_value >= max_pos_value:
                    break

                qty = int(self.grid_amount / buy_price) // 100 * 100
                if qty >= 100 and qty * buy_price <= cash:
                    signals.append(GridSignal(
                        code=code, direction="buy", price=round(buy_price, 2),
                        quantity=qty, grid_level=i,
                        reason=f"网格买入 L{i}, 间距={params.spacing_pct:.2%}",
                    ))
                    position_value += qty * buy_price

        # 卖出信号 (T+1)
        avail = available_position
        for i in range(1, params.n_grids + 1):
            sell_price = ref_price * (1 + params.spacing_pct * i)
            if sell_price <= 0 or avail <= 0:
                break

            qty = min(avail, int(self.grid_amount / sell_price)) // 100 * 100
            if qty >= 100:
                signals.append(GridSignal(
                    code=code, direction="sell", price=round(sell_price, 2),
                    quantity=qty, grid_level=i,
                    reason=f"网格卖出 L{i}, 间距={params.spacing_pct:.2%}",
                ))
                avail -= qty

        return signals
