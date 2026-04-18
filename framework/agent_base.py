#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 基类 - 所有 Agent 的父类
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from .message_queue import MessageQueue, Message, get_queue
from .event_bus import EventBus, Event, get_event_bus

logger = logging.getLogger(__name__)


class AgentBase(ABC):
    """
    Agent 基类
    
    所有 Agent 都需要继承此类并实现相应方法
    
    生命周期:
    1. __init__ - 初始化
    2. on_start - 启动时调用
    3. on_message - 收到消息时调用
    4. on_tick - 定期调用 (心跳)
    5. on_stop - 停止时调用
    """
    
    def __init__(self, name: str, queue: MessageQueue = None, 
                 event_bus: EventBus = None):
        """
        初始化 Agent
        
        Args:
            name: Agent 名称
            queue: 消息队列 (可选，默认使用全局)
            event_bus: 事件总线 (可选，默认使用全局)
        """
        self.name = name
        self.queue = queue or get_queue()
        self.event_bus = event_bus or get_event_bus()
        
        self.running = False
        self.worker_thread = None
        
        # 订阅消息队列
        self.queue.subscribe(name, self._on_message_wrapper)
        
        logger.info(f"Agent {name} 初始化完成")
    
    def _on_message_wrapper(self, message: Message):
        """消息包装器"""
        try:
            self.on_message(message)
        except Exception as e:
            logger.error(f"{self.name} 处理消息失败：{e}")
            self.queue.fail(message.id, self.name, str(e), retry=True)
    
    @abstractmethod
    def on_message(self, message: Message):
        """
        处理收到的消息 (必须实现)
        
        Args:
            message: 消息对象
        """
        pass
    
    def on_start(self):
        """启动时调用 (可选实现)"""
        logger.info(f"{self.name} 启动")
    
    def on_stop(self):
        """停止时调用 (可选实现)"""
        logger.info(f"{self.name} 停止")
    
    def on_tick(self):
        """定期调用 (可选实现，默认每 10 秒)"""
        pass
    
    def send_message(self, to_agent: str, msg_type: str, 
                     content: Dict[str, Any], priority: int = 5) -> str:
        """
        发送消息
        
        Args:
            to_agent: 接收者
            msg_type: 消息类型
            content: 消息内容
            priority: 优先级
        
        Returns:
            消息 ID
        """
        return self.queue.send(self.name, to_agent, msg_type, content, priority)
    
    def broadcast(self, msg_type: str, content: Dict[str, Any], 
                  exclude: list = None) -> list:
        """
        广播消息
        
        Args:
            msg_type: 消息类型
            content: 消息内容
            exclude: 排除的 Agent 列表
        
        Returns:
            消息 ID 列表
        """
        return self.queue.broadcast(self.name, msg_type, content, exclude)
    
    def publish_event(self, event_type: str, data: Dict[str, Any]):
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        self.event_bus.publish(event_type, self.name, data)
    
    def start(self, tick_interval: float = 10.0):
        """
        启动 Agent
        
        Args:
            tick_interval: 心跳间隔 (秒)
        """
        if self.running:
            logger.warning(f"{self.name} 已在运行中")
            return
        
        self.running = True
        self.on_start()
        
        # 启动心跳线程
        def tick_worker():
            while self.running:
                try:
                    self.on_tick()
                except Exception as e:
                    logger.error(f"{self.name} 心跳失败：{e}")
                time.sleep(tick_interval)
        
        self.worker_thread = threading.Thread(target=tick_worker, daemon=True)
        self.worker_thread.start()
        
        logger.info(f"{self.name} 已启动 (心跳间隔：{tick_interval}s)")
    
    def stop(self):
        """停止 Agent"""
        self.running = False
        self.on_stop()
        self.queue.unsubscribe(self.name)
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        logger.info(f"{self.name} 已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "name": self.name,
            "running": self.running,
            "timestamp": datetime.now().isoformat()
        }


class SimpleAgent(AgentBase):
    """
    简单 Agent 实现 - 用于快速原型
    
    只需提供 on_message 的实现
    """
    
    def __init__(self, name: str, message_handler=None, **kwargs):
        """
        初始化简单 Agent
        
        Args:
            name: Agent 名称
            message_handler: 消息处理函数 (可选)
        """
        super().__init__(name, **kwargs)
        self._handler = message_handler
    
    def on_message(self, message: Message):
        if self._handler:
            self._handler(message, self)
        else:
            logger.info(f"{self.name} 收到消息：{message.msg_type}")
    
    def set_handler(self, handler):
        """设置消息处理器"""
        self._handler = handler
