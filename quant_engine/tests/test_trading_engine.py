# -*- coding: utf-8 -*-
"""
综合测试 - BobQuant 量化交易引擎 v2.0

测试覆盖:
1. Market Regime (市场状态识别)
2. Risk Control (双级熔断风控)
3. Grid Engine (动态网格交易)
4. ATR Stop (动态止损)
5. Position Manager (持仓管理 T+1)
6. Signal Generator (信号生成)
7. Trading Engine (主引擎集成)
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

# 添加父目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quant_engine.market_regime import RegimeFilter, RegimeState, RegimeParams, DEFAULT_PARAMS
from quant_engine.risk_control import RiskControlManager, PositionInfo, CircuitBreakerState
from quant_engine.grid_engine import GridEngine, GridSignal, GridParams
from quant_engine.atr_stop import ATRStopLoss, compute_atr
from quant_engine.position_manager import PositionManager, Position
from quant_engine.signal_generator import SignalGenerator
from quant_engine.trading_engine import TradingEngine


# ==================== 工具函数 ====================

def make_ohlc(n=300, start_price=10.0, seed=42):
    """生成模拟 OHLCV 数据"""
    np.random.seed(seed)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
    returns = np.random.normal(0.0005, 0.02, n)
    prices = start_price * np.cumprod(1 + returns)
    df = pd.DataFrame({
        "date": dates,
        "open": prices * (1 + np.random.normal(0, 0.005, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.01, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.01, n))),
        "close": prices,
        "volume": np.random.randint(1_000_000, 50_000_000, n),
    })
    df["high"] = df[["open", "high", "close"]].max(axis=1) * 1.01
    df["low"] = df[["open", "low", "close"]].min(axis=1) * 0.99
    return df


def default_config():
    return {
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
            "state_file": "/tmp/test_risk_state.json",
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


# ==================== 1. Market Regime 测试 ====================

class TestMarketRegime(unittest.TestCase):

    def test_normal_market(self):
        """正常市场状态"""
        df = make_ohlc(n=300, start_price=4000, seed=42)
        config = default_config()
        rf = RegimeFilter(config)
        result = rf.check({
            "close": df["close"],
            "high": df["high"],
            "low": df["low"],
        })
        self.assertIn(result["state"], ["normal", "warning"])
        self.assertTrue(result["can_buy"])
        self.assertTrue(result["can_open_new"])

    def test_hard_circuit_break(self):
        """硬熔断触发"""
        df = make_ohlc(n=300, start_price=4000, seed=42)
        config = default_config()
        rf = RegimeFilter(config)
        result = rf.check({
            "close": df["close"],
            "high": df["high"],
            "low": df["low"],
            "index_daily_return": -0.06,  # 跌 6%
            "limit_down_count": 300,  # 300 只跌停
        })
        self.assertEqual(result["state"], "hard_circuit_break")
        self.assertFalse(result["can_buy"])
        self.assertFalse(result["can_open_new"])

    def test_insufficient_data(self):
        """数据不足时使用默认状态"""
        rf = RegimeFilter(default_config())
        result = rf.check({"close": pd.Series([1, 2, 3])})
        self.assertEqual(result["state"], "normal")
        self.assertTrue(result["can_buy"])

    def test_params_structure(self):
        """参数结构正确性"""
        for state in RegimeState:
            params = DEFAULT_PARAMS[state]
            self.assertIsInstance(params, RegimeParams)
            self.assertGreaterEqual(params.max_position_per_stock, 0)
            self.assertGreaterEqual(params.grid_spacing_multiplier, 0)
            self.assertGreaterEqual(params.max_grids, 0)

    def test_reset(self):
        """reset 后状态归零"""
        rf = RegimeFilter(default_config())
        rf._adx_history = [10, 20, 30]
        rf._confirmed_state = RegimeState.WARNING
        rf.reset()
        self.assertEqual(len(rf._adx_history), 0)
        self.assertEqual(rf._confirmed_state, RegimeState.NORMAL)


# ==================== 2. Risk Control 测试 ====================

class TestRiskControl(unittest.TestCase):

    def setUp(self):
        self.tmpfile = tempfile.mktemp(suffix=".json")
        self.config = default_config()
        self.config["risk_control"]["state_file"] = self.tmpfile

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_no_trigger_normal(self):
        """正常情况无触发"""
        rc = RiskControlManager(self.config)
        positions = [
            PositionInfo(code="000001.SZ", cost_price=10.0, current_price=10.5, quantity=1000, unrealized_pnl_pct=0.05),
        ]
        state = rc.check(positions, total_value=1_100_000)
        self.assertFalse(state.is_global_breaker)
        self.assertEqual(len(state.single_stock_breakers), 0)

    def test_single_stock_breaker(self):
        """个股熔断触发"""
        rc = RiskControlManager(self.config)
        positions = [
            PositionInfo(code="000001.SZ", cost_price=10.0, current_price=8.0, quantity=1000, unrealized_pnl_pct=-0.20),
        ]
        state = rc.check(positions, total_value=950_000)
        self.assertTrue(state.single_stock_breakers.get("000001.SZ"))
        self.assertFalse(rc.should_allow_buy("000001.SZ"))
        self.assertTrue(rc.should_allow_sell("000001.SZ"))  # 始终允许卖出

    def test_global_breaker(self):
        """全局熔断触发"""
        rc = RiskControlManager(self.config)
        positions = []
        state = rc.check(positions, total_value=850_000)  # 回撤 15% > 10%
        self.assertTrue(state.is_global_breaker)
        self.assertFalse(rc.should_allow_buy("000001.SZ"))
        self.assertFalse(rc.should_allow_buy("600519.SH"))

    def test_state_persistence(self):
        """状态持久化"""
        rc = RiskControlManager(self.config)
        rc.check([], total_value=850_000)
        self.assertTrue(os.path.exists(self.tmpfile))

        # 新实例加载状态
        rc2 = RiskControlManager(self.config)
        self.assertTrue(rc2.state.is_global_breaker)

    def test_reset_global(self):
        """手动重置全局熔断"""
        rc = RiskControlManager(self.config)
        rc.check([], total_value=850_000)
        self.assertTrue(rc.reset_global())
        self.assertFalse(rc.state.is_global_breaker)

    def test_disabled(self):
        """风控禁用时始终允许"""
        cfg = default_config()
        cfg["risk_control"]["enabled"] = False
        cfg["risk_control"]["state_file"] = self.tmpfile
        rc = RiskControlManager(cfg)
        positions = [
            PositionInfo(code="000001.SZ", cost_price=10.0, current_price=5.0, quantity=1000, unrealized_pnl_pct=-0.50),
        ]
        state = rc.check(positions, total_value=500_000)
        self.assertFalse(state.is_global_breaker)
        self.assertTrue(rc.should_allow_buy("000001.SZ"))


# ==================== 3. Grid Engine 测试 ====================

class TestGridEngine(unittest.TestCase):

    def test_calc_spacing(self):
        """间距计算"""
        engine = GridEngine(default_config())
        spacing = engine.calc_spacing(0.25)  # 25% 波动率
        self.assertAlmostEqual(spacing, 0.02, delta=0.001)

    def test_spacing_clamped(self):
        """间距在边界内"""
        engine = GridEngine(default_config())
        for vol in [0.05, 0.10, 0.20, 0.30, 0.50, 1.0]:
            spacing = engine.calc_spacing(vol)
            self.assertGreaterEqual(spacing, 0.015)
            self.assertLessEqual(spacing, 0.035)

    def test_grid_params(self):
        """网格参数计算"""
        engine = GridEngine(default_config())
        params = engine.calc_grid_params(ref_price=10.0, atr_20=0.3, volatility_60d=0.25)
        self.assertIsInstance(params, GridParams)
        self.assertGreater(params.spacing_pct, 0)
        self.assertGreaterEqual(params.n_grids, 3)
        self.assertGreater(params.upper_rail, params.lower_rail)

    def test_generate_signals_buy(self):
        """生成买入信号"""
        engine = GridEngine(default_config())
        signals = engine.generate_signals(
            code="000001.SZ", ref_price=10.0, atr_20=0.3,
            volatility_60d=0.25,
            current_position=0, available_position=0,
            cash=1_000_000,
        )
        buy_signals = [s for s in signals if s.direction == "buy"]
        self.assertGreater(len(buy_signals), 0)
        for s in buy_signals:
            self.assertEqual(s.code, "000001.SZ")
            self.assertGreater(s.quantity, 0)
            self.assertEqual(s.quantity % 100, 0)  # 整手

    def test_generate_signals_sell(self):
        """生成卖出信号 (有持仓)"""
        engine = GridEngine(default_config())
        signals = engine.generate_signals(
            code="000001.SZ", ref_price=10.0, atr_20=0.3,
            volatility_60d=0.25,
            current_position=5000, available_position=5000,
            cash=1_000_000,
        )
        sell_signals = [s for s in signals if s.direction == "sell"]
        self.assertGreater(len(sell_signals), 0)
        for s in sell_signals:
            self.assertGreater(s.quantity, 0)
            self.assertLessEqual(s.quantity, 5000)

    def test_no_buy_when_forbidden(self):
        """禁止买入时无买入信号"""
        engine = GridEngine(default_config())
        signals = engine.generate_signals(
            code="000001.SZ", ref_price=10.0, atr_20=0.3,
            volatility_60d=0.25,
            current_position=0, available_position=0,
            cash=1_000_000,
            can_buy=False,
        )
        buy_signals = [s for s in signals if s.direction == "buy"]
        self.assertEqual(len(buy_signals), 0)

    def test_spacing_multiplier(self):
        """间距乘数影响信号数量"""
        engine = GridEngine(default_config())
        signals_normal = engine.generate_signals(
            code="000001.SZ", ref_price=10.0, atr_20=0.3,
            volatility_60d=0.25,
            current_position=0, available_position=0,
            cash=1_000_000,
            spacing_mult=1.0,
        )
        signals_wide = engine.generate_signals(
            code="000001.SZ", ref_price=10.0, atr_20=0.3,
            volatility_60d=0.25,
            current_position=0, available_position=0,
            cash=1_000_000,
            spacing_mult=2.0,
        )
        self.assertGreaterEqual(len(signals_normal), len(signals_wide))


# ==================== 4. ATR Stop 测试 ====================

class TestATRStop(unittest.TestCase):

    def test_basic_stop(self):
        """基本止损计算"""
        stopper = ATRStopLoss(default_config())
        stop_price, triggered = stopper.calculate_stop_price(
            cost_price=10.0, current_price=10.0, atr_value=0.3,
        )
        # ATR stop = 10 - 2.0 * 0.3 = 9.4, but min_stop_pct = 3% → 9.7
        # max(9.4, 9.7) = 9.7
        self.assertAlmostEqual(stop_price, 9.7, delta=0.01)
        self.assertFalse(triggered)

    def test_triggered(self):
        """触发止损"""
        stopper = ATRStopLoss(default_config())
        stop_price, triggered = stopper.calculate_stop_price(
            cost_price=10.0, current_price=9.0, atr_value=0.3,
        )
        self.assertTrue(triggered)

    def test_trailing(self):
        """trailing stop 只升不降"""
        stopper = ATRStopLoss(default_config())

        # 第一次: 成本 10, ATR 0.3
        sp1, _ = stopper.calculate_stop_price(
            cost_price=10.0, current_price=10.0, atr_value=0.3,
        )

        # 价格上涨到 12, ATR 不变
        sp2, _ = stopper.calculate_stop_price(
            cost_price=10.0, current_price=12.0, atr_value=0.3,
            current_stop=sp1,
        )
        self.assertGreater(sp2, sp1)

        # 价格回落到 11, 止损不应下降
        sp3, _ = stopper.calculate_stop_price(
            cost_price=10.0, current_price=11.0, atr_value=0.3,
            current_stop=sp2,
        )
        self.assertGreaterEqual(sp3, sp2)

    def test_min_stop_pct(self):
        """最小止损限制"""
        stopper = ATRStopLoss(default_config())
        # ATR=0.01 → stop = 10 - 2*0.01 = 9.98, min_stop=9.7 → max=9.98
        stop_price, triggered = stopper.calculate_stop_price(
            cost_price=10.0, current_price=10.0, atr_value=0.01,
        )
        self.assertAlmostEqual(stop_price, 9.98, delta=0.01)
        self.assertFalse(triggered)

        # 当 ATR=0.2 → stop = 10 - 2*0.2 = 9.6, min_stop=9.7 → max=9.7
        stop_price2, _ = stopper.calculate_stop_price(
            cost_price=10.0, current_price=10.0, atr_value=0.2,
        )
        self.assertAlmostEqual(stop_price2, 9.7, delta=0.01)

    def test_zero_atr(self):
        """ATR 为 0 时回退"""
        stopper = ATRStopLoss(default_config())
        stop_price, triggered = stopper.calculate_stop_price(
            cost_price=10.0, current_price=9.5, atr_value=0,
        )
        self.assertAlmostEqual(stop_price, 9.7, delta=0.01)
        self.assertTrue(triggered)

    def test_compute_atr(self):
        """ATR 计算"""
        df = make_ohlc(n=50, start_price=10.0)
        atr = compute_atr(df["high"], df["low"], df["close"], period=14)
        self.assertFalse(atr.empty)
        self.assertGreater(atr.iloc[-1], 0)


# ==================== 5. Position Manager 测试 ====================

class TestPositionManager(unittest.TestCase):

    def test_open_position(self):
        """开仓"""
        pm = PositionManager()
        pos = pm.open_position("000001.SZ", "平安银行", 10.0, 1000)
        self.assertEqual(pos.code, "000001.SZ")
        self.assertEqual(pos.quantity, 1000)
        self.assertEqual(pos.cost_price, 10.0)

    def test_t1_lock(self):
        """T+1 锁定: 当日买入不可卖"""
        pm = PositionManager()
        pm.open_position("000001.SZ", "平安银行", 10.0, 1000)
        pos = pm.get("000001.SZ")
        self.assertEqual(pos.available, 0)  # 今日买入, 不可卖
        self.assertFalse(pos.can_sell(100))

    def test_t1_unlock(self):
        """T+1 解锁: 隔日可卖"""
        pm = PositionManager()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        pos = Position("000001.SZ", "平安银行")
        pos.add_buy(10.0, 1000, date=yesterday)
        pm.positions["000001.SZ"] = pos
        self.assertEqual(pos.available, 1000)
        self.assertTrue(pos.can_sell(500))

    def test_partial_sell(self):
        """部分卖出"""
        pm = PositionManager()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        pos = Position("000001.SZ", "平安银行")
        pos.add_buy(10.0, 1000, date=yesterday)
        pm.positions["000001.SZ"] = pos

        self.assertTrue(pm.close_position("000001.SZ", 300))
        self.assertEqual(pm.get("000001.SZ").quantity, 700)

    def test_close_position(self):
        """清仓"""
        pm = PositionManager()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        pos = Position("000001.SZ", "平安银行")
        pos.add_buy(10.0, 1000, date=yesterday)
        pm.positions["000001.SZ"] = pos

        self.assertTrue(pm.close_position("000001.SZ", 1000))
        self.assertIsNone(pm.get("000001.SZ"))

    def test_sell_insufficient(self):
        """卖出数量不足"""
        pm = PositionManager()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        pos = Position("000001.SZ", "平安银行")
        pos.add_buy(10.0, 500, date=yesterday)
        pm.positions["000001.SZ"] = pos

        self.assertFalse(pm.close_position("000001.SZ", 600))

    def test_cost_price_average(self):
        """加权平均成本价"""
        pos = Position("000001.SZ", "平安银行")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        pos.add_buy(10.0, 1000, date=yesterday)
        pos.add_buy(12.0, 1000, date=yesterday)
        self.assertAlmostEqual(pos.cost_price, 11.0, delta=0.01)
        self.assertEqual(pos.quantity, 2000)

    def test_total_market_value(self):
        """总市值计算"""
        pm = PositionManager()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        pm.open_position("000001.SZ", "平安银行", 10.0, 1000, date=yesterday)
        pm.open_position("600519.SH", "贵州茅台", 1800.0, 100, date=yesterday)
        prices = {"000001.SZ": 11.0, "600519.SH": 1850.0}
        mv = pm.total_market_value(prices)
        self.assertAlmostEqual(mv, 11.0 * 1000 + 1850.0 * 100, delta=1)


# ==================== 6. Signal Generator 测试 ====================

class TestSignalGenerator(unittest.TestCase):

    def test_generate_signals(self):
        """基本信号生成"""
        config = default_config()
        config["risk_control"]["state_file"] = "/tmp/test_sg_risk.json"
        sg = SignalGenerator(config)

        df = make_ohlc(n=300, start_price=10.0, seed=42)
        result = sg.update_market({"close": make_ohlc(n=300, start_price=4000)["close"],
                                    "high": make_ohlc(n=300, start_price=4000)["high"],
                                    "low": make_ohlc(n=300, start_price=4000)["low"]})

        stock_data = {
            "000001.SZ": {
                "name": "平安银行",
                "high": df["high"],
                "low": df["low"],
                "close": df["close"],
                "ref_price": df["close"].iloc[-2],
            }
        }

        signals = sg.generate_signals(stock_data, {"000001.SZ": df["close"].iloc[-1]}, result)
        self.assertIsInstance(signals, list)

    def test_risk_filters_buy(self):
        """风控过滤买入信号"""
        config = default_config()
        config["risk_control"]["state_file"] = "/tmp/test_sg_risk2.json"
        sg = SignalGenerator(config)

        # 触发全局熔断
        sg.risk.check([], total_value=850_000)

        df = make_ohlc(n=300, start_price=10.0, seed=42)
        result = sg.regime.check({"close": pd.Series([1.0] * 200)})

        stock_data = {
            "000001.SZ": {
                "name": "平安银行",
                "high": df["high"],
                "low": df["low"],
                "close": df["close"],
                "ref_price": df["close"].iloc[-2],
            }
        }

        signals = sg.generate_signals(stock_data, {"000001.SZ": df["close"].iloc[-1]}, result)
        buy_signals = [s for s in signals if s["direction"] == "buy"]
        self.assertEqual(len(buy_signals), 0)

    def tearDown(self):
        for f in ["/tmp/test_sg_risk.json", "/tmp/test_sg_risk2.json"]:
            if os.path.exists(f):
                os.remove(f)


# ==================== 7. Trading Engine 集成测试 ====================

class TestTradingEngine(unittest.TestCase):

    STATE_FILE = "/tmp/test_engine_state.json"

    def setUp(self):
        self.config = default_config()
        self.config["risk_control"]["state_file"] = "/tmp/test_te_risk.json"

    def tearDown(self):
        for f in ["/tmp/test_engine_state.json", "/tmp/test_te_risk.json"]:
            if os.path.exists(f):
                os.remove(f)

    def test_full_workflow(self):
        """完整工作流: 市场状态 -> 信号 -> 执行 -> 查询"""
        with patch.object(TradingEngine, 'save_state', return_value=None):
            engine = TradingEngine(self.config)

            # 更新市场状态
            benchmark = make_ohlc(n=300, start_price=4000)
            engine.update_benchmark(benchmark)
            self.assertIsNotNone(engine._regime_result)

            # 更新价格
            stock_df = make_ohlc(n=300, start_price=10.0, seed=42)
            engine.update_prices({"000001.SZ": stock_df["close"].iloc[-1]})

            # 生成信号
            stock_data = {
                "000001.SZ": {
                    "name": "平安银行",
                    "high": stock_df["high"],
                    "low": stock_df["low"],
                    "close": stock_df["close"],
                    "ref_price": stock_df["close"].iloc[-2],
                }
            }
            signals = engine.generate_signals(stock_data)
            self.assertIsInstance(signals, list)

            # 执行买入信号
            for sig in signals:
                if sig["direction"] == "buy":
                    result = engine.execute(sig)
                    self.assertIn(result["success"], [True, False])
                    break

            # 查询状态
            status = engine.get_status()
            self.assertIn("cash", status)
            self.assertIn("positions", status)
            self.assertIn("total_value", status)

    def test_buy_and_sell(self):
        """买入后卖出"""
        engine = TradingEngine(self.config)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 手动建仓 (模拟隔日)
        pos = engine.positions.open_position("000001.SZ", "平安银行", 10.0, 1000, date=yesterday)

        # 卖出
        result = engine.execute({
            "code": "000001.SZ", "name": "平安银行",
            "direction": "sell", "price": 10.5, "quantity": 500,
            "reason": "测试卖出",
        })
        self.assertTrue(result["success"])
        self.assertEqual(engine.positions.get("000001.SZ").quantity, 500)

    def test_insufficient_funds(self):
        """资金不足"""
        engine = TradingEngine(self.config)
        engine.cash = 100  # 极少资金

        result = engine.execute({
            "code": "000001.SZ", "name": "平安银行",
            "direction": "buy", "price": 10.0, "quantity": 1000,
            "reason": "测试",
        })
        self.assertFalse(result["success"])
        self.assertIn("资金不足", result["message"])

    def test_sell_without_position(self):
        """无持仓卖出"""
        engine = TradingEngine(self.config)
        result = engine.execute({
            "code": "000001.SZ", "name": "平安银行",
            "direction": "sell", "price": 10.0, "quantity": 100,
            "reason": "测试",
        })
        self.assertFalse(result["success"])

    def test_save_and_load_state(self):
        """状态持久化与恢复"""
        engine = TradingEngine(self.config)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        engine.positions.open_position("000001.SZ", "平安银行", 10.0, 1000, date=yesterday)
        engine.cash = 900_000

        # 用真实文件路径
        import quant_engine.trading_engine as te_mod
        original_state_file = te_mod.STATE_FILE
        te_mod.STATE_FILE = Path("/tmp/test_engine_state.json")

        engine.save_state()
        self.assertTrue(os.path.exists("/tmp/test_engine_state.json"))

        # 新引擎加载
        engine2 = TradingEngine(self.config)
        loaded = engine2.load_state()
        self.assertTrue(loaded)
        self.assertAlmostEqual(engine2.cash, 900_000, delta=1)
        self.assertIsNotNone(engine2.positions.get("000001.SZ"))

        te_mod.STATE_FILE = original_state_file

    def test_risk_blocks_buy(self):
        """全局熔断阻止买入"""
        engine = TradingEngine(self.config)
        engine.risk.check([], total_value=850_000)  # 触发全局熔断

        result = engine.execute({
            "code": "000001.SZ", "name": "平安银行",
            "direction": "buy", "price": 10.0, "quantity": 1000,
            "reason": "测试",
        })
        self.assertFalse(result["success"])
        self.assertIn("风控", result["message"])

    def test_lot_size_validation(self):
        """整手校验"""
        engine = TradingEngine(self.config)
        result = engine.execute({
            "code": "000001.SZ", "name": "平安银行",
            "direction": "buy", "price": 10.0, "quantity": 150,  # 不是 100 的倍数
            "reason": "测试",
        })
        self.assertFalse(result["success"])

    def test_status_report(self):
        """状态报告完整性"""
        engine = TradingEngine(self.config)
        status = engine.get_status()
        required_keys = {"cash", "total_value", "pnl", "pnl_pct", "positions", "n_positions", "regime"}
        for key in required_keys:
            self.assertIn(key, status)


# ==================== 8. 边界与异常测试 ====================

class TestEdgeCases(unittest.TestCase):

    def test_zero_price(self):
        """零价格处理"""
        engine = GridEngine(default_config())
        signals = engine.generate_signals(
            code="000001.SZ", ref_price=0.0, atr_20=0.3,
            volatility_60d=0.25,
            current_position=0, available_position=0,
            cash=1_000_000,
        )
        # 价格为 0 时不应产生有效信号
        for s in signals:
            self.assertGreater(s.price, 0)

    def test_very_high_volatility(self):
        """极高波动率"""
        engine = GridEngine(default_config())
        spacing = engine.calc_spacing(2.0)  # 200% 波动率
        self.assertLessEqual(spacing, 0.035)  # 不超过上限

    def test_empty_stock_data(self):
        """空股票数据"""
        config = default_config()
        config["risk_control"]["state_file"] = "/tmp/test_edge_risk.json"
        sg = SignalGenerator(config)
        # 使用有效 regime_result
        result = sg.regime.check({"close": pd.Series([1.0] * 200)})
        signals = sg.generate_signals({}, {}, result)
        self.assertEqual(len(signals), 0)

    def tearDown(self):
        f = "/tmp/test_edge_risk.json"
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    unittest.main()
