"""
BobQuant 工具系统

重构后的工具系统，借鉴 Claude Code 的架构设计：
- 统一的工具基类
- 集中式工具注册表
- Schema 验证
- 权限检查
- 审计日志
"""

from .base import Tool, ToolResult, ToolContext, ToolProgress, ToolError, ValidationError, PermissionError, ExecutionError
from .registry import ToolRegistry, get_registry, register_tool
from .schema import validate_schema, SchemaValidationError, SchemaBuilder, to_json_schema
from .audit import AuditLogger, get_audit_logger, AuditLogEntry, audit_action

__all__ = [
    # 基类
    "Tool",
    "ToolResult",
    "ToolContext",
    "ToolProgress",
    # 错误类型
    "ToolError",
    "ValidationError",
    "PermissionError",
    "ExecutionError",
    # 注册表
    "ToolRegistry",
    "get_registry",
    "register_tool",
    # Schema 验证
    "validate_schema",
    "SchemaValidationError",
    "SchemaBuilder",
    "to_json_schema",
    # 审计日志
    "AuditLogger",
    "get_audit_logger",
    "AuditLogEntry",
    "audit_action",
]
