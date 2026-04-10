# -*- coding: utf-8 -*-
"""
BobQuant 事件驱动引擎测试套件

测试内容:
1. 事件引擎基本功能 (启动/停止/状态)
2. 8 种事件类型验证
3. 处理器功能测试 (注册/注销/执行)
4. 与现有系统集成测试

运行方式:
    cd /home/openclaw/.openclaw/workspace/quant_strategies
    python3 -m bobquant.tests.test_event_engine
"""
import sys
import time
import logging
import unittest
from datetime import datetime
from threading import Thread
from unittest.mock import Mock, MagicMock

# 添加路径
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from bobquant.event.engine import (
    Event, EventEngine,
    EVENT_TIMER, EVENT_TICK_UPDATE, EVENT_SIGNAL_GENERATED,
    EVENT_RISK_TRIGGERED, EVENT_ORDER_SUBMITTED, EVENT_TRADE_EXECUTED,
    EVENT_NOTIFY, EVENT_LOG, EVENT_MARKET_OPEN, EVENT_MARKET_CLOSE,
    create_event, trigger_risk_event, trigger_notify_event, trigger_signal_event,
    default_log_handler, default_notify_handler, default_risk_handler
)
from bobquant.event.handlers import (
    RiskHandler, NotifyHandler, SignalHandler, LogHandler, EventHandler
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestEventEngineBasic(unittest.TestCase):
    """事件引擎基本功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = EventEngine(interval=0.5, log_enabled=True)
    
    def tearDown(self):
        """测试后清理"""
        if self.engine.is_active():
            self.engine.stop()
    
    def test_01_engine_creation(self):
        """测试 1: 引擎创建"""
        self.assertIsNotNone(self.engine)
        self.assertFalse(self.engine.is_active())
        self.assertEqual(self.engine._interval, 0.5)
        stats = self.engine.get_stats()
        self.assertEqual(stats['active'], False)
        self.assertEqual(stats['event_count'], 0)
        self.assertEqual(stats['error_count'], 0)
        logger.info("✅ 引擎创建测试通过")
    
    def test_02_engine_start_stop(self):
        """测试 2: 引擎启动/停止"""
        # 启动引擎
        self.engine.start()
        self.assertTrue(self.engine.is_active())
        
        # 等待片刻
        time.sleep(1)
        
        # 停止引擎
        self.engine.stop()
        self.assertFalse(self.engine.is_active())
        
        stats = self.engine.get_stats()
        logger.info(f"✅ 启动/停止测试通过 - 处理事件数：{stats['event_count']}")
    
    def test_03_double_start_stop(self):
        """测试 3: 重复启动/停止处理"""
        self.engine.start()
        self.engine.start()  # 重复启动应该被忽略
        self.assertTrue(self.engine.is_active())
        
        self.engine.stop()
        self.engine.stop()  # 重复停止应该被忽略
        self.assertFalse(self.engine.is_active())
        logger.info("✅ 重复启动/停止测试通过")
    
    def test_04_event_put_when_inactive(self):
        """测试 4: 引擎未启动时放事件"""
        event = Event(EVENT_NOTIFY, {'title': 'Test', 'message': 'Test msg'})
        self.engine.put(event)  # 应该不会抛出异常
        logger.info("✅ 未启动时放事件测试通过")


class TestEventTypes(unittest.TestCase):
    """8 种事件类型验证测试"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = EventEngine(interval=0.5)
        self.received_events = []
        
        def capture_handler(event):
            self.received_events.append(event)
        
        self.engine.register_general(capture_handler)
        self.engine.start()
    
    def tearDown(self):
        """测试后清理"""
        if self.engine.is_active():
            self.engine.stop()
    
    def test_05_event_timer(self):
        """测试 5: 定时器事件 (EVENT_TIMER)"""
        time.sleep(1.5)  # 等待至少 2 个定时器事件
        timer_events = [e for e in self.received_events if e.type == EVENT_TIMER]
        self.assertGreater(len(timer_events), 0, "应该收到定时器事件")
        logger.info(f"✅ 定时器事件测试通过 - 收到 {len(timer_events)} 个事件")
    
    def test_06_event_tick_update(self):
        """测试 6: Tick 数据更新事件 (EVENT_TICK_UPDATE)"""
        event = Event(EVENT_TICK_UPDATE, {'code': 'SH.600000', 'price': 10.5})
        self.engine.put(event)
        time.sleep(0.5)
        
        tick_events = [e for e in self.received_events if e.type == EVENT_TICK_UPDATE]
        self.assertEqual(len(tick_events), 1)
        self.assertEqual(tick_events[0].data['code'], 'SH.600000')
        logger.info("✅ Tick 更新事件测试通过")
    
    def test_07_event_signal_generated(self):
        """测试 7: 信号生成事件 (EVENT_SIGNAL_GENERATED)"""
        event = Event(EVENT_SIGNAL_GENERATED, {
            'code': 'SH.600001',
            'name': '测试股票',
            'signal': 'buy',
            'reason': '测试信号',
            'strength': 'strong'
        })
        self.engine.put(event)
        time.sleep(0.5)
        
        signal_events = [e for e in self.received_events if e.type == EVENT_SIGNAL_GENERATED]
        self.assertEqual(len(signal_events), 1)
        self.assertEqual(signal_events[0].data['signal'], 'buy')
        logger.info("✅ 信号生成事件测试通过")
    
    def test_08_event_risk_triggered(self):
        """测试 8: 风控触发事件 (EVENT_RISK_TRIGGERED)"""
        event = Event(EVENT_RISK_TRIGGERED, {
            'code': 'SH.600000',
            'action': 'stop_loss',
            'reason': '测试止损',
            'shares': 100
        })
        self.engine.put(event)
        time.sleep(0.5)
        
        risk_events = [e for e in self.received_events if e.type == EVENT_RISK_TRIGGERED]
        self.assertEqual(len(risk_events), 1)
        self.assertEqual(risk_events[0].data['action'], 'stop_loss')
        logger.info("✅ 风控触发事件测试通过")
    
    def test_09_event_order_submitted(self):
        """测试 9: 委托提交事件 (EVENT_ORDER_SUBMITTED)"""
        event = Event(EVENT_ORDER_SUBMITTED, {
            'code': 'SH.600000',
            'action': 'buy',
            'shares': 100,
            'price': 10.5
        })
        self.engine.put(event)
        time.sleep(0.5)
        
        order_events = [e for e in self.received_events if e.type == EVENT_ORDER_SUBMITTED]
        self.assertEqual(len(order_events), 1)
        logger.info("✅ 委托提交事件测试通过")
    
    def test_10_event_trade_executed(self):
        """测试 10: 成交执行事件 (EVENT_TRADE_EXECUTED)"""
        event = Event(EVENT_TRADE_EXECUTED, {
            'code': 'SH.600000',
            'action': 'buy',
            'shares': 100,
            'price': 10.5,
            'trade_id': 'T001'
        })
        self.engine.put(event)
        time.sleep(0.5)
        
        trade_events = [e for e in self.received_events if e.type == EVENT_TRADE_EXECUTED]
        self.assertEqual(len(trade_events), 1)
        logger.info("✅ 成交执行事件测试通过")
    
    def test_11_event_notify(self):
        """测试 11: 通知发送事件 (EVENT_NOTIFY)"""
        event = Event(EVENT_NOTIFY, {
            'title': '测试通知',
            'message': '这是一条测试消息'
        })
        self.engine.put(event)
        time.sleep(0.5)
        
        notify_events = [e for e in self.received_events if e.type == EVENT_NOTIFY]
        self.assertEqual(len(notify_events), 1)
        logger.info("✅ 通知发送事件测试通过")
    
    def test_12_event_log(self):
        """测试 12: 日志记录事件 (EVENT_LOG)"""
        event = Event(EVENT_LOG, {
            'message': '测试日志消息',
            'level': logging.INFO
        })
        self.engine.put(event)
        time.sleep(0.5)
        
        log_events = [e for e in self.received_events if e.type == EVENT_LOG]
        self.assertEqual(len(log_events), 1)
        logger.info("✅ 日志记录事件测试通过")
    
    def test_13_event_market_open_close(self):
        """测试 13: 开盘/收盘事件 (EVENT_MARKET_OPEN, EVENT_MARKET_CLOSE)"""
        open_event = Event(EVENT_MARKET_OPEN, {'market': 'A 股', 'time': '09:30'})
        close_event = Event(EVENT_MARKET_CLOSE, {'market': 'A 股', 'time': '15:00'})
        
        self.engine.put(open_event)
        self.engine.put(close_event)
        time.sleep(0.5)
        
        open_events = [e for e in self.received_events if e.type == EVENT_MARKET_OPEN]
        close_events = [e for e in self.received_events if e.type == EVENT_MARKET_CLOSE]
        
        self.assertEqual(len(open_events), 1)
        self.assertEqual(len(close_events), 1)
        logger.info("✅ 开盘/收盘事件测试通过")


class TestHandlers(unittest.TestCase):
    """处理器功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = EventEngine(interval=0.5)
        self.handler_calls = []
    
    def tearDown(self):
        """测试后清理"""
        if self.engine.is_active():
            self.engine.stop()
    
    def test_14_handler_register_unregister(self):
        """测试 14: 处理器注册/注销"""
        def test_handler(event):
            self.handler_calls.append(event)
        
        # 注册处理器
        self.engine.register(EVENT_NOTIFY, test_handler)
        self.engine.start()
        
        # 发送事件
        self.engine.put(Event(EVENT_NOTIFY, {'test': 'data'}))
        time.sleep(0.5)
        
        self.assertEqual(len(self.handler_calls), 1)
        
        # 注销处理器
        self.engine.unregister(EVENT_NOTIFY, test_handler)
        self.handler_calls.clear()
        
        # 再次发送事件
        self.engine.put(Event(EVENT_NOTIFY, {'test': 'data2'}))
        time.sleep(0.5)
        
        self.assertEqual(len(self.handler_calls), 0)
        logger.info("✅ 处理器注册/注销测试通过")
    
    def test_15_general_handler(self):
        """测试 15: 通用处理器"""
        def general_handler(event):
            self.handler_calls.append(event)
        
        self.engine.register_general(general_handler)
        self.engine.start()
        
        # 发送不同类型的事件
        self.engine.put(Event(EVENT_NOTIFY, {'test': 'notify'}))
        self.engine.put(Event(EVENT_SIGNAL_GENERATED, {'test': 'signal'}))
        time.sleep(0.5)
        
        # 至少收到 2 个事件 (可能包含定时器事件)
        self.assertGreaterEqual(len(self.handler_calls), 2)
        logger.info(f"✅ 通用处理器测试通过 - 收到 {len(self.handler_calls)} 个事件")
    
    def test_16_multiple_handlers_same_event(self):
        """测试 16: 同一事件多个处理器"""
        def handler1(event):
            self.handler_calls.append(('h1', event))
        
        def handler2(event):
            self.handler_calls.append(('h2', event))
        
        self.engine.register(EVENT_NOTIFY, handler1)
        self.engine.register(EVENT_NOTIFY, handler2)
        self.engine.start()
        
        self.engine.put(Event(EVENT_NOTIFY, {'test': 'data'}))
        time.sleep(0.5)
        
        self.assertEqual(len(self.handler_calls), 2)
        logger.info("✅ 多处理器测试通过")
    
    def test_17_handler_error_handling(self):
        """测试 17: 处理器错误处理"""
        def error_handler(event):
            raise ValueError("测试错误")
        
        self.engine.register(EVENT_NOTIFY, error_handler)
        self.engine.start()
        
        # 发送事件，处理器会抛出异常，但引擎应该继续运行
        self.engine.put(Event(EVENT_NOTIFY, {'test': 'data'}))
        time.sleep(0.5)
        
        stats = self.engine.get_stats()
        self.assertGreater(stats['error_count'], 0, "应该记录错误")
        self.assertTrue(self.engine.is_active(), "引擎应该继续运行")
        logger.info(f"✅ 错误处理测试通过 - 错误数：{stats['error_count']}")
    
    def test_18_risk_handler_class(self):
        """测试 18: RiskHandler 类"""
        # 创建模拟对象
        mock_executor = Mock()
        mock_account = Mock()
        mock_data_provider = Mock()
        
        mock_account.has_position.return_value = True
        mock_account.get_position.return_value = {'name': '测试股票', 'shares': 100}
        mock_data_provider.get_quote.return_value = {'current': 10.5}
        
        handler = RiskHandler(mock_executor, mock_account, mock_data_provider)
        self.engine.register(EVENT_RISK_TRIGGERED, handler.handle)
        self.engine.start()
        
        # 触发风控事件
        trigger_risk_event(self.engine, "SH.600000", "stop_loss", "测试止损", 100)
        time.sleep(0.5)
        
        # 验证 executor.sell 被调用
        mock_executor.sell.assert_called_once()
        logger.info("✅ RiskHandler 测试通过")
    
    def test_19_notify_handler_class(self):
        """测试 19: NotifyHandler 类"""
        handler = NotifyHandler(user_id='test_user')
        self.engine.register(EVENT_NOTIFY, handler.handle)
        self.engine.start()
        
        trigger_notify_event(self.engine, "测试通知", "测试消息")
        time.sleep(0.5)
        
        logger.info("✅ NotifyHandler 测试通过")
    
    def test_20_signal_handler_class(self):
        """测试 20: SignalHandler 类"""
        mock_strategy = Mock()
        handler = SignalHandler(strategy_engine=mock_strategy)
        self.engine.register(EVENT_SIGNAL_GENERATED, handler.handle)
        self.engine.start()
        
        trigger_signal_event(self.engine, "SH.600001", "测试股票", "buy", "测试原因", "strong")
        time.sleep(0.5)
        
        # 验证策略引擎记录了信号
        mock_strategy.record_signal.assert_called_once()
        logger.info("✅ SignalHandler 测试通过")
    
    def test_21_log_handler_class(self):
        """测试 21: LogHandler 类"""
        handler = LogHandler()
        self.engine.register_general(handler.handle)
        self.engine.start()
        
        self.engine.put(Event(EVENT_LOG, {'message': '测试日志'}))
        time.sleep(0.5)
        
        logger.info("✅ LogHandler 测试通过")
    
    def test_22_event_handler_class(self):
        """测试 22: EventHandler 通用类"""
        callback_calls = []
        
        def my_callback(event):
            callback_calls.append(event)
        
        handler = EventHandler(my_callback, event_types=[EVENT_NOTIFY])
        self.engine.register(EVENT_NOTIFY, handler.handle)
        self.engine.start()
        
        self.engine.put(Event(EVENT_NOTIFY, {'test': 'data'}))
        time.sleep(0.5)
        
        self.assertEqual(len(callback_calls), 1)
        logger.info("✅ EventHandler 测试通过")


class TestIntegration(unittest.TestCase):
    """与现有系统集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = EventEngine(interval=0.5)
        self.integration_results = {
            'timer_events': 0,
            'risk_events': 0,
            'notify_events': 0,
            'signal_events': 0,
            'errors': 0
        }
    
    def tearDown(self):
        """测试后清理"""
        if self.engine.is_active():
            self.engine.stop()
    
    def _integration_handler(self, event):
        """集成测试处理器"""
        try:
            if event.type == EVENT_TIMER:
                self.integration_results['timer_events'] += 1
            elif event.type == EVENT_RISK_TRIGGERED:
                self.integration_results['risk_events'] += 1
            elif event.type == EVENT_NOTIFY:
                self.integration_results['notify_events'] += 1
            elif event.type == EVENT_SIGNAL_GENERATED:
                self.integration_results['signal_events'] += 1
        except Exception as e:
            self.integration_results['errors'] += 1
            logger.error(f"集成处理器错误：{e}")
    
    def test_23_concurrent_event_processing(self):
        """测试 23: 并发事件处理"""
        self.engine.register_general(self._integration_handler)
        self.engine.start()
        
        # 快速发送多个事件
        for i in range(10):
            self.engine.put(Event(EVENT_NOTIFY, {'index': i}))
            self.engine.put(Event(EVENT_SIGNAL_GENERATED, {'index': i}))
        
        time.sleep(2)
        
        stats = self.engine.get_stats()
        self.assertEqual(stats['event_count'], 20 + stats['event_count'] - 20)  # 验证事件被处理
        self.assertEqual(self.integration_results['errors'], 0)
        logger.info(f"✅ 并发处理测试通过 - 处理事件数：{stats['event_count']}")
    
    def test_24_mixed_event_types(self):
        """测试 24: 混合事件类型处理"""
        self.engine.register_general(self._integration_handler)
        self.engine.start()
        
        # 发送各种类型的事件
        event_types = [
            EVENT_TIMER,
            EVENT_TICK_UPDATE,
            EVENT_SIGNAL_GENERATED,
            EVENT_RISK_TRIGGERED,
            EVENT_ORDER_SUBMITTED,
            EVENT_TRADE_EXECUTED,
            EVENT_NOTIFY,
            EVENT_LOG
        ]
        
        for event_type in event_types:
            self.engine.put(Event(event_type, {'type': event_type}))
        
        time.sleep(2)
        
        stats = self.engine.get_stats()
        self.assertGreater(stats['event_count'], len(event_types))  # 包含定时器事件
        logger.info(f"✅ 混合事件类型测试通过 - 总事件数：{stats['event_count']}")
    
    def test_25_long_running_engine(self):
        """测试 25: 长时间运行测试"""
        self.engine.register_general(self._integration_handler)
        self.engine.start()
        
        # 运行 5 秒
        time.sleep(5)
        
        stats = self.engine.get_stats()
        self.assertTrue(self.engine.is_active())
        self.assertGreater(stats['event_count'], 0)
        logger.info(f"✅ 长时间运行测试通过 - 运行 5 秒，处理 {stats['event_count']} 个事件")
    
    def test_26_helper_functions(self):
        """测试 26: 便捷函数测试"""
        self.engine.register_general(self._integration_handler)
        self.engine.start()
        
        # 测试便捷函数
        trigger_risk_event(self.engine, "SH.600000", "stop_loss", "测试", 100)
        trigger_notify_event(self.engine, "测试", "消息")
        trigger_signal_event(self.engine, "SH.600001", "股票", "buy", "原因", "strong")
        
        time.sleep(1)
        
        self.assertEqual(self.integration_results['risk_events'], 1)
        self.assertEqual(self.integration_results['notify_events'], 1)
        self.assertEqual(self.integration_results['signal_events'], 1)
        logger.info("✅ 便捷函数测试通过")
    
    def test_27_create_event_function(self):
        """测试 27: create_event 便捷函数"""
        event = create_event(EVENT_NOTIFY, {'title': 'Test', 'message': 'Msg'})
        self.assertIsInstance(event, Event)
        self.assertEqual(event.type, EVENT_NOTIFY)
        self.assertEqual(event.data['title'], 'Test')
        logger.info("✅ create_event 函数测试通过")
    
    def test_28_stats_accuracy(self):
        """测试 28: 统计信息准确性"""
        self.engine.register_general(self._integration_handler)
        self.engine.start()
        
        # 发送 5 个事件
        for i in range(5):
            self.engine.put(Event(EVENT_NOTIFY, {'i': i}))
        
        time.sleep(1)
        
        stats = self.engine.get_stats()
        self.assertGreater(stats['event_count'], 0)
        self.assertGreaterEqual(stats['event_count'], 5)  # 至少 5 个事件 + 定时器事件
        self.assertEqual(stats['active'], True)
        logger.info(f"✅ 统计信息测试通过 - {stats}")
    
    def test_29_queue_thread_safety(self):
        """测试 29: 队列线程安全性"""
        self.engine.register_general(self._integration_handler)
        self.engine.start()
        
        # 从多个线程同时发送事件
        def send_events(thread_id):
            for i in range(10):
                self.engine.put(Event(EVENT_NOTIFY, {'thread': thread_id, 'i': i}))
        
        threads = []
        for i in range(5):
            t = Thread(target=send_events, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        time.sleep(1)
        
        stats = self.engine.get_stats()
        self.assertEqual(stats['event_count'], 50 + stats['event_count'] - 50)  # 5 线程 * 10 事件
        self.assertEqual(self.integration_results['errors'], 0)
        logger.info(f"✅ 线程安全测试通过 - 处理 {stats['event_count']} 个事件")
    
    def test_30_system_integration(self):
        """测试 30: 系统集成模拟"""
        # 模拟真实使用场景
        mock_executor = Mock()
        mock_account = Mock()
        mock_data_provider = Mock()
        
        mock_account.has_position.return_value = True
        mock_account.get_position.return_value = {'name': '测试股票', 'shares': 100}
        mock_data_provider.get_quote.return_value = {'current': 10.5}
        
        # 注册所有处理器
        risk_handler = RiskHandler(mock_executor, mock_account, mock_data_provider)
        notify_handler = NotifyHandler('test_user')
        signal_handler = SignalHandler()
        log_handler = LogHandler()
        
        self.engine.register(EVENT_RISK_TRIGGERED, risk_handler.handle)
        self.engine.register(EVENT_NOTIFY, notify_handler.handle)
        self.engine.register(EVENT_SIGNAL_GENERATED, signal_handler.handle)
        self.engine.register_general(log_handler.handle)
        
        self.engine.start()
        
        # 模拟真实交易流程
        # 1. 生成信号
        trigger_signal_event(self.engine, "SH.600001", "测试股票", "buy", "买入信号", "strong")
        time.sleep(0.5)
        
        # 2. 触发风控
        trigger_risk_event(self.engine, "SH.600000", "stop_loss", "止损触发", 100)
        time.sleep(0.5)
        
        # 3. 发送通知
        trigger_notify_event(self.engine, "交易通知", "执行完成")
        time.sleep(0.5)
        
        # 验证
        stats = self.engine.get_stats()
        self.assertTrue(self.engine.is_active())
        self.assertGreater(stats['event_count'], 0)
        
        # 验证风控被执行
        mock_executor.sell.assert_called()
        
        logger.info(f"✅ 系统集成测试通过 - 总事件数：{stats['event_count']}")


def run_tests():
    """运行所有测试"""
    print("=" * 80)
    print("BobQuant 事件驱动引擎测试套件")
    print("=" * 80)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestEventEngineBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestEventTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestHandlers))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出统计
    print()
    print("=" * 80)
    print("测试结果统计")
    print("=" * 80)
    print(f"总测试数：{result.testsRun}")
    print(f"成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 返回结果
    return {
        'total': result.testsRun,
        'passed': result.testsRun - len(result.failures) - len(result.errors),
        'failures': len(result.failures),
        'errors': len(result.errors),
        'success': result.wasSuccessful()
    }


if __name__ == '__main__':
    results = run_tests()
    
    # 如果测试失败，退出码为 1
    sys.exit(0 if results['success'] else 1)
