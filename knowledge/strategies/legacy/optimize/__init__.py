#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 参数优化模块

提供 Optuna 参数优化功能：
- MACD/RSI/布林带策略参数优化
- 目标函数定义（夏普比率、总收益等）
- 剪枝优化
- 可视化结果
"""
from .optuna_optimizer import OptunaOptimizer

__all__ = ['OptunaOptimizer']
