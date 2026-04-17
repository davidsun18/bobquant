"""
Persistence - 磁盘持久化模块

设计目标：
1. JSONL 格式存储（每行一个 JSON 对象）
2. 支持按时间/大小自动轮转
3. 原子写入（避免数据损坏）
4. 压缩支持（可选）
5. 退避重试机制

文件格式：
```jsonl
{"event_id": "...", "event_type": "order.submitted", "timestamp": 1234567890.123, ...}
{"event_id": "...", "event_type": "order.filled", "timestamp": 1234567891.456, ...}
```

架构参考：
- Claude Code: 日志持久化格式
- JSONL: 便于流式处理和增量读取
"""

import os
import json
import gzip
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterator
from datetime import datetime
from pathlib import Path
import time

from .sink import TelemetryEvent
from .retry import retry_with_backoff, RetryConfig


@dataclass
class PersistenceConfig:
    """
    持久化配置
    
    Attributes:
        base_dir: 基础存储目录
        file_prefix: 文件前缀
        max_file_size: 单个文件最大大小（MB，触发轮转）
        max_file_age: 文件最大保存时间（小时）
        compression: 是否启用压缩（.gz）
        retention_days: 保留天数（自动清理旧文件）
        buffer_size: 写入缓冲区大小（行数）
        flush_interval: 强制刷新间隔（秒）
        atomic_write: 是否使用原子写入（临时文件 + 重命名）
    """
    base_dir: str = "./telemetry_data"
    file_prefix: str = "events"
    max_file_size: int = 100  # 100 MB
    max_file_age: int = 24  # 24 小时
    compression: bool = False
    retention_days: int = 30
    buffer_size: int = 100
    flush_interval: float = 10.0
    atomic_write: bool = True
    retry_config: RetryConfig = field(default_factory=RetryConfig)


class JSONLPersister:
    """
    JSONL 格式持久化器
    
    特性：
    1. 自动文件轮转（基于大小和时间）
    2. 原子写入（避免写入中断导致文件损坏）
    3. 可选压缩（节省磁盘空间）
    4. 自动清理过期文件
    5. 退避重试（处理磁盘 IO 错误）
    
    使用示例：
    ```python
    config = PersistenceConfig(
        base_dir="/var/log/bobquant/telemetry",
        max_file_size=50,  # 50MB
        compression=True
    )
    persister = JSONLPersister(config)
    
    # 保存单个事件
    persister.save(event)
    
    # 批量保存
    persister.save_batch([event1, event2, event3])
    
    # 读取历史数据
    for event in persister.read_events(start_time, end_time):
        process(event)
    ```
    """
    
    def __init__(self, config: Optional[PersistenceConfig] = None):
        """
        初始化持久化器
        
        Args:
            config: 持久化配置
        """
        self.config = config or PersistenceConfig()
        
        # 创建基础目录
        self._base_path = Path(self.config.base_dir)
        self._base_path.mkdir(parents=True, exist_ok=True)
        
        # 当前文件路径
        self._current_file: Optional[Path] = None
        self._current_size = 0
        self._current_line_count = 0
        self._file_handle = None
        
        # 写入锁
        self._write_lock = threading.Lock()
        
        # 后台刷新线程
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        self._last_flush_time = time.time()
        
        # 统计信息
        self._stats = {
            "events_written": 0,
            "files_created": 0,
            "files_rotated": 0,
            "bytes_written": 0,
            "write_errors": 0,
            "files_cleaned": 0,
        }
        self._stats_lock = threading.Lock()
        
        # 初始化第一个文件
        self._rotate_file()
    
    def _get_file_path(self, timestamp: Optional[float] = None) -> Path:
        """
        生成文件路径
        
        格式：{prefix}_YYYYMMDD_HHMMSS.jsonl[.gz]
        """
        ts = datetime.fromtimestamp(timestamp or time.time())
        suffix = ".jsonl.gz" if self.config.compression else ".jsonl"
        filename = f"{self.config.file_prefix}_{ts.strftime('%Y%m%d_%H%M%S')}{suffix}"
        return self._base_path / filename
    
    def _rotate_file(self):
        """创建新文件（轮转）"""
        # 关闭旧文件
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        
        # 创建新文件
        self._current_file = self._get_file_path()
        self._current_size = 0
        self._current_line_count = 0
        
        # 使用原子写入：先写临时文件
        if self.config.atomic_write:
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=".tmp",
                dir=self._base_path
            )
            self._temp_path = Path(temp_path)
            os.close(temp_fd)
            self._write_path = self._temp_path
        else:
            self._write_path = self._current_file
        
        # 打开文件
        mode = "wt" if self.config.compression else "w"
        open_func = gzip.open if self.config.compression else open
        self._file_handle = open_func(self._write_path, mode, encoding="utf-8")
        
        with self._stats_lock:
            self._stats["files_created"] += 1
    
    def _check_rotation(self):
        """检查是否需要轮转文件"""
        # 检查文件大小
        max_bytes = self.config.max_file_size * 1024 * 1024
        if self._current_size >= max_bytes:
            self._complete_write()
            self._rotate_file()
            with self._stats_lock:
                self._stats["files_rotated"] += 1
            return
        
        # 检查文件时间
        if self._current_file and self._current_file.exists():
            file_age = time.time() - self._current_file.stat().st_mtime
            if file_age >= self.config.max_file_age * 3600:
                self._complete_write()
                self._rotate_file()
                with self._stats_lock:
                    self._stats["files_rotated"] += 1
    
    def _complete_write(self):
        """完成当前文件写入（原子提交）"""
        if not self._file_handle:
            return
        
        self._file_handle.flush()
        self._file_handle.close()
        self._file_handle = None
        
        # 原子重命名
        if self.config.atomic_write and hasattr(self, '_temp_path'):
            try:
                self._temp_path.rename(self._current_file)
            except Exception as e:
                import logging
                logging.error(f"Failed to rename temp file: {e}")
                # 清理临时文件
                try:
                    self._temp_path.unlink()
                except:
                    pass
    
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def save(self, event: TelemetryEvent):
        """
        保存单个事件
        
        Args:
            event: 遥测事件
        """
        self._save_event(event)
    
    def _save_event(self, event: TelemetryEvent):
        """内部保存逻辑（支持重试）"""
        with self._write_lock:
            # 检查轮转
            self._check_rotation()
            
            if not self._file_handle:
                self._rotate_file()
            
            # 序列化事件
            event_dict = event.to_dict()
            line = json.dumps(event_dict, ensure_ascii=False, default=str) + "\n"
            line_bytes = len(line.encode('utf-8'))
            
            # 写入
            self._file_handle.write(line)
            self._current_size += line_bytes
            self._current_line_count += 1
            
            # 更新统计
            with self._stats_lock:
                self._stats["events_written"] += 1
                self._stats["bytes_written"] += line_bytes
    
    def save_batch(self, events: List[TelemetryEvent]):
        """
        批量保存事件
        
        Args:
            events: 事件列表
        """
        with self._write_lock:
            for event in events:
                self._check_rotation()
                
                if not self._file_handle:
                    self._rotate_file()
                
                event_dict = event.to_dict()
                line = json.dumps(event_dict, ensure_ascii=False, default=str) + "\n"
                line_bytes = len(line.encode('utf-8'))
                
                self._file_handle.write(line)
                self._current_size += line_bytes
                self._current_line_count += 1
                
                # 缓冲区满则刷新
                if self._current_line_count >= self.config.buffer_size:
                    self._file_handle.flush()
            
            # 更新统计
            with self._stats_lock:
                self._stats["events_written"] += len(events)
    
    def flush(self):
        """强制刷新缓冲区"""
        with self._write_lock:
            if self._file_handle:
                self._file_handle.flush()
                self._complete_write()
                self._rotate_file()
    
    def start(self):
        """启动后台刷新线程"""
        if self._running:
            return
        
        self._running = True
        self._last_flush_time = time.time()
        
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def stop(self, flush: bool = True):
        """
        停止持久化器
        
        Args:
            flush: 是否刷新剩余数据
        """
        self._running = False
        
        if flush:
            self.flush()
        
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)
        
        # 关闭文件
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    def _flush_loop(self):
        """后台刷新循环"""
        while self._running:
            time.sleep(self.config.flush_interval)
            
            if not self._running:
                break
            
            # 定期刷新
            with self._write_lock:
                if self._file_handle:
                    self._file_handle.flush()
                
                # 定期清理旧文件
                self._cleanup_old_files()
    
    def _cleanup_old_files(self):
        """清理过期文件"""
        cutoff_time = time.time() - (self.config.retention_days * 24 * 3600)
        
        try:
            for file_path in self._base_path.glob(f"{self.config.file_prefix}_*"):
                if file_path.is_file():
                    file_mtime = file_path.stat().st_mtime
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        with self._stats_lock:
                            self._stats["files_cleaned"] += 1
        except Exception as e:
            import logging
            logging.error(f"Error cleaning up old files: {e}")
    
    def read_events(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        event_type: Optional[str] = None
    ) -> Iterator[TelemetryEvent]:
        """
        读取历史事件
        
        Args:
            start_time: 起始时间戳
            end_time: 结束时间戳
            event_type: 事件类型过滤
            
        Yields:
            TelemetryEvent: 事件对象
        """
        pattern = f"{self.config.file_prefix}_*"
        
        for file_path in sorted(self._base_path.glob(pattern)):
            if not file_path.is_file():
                continue
            
            # 打开文件（支持压缩）
            open_func = gzip.open if file_path.suffix == ".gz" else open
            mode = "rt" if file_path.suffix == ".gz" else "r"
            
            try:
                with open_func(file_path, mode, encoding="utf-8") as f:
                    for line in f:
                        try:
                            event_dict = json.loads(line.strip())
                            
                            # 时间过滤
                            event_time = event_dict.get("timestamp", 0)
                            if start_time and event_time < start_time:
                                continue
                            if end_time and event_time > end_time:
                                continue
                            
                            # 类型过滤
                            if event_type and event_dict.get("event_type") != event_type:
                                continue
                            
                            yield TelemetryEvent.from_dict(event_dict)
                            
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                import logging
                logging.error(f"Error reading file {file_path}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
        
        stats["current_file"] = str(self._current_file) if self._current_file else None
        stats["current_size_mb"] = self._current_size / (1024 * 1024)
        
        # 计算总文件大小
        total_size = sum(
            f.stat().st_size
            for f in self._base_path.glob(f"{self.config.file_prefix}_*")
            if f.is_file()
        )
        stats["total_storage_mb"] = total_size / (1024 * 1024)
        
        return stats
    
    def list_files(self) -> List[Dict[str, Any]]:
        """列出所有数据文件"""
        files = []
        for file_path in sorted(self._base_path.glob(f"{self.config.file_prefix}_*")):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "path": str(file_path),
                    "size_mb": stat.st_size / (1024 * 1024),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        return files
