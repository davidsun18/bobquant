# -*- coding: utf-8 -*-
"""
BobQuant 技术指标库 v2.0
所有指标函数接收 DataFrame，返回添加了新列的 DataFrame

v2.0 新增：
- 双 MACD 策略（短周期 + 长周期过滤）
- 动态布林带（根据波动率自适应标准差）
- 波动率计算
"""
import pandas as pd
import numpy as np


def macd(df, fast=12, slow=26, signal=9, prefix=''):
    """
    MACD 指标
    
    Args:
        df: DataFrame，包含 'close' 列
        fast: 快线周期
        slow: 慢线周期
        signal: 信号线周期
        prefix: 列名前缀（用于区分双 MACD）
        
    Returns:
        DataFrame，添加了 MACD 相关列
    """
    df = df.copy()
    df[f'{prefix}ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df[f'{prefix}ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df[f'{prefix}macd'] = df[f'{prefix}ema_fast'] - df[f'{prefix}ema_slow']
    df[f'{prefix}macd_signal'] = df[f'{prefix}macd'].ewm(span=signal, adjust=False).mean()
    df[f'{prefix}macd_hist'] = df[f'{prefix}macd'] - df[f'{prefix}macd_signal']
    
    # 兼容旧版字段名（仅当 prefix 为空时）
    if prefix == '':
        df['ma1'] = df['ema_fast']
        df['ma2'] = df['ema_slow']
    
    return df


def dual_macd(df):
    """
    双 MACD 策略指标
    
    计算短周期 (6,13,5) 和长周期 (24,52,18) 两套 MACD
    用于过滤假信号：只有双 MACD 同向时才认为是有效信号
    
    Returns:
        DataFrame，添加了双 MACD 相关列
    """
    df = df.copy()
    
    # 短周期 MACD (6,13,5) - 敏感，捕捉早期信号
    df = macd(df, fast=6, slow=13, signal=5, prefix='short_')
    
    # 长周期 MACD (24,52,18) - 稳定，过滤噪音
    df = macd(df, fast=24, slow=52, signal=18, prefix='long_')
    
    # 双 MACD 确认信号
    # 金叉确认：短周期和长周期同时金叉
    df['dual_golden'] = (
        (df['short_macd'] > df['short_macd_signal']) & 
        (df['long_macd'] > df['long_macd_signal']) &
        (df['short_macd'].shift(1) <= df['short_macd_signal'].shift(1)) &
        (df['long_macd'].shift(1) <= df['long_macd_signal'].shift(1))
    )
    
    # 死叉确认：短周期和长周期同时死叉
    df['dual_death'] = (
        (df['short_macd'] < df['short_macd_signal']) & 
        (df['long_macd'] < df['long_macd_signal']) &
        (df['short_macd'].shift(1) >= df['short_macd_signal'].shift(1)) &
        (df['long_macd'].shift(1) >= df['long_macd_signal'].shift(1))
    )
    
    # 单 MACD 信号（用于对比）
    df['single_golden'] = (df['short_macd'] > df['short_macd_signal']) & \
                          (df['short_macd'].shift(1) <= df['short_macd_signal'].shift(1))
    df['single_death'] = (df['short_macd'] < df['short_macd_signal']) & \
                         (df['short_macd'].shift(1) >= df['short_macd_signal'].shift(1))
    
    return df


def volatility(df, period=20):
    """
    计算波动率（用于动态布林带）
    
    Args:
        df: DataFrame
        period: 计算周期
        
    Returns:
        DataFrame，添加了波动率列
    """
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(period).std()
    df['volatility_annual'] = df['volatility'] * np.sqrt(252)  # 年化波动率
    return df


def bollinger(df, window=20, num_std=2, dynamic=False, vol_period=20):
    """
    布林带指标
    
    Args:
        df: DataFrame，包含 'close' 列
        window: 中轨周期
        num_std: 标准差倍数
        dynamic: 是否启用动态标准差
        vol_period: 波动率计算周期
        
    Returns:
        DataFrame，添加了布林带相关列
    """
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(window).mean()
    df['bb_std'] = df['close'].rolling(window).std()
    
    if dynamic:
        # 动态布林带：根据波动率自适应调整标准差
        df = volatility(df, vol_period)
        
        # 高波动股用 2.5 倍标准差，低波动用 1.8 倍，默认 2.0 倍
        # 使用年化波动率分位数来判断
        vol_median = df['volatility_annual'].median()
        vol_high = df['volatility_annual'].quantile(0.75)
        vol_low = df['volatility_annual'].quantile(0.25)
        
        def get_dynamic_std(row):
            if pd.isna(row['volatility_annual']):
                return num_std
            if row['volatility_annual'] > vol_high:
                return 2.5  # 高波动
            elif row['volatility_annual'] < vol_low:
                return 1.8  # 低波动
            else:
                return num_std  # 中等波动
        
        df['bb_std_dynamic'] = df.apply(get_dynamic_std, axis=1)
        df['bb_upper'] = df['bb_mid'] + df['bb_std_dynamic'] * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - df['bb_std_dynamic'] * df['bb_std']
        df['bb_std_used'] = df['bb_std_dynamic']
    else:
        df['bb_upper'] = df['bb_mid'] + num_std * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - num_std * df['bb_std']
        df['bb_std_used'] = num_std
    
    denom = df['bb_upper'] - df['bb_lower']
    df['bb_pos'] = (df['close'] - df['bb_lower']) / denom.replace(0, 1e-10)
    return df


def rsi(df, period=14):
    """RSI 相对强弱指标"""
    df = df.copy()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df


def volume_ratio(df, period=20):
    """量比（当日成交量 / N日均量）"""
    df = df.copy()
    df['vol_ma'] = df['volume'].rolling(period).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma'].replace(0, 1e-10)
    return df


def compute_all(df):
    """一次性计算所有指标（方便策略使用）"""
    df = macd(df)
    df = bollinger(df)
    df = rsi(df)
    if 'volume' in df.columns:
        df = volume_ratio(df)
    return df
