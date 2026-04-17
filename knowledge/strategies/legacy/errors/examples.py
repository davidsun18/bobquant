# -*- coding: utf-8 -*-
"""
BobQuant 错误处理系统使用示例

展示各种错误处理场景的实际用法
"""

import time
import random
from typing import Optional

from bobquant.errors import (
    # 错误类型
    BobQuantError,
    NetworkError,
    TimeoutError,
    RateLimitError,
    DataNotFoundError,
    InsufficientFundsError,
    OrderRejectedError,
    ConfigurationError,
    
    # 分类和恢复
    ErrorClassifier,
    ErrorCategory,
    ErrorSeverity,
    RecoveryManager,
    RetryConfig,
    RetryStrategy,
    DataSourceFailover,
    
    # 消息生成
    ErrorMessageGenerator,
    MessageDetailLevel,
    
    # 装饰器
    retry,
    with_fallback,
    circuit_breaker,
)


# =============================================================================
# 示例 1: 错误分类
# =============================================================================

def example_error_classification():
    """示例：错误分类"""
    print("=" * 60)
    print("示例 1: 错误分类")
    print("=" * 60)
    
    classifier = ErrorClassifier()
    
    # 模拟各种异常
    test_exceptions = [
        ConnectionRefusedError("Connection refused"),
        TimeoutError("Request timed out after 30 seconds"),
        Exception("Rate limit exceeded, 429 Too Many Requests"),
        Exception("Authentication failed: invalid API key"),
        FileNotFoundError("[Errno 2] No such file or directory: 'data.csv'"),
        Exception("Insufficient funds for order"),
        ValueError("Invalid configuration parameter"),
    ]
    
    for exc in test_exceptions:
        classified = classifier.classify(exc, context={"test": True})
        
        print(f"\n原始错误：{type(exc).__name__}: {exc}")
        print(f"  分类错误：{type(classified.classified_error).__name__}")
        print(f"  类别：{classified.category.value}")
        print(f"  严重程度：{classified.severity.value}")
        print(f"  可恢复：{classified.recoverable}")
        print(f"  置信度：{classified.confidence:.2f}")
        print(f"  处理策略：{classified.handling_strategy}")
    
    print("\n" + "=" * 60)


# =============================================================================
# 示例 2: 重试机制
# =============================================================================

def example_retry_mechanism():
    """示例：重试机制"""
    print("=" * 60)
    print("示例 2: 重试机制")
    print("=" * 60)
    
    # 模拟可能失败的函数
    call_count = 0
    
    def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise NetworkError(f"模拟网络失败 #{call_count}")
        return f"成功！尝试了 {call_count} 次"
    
    # 配置重试
    recovery = RecoveryManager(
        retry_config=RetryConfig(
            max_retries=5,
            strategy=RetryStrategy.JITTERED,
            base_delay=0.5,
            max_delay=5.0,
        )
    )
    
    # 执行带重试
    def on_retry(attempt, error, delay):
        print(f"  重试 #{attempt}, 延迟 {delay:.2f}s: {error}")
    
    try:
        result = recovery.execute_with_retry(
            flaky_operation,
            on_retry=on_retry
        )
        print(f"\n结果：{result}")
    except Exception as e:
        print(f"\n最终失败：{e}")
    
    print("\n" + "=" * 60)


# =============================================================================
# 示例 3: 熔断器
# =============================================================================

def example_circuit_breaker():
    """示例：熔断器"""
    print("=" * 60)
    print("示例 3: 熔断器")
    print("=" * 60)
    
    recovery = RecoveryManager(
        circuit_breaker_config={
            "failure_threshold": 3,
            "success_threshold": 2,
            "timeout": 5.0,
        }
    )
    
    # 模拟失败的服务
    def failing_service():
        raise NetworkError("服务暂时不可用")
    
    service_name = "test_service"
    
    # 连续失败，触发熔断
    print("连续调用失败服务...")
    for i in range(5):
        try:
            recovery.execute_with_retry(
                failing_service,
                retry_config=RetryConfig(max_retries=0)  # 不重试
            )
        except Exception as e:
            print(f"  调用 #{i+1}: {e}")
        
        # 检查熔断器状态
        state = recovery.get_circuit_breaker_state(service_name)
        print(f"    熔断器状态：{state['state']}")
    
    print("\n" + "=" * 60)


# =============================================================================
# 示例 4: 降级策略
# =============================================================================

def example_fallback_strategy():
    """示例：降级策略"""
    print("=" * 60)
    print("示例 4: 降级策略")
    print("=" * 60)
    
    # 模拟主服务和备用服务
    def primary_service():
        raise NetworkError("主服务失败")
    
    def fallback_service_1():
        print("  → 使用备用服务 1")
        return "备用服务 1 的数据"
    
    def fallback_service_2():
        print("  → 使用备用服务 2")
        return "备用服务 2 的数据"
    
    recovery = RecoveryManager()
    
    # 执行带降级
    result = recovery.execute_with_fallback(
        primary_service,
        fallbacks=[fallback_service_1, fallback_service_2]
    )
    
    print(f"\n结果：{result}")
    
    print("\n" + "=" * 60)


# =============================================================================
# 示例 5: 装饰器用法
# =============================================================================

@retry(max_retries=3, base_delay=0.5)
def decorated_retry_example():
    """示例：重试装饰器"""
    if not hasattr(decorated_retry_example, 'calls'):
        decorated_retry_example.calls = 0
    decorated_retry_example.calls += 1
    
    if decorated_retry_example.calls < 2:
        raise TimeoutError("模拟超时")
    
    return f"成功！调用 {decorated_retry_example.calls} 次"


def fallback_data():
    """降级数据"""
    return {"source": "cache", "data": "备用数据"}


@with_fallback(fallback_data)
def decorated_fallback_example():
    """示例：降级装饰器"""
    raise DataNotFoundError("主数据源无数据")


@circuit_breaker(failure_threshold=3, timeout=10.0)
def decorated_circuit_example():
    """示例：熔断器装饰器"""
    if random.random() < 0.7:
        raise NetworkError("随机失败")
    return "成功"


def example_decorators():
    """示例：装饰器用法"""
    print("=" * 60)
    print("示例 5: 装饰器用法")
    print("=" * 60)
    
    # 重试装饰器
    print("\n1. 重试装饰器:")
    try:
        result = decorated_retry_example()
        print(f"   结果：{result}")
    except Exception as e:
        print(f"   失败：{e}")
    
    # 降级装饰器
    print("\n2. 降级装饰器:")
    try:
        result = decorated_fallback_example()
        print(f"   结果：{result}")
    except Exception as e:
        print(f"   失败：{e}")
    
    # 熔断器装饰器
    print("\n3. 熔断器装饰器 (5 次调用):")
    for i in range(5):
        try:
            result = decorated_circuit_example()
            print(f"   调用 #{i+1}: {result}")
        except Exception as e:
            print(f"   调用 #{i+1}: {e}")
    
    print("\n" + "=" * 60)


# =============================================================================
# 示例 6: 用户友好的错误消息
# =============================================================================

def example_user_messages():
    """示例：用户友好的错误消息"""
    print("=" * 60)
    print("示例 6: 用户友好的错误消息")
    print("=" * 60)
    
    generator = ErrorMessageGenerator(language="zh")
    
    # 创建各种错误
    test_errors = [
        NetworkError("连接被拒绝", context={"host": "api.example.com"}),
        TimeoutError("请求超时", timeout_seconds=30),
        RateLimitError("触发速率限制", retry_after=60),
        InsufficientFundsError(
            "可用资金不足",
            required=10000.0,
            available=5000.0
        ),
        DataNotFoundError("数据不存在", code="sh999999"),
    ]
    
    for error in test_errors:
        print(f"\n错误类型：{type(error).__name__}")
        print("-" * 40)
        
        # 简洁模式
        brief = generator.generate(error, MessageDetailLevel.BRIEF)
        print(f"【简洁】{brief.title}: {brief.message}")
        
        # 标准模式
        standard = generator.generate(error, MessageDetailLevel.STANDARD)
        print(f"【标准】{standard.to_string()}")
        
        # 详细模式
        detailed = generator.generate(error, MessageDetailLevel.DETAILED)
        print(f"【详细】技术细节:\n{detailed.technical_details}")
        print()
    
    # 批量摘要
    print("\n批量错误摘要:")
    summary = generator.generate_summary(test_errors)
    print(summary)
    
    print("\n" + "=" * 60)


# =============================================================================
# 示例 7: 数据源故障转移
# =============================================================================

def example_data_source_failover():
    """示例：数据源故障转移"""
    print("=" * 60)
    print("示例 7: 数据源故障转移")
    print("=" * 60)
    
    # 模拟数据源
    class MockProvider:
        def __init__(self, name, fail_rate=0.5):
            self.name = name
            self.fail_rate = fail_rate
            self.call_count = 0
        
        def get_quote(self, code):
            self.call_count += 1
            if random.random() < self.fail_rate:
                raise NetworkError(f"{self.name} 失败")
            return {"code": code, "price": random.uniform(10, 100), "source": self.name}
    
    # 创建故障转移管理器
    failover = DataSourceFailover()
    
    # 注册数据源（主数据源失败率高，备用较低）
    providers = [
        MockProvider("腾讯财经", fail_rate=0.8),   # 主数据源，但今天不稳定
        MockProvider("yfinance", fail_rate=0.5),   # 备用 1
        MockProvider("AKShare", fail_rate=0.3),    # 备用 2，最稳定
    ]
    
    failover.register_data_sources(
        "quote_provider",
        sources=providers,
        priorities=[0, 1, 2]
    )
    
    # 执行带故障转移
    def fetch_quote(source, code):
        return source.get_quote(code)
    
    print("尝试获取股票行情（自动故障转移）...")
    try:
        result = failover.execute_with_failover(
            provider_name="quote_provider",
            operation="get_quote",
            func=fetch_quote,
            code="sh600519"
        )
        print(f"\n✓ 成功获取：{result}")
    except Exception as e:
        print(f"\n✗ 所有数据源都失败：{e}")
    
    # 显示各数据源调用次数
    print("\n数据源调用统计:")
    for p in providers:
        print(f"  {p.name}: {p.call_count} 次")
    
    print("\n" + "=" * 60)


# =============================================================================
# 示例 8: 完整错误处理链
# =============================================================================

def example_complete_error_chain():
    """示例：完整错误处理链"""
    print("=" * 60)
    print("示例 8: 完整错误处理链")
    print("=" * 60)
    
    # 模拟 API 调用
    def call_stock_api(code: str):
        """模拟股票 API 调用"""
        if code == "invalid":
            raise Exception("404 Not Found")
        if random.random() < 0.3:
            raise TimeoutError("API 响应超时")
        return {"code": code, "price": random.uniform(10, 100)}
    
    # 完整处理流程
    classifier = ErrorClassifier()
    recovery = RecoveryManager()
    generator = ErrorMessageGenerator(language="zh")
    
    test_codes = ["sh600519", "invalid", "sz000001"]
    
    for code in test_codes:
        print(f"\n处理股票：{code}")
        print("-" * 40)
        
        try:
            # 带重试的执行
            result = recovery.execute_with_retry(
                call_stock_api,
                code,
                retry_config=RetryConfig(max_retries=2, base_delay=0.3),
                on_retry=lambda a, e, d: print(f"  重试 #{a}: {e}")
            )
            
            print(f"✓ 成功：{result}")
        
        except Exception as e:
            # 分类错误
            classified = classifier.classify(e, context={"code": code})
            
            # 生成用户消息
            message = generator.generate(
                classified.classified_error,
                MessageDetailLevel.STANDARD
            )
            
            print(f"✗ 失败")
            print(f"  标题：{message.title}")
            print(f"  消息：{message.message}")
            print(f"  建议：{message.suggestion}")
    
    print("\n" + "=" * 60)


# =============================================================================
# 主函数
# =============================================================================

def run_all_examples():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("BobQuant 错误处理系统 - 使用示例集")
    print("=" * 60 + "\n")
    
    example_error_classification()
    example_retry_mechanism()
    example_circuit_breaker()
    example_fallback_strategy()
    example_decorators()
    example_user_messages()
    example_data_source_failover()
    example_complete_error_chain()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_examples()
