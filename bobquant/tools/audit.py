"""
审计日志模块

提供工具执行的审计日志功能，包括：
- 操作记录
- 日志存储
- 日志查询
- 日志导出
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import asyncio


@dataclass
class AuditLogEntry:
    """审计日志条目"""
    # 基本信息
    timestamp: datetime
    action: str
    tool_name: str
    tool_use_id: str
    
    # 操作详情
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # 状态
    status: str = "success"  # success, failed, cancelled
    error_message: str = ""
    
    # 上下文信息
    user_id: str = ""
    session_id: str = ""
    strategy_id: str = ""
    
    # 性能指标
    duration_ms: float = 0.0
    memory_usage_mb: float = 0.0
    
    # 权限信息
    permission_result: str = "allow"  # allow, deny, ask
    permission_source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogEntry":
        """从字典创建"""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class AuditLogger:
    """审计日志记录器
    
    单例模式，管理所有工具的审计日志。
    
    功能：
    - 记录工具调用
    - 记录权限决策
    - 记录执行结果
    - 日志查询和导出
    """
    
    _instance: Optional["AuditLogger"] = None
    
    def __new__(cls) -> "AuditLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._logs: List[AuditLogEntry] = []
        self._log_file: Optional[Path] = None
        self._max_memory_logs = 10000  # 内存中最多保留的日志数
        self._callbacks: List[Callable[[AuditLogEntry], None]] = []
        self._logger = logging.getLogger("bobquant.audit")
        self._initialized = True
    
    @classmethod
    def get_instance(cls) -> "AuditLogger":
        """获取审计日志单例"""
        return cls()
    
    def configure(
        self,
        log_file: Optional[str] = None,
        max_memory_logs: int = 10000,
    ) -> None:
        """配置审计日志
        
        Args:
            log_file: 日志文件路径
            max_memory_logs: 内存中最多保留的日志数
        """
        if log_file:
            self._log_file = Path(log_file)
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._max_memory_logs = max_memory_logs
    
    def add_callback(self, callback: Callable[[AuditLogEntry], None]) -> None:
        """添加日志回调
        
        Args:
            callback: 回调函数，接收 AuditLogEntry 参数
        """
        self._callbacks.append(callback)
    
    def log(
        self,
        action: str,
        tool_name: str,
        tool_use_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: str = "",
        duration_ms: float = 0.0,
        permission_result: str = "allow",
        **kwargs,
    ) -> AuditLogEntry:
        """记录审计日志
        
        Args:
            action: 操作类型
            tool_name: 工具名称
            tool_use_id: 工具使用 ID
            input_data: 输入数据
            output_data: 输出数据
            status: 状态
            error_message: 错误消息
            duration_ms: 执行时长
            permission_result: 权限结果
            **kwargs: 其他字段
            
        Returns:
            AuditLogEntry: 日志条目
        """
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            action=action,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            input_data=input_data or {},
            output_data=output_data or {},
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
            permission_result=permission_result,
            **kwargs,
        )
        
        # 添加到内存
        self._logs.append(entry)
        
        # 限制内存中的日志数量
        if len(self._logs) > self._max_memory_logs:
            self._logs = self._logs[-self._max_memory_logs:]
        
        # 写入文件
        if self._log_file:
            self._write_to_file(entry)
        
        # 触发回调
        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception as e:
                self._logger.error(f"Audit callback error: {e}")
        
        # 记录到标准日志
        self._logger.info(
            f"[AUDIT] {action} - {tool_name} - {status} - {duration_ms:.2f}ms"
        )
        
        return entry
    
    def _write_to_file(self, entry: AuditLogEntry) -> None:
        """写入文件"""
        if not self._log_file:
            return
        
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            self._logger.error(f"Failed to write audit log: {e}")
    
    def query(
        self,
        tool_name: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """查询审计日志
        
        Args:
            tool_name: 工具名称过滤
            action: 操作类型过滤
            status: 状态过滤
            start_time: 开始时间
            end_time: 结束时间
            user_id: 用户 ID 过滤
            limit: 返回数量限制
            
        Returns:
            List[AuditLogEntry]: 日志列表
        """
        results = self._logs
        
        # 过滤
        if tool_name:
            results = [e for e in results if e.tool_name == tool_name]
        if action:
            results = [e for e in results if e.action == action]
        if status:
            results = [e for e in results if e.status == status]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        
        # 按时间倒序
        results.sort(key=lambda x: x.timestamp, reverse=True)
        
        # 限制数量
        return results[:limit]
    
    def get_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """获取统计信息
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict: 统计信息
        """
        logs = self._logs
        if start_time:
            logs = [e for e in logs if e.timestamp >= start_time]
        if end_time:
            logs = [e for e in logs if e.timestamp <= end_time]
        
        total = len(logs)
        success = sum(1 for e in logs if e.status == "success")
        failed = sum(1 for e in logs if e.status == "failed")
        
        # 按工具统计
        tool_counts: Dict[str, int] = {}
        for entry in logs:
            tool_counts[entry.tool_name] = tool_counts.get(entry.tool_name, 0) + 1
        
        # 平均执行时间
        avg_duration = sum(e.duration_ms for e in logs) / total if total > 0 else 0
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_ms": avg_duration,
            "tool_counts": tool_counts,
            "time_range": {
                "start": min(e.timestamp for e in logs).isoformat() if logs else None,
                "end": max(e.timestamp for e in logs).isoformat() if logs else None,
            },
        }
    
    def export(
        self,
        format: str = "json",
        output_file: Optional[str] = None,
        **query_kwargs,
    ) -> str:
        """导出审计日志
        
        Args:
            format: 导出格式 (json, csv)
            output_file: 输出文件路径
            **query_kwargs: 查询参数
            
        Returns:
            str: 导出内容或文件路径
        """
        logs = self.query(**query_kwargs)
        
        if format == "json":
            data = json.dumps([e.to_dict() for e in logs], indent=2, ensure_ascii=False)
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(data)
                return output_file
            return data
        
        elif format == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            if logs:
                fieldnames = list(logs[0].to_dict().keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for entry in logs:
                    writer.writerow(entry.to_dict())
            
            if output_file:
                with open(output_file, "w", encoding="utf-8", newline="") as f:
                    f.write(output.getvalue())
                return output_file
            return output.getvalue()
        
        raise ValueError(f"Unsupported format: {format}")
    
    def clear(self) -> None:
        """清空内存中的日志"""
        self._logs.clear()
        self._logger.info("Audit logs cleared")


# 便捷的审计装饰器
def audit_action(action_name: Optional[str] = None):
    """审计装饰器
    
    用法:
        @audit_action("place_order")
        async def place_order(...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = AuditLogger.get_instance()
            action = action_name or func.__name__
            
            start_time = datetime.now()
            status = "success"
            error_message = ""
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                logger.log(
                    action=action,
                    tool_name=func.__module__,
                    tool_use_id=kwargs.get("tool_use_id", "unknown"),
                    input_data=kwargs,
                    output_data=result.data if hasattr(result, "data") else result,
                    status=status,
                    duration_ms=duration,
                )
                
                return result
            except Exception as e:
                status = "failed"
                error_message = str(e)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                logger.log(
                    action=action,
                    tool_name=func.__module__,
                    tool_use_id=kwargs.get("tool_use_id", "unknown"),
                    input_data=kwargs,
                    status=status,
                    error_message=error_message,
                    duration_ms=duration,
                )
                
                raise
        
        return wrapper
    return decorator


# 全局审计日志实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
