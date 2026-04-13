"""
Telemetry Sink - 遥测数据接收器

设计目标：
1. 解耦事件生产与消费（类似 Claude Code 的事件队列）
2. 线程安全的异步事件采集
3. 支持背压控制（防止内存爆炸）
4. 轻量级，零依赖

架构参考：
- Claude Code: src/utils/telemetry/events.ts (logOTelEvent)
- 使用 queue.Queue 实现线程安全的生产者 - 消费者模式
"""

import time
import uuid
import threading
import queue
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """事件类型枚举"""
    # 交易事件
    ORDER_SUBMITTED = "order.submitted"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"
    
    # 市场事件
    TICK_RECEIVED = "market.tick"
    BAR_COMPLETED = "market.bar"
    SIGNAL_GENERATED = "signal.generated"
    
    # 系统事件
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    ERROR_OCCURRED = "system.error"
    PERFORMANCE_METRIC = "system.performance"
    
    # 风控事件
    RISK_CHECK_PASSED = "risk.check_passed"
    RISK_CHECK_FAILED = "risk.check_failed"
    POSITION_LIMIT_HIT = "risk.position_limit"
    
    # 自定义事件
    CUSTOM = "custom"


@dataclass
class TelemetryEvent:
    """
    遥测事件数据结构
    
    参考 Claude Code 的事件格式：
    - event.name: 事件名称
    - event.timestamp: ISO8601 时间戳
    - event.sequence: 单调递增序列号
    - attributes: 事件属性（键值对）
    """
    event_type: EventType
    event_name: str
    timestamp: float = field(default_factory=time.time)
    sequence: int = 0
    attributes: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 上下文信息（可选）
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None  # 关联 ID，用于追踪相关事件
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于序列化）"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "event_name": self.event_name,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "sequence": self.sequence,
            "attributes": self.attributes,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetryEvent":
        """从字典创建事件"""
        return cls(
            event_type=EventType(data["event_type"]),
            event_name=data["event_name"],
            timestamp=data["timestamp"],
            sequence=data.get("sequence", 0),
            attributes=data.get("attributes", {}),
            event_id=data.get("event_id", str(uuid.uuid4())),
            session_id=data.get("session_id"),
            correlation_id=data.get("correlation_id"),
        )


class TelemetrySink:
    """
    遥测数据接收器（Sink）
    
    核心职责：
    1. 接收来自各模块的遥测事件
    2. 维护全局序列号（保证事件顺序）
    3. 线程安全的队列管理
    4. 背压控制（防止内存爆炸）
    5. 将事件分发给下游处理器（BatchProcessor, Persister 等）
    
    使用示例：
    ```python
    sink = TelemetrySink(max_queue_size=10000)
    
    # 注册消费者（可以是批处理器、持久化器等）
    sink.add_consumer(batch_processor.process)
    sink.add_consumer(persister.save)
    
    # 启动后台处理线程
    sink.start()
    
    # 发送事件
    sink.emit(TelemetryEvent(
        event_type=EventType.ORDER_SUBMITTED,
        event_name="order.submitted",
        attributes={"symbol": "000001.SZ", "price": 10.5, "volume": 100}
    ))
    
    # 停止
    sink.stop()
    ```
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        session_id: Optional[str] = None,
        enable_backpressure: bool = True
    ):
        """
        初始化遥测 Sink
        
        Args:
            max_queue_size: 最大队列大小（背压阈值）
            session_id: 会话 ID（默认自动生成）
            enable_backpressure: 是否启用背压控制
        """
        self._queue: queue.Queue[TelemetryEvent] = queue.Queue(maxsize=max_queue_size)
        self._max_queue_size = max_queue_size
        self._session_id = session_id or str(uuid.uuid4())[:8]
        self._enable_backpressure = enable_backpressure
        
        # 全局序列号（线程安全）
        self._sequence_lock = threading.Lock()
        self._sequence = 0
        
        # 消费者列表
        self._consumers: List[Callable[[TelemetryEvent], None]] = []
        
        # 后台处理线程
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # 统计信息
        self._stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "backpressure_events": 0,
        }
        self._stats_lock = threading.Lock()
        
    def _next_sequence(self) -> int:
        """获取下一个序列号（线程安全）"""
        with self._sequence_lock:
            self._sequence += 1
            return self._sequence
    
    def add_consumer(self, consumer: Callable[[TelemetryEvent], None]):
        """
        添加事件消费者
        
        消费者可以是：
        - BatchProcessor.process()
        - JSONLPersister.save()
        - 自定义处理函数
        
        Args:
            consumer: 接收 TelemetryEvent 的函数
        """
        self._consumers.append(consumer)
    
    def remove_consumer(self, consumer: Callable[[TelemetryEvent], None]):
        """移除消费者"""
        if consumer in self._consumers:
            self._consumers.remove(consumer)
    
    def emit(
        self,
        event_type: EventType,
        event_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        blocking: bool = False,
        timeout: float = 1.0
    ) -> bool:
        """
        发送遥测事件
        
        Args:
            event_type: 事件类型
            event_name: 事件名称
            attributes: 事件属性
            correlation_id: 关联 ID（用于追踪相关事件）
            blocking: 是否阻塞等待（背压时）
            timeout: 阻塞超时时间（秒）
            
        Returns:
            bool: 是否成功发送
        """
        event = TelemetryEvent(
            event_type=event_type,
            event_name=event_name,
            attributes=attributes or {},
            session_id=self._session_id,
            correlation_id=correlation_id,
            sequence=self._next_sequence(),
        )
        
        return self.emit_event(event, blocking=blocking, timeout=timeout)
    
    def emit_event(self, event: TelemetryEvent, blocking: bool = False, timeout: float = 1.0) -> bool:
        """
        发送已构建的事件对象
        
        Args:
            event: TelemetryEvent 对象
            blocking: 是否阻塞等待
            timeout: 阻塞超时时间
            
        Returns:
            bool: 是否成功发送
        """
        try:
            if self._enable_backpressure and self._queue.full():
                with self._stats_lock:
                    self._stats["backpressure_events"] += 1
                
                if blocking:
                    # 阻塞模式：等待队列有空位
                    self._queue.put(event, timeout=timeout)
                else:
                    # 非阻塞模式：丢弃事件
                    with self._stats_lock:
                        self._stats["events_dropped"] += 1
                    return False
            else:
                self._queue.put(event, block=False)
            
            with self._stats_lock:
                self._stats["events_emitted"] += 1
            
            return True
            
        except queue.Full:
            with self._stats_lock:
                self._stats["events_dropped"] += 1
            return False
    
    def start(self):
        """启动后台处理线程"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._worker_thread.start()
    
    def stop(self, wait: bool = True, timeout: float = 5.0):
        """
        停止后台处理线程
        
        Args:
            wait: 是否等待队列处理完成
            timeout: 等待超时时间
        """
        self._running = False
        
        if wait and self._worker_thread:
            self._worker_thread.join(timeout=timeout)
    
    def _process_loop(self):
        """后台处理循环"""
        while self._running:
            try:
                # 从队列获取事件（带超时，便于响应停止信号）
                event = self._queue.get(timeout=0.1)
                
                # 分发给所有消费者
                for consumer in self._consumers:
                    try:
                        consumer(event)
                    except Exception as e:
                        # 消费者异常不影响其他消费者
                        import logging
                        logging.error(f"Telemetry consumer error: {e}")
                
                with self._stats_lock:
                    self._stats["events_processed"] += 1
                    
            except queue.Empty:
                continue
            except Exception as e:
                import logging
                logging.error(f"Telemetry sink process error: {e}")
    
    def flush(self, timeout: float = 5.0):
        """
        等待队列清空
        
        Args:
            timeout: 最大等待时间
        """
        start_time = time.time()
        while not self._queue.empty():
            if time.time() - start_time > timeout:
                break
            time.sleep(0.01)
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
            stats["queue_size"] = self._queue.qsize()
            stats["queue_max"] = self._max_queue_size
        return stats
    
    @property
    def session_id(self) -> str:
        """获取会话 ID"""
        return self._session_id
    
    @property
    def queue_size(self) -> int:
        """获取当前队列大小"""
        return self._queue.qsize()


# 全局单例（可选）
_global_sink: Optional[TelemetrySink] = None

def get_global_sink() -> TelemetrySink:
    """获取全局 Sink 实例（单例）"""
    global _global_sink
    if _global_sink is None:
        _global_sink = TelemetrySink()
    return _global_sink

def init_global_sink(**kwargs) -> TelemetrySink:
    """初始化全局 Sink 实例"""
    global _global_sink
    _global_sink = TelemetrySink(**kwargs)
    return _global_sink
