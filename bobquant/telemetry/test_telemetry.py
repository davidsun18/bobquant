"""
BobQuant Telemetry System - 单元测试
"""

import unittest
import time
import tempfile
import shutil
from pathlib import Path


class TestTelemetrySink(unittest.TestCase):
    """测试 TelemetrySink"""
    
    def setUp(self):
        from bobquant.telemetry import TelemetrySink, EventType
        
        self.sink = TelemetrySink(max_queue_size=100)
        self.received_events = []
        
        def consumer(event):
            self.received_events.append(event)
        
        self.sink.add_consumer(consumer)
        self.sink.start()
    
    def tearDown(self):
        self.sink.stop()
    
    def test_emit_event(self):
        """测试事件发送"""
        from bobquant.telemetry import EventType
        
        success = self.sink.emit(
            event_type=EventType.ORDER_SUBMITTED,
            event_name="order.submitted",
            attributes={"symbol": "000001.SZ"}
        )
        
        self.assertTrue(success)
        time.sleep(0.2)  # 等待处理
        self.assertEqual(len(self.received_events), 1)
    
    def test_backpressure(self):
        """测试背压控制"""
        from bobquant.telemetry import EventType
        
        # 填满队列
        for i in range(100):
            self.sink.emit(
                event_type=EventType.CUSTOM,
                event_name=f"event.{i}",
                blocking=False
            )
        
        # 下一个应该被丢弃
        success = self.sink.emit(
            event_type=EventType.CUSTOM,
            event_name="dropped_event",
            blocking=False
        )
        
        self.assertFalse(success)
        
        stats = self.sink.get_stats()
        self.assertGreater(stats["events_dropped"], 0)


class TestBatchProcessor(unittest.TestCase):
    """测试 BatchProcessor"""
    
    def setUp(self):
        from bobquant.telemetry import BatchProcessor, BatchConfig, TelemetryEvent, EventType
        
        self.config = BatchConfig(
            max_batch_size=5,
            max_wait_time=1.0
        )
        self.processor = BatchProcessor(self.config)
        self.received_batches = []
        
        def handler(batch):
            self.received_batches.append(batch)
        
        self.processor.on_batch_ready(handler)
        self.processor.start()
    
    def tearDown(self):
        self.processor.stop()
    
    def test_size_trigger(self):
        """测试大小触发"""
        from bobquant.telemetry import TelemetryEvent, EventType
        
        # 发送 5 个事件（达到批次大小）
        for i in range(5):
            event = TelemetryEvent(
                event_type=EventType.CUSTOM,
                event_name=f"event.{i}"
            )
            self.processor.process(event)
        
        time.sleep(0.5)  # 等待处理
        self.assertEqual(len(self.received_batches), 1)
        self.assertEqual(len(self.received_batches[0]), 5)
    
    def test_time_trigger(self):
        """测试时间触发"""
        from bobquant.telemetry import TelemetryEvent, EventType
        
        # 发送 1 个事件（不足批次大小）
        event = TelemetryEvent(
            event_type=EventType.CUSTOM,
            event_name="event.1"
        )
        self.processor.process(event)
        
        # 等待时间触发
        time.sleep(1.5)
        
        self.assertEqual(len(self.received_batches), 1)
    
    def test_force_flush(self):
        """测试强制刷新"""
        from bobquant.telemetry import TelemetryEvent, EventType
        
        # 发送 2 个事件
        for i in range(2):
            event = TelemetryEvent(
                event_type=EventType.CUSTOM,
                event_name=f"event.{i}"
            )
            self.processor.process(event)
        
        # 强制刷新
        self.processor.force_flush()
        time.sleep(0.2)
        
        self.assertEqual(len(self.received_batches), 1)
        self.assertEqual(len(self.received_batches[0]), 2)


class TestJSONLPersister(unittest.TestCase):
    """测试 JSONLPersister"""
    
    def setUp(self):
        from bobquant.telemetry import JSONLPersister, PersistenceConfig
        
        self.temp_dir = tempfile.mkdtemp()
        self.config = PersistenceConfig(
            base_dir=self.temp_dir,
            max_file_size=1,  # 1MB 触发轮转
            atomic_write=True,
        )
        self.persister = JSONLPersister(self.config)
        self.persister.start()
    
    def tearDown(self):
        self.persister.stop()
        shutil.rmtree(self.temp_dir)
    
    def test_save_event(self):
        """测试保存单个事件"""
        from bobquant.telemetry import TelemetryEvent, EventType
        
        event = TelemetryEvent(
            event_type=EventType.ORDER_SUBMITTED,
            event_name="order.submitted",
            attributes={"symbol": "000001.SZ", "price": 10.5}
        )
        
        self.persister.save(event)
        self.persister.flush()
        
        # 读取验证
        events = list(self.persister.read_events())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_name, "order.submitted")
    
    def test_save_batch(self):
        """测试批量保存"""
        from bobquant.telemetry import TelemetryEvent, EventType
        
        events = [
            TelemetryEvent(
                event_type=EventType.ORDER_SUBMITTED,
                event_name="order.submitted",
                attributes={"symbol": f"00000{i}.SZ"}
            )
            for i in range(1, 6)
        ]
        
        self.persister.save_batch(events)
        self.persister.flush()
        
        read_events = list(self.persister.read_events())
        self.assertEqual(len(read_events), 5)
    
    def test_file_rotation(self):
        """测试文件轮转"""
        from bobquant.telemetry import TelemetryEvent, EventType
        
        # 保存大量事件触发轮转
        for i in range(1000):
            event = TelemetryEvent(
                event_type=EventType.CUSTOM,
                event_name="event",
                attributes={"data": "x" * 1000}  # 大数据
            )
            self.persister.save(event)
        
        self.persister.flush()
        
        stats = self.persister.get_stats()
        self.assertGreater(stats["files_created"], 1)


class TestPIIMasker(unittest.TestCase):
    """测试 PIIMasker"""
    
    def setUp(self):
        from bobquant.telemetry import PIIMasker
        
        self.masker = PIIMasker()
    
    def test_phone_masking(self):
        """测试手机号脱敏"""
        masked = self.masker.mask_value("13812345678", "phone")
        self.assertEqual(masked, "138****5678")
    
    def test_email_masking(self):
        """测试邮箱脱敏"""
        masked = self.masker.mask_value("david@example.com", "email")
        self.assertTrue(masked.startswith("d"))
        self.assertTrue("@example.com" in masked)
    
    def test_id_card_masking(self):
        """测试身份证脱敏"""
        masked = self.masker.mask_value("110101199001011234", "id_card")
        self.assertEqual(masked[:6], "110101")
        self.assertEqual(masked[-4:], "1234")
    
    def test_bank_card_masking(self):
        """测试银行卡脱敏"""
        masked = self.masker.mask_value("6222021234567890123", "bank_card")
        self.assertEqual(masked[:4], "6222")
        self.assertEqual(masked[-4:], "0123")
    
    def test_hash_masking(self):
        """测试哈希脱敏"""
        masked = self.masker.mask_value("user_12345", "user_id")
        self.assertTrue(masked.startswith("hash_"))


class TestMultiLevelCache(unittest.TestCase):
    """测试 MultiLevelCache"""
    
    def setUp(self):
        from bobquant.telemetry import MultiLevelCache, CacheConfig
        
        self.temp_dir = tempfile.mkdtemp()
        self.config = CacheConfig(
            memory_max_size=100,
            disk_path=f"{self.temp_dir}/cache.db",
        )
        self.cache = MultiLevelCache(self.config)
        self.cache.start()
    
    def tearDown(self):
        self.cache.stop()
        shutil.rmtree(self.temp_dir)
    
    def test_set_get(self):
        """测试基本读写"""
        self.cache.set("key1", "value1")
        value = self.cache.get("key1")
        self.assertEqual(value, "value1")
    
    def test_cache_miss(self):
        """测试缓存未命中"""
        value = self.cache.get("nonexistent")
        self.assertIsNone(value)
    
    def test_batch_operations(self):
        """测试批量操作"""
        items = {f"key{i}": f"value{i}" for i in range(10)}
        self.cache.set_batch(items)
        
        results = self.cache.get_batch(list(items.keys()))
        self.assertEqual(len(results), 10)
    
    def test_memory_to_disk_fill(self):
        """测试磁盘回填内存"""
        # 直接写入磁盘
        if self.cache._disk:
            self.cache._disk.set("disk_key", "disk_value")
        
        # 读取应该回填到内存
        value = self.cache.get("disk_key")
        self.assertEqual(value, "disk_value")
        
        # 再次读取应该命中内存
        stats_before = self.cache.get_stats()
        self.cache.get("disk_key")
        stats_after = self.cache.get_stats()
        
        self.assertEqual(stats_after["memory_hits"], stats_before["memory_hits"] + 1)


class TestRetryMechanism(unittest.TestCase):
    """测试重试机制"""
    
    def test_retry_success(self):
        """测试重试成功"""
        from bobquant.telemetry import retry_with_backoff
        
        attempt_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = flaky_function()
        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 3)
    
    def test_retry_failure(self):
        """测试重试失败"""
        from bobquant.telemetry import retry_with_backoff, RetryError
        
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def failing_function():
            raise ValueError("Always fails")
        
        with self.assertRaises(RetryError):
            failing_function()


class TestMetricsRegistry(unittest.TestCase):
    """测试 MetricsRegistry"""
    
    def setUp(self):
        from bobquant.telemetry import MetricsRegistry
        
        self.registry = MetricsRegistry()
    
    def test_counter_increment(self):
        """测试计数器增加"""
        self.registry.inc("bobquant.orders.total", labels={"type": "buy"})
        self.registry.inc("bobquant.orders.total", labels={"type": "buy"})
        
        value = self.registry.get("bobquant.orders.total", labels={"type": "buy"})
        self.assertEqual(value, 2)
    
    def test_gauge_set(self):
        """测试仪表盘设置"""
        self.registry.set("bobquant.position.current", 1000, labels={"symbol": "000001.SZ"})
        
        value = self.registry.get("bobquant.position.current", labels={"symbol": "000001.SZ"})
        self.assertEqual(value, 1000)
    
    def test_histogram_observe(self):
        """测试直方图观察"""
        self.registry.observe("bobquant.latency.order_submit", 10.5)
        self.registry.observe("bobquant.latency.order_submit", 20.3)
        self.registry.observe("bobquant.latency.order_submit", 15.7)
        
        stats = self.registry.get("bobquant.latency.order_submit")
        self.assertEqual(stats["count"], 3)
        self.assertAlmostEqual(stats["avg"], (10.5 + 20.3 + 15.7) / 3, places=2)
    
    def test_prometheus_export(self):
        """测试 Prometheus 导出"""
        self.registry.inc("bobquant.orders.total", labels={"type": "buy"})
        self.registry.set("bobquant.position.current", 1000)
        
        output = self.registry.export_prometheus()
        
        # Prometheus 格式使用点分隔符（我们的实现）
        self.assertIn("bobquant.orders.total", output)
        self.assertIn("bobquant.position.current", output)


class TestEventType(unittest.TestCase):
    """测试 EventType 枚举"""
    
    def test_event_types_exist(self):
        """测试事件类型存在"""
        from bobquant.telemetry import EventType
        
        # 交易事件
        self.assertEqual(EventType.ORDER_SUBMITTED.value, "order.submitted")
        self.assertEqual(EventType.ORDER_FILLED.value, "order.filled")
        
        # 市场事件
        self.assertEqual(EventType.TICK_RECEIVED.value, "market.tick")
        self.assertEqual(EventType.SIGNAL_GENERATED.value, "signal.generated")
        
        # 系统事件
        self.assertEqual(EventType.SYSTEM_START.value, "system.start")
        self.assertEqual(EventType.ERROR_OCCURRED.value, "system.error")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestTelemetrySink))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestJSONLPersister))
    suite.addTests(loader.loadTestsFromTestCase(TestPIIMasker))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiLevelCache))
    suite.addTests(loader.loadTestsFromTestCase(TestRetryMechanism))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestEventType))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
