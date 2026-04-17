# -*- coding: utf-8 -*-
"""
BobQuant 技术指标库 v3.0 - 集成 TA-Lib 高级指标库

v3.0 新增:
- 完整集成 talib_advanced 模块
- 150+ TA-Lib 指标封装
- 指标组合策略
- 指标背离检测
- 金叉/死叉检测
- 多周期共振分析

v2.2 新增:
- 集成 TA-Lib 高性能指标计算
- 支持 150+ 技术指标
- K 线形态识别 (CDL 系列)
- 性能提升 10-100 倍

使用方式:
    from bobquant.indicator.technical import macd, bollinger
    from bobquant.indicator.talib_advanced import TALibIndicators, IndicatorStrategies
    
    # 基础用法
    df = macd(df)  # 自动使用 TA-Lib 加速
    
    # 高级用法
    ind = TALibIndicators(df)
    df['rsi'] = ind.rsi(14)
    
    # 策略用法
    strategies = IndicatorStrategies(df)
    df = strategies.dual_ma_strategy()
"""
import pandas as pd
import numpy as np

# 尝试导入 TA-Lib
try:
    import talib
    TALIB_AVAILABLE = True
    print("[指标] ✅ TA-Lib 已加载，高性能模式启用")
except ImportError:
    TALIB_AVAILABLE = False
    print("[指标] ⚠️ TA-Lib 未安装，使用纯 Python 实现")

# 导入高级指标模块
try:
    from .talib_advanced import (
        TALibIndicators,
        IndicatorStrategies,
        DivergenceDetector,
        CrossDetector,
        compute_indicator,
        apply_indicators,
        get_all_indicators_info
    )
    print("[指标] ✅ talib_advanced 模块已加载")
except ImportError as e:
    print(f"[指标] ⚠️ talib_advanced 模块导入失败：{e}")


def macd(df, fast=12, slow=26, signal=9, prefix=''):
    """
    MACD 指标 - v2.2: 优先使用 TA-Lib
    
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
    
    if TALIB_AVAILABLE:
        # 使用 TA-Lib (性能提升 10-100 倍)
        df[f'{prefix}macd'], df[f'{prefix}macd_signal'], df[f'{prefix}macd_hist'] = \
            talib.MACD(df['close'].values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
    else:
        # 降级到纯 Python 实现
        df[f'{prefix}ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df[f'{prefix}ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df[f'{prefix}macd'] = df[f'{prefix}ema_fast'] - df[f'{prefix}ema_slow']
        df[f'{prefix}macd_signal'] = df[f'{prefix}macd'].ewm(span=signal, adjust=False).mean()
        df[f'{prefix}macd_hist'] = df[f'{prefix}macd'] - df[f'{prefix}macd_signal']
    
    # 兼容旧版字段名（仅当 prefix 为空时）
    if prefix == '':
        df['ma1'] = df.get(f'{prefix}ema_fast', df['close'])
        df['ma2'] = df.get(f'{prefix}ema_slow', df['close'])
    
    return df


def dual_macd(df):
    """
    双 MACD 策略指标
    
    计算短周期 (6,13,5) 和长周期 (24,52,18) 两套 MACD
    用于过滤假信号：只有双 MACD 同向时才认为是有效信号
    """
    df = macd(df, fast=6, slow=13, signal=5, prefix='short_')
    df = macd(df, fast=24, slow=52, signal=18, prefix='long_')
    
    # 双金叉：短周期和长周期同时金叉
    df['dual_golden'] = (
        (df['short_macd'] > df['short_macd_signal']) & 
        (df['short_macd'].shift(1) <= df['short_macd_signal'].shift(1)) &
        (df['long_macd'] > df['long_macd_signal']) & 
        (df['long_macd'].shift(1) <= df['long_macd_signal'].shift(1))
    )
    
    # 双死叉：短周期和长周期同时死叉
    df['dual_death'] = (
        (df['short_macd'] < df['short_macd_signal']) & 
        (df['short_macd'].shift(1) >= df['short_macd_signal'].shift(1)) &
        (df['long_macd'] < df['long_macd_signal']) & 
        (df['long_macd'].shift(1) >= df['long_macd_signal'].shift(1))
    )
    
    return df


def bollinger(df, window=20, num_std=2, dynamic=False):
    """
    布林带 - v2.2: 优先使用 TA-Lib
    
    Args:
        df: DataFrame，包含 'close' 列
        window: 周期
        num_std: 标准差倍数
        dynamic: 是否使用动态标准差（根据波动率自适应）
        
    Returns:
        DataFrame，添加了布林带相关列
    """
    df = df.copy()
    
    if TALIB_AVAILABLE:
        # 使用 TA-Lib
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = \
            talib.BBANDS(df['close'].values, timeperiod=window, nbdevup=num_std, nbdevdn=num_std, matype=0)
        df['bb_std_used'] = num_std
    else:
        # 降级到纯 Python 实现
        df['bb_middle'] = df['close'].rolling(window=window).mean()
        bb_std = df['close'].rolling(window=window).std()
        
        if dynamic:
            # 动态调整标准差：高波动时扩大，低波动时缩小
            volatility = df['close'].pct_change().rolling(20).std()
            vol_adjustment = 1 + (volatility - volatility.mean()) / volatility.mean()
            vol_adjustment = vol_adjustment.clip(0.8, 1.5)  # 限制调整范围
            df['bb_std_used'] = num_std * vol_adjustment
        else:
            df['bb_std_used'] = num_std
        
        df['bb_upper'] = df['bb_middle'] + (bb_std * df['bb_std_used'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * df['bb_std_used'])
    
    # 计算 %B 指标
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    return df


def rsi(df, period=14):
    """
    RSI 指标 - v2.2: 优先使用 TA-Lib
    """
    df = df.copy()
    
    if TALIB_AVAILABLE:
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=period)
    else:
        # 降级到纯 Python 实现
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
    
    return df


def atr(df, period=14):
    """
    平均真实波动幅度 (ATR) - v2.2: 优先使用 TA-Lib
    
    用于衡量波动率，适合设置止损位
    """
    df = df.copy()
    
    if TALIB_AVAILABLE:
        df['atr'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=period)
    else:
        # 降级到纯 Python 实现
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=period).mean()
    
    return df


def kdj(df, n=9, m1=3, m2=3):
    """
    KDJ 指标 - 随机指标
    
    Args:
        df: DataFrame，包含 'high', 'low', 'close' 列
        n: RSV 计算周期
        m1: K 值平滑周期
        m2: D 值平滑周期
        
    Returns:
        DataFrame，添加了 KDJ 相关列
    """
    df = df.copy()
    
    if TALIB_AVAILABLE:
        # TA-Lib 的 KD 指标（慢速随机）
        df['k'], df['d'] = talib.STOCH(df['high'].values, df['low'].values, df['close'].values,
                                        fastk_period=n, slowk_period=m1, slowk_matype=0,
                                        slowd_period=m2, slowd_matype=0)
        df['j'] = 3 * df['k'] - 2 * df['d']
    else:
        # 降级到纯 Python 实现
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        df['k'] = rsv.ewm(com=m1-1, adjust=False).mean()
        df['d'] = df['k'].ewm(com=m2-1, adjust=False).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
    
    return df


def volume_ratio(df, period=5):
    """
    成交量比率 - 当前成交量 / N 日平均成交量
    """
    df = df.copy()
    
    if 'volume' in df.columns:
        df['volume_ma'] = df['volume'].rolling(window=period).mean()
        df['vol_ratio'] = df['volume'] / df['volume_ma']
    else:
        df['vol_ratio'] = 1.0
    
    return df


def momentum(df, period=10):
    """
    动量指标 - v2.2: 优先使用 TA-Lib
    """
    df = df.copy()
    
    if TALIB_AVAILABLE:
        df['mom'] = talib.MOM(df['close'].values, timeperiod=period)
    else:
        df['mom'] = df['close'].diff(period)
    
    return df


def cci(df, period=20):
    """
    CCI 指标 - 顺势指标 - v2.2: 优先使用 TA-Lib
    """
    df = df.copy()
    
    if TALIB_AVAILABLE:
        df['cci'] = talib.CCI(df['high'].values, df['low'].values, df['close'].values, timeperiod=period)
    else:
        # 降级到纯 Python 实现
        tp = (df['high'] + df['low'] + df['close']) / 3
        tp_mean = tp.rolling(window=period).mean()
        tp_std = tp.rolling(window=period).std()
        df['cci'] = (tp - tp_mean) / (tp_std * 0.015)
    
    return df


# ==================== K 线形态识别 (CDL 系列) - v2.2 新增 ====================

def candlestick_patterns(df):
    """
    K 线形态识别 - v2.2 新增 (仅 TA-Lib)
    
    识别常见 K 线形态：
    - 锤子线/上吊线
    - 吞没形态
    - 晨星/暮星
    - 三只乌鸦/三个白兵
    - 等等...
    
    Returns:
        DataFrame，添加了各种形态识别结果
    """
    df = df.copy()
    
    if not TALIB_AVAILABLE:
        print("[指标] ⚠️ TA-Lib 未安装，跳过 K 线形态识别")
        return df
    
    # 单 K 线形态
    df['cdl_doji'] = talib.CDLDOJI(df['open'], df['high'], df['low'], df['close'])  # 十字星
    df['cdl_hammer'] = talib.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])  # 锤子线
    df['cdl_hanging'] = talib.CDLHANGINGMAN(df['open'], df['high'], df['low'], df['close'])  # 上吊线
    df['cdl_shooting'] = talib.CDLSHOOTINGSTAR(df['open'], df['high'], df['low'], df['close'])  # 流星线
    
    # 双 K 线形态
    df['cdl_engulfing'] = talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])  # 吞没
    df['cdl_harami'] = talib.CDLHARAMI(df['open'], df['high'], df['low'], df['close'])  # 孕线
    
    # 三 K 线形态
    df['cdl_morning'] = talib.CDLMORNINGSTAR(df['open'], df['high'], df['low'], df['close'])  # 晨星
    df['cdl_evening'] = talib.CDLEVENINGSTAR(df['open'], df['high'], df['low'], df['close'])  # 暮星
    df['cdl_3soldiers'] = talib.CDL3WHITESOLDIERS(df['open'], df['high'], df['low'], df['close'])  # 三个白兵
    df['cdl_3crows'] = talib.CDL3BLACKCROWS(df['open'], df['high'], df['low'], df['close'])  # 三只乌鸦
    
    # 解释信号
    df['bullish_pattern'] = (
        (df['cdl_hammer'] == 100) |
        (df['cdl_morning'] == 100) |
        (df['cdl_engulfing'] == 100) |
        (df['cdl_3soldiers'] == 100)
    )
    
    df['bearish_pattern'] = (
        (df['cdl_hanging'] == 100) |
        (df['cdl_evening'] == 100) |
        (df['cdl_engulfing'] == -100) |
        (df['cdl_3crows'] == -100)
    )
    
    return df


# ==================== 综合指标应用 ====================

def apply_all_indicators(df):
    """
    应用所有常用指标 - v2.2: 使用 TA-Lib 加速
    
    Args:
        df: DataFrame，包含 OHLCV 列
        
    Returns:
        DataFrame，添加了所有技术指标
    """
    # 趋势指标
    df = macd(df)
    df = bollinger(df, dynamic=True)
    
    # 摆动指标
    df = rsi(df)
    df = kdj(df)
    df = cci(df)
    
    # 波动率指标
    df = atr(df)
    
    # 成交量指标
    df = volume_ratio(df)
    
    # K 线形态
    df = candlestick_patterns(df)
    
    return df


# ==================== 性能测试 ====================

def benchmark_talib():
    """
    性能测试：对比 TA-Lib 和纯 Python 实现
    """
    import time
    
    # 生成测试数据
    np.random.seed(42)
    n = 10000
    close = np.random.randn(n).cumsum() + 100
    
    print("=" * 60)
    print("TA-Lib 性能测试")
    print("=" * 60)
    
    # TA-Lib RSI
    if TALIB_AVAILABLE:
        start = time.time()
        for _ in range(100):
            talib.RSI(close, timeperiod=14)
        talib_time = time.time() - start
        print(f"TA-Lib RSI (100 次): {talib_time:.4f} 秒")
    
    # 纯 Python RSI
    df = pd.DataFrame({'close': close})
    start = time.time()
    for _ in range(100):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        100 - (100 / (1 + rs))
    python_time = time.time() - start
    print(f"纯 Python RSI (100 次): {python_time:.4f} 秒")
    
    if TALIB_AVAILABLE:
        speedup = python_time / talib_time
        print(f"\n⚡ 性能提升：{speedup:.1f}x")
    
    print("=" * 60)


# ==================== 导出高级指标接口 ====================

__all__ = [
    # 基础指标
    'macd', 'dual_macd', 'bollinger', 'rsi', 'atr', 'kdj',
    'volume_ratio', 'momentum', 'cci', 'candlestick_patterns',
    'apply_all_indicators',
    # 高级指标
    'TALibIndicators', 'IndicatorStrategies', 'DivergenceDetector',
    'CrossDetector', 'compute_indicator', 'apply_indicators',
    'get_all_indicators_info'
]


if __name__ == '__main__':
    # 测试
    test_df = pd.DataFrame({
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    print("📊 技术指标测试")
    print("=" * 60)
    
    df = apply_all_indicators(test_df)
    print(f"数据形状：{df.shape}")
    print(f"列数：{len(df.columns)}")
    print(f"\n新增指标列:")
    for col in df.columns:
        if col not in ['open', 'high', 'low', 'close', 'volume']:
            print(f"  - {col}")
    
    print("\n" + "=" * 60)
    benchmark_talib()
    
    # 测试高级指标
    print("\n" + "=" * 60)
    print("📊 高级指标测试 (talib_advanced)")
    print("=" * 60)
    
    try:
        from .talib_advanced import TALibIndicators, IndicatorStrategies
        
        ind = TALibIndicators(test_df)
        
        # 测试 10 个核心指标
        print("\n【计算 10 个核心指标】")
        core_tests = [
            ('SMA(20)', ind.sma, 20),
            ('EMA(20)', ind.ema, 20),
            ('RSI(14)', ind.rsi, 14),
            ('MACD', ind.macd, None),
            ('KDJ', ind.stoch, None),
            ('布林带', ind.bbands, None),
            ('ATR(14)', ind.atr, 14),
            ('CCI(20)', ind.cci, 20),
            ('威廉指标', ind.willr, 14),
            ('资金流量', ind.mfi, 14)
        ]
        
        for name, func, param in core_tests:
            try:
                if param:
                    result = func(param)
                else:
                    result = func()
                
                if isinstance(result, tuple):
                    print(f"✅ {name}: {len(result)} 个序列")
                else:
                    print(f"✅ {name}: 长度 {len(result)}")
            except Exception as e:
                print(f"❌ {name}: {e}")
        
        # 测试策略
        print("\n【测试指标组合策略】")
        strategies = IndicatorStrategies(test_df)
        df_ma = strategies.dual_ma_strategy()
        print(f"✅ 双均线策略：金叉 {df_ma['golden_cross'].sum()} 次，死叉 {df_ma['death_cross'].sum()} 次")
        
        print("\n" + "=" * 60)
        print("高级指标测试完成！")
        
    except Exception as e:
        print(f"⚠️ 高级指标测试失败：{e}")
