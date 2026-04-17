# -*- coding: utf-8 -*-
"""
BobQuant 错误处理系统 v1.0
灵感来自 Claude Code 的错误处理设计

提供标准化错误类型、分类器、恢复机制和用户友好的错误消息
"""

from .types import (
    # 基础错误
    BobQuantError,
    APIError,
    NetworkError,
    TimeoutError,
    RateLimitError,
    AuthenticationError,
    
    # 数据错误
    DataError,
    DataNotFoundError,
    DataFormatError,
    DataValidationError,
    DataStaleError,
    
    # 交易错误
    TradingError,
    OrderError,
    OrderRejectedError,
    InsufficientFundsError,
    PositionError,
    MarketClosedError,
    
    # 策略错误
    StrategyError,
    SignalError,
    ConfigurationError,
    BacktestError,
    
    # 系统错误
    SystemError,
    FileSystemError,
    DatabaseError,
    MemoryError,
    
    # 外部服务错误
    ExternalServiceError,
    ThirdPartyAPIError,
    
    # 错误分类和恢复
    ErrorCategory,
    ErrorSeverity,
)

from .classifier import ErrorClassifier
from .recovery import (
    RecoveryManager,
    RetryStrategy,
    RetryConfig,
    CircuitBreakerConfig,
    DataSourceFailover,
    retry,
    with_fallback,
    circuit_breaker,
)
from .messages import ErrorMessageGenerator, MessageDetailLevel, UserMessage

__version__ = "1.0.0"
__all__ = [
    # 错误类型
    'BobQuantError',
    'APIError',
    'NetworkError',
    'TimeoutError',
    'RateLimitError',
    'AuthenticationError',
    'DataError',
    'DataNotFoundError',
    'DataFormatError',
    'DataValidationError',
    'DataStaleError',
    'TradingError',
    'OrderError',
    'OrderRejectedError',
    'InsufficientFundsError',
    'PositionError',
    'MarketClosedError',
    'StrategyError',
    'SignalError',
    'ConfigurationError',
    'BacktestError',
    'SystemError',
    'FileSystemError',
    'DatabaseError',
    'MemoryError',
    'ExternalServiceError',
    'ThirdPartyAPIError',
    # 分类和恢复
    'ErrorCategory',
    'ErrorSeverity',
    'ErrorClassifier',
    'RecoveryManager',
    'RetryStrategy',
    # 消息生成
    'ErrorMessageGenerator',
    'MessageDetailLevel',
    'UserMessage',
    # 恢复机制
    'RecoveryManager',
    'RetryStrategy',
    'RetryConfig',
    'CircuitBreakerConfig',
    'DataSourceFailover',
    # 装饰器
    'retry',
    'with_fallback',
    'circuit_breaker',
]
