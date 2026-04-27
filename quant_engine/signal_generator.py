# -*- coding: utf-8 -*-
"""
signal_generator.py - 统一信号生成器

整合市场状态、风控、网格引擎、ATR止损，生成最终可执行信号。
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .market_regime import RegimeFilter, RegimeState
from .risk_control import RiskControlManager, PositionInfo as RiskPosition
from .grid_engine import GridEngine, GridSignal
from .atr_stop import ATRStopLoss, compute_atr
from .position_manager import PositionManager

logger = logging.getLogger("quant_engine.signals")


class SignalGenerator:
    """统一信号生成器"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.regime = RegimeFilter(config)
        self.risk = RiskControlManager(config)
        self.grid = GridEngine(config)
        self.atr_stop = ATRStopLoss(config)
        self.positions = PositionManager()
        self.cash = config.get("capital", {}).get("total", 1_000_000)
        self.starting_cash = self.cash

    def update_market(self, benchmark_data: dict) -> dict:
        """更新市场状态，返回 regime 结果"""
        return self.regime.check(benchmark_data)

    def check_risk(self, market_prices: Dict[str, float]) -> dict:
        """
        执行风控检查

        Parameters:
            market_prices: {code: current_price}
        """
        risk_positions = []
        for code, pos in self.positions.all_positions().items():
            price = market_prices.get(code, pos.cost_price)
            pnl_pct = (price - pos.cost_price) / pos.cost_price if pos.cost_price > 0 else 0
            risk_positions.append(RiskPosition(
                code=code, cost_price=pos.cost_price,
                current_price=price, quantity=pos.quantity,
                unrealized_pnl_pct=pnl_pct,
            ))

        total_value = self.cash + self.positions.total_market_value(market_prices)
        return self.risk.check(risk_positions, total_value)

    def generate_signals(self, stock_data: Dict[str, dict],
                         market_prices: Dict[str, float],
                         regime_result: dict) -> List[Dict]:
        """
        生成交易信号

        Parameters:
            stock_data: {
                code: {
                    "name": str,
                    "high": pd.Series,
                    "low": pd.Series,
                    "close": pd.Series,
                    "ref_price": float,  # T-1 收盘价
                }
            }
            market_prices: {code: current_price}
            regime_result: regime.check() 返回值

        Returns:
            List[Dict]: 可执行信号列表
        """
        params = regime_result["params"]
        can_buy = regime_result["can_buy"]
        can_open = regime_result["can_open_new"]
        spacing_mult = params.grid_spacing_multiplier
        max_grids = params.max_grids
        stop_mult = params.stop_loss_multiplier

        signals = []

        for code, data in stock_data.items():
            close = data["close"]
            high = data["high"]
            low = data["low"]
            ref_price = data["ref_price"]
            name = data.get("name", code)

            if len(close) < self.atr_stop.atr_period + 1:
                continue

            atr = self.atr_stop.calculate_position_atr(high, low, close)
            vol_60 = (close.pct_change().dropna().rolling(60).std() * np.sqrt(252))
            vol_60d = vol_60.iloc[-1] if not vol_60.empty else 0.20
            daily_vol = vol_60d / np.sqrt(252)

            pos = self.positions.get(code)
            current_pos = pos.quantity if pos else 0
            avail_pos = pos.available if pos else 0

            # 网格信号
            grid_signals = self.grid.generate_signals(
                code=code, ref_price=ref_price, atr_20=atr,
                volatility_60d=vol_60d,
                current_position=current_pos,
                available_position=avail_pos,
                cash=self.cash,
                spacing_mult=spacing_mult,
                max_grids_override=max_grids,
                can_buy=can_buy,
                can_open_new=can_open,
            )

            for gs in grid_signals:
                # 风控过滤
                if gs.direction == "buy" and not self.risk.should_allow_buy(code):
                    logger.info(f"风控拦截: {code} 买入信号")
                    continue

                current_price = market_prices.get(code, ref_price)
                pnl_pct = (current_price - pos.cost_price) / pos.cost_price if (pos and pos.cost_price > 0) else 0

                signals.append({
                    "code": code,
                    "name": name,
                    "direction": gs.direction,
                    "price": gs.price,
                    "quantity": gs.quantity,
                    "grid_level": gs.grid_level,
                    "reason": gs.reason,
                    "atr": round(atr, 3),
                    "volatility": round(vol_60d, 4),
                    "pnl_pct": round(pnl_pct, 4) if pos else None,
                    "timestamp": datetime.now().isoformat(),
                })

            # ATR 止损检查
            if pos and pos.cost_price > 0 and atr > 0:
                stop_price, triggered = self.atr_stop.calculate_stop_price(
                    cost_price=pos.cost_price,
                    current_price=market_prices.get(code, ref_price),
                    atr_value=atr,
                    stop_loss_multiplier=stop_mult,
                    current_stop=pos.stop_loss,
                )

                # 更新止损价 (trailing)
                if pos.stop_loss is None or stop_price > pos.stop_loss:
                    pos.stop_loss = stop_price
                pos.last_atr = atr

                if triggered and pos.available > 0:
                    signals.append({
                        "code": code,
                        "name": name,
                        "direction": "sell",
                        "price": round(market_prices.get(code, ref_price), 2),
                        "quantity": pos.available,
                        "grid_level": 0,
                        "reason": f"ATR止损触发 (stop={stop_price:.2f}, atr_mult={self.atr_stop.atr_multiplier * stop_mult:.1f}x)",
                        "atr": round(atr, 3),
                        "volatility": round(vol_60d, 4),
                        "pnl_pct": round((market_prices.get(code, ref_price) - pos.cost_price) / pos.cost_price, 4),
                        "timestamp": datetime.now().isoformat(),
                        "is_stop_loss": True,
                    })

        # 按优先级排序: 止损 > 卖出 > 买入
        priority = {"sell": 1, "buy": 2}
        signals.sort(key=lambda s: (0 if s.get("is_stop_loss") else 1, priority.get(s["direction"], 3)))

        return signals
