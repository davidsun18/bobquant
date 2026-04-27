#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution Bot - 交易执行机器人 v2.0

集成 BobQuant 量化交易引擎:
- 市场状态识别 (RegimeFilter)
- 双级熔断风控 (RiskControl)
- 动态网格交易 (GridEngine)
- ATR 动态止损 (ATRStopLoss)
- T+1 合规持仓管理

旧版代码保留为兼容层，新功能通过 TradingEngine 实现。
"""

import sys
import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加框架路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.agent_base import AgentBase, Message
from framework.trading_rules import TradingRules, TradingConfig, get_trading_rules
from framework.message_queue import get_queue

# 引入新引擎
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "quant_engine"))
from quant_engine.trading_engine import TradingEngine
from quant_engine.position_manager import Position
from quant_engine.market_regime import RegimeFilter, RegimeState

# 配置日志
LOG_DIR = Path("/home/openclaw/.openclaw/workspace/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / "execution_bot.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ExecutionBot")

# ==================== 引擎配置 ====================

ENGINE_CONFIG = {
    "capital": {"total": 1_000_000},
    "grid": {
        "base_spacing": 0.02,
        "min_spacing": 0.015,
        "max_spacing": 0.035,
        "max_grids": 5,
        "grid_amount": 10000,
        "atr_period": 20,
        "rail_z": 2.0,
        "t1_min_spacing_coef": 1.5,
    },
    "atr_stop": {
        "atr_period": 20,
        "atr_multiplier": 2.0,
        "trailing": True,
        "min_stop_pct": 0.03,
    },
    "risk_control": {
        "enabled": True,
        "single_stock_loss_threshold": 0.15,
        "max_drawdown_threshold": 0.10,
        "initial_peak": 1_000_000,
        "state_file": str(LOG_DIR / "risk_state.json"),
    },
    "regime_filter": {
        "adx_normal_max": 25,
        "adx_warning_max": 35,
        "vol_normal_low": 0.30,
        "vol_normal_high": 0.70,
        "vol_extreme_low": 0.15,
        "vol_extreme_high": 0.85,
        "smoothing_days": 3,
        "confirm_days": 2,
        "hard_stop_index_drop": 0.05,
        "hard_stop_limit_down_count": 200,
    },
}


class ExecutionBot(AgentBase):
    """交易执行机器人 v2.0"""

    def __init__(self):
        super().__init__("execution_bot")

        self.rules = get_trading_rules()
        self.engine = TradingEngine(ENGINE_CONFIG)

        # 兼容旧版: 加载持久化状态
        self.engine.load_state()

        # 基准指数数据缓存
        self._benchmark_df = None
        self._stock_data_cache: Dict[str, dict] = {}

        logger.info(f"Execution Bot v2.0 启动，初始资金：¥{self.engine.cash:,.2f}")

    def on_start(self):
        """启动时调用"""
        logger.info("Execution Bot v2.0 启动")
        self.publish_event("agent_status", {
            "agent": "execution_bot",
            "version": "2.0",
            "status": "running",
            "cash": self.engine.cash,
        })

    def on_message(self, message: Message):
        """处理收到的消息"""
        logger.info(f"收到消息：{message.msg_type} from {message.from_agent}")

        try:
            if message.msg_type == "trade_order":
                self.handle_trade_order(message)
            elif message.msg_type == "query_position":
                self.handle_query_position(message)
            elif message.msg_type == "query_order":
                self.handle_query_order(message)
            elif message.msg_type == "update_benchmark":
                self.handle_update_benchmark(message)
            elif message.msg_type == "update_prices":
                self.handle_update_prices(message)
            elif message.msg_type == "generate_signals":
                self.handle_generate_signals(message)
            elif message.msg_type == "get_status":
                self.handle_get_status(message)
            else:
                logger.warning(f"未知消息类型：{message.msg_type}")
        except Exception as e:
            logger.error(f"处理消息失败：{e}", exc_info=True)
            self.queue.fail(message.id, "execution_bot", str(e), retry=False)

    def handle_update_benchmark(self, message: Message):
        """更新基准指数数据"""
        import pandas as pd
        content = message.content
        try:
            df = pd.DataFrame(content.get("data", []))
            if not df.empty:
                self.engine.update_benchmark(df)
                self._benchmark_df = df
                self.send_message(message.from_agent, "benchmark_updated", {
                    "state": self.engine._regime_result.get("state", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                })
            else:
                self.send_message(message.from_agent, "benchmark_updated", {
                    "error": "数据为空",
                })
        except Exception as e:
            self.send_message(message.from_agent, "benchmark_updated", {
                "error": str(e),
            })

    def handle_update_prices(self, message: Message):
        """更新股票价格"""
        prices = message.content.get("prices", {})
        self.engine.update_prices(prices)
        self.send_message(message.from_agent, "prices_updated", {
            "count": len(prices),
            "timestamp": datetime.now().isoformat(),
        })

    def handle_generate_signals(self, message: Message):
        """生成交易信号"""
        import pandas as pd
        stock_data = message.content.get("stock_data", {})

        # 转换为引擎需要的格式
        engine_stock_data = {}
        for code, data in stock_data.items():
            df = pd.DataFrame(data.get("history", []))
            if df.empty or len(df) < 30:
                continue
            engine_stock_data[code] = {
                "name": data.get("name", code),
                "high": df["high"],
                "low": df["low"],
                "close": df["close"],
                "ref_price": data.get("ref_price", df["close"].iloc[-2]),
            }

        # 风控检查
        self.engine.check_risk()

        # 生成信号
        signals = self.engine.generate_signals(engine_stock_data)

        self.send_message(message.from_agent, "signals_generated", {
            "signals": signals,
            "count": len(signals),
            "regime": self.engine._regime_result.get("state", "unknown") if self.engine._regime_result else "unknown",
            "risk_global": self.engine.risk.state.is_global_breaker,
            "timestamp": datetime.now().isoformat(),
        })

    def handle_trade_order(self, message: Message):
        """处理交易订单 (兼容旧版)"""
        content = message.content
        signal = {
            "code": content.get("stock_code"),
            "name": content.get("stock_name", ""),
            "direction": content.get("action", "buy").lower(),
            "price": float(content.get("price", 0)),
            "quantity": int(content.get("quantity", 0)),
            "reason": content.get("reason", "manual"),
        }

        result = self.engine.execute(signal)

        if result["success"]:
            self.send_message(message.from_agent, "order_filled", {
                "order_id": f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}",
                **result["details"],
                **signal,
            })
            self.publish_event("trade_executed", {
                "stock_code": signal["code"],
                "action": signal["direction"],
                "price": signal["price"],
                "quantity": signal["quantity"],
                "amount": signal["price"] * signal["quantity"],
            })
        else:
            self.send_message(message.from_agent, "order_rejected", {
                "reason": result["message"],
                "stock_code": signal["code"],
                "action": signal["direction"],
                "quantity": signal["quantity"],
            })

        # 持久化状态
        self.engine.save_state()

    def handle_query_position(self, message: Message):
        """处理持仓查询"""
        stock_code = message.content.get('stock_code')

        if stock_code:
            pos = self.engine.positions.get(stock_code)
            if pos:
                self.send_message(message.from_agent, "position_info", pos.to_dict())
            else:
                self.send_message(message.from_agent, "position_info", {
                    "stock_code": stock_code, "quantity": 0, "available": 0
                })
        else:
            status = self.engine.get_status()
            self.send_message(message.from_agent, "position_list", {
                "positions": status["positions"],
                "cash": status["cash"],
                "total_value": status["total_value"],
            })

    def handle_query_order(self, message: Message):
        """处理订单查询"""
        status = self.engine.get_status()
        self.send_message(message.from_agent, "order_list", {
            "orders": status.get("recent_trades", []),
        })

    def handle_get_status(self, message: Message):
        """获取引擎状态"""
        status = self.engine.get_status()
        self.send_message(message.from_agent, "engine_status", status)

    def on_tick(self):
        """定期调用 (每 10 秒)"""
        # 持久化状态
        self.engine.save_state()

        # 发布状态
        status = self.engine.get_status()
        self.publish_event("execution_status", {
            "cash": status["cash"],
            "positions": status["n_positions"],
            "total_value": status["total_value"],
            "pnl": status["pnl"],
            "pnl_pct": status["pnl_pct"],
            "regime": status["regime"],
        })

    def get_status(self) -> Dict:
        """获取状态"""
        return self.engine.get_status()


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Execution Bot v2.0 启动")
    logger.info("=" * 60)

    bot = ExecutionBot()
    bot.start(tick_interval=10.0)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号")
        bot.stop()
        bot.engine.save_state()


if __name__ == "__main__":
    main()
