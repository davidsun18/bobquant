"""
P2 高级因子库
在P0+P1基础上的增强因子，用于精细化筛选和风险控制
逻辑顺序：P0(基础) → P1(增强) → P2(精细化)
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List


class AdvancedFactors:
    """
    P2高级因子
    包括：趋势强度、波动率、资金流向、技术形态
    """
    
    # ===== 1. 趋势强度因子 =====
    
    @staticmethod
    def trend_strength(df: pd.DataFrame) -> pd.DataFrame:
        """
        趋势强度因子 (P2)
        
        计算价格趋势的稳定性和强度
        """
        if len(df) < 20:
            return df
        
        # ADX - 平均趋向指数 (衡量趋势强度)
        df['adx'] = AdvancedFactors._calculate_adx(df)
        
        # 趋势一致性：收盘价在均线同侧的比例
        df['trend_consistency'] = AdvancedFactors._trend_consistency(df)
        
        # 趋势持续性：连续上涨/下跌天数
        df['consecutive_up'] = AdvancedFactors._consecutive_days(df, direction='up')
        df['consecutive_down'] = AdvancedFactors._consecutive_days(df, direction='down')
        
        # 趋势评分 (0-100)
        df['trend_score'] = (
            (df['adx'] / 100 * 40) +  # ADX占40%
            (df['trend_consistency'] * 40) +  # 一致性占40%
            (np.where(df['consecutive_up'] > 3, 20, 0)) +  # 连续上涨加分
            (np.where(df['consecutive_down'] > 3, -20, 0))  # 连续下跌扣分
        ).clip(0, 100)
        
        return df
    
    @staticmethod
    def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算ADX指标"""
        # +DM和-DM
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # ATR
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        # +DI和-DI
        plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=period).mean() / atr
        
        # DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx.fillna(0)
    
    @staticmethod
    def _trend_consistency(df: pd.DataFrame, period: int = 10) -> pd.Series:
        """计算趋势一致性 (价格在MA同侧的比例)"""
        ma20 = df['close'].rolling(window=20).mean()
        above_ma = (df['close'] > ma20).astype(int)
        consistency = above_ma.rolling(window=period).mean()
        return consistency * 100  # 转换为百分比
    
    @staticmethod
    def _consecutive_days(df: pd.DataFrame, direction: str = 'up') -> pd.Series:
        """计算连续上涨/下跌天数"""
        if direction == 'up':
            condition = df['close'] > df['close'].shift(1)
        else:
            condition = df['close'] < df['close'].shift(1)
        
        # 使用cumsum技巧计算连续天数
        groups = (condition != condition.shift()).cumsum()
        consecutive = condition.groupby(groups).cumsum()
        return consecutive.where(condition, 0)
    
    # ===== 2. 波动率因子 =====
    
    @staticmethod
    def volatility_factors(df: pd.DataFrame) -> pd.DataFrame:
        """
        波动率因子 (P2)
        
        用于风险控制和仓位管理
        """
        if len(df) < 20:
            return df
        
        # 历史波动率 (年化)
        df['volatility_20'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(252) * 100
        
        # 波动率变化
        df['volatility_change'] = df['volatility_20'].pct_change(5)
        
        # 波动率状态
        vol_mean = df['volatility_20'].rolling(window=60).mean()
        df['volatility_state'] = 'normal'
        df.loc[df['volatility_20'] < vol_mean * 0.8, 'volatility_state'] = 'low'
        df.loc[df['volatility_20'] > vol_mean * 1.2, 'volatility_state'] = 'high'
        
        # 波动率收缩/扩张
        df['volatility_squeeze'] = df['volatility_20'] < vol_mean * 0.7
        df['volatility_expansion'] = df['volatility_20'] > vol_mean * 1.3
        
        # 振幅因子
        df['amplitude'] = ((df['high'] - df['low']) / df['close']) * 100
        df['amplitude_ma'] = df['amplitude'].rolling(window=20).mean()
        
        return df
    
    # ===== 3. 资金流向因子 =====
    
    @staticmethod
    def money_flow(df: pd.DataFrame) -> pd.DataFrame:
        """
        资金流向因子 (P2)
        
        基于价格和成交量计算资金流入流出
        """
        if len(df) < 5:
            return df
        
        # 典型价格
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # 资金流 (Money Flow)
        money_flow = typical_price * df['volume']
        
        # 资金流方向 (基于价格变化)
        price_change = df['close'].diff()
        positive_flow = money_flow.where(price_change > 0, 0)
        negative_flow = money_flow.where(price_change < 0, 0)
        
        # 资金流比率 (MFR)
        period = 14
        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()
        
        df['mfi'] = 100 - (100 / (1 + positive_sum / negative_sum.replace(0, np.nan)))
        df['mfi'] = df['mfi'].fillna(50)
        
        # 资金流强度
        df['money_flow_strength'] = (positive_sum - negative_sum) / (positive_sum + negative_sum).replace(0, np.nan)
        df['money_flow_strength'] = df['money_flow_strength'].fillna(0)
        
        # 大单资金估算 (基于成交量和价格变动)
        df['large_order_estimate'] = df['volume'] * df['close'] * (price_change / df['close'].shift(1)).abs()
        df['large_order_ma'] = df['large_order_estimate'].rolling(window=5).mean()
        
        # 资金流入信号
        df['money_inflow'] = df['mfi'] < 20  # 超卖区资金流入
        df['money_outflow'] = df['mfi'] > 80  # 超买区资金流出
        
        return df
    
    # ===== 4. 技术形态因子 =====
    
    @staticmethod
    def pattern_recognition(df: pd.DataFrame) -> pd.DataFrame:
        """
        技术形态识别 (P2)
        
        自动识别常见K线形态
        """
        if len(df) < 5:
            return df
        
        # 锤子线 (Hammer)
        df['hammer'] = AdvancedFactors._is_hammer(df)
        
        # 吞没形态 (Engulfing)
        df['bullish_engulfing'] = AdvancedFactors._is_bullish_engulfing(df)
        df['bearish_engulfing'] = AdvancedFactors._is_bearish_engulfing(df)
        
        # 早晨之星/黄昏之星
        df['morning_star'] = AdvancedFactors._is_morning_star(df)
        df['evening_star'] = AdvancedFactors._is_evening_star(df)
        
        # 突破形态
        df['breakout_high'] = df['close'] > df['high'].rolling(window=20).max().shift(1)
        df['breakdown_low'] = df['close'] < df['low'].rolling(window=20).min().shift(1)
        
        # 形态综合评分
        df['pattern_score'] = (
            df['hammer'].astype(int) * 20 +
            df['bullish_engulfing'].astype(int) * 30 +
            df['bearish_engulfing'].astype(int) * (-30) +
            df['morning_star'].astype(int) * 40 +
            df['evening_star'].astype(int) * (-40) +
            df['breakout_high'].astype(int) * 25 +
            df['breakdown_low'].astype(int) * (-25)
        ).clip(-100, 100)
        
        return df
    
    @staticmethod
    def _is_hammer(df: pd.DataFrame) -> pd.Series:
        """识别锤子线"""
        body = abs(df['close'] - df['open'])
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        
        # 下影线长，上影线短，实体小
        return (lower_shadow > body * 2) & (upper_shadow < body) & (body < df['close'] * 0.02)
    
    @staticmethod
    def _is_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
        """识别看涨吞没"""
        prev_red = df['open'].shift(1) > df['close'].shift(1)
        curr_green = df['close'] > df['open']
        engulf = (df['open'] < df['close'].shift(1)) & (df['close'] > df['open'].shift(1))
        return prev_red & curr_green & engulf
    
    @staticmethod
    def _is_bearish_engulfing(df: pd.DataFrame) -> pd.Series:
        """识别看跌吞没"""
        prev_green = df['close'].shift(1) > df['open'].shift(1)
        curr_red = df['open'] > df['close']
        engulf = (df['open'] > df['close'].shift(1)) & (df['close'] < df['open'].shift(1))
        return prev_green & curr_red & engulf
    
    @staticmethod
    def _is_morning_star(df: pd.DataFrame) -> pd.Series:
        """识别早晨之星"""
        # 第一天大跌
        day1_red = df['open'].shift(2) > df['close'].shift(2)
        day1_large = (df['open'].shift(2) - df['close'].shift(2)) > df['close'].shift(2) * 0.02
        
        # 第二天小实体（十字星）
        day2_small = abs(df['close'].shift(1) - df['open'].shift(1)) < df['close'].shift(1) * 0.01
        
        # 第三天大涨
        day3_green = df['close'] > df['open']
        day3_large = (df['close'] - df['open']) > df['close'] * 0.02
        
        return day1_red & day1_large & day2_small & day3_green & day3_large
    
    @staticmethod
    def _is_evening_star(df: pd.DataFrame) -> pd.Series:
        """识别黄昏之星"""
        # 第一天大涨
        day1_green = df['close'].shift(2) > df['open'].shift(2)
        day1_large = (df['close'].shift(2) - df['open'].shift(2)) > df['close'].shift(2) * 0.02
        
        # 第二天小实体
        day2_small = abs(df['close'].shift(1) - df['open'].shift(1)) < df['close'].shift(1) * 0.01
        
        # 第三天大跌
        day3_red = df['open'] > df['close']
        day3_large = (df['open'] - df['close']) > df['close'] * 0.02
        
        return day1_green & day1_large & day2_small & day3_red & day3_large
    
    # ===== 5. 多时间周期因子 =====
    
    @staticmethod
    def multi_timeframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        多时间周期一致性 (P2)
        
        检查不同时间周期的趋势一致性
        """
        if len(df) < 60:
            return df
        
        # 短期趋势 (5日)
        df['trend_short'] = np.where(df['close'] > df['close'].shift(5), 1, -1)
        
        # 中期趋势 (20日)
        df['trend_mid'] = np.where(df['close'] > df['close'].shift(20), 1, -1)
        
        # 长期趋势 (60日)
        df['trend_long'] = np.where(df['close'] > df['close'].shift(60), 1, -1)
        
        # 趋势一致性得分
        df['timeframe_consistency'] = (df['trend_short'] + df['trend_mid'] + df['trend_long']) / 3
        
        # 多头排列/空头排列
        df['bullish_alignment'] = (df['close'] > df['close'].shift(5)) & \
                                   (df['close'].shift(5) > df['close'].shift(20)) & \
                                   (df['close'].shift(20) > df['close'].shift(60))
        
        df['bearish_alignment'] = (df['close'] < df['close'].shift(5)) & \
                                   (df['close'].shift(5) < df['close'].shift(20)) & \
                                   (df['close'].shift(20) < df['close'].shift(60))
        
        return df
    
    # ===== 6. 综合P2因子计算 =====
    
    @staticmethod
    def all_p2_factors(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有P2因子
        
        逻辑顺序：
        1. 趋势强度 (判断趋势质量)
        2. 波动率 (评估风险)
        3. 资金流向 (确认资金态度)
        4. 技术形态 (寻找入场点)
        5. 多时间周期 (确认大方向)
        """
        df = AdvancedFactors.trend_strength(df)
        df = AdvancedFactors.volatility_factors(df)
        df = AdvancedFactors.money_flow(df)
        df = AdvancedFactors.pattern_recognition(df)
        df = AdvancedFactors.multi_timeframe(df)
        
        return df
    
    @staticmethod
    def generate_p2_signals(df: pd.DataFrame) -> Dict:
        """
        生成P2级别信号
        
        在P0+P1基础上，增加P2的精细化判断
        """
        if len(df) < 2:
            return {}
        
        latest = df.iloc[-1]
        
        signals = {
            # 趋势强度
            'trend_strength': latest.get('trend_score', 50),
            'trend_quality': 'strong' if latest.get('trend_score', 0) > 70 else \
                           'weak' if latest.get('trend_score', 0) < 30 else 'normal',
            
            # 波动率
            'volatility': latest.get('volatility_20', 0),
            'vol_state': latest.get('volatility_state', 'normal'),
            'vol_squeeze': latest.get('volatility_squeeze', False),
            
            # 资金流向
            'mfi': latest.get('mfi', 50),
            'money_flow_strength': latest.get('money_flow_strength', 0),
            'money_inflow': latest.get('money_inflow', False),
            
            # 技术形态
            'pattern_score': latest.get('pattern_score', 0),
            'has_hammer': latest.get('hammer', False),
            'has_engulfing': latest.get('bullish_engulfing', False) or latest.get('bearish_engulfing', False),
            'has_star': latest.get('morning_star', False) or latest.get('evening_star', False),
            
            # 多时间周期
            'timeframe_consistency': latest.get('timeframe_consistency', 0),
            'bullish_alignment': latest.get('bullish_alignment', False),
            'bearish_alignment': latest.get('bearish_alignment', False),
        }
        
        # P2综合评分 (基于P1评分，增加P2调整)
        base_score = 50  # 假设P1给了50分
        
        # 趋势强度调整
        if signals['trend_quality'] == 'strong':
            base_score += 10
        elif signals['trend_quality'] == 'weak':
            base_score -= 10
        
        # 波动率调整
        if signals['vol_squeeze']:
            base_score += 5  # 波动率收缩，可能有大行情
        
        # 资金流向调整
        if signals['money_inflow']:
            base_score += 10
        
        # 技术形态调整
        if signals['pattern_score'] > 30:
            base_score += 10
        elif signals['pattern_score'] < -30:
            base_score -= 10
        
        # 多时间周期调整
        if signals['bullish_alignment']:
            base_score += 15
        elif signals['bearish_alignment']:
            base_score -= 15
        
        signals['p2_adjusted_score'] = max(0, min(100, base_score))
        
        return signals


# 模块级别的函数，方便直接导入
def generate_p2_signals(df: pd.DataFrame) -> Dict:
    """
    生成 P2 级别信号（模块级别函数）
    
    Args:
        df: 包含所有 P0+P1+P2 因子的 DataFrame
    
    Returns:
        P2 信号字典
    """
    return AdvancedFactors.generate_p2_signals(df)
