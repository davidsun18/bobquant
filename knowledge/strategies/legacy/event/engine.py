# -*- coding: utf-8 -*-
"""
BobQuant 事件驱动引擎 v1.0 (原型)

基于 vn.py EventEngine 设计，为 bobquant 提供事件驱动能力。
支持混合架构：保留现有轮询主循环，引入事件机制处理异步/紧急事件。

功能:
- 事件队列管理 (线程安全)
- 事件处理器注册/注销
- 定时器事件
- 通用处理器支持

事件类型:
- EVENT_TIMER: 定时器事件 (默认 1 秒间隔)
- EVENT_TICK_UPDATE: Tick 数据更新
- EVENT_SIGNAL_GENERATED: 信号生成
- EVENT_RISK_TRIGGERED: 风控触发 (紧急)
- EVENT_ORDER_SUBMITTED: 委托提交
- EVENT_TRADE_EXECUTED: 成交执行
- EVENT_NOTIFY: 通知发送 (异步)
- EVENT_LOG: 日志记录

使用示例:
    # 创建事件引擎
    engine = EventEngine(interval=1)
    
    # 注册事件处理器
    engine.register(EVENT_RISK_TRIGGERED, on_risk_event)
    engine.register(EVENT_NOTIFY, on_notify_event)
    
    # 启动引擎
    engine.start()
    
    # 触发事件
    engine.put(Event(EVENT_RISK_TRIGGERED, data={'code': 'SH.600000', 'action': 'stop_loss'}))
    
    # 停止引擎
    engine.stop()
"""
from collections import defaultdict
from collections.abc import Callable
from queue import Empty, Queue
from threading import Thread
from time import sleep
from typing import Any
import logging

# ============ 事件类型定义 ============
EVENT_TIMER = "eTimer"                    # 定时器事件
EVENT_TICK_UPDATE = "eTickUpdate"         # Tick 数据更新
EVENT_SIGNAL_GENERATED = "eSignal"        # 信号生成
EVENT_RISK_TRIGGERED = "eRisk"            # 风控触发 (紧急)
EVENT_ORDER_SUBMITTED = "eOrder"          # 委托提交
EVENT_TRADE_EXECUTED = "eTrade"           # 成交执行
EVENT_NOTIFY = "eNotify"                  # 通知发送 (异步)
EVENT_LOG = "eLog"                        # 日志记录
EVENT_MARKET_OPEN = "eMarketOpen"         # 开盘事件
EVENT_MARKET_CLOSE = "eMarketClose"       # 收盘事件


class Event:
    """
    事件对象
    
    包含事件类型和数据，用于在事件引擎中传递信息。
    """
    
    def __init__(self, type: str, data: Any = None) -> None:
        """
        初始化事件
        
        Args:
            type: 事件类型字符串 (用于分发)
            data: 事件携带的数据 (可以是任意 Python 对象)
        """
        self.type: str = type
        self.data: Any = data
    
    def __repr__(self) -> str:
        return f"Event(type={self.type}, data={self.data})"


# 定义处理器函数类型
HandlerType = Callable[[Event], None]


class EventEngine:
    """
    事件引擎
    
    基于队列和线程的事件分发框架。
    支持:
    - 特定事件类型处理器
    - 通用处理器 (监听所有事件)
    - 定时器事件 (固定间隔触发)
    - 线程安全的事件队列
    
    架构:
        Timer Thread ──▶ Event Queue ──▶ Event Handler Thread
        (生成定时事件)    (线程安全)      (处理所有事件)
    """
    
    def __init__(self, interval: int = 1, log_enabled: bool = True) -> None:
        """
        初始化事件引擎
        
        Args:
            interval: 定时器事件间隔 (秒)，默认 1 秒
            log_enabled: 是否启用日志，默认 True
        """
        self._interval: int = interval
        self._queue: Queue = Queue()
        self._active: bool = False
        self._thread: Thread = Thread(target=self._run, name="EventEngine-Handler")
        self._timer: Thread = Thread(target=self._run_timer, name="EventEngine-Timer")
        self._handlers: defaultdict = defaultdict(list)
        self._general_handlers: list = []
        self._log_enabled: bool = log_enabled
        
        # 事件统计
        self._event_count: int = 0
        self._error_count: int = 0
        
        if self._log_enabled:
            self._log(f"事件引擎初始化完成 (间隔={interval}s)")
    
    def _log(self, message: str) -> None:
        """内部日志方法"""
        if self._log_enabled:
            logging.info(f"[EventEngine] {message}")
    
    def _log_error(self, message: str) -> None:
        """内部错误日志方法"""
        if self._log_enabled:
            logging.error(f"[EventEngine] {message}")
    
    def _run(self) -> None:
        """
        事件处理主循环
        
        从队列中获取事件并处理，直到引擎停止。
        使用阻塞式 get (timeout=1) 以便响应停止信号。
        """
        self._log("事件处理线程启动")
        
        while self._active:
            try:
                # 阻塞获取事件 (timeout=1 秒，以便检查_active 状态)
                event: Event = self._queue.get(block=True, timeout=1)
                self._event_count += 1
                self._process(event)
            except Empty:
                # 队列为空，继续循环
                pass
            except Exception as e:
                self._error_count += 1
                self._log_error(f"事件处理异常：{e}")
        
        self._log(f"事件处理线程停止 (处理事件数={self._event_count}, 错误数={self._error_count})")
    
    def _process(self, event: Event) -> None:
        """
        处理单个事件
        
        1. 首先分发给注册了该事件类型的处理器
        2. 然后分发给通用处理器 (监听所有事件)
        
        Args:
            event: 要处理的事件对象
        """
        # 分发给特定类型的处理器
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    self._error_count += 1
                    self._log_error(f"处理器执行失败 [{event.type}]: {e}")
        
        # 分发给通用处理器
        if self._general_handlers:
            for handler in self._general_handlers:
                try:
                    handler(event)
                except Exception as e:
                    self._error_count += 1
                    self._log_error(f"通用处理器执行失败 [{event.type}]: {e}")
    
    def _run_timer(self) -> None:
        """
        定时器线程
        
        按固定间隔生成定时器事件。
        """
        self._log(f"定时器线程启动 (间隔={self._interval}s)")
        
        while self._active:
            sleep(self._interval)
            event: Event = Event(EVENT_TIMER)
            self.put(event)
        
        self._log("定时器线程停止")
    
    def start(self) -> None:
        """
        启动事件引擎
        
        启动事件处理线程和定时器线程。
        引擎必须在创建后显式调用 start() 才能开始工作。
        """
        if self._active:
            self._log("引擎已在运行，忽略 start() 调用")
            return
        
        self._active = True
        self._thread.start()
        self._timer.start()
        self._log("事件引擎已启动")
    
    def stop(self) -> None:
        """
        停止事件引擎
        
        设置停止标志并等待线程结束。
        调用后引擎将不再处理新事件。
        """
        if not self._active:
            self._log("引擎已停止，忽略 stop() 调用")
            return
        
        self._active = False
        self._timer.join()  # 等待定时器线程结束
        self._thread.join()  # 等待事件处理线程结束
        self._log("事件引擎已停止")
    
    def put(self, event: Event) -> None:
        """
        将事件放入队列
        
        线程安全，可在任意线程中调用。
        
        Args:
            event: 要放入队列的事件对象
        """
        if not self._active:
            self._log(f"警告：引擎未启动，事件将被忽略 [{event.type}]")
            return
        
        self._queue.put(event)
    
    def register(self, type: str, handler: HandlerType) -> None:
        """
        注册特定事件类型的处理器
        
        同一处理器不能重复注册同一事件类型。
        
        Args:
            type: 事件类型字符串
            handler: 处理器函数 (接收 Event 对象作为参数)
        """
        handler_list: list = self._handlers[type]
        if handler not in handler_list:
            handler_list.append(handler)
            self._log(f"注册处理器：{type} -> {handler.__name__}")
        else:
            self._log(f"警告：处理器已注册，忽略重复注册 [{type} -> {handler.__name__}]")
    
    def unregister(self, type: str, handler: HandlerType) -> None:
        """
        注销已注册的处理器
        
        Args:
            type: 事件类型字符串
            handler: 要注销的处理器函数
        """
        handler_list: list = self._handlers[type]
        
        if handler in handler_list:
            handler_list.remove(handler)
            self._log(f"注销处理器：{type} -> {handler.__name__}")
            
            # 如果该类型没有处理器了，清理字典
            if not handler_list:
                self._handlers.pop(type)
        else:
            self._log(f"警告：处理器未注册，无法注销 [{type} -> {handler.__name__}]")
    
    def register_general(self, handler: HandlerType) -> None:
        """
        注册通用处理器
        
        通用处理器会接收所有类型的事件。
        
        Args:
            handler: 处理器函数
        """
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)
            self._log(f"注册通用处理器：{handler.__name__}")
        else:
            self._log(f"警告：通用处理器已注册，忽略重复注册 [{handler.__name__}]")
    
    def unregister_general(self, handler: HandlerType) -> None:
        """
        注销通用处理器
        
        Args:
            handler: 要注销的处理器函数
        """
        if handler in self._general_handlers:
            self._general_handlers.remove(handler)
            self._log(f"注销通用处理器：{handler.__name__}")
        else:
            self._log(f"警告：通用处理器未注册，无法注销 [{handler.__name__}]")
    
    def is_active(self) -> bool:
        """
        检查引擎是否正在运行
        
        Returns:
            bool: True 表示引擎正在运行
        """
        return self._active
    
    def get_stats(self) -> dict:
        """
        获取引擎统计信息
        
        Returns:
            dict: 包含事件计数和错误计数的字典
        """
        return {
            'active': self._active,
            'event_count': self._event_count,
            'error_count': self._error_count,
            'queue_size': self._queue.qsize(),
            'handler_count': sum(len(h) for h in self._handlers.values()),
            'general_handler_count': len(self._general_handlers)
        }


# ============ 便捷函数 ============

def create_event(event_type: str, data: Any = None) -> Event:
    """
    创建事件的便捷函数
    
    Args:
        event_type: 事件类型
        data: 事件数据
    
    Returns:
        Event: 创建的事件对象
    """
    return Event(event_type, data)


def trigger_risk_event(engine: EventEngine, code: str, action: str, reason: str = '', shares: int = 0) -> None:
    """
    触发风控事件的便捷函数
    
    Args:
        engine: 事件引擎实例
        code: 股票代码
        action: 风控动作 ('stop_loss', 'take_profit', 'trailing_stop')
        reason: 触发原因
        shares: 涉及股数
    """
    data = {
        'code': code,
        'action': action,
        'reason': reason,
        'shares': shares,
        'timestamp': None  # 由处理器设置
    }
    event = Event(EVENT_RISK_TRIGGERED, data)
    engine.put(event)


def trigger_notify_event(engine: EventEngine, title: str, message: str) -> None:
    """
    触发通知事件的便捷函数
    
    Args:
        engine: 事件引擎实例
        title: 通知标题
        message: 通知内容
    """
    data = {
        'title': title,
        'message': message,
        'timestamp': None  # 由处理器设置
    }
    event = Event(EVENT_NOTIFY, data)
    engine.put(event)


def trigger_signal_event(engine: EventEngine, code: str, name: str, signal: str, 
                         reason: str, strength: str = 'normal') -> None:
    """
    触发信号事件的便捷函数
    
    Args:
        engine: 事件引擎实例
        code: 股票代码
        name: 股票名称
        signal: 信号类型 ('buy', 'sell')
        reason: 信号原因
        strength: 信号强度 ('normal', 'strong', 'weak')
    """
    data = {
        'code': code,
        'name': name,
        'signal': signal,
        'reason': reason,
        'strength': strength,
        'timestamp': None  # 由处理器设置
    }
    event = Event(EVENT_SIGNAL_GENERATED, data)
    engine.put(event)


# ============ 示例处理器 ============

def default_log_handler(event: Event) -> None:
    """
    默认日志处理器
    
    记录所有事件到日志。可作为通用处理器注册。
    
    Args:
        event: 事件对象
    """
    logging.info(f"[Event] {event.type}: {event.data}")


def default_notify_handler(event: Event) -> None:
    """
    默认通知处理器
    
    处理 EVENT_NOTIFY 类型事件，发送飞书通知。
    注意：需要实际实现 send_feishu 函数。
    
    Args:
        event: 事件对象
    """
    if event.type != EVENT_NOTIFY:
        return
    
    data = event.data
    title = data.get('title', '通知')
    message = data.get('message', '')
    
    # TODO: 实际实现时替换为真实的 send_feishu 调用
    # from notify.feishu import send_feishu
    # send_feishu(title, message, user_id)
    
    logging.info(f"[通知] {title}: {message}")


def default_risk_handler(event: Event) -> None:
    """
    默认风控处理器
    
    处理 EVENT_RISK_TRIGGERED 类型事件，执行紧急风控操作。
    注意：需要实际实现风控执行逻辑。
    
    Args:
        event: 事件对象
    """
    if event.type != EVENT_RISK_TRIGGERED:
        return
    
    data = event.data
    code = data.get('code', '')
    action = data.get('action', '')
    reason = data.get('reason', '')
    shares = data.get('shares', 0)
    
    # TODO: 实际实现时替换为真实的风控执行逻辑
    # executor.sell(code, name, shares, price, reason, label)
    
    logging.info(f"[风控] {code}: {action} - {reason} (股数：{shares})")


# ============ 测试代码 ============

if __name__ == "__main__":
    import time
    from datetime import datetime
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("BobQuant 事件引擎测试")
    print("=" * 60)
    
    # 创建引擎
    engine = EventEngine(interval=1)
    
    # 注册处理器
    engine.register(EVENT_NOTIFY, default_notify_handler)
    engine.register(EVENT_RISK_TRIGGERED, default_risk_handler)
    engine.register_general(default_log_handler)
    
    # 启动引擎
    engine.start()
    print(f"\n✅ 事件引擎已启动")
    print(f"   统计：{engine.get_stats()}")
    
    # 发送测试事件
    print("\n📤 发送测试事件...")
    
    # 测试通知事件
    trigger_notify_event(engine, "测试通知", "这是一条测试通知消息")
    
    # 测试风控事件
    trigger_risk_event(engine, "SH.600000", "stop_loss", "测试止损", 100)
    
    # 测试信号事件
    trigger_signal_event(engine, "SH.600001", "测试股票", "buy", "测试买入信号", "strong")
    
    # 等待处理
    time.sleep(2)
    
    # 查看统计
    print(f"\n📊 引擎统计：{engine.get_stats()}")
    
    # 运行 5 秒后停止
    print("\n⏳ 运行 5 秒后停止...")
    time.sleep(5)
    
    # 停止引擎
    engine.stop()
    print(f"\n⏹️ 事件引擎已停止")
    print(f"   最终统计：{engine.get_stats()}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
