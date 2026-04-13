"""
Metrics Registry - 监控指标注册表

设计目标：
1. 定义 BobQuant 的核心监控指标
2. 提供指标收集接口
3. 支持指标导出和可视化

指标分类：
- 交易指标（订单、成交、持仓）
- 性能指标（延迟、吞吐量）
- 系统指标（CPU、内存、磁盘）
- 风控指标（风险敞口、回撤）
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from collections import defaultdict


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"  # 计数器（只增不减）
    GAUGE = "gauge"  # 仪表盘（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布）
    SUMMARY = "summary"  # 摘要（分位数）


@dataclass
class MetricDefinition:
    """
    指标定义
    
    Attributes:
        name: 指标名称
        description: 指标描述
        metric_type: 指标类型
        unit: 单位
        labels: 标签列表
        enabled: 是否启用
    """
    name: str
    description: str
    metric_type: MetricType
    unit: str = ""
    labels: List[str] = field(default_factory=list)
    enabled: bool = True


# BobQuant 预定义指标清单
BOBQUANT_METRICS = [
    # ==================== 交易指标 ====================
    MetricDefinition(
        name="bobquant.orders.total",
        description="订单总数",
        metric_type=MetricType.COUNTER,
        unit="orders",
        labels=["type", "symbol", "status"],
    ),
    MetricDefinition(
        name="bobquant.orders.filled",
        description="成交订单数",
        metric_type=MetricType.COUNTER,
        unit="orders",
        labels=["type", "symbol"],
    ),
    MetricDefinition(
        name="bobquant.orders.rejected",
        description="被拒绝订单数",
        metric_type=MetricType.COUNTER,
        unit="orders",
        labels=["reason", "symbol"],
    ),
    MetricDefinition(
        name="bobquant.volume.traded",
        description="成交总股数",
        metric_type=MetricType.COUNTER,
        unit="shares",
        labels=["symbol", "direction"],
    ),
    MetricDefinition(
        name="bobquant.amount.traded",
        description="成交总金额",
        metric_type=MetricType.COUNTER,
        unit="CNY",
        labels=["symbol", "direction"],
    ),
    MetricDefinition(
        name="bobquant.position.current",
        description="当前持仓数量",
        metric_type=MetricType.GAUGE,
        unit="shares",
        labels=["symbol", "direction"],
    ),
    MetricDefinition(
        name="bobquant.position.value",
        description="当前持仓市值",
        metric_type=MetricType.GAUGE,
        unit="CNY",
        labels=["symbol"],
    ),
    MetricDefinition(
        name="bobquant.pnl.realized",
        description="已实现盈亏",
        metric_type=MetricType.COUNTER,
        unit="CNY",
        labels=["symbol", "strategy"],
    ),
    MetricDefinition(
        name="bobquant.pnl.unrealized",
        description="未实现盈亏",
        metric_type=MetricType.GAUGE,
        unit="CNY",
        labels=["symbol", "strategy"],
    ),
    
    # ==================== 性能指标 ====================
    MetricDefinition(
        name="bobquant.latency.order_submit",
        description="订单提交延迟",
        metric_type=MetricType.HISTOGRAM,
        unit="ms",
        labels=["broker", "symbol"],
    ),
    MetricDefinition(
        name="bobquant.latency.market_data",
        description="行情数据延迟",
        metric_type=MetricType.HISTOGRAM,
        unit="ms",
        labels=["source", "symbol"],
    ),
    MetricDefinition(
        name="bobquant.latency.signal_generation",
        description="信号生成延迟",
        metric_type=MetricType.HISTOGRAM,
        unit="ms",
        labels=["strategy"],
    ),
    MetricDefinition(
        name="bobquant.throughput.ticks",
        description="Tick 处理吞吐量",
        metric_type=MetricType.GAUGE,
        unit="ticks/s",
        labels=["source"],
    ),
    MetricDefinition(
        name="bobquant.throughput.orders",
        description="订单处理吞吐量",
        metric_type=MetricType.GAUGE,
        unit="orders/s",
        labels=["type"],
    ),
    
    # ==================== 系统指标 ====================
    MetricDefinition(
        name="bobquant.system.cpu_usage",
        description="CPU 使用率",
        metric_type=MetricType.GAUGE,
        unit="%",
        labels=["core"],
    ),
    MetricDefinition(
        name="bobquant.system.memory_usage",
        description="内存使用量",
        metric_type=MetricType.GAUGE,
        unit="MB",
        labels=["type"],
    ),
    MetricDefinition(
        name="bobquant.system.disk_usage",
        description="磁盘使用量",
        metric_type=MetricType.GAUGE,
        unit="MB",
        labels=["path"],
    ),
    MetricDefinition(
        name="bobquant.system.gc_pause",
        description="GC 暂停时间",
        metric_type=MetricType.HISTOGRAM,
        unit="ms",
        labels=["generation"],
    ),
    MetricDefinition(
        name="bobquant.system.thread_count",
        description="线程数量",
        metric_type=MetricType.GAUGE,
        unit="threads",
    ),
    
    # ==================== 风控指标 ====================
    MetricDefinition(
        name="bobquant.risk.exposure",
        description="风险敞口",
        metric_type=MetricType.GAUGE,
        unit="CNY",
        labels=["asset_class"],
    ),
    MetricDefinition(
        name="bobquant.risk.drawdown",
        description="当前回撤",
        metric_type=MetricType.GAUGE,
        unit="%",
        labels=["timeframe"],
    ),
    MetricDefinition(
        name="bobquant.risk.var",
        description="风险价值 (VaR)",
        metric_type=MetricType.GAUGE,
        unit="CNY",
        labels=["confidence", "timeframe"],
    ),
    MetricDefinition(
        name="bobquant.risk.position_ratio",
        description="持仓比例",
        metric_type=MetricType.GAUGE,
        unit="%",
        labels=["symbol"],
    ),
    MetricDefinition(
        name="bobquant.risk.concentration",
        description="持仓集中度",
        metric_type=MetricType.GAUGE,
        unit="%",
        labels=["top_n"],
    ),
    
    # ==================== 策略指标 ====================
    MetricDefinition(
        name="bobquant.strategy.signals",
        description="策略信号数量",
        metric_type=MetricType.COUNTER,
        unit="signals",
        labels=["strategy", "type"],
    ),
    MetricDefinition(
        name="bobquant.strategy.win_rate",
        description="策略胜率",
        metric_type=MetricType.GAUGE,
        unit="%",
        labels=["strategy", "timeframe"],
    ),
    MetricDefinition(
        name="bobquant.strategy.sharpe_ratio",
        description="夏普比率",
        metric_type=MetricType.GAUGE,
        unit="ratio",
        labels=["strategy", "timeframe"],
    ),
    MetricDefinition(
        name="bobquant.strategy.max_drawdown",
        description="最大回撤",
        metric_type=MetricType.GAUGE,
        unit="%",
        labels=["strategy"],
    ),
    
    # ==================== 遥测指标 ====================
    MetricDefinition(
        name="bobquant.telemetry.events_emitted",
        description=" emitted 事件数",
        metric_type=MetricType.COUNTER,
        unit="events",
        labels=["event_type"],
    ),
    MetricDefinition(
        name="bobquant.telemetry.events_dropped",
        description="丢弃事件数",
        metric_type=MetricType.COUNTER,
        unit="events",
        labels=["reason"],
    ),
    MetricDefinition(
        name="bobquant.telemetry.batch_size",
        description="批处理大小",
        metric_type=MetricType.HISTOGRAM,
        unit="events",
        labels=["trigger"],
    ),
    MetricDefinition(
        name="bobquant.telemetry.persistence_latency",
        description="持久化延迟",
        metric_type=MetricType.HISTOGRAM,
        unit="ms",
    ),
]


class MetricCollector:
    """
    指标收集器
    
    用于收集和存储指标数据
    """
    
    def __init__(self, definition: MetricDefinition):
        self.definition = definition
        self._lock = threading.Lock()
        
        if definition.metric_type == MetricType.COUNTER:
            self._value = 0
        elif definition.metric_type == MetricType.GAUGE:
            self._value = 0.0
        elif definition.metric_type == MetricType.HISTOGRAM:
            self._values: List[float] = []
        elif definition.metric_type == MetricType.SUMMARY:
            self._values: List[float] = []
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        with self._lock:
            if self.definition.metric_type == MetricType.COUNTER:
                self._value += value
            elif self.definition.metric_type == MetricType.GAUGE:
                self._value += value
    
    def dec(self, value: float = 1.0):
        """减少计数器（仅 Gauge）"""
        with self._lock:
            if self.definition.metric_type == MetricType.GAUGE:
                self._value -= value
    
    def set(self, value: float):
        """设置值（仅 Gauge）"""
        with self._lock:
            if self.definition.metric_type == MetricType.GAUGE:
                self._value = value
    
    def observe(self, value: float):
        """观察值（Histogram/Summary）"""
        with self._lock:
            if self.definition.metric_type in (MetricType.HISTOGRAM, MetricType.SUMMARY):
                self._values.append(value)
    
    def get(self) -> Any:
        """获取当前值"""
        with self._lock:
            if self.definition.metric_type in (MetricType.HISTOGRAM, MetricType.SUMMARY):
                if not self._values:
                    return {"count": 0, "sum": 0, "avg": 0}
                return {
                    "count": len(self._values),
                    "sum": sum(self._values),
                    "avg": sum(self._values) / len(self._values),
                    "min": min(self._values),
                    "max": max(self._values),
                }
            return self._value
    
    def reset(self):
        """重置指标"""
        with self._lock:
            if self.definition.metric_type == MetricType.COUNTER:
                pass  # Counter 不重置
            elif self.definition.metric_type == MetricType.GAUGE:
                self._value = 0.0
            elif self.definition.metric_type in (MetricType.HISTOGRAM, MetricType.SUMMARY):
                self._values.clear()


class MetricsRegistry:
    """
    指标注册表
    
    管理所有监控指标的注册、收集和导出
    
    使用示例：
    ```python
    registry = MetricsRegistry()
    
    # 注册指标
    registry.register("bobquant.orders.total", labels=["type", "symbol"])
    
    # 收集指标
    registry.inc("bobquant.orders.total", labels={"type": "buy", "symbol": "000001.SZ"})
    
    # 获取指标
    value = registry.get("bobquant.orders.total")
    
    # 导出指标
    metrics = registry.export()
    ```
    """
    
    def __init__(self):
        self._metrics: Dict[str, Dict[str, MetricCollector]] = defaultdict(dict)
        self._definitions: Dict[str, MetricDefinition] = {}
        self._lock = threading.Lock()
        
        # 注册预定义指标
        for metric_def in BOBQUANT_METRICS:
            self.register_definition(metric_def)
    
    def register_definition(self, definition: MetricDefinition):
        """注册指标定义"""
        with self._lock:
            self._definitions[definition.name] = definition
    
    def _get_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """生成指标键（包含标签）"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def inc(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = self._get_key(name, labels)
        
        with self._lock:
            if key not in self._metrics[name]:
                definition = self._definitions.get(name)
                if definition:
                    self._metrics[name][key] = MetricCollector(definition)
            
            if key in self._metrics[name]:
                self._metrics[name][key].inc(value)
    
    def dec(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """减少计数器"""
        key = self._get_key(name, labels)
        
        with self._lock:
            if key not in self._metrics[name]:
                definition = self._definitions.get(name)
                if definition:
                    self._metrics[name][key] = MetricCollector(definition)
            
            if key in self._metrics[name]:
                self._metrics[name][key].dec(value)
    
    def set(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置指标值"""
        key = self._get_key(name, labels)
        
        with self._lock:
            if key not in self._metrics[name]:
                definition = self._definitions.get(name)
                if definition:
                    self._metrics[name][key] = MetricCollector(definition)
            
            if key in self._metrics[name]:
                self._metrics[name][key].set(value)
    
    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """观察值（Histogram）"""
        key = self._get_key(name, labels)
        
        with self._lock:
            if key not in self._metrics[name]:
                definition = self._definitions.get(name)
                if definition:
                    self._metrics[name][key] = MetricCollector(definition)
            
            if key in self._metrics[name]:
                self._metrics[name][key].observe(value)
    
    def get(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[Any]:
        """获取指标值"""
        key = self._get_key(name, labels)
        
        with self._lock:
            if key in self._metrics[name]:
                return self._metrics[name][key].get()
        return None
    
    def get_all(self, name: str) -> Dict[str, Any]:
        """获取指标的所有标签变体"""
        with self._lock:
            return {
                key: collector.get()
                for key, collector in self._metrics[name].items()
            }
    
    def export(self) -> Dict[str, Any]:
        """导出所有指标"""
        with self._lock:
            result = {}
            for name, collectors in self._metrics.items():
                definition = self._definitions.get(name)
                result[name] = {
                    "definition": {
                        "description": definition.description if definition else "",
                        "type": definition.metric_type.value if definition else "",
                        "unit": definition.unit if definition else "",
                    },
                    "values": {
                        key: collector.get()
                        for key, collector in collectors.items()
                    }
                }
            return result
    
    def export_prometheus(self) -> str:
        """导出为 Prometheus 格式"""
        lines = []
        
        with self._lock:
            for name, collectors in self._metrics.items():
                definition = self._definitions.get(name)
                
                if not definition:
                    continue
                
                # 添加 HELP
                lines.append(f"# HELP {name} {definition.description}")
                
                # 添加 TYPE
                lines.append(f"# TYPE {name} {definition.metric_type.value}")
                
                # 添加指标值
                for key, collector in collectors.items():
                    value = collector.get()
                    
                    if definition.metric_type in (MetricType.HISTOGRAM, MetricType.SUMMARY):
                        # 直方图/摘要需要特殊处理
                        if isinstance(value, dict):
                            lines.append(f'{name}_count{{}} {value["count"]}')
                            lines.append(f'{name}_sum{{}} {value["sum"]}')
                    else:
                        # 解析标签
                        labels_str = key.replace(f"{name}{{", "").replace("}", "")
                        if labels_str:
                            lines.append(f'{name}{{{labels_str}}} {value}')
                        else:
                            lines.append(f'{name} {value}')
        
        return "\n".join(lines)
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            for collectors in self._metrics.values():
                for collector in collectors.values():
                    collector.reset()


# 全局指标注册表
_global_registry: Optional[MetricsRegistry] = None

def get_metrics_registry() -> MetricsRegistry:
    """获取全局指标注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = MetricsRegistry()
    return _global_registry
