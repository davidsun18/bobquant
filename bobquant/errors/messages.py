# -*- coding: utf-8 -*-
"""
BobQuant 用户友好的错误消息生成器 v1.0

功能：
1. 将技术错误转换为用户友好的消息
2. 提供清晰的解决建议
3. 支持多语言（中文/英文）
4. 支持不同详细程度（简洁/标准/详细）

设计灵感来自 Claude Code 的用户体验设计
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from .types import (
    BobQuantError,
    ErrorCategory,
    ErrorSeverity,
    # 具体错误类型
    APIError,
    NetworkError,
    TimeoutError,
    RateLimitError,
    AuthenticationError,
    DataError,
    DataNotFoundError,
    DataFormatError,
    DataValidationError,
    DataStaleError,
    TradingError,
    OrderError,
    OrderRejectedError,
    InsufficientFundsError,
    PositionError,
    MarketClosedError,
    StrategyError,
    SignalError,
    ConfigurationError,
    BacktestError,
    SystemError,
    FileSystemError,
    DatabaseError,
    MemoryError,
    ExternalServiceError,
    ThirdPartyAPIError,
)


class MessageDetailLevel(Enum):
    """消息详细程度"""
    BRIEF = "brief"      # 简洁（1 句话）
    STANDARD = "standard"  # 标准（2-3 句话）
    DETAILED = "detailed"  # 详细（包含技术细节）


@dataclass
class UserMessage:
    """用户消息"""
    title: str           # 标题
    message: str         # 主要消息
    suggestion: str      # 建议操作
    technical_details: Optional[str] = None  # 技术细节
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.SYSTEM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "message": self.message,
            "suggestion": self.suggestion,
            "technical_details": self.technical_details,
            "severity": self.severity.value,
            "category": self.category.value
        }
    
    def to_string(self, include_technical: bool = False) -> str:
        """转换为字符串"""
        result = f"{self.title}: {self.message}\n\n建议：{self.suggestion}"
        if include_technical and self.technical_details:
            result += f"\n\n技术细节：{self.technical_details}"
        return result


class ErrorMessageGenerator:
    """
    错误消息生成器
    
    将技术错误转换为用户友好的消息
    """
    
    def __init__(self, language: str = "zh"):
        self.language = language
        self._templates = self._build_templates()
    
    def _build_templates(self) -> Dict[str, Dict[str, str]]:
        """构建消息模板"""
        return {
            # ========== 网络错误 ==========
            "NetworkError": {
                "zh": {
                    "title": "网络连接问题",
                    "message": "无法连接到网络，请检查您的网络连接",
                    "suggestion": "检查网线/WiFi 连接，或稍后重试"
                },
                "en": {
                    "title": "Network Connection Issue",
                    "message": "Unable to connect to the network",
                    "suggestion": "Check your network connection and try again"
                }
            },
            "TimeoutError": {
                "zh": {
                    "title": "请求超时",
                    "message": "操作超时，服务器响应太慢",
                    "suggestion": "网络可能较慢，建议稍后重试"
                },
                "en": {
                    "title": "Request Timeout",
                    "message": "Operation timed out, server response is slow",
                    "suggestion": "Network may be slow, try again later"
                }
            },
            "RateLimitError": {
                "zh": {
                    "title": "请求过于频繁",
                    "message": "您的请求过于频繁，已被暂时限制",
                    "suggestion": "请稍等片刻后重试"
                },
                "en": {
                    "title": "Too Many Requests",
                    "message": "Your requests are too frequent",
                    "suggestion": "Please wait a moment and try again"
                }
            },
            "AuthenticationError": {
                "zh": {
                    "title": "认证失败",
                    "message": "无法验证您的身份",
                    "suggestion": "请检查 API 密钥或重新登录"
                },
                "en": {
                    "title": "Authentication Failed",
                    "message": "Unable to verify your identity",
                    "suggestion": "Check your API key or log in again"
                }
            },
            
            # ========== 数据错误 ==========
            "DataNotFoundError": {
                "zh": {
                    "title": "数据不存在",
                    "message": "找不到请求的数据",
                    "suggestion": "请检查股票代码是否正确"
                },
                "en": {
                    "title": "Data Not Found",
                    "message": "Requested data not found",
                    "suggestion": "Check if the stock code is correct"
                }
            },
            "DataFormatError": {
                "zh": {
                    "title": "数据格式错误",
                    "message": "数据格式不正确，无法解析",
                    "suggestion": "可能是数据源问题，请稍后重试"
                },
                "en": {
                    "title": "Data Format Error",
                    "message": "Data format is incorrect",
                    "suggestion": "May be a data source issue, try again later"
                }
            },
            "DataValidationError": {
                "zh": {
                    "title": "数据验证失败",
                    "message": "数据未通过验证",
                    "suggestion": "请检查输入的数据是否正确"
                },
                "en": {
                    "title": "Data Validation Failed",
                    "message": "Data failed validation",
                    "suggestion": "Check if the input data is correct"
                }
            },
            "DataStaleError": {
                "zh": {
                    "title": "数据已过期",
                    "message": "数据已过时，需要刷新",
                    "suggestion": "正在自动刷新数据"
                },
                "en": {
                    "title": "Data Expired",
                    "message": "Data is outdated, needs refresh",
                    "suggestion": "Automatically refreshing data"
                }
            },
            
            # ========== 交易错误 ==========
            "InsufficientFundsError": {
                "zh": {
                    "title": "资金不足",
                    "message": "可用资金不足以完成此交易",
                    "suggestion": "请减少交易数量或充值"
                },
                "en": {
                    "title": "Insufficient Funds",
                    "message": "Not enough funds for this transaction",
                    "suggestion": "Reduce trade amount or add funds"
                }
            },
            "OrderRejectedError": {
                "zh": {
                    "title": "订单被拒绝",
                    "message": "订单未能成功提交",
                    "suggestion": "请检查订单参数或联系券商"
                },
                "en": {
                    "title": "Order Rejected",
                    "message": "Order was not accepted",
                    "suggestion": "Check order parameters or contact broker"
                }
            },
            "MarketClosedError": {
                "zh": {
                    "title": "市场已关闭",
                    "message": "当前不在交易时间",
                    "suggestion": "请在交易时间内操作"
                },
                "en": {
                    "title": "Market Closed",
                    "message": "Currently not in trading hours",
                    "suggestion": "Please operate during trading hours"
                }
            },
            "PositionError": {
                "zh": {
                    "title": "持仓问题",
                    "message": "持仓相关操作出现问题",
                    "suggestion": "请检查持仓状态"
                },
                "en": {
                    "title": "Position Issue",
                    "message": "Problem with position operation",
                    "suggestion": "Check your position status"
                }
            },
            
            # ========== 策略错误 ==========
            "SignalError": {
                "zh": {
                    "title": "信号生成失败",
                    "message": "无法生成交易信号",
                    "suggestion": "请检查策略配置和数据"
                },
                "en": {
                    "title": "Signal Generation Failed",
                    "message": "Unable to generate trading signal",
                    "suggestion": "Check strategy configuration and data"
                }
            },
            "ConfigurationError": {
                "zh": {
                    "title": "配置错误",
                    "message": "系统配置存在问题",
                    "suggestion": "请检查配置文件或联系管理员"
                },
                "en": {
                    "title": "Configuration Error",
                    "message": "System configuration has issues",
                    "suggestion": "Check configuration files or contact admin"
                }
            },
            "BacktestError": {
                "zh": {
                    "title": "回测失败",
                    "message": "回测执行出现问题",
                    "suggestion": "请检查回测参数和历史数据"
                },
                "en": {
                    "title": "Backtest Failed",
                    "message": "Backtest execution has issues",
                    "suggestion": "Check backtest parameters and historical data"
                }
            },
            
            # ========== 系统错误 ==========
            "FileSystemError": {
                "zh": {
                    "title": "文件系统错误",
                    "message": "文件操作失败",
                    "suggestion": "请检查文件权限和磁盘空间"
                },
                "en": {
                    "title": "File System Error",
                    "message": "File operation failed",
                    "suggestion": "Check file permissions and disk space"
                }
            },
            "DatabaseError": {
                "zh": {
                    "title": "数据库错误",
                    "message": "数据库操作失败",
                    "suggestion": "请检查数据库连接状态"
                },
                "en": {
                    "title": "Database Error",
                    "message": "Database operation failed",
                    "suggestion": "Check database connection status"
                }
            },
            "MemoryError": {
                "zh": {
                    "title": "内存不足",
                    "message": "系统内存不足",
                    "suggestion": "请关闭其他程序后重试"
                },
                "en": {
                    "title": "Out of Memory",
                    "message": "System memory is low",
                    "suggestion": "Close other programs and try again"
                }
            },
            
            # ========== 外部服务错误 ==========
            "ThirdPartyAPIError": {
                "zh": {
                    "title": "外部服务异常",
                    "message": "第三方服务暂时不可用",
                    "suggestion": "请稍后重试或联系技术支持"
                },
                "en": {
                    "title": "External Service Issue",
                    "message": "Third-party service temporarily unavailable",
                    "suggestion": "Try again later or contact support"
                }
            },
        }
    
    def generate(
        self,
        error: BobQuantError,
        detail_level: MessageDetailLevel = MessageDetailLevel.STANDARD
    ) -> UserMessage:
        """
        生成用户友好的消息
        
        Args:
            error: BobQuant 错误
            detail_level: 详细程度
        
        Returns:
            UserMessage: 用户消息
        """
        error_type = type(error).__name__
        lang = self.language
        
        # 获取模板
        template = self._templates.get(error_type, {}).get(lang, {
            "title": "系统错误" if lang == "zh" else "System Error",
            "message": "发生未知错误" if lang == "zh" else "An unknown error occurred",
            "suggestion": "请稍后重试" if lang == "zh" else "Please try again later"
        })
        
        # 根据详细程度构建消息
        if detail_level == MessageDetailLevel.BRIEF:
            message = UserMessage(
                title=template["title"],
                message=template["message"],
                suggestion=template["suggestion"],
                severity=error.severity,
                category=error.category
            )
        
        elif detail_level == MessageDetailLevel.STANDARD:
            # 添加上下文信息
            context_msg = self._format_context(error.context, lang)
            main_message = template["message"]
            if context_msg:
                main_message = f"{template['message']}。{context_msg}"
            
            message = UserMessage(
                title=template["title"],
                message=main_message,
                suggestion=error.suggestion or template["suggestion"],
                severity=error.severity,
                category=error.category
            )
        
        else:  # DETAILED
            # 包含技术细节
            technical = self._format_technical_details(error, lang)
            context_msg = self._format_context(error.context, lang)
            
            message = UserMessage(
                title=template["title"],
                message=template["message"],
                suggestion=error.suggestion or template["suggestion"],
                technical_details=technical,
                severity=error.severity,
                category=error.category
            )
        
        return message
    
    def _format_context(
        self,
        context: Dict[str, Any],
        language: str
    ) -> str:
        """格式化上下文信息"""
        if not context:
            return ""
        
        parts = []
        
        # 常见上下文字段
        if "code" in context:
            parts.append(f"代码：{context['code']}")
        
        if "timeout_seconds" in context:
            parts.append(f"超时时间：{context['timeout_seconds']}秒")
        
        if "retry_after" in context:
            parts.append(f"建议等待：{context['retry_after']}秒")
        
        if "required_amount" in context and "available_amount" in context:
            parts.append(
                f"需要：{context['required_amount']:.2f}, "
                f"可用：{context['available_amount']:.2f}"
            )
        
        if "strategy_name" in context:
            parts.append(f"策略：{context['strategy_name']}")
        
        if language == "zh":
            return "；".join(parts) if parts else ""
        else:
            return "; ".join(parts) if parts else ""
    
    def _format_technical_details(
        self,
        error: BobQuantError,
        language: str
    ) -> str:
        """格式化技术细节"""
        details = []
        
        # 错误类型
        details.append(f"错误类型：{type(error).__name__}")
        
        # 错误分类
        details.append(f"分类：{error.category.value}")
        
        # 严重程度
        severity_map = {
            "zh": {"low": "低", "medium": "中", "high": "高", "critical": "严重"},
            "en": {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}
        }
        sev = severity_map.get(language, severity_map["en"]).get(
            error.severity.value, error.severity.value
        )
        details.append(f"严重程度：{sev}")
        
        # 时间戳
        details.append(f"时间：{error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 原始错误
        if error.original_error:
            details.append(f"原始错误：{type(error.original_error).__name__}: {error.original_error}")
        
        # 可恢复性
        recoverable = "是" if language == "zh" else "Yes"
        not_recoverable = "否" if language == "zh" else "No"
        details.append(f"可自动恢复：{recoverable if error.recoverable else not_recoverable}")
        
        return "\n".join(details)
    
    def generate_batch(
        self,
        errors: List[BobQuantError],
        detail_level: MessageDetailLevel = MessageDetailLevel.STANDARD
    ) -> List[UserMessage]:
        """批量生成消息"""
        return [self.generate(error, detail_level) for error in errors]
    
    def generate_summary(
        self,
        errors: List[BobQuantError],
        language: Optional[str] = None
    ) -> str:
        """
        生成错误摘要
        
        Args:
            errors: 错误列表
            language: 语言（可选，覆盖默认）
        
        Returns:
            str: 摘要文本
        """
        lang = language or self.language
        
        if not errors:
            return "无错误" if lang == "zh" else "No errors"
        
        # 统计
        by_category = {}
        by_severity = {}
        
        for error in errors:
            cat = error.category.value
            sev = error.severity.value
            
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        # 构建摘要
        lines = []
        
        if lang == "zh":
            lines.append(f"共发现 {len(errors)} 个错误")
            
            if by_severity.get("critical", 0) > 0:
                lines.append(f"⚠️ 严重错误：{by_severity['critical']} 个")
            if by_severity.get("high", 0) > 0:
                lines.append(f"🔴 高优先级错误：{by_severity['high']} 个")
            if by_severity.get("medium", 0) > 0:
                lines.append(f"🟡 中优先级错误：{by_severity['medium']} 个")
            
            lines.append("\n错误分类：")
            for cat, count in by_category.items():
                lines.append(f"  - {cat}: {count} 个")
        
        else:
            lines.append(f"Found {len(errors)} errors")
            
            if by_severity.get("critical", 0) > 0:
                lines.append(f"⚠️ Critical: {by_severity['critical']}")
            if by_severity.get("high", 0) > 0:
                lines.append(f"🔴 High: {by_severity['high']}")
            if by_severity.get("medium", 0) > 0:
                lines.append(f"🟡 Medium: {by_severity['medium']}")
            
            lines.append("\nBy Category:")
            for cat, count in by_category.items():
                lines.append(f"  - {cat}: {count}")
        
        return "\n".join(lines)


# =============================================================================
# 错误消息模板（用于日志和 API 响应）
# =============================================================================

ERROR_MESSAGE_TEMPLATES = {
    # 网络相关
    "network_retry": {
        "zh": "网络不稳定，已自动重试 {attempt} 次",
        "en": "Network unstable, automatically retried {attempt} times"
    },
    "network_fallback": {
        "zh": "主网络通道失败，已切换到备用通道",
        "en": "Primary network failed, switched to backup"
    },
    
    # 数据相关
    "data_refresh": {
        "zh": "数据已过期，正在刷新最新数据",
        "en": "Data expired, refreshing latest data"
    },
    "data_source_switch": {
        "zh": "数据源 {from_source} 失败，切换到 {to_source}",
        "en": "Data source {from_source} failed, switching to {to_source}"
    },
    
    # 交易相关
    "order_retry": {
        "zh": "订单提交失败，正在重试",
        "en": "Order submission failed, retrying"
    },
    "order_cancelled": {
        "zh": "订单因风控原因被取消：{reason}",
        "en": "Order cancelled due to risk control: {reason}"
    },
    
    # 系统相关
    "system_recovery": {
        "zh": "系统已自动恢复，服务继续",
        "en": "System auto-recovered, service continuing"
    },
    "manual_intervention": {
        "zh": "需要人工干预：{issue}",
        "en": "Manual intervention required: {issue}"
    },
}


def format_error_message(
    template_key: str,
    language: str = "zh",
    **kwargs
) -> str:
    """
    格式化错误消息模板
    
    Args:
        template_key: 模板键
        language: 语言
        **kwargs: 模板参数
    
    Returns:
        str: 格式化后的消息
    """
    template = ERROR_MESSAGE_TEMPLATES.get(template_key, {}).get(
        language,
        ERROR_MESSAGE_TEMPLATES.get(template_key, {}).get("en", template_key)
    )
    
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


# 全局消息生成器实例
_default_generator_zh = ErrorMessageGenerator("zh")
_default_generator_en = ErrorMessageGenerator("en")


def generate_error_message(
    error: BobQuantError,
    language: str = "zh",
    detail_level: MessageDetailLevel = MessageDetailLevel.STANDARD
) -> UserMessage:
    """
    使用默认生成器生成错误消息
    
    Args:
        error: BobQuant 错误
        language: 语言
        detail_level: 详细程度
    
    Returns:
        UserMessage: 用户消息
    """
    generator = _default_generator_zh if language == "zh" else _default_generator_en
    return generator.generate(error, detail_level)
