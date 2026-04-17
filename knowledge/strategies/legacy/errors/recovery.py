# -*- coding: utf-8 -*-
"""
BobQuant 错误恢复机制 v1.0

功能：
1. 重试机制（二次退避策略）
2. 降级策略（数据源切换）
3. 熔断器模式
4. 自动故障转移

设计灵感来自 Claude Code 的恢复系统和分布式系统的容错模式
"""

import time
import random
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps
import threading

from .types import (
    BobQuantError,
    ErrorCategory,
    ErrorSeverity,
    RateLimitError,
    TimeoutError,
    NetworkError,
    DataNotFoundError,
    DataStaleError,
    AuthenticationError,
    ThirdPartyAPIError,
)
from .classifier import ErrorClassifier, ClassifiedError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    NONE = "none"                    # 不重试
    FIXED = "fixed"                  # 固定间隔
    LINEAR = "linear"                # 线性退避
    EXPONENTIAL = "exponential"      # 指数退避（二次退避）
    JITTERED = "jittered"            # 带抖动的指数退避


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.JITTERED
    base_delay: float = 1.0          # 基础延迟（秒）
    max_delay: float = 60.0          # 最大延迟（秒）
    jitter_factor: float = 0.1       # 抖动因子 (0-1)
    retryable_errors: List[Type[BobQuantError]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.retryable_errors:
            # 默认重试的错误类型
            self.retryable_errors = [
                RateLimitError,
                TimeoutError,
                NetworkError,
                DataStaleError,
                ThirdPartyAPIError,
            ]


@dataclass
class RetryState:
    """重试状态"""
    attempt: int = 0
    last_error: Optional[Exception] = None
    last_attempt_time: Optional[datetime] = None
    next_retry_time: Optional[datetime] = None
    total_delay: float = 0.0


class CircuitBreakerStateEnum(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态（测试恢复）


# 向后兼容别名
CircuitBreakerState = CircuitBreakerStateEnum


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5       # 失败阈值
    success_threshold: int = 2       # 成功阈值（半开状态）
    timeout: float = 30.0            # 熔断超时（秒）
    half_open_max_calls: int = 3     # 半开状态最大调用数


@dataclass
class CircuitBreakerStatus:
    """熔断器状态数据"""
    state: CircuitBreakerStateEnum = CircuitBreakerStateEnum.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0


class RecoveryManager:
    """
    恢复管理器
    
    提供重试、降级、熔断等恢复机制
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        classifier: Optional[ErrorClassifier] = None
    ):
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.classifier = classifier or ErrorClassifier()
        
        # 熔断器状态（按服务名称隔离）
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._lock = threading.Lock()
        
        # 降级策略
        self._fallbacks: Dict[str, List[Callable]] = {}
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟（二次退避）
        
        Args:
            attempt: 当前重试次数
        
        Returns:
            float: 延迟时间（秒）
        """
        if self.retry_config.strategy == RetryStrategy.NONE:
            return 0.0
        
        elif self.retry_config.strategy == RetryStrategy.FIXED:
            delay = self.retry_config.base_delay
        
        elif self.retry_config.strategy == RetryStrategy.LINEAR:
            delay = self.retry_config.base_delay * attempt
        
        elif self.retry_config.strategy == RetryStrategy.EXPONENTIAL:
            # 二次退避：delay = base * 2^(attempt-1)
            delay = self.retry_config.base_delay * (2 ** (attempt - 1))
        
        elif self.retry_config.strategy == RetryStrategy.JITTERED:
            # 带抖动的指数退避
            base_delay = self.retry_config.base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(-1, 1) * self.retry_config.jitter_factor * base_delay
            delay = base_delay + jitter
        
        else:
            delay = self.retry_config.base_delay
        
        # 限制最大延迟
        return min(delay, self.retry_config.max_delay)
    
    def should_retry(self, error: Exception, state: RetryState) -> bool:
        """
        判断是否应该重试
        
        Args:
            error: 错误
            state: 重试状态
        
        Returns:
            bool: 是否重试
        """
        if state.attempt >= self.retry_config.max_retries:
            return False
        
        # 检查错误类型是否可重试
        classified = self.classifier.classify(error)
        if not classified.recoverable:
            return False
        
        # 检查是否在可重试错误列表中
        for retryable_type in self.retry_config.retryable_errors:
            if isinstance(classified.classified_error, retryable_type):
                return True
        
        # 默认：如果是可恢复错误则重试
        return classified.recoverable
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        retry_config: Optional[RetryConfig] = None,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
        **kwargs
    ) -> Any:
        """
        执行函数并重试
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            retry_config: 重试配置（可选，覆盖默认配置）
            on_retry: 重试回调 (attempt, error, delay)
            **kwargs: 关键字参数
        
        Returns:
            Any: 函数返回值
        
        Raises:
            Exception: 最后一次尝试的错误
        """
        config = retry_config or self.retry_config
        state = RetryState()
        
        while True:
            try:
                state.attempt += 1
                state.last_attempt_time = datetime.now()
                
                result = func(*args, **kwargs)
                
                # 成功：重置熔断器
                self._record_success(func.__name__)
                
                return result
            
            except Exception as e:
                state.last_error = e
                
                # 记录失败
                self._record_failure(func.__name__, e)
                
                # 判断是否重试
                if not self.should_retry(e, state):
                    logger.error(f"不重试：{type(e).__name__}: {e}")
                    raise
                
                # 检查熔断器
                if self._is_circuit_open(func.__name__):
                    logger.warning(f"熔断器打开，拒绝执行：{func.__name__}")
                    raise
                
                # 计算延迟
                delay = self.calculate_delay(state.attempt)
                state.total_delay += delay
                state.next_retry_time = datetime.now() + timedelta(seconds=delay)
                
                # 回调
                if on_retry:
                    on_retry(state.attempt, e, delay)
                
                logger.warning(
                    f"重试 {state.attempt}/{config.max_retries} "
                    f"延迟 {delay:.2f}s: {type(e).__name__}: {e}"
                )
                
                # 等待
                time.sleep(delay)
    
    def _record_success(self, service_name: str):
        """记录成功"""
        with self._lock:
            if service_name not in self._circuit_breakers:
                self._circuit_breakers[service_name] = CircuitBreakerStatus()
            
            cb = self._circuit_breakers[service_name]
            
            if cb.state == CircuitBreakerState.HALF_OPEN:
                cb.success_count += 1
                if cb.success_count >= self.circuit_breaker_config.success_threshold:
                    cb.state = CircuitBreakerState.CLOSED
                    cb.failure_count = 0
                    cb.success_count = 0
                    logger.info(f"熔断器关闭：{service_name}")
            
            elif cb.state == CircuitBreakerState.CLOSED:
                cb.failure_count = 0
    
    def _record_failure(self, service_name: str, error: Exception):
        """记录失败"""
        with self._lock:
            if service_name not in self._circuit_breakers:
                self._circuit_breakers[service_name] = CircuitBreakerStatus()
            
            cb = self._circuit_breakers[service_name]
            cb.failure_count += 1
            cb.last_failure_time = datetime.now()
            
            if cb.state == CircuitBreakerState.HALF_OPEN:
                cb.state = CircuitBreakerState.OPEN
                cb.half_open_calls = 0
                logger.warning(f"熔断器打开（半开失败）：{service_name}")
            
            elif cb.state == CircuitBreakerState.CLOSED:
                if cb.failure_count >= self.circuit_breaker_config.failure_threshold:
                    cb.state = CircuitBreakerState.OPEN
                    logger.warning(
                        f"熔断器打开（失败阈值）：{service_name}, "
                        f"failures={cb.failure_count}"
                    )
    
    def _is_circuit_open(self, service_name: str) -> bool:
        """检查熔断器是否打开"""
        with self._lock:
            if service_name not in self._circuit_breakers:
                return False
            
            cb = self._circuit_breakers[service_name]
            
            if cb.state == CircuitBreakerState.OPEN:
                # 检查是否超时
                if cb.last_failure_time:
                    elapsed = (datetime.now() - cb.last_failure_time).total_seconds()
                    if elapsed >= self.circuit_breaker_config.timeout:
                        cb.state = CircuitBreakerState.HALF_OPEN
                        cb.half_open_calls = 0
                        logger.info(f"熔断器半开：{service_name}")
                        return False
                return True
            
            elif cb.state == CircuitBreakerState.HALF_OPEN:
                cb.half_open_calls += 1
                if cb.half_open_calls > self.circuit_breaker_config.half_open_max_calls:
                    return True
                return False
            
            return False
    
    def register_fallback(
        self,
        primary_name: str,
        fallback: Callable,
        priority: int = 0
    ):
        """
        注册降级策略
        
        Args:
            primary_name: 主服务名称
            fallback: 降级函数
            priority: 优先级（数字越小优先级越高）
        """
        if primary_name not in self._fallbacks:
            self._fallbacks[primary_name] = []
        
        self._fallbacks[primary_name].append((priority, fallback))
        self._fallbacks[primary_name].sort(key=lambda x: x[0])
    
    def execute_with_fallback(
        self,
        primary: Callable,
        *args,
        fallbacks: Optional[List[Callable]] = None,
        **kwargs
    ) -> Any:
        """
        执行主函数，失败时使用降级策略
        
        Args:
            primary: 主函数
            *args: 位置参数
            fallbacks: 降级函数列表
            **kwargs: 关键字参数
        
        Returns:
            Any: 返回值
        """
        all_fallbacks = []
        
        # 添加注册的降级
        if primary.__name__ in self._fallbacks:
            all_fallbacks.extend(
                fb for _, fb in self._fallbacks[primary.__name__]
            )
        
        # 添加传入的降级
        if fallbacks:
            all_fallbacks.extend(fallbacks)
        
        # 尝试主函数
        try:
            return primary(*args, **kwargs)
        except Exception as e:
            logger.warning(f"主函数失败：{primary.__name__}: {e}")
            
            # 尝试降级
            for i, fallback in enumerate(all_fallbacks):
                try:
                    logger.info(f"使用降级 #{i+1}: {fallback.__name__}")
                    return fallback(*args, **kwargs)
                except Exception as fe:
                    logger.warning(f"降级 #{i+1} 失败：{fallback.__name__}: {fe}")
            
            # 所有降级都失败
            raise Exception(
                f"主函数和所有降级都失败：{primary.__name__}, "
                f"尝试了 {len(all_fallbacks)} 个降级"
            )
    
    def get_circuit_breaker_state(self, service_name: str) -> Dict[str, Any]:
        """
        获取熔断器状态
        
        Args:
            service_name: 服务名称
        
        Returns:
            dict: 熔断器状态
        """
        with self._lock:
            if service_name not in self._circuit_breakers:
                return {
                    "state": "not_initialized",
                    "failure_count": 0,
                    "success_count": 0
                }
            
            cb = self._circuit_breakers[service_name]
            return {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "success_count": cb.success_count,
                "last_failure_time": cb.last_failure_time.isoformat() if cb.last_failure_time else None,
                "half_open_calls": cb.half_open_calls
            }
    
    def reset_circuit_breaker(self, service_name: str):
        """重置熔断器"""
        with self._lock:
            if service_name in self._circuit_breakers:
                self._circuit_breakers[service_name] = CircuitBreakerStatus()
                logger.info(f"熔断器已重置：{service_name}")


# =============================================================================
# 数据源降级策略
# =============================================================================

class DataSourceFailover:
    """
    数据源故障转移
    
    当主数据源失败时，自动切换到备用数据源
    """
    
    def __init__(self, recovery_manager: Optional[RecoveryManager] = None):
        self.recovery = recovery_manager or RecoveryManager()
        self._data_sources: Dict[str, List[Any]] = {}
        self._current_source: Dict[str, int] = {}
    
    def register_data_sources(
        self,
        provider_name: str,
        sources: List[Any],
        priorities: Optional[List[int]] = None
    ):
        """
        注册数据源列表
        
        Args:
            provider_name: 数据源组名称
            sources: 数据源实例列表
            priorities: 优先级列表（数字越小优先级越高）
        """
        if priorities is None:
            priorities = list(range(len(sources)))
        
        # 按优先级排序
        sorted_sources = sorted(
            zip(sources, priorities),
            key=lambda x: x[1]
        )
        
        self._data_sources[provider_name] = [s for s, _ in sorted_sources]
        self._current_source[provider_name] = 0
        
        logger.info(
            f"注册数据源组：{provider_name}, "
            f"共 {len(sources)} 个数据源"
        )
    
    def get_current_source(self, provider_name: str) -> Optional[Any]:
        """获取当前数据源"""
        if provider_name not in self._data_sources:
            return None
        
        idx = self._current_source.get(provider_name, 0)
        if idx < len(self._data_sources[provider_name]):
            return self._data_sources[provider_name][idx]
        
        return None
    
    def switch_to_next(self, provider_name: str) -> bool:
        """
        切换到下一个数据源
        
        Returns:
            bool: 是否还有可用数据源
        """
        if provider_name not in self._data_sources:
            return False
        
        current = self._current_source.get(provider_name, 0)
        next_idx = current + 1
        
        if next_idx < len(self._data_sources[provider_name]):
            self._current_source[provider_name] = next_idx
            logger.info(
                f"切换数据源：{provider_name} #{current} -> #{next_idx}"
            )
            return True
        
        logger.warning(f"数据源组耗尽：{provider_name}")
        return False
    
    def reset(self, provider_name: str):
        """重置到主数据源"""
        if provider_name in self._current_source:
            self._current_source[provider_name] = 0
            logger.info(f"重置数据源：{provider_name} -> #0")
    
    def execute_with_failover(
        self,
        provider_name: str,
        operation: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        执行操作，支持数据源故障转移
        
        Args:
            provider_name: 数据源组名称
            operation: 操作名称（用于日志）
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Any: 返回值
        """
        if provider_name not in self._data_sources:
            return func(*args, **kwargs)
        
        sources = self._data_sources[provider_name]
        current_idx = self._current_source.get(provider_name, 0)
        
        last_error = None
        
        # 尝试所有数据源
        for i in range(len(sources)):
            idx = (current_idx + i) % len(sources)
            source = sources[idx]
            
            try:
                logger.info(
                    f"使用数据源：{provider_name} #{idx} "
                    f"执行 {operation}"
                )
                
                result = func(source, *args, **kwargs)
                
                # 成功：重置到主数据源
                self.reset(provider_name)
                
                return result
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"数据源 #{idx} 失败：{operation}: {type(e).__name__}: {e}"
                )
                
                # 切换到下一个
                if i < len(sources) - 1:
                    self.switch_to_next(provider_name)
        
        # 所有数据源都失败
        raise Exception(
            f"所有数据源都失败：{provider_name}, "
            f"尝试了 {len(sources)} 个数据源, "
            f"最后错误：{last_error}"
        )


# =============================================================================
# 装饰器
# =============================================================================

def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.JITTERED,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟
        strategy: 重试策略
        retryable_exceptions: 可重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            recovery = RecoveryManager(
                retry_config=RetryConfig(
                    max_retries=max_retries,
                    strategy=strategy,
                    base_delay=base_delay
                )
            )
            
            return recovery.execute_with_retry(
                func, *args, **kwargs
            )
        
        return wrapper
    return decorator


def with_fallback(fallback_func: Callable):
    """
    降级装饰器
    
    Args:
        fallback_func: 降级函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            recovery = RecoveryManager()
            
            return recovery.execute_with_fallback(
                func, *args,
                fallbacks=[fallback_func],
                **kwargs
            )
        
        return wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    timeout: float = 30.0,
    name: Optional[str] = None
):
    """
    熔断器装饰器
    
    Args:
        failure_threshold: 失败阈值
        timeout: 超时时间
        name: 服务名称（默认使用函数名）
    """
    def decorator(func: Callable) -> Callable:
        service_name = name or func.__name__
        recovery = RecoveryManager(
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout=timeout
            )
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 检查熔断器
            if recovery._is_circuit_open(service_name):
                raise Exception(f"熔断器打开：{service_name}")
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                recovery._record_failure(service_name, e)
                raise
        
        return wrapper
    return decorator
