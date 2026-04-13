#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant Backtrader 回测引擎 v1.0

基于 Backtrader 的事件驱动回测系统，提供专业级回测能力。

特性：
1. 事件驱动架构，支持复杂交易逻辑
2. 完整的绩效分析（夏普比率、最大回撤、Sortino 比率等）
3. 参数优化（网格搜索、优化器）
4. 多策略对比分析
5. 支持日线/分钟线回测
6. 集成到现有回测系统

用法：
    from backtest.backtrader_engine import BacktraderEngine
    
    # 初始化
    engine = BacktraderEngine(initial_capital=1000000)
    
    # 运行 MACD 策略回测
    results = engine.run_macd(
        code='000001.SZ',
        start_date='2024-01-01',
        end_date='2024-12-31',
        fast_period=12,
        slow_period=26,
        signal_period=9
    )
    
    # 查看结果
    print(results['metrics'])
"""
import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import json
import os
import warnings
from loguru import logger

warnings.filterwarnings('ignore')

# 添加项目路径
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)


# ==================== 策略定义 ====================

class MACDStrategy(bt.Strategy):
    """MACD 策略"""
    
    params = (
        ('fast_period', 12),
        ('slow_period', 26),
        ('signal_period', 9),
        ('stake_percent', 0.95),  # 每次使用 95% 可用资金
    )
    
    def __init__(self):
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.trade_history = []
        
        # MACD 指标
        self.macd = bt.ind.MACD(
            self.data.close,
            period_me1=self.p.fast_period,
            period_me2=self.p.slow_period,
            period_signal=self.p.signal_period
        )
        
        # 金叉死叉信号
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行：价格={order.executed.price:.2f}, '
                        f'成本={order.executed.value:.2f}, '
                        f'手续费={order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:
                self.log(f'卖出执行：价格={order.executed.price:.2f}, '
                        f'成本={order.executed.value:.2f}, '
                        f'手续费={order.executed.comm:.2f}')
            
            self.trade_history.append({
                'date': self.data.datetime.date(),
                'type': 'buy' if order.isbuy() else 'sell',
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm
            })
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return
        self.log(f'交易利润：毛利={trade.pnl:.2f}, 净利={trade.pnlcomm:.2f}')
    
    def log(self, txt, dt=None):
        """日志记录"""
        dt = dt or self.datas[0].datetime.date(0)
        logger.debug(f'{dt.isoformat()} {txt}')
    
    def next(self):
        """主逻辑"""
        if self.order:
            return
        
        if self.crossover > 0:  # 金叉买入
            if not self.getposition().size:
                # 计算可买数量（95% 仓位，100 股整数倍）
                available_cash = self.broker.getcash() * self.p.stake_percent
                size = int(available_cash / self.data.close[0] / 100) * 100
                if size >= 100:
                    self.order = self.buy(size=size)
        
        elif self.crossover < 0:  # 死叉卖出
            if self.getposition().size:
                self.order = self.close()


class RSIStrategy(bt.Strategy):
    """RSI 策略"""
    
    params = (
        ('rsi_period', 14),
        ('oversold', 30),
        ('overbought', 70),
        ('stake_percent', 0.95),
    )
    
    def __init__(self):
        self.order = None
        self.rsi = bt.ind.RSI(self.data.close, period=self.p.rsi_period)
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入：价格={order.executed.price:.2f}')
            else:
                self.log(f'卖出：价格={order.executed.price:.2f}')
        self.order = None
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        logger.debug(f'{dt.isoformat()} {txt}')
    
    def next(self):
        if self.order:
            return
        
        if self.rsi < self.p.oversold and not self.getposition().size:
            available_cash = self.broker.getcash() * self.p.stake_percent
            size = int(available_cash / self.data.close[0] / 100) * 100
            if size >= 100:
                self.order = self.buy(size=size)
        
        elif self.rsi > self.p.overbought and self.getposition().size:
            self.order = self.close()


class DualMAStrategy(bt.Strategy):
    """双均线策略"""
    
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
        ('stake_percent', 0.95),
    )
    
    def __init__(self):
        self.order = None
        self.fast_ma = bt.ind.SMA(self.data.close, period=self.p.fast_period)
        self.slow_ma = bt.ind.SMA(self.data.close, period=self.p.slow_period)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入：价格={order.executed.price:.2f}')
            else:
                self.log(f'卖出：价格={order.executed.price:.2f}')
        self.order = None
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        logger.debug(f'{dt.isoformat()} {txt}')
    
    def next(self):
        if self.order:
            return
        
        if self.crossover > 0 and not self.getposition().size:
            available_cash = self.broker.getcash() * self.p.stake_percent
            size = int(available_cash / self.data.close[0] / 100) * 100
            if size >= 100:
                self.order = self.buy(size=size)
        
        elif self.crossover < 0 and self.getposition().size:
            self.order = self.close()


class BollingerStrategy(bt.Strategy):
    """布林带策略"""
    
    params = (
        ('period', 20),
        ('num_std', 2.0),
        ('stake_percent', 0.95),
    )
    
    def __init__(self):
        self.order = None
        self.bb = bt.ind.BollingerBands(
            self.data.close,
            period=self.p.period,
            devfactor=self.p.num_std
        )
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入：价格={order.executed.price:.2f}')
            else:
                self.log(f'卖出：价格={order.executed.price:.2f}')
        self.order = None
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        logger.debug(f'{dt.isoformat()} {txt}')
    
    def next(self):
        if self.order:
            return
        
        # 价格从下轨下方穿回买入
        if self.data.close[0] < self.bb.bot[0] and not self.getposition().size:
            available_cash = self.broker.getcash() * self.p.stake_percent
            size = int(available_cash / self.data.close[0] / 100) * 100
            if size >= 100:
                self.order = self.buy(size=size)
        
        # 价格从上轨上方穿回卖出
        elif self.data.close[0] > self.bb.top[0] and self.getposition().size:
            self.order = self.close()


# ==================== 回测引擎 ====================

class BacktraderEngine:
    """Backtrader 回测引擎"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化回测引擎
        
        Args:
            config: 配置字典，包含：
                - initial_capital: 初始资金 (默认 100 万)
                - commission_rate: 手续费率 (默认 0.0005)
                - stamp_duty_rate: 印花税率 (默认 0.001)
                - slippage: 滑点 (默认 0.002)
        """
        self.config = config or {}
        self.initial_capital = self.config.get('initial_capital', 1000000)
        self.commission_rate = self.config.get('commission_rate', 0.0005)
        self.stamp_duty_rate = self.config.get('stamp_duty_rate', 0.001)
        self.slippage = self.config.get('slippage', 0.002)
        
        self.cerebro = None
        self.results = None
        self.data = None
    
    def fetch_data(self, code: str, start_date: str, end_date: str,
                   timeframe: str = 'daily') -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            code: 股票代码 (如 '000001.SZ' 或 'sh.600000')
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            timeframe: 时间周期 'daily' 或 'minute'
            
        Returns:
            pd.DataFrame: 包含 OHLCV 数据的 DataFrame
        """
        logger.info(f"📡 获取 {code} 数据：{start_date} → {end_date} ({timeframe})")
        
        # 转换代码格式
        if '.' in code and not code.startswith(('sh.', 'sz.')):
            parts = code.split('.')
            code = f"{parts[1].lower()}.{parts[0]}"
        
        try:
            import baostock as bs
            lg = bs.login()
            
            # 计算交易日数量（多获取一些用于指标计算）
            start = pd.to_datetime(start_date) - timedelta(days=60)
            end = pd.to_datetime(end_date)
            
            if timeframe == 'minute':
                # 获取分钟线数据
                rs = bs.query_history_k_data_plus(
                    code,
                    "date,time,open,high,low,close,volume,amount",
                    start_date=start.strftime('%Y-%m-%d'),
                    end_date=end.strftime('%Y-%m-%d'),
                    frequency="5",  # 5 分钟线
                    adjustflag="3"
                )
            else:
                # 获取日线数据
                rs = bs.query_history_k_data_plus(
                    code,
                    "date,open,high,low,close,volume,amount",
                    start_date=start.strftime('%Y-%m-%d'),
                    end_date=end.strftime('%Y-%m-%d'),
                    frequency="d",
                    adjustflag="3"
                )
            
            data_list = []
            while (rs.error_code == '0') and rs.next():
                row = rs.get_row_data()
                if len(row) >= 6 and row[4]:  # close 不为空
                    if timeframe == 'minute':
                        data_list.append({
                            'datetime': f"{row[0]} {row[1]}",
                            'open': float(row[2] or 0),
                            'high': float(row[3] or 0),
                            'low': float(row[4] or 0),
                            'close': float(row[5] or 0),
                            'volume': float(row[6] or 0),
                        })
                    else:
                        data_list.append({
                            'date': row[0],
                            'open': float(row[1] or 0),
                            'high': float(row[2] or 0),
                            'low': float(row[3] or 0),
                            'close': float(row[4] or 0),
                            'volume': float(row[5] or 0),
                        })
            
            bs.logout()
            
            if not data_list:
                raise ValueError(f"未获取到 {code} 的数据")
            
            df = pd.DataFrame(data_list)
            
            if timeframe == 'minute':
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df.set_index('datetime').sort_index()
            else:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
            
            # 过滤到指定时间段
            df = df[start_date:end]
            
            logger.info(f"✅ 数据获取成功：{len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.warning(f"❌ 数据获取失败：{e}")
            return self._generate_mock_data(start_date, end_date, timeframe)
    
    def _generate_mock_data(self, start_date: str, end_date: str,
                           timeframe: str = 'daily') -> pd.DataFrame:
        """生成模拟数据用于测试"""
        logger.warning("⚠️  使用模拟数据进行演示")
        
        if timeframe == 'minute':
            dates = pd.date_range(start_date, end_date, freq='5T')  # 5 分钟
        else:
            dates = pd.date_range(start_date, end_date, freq='B')  # 工作日
        
        n = len(dates)
        
        # 生成随机价格序列（几何布朗运动）
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, n)
        price = 10 * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'open': price * (1 + np.random.uniform(-0.01, 0.01, n)),
            'high': price * (1 + np.random.uniform(0, 0.02, n)),
            'low': price * (1 - np.random.uniform(0, 0.02, n)),
            'close': price,
            'volume': np.random.randint(1000000, 10000000, n)
        }, index=dates)
        
        return df
    
    def _setup_cerebro(self):
        """设置 Cerebro 引擎"""
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(self.initial_capital)
        
        # 设置手续费（佣金 + 印花税）
        total_commission = self.commission_rate + self.stamp_duty_rate
        self.cerebro.broker.setcommission(commission=total_commission)
        
        # 设置滑点
        self.cerebro.broker.set_slippage_perc(self.slippage)
        
        logger.info(f"💰 初始资金：{self.initial_capital:,.0f} 元")
        logger.info(f"📊 手续费率：{total_commission*100:.3f}%")
        logger.info(f"📉 滑点：{self.slippage*100:.2f}%")
    
    def add_data(self, df: pd.DataFrame, name: str = 'data',
                 timeframe: str = 'daily'):
        """
        添加数据到 Cerebro
        
        Args:
            df: DataFrame，需包含 OHLCV 列
            name: 数据名称
            timeframe: 时间周期 'daily' 或 'minute'
        """
        self.data = df
        
        if timeframe == 'minute':
            # 分钟线数据
            data = bt.feeds.PandasData(
                dataname=df,
                datetime=-1,
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            # 设置分钟线 timeframe
            self.cerebro.adddata(data, name=name)
            self.cerebro.broker.set_coc(True)  # 允许当日成交
        else:
            # 日线数据
            data = bt.feeds.PandasData(
                dataname=df,
                datetime=-1,
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            self.cerebro.adddata(data, name=name)
        
        logger.info(f"📈 添加数据：{name}, {len(df)} 条记录")
    
    def add_analyzers(self):
        """添加分析器"""
        # 收益率
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # 夏普比率
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio,
                                _name='sharpe',
                                riskfreerate=0.03,
                                annualize=True,
                                timeframe=bt.TimeFrame.Days)
        
        # 最大回撤
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
        # 交易分析
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # SQN（系统质量比）
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        
        # 时间收益率
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return')
        
        # VWR（方差加权收益率）
        self.cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')
        
        logger.info("✅ 添加分析器完成")
    
    def run(self, strategy_class: bt.Strategy, **strategy_params) -> Dict:
        """
        运行回测
        
        Args:
            strategy_class: 策略类
            **strategy_params: 策略参数
            
        Returns:
            dict: 回测结果
        """
        logger.info("🚀 开始回测...")
        
        # 添加策略
        self.cerebro.addstrategy(strategy_class, **strategy_params)
        
        # 运行回测
        results = self.cerebro.run()
        strat = results[0]
        
        # 获取分析结果
        initial_cash = self.initial_capital
        final_cash = self.cerebro.broker.getvalue()
        total_return = (final_cash - initial_cash) / initial_cash
        
        # 提取分析器结果
        returns = strat.analyzers.returns.get_analysis()
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        sqn = strat.analyzers.sqn.get_analysis()
        vwr = strat.analyzers.vwr.get_analysis()
        
        # 计算额外指标
        winning_trades = trades.get('won', {}).get('total', 0)
        losing_trades = trades.get('lost', {}).get('total', 0)
        total_trades = trades.get('total', {}).get('total', 0)
        win_rate = winning_trades / max(total_trades, 1)
        
        # 计算 Sortino 比率
        time_returns = strat.analyzers.time_return.get_analysis()
        if time_returns:
            returns_series = pd.Series(list(time_returns.values()))
            downside_returns = returns_series[returns_series < 0]
            if len(downside_returns) > 0:
                downside_std = downside_returns.std()
                mean_return = returns_series.mean()
                sortino_ratio = (mean_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0
            else:
                sortino_ratio = 0
        else:
            sortino_ratio = 0
        
        metrics = {
            'initial_cash': initial_cash,
            'final_cash': final_cash,
            'total_return': total_return,
            'total_return_pct': f'{total_return * 100:.2f}%',
            'total_profit': final_cash - initial_cash,
            'sharpe_ratio': sharpe.get('sharperatio', None),
            'sortino_ratio': sortino_ratio,
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) / 100,
            'max_drawdown_pct': f"{drawdown.get('max', {}).get('drawdown', 0):.2f}%",
            'max_drawdown_money': drawdown.get('max', {}).get('moneydown', 0),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'win_rate_pct': f'{win_rate * 100:.1f}%',
            'sqn': sqn.get('sqn', 0),
            'vwr': vwr.get('vwr', 0),
        }
        
        logger.info(f"✅ 回测完成！总收益：{metrics['total_return_pct']}")
        
        self.results = {
            'metrics': metrics,
            'strategy': strat.__class__.__name__,
            'trading_days': len(self.data),
            'start_date': self.data.index[0].strftime('%Y-%m-%d') if hasattr(self.data.index[0], 'strftime') else str(self.data.index[0]),
            'end_date': self.data.index[-1].strftime('%Y-%m-%d') if hasattr(self.data.index[-1], 'strftime') else str(self.data.index[-1]),
        }
        
        return self.results
    
    def run_macd(self, code: str, start_date: str, end_date: str,
                 fast_period: int = 12, slow_period: int = 26,
                 signal_period: int = 9, timeframe: str = 'daily',
                 **kwargs) -> Dict:
        """
        运行 MACD 策略回测
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            fast_period: 快线周期 (默认 12)
            slow_period: 慢线周期 (默认 26)
            signal_period: 信号线周期 (默认 9)
            timeframe: 时间周期 'daily' 或 'minute'
            **kwargs: 其他配置参数
            
        Returns:
            dict: 回测结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("🚀 BobQuant Backtrader 回测 - MACD 策略")
        logger.info("=" * 60)
        logger.info(f"股票代码：  {code}")
        logger.info(f"时间段：    {start_date} → {end_date}")
        logger.info(f"时间周期：  {timeframe}")
        logger.info(f"MACD 参数：  {fast_period}/{slow_period}/{signal_period}")
        logger.info("=" * 60)
        
        # 获取数据
        df = self.fetch_data(code, start_date, end_date, timeframe)
        
        if len(df) < max(slow_period, fast_period) + 10:
            raise ValueError(f"数据量不足：需要至少 {max(slow_period, fast_period) + 10} 条记录")
        
        # 设置引擎
        self._setup_cerebro()
        
        # 添加数据
        self.add_data(df, name=code, timeframe=timeframe)
        
        # 添加分析器
        self.add_analyzers()
        
        # 运行回测
        results = self.run(
            MACDStrategy,
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period
        )
        
        # 添加策略信息
        results['strategy'] = {
            'name': 'MACD',
            'parameters': {
                'fast_period': fast_period,
                'slow_period': slow_period,
                'signal_period': signal_period
            }
        }
        results['code'] = code
        
        # 打印结果
        self._print_results(results)
        
        return results
    
    def run_rsi(self, code: str, start_date: str, end_date: str,
                rsi_period: int = 14, oversold: float = 30,
                overbought: float = 70, timeframe: str = 'daily',
                **kwargs) -> Dict:
        """运行 RSI 策略回测"""
        logger.info("\n" + "=" * 60)
        logger.info("🚀 BobQuant Backtrader 回测 - RSI 策略")
        logger.info("=" * 60)
        
        df = self.fetch_data(code, start_date, end_date, timeframe)
        
        self._setup_cerebro()
        self.add_data(df, name=code, timeframe=timeframe)
        self.add_analyzers()
        
        results = self.run(
            RSIStrategy,
            rsi_period=rsi_period,
            oversold=oversold,
            overbought=overbought
        )
        
        results['strategy'] = {
            'name': 'RSI',
            'parameters': {
                'rsi_period': rsi_period,
                'oversold': oversold,
                'overbought': overbought
            }
        }
        results['code'] = code
        
        self._print_results(results)
        return results
    
    def run_dual_ma(self, code: str, start_date: str, end_date: str,
                    fast_period: int = 5, slow_period: int = 20,
                    timeframe: str = 'daily', **kwargs) -> Dict:
        """运行双均线策略回测"""
        logger.info("\n" + "=" * 60)
        logger.info("🚀 BobQuant Backtrader 回测 - 双均线策略")
        logger.info("=" * 60)
        
        df = self.fetch_data(code, start_date, end_date, timeframe)
        
        self._setup_cerebro()
        self.add_data(df, name=code, timeframe=timeframe)
        self.add_analyzers()
        
        results = self.run(
            DualMAStrategy,
            fast_period=fast_period,
            slow_period=slow_period
        )
        
        results['strategy'] = {
            'name': 'Dual MA',
            'parameters': {
                'fast_period': fast_period,
                'slow_period': slow_period
            }
        }
        results['code'] = code
        
        self._print_results(results)
        return results
    
    def run_bollinger(self, code: str, start_date: str, end_date: str,
                      period: int = 20, num_std: float = 2.0,
                      timeframe: str = 'daily', **kwargs) -> Dict:
        """运行布林带策略回测"""
        logger.info("\n" + "=" * 60)
        logger.info("🚀 BobQuant Backtrader 回测 - 布林带策略")
        logger.info("=" * 60)
        
        df = self.fetch_data(code, start_date, end_date, timeframe)
        
        self._setup_cerebro()
        self.add_data(df, name=code, timeframe=timeframe)
        self.add_analyzers()
        
        results = self.run(
            BollingerStrategy,
            period=period,
            num_std=num_std
        )
        
        results['strategy'] = {
            'name': 'Bollinger Bands',
            'parameters': {
                'period': period,
                'num_std': num_std
            }
        }
        results['code'] = code
        
        self._print_results(results)
        return results
    
    def _print_results(self, results: Dict):
        """打印回测结果"""
        metrics = results.get('metrics', {})
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 回测结果")
        logger.info("=" * 60)
        logger.info(f"初始资金：    {metrics.get('initial_cash', 0):,.0f} 元")
        logger.info(f"最终权益：    {metrics.get('final_cash', 0):,.0f} 元")
        logger.info(f"总收益率：    {metrics.get('total_return_pct', 'N/A')}")
        logger.info(f"总利润：      {metrics.get('total_profit', 0):,.0f} 元")
        logger.info(f"年化收益：    N/A")  # 需要计算
        logger.info(f"最大回撤：    {metrics.get('max_drawdown_pct', 'N/A')}")
        logger.info(f"夏普比率：    {metrics.get('sharpe_ratio', 0):.2f}" if metrics.get('sharpe_ratio') else "夏普比率：N/A")
        logger.info(f"Sortino 比率：  {metrics.get('sortino_ratio', 0):.2f}")
        logger.info(f"交易次数：    {metrics.get('total_trades', 0)}")
        logger.info(f"胜率：        {metrics.get('win_rate_pct', 'N/A')}")
        logger.info(f"SQN:          {metrics.get('sqn', 0):.2f}")
        logger.info("=" * 60)
    
    def optimize_macd(self, code: str, start_date: str, end_date: str,
                      fast_range: Tuple[int, int] = (8, 20),
                      slow_range: Tuple[int, int] = (20, 40),
                      signal_range: Tuple[int, int] = (5, 15),
                      timeframe: str = 'daily') -> Dict:
        """
        MACD 参数优化（网格搜索）
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            fast_range: 快线周期范围 (min, max)
            slow_range: 慢线周期范围 (min, max)
            signal_range: 信号线周期范围 (min, max)
            timeframe: 时间周期
            
        Returns:
            dict: 最优参数和结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("🔬 Backtrader 参数优化 - MACD")
        logger.info("=" * 60)
        
        df = self.fetch_data(code, start_date, end_date, timeframe)
        self.data = df
        
        # 生成参数网格
        fast_windows = range(fast_range[0], fast_range[1] + 1, 2)
        slow_windows = range(slow_range[0], slow_range[1] + 1, 2)
        signal_windows = range(signal_range[0], signal_range[1] + 1, 2)
        
        total_combinations = len(fast_windows) * len(slow_windows) * len(signal_windows)
        logger.info(f"\n📊 参数网格：{len(fast_windows)} × {len(slow_windows)} × {len(signal_windows)} = "
                   f"{total_combinations} 种组合")
        
        best_sharpe = -np.inf
        best_params = None
        best_results = None
        
        count = 0
        for fast in fast_windows:
            for slow in slow_windows:
                for signal in signal_windows:
                    if fast >= slow:
                        continue
                    
                    count += 1
                    if count % 20 == 0:
                        logger.info(f"   进度：{count}/{total_combinations}")
                    
                    try:
                        # 设置引擎
                        self._setup_cerebro()
                        self.add_data(df, name=code, timeframe=timeframe)
                        
                        # 添加策略
                        self.cerebro.addstrategy(
                            MACDStrategy,
                            fast_period=fast,
                            slow_period=slow,
                            signal_period=signal
                        )
                        
                        # 添加分析器
                        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio,
                                                _name='sharpe',
                                                riskfreerate=0.03,
                                                annualize=True)
                        
                        # 运行
                        results = self.cerebro.run()
                        strat = results[0]
                        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
                        
                        if sharpe and sharpe > best_sharpe:
                            best_sharpe = sharpe
                            best_params = (fast, slow, signal)
                            
                            # 获取完整结果
                            self._setup_cerebro()
                            self.add_data(df, name=code, timeframe=timeframe)
                            self.add_analyzers()
                            best_results = self.run(
                                MACDStrategy,
                                fast_period=fast,
                                slow_period=slow,
                                signal_period=signal
                            )
                            
                    except Exception as e:
                        logger.warning(f"参数 ({fast},{slow},{signal}) 失败：{e}")
                        continue
        
        if best_params:
            logger.info("\n" + "=" * 60)
            logger.info("✅ 最优参数找到！")
            logger.info("=" * 60)
            logger.info(f"快线周期：  {best_params[0]}")
            logger.info(f"慢线周期：  {best_params[1]}")
            logger.info(f"信号周期：  {best_params[2]}")
            logger.info(f"夏普比率：  {best_sharpe:.2f}")
            logger.info("=" * 60)
            
            return {
                'best_params': {
                    'fast_period': best_params[0],
                    'slow_period': best_params[1],
                    'signal_period': best_params[2]
                },
                'best_sharpe': best_sharpe,
                'results': best_results
            }
        else:
            logger.warning("❌ 未找到有效参数")
            return {'error': 'No valid parameters found'}
    
    def compare_strategies(self, code: str, start_date: str, end_date: str,
                          strategies: List[str] = None,
                          timeframe: str = 'daily') -> Dict:
        """
        多策略对比分析
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            strategies: 策略列表 ['macd', 'rsi', 'dual_ma', 'bollinger']
            timeframe: 时间周期
            
        Returns:
            dict: 对比结果
        """
        if strategies is None:
            strategies = ['macd', 'rsi', 'dual_ma', 'bollinger']
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 Backtrader 多策略对比")
        logger.info("=" * 60)
        logger.info(f"股票代码：  {code}")
        logger.info(f"时间段：    {start_date} → {end_date}")
        logger.info(f"策略列表：  {', '.join(strategies)}")
        logger.info("=" * 60)
        
        results = {}
        comparison = []
        
        for strategy_name in strategies:
            try:
                if strategy_name == 'macd':
                    result = self.run_macd(code, start_date, end_date, timeframe=timeframe)
                elif strategy_name == 'rsi':
                    result = self.run_rsi(code, start_date, end_date, timeframe=timeframe)
                elif strategy_name == 'dual_ma':
                    result = self.run_dual_ma(code, start_date, end_date, timeframe=timeframe)
                elif strategy_name == 'bollinger':
                    result = self.run_bollinger(code, start_date, end_date, timeframe=timeframe)
                else:
                    continue
                
                results[strategy_name] = result
                
                # 提取对比指标
                metrics = result.get('metrics', {})
                comparison.append({
                    'strategy': strategy_name,
                    'total_return': metrics.get('total_return', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0) or 0,
                    'max_drawdown': metrics.get('max_drawdown', 0),
                    'total_trades': metrics.get('total_trades', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'sqn': metrics.get('sqn', 0),
                })
                
            except Exception as e:
                logger.warning(f"策略 {strategy_name} 回测失败：{e}")
                results[strategy_name] = {'error': str(e)}
        
        # 排序比较
        comparison_df = pd.DataFrame(comparison)
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 策略对比结果")
        logger.info("=" * 60)
        
        # 按收益率排序
        if len(comparison_df) > 0:
            logger.info("\n按总收益率排序:")
            sorted_by_return = comparison_df.sort_values('total_return', ascending=False)
            for _, row in sorted_by_return.iterrows():
                logger.info(f"  {row['strategy']:12s} 收益：{row['total_return']*100:7.2f}%  "
                           f"夏普：{row['sharpe_ratio']:6.2f}  "
                           f"回撤：{row['max_drawdown']*100:6.2f}%")
            
            # 按夏普比率排序
            logger.info("\n按夏普比率排序:")
            sorted_by_sharpe = comparison_df.sort_values('sharpe_ratio', ascending=False)
            for _, row in sorted_by_sharpe.iterrows():
                logger.info(f"  {row['strategy']:12s} 夏普：{row['sharpe_ratio']:6.2f}  "
                           f"收益：{row['total_return']*100:7.2f}%  "
                           f"回撤：{row['max_drawdown']*100:6.2f}%")
        
        logger.info("=" * 60)
        
        return {
            'code': code,
            'start_date': start_date,
            'end_date': end_date,
            'timeframe': timeframe,
            'results': results,
            'comparison': comparison,
            'comparison_df': comparison_df
        }
    
    def export_report(self, results: Dict, output_path: str):
        """
        导出回测报告
        
        Args:
            results: 回测结果
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 序列化结果
        report = {
            'report_time': datetime.now().isoformat(),
            'engine': 'backtrader',
            'summary': results.get('metrics', {}),
            'strategy': results.get('strategy', {}),
            'config': {
                'initial_capital': self.initial_capital,
                'commission_rate': self.commission_rate,
                'stamp_duty_rate': self.stamp_duty_rate,
                'slippage': self.slippage
            },
            'trading_days': results.get('trading_days', 0),
            'start_date': results.get('start_date', ''),
            'end_date': results.get('end_date', ''),
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📄 回测报告已保存：{output_path}")
        return report
    
    def plot(self, filename: str = None):
        """
        绘制回测结果
        
        Args:
            filename: 保存文件名（可选）
        """
        if self.cerebro:
            if filename:
                self.cerebro.plot(style='candlestick', filename=filename)
            else:
                self.cerebro.plot(style='candlestick')


# ==================== 快捷函数 ====================

def run_backtrader_backtest(config: Dict, stock_pool: List[Dict],
                            start_date: str, end_date: str,
                            strategy: str = 'macd',
                            timeframe: str = 'daily') -> Dict:
    """
    Backtrader 回测快捷函数
    
    Args:
        config: 配置字典
        stock_pool: 股票池
        start_date: 开始日期
        end_date: 结束日期
        strategy: 策略名称 ('macd', 'rsi', 'dual_ma', 'bollinger')
        timeframe: 时间周期 ('daily' 或 'minute')
        
    Returns:
        dict: 回测结果
    """
    engine = BacktraderEngine(config)
    
    # 对股票池中的每只股票进行回测
    all_results = []
    for stock in stock_pool[:5]:  # 限制为前 5 只股票
        code = stock['code']
        try:
            if strategy == 'macd':
                result = engine.run_macd(code, start_date, end_date, timeframe=timeframe)
            elif strategy == 'rsi':
                result = engine.run_rsi(code, start_date, end_date, timeframe=timeframe)
            elif strategy == 'dual_ma':
                result = engine.run_dual_ma(code, start_date, end_date, timeframe=timeframe)
            elif strategy == 'bollinger':
                result = engine.run_bollinger(code, start_date, end_date, timeframe=timeframe)
            else:
                result = engine.run_macd(code, start_date, end_date, timeframe=timeframe)
            
            all_results.append(result)
        except Exception as e:
            logger.error(f"❌ {code} 回测失败：{e}")
            all_results.append({'code': code, 'error': str(e)})
    
    # 汇总结果
    if all_results:
        valid_results = [r for r in all_results if 'metrics' in r]
        if valid_results:
            avg_return = np.mean([r['metrics']['total_return'] for r in valid_results])
            avg_sharpe = np.mean([r['metrics']['sharpe_ratio'] or 0 for r in valid_results])
            
            return {
                'engine': 'backtrader',
                'strategy': strategy,
                'stock_count': len(valid_results),
                'avg_return': avg_return,
                'avg_sharpe': avg_sharpe,
                'timeframe': timeframe,
                'individual_results': valid_results
            }
    
    return {'error': 'No results', 'engine': 'backtrader'}


def compare_engines(config: Dict, code: str, start_date: str, end_date: str,
                    strategy: str = 'macd') -> Dict:
    """
    对比 Backtrader 和 VectorBT 引擎性能
    
    Args:
        config: 配置字典
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        strategy: 策略名称
        
    Returns:
        dict: 对比结果
    """
    import time
    
    logger.info("\n" + "=" * 70)
    logger.info("🔬 回测引擎对比：Backtrader vs VectorBT")
    logger.info("=" * 70)
    
    results = {}
    
    # Backtrader 回测
    logger.info("\n⏱️  Backtrader 回测...")
    start_time = time.time()
    try:
        bt_engine = BacktraderEngine(config)
        if strategy == 'macd':
            bt_result = bt_engine.run_macd(code, start_date, end_date)
        else:
            bt_result = bt_engine.run_macd(code, start_date, end_date)
        
        bt_time = time.time() - start_time
        results['backtrader'] = {
            'result': bt_result,
            'time': bt_time,
            'metrics': bt_result.get('metrics', {})
        }
        logger.info(f"✅ Backtrader 完成：{bt_time:.2f}秒")
    except Exception as e:
        logger.error(f"❌ Backtrader 失败：{e}")
        results['backtrader'] = {'error': str(e), 'time': 0}
    
    # VectorBT 回测
    logger.info("\n⏱️  VectorBT 回测...")
    start_time = time.time()
    try:
        from .vectorbt_backtest import VectorBTBacktest
        vbt_engine = VectorBTBacktest(config)
        if strategy == 'macd':
            vbt_result = vbt_engine.run_macd(code, start_date, end_date)
        else:
            vbt_result = vbt_engine.run_macd(code, start_date, end_date)
        
        vbt_time = time.time() - start_time
        results['vectorbt'] = {
            'result': vbt_result,
            'time': vbt_time,
            'metrics': vbt_result.get('metrics', {})
        }
        logger.info(f"✅ VectorBT 完成：{vbt_time:.2f}秒")
    except Exception as e:
        logger.error(f"❌ VectorBT 失败：{e}")
        results['vectorbt'] = {'error': str(e), 'time': 0}
    
    # 对比分析
    logger.info("\n" + "=" * 70)
    logger.info("📊 引擎性能对比")
    logger.info("=" * 70)
    
    if 'backtrader' in results and 'vectorbt' in results:
        bt = results['backtrader']
        vbt = results['vectorbt']
        
        if 'metrics' in bt and 'metrics' in vbt:
            logger.info(f"\n运行时间:")
            logger.info(f"  Backtrader:  {bt['time']:6.2f}秒")
            logger.info(f"  VectorBT:    {vbt['time']:6.2f}秒")
            logger.info(f"  速度比：     {bt['time']/vbt['time']:.2f}x (Backtrader/VectorBT)")
            
            logger.info(f"\n总收益率:")
            logger.info(f"  Backtrader:  {bt['metrics'].get('total_return_pct', 'N/A'):>10}")
            logger.info(f"  VectorBT:    {vbt['metrics'].get('total_return_pct', 'N/A'):>10}")
            
            logger.info(f"\n夏普比率:")
            bt_sharpe = bt['metrics'].get('sharpe_ratio', 0) or 0
            vbt_sharpe = vbt['metrics'].get('sharpe_ratio', 0) or 0
            logger.info(f"  Backtrader:  {bt_sharpe:10.2f}")
            logger.info(f"  VectorBT:    {vbt_sharpe:10.2f}")
            
            logger.info(f"\n最大回撤:")
            logger.info(f"  Backtrader:  {bt['metrics'].get('max_drawdown_pct', 'N/A'):>10}")
            logger.info(f"  VectorBT:    {vbt['metrics'].get('max_drawdown_pct', 'N/A'):>10}")
            
            logger.info(f"\n交易次数:")
            logger.info(f"  Backtrader:  {bt['metrics'].get('total_trades', 0):10d}")
            logger.info(f"  VectorBT:    {vbt['metrics'].get('total_trades', 0):10d}")
    
    logger.info("=" * 70)
    
    return results


# ==================== 测试示例 ====================

if __name__ == '__main__':
    from loguru import logger
    logger.add("backtest.log", rotation="10 MB")
    
    print("=" * 60)
    print("BobQuant Backtrader 回测引擎 - 测试示例")
    print("=" * 60)
    
    # 配置
    config = {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'slippage': 0.002
    }
    
    # 初始化
    engine = BacktraderEngine(config)
    
    # 测试 MACD 策略
    results = engine.run_macd(
        code='000001.SZ',
        start_date='2024-01-01',
        end_date='2024-12-31',
        fast_period=12,
        slow_period=26,
        signal_period=9
    )
    
    # 导出报告
    report_path = 'backtest/reports/backtrader_macd_000001_2024.json'
    engine.export_report(results, report_path)
    
    print("\n✅ Backtrader 回测测试完成！")
