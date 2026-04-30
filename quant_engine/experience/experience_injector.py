# -*- coding: utf-8 -*-
"""
experience_injector.py - 经验注入器

在信号生成时，自动从经验库召回相关历史经验，
将经验转化为对信号置信度的调整。

核心逻辑：
1. 根据当前市场状态、技术指标生成场景标签
2. 从经验库检索 Top-K 条相关经验
3. 将经验转化为 conviction_adjustment（置信度调整）
4. 如果调整后的置信度低于门槛，拦截信号

这不是大模型推理，而是基于历史统计的规则调整。
"""

import logging
from typing import Dict, List, Optional, Tuple

from .experience_lib import ExperienceEntry, ExperienceLibrary, get_experience_lib

logger = logging.getLogger("quant_engine.injector")


class ExperienceInjector:
    """
    经验注入器

    用法:
        injector = ExperienceInjector()
        adjustment, experiences = injector.inject_context(
            regime_state="normal",
            regime_adx=20.0,
            regime_vol_pct=0.50,
            grid_level=0,
            signal_type="buy",
            has_position=False,
        )
        # adjustment 可能是 +5.0（经验支持）或 -15.0（经验反对）
    """

    def __init__(self, top_k: int = 5, conviction_threshold: float = 30.0):
        """
        Args:
            top_k: 召回的经验条数
            conviction_threshold: 信号置信度门槛（经验调整前）
        """
        self.top_k = top_k
        self.conviction_threshold = conviction_threshold
        self.lib = get_experience_lib()

    def inject_context(
        self,
        regime_state: str,
        regime_adx: float,
        regime_vol_pct: float,
        grid_level: int,
        signal_type: str,
        has_position: bool,
    ) -> Tuple[float, List[ExperienceEntry]]:
        """
        注入经验上下文

        Returns:
            (conviction_adjustment, related_experiences)
            conviction_adjustment: 对置信度的调整值（-30 ~ +30）
            related_experiences: 召回的相关经验列表
        """
        # 生成场景标签
        context_tags = ExperienceLibrary.generate_tags(
            regime_state=regime_state,
            regime_adx=regime_adx,
            regime_vol_pct=regime_vol_pct,
            grid_level=grid_level,
            signal_type=signal_type,
            has_position=has_position,
        )

        # 召回相关经验
        experiences = self.lib.retrieve(context_tags, self.top_k)
        if not experiences:
            logger.debug("经验注入: 未找到相关历史经验")
            return 0.0, []

        # 计算调整值
        adjustment = self._compute_adjustment(experiences)

        logger.info(
            f"经验注入: {len(experiences)} 条相关经验, "
            f"置信度调整 {adjustment:+.1f}"
        )

        return adjustment, experiences

    def _compute_adjustment(self, experiences: List[ExperienceEntry]) -> float:
        """
        根据召回的经验计算置信度调整

        加权逻辑：
        - 成功经验 → 正向调整
        - 失败经验 → 负向调整
        - 调整幅度 = 经验自身 conviction_impact × 出现次数权重
        """
        total_adjustment = 0.0
        total_weight = 0.0

        for exp in experiences:
            # 出现次数越多，权重越高（上限 3 倍）
            weight = min(exp.occurrence_count, 3)
            total_adjustment += exp.conviction_impact * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        # 平均调整值，限制在 ±30
        avg = total_adjustment / total_weight
        return max(-30.0, min(30.0, avg))

    def should_block_signal(
        self, base_conviction: float, adjustment: float
    ) -> Tuple[bool, float]:
        """
        判断信号是否应该被拦截

        Args:
            base_conviction: 信号原始置信度（0-100）
            adjustment: 经验调整值

        Returns:
            (should_block, adjusted_conviction)
        """
        adjusted = base_conviction + adjustment
        should_block = adjusted < self.conviction_threshold
        return should_block, round(adjusted, 1)

    def get_context_summary(self, experiences: List[ExperienceEntry]) -> str:
        """
        生成经验上下文的摘要文本（用于日志或 LLM 注入）

        示例输出：
        "历史经验参考：
         1. [成功] BTC 正常市场下买入成功（+3.2%）
         2. [失败] ETH 预警市场下买入失败（-2.1%）— 忽略高波动信号
         3. [成功] BTC 正常市场下买入成功（+1.8%）"
        """
        if not experiences:
            return "无相关历史经验"

        lines = ["历史经验参考："]
        for i, exp in enumerate(experiences, 1):
            tag = "[成功]" if exp.lesson_type == "success_pattern" else "[失败]"
            lines.append(f"  {i}. {tag} {exp.summary}")
        return "\n".join(lines)


# 单例
_default_injector: Optional[ExperienceInjector] = None


def get_experience_injector(**kwargs) -> ExperienceInjector:
    global _default_injector
    if _default_injector is None:
        _default_injector = ExperienceInjector(**kwargs)
    return _default_injector
