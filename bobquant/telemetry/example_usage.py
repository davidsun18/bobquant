"""
BobQuant Telemetry System - 使用示例

演示如何集成遥测系统到 BobQuant 交易中
"""

import time
import random
from typing import Dict, Any

# 导入遥测模块
from .sink import TelemetrySink, TelemetryEvent, EventType
from .batch import BatchProcessor, BatchConfig
from .persistence import JSONLPersister, PersistenceConfig
from .pii import PIIMasker
from .cache import MultiLevelCache, CacheConfig
from .metrics import get_metrics_registry
from .opentelemetry_integration import OpenTelemetryIntegration


class TelemetrySystem:
    """
    BobQuant 遥测系统集成类
    
    一站式初始化所有遥测组件
    """
    
    def __init__(
        self,
        data_dir: str = "./telemetry_data",
        enable_masking: bool = True,
        enable_otel: bool = False,
    ):
        """
        初始化遥测系统
        
        Args:
            data_dir: 数据存储目录
            enable_masking: 是否启用 PII 脱敏
            enable_otel: 是否启用 OpenTelemetry
        """
        print("[Telemetry] Initializing BobQuant Telemetry System...")
        
        # 1. 创建 Sink
        self.sink = TelemetrySink(max_queue_size=10000)
        
        # 2. 创建批处理器
        batch_config = BatchConfig(
            max_batch_size=100,
            max_wait_time=5.0,
        )
        self.batch_processor = BatchProcessor(batch_config)
        
        # 3. 创建持久化器
        persist_config = PersistenceConfig(
            base_dir=data_dir,
            max_file_size=100,  # 100MB
            compression=False,
            atomic_write=True,
        )
        self.persister = JSONLPersister(persist_config)
        
        # 4. 创建脱敏器
        self.masker = PIIMasker() if enable_masking else None
        
        # 5. 创建缓存
        cache_config = CacheConfig(
            memory_max_size=10000,
            disk_path=f"{data_dir}/cache.db",
        )
        self.cache = MultiLevelCache(cache_config)
        
        # 6. 创建 OpenTelemetry 集成（可选）
        self.otel = OpenTelemetryIntegration() if enable_otel else None
        
        # 7. 获取指标注册表
        self.metrics = get_metrics_registry()
        
        # 连接组件
        self._connect_components()
        
        # 启动后台线程
        self._start()
        
        print("[Telemetry] System initialized successfully")
    
    def _connect_components(self):
        """连接各组件"""
        # Sink -> BatchProcessor
        self.sink.add_consumer(self.batch_processor.process)
        
        # BatchProcessor -> Persister
        def save_batch(batch):
            # 可选：脱敏
            if self.masker:
                batch = self.masker.mask_batch(batch)
            self.persister.save_batch(batch)
            
            # 记录指标
            self.metrics.inc("bobquant.telemetry.events_emitted", len(batch))
        
        self.batch_processor.on_batch_ready(save_batch)
    
    def _start(self):
        """启动所有后台线程"""
        self.sink.start()
        self.batch_processor.start()
        self.persister.start()
        self.cache.start()
    
    def stop(self):
        """停止系统"""
        print("[Telemetry] Stopping system...")
        self.sink.stop(wait=True)
        self.batch_processor.stop(flush=True)
        self.persister.stop(flush=True)
        self.cache.stop(flush=True)
        if self.otel:
            self.otel.shutdown()
        print("[Telemetry] System stopped")
    
    def emit_event(
        self,
        event_type: EventType,
        event_name: str,
        attributes: Dict[str, Any],
        correlation_id: str = None,
    ):
        """
        发送事件
        
        Args:
            event_type: 事件类型
            event_name: 事件名称
            attributes: 事件属性
            correlation_id: 关联 ID
        """
        self.sink.emit(
            event_type=event_type,
            event_name=event_name,
            attributes=attributes,
            correlation_id=correlation_id,
        )
    
    def record_order_submitted(
        self,
        order_id: str,
        symbol: str,
        price: float,
        volume: int,
        direction: str,
        user_id: str = None,
    ):
        """记录订单提交"""
        # 脱敏用户 ID
        if user_id and self.masker:
            user_id = self.masker.mask_value(user_id, "user_id")
        
        self.emit_event(
            event_type=EventType.ORDER_SUBMITTED,
            event_name="order.submitted",
            attributes={
                "order_id": order_id,
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "direction": direction,
                "user_id": user_id,
            },
            correlation_id=order_id,
        )
        
        # 记录指标
        self.metrics.inc("bobquant.orders.total", labels={
            "type": direction,
            "symbol": symbol,
            "status": "submitted",
        })
    
    def record_order_filled(
        self,
        order_id: str,
        symbol: str,
        fill_price: float,
        fill_volume: int,
        latency_ms: float,
    ):
        """记录订单成交"""
        self.emit_event(
            event_type=EventType.ORDER_FILLED,
            event_name="order.filled",
            attributes={
                "order_id": order_id,
                "symbol": symbol,
                "fill_price": fill_price,
                "fill_volume": fill_volume,
                "latency_ms": latency_ms,
            },
            correlation_id=order_id,
        )
        
        # 记录指标
        self.metrics.inc("bobquant.orders.filled", labels={
            "type": "market",
            "symbol": symbol,
        })
        self.metrics.observe("bobquant.latency.order_submit", latency_ms, labels={
            "broker": "default",
            "symbol": symbol,
        })
    
    def record_signal(
        self,
        strategy: str,
        symbol: str,
        signal_type: str,
        confidence: float,
        latency_ms: float,
    ):
        """记录交易信号"""
        self.emit_event(
            event_type=EventType.SIGNAL_GENERATED,
            event_name="signal.generated",
            attributes={
                "strategy": strategy,
                "symbol": symbol,
                "signal_type": signal_type,
                "confidence": confidence,
                "latency_ms": latency_ms,
            },
        )
        
        # 记录指标
        self.metrics.inc("bobquant.strategy.signals", labels={
            "strategy": strategy,
            "type": signal_type,
        })
        self.metrics.observe("bobquant.latency.signal_generation", latency_ms, labels={
            "strategy": strategy,
        })
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None,
    ):
        """记录错误"""
        self.emit_event(
            event_type=EventType.ERROR_OCCURRED,
            event_name="system.error",
            attributes={
                "error_type": error_type,
                "error_message": error_message,
                **(context or {}),
            },
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            "sink": self.sink.get_stats(),
            "batch": self.batch_processor.get_stats(),
            "persistence": self.persister.get_stats(),
            "cache": self.cache.get_stats(),
            "metrics": self.metrics.export(),
        }


# ==================== 使用示例 ====================

def example_basic_usage():
    """基础使用示例"""
    print("\n=== 基础使用示例 ===\n")
    
    # 初始化系统
    telemetry = TelemetrySystem(
        data_dir="./example_telemetry_data",
        enable_masking=True,
        enable_otel=False,
    )
    
    try:
        # 1. 记录订单提交
        telemetry.record_order_submitted(
            order_id="ORD-20260411-001",
            symbol="000001.SZ",
            price=10.5,
            volume=1000,
            direction="buy",
            user_id="user_12345",
        )
        
        # 2. 记录订单成交
        time.sleep(0.1)  # 模拟延迟
        telemetry.record_order_filled(
            order_id="ORD-20260411-001",
            symbol="000001.SZ",
            fill_price=10.52,
            fill_volume=1000,
            latency_ms=50.5,
        )
        
        # 3. 记录交易信号
        telemetry.record_signal(
            strategy="macd_strategy",
            symbol="000001.SZ",
            signal_type="buy",
            confidence=0.85,
            latency_ms=15.2,
        )
        
        # 4. 记录错误
        telemetry.record_error(
            error_type="NetworkError",
            error_message="Connection timeout",
            context={"broker": "broker_1", "retry_count": 3},
        )
        
        # 等待处理完成
        time.sleep(2)
        
        # 5. 查看统计
        stats = telemetry.get_stats()
        print("\n系统统计:")
        print(f"  事件 emitted: {stats['sink']['events_emitted']}")
        print(f"  事件 processed: {stats['sink']['events_processed']}")
        print(f"  批次创建：{stats['batch']['batches_created']}")
        print(f"  事件写入：{stats['persistence']['events_written']}")
        print(f"  缓存命中率：{stats['cache'].get('hit_rate', 0):.2%}")
        
    finally:
        # 停止系统
        telemetry.stop()


def example_with_cache():
    """缓存使用示例"""
    print("\n=== 缓存使用示例 ===\n")
    
    from .cache import MultiLevelCache, CacheConfig
    
    config = CacheConfig(
        memory_max_size=100,
        disk_path="./example_cache.db",
    )
    cache = MultiLevelCache(config)
    cache.start()
    
    try:
        # 写入缓存
        cache.set("market_data:000001.SZ", {
            "price": 10.5,
            "volume": 1000000,
            "timestamp": time.time(),
        })
        
        # 读取缓存（命中内存）
        data = cache.get("market_data:000001.SZ")
        print(f"缓存命中：{data}")
        
        # 批量读取
        cache.set("market_data:000002.SZ", {"price": 20.3})
        cache.set("market_data:000003.SZ", {"price": 15.7})
        
        results = cache.get_batch([
            "market_data:000001.SZ",
            "market_data:000002.SZ",
            "market_data:000003.SZ",
        ])
        print(f"批量读取：{len(results)} 条数据")
        
        # 查看统计
        stats = cache.get_stats()
        print(f"缓存命中率：{stats.get('hit_rate', 0):.2%}")
        
    finally:
        cache.stop()


def example_with_pii_masking():
    """PII 脱敏示例"""
    print("\n=== PII 脱敏示例 ===\n")
    
    from .pii import PIIMasker, MaskingRule, MaskingLevel
    
    masker = PIIMasker()
    
    # 测试各种脱敏
    test_cases = [
        ("phone", "13812345678"),
        ("email", "david@example.com"),
        ("id_card", "110101199001011234"),
        ("bank_card", "6222021234567890123"),
        ("user_id", "user_12345"),
    ]
    
    print("脱敏结果:")
    for field_name, value in test_cases:
        masked = masker.mask_value(value, field_name=field_name)
        print(f"  {field_name}: {value} -> {masked}")
    
    # 测试事件脱敏
    from .sink import TelemetryEvent, EventType
    
    event = TelemetryEvent(
        event_type=EventType.ORDER_SUBMITTED,
        event_name="order.submitted",
        attributes={
            "order_id": "ORD-001",
            "user_phone": "13812345678",
            "user_email": "david@example.com",
            "symbol": "000001.SZ",
            "price": 10.5,
        },
    )
    
    masked_event = masker.mask_event(event)
    print(f"\n事件脱敏:")
    print(f"  原始属性：{event.attributes}")
    print(f"  脱敏属性：{masked_event.attributes}")


def example_metrics_export():
    """指标导出示例"""
    print("\n=== 指标导出示例 ===\n")
    
    from .metrics import MetricsRegistry, MetricDefinition, MetricType
    
    registry = MetricsRegistry()
    
    # 模拟一些指标数据
    registry.inc("bobquant.orders.total", labels={"type": "buy", "symbol": "000001.SZ", "status": "submitted"})
    registry.inc("bobquant.orders.total", labels={"type": "sell", "symbol": "000002.SZ", "status": "submitted"})
    registry.inc("bobquant.orders.filled", labels={"type": "buy", "symbol": "000001.SZ"})
    
    registry.set("bobquant.position.current", 1000, labels={"symbol": "000001.SZ", "direction": "long"})
    registry.set("bobquant.pnl.unrealized", 5200.5, labels={"symbol": "000001.SZ", "strategy": "macd"})
    
    registry.observe("bobquant.latency.order_submit", 45.2, labels={"broker": "default", "symbol": "000001.SZ"})
    registry.observe("bobquant.latency.order_submit", 52.1, labels={"broker": "default", "symbol": "000001.SZ"})
    registry.observe("bobquant.latency.order_submit", 38.7, labels={"broker": "default", "symbol": "000001.SZ"})
    
    # 导出为字典
    metrics = registry.export()
    print("指标导出 (字典格式):")
    for name, data in list(metrics.items())[:3]:
        print(f"  {name}: {data['values']}")
    
    # 导出为 Prometheus 格式
    prometheus_output = registry.export_prometheus()
    print("\nPrometheus 格式:")
    print(prometheus_output[:500] + "..." if len(prometheus_output) > 500 else prometheus_output)


if __name__ == "__main__":
    # 运行所有示例
    example_basic_usage()
    example_with_cache()
    example_with_pii_masking()
    example_metrics_export()
    
    print("\n=== 所有示例完成 ===")
