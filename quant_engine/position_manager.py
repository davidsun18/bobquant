# -*- coding: utf-8 -*-
"""
position_manager.py - 持仓管理器 (T+1 合规)

管理持仓的买入/卖出记录，严格区分总持仓和可用持仓。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("quant_engine.position")


class Position:
    """单只股票持仓"""

    def __init__(self, code: str, name: str = ""):
        self.code = code
        self.name = name
        self.quantity = 0
        self.cost_price = 0.0
        self.frozen = 0  # 挂单冻结
        self.buy_records: List[Dict] = []  # [{date, price, quantity}]
        self.stop_loss: Optional[float] = None  # 当前止损价
        self.last_atr: float = 0.0

    @property
    def available(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        avail = 0
        for r in self.buy_records:
            if r["date"] < today:
                avail += r["quantity"]
        return max(0, avail - self.frozen)

    def add_buy(self, price: float, quantity: int, date: str = None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        total_cost = self.cost_price * self.quantity + price * quantity
        self.quantity += quantity
        self.cost_price = total_cost / self.quantity if self.quantity > 0 else 0
        self.buy_records.append({"date": date, "price": price, "quantity": quantity})
        # 清理 3 天前的记录
        cutoff = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        self.buy_records = [r for r in self.buy_records if r["date"] >= cutoff]

    def execute_sell(self, quantity: int) -> bool:
        if quantity > self.available:
            return False
        self.quantity -= quantity
        # 从最早的可用记录中扣减
        today = datetime.now().strftime("%Y-%m-%d")
        remaining = quantity
        for r in self.buy_records:
            if r["date"] < today and remaining > 0:
                deduct = min(remaining, r["quantity"])
                r["quantity"] -= deduct
                remaining -= deduct
        self.buy_records = [r for r in self.buy_records if r["quantity"] > 0]
        if self.quantity <= 0:
            self.quantity = 0
            self.cost_price = 0.0
        return True

    def can_sell(self, quantity: int) -> bool:
        return quantity <= self.available

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "name": self.name,
            "quantity": self.quantity,
            "available": self.available,
            "cost_price": round(self.cost_price, 3),
            "frozen": self.frozen,
            "stop_loss": self.stop_loss,
            "last_atr": self.last_atr,
        }


class PositionManager:
    """持仓管理器"""

    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def get(self, code: str) -> Optional[Position]:
        return self.positions.get(code)

    def open_position(self, code: str, name: str, price: float,
                      quantity: int, date: str = None) -> Position:
        if code not in self.positions:
            self.positions[code] = Position(code, name)
        pos = self.positions[code]
        pos.add_buy(price, quantity, date)
        return pos

    def close_position(self, code: str, quantity: int) -> bool:
        pos = self.positions.get(code)
        if pos is None or not pos.execute_sell(quantity):
            return False
        if pos.quantity <= 0:
            del self.positions[code]
        return True

    def all_positions(self) -> Dict[str, Position]:
        return self.positions.copy()

    def total_market_value(self, prices: Dict[str, float]) -> float:
        return sum(
            pos.quantity * prices.get(pos.code, pos.cost_price)
            for pos in self.positions.values()
        )
