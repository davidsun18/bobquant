# -*- coding: utf-8 -*-
"""
review_agent.py - 自动复盘 Agent

核心职责：
1. 定期检查历史决策快照，评估结果（赢/亏/平）
2. 对失败的决策进行深度分析，提炼经验教训
3. 对成功的决策提取成功模式
4. 生成经验条目并归档到经验库

复盘逻辑：
- 每个决策快照在创建后 N 小时自动回访
- 对比"预测方向"和"实际走势"
- 分析"为什么对"或"为什么错"
- 生成带标签的经验条目

不需要大模型：基于规则+统计的自动复盘。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .experience_lib import (
    DecisionOutcome,
    DecisionSnapshot,
    ExperienceEntry,
    ExperienceLibrary,
    LessonType,
    get_experience_lib,
)

logger = logging.getLogger("quant_engine.review")


class ReviewAgent:
    """
    自动复盘 Agent

    用法:
        agent = ReviewAgent()
        agent.run_review()  # 执行一次复盘
    """

    def __init__(self, review_hours: int = 24):
        """
        Args:
            review_hours: 决策后多少小时进行复盘（默认24小时）
        """
        self.review_hours = review_hours
        self.lib = get_experience_lib()

    def run_review(self, market_prices: Optional[Dict[str, float]] = None) -> dict:
        """
        执行完整复盘流程

        Args:
            market_prices: 当前市场价格 {code: price}，用于计算实际收益

        Returns:
            {
                "reviewed_count": int,
                "win_count": int,
                "loss_count": int,
                "experiences_added": int,
                "experiences": List[ExperienceEntry],
            }
        """
        market_prices = market_prices or {}
        result = {
            "reviewed_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "break_even_count": 0,
            "experiences_added": 0,
            "experiences": [],
        }

        # 1. 找出需要复盘的快照
        pending = self._find_pending_reviews()
        if not pending:
            logger.info("复盘: 没有待处理的决策快照")
            return result

        logger.info(f"复盘: 找到 {len(pending)} 个待复盘的决策")

        # 2. 逐个评估
        for snapshot in pending:
            outcome, actual_return = self._evaluate_decision(snapshot, market_prices)
            detail = self._generate_review_detail(snapshot, outcome, actual_return)

            # 更新快照结果
            self.lib.update_snapshot_outcome(
                snapshot.decision_id, outcome.value, actual_return, detail
            )
            result["reviewed_count"] += 1

            if outcome == DecisionOutcome.WIN:
                result["win_count"] += 1
            elif outcome == DecisionOutcome.LOSS:
                result["loss_count"] += 1
            elif outcome == DecisionOutcome.BREAK_EVEN:
                result["break_even_count"] += 1

            # 3. 生成经验条目
            experience = self._generate_experience(snapshot, outcome, actual_return, detail)
            if experience:
                self.lib.add_experience(experience)
                result["experiences_added"] += 1
                result["experiences"].append(experience)

        logger.info(
            f"复盘完成: {result['reviewed_count']} 个决策, "
            f"赢 {result['win_count']}, 亏 {result['loss_count']}, "
            f"新增 {result['experiences_added']} 条经验"
        )
        return result

    def _find_pending_reviews(self) -> List[DecisionSnapshot]:
        """查找需要复盘的决策快照"""
        cutoff = datetime.now() - timedelta(hours=self.review_hours)
        pending = []

        # 扫描所有快照文件
        snapshots_dir = self.lib.snapshots_dir
        if not snapshots_dir.exists():
            return []

        for filepath in sorted(snapshots_dir.glob("*.jsonl")):
            snaps = self.lib.load_snapshots(filepath.stem)
            for snap in snaps:
                if snap.outcome == DecisionOutcome.PENDING.value:
                    # 检查是否超过复盘时间
                    try:
                        decision_time = datetime.fromisoformat(snap.timestamp)
                        if decision_time <= cutoff:
                            pending.append(snap)
                    except Exception:
                        pending.append(snap)  # 时间解析失败也加入

        return pending

    def _evaluate_decision(
        self, snapshot: DecisionSnapshot, market_prices: Dict[str, float]
    ) -> Tuple[DecisionOutcome, float]:
        """
        评估一个决策的结果

        Returns:
            (outcome, actual_return)
        """
        code = snapshot.code
        decision_price = snapshot.price

        # 获取当前价格
        current_price = market_prices.get(code, 0)
        if current_price <= 0:
            # 无法获取价格，跳过
            return DecisionOutcome.PENDING, 0.0

        # 计算实际收益率
        if snapshot.direction == "buy":
            actual_return = (current_price - decision_price) / decision_price
        elif snapshot.direction == "sell":
            # 卖出决策：看是否避免了进一步亏损
            actual_return = (decision_price - current_price) / decision_price
        else:
            actual_return = 0.0

        # 判断结果
        threshold = 0.01  # 1% 作为盈亏阈值
        if actual_return > threshold:
            return DecisionOutcome.WIN, actual_return
        elif actual_return < -threshold:
            return DecisionOutcome.LOSS, actual_return
        else:
            return DecisionOutcome.BREAK_EVEN, actual_return

    def _generate_review_detail(
        self, snapshot: DecisionSnapshot, outcome: DecisionOutcome, actual_return: float
    ) -> str:
        """生成复盘详情文本"""
        direction_label = "买入" if snapshot.direction == "buy" else "卖出"

        lines = [
            f"决策: {snapshot.code} {direction_label} @ {snapshot.price:.2f}",
            f"市场状态: {snapshot.regime_state} (ADX={snapshot.regime_adx:.1f}, 波动率分位={snapshot.regime_vol_percentile:.0%})",
            f"网格层级: {snapshot.grid_level}, 信号理由: {snapshot.reason}",
            f"实际收益: {actual_return:+.2%}",
        ]

        if outcome == DecisionOutcome.WIN:
            lines.append("结论: 判断正确，信号有效")
        elif outcome == DecisionOutcome.LOSS:
            lines.append("结论: 判断错误，需要复盘原因")
            lines.append("可能原因分析:")
            if snapshot.regime_state in ("warning", "soft_circuit_break"):
                lines.append("  - 市场状态偏脆弱，逆势操作风险高")
            if snapshot.volatility_60d > 0.40:
                lines.append("  - 高波动环境，价格噪音大")
            if snapshot.grid_level > 2:
                lines.append("  - 网格层级较深，可能趋势已反转")
        else:
            lines.append("结论: 基本持平，信号中性")

        return " | ".join(lines)

    def _generate_experience(
        self, snapshot: DecisionSnapshot, outcome: DecisionOutcome,
        actual_return: float, detail: str
    ) -> Optional[ExperienceEntry]:
        """
        从复盘中生成经验条目

        关键：带标签，便于后续检索。
        """
        # 生成场景标签
        tags = ExperienceLibrary.generate_tags(
            regime_state=snapshot.regime_state,
            regime_adx=snapshot.regime_adx,
            regime_vol_pct=snapshot.regime_vol_percentile,
            grid_level=snapshot.grid_level,
            signal_type=snapshot.direction,
            has_position=snapshot.pnl_at_decision != 0,
        )

        # 根据结果生成经验
        if outcome == DecisionOutcome.WIN:
            lesson_type = LessonType.SUCCESS_PATTERN.value
            summary = f"{snapshot.code} 在 {snapshot.regime_state} 市场下 {snapshot.direction} 成功 (收益 {actual_return:+.2%})"
            conviction_impact = min(15, abs(actual_return) * 100)  # 正向影响
        elif outcome == DecisionOutcome.LOSS:
            lesson_type = LessonType.FAILURE_PATTERN.value
            summary = f"{snapshot.code} 在 {snapshot.regime_state} 市场下 {snapshot.direction} 失败 (亏损 {actual_return:+.2%})"
            conviction_impact = -min(20, abs(actual_return) * 100)  # 负向影响
        else:
            # 平手不生成经验
            return None

        return ExperienceEntry(
            source_decision_id=snapshot.decision_id,
            lesson_type=lesson_type,
            tags=tags,
            summary=summary,
            detail=detail,
            conviction_impact=round(conviction_impact, 1),
        )


# 单例
_default_reviewer: Optional[ReviewAgent] = None


def get_review_agent(review_hours: int = 24) -> ReviewAgent:
    global _default_reviewer
    if _default_reviewer is None:
        _default_reviewer = ReviewAgent(review_hours)
    return _default_reviewer
