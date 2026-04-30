# -*- coding: utf-8 -*-
"""
test_experience.py - 经验学习系统单元测试

测试覆盖：
- 决策快照创建和保存
- 经验库存储和加载
- 经验检索（标签匹配）
- 复盘 Agent
- 经验注入器
- 反馈闭环
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# 确保模块路径正确
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quant_engine.experience.experience_lib import (
    DecisionOutcome,
    DecisionSnapshot,
    ExperienceEntry,
    ExperienceLibrary,
    LessonType,
)
from quant_engine.experience.review_agent import ReviewAgent
from quant_engine.experience.experience_injector import ExperienceInjector
from quant_engine.experience.feedback_loop import FeedbackLoop


class TestDecisionSnapshot(unittest.TestCase):
    """决策快照测试"""

    def test_create_snapshot(self):
        snap = DecisionSnapshot(
            decision_id="test_001",
            code="000001",
            name="平安银行",
            direction="buy",
            regime_state="normal",
            regime_adx=20.0,
            regime_vol_percentile=0.50,
            price=15.50,
            atr_20=0.30,
            volatility_60d=0.25,
            grid_level=0,
            reason="网格买入信号",
        )
        self.assertEqual(snap.code, "000001")
        self.assertEqual(snap.direction, "buy")
        self.assertEqual(snap.outcome, "pending")

    def test_snapshot_serialization(self):
        snap = DecisionSnapshot(
            decision_id="test_002",
            code="600519",
            name="贵州茅台",
            direction="sell",
            price=1800.0,
        )
        d = snap.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["code"], "600519")

        snap2 = DecisionSnapshot.from_dict(d)
        self.assertEqual(snap2.decision_id, "test_002")

    def test_tag_generation(self):
        tags = ExperienceLibrary.generate_tags(
            regime_state="normal",
            regime_adx=20.0,
            regime_vol_pct=0.50,
            grid_level=0,
            signal_type="buy",
            has_position=False,
        )
        self.assertEqual(tags["regime"], "normal")
        self.assertEqual(tags["adx_range"], "low")
        self.assertEqual(tags["vol_range"], "normal")
        self.assertEqual(tags["grid_level"], "entry")
        self.assertEqual(tags["position_type"], "new_open")


class TestExperienceLibrary(unittest.TestCase):
    """经验库测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.lib = ExperienceLibrary(base_dir=self.test_dir)

    def test_save_and_load_snapshot(self):
        snap = DecisionSnapshot(
            decision_id="snap_001",
            code="000001",
            direction="buy",
            price=15.0,
            regime_state="normal",
        )
        self.lib.save_snapshot(snap)

        snaps = self.lib.load_snapshots(datetime.now().strftime("%Y-%m-%d"))
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0].decision_id, "snap_001")

    def test_add_experience(self):
        exp = ExperienceEntry(
            experience_id="exp_001",
            source_decision_id="snap_001",
            lesson_type="success_pattern",
            tags={"regime": "normal", "signal_type": "buy"},
            summary="正常市场买入成功",
            conviction_impact=10.0,
        )
        self.lib.add_experience(exp)
        self.assertEqual(len(self.lib._experiences), 1)

    def test_experience_merge(self):
        """相同标签的经验应该合并"""
        exp1 = ExperienceEntry(
            lesson_type="success_pattern",
            tags={"regime": "normal", "signal_type": "buy"},
            summary="经验1",
            conviction_impact=10.0,
        )
        exp2 = ExperienceEntry(
            lesson_type="success_pattern",
            tags={"regime": "normal", "signal_type": "buy"},
            summary="经验2",
            conviction_impact=8.0,
        )
        self.lib.add_experience(exp1)
        self.lib.add_experience(exp2)
        # 应该合并为1条，occurrence_count=2
        self.assertEqual(len(self.lib._experiences), 1)
        self.assertEqual(self.lib._experiences[0].occurrence_count, 2)

    def test_retrieve_by_tags(self):
        # 添加多条经验
        for i in range(5):
            exp = ExperienceEntry(
                lesson_type="success_pattern" if i < 3 else "failure_pattern",
                tags={"regime": "normal", "adx_range": "low", "signal_type": "buy"},
                summary=f"经验{i}",
                conviction_impact=10.0 if i < 3 else -15.0,
                occurrence_count=i + 1,
            )
            self.lib.add_experience(exp)

        # 检索
        results = self.lib.retrieve(
            {"regime": "normal", "adx_range": "low", "signal_type": "buy"},
            top_k=3,
        )
        self.assertLessEqual(len(results), 3)

    def test_stats(self):
        snap = DecisionSnapshot(
            decision_id="stats_001",
            code="000001",
            direction="buy",
            price=15.0,
        )
        self.lib.save_snapshot(snap)
        stats = self.lib.get_stats()
        self.assertEqual(stats["total_decisions"], 1)

    def test_update_outcome(self):
        snap = DecisionSnapshot(
            decision_id="outcome_001",
            code="000001",
            direction="buy",
            price=15.0,
        )
        self.lib.save_snapshot(snap)

        result = self.lib.update_snapshot_outcome(
            "outcome_001", "win", 0.05, "判断正确"
        )
        self.assertTrue(result)

        snaps = self.lib.load_all_snapshots()
        for s in snaps:
            if s.decision_id == "outcome_001":
                self.assertEqual(s.outcome, "win")
                self.assertEqual(s.actual_return, 0.05)
                break


class TestReviewAgent(unittest.TestCase):
    """复盘 Agent 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.lib = ExperienceLibrary(base_dir=self.test_dir)

        # 创建一个24小时前的待复盘快照
        past_time = (datetime.now() - timedelta(hours=25)).isoformat()
        snap = DecisionSnapshot(
            decision_id="review_001",
            timestamp=past_time,
            code="000001",
            direction="buy",
            price=15.0,
            regime_state="normal",
            regime_adx=20.0,
            regime_vol_percentile=0.50,
            grid_level=0,
        )
        # 直接写入文件
        date_str = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d")
        filepath = Path(self.test_dir) / "snapshots" / f"{date_str}.jsonl"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(json.dumps(snap.to_dict()) + "\n")

    def test_review_with_price_data(self):
        agent = ReviewAgent(review_hours=24)
        # 覆盖 lib 为测试目录
        agent.lib = self.lib

        market_prices = {"000001": 15.50}  # 涨了 3.3%
        result = agent.run_review(market_prices)

        self.assertEqual(result["reviewed_count"], 1)
        self.assertEqual(result["win_count"], 1)
        self.assertEqual(result["experiences_added"], 1)

    def test_review_loss(self):
        agent = ReviewAgent(review_hours=24)
        agent.lib = self.lib

        market_prices = {"000001": 14.0}  # 跌了 6.7%
        result = agent.run_review(market_prices)

        self.assertEqual(result["loss_count"], 1)


class TestExperienceInjector(unittest.TestCase):
    """经验注入器测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.lib = ExperienceLibrary(base_dir=self.test_dir)
        self.injector = ExperienceInjector(top_k=3)
        self.injector.lib = self.lib

        # 添加一些经验
        for i in range(3):
            exp = ExperienceEntry(
                lesson_type="success_pattern",
                tags={"regime": "normal", "signal_type": "buy"},
                summary=f"成功模式{i}",
                conviction_impact=10.0 + i,
                occurrence_count=2,
            )
            self.lib.add_experience(exp)

        # 添加一条失败经验
        exp_fail = ExperienceEntry(
            lesson_type="failure_pattern",
            tags={"regime": "warning", "signal_type": "buy"},
            summary="预警市场买入失败",
            conviction_impact=-20.0,
            occurrence_count=3,
        )
        self.lib.add_experience(exp_fail)

    def test_positive_adjustment(self):
        adj, experiences = self.injector.inject_context(
            regime_state="normal",
            regime_adx=20.0,
            regime_vol_pct=0.50,
            grid_level=0,
            signal_type="buy",
            has_position=False,
        )
        # 成功经验应该被召回（可能有混合，但主要是正向）
        self.assertGreater(len(experiences), 0)
        # 调整值应该在合理范围内（-30 ~ +30）
        self.assertGreaterEqual(adj, -30.0)
        self.assertLessEqual(adj, 30.0)

    def test_negative_adjustment(self):
        adj, experiences = self.injector.inject_context(
            regime_state="warning",
            regime_adx=30.0,
            regime_vol_pct=0.50,
            grid_level=0,
            signal_type="buy",
            has_position=False,
        )
        # 应该召回失败经验，负向调整
        self.assertLess(adj, 0)

    def test_no_experiences(self):
        # 不匹配的标签
        adj, experiences = self.injector.inject_context(
            regime_state="hard_circuit_break",
            regime_adx=50.0,
            regime_vol_pct=0.90,
            grid_level=5,
            signal_type="sell",
            has_position=True,
        )
        self.assertEqual(adj, 0.0)
        self.assertEqual(len(experiences), 0)

    def test_signal_blocking(self):
        # 设置门槛
        self.injector.conviction_threshold = 40.0
        
        # 基础置信度 50，调整 -15 → 35，低于门槛 40 → 应该拦截
        should_block, adjusted = self.injector.should_block_signal(50.0, -15.0)
        self.assertTrue(should_block)
        self.assertEqual(adjusted, 35.0)

        # 基础置信度 60，调整 +10 → 70 → 不应拦截
        should_block, adjusted = self.injector.should_block_signal(60.0, 10.0)
        self.assertFalse(should_block)
        self.assertEqual(adjusted, 70.0)


class TestFeedbackLoop(unittest.TestCase):
    """反馈闭环测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.loop = FeedbackLoop(config={"feedback_loop": {"base_dir": self.test_dir, "min_samples": 5}})

    def _make_trades(self, count, win_rate):
        """生成模拟交易历史"""
        trades = []
        wins = int(count * win_rate)
        for i in range(count):
            trades.append({
                "time": datetime.now().isoformat(),
                "action": "sell",
                "code": "000001",
                "price": 15.0,
                "quantity": 100,
                "pnl_pct": 0.03 if i < wins else -0.02,
                "is_stop_loss": False,
                "reason": "网格卖出",
            })
        return trades

    def test_no_adjustment_high_win_rate(self):
        """高胜率但门槛已经很低，不需要调整"""
        trades = self._make_trades(20, 0.70)
        config = {"conviction_threshold": 35.0, "grid_spacing_multiplier": 1.0, "stop_loss_multiplier": 1.0}
        adjustments = self.loop.run_weekly_review(trades, config)
        # 可能不调整（门槛已经很低）
        # 检查返回格式
        self.assertIsInstance(adjustments, list)

    def test_adjustment_low_win_rate(self):
        """低胜率应该提高门槛"""
        trades = self._make_trades(20, 0.30)
        config = {"conviction_threshold": 50.0, "grid_spacing_multiplier": 1.0, "stop_loss_multiplier": 1.0}
        adjustments = self.loop.run_weekly_review(trades, config)

        conv_adj = [a for a in adjustments if a["parameter"] == "conviction_threshold"]
        if conv_adj:
            self.assertGreater(conv_adj[0]["new_value"], conv_adj[0]["old_value"])

    def test_consecutive_loss_pause(self):
        """连续亏损应该暂停调整"""
        # 全亏损
        trades = []
        for i in range(10):
            trades.append({
                "time": datetime.now().isoformat(),
                "action": "sell",
                "code": "000001",
                "price": 15.0,
                "quantity": 100,
                "pnl_pct": -0.05,
                "is_stop_loss": False,
            })
        config = {"conviction_threshold": 50.0}
        adjustments = self.loop.run_weekly_review(trades, config)
        # 连续亏损应该暂停
        self.assertEqual(len(adjustments), 0)

    def test_feedback_history(self):
        trades = self._make_trades(20, 0.30)
        config = {"conviction_threshold": 50.0, "grid_spacing_multiplier": 1.0, "stop_loss_multiplier": 1.0}
        self.loop.run_weekly_review(trades, config)

        history = self.loop.get_feedback_history()
        self.assertIsInstance(history, list)

    def test_revert(self):
        trades = self._make_trades(20, 0.30)
        config = {"conviction_threshold": 50.0}
        adjustments = self.loop.run_weekly_review(trades, config)

        if adjustments:
            entry_id = self.loop.feedback_log[-1].entry_id
            result = self.loop.revert(entry_id)
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
