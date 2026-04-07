#!/usr/bin/env python3
"""
QuantStats 绩效评估模块

集成 QuantStats 库，提供 50+ 风险指标和蒙特卡洛模拟分析
用于改进现有系统的绩效评估和风控模块

功能:
- 计算夏普比率、Sortino 比率、最大回撤等 50+ 指标
- 生成 HTML 绩效报告
- 蒙特卡洛模拟分析
- 交易记录转换为收益率序列
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

try:
    import quantstats as qs
    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False
    print("⚠️ QuantStats 未安装，运行：pip3 install quantstats")


class PerformanceAnalyzer:
    """绩效分析器 - 基于 QuantStats"""
    
    def __init__(self, initial_capital: float = 100000.0):
        """
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.trades: List[dict] = []
        self.daily_returns: pd.Series = None
        self.portfolio_value: pd.Series = None
        
        if not QUANTSTATS_AVAILABLE:
            raise ImportError("QuantStats 未安装")
    
    def add_trade(
        self,
        code: str,
        action: str,
        price: float,
        shares: int,
        timestamp: datetime,
        profit: float = 0.0
    ):
        """
        添加交易记录
        
        Args:
            code: 股票代码
            action: 买入/卖出
            price: 成交价格
            shares: 成交数量
            timestamp: 成交时间
            profit: 盈亏（卖出时填写）
        """
        trade = {
            'code': code,
            'action': action,
            'price': price,
            'shares': shares,
            'timestamp': timestamp,
            'profit': profit
        }
        self.trades.append(trade)
    
    def load_trades_from_json(self, json_path: str):
        """
        从 JSON 文件加载交易记录
        
        Args:
            json_path: 交易记录 JSON 文件路径
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"交易记录文件不存在：{json_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 支持两种格式
        if isinstance(data, list):
            trades = data
        elif isinstance(data, dict) and 'trades' in data:
            trades = data['trades']
        else:
            trades = data.get('transactions', [])
        
        for trade in trades:
            # 解析时间
            time_str = trade.get('time', trade.get('timestamp', ''))
            if time_str:
                try:
                    timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            self.add_trade(
                code=trade.get('code', trade.get('stock', '')),
                action=trade.get('action', trade.get('type', '')),
                price=float(trade.get('price', 0)),
                shares=int(trade.get('shares', trade.get('volume', 0))),
                timestamp=timestamp,
                profit=float(trade.get('profit', trade.get('pnl', 0)))
            )
        
        print(f"✅ 已加载 {len(self.trades)} 条交易记录")
    
    def calculate_daily_returns(self) -> pd.Series:
        """
        计算每日收益率序列
        
        Returns:
            每日收益率 Series
        """
        if not self.trades:
            raise ValueError("没有交易记录")
        
        # 按日期聚合盈亏
        daily_pnl = {}
        for trade in self.trades:
            date = trade['timestamp'].strftime('%Y-%m-%d')
            if date not in daily_pnl:
                daily_pnl[date] = 0.0
            daily_pnl[date] += trade.get('profit', 0.0)
        
        # 转换为 Series
        dates = sorted(daily_pnl.keys())
        returns = []
        
        # 计算每日收益率
        capital = self.initial_capital
        for date in dates:
            pnl = daily_pnl[date]
            daily_return = pnl / capital if capital > 0 else 0.0
            returns.append(daily_return)
            capital += pnl  # 更新资金
        
        self.daily_returns = pd.Series(returns, index=pd.to_datetime(dates))
        return self.daily_returns
    
    def calculate_portfolio_value(self) -> pd.Series:
        """
        计算投资组合价值序列
        
        Returns:
            投资组合价值 Series
        """
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        # 计算累计收益
        cumulative = (1 + self.daily_returns).cumprod()
        self.portfolio_value = self.initial_capital * cumulative
        
        return self.portfolio_value
    
    def get_metrics(self) -> dict:
        """
        获取所有绩效指标
        
        Returns:
            指标字典
        """
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        metrics = {}
        
        # 基础指标
        metrics['总收益率'] = qs.stats.comp(self.daily_returns)
        metrics['年化收益率'] = qs.stats.cagr(self.daily_returns)
        metrics['夏普比率'] = qs.stats.sharpe(self.daily_returns)
        metrics['Sortino 比率'] = qs.stats.sortino(self.daily_returns)
        metrics['最大回撤'] = qs.stats.max_drawdown(self.daily_returns)
        metrics['Calmar 比率'] = qs.stats.calmar(self.daily_returns)
        
        # 风险指标
        metrics['波动率 (年化)'] = qs.stats.volatility(self.daily_returns)
        metrics['VaR 95%'] = qs.stats.var(self.daily_returns, confidence=0.95)
        metrics['CVaR 95%'] = qs.stats.cvar(self.daily_returns, confidence=0.95)
        
        # 交易统计
        metrics['总交易日'] = len(self.daily_returns)
        metrics['盈利天数'] = (self.daily_returns > 0).sum()
        metrics['亏损天数'] = (self.daily_returns < 0).sum()
        metrics['胜率'] = (self.daily_returns > 0).sum() / len(self.daily_returns)
        
        # 收益风险比
        metrics['收益风险比'] = metrics['年化收益率'] / metrics['波动率 (年化)'] if metrics['波动率 (年化)'] > 0 else 0
        
        # 最终资金
        if self.portfolio_value is None:
            self.calculate_portfolio_value()
        metrics['最终资金'] = self.portfolio_value.iloc[-1]
        metrics['总盈亏'] = metrics['最终资金'] - self.initial_capital
        
        return metrics
    
    def generate_html_report(
        self,
        output_path: str = None,
        benchmark: str = None,
        title: str = "量化策略绩效报告"
    ) -> str:
        """
        生成 HTML 绩效报告
        
        Args:
            output_path: 输出文件路径
            benchmark: 基准代码（如 'SH000300' 沪深 300）
            title: 报告标题
        
        Returns:
            输出文件路径
        """
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"backtest_results/performance_report_{timestamp}.html"
        
        # 确保目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 生成完整报告
        qs.reports.full(
            self.daily_returns,
            benchmark=benchmark,
            output=output_path,
            title=title,
            language='zh'
        )
        
        print(f"✅ HTML 报告已生成：{output_path}")
        return output_path
    
    def monte_carlo_analysis(
        self,
        n_simulations: int = 1000,
        days: int = 252
    ) -> dict:
        """
        蒙特卡洛模拟分析
        
        Args:
            n_simulations: 模拟次数
            days: 模拟天数（252=1 年交易日）
        
        Returns:
            分析结果字典
        """
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        # 使用 QuantStats 的蒙特卡洛模拟
        mc_results = qs.reports.monte_carlo(
            self.daily_returns,
            n_simulations=n_simulations,
            days=days,
            show=False,
            save=False
        )
        
        # 提取关键统计
        if hasattr(mc_results, 'summary'):
            summary = mc_results.summary
            result = {
                '中位数最终值': summary.get('median', 0),
                '5% 分位数': summary.get('5%', 0),
                '95% 分位数': summary.get('95%', 0),
                '平均值': summary.get('mean', 0),
                '标准差': summary.get('std', 0)
            }
        else:
            result = {'error': '无法解析蒙特卡洛结果'}
        
        return result
    
    def plot_metrics(self, save_path: str = None):
        """
        绘制关键指标图表
        
        Args:
            save_path: 保存路径
        """
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        # 绘制收益率分布
        qs.plots.histogram(self.daily_returns, savefig=save_path)
        
        # 绘制累计收益
        qs.plots.earnings(self.daily_returns, savefig=save_path)
        
        # 绘制回撤
        qs.plots.drawdown(self.daily_returns, savefig=save_path)
        
        print(f"✅ 图表已保存")


class DualThrustStrategy:
    """
    Dual Thrust 策略 - 经典日内突破策略
    
    核心逻辑:
    1. 计算 N 日的 HH(最高价)、LL(最低价)、HC(收盘价)、LC(收盘价)
    2. Range = max(HH-LC, HC-LL)
    3. 上轨 = 开盘价 + K1 * Range
    4. 下轨 = 开盘价 - K2 * Range
    5. 突破上轨做多，跌破下轨做空
    
    适配 A 股:
    - 只做多不做空（T+1 限制）
    - 结合现有三阶段引擎
    - 添加成交量确认
    """
    
    def __init__(
        self,
        lookback: int = 4,
        k1: float = 0.5,
        k2: float = 0.5,
        volume_confirm: bool = True
    ):
        """
        Args:
            lookback: 回看天数
            k1: 上轨系数
            k2: 下轨系数
            volume_confirm: 是否需要成交量确认
        """
        self.lookback = lookback
        self.k1 = k1
        self.k2 = k2
        self.volume_confirm = volume_confirm
        
        self.signals: List[dict] = []
    
    def calculate_range(self, df: pd.DataFrame) -> float:
        """
        计算 Dual Thrust Range
        
        Args:
            df: 包含 high, low, close 列的 DataFrame
        
        Returns:
            Range 值
        """
        # 过去 N 天的最高价
        hh = df['high'].rolling(self.lookback).max()
        # 过去 N 天的最低价
        ll = df['low'].rolling(self.lookback).min()
        # 过去 N 天的收盘价
        hc = df['close'].shift(1).rolling(self.lookback).max()
        lc = df['close'].shift(1).rolling(self.lookback).min()
        
        # Range = max(HH-LC, HC-LL)
        range_val = np.maximum(hh - lc, hc - ll)
        
        return range_val.iloc[-1]
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        open_price: float,
        volume: float = None,
        avg_volume: float = None
    ) -> Tuple[str, float, str]:
        """
        生成交易信号
        
        Args:
            df: 历史 K 线数据
            current_price: 当前价格
            open_price: 今日开盘价
            volume: 当前成交量
            avg_volume: 平均成交量
        
        Returns:
            (信号：buy/sell/hold, 强度 0-1, 原因)
        """
        if len(df) < self.lookback:
            return 'hold', 0.0, f"数据不足 (需要{self.lookback}天)"
        
        # 计算 Range
        range_val = self.calculate_range(df)
        
        # 计算上下轨
        upper轨 = open_price + self.k1 * range_val
        lower轨 = open_price - self.k2 * range_val
        
        # 判断突破
        signal = 'hold'
        strength = 0.0
        reason = ""
        
        if current_price > upper轨:
            signal = 'buy'
            strength = min(1.0, (current_price - upper轨) / range_val * 2)
            reason = f"突破上轨 {upper轨:.2f} (Range={range_val:.2f})"
            
            # 成交量确认
            if self.volume_confirm and volume and avg_volume:
                if volume < avg_volume * 1.5:
                    strength *= 0.5
                    reason += " (成交量未确认)"
        
        elif current_price < lower轨:
            # A 股只做多，跌破下轨作为止损信号
            signal = 'sell'
            strength = min(1.0, (lower轨 - current_price) / range_val * 2)
            reason = f"跌破下轨 {lower轨:.2f} (Range={range_val:.2f})"
        
        else:
            reason = f"在轨道内 (上轨={upper轨:.2f}, 下轨={lower轨:.2f})"
        
        return signal, strength, reason
    
    def backtest(
        self,
        df: pd.DataFrame,
        initial_capital: float = 100000.0,
        position_size: float = 0.1
    ) -> pd.Series:
        """
        简单回测
        
        Args:
            df: K 线数据 (包含 open, high, low, close, volume)
            initial_capital: 初始资金
            position_size: 单次仓位比例
        
        Returns:
            每日资金曲线
        """
        capital = initial_capital
        position = 0  # 持仓数量
        buy_price = 0  # 买入价格
        
        portfolio_values = []
        
        for i in range(self.lookback, len(df)):
            row = df.iloc[i]
            hist_df = df.iloc[:i+1]
            
            # 生成信号
            signal, strength, _ = self.generate_signal(
                df=hist_df,
                current_price=row['close'],
                open_price=row['open'],
                volume=row.get('volume'),
                avg_volume=df['volume'].rolling(20).mean().iloc[i]
            )
            
            # 执行交易
            if signal == 'buy' and position == 0:
                # 买入
                shares = int(capital * position_size / row['open'])
                if shares > 0:
                    position = shares
                    buy_price = row['open']
                    capital -= shares * row['open']
            
            elif signal == 'sell' and position > 0:
                # 卖出
                capital += position * row['open']
                position = 0
                buy_price = 0
            
            # 计算总资产
            total_value = capital + position * row['close']
            portfolio_values.append(total_value)
        
        return pd.Series(portfolio_values)


# ========== 测试 ==========
if __name__ == '__main__':
    print("="*60)
    print("测试 QuantStats 集成模块")
    print("="*60)
    
    # 测试绩效分析器
    print("\n【1】测试 PerformanceAnalyzer")
    analyzer = PerformanceAnalyzer(initial_capital=100000.0)
    
    # 生成模拟交易记录
    base_date = datetime(2026, 3, 1)
    for i in range(30):
        date = base_date + timedelta(days=i)
        profit = np.random.randn() * 500  # 随机盈亏
        analyzer.add_trade(
            code='sh.600519',
            action='卖出' if profit > 0 else '买入',
            price=1500.0,
            shares=100,
            timestamp=date,
            profit=profit
        )
    
    # 计算指标
    metrics = analyzer.get_metrics()
    print(f"\n绩效指标:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    # 测试 Dual Thrust
    print("\n【2】测试 Dual Thrust 策略")
    dt = DualThrustStrategy(lookback=4, k1=0.5, k2=0.5)
    
    # 生成模拟 K 线
    dates = pd.date_range('2026-01-01', periods=50, freq='D')
    df = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(50)),
        'high': 100 + np.cumsum(np.random.randn(50)) + np.abs(np.random.randn(50)),
        'low': 100 + np.cumsum(np.random.randn(50)) - np.abs(np.random.randn(50)),
        'close': 100 + np.cumsum(np.random.randn(50)),
        'volume': np.random.randint(1000, 10000, 50)
    }, index=dates)
    
    signal, strength, reason = dt.generate_signal(
        df=df,
        current_price=df['close'].iloc[-1],
        open_price=df['open'].iloc[-1],
        volume=df['volume'].iloc[-1],
        avg_volume=df['volume'].rolling(20).mean().iloc[-1]
    )
    
    print(f"  信号：{signal}")
    print(f"  强度：{strength:.2f}")
    print(f"  原因：{reason}")
    
    print("\n✅ 测试完成")
