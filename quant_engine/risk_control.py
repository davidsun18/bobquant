# -*- coding: utf-8 -*-
"""
risk_control.py - 双级熔断风控模块

级别1: 单股未实现亏损 ≥ 15% → 暂停该股买入，仅允许卖出
级别2: 总账户最大回撤 ≥ 10% → 全局停止所有买入，仅保留卖出
"""

import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quant_engine.risk")


@dataclass
class PositionInfo:
    code: str
    cost_price: float
    current_price: float
    quantity: int
    unrealized_pnl_pct: float  # (current - cost) / cost


@dataclass
class CircuitBreakerState:
    is_global_breaker: bool = False
    single_stock_breakers: Dict[str, bool] = None
    trigger_reason: str = ""
    trigger_time: str = ""

    def __post_init__(self):
        if self.single_stock_breakers is None:
            self.single_stock_breakers = {}


class RiskControlManager:
    """双级熔断风控管理器"""

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("risk_control", {})
        self.enabled = cfg.get("enabled", True)
        self.single_stock_loss_threshold = cfg.get("single_stock_loss_threshold", 0.15)
        self.max_drawdown_threshold = cfg.get("max_drawdown_threshold", 0.10)
        self.state_file = cfg.get("state_file", "/home/openclaw/.openclaw/workspace/quant_engine/risk_state.json")
        self.peak_value = cfg.get("initial_peak", 1_000_000.0)
        self.state = CircuitBreakerState()
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                self.state = CircuitBreakerState(
                    is_global_breaker=data.get("is_global_breaker", False),
                    single_stock_breakers=data.get("single_stock_breakers", {}),
                    trigger_reason=data.get("trigger_reason", ""),
                    trigger_time=data.get("trigger_time", ""),
                )
                self.peak_value = data.get("peak_value", self.peak_value)
            except Exception as e:
                logger.warning(f"加载风控状态失败: {e}")

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump({
                    "is_global_breaker": self.state.is_global_breaker,
                    "single_stock_breakers": self.state.single_stock_breakers,
                    "trigger_reason": self.state.trigger_reason,
                    "trigger_time": self.state.trigger_time,
                    "peak_value": self.peak_value,
                    "last_update": datetime.now().isoformat(),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存风控状态失败: {e}")

    def check(self, positions: List[PositionInfo], total_value: float) -> CircuitBreakerState:
        """执行完整熔断检查"""
        if not self.enabled:
            return CircuitBreakerState(trigger_reason="风控已禁用")

        # 更新峰值
        if total_value > self.peak_value:
            self.peak_value = total_value

        # 重置
        self.state.single_stock_breakers = {}
        self.state.is_global_breaker = False
        self.state.trigger_reason = ""

        # 全局熔断检查
        if self.peak_value > 0:
            drawdown = (self.peak_value - total_value) / self.peak_value
            if drawdown >= self.max_drawdown_threshold:
                self.state.is_global_breaker = True
                self.state.trigger_reason = f"总回撤 {drawdown:.2%} >= 阈值 {self.max_drawdown_threshold:.0%}"
                self.state.trigger_time = datetime.now().isoformat()
                logger.critical(f"全局熔断: 回撤 {drawdown:.2%}")

        # 个股熔断检查
        for pos in positions:
            pnl_pct = (pos.current_price - pos.cost_price) / pos.cost_price if pos.cost_price > 0 else 0
            if pnl_pct <= -self.single_stock_loss_threshold:
                self.state.single_stock_breakers[pos.code] = True
                logger.warning(f"个股熔断: {pos.code} 亏损 {pnl_pct:.2%}")

        self._save_state()
        return self.state

    def should_allow_buy(self, code: str) -> bool:
        if not self.enabled:
            return True
        if self.state.is_global_breaker:
            return False
        if self.state.single_stock_breakers.get(code):
            return False
        return True

    def should_allow_sell(self, code: str) -> bool:
        """熔断时始终允许卖出"""
        return True

    def reset_global(self):
        if self.state.is_global_breaker:
            self.state.is_global_breaker = False
            self.state.trigger_reason = "手动重置"
            self.state.trigger_time = datetime.now().isoformat()
            self._save_state()
            return True
        return False
