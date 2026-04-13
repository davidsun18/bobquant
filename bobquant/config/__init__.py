# -*- coding: utf-8 -*-
"""
BobQuant 配置模块
提供 5 层配置继承、JSON5 支持、SecretRef、配置迁移和验证
"""

from .schema import (
    # 主配置 schema
    BobQuantConfig,
    SystemConfig,
    AccountConfig,
    StrategyConfig,
    PositionConfig,
    RiskControlConfig,
    MarketRiskConfig,
    DataConfig,
    TradingHoursConfig,
    TwapConfig,
    RlConfig,
    NotifyConfig,
    LogConfig,
    RebalanceConfig,
    
    # SecretRef 支持
    SecretRef,
    SecretType,
    
    # 配置加载器
    ConfigLoader,
    
    # 配置验证
    ConfigValidator,
    ValidationError,
)

from .migrations import (
    ConfigMigrator,
    MigrationError,
    MigrationStep,
)

__all__ = [
    # Schema
    'BobQuantConfig',
    'SystemConfig',
    'AccountConfig',
    'StrategyConfig',
    'PositionConfig',
    'RiskControlConfig',
    'MarketRiskConfig',
    'DataConfig',
    'TradingHoursConfig',
    'TwapConfig',
    'RlConfig',
    'NotifyConfig',
    'LogConfig',
    'RebalanceConfig',
    
    # SecretRef
    'SecretRef',
    'SecretType',
    
    # 加载器
    'ConfigLoader',
    
    # 验证
    'ConfigValidator',
    'ValidationError',
    
    # 迁移
    'ConfigMigrator',
    'MigrationError',
    'MigrationStep',
]
