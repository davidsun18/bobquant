"""
工具基类 - 借鉴 Claude Code Tool.ts

所有 BobQuant 工具的抽象基类，提供统一的接口：
- call: 执行工具
- validate_input: 输入验证
- check_permissions: 权限检查
- description: 工具描述
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar, Callable
from datetime import datetime
import logging

# 类型定义
T_Input = TypeVar("T_Input", bound=Dict[str, Any])
T_Output = TypeVar("T_Output")
T_Progress = TypeVar("T_Progress")


@dataclass
class ToolProgress:
    """工具执行进度信息"""
    tool_use_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolResult(Generic[T_Output]):
    """工具执行结果"""
    data: T_Output
    new_messages: List[Dict[str, Any]] = field(default_factory=list)
    context_modifier: Optional[Callable] = None
    mcp_meta: Optional[Dict[str, Any]] = None


@dataclass
class ToolContext:
    """工具执行上下文
    
    类似于 Claude Code 的 ToolUseContext，包含：
    - 配置选项
    - 取消控制
    - 状态管理
    - 消息历史
    """
    # 配置选项
    options: Dict[str, Any]
    
    # 取消控制
    abort_controller: Optional[Any] = None  # asyncio.CancelledError 或类似
    
    # 状态管理回调
    get_app_state: Optional[Callable] = None
    set_app_state: Optional[Callable] = None
    
    # 消息历史
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # 工具使用 ID
    tool_use_id: Optional[str] = None
    
    # 用户修改标记
    user_modified: bool = False
    
    # 日志记录器
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("bobquant.tools"))
    
    # 权限上下文
    permission_context: Optional["PermissionContext"] = None
    
    # 审计日志回调
    audit_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None


@dataclass
class PermissionContext:
    """权限上下文
    
    类似于 Claude Code 的 ToolPermissionContext
    """
    # 权限模式
    mode: str = "default"  # default, auto, strict
    
    # 允许规则
    always_allow_rules: Dict[str, Any] = field(default_factory=dict)
    
    # 拒绝规则
    always_deny_rules: Dict[str, Any] = field(default_factory=dict)
    
    # 需要询问的规则
    always_ask_rules: Dict[str, Any] = field(default_factory=dict)
    
    # 额外工作目录
    additional_working_directories: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """输入验证结果"""
    result: bool
    message: str = ""
    error_code: int = 0


@dataclass
class PermissionResult:
    """权限检查结果
    
    类似于 Claude Code 的 PermissionResult
    """
    # 行为：allow, deny, ask
    behavior: str
    message: str = ""
    updated_input: Optional[Dict[str, Any]] = None
    content_blocks: Optional[List[Dict[str, Any]]] = None
    decision_reason: Optional[Dict[str, Any]] = None
    user_modified: bool = False
    accept_feedback: Optional[str] = None


class Tool(ABC, Generic[T_Input, T_Output, T_Progress]):
    """工具基类
    
    所有工具必须继承此类并实现抽象方法。
    
    设计灵感来自 Claude Code Tool.ts，提供：
    - 统一的工具接口
    - 输入验证
    - 权限检查
    - 进度报告
    - 审计日志
    """
    
    # 类属性 - 工具元数据
    name: str = "base_tool"
    description_text: str = "基础工具"
    search_hint: str = ""  # 用于工具搜索的关键词
    
    # 工具配置
    is_mcp: bool = False
    should_defer: bool = False  # 是否延迟加载
    always_load: bool = False  # 是否总是加载
    max_result_size_chars: int = 100000  # 最大结果大小
    
    # 可选的 MCP 信息
    mcp_info: Optional[Dict[str, str]] = None
    
    # 输入 Schema (由子类定义)
    input_schema: Optional[Dict[str, Any]] = None
    
    # 输出 Schema (可选)
    output_schema: Optional[Dict[str, Any]] = None
    
    # 工具别名 (用于向后兼容) - 类属性
    # aliases 在子类中定义为类属性，不在实例中
    
    def __init__(self):
        self.logger = logging.getLogger(f"bobquant.tools.{self.name}")
    
    @abstractmethod
    async def call(
        self,
        args: T_Input,
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[T_Output]:
        """执行工具
        
        Args:
            args: 工具输入参数
            context: 工具执行上下文
            on_progress: 进度回调函数
            
        Returns:
            ToolResult: 工具执行结果
            
        Raises:
            ValidationError: 输入验证失败
            PermissionError: 权限检查失败
            ToolError: 工具执行错误
        """
        pass
    
    async def validate_input(
        self,
        input_data: T_Input,
        context: ToolContext,
    ) -> ValidationResult:
        """验证输入
        
        子类可以重写此方法提供自定义验证逻辑。
        
        Args:
            input_data: 输入数据
            context: 工具上下文
            
        Returns:
            ValidationResult: 验证结果
        """
        # 默认实现：如果有 schema 则验证
        if self.input_schema:
            try:
                from .schema import validate_schema
                validate_schema(input_data, self.input_schema)
                return ValidationResult(result=True)
            except Exception as e:
                return ValidationResult(
                    result=False,
                    message=str(e),
                    error_code=1
                )
        return ValidationResult(result=True)
    
    async def check_permissions(
        self,
        input_data: T_Input,
        context: ToolContext,
    ) -> PermissionResult:
        """检查权限
        
        子类可以重写此方法提供自定义权限逻辑。
        
        Args:
            input_data: 输入数据
            context: 工具上下文
            
        Returns:
            PermissionResult: 权限结果
        """
        # 默认实现：允许执行
        return PermissionResult(
            behavior="allow",
            updated_input=input_data
        )
    
    async def description(
        self,
        input_data: T_Input,
        options: Dict[str, Any],
    ) -> str:
        """获取工具描述
        
        Args:
            input_data: 输入数据
            options: 选项
            
        Returns:
            str: 工具描述
        """
        return self.description_text
    
    def is_enabled(self) -> bool:
        """检查工具是否启用"""
        return True
    
    def is_concurrency_safe(self, input_data: T_Input) -> bool:
        """检查工具是否并发安全"""
        return False
    
    def is_read_only(self, input_data: T_Input) -> bool:
        """检查工具是否只读"""
        return False
    
    def is_destructive(self, input_data: T_Input) -> bool:
        """检查工具是否具有破坏性"""
        return False
    
    def user_facing_name(self, input_data: Optional[T_Input] = None) -> str:
        """获取用户友好的工具名称"""
        return self.name
    
    def get_activity_description(
        self,
        input_data: Optional[T_Input] = None,
    ) -> Optional[str]:
        """获取活动描述（用于进度显示）"""
        return None
    
    def get_tool_use_summary(
        self,
        input_data: Optional[T_Input] = None,
    ) -> Optional[str]:
        """获取工具使用摘要"""
        return None
    
    def map_result_to_block(
        self,
        content: T_Output,
        tool_use_id: str,
    ) -> Dict[str, Any]:
        """将结果映射到标准块格式
        
        Args:
            content: 工具结果
            tool_use_id: 工具使用 ID
            
        Returns:
            Dict: 标准块格式
        """
        return {
            "type": "tool_result",
            "content": str(content) if not isinstance(content, (dict, list)) else content,
            "tool_use_id": tool_use_id,
            "is_error": False,
        }
    
    def _log_audit(
        self,
        context: ToolContext,
        action: str,
        details: Dict[str, Any],
    ) -> None:
        """记录审计日志
        
        Args:
            context: 工具上下文
            action: 操作类型
            details: 详细信息
        """
        if context.audit_callback:
            context.audit_callback(action, details)
        
        # 同时记录到日志
        self.logger.info(f"[AUDIT] {action}: {details}")
    
    def _emit_progress(
        self,
        progress: ToolProgress,
        on_progress: Optional[Callable[[ToolProgress], None]],
    ) -> None:
        """发出进度更新
        
        Args:
            progress: 进度信息
            on_progress: 进度回调
        """
        if on_progress:
            try:
                on_progress(progress)
            except Exception as e:
                self.logger.warning(f"Progress callback error: {e}")


# 工具错误类型
class ToolError(Exception):
    """工具执行错误基类"""
    def __init__(self, message: str, error_code: int = 0):
        super().__init__(message)
        self.error_code = error_code
        self.timestamp = datetime.now()


class ValidationError(ToolError):
    """输入验证错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code=1)
        self.details = details or {}


class PermissionError(ToolError):
    """权限错误"""
    def __init__(self, message: str, behavior: str = "deny"):
        super().__init__(message, error_code=2)
        self.behavior = behavior


class ExecutionError(ToolError):
    """执行错误"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, error_code=3)
        self.original_error = original_error
