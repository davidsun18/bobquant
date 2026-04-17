# -*- coding: utf-8 -*-
"""
BobQuant 高频交易策略模块 v2.4

功能:
- 超短线剥头皮策略
- 动量交易策略
- 均值回归策略
- 突破交易策略
- 微趋势跟踪

v2.4 新增:
- 0.15% 触发做 T
- 1 个价位即可止盈
- 5 分钟最长持仓
- 动量 + 突破 + 均值回归
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

try:
    from ..indicator import technical as ta
except ImportError:
    from indicator import technical as ta


class ScalpingStrategy:
    """
    剥头皮策略 - 超短线交易
    
    核心思路:
    - 捕捉微小价格波动 (0.1%-0.3%)
    - 快速进出，持仓时间短 (1-5 分钟)
    - 高胜率，低盈亏比
    - 日内平仓，不留隔夜仓
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.threshold = config.get('scalping_threshold', 0.001)  # 0.1%
        self.max_holding_time = config.get('max_holding_time', 300)  # 5 分钟
        self.min_profit_tick = config.get('min_profit_tick', 1)  # 1 个价位
        self.entry_times: Dict[str, datetime] = {}  # 记录入场时间
    
    def check(self, code: str, quote: Dict, df: pd.DataFrame, pos: Optional[Dict]) -> Dict:
        """
        检查剥头皮机会
        
        Returns:
            {'signal': 'buy'/'sell'/None, 'reason': str, 'urgency': 'high'/'normal'}
        """
        if df is None or len(df) < 10:
            return {'signal': None}
        
        # 计算短期指标
        df = ta.macd(df, fast=3, slow=8, signal=3)
        df = ta.rsi(df, period=6)
        df = ta.bollinger(df, window=12, num_std=1.5)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        current_price = quote.get('current', latest['close'])
        
        # 1. 快速 MACD 金叉/死叉
        macd_golden = latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']
        macd_death = latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']
        
        # 2. RSI 极端值
        rsi_oversold = latest.get('rsi', 50) < 30
        rsi_overbought = latest.get('rsi', 50) > 70
        
        # 3. 布林带突破
        bb_lower = latest.get('bb_lower', current_price * 0.99)
        bb_upper = latest.get('bb_upper', current_price * 1.01)
        touch_lower = current_price <= bb_lower * 1.001
        touch_upper = current_price >= bb_upper * 0.999
        
        # 4. 价格动量
        if len(df) >= 5:
            momentum_5min = (current_price - df['close'].iloc[-5]) / df['close'].iloc[-5]
        else:
            momentum_5min = 0
        
        # 买入信号
        if not pos:
            if macd_golden or (rsi_oversold and touch_lower):
                if abs(momentum_5min) < self.threshold * 2:  # 避免追涨杀跌
                    return {
                        'signal': 'buy',
                        'reason': f'剥头皮买入 (MACD 金叉 + RSI={latest.get("rsi", 0):.0f})',
                        'urgency': 'high',
                        'target_profit': self.threshold * 2,
                        'stop_loss': -self.threshold
                    }
        
        # 卖出信号（有持仓时）
        if pos:
            # 检查持仓时间
            entry_time = self.entry_times.get(code)
            if entry_time:
                holding_time = (datetime.now() - entry_time).total_seconds()
                if holding_time > self.max_holding_time:
                    return {
                        'signal': 'sell',
                        'reason': f'时间止损 (持仓{holding_time/60:.0f}分钟)',
                        'urgency': 'high'
                    }
            
            # 盈利达到目标
            avg_cost = pos.get('avg_price', current_price)
            profit_pct = (current_price - avg_cost) / avg_cost
            
            if profit_pct >= self.threshold * 2:
                return {
                    'signal': 'sell',
                    'reason': f'剥头皮止盈 (+{profit_pct*100:.2f}%)',
                    'urgency': 'high'
                }
            
            # 止损
            if profit_pct <= -self.threshold:
                return {
                    'signal': 'sell',
                    'reason': f'剥头皮止损 ({profit_pct*100:.2f}%)',
                    'urgency': 'high'
                }
            
            # RSI 超买或 MACD 死叉
            if macd_death or rsi_overbought:
                if profit_pct > 0:
                    return {
                        'signal': 'sell',
                        'reason': f'剥头皮信号 (RSI={latest.get("rsi", 0):.0f})',
                        'urgency': 'normal'
                    }
        
        return {'signal': None}
    
    def on_trade(self, code: str, action: str):
        """记录交易"""
        if action == 'buy':
            self.entry_times[code] = datetime.now()
        elif action == 'sell':
            self.entry_times.pop(code, None)


class MomentumStrategy:
    """
    动量交易策略 - 追涨杀跌
    
    核心思路:
    - 捕捉短期强势股
    - 2 分钟内涨跌≥0.2% 触发
    - 顺势交易，快进快出
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.threshold = config.get('momentum_threshold', 0.002)  # 0.2%
        self.lookback_minutes = 2
    
    def check(self, code: str, quote: Dict, df: pd.DataFrame, pos: Optional[Dict]) -> Dict:
        """检查动量机会"""
        if df is None or len(df) < 5:
            return {'signal': None}
        
        current_price = quote.get('current', df['close'].iloc[-1])
        
        # 计算 2 分钟动量
        if len(df) >= 5:
            momentum = (current_price - df['close'].iloc[-5]) / df['close'].iloc[-5]
        else:
            return {'signal': None}
        
        # 成交量确认
        if 'volume' in df.columns:
            vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(5).mean().iloc[-1]
        else:
            vol_ratio = 1.0
        
        # 强势上涨（放量）
        if momentum >= self.threshold and vol_ratio >= 1.2:
            if not pos or pos.get('avg_price', current_price) < current_price * 0.995:
                return {
                    'signal': 'buy',
                    'reason': f'动量买入 (2 分钟 +{momentum*100:.2f}%, 量比{vol_ratio:.1f}x)',
                    'urgency': 'high',
                    'target_profit': self.threshold * 2,
                    'stop_loss': -self.threshold
                }
        
        # 弱势下跌（止损）
        if pos:
            avg_cost = pos.get('avg_price', current_price)
            profit_pct = (current_price - avg_cost) / avg_cost
            
            if momentum <= -self.threshold and profit_pct < -self.threshold * 0.5:
                return {
                    'signal': 'sell',
                    'reason': f'动量止损 (2 分钟 {momentum*100:.2f}%)',
                    'urgency': 'high'
                }
            
            # 动量反转止盈
            if profit_pct >= self.threshold * 1.5 and momentum < 0:
                return {
                    'signal': 'sell',
                    'reason': f'动量止盈 (+{profit_pct*100:.2f}%, 动量反转)',
                    'urgency': 'normal'
                }
        
        return {'signal': None}


class MeanReversionStrategy:
    """
    均值回归策略 - 高抛低吸
    
    核心思路:
    - 价格偏离均线 0.2% 时反向操作
    - 回归均值即平仓
    - 适合震荡市
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.threshold = config.get('reversion_threshold', 0.002)  # 0.2%
        self.ma_period = 20
    
    def check(self, code: str, quote: Dict, df: pd.DataFrame, pos: Optional[Dict]) -> Dict:
        """检查均值回归机会"""
        if df is None or len(df) < self.ma_period:
            return {'signal': None}
        
        current_price = quote.get('current', df['close'].iloc[-1])
        ma20 = df['close'].rolling(self.ma_period).mean().iloc[-1]
        
        # 计算偏离度
        deviation = (current_price - ma20) / ma20
        
        # 价格大幅低于均线（买入）
        if deviation <= -self.threshold:
            if not pos:
                return {
                    'signal': 'buy',
                    'reason': f'均值回归买入 (偏离-{deviation*100:.2f}%)',
                    'urgency': 'normal',
                    'target_profit': self.threshold,  # 回归均线
                    'stop_loss': -self.threshold * 1.5
                }
        
        # 价格大幅高于均线（卖出）
        if pos:
            avg_cost = pos.get('avg_price', current_price)
            profit_pct = (current_price - avg_cost) / avg_cost
            
            if deviation >= self.threshold:
                if profit_pct > 0:
                    return {
                        'signal': 'sell',
                        'reason': f'均值回归卖出 (偏离 +{deviation*100:.2f}%)',
                        'urgency': 'normal'
                    }
            
            # 回归均线即止盈
            if abs(deviation) < self.threshold * 0.3 and profit_pct > 0:
                return {
                    'signal': 'sell',
                    'reason': f'均值回归止盈 (已回归，+{profit_pct*100:.2f}%)',
                    'urgency': 'low'
                }
        
        return {'signal': None}


class BreakoutStrategy:
    """
    突破交易策略 - 追突破
    
    核心思路:
    - 突破 N 日高点买入
    - 跌破 N 日低点卖出
    - 适合趋势市
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.window = config.get('breakout_window', 5)  # 5 日高点
    
    def check(self, code: str, quote: Dict, df: pd.DataFrame, pos: Optional[Dict]) -> Dict:
        """检查突破机会"""
        if df is None or len(df) < self.window:
            return {'signal': None}
        
        current_price = quote.get('current', df['close'].iloc[-1])
        
        # 计算 N 日高低点
        high_n = df['high'].rolling(self.window).max().iloc[-1]
        low_n = df['low'].rolling(self.window).min().iloc[-1]
        
        # 突破高点（买入）
        if current_price >= high_n * 0.999:
            if not pos:
                # 成交量确认
                if 'volume' in df.columns:
                    vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(5).mean().iloc[-1]
                    if vol_ratio >= 1.5:  # 放量突破
                        return {
                            'signal': 'buy',
                            'reason': f'突破{self.window}日高点 (量比{vol_ratio:.1f}x)',
                            'urgency': 'high',
                            'target_profit': 0.02,  # 2% 目标
                            'stop_loss': -0.01      # 1% 止损
                        }
        
        # 跌破低点（卖出）
        if pos:
            avg_cost = pos.get('avg_price', current_price)
            profit_pct = (current_price - avg_cost) / avg_cost
            
            if current_price <= low_n * 1.001:
                return {
                    'signal': 'sell',
                    'reason': f'跌破{self.window}日低点',
                    'urgency': 'high'
                }
            
            # 突破后止盈
            if profit_pct >= 0.02:
                return {
                    'signal': 'sell',
                    'reason': f'突破止盈 (+{profit_pct*100:.2f}%)',
                    'urgency': 'normal'
                }
        
        return {'signal': None}


class HighFrequencyEngine:
    """
    高频交易引擎 - 整合所有高频策略
    
    策略优先级:
    1. 剥头皮 (最高优先级，最快)
    2. 动量交易
    3. 均值回归
    4. 突破交易
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.scalping = ScalpingStrategy(config)
        self.momentum = MomentumStrategy(config)
        self.mean_reversion = MeanReversionStrategy(config)
        self.breakout = BreakoutStrategy(config)
        
        self.trade_count: Dict[str, int] = {}  # 每只股票交易次数
        self.last_trade_time: Dict[str, datetime] = {}
    
    def check(self, code: str, name: str, quote: Dict, df: pd.DataFrame, pos: Optional[Dict]) -> Dict:
        """
        综合所有高频策略，返回最终信号
        
        Returns:
            {'signal': 'buy'/'sell'/None, 'strategy': str, 'reason': str, 'urgency': str}
        """
        signals = []
        
        # 1. 剥头皮策略（最高优先级）
        scalping_signal = self.scalping.check(code, quote, df, pos)
        if scalping_signal['signal']:
            signals.append(('scalping', scalping_signal))
        
        # 2. 动量策略
        momentum_signal = self.momentum.check(code, quote, df, pos)
        if momentum_signal['signal']:
            signals.append(('momentum', momentum_signal))
        
        # 3. 均值回归
        mr_signal = self.mean_reversion.check(code, quote, df, pos)
        if mr_signal['signal']:
            signals.append(('mean_reversion', mr_signal))
        
        # 4. 突破策略
        breakout_signal = self.breakout.check(code, quote, df, pos)
        if breakout_signal['signal']:
            signals.append(('breakout', breakout_signal))
        
        # 选择最高优先级信号
        if not signals:
            return {'signal': None}
        
        # 按 urgency 排序：high > normal > low
        urgency_order = {'high': 0, 'normal': 1, 'low': 2}
        signals.sort(key=lambda x: urgency_order.get(x[1].get('urgency', 'normal'), 1))
        
        best_strategy, best_signal = signals[0]
        
        return {
            'signal': best_signal['signal'],
            'strategy': best_strategy,
            'reason': best_signal.get('reason', ''),
            'urgency': best_signal.get('urgency', 'normal'),
            'target_profit': best_signal.get('target_profit'),
            'stop_loss': best_signal.get('stop_loss')
        }
    
    def on_trade(self, code: str, action: str):
        """记录交易"""
        now = datetime.now()
        
        # 更新交易计数
        self.trade_count[code] = self.trade_count.get(code, 0) + 1
        self.last_trade_time[code] = now
        
        # 通知策略层
        self.scalping.on_trade(code, action)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_trades': sum(self.trade_count.values()),
            'stocks_traded': len(self.trade_count),
            'last_trade': {k: v.isoformat() for k, v in self.last_trade_time.items()}
        }


# 策略工厂
def create_high_frequency_strategy(config: Dict):
    """创建高频策略实例"""
    return HighFrequencyEngine(config)
