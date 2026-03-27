"""
技术指标因子库 - P0+P1级别
统一接口设计，所有指标返回DataFrame，便于链式调用
"""

import pandas as pd
import numpy as np
from typing import Optional


class TechnicalIndicator:
    """技术指标基类"""
    
    @staticmethod
    def validate_df(df: Optional[pd.DataFrame]) -> bool:
        """验证数据框"""
        if df is None or len(df) < 30:
            return False
        required = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required)


# ===== P0: 核心必备因子 =====

def ma(df: pd.DataFrame, periods=[5, 10, 20, 60]) -> pd.DataFrame:
    """
    移动平均线 (P0)
    
    Args:
        periods: 周期列表，默认[5,10,20,60]
    
    Returns:
        DataFrame with columns: ma5, ma10, ma20, ma60
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    for period in periods:
        df[f'ma{period}'] = df['close'].rolling(window=period).mean()
    
    return df


def macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """
    MACD指标 (P0)
    
    Args:
        fast: 快线周期
        slow: 慢线周期
        signal: 信号线周期
    
    Returns:
        DataFrame with columns: macd_fast, macd_slow, macd_signal, macd_hist, macd_golden, macd_death
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    # 计算EMA
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    # MACD线和信号线
    df['macd_fast'] = ema_fast
    df['macd_slow'] = ema_slow
    df['macd_line'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd_line'].ewm(span=signal, adjust=False).mean()
    df['macd_hist'] = df['macd_line'] - df['macd_signal']
    
    # 金叉死叉信号
    df['macd_golden'] = (df['macd_line'] > df['macd_signal']) & (df['macd_line'].shift(1) <= df['macd_signal'].shift(1))
    df['macd_death'] = (df['macd_line'] < df['macd_signal']) & (df['macd_line'].shift(1) >= df['macd_signal'].shift(1))
    
    return df


def rsi(df: pd.DataFrame, period=14) -> pd.DataFrame:
    """
    RSI相对强弱指标 (P0)
    
    Args:
        period: 计算周期，默认14
    
    Returns:
        DataFrame with columns: rsi, rsi_signal
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # RSI信号
    df['rsi_overbought'] = df['rsi'] > 70  # 超买
    df['rsi_oversold'] = df['rsi'] < 30    # 超卖
    
    return df


def volume_ma(df: pd.DataFrame, periods=[5, 10, 20]) -> pd.DataFrame:
    """
    成交量均线 (P0)
    
    Returns:
        DataFrame with columns: vol_ma5, vol_ma10, vol_ma20
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    for period in periods:
        df[f'vol_ma{period}'] = df['volume'].rolling(window=period).mean()
    
    # 量比
    df['volume_ratio'] = df['volume'] / df['vol_ma5']
    
    return df


# ===== P1: 重要增强因子 =====

def bollinger(df: pd.DataFrame, period=20, std_dev=2) -> pd.DataFrame:
    """
    布林带 (P1)
    
    Args:
        period: 中轨周期，默认20
        std_dev: 标准差倍数，默认2
    
    Returns:
        DataFrame with columns: boll_mid, boll_upper, boll_lower, boll_pct, boll_squeeze
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    # 中轨和带宽
    df['boll_mid'] = df['close'].rolling(window=period).mean()
    df['boll_std'] = df['close'].rolling(window=period).std()
    df['boll_upper'] = df['boll_mid'] + (df['boll_std'] * std_dev)
    df['boll_lower'] = df['boll_mid'] - (df['boll_std'] * std_dev)
    
    # 布林带位置百分比
    df['boll_pct'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'])
    
    # 突破信号
    df['boll_break_upper'] = df['close'] > df['boll_upper']
    df['boll_break_lower'] = df['close'] < df['boll_lower']
    
    # 布林带收口（波动率降低）
    df['boll_width'] = (df['boll_upper'] - df['boll_lower']) / df['boll_mid']
    df['boll_squeeze'] = df['boll_width'] < df['boll_width'].rolling(window=20).mean() * 0.85
    
    return df


def kdj(df: pd.DataFrame, n=9, m1=3, m2=3) -> pd.DataFrame:
    """
    KDJ随机指标 (P1)
    
    Args:
        n: RSV周期，默认9
        m1: K平滑周期，默认3
        m2: D平滑周期，默认3
    
    Returns:
        DataFrame with columns: kdj_k, kdj_d, kdj_j, kdj_golden, kdj_death
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    # RSV
    low_list = df['low'].rolling(window=n, min_periods=n).min()
    high_list = df['high'].rolling(window=n, min_periods=n).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    
    # K, D, J值
    df['kdj_k'] = rsv.ewm(alpha=1/m1, adjust=False).mean()
    df['kdj_d'] = df['kdj_k'].ewm(alpha=1/m2, adjust=False).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    
    # 金叉死叉
    df['kdj_golden'] = (df['kdj_k'] > df['kdj_d']) & (df['kdj_k'].shift(1) <= df['kdj_d'].shift(1))
    df['kdj_death'] = (df['kdj_k'] < df['kdj_d']) & (df['kdj_k'].shift(1) >= df['kdj_d'].shift(1))
    
    # 超买超卖
    df['kdj_overbought'] = df['kdj_j'] > 100
    df['kdj_oversold'] = df['kdj_j'] < 0
    
    return df


def atr(df: pd.DataFrame, period=14) -> pd.DataFrame:
    """
    ATR真实波幅 (P1) - 用于止损和仓位管理
    
    Args:
        period: 计算周期，默认14
    
    Returns:
        DataFrame with columns: atr, atr_pct
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    # 真实波幅
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=period).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100  # ATR百分比
    
    return df


def momentum(df: pd.DataFrame, periods=[5, 10, 20]) -> pd.DataFrame:
    """
    价格动量 (P0)
    
    Returns:
        DataFrame with columns: mom5, mom10, mom20
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    for period in periods:
        df[f'mom{period}'] = (df['close'] / df['close'].shift(period) - 1) * 100
    
    return df


# ===== 组合指标 =====

def all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有P0+P1指标
    
    链式调用，一次性计算所有指标
    """
    if not TechnicalIndicator.validate_df(df):
        return df
    
    # P0: 核心指标
    df = ma(df)
    df = macd(df)
    df = rsi(df)
    df = volume_ma(df)
    df = momentum(df)
    
    # P1: 增强指标
    df = bollinger(df)
    df = kdj(df)
    df = atr(df)
    
    return df


# ===== 信号生成器 =====

def generate_signals(df: pd.DataFrame) -> dict:
    """
    生成交易信号
    
    Returns:
        {
            'macd_signal': 'buy'/'sell'/'hold',
            'rsi_signal': 'overbought'/'oversold'/'normal',
            'kdj_signal': 'buy'/'sell'/'hold',
            'boll_signal': 'break_upper'/'break_lower'/'squeeze'/'normal',
            'composite_score': 0-100  # 综合打分
        }
    """
    if not TechnicalIndicator.validate_df(df) or len(df) < 2:
        return {}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = {
        'macd_signal': 'hold',
        'rsi_signal': 'normal',
        'kdj_signal': 'hold',
        'boll_signal': 'normal',
        'composite_score': 50
    }
    
    # MACD信号
    if latest.get('macd_golden', False):
        signals['macd_signal'] = 'buy'
    elif latest.get('macd_death', False):
        signals['macd_signal'] = 'sell'
    
    # RSI信号
    if latest.get('rsi_overbought', False):
        signals['rsi_signal'] = 'overbought'
    elif latest.get('rsi_oversold', False):
        signals['rsi_signal'] = 'oversold'
    
    # KDJ信号
    if latest.get('kdj_golden', False):
        signals['kdj_signal'] = 'buy'
    elif latest.get('kdj_death', False):
        signals['kdj_signal'] = 'sell'
    
    # 布林带信号
    if latest.get('boll_break_upper', False):
        signals['boll_signal'] = 'break_upper'
    elif latest.get('boll_break_lower', False):
        signals['boll_signal'] = 'break_lower'
    elif latest.get('boll_squeeze', False):
        signals['boll_signal'] = 'squeeze'
    
    # 综合打分 (简单版)
    score = 50
    if signals['macd_signal'] == 'buy': score += 20
    if signals['macd_signal'] == 'sell': score -= 20
    if signals['kdj_signal'] == 'buy': score += 15
    if signals['kdj_signal'] == 'sell': score -= 15
    if signals['rsi_signal'] == 'oversold': score += 10
    if signals['rsi_signal'] == 'overbought': score -= 10
    
    signals['composite_score'] = max(0, min(100, score))
    
    return signals
