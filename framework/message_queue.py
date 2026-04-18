#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息队列模块 - 基于文件系统的轻量级消息队列
支持发布/订阅模式，无需 Redis 依赖
"""

import os
import json
import time
import uuid
import fcntl
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """消息数据结构"""
    id: str
    timestamp: str
    from_agent: str
    to_agent: str
    msg_type: str
    content: Dict[str, Any]
    priority: int = 0  # 0-10, 越高优先级越高
    status: str = "pending"  # pending, delivered, read, failed
    retry_count: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(**data)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        return cls.from_dict(json.loads(json_str))


class MessageQueue:
    """
    基于文件系统的消息队列
    
    特性:
    - 无需外部依赖 (Redis 等)
    - 支持发布/订阅
    - 消息持久化
    - 优先级队列
    - 自动清理过期消息
    """
    
    def __init__(self, queue_dir: str = None):
        """
        初始化消息队列
        
        Args:
            queue_dir: 队列数据存储目录
        """
        if queue_dir is None:
            queue_dir = "/home/openclaw/.openclaw/workspace/message_queue"
        
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        # 各个子目录
        self.pending_dir = self.queue_dir / "pending"
        self.delivered_dir = self.queue_dir / "delivered"
        self.failed_dir = self.queue_dir / "failed"
        self.archive_dir = self.queue_dir / "archive"
        
        for d in [self.pending_dir, self.delivered_dir, self.failed_dir, self.archive_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 订阅者注册表
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 运行标志
        self.running = False
        self.worker_thread = None
        
        logger.info(f"消息队列初始化完成：{self.queue_dir}")
    
    def publish(self, message: Message) -> str:
        """
        发布消息
        
        Args:
            message: 消息对象
        
        Returns:
            消息 ID
        """
        message.id = message.id or str(uuid.uuid4())
        message.timestamp = message.timestamp or datetime.now().isoformat()
        
        # 按优先级和接收者存储
        filename = f"{message.to_agent}_{message.priority}_{message.id}.json"
        filepath = self.pending_dir / filename
        
        with self.lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(message.to_json())
        
        logger.debug(f"消息发布：{message.id} -> {message.to_agent}")
        
        # 通知订阅者
        self._notify_subscribers(message)
        
        return message.id
    
    def subscribe(self, agent_name: str, callback: Callable[[Message], None]):
        """
        订阅消息
        
        Args:
            agent_name: Agent 名称
            callback: 回调函数
        """
        with self.lock:
            self.subscribers[agent_name].append(callback)
        logger.info(f"Agent {agent_name} 已订阅消息队列")
    
    def unsubscribe(self, agent_name: str, callback: Callable = None):
        """
        取消订阅
        
        Args:
            agent_name: Agent 名称
            callback: 特定回调函数 (可选)
        """
        with self.lock:
            if callback:
                if callback in self.subscribers[agent_name]:
                    self.subscribers[agent_name].remove(callback)
            else:
                self.subscribers[agent_name] = []
    
    def poll(self, agent_name: str, limit: int = 10) -> List[Message]:
        """
        轮询消息
        
        Args:
            agent_name: Agent 名称
            limit: 最大获取数量
        
        Returns:
            消息列表
        """
        messages = []
        
        with self.lock:
            # 查找该 Agent 的待处理消息
            pattern = f"{agent_name}_*_.json"
            for filepath in sorted(self.pending_dir.glob(pattern)):
                if len(messages) >= limit:
                    break
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    message = Message.from_json(content)
                    
                    # 移动到已投递目录
                    new_filepath = self.delivered_dir / filepath.name
                    filepath.rename(new_filepath)
                    
                    message.status = "delivered"
                    messages.append(message)
                    
                except Exception as e:
                    logger.error(f"读取消息失败 {filepath}: {e}")
                    # 移动到失败目录
                    try:
                        filepath.rename(self.failed_dir / filepath.name)
                    except:
                        pass
        
        return messages
    
    def ack(self, message_id: str, agent_name: str):
        """
        确认消息已处理
        
        Args:
            message_id: 消息 ID
            agent_name: Agent 名称
        """
        # 查找消息文件
        pattern = f"{agent_name}_*_{message_id}.json"
        for filepath in self.delivered_dir.glob(pattern):
            try:
                # 移动到归档目录
                archive_path = self.archive_dir / datetime.now().strftime('%Y-%m-%d') / filepath.name
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                filepath.rename(archive_path)
                logger.debug(f"消息已归档：{message_id}")
            except Exception as e:
                logger.error(f"归档消息失败 {filepath}: {e}")
    
    def fail(self, message_id: str, agent_name: str, error: str, retry: bool = True):
        """
        标记消息处理失败
        
        Args:
            message_id: 消息 ID
            agent_name: Agent 名称
            error: 错误信息
            retry: 是否重试
        """
        pattern = f"{agent_name}_*_{message_id}.json"
        
        for filepath in self.delivered_dir.glob(pattern):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    message = Message.from_json(f.read())
                
                message.status = "failed"
                message.error = error
                message.retry_count += 1
                
                if retry and message.retry_count < 3:
                    # 重新放入待处理队列
                    message.status = "pending"
                    new_filepath = self.pending_dir / filepath.name
                    with open(new_filepath, 'w', encoding='utf-8') as f:
                        f.write(message.to_json())
                    filepath.unlink()
                    logger.warning(f"消息重试：{message_id} (第{message.retry_count}次)")
                else:
                    # 移动到失败目录
                    filepath.rename(self.failed_dir / filepath.name)
                    logger.error(f"消息失败：{message_id} - {error}")
                    
            except Exception as e:
                logger.error(f"处理失败消息出错：{e}")
    
    def _notify_subscribers(self, message: Message):
        """通知订阅者有新消息"""
        callbacks = self.subscribers.get(message.to_agent, [])
        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"通知订阅者失败：{e}")
    
    def get_stats(self) -> Dict[str, int]:
        """获取队列统计信息"""
        return {
            "pending": len(list(self.pending_dir.glob("*.json"))),
            "delivered": len(list(self.delivered_dir.glob("*.json"))),
            "failed": len(list(self.failed_dir.glob("*.json"))),
            "subscribers": len(self.subscribers),
        }
    
    def cleanup(self, days: int = 7):
        """
        清理过期消息
        
        Args:
            days: 保留天数
        """
        cutoff = time.time() - (days * 24 * 3600)
        
        for directory in [self.archive_dir, self.failed_dir]:
            for filepath in directory.rglob("*.json"):
                try:
                    if filepath.stat().st_mtime < cutoff:
                        filepath.unlink()
                        logger.debug(f"清理过期消息：{filepath}")
                except Exception as e:
                    logger.error(f"清理消息失败 {filepath}: {e}")
    
    def start_worker(self, interval: float = 1.0):
        """
        启动后台工作线程 (定期清理)
        
        Args:
            interval: 检查间隔 (秒)
        """
        self.running = True
        
        def worker():
            while self.running:
                try:
                    self.cleanup()
                except Exception as e:
                    logger.error(f"清理任务失败：{e}")
                time.sleep(interval)
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
        logger.info("消息队列后台工作线程已启动")
    
    def stop_worker(self):
        """停止后台工作线程"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("消息队列后台工作线程已停止")
    
    # 便捷方法
    
    def send(self, from_agent: str, to_agent: str, msg_type: str, 
             content: Dict, priority: int = 5) -> str:
        """
        便捷发送消息
        
        Args:
            from_agent: 发送者
            to_agent: 接收者
            msg_type: 消息类型
            content: 消息内容
            priority: 优先级
        
        Returns:
            消息 ID
        """
        message = Message(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=msg_type,
            content=content,
            priority=priority
        )
        return self.publish(message)
    
    def broadcast(self, from_agent: str, msg_type: str, 
                  content: Dict, exclude: List[str] = None) -> List[str]:
        """
        广播消息给所有 Agent
        
        Args:
            from_agent: 发送者
            msg_type: 消息类型
            content: 消息内容
            exclude: 排除的 Agent 列表
        
        Returns:
            消息 ID 列表
        """
        exclude = exclude or []
        message_ids = []
        
        # 获取所有已知的 Agent
        known_agents = set(self.subscribers.keys())
        
        for agent in known_agents:
            if agent not in exclude:
                msg_id = self.send(from_agent, agent, msg_type, content, priority=3)
                message_ids.append(msg_id)
        
        return message_ids


# 全局单例
_global_queue: Optional[MessageQueue] = None

def get_queue() -> MessageQueue:
    """获取全局消息队列单例"""
    global _global_queue
    if _global_queue is None:
        _global_queue = MessageQueue()
    return _global_queue


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    queue = MessageQueue()
    
    # 测试发布/订阅
    def on_message(msg: Message):
        print(f"收到消息：{msg.from_agent} -> {msg.to_agent}: {msg.content}")
    
    queue.subscribe("test_bot", on_message)
    
    # 发送测试消息
    msg_id = queue.send("boss_bot", "test_bot", "test", {"hello": "world"})
    print(f"发送消息：{msg_id}")
    
    # 轮询消息
    messages = queue.poll("test_bot")
    print(f"轮询到 {len(messages)} 条消息")
    
    # 确认消息
    for msg in messages:
        queue.ack(msg.id, "test_bot")
    
    # 统计
    print(f"队列统计：{queue.get_stats()}")
