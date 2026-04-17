# -*- coding: utf-8 -*-
"""
BobQuant 标准化错误类型系统 v1.0

设计原则：
1. 层次化：基础错误 → 领域错误 → 具体错误
2. 信息丰富：每个错误包含上下文、原因、建议操作
3. 可恢复性：标记错误是否可自动恢复
4. 用户友好：提供清晰的错误消息和解决建议

灵感来自 Claude Code 的错误处理设计
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"              # 低：不影响核心功能，可忽略
    MEDIUM = "medium"        # 中：影响部分功能，需要关注
    HIGH = "high"            # 高：影响核心功能，需要立即处理
    CRITICAL = "critical"    # 严重：系统无法继续运行


class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"              # 网络错误
    DATA = "data"                    # 数据错误
    TRADING = "trading"              # 交易错误
    STRATEGY = "strategy"            # 策略错误
    CONFIGURATION = "configuration"  # 配置错误
    SYSTEM = "system"                # 系统错误
    EXTERNAL = "external"            # 外部服务错误
    VALIDATION = "validation"        # 验证错误


class BobQuantError(Exception):
    """
    BobQuant 所有错误的基类
    
    Attributes:
        message: 错误消息
        category: 错误分类
        severity: 严重程度
        recoverable: 是否可自动恢复
        context: 错误上下文信息
        suggestion: 用户建议操作
        timestamp: 错误发生时间
        original_error: 原始异常（如果有）
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = False,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.context = context or {}
        self.suggestion = suggestion
        self.timestamp = datetime.now()
        self.original_error = original_error
        self._extra_info = kwargs
        
        # 添加上下文信息到消息
        if context:
            self._full_message = f"{message} | Context: {context}"
        else:
            self._full_message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """将错误转换为字典，便于日志记录和 API 响应"""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "context": self.context,
            "suggestion": self.suggestion,
            "timestamp": self.timestamp.isoformat(),
            "original_error": str(self.original_error) if self.original_error else None,
            **self._extra_info
        }
    
    def __str__(self) -> str:
        return f"[{self.__class__.__name__}] {self.message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, severity={self.severity.value})"


# =============================================================================
# 网络与 API 错误 (5 种)
# =============================================================================

class APIError(BobQuantError):
    """API 调用失败的通用错误"""
    
    def __init__(self, message: str = "API 调用失败", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('category', None)
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            suggestion="检查网络连接后重试",
            **kwargs
        )


class NetworkError(APIError):
    """网络连接错误"""
    
    def __init__(self, message: str = "网络连接失败", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            suggestion="检查网络连接和防火墙设置",
            **kwargs
        )


class TimeoutError(APIError):
    """请求超时错误"""
    
    def __init__(self, message: str = "请求超时", timeout_seconds: float = 30.0, **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        # 合并上下文
        existing_context = kwargs.pop('context', {})
        merged_context = {"timeout_seconds": timeout_seconds, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            context=merged_context,
            suggestion="增加超时时间或检查网络速度",
            **kwargs
        )


class RateLimitError(APIError):
    """API 速率限制错误"""
    
    def __init__(
        self,
        message: str = "触发 API 速率限制",
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        **kwargs
    ):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        # 合并上下文
        existing_context = kwargs.pop('context', {})
        merged_context = {
            "retry_after": retry_after,
            "rate_limit": limit,
            **existing_context
        }
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            context=merged_context,
            suggestion=f"等待 {retry_after or '一段时间'} 后重试",
            **kwargs
        )


class AuthenticationError(APIError):
    """认证失败错误"""
    
    def __init__(self, message: str = "认证失败", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            suggestion="检查 API 密钥或重新登录",
            **kwargs
        )


# =============================================================================
# 数据错误 (5 种)
# =============================================================================

class DataError(BobQuantError):
    """数据相关错误的基类"""
    
    def __init__(self, message: str = "数据错误", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('category', None)
        kwargs.pop('severity', None)
        
        super().__init__(
            message=message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DataNotFoundError(DataError):
    """数据不存在错误"""
    
    def __init__(self, message: str = "数据不存在", code: Optional[str] = None, **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        # 合并上下文
        existing_context = kwargs.pop('context', {})
        merged_context = {"code": code, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,
            context=merged_context,
            suggestion="检查股票代码是否正确或数据源是否支持",
            **kwargs
        )


class DataFormatError(DataError):
    """数据格式错误"""
    
    def __init__(
        self,
        message: str = "数据格式错误",
        expected_format: Optional[str] = None,
        actual_format: Optional[str] = None,
        **kwargs
    ):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        # 合并上下文
        existing_context = kwargs.pop('context', {})
        merged_context = {
            "expected_format": expected_format,
            "actual_format": actual_format,
            **existing_context
        }
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            context=merged_context,
            suggestion="检查数据源格式或联系数据提供商",
            **kwargs
        )


class DataValidationError(DataError):
    """数据验证错误"""
    
    def __init__(
        self,
        message: str = "数据验证失败",
        field: Optional[str] = None,
        value: Any = None,
        **kwargs
    ):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        # 合并上下文
        existing_context = kwargs.pop('context', {})
        merged_context = {"field": field, "value": value, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            context=merged_context,
            suggestion="检查数据完整性",
            **kwargs
        )


class DataStaleError(DataError):
    """数据过期错误"""
    
    def __init__(
        self,
        message: str = "数据已过期",
        data_age_seconds: Optional[float] = None,
        max_age_seconds: Optional[float] = None,
        **kwargs
    ):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        
        # 合并上下文
        existing_context = kwargs.pop('context', {})
        merged_context = {
            "data_age_seconds": data_age_seconds,
            "max_age_seconds": max_age_seconds,
            **existing_context
        }
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            context=merged_context,
            suggestion="刷新数据后重试",
            **kwargs
        )


# =============================================================================
# 交易错误 (6 种)
# =============================================================================

class TradingError(BobQuantError):
    """交易相关错误的基类"""
    
    def __init__(self, message: str = "交易错误", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('category', None)
        kwargs.pop('severity', None)
        
        super().__init__(
            message=message,
            category=ErrorCategory.TRADING,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class OrderError(TradingError):
    """订单错误"""
    
    def __init__(
        self,
        message: str = "订单错误",
        order_id: Optional[str] = None,
        action: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"order_id": order_id, "action": action, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            context=merged_context,
            **kwargs
        )


class OrderRejectedError(OrderError):
    """订单被拒绝错误"""
    
    def __init__(
        self,
        message: str = "订单被拒绝",
        reason: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"rejection_reason": reason, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            context=merged_context,
            suggestion="检查订单参数或联系券商",
            **kwargs
        )


class InsufficientFundsError(TradingError):
    """资金不足错误"""
    
    def __init__(
        self,
        message: str = "可用资金不足",
        required: Optional[float] = None,
        available: Optional[float] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {
            "required_amount": required,
            "available_amount": available,
            **existing_context
        }
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            context=merged_context,
            suggestion="减少交易数量或充值",
            **kwargs
        )


class PositionError(TradingError):
    """持仓错误"""
    
    def __init__(
        self,
        message: str = "持仓错误",
        code: Optional[str] = None,
        position_type: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"code": code, "position_type": position_type, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=merged_context,
            **kwargs
        )


class MarketClosedError(TradingError):
    """市场关闭错误"""
    
    def __init__(
        self,
        message: str = "市场已关闭",
        market: Optional[str] = None,
        reopen_time: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"market": market, "reopen_time": reopen_time, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            context=merged_context,
            suggestion="等待市场开盘后重试",
            **kwargs
        )


# =============================================================================
# 策略错误 (4 种)
# =============================================================================

class StrategyError(BobQuantError):
    """策略相关错误的基类"""
    
    def __init__(self, message: str = "策略错误", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('category', None)
        kwargs.pop('severity', None)
        
        super().__init__(
            message=message,
            category=ErrorCategory.STRATEGY,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class SignalError(StrategyError):
    """信号生成错误"""
    
    def __init__(
        self,
        message: str = "信号生成失败",
        strategy_name: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"strategy_name": strategy_name, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=merged_context,
            suggestion="检查策略配置和输入数据",
            **kwargs
        )


class ConfigurationError(StrategyError):
    """配置错误"""
    
    def __init__(
        self,
        message: str = "配置错误",
        config_key: Optional[str] = None,
        invalid_value: Any = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"config_key": config_key, "invalid_value": invalid_value, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            context=merged_context,
            suggestion="检查配置文件或环境变量",
            **kwargs
        )


class BacktestError(StrategyError):
    """回测错误"""
    
    def __init__(
        self,
        message: str = "回测执行失败",
        backtest_id: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"backtest_id": backtest_id, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            context=merged_context,
            suggestion="检查回测参数和数据完整性",
            **kwargs
        )


# =============================================================================
# 系统错误 (4 种)
# =============================================================================

class SystemError(BobQuantError):
    """系统相关错误的基类"""
    
    def __init__(self, message: str = "系统错误", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('category', None)
        kwargs.pop('severity', None)
        
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class FileSystemError(SystemError):
    """文件系统错误"""
    
    def __init__(
        self,
        message: str = "文件系统错误",
        path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"path": path, "operation": operation, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            context=merged_context,
            suggestion="检查文件权限和磁盘空间",
            **kwargs
        )


class DatabaseError(SystemError):
    """数据库错误"""
    
    def __init__(
        self,
        message: str = "数据库错误",
        db_type: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {"db_type": db_type, "operation": operation, **existing_context}
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            context=merged_context,
            suggestion="检查数据库连接和状态",
            **kwargs
        )


class MemoryError(SystemError):
    """内存错误"""
    
    def __init__(
        self,
        message: str = "内存不足",
        required_mb: Optional[int] = None,
        available_mb: Optional[int] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {
            "required_mb": required_mb,
            "available_mb": available_mb,
            **existing_context
        }
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            context=merged_context,
            suggestion="关闭其他程序或增加内存",
            **kwargs
        )


# =============================================================================
# 外部服务错误 (2 种)
# =============================================================================

class ExternalServiceError(BobQuantError):
    """外部服务错误的基类"""
    
    def __init__(self, message: str = "外部服务错误", **kwargs):
        # 移除已显式设置的参数，避免重复
        kwargs.pop('category', None)
        kwargs.pop('severity', None)
        kwargs.pop('recoverable', None)
        
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            **kwargs
        )


class ThirdPartyAPIError(ExternalServiceError):
    """第三方 API 错误"""
    
    def __init__(
        self,
        message: str = "第三方 API 错误",
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        kwargs.pop('severity', None)
        kwargs.pop('suggestion', None)
        existing_context = kwargs.pop('context', {})
        merged_context = {
            "service_name": service_name,
            "status_code": status_code,
            **existing_context
        }
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            context=merged_context,
            suggestion="检查第三方服务状态或稍后重试",
            **kwargs
        )


# =============================================================================
# 错误转换链辅助函数
# =============================================================================

def convert_exception(
    exc: Exception,
    target_class: type = BobQuantError,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> BobQuantError:
    """
    将普通异常转换为 BobQuant 标准化错误
    
    Args:
        exc: 原始异常
        target_class: 目标错误类型
        context: 附加上下文
        **kwargs: 其他参数
    
    Returns:
        BobQuantError: 标准化错误
    """
    if isinstance(exc, BobQuantError):
        return exc
    
    return target_class(
        message=str(exc),
        original_error=exc,
        context=context,
        **kwargs
    )


def create_error_chain(
    errors: List[BobQuantError],
    primary_error: Optional[BobQuantError] = None
) -> Dict[str, Any]:
    """
    创建错误链，用于记录多个相关错误
    
    Args:
        errors: 错误列表
        primary_error: 主要错误
    
    Returns:
        dict: 错误链信息
    """
    if not errors:
        return {"errors": [], "primary": None}
    
    return {
        "primary": primary_error.to_dict() if primary_error else errors[0].to_dict(),
        "related": [e.to_dict() for e in errors[1:]] if len(errors) > 1 else [],
        "count": len(errors),
        "timestamp": datetime.now().isoformat()
    }
