#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件总线模块 - WebSocket 实时事件推送
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set, Any, Callable, Optional
from dataclasses import dataclass, asdict
import threading
import queue

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """事件数据结构"""
    id: str
    timestamp: str
    event_type: str
    source: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EventBus:
    """
    事件总线 - 支持 WebSocket 实时推送
    
    特性:
    - 发布/订阅模式
    - 事件类型过滤
    - WebSocket 连接管理
    - 事件历史记录
    """
    
    def __init__(self, max_history: int = 1000):
        """
        初始化事件总线
        
        Args:
            max_history: 最大历史事件数量
        """
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.websocket_clients: Set[Any] = set()
        self.event_history: List[Event] = []
        self.max_history = max_history
        
        # 线程安全队列 (用于跨线程事件)
        self.event_queue = queue.Queue()
        
        # 锁
        self.lock = threading.Lock()
        
        logger.info("事件总线初始化完成")
    
    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """
        订阅事件
        
        Args:
            event_type: 事件类型 (* 表示所有)
            callback: 回调函数
        """
        with self.lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = set()
            self.subscribers[event_type].add(callback)
        logger.debug(f"订阅事件：{event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        with self.lock:
            if event_type in self.subscribers:
                self.subscribers[event_type].discard(callback)
    
    def publish(self, event_type: str, source: str, data: Dict[str, Any]) -> str:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            source: 事件来源
            data: 事件数据
        
        Returns:
            事件 ID
        """
        import uuid
        
        event = Event(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            source=source,
            data=data
        )
        
        # 添加到历史
        with self.lock:
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
        
        # 通知订阅者
        self._notify_subscribers(event)
        
        # 推送到 WebSocket 客户端
        self._push_to_websockets(event)
        
        logger.debug(f"事件发布：{event_type} from {source}")
        
        return event.id
    
    def publish_async(self, event_type: str, source: str, data: Dict[str, Any]):
        """异步发布事件 (线程安全)"""
        self.event_queue.put((event_type, source, data))
    
    def process_async_events(self):
        """处理异步事件队列"""
        try:
            while not self.event_queue.empty():
                event_type, source, data = self.event_queue.get_nowait()
                self.publish(event_type, source, data)
        except queue.Empty:
            pass
    
    def _notify_subscribers(self, event: Event):
        """通知订阅者"""
        # 精确匹配
        callbacks = self.subscribers.get(event.event_type, set())
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调失败：{e}")
        
        # 通配符订阅
        wildcard_callbacks = self.subscribers.get("*", set())
        for callback in wildcard_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调失败：{e}")
    
    def _push_to_websockets(self, event: Event):
        """推送到 WebSocket 客户端"""
        # 这里需要实际的 WebSocket 实现
        # 在 FastAPI 中会使用 WebSocket 连接
        pass
    
    def register_websocket(self, websocket):
        """注册 WebSocket 连接"""
        self.websocket_clients.add(websocket)
        logger.info(f"WebSocket 连接已注册，当前连接数：{len(self.websocket_clients)}")
    
    def unregister_websocket(self, websocket):
        """注销 WebSocket 连接"""
        self.websocket_clients.discard(websocket)
        logger.info(f"WebSocket 连接已注销，当前连接数：{len(self.websocket_clients)}")
    
    async def send_to_websocket(self, websocket, event: Event):
        """发送事件到 WebSocket"""
        try:
            await websocket.send_text(event.to_json())
        except Exception as e:
            logger.error(f"WebSocket 发送失败：{e}")
            self.unregister_websocket(websocket)
    
    def broadcast_to_websockets(self, event: Event):
        """广播事件到所有 WebSocket 客户端 (同步版本)"""
        for ws in list(self.websocket_clients):
            try:
                # 这里需要在异步上下文中调用
                asyncio.create_task(self.send_to_websocket(ws, event))
            except Exception as e:
                logger.error(f"广播失败：{e}")
    
    def get_history(self, event_type: str = None, limit: int = 100) -> List[Event]:
        """
        获取历史事件
        
        Args:
            event_type: 事件类型过滤
            limit: 最大返回数量
        
        Returns:
            事件列表
        """
        with self.lock:
            if event_type:
                events = [e for e in self.event_history if e.event_type == event_type]
            else:
                events = list(self.event_history)
            
            return events[-limit:]
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "subscribers": sum(len(s) for s in self.subscribers.values()),
            "websocket_clients": len(self.websocket_clients),
            "history_size": len(self.event_history),
            "event_types": len(self.subscribers)
        }


# 全局单例
_global_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """获取全局事件总线单例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    bus = EventBus()
    
    def on_trade(event: Event):
        print(f"交易事件：{event.data}")
    
    def on_all(event: Event):
        print(f"所有事件：{event.event_type} - {event.data}")
    
    bus.subscribe("trade", on_trade)
    bus.subscribe("*", on_all)
    
    # 发布事件
    bus.publish("trade", "execution_bot", {
        "action": "buy",
        "stock": "600519",
        "price": 1400.00
    })
    
    print(f"事件统计：{bus.get_stats()}")
    print(f"历史事件：{len(bus.get_history())}")
