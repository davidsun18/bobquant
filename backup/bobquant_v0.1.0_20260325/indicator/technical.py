# -*- coding: utf-8 -*-
"""
BobQuant 技术指标库
所有指标函数接收 DataFrame，返回添加了新列的 DataFrame
"""
import pandas as pd


def macd(df, fast=12, slow=26):
    """MACD 指标"""
    df = df.copy()
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    # 兼容旧版字段名
    df['ma1'] = df['ema_fast']
    df['ma2'] = df['ema_slow']
    return df


def bollinger(df, window=20, num_std=2):
    """布林带指标"""
    df = df.copy()
    df['bb_mid'] = df['close'].rolling(window).mean()
    df['bb_std'] = df['close'].rolling(window).std()
    df['bb_upper'] = df['bb_mid'] + num_std * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - num_std * df['bb_std']
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
