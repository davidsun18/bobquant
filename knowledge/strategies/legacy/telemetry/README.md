# BobQuant Telemetry System - 监控与遥测系统

> 借鉴 Claude Code 的遥测架构，为 BobQuant 提供完整的监控、追踪和数据分析能力

## 📐 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BobQuant Telemetry System                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Producers  │───▶│  Telemetry   │───▶│    Batch     │               │
│  │  (Modules)   │    │     Sink     │    │  Processor   │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                    │                       │
│         │                   │                    ▼                       │
│         │                   │           ┌──────────────┐                │
│         │                   │           │   PII        │                │
│         │                   │           │   Masker     │                │
│         │                   │           └──────────────┘                │
│         │                   │                    │                       │
│         │                   │                    ▼                       │
│         │                   │           ┌──────────────┐                │
│         │                   │           │ Persistence  │                │
│         │                   │           │   (JSONL)    │                │
│         │                   │           └──────────────┘                │
│         │                   │                    │                       │
│         ▼                   ▼                    ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │    Cache     │◀───│   Metrics    │◀───│ OpenTelemetry│               │
│  │ (Memory+Disk)│    │   Registry   │    │  (Optional)  │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🗂️ 模块结构

```
telemetry/
├── __init__.py                 # 模块入口
├── sink.py                     # 遥测 Sink（生产 - 消费解耦）
├── batch.py                    # 批处理器（大小 + 时间双触发）
├── persistence.py              # 磁盘持久化（JSONL 格式）
├── retry.py                    # 退避重试机制
├── pii.py                      # PII 脱敏保护
├── cache.py                    # 多级缓存（内存→磁盘）
├── opentelemetry_integration.py # OpenTelemetry 集成（可选）
├── metrics.py                  # 监控指标注册表
├── example_usage.py            # 使用示例
└── README.md                   # 本文档
```

## 🚀 快速开始

### 1. 基础使用

```python
from bobquant.telemetry import TelemetrySink, EventType

# 创建 Sink
sink = TelemetrySink(max_queue_size=10000)
sink.start()

# 发送事件
sink.emit(
    event_type=EventType.ORDER_SUBMITTED,
    event_name="order.submitted",
    attributes={"symbol": "000001.SZ", "price": 10.5, "volume": 1000}
)

# 停止
sink.stop()
```

### 2. 完整系统集成

```python
from bobquant.telemetry.example_usage import TelemetrySystem

# 初始化系统
telemetry = TelemetrySystem(
    data_dir="./telemetry_data",
    enable_masking=True,
    enable_otel=False,
)

# 记录交易事件
telemetry.record_order_submitted(
    order_id="ORD-001",
    symbol="000001.SZ",
    price=10.5,
    volume=1000,
    direction="buy",
)

# 获取统计
stats = telemetry.get_stats()

# 停止系统
telemetry.stop()
```

## 📋 核心组件

### 1. TelemetrySink - 遥测接收器

**职责：**
- 解耦事件生产与消费
- 线程安全的队列管理
- 背压控制（防止内存爆炸）
- 全局序列号维护

**配置参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_queue_size | int | 10000 | 最大队列大小 |
| session_id | str | 自动生成 | 会话 ID |
| enable_backpressure | bool | True | 是否启用背压 |

### 2. BatchProcessor - 批处理器

**触发机制：**
- **大小触发**：批次达到 `max_batch_size` 立即刷新
- **时间触发**：距离上次刷新超过 `max_wait_time` 强制刷新

**配置参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_batch_size | int | 100 | 最大批次大小 |
| max_wait_time | float | 5.0 | 最大等待时间（秒） |
| max_queue_size | int | 1000 | 批次队列大小 |

### 3. JSONLPersister - 磁盘持久化

**文件格式：**
```jsonl
{"event_id": "uuid", "event_type": "order.submitted", "timestamp": 1234567890.123, ...}
{"event_id": "uuid", "event_type": "order.filled", "timestamp": 1234567891.456, ...}
```

**特性：**
- 自动文件轮转（基于大小和时间）
- 原子写入（临时文件 + 重命名）
- 可选压缩（.gz）
- 自动清理过期文件

**配置参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| base_dir | str | ./telemetry_data | 存储目录 |
| max_file_size | int | 100 | 单文件最大 MB |
| max_file_age | int | 24 | 文件最大保存小时 |
| compression | bool | False | 是否压缩 |
| retention_days | int | 30 | 保留天数 |

### 4. RetryConfig - 退避重试

**退避策略：**
```
delay = base_delay × (exponential_base ^ attempt) + jitter
```

**配置参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_retries | int | 3 | 最大重试次数 |
| base_delay | float | 0.1 | 基础延迟（秒） |
| max_delay | float | 30.0 | 最大延迟（秒） |
| exponential_base | float | 2.0 | 指数基数 |
| jitter | bool | True | 是否启用抖动 |

**使用示例：**
```python
from bobquant.telemetry import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=0.1)
def save_to_disk(data):
    # 可能失败的操作
    pass
```

### 5. PIIMasker - PII 脱敏

**预定义规则：**
| 字段类型 | 脱敏方式 | 示例 |
|----------|----------|------|
| 手机号 | 保留前 3 后 4 | 138****5678 |
| 邮箱 | 保留首字母 + 域名 | d***@example.com |
| 身份证 | 保留前 6 后 4 | 110101********1234 |
| 银行卡 | 保留前 4 后 4 | 6222 **** **** 1234 |
| 用户 ID | 哈希处理 | hash_a1b2c3d4e5f6 |

**脱敏级别：**
- `NONE`: 不脱敏
- `PARTIAL`: 部分脱敏（保留首尾）
- `FULL`: 完全脱敏
- `HASH`: 哈希处理（可关联分析）

**使用示例：**
```python
from bobquant.telemetry import PIIMasker

masker = PIIMasker()
masked_phone = masker.mask_value("13812345678", "phone")
# 输出：138****5678
```

### 6. MultiLevelCache - 多级缓存

**架构：**
```
读取：内存缓存 → 磁盘缓存 → 回填内存
写入：内存缓存 → 异步写入磁盘
```

**配置参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| memory_max_size | int | 10000 | 内存最大条目 |
| memory_ttl | float | 3600 | 内存 TTL（秒） |
| disk_path | str | ./cache.db | 磁盘数据库路径 |
| disk_ttl | float | 86400 | 磁盘 TTL（秒） |

### 7. MetricsRegistry - 指标注册表

**支持的指标类型：**
- `COUNTER`: 计数器（只增不减）
- `GAUGE`: 仪表盘（可增可减）
- `HISTOGRAM`: 直方图（分布统计）
- `SUMMARY`: 摘要（分位数）

**导出格式：**
- 字典格式（Python）
- Prometheus 格式（监控集成）

## 📊 监控指标清单

### 交易指标
| 指标名称 | 类型 | 单位 | 说明 |
|----------|------|------|------|
| bobquant.orders.total | COUNTER | orders | 订单总数 |
| bobquant.orders.filled | COUNTER | orders | 成交订单数 |
| bobquant.orders.rejected | COUNTER | orders | 被拒绝订单数 |
| bobquant.volume.traded | COUNTER | shares | 成交总股数 |
| bobquant.amount.traded | COUNTER | CNY | 成交总金额 |
| bobquant.position.current | GAUGE | shares | 当前持仓数量 |
| bobquant.position.value | GAUGE | CNY | 当前持仓市值 |
| bobquant.pnl.realized | COUNTER | CNY | 已实现盈亏 |
| bobquant.pnl.unrealized | GAUGE | CNY | 未实现盈亏 |

### 性能指标
| 指标名称 | 类型 | 单位 | 说明 |
|----------|------|------|------|
| bobquant.latency.order_submit | HISTOGRAM | ms | 订单提交延迟 |
| bobquant.latency.market_data | HISTOGRAM | ms | 行情数据延迟 |
| bobquant.latency.signal_generation | HISTOGRAM | ms | 信号生成延迟 |
| bobquant.throughput.ticks | GAUGE | ticks/s | Tick 处理吞吐量 |
| bobquant.throughput.orders | GAUGE | orders/s | 订单处理吞吐量 |

### 系统指标
| 指标名称 | 类型 | 单位 | 说明 |
|----------|------|------|------|
| bobquant.system.cpu_usage | GAUGE | % | CPU 使用率 |
| bobquant.system.memory_usage | GAUGE | MB | 内存使用量 |
| bobquant.system.disk_usage | GAUGE | MB | 磁盘使用量 |
| bobquant.system.thread_count | GAUGE | threads | 线程数量 |

### 风控指标
| 指标名称 | 类型 | 单位 | 说明 |
|----------|------|------|------|
| bobquant.risk.exposure | GAUGE | CNY | 风险敞口 |
| bobquant.risk.drawdown | GAUGE | % | 当前回撤 |
| bobquant.risk.var | GAUGE | CNY | 风险价值 (VaR) |
| bobquant.risk.position_ratio | GAUGE | % | 持仓比例 |
| bobquant.risk.concentration | GAUGE | % | 持仓集中度 |

### 策略指标
| 指标名称 | 类型 | 单位 | 说明 |
|----------|------|------|------|
| bobquant.strategy.signals | COUNTER | signals | 策略信号数量 |
| bobquant.strategy.win_rate | GAUGE | % | 策略胜率 |
| bobquant.strategy.sharpe_ratio | GAUGE | ratio | 夏普比率 |
| bobquant.strategy.max_drawdown | GAUGE | % | 最大回撤 |

### 遥测指标
| 指标名称 | 类型 | 单位 | 说明 |
|----------|------|------|------|
| bobquant.telemetry.events_emitted | COUNTER | events | emitted 事件数 |
| bobquant.telemetry.events_dropped | COUNTER | events | 丢弃事件数 |
| bobquant.telemetry.batch_size | HISTOGRAM | events | 批处理大小 |
| bobquant.telemetry.persistence_latency | HISTOGRAM | ms | 持久化延迟 |

## 🔧 OpenTelemetry 集成

### 安装依赖
```bash
pip install opentelemetry-api
pip install opentelemetry-sdk
pip install opentelemetry-exporter-otlp
```

### 配置使用
```python
from bobquant.telemetry import OpenTelemetryIntegration, OpenTelemetryConfig

config = OpenTelemetryConfig(
    service_name="bobquant",
    exporter_type=ExporterType.OTLP,
    otlp_endpoint="http://localhost:4317",
)

otel = OpenTelemetryIntegration(config)

# 创建追踪 Span
with otel.trace("order_execution", {"symbol": "000001.SZ"}):
    execute_order()

# 记录指标
otel.record_metric("orders.count", 1, {"type": "buy"})

# 关闭
otel.shutdown()
```

## 📁 数据存储结构

```
telemetry_data/
├── events_20260411_014900.jsonl    # 事件数据文件
├── events_20260411_024900.jsonl
├── ...
└── cache.db                         # 缓存数据库
```

## 🔍 查询历史数据

```python
from bobquant.telemetry import JSONLPersister, PersistenceConfig

config = PersistenceConfig(base_dir="./telemetry_data")
persister = JSONLPersister(config)

# 按时间范围查询
for event in persister.read_events(
    start_time=1712764800,  # 2026-04-11 00:00:00
    end_time=1712851200,    # 2026-04-12 00:00:00
    event_type="order.filled"
):
    print(event.to_dict())
```

## 📈 最佳实践

### 1. 性能优化
- 使用批处理减少 I/O 次数
- 合理设置批次大小（50-200 事件/批）
- 启用压缩节省磁盘空间
- 定期清理过期数据

### 2. 数据安全
- 生产环境启用 PII 脱敏
- 敏感字段使用 HASH 级别脱敏
- 定期备份遥测数据
- 限制数据访问权限

### 3. 监控告警
- 监控事件丢弃率（>1% 告警）
- 监控持久化延迟（>1s 告警）
- 监控磁盘使用量（>80% 告警）
- 监控队列积压（>5000 告警）

## 📝 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-04-11 | 初始版本，完整功能实现 |

## 📚 参考资料

- [Claude Code Telemetry Architecture](../claude_code_leak/src/utils/telemetry/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/)
- [JSONL Format](http://jsonlines.org/)
