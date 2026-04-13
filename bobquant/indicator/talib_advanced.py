# -*- coding: utf-8 -*-
"""
BobQuant TA-Lib 高级指标库 v3.0

功能:
- 150+ TA-Lib 指标完整封装
- 指标组合策略
- 指标背离检测
- 金叉/死叉信号
- 多周期共振分析

作者：BobQuant Team
版本：3.0
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import talib

# ==================== 指标分类常量 ====================

# 重叠指标 (Overlap Studies)
OVERLAP_INDICATORS = [
    'SMA', 'EMA', 'WMA', 'DEMA', 'TEMA', 'TRIMA',
    'KAMA', 'MAMA', 'T3', 'MA', 'VWAP'
]

# 动量指标 (Momentum Indicators)
MOMENTUM_INDICATORS = [
    'ADX', 'ADXR', 'APO', 'AROON', 'AROONOSC', 'CCI', 'CMO',
    'DX', 'MACD', 'MACDEXT', 'MACDFIX', 'MOM', 'PPO', 'ROC',
    'ROCP', 'ROCR', 'ROCR100', 'RSI', 'STOCH', 'STOCHF',
    'STOCHRSI', 'TRIX', 'ULTOSC', 'WILLR'
]

# 波动率指标 (Volatility Indicators)
VOLATILITY_INDICATORS = [
    'ATR', 'NATR', 'BBANDS', 'STDDEV', 'TRANGE'
]

# 成交量指标 (Volume Indicators)
VOLUME_INDICATORS = [
    'AD', 'ADOSC', 'OBV', 'MFI', 'VWAP'
]

# K 线形态指标 (Pattern Recognition)
PATTERN_INDICATORS = [
    'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE',
    'CDL3OUTSIDE', 'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS',
    'CDLABANDONEDBABY', 'CDLADVANCEBLOCK', 'CDLBELTHOLD',
    'CDLBREAKAWAY', 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL',
    'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER', 'CDLDOJI',
    'CDLDOJISTAR', 'CDLDRAGONFLYDOJI', 'CDLENGULFING',
    'CDLEVENINGDOJISTAR', 'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE',
    'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN',
    'CDLHARAMI', 'CDLHARAMICROSS', 'CDLHIGHWAVE', 'CDLHIKKAKE',
    'CDLHIKKAKEMOD', 'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS',
    'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING',
    'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM', 'CDLLONGLEGGEDDOJI',
    'CDLLONGLINE', 'CDLMARUBOZU', 'CDLMATCHINGLOW', 'CDLMATHOLD',
    'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK',
    'CDLPIERCING', 'CDLRICKSHAWMAN', 'CDLRISEFALL3METHODS',
    'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR', 'CDLSHORTLINE',
    'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN', 'CDLSTICKSANDWICH',
    'CDLTAKURI', 'CDLTASUKIGAP', 'CDLTHRUSTING', 'CDLTRISTAR',
    'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS', 'CDLXSIDEGAP3METHODS'
]

# 价格转换指标 (Price Transform)
PRICE_TRANSFORM_INDICATORS = [
    'AVGPRICE', 'MEDPRICE', 'TYPPRICE', 'WCLPRICE'
]

# 周期指标 (Cycle Indicators)
CYCLE_INDICATORS = [
    'HT_DCPERIOD', 'HT_DCPHASE', 'HT_PHASOR', 'HT_SINE', 'HT_TRENDLINE', 'HT_TRENDMODE'
]

# 统计指标 (Statistics)
STATISTIC_INDICATORS = [
    'BETA', 'CORREL', 'LINEARREG', 'LINEARREG_ANGLE',
    'LINEARREG_INTERCEPT', 'LINEARREG_SLOPE', 'SLOPE',
    'STDDEV', 'TSF', 'VAR'
]

# 数学运算指标 (Math Transform)
MATH_TRANSFORM_INDICATORS = [
    'ACOS', 'ASIN', 'ATAN', 'CEIL', 'COS', 'COSH', 'EXP',
    'FLOOR', 'LN', 'LOG10', 'SIN', 'SINH', 'SQRT', 'TAN', 'TANH'
]

# 数学运算指标 (Math Operators)
MATH_OPERATOR_INDICATORS = [
    'ADD', 'DIV', 'MAX', 'MAXINDEX', 'MIN', 'MININDEX',
    'MINMAX', 'MINMAXINDEX', 'MULT', 'SUB', 'SUM'
]

# 所有支持的指标
ALL_INDICATORS = (
    OVERLAP_INDICATORS + MOMENTUM_INDICATORS + VOLATILITY_INDICATORS +
    VOLUME_INDICATORS + PATTERN_INDICATORS + PRICE_TRANSFORM_INDICATORS +
    CYCLE_INDICATORS + STATISTIC_INDICATORS + MATH_TRANSFORM_INDICATORS +
    MATH_OPERATOR_INDICATORS
)


# ==================== 基础指标封装 ====================

class TALibIndicators:
    """TA-Lib 指标封装类 - 提供 150+ 技术指标"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化指标计算器
        
        Args:
            df: DataFrame，必须包含 'open', 'high', 'low', 'close', 'volume' 列
        """
        self.df = df.copy()
        self._validate_columns()
    
    def _validate_columns(self):
        """验证必需的列是否存在"""
        required = ['open', 'high', 'low', 'close']
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"缺少必需的列：{missing}")
    
    # ========== 重叠指标 (Overlap Studies) ==========
    
    def sma(self, period: int = 20, col: str = 'close') -> pd.Series:
        """简单移动平均线 (SMA)"""
        return talib.SMA(self.df[col].values, timeperiod=period)
    
    def ema(self, period: int = 20, col: str = 'close') -> pd.Series:
        """指数移动平均线 (EMA)"""
        return talib.EMA(self.df[col].values, timeperiod=period)
    
    def wma(self, period: int = 20, col: str = 'close') -> pd.Series:
        """加权移动平均线 (WMA)"""
        return talib.WMA(self.df[col].values, timeperiod=period)
    
    def dema(self, period: int = 30, col: str = 'close') -> pd.Series:
        """双指数移动平均线 (DEMA)"""
        return talib.DEMA(self.df[col].values, timeperiod=period)
    
    def tema(self, period: int = 30, col: str = 'close') -> pd.Series:
        """三重指数移动平均线 (TEMA)"""
        return talib.TEMA(self.df[col].values, timeperiod=period)
    
    def trima(self, period: int = 30, col: str = 'close') -> pd.Series:
        """三角移动平均线 (TRIMA)"""
        return talib.TRIMA(self.df[col].values, timeperiod=period)
    
    def kama(self, period: int = 30, col: str = 'close') -> pd.Series:
        """考夫曼自适应移动平均线 (KAMA)"""
        return talib.KAMA(self.df[col].values, timeperiod=period)
    
    def mama(self, fastlimit: float = 0.5, slowlimit: float = 0.05, col: str = 'close') -> Tuple[pd.Series, pd.Series]:
        """MESA 自适应移动平均线 (MAMA/FAMA)"""
        mama, fama = talib.MAMA(self.df[col].values, fastlimit=fastlimit, slowlimit=slowlimit)
        return mama, fama
    
    def t3(self, period: int = 30, vfactor: float = 0.7, col: str = 'close') -> pd.Series:
        """T3 移动平均线"""
        return talib.T3(self.df[col].values, timeperiod=period, vfactor=vfactor)
    
    def ma(self, period: int = 30, matype: int = 0, col: str = 'close') -> pd.Series:
        """通用移动平均线 (支持多种类型)
        
        matype: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 5=TRIMA, 6=KAMA, 7=MAMA, 8=T3
        """
        return talib.MA(self.df[col].values, timeperiod=period, matype=matype)
    
    # ========== 动量指标 (Momentum Indicators) ==========
    
    def adx(self, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """平均趋向指标 (ADX) + DI"""
        plus_di = talib.PLUS_DI(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
        minus_di = talib.MINUS_DI(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
        adx = talib.ADX(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
        return adx, plus_di, minus_di
    
    def adxr(self, period: int = 14) -> pd.Series:
        """平均趋向指标评级 (ADXR)"""
        return talib.ADXR(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
    
    def apo(self, fastperiod: int = 12, slowperiod: int = 26, matype: int = 0) -> pd.Series:
        """绝对价格振荡器 (APO)"""
        return talib.APO(self.df['close'].values, fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)
    
    def aroon(self, period: int = 14) -> Tuple[pd.Series, pd.Series]:
        """阿隆指标 (Aroon)"""
        aroon_up, aroon_down = talib.AROON(self.df['high'].values, self.df['low'].values, timeperiod=period)
        return aroon_up, aroon_down
    
    def aroonosc(self, period: int = 14) -> pd.Series:
        """阿隆振荡器 (Aroon Oscillator)"""
        return talib.AROONOSC(self.df['high'].values, self.df['low'].values, timeperiod=period)
    
    def cci(self, period: int = 20) -> pd.Series:
        """商品通道指标 (CCI)"""
        return talib.CCI(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
    
    def cmo(self, period: int = 14, col: str = 'close') -> pd.Series:
        """钱德动量振荡器 (CMO)"""
        return talib.CMO(self.df[col].values, timeperiod=period)
    
    def dx(self, period: int = 14) -> pd.Series:
        """趋向指标 (DX)"""
        return talib.DX(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
    
    def macd(self, fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """平滑异同移动平均线 (MACD)"""
        macd_line, signal_line, histogram = talib.MACD(
            self.df['close'].values,
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )
        return macd_line, signal_line, histogram
    
    def macdext(self, fastperiod: int = 12, fastmatype: int = 0,
                slowperiod: int = 26, slowmatype: int = 0,
                signalperiod: int = 9, signalmatype: int = 0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD 扩展版 (可指定 MA 类型)"""
        macd_line, signal_line, histogram = talib.MACDEXT(
            self.df['close'].values,
            fastperiod=fastperiod, fastmatype=fastmatype,
            slowperiod=slowperiod, slowmatype=slowmatype,
            signalperiod=signalperiod, signalmatype=signalmatype
        )
        return macd_line, signal_line, histogram
    
    def mom(self, period: int = 10, col: str = 'close') -> pd.Series:
        """动量指标 (Momentum)"""
        return talib.MOM(self.df[col].values, timeperiod=period)
    
    def ppo(self, fastperiod: int = 12, slowperiod: int = 26, matype: int = 0) -> pd.Series:
        """价格百分比振荡器 (PPO)"""
        return talib.PPO(self.df['close'].values, fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)
    
    def roc(self, period: int = 10, col: str = 'close') -> pd.Series:
        """变化率指标 (ROC)"""
        return talib.ROC(self.df[col].values, timeperiod=period)
    
    def rocp(self, period: int = 10, col: str = 'close') -> pd.Series:
        """变化率百分比 (ROCP)"""
        return talib.ROCP(self.df[col].values, timeperiod=period)
    
    def rocr(self, period: int = 10, col: str = 'close') -> pd.Series:
        """变化率比率 (ROCR)"""
        return talib.ROCR(self.df[col].values, timeperiod=period)
    
    def rocr100(self, period: int = 10, col: str = 'close') -> pd.Series:
        """变化率比率 100 (ROCR100)"""
        return talib.ROCR100(self.df[col].values, timeperiod=period)
    
    def rsi(self, period: int = 14, col: str = 'close') -> pd.Series:
        """相对强弱指标 (RSI)"""
        return talib.RSI(self.df[col].values, timeperiod=period)
    
    def stoch(self, fastk_period: int = 5, slowk_period: int = 3, slowk_matype: int = 0,
              slowd_period: int = 3, slowd_matype: int = 0) -> Tuple[pd.Series, pd.Series]:
        """随机指标 (Stochastic)"""
        slowk, slowd = talib.STOCH(
            self.df['high'].values, self.df['low'].values, self.df['close'].values,
            fastk_period=fastk_period, slowk_period=slowk_period, slowk_matype=slowk_matype,
            slowd_period=slowd_period, slowd_matype=slowd_matype
        )
        return slowk, slowd
    
    def stochf(self, fastk_period: int = 5, fastd_period: int = 3, fastd_matype: int = 0) -> Tuple[pd.Series, pd.Series]:
        """快速随机指标 (Stochastic Fast)"""
        fastk, fastd = talib.STOCHF(
            self.df['high'].values, self.df['low'].values, self.df['close'].values,
            fastk_period=fastk_period, fastd_period=fastd_period, fastd_matype=fastd_matype
        )
        return fastk, fastd
    
    def stochrsi(self, period: int = 14, fastk_period: int = 5, fastd_period: int = 3,
                 fastd_matype: int = 0, col: str = 'close') -> Tuple[pd.Series, pd.Series]:
        """随机 RSI (StochRSI)"""
        fastk, fastd = talib.STOCHRSI(
            self.df[col].values, timeperiod=period,
            fastk_period=fastk_period, fastd_period=fastd_period, fastd_matype=fastd_matype
        )
        return fastk, fastd
    
    def trix(self, period: int = 30, col: str = 'close') -> pd.Series:
        """1 日变化率的三重指数平滑 (TRIX)"""
        return talib.TRIX(self.df[col].values, timeperiod=period)
    
    def ultosc(self, timeperiod1: int = 7, timeperiod2: int = 14, timeperiod3: int = 28) -> pd.Series:
        """终极振荡器 (Ultimate Oscillator)"""
        return talib.ULTOSC(
            self.df['high'].values, self.df['low'].values, self.df['close'].values,
            timeperiod1=timeperiod1, timeperiod2=timeperiod2, timeperiod3=timeperiod3
        )
    
    def willr(self, period: int = 14) -> pd.Series:
        """威廉指标 (Williams %R)"""
        return talib.WILLR(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
    
    # ========== 波动率指标 (Volatility Indicators) ==========
    
    def atr(self, period: int = 14) -> pd.Series:
        """平均真实波动幅度 (ATR)"""
        return talib.ATR(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
    
    def natr(self, period: int = 14) -> pd.Series:
        """归一化平均真实波动幅度 (NATR)"""
        return talib.NATR(self.df['high'].values, self.df['low'].values, self.df['close'].values, timeperiod=period)
    
    def bbands(self, period: int = 20, nbdevup: float = 2.0, nbdevdn: float = 2.0, matype: int = 0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """布林带 (Bollinger Bands)"""
        upper, middle, lower = talib.BBANDS(
            self.df['close'].values,
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=matype
        )
        return upper, middle, lower
    
    def stddev(self, period: int = 5, col: str = 'close', nbdev: float = 1.0) -> pd.Series:
        """标准差 (Standard Deviation)"""
        return talib.STDDEV(self.df[col].values, timeperiod=period, nbdev=nbdev)
    
    def trange(self) -> pd.Series:
        """真实波动幅度 (True Range)"""
        return talib.TRANGE(self.df['high'].values, self.df['low'].values, self.df['close'].values)
    
    # ========== 成交量指标 (Volume Indicators) ==========
    
    def ad(self) -> pd.Series:
        """累积/派发线 (Accumulation/Distribution Line)"""
        return talib.AD(
            self.df['high'].values.astype(np.double),
            self.df['low'].values.astype(np.double),
            self.df['close'].values.astype(np.double),
            self.df['volume'].values.astype(np.double)
        )
    
    def adosc(self, fastperiod: int = 3, slowperiod: int = 10) -> pd.Series:
        """累积/派发线振荡器 (AD Oscillator)"""
        return talib.ADOSC(
            self.df['high'].values.astype(np.double),
            self.df['low'].values.astype(np.double),
            self.df['close'].values.astype(np.double),
            self.df['volume'].values.astype(np.double),
            fastperiod=fastperiod, slowperiod=slowperiod
        )
    
    def obv(self, col: str = 'close') -> pd.Series:
        """能量潮 (On Balance Volume)"""
        return talib.OBV(
            self.df[col].values.astype(np.double),
            self.df['volume'].values.astype(np.double)
        )
    
    def mfi(self, period: int = 14) -> pd.Series:
        """资金流量指标 (Money Flow Index)"""
        return talib.MFI(
            self.df['high'].values.astype(np.double),
            self.df['low'].values.astype(np.double),
            self.df['close'].values.astype(np.double),
            self.df['volume'].values.astype(np.double),
            timeperiod=period
        )
    
    def vwap(self) -> pd.Series:
        """成交量加权平均价 (VWAP) - 需要计算"""
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        return (typical_price * self.df['volume']).cumsum() / self.df['volume'].cumsum()
    
    # ========== 价格转换指标 (Price Transform) ==========
    
    def avgprice(self) -> pd.Series:
        """平均价格 (Average Price)"""
        return talib.AVGPRICE(self.df['open'].values, self.df['high'].values,
                              self.df['low'].values, self.df['close'].values)
    
    def medprice(self) -> pd.Series:
        """中价 (Median Price)"""
        return talib.MEDPRICE(self.df['high'].values, self.df['low'].values)
    
    def typprice(self) -> pd.Series:
        """典型价格 (Typical Price)"""
        return talib.TYPPRICE(self.df['high'].values, self.df['low'].values, self.df['close'].values)
    
    def wclprice(self) -> pd.Series:
        """加权收盘价 (Weighted Close Price)"""
        return talib.WCLPRICE(self.df['high'].values, self.df['low'].values, self.df['close'].values)
    
    # ========== 周期指标 (Cycle Indicators) ==========
    
    def ht_dcperiod(self, col: str = 'close') -> pd.Series:
        """希尔伯特变换 - 主导周期 (Hilbert Transform - Dominant Cycle Period)"""
        return talib.HT_DCPERIOD(self.df[col].values)
    
    def ht_dcphase(self, col: str = 'close') -> pd.Series:
        """希尔伯特变换 - 主导周期相位 (Hilbert Transform - Dominant Cycle Phase)"""
        return talib.HT_DCPHASE(self.df[col].values)
    
    def ht_phasor(self, col: str = 'close') -> Tuple[pd.Series, pd.Series]:
        """希尔伯特变换 - 相位成分 (Hilbert Transform - Phasor Components)"""
        inphase, quadrature = talib.HT_PHASOR(self.df[col].values)
        return inphase, quadrature
    
    def ht_sine(self, col: str = 'close') -> Tuple[pd.Series, pd.Series]:
        """希尔伯特变换 - 正弦波 (Hilbert Transform - SineWave)"""
        sine, leadsine = talib.HT_SINE(self.df[col].values)
        return sine, leadsine
    
    def ht_trendline(self, col: str = 'close') -> pd.Series:
        """希尔伯特变换 - 瞬时趋势线 (Hilbert Transform - Instantaneous Trendline)"""
        return talib.HT_TRENDLINE(self.df[col].values)
    
    def ht_trendmode(self, col: str = 'close') -> pd.Series:
        """希尔伯特变换 - 趋势 vs 周期模式 (Hilbert Transform - Trend vs Cycle Mode)"""
        return talib.HT_TRENDMODE(self.df[col].values)
    
    # ========== 统计指标 (Statistics) ==========
    
    def beta(self, period: int = 5) -> pd.Series:
        """贝塔系数 (Beta)"""
        return talib.BETA(self.df['high'].values, self.df['low'].values, timeperiod=period)
    
    def correl(self, period: int = 30) -> pd.Series:
        """皮尔逊相关系数 (Pearson's Correlation Coefficient)"""
        return talib.CORREL(self.df['high'].values, self.df['low'].values, timeperiod=period)
    
    def linearreg(self, period: int = 14, col: str = 'close') -> pd.Series:
        """线性回归 (Linear Regression)"""
        return talib.LINEARREG(self.df[col].values, timeperiod=period)
    
    def linearreg_angle(self, period: int = 14, col: str = 'close') -> pd.Series:
        """线性回归角度 (Linear Regression Angle)"""
        return talib.LINEARREG_ANGLE(self.df[col].values, timeperiod=period)
    
    def linearreg_intercept(self, period: int = 14, col: str = 'close') -> pd.Series:
        """线性回归截距 (Linear Regression Intercept)"""
        return talib.LINEARREG_INTERCEPT(self.df[col].values, timeperiod=period)
    
    def linearreg_slope(self, period: int = 14, col: str = 'close') -> pd.Series:
        """线性回归斜率 (Linear Regression Slope)"""
        return talib.LINEARREG_SLOPE(self.df[col].values, timeperiod=period)
    
    def slope(self, period: int = 14, col: str = 'close') -> pd.Series:
        """斜率 (Slope)"""
        return talib.SLOPE(self.df[col].values, timeperiod=period)
    
    def tsf(self, period: int = 14, col: str = 'close') -> pd.Series:
        """时间序列预测 (Time Series Forecast)"""
        return talib.TSF(self.df[col].values, timeperiod=period)
    
    def var(self, period: int = 5, col: str = 'close', nbdev: float = 1.0) -> pd.Series:
        """方差 (Variance)"""
        return talib.VAR(self.df[col].values, timeperiod=period, nbdev=nbdev)
    
    # ========== K 线形态识别 (Pattern Recognition) ==========
    
    def cdl_pattern(self, pattern_name: str) -> pd.Series:
        """
        通用 K 线形态识别函数
        
        Args:
            pattern_name: 形态名称 (如 'CDLDOJI', 'CDLENGULFING' 等)
        
        Returns:
            pd.Series: 形态识别结果 (+100 看涨，-100 看跌，0 无)
        """
        pattern_func = getattr(talib, pattern_name, None)
        if pattern_func is None:
            raise ValueError(f"未知的 K 线形态：{pattern_name}")
        
        return pattern_func(
            self.df['open'].values,
            self.df['high'].values,
            self.df['low'].values,
            self.df['close'].values
        )
    
    def cdl_doji(self) -> pd.Series:
        """十字星 (Doji)"""
        return talib.CDLDOJI(self.df['open'].values, self.df['high'].values,
                            self.df['low'].values, self.df['close'].values)
    
    def cdl_engulfing(self) -> pd.Series:
        """吞没形态 (Engulfing Pattern)"""
        return talib.CDLENGULFING(self.df['open'].values, self.df['high'].values,
                                  self.df['low'].values, self.df['close'].values)
    
    def cdl_hammer(self) -> pd.Series:
        """锤子线 (Hammer)"""
        return talib.CDLHAMMER(self.df['open'].values, self.df['high'].values,
                               self.df['low'].values, self.df['close'].values)
    
    def cdl_hanging(self) -> pd.Series:
        """上吊线 (Hanging Man)"""
        return talib.CDLHANGINGMAN(self.df['open'].values, self.df['high'].values,
                                   self.df['low'].values, self.df['close'].values)
    
    def cdl_morning(self) -> pd.Series:
        """晨星 (Morning Star)"""
        return talib.CDLMORNINGSTAR(self.df['open'].values, self.df['high'].values,
                                    self.df['low'].values, self.df['close'].values)
    
    def cdl_evening(self) -> pd.Series:
        """暮星 (Evening Star)"""
        return talib.CDLEVENINGSTAR(self.df['open'].values, self.df['high'].values,
                                    self.df['low'].values, self.df['close'].values)
    
    def cdl_shooting(self) -> pd.Series:
        """流星线 (Shooting Star)"""
        return talib.CDLSHOOTINGSTAR(self.df['open'].values, self.df['high'].values,
                                     self.df['low'].values, self.df['close'].values)
    
    def cdl_3soldiers(self) -> pd.Series:
        """三个白兵 (Three White Soldiers)"""
        return talib.CDL3WHITESOLDIERS(self.df['open'].values, self.df['high'].values,
                                       self.df['low'].values, self.df['close'].values)
    
    def cdl_3crows(self) -> pd.Series:
        """三只乌鸦 (Three Black Crows)"""
        return talib.CDL3BLACKCROWS(self.df['open'].values, self.df['high'].values,
                                    self.df['low'].values, self.df['close'].values)
    
    def cdl_harami(self) -> pd.Series:
        """孕线 (Harami Pattern)"""
        return talib.CDLHARAMI(self.df['open'].values, self.df['high'].values,
                               self.df['low'].values, self.df['close'].values)
    
    # ========== 数学运算 (Math Operators) ==========
    
    def add(self, real: pd.Series = None, period: int = None) -> pd.Series:
        """向量算术加 (Vector Arithmetic Add)"""
        if real is not None:
            return talib.ADD(self.df['close'].values, real.values)
        return talib.SUM(self.df['close'].values, timeperiod=period)
    
    def sub(self, real: pd.Series = None) -> pd.Series:
        """向量算术减 (Vector Arithmetic Sub)"""
        if real is not None:
            return talib.SUB(self.df['close'].values, real.values)
        return self.df['close'].diff()
    
    def mult(self, real: pd.Series = None) -> pd.Series:
        """向量算术乘 (Vector Arithmetic Mult)"""
        if real is not None:
            return talib.MULT(self.df['close'].values, real.values)
        return self.df['close'].cumprod()
    
    def div(self, real: pd.Series = None) -> pd.Series:
        """向量算术除 (Vector Arithmetic Div)"""
        if real is not None:
            return talib.DIV(self.df['close'].values, real.values)
        return self.df['close'].pct_change()
    
    def max(self, period: int = 30, col: str = 'close') -> pd.Series:
        """最大值 (Highest value over a specified period)"""
        return talib.MAX(self.df[col].values, timeperiod=period)
    
    def min(self, period: int = 30, col: str = 'close') -> pd.Series:
        """最小值 (Lowest value over a specified period)"""
        return talib.MIN(self.df[col].values, timeperiod=period)
    
    def maxindex(self, period: int = 30, col: str = 'close') -> pd.Series:
        """最大值索引 (Index of highest value over a specified period)"""
        return talib.MAXINDEX(self.df[col].values, timeperiod=period)
    
    def minindex(self, period: int = 30, col: str = 'close') -> pd.Series:
        """最小值索引 (Index of lowest value over a specified period)"""
        return talib.MININDEX(self.df[col].values, timeperiod=period)
    
    def sum(self, period: int = 30, col: str = 'close') -> pd.Series:
        """求和 (Summation)"""
        return talib.SUM(self.df[col].values, timeperiod=period)


# ==================== 指标组合策略 ====================

class IndicatorStrategies:
    """指标组合策略类"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.indicators = TALibIndicators(df)
    
    def dual_ma_strategy(self, short_period: int = 5, long_period: int = 20) -> pd.DataFrame:
        """
        双均线策略
        
        Returns:
            DataFrame 添加信号列
        """
        df = self.df.copy()
        df['ma_short'] = self.indicators.sma(short_period)
        df['ma_long'] = self.indicators.sma(long_period)
        
        # 金叉：短期均线上穿长期均线
        df['golden_cross'] = (df['ma_short'] > df['ma_long']) & \
                            (df['ma_short'].shift(1) <= df['ma_long'].shift(1))
        
        # 死叉：短期均线下穿长期均线
        df['death_cross'] = (df['ma_short'] < df['ma_long']) & \
                           (df['ma_short'].shift(1) >= df['ma_long'].shift(1))
        
        # 交易信号：1=买入，-1=卖出，0=持有
        df['signal'] = 0
        df.loc[df['golden_cross'], 'signal'] = 1
        df.loc[df['death_cross'], 'signal'] = -1
        
        return df
    
    def macd_rsi_strategy(self, rsi_period: int = 14, rsi_overbought: int = 70,
                          rsi_oversold: int = 30) -> pd.DataFrame:
        """
        MACD + RSI 组合策略
        
        Returns:
            DataFrame 添加信号列
        """
        df = self.df.copy()
        
        # MACD
        macd_line, signal_line, histogram = self.indicators.macd()
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_hist'] = histogram
        
        # RSI
        df['rsi'] = self.indicators.rsi(rsi_period)
        
        # 买入信号：MACD 金叉 + RSI 超卖
        df['buy_signal'] = (
            (df['macd'] > df['macd_signal']) &
            (df['macd'].shift(1) <= df['macd_signal'].shift(1)) &
            (df['rsi'] < rsi_oversold)
        )
        
        # 卖出信号：MACD 死叉 + RSI 超买
        df['sell_signal'] = (
            (df['macd'] < df['macd_signal']) &
            (df['macd'].shift(1) >= df['macd_signal'].shift(1)) &
            (df['rsi'] > rsi_overbought)
        )
        
        return df
    
    def bollinger_rsi_strategy(self, bb_period: int = 20, bb_std: float = 2.0,
                                rsi_period: int = 14) -> pd.DataFrame:
        """
        布林带 + RSI 组合策略
        
        Returns:
            DataFrame 添加信号列
        """
        df = self.df.copy()
        
        # 布林带
        upper, middle, lower = self.indicators.bbands(bb_period, bb_std)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        
        # RSI
        df['rsi'] = self.indicators.rsi(rsi_period)
        
        # 买入信号：价格触及下轨 + RSI 超卖
        df['buy_signal'] = (
            (df['close'] <= df['bb_lower']) &
            (df['rsi'] < 30)
        )
        
        # 卖出信号：价格触及上轨 + RSI 超买
        df['sell_signal'] = (
            (df['close'] >= df['bb_upper']) &
            (df['rsi'] > 70)
        )
        
        return df
    
    def triple_screen_strategy(self, ema_period: int = 13, macd_fast: int = 12,
                               macd_slow: int = 26, rsi_period: int = 14) -> pd.DataFrame:
        """
        三重滤网交易系统 (Triple Screen Trading System)
        
        第一重：趋势过滤 (EMA)
        第二重：动量指标 (MACD)
        第三重：入场时机 (RSI)
        
        Returns:
            DataFrame 添加信号列
        """
        df = self.df.copy()
        
        # 第一重：趋势
        df['ema'] = self.indicators.ema(ema_period)
        df['trend_up'] = df['close'] > df['ema']
        
        # 第二重：动量
        macd_line, signal_line, histogram = self.indicators.macd(macd_fast, macd_slow)
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_hist'] = histogram
        df['momentum_up'] = histogram > 0
        
        # 第三重：入场
        df['rsi'] = self.indicators.rsi(rsi_period)
        
        # 买入：上涨趋势 + 上涨动量 + RSI 从超卖区反弹
        df['buy_signal'] = (
            df['trend_up'] &
            df['momentum_up'] &
            (df['rsi'] < 40) &
            (df['rsi'].shift(1) < df['rsi'])
        )
        
        # 卖出：下跌趋势 + 下跌动量 + RSI 从超买区回落
        df['sell_signal'] = (
            (~df['trend_up']) &
            (~df['momentum_up']) &
            (df['rsi'] > 60) &
            (df['rsi'].shift(1) > df['rsi'])
        )
        
        return df


# ==================== 背离检测 ====================

class DivergenceDetector:
    """指标背离检测器"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.indicators = TALibIndicators(df)
    
    def detect_divergence(self, indicator: str = 'rsi', period: int = 14,
                         lookback: int = 5) -> Dict[str, pd.Series]:
        """
        检测指标背离
        
        Args:
            indicator: 指标名称 ('rsi', 'macd', 'stoch')
            period: 指标周期
            lookback: 回溯周期
        
        Returns:
            Dict 包含看涨背离和看跌背离信号
        """
        df = self.df.copy()
        
        # 获取指标值
        if indicator == 'rsi':
            indicator_values = self.indicators.rsi(period)
        elif indicator == 'macd':
            indicator_values = self.indicators.macd()[2]  # 使用 MACD 柱状图
        elif indicator == 'stoch':
            indicator_values = self.indicators.stoch()[0]  # 使用 %K
        else:
            raise ValueError(f"不支持的指标：{indicator}")
        
        df['indicator'] = indicator_values
        
        # 检测价格高低点
        df['price_high'] = df['high'].rolling(lookback).max()
        df['price_low'] = df['low'].rolling(lookback).min()
        
        # 检测指标高低点
        df['indicator_high'] = df['indicator'].rolling(lookback).max()
        df['indicator_low'] = df['indicator'].rolling(lookback).min()
        
        # 看涨背离：价格创新低，指标未创新低
        df['bullish_div'] = (
            (df['low'] == df['price_low']) &
            (df['indicator'] > df['indicator_low'].shift(1))
        )
        
        # 看跌背离：价格创新高，指标未创新高
        df['bearish_div'] = (
            (df['high'] == df['price_high']) &
            (df['indicator'] < df['indicator_high'].shift(1))
        )
        
        return {
            'bullish_divergence': df['bullish_div'],
            'bearish_divergence': df['bearish_div']
        }
    
    def hidden_divergence(self, indicator: str = 'rsi', period: int = 14,
                         lookback: int = 5) -> Dict[str, pd.Series]:
        """
        检测隐藏背离 (趋势延续信号)
        
        隐藏看涨背离：价格未创新低，指标创新低
        隐藏看跌背离：价格未创新高，指标创新高
        
        Returns:
            Dict 包含隐藏背离信号
        """
        df = self.df.copy()
        
        # 获取指标值
        if indicator == 'rsi':
            indicator_values = self.indicators.rsi(period)
        elif indicator == 'macd':
            indicator_values = self.indicators.macd()[2]
        else:
            indicator_values = self.indicators.rsi(period)
        
        df['indicator'] = indicator_values
        
        # 价格趋势
        df['price_trend'] = df['close'].diff()
        
        # 隐藏看涨背离：价格 higher low，指标 lower low
        df['hidden_bullish'] = (
            (df['low'] > df['low'].shift(lookback)) &
            (df['indicator'] < df['indicator'].shift(lookback)) &
            (df['price_trend'] > 0)
        )
        
        # 隐藏看跌背离：价格 lower high，指标 higher high
        df['hidden_bearish'] = (
            (df['high'] < df['high'].shift(lookback)) &
            (df['indicator'] > df['indicator'].shift(lookback)) &
            (df['price_trend'] < 0)
        )
        
        return {
            'hidden_bullish_divergence': df['hidden_bullish'],
            'hidden_bearish_divergence': df['hidden_bearish']
        }


# ==================== 金叉/死叉检测 ====================

class CrossDetector:
    """金叉/死叉检测器"""
    
    @staticmethod
    def golden_cross(fast_series: Union[pd.Series, np.ndarray], slow_series: Union[pd.Series, np.ndarray]) -> np.ndarray:
        """
        检测金叉 (快线上穿慢线)
        
        Args:
            fast_series: 快线
            slow_series: 慢线
        
        Returns:
            np.ndarray: 金叉信号 (True/False)
        """
        fast = pd.Series(fast_series) if isinstance(fast_series, np.ndarray) else fast_series
        slow = pd.Series(slow_series) if isinstance(slow_series, np.ndarray) else slow_series
        return ((fast > slow) & (fast.shift(1) <= slow.shift(1))).values
    
    @staticmethod
    def death_cross(fast_series: Union[pd.Series, np.ndarray], slow_series: Union[pd.Series, np.ndarray]) -> np.ndarray:
        """
        检测死叉 (快线下穿慢线)
        
        Args:
            fast_series: 快线
            slow_series: 慢线
        
        Returns:
            np.ndarray: 死叉信号 (True/False)
        """
        fast = pd.Series(fast_series) if isinstance(fast_series, np.ndarray) else fast_series
        slow = pd.Series(slow_series) if isinstance(slow_series, np.ndarray) else slow_series
        return ((fast < slow) & (fast.shift(1) >= slow.shift(1))).values
    
    @staticmethod
    def cross_above(series: Union[pd.Series, np.ndarray], level: float) -> np.ndarray:
        """检测上穿某水平"""
        s = pd.Series(series) if isinstance(series, np.ndarray) else series
        return ((s > level) & (s.shift(1) <= level)).values
    
    @staticmethod
    def cross_below(series: Union[pd.Series, np.ndarray], level: float) -> np.ndarray:
        """检测下穿某水平"""
        s = pd.Series(series) if isinstance(series, np.ndarray) else series
        return ((s < level) & (s.shift(1) >= level)).values


# ==================== 便捷函数 ====================

def compute_indicator(df: pd.DataFrame, indicator_name: str, **kwargs) -> Union[pd.Series, Tuple]:
    """
    便捷函数：计算单个指标
    
    Args:
        df: DataFrame
        indicator_name: 指标名称
        **kwargs: 指标参数
    
    Returns:
        指标计算结果
    """
    ind = TALibIndicators(df)
    indicator_func = getattr(ind, indicator_name, None)
    
    if indicator_func is None:
        raise ValueError(f"未知的指标：{indicator_name}")
    
    return indicator_func(**kwargs)


def apply_indicators(df: pd.DataFrame, indicator_list: List[str], **kwargs) -> pd.DataFrame:
    """
    便捷函数：批量应用多个指标
    
    Args:
        df: DataFrame
        indicator_list: 指标名称列表
        **kwargs: 指标参数
    
    Returns:
        DataFrame 添加指标列
    """
    result = df.copy()
    ind = TALibIndicators(df)
    
    for indicator_name in indicator_list:
        indicator_func = getattr(ind, indicator_name, None)
        if indicator_func:
            indicator_result = indicator_func(**kwargs)
            
            # 处理多返回值
            if isinstance(indicator_result, tuple):
                for i, series in enumerate(indicator_result):
                    result[f'{indicator_name}_{i}'] = series
            else:
                result[indicator_name] = indicator_result
    
    return result


def get_all_indicators_info() -> Dict[str, List[str]]:
    """
    获取所有支持指标的信息
    
    Returns:
        Dict 包含各类指标列表
    """
    return {
        'overlap': OVERLAP_INDICATORS,
        'momentum': MOMENTUM_INDICATORS,
        'volatility': VOLATILITY_INDICATORS,
        'volume': VOLUME_INDICATORS,
        'pattern': PATTERN_INDICATORS,
        'price_transform': PRICE_TRANSFORM_INDICATORS,
        'cycle': CYCLE_INDICATORS,
        'statistics': STATISTIC_INDICATORS,
        'math_transform': MATH_TRANSFORM_INDICATORS,
        'math_operator': MATH_OPERATOR_INDICATORS,
        'all': ALL_INDICATORS
    }


# ==================== 测试代码 ====================

if __name__ == '__main__':
    print("=" * 80)
    print("BobQuant TA-Lib 高级指标库 v3.0 - 测试")
    print("=" * 80)
    
    # 生成测试数据
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2024-01-01', periods=n, freq='D')
    
    test_df = pd.DataFrame({
        'open': np.random.randn(n).cumsum() + 100,
        'high': np.random.randn(n).cumsum() + 102,
        'low': np.random.randn(n).cumsum() + 98,
        'close': np.random.randn(n).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, n)
    }, index=dates)
    
    # 测试核心指标
    print("\n【测试 10 个核心指标】")
    print("-" * 80)
    
    ind = TALibIndicators(test_df)
    
    core_indicators = [
        ('SMA(20)', lambda: ind.sma(20)),
        ('EMA(20)', lambda: ind.ema(20)),
        ('MACD', lambda: ind.macd()),
        ('RSI(14)', lambda: ind.rsi(14)),
        ('KDJ', lambda: ind.stoch()),
        ('布林带', lambda: ind.bbands(20)),
        ('ATR(14)', lambda: ind.atr(14)),
        ('CCI(20)', lambda: ind.cci(20)),
        ('威廉指标', lambda: ind.willr(14)),
        ('资金流量', lambda: ind.mfi(14))
    ]
    
    results = {}
    for name, func in core_indicators:
        try:
            result = func()
            if isinstance(result, tuple):
                results[name] = [len(r) for r in result]
                print(f"✅ {name}: {len(result)} 个序列，长度 {[len(r) for r in result]}")
            else:
                results[name] = len(result)
                print(f"✅ {name}: 长度 {len(result)}")
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    # 测试策略
    print("\n【测试指标组合策略】")
    print("-" * 80)
    
    strategies = IndicatorStrategies(test_df)
    
    # 双均线策略
    df_ma = strategies.dual_ma_strategy()
    golden_count = df_ma['golden_cross'].sum()
    death_count = df_ma['death_cross'].sum()
    print(f"✅ 双均线策略：金叉 {golden_count} 次，死叉 {death_count} 次")
    
    # MACD+RSI 策略
    df_macd_rsi = strategies.macd_rsi_strategy()
    buy_count = df_macd_rsi['buy_signal'].sum()
    sell_count = df_macd_rsi['sell_signal'].sum()
    print(f"✅ MACD+RSI 策略：买入 {buy_count} 次，卖出 {sell_count} 次")
    
    # 测试背离检测
    print("\n【测试背离检测】")
    print("-" * 80)
    
    detector = DivergenceDetector(test_df)
    div_signals = detector.detect_divergence('rsi', 14, 5)
    bullish_count = div_signals['bullish_divergence'].sum()
    bearish_count = div_signals['bearish_divergence'].sum()
    print(f"✅ RSI 背离：看涨 {bullish_count} 次，看跌 {bearish_count} 次")
    
    # 测试金叉死叉
    print("\n【测试金叉/死叉检测】")
    print("-" * 80)
    
    sma5 = ind.sma(5)
    sma20 = ind.sma(20)
    golden = CrossDetector.golden_cross(sma5, sma20)
    death = CrossDetector.death_cross(sma5, sma20)
    print(f"✅ SMA(5/20) 金叉：{golden.sum()} 次，死叉：{death.sum()} 次")
    
    # 获取所有指标信息
    print("\n【支持的指标列表】")
    print("-" * 80)
    
    info = get_all_indicators_info()
    total_count = sum(len(v) for k, v in info.items() if k != 'all')
    print(f"总指标数：{total_count}+")
    
    for category, indicators in info.items():
        if category != 'all':
            print(f"\n{category.upper()}: {len(indicators)} 个")
            print(f"  {', '.join(indicators[:5])}{'...' if len(indicators) > 5 else ''}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
