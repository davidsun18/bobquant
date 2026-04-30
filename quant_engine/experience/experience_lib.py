# -*- coding: utf-8 -*-
"""
experience_lib.py - BobQuant 经验库

核心思想：让系统像交易员一样从历史中积累和调用经验。

三层结构：
1. DecisionSnapshot - 每次决策时记录完整上下文
2. ExperienceEntry - 事后复盘提炼的经验（带标签）
3. ExperienceLibrary - 存储、检索、管理经验的中央库

检索逻辑：基于标签相似度（市场状态、RSI区间、波动率区间等）
召回 Top-K 条相关经验，注入到下一次信号生成的上下文中。
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quant_engine.experience")

# ==================== 数据结构 ====================


class DecisionOutcome(Enum):
    """决策结果"""
    PENDING = "pending"       # 待验证
    WIN = "win"               # 盈利/判断正确
    LOSS = "loss"             # 亏损/判断错误
    BREAK_EVEN = "break_even" # 平手
    STOPPED_OUT = "stopped_out"  # 止损出场


class LessonType(Enum):
    """经验类型"""
    SUCCESS_PATTERN = "success_pattern"   # 成功模式（应该复制）
    FAILURE_PATTERN = "failure_pattern"   # 失败模式（应该避免）
    WARNING = "warning"                   # 风险提示
    RULE_ADJUSTMENT = "rule_adjustment"   # 规则调整建议


@dataclass
class DecisionSnapshot:
    """
    决策快照 —— 每次信号生成时自动记录

    记录"当时看到了什么、为什么这么做、预测了什么"
    类似交易员的工作日记。
    """
    # 决策元信息
    decision_id: str = ""
    timestamp: str = ""
    code: str = ""
    name: str = ""
    direction: str = ""           # buy / sell

    # 市场状态
    regime_state: str = ""        # normal / warning / soft_circuit_break / hard_circuit_break
    regime_adx: float = 0.0
    regime_vol_percentile: float = 0.0

    # 技术指标快照
    price: float = 0.0
    atr_20: float = 0.0
    volatility_60d: float = 0.0
    pnl_at_decision: float = 0.0  # 当时持仓盈亏%（如有）

    # 网格信息
    grid_level: int = 0
    grid_spacing: float = 1.0

    # 决策理由
    reason: str = ""

    # 预测
    predicted_direction: str = ""  # up / down / sideways
    target_price: float = 0.0

    # 结果（事后填充）
    outcome: str = "pending"
    outcome_reviewed_at: str = ""
    actual_return: float = 0.0

    # 风控状态
    global_breaker: bool = False
    single_stock_breakers: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionSnapshot":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExperienceEntry:
    """
    经验条目 —— 从历史决策中提炼出的可复用知识

    带标签系统，支持按场景相似度检索。
    """
    experience_id: str = ""
    created_at: str = ""
    source_decision_id: str = ""  # 来源于哪条决策

    # 场景标签（用于相似度匹配）
    tags: Dict[str, str] = field(default_factory=dict)
    """
    示例标签：
    {
        "regime": "normal",
        "adx_range": "low",          # low (<25), medium (25-35), high (>35)
        "vol_range": "normal",       # low, normal, high
        "grid_level": "entry",       # entry, grid_1, grid_2+
        "position_type": "new_open", # new_open, add_position
        "signal_type": "grid_buy",   # grid_buy, grid_sell, stop_loss
    }
    """

    # 经验内容
    lesson_type: str = "success_pattern"  # success_pattern / failure_pattern / warning / rule_adjustment
    summary: str = ""                     # 一句话总结
    detail: str = ""                      # 详细说明
    conviction_impact: float = 0.0        # 对置信度的影响（-30 ~ +30）

    # 统计信息
    occurrence_count: int = 1             # 类似场景出现次数
    success_rate: float = 0.0             # 类似场景成功率
    last_seen: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExperienceEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== 经验库 ====================


class ExperienceLibrary:
    """
    经验库 —— 存储、检索、管理所有经验

    存储格式：
    - snapshots/<date>.jsonl  — 决策快照（按日期分文件）
    - experiences.json         — 经验条目（主库）
    - stats.json               — 统计信息
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            "/home/openclaw/.openclaw/workspace/quant_engine/experience"
        )
        self.snapshots_dir = self.base_dir / "snapshots"
        self.experiences_file = self.base_dir / "experiences.json"
        self.stats_file = self.base_dir / "stats.json"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(exist_ok=True)

        self._experiences: List[ExperienceEntry] = []
        self._stats = {
            "total_decisions": 0,
            "total_experiences": 0,
            "win_count": 0,
            "loss_count": 0,
            "break_even_count": 0,
            "overall_win_rate": 0.0,
            "last_updated": "",
        }
        self._load()

    def _load(self):
        """加载经验库"""
        if self.experiences_file.exists():
            try:
                with open(self.experiences_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._experiences = [ExperienceEntry.from_dict(e) for e in data]
                logger.info(f"经验库已加载: {len(self._experiences)} 条经验")
            except Exception as e:
                logger.error(f"加载经验库失败: {e}")

        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    self._stats = json.load(f)
            except Exception:
                pass

    def _save_experiences(self):
        with open(self.experiences_file, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._experiences], f, ensure_ascii=False, indent=2)

    def _save_stats(self):
        self._stats["total_experiences"] = len(self._experiences)
        self._stats["last_updated"] = datetime.now().isoformat()
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self._stats, f, ensure_ascii=False, indent=2)

    # ==================== 决策快照 ====================

    def save_snapshot(self, snapshot: DecisionSnapshot):
        """保存决策快照到当日文件"""
        if not snapshot.decision_id:
            snapshot.decision_id = f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{snapshot.code}"
        if not snapshot.timestamp:
            snapshot.timestamp = datetime.now().isoformat()

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.snapshots_dir / f"{date_str}.jsonl"

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")

        self._stats["total_decisions"] += 1
        self._save_stats()
        logger.debug(f"决策快照已保存: {snapshot.decision_id} ({snapshot.code} {snapshot.direction})")

    def load_snapshots(self, date: Optional[str] = None) -> List[DecisionSnapshot]:
        """加载指定日期的决策快照（默认今天）"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        filepath = self.snapshots_dir / f"{date}.jsonl"
        if not filepath.exists():
            return []

        snapshots = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        snapshots.append(DecisionSnapshot.from_dict(json.loads(line)))
                    except Exception as e:
                        logger.warning(f"解析快照失败: {e}")
        return snapshots

    def load_all_snapshots(self, limit: int = 1000) -> List[DecisionSnapshot]:
        """加载所有历史快照（按时间倒序）"""
        all_snapshots = []
        for filepath in sorted(self.snapshots_dir.glob("*.jsonl"), reverse=True):
            for snap in self.load_snapshots(filepath.stem):
                all_snapshots.append(snap)
                if len(all_snapshots) >= limit:
                    return all_snapshots
        return all_snapshots

    # ==================== 经验条目 ====================

    def add_experience(self, entry: ExperienceEntry):
        """添加新的经验条目"""
        if not entry.experience_id:
            entry.experience_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not entry.created_at:
            entry.created_at = datetime.now().isoformat()
        if not entry.last_seen:
            entry.last_seen = datetime.now().isoformat()

        # 检查是否已有类似经验（标签匹配），有则合并
        existing = self._find_similar(entry.tags)
        if existing:
            existing.occurrence_count += 1
            existing.last_seen = entry.last_seen
            # 更新成功率
            total = existing.occurrence_count
            existing.success_rate = (
                (existing.success_rate * (total - 1) + (1.0 if entry.lesson_type == "success_pattern" else 0.0))
                / total
            )
            logger.info(f"经验已合并: {existing.experience_id} (出现{existing.occurrence_count}次)")
        else:
            self._experiences.append(entry)
            logger.info(f"新经验已添加: {entry.experience_id} - {entry.summary}")

        self._save_experiences()
        self._save_stats()

    def _find_similar(self, tags: Dict[str, str]) -> Optional[ExperienceEntry]:
        """查找标签匹配的经验"""
        for exp in self._experiences:
            match_count = sum(1 for k, v in tags.items() if exp.tags.get(k) == v)
            if match_count >= 2:  # 至少2个标签匹配视为相似
                return exp
        return None

    def retrieve(self, context_tags: Dict[str, str], top_k: int = 5) -> List[ExperienceEntry]:
        """
        根据当前场景标签检索最相关的经验

        这是"成长"的核心：带着历史经验做新决策。
        """
        scored = []
        for exp in self._experiences:
            # 计算相似度：匹配的标签数 * 经验权重
            match_count = sum(1 for k, v in context_tags.items() if exp.tags.get(k) == v)
            if match_count == 0:
                continue

            # 权重：出现次数越多、最近越活跃的权重越高
            recency_weight = 1.0
            if exp.last_seen:
                try:
                    last = datetime.fromisoformat(exp.last_seen)
                    days_ago = (datetime.now() - last).days
                    recency_weight = max(0.3, 1.0 - days_ago / 365)  # 一年内衰减
                except Exception:
                    pass

            score = match_count * recency_weight * min(exp.occurrence_count, 5)
            scored.append((score, exp))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [exp for _, exp in scored[:top_k]]

    def get_stats(self) -> dict:
        self._save_stats()
        return self._stats.copy()

    # ==================== 复盘 ====================

    def update_snapshot_outcome(self, decision_id: str, outcome: str,
                                 actual_return: float, detail: str = "") -> bool:
        """更新决策快照的结果"""
        # 找到对应快照文件并更新
        for filepath in sorted(self.snapshots_dir.glob("*.jsonl"), reverse=True):
            updated = False
            lines = []
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("decision_id") == decision_id:
                            data["outcome"] = outcome
                            data["actual_return"] = actual_return
                            data["outcome_reviewed_at"] = datetime.now().isoformat()
                            data["review_detail"] = detail
                            updated = True

                            # 更新统计
                            if outcome == DecisionOutcome.WIN.value:
                                self._stats["win_count"] += 1
                            elif outcome == DecisionOutcome.LOSS.value:
                                self._stats["loss_count"] += 1
                            elif outcome == DecisionOutcome.BREAK_EVEN.value:
                                self._stats["break_even_count"] += 1

                        lines.append(json.dumps(data, ensure_ascii=False))
                    except Exception:
                        lines.append(line)

            if updated:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                self._save_stats()
                return True

        return False

    # ==================== 场景标签生成 ====================

    @staticmethod
    def generate_tags(regime_state: str, regime_adx: float, regime_vol_pct: float,
                      grid_level: int, signal_type: str, has_position: bool) -> Dict[str, str]:
        """
        根据当前场景自动生成经验标签

        这是让经验"可检索"的关键——用标准化的标签描述场景。
        """
        tags = {}

        # 市场状态
        tags["regime"] = regime_state

        # ADX 区间
        if regime_adx < 25:
            tags["adx_range"] = "low"
        elif regime_adx < 35:
            tags["adx_range"] = "medium"
        else:
            tags["adx_range"] = "high"

        # 波动率区间
        if regime_vol_pct < 0.30:
            tags["vol_range"] = "low"
        elif regime_vol_pct < 0.70:
            tags["vol_range"] = "normal"
        else:
            tags["vol_range"] = "high"

        # 网格层级
        if grid_level == 0:
            tags["grid_level"] = "entry"
        elif grid_level <= 2:
            tags["grid_level"] = "grid_early"
        else:
            tags["grid_level"] = "grid_deep"

        # 仓位类型
        tags["position_type"] = "new_open" if not has_position else "add_position"

        # 信号类型
        tags["signal_type"] = signal_type

        return tags


# 单例
_default_lib: Optional[ExperienceLibrary] = None


def get_experience_lib() -> ExperienceLibrary:
    global _default_lib
    if _default_lib is None:
        _default_lib = ExperienceLibrary()
    return _default_lib
