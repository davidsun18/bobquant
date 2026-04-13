"""
Batch Processor - 批处理器

设计目标：
1. 大小 + 时间双触发（类似 Kafka 的 batch 机制）
2. 减少磁盘 I/O 和网络请求次数
3. 支持优雅关闭和强制刷新
4. 线程安全

架构参考：
- Claude Code: BatchLogRecordProcessor, BatchSpanProcessor
- Kafka: batch.size + linger.ms 双触发机制
"""

import time
import threading
import queue
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from .sink import TelemetryEvent


@dataclass
class BatchConfig:
    """
    批处理配置
    
    Attributes:
        max_batch_size: 最大批次大小（触发阈值）
        max_wait_time: 最大等待时间（秒，时间触发阈值）
        max_queue_size: 批次队列最大大小（背压控制）
        enable_compression: 是否启用压缩（可选）
    """
    max_batch_size: int = 100  # 100 个事件触发一次
    max_wait_time: float = 5.0  # 5 秒触发一次
    max_queue_size: int = 1000  # 最多缓存 1000 个批次
    enable_compression: bool = False


class BatchProcessor:
    """
    批处理器
    
    工作原理：
    1. 接收来自 Sink 的事件
    2. 累积到当前批次
    3. 当满足以下任一条件时触发：
       - 批次大小达到 max_batch_size
       - 距离上次触发超过 max_wait_time
    4. 将完整批次发送给下游处理器
    
    使用示例：
    ```python
    config = BatchConfig(max_batch_size=50, max_wait_time=3.0)
    processor = BatchProcessor(config)
    
    # 注册批次处理器（当批次就绪时调用）
    processor.on_batch_ready(persister.save_batch)
    
    # 启动处理
    processor.start()
    
    # 停止时强制刷新剩余事件
    processor.stop(flush=True)
    ```
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """
        初始化批处理器
        
        Args:
            config: 批处理配置
        """
        self.config = config or BatchConfig()
        
        # 当前批次
        self._current_batch: List[TelemetryEvent] = []
        self._batch_lock = threading.Lock()
        self._last_flush_time = time.time()
        
        # 批次队列（已完成的批次等待处理）
        self._batch_queue: queue.Queue[List[TelemetryEvent]] = queue.Queue(
            maxsize=self.config.max_queue_size
        )
        
        # 批次处理器列表
        self._batch_handlers: List[Callable[[List[TelemetryEvent]], None]] = []
        
        # 后台线程
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._timer_thread: Optional[threading.Thread] = None
        
        # 统计信息
        self._stats = {
            "batches_created": 0,
            "batches_processed": 0,
            "events_batched": 0,
            "events_dropped": 0,
            "time_triggers": 0,
            "size_triggers": 0,
            "flush_triggers": 0,
        }
        self._stats_lock = threading.Lock()
    
    def on_batch_ready(self, handler: Callable[[List[TelemetryEvent]], None]):
        """
        注册批次就绪处理器
        
        Args:
            handler: 接收 List[TelemetryEvent] 的函数
        """
        self._batch_handlers.append(handler)
    
    def process(self, event: TelemetryEvent):
        """
        处理单个事件（由 Sink 调用）
        
        Args:
            event: 遥测事件
        """
        with self._batch_lock:
            self._current_batch.append(event)
            
            # 检查是否达到大小阈值
            if len(self._current_batch) >= self.config.max_batch_size:
                self._flush_batch(trigger="size")
                return
        
        # 时间触发由定时器线程处理
    
    def start(self):
        """启动后台线程"""
        if self._running:
            return
        
        self._running = True
        self._last_flush_time = time.time()
        
        # 启动批次处理线程
        self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._worker_thread.start()
        
        # 启动定时器线程（时间触发）
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
    
    def stop(self, flush: bool = True, timeout: float = 5.0):
        """
        停止批处理器
        
        Args:
            flush: 是否刷新剩余事件
            timeout: 等待超时时间
        """
        self._running = False
        
        # 刷新剩余事件
        if flush:
            self.force_flush()
        
        # 等待线程结束
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
        if self._timer_thread:
            self._timer_thread.join(timeout=timeout)
    
    def force_flush(self):
        """强制刷新当前批次（无论大小）"""
        with self._batch_lock:
            if self._current_batch:
                self._flush_batch(trigger="flush")
    
    def _flush_batch(self, trigger: str = "manual"):
        """
        刷新当前批次
        
        Args:
            trigger: 触发类型 ("size", "time", "flush", "manual")
        """
        if not self._current_batch:
            return
        
        # 创建批次副本
        batch = self._current_batch.copy()
        self._current_batch.clear()
        self._last_flush_time = time.time()
        
        # 更新统计
        with self._stats_lock:
            self._stats["batches_created"] += 1
            self._stats["events_batched"] += len(batch)
            if trigger == "size":
                self._stats["size_triggers"] += 1
            elif trigger == "time":
                self._stats["time_triggers"] += 1
            elif trigger == "flush":
                self._stats["flush_triggers"] += 1
        
        # 将批次放入队列
        try:
            self._batch_queue.put(batch, block=False)
        except queue.Full:
            with self._stats_lock:
                self._stats["events_dropped"] += len(batch)
    
    def _timer_loop(self):
        """定时器循环（时间触发）"""
        while self._running:
            time.sleep(self.config.max_wait_time / 2)  # 半周期检查
            
            if not self._running:
                break
            
            with self._batch_lock:
                elapsed = time.time() - self._last_flush_time
                if elapsed >= self.config.max_wait_time and self._current_batch:
                    self._flush_batch(trigger="time")
    
    def _process_loop(self):
        """批次处理循环"""
        while self._running:
            try:
                # 从队列获取批次
                batch = self._batch_queue.get(timeout=0.1)
                
                # 调用所有处理器
                for handler in self._batch_handlers:
                    try:
                        handler(batch)
                    except Exception as e:
                        import logging
                        logging.error(f"Batch handler error: {e}")
                
                with self._stats_lock:
                    self._stats["batches_processed"] += 1
                    
            except queue.Empty:
                continue
            except Exception as e:
                import logging
                logging.error(f"Batch processor error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
        
        with self._batch_lock:
            stats["current_batch_size"] = len(self._current_batch)
            stats["queue_size"] = self._batch_queue.qsize()
        
        return stats
    
    @property
    def pending_events(self) -> int:
        """获取待处理事件数"""
        with self._batch_lock:
            return len(self._current_batch)


class AsyncBatchProcessor(BatchProcessor):
    """
    异步批处理器（支持回调）
    
    在 BatchProcessor 基础上增加：
    - 异步处理支持
    - 完成回调
    - 错误回调
    """
    
    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        on_success: Optional[Callable[[List[TelemetryEvent]], None]] = None,
        on_error: Optional[Callable[[List[TelemetryEvent], Exception], None]] = None,
    ):
        super().__init__(config)
        self._on_success = on_success
        self._on_error = on_error
    
    def on_batch_ready(self, handler: Callable[[List[TelemetryEvent]], None]):
        """注册带错误处理的处理器"""
        def wrapped_handler(batch: List[TelemetryEvent]):
            try:
                handler(batch)
                if self._on_success:
                    self._on_success(batch)
            except Exception as e:
                if self._on_error:
                    self._on_error(batch, e)
                raise
        
        self._batch_handlers.append(wrapped_handler)
