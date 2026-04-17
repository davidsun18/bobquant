"""
BobQuant Telemetry System - 监控与遥测模块

借鉴 Claude Code 的遥测架构，提供：
- 异步事件采集
- 批处理（大小 + 时间双触发）
- 磁盘持久化（JSONL）
- PII 脱敏保护
- 多级缓存（内存→磁盘）
- OpenTelemetry 集成（可选）

Author: Bob (AI Assistant)
Date: 2026-04-11
"""

from .sink import TelemetrySink, TelemetryEvent, EventType, init_global_sink
from .batch import BatchProcessor, BatchConfig
from .persistence import JSONLPersister, PersistenceConfig
from .pii import PIIMasker, MaskingRule, MaskingLevel
from .cache import MultiLevelCache, CacheConfig
from .retry import RetryConfig, retry_with_backoff, RetryError
from .metrics import MetricsRegistry, MetricDefinition, MetricType, get_metrics_registry
from .opentelemetry_integration import OpenTelemetryIntegration, OpenTelemetryConfig, ExporterType

__version__ = "1.0.0"
__all__ = [
    "TelemetrySink",
    "TelemetryEvent",
    "BatchProcessor",
    "BatchConfig",
    "JSONLPersister",
    "PersistenceConfig",
    "PIIMasker",
    "MaskingRule",
    "MultiLevelCache",
    "RetryConfig",
    "retry_with_backoff",
]
