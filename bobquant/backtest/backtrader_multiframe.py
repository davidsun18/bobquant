#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtrader 多时间框架分析模块
============================

功能:
1. 同时使用日线 + 分钟线数据
2. 多时间框架信号确认
3. 应用于做 T 策略优化

作者:Bob
日期:2026-04-10
"""

import backtrader as bt
import backtrader.indicators as btind
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


# ============================================================================
# 多时间框架数据源
# ============================================================================

class MultiFrameData(bt.FeedBase):
    """
    多时间框架数据源
    支持同时加载日线和分钟线数据
    """
    params = (
        ('daily_data', None),      # 日线数据 DataFrame
        ('minute_data', None),     # 分钟线数据 DataFrame
        ('timeframe_daily', bt.TimeFrame.Days),
        ('timeframe_minute', bt.TimeFrame.Minutes),
    )

    def __init__(self):
        super().__init__()
        self.daily_df = self.p.daily_data
        self.minute_df = self.p.minute_data


# ============================================================================
# 多时间框架策略基类
# ============================================================================

class MultiFrameStrategy(bt.Strategy):
    """
    多时间框架策略基类

    核心逻辑:
    1. 日线确定趋势方向
    2. 分钟线寻找入场点
    3. 多时间框架信号确认
    """
    params = (
        ('daily_timeframe', bt.TimeFrame.Days),
        ('minute_timeframe', bt.TimeFrame.Minutes),
        ('fast_period', 5),
        ('slow_period', 20),
        ('rsi_period', 14),
        ('printlog', True),
    )

    def __init__(self):
        # 日线数据(第一个数据源)
        self.daily_data = self.datas[0]
        # 分钟线数据(第二个数据源)
        self.minute_data = self.datas[1]

        # 日线趋势指标(在日线数据上计算)
        self.daily_sma_fast = btind.SMA(
            self.daily_data.close, period=self.p.fast_period)
        self.daily_sma_slow = btind.SMA(
            self.daily_data.close, period=self.p.slow_period)
        self.daily_ema = btind.EMA(
            self.daily_data.close, period=10)
        self.daily_rsi = btind.RSI(
            self.daily_data.close, period=self.p.rsi_period)
        self.daily_macd = btind.MACD(
            self.daily_data.close, period_me1=12, period_me2=26, period_signal=9)

        # 分钟线指标(在分钟线数据上计算)
        self.minute_sma_fast = btind.SMA(
            self.minute_data.close, period=self.p.fast_period)
        self.minute_sma_slow = btind.SMA(
            self.minute_data.close, period=self.p.slow_period)
        self.minute_bollinger = btind.BollingerBands(
            self.minute_data.close, period=20, devfactor=2.0)
        self.minute_rsi = btind.RSI(
            self.minute_data.close, period=self.p.rsi_period)

        # 多时间框架信号
        self.daily_trend = None  # 日线趋势:1=上涨,-1=下跌,0=震荡
        self.minute_signal = None  # 分钟线信号:1=买入,-1=卖出,0=观望

        # 交易信号
        self.buy_signal = False
        self.sell_signal = False

    def get_daily_trend(self):
        """
        获取日线趋势

        返回:
        1: 上涨趋势 (快线>慢线 且 RSI>50)
        -1: 下跌趋势 (快线<慢线 且 RSI<50)
        0: 震荡
        """
        # 检查是否有足够的数据
        if len(self.daily_data) < self.p.slow_period:
            return 0

        # 使用 [-1] 获取最新的完整日线数据
        fast = self.daily_sma_fast[-1]
        slow = self.daily_sma_slow[-1]
        rsi = self.daily_rsi[-1]

        if pd.isna(fast) or pd.isna(slow) or pd.isna(rsi):
            return 0

        if fast > slow and rsi > 50:
            return 1  # 上涨趋势
        elif fast < slow and rsi < 50:
            return -1  # 下跌趋势
        else:
            return 0  # 震荡

    def get_minute_signal(self, daily_trend):
        """
        获取分钟线交易信号
        
        参数：
        daily_trend: 日线趋势 (1/-1/0)
        
        返回：
        1: 买入信号
        -1: 卖出信号
        0: 观望
        """
        if len(self.minute_data) < self.p.slow_period:
            return 0
        
        close = self.minute_data.close[0]
        fast = self.minute_sma_fast[0]
        slow = self.minute_sma_slow[0]
        rsi = self.minute_rsi[0]
        bb_top = self.minute_bollinger.lines.top[0]
        bb_bot = self.minute_bollinger.lines.bot[0]
        
        # 检查 NaN
        if any(pd.isna([close, fast, slow, rsi, bb_top, bb_bot])):
            return 0
        
        # 做多信号（日线上涨趋势 + 分钟线回调）
        if daily_trend == 1:
            # 分钟线回调到支撑位
            if close < fast and close > bb_bot and rsi < 40:
                return 1  # 买入信号
            # 分钟线突破
            elif fast > slow and close > fast and rsi > 50:
                return 1  # 买入信号
        
        # 做空信号（日线下跌趋势 + 分钟线反弹）
        elif daily_trend == -1:
            # 分钟线反弹到压力位
            if close > fast and close < bb_top and rsi > 60:
                return -1  # 卖出信号
            # 分钟线跌破
            elif fast < slow and close < fast and rsi < 50:
                return -1  # 卖出信号
        
        return 0  # 观望

    def next(self):
        """主逻辑"""
        # 获取日线趋势
        self.daily_trend = self.get_daily_trend()

        # 获取分钟线信号
        self.minute_signal = self.get_minute_signal(self.daily_trend)

        # 多时间框架信号确认
        self.confirm_signals()

        # 执行交易逻辑
        self.execute_trades()

        # 打印日志
        if self.p.printlog:
            self.log_status()

    def confirm_signals(self):
        """
        多时间框架信号确认

        确认规则:
        1. 日线趋势 + 分钟线信号同向 → 强信号
        2. 日线趋势 + 分钟线信号反向 → 弱信号/观望
        3. 日线震荡 → 降低仓位或观望
        """
        self.buy_signal = False
        self.sell_signal = False

        # 强买入信号:日线上涨 + 分钟线买入
        if self.daily_trend == 1 and self.minute_signal == 1:
            self.buy_signal = True

        # 强卖出信号:日线下跌 + 分钟线卖出
        elif self.daily_trend == -1 and self.minute_signal == -1:
            self.sell_signal = True

        # 日线震荡时,只在分钟线极端情况下交易
        elif self.daily_trend == 0:
            if self.minute_rsi[0] < 20:
                self.buy_signal = True  # 超卖反弹
            elif self.minute_rsi[0] > 80:
                self.sell_signal = True  # 超买回调

    def execute_trades(self):
        """执行交易逻辑(子类重写)"""
        pass

    def log_status(self):
        """打印状态日志"""
        dt = self.minute_data.datetime.datetime(0)
        price = self.minute_data.close[0]

        trend_map = {1: '上涨', -1: '下跌', 0: '震荡'}
        signal_map = {1: '买入', -1: '卖出', 0: '观望'}

        print(f"[{dt.strftime('%Y-%m-%d %H:%M')}] "
              f"价格={price:.2f} | "
              f"日线趋势={trend_map.get(self.daily_trend, '未知')} | "
              f"分钟信号={signal_map.get(self.minute_signal, '未知')} | "
              f"买入={self.buy_signal} | 卖出={self.sell_signal}")


# ============================================================================
# 做 T 策略(多时间框架优化版)
# ============================================================================

class T0MultiFrameStrategy(MultiFrameStrategy):
    """
    做 T 策略 - 多时间框架优化版

    策略逻辑:
    1. 日线确定底仓方向
    2. 分钟线寻找做 T 机会
    3. 多时间框架确认提高胜率
    """
    params = (
        ('base_position', 0.5),      # 底仓比例
        ('t0_size', 0.3),            # 做 T 仓位比例
        ('profit_target', 0.01),     # 止盈目标 1%
        ('stop_loss', 0.005),        # 止损 0.5%
        ('max_trades_per_day', 3),   # 每日最大交易次数
    )

    def __init__(self):
        super().__init__()
        self.order = None
        self.buy_price = None
        self.trades_today = 0
        self.last_trade_date = None
        self.position_size = 0

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                print(f"✓ 买入成交:{order.executed.price:.2f}")
            else:
                print(f"✓ 卖出成交:{order.executed.price:.2f}")

            self.order = None

    def execute_trades(self):
        """执行做 T 交易"""
        if self.order:
            return  # 已有未完成订单

        # 检查是否新交易日
        current_date = self.minute_data.datetime.date(0)
        if self.last_trade_date != current_date:
            self.trades_today = 0
            self.last_trade_date = current_date

        # 检查交易次数限制
        if self.trades_today >= self.p.max_trades_per_day:
            return

        # 获取当前仓位
        position = self.getposition(self.minute_data)
        self.position_size = position.size

        # 买入逻辑
        if self.buy_signal and not position:
            # 计算买入数量
            cash = self.broker.getcash()
            size = int((cash * self.p.t0_size) / self.minute_data.close[0])

            if size > 0:
                self.order = self.buy(size=size)
                self.trades_today += 1
                print(f"→ 发出买入订单:{size}股 @ {self.minute_data.close[0]:.2f}")

        # 卖出逻辑
        elif self.sell_signal and position:
            # 检查是否达到止盈/止损
            if self.buy_price:
                current_price = self.minute_data.close[0]
                profit_pct = (current_price - self.buy_price) / self.buy_price

                # 止盈
                if profit_pct >= self.p.profit_target:
                    self.order = self.sell(size=position.size)
                    self.trades_today += 1
                    print(f"→ 止盈卖出:{position.size}股 @ {current_price:.2f} (盈利{profit_pct*100:.2f}%)")

                # 止损
                elif profit_pct <= -self.p.stop_loss:
                    self.order = self.sell(size=position.size)
                    self.trades_today += 1
                    print(f"→ 止损卖出:{position.size}股 @ {current_price:.2f} (亏损{profit_pct*100:.2f}%)")

            # 信号反转时平仓
            elif not self.buy_signal:
                self.order = self.sell(size=position.size)
                self.trades_today += 1
                print(f"→ 信号反转平仓:{position.size}股 @ {self.minute_data.close[0]:.2f}")

    def log_status(self):
        """增强版状态日志"""
        super().log_status()
        position = self.getposition(self.minute_data)
        if position:
            print(f"  持仓:{position.size}股 | 成本:{self.buy_price:.2f}" if self.buy_price else "")


# ============================================================================
# 多时间框架信号分析器
# ============================================================================

class MultiFrameAnalyzer:
    """
    多时间框架信号分析器

    用于离线分析历史数据的多时间框架信号
    """

    def __init__(self, daily_df, minute_df):
        """
        参数:
        daily_df: 日线数据 DataFrame (columns: open, high, low, close, volume)
        minute_df: 分钟线数据 DataFrame (columns: open, high, low, close, volume)
        """
        self.daily_df = daily_df
        self.minute_df = minute_df
        self.signals = []

    def calculate_daily_trend(self, window=20):
        """
        计算日线趋势

        返回:
        DataFrame with trend column (1/-1/0)
        """
        df = self.daily_df.copy()

        # 计算均线
        df['sma_fast'] = df['close'].rolling(window=5).mean()
        df['sma_slow'] = df['close'].rolling(window=window).mean()
        df['rsi'] = self._calculate_rsi(df['close'], 14)

        # 判断趋势
        def get_trend(row):
            if pd.isna(row['sma_slow']):
                return 0
            if row['sma_fast'] > row['sma_slow'] and row['rsi'] > 50:
                return 1
            elif row['sma_fast'] < row['sma_slow'] and row['rsi'] < 50:
                return -1
            return 0

        df['trend'] = df.apply(get_trend, axis=1)
        return df

    def calculate_minute_signals(self, daily_trend_df):
        """
        计算分钟线信号

        参数:
        daily_trend_df: 包含日线趋势的 DataFrame

        返回:
        DataFrame with signals
        """
        df = self.minute_df.copy()

        # 计算分钟线指标
        df['sma_fast'] = df['close'].rolling(window=5).mean()
        df['sma_slow'] = df['close'].rolling(window=20).mean()
        df['rsi'] = self._calculate_rsi(df['close'], 14)

        # 布林带
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_top'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_bot'] = df['bb_mid'] - 2 * df['bb_std']

        # 合并日线趋势
        daily_trend_df = daily_trend_df.set_index('datetime')
        df = df.set_index('datetime')
        df['daily_trend'] = daily_trend_df['trend'].reindex(
            df.index.date, method='ffill'
        ).values

        # 生成信号
        def get_signal(row):
            if pd.isna(row['sma_slow']) or pd.isna(row['daily_trend']):
                return 0

            # 做多信号
            if row['daily_trend'] == 1:
                if row['close'] < row['sma_fast'] and row['close'] > row['bb_bot'] and row['rsi'] < 40:
                    return 1
                if row['sma_fast'] > row['sma_slow'] and row['close'] > row['sma_fast'] and row['rsi'] > 50:
                    return 1

            # 做空信号
            elif row['daily_trend'] == -1:
                if row['close'] > row['sma_fast'] and row['close'] < row['bb_top'] and row['rsi'] > 60:
                    return -1
                if row['sma_fast'] < row['sma_slow'] and row['close'] < row['sma_fast'] and row['rsi'] < 50:
                    return -1

            # 日线震荡时的超买超卖
            elif row['daily_trend'] == 0:
                if row['rsi'] < 20:
                    return 1
                if row['rsi'] > 80:
                    return -1

            return 0

        df['signal'] = df.apply(get_signal, axis=1)
        return df.reset_index()

    def _calculate_rsi(self, prices, period=14):
        """计算 RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def analyze_signals(self):
        """
        分析信号质量

        返回:
        信号统计信息
        """
        # 计算日线趋势
        daily_trend_df = self.calculate_daily_trend()

        # 计算分钟线信号
        signals_df = self.calculate_minute_signals(daily_trend_df)

        # 统计分析
        total_signals = len(signals_df[signals_df['signal'] != 0])
        buy_signals = len(signals_df[signals_df['signal'] == 1])
        sell_signals = len(signals_df[signals_df['signal'] == -1])

        # 按日线趋势分类
        trend_stats = signals_df.groupby('daily_trend')['signal'].value_counts()

        return {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'trend_distribution': trend_stats.to_dict(),
            'signals_df': signals_df
        }


# ============================================================================
# 示例:运行回测
# ============================================================================

def run_multiframe_backtest(stock_code, start_date, end_date):
    """
    运行多时间框架回测示例

    参数:
    stock_code: 股票代码
    start_date: 开始日期 'YYYY-MM-DD'
    end_date: 结束日期 'YYYY-MM-DD'
    """
    print(f"开始回测:{stock_code}")
    print(f"时间范围:{start_date} 至 {end_date}")
    print("=" * 60)

    # 创建 Cerebro 引擎
    cerebro = bt.Cerebro()

    # 添加策略
    cerebro.addstrategy(T0MultiFrameStrategy)

    # 这里需要添加实际的数据源
    # 示例:使用 PandasData
    # data_daily = bt.feeds.PandasData(dataname=daily_df, ...)
    # data_minute = bt.feeds.PandasData(dataname=minute_df, ...)
    # cerebro.adddata(data_daily)
    # cerebro.adddata(data_minute)

    # 设置初始资金
    cerebro.broker.setcash(100000.0)

    # 设置手续费
    cerebro.broker.setcommission(commission=0.0003)

    # 运行回测
    # results = cerebro.run()

    print("回测框架已准备就绪")
    print("请根据实际数据源配置数据加载部分")

    return cerebro


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Backtrader 多时间框架分析模块")
    print("=" * 60)

    # 示例:创建分析器
    # 注意:这里需要实际的数据
    print("\n模块已加载,可用功能:")
    print("1. MultiFrameData - 多时间框架数据源")
    print("2. MultiFrameStrategy - 多时间框架策略基类")
    print("3. T0MultiFrameStrategy - 做 T 策略(多时间框架优化版)")
    print("4. MultiFrameAnalyzer - 多时间框架信号分析器")
    print("\n使用示例:")
    print("  from backtrader_multiframe import T0MultiFrameStrategy, MultiFrameAnalyzer")
    print("  analyzer = MultiFrameAnalyzer(daily_df, minute_df)")
    print("  results = analyzer.analyze_signals()")
