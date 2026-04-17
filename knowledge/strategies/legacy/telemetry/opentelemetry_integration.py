"""
OpenTelemetry Integration - OpenTelemetry 集成模块（可选）

设计目标：
1. 无缝集成 OpenTelemetry 标准
2. 支持多种导出器（OTLP, Console, Prometheus）
3. 自动追踪关键操作
4. 与现有 Sink 系统协同工作

使用示例：
```python
# 初始化
otel = OpenTelemetryIntegration(
    service_name="bobquant",
    exporter_type="otlp",
    endpoint="http://localhost:4317"
)

# 创建 Span
with otel.trace("order_execution", {"symbol": "000001.SZ"}):
    execute_order()

# 记录指标
otel.record_metric("orders.count", 1, {"type": "buy"})

# 关闭
otel.shutdown()
```
"""

import os
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Generator
from enum import Enum


class ExporterType(Enum):
    """导出器类型"""
    CONSOLE = "console"
    OTLP = "otlp"
    PROMETHEUS = "prometheus"
    NONE = "none"


@dataclass
class OpenTelemetryConfig:
    """
    OpenTelemetry 配置
    
    Attributes:
        service_name: 服务名称
        service_version: 服务版本
        exporter_type: 导出器类型
        otlp_endpoint: OTLP 端点
        otlp_headers: OTLP 请求头
        enable_tracing: 是否启用追踪
        enable_metrics: 是否启用指标
        enable_logging: 是否启用日志
        sampling_rate: 采样率（0-1）
    """
    service_name: str = "bobquant"
    service_version: str = "1.0.0"
    exporter_type: ExporterType = ExporterType.CONSOLE
    otlp_endpoint: str = "http://localhost:4317"
    otlp_headers: Dict[str, str] = None
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    sampling_rate: float = 1.0
    
    def __post_init__(self):
        if self.otlp_headers is None:
            self.otlp_headers = {}


class OpenTelemetryIntegration:
    """
    OpenTelemetry 集成类
    
    注意：这是可选组件，需要安装 opentelemetry 相关包：
    ```bash
    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-otlp
    ```
    
    如果未安装，会自动降级到控制台输出模式。
    """
    
    def __init__(self, config: Optional[OpenTelemetryConfig] = None):
        """
        初始化 OpenTelemetry 集成
        
        Args:
            config: 配置对象
        """
        self.config = config or OpenTelemetryConfig()
        self._initialized = False
        self._fallback_mode = False
        
        # 尝试导入 OpenTelemetry
        try:
            from opentelemetry import trace, metrics
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.resources import Resource
            
            self._trace = trace
            self._metrics = metrics
            self._TracerProvider = TracerProvider
            self._MeterProvider = MeterProvider
            self._Resource = Resource
            
            self._setup_providers()
            self._initialized = True
            
        except ImportError:
            # OpenTelemetry 未安装，使用降级模式
            self._fallback_mode = True
            print("[Telemetry] OpenTelemetry not installed, using fallback mode")
    
    def _setup_providers(self):
        """设置追踪和指标提供者"""
        if self._fallback_mode:
            return
        
        # 创建资源
        resource = self._Resource.create({
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
        })
        
        # 设置追踪
        if self.config.enable_tracing:
            tracer_provider = self._TracerProvider(resource=resource)
            
            # 添加导出器
            self._setup_span_exporter(tracer_provider)
            
            self._trace.set_tracer_provider(tracer_provider)
            self._tracer = tracer_provider.get_tracer(self.config.service_name)
        
        # 设置指标
        if self.config.enable_metrics:
            meter_provider = self._MeterProvider(resource=resource)
            
            # 添加导出器
            self._setup_metric_exporter(meter_provider)
            
            self._metrics.set_meter_provider(meter_provider)
            self._meter = meter_provider.get_meter(self.config.service_name)
    
    def _setup_span_exporter(self, tracer_provider):
        """设置 Span 导出器"""
        if self.config.exporter_type == ExporterType.CONSOLE:
            from opentelemetry.sdk.trace.export import (
                ConsoleSpanExporter,
                SimpleSpanProcessor,
            )
            tracer_provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )
        
        elif self.config.exporter_type == ExporterType.OTLP:
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            
            exporter = OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint,
                headers=self.config.otlp_headers,
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(exporter)
            )
    
    def _setup_metric_exporter(self, meter_provider):
        """设置指标导出器"""
        if self.config.exporter_type == ExporterType.CONSOLE:
            from opentelemetry.sdk.metrics.export import (
                ConsoleMetricExporter,
                PeriodicExportingMetricReader,
            )
            reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=10000,
            )
            meter_provider.add_metric_reader(reader)
        
        elif self.config.exporter_type == ExporterType.OTLP:
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            
            exporter = OTLPMetricExporter(
                endpoint=self.config.otlp_endpoint,
                headers=self.config.otlp_headers,
            )
            reader = PeriodicExportingMetricReader(
                exporter,
                export_interval_millis=10000,
            )
            meter_provider.add_metric_reader(reader)
    
    @contextmanager
    def trace(
        self,
        operation: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: str = "internal"
    ) -> Generator:
        """
        创建追踪 Span（上下文管理器）
        
        使用示例：
        ```python
        with otel.trace("order_execution", {"symbol": "000001.SZ"}):
            execute_order()
        ```
        
        Args:
            operation: 操作名称
            attributes: 属性字典
            kind: Span 类型 (internal, server, client, producer, consumer)
        """
        if self._fallback_mode:
            # 降级模式：简单打印
            start_time = time.time()
            print(f"[Trace] Start: {operation}")
            try:
                yield None
            finally:
                duration = time.time() - start_time
                print(f"[Trace] End: {operation} ({duration:.3f}s)")
            return
        
        if not self.config.enable_tracing:
            yield None
            return
        
        # 映射 Span kind
        from opentelemetry.trace import SpanKind
        kind_map = {
            "internal": SpanKind.INTERNAL,
            "server": SpanKind.SERVER,
            "client": SpanKind.CLIENT,
            "producer": SpanKind.PRODUCER,
            "consumer": SpanKind.CONSUMER,
        }
        span_kind = kind_map.get(kind, SpanKind.INTERNAL)
        
        with self._tracer.start_as_current_span(
            operation,
            kind=span_kind,
            attributes=attributes or {},
        ) as span:
            yield span
    
    def trace_async(self, operation: str, attributes: Optional[Dict[str, Any]] = None):
        """
        创建追踪 Span（手动管理）
        
        使用示例：
        ```python
        span = otel.trace_async("operation")
        try:
            do_something()
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            span.end()
        ```
        """
        if self._fallback_mode or not self.config.enable_tracing:
            return None
        
        span = self._tracer.start_span(
            operation,
            attributes=attributes or {},
        )
        return span
    
    def record_metric(
        self,
        name: str,
        value: float,
        attributes: Optional[Dict[str, Any]] = None,
        metric_type: str = "counter"
    ):
        """
        记录指标
        
        Args:
            name: 指标名称
            value: 指标值
            attributes: 属性
            metric_type: 指标类型 (counter, gauge, histogram)
        """
        if self._fallback_mode:
            print(f"[Metric] {name} = {value}")
            return
        
        if not self.config.enable_metrics:
            return
        
        if metric_type == "counter":
            counter = self._meter.create_counter(name)
            counter.add(value, attributes or {})
        
        elif metric_type == "gauge":
            # 使用 ObservableGauge
            gauge_value = [value]
            
            def callback(options):
                from opentelemetry.sdk.metrics import Observation
                yield Observation(gauge_value[0], attributes or {})
            
            self._meter.create_observable_gauge(
                name,
                callbacks=[callback],
            )
        
        elif metric_type == "histogram":
            histogram = self._meter.create_histogram(name)
            histogram.record(value, attributes or {})
    
    def record_event(
        self,
        event_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        记录事件（日志）
        
        Args:
            event_name: 事件名称
            attributes: 属性
        """
        if self._fallback_mode:
            print(f"[Event] {event_name}: {attributes}")
            return
        
        if not self.config.enable_logging:
            return
        
        from opentelemetry import logs
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import ConsoleLogExporter
        
        logger_provider = LoggerProvider()
        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(ConsoleLogExporter())
        )
        logs.set_logger_provider(logger_provider)
        
        logger = logs.get_logger(self.config.service_name)
        logger.emit({
            "body": event_name,
            "attributes": attributes or {},
        })
    
    def get_tracer(self):
        """获取 Tracer 对象"""
        if self._fallback_mode:
            return None
        return self._tracer
    
    def get_meter(self):
        """获取 Meter 对象"""
        if self._fallback_mode:
            return None
        return self._meter
    
    def shutdown(self):
        """关闭 OpenTelemetry"""
        if self._fallback_mode:
            return
        
        if self.config.enable_tracing:
            from opentelemetry.trace import get_tracer_provider
            get_tracer_provider().shutdown()
        
        if self.config.enable_metrics:
            from opentelemetry.metrics import get_meter_provider
            get_meter_provider().shutdown()
    
    def is_available(self) -> bool:
        """检查 OpenTelemetry 是否可用"""
        return self._initialized and not self._fallback_mode


# 全局实例
_global_otel: Optional[OpenTelemetryIntegration] = None

def get_otel() -> OpenTelemetryIntegration:
    """获取全局 OpenTelemetry 实例"""
    global _global_otel
    if _global_otel is None:
        _global_otel = OpenTelemetryIntegration()
    return _global_otel

def init_otel(**kwargs) -> OpenTelemetryIntegration:
    """初始化全局 OpenTelemetry 实例"""
    global _global_otel
    _global_otel = OpenTelemetryIntegration(
        config=OpenTelemetryConfig(**kwargs) if 'config' not in kwargs else kwargs.get('config')
    )
    return _global_otel
