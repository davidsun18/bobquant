"""
Retry Mechanism - 退避重试机制

设计目标：
1. 指数退避（Exponential Backoff）
2. 抖动（Jitter）避免惊群效应
3. 可配置的重试策略
4. 装饰器模式，易于使用

架构参考：
- AWS SDK: 标准重试策略
- tenacity 库：Python 重试最佳实践
"""

import time
import random
import functools
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, Type, Tuple


@dataclass
class RetryConfig:
    """
    重试配置
    
    Attributes:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数基数（2 表示指数增长）
        jitter: 是否启用抖动
        jitter_factor: 抖动因子（0-1，表示延迟的随机比例）
        retryable_exceptions: 可重试的异常类型
    """
    max_retries: int = 3
    base_delay: float = 0.1  # 100ms
    max_delay: float = 30.0  # 30 秒
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


class RetryError(Exception):
    """重试失败异常"""
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """
    计算重试延迟时间
    
    公式：delay = base_delay * (exponential_base ^ attempt) + jitter
    
    Args:
        attempt: 当前尝试次数（从 0 开始）
        config: 重试配置
        
    Returns:
        float: 延迟时间（秒）
    """
    # 指数退避
    delay = config.base_delay * (config.exponential_base ** attempt)
    
    # 限制最大延迟
    delay = min(delay, config.max_delay)
    
    # 添加抖动
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay)  # 确保非负
    
    return delay


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    退避重试装饰器
    
    使用示例：
    ```python
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def save_to_disk(data):
        # 可能失败的操作
        pass
    
    # 或者使用配置对象
    config = RetryConfig(max_retries=5, base_delay=0.5)
    
    @retry_with_backoff(**config.__dict__)
    def network_request():
        pass
    ```
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        jitter: 是否启用抖动
        retryable_exceptions: 可重试的异常类型
        on_retry: 重试回调函数 (attempt, exception, delay)
        
    Returns:
        装饰器函数
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    # 达到最大重试次数
                    if attempt >= config.max_retries:
                        break
                    
                    # 计算延迟
                    delay = calculate_delay(attempt, config)
                    
                    # 重试回调
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    # 记录日志
                    logging.warning(
                        f"Retry {attempt + 1}/{config.max_retries} after {delay:.2f}s "
                        f"due to: {type(e).__name__}: {e}"
                    )
                    
                    # 等待
                    time.sleep(delay)
            
            # 所有重试失败
            raise RetryError(
                f"Failed after {config.max_retries + 1} attempts",
                last_exception
            )
        
        return wrapper
    return decorator


class RetryExecutor:
    """
    重试执行器（面向对象方式）
    
    使用示例：
    ```python
    executor = RetryExecutor(
        max_retries=3,
        on_retry=lambda attempt, e, delay: print(f"Retry {attempt}: {e}")
    )
    
    result = executor.execute(risky_operation, arg1, arg2)
    ```
    """
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
        on_success: Optional[Callable[[Any, int], None]] = None,
        on_failure: Optional[Callable[[Exception, int], None]] = None,
    ):
        """
        初始化重试执行器
        
        Args:
            config: 重试配置
            on_retry: 重试回调
            on_success: 成功回调 (result, attempts)
            on_failure: 失败回调 (exception, attempts)
        """
        self.config = config or RetryConfig()
        self.on_retry = on_retry
        self.on_success = on_success
        self.on_failure = on_failure
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数（带重试）
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                if self.on_success:
                    self.on_success(result, attempt + 1)
                
                return result
                
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt >= self.config.max_retries:
                    break
                
                delay = calculate_delay(attempt, self.config)
                
                if self.on_retry:
                    self.on_retry(attempt, e, delay)
                
                logging.warning(
                    f"Retry {attempt + 1}/{self.config.max_retries} "
                    f"after {delay:.2f}s: {e}"
                )
                
                time.sleep(delay)
        
        # 所有重试失败
        if self.on_failure:
            self.on_failure(last_exception, self.config.max_retries + 1)
        
        raise RetryError(
            f"Failed after {self.config.max_retries + 1} attempts",
            last_exception
        )
    
    def execute_with_timeout(
        self,
        func: Callable,
        timeout: float,
        *args,
        **kwargs
    ) -> Any:
        """
        带超时的重试执行
        
        Args:
            func: 要执行的函数
            timeout: 总超时时间（秒）
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值
        """
        start_time = time.time()
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            # 检查总超时
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise RetryError(
                    f"Timeout after {timeout:.1f}s",
                    last_exception
                )
            
            try:
                return func(*args, **kwargs)
                
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt >= self.config.max_retries:
                    break
                
                delay = calculate_delay(attempt, self.config)
                
                # 确保不会超过总超时
                remaining = timeout - elapsed
                delay = min(delay, remaining - 0.1)  # 留 100ms 余量
                
                if delay > 0:
                    time.sleep(delay)
        
        raise RetryError(
            f"Failed after {self.config.max_retries + 1} attempts",
            last_exception
        )


# 预定义的重试配置
RETRY_QUICK = RetryConfig(
    max_retries=2,
    base_delay=0.05,
    max_delay=1.0,
)

RETRY_STANDARD = RetryConfig(
    max_retries=3,
    base_delay=0.1,
    max_delay=10.0,
)

RETRY_PERSISTENT = RetryConfig(
    max_retries=5,
    base_delay=0.5,
    max_delay=60.0,
)
