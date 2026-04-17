# -*- coding: utf-8 -*-
"""
BobQuant 错误分类器 v1.0

功能：
1. 自动分类错误（基于错误类型、消息内容、上下文）
2. 确定错误严重程度
3. 判断是否可自动恢复
4. 提供处理建议

设计灵感来自 Claude Code 的错误分类系统
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from .types import (
    BobQuantError,
    ErrorCategory,
    ErrorSeverity,
    # 具体错误类型
    APIError,
    NetworkError,
    TimeoutError,
    RateLimitError,
    AuthenticationError,
    DataError,
    DataNotFoundError,
    DataFormatError,
    DataValidationError,
    DataStaleError,
    TradingError,
    OrderError,
    OrderRejectedError,
    InsufficientFundsError,
    PositionError,
    MarketClosedError,
    StrategyError,
    SignalError,
    ConfigurationError,
    BacktestError,
    SystemError,
    FileSystemError,
    DatabaseError,
    MemoryError,
    ExternalServiceError,
    ThirdPartyAPIError,
)


@dataclass
class ClassificationRule:
    """分类规则"""
    pattern: str  # 正则表达式或关键词
    error_type: type  # 目标错误类型
    category: ErrorCategory
    severity: ErrorSeverity
    recoverable: bool
    suggestion: str
    priority: int = 0  # 优先级，越高越先匹配


@dataclass
class ClassifiedError:
    """已分类的错误"""
    original_error: Exception
    classified_error: BobQuantError
    category: ErrorCategory
    severity: ErrorSeverity
    recoverable: bool
    confidence: float  # 分类置信度 (0-1)
    matched_rule: Optional[ClassificationRule] = None
    handling_strategy: Optional[str] = None


class ErrorClassifier:
    """
    错误分类器
    
    使用规则匹配和启发式方法将原始异常分类为标准化错误
    """
    
    def __init__(self):
        self.rules: List[ClassificationRule] = []
        self._build_default_rules()
    
    def _build_default_rules(self):
        """构建默认分类规则"""
        
        # ========== 网络错误 ==========
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(connection\s*(refused|reset|timed\s*out)|network\s*unreachable|no\s*route\s*to\s*host)",
            error_type=NetworkError,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            suggestion="检查网络连接和防火墙设置",
            priority=10
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(time[-_]?out|timeout|timed?\s*out)",
            error_type=TimeoutError,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion="增加超时时间或检查网络速度",
            priority=10
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(rate\s*limit|too\s*many\s*requests|429|throttl)",
            error_type=RateLimitError,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion="等待一段时间后重试",
            priority=10
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(auth|unauthorized|401|403|invalid\s*(token|key|credential)|permission\s*denied)",
            error_type=AuthenticationError,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            suggestion="检查 API 密钥或重新登录",
            priority=10
        ))
        
        # ========== 数据错误 ==========
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(no\s*data|data\s*not\s*found|empty\s*response|404)",
            error_type=DataNotFoundError,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,
            suggestion="检查股票代码是否正确或数据源是否支持",
            priority=9
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(invalid\s*(format|type|value)|malformed|parse\s*error|decode\s*error)",
            error_type=DataFormatError,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            suggestion="检查数据源格式或联系数据提供商",
            priority=9
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(validation|validate|invalid\s*(input|parameter|argument))",
            error_type=DataValidationError,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            suggestion="检查输入参数",
            priority=9
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(stale|outdated|expired|old\s*data|cache\s*miss)",
            error_type=DataStaleError,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion="刷新数据后重试",
            priority=8
        ))
        
        # ========== 交易错误 ==========
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(insufficient\s*(funds|balance|money)|not\s*enough\s*(cash|capital))",
            error_type=InsufficientFundsError,
            category=ErrorCategory.TRADING,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            suggestion="减少交易数量或充值",
            priority=10
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(order\s*(reject|denied|failed)|rejected|denied)",
            error_type=OrderRejectedError,
            category=ErrorCategory.TRADING,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            suggestion="检查订单参数或联系券商",
            priority=10
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(market\s*(closed|halt|suspend)|trading\s*halt|not\s*trading)",
            error_type=MarketClosedError,
            category=ErrorCategory.TRADING,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion="等待市场开盘后重试",
            priority=9
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(position|holdings?|inventory)",
            error_type=PositionError,
            category=ErrorCategory.TRADING,
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,
            suggestion="检查持仓状态",
            priority=7
        ))
        
        # ========== 策略错误 ==========
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(signal|indicator|strategy\s*error)",
            error_type=SignalError,
            category=ErrorCategory.STRATEGY,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion="检查策略配置和输入数据",
            priority=8
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(config|configuration|setting|invalid\s*parameter)",
            error_type=ConfigurationError,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            suggestion="检查配置文件或环境变量",
            priority=8
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(backtest|back[-_]?test|simulation)",
            error_type=BacktestError,
            category=ErrorCategory.STRATEGY,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            suggestion="检查回测参数和数据完整性",
            priority=7
        ))
        
        # ========== 系统错误 ==========
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(file\s*(not\s*found|system|error|access|permission)|[Nn]o\s*suc?h\s*file|I/O)",
            error_type=FileSystemError,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            suggestion="检查文件权限和磁盘空间",
            priority=9
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(database|db|sqlite|mysql|postgres|mongo|redis)",
            error_type=DatabaseError,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            suggestion="检查数据库连接和状态",
            priority=9
        ))
        
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(memory|ram|oom|out\s*of\s*memory)",
            error_type=MemoryError,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            suggestion="关闭其他程序或增加内存",
            priority=10
        ))
        
        # ========== 外部服务错误 ==========
        self.rules.append(ClassificationRule(
            pattern=r"(?i)(api|service|external|third[-_]?party|provider)",
            error_type=ThirdPartyAPIError,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            suggestion="检查第三方服务状态或稍后重试",
            priority=6
        ))
        
        # ========== 默认规则 ==========
        self.rules.append(ClassificationRule(
            pattern=r".*",  # 匹配所有
            error_type=APIError,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion="稍后重试",
            priority=0
        ))
        
        # 按优先级排序
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def classify(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ClassifiedError:
        """
        分类单个错误
        
        Args:
            error: 原始异常
            context: 上下文信息
        
        Returns:
            ClassifiedError: 已分类的错误
        """
        # 如果已经是 BobQuantError，直接包装
        if isinstance(error, BobQuantError):
            return ClassifiedError(
                original_error=error,
                classified_error=error,
                category=error.category,
                severity=error.severity,
                recoverable=error.recoverable,
                confidence=1.0,
                handling_strategy=self._determine_handling_strategy(error)
            )
        
        # 尝试匹配规则
        error_message = str(error)
        error_type_name = type(error).__name__
        combined_text = f"{error_message} {error_type_name}"
        
        matched_rule = None
        confidence = 0.0
        
        for rule in self.rules:
            if re.search(rule.pattern, combined_text):
                matched_rule = rule
                confidence = self._calculate_confidence(rule, error)
                break
        
        # 创建标准化错误
        if matched_rule:
            classified_error = matched_rule.error_type(
                message=error_message,
                original_error=error,
                context=context
            )
        else:
            # 默认错误
            classified_error = BobQuantError(
                message=error_message,
                original_error=error,
                context=context
            )
        
        return ClassifiedError(
            original_error=error,
            classified_error=classified_error,
            category=classified_error.category,
            severity=classified_error.severity,
            recoverable=classified_error.recoverable,
            confidence=confidence,
            matched_rule=matched_rule,
            handling_strategy=self._determine_handling_strategy(classified_error)
        )
    
    def _calculate_confidence(
        self,
        rule: ClassificationRule,
        error: Exception
    ) -> float:
        """
        计算分类置信度
        
        Args:
            rule: 匹配的规则
            error: 原始异常
        
        Returns:
            float: 置信度 (0-1)
        """
        confidence = 0.5  # 基础置信度
        
        # 优先级越高，置信度越高
        confidence += min(rule.priority / 20.0, 0.3)
        
        # 错误类型名称匹配，增加置信度
        if rule.error_type.__name__.lower() in type(error).__name__.lower():
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _determine_handling_strategy(
        self,
        error: BobQuantError
    ) -> Optional[str]:
        """
        确定错误处理策略
        
        Args:
            error: 标准化错误
        
        Returns:
            str: 处理策略名称
        """
        if not error.recoverable:
            return "manual_intervention"
        
        if error.severity == ErrorSeverity.CRITICAL:
            return "immediate_alert"
        
        if isinstance(error, (RateLimitError, TimeoutError)):
            return "retry_with_backoff"
        
        if isinstance(error, (NetworkError, DataStaleError)):
            return "retry_immediately"
        
        if isinstance(error, (MarketClosedError,)):
            return "wait_and_retry"
        
        if isinstance(error, (AuthenticationError, ConfigurationError)):
            return "reconfigure"
        
        return "retry_with_backoff"
    
    def classify_batch(
        self,
        errors: List[Exception],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ClassifiedError]:
        """
        批量分类错误
        
        Args:
            errors: 错误列表
            context: 上下文信息
        
        Returns:
            List[ClassifiedError]: 已分类的错误列表
        """
        return [self.classify(error, context) for error in errors]
    
    def get_category_summary(
        self,
        classified_errors: List[ClassifiedError]
    ) -> Dict[str, Any]:
        """
        获取错误分类摘要
        
        Args:
            classified_errors: 已分类的错误列表
        
        Returns:
            dict: 分类摘要
        """
        summary = {
            "total": len(classified_errors),
            "by_category": {},
            "by_severity": {},
            "recoverable_count": 0,
            "non_recoverable_count": 0,
        }
        
        for ce in classified_errors:
            # 按分类统计
            cat = ce.category.value
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1
            
            # 按严重程度统计
            sev = ce.severity.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
            
            # 可恢复性统计
            if ce.recoverable:
                summary["recoverable_count"] += 1
            else:
                summary["non_recoverable_count"] += 1
        
        return summary
    
    def add_rule(
        self,
        pattern: str,
        error_type: type,
        category: ErrorCategory,
        severity: ErrorSeverity,
        recoverable: bool,
        suggestion: str,
        priority: int = 5
    ):
        """
        添加自定义分类规则
        
        Args:
            pattern: 正则表达式
            error_type: 错误类型
            category: 错误分类
            severity: 严重程度
            recoverable: 是否可恢复
            suggestion: 建议操作
            priority: 优先级
        """
        rule = ClassificationRule(
            pattern=pattern,
            error_type=error_type,
            category=category,
            severity=severity,
            recoverable=recoverable,
            suggestion=suggestion,
            priority=priority
        )
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)


# 全局分类器实例
_default_classifier = ErrorClassifier()


def classify_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> ClassifiedError:
    """
    使用默认分类器分类错误
    
    Args:
        error: 原始异常
        context: 上下文信息
    
    Returns:
        ClassifiedError: 已分类的错误
    """
    return _default_classifier.classify(error, context)
