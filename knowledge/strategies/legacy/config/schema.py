# -*- coding: utf-8 -*-
"""
BobQuant 配置 Schema 定义

借鉴 Claude Code 的 Zod schema 设计模式，使用 Pydantic v2 实现：
- 5 层配置继承：Global Defaults → Per-Strategy → Per-Channel → Per-Account → Per-Group
- SecretRef 支持：环境变量/文件/命令
- JSON5 支持：注释、尾随逗号、环境变量替换
- 配置验证和错误处理
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from datetime import time
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError as PydanticValidationError, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
import json5  # JSON5 解析库


# ==================== SecretRef 实现 ====================

class SecretType(str, Enum):
    """Secret 引用类型"""
    ENV = "env"      # 环境变量
    FILE = "file"    # 文件
    CMD = "cmd"      # 命令


class SecretRef(BaseModel):
    """
    Secret 引用 - 支持三种类型：
    - env: 从环境变量读取
    - file: 从文件读取
    - cmd: 执行命令获取
    
    示例：
    - SecretRef(type="env", ref="API_KEY")
    - SecretRef(type="file", ref="/path/to/secret.txt")
    - SecretRef(type="cmd", ref="vault read secret/api_key")
    """
    type: SecretType = Field(..., description="Secret 类型")
    ref: str = Field(..., description="引用路径：环境变量名/文件路径/命令")
    _resolved_value: Optional[str] = None
    
    def resolve(self) -> str:
        """解析 Secret 引用，返回实际值"""
        if self._resolved_value is not None:
            return self._resolved_value
            
        if self.type == SecretType.ENV:
            value = os.environ.get(self.ref)
            if value is None:
                raise ValueError(f"环境变量 '{self.ref}' 未设置")
            self._resolved_value = value
            
        elif self.type == SecretType.FILE:
            path = Path(self.ref).expanduser()
            if not path.exists():
                raise ValueError(f"Secret 文件不存在：{self.ref}")
            self._resolved_value = path.read_text().strip()
            
        elif self.type == SecretType.CMD:
            try:
                result = subprocess.run(
                    self.ref,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )
                self._resolved_value = result.stdout.strip()
            except subprocess.CalledProcessError as e:
                raise ValueError(f"命令执行失败：{self.ref}, 错误：{e.stderr}")
            except subprocess.TimeoutExpired:
                raise ValueError(f"命令执行超时：{self.ref}")
        
        return self._resolved_value
    
    @classmethod
    def from_string(cls, value: str) -> Union["SecretRef", str]:
        """
        从字符串解析 SecretRef
        格式：${type:ref}
        示例：${env:API_KEY}, ${file:~/.secret}, ${cmd:vault read key}
        """
        pattern = r'\$\{(env|file|cmd):([^}]+)\}'
        match = re.match(pattern, value)
        if match:
            secret_type, ref = match.groups()
            return cls(type=SecretType(secret_type), ref=ref)
        return value
    
    def __str__(self) -> str:
        return f"${{{self.type.value}:{self.ref}}}"


# ==================== 配置 Schema 定义 ====================

class SystemConfig(BaseModel):
    """系统配置"""
    name: str = Field(default="BobQuant", description="系统名称")
    version: str = Field(default="3.0", description="版本号")
    mode: Literal["simulation", "real", "backtest"] = Field(default="simulation", description="运行模式")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="日志级别")
    debug: bool = Field(default=False, description="调试模式")
    check_interval: int = Field(default=60, description="检查间隔（秒）")


class AccountConfig(BaseModel):
    """账户配置"""
    initial_capital: float = Field(default=1000000.0, description="初始资金")
    commission_rate: float = Field(default=0.0005, description="佣金费率")
    stamp_duty_rate: float = Field(default=0.001, description="印花税率")
    max_position_pct: float = Field(default=0.10, description="单票最大仓位比例")
    max_stocks: int = Field(default=10, description="最大持仓数量")
    api_key: Optional[Union[str, SecretRef]] = Field(default=None, description="券商 API 密钥")
    api_secret: Optional[Union[str, SecretRef]] = Field(default=None, description="券商 API 密钥")


class StrategyConfig(BaseModel):
    """策略配置"""
    # 双 MACD 策略
    dual_macd: Optional[Dict[str, Any]] = Field(default=None, description="双 MACD 策略配置")
    # 布林带策略
    bollinger: Optional[Dict[str, Any]] = Field(default=None, description="布林带策略配置")
    # 信号过滤
    signal: Optional[Dict[str, Any]] = Field(default=None, description="信号过滤配置")
    # 金字塔加仓
    pyramid: Optional[Dict[str, Any]] = Field(default=None, description="金字塔加仓配置")
    # 其他策略参数
    model_config = ConfigDict(extra='allow')  # 允许额外字段


class PositionConfig(BaseModel):
    """仓位管理配置"""
    max_position_pct: float = Field(default=0.10, description="单票最大仓位比例")
    max_stocks: int = Field(default=10, description="最大同时持仓数量")
    min_buy_shares: int = Field(default=100, description="最小买入股数")
    pyramid: Optional[Dict[str, Any]] = Field(default=None, description="金字塔加仓配置")


class StopLossConfig(BaseModel):
    """止损配置"""
    enabled: bool = Field(default=True, description="是否启用止损")
    pct: float = Field(default=-0.08, description="止损比例")


class TrailingStopConfig(BaseModel):
    """跟踪止损配置"""
    enabled: bool = Field(default=True, description="是否启用跟踪止损")
    activation_pct: float = Field(default=0.05, description="激活阈值")
    drawdown_pct: float = Field(default=0.02, description="回撤阈值")


class TakeProfitLevel(BaseModel):
    """止盈层级"""
    threshold: float = Field(..., description="盈利阈值")
    sell_ratio: float = Field(..., description="卖出比例")


class RiskControlConfig(BaseModel):
    """风控配置"""
    stop_loss: Optional[StopLossConfig] = Field(default=None, description="硬止损配置")
    trailing_stop: Optional[TrailingStopConfig] = Field(default=None, description="跟踪止损配置")
    take_profit: Optional[Dict[str, Any]] = Field(default=None, description="分批止盈配置")


class MarketRiskConfig(BaseModel):
    """大盘风控配置"""
    enabled: bool = Field(default=True, description="是否启用大盘风控")
    index_code: str = Field(default="sh.000001", description="大盘指数代码")
    ma20_line: int = Field(default=20, description="均线周期")
    max_position_bear: float = Field(default=0.50, description="熊市最大仓位")
    crash_threshold: float = Field(default=-0.03, description="暴跌阈值")


class DataConfig(BaseModel):
    """数据源配置"""
    primary: str = Field(default="tencent", description="主数据源")
    fallback: Optional[str] = Field(default=None, description="备用数据源")
    history_provider: str = Field(default="baostock", description="历史数据提供商")
    history_days: int = Field(default=60, description="历史数据天数")
    api_key: Optional[Union[str, SecretRef]] = Field(default=None, description="数据 API 密钥")


class TradingHoursConfig(BaseModel):
    """交易时段配置"""
    morning_start: str = Field(default="09:25", description="早盘开始时间")
    morning_end: str = Field(default="11:35", description="早盘结束时间")
    afternoon_start: str = Field(default="12:55", description="午盘开始时间")
    afternoon_end: str = Field(default="15:05", description="午盘结束时间")
    pre_market: Optional[str] = Field(default=None, description="盘前准备时间")
    post_market: Optional[str] = Field(default=None, description="盘后总结时间")


class TwapConfig(BaseModel):
    """TWAP 算法执行配置"""
    enabled: bool = Field(default=False, description="是否启用 TWAP")
    threshold: int = Field(default=10000, description="触发 TWAP 的股数阈值")
    slices: int = Field(default=5, description="拆分份数")
    duration_minutes: int = Field(default=10, description="执行时长")


class RlTrainingConfig(BaseModel):
    """RL 训练配置"""
    total_timesteps: int = Field(default=10000, description="训练总步数")
    eval_freq: int = Field(default=1000, description="评估频率")
    n_eval_episodes: int = Field(default=5, description="评估回合数")
    window_size: int = Field(default=60, description="状态窗口大小")


class RlTradingConfig(BaseModel):
    """RL 交易配置"""
    max_stocks: int = Field(default=10, description="最大持仓数量")
    max_position_pct: float = Field(default=0.10, description="单票最大仓位")
    initial_capital: float = Field(default=1000000.0, description="初始资金")


class RlPredictionConfig(BaseModel):
    """RL 预测配置"""
    use_trained_model: bool = Field(default=True, description="是否使用已训练模型")
    deterministic: bool = Field(default=True, description="是否确定性预测")


class RlConfig(BaseModel):
    """强化学习配置"""
    enabled: bool = Field(default=False, description="是否启用 RL")
    algorithm: Literal["ppo", "a2c", "dqn"] = Field(default="ppo", description="算法选择")
    model_path: str = Field(default="rl/models", description="模型保存路径")
    training: Optional[RlTrainingConfig] = Field(default=None, description="训练配置")
    trading: Optional[RlTradingConfig] = Field(default=None, description="交易配置")
    prediction: Optional[RlPredictionConfig] = Field(default=None, description="预测配置")


class NotifyEventsConfig(BaseModel):
    """通知事件配置"""
    trade_executed: bool = Field(default=True, description="交易执行通知")
    stop_loss: bool = Field(default=True, description="止损触发通知")
    take_profit: bool = Field(default=True, description="止盈触发通知")
    daily_report: bool = Field(default=True, description="日报通知")
    risk_warning: bool = Field(default=True, description="风险预警通知")


class NotifyFeishuConfig(BaseModel):
    """飞书通知配置"""
    enabled: bool = Field(default=True, description="是否启用飞书通知")
    user_id: Optional[Union[str, SecretRef]] = Field(default=None, description="用户 ID")
    webhook_url: Optional[Union[str, SecretRef]] = Field(default=None, description="Webhook URL")


class NotifyConfig(BaseModel):
    """通知配置"""
    feishu: Optional[NotifyFeishuConfig] = Field(default=None, description="飞书通知配置")
    events: Optional[NotifyEventsConfig] = Field(default=None, description="通知事件配置")


class LogConfig(BaseModel):
    """日志配置"""
    dir: str = Field(default="logs", description="日志目录")
    max_size: int = Field(default=10485760, description="单个日志文件最大大小 (字节)")
    backup_count: int = Field(default=10, description="备份文件数量")


class RebalanceConfig(BaseModel):
    """自动调仓配置"""
    enabled: bool = Field(default=False, description="是否启用自动调仓")
    mode: Literal["equal_weight", "target_weight"] = Field(default="equal_weight", description="调仓模式")
    frequency: Literal["daily", "weekly", "monthly"] = Field(default="weekly", description="调仓频率")
    rebalance_day: int = Field(default=0, description="调仓日")
    threshold_pct: float = Field(default=0.05, description="偏离阈值")
    min_trade_value: float = Field(default=1000.0, description="最小交易金额")
    commission_rate: float = Field(default=0.0005, description="佣金费率")
    stamp_duty_rate: float = Field(default=0.001, description="印花税率")
    slippage: float = Field(default=0.001, description="滑点")
    max_position_pct: float = Field(default=0.10, description="单票最大仓位")
    min_position_pct: float = Field(default=0.02, description="单票最小仓位")
    respect_t1: bool = Field(default=True, description="是否遵守 T+1 规则")
    notify_enabled: bool = Field(default=True, description="是否发送调仓通知")


# ==================== 5 层配置继承 ====================

class LayerConfig(BaseModel):
    """单层配置基类"""
    model_config = ConfigDict(extra='allow')
    
    def merge_with(self, other: "LayerConfig") -> "LayerConfig":
        """
        与其他层配置合并（other 优先级更高）
        """
        self_dict = self.model_dump(exclude_unset=True)
        other_dict = other.model_dump(exclude_unset=True)
        merged = deep_merge(self_dict, other_dict)
        return self.__class__(**merged)


class GlobalDefaults(LayerConfig):
    """全局默认配置（第 1 层）"""
    system: Optional[SystemConfig] = None
    account: Optional[AccountConfig] = None
    strategy: Optional[StrategyConfig] = None
    position: Optional[PositionConfig] = None
    risk_control: Optional[RiskControlConfig] = None
    market_risk: Optional[MarketRiskConfig] = None
    data: Optional[DataConfig] = None
    trading_hours: Optional[TradingHoursConfig] = None
    twap: Optional[TwapConfig] = None
    rl: Optional[RlConfig] = None
    notify: Optional[NotifyConfig] = None
    log: Optional[LogConfig] = None
    rebalance: Optional[RebalanceConfig] = None


class PerStrategyConfig(GlobalDefaults):
    """策略级配置（第 2 层）"""
    strategy_name: str = Field(..., description="策略名称")


class PerChannelConfig(GlobalDefaults):
    """渠道级配置（第 3 层）"""
    channel: str = Field(..., description="渠道标识")


class PerAccountConfig(BaseModel):
    """账户级配置（第 4 层）"""
    model_config = ConfigDict(extra='allow')
    account_id: str = Field(..., description="账户标识")
    
    # 继承 GlobalDefaults 的所有字段
    system: Optional[SystemConfig] = None
    account: Optional[AccountConfig] = None
    strategy: Optional[StrategyConfig] = None
    position: Optional[PositionConfig] = None
    risk_control: Optional[RiskControlConfig] = None
    market_risk: Optional[MarketRiskConfig] = None
    data: Optional[DataConfig] = None
    trading_hours: Optional[TradingHoursConfig] = None
    twap: Optional[TwapConfig] = None
    rl: Optional[RlConfig] = None
    notify: Optional[NotifyConfig] = None
    log: Optional[LogConfig] = None
    rebalance: Optional[RebalanceConfig] = None


class PerGroupConfig(GlobalDefaults):
    """组级配置（第 5 层）"""
    group_id: str = Field(..., description="组标识")


# ==================== 完整配置 Schema ====================

class BobQuantConfig(BaseModel):
    """
    BobQuant 完整配置
    
    支持 5 层配置继承：
    1. Global Defaults - 全局默认值
    2. Per-Strategy - 策略级配置
    3. Per-Channel - 渠道级配置
    4. Per-Account - 账户级配置
    5. Per-Group - 组级配置
    
    优先级：Per-Group > Per-Account > Per-Channel > Per-Strategy > Global Defaults
    """
    model_config = ConfigDict(extra='allow')
    
    # 系统配置
    system: Optional[SystemConfig] = None
    account: Optional[AccountConfig] = None
    strategy: Optional[StrategyConfig] = None
    position: Optional[PositionConfig] = None
    risk_control: Optional[RiskControlConfig] = None
    market_risk: Optional[MarketRiskConfig] = None
    data: Optional[DataConfig] = None
    trading_hours: Optional[TradingHoursConfig] = None
    twap: Optional[TwapConfig] = None
    rl: Optional[RlConfig] = None
    notify: Optional[NotifyConfig] = None
    log: Optional[LogConfig] = None
    rebalance: Optional[RebalanceConfig] = None
    
    # 股票池配置（支持两种格式：列表或配置字典）
    stock_pool: Optional[Any] = Field(default=None, description="股票池配置")
    
    # 多层配置叠加
    global_defaults: Optional[GlobalDefaults] = Field(default=None, description="全局默认配置")
    strategy_configs: Optional[Dict[str, PerStrategyConfig]] = Field(default=None, description="策略级配置")
    channel_configs: Optional[Dict[str, PerChannelConfig]] = Field(default=None, description="渠道级配置")
    account_configs: Optional[Dict[str, PerAccountConfig]] = Field(default=None, description="账户级配置")
    group_configs: Optional[Dict[str, PerGroupConfig]] = Field(default=None, description="组级配置")
    
    # 当前生效的层标识（用于确定最终配置）
    active_strategy: Optional[str] = Field(default=None, description="当前激活的策略")
    active_channel: Optional[str] = Field(default=None, description="当前激活的渠道")
    active_account: Optional[str] = Field(default=None, description="当前激活的账户")
    active_group: Optional[str] = Field(default=None, description="当前激活的组")
    
    def resolve(self) -> "BobQuantConfig":
        """
        解析多层配置，返回最终合并后的配置
        
        优先级：Per-Group > Per-Account > Per-Channel > Per-Strategy > Global Defaults
        """
        # 从底层开始逐层合并
        base_dict = {}
        
        # 第 1 层：全局默认
        if self.global_defaults:
            base_dict = deep_merge(base_dict, self.global_defaults.model_dump(exclude_unset=True))
        
        # 第 2 层：策略级
        if self.active_strategy and self.strategy_configs:
            strategy_cfg = self.strategy_configs.get(self.active_strategy)
            if strategy_cfg:
                base_dict = deep_merge(base_dict, strategy_cfg.model_dump(exclude_unset=True))
        
        # 第 3 层：渠道级
        if self.active_channel and self.channel_configs:
            channel_cfg = self.channel_configs.get(self.active_channel)
            if channel_cfg:
                base_dict = deep_merge(base_dict, channel_cfg.model_dump(exclude_unset=True))
        
        # 第 4 层：账户级
        if self.active_account and self.account_configs:
            account_cfg = self.account_configs.get(self.active_account)
            if account_cfg:
                base_dict = deep_merge(base_dict, account_cfg.model_dump(exclude_unset=True))
        
        # 第 5 层：组级
        if self.active_group and self.group_configs:
            group_cfg = self.group_configs.get(self.active_group)
            if group_cfg:
                base_dict = deep_merge(base_dict, group_cfg.model_dump(exclude_unset=True))
        
        # 合并顶层的配置（不包括内部字段）
        self_dict = {}
        for field_name in ['system', 'account', 'strategy', 'position', 'risk_control',
                           'market_risk', 'data', 'trading_hours', 'twap', 'rl',
                           'notify', 'log', 'rebalance', 'stock_pool']:
            value = getattr(self, field_name)
            if value is not None:
                if isinstance(value, BaseModel):
                    self_dict[field_name] = value.model_dump(exclude_unset=True)
                else:
                    self_dict[field_name] = value
        
        final_dict = deep_merge(base_dict, self_dict)
        
        return BobQuantConfig(**final_dict)
    
    def resolve_secrets(self) -> "BobQuantConfig":
        """
        解析所有 SecretRef，替换为实际值
        """
        def resolve_value(value: Any) -> Any:
            if isinstance(value, SecretRef):
                return value.resolve()
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            elif isinstance(value, BaseModel):
                resolved_dict = {}
                for field_name, field_value in value.model_dump().items():
                    resolved_dict[field_name] = resolve_value(field_value)
                return value.__class__(**resolved_dict)
            return value
        
        resolved_dict = {}
        for field_name, field_value in self.model_dump().items():
            resolved_dict[field_name] = resolve_value(field_value)
        
        return BobQuantConfig(**resolved_dict)


# ==================== 辅助函数 ====================

def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    深度合并两个字典（override 优先级更高）
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def expand_env_vars(text: str) -> str:
    """
    扩展环境变量
    支持格式：${VAR_NAME} 或 $VAR_NAME
    """
    # ${VAR_NAME} 格式
    def replace_braced(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    text = re.sub(r'\$\{([^}]+)\}', replace_braced, text)
    
    # $VAR_NAME 格式（不包含花括号）
    def replace_simple(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    text = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)', replace_simple, text)
    
    return text


# ==================== 配置加载器 ====================

class ConfigLoader:
    """
    配置加载器
    
    支持：
    - JSON5 格式（注释、尾随逗号）
    - 环境变量替换
    - SecretRef 解析
    - 多层配置继承
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else None
    
    def load_json5(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        加载配置文件（支持 JSON5 和 YAML）
        
        支持：
        - JSON5：注释（// 和 /* */）、尾随逗号、环境变量替换
        - YAML：标准 YAML 格式
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"配置文件不存在：{filepath}")
        
        content = filepath.read_text(encoding='utf-8')
        
        # 环境变量替换
        content = expand_env_vars(content)
        
        # 根据文件扩展名选择解析方式
        suffix = filepath.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            # YAML 格式
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                raise ImportError("请安装 PyYAML: pip install pyyaml")
            except yaml.YAMLError as e:
                raise ValueError(f"YAML 解析失败：{e}")
        else:
            # JSON5 格式
            try:
                data = json5.loads(content)
            except json5.JSON5DecodeError as e:
                raise ValueError(f"JSON5 解析失败：{e}")
        
        return data
    
    def load(self, 
             config_path: Optional[Union[str, Path]] = None,
             strategy: Optional[str] = None,
             channel: Optional[str] = None,
             account: Optional[str] = None,
             group: Optional[str] = None) -> BobQuantConfig:
        """
        加载配置
        
        Args:
            config_path: 配置文件路径
            strategy: 策略标识
            channel: 渠道标识
            account: 账户标识
            group: 组标识
        
        Returns:
            BobQuantConfig: 解析后的配置对象
        """
        path = Path(config_path) if config_path else self.config_path
        
        if not path:
            raise ValueError("未指定配置文件路径")
        
        # 加载 JSON5
        data = self.load_json5(path)
        
        # 转换为配置对象
        data['active_strategy'] = strategy
        data['active_channel'] = channel
        data['active_account'] = account
        data['active_group'] = group
        
        config = BobQuantConfig(**data)
        
        # 解析多层配置
        resolved = config.resolve()
        
        return resolved
    
    def load_with_secrets(self, 
                         config_path: Optional[Union[str, Path]] = None,
                         **kwargs) -> BobQuantConfig:
        """
        加载配置并解析所有 SecretRef
        """
        config = self.load(config_path, **kwargs)
        return config.resolve_secrets()


# ==================== 配置验证 ====================

class ValidationError(Exception):
    """配置验证错误"""
    def __init__(self, message: str, field: Optional[str] = None, suggestion: Optional[str] = None):
        self.message = message
        self.field = field
        self.suggestion = suggestion
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        msg = f"配置验证错误：{self.message}"
        if self.field:
            msg = f"{msg} (字段：{self.field})"
        if self.suggestion:
            msg = f"{msg} 建议：{self.suggestion}"
        return msg


class ConfigValidator:
    """
    配置验证器
    
    提供：
    - Schema 验证
    - 业务规则验证
    - 详细错误信息
    """
    
    def __init__(self, config: BobQuantConfig):
        self.config = config
        self.errors: List[ValidationError] = []
    
    def validate_schema(self) -> bool:
        """
        验证 Schema 合法性
        """
        try:
            BobQuantConfig.model_validate(self.config.model_dump())
            return True
        except PydanticValidationError as e:
            for error in e.errors():
                field = '.'.join(str(x) for x in error.get('loc', []))
                self.errors.append(ValidationError(
                    message=error.get('msg', '未知错误'),
                    field=field,
                    suggestion="检查字段类型和格式"
                ))
            return False
    
    def validate_business_rules(self) -> bool:
        """
        验证业务规则
        """
        valid = True
        
        # 检查仓位比例
        if self.config.account and self.config.account.max_position_pct:
            if not (0 < self.config.account.max_position_pct <= 1):
                self.errors.append(ValidationError(
                    message="单票最大仓位比例必须在 0-1 之间",
                    field="account.max_position_pct",
                    suggestion="例如：0.10 表示 10%"
                ))
                valid = False
        
        # 检查止损比例
        if self.config.risk_control and self.config.risk_control.stop_loss:
            stop_loss = self.config.risk_control.stop_loss
            if stop_loss.enabled and stop_loss.pct >= 0:
                self.errors.append(ValidationError(
                    message="止损比例必须为负数",
                    field="risk_control.stop_loss.pct",
                    suggestion="例如：-0.08 表示 -8%"
                ))
                valid = False
        
        # 检查交易时段
        if self.config.trading_hours:
            th = self.config.trading_hours
            if th.morning_start >= th.morning_end:
                self.errors.append(ValidationError(
                    message="早盘开始时间必须早于结束时间",
                    field="trading_hours",
                ))
                valid = False
        
        return valid
    
    def validate_secrets(self) -> bool:
        """
        验证 SecretRef 是否可解析
        """
        valid = True
        
        def check_secret(value: Any, path: str):
            nonlocal valid
            if isinstance(value, SecretRef):
                try:
                    value.resolve()
                except ValueError as e:
                    self.errors.append(ValidationError(
                        message=str(e),
                        field=path,
                        suggestion="检查环境变量/文件路径/命令是否正确"
                    ))
                    valid = False
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_secret(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_secret(item, f"{path}[{i}]")
        
        check_secret(self.config.model_dump(), "config")
        return valid
    
    def validate_all(self) -> bool:
        """
        执行所有验证
        """
        self.errors = []
        
        self.validate_schema()
        self.validate_business_rules()
        self.validate_secrets()
        
        return len(self.errors) == 0
    
    def get_errors(self) -> List[ValidationError]:
        """获取所有错误"""
        return self.errors
    
    def get_error_report(self) -> str:
        """获取错误报告"""
        if not self.errors:
            return "✓ 配置验证通过"
        
        report = ["配置验证失败，发现以下问题："]
        for i, error in enumerate(self.errors, 1):
            report.append(f"\n{i}. {error.format_message()}")
        
        return "\n".join(report)


# ==================== 配置示例 ====================

def get_example_config() -> str:
    """返回配置示例（JSON5 格式）"""
    return '''
{
  // ==================== 系统配置 ====================
  "system": {
    "name": "BobQuant 模拟盘",
    "version": "3.0",
    "mode": "simulation",  // simulation / real / backtest
    "log_level": "INFO",
    "debug": false
  },
  
  // ==================== 账户配置 ====================
  "account": {
    "initial_capital": 1000000,  // 初始资金 100 万
    "commission_rate": 0.0005,   // 佣金万分之五
    "stamp_duty_rate": 0.001,    // 印花税千分之一
    "max_position_pct": 0.10,    // 单票最大仓位 10%
    "max_stocks": 10,            // 最大持仓 10 只
    // SecretRef 示例 - 从环境变量读取 API 密钥
    "api_key": "${env:BOBQUANT_API_KEY}",
    "api_secret": "${file:~/.bobquant/secret.txt}"
  },
  
  // ==================== 策略配置 ====================
  "strategy": {
    "dual_macd": {
      "enabled": true,
      "short_period": [6, 13, 5],
      "long_period": [24, 52, 18]
    },
    "bollinger": {
      "enabled": true,
      "window": 20,
      "num_std": 2,
      "dynamic": true
    },
    "signal": {
      "rsi_buy_max": 35,
      "rsi_sell_min": 70,
      "volume_confirm": true,
      "volume_ratio_buy": 1.5
    }
  },
  
  // ==================== 仓位管理 ====================
  "position": {
    "max_position_pct": 0.10,
    "max_stocks": 10,
    "min_buy_shares": 100,
    "pyramid": {
      "enabled": true,
      "levels": [0.03, 0.05, 0.07],
      "add_dip_pct": 0.03
    }
  },
  
  // ==================== 风控配置 ====================
  "risk_control": {
    "stop_loss": {
      "enabled": true,
      "pct": -0.08  // -8% 止损
    },
    "trailing_stop": {
      "enabled": true,
      "activation_pct": 0.05,  // 盈利 5% 后激活
      "drawdown_pct": 0.02     // 回撤 2% 止盈
    },
    "take_profit": {
      "enabled": true,
      "levels": [
        {"threshold": 0.05, "sell_ratio": 0.33},
        {"threshold": 0.10, "sell_ratio": 0.50},
        {"threshold": 0.15, "sell_ratio": 1.00}
      ]
    }
  },
  
  // ==================== 大盘风控 ====================
  "market_risk": {
    "enabled": true,
    "index_code": "sh.000001",
    "ma20_line": 20,
    "max_position_bear": 0.50,
    "crash_threshold": -0.03
  },
  
  // ==================== 数据源 ====================
  "data": {
    "primary": "tencent",
    "fallback": "tencent",
    "history_provider": "baostock",
    "history_days": 60
  },
  
  // ==================== 交易时段 ====================
  "trading_hours": {
    "morning_start": "09:25",
    "morning_end": "11:35",
    "afternoon_start": "12:55",
    "afternoon_end": "15:05",
    "pre_market": "09:15",
    "post_market": "15:30"
  },
  
  // ==================== TWAP 算法 ====================
  "twap": {
    "enabled": false,
    "threshold": 10000,
    "slices": 5,
    "duration_minutes": 10
  },
  
  // ==================== 强化学习 ====================
  "rl": {
    "enabled": false,
    "algorithm": "ppo",
    "model_path": "rl/models",
    "training": {
      "total_timesteps": 10000,
      "eval_freq": 1000,
      "n_eval_episodes": 5,
      "window_size": 60
    },
    "trading": {
      "max_stocks": 10,
      "max_position_pct": 0.10,
      "initial_capital": 1000000
    },
    "prediction": {
      "use_trained_model": true,
      "deterministic": true
    }
  },
  
  // ==================== 通知配置 ====================
  "notify": {
    "feishu": {
      "enabled": true,
      "user_id": "ou_973651ccbc692b7cd90a7d561f6885b3",
      "webhook_url": "${env:FEISHU_WEBHOOK_URL}"  // SecretRef 示例
    },
    "events": {
      "trade_executed": true,
      "stop_loss": true,
      "take_profit": true,
      "daily_report": true,
      "risk_warning": true
    }
  },
  
  // ==================== 日志配置 ====================
  "log": {
    "dir": "logs/sim_trading",
    "max_size": 10485760,  // 10MB
    "backup_count": 10
  },
  
  // ==================== 自动调仓 ====================
  "rebalance": {
    "enabled": false,
    "mode": "equal_weight",
    "frequency": "weekly",
    "rebalance_day": 0,
    "threshold_pct": 0.05,
    "min_trade_value": 1000,
    "commission_rate": 0.0005,
    "stamp_duty_rate": 0.001,
    "slippage": 0.001,
    "max_position_pct": 0.10,
    "min_position_pct": 0.02,
    "respect_t1": true,
    "notify_enabled": true
  },
  
  // ==================== 股票池 ====================
  "stock_pool": [
    {"code": "sh.600000", "name": "浦发银行", "strategy": "bollinger"},
    {"code": "sh.600036", "name": "招商银行", "strategy": "dual_macd"},
    // 更多股票...
  ],
  
  // ==================== 5 层配置继承示例 ====================
  "global_defaults": {
    "account": {
      "initial_capital": 1000000,
      "commission_rate": 0.0005
    }
  },
  
  "strategy_configs": {
    "bollinger_conservative": {
      "strategy_name": "bollinger_conservative",
      "position": {"max_position_pct": 0.05},
      "risk_control": {"stop_loss": {"pct": -0.05}}
    },
    "dual_macd_aggressive": {
      "strategy_name": "dual_macd_aggressive",
      "position": {"max_position_pct": 0.15},
      "risk_control": {"stop_loss": {"pct": -0.10}}
    }
  },
  
  "channel_configs": {
    "sim_channel": {
      "channel": "sim_channel",
      "system": {"mode": "simulation"}
    },
    "real_channel": {
      "channel": "real_channel",
      "system": {"mode": "real"}
    }
  },
  
  "account_configs": {
    "account_001": {
      "account_id": "account_001",
      "account": {"initial_capital": 500000}
    }
  },
  
  "group_configs": {
    "group_a": {
      "group_id": "group_a",
      "account": {"max_stocks": 5}
    }
  },
  
  // 当前激活的配置层
  "active_strategy": "bollinger_conservative",
  "active_channel": "sim_channel",
  "active_account": "account_001",
  "active_group": "group_a"
}
'''
