# BobQuant v3.0 使用示例

**版本**: v3.0.0  
**最后更新**: 2026-04-11

---

## 📖 目录

1. [快速开始](#快速开始)
2. [配置系统示例](#配置系统示例)
3. [权限系统示例](#权限系统示例)
4. [错误处理示例](#错误处理示例)
5. [遥测系统示例](#遥测系统示例)
6. [工具系统示例](#工具系统示例)
7. [完整交易流程](#完整交易流程)
8. [高级用法](#高级用法)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
pip install -r requirements.txt
```

### 2. 创建配置文件

```bash
mkdir -p config
cat > config/bobquant.json5 << 'EOF'
{
  // 系统配置
  system: {
    name: "BobQuant",
    version: "3.0",
    mode: "simulation",  // simulation, real, backtest
    log_level: "INFO",
    debug: false,
  },
  
  // 账户配置
  account: {
    initial_capital: 1000000,
    commission_rate: 0.0005,
    stamp_duty_rate: 0.001,
    max_position_pct: 0.10,
  },
  
  // 数据源配置
  data: {
    primary: "tencent",
    fallback: "baostock",
    history_days: 60,
  },
  
  // 交易时段
  trading_hours: {
    morning_start: "09:25",
    morning_end: "11:35",
    afternoon_start: "12:55",
    afternoon_end: "15:05",
  },
  
  // 股票池
  stock_pool: [
    { code: "000001.SZ", name: "平安银行", strategy: "dual_macd" },
    { code: "600519.SH", name: "贵州茅台", strategy: "bollinger" },
  ],
  
  // 风控配置
  risk_control: {
    stop_loss: { enabled: true, pct: -0.08 },
    trailing_stop: { enabled: true, activation_pct: 0.05, drawdown_pct: 0.02 },
  },
  
  // 通知配置
  notify: {
    feishu: {
      enabled: true,
      user_id: "${env:FEISHU_USER_ID}",  // 从环境变量读取
    },
  },
  
  // 日志配置
  log: {
    dir: "logs",
    max_size: 10485760,
    backup_count: 10,
  },
}
EOF
```

### 3. 运行主程序

```bash
# 设置环境变量
export FEISHU_USER_ID="ou_xxxxxxxxxx"

# 运行
python -m bobquant.main
```

---

## ⚙️ 配置系统示例

### 示例 1: 使用 SecretRef 保护敏感信息

```json5
{
  account: {
    // 从环境变量读取
    api_key: "${env:API_KEY}",
    
    // 从文件读取
    api_secret: "${file:~/.bobquant/secret.txt}",
    
    // 从命令读取（如 vault）
    api_token: "${cmd:vault kv get -field=token secret/bobquant}",
  },
}
```

```python
from bobquant.config import ConfigLoader, SecretRef

# 加载配置并自动解析 SecretRef
loader = ConfigLoader("config/bobquant.json5")
config = loader.load_with_secrets()

# 访问已解析的配置
api_key = config.account.api_key  # 已是实际值，不是引用
```

### 示例 2: 5 层配置继承

```json5
{
  // 第 1 层：全局默认
  global_defaults: {
    system: { mode: "simulation", log_level: "INFO" },
    account: { initial_capital: 1000000, commission_rate: 0.0005 },
  },
  
  // 第 2 层：策略级配置
  strategy_configs: {
    "dual_macd": {
      strategy_name: "dual_macd",
      strategy: {
        dual_macd: { fast: 12, slow: 26, signal: 9 },
      },
    },
    "bollinger": {
      strategy_name: "bollinger",
      strategy: {
        bollinger: { period: 20, std_dev: 2.0 },
      },
    },
  },
  
  // 第 3 层：渠道级配置
  channel_configs: {
    "ctp": {
      channel: "ctp",
      account: { commission_rate: 0.0003 },  // CTP 佣金更低
    },
    "xtp": {
      channel: "xtp",
      account: { commission_rate: 0.00025 },
    },
  },
  
  // 第 4 层：账户级配置
  account_configs: {
    "account_001": {
      account_id: "account_001",
      account: { initial_capital: 2000000 },  // 这个账户资金更多
    },
  },
  
  // 第 5 层：组级配置
  group_configs: {
    "group_alpha": {
      group_id: "group_alpha",
      risk_control: {
        stop_loss: { pct: -0.05 },  // 更严格的止损
      },
    },
  },
  
  // 激活的配置
  active_strategy: "dual_macd",
  active_channel: "ctp",
  active_account: "account_001",
  active_group: "group_alpha",
}
```

```python
from bobquant.config import ConfigLoader

loader = ConfigLoader("config/bobquant.json5")

# 加载并自动合并 5 层配置
config = loader.load()

# 最终配置优先级：
# group_alpha > account_001 > ctp > dual_macd > global_defaults

print(config.account.commission_rate)  # 0.0003 (来自 ctp 渠道)
print(config.account.initial_capital)  # 2000000 (来自 account_001)
print(config.risk_control.stop_loss.pct)  # -0.05 (来自 group_alpha)
```

### 示例 3: 配置验证

```python
from bobquant.config import ConfigLoader, ConfigValidator

loader = ConfigLoader("config/bobquant.json5")
config = loader.load()

# 创建验证器
validator = ConfigValidator(config)

# Schema 验证
if not validator.validate_schema():
    print("Schema 验证失败:")
    for error in validator.errors:
        print(f"  - {error}")

# 业务规则验证
if not validator.validate_business_rules():
    print("业务规则验证失败:")
    for error in validator.errors:
        print(f"  - {error}")

# 验证 SecretRef
if not validator.validate_secrets():
    print("SecretRef 验证失败:")
    for error in validator.errors:
        print(f"  - {error}")
```

---

## 🔐 权限系统示例

### 示例 1: 基本权限检查

```python
from bobquant.permissions import PermissionEngine, PermissionMode, PermissionRequest

# 创建权限引擎
engine = PermissionEngine(
    mode=PermissionMode.AUTO,  # AI 分类模式
    grace_period_ms=200.0,     # 200ms 防误触
    denial_threshold=3,        # 连续 3 次拒绝后降级
)

# 创建权限请求
request = PermissionRequest(
    action="trade",
    symbol="000001.SZ",
    side="buy",
    quantity=1000,
    price=10.5,
    order_type="limit",
    risk_level="normal",
)

# 检查权限
response = engine.check_permission(request)

if response.granted:
    print(f"✅ 权限已授予：{response.reason}")
else:
    print(f"❌ 权限被拒绝：{response.reason}")
    if response.requires_confirmation:
        print("需要用户确认")
```

### 示例 2: 切换权限模式

```python
from bobquant.permissions import PermissionMode

# 调试模式：允许所有交易
engine.set_mode(PermissionMode.ACCEPT_EDITS)

# 计划模式：只规划不执行
engine.set_mode(PermissionMode.PLAN)

# 跳过风控：完全信任（慎用！）
engine.set_mode(PermissionMode.BYPASS_PERMISSIONS)

# AI 分类：生产环境推荐
engine.set_mode(PermissionMode.AUTO)

# 默认询问：需要用户确认
engine.set_mode(PermissionMode.DEFAULT)
```

### 示例 3: 自定义 AI 分类器

```python
from bobquant.permissions import TradeClassifier

def custom_classifier(request):
    """自定义 AI 分类器"""
    classifier = TradeClassifier()
    
    # 分类交易风险
    risk_level = classifier.classify(
        request.symbol,
        request.side,
        request.quantity,
        request.price
    )
    
    # 自定义决策逻辑
    if risk_level == 'low':
        # 低风险：自动允许
        return {'granted': True, 'reason': '低风险交易'}
    
    elif risk_level == 'normal':
        # 中等风险：检查是否超过阈值
        if request.quantity > 10000:
            return {'granted': False, 'reason': '数量超限 - 需要确认'}
        return {'granted': True, 'reason': '中等风险但数量合理'}
    
    else:
        # 高风险：拒绝
        return {'granted': False, 'reason': '高风险交易 - 拒绝'}

# 设置分类器
engine.classifier_callback = custom_classifier
```

### 示例 4: 规则匹配器

```python
from bobquant.permissions import RuleMatcher

# 创建规则匹配器
matcher = RuleMatcher()

# 添加允许规则
matcher.add_rule({
    'name': 'allow_blue_chips',
    'action': 'allow',
    'symbols': ['600519.SH', '000858.SZ', '000001.SZ'],  # 蓝筹股
    'max_quantity': 10000,
})

# 添加拒绝规则
matcher.add_rule({
    'name': 'deny_st_stocks',
    'action': 'deny',
    'pattern': 'ST.*',  # ST 股票
})

# 添加需要确认的规则
matcher.add_rule({
    'name': 'ask_large_orders',
    'action': 'ask',
    'min_quantity': 50000,
})

# 使用规则匹配器
response = engine.check_permission(request, rule_matcher=matcher)
```

---

## 🛠️ 错误处理示例

### 示例 1: 错误分类

```python
from bobquant.errors import ErrorClassifier, NetworkError, DataError

classifier = ErrorClassifier()

# 分类网络错误
error = NetworkError("连接超时")
classified = classifier.classify(error)

print(f"类别：{classified.category}")      # ErrorCategory.NETWORK
print(f"严重性：{classified.severity}")    # ErrorSeverity.MEDIUM
print(f"可恢复：{classified.recoverable}")  # True
print(f"用户消息：{classified.user_message}")

# 分类数据错误
error = DataNotFoundError("股票数据不存在")
classified = classifier.classify(error)

print(f"类别：{classified.category}")      # ErrorCategory.DATA
print(f"严重性：{classified.severity}")    # ErrorSeverity.HIGH
print(f"可恢复：{classified.recoverable}")  # False (需要用户干预)
```

### 示例 2: 重试机制

```python
from bobquant.errors import retry, RetryStrategy, RecoveryManager, RetryConfig

# 方法 1: 使用装饰器
@retry(
    max_retries=3,
    strategy=RetryStrategy.JITTERED,  # 带抖动的指数退避
    base_delay=1.0,
    max_delay=60.0,
)
def fetch_data_with_retry(code: str):
    return data_provider.get_history(code, days=60)

# 调用（自动重试）
df = fetch_data_with_retry("000001.SZ")

# 方法 2: 使用恢复管理器
recovery = RecoveryManager(
    retry_config=RetryConfig(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=1.0,
    )
)

def on_retry(attempt, error, delay):
    print(f"重试 #{attempt}: {error} (延迟 {delay}s)")

result = recovery.execute_with_retry(
    data_provider.get_history,
    "000001.SZ",
    days=60,
    on_retry=on_retry,
)
```

### 示例 3: 熔断器

```python
from bobquant.errors import circuit_breaker, RecoveryManager, CircuitBreakerConfig

# 方法 1: 使用装饰器
@circuit_breaker(
    failure_threshold=5,   # 5 次失败后打开
    timeout=30.0,          # 30 秒后尝试恢复
    name="market_data_api"
)
def get_market_data(code: str):
    return data_provider.get_quote(code)

# 方法 2: 使用恢复管理器
recovery = RecoveryManager(
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=30.0,
        half_open_max_calls=3,
    )
)

# 检查熔断器状态
status = recovery.get_circuit_breaker_state("market_data_api")
print(f"状态：{status['state']}")
print(f"失败次数：{status['failure_count']}")

# 重置熔断器
recovery.reset_circuit_breaker("market_data_api")
```

### 示例 4: 降级策略

```python
from bobquant.errors import with_fallback, RecoveryManager, DataSourceFailover

# 方法 1: 使用装饰器
def fallback_fetch(code: str):
    """降级函数：使用备用数据源"""
    return backup_provider.get_history(code, days=60)

@with_fallback(fallback_func=fallback_fetch)
def primary_fetch(code: str):
    """主函数：使用主数据源"""
    return primary_provider.get_history(code, days=60)

# 调用（主函数失败时自动使用降级）
df = primary_fetch("000001.SZ")

# 方法 2: 使用数据源故障转移
failover = DataSourceFailover()

# 注册数据源组
failover.register_data_sources(
    "market_data",
    sources=[primary_provider, backup_provider, tertiary_provider],
    priorities=[0, 1, 2],  # 优先级：primary > backup > tertiary
)

# 执行操作（自动故障转移）
result = failover.execute_with_failover(
    provider_name="market_data",
    operation="get_quote",
    func=lambda src, code: src.get_quote(code),
    code="000001.SZ",
)
```

---

## 📊 遥测系统示例

### 示例 1: 初始化遥测

```python
from bobquant.telemetry import (
    init_global_sink,
    TelemetrySink,
    BatchProcessor,
    BatchConfig,
    JSONLPersister,
    PersistenceConfig,
)

# 创建 Sink
sink = init_global_sink(
    max_queue_size=10000,
    enable_backpressure=True,
)

# 创建批处理器
batch_config = BatchConfig(
    batch_size=100,       # 100 条触发
    flush_interval=5.0,   # 或 5 秒触发
)
batch_processor = BatchProcessor(sink=sink, config=batch_config)

# 创建持久化器
persistence_config = PersistenceConfig(
    output_dir="logs/telemetry",
    filename_prefix="bobquant_events",
    rotation_size_mb=100,  # 100MB 轮转
)
persister = JSONLPersister(config=persistence_config)

# 注册消费者
sink.add_consumer(batch_processor.process)
sink.add_consumer(persister.save)

# 启动
sink.start()
```

### 示例 2: 发送事件

```python
from bobquant.telemetry import EventType, TelemetryEvent

# 方法 1: 便捷方法
sink.emit(
    event_type=EventType.ORDER_SUBMITTED,
    event_name="order.submitted",
    attributes={
        "symbol": "000001.SZ",
        "side": "buy",
        "price": 10.5,
        "quantity": 1000,
        "order_type": "limit",
    },
    correlation_id="trade_001",  # 关联 ID，用于追踪
)

# 方法 2: 构建事件对象
event = TelemetryEvent(
    event_type=EventType.ORDER_FILLED,
    event_name="order.filled",
    attributes={
        "symbol": "000001.SZ",
        "fill_price": 10.48,
        "fill_quantity": 1000,
    },
    correlation_id="trade_001",  # 与提交事件关联
)
sink.emit_event(event)
```

### 示例 3: 监控指标

```python
from bobquant.telemetry import get_metrics_registry, MetricType

# 获取指标注册表
registry = get_metrics_registry()

# 增加计数器
registry.increment("bobquant.orders.total", labels={
    "type": "buy",
    "symbol": "000001.SZ",
    "status": "filled",
})

# 设置仪表盘
registry.gauge("bobquant.position.value", value=125000.0, labels={
    "symbol": "000001.SZ",
})

# 记录直方图
registry.histogram("bobquant.latency.order_submit", value=15.5, labels={
    "broker": "ctp",
    "symbol": "000001.SZ",
})

# 查询指标
metrics = registry.get_metric("bobquant.orders.total")
print(f"总订单数：{metrics.value}")

# 导出指标（用于 Prometheus 等）
exported = registry.export_prometheus()
print(exported)
```

### 示例 4: 查询遥测数据

```python
from bobquant.telemetry import JSONLPersister
from pathlib import Path

# 读取持久化的事件
persister = JSONLPersister(config=PersistenceConfig(output_dir="logs/telemetry"))

# 获取最新的事件文件
files = persister.get_files()
latest_file = files[0] if files else None

if latest_file:
    # 读取事件
    events = persister.read_file(latest_file)
    
    # 过滤事件
    order_events = [
        e for e in events
        if e['event_type'] == 'order.submitted'
    ]
    
    # 按关联 ID 分组
    from collections import defaultdict
    trades = defaultdict(list)
    for event in events:
        if event.get('correlation_id'):
            trades[event['correlation_id']].append(event)
    
    # 分析交易链路
    for trade_id, trade_events in trades.items():
        print(f"交易 {trade_id}:")
        for event in trade_events:
            print(f"  - {event['event_name']} @ {event['timestamp_iso']}")
```

---

## 🔧 工具系统示例

### 示例 1: 注册工具

```python
from bobquant.tools import ToolRegistry, register_tool, Tool, ToolResult, ToolContext
from typing import Dict, Any

# 方法 1: 使用装饰器
@register_tool(category="trading")
class OrderTool(Tool):
    name = "order"
    description_text = "执行交易订单"
    
    async def call(self, args: Dict[str, Any], context: ToolContext, on_progress=None):
        # 执行订单
        symbol = args['symbol']
        side = args['side']
        quantity = args['quantity']
        
        # ... 执行逻辑 ...
        
        return ToolResult(data={"status": "success", "order_id": "12345"})

# 方法 2: 手动注册
registry = get_registry()
registry.register(OrderTool, category="trading")
```

### 示例 2: 使用工具

```python
from bobquant.tools import get_registry, ToolContext

# 获取注册表
registry = get_registry()

# 查找工具
order_tool = registry.get("order")

if order_tool:
    # 创建上下文
    context = ToolContext(
        options={},
        messages=[],
    )
    
    # 执行工具
    result = await order_tool.call(
        args={
            "symbol": "000001.SZ",
            "side": "buy",
            "quantity": 1000,
            "price": 10.5,
        },
        context=context,
    )
    
    print(f"订单结果：{result.data}")
```

### 示例 3: 审计日志

```python
from bobquant.tools import AuditLogger, audit_action

# 方法 1: 使用审计记录器
audit_logger = AuditLogger()
audit_logger.log(
    action="trade.execute",
    details={
        "symbol": "000001.SZ",
        "side": "buy",
        "quantity": 1000,
        "price": 10.5,
        "user": "trader_001",
    },
)

# 方法 2: 使用便捷函数
audit_action(
    "risk.check",
    {
        "symbol": "000001.SZ",
        "action": "sell",
        "result": "allowed",
    }
)
```

---

## 📈 完整交易流程

### 示例：运行一次完整交易检查

```python
from bobquant.main import BobQuantEngine
from pathlib import Path

# 1. 创建引擎
engine = BobQuantEngine(
    config_path=Path("config/bobquant.json5")
)

# 2. 初始化
if not engine.initialize():
    print("❌ 初始化失败")
    exit(1)

print("✅ 引擎初始化完成")

# 3. 执行一次交易检查
print("\n📊 执行交易检查...")
trades = engine.run_check()

if trades:
    print(f"\n✅ 执行 {len(trades)} 笔交易:")
    for trade in trades:
        print(f"  - {trade.get('action')} {trade.get('code')} {trade.get('shares')}股 @ ¥{trade.get('price'):.2f}")
else:
    print("\n⚪ 无交易信号")

# 4. 查看账户汇总
print("\n💰 账户汇总:")
summary = engine.portfolio_summary()

# 5. 优雅关闭
engine.shutdown()
```

### 输出示例

```
🚀 BobQuant v3.0 引擎初始化完成
📋 加载配置...
✅ 配置加载成功 (模式：simulation)
📊 初始化遥测系统...
  ✅ 遥测系统就绪 (目录：logs/telemetry)
📈 初始化数据提供商...
  ✅ 数据提供商就绪 (tencent)
💰 初始化账户...
  ✅ 账户就绪 (初始资金：¥1,000,000)
⚡ 初始化执行器...
  ✅ 执行器就绪
🧠 初始化策略引擎...
  ⚡ 高频交易引擎就绪
  🧠 综合决策引擎就绪 (ML=True, 情绪=True)
🔐 初始化权限系统...
  🔐 权限模式：AI 分类 (生产模式)
  ✅ AI 分类器已配置
🔧 注册工具...
  ✅ 工具注册表就绪 (已注册：0 个工具)

📊 执行交易检查...
📊 检查交易信号（v3.0 集成版）...
  ⚡ Phase 0: 高频交易策略...
  🎯 高频信号：平安银行 - 剥头皮 - 短期超买
  📌 Phase 1: 网格做 T...
  📌 Phase 2: 风控...
  📌 Phase 3: 策略信号...
  ✅ 执行 1 笔交易

✅ 执行 1 笔交易:
  - 买入 000001.SZ 1000 股 @ ¥10.50

============================================================
📊 账户汇总
============================================================
总资产：¥1,025,430 (现金¥25,430 + 持仓¥1,000,000)
盈亏：¥+25,430 (+2.54%)
持仓：5 只
============================================================

🛑 关闭 BobQuant 引擎...
✅ 引擎已关闭
```

---

## 🎓 高级用法

### 示例 1: 自定义策略

```python
from bobquant.strategy.engine import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    """自定义策略"""
    
    def check(self, code, name, quote, df, position, config):
        # 实现你的策略逻辑
        if df['close'].iloc[-1] > df['close'].iloc[-5]:
            return {
                'signal': 'buy',
                'reason': '5 日上涨',
                'strength': 'strong',
            }
        return {'signal': None}

# 注册策略
from bobquant.strategy.engine import register_strategy
register_strategy("my_custom", MyCustomStrategy)
```

### 示例 2: 自定义数据源

```python
from bobquant.data.provider import BaseDataProvider

class MyCustomProvider(BaseDataProvider):
    """自定义数据提供商"""
    
    def get_quote(self, code):
        # 从你的数据源获取实时行情
        return {'current': 10.5, 'open': 10.3, 'high': 10.8, 'low': 10.2}
    
    def get_history(self, code, days=60):
        # 从你的数据源获取历史数据
        import pandas as pd
        return pd.DataFrame({...})

# 注册数据源
from bobquant.data.provider import register_provider
register_provider("my_custom", MyCustomProvider)
```

### 示例 3: 自定义通知渠道

```python
from bobquant.notify.base import BaseNotifier

class WeChatNotifier(BaseNotifier):
    """微信通知"""
    
    def send(self, title, message):
        # 发送微信通知
        pass

# 使用
from bobquant.notify import get_notifier
notifier = get_notifier("wechat")
notifier.send("交易通知", "买入 000001.SZ 1000 股")
```

---

## 📚 更多资源

- [集成测试报告](INTEGRATION_REPORT.md)
- [配置系统文档](config/README.md)
- [权限系统文档](permissions/README.md)
- [错误处理文档](errors/README.md)
- [遥测系统文档](telemetry/README.md)
- [工具系统文档](tools/README.md)

---

**最后更新**: 2026-04-11  
**作者**: Bob (AI Assistant) ⚡
