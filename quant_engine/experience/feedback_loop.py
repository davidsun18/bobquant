# -*- coding: utf-8 -*-
"""
feedback_loop.py - 规则自适应反馈闭环

核心思想：让系统自己调整规则，而不是人手动调参。

工作原理：
1. 系统定期（每周日）统计历史交易数据
2. 分析不同参数组合下的胜率表现
3. 根据统计结果自动微调规则参数
4. 所有调整留痕，支持回滚

可自适应的参数：
- 开仓置信度门槛（conviction_threshold）
- 网格间距乘数（grid_spacing_multiplier）
- 止损乘数（stop_loss_multiplier）
- 单股最大仓位（max_position_per_stock）

安全机制：
- 每次调整幅度有限制（步长限制）
- 连续亏损时暂停自动调整
- 所有调整记录在 feedback_log.json
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quant_engine.feedback")


@dataclass
class FeedbackEntry:
    """反馈记录"""
    entry_id: str = ""
    timestamp: str = ""
    parameter: str = ""           # 被调整的参数名
    old_value: float = 0.0
    new_value: float = 0.0
    reason: str = ""              # 调整原因
    supporting_data: dict = field(default_factory=dict)  # 支撑数据
    status: str = "active"        # active / reverted


class FeedbackLoop:
    """
    规则自适应反馈闭环

    用法:
        loop = FeedbackLoop()
        # 每周执行一次
        adjustments = loop.run_weekly_review(trade_history, regime_stats)
    """

    def __init__(self, config: Optional[dict] = None):
        cfg = (config or {}).get("feedback_loop", {})
        self.base_dir = Path(cfg.get("base_dir", "/home/openclaw/.openclaw/workspace/quant_engine/experience"))
        self.feedback_log_file = self.base_dir / "feedback_log.json"
        self.config_file = self.base_dir / "adaptive_config.json"

        # 步长限制（防止一次调太大）
        self.max_step_pct = cfg.get("max_step_pct", 0.10)  # 每次最多调整 10%

        # 最小样本量（样本太少不调整）
        self.min_samples = cfg.get("min_samples", 20)

        # 连续亏损暂停阈值
        self.consecutive_loss_pause = cfg.get("consecutive_loss_pause", 5)

        self.feedback_log: List[FeedbackEntry] = []
        self._adaptive_config = {}
        self._load()

    def _load(self):
        if self.feedback_log_file.exists():
            try:
                with open(self.feedback_log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.feedback_log = [FeedbackEntry(**e) for e in data]
            except Exception as e:
                logger.warning(f"加载反馈日志失败: {e}")

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._adaptive_config = json.load(f)
            except Exception:
                pass

    def _save(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with open(self.feedback_log_file, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self.feedback_log], f, ensure_ascii=False, indent=2)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._adaptive_config, f, ensure_ascii=False, indent=2)

    def run_weekly_review(
        self,
        trade_history: List[dict],
        current_config: dict,
    ) -> List[dict]:
        """
        执行每周规则审查

        Args:
            trade_history: 最近一周的交易记录
            current_config: 当前配置参数

        Returns:
            调整列表（可能为空）
        """
        adjustments = []

        # 检查样本量
        if len(trade_history) < self.min_samples:
            logger.info(f"反馈闭环: 样本量不足 ({len(trade_history)} < {self.min_samples})，跳过调整")
            return adjustments

        # 检查连续亏损
        recent_losses = self._count_consecutive_losses(trade_history)
        if recent_losses >= self.consecutive_loss_pause:
            logger.warning(f"反馈闭环: 连续 {recent_losses} 次亏损，暂停自动调整")
            return adjustments

        # 分析胜率
        overall_stats = self._compute_stats(trade_history)

        # 1. 开仓置信度门槛调整
        adj = self._review_conviction_threshold(trade_history, overall_stats, current_config)
        if adj:
            adjustments.append(adj)

        # 2. 网格间距调整
        adj = self._review_grid_spacing(trade_history, overall_stats, current_config)
        if adj:
            adjustments.append(adj)

        # 3. 止损乘数调整
        adj = self._review_stop_loss(trade_history, overall_stats, current_config)
        if adj:
            adjustments.append(adj)

        if adjustments:
            self._save()
            logger.info(f"反馈闭环: 本周调整 {len(adjustments)} 项参数")
        else:
            logger.info("反馈闭环: 本周无需调整")

        return adjustments

    def _count_consecutive_losses(self, trades: List[dict]) -> int:
        """计算连续亏损次数（从最新的交易往前数）"""
        count = 0
        for trade in reversed(trades):
            if trade.get("pnl_pct", 0) < 0:
                count += 1
            else:
                break
        return count

    def _compute_stats(self, trades: List[dict]) -> dict:
        """计算交易统计"""
        if not trades:
            return {"win_rate": 0, "avg_pnl": 0, "total": 0}

        wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
        total_pnl = sum(t.get("pnl_pct", 0) for t in trades)

        return {
            "win_rate": wins / len(trades),
            "avg_pnl": total_pnl / len(trades),
            "total": len(trades),
        }

    def _review_conviction_threshold(
        self, trades: List[dict], stats: dict, config: dict
    ) -> Optional[dict]:
        """审查开仓置信度门槛"""
        current = config.get("conviction_threshold", 50.0)

        # 如果当前胜率 > 55% 且门槛较高 → 降低门槛
        if stats["win_rate"] > 0.55 and current > 40:
            new_val = current * (1 - self.max_step_pct / 2)
            reason = f"胜率 {stats['win_rate']:.0%} > 55%，降低门槛以增加交易机会"
            return self._record_adjustment(
                "conviction_threshold", current, round(new_val, 1), reason
            )

        # 如果当前胜率 < 45% → 提高门槛
        if stats["win_rate"] < 0.45 and current < 70:
            new_val = current * (1 + self.max_step_pct / 2)
            reason = f"胜率 {stats['win_rate']:.0%} < 45%，提高门槛以过滤低质量信号"
            return self._record_adjustment(
                "conviction_threshold", current, round(new_val, 1), reason
            )

        return None

    def _review_grid_spacing(
        self, trades: List[dict], stats: dict, config: dict
    ) -> Optional[dict]:
        """审查网格间距"""
        current = config.get("grid_spacing_multiplier", 1.0)

        # 如果交易过于频繁且平均亏损 → 增大间距
        if stats["total"] > 50 and stats["avg_pnl"] < -0.01:
            new_val = current * (1 + self.max_step_pct)
            reason = f"交易频繁({stats['total']}笔)且平均亏损，增大网格间距"
            return self._record_adjustment(
                "grid_spacing_multiplier", current, round(new_val, 2), reason
            )

        # 如果很少交易且历史胜率高 → 缩小间距
        if stats["total"] < 10 and stats["win_rate"] > 0.60:
            new_val = current * (1 - self.max_step_pct)
            reason = f"交易过少({stats['total']}笔)且胜率高({stats['win_rate']:.0%})，缩小网格间距"
            return self._record_adjustment(
                "grid_spacing_multiplier", current, round(new_val, 2), reason
            )

        return None

    def _review_stop_loss(
        self, trades: List[dict], stats: dict, config: dict
    ) -> Optional[dict]:
        """审查止损乘数"""
        current = config.get("stop_loss_multiplier", 1.0)

        # 统计被止损的交易
        stopped_trades = [t for t in trades if t.get("is_stop_loss")]
        if not stopped_trades:
            return None

        # 如果被止损的交易后续反弹概率高 → 止损太紧
        stopped_pnl = [t.get("pnl_pct", 0) for t in stopped_trades]
        avg_stop_loss = sum(stopped_pnl) / len(stopped_pnl)

        if avg_stop_loss < -0.10 and current < 1.5:
            # 平均止损亏损 > 10%，可能止损太紧
            new_val = current * (1 + self.max_step_pct / 2)
            reason = f"止损平均亏损 {avg_stop_loss:.0%}，可能止损过紧，放宽止损乘数"
            return self._record_adjustment(
                "stop_loss_multiplier", current, round(new_val, 2), reason
            )

        return None

    def _record_adjustment(
        self, parameter: str, old_value: float, new_value: float, reason: str
    ) -> dict:
        entry = FeedbackEntry(
            entry_id=f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
        self.feedback_log.append(entry)

        # 更新自适应配置
        self._adaptive_config[parameter] = new_value

        logger.info(f"参数调整: {parameter} {old_value} → {new_value} ({reason})")
        return {
            "parameter": parameter,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
        }

    def get_adaptive_config(self) -> dict:
        """获取当前自适应配置"""
        return self._adaptive_config.copy()

    def get_feedback_history(self, limit: int = 50) -> List[dict]:
        """获取反馈历史"""
        return [asdict(e) for e in self.feedback_log[-limit:]]

    def revert(self, entry_id: str) -> bool:
        """回滚某次调整"""
        for entry in self.feedback_log:
            if entry.entry_id == entry_id:
                entry.status = "reverted"
                self._adaptive_config[entry.parameter] = entry.old_value
                self._save()
                logger.info(f"已回滚调整: {entry_id} ({entry.parameter})")
                return True
        return False


# 单例
_default_loop: Optional[FeedbackLoop] = None


def get_feedback_loop(config: Optional[dict] = None) -> FeedbackLoop:
    global _default_loop
    if _default_loop is None:
        _default_loop = FeedbackLoop(config)
    return _default_loop
