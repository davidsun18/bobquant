# -*- coding: utf-8 -*-
"""
权限引擎核心
实现 BobQuant 的权限控制模式，借鉴 Claude Code 的 PermissionMode 设计
"""

import time
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PermissionMode(Enum):
    """
    权限模式 (借鉴 Claude Code)
    
    - acceptEdits: 允许交易 (自动执行)
    - bypassPermissions: 跳过风控 (完全信任模式)
    - default: 默认询问 (需要用户确认)
    - plan: 计划模式 (只规划不执行)
    - auto: AI 分类器 (由 AI 决定是否询问)
    """
    ACCEPT_EDITS = auto()          # 允许交易，自动执行
    BYPASS_PERMISSIONS = auto()    # 跳过风控，完全信任
    DEFAULT = auto()               # 默认询问，需要确认
    PLAN = auto()                  # 计划模式，只规划不执行
    AUTO = auto()                  # AI 分类器，智能决策


@dataclass
class PermissionRequest:
    """权限请求对象"""
    action: str                    # 动作类型：trade, risk_check, cancel, modify
    symbol: str                    # 股票代码
    side: str                      # 买卖方向：buy, sell
    quantity: int                  # 数量
    price: Optional[float] = None  # 价格
    order_type: str = "limit"      # 订单类型：limit, market
    strategy: str = ""             # 策略名称
    risk_level: str = "normal"     # 风险等级：low, normal, high, critical
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PermissionResponse:
    """权限响应对象"""
    granted: bool                  # 是否授权
    mode: PermissionMode           # 使用的权限模式
    reason: str = ""               # 决策原因
    requires_confirmation: bool = False  # 是否需要用户确认
    grace_period_remaining: float = 0.0  # 优雅期剩余时间 (秒)
    denial_count: int = 0          # 拒绝次数
    degraded: bool = False         # 是否已降级


@dataclass
class DenialRecord:
    """拒绝记录"""
    timestamp: float
    request: PermissionRequest
    reason: str


class GracePeriodManager:
    """
    优雅期管理器
    实现 200ms 防误触机制，防止快速连续操作导致的误判
    """
    
    def __init__(self, grace_period_ms: float = 200.0):
        """
        初始化优雅期管理器
        
        Args:
            grace_period_ms: 优雅期时长 (毫秒)，默认 200ms
        """
        self.grace_period_ms = grace_period_ms
        self._last_request_time: Dict[str, float] = {}  # 按 action+symbol 记录
        self._pending_requests: Dict[str, PermissionRequest] = {}
    
    def check_grace_period(self, request: PermissionRequest) -> tuple[bool, float]:
        """
        检查是否在优雅期内
        
        Args:
            request: 权限请求
            
        Returns:
            (in_grace_period, remaining_ms): 是否在优雅期及剩余时间
        """
        key = f"{request.action}:{request.symbol}"
        current_time = time.time() * 1000  # 转换为毫秒
        
        if key in self._last_request_time:
            elapsed = current_time - self._last_request_time[key]
            if elapsed < self.grace_period_ms:
                remaining = self.grace_period_ms - elapsed
                logger.debug(f"优雅期检查：{key} 剩余 {remaining:.2f}ms")
                return True, remaining / 1000.0  # 返回秒数
        
        # 更新最后请求时间
        self._last_request_time[key] = current_time
        return False, 0.0
    
    def clear(self, key: Optional[str] = None):
        """清除优雅期记录"""
        if key:
            self._last_request_time.pop(key, None)
        else:
            self._last_request_time.clear()


class DenialTracker:
    """
    拒绝次数追踪器
    实现降级机制：连续拒绝后自动切换到更严格的模式
    """
    
    def __init__(self, threshold: int = 3, decay_minutes: int = 5):
        """
        初始化拒绝追踪器
        
        Args:
            threshold: 触发降级的拒绝次数阈值
            decay_minutes: 拒绝计数衰减时间 (分钟)
        """
        self.threshold = threshold
        self.decay_minutes = decay_minutes
        self._denial_counts: Dict[str, List[DenialRecord]] = {}
    
    def record_denial(self, key: str, request: PermissionRequest, reason: str):
        """记录一次拒绝"""
        if key not in self._denial_counts:
            self._denial_counts[key] = []
        
        record = DenialRecord(
            timestamp=time.time(),
            request=request,
            reason=reason
        )
        self._denial_counts[key].append(record)
        logger.warning(f"拒绝记录：{key} 原因={reason} 累计={len(self._denial_counts[key])}")
    
    def get_denial_count(self, key: str) -> int:
        """获取当前拒绝次数 (已衰减)"""
        if key not in self._denial_counts:
            return 0
        
        # 清理过期的拒绝记录
        cutoff = time.time() - (self.decay_minutes * 60)
        self._denial_counts[key] = [
            r for r in self._denial_counts[key]
            if r.timestamp > cutoff
        ]
        
        return len(self._denial_counts[key])
    
    def is_degraded(self, key: str) -> bool:
        """检查是否已触发降级"""
        return self.get_denial_count(key) >= self.threshold
    
    def reset(self, key: Optional[str] = None):
        """重置拒绝计数"""
        if key:
            self._denial_counts.pop(key, None)
        else:
            self._denial_counts.clear()


class PermissionEngine:
    """
    权限引擎
    核心权限控制逻辑，整合模式管理、规则匹配、AI 分类、优雅期和降级机制
    """
    
    def __init__(
        self,
        mode: PermissionMode = PermissionMode.DEFAULT,
        grace_period_ms: float = 200.0,
        denial_threshold: int = 3,
        classifier_callback: Optional[Callable] = None
    ):
        """
        初始化权限引擎
        
        Args:
            mode: 默认权限模式
            grace_period_ms: 优雅期时长 (毫秒)
            denial_threshold: 降级阈值
            classifier_callback: AI 分类器回调函数
        """
        self.mode = mode
        self.grace_period_manager = GracePeriodManager(grace_period_ms)
        self.denial_tracker = DenialTracker(threshold=denial_threshold)
        self.classifier_callback = classifier_callback
        
        # 模式描述
        self._mode_descriptions = {
            PermissionMode.ACCEPT_EDITS: "允许交易 - 自动执行",
            PermissionMode.BYPASS_PERMISSIONS: "跳过风控 - 完全信任",
            PermissionMode.DEFAULT: "默认询问 - 需要确认",
            PermissionMode.PLAN: "计划模式 - 只规划不执行",
            PermissionMode.AUTO: "AI 分类 - 智能决策",
        }
        
        logger.info(f"权限引擎初始化：mode={mode.name}")
    
    def set_mode(self, mode: PermissionMode):
        """切换权限模式"""
        self.mode = mode
        logger.info(f"权限模式切换：{mode.name}")
    
    def get_mode_description(self) -> str:
        """获取当前模式描述"""
        return self._mode_descriptions.get(self.mode, "未知模式")
    
    def check_permission(
        self,
        request: PermissionRequest,
        rule_matcher: Optional[Any] = None
    ) -> PermissionResponse:
        """
        检查权限
        
        Args:
            request: 权限请求
            rule_matcher: 规则匹配器 (可选)
            
        Returns:
            PermissionResponse: 权限响应
        """
        key = f"{request.action}:{request.symbol}"
        
        # 1. 检查优雅期
        in_grace, grace_remaining = self.grace_period_manager.check_grace_period(request)
        
        # 2. 检查是否已降级
        is_degraded = self.denial_tracker.is_degraded(key)
        denial_count = self.denial_tracker.get_denial_count(key)
        
        # 3. 根据模式决策
        granted = False
        requires_confirmation = False
        reason = ""
        
        if self.mode == PermissionMode.BYPASS_PERMISSIONS:
            # 跳过风控模式：直接允许
            granted = True
            reason = "跳过风控模式"
            
        elif self.mode == PermissionMode.ACCEPT_EDITS:
            # 允许交易模式：自动执行
            granted = True
            reason = "允许交易模式"
            
        elif self.mode == PermissionMode.PLAN:
            # 计划模式：只规划不执行
            granted = False
            requires_confirmation = False
            reason = "计划模式 - 仅规划"
            
        elif self.mode == PermissionMode.AUTO:
            # AI 分类模式：使用分类器决策
            if self.classifier_callback:
                try:
                    ai_decision = self.classifier_callback(request)
                    granted = ai_decision.get('granted', False)
                    reason = ai_decision.get('reason', 'AI 分类器决策')
                    requires_confirmation = not granted
                except Exception as e:
                    logger.error(f"AI 分类器错误：{e}")
                    granted = False
                    requires_confirmation = True
                    reason = f"AI 分类器异常：{e}"
            else:
                granted = False
                requires_confirmation = True
                reason = "AI 分类器未配置"
                
        else:  # DEFAULT
            # 默认模式：需要确认
            granted = False
            requires_confirmation = True
            reason = "默认模式 - 需要用户确认"
        
        # 4. 规则匹配覆盖 (如果提供了规则匹配器)
        if rule_matcher and request.action == "trade":
            rule_result = rule_matcher.match(request.symbol, request.side)
            if rule_result.get('action') == 'allow':
                granted = True
                reason = f"规则匹配：{rule_result.get('rule', 'unknown')}"
                requires_confirmation = False
            elif rule_result.get('action') == 'deny':
                granted = False
                reason = f"规则拒绝：{rule_result.get('rule', 'unknown')}"
        
        # 5. 降级处理
        if is_degraded and not granted:
            reason += " [已降级 - 连续拒绝]"
        
        # 6. 记录拒绝 (如果拒绝)
        if not granted and requires_confirmation:
            self.denial_tracker.record_denial(key, request, reason)
        
        return PermissionResponse(
            granted=granted,
            mode=self.mode,
            reason=reason,
            requires_confirmation=requires_confirmation,
            grace_period_remaining=grace_remaining,
            denial_count=denial_count,
            degraded=is_degraded
        )
    
    def confirm_permission(self, request: PermissionRequest, confirmed: bool):
        """
        用户确认权限
        
        Args:
            request: 权限请求
            confirmed: 是否确认
        """
        key = f"{request.action}:{request.symbol}"
        
        if confirmed:
            # 确认成功，重置拒绝计数
            self.denial_tracker.reset(key)
            logger.info(f"权限确认：{key} 已确认")
        else:
            # 用户拒绝，记录拒绝
            self.denial_tracker.record_denial(key, request, "用户拒绝")
            logger.warning(f"权限拒绝：{key} 用户拒绝")
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            'mode': self.mode.name,
            'mode_description': self.get_mode_description(),
            'grace_period_ms': self.grace_period_manager.grace_period_ms,
            'denial_threshold': self.denial_tracker.threshold,
        }
