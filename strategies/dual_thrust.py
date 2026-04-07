#!/usr/bin/env python3
"""
Dual Thrust 策略实现 - A 股适配版

经典日内突破策略，适配 A 股 T+1 制度

核心逻辑:
1. Range = max(HH-LC, HC-LL)
   - HH: N 日最高价
   - LL: N 日最低价
   - HC: N 日收盘价最高
   - LC: N 日收盘价最低
2. 上轨 = 今日开盘价 + K1 * Range
3. 下轨 = 今日开盘价 - K2 * Range
4. 突破上轨 → 买入信号
5. 跌破下轨 → 卖出/止损信号

A 股适配:
- 只做多不做空
- 结合成交量确认
- 添加时间过滤（避免尾盘假突破）
- 结合现有风控模块
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
import json


class DualThrustSignal:
    """Dual Thrust 信号生成器"""
    
    def __init__(
        self,
        lookback: int = 4,
        k1: float = 0.5,
        k2: float = 0.5,
        volume_confirm: bool = True,
        volume_ratio: float = 1.5,
        time_filter: bool = True,
        morning_start: time = time(9, 45),
        morning_end: time = time(11, 20),
        afternoon_start: time = time(13, 0),
        afternoon_end: time = time(14, 45)
    ):
        """
        Args:
            lookback: 回看天数（默认 4 天）
            k1: 上轨系数（默认 0.5）
            k2: 下轨系数（默认 0.5）
            volume_confirm: 是否需要成交量确认
            volume_ratio: 成交量倍数（当前量/均量）
            time_filter: 是否启用时间过滤
            morning_start: 早盘允许交易开始时间
            morning_end: 早盘允许交易结束时间
            afternoon_start: 午盘允许交易开始时间
            afternoon_end: 午盘允许交易结束时间
        """
        self.lookback = lookback
        self.k1 = k1
        self.k2 = k2
        self.volume_confirm = volume_confirm
        self.volume_ratio = volume_ratio
        self.time_filter = time_filter
        self.morning_start = morning_start
        self.morning_end = morning_end
        self.afternoon_start = afternoon_start
        self.afternoon_end = afternoon_end
        
        self.signals_history: List[dict] = []
    
    def calculate_dual_thrust_range(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """
        计算 Dual Thrust Range 和上下轨
        
        Args:
            df: 包含 open, high, low, close 的 DataFrame
        
        Returns:
            (range_val, upper_bound, lower_bound)
        """
        if len(df) < self.lookback:
            return 0.0, 0.0, 0.0
        
        # 过去 N 天的数据
        hist = df.iloc[-self.lookback:]
        
        # HH: N 日最高价
        hh = hist['high'].max()
        # LL: N 日最低价
        ll = hist['low'].min()
        # HC: N 日收盘价最高
        hc = hist['close'].max()
        # LC: N 日收盘价最低
        lc = hist['close'].min()
        
        # Range = max(HH-LC, HC-LL)
        range_val = max(hh - lc, hc - ll)
        
        # 今日开盘价
        today_open = df['open'].iloc[-1]
        
        # 上下轨
        upper_bound = today_open + self.k1 * range_val
        lower_bound = today_open - self.k2 * range_val
        
        return range_val, upper_bound, lower_bound
    
    def is_valid_trading_time(self, current_time: datetime) -> Tuple[bool, str]:
        """
        检查是否在有效交易时间内
        
        Returns:
            (是否有效，原因)
        """
        if not self.time_filter:
            return True, "时间过滤已禁用"
        
        t = current_time.time()
        
        # 检查早盘窗口
        if self.morning_start <= t <= self.morning_end:
            return True, f"在早盘窗口 ({self.morning_start}-{self.morning_end})"
        
        # 检查午盘窗口
        if self.afternoon_start <= t <= self.afternoon_end:
            return True, f"在午盘窗口 ({self.afternoon_start}-{self.afternoon_end})"
        
        return False, f"不在交易时间窗口 (当前{t})"
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        current_time: datetime,
        volume: float = None,
        avg_volume: float = None,
        code: str = None
    ) -> Dict:
        """
        生成交易信号
        
        Args:
            df: 历史 K 线数据（至少 lookback 天）
            current_price: 当前价格
            current_time: 当前时间
            volume: 当前成交量
            avg_volume: 平均成交量（20 日均量）
            code: 股票代码
        
        Returns:
            信号字典 {action, strength, reason, ...}
        """
        result = {
            'code': code,
            'timestamp': current_time,
            'action': 'hold',
            'strength': 0.0,
            'reason': '',
            'upper_bound': 0.0,
            'lower_bound': 0.0,
            'range': 0.0
        }
        
        # 1. 检查数据是否足够
        if len(df) < self.lookback:
            result['reason'] = f"数据不足 (需要{self.lookback}天，实际{len(df)}天)"
            return result
        
        # 2. 检查交易时间
        time_valid, time_reason = self.is_valid_trading_time(current_time)
        if not time_valid:
            result['reason'] = f"时间过滤：{time_reason}"
            return result
        
        # 3. 计算 Range 和上下轨
        range_val, upper_bound, lower_bound = self.calculate_dual_thrust_range(df)
        result['range'] = range_val
        result['upper_bound'] = upper_bound
        result['lower_bound'] = lower_bound
        
        if range_val <= 0:
            result['reason'] = "Range 为 0，无法生成信号"
            return result
        
        # 4. 判断突破
        action = 'hold'
        strength = 0.0
        reason = ""
        
        # 突破上轨 - 买入信号
        if current_price > upper_bound:
            action = 'buy'
            strength = min(1.0, (current_price - upper_bound) / range_val * 2)
            reason = f"突破上轨 {upper_bound:.2f} (Range={range_val:.2f}, 超出{current_price-upper_bound:.2f})"
            
            # 成交量确认
            if self.volume_confirm and volume and avg_volume:
                vol_ratio = volume / avg_volume if avg_volume > 0 else 0
                if vol_ratio < self.volume_ratio:
                    strength *= 0.5
                    reason += f" | 成交量未确认 (当前{volume:.0f}, 均量{avg_volume:.0f}, 比率{vol_ratio:.2f})"
                else:
                    reason += f" | 成交量确认 (放量{vol_ratio:.2f}倍)"
        
        # 跌破下轨 - 卖出信号（A 股作为止损）
        elif current_price < lower_bound:
            action = 'sell'
            strength = min(1.0, (lower_bound - current_price) / range_val * 2)
            reason = f"跌破下轨 {lower_bound:.2f} (Range={range_val:.2f}, 跌破{lower_bound-current_price:.2f})"
        
        else:
            # 在轨道内
            mid = (upper_bound + lower_bound) / 2
            reason = f"在轨道内 (上轨={upper_bound:.2f}, 下轨={lower_bound:.2f}, 中轨={mid:.2f})"
        
        result['action'] = action
        result['strength'] = strength
        result['reason'] = reason
        
        # 记录信号历史
        self.signals_history.append(result.copy())
        
        return result
    
    def get_signals_summary(self) -> dict:
        """获取信号统计摘要"""
        if not self.signals_history:
            return {'total': 0}
        
        buys = [s for s in self.signals_history if s['action'] == 'buy']
        sells = [s for s in self.signals_history if s['action'] == 'sell']
        
        return {
            'total_signals': len(self.signals_history),
            'buy_signals': len(buys),
            'sell_signals': len(sells),
            'hold_signals': len(self.signals_history) - len(buys) - len(sells),
            'avg_buy_strength': np.mean([s['strength'] for s in buys]) if buys else 0,
            'avg_sell_strength': np.mean([s['strength'] for s in sells]) if sells else 0
        }


class DualThrustBacktester:
    """Dual Thrust 回测器"""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        position_size: float = 0.1,
        commission: float = 0.0003,  # 万分之三
        slippage: float = 0.001  # 千分之一滑点
    ):
        """
        Args:
            initial_capital: 初始资金
            position_size: 单次仓位比例
            commission: 手续费率
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.commission = commission
        self.slippage = slippage
        
        self.trades: List[dict] = []
        self.equity_curve: List[float] = []
    
    def run_backtest(
        self,
        df: pd.DataFrame,
        strategy: DualThrustSignal,
        code: str = 'TEST'
    ) -> pd.DataFrame:
        """
        运行回测
        
        Args:
            df: K 线数据（包含 open, high, low, close, volume）
            strategy: DualThrustSignal 实例
            code: 股票代码
        
        Returns:
            回测结果 DataFrame
        """
        capital = self.initial_capital
        position = 0
        buy_price = 0
        buy_time = None
        
        results = []
        
        # 从 lookback 天后开始
        start_idx = strategy.lookback
        
        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            current_time = row.name if hasattr(row.name, 'to_pydatetime') else datetime.now()
            
            # 获取历史数据
            hist_df = df.iloc[:i+1].copy()
            
            # 生成信号
            signal = strategy.generate_signal(
                df=hist_df,
                current_price=row['close'],
                current_time=current_time,
                volume=row.get('volume'),
                avg_volume=df['volume'].rolling(20).mean().iloc[i] if i >= 20 else df['volume'].iloc[:i].mean(),
                code=code
            )
            
            # 执行交易
            if signal['action'] == 'buy' and position == 0 and signal['strength'] >= 0.5:
                # 买入（考虑滑点）
                exec_price = row['open'] * (1 + self.slippage)
                shares = int(capital * self.position_size / exec_price)
                
                if shares > 0:
                    cost = shares * exec_price * (1 + self.commission)
                    if cost <= capital:
                        position = shares
                        buy_price = exec_price
                        buy_time = current_time
                        capital -= cost
                        
                        self.trades.append({
                            'time': current_time,
                            'action': 'buy',
                            'price': exec_price,
                            'shares': shares,
                            'cost': cost
                        })
            
            elif signal['action'] == 'sell' and position > 0:
                # 卖出（考虑滑点）
                exec_price = row['open'] * (1 - self.slippage)
                revenue = position * exec_price * (1 - self.commission)
                profit = revenue - position * buy_price
                
                capital += revenue
                
                self.trades.append({
                    'time': current_time,
                    'action': 'sell',
                    'price': exec_price,
                    'shares': position,
                    'revenue': revenue,
                    'profit': profit,
                    'buy_price': buy_price,
                    'buy_time': buy_time
                })
                
                position = 0
                buy_price = 0
                buy_time = None
            
            # 记录权益
            total_equity = capital + position * row['close']
            self.equity_curve.append(total_equity)
            
            results.append({
                'time': current_time,
                'equity': total_equity,
                'capital': capital,
                'position_value': position * row['close'],
                'signal': signal['action']
            })
        
        return pd.DataFrame(results)
    
    def get_performance(self) -> dict:
        """获取回测绩效"""
        if not self.equity_curve:
            return {}
        
        equity = pd.Series(self.equity_curve)
        returns = equity.pct_change().dropna()
        
        # 基础指标
        total_return = (equity.iloc[-1] - self.initial_capital) / self.initial_capital
        max_equity = equity.cummax()
        max_drawdown = ((equity - max_equity) / max_equity).min()
        
        # 交易统计
        buy_trades = [t for t in self.trades if t['action'] == 'buy']
        sell_trades = [t for t in self.trades if t['action'] == 'sell']
        
        profitable_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(profitable_trades) / len(sell_trades) if sell_trades else 0
        
        avg_profit = np.mean([t['profit'] for t in sell_trades]) if sell_trades else 0
        
        return {
            '初始资金': self.initial_capital,
            '最终权益': equity.iloc[-1],
            '总收益率': total_return,
            '最大回撤': max_drawdown,
            '交易次数': len(sell_trades),
            '胜率': win_rate,
            '平均盈亏': avg_profit,
            '夏普比率': returns.mean() / returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        }


# ========== 测试 ==========
if __name__ == '__main__':
    print("="*60)
    print("Dual Thrust 策略测试")
    print("="*60)
    
    # 生成模拟数据
    np.random.seed(42)
    n_days = 100
    dates = pd.date_range('2026-01-01', periods=n_days, freq='D')
    
    # 模拟价格序列（带趋势）
    trend = np.linspace(0, 20, n_days)
    noise = np.cumsum(np.random.randn(n_days))
    prices = 100 + trend + noise
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(n_days),
        'high': prices + np.abs(np.random.randn(n_days)) + 2,
        'low': prices - np.abs(np.random.randn(n_days)) - 2,
        'close': prices,
        'volume': np.random.randint(1000, 10000, n_days)
    }, index=dates)
    
    # 创建策略
    strategy = DualThrustSignal(
        lookback=4,
        k1=0.5,
        k2=0.5,
        volume_confirm=False,  # 测试时禁用成交量确认
        time_filter=False  # 测试时禁用时间过滤
    )
    
    # 测试信号生成
    print("\n【1】测试信号生成")
    signal = strategy.generate_signal(
        df=df,
        current_price=df['close'].iloc[-1],
        current_time=datetime.now(),
        volume=df['volume'].iloc[-1],
        avg_volume=df['volume'].rolling(20).mean().iloc[-1],
        code='sh.600519'
    )
    
    print(f"  代码：{signal['code']}")
    print(f"  信号：{signal['action']}")
    print(f"  强度：{signal['strength']:.2f}")
    print(f"  Range: {signal['range']:.2f}")
    print(f"  上轨：{signal['upper_bound']:.2f}")
    print(f"  下轨：{signal['lower_bound']:.2f}")
    print(f"  原因：{signal['reason']}")
    
    # 测试回测
    print("\n【2】测试回测")
    backtester = DualThrustBacktester(
        initial_capital=100000.0,
        position_size=0.2
    )
    
    results = backtester.run_backtest(df, strategy)
    performance = backtester.get_performance()
    
    print(f"\n回测绩效:")
    for key, value in performance.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}" if value < 10 else f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    # 信号统计
    print("\n【3】信号统计")
    summary = strategy.get_signals_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 测试完成")
