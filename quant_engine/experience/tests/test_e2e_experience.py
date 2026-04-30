# -*- coding: utf-8 -*-
"""
test_e2e_experience.py - 自学习系统端到端集成测试

测试完整的自学习闭环：
1. 信号生成 → 自动记录决策快照
2. 复盘 → 生成经验条目
3. 再次信号生成 → 召回经验 → 调整置信度
4. 反馈闭环 → 参数调整
"""

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quant_engine import TradingEngine


def make_benchmark_df(days=300):
    """生成模拟基准数据"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq="B")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(days) * 0.5)
    high = close + np.abs(np.random.randn(days) * 0.3)
    low = close - np.abs(np.random.randn(days) * 0.3)
    return pd.DataFrame({"date": dates, "close": close, "high": high, "low": low})


def make_stock_data(code="000001", name="平安银行", days=300, base_price=15.0):
    """生成模拟股票数据"""
    np.random.seed(hash(code) % 10000)
    dates = pd.date_range(end=datetime.now(), periods=days, freq="B")
    close = base_price + np.cumsum(np.random.randn(days) * 0.1)
    close = np.maximum(close, 1.0)
    high = close + np.abs(np.random.randn(days) * 0.05)
    low = close - np.abs(np.random.randn(days) * 0.05)
    return {
        code: {
            "name": name,
            "close": pd.Series(close),
            "high": pd.Series(high),
            "low": pd.Series(low),
            "ref_price": float(close[-1]),
        }
    }


class TestEndToEndExperience(unittest.TestCase):
    """端到端集成测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            "capital": {"total": 1_000_000},
            "experience": {
                "enabled": True,
                "top_k": 3,
                "conviction_threshold": 30.0,
                "base_dir": self.test_dir,
            },
        }
        self.engine = TradingEngine(self.config)
        self.benchmark_df = make_benchmark_df()

    def test_full_cycle(self):
        """完整流程: 信号生成 → 快照 → 复盘 → 经验注入"""
        # 1. 更新市场状态
        self.engine.update_benchmark(self.benchmark_df)

        # 2. 生成信号（应自动记录快照）
        stock_data = make_stock_data()
        prices = {"000001": stock_data["000001"]["ref_price"]}
        self.engine.update_prices(prices)

        signals = self.engine.generate_signals(stock_data)
        self.assertIsInstance(signals, list)

        # 3. 执行交易
        for sig in signals[:1]:  # 只执行第一个
            result = self.engine.execute(sig)
            self.assertIn("success", result)

        # 4. 运行复盘（需要修改快照时间为过去）
        # 这里测试复盘 API 能正常调用
        review_result = self.engine.run_review(prices)
        self.assertIn("reviewed_count", review_result)

        # 5. 获取经验摘要
        summary = self.engine.get_experience_summary()
        self.assertIn("stats", summary)
        self.assertIn("recent_experiences", summary)

    def test_review_creates_experiences(self):
        """复盘应能生成经验条目"""
        from quant_engine.experience import (
            DecisionSnapshot,
            get_experience_lib,
            get_review_agent,
        )

        lib = get_experience_lib()

        # 写入一个过去的快照
        past = (datetime.now() - timedelta(hours=25)).isoformat()
        snap = DecisionSnapshot(
            decision_id="e2e_test_001",
            timestamp=past,
            code="000001",
            name="平安银行",
            direction="buy",
            price=15.0,
            regime_state="normal",
            regime_adx=20.0,
            regime_vol_percentile=0.50,
            grid_level=0,
        )
        # 直接写入
        from pathlib import Path
        date_str = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d")
        snap_dir = Path(self.test_dir) / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        filepath = snap_dir / f"{date_str}.jsonl"
        import json
        with open(filepath, "w") as f:
            f.write(json.dumps(snap.to_dict()) + "\n")

        # 覆盖 lib 路径
        lib.base_dir = Path(self.test_dir)
        lib.snapshots_dir = snap_dir
        lib._load()

        reviewer = get_review_agent()
        reviewer.lib = lib

        result = reviewer.run_review({"000001": 15.50})  # 涨了 3.3%
        self.assertGreaterEqual(result["reviewed_count"], 1)
        self.assertGreaterEqual(result["win_count"], 1)

    def test_feedback_loop_integration(self):
        """反馈闭环应能正常工作"""
        trades = []
        for i in range(25):
            trades.append({
                "time": datetime.now().isoformat(),
                "action": "sell",
                "code": "000001",
                "price": 15.0,
                "quantity": 100,
                "pnl_pct": 0.02 if i < 15 else -0.03,
                "is_stop_loss": False,
                "reason": "网格卖出",
            })

        adjustments = self.engine.run_weekly_review()
        self.assertIsInstance(adjustments, list)


if __name__ == "__main__":
    unittest.main()
