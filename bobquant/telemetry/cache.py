"""
Multi-Level Cache - 多级缓存系统

设计目标：
1. 内存 → 磁盘两级缓存
2. LRU 淘汰策略（防止内存爆炸）
3. 异步写入磁盘
4. 支持批量读取

架构参考：
- Redis: 内存缓存最佳实践
- SQLite: 轻量级磁盘存储
- Python functools.lru_cache
"""

import os
import json
import time
import threading
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, OrderedDict
from collections import OrderedDict
from pathlib import Path
from datetime import datetime


@dataclass
class CacheConfig:
    """
    缓存配置
    
    Attributes:
        memory_max_size: 内存缓存最大条目数
        memory_ttl: 内存缓存 TTL（秒）
        disk_enabled: 是否启用磁盘缓存
        disk_path: 磁盘缓存路径
        disk_max_size_mb: 磁盘缓存最大大小（MB）
        disk_ttl: 磁盘缓存 TTL（秒）
        flush_interval: 异步刷新间隔（秒）
    """
    memory_max_size: int = 10000
    memory_ttl: float = 3600.0  # 1 小时
    disk_enabled: bool = True
    disk_path: str = "./telemetry_cache.db"
    disk_max_size_mb: int = 500
    disk_ttl: float = 86400.0  # 24 小时
    flush_interval: float = 5.0


class MemoryCache:
    """
    内存缓存（LRU 实现）
    
    特性：
    - O(1) 读写
    - 自动 LRU 淘汰
    - TTL 过期
    """
    
    def __init__(self, max_size: int = 10000, ttl: float = 3600.0):
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.Lock()
        
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            value, timestamp = self._cache[key]
            
            # 检查 TTL
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None
            
            # LRU: 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            return value
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self._lock:
            # 如果已存在，先删除（更新 LRU 顺序）
            if key in self._cache:
                del self._cache[key]
            
            # 检查容量
            while len(self._cache) >= self._max_size:
                # 淘汰最旧的
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1
            
            # 添加新值
            self._cache[key] = (value, time.time())
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())
    
    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._lock:
            stats = self._stats.copy()
            stats["size"] = len(self._cache)
            stats["max_size"] = self._max_size
        return stats
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            now = time.time()
            expired_keys = []
            
            for key, (value, timestamp) in self._cache.items():
                if now - timestamp > self._ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats["expirations"] += 1
            
            return len(expired_keys)


class DiskCache:
    """
    磁盘缓存（SQLite 实现）
    
    特性：
    - 持久化存储
    - 支持大量数据
    - TTL 过期
    - 定期清理
    """
    
    def __init__(self, db_path: str, ttl: float = 86400.0, max_size_mb: int = 500):
        self._db_path = Path(db_path)
        self._ttl = ttl
        self._max_size_mb = max_size_mb
        
        # 创建数据库目录
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化锁（必须在 _init_db 之前）
        self._lock = threading.Lock()
        
        # 初始化数据库
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        
        self._init_db()
        
        self._stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "deletes": 0,
            "cleanups": 0,
        }
    
    def _init_db(self):
        """初始化数据库表"""
        with self._lock:
            cursor = self._conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_accessed 
                ON cache(accessed_at)
            """)
            
            self._conn.commit()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT value, created_at FROM cache WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if row is None:
                self._stats["misses"] += 1
                return None
            
            value, created_at = row
            
            # 检查 TTL
            if time.time() - created_at > self._ttl:
                self.delete(key)
                self._stats["misses"] += 1
                return None
            
            # 更新访问时间
            cursor.execute(
                "UPDATE cache SET accessed_at = ? WHERE key = ?",
                (time.time(), key)
            )
            self._conn.commit()
            
            self._stats["hits"] += 1
            
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self._lock:
            cursor = self._conn.cursor()
            
            # 序列化值
            try:
                value_str = json.dumps(value, ensure_ascii=False, default=str)
            except Exception:
                value_str = str(value)
            
            now = time.time()
            
            # UPSERT
            cursor.execute("""
                INSERT OR REPLACE INTO cache (key, value, created_at, accessed_at)
                VALUES (?, ?, ?, ?)
            """, (key, value_str, now, now))
            
            self._conn.commit()
            self._stats["writes"] += 1
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
            deleted = cursor.rowcount > 0
            self._conn.commit()
            
            if deleted:
                self._stats["deletes"] += 1
            
            return deleted
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM cache")
            self._conn.commit()
    
    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache")
            return cursor.fetchone()[0]
    
    def size_mb(self) -> float:
        """获取缓存大小（MB）"""
        try:
            return self._db_path.stat().st_size / (1024 * 1024)
        except:
            return 0.0
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            cursor = self._conn.cursor()
            cutoff = time.time() - self._ttl
            
            cursor.execute(
                "DELETE FROM cache WHERE created_at < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
            self._conn.commit()
            
            if deleted > 0:
                self._stats["cleanups"] += deleted
            
            return deleted
    
    def cleanup_by_size(self) -> int:
        """按大小清理（淘汰最旧的）"""
        with self._lock:
            current_size_mb = self.size_mb()
            if current_size_mb <= self._max_size_mb:
                return 0
            
            cursor = self._conn.cursor()
            
            # 删除最旧的 10%
            cursor.execute("""
                DELETE FROM cache WHERE rowid IN (
                    SELECT rowid FROM cache 
                    ORDER BY accessed_at ASC 
                    LIMIT (SELECT COUNT(*) FROM cache) / 10
                )
            """)
            deleted = cursor.rowcount
            self._conn.commit()
            
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self._stats.copy()
            # 直接在锁内获取大小，避免重复获取锁导致死锁
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache")
            stats["size"] = cursor.fetchone()[0]
            stats["size_mb"] = self.size_mb()
            stats["max_size_mb"] = self._max_size_mb
        return stats
    
    def close(self):
        """关闭数据库连接"""
        with self._lock:
            self._conn.close()


class MultiLevelCache:
    """
    多级缓存（内存 + 磁盘）
    
    读取策略：
    1. 先查内存缓存
    2. 内存未命中则查磁盘缓存
    3. 磁盘命中则回填内存
    
    写入策略：
    1. 写入内存缓存
    2. 异步写入磁盘缓存
    
    使用示例：
    ```python
    config = CacheConfig(
        memory_max_size=5000,
        disk_path="./cache.db"
    )
    cache = MultiLevelCache(config)
    
    # 写入
    cache.set("key1", {"data": "value"})
    
    # 读取
    value = cache.get("key1")
    
    # 批量读取
    values = cache.get_batch(["key1", "key2", "key3"])
    ```
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        初始化多级缓存
        
        Args:
            config: 缓存配置
        """
        self.config = config or CacheConfig()
        
        # 初始化各级缓存
        self._memory = MemoryCache(
            max_size=self.config.memory_max_size,
            ttl=self.config.memory_ttl
        )
        
        self._disk: Optional[DiskCache] = None
        if self.config.disk_enabled:
            self._disk = DiskCache(
                db_path=self.config.disk_path,
                ttl=self.config.disk_ttl,
                max_size_mb=self.config.disk_max_size_mb
            )
        
        # 后台刷新线程
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        
        # 待刷新的队列
        self._pending_writes: OrderedDict[str, Any] = OrderedDict()
        self._pending_lock = threading.Lock()
        
        # 统计信息
        self._stats = {
            "memory_hits": 0,
            "disk_hits": 0,
            "misses": 0,
            "writes": 0,
        }
        self._stats_lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（多级查找）
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，未命中返回 None
        """
        # 1. 尝试内存缓存
        value = self._memory.get(key)
        if value is not None:
            with self._stats_lock:
                self._stats["memory_hits"] += 1
            return value
        
        # 2. 尝试磁盘缓存
        if self._disk:
            value = self._disk.get(key)
            if value is not None:
                # 回填内存
                self._memory.set(key, value)
                with self._stats_lock:
                    self._stats["disk_hits"] += 1
                return value
        
        # 3. 未命中
        with self._stats_lock:
            self._stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, sync: bool = False):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            sync: 是否同步写入磁盘
        """
        # 1. 写入内存
        self._memory.set(key, value)
        
        # 2. 加入待刷新队列
        with self._pending_lock:
            self._pending_writes[key] = value
        
        # 3. 同步写入磁盘（可选）
        if sync and self._disk:
            self._disk.set(key, value)
            with self._pending_lock:
                self._pending_writes.pop(key, None)
        
        with self._stats_lock:
            self._stats["writes"] += 1
    
    def delete(self, key: str):
        """删除缓存值"""
        self._memory.delete(key)
        if self._disk:
            self._disk.delete(key)
        
        with self._pending_lock:
            self._pending_writes.pop(key, None)
    
    def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取缓存值
        
        Args:
            keys: 缓存键列表
            
        Returns:
            字典 {key: value}
        """
        result = {}
        missing_keys = []
        
        # 1. 批量从内存读取
        for key in keys:
            value = self._memory.get(key)
            if value is not None:
                result[key] = value
            else:
                missing_keys.append(key)
        
        # 2. 从磁盘读取缺失的
        if missing_keys and self._disk:
            for key in missing_keys:
                value = self._disk.get(key)
                if value is not None:
                    result[key] = value
                    self._memory.set(key, value)  # 回填
        
        return result
    
    def set_batch(self, items: Dict[str, Any], sync: bool = False):
        """批量设置缓存值"""
        for key, value in items.items():
            self.set(key, value, sync=sync)
    
    def flush(self):
        """刷新待写入队列到磁盘"""
        with self._pending_lock:
            if not self._disk or not self._pending_writes:
                return
            
            for key, value in self._pending_writes.items():
                self._disk.set(key, value)
            
            self._pending_writes.clear()
    
    def start(self):
        """启动后台刷新线程"""
        if self._running:
            return
        
        self._running = True
        
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def stop(self, flush: bool = True):
        """
        停止缓存系统
        
        Args:
            flush: 是否刷新剩余数据
        """
        self._running = False
        
        if flush:
            self.flush()
        
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)
        
        if self._disk:
            self._disk.close()
    
    def _flush_loop(self):
        """后台刷新循环"""
        while self._running:
            time.sleep(self.config.flush_interval)
            
            if not self._running:
                break
            
            # 刷新待写入队列
            self.flush()
            
            # 定期清理过期数据
            self._memory.cleanup_expired()
            if self._disk:
                self._disk.cleanup_expired()
                self._disk.cleanup_by_size()
    
    def clear(self):
        """清空所有缓存"""
        self._memory.clear()
        if self._disk:
            self._disk.clear()
        
        with self._pending_lock:
            self._pending_writes.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
        
        stats["memory_cache"] = self._memory.get_stats()
        
        if self._disk:
            stats["disk_cache"] = self._disk.get_stats()
        
        with self._pending_lock:
            stats["pending_writes"] = len(self._pending_writes)
        
        # 计算命中率
        total_requests = stats["memory_hits"] + stats["disk_hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_rate"] = (stats["memory_hits"] + stats["disk_hits"]) / total_requests
        else:
            stats["hit_rate"] = 0.0
        
        return stats
