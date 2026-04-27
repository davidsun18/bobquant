# -*- coding: utf-8 -*-
"""
trading_engine.py - 主交易引擎

整合市场状态识别、风控、网格交易、ATR止损，提供统一的交易接口。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .market_regime import RegimeFilter, RegimeState
from .risk_control import RiskControlManager, PositionInfo as RiskPosition
from .grid_engine import GridEngine
from .atr_stop import ATRStopLoss, compute_atr
from .position_manager import PositionManager
from .signal_generator import SignalGenerator

logger = logging.getLogger("quant_engine.engine")

STATE_FILE = Path("/home/openclaw/.openclaw/workspace/quant_engine/engine_state.json")


class TradingEngine:
    """
    BobQuant 交易引擎 v2.0

    使用方式:
        engine = TradingEngine(config)
        engine.load_state()  # 可选，恢复上次状态

        # 每日开盘前
        engine.update_benchmark(benchmark_df)  # 更新市场状态
        engine.update_prices(market_prices)     # 更新最新价格
        engine.check_stop_losses()              # 检查止损

        # 生成信号
        signals = engine.generate_signals(stock_data)

        # 执行交易
        for sig in signals:
            engine.execute(sig)

        engine.save_state()
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.signal_gen = SignalGenerator(config)
        self.positions = self.signal_gen.positions
        self.risk = self.signal_gen.risk
        self.regime = self.signal_gen.regime
        self.grid = self.signal_gen.grid
        self.atr_stop = self.signal_gen.atr_stop
        self.cash = self.signal_gen.cash
        self.starting_cash = self.signal_gen.starting_cash

        self._market_prices: Dict[str, float] = {}
        self._regime_result: Optional[dict] = None
        self._risk_state: Optional[dict] = None
        self._trade_log: List[Dict] = []

    # ==================== 市场状态 ====================

    def update_benchmark(self, benchmark_df: pd.DataFrame):
        """
        更新基准指数数据，重新判断市场状态

        benchmark_df 需包含: date, open, high, low, close, volume
        """
        required = {"close", "high", "low"}
        if not required.issubset(benchmark_df.columns):
            logger.warning(f"基准数据缺少列: {required - set(benchmark_df.columns)}")
            return

        data = {
            "close": benchmark_df["close"],
            "high": benchmark_df["high"],
            "low": benchmark_df["low"],
            "volume": benchmark_df.get("volume", pd.Series()),
        }

        if len(benchmark_df) >= 2:
            data["index_daily_return"] = benchmark_df["close"].pct_change().iloc[-1]

        self._regime_result = self.regime.check(data)
        logger.info(f"市场状态更新: {self._regime_result['state']}")

    # ==================== 价格更新 ====================

    def update_prices(self, prices: Dict[str, float]):
        """更新所有股票最新价格"""
        self._market_prices.update(prices)

    # ==================== 风控 ====================

    def check_risk(self) -> dict:
        """执行风控检查"""
        self._risk_state = self.signal_gen.check_risk(self._market_prices)
        return self._risk_state

    # ==================== 信号生成 ====================

    def generate_signals(self, stock_data: Dict[str, dict]) -> List[Dict]:
        """
        生成交易信号

        stock_data: {
            code: {
                "name": str,
                "high": pd.Series,
                "low": pd.Series,
                "close": pd.Series,
                "ref_price": float,
            }
        }
        """
        if self._regime_result is None:
            logger.warning("未更新市场状态，使用默认参数")
            self._regime_result = self.regime.check({"close": pd.Series([1] * 100)})

        signals = self.signal_gen.generate_signals(
            stock_data, self._market_prices, self._regime_result
        )

        logger.info(f"生成 {len(signals)} 个信号 "
                    f"(买入={sum(1 for s in signals if s['direction']=='buy')}, "
                    f"卖出={sum(1 for s in signals if s['direction']=='sell')})")

        return signals

    # ==================== 交易执行 ====================

    def execute(self, signal: Dict) -> Dict:
        """
        执行单个信号

        Returns:
            {success: bool, message: str, details: dict}
        """
        code = signal["code"]
        direction = signal["direction"]
        price = signal["price"]
        quantity = signal["quantity"]
        name = signal.get("name", code)

        # 价格校验
        if price <= 0 or quantity <= 0:
            return {"success": False, "message": "价格或数量无效"}

        # 整手校验
        if quantity % 100 != 0:
            return {"success": False, "message": f"数量 {quantity} 不是 100 的整数倍"}

        if direction == "buy":
            return self._execute_buy(code, name, price, quantity, signal)
        elif direction == "sell":
            return self._execute_sell(code, price, quantity, signal)
        else:
            return {"success": False, "message": f"未知方向: {direction}"}

    def _execute_buy(self, code: str, name: str, price: float,
                     quantity: int, signal: Dict) -> Dict:
        """执行买入"""
        if not self.risk.should_allow_buy(code):
            return {"success": False, "message": f"风控禁止买入 {code}"}

        # 资金检查 (含手续费估算 万三)
        cost = price * quantity
        fees = cost * 0.0003
        total = cost + fees
        if total > self.cash:
            return {"success": False, "message": f"资金不足: 需要 {total:.2f}, 可用 {self.cash:.2f}"}

        self.cash -= total
        self.positions.open_position(code, name, price, quantity)
        self._trade_log.append({
            "time": datetime.now().isoformat(),
            "action": "buy", "code": code, "name": name,
            "price": price, "quantity": quantity,
            "cost": round(total, 2),
            "reason": signal.get("reason", ""),
        })

        logger.info(f"买入 {code} {quantity}股 @ {price:.2f} "
                     f"费用 {fees:.2f} 剩余 {self.cash:.2f}")
        return {"success": True, "message": f"买入 {code} {quantity}股",
                "details": {"price": price, "quantity": quantity, "cost": round(total, 2)}}

    def _execute_sell(self, code: str, price: float,
                      quantity: int, signal: Dict) -> Dict:
        """执行卖出"""
        pos = self.positions.get(code)
        if pos is None:
            return {"success": False, "message": f"无 {code} 持仓"}

        if not pos.can_sell(quantity):
            return {"success": False,
                    "message": f"可卖不足: 需要 {quantity}, 可用 {pos.available}"}

        if not self.risk.should_allow_sell(code):
            return {"success": False, "message": f"风控禁止卖出 {code}"}

        revenue = price * quantity
        stamp_tax = revenue * 0.0005  # 印花税
        commission = revenue * 0.0003
        total_fees = stamp_tax + commission
        net = revenue - total_fees

        self.cash += net
        self.positions.close_position(code, quantity)

        is_stop = signal.get("is_stop_loss", False)
        self._trade_log.append({
            "time": datetime.now().isoformat(),
            "action": "sell", "code": code,
            "price": price, "quantity": quantity,
            "revenue": round(net, 2),
            "fees": round(total_fees, 2),
            "is_stop_loss": is_stop,
            "reason": signal.get("reason", ""),
        })

        action_name = "止损卖出" if is_stop else "卖出"
        logger.info(f"{action_name} {code} {quantity}股 @ {price:.2f} "
                     f"净收入 {net:.2f}")
        return {"success": True, "message": f"{action_name} {code} {quantity}股",
                "details": {"price": price, "quantity": quantity, "net": round(net, 2)}}

    # ==================== 状态查询 ====================

    def get_status(self) -> Dict:
        """获取引擎完整状态"""
        total_value = self.cash + self.positions.total_market_value(self._market_prices)
        pnl = total_value - self.starting_cash

        pos_data = {code: pos.to_dict() for code, pos in self.positions.all_positions().items()}

        return {
            "cash": round(self.cash, 2),
            "total_value": round(total_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / self.starting_cash * 100, 2),
            "positions": pos_data,
            "n_positions": len(self.positions.all_positions()),
            "regime": self._regime_result.get("state") if self._regime_result else "unknown",
            "risk_global_breaker": self.risk.state.is_global_breaker,
            "risk_single_breakers": self.risk.state.single_stock_breakers,
            "recent_trades": self._trade_log[-10:],
            "timestamp": datetime.now().isoformat(),
        }

    # ==================== 持久化 ====================

    def save_state(self):
        """保存引擎状态到文件"""
        state = {
            "cash": self.cash,
            "starting_cash": self.starting_cash,
            "positions": {code: pos.to_dict() for code, pos in self.positions.all_positions().items()},
            "regime_state": self._regime_result,
            "trade_log": self._trade_log[-100:],
            "saved_at": datetime.now().isoformat(),
        }
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self) -> bool:
        """从文件恢复引擎状态"""
        if not STATE_FILE.exists():
            return False

        try:
            with open(STATE_FILE) as f:
                state = json.load(f)

            self.cash = state.get("cash", self.starting_cash)
            self.starting_cash = state.get("starting_cash", self.starting_cash)

            for code, pdata in state.get("positions", {}).items():
                pos = self.positions.open_position(
                    code, pdata.get("name", ""),
                    pdata.get("cost_price", 0),
                    pdata.get("quantity", 0),
                    date=datetime.now().strftime("%Y-%m-%d"),
                )
                pos.stop_loss = pdata.get("stop_loss")
                pos.last_atr = pdata.get("last_atr", 0)

            self._regime_result = state.get("regime_state")
            self._trade_log = state.get("trade_log", [])
            logger.info(f"引擎状态已恢复: cash={self.cash:.2f}, {len(self.positions.all_positions())} 持仓")
            return True
        except Exception as e:
            logger.error(f"加载状态失败: {e}")
            return False
