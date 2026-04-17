# -*- coding: utf-8 -*-
"""
BobQuant 事件驱动模块

提供事件驱动架构支持，基于 vn.py EventEngine 设计。
支持混合架构：保留现有轮询主循环，引入事件机制处理异步/紧急事件。

模块结构:
- engine: 事件引擎核心 (Event, EventEngine)
- handlers: 事件处理器实现 (风控、通知、日志等)
- events: 事件类型定义和便捷函数

使用示例:
    from bobquant.event import EventEngine, EVENT_RISK_TRIGGERED, trigger_risk_event
    
    # 创建并启动引擎
    engine = EventEngine(interval=1)
    engine.start()
    
    # 注册处理器
    from bobquant.event.handlers import RiskHandler, NotifyHandler
    engine.register(EVENT_RISK_TRIGGERED, RiskHandler().handle)
    
    # 触发事件
    trigger_risk_event(engine, "SH.600000", "stop_loss", "止损触发", 100)
    
    # 停止引擎
    engine.stop()
"""

from .engine import (
    # 事件类
    Event,
    
    # 事件引擎
    EventEngine,
    
    # 事件类型常量
    EVENT_TIMER,
    EVENT_TICK_UPDATE,
    EVENT_SIGNAL_GENERATED,
    EVENT_RISK_TRIGGERED,
    EVENT_ORDER_SUBMITTED,
    EVENT_TRADE_EXECUTED,
    EVENT_NOTIFY,
    EVENT_LOG,
    EVENT_MARKET_OPEN,
    EVENT_MARKET_CLOSE,
    
    # 便捷函数
    create_event,
    trigger_risk_event,
    trigger_notify_event,
    trigger_signal_event,
    
    # 默认处理器
    default_log_handler,
    default_notify_handler,
    default_risk_handler,
)

__all__ = [
    # 核心类
    'Event',
    'EventEngine',
    
    # 事件类型
    'EVENT_TIMER',
    'EVENT_TICK_UPDATE',
    'EVENT_SIGNAL_GENERATED',
    'EVENT_RISK_TRIGGERED',
    'EVENT_ORDER_SUBMITTED',
    'EVENT_TRADE_EXECUTED',
    'EVENT_NOTIFY',
    'EVENT_LOG',
    'EVENT_MARKET_OPEN',
    'EVENT_MARKET_CLOSE',
    
    # 便捷函数
    'create_event',
    'trigger_risk_event',
    'trigger_notify_event',
    'trigger_signal_event',
    
    # 默认处理器
    'default_log_handler',
    'default_notify_handler',
    'default_risk_handler',
]

__version__ = '1.0.0'
__author__ = 'BobQuant Team'
