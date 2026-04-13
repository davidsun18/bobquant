# BobQuant 错误处理系统 v1.0

灵感来自 Claude Code 的错误处理设计，提供标准化、可恢复、用户友好的错误处理机制。

## 📋 目录

- [快速开始](#快速开始)
- [错误类型清单](#错误类型清单)
- [错误分类流程](#错误分类流程)
- [恢复机制](#恢复机制)
- [使用示例](#使用示例)
- [API 参考](#api-参考)

---

## 🚀 快速开始

### 基本使用

```python
from bobquant.errors import (
    BobQuantError,
    ErrorClassifier,
    RecoveryManager,
    ErrorMessageGenerator,
    retry,
    with_fallback,
)

# 1. 捕获并分类错误
classifier = ErrorClassifier()

try:
    # 可能出错的代码
    result = risky_operation()
except Exception as e:
    classified = classifier.classify(e)
    print(f"分类：{classified.category}")
    print(f"严重程度：{classified.severity}")
    print(f"可恢复：{classified.recoverable}")

# 2. 自动重试
recovery = RecoveryManager()

result = recovery.execute_with_retry(
    risky_operation,
    max_retries=3,
    on_retry=lambda attempt, error, delay: print(f"重试 {attempt}: {error}")
)

# 3. 使用装饰器
@retry(max_retries=3, base_delay=1.0)
def fetch_data():
    return api_call()

# 4. 生成用户友好的消息
generator = ErrorMessageGenerator()

try:
    operation()
except BobQuantError as e:
    message = generator.generate(e)
    print(message.to_string())
```

---

## 📝 错误类型清单（20+ 种）

### 网络与 API 错误 (5 种)

| 错误类型 | 说明 | 可恢复 | 严重程度 |
|---------|------|--------|---------|
| `APIError` | API 调用失败 | ✅ | 高 |
| `NetworkError` | 网络连接失败 | ✅ | 高 |
| `TimeoutError` | 请求超时 | ✅ | 中 |
| `RateLimitError` | 触发速率限制 | ✅ | 中 |
| `AuthenticationError` | 认证失败 | ❌ | 严重 |

### 数据错误 (5 种)

| 错误类型 | 说明 | 可恢复 | 严重程度 |
|---------|------|--------|---------|
| `DataError` | 数据相关错误基类 | - | 高 |
| `DataNotFoundError` | 数据不存在 | ❌ | 中 |
| `DataFormatError` | 数据格式错误 | ❌ | 高 |
| `DataValidationError` | 数据验证失败 | ❌ | 高 |
| `DataStaleError` | 数据过期 | ✅ | 中 |

### 交易错误 (6 种)

| 错误类型 | 说明 | 可恢复 | 严重程度 |
|---------|------|--------|---------|
| `TradingError` | 交易相关错误基类 | - | 高 |
| `OrderError` | 订单错误 | - | 高 |
| `OrderRejectedError` | 订单被拒绝 | ❌ | 高 |
| `InsufficientFundsError` | 资金不足 | ❌ | 高 |
| `PositionError` | 持仓错误 | - | 中 |
| `MarketClosedError` | 市场关闭 | ✅ | 中 |

### 策略错误 (4 种)

| 错误类型 | 说明 | 可恢复 | 严重程度 |
|---------|------|--------|---------|
| `StrategyError` | 策略相关错误基类 | - | 高 |
| `SignalError` | 信号生成失败 | ✅ | 中 |
| `ConfigurationError` | 配置错误 | ❌ | 高 |
| `BacktestError` | 回测失败 | ✅ | 高 |

### 系统错误 (4 种)

| 错误类型 | 说明 | 可恢复 | 严重程度 |
|---------|------|--------|---------|
| `SystemError` | 系统相关错误基类 | - | 严重 |
| `FileSystemError` | 文件系统错误 | ❌ | 高 |
| `DatabaseError` | 数据库错误 | ❌ | 严重 |
| `MemoryError` | 内存不足 | ❌ | 严重 |

### 外部服务错误 (2 种)

| 错误类型 | 说明 | 可恢复 | 严重程度 |
|---------|------|--------|---------|
| `ExternalServiceError` | 外部服务错误基类 | ✅ | 高 |
| `ThirdPartyAPIError` | 第三方 API 错误 | ✅ | 高 |

---

## 🔄 错误分类流程图

```
原始异常 (Exception)
       │
       ▼
┌─────────────────────┐
│   ErrorClassifier   │
│     规则匹配        │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  判断错误类型       │
│  - 网络错误？       │
│  - 数据错误？       │
│  - 交易错误？       │
│  - 系统错误？       │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  确定严重程度       │
│  - Low              │
│  - Medium           │
│  - High             │
│  - Critical         │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  判断可恢复性       │
│  - recoverable=true │
│  - recoverable=false│
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  选择处理策略       │
│  - retry_with_backoff│
│  - retry_immediately│
│  - wait_and_retry   │
│  - manual_intervention│
│  - reconfigure      │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  生成用户消息       │
│  ErrorMessageGenerator│
└─────────────────────┘
```

---

## 🔧 恢复机制

### 1. 重试机制（二次退避）

```python
from bobquant.errors import RecoveryManager, RetryConfig, RetryStrategy

# 配置重试
config = RetryConfig(
    max_retries=3,
    strategy=RetryStrategy.JITTERED,  # 带抖动的指数退避
    base_delay=1.0,    # 基础延迟 1 秒
    max_delay=60.0,    # 最大延迟 60 秒
)

recovery = RecoveryManager(retry_config=config)

# 执行带重试的操作
result = recovery.execute_with_retry(
    api_call,
    on_retry=lambda attempt, error, delay: print(
        f"重试 #{attempt}, 延迟 {delay}s: {error}"
    )
)
```

**退避策略说明：**

| 策略 | 延迟计算 | 适用场景 |
|-----|---------|---------|
| `FIXED` | 固定延迟 | 简单重试 |
| `LINEAR` | delay = base × attempt | 线性增长 |
| `EXPONENTIAL` | delay = base × 2^(attempt-1) | 指数增长 |
| `JITTERED` | 指数 + 随机抖动 | 避免并发冲突（推荐） |

### 2. 熔断器模式

```python
from bobquant.errors import RecoveryManager, CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,    # 5 次失败后熔断
    success_threshold=2,    # 2 次成功后恢复
    timeout=30.0,           # 30 秒后尝试恢复
)

recovery = RecoveryManager(circuit_breaker_config=config)

# 检查熔断器状态
state = recovery.get_circuit_breaker_state("api_service")
print(state)  # {'state': 'closed', 'failure_count': 0, ...}
```

**熔断器状态：**
- `CLOSED`（关闭）：正常状态，允许调用
- `OPEN`（打开）：熔断状态，拒绝调用
- `HALF_OPEN`（半开）：测试恢复，允许有限调用

### 3. 降级策略（数据源切换）

```python
from bobquant.errors import DataSourceFailover
from data.provider import get_provider

# 注册多个数据源
failover = DataSourceFailover()

failover.register_data_sources(
    "quote_provider",
    sources=[
        get_provider("tencent"),      # 主数据源
        get_provider("yfinance"),     # 备用 1
        get_provider("akshare"),      # 备用 2
    ],
    priorities=[0, 1, 2]  # 优先级
)

# 自动故障转移
def fetch_quote(source, code):
    return source.get_quote(code)

result = failover.execute_with_failover(
    provider_name="quote_provider",
    operation="get_quote",
    func=fetch_quote,
    code="sh600519"
)
```

### 4. 装饰器用法

```python
from bobquant.errors import retry, with_fallback, circuit_breaker

# 重试装饰器
@retry(max_retries=3, base_delay=1.0)
def fetch_data():
    return api_call()

# 降级装饰器
def fallback_fetch():
    return cached_data()

@with_fallback(fallback_fetch)
def fetch_data():
    return api_call()

# 熔断器装饰器
@circuit_breaker(failure_threshold=5, timeout=30.0)
def critical_operation():
    return important_api_call()
```

---

## 💬 用户友好的错误消息

```python
from bobquant.errors import (
    ErrorMessageGenerator,
    MessageDetailLevel,
    generate_error_message,
)

generator = ErrorMessageGenerator(language="zh")

try:
    risky_operation()
except BobQuantError as e:
    # 简洁模式
    brief = generator.generate(e, MessageDetailLevel.BRIEF)
    print(brief.title)  # "网络连接问题"
    print(brief.message)  # "无法连接到网络..."
    
    # 标准模式
    standard = generator.generate(e, MessageDetailLevel.STANDARD)
    print(standard.to_string())
    
    # 详细模式（包含技术细节）
    detailed = generator.generate(e, MessageDetailLevel.DETAILED)
    print(detailed.technical_details)
```

**输出示例：**

```
标题：网络连接问题
消息：无法连接到网络，请检查您的网络连接；超时时间：30 秒

建议：检查网络连接和防火墙设置

技术细节：
错误类型：TimeoutError
分类：network
严重程度：中
时间：2026-04-11 01:30:45
原始错误：requests.exceptions.Timeout: Connection timed out
可自动恢复：是
```

---

## 📚 API 参考

### ErrorClassifier

```python
classifier = ErrorClassifier()

# 分类单个错误
classified = classifier.classify(exception, context={"code": "sh600519"})

# 批量分类
classified_list = classifier.classify_batch([e1, e2, e3])

# 获取分类摘要
summary = classifier.get_category_summary(classified_list)
```

### RecoveryManager

```python
recovery = RecoveryManager(
    retry_config=RetryConfig(...),
    circuit_breaker_config=CircuitBreakerConfig(...)
)

# 执行带重试
result = recovery.execute_with_retry(func, *args, **kwargs)

# 执行带降级
result = recovery.execute_with_fallback(
    primary_func, *args,
    fallbacks=[fallback1, fallback2]
)

# 熔断器管理
state = recovery.get_circuit_breaker_state("service_name")
recovery.reset_circuit_breaker("service_name")
```

### ErrorMessageGenerator

```python
generator = ErrorMessageGenerator(language="zh")

# 生成单条消息
message = generator.generate(error, MessageDetailLevel.STANDARD)

# 批量生成
messages = generator.generate_batch([e1, e2, e3])

# 生成摘要
summary = generator.generate_summary([e1, e2, e3])
```

---

## 🔗 集成示例

### 与数据源集成

```python
# data/provider.py
from bobquant.errors import (
    RecoveryManager,
    DataSourceFailover,
    DataNotFoundError,
    TimeoutError,
)

class TencentProvider(DataProvider):
    def __init__(self, retry=2, timeout=3, max_workers=10):
        self.recovery = RecoveryManager()
        self.failover = DataSourceFailover(self.recovery)
        
    def get_quote(self, code):
        return self.recovery.execute_with_retry(
            self._fetch_quote,
            code,
            max_retries=self.retry,
            on_retry=self._on_retry
        )
    
    def _fetch_quote(self, code):
        # 实际的网络请求
        response = requests.get(url, timeout=self.timeout)
        if response.status_code == 404:
            raise DataNotFoundError(code=code)
        return parse_response(response)
    
    def _on_retry(self, attempt, error, delay):
        logger.warning(f"重试 #{attempt}: {error}")
```

### 与交易系统集成

```python
# broker/base.py
from bobquant.errors import (
    InsufficientFundsError,
    OrderRejectedError,
    MarketClosedError,
    retry,
    circuit_breaker,
)

class BaseBroker:
    @circuit_breaker(failure_threshold=3)
    def submit_order(self, code, action, shares, price):
        try:
            return self._execute_order(code, action, shares, price)
        except APIError as e:
            if "insufficient" in str(e).lower():
                raise InsufficientFundsError(
                    required=shares * price,
                    available=self.cash
                )
            elif "rejected" in str(e).lower():
                raise OrderRejectedError(reason=str(e))
            elif "market closed" in str(e).lower():
                raise MarketClosedError()
            raise
```

---

## 🎯 最佳实践

1. **始终捕获 BobQuantError**：在边界处捕获并转换为用户消息
2. **使用装饰器**：在函数级别声明重试/熔断策略
3. **记录错误上下文**：便于调试和问题追踪
4. **区分可恢复性**：不是所有错误都值得重试
5. **优雅降级**：提供备用方案而非直接失败
6. **用户友好**：技术细节仅用于日志，用户看到简洁消息

---

## 📊 错误处理统计

系统会自动记录：
- 错误分类分布
- 重试成功率
- 熔断器触发次数
- 降级切换次数

通过 `RecoveryManager` 和 `ErrorClassifier` 的方法获取统计信息。
