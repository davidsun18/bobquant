#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant VectorBT 回测引擎 v1.0

基于 VectorBT 的向量化回测系统，提供高性能回测能力。

特性：
1. 向量化计算，速度比传统循环快 10-100 倍
2. 支持多种技术指标（MACD, RSI, Bollinger Bands 等）
3. 自动计算绩效指标（夏普比率、最大回撤、年化收益等）
4. 支持参数优化和网格搜索

用法：
    from backtest.vectorbt_backtest import VectorBTBacktest
    
    # 初始化
    backtest = VectorBTBacktest(initial_capital=1000000)
    
    # 运行 MACD 策略回测
    results = backtest.run_macd(
        code='000001.SZ',
        start_date='2024-01-01',
        end_date='2024-12-31',
        fast_window=12,
        slow_window=26,
        signal_window=9
    )
    
    # 查看结果
    print(results['metrics'])
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import json
import os
import warnings

warnings.filterwarnings('ignore')

try:
    import vectorbt as vbt
    print(f"✅ VectorBT 版本：{vbt.__version__}")
except ImportError:
    raise ImportError("请安装 vectorbt: pip3 install vectorbt")

# 添加项目路径
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)


class VectorBTBacktest:
    """VectorBT 向量化回测引擎"""
    
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
        
        # 回测结果
        self.results = None
        self.portfolio = None
        self.data = None
    
    def fetch_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            code: 股票代码 (如 '000001.SZ' 或 'sh.600000')
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            
        Returns:
            pd.DataFrame: 包含 OHLCV 数据的 DataFrame
        """
        print(f"📡 获取 {code} 数据：{start_date} → {end_date}")
        
        # 转换代码格式
        if '.' in code and not code.startswith(('sh.', 'sz.')):
            # 000001.SZ -> sz.000001
            parts = code.split('.')
            code = f"{parts[1].lower()}.{parts[0]}"
        
        try:
            # 使用 baostock 获取数据
            import baostock as bs
            lg = bs.login()
            
            # 计算交易日数量（多获取一些用于指标计算）
            start = pd.to_datetime(start_date) - timedelta(days=60)
            end = pd.to_datetime(end_date)
            
            rs = bs.query_history_k_data_plus(
                code,
                "date,open,high,low,close,volume,amount",
                start_date=start.strftime('%Y-%m-%d'),
                end_date=end.strftime('%Y-%m-%d'),
                frequency="d",
                adjustflag="3"  # 后复权
            )
            
            data_list = []
            while (rs.error_code == '0') and rs.next():
                row = rs.get_row_data()
                if len(row) >= 6 and row[3]:  # close 不为空
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
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            
            # 过滤到指定时间段
            df = df[start_date:end]
            
            print(f"✅ 数据获取成功：{len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"❌ 数据获取失败：{e}")
            # 尝试使用备用数据源
            return self._fetch_data_fallback(code, start_date, end_date)
    
    def _fetch_data_fallback(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """备用数据获取方法"""
        print("⚠️  使用备用数据源...")
        
        # 生成模拟数据用于测试
        print("⚠️  使用模拟数据进行演示")
        return self._generate_mock_data(start_date, end_date)
    
    def _generate_mock_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟数据用于测试"""
        dates = pd.date_range(start_date, end_date, freq='B')
        n = len(dates)
        
        # 生成随机价格序列（几何布朗运动）
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, n)  # 日均收益 0.05%，波动 2%
        price = 10 * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'open': price * (1 + np.random.uniform(-0.01, 0.01, n)),
            'high': price * (1 + np.random.uniform(0, 0.02, n)),
            'low': price * (1 - np.random.uniform(0, 0.02, n)),
            'close': price,
            'volume': np.random.randint(1000000, 10000000, n)
        }, index=dates)
        
        return df
    
    def run_macd(self, code: str, start_date: str, end_date: str,
                 fast_window: int = 12, slow_window: int = 26,
                 signal_window: int = 9, **kwargs) -> Dict:
        """
        运行 MACD 策略回测
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            fast_window: 快线周期 (默认 12)
            slow_window: 慢线周期 (默认 26)
            signal_window: 信号线周期 (默认 9)
            **kwargs: 其他配置参数
            
        Returns:
            dict: 回测结果
        """
        print("\n" + "=" * 60)
        print("🚀 BobQuant VectorBT 回测 - MACD 策略")
        print("=" * 60)
        print(f"股票代码：  {code}")
        print(f"时间段：    {start_date} → {end_date}")
        print(f"MACD 参数：  {fast_window}/{slow_window}/{signal_window}")
        print("=" * 60)
        
        # 获取数据
        df = self.fetch_data(code, start_date, end_date)
        self.data = df
        
        if len(df) < max(slow_window, fast_window) + 10:
            raise ValueError(f"数据量不足：需要至少 {max(slow_window, fast_window) + 10} 条记录")
        
        # 使用 VectorBT 计算 MACD
        print("\n⚙️  计算 MACD 指标...")
        macd_fast = vbt.MA.run(df['close'], fast_window, short_name='fast')
        macd_slow = vbt.MA.run(df['close'], slow_window, short_name='slow')
        
        macd_line = macd_fast.ma - macd_slow.ma
        signal_line = vbt.MA.run(macd_line, signal_window, short_name='signal').ma
        hist = macd_line - signal_line
        
        # 生成交易信号
        print("📊 生成交易信号...")
        entries = macd_line.vbt.crossed_above(signal_line)
        exits = macd_line.vbt.crossed_below(signal_line)
        
        # 运行回测
        print("📈 运行回测...")
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=self.commission_rate + self.slippage,
            slippage=self.slippage,
            freq='1D'
        )
        
        self.portfolio = portfolio
        
        # 计算绩效指标
        results = self._calculate_metrics(df, portfolio, code)
        
        # 添加策略信息
        results['strategy'] = {
            'name': 'MACD',
            'parameters': {
                'fast_window': fast_window,
                'slow_window': slow_window,
                'signal_window': signal_window
            }
        }
        
        self.results = results
        return results
    
    def run_rsi(self, code: str, start_date: str, end_date: str,
                rsi_period: int = 14, oversold: float = 30,
                overbought: float = 70, **kwargs) -> Dict:
        """
        运行 RSI 策略回测
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            rsi_period: RSI 周期 (默认 14)
            oversold: 超卖阈值 (默认 30)
            overbought: 超买阈值 (默认 70)
            
        Returns:
            dict: 回测结果
        """
        print("\n" + "=" * 60)
        print("🚀 BobQuant VectorBT 回测 - RSI 策略")
        print("=" * 60)
        
        df = self.fetch_data(code, start_date, end_date)
        self.data = df
        
        # 计算 RSI
        print("⚙️  计算 RSI 指标...")
        rsi = vbt.RSI.run(df['close'], window=rsi_period)
        
        # 生成信号
        rsi_series = rsi.rsi if hasattr(rsi, 'rsi') else rsi
        entries = rsi_series.vbt.crossed_below(oversold)
        exits = rsi_series.vbt.crossed_above(overbought)
        
        # 运行回测
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=self.commission_rate + self.slippage,
            freq='1D'
        )
        
        self.portfolio = portfolio
        results = self._calculate_metrics(df, portfolio, code)
        
        results['strategy'] = {
            'name': 'RSI',
            'parameters': {
                'rsi_period': rsi_period,
                'oversold': oversold,
                'overbought': overbought
            }
        }
        
        self.results = results
        return results
    
    def run_bollinger(self, code: str, start_date: str, end_date: str,
                      window: int = 20, num_std: float = 2.0, **kwargs) -> Dict:
        """
        运行布林带策略回测
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            window: 周期 (默认 20)
            num_std: 标准差倍数 (默认 2.0)
            
        Returns:
            dict: 回测结果
        """
        print("\n" + "=" * 60)
        print("🚀 BobQuant VectorBT 回测 - 布林带策略")
        print("=" * 60)
        
        df = self.fetch_data(code, start_date, end_date)
        self.data = df
        
        # 计算布林带
        print("⚙️  计算布林带指标...")
        bb = vbt.BBANDS.run(df['close'], window=window, alpha=num_std)
        
        # 生成信号（价格从下轨下方穿回买入，从上轨上方穿回卖出）
        entries = df['close'].vbt.crossed_above(bb.bb_lower)
        exits = df['close'].vbt.crossed_below(bb.bb_upper)
        
        # 运行回测
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=self.commission_rate + self.slippage,
            freq='1D'
        )
        
        self.portfolio = portfolio
        results = self._calculate_metrics(df, portfolio, code)
        
        results['strategy'] = {
            'name': 'Bollinger Bands',
            'parameters': {
                'window': window,
                'num_std': num_std
            }
        }
        
        self.results = results
        return results
    
    def _calculate_metrics(self, df: pd.DataFrame, portfolio: vbt.Portfolio,
                          code: str) -> Dict:
        """
        计算绩效指标
        
        Args:
            df: 价格数据
            portfolio: VectorBT 组合对象
            code: 股票代码
            
        Returns:
            dict: 绩效指标
        """
        print("\n📊 计算绩效指标...")
        
        # 基础统计
        final_value = portfolio.value().iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # 年化收益率
        days = len(df)
        years = days / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 最大回撤
        max_drawdown = portfolio.max_drawdown()
        if isinstance(max_drawdown, pd.Series):
            max_drawdown = max_drawdown.iloc[0]
        
        # 夏普比率
        sharpe_ratio = portfolio.sharpe_ratio()
        if isinstance(sharpe_ratio, pd.Series):
            sharpe_ratio = sharpe_ratio.iloc[0]
        
        # 交易统计
        stats = portfolio.stats()
        total_trades = stats['Total Trades'] if 'Total Trades' in stats else 0
        winning_trades = stats['Winning Trades'] if 'Winning Trades' in stats else 0
        losing_trades = stats['Losing Trades'] if 'Losing Trades' in stats else 0
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 平均盈亏比
        avg_win = stats['Avg. Winning Trade'] if 'Avg. Winning Trade' in stats else 0
        avg_loss = stats['Avg. Losing Trade'] if 'Avg. Losing Trade' in stats else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # 构建结果
        metrics = {
            'total_return': total_return,
            'total_return_pct': f"{total_return * 100:.2f}%",
            'annual_return': annual_return,
            'annual_return_pct': f"{annual_return * 100:.2f}%",
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': f"{max_drawdown * 100:.2f}%",
            'sharpe_ratio': sharpe_ratio if sharpe_ratio else 0,
            'total_trades': int(total_trades),
            'winning_trades': int(winning_trades),
            'losing_trades': int(losing_trades),
            'win_rate': win_rate,
            'win_rate_pct': f"{win_rate * 100:.1f}%",
            'profit_factor': profit_factor,
            'final_value': final_value,
            'initial_capital': self.initial_capital,
            'total_profit': final_value - self.initial_capital
        }
        
        # 打印结果
        print("\n" + "=" * 60)
        print("📊 回测结果")
        print("=" * 60)
        print(f"初始资金：    {self.initial_capital:,.0f} 元")
        print(f"最终权益：    {final_value:,.0f} 元")
        print(f"总收益率：    {total_return * 100:+.2f}%")
        print(f"年化收益：    {annual_return * 100:+.2f}%")
        print(f"最大回撤：    {max_drawdown * 100:.2f}%")
        print(f"夏普比率：    {sharpe_ratio:.2f}" if sharpe_ratio else "夏普比率：N/A")
        print(f"交易次数：    {total_trades}")
        print(f"胜率：        {win_rate * 100:.1f}%")
        print(f"盈亏比：      {profit_factor:.2f}")
        print("=" * 60)
        
        return {
            'code': code,
            'metrics': metrics,
            'strategy': {},  # 由具体策略填充
            'trading_days': days,
            'start_date': df.index[0].strftime('%Y-%m-%d'),
            'end_date': df.index[-1].strftime('%Y-%m-%d')
        }
    
    def optimize_macd(self, code: str, start_date: str, end_date: str,
                      fast_range: Tuple[int, int] = (8, 20),
                      slow_range: Tuple[int, int] = (20, 40),
                      signal_range: Tuple[int, int] = (5, 15)) -> Dict:
        """
        MACD 参数优化（网格搜索）
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            fast_range: 快线周期范围 (min, max)
            slow_range: 慢线周期范围 (min, max)
            signal_range: 信号线周期范围 (min, max)
            
        Returns:
            dict: 最优参数和结果
        """
        print("\n" + "=" * 60)
        print("🔬 VectorBT 参数优化 - MACD")
        print("=" * 60)
        
        df = self.fetch_data(code, start_date, end_date)
        self.data = df
        
        # 生成参数网格
        fast_windows = range(fast_range[0], fast_range[1] + 1, 2)
        slow_windows = range(slow_range[0], slow_range[1] + 1, 2)
        signal_windows = range(signal_range[0], signal_range[1] + 1, 2)
        
        print(f"\n📊 参数网格：{len(fast_windows)} × {len(slow_windows)} × {len(signal_windows)} = "
              f"{len(fast_windows) * len(slow_windows) * len(signal_windows)} 种组合")
        
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
                        print(f"   进度：{count}/{len(fast_windows) * len(slow_windows) * len(signal_windows)}")
                    
                    try:
                        # 快速回测
                        macd_fast = vbt.MA.run(df['close'], fast, short_name='fast')
                        macd_slow = vbt.MA.run(df['close'], slow, short_name='slow')
                        macd_line = macd_fast.ma - macd_slow.ma
                        signal_line = vbt.MA.run(macd_line, signal, short_name='signal').ma
                        
                        entries = macd_line.vbt.crossed_above(signal_line)
                        exits = macd_line.vbt.crossed_below(signal_line)
                        
                        portfolio = vbt.Portfolio.from_signals(
                            close=df['close'],
                            entries=entries,
                            exits=exits,
                            init_cash=self.initial_capital,
                            fees=self.commission_rate,
                            freq='1D'
                        )
                        
                        sharpe = portfolio.sharpe_ratio()
                        if isinstance(sharpe, pd.Series):
                            sharpe = sharpe.iloc[0]
                        
                        if sharpe and sharpe > best_sharpe:
                            best_sharpe = sharpe
                            best_params = (fast, slow, signal)
                            best_results = self._calculate_metrics(df, portfolio, code)
                            
                    except Exception as e:
                        continue
        
        if best_params:
            print("\n" + "=" * 60)
            print("✅ 最优参数找到！")
            print("=" * 60)
            print(f"快线周期：  {best_params[0]}")
            print(f"慢线周期：  {best_params[1]}")
            print(f"信号周期：  {best_params[2]}")
            print(f"夏普比率：  {best_sharpe:.2f}")
            print("=" * 60)
            
            return {
                'best_params': {
                    'fast_window': best_params[0],
                    'slow_window': best_params[1],
                    'signal_window': best_params[2]
                },
                'best_sharpe': best_sharpe,
                'results': best_results
            }
        else:
            print("❌ 未找到有效参数")
            return {'error': 'No valid parameters found'}
    
    def export_report(self, results: Dict, output_path: str):
        """
        导出回测报告
        
        Args:
            results: 回测结果
            output_path: 输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        report = {
            'report_time': datetime.now().isoformat(),
            'engine': 'vectorbt',
            'summary': results['metrics'],
            'strategy': results.get('strategy', {}),
            'config': {
                'initial_capital': self.initial_capital,
                'commission_rate': self.commission_rate,
                'stamp_duty_rate': self.stamp_duty_rate
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 回测报告已保存：{output_path}")
        return report


def run_vectorbt_backtest(config: Dict, stock_pool: List[Dict],
                          start_date: str, end_date: str,
                          strategy: str = 'macd') -> Dict:
    """
    VectorBT 回测快捷函数
    
    Args:
        config: 配置字典
        stock_pool: 股票池
        start_date: 开始日期
        end_date: 结束日期
        strategy: 策略名称 ('macd', 'rsi', 'bollinger')
        
    Returns:
        dict: 回测结果
    """
    engine = VectorBTBacktest(config)
    
    # 对股票池中的每只股票进行回测
    all_results = []
    for stock in stock_pool[:5]:  # 限制为前 5 只股票
        code = stock['code']
        try:
            if strategy == 'macd':
                result = engine.run_macd(code, start_date, end_date)
            elif strategy == 'rsi':
                result = engine.run_rsi(code, start_date, end_date)
            elif strategy == 'bollinger':
                result = engine.run_bollinger(code, start_date, end_date)
            else:
                result = engine.run_macd(code, start_date, end_date)
            
            all_results.append(result)
        except Exception as e:
            print(f"❌ {code} 回测失败：{e}")
            all_results.append({'code': code, 'error': str(e)})
    
    # 汇总结果
    if all_results:
        valid_results = [r for r in all_results if 'metrics' in r]
        if valid_results:
            avg_return = np.mean([r['metrics']['total_return'] for r in valid_results])
            avg_sharpe = np.mean([r['metrics']['sharpe_ratio'] for r in valid_results])
            
            return {
                'engine': 'vectorbt',
                'strategy': strategy,
                'stock_count': len(valid_results),
                'avg_return': avg_return,
                'avg_sharpe': avg_sharpe,
                'individual_results': valid_results
            }
    
    return {'error': 'No results', 'engine': 'vectorbt'}


# 测试示例
if __name__ == '__main__':
    print("=" * 60)
    print("BobQuant VectorBT 回测引擎 - 测试示例")
    print("=" * 60)
    
    # 配置
    config = {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'slippage': 0.002
    }
    
    # 初始化
    backtest = VectorBTBacktest(config)
    
    # 测试 MACD 策略
    results = backtest.run_macd(
        code='000001.SZ',
        start_date='2024-01-01',
        end_date='2024-12-31',
        fast_window=12,
        slow_window=26,
        signal_window=9
    )
    
    # 导出报告
    report_path = 'backtest/reports/vectorbt_macd_000001_2024.json'
    backtest.export_report(results, report_path)
    
    print("\n✅ VectorBT 回测测试完成！")
