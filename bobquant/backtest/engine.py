# -*- coding: utf-8 -*-
"""
BobQuant 回测系统 v2.0

功能：
1. 历史数据回测
2. 关键指标计算（年化收益、最大回撤、夏普比率等）
3. 策略对比分析
4. 交易记录回放

v2.0 新增：
- 完整牛熊周期验证
- 多策略对比
- 风险调整收益指标
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

try:
    from ..indicator import technical as ta
    from ..strategy.engine import get_strategy, DecisionEngine
    from ..data.provider import DataProvider, get_provider
    from ..core.account import Account
except ImportError:
    from indicator import technical as ta
    from strategy.engine import get_strategy, DecisionEngine
    from data.provider import DataProvider, get_provider
    from core.account import Account


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config):
        self.config = config
        self.initial_capital = config.get('initial_capital', 1000000)
        self.commission_rate = config.get('commission_rate', 0.0005)
        self.stamp_duty_rate = config.get('stamp_duty_rate', 0.001)
        
        # 回测结果
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
    
    def run(self, stock_pool: List[Dict], start_date: str, end_date: str, 
            strategy_name: str = 'macd', initial_capital: Optional[float] = None):
        """
        运行回测
        
        Args:
            stock_pool: 股票池配置列表 [{'code': 'sh.600000', 'name': 'XXX', 'strategy': 'macd'}, ...]
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            strategy_name: 策略名称
            initial_capital: 初始资金
            
        Returns:
            dict: 回测结果
        """
        capital = initial_capital or self.initial_capital
        account = Account(capital, self.commission_rate, self.stamp_duty_rate)
        
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        
        # 获取交易日历
        trading_days = self._get_trading_days(start_date, end_date)
        
        print(f"🚀 开始回测：{start_date} → {end_date}")
        print(f"📊 股票池：{len(stock_pool)} 只股票")
        print(f"💰 初始资金：{capital:,.0f}")
        print(f"📈 策略：{strategy_name}")
        print("-" * 60)
        
        # 初始化策略
        strategy = get_strategy(strategy_name)
        if hasattr(strategy, 'config'):
            strategy.config = self.config
        
        # 逐日回测
        prev_equity = capital
        for i, date in enumerate(trading_days):
            # 获取当日行情
            daily_signals = []
            
            for stock in stock_pool:
                code = stock['code']
                name = stock.get('name', '')
                
                # 获取历史数据（截至当日）
                df = self._get_history_until(code, date, days=60)
                if df is None or len(df) < 30:
                    continue
                
                # 获取当日 quote
                quote = self._get_quote_from_df(df)
                if quote is None:
                    continue
                
                # 获取持仓
                pos = account.get_position(code)
                
                # 检查信号
                signal_result = strategy.check(code, name, quote, df, pos, self.config)
                
                if signal_result and signal_result.get('signal'):
                    daily_signals.append({
                        'code': code,
                        'name': name,
                        'signal': signal_result['signal'],
                        'reason': signal_result.get('reason', ''),
                        'strength': signal_result.get('strength', 'normal')
                    })
            
            # 执行交易
            for sig in daily_signals:
                code = sig['code']
                quote = self._get_latest_quote(code, trading_days[:i+1])
                
                if sig['signal'] == 'buy':
                    # 买入逻辑
                    result = self._execute_buy(account, code, sig['name'], quote, sig['reason'])
                    if result['executed']:
                        self.trades.append({
                            'date': date,
                            'code': code,
                            'name': sig['name'],
                            'action': 'buy',
                            'price': result['price'],
                            'shares': result['shares'],
                            'reason': sig['reason']
                        })
                
                elif sig['signal'] == 'sell':
                    # 卖出逻辑
                    result = self._execute_sell(account, code, quote, sig['reason'])
                    if result['executed']:
                        self.trades.append({
                            'date': date,
                            'code': code,
                            'name': sig['name'],
                            'action': 'sell',
                            'price': result['price'],
                            'shares': result['shares'],
                            'reason': sig['reason']
                        })
            
            # 记录当日权益
            current_equity = self._calculate_equity(account, trading_days[i])
            self.equity_curve.append({
                'date': date,
                'equity': current_equity,
                'cash': account.cash,
                'position_value': current_equity - account.cash
            })
            
            # 计算日收益率
            if prev_equity > 0:
                daily_return = (current_equity - prev_equity) / prev_equity
                self.daily_returns.append(daily_return)
            prev_equity = current_equity
            
            # 进度显示
            if (i + 1) % 20 == 0 or i == len(trading_days) - 1:
                print(f"  进度：{i+1}/{len(trading_days)} 交易日，权益：{current_equity:,.0f} ({(current_equity/capital-1)*100:+.1f}%)")
        
        print("-" * 60)
        
        # 计算回测指标
        results = self._calculate_metrics(capital, start_date, end_date)
        
        return {
            'config': {
                'stock_pool_size': len(stock_pool),
                'start_date': start_date,
                'end_date': end_date,
                'strategy': strategy_name,
                'initial_capital': capital
            },
            'metrics': results,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'daily_returns': self.daily_returns
        }
    
    def _get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日历（简化版，实际应使用交易所日历）"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # 生成日期范围（排除周末）
        all_days = pd.date_range(start, end, freq='B')  # B = 工作日
        return [d.strftime('%Y-%m-%d') for d in all_days]
    
    def _get_history_until(self, code: str, date: str, days: int = 60) -> Optional[pd.DataFrame]:
        """获取截至某日的历史数据"""
        end = pd.to_datetime(date)
        start = end - timedelta(days=days)
        
        try:
            df = fetcher.get_history_data(code, days=days)
            if df is not None and len(df) > 0:
                # 确保日期格式
                if 'time' in df.columns:
                    df['date'] = pd.to_datetime(df['time'])
                return df
        except Exception as e:
            print(f"  获取 {code} 数据失败：{e}")
        
        return None
    
    def _get_quote_from_df(self, df: pd.DataFrame) -> Optional[Dict]:
        """从 DataFrame 提取 quote"""
        if df is None or len(df) == 0:
            return None
        
        latest = df.iloc[-1]
        return {
            'current': latest['close'],
            'open': latest.get('open', latest['close']),
            'high': latest.get('high', latest['close']),
            'low': latest.get('low', latest['close']),
            'volume': latest.get('volume', 0)
        }
    
    def _get_latest_quote(self, code: str, trading_days: List[str]) -> Optional[Dict]:
        """获取最新行情"""
        if not trading_days:
            return None
        
        df = self._get_history_until(code, trading_days[-1], days=2)
        return self._get_quote_from_df(df)
    
    def _execute_buy(self, account: Account, code: str, name: str, quote: Dict, reason: str) -> Dict:
        """执行买入"""
        if quote is None or quote['current'] <= 0:
            return {'executed': False}
        
        # 计算买入数量（简化：固定金额买入）
        buy_amount = min(account.cash * 0.1, 50000)  # 最多用 10% 现金或 5 万
        price = quote['current']
        shares = int(buy_amount / price / 100) * 100  # 100 股整数倍
        
        if shares < 100:
            return {'executed': False}
        
        # 执行买入
        cost = shares * price * (1 + self.commission_rate)
        if cost > account.cash:
            shares = int(account.cash / price / 100) * 100
            if shares < 100:
                return {'executed': False}
            cost = shares * price * (1 + self.commission_rate)
        
        account.buy(code, name, shares, price)
        
        return {
            'executed': True,
            'price': price,
            'shares': shares,
            'cost': cost
        }
    
    def _execute_sell(self, account: Account, code: str, quote: Dict, reason: str) -> Dict:
        """执行卖出"""
        if quote is None or quote['current'] <= 0:
            return {'executed': False}
        
        pos = account.get_position(code)
        if not pos or pos.get('shares', 0) <= 0:
            return {'executed': False}
        
        shares = pos['shares']
        price = quote['current']
        
        # 执行卖出
        account.sell(code, shares, price)
        
        return {
            'executed': True,
            'price': price,
            'shares': shares,
            'revenue': shares * price * (1 - self.commission_rate - self.stamp_duty_rate)
        }
    
    def _calculate_equity(self, account: Account, date: str) -> float:
        """计算总权益"""
        # 简化：假设持仓市值按最新收盘价计算
        position_value = 0
        for code, pos in account.positions.items():
            # 获取最新价格（简化处理）
            if pos.get('shares', 0) > 0:
                position_value += pos['shares'] * pos['avg_price']  # 简化：用成本价代替
        
        return account.cash + position_value
    
    def _calculate_metrics(self, initial_capital: float, start_date: str, end_date: str) -> Dict:
        """计算回测指标"""
        if not self.equity_curve:
            return {'error': '无回测数据'}
        
        final_equity = self.equity_curve[-1]['equity']
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 计算年化收益率
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        days = (end - start).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown()
        
        # 计算夏普比率
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # 计算胜率
        win_trades = len([t for t in self.trades if t['action'] == 'sell'])  # 简化
        total_trades = len(self.trades)
        win_rate = win_trades / max(total_trades, 1)
        
        # 交易统计
        buy_trades = len([t for t in self.trades if t['action'] == 'buy'])
        sell_trades = len([t for t in self.trades if t['action'] == 'sell'])
        
        return {
            'total_return': total_return,
            'total_return_pct': f"{total_return*100:.2f}%",
            'annual_return': annual_return,
            'annual_return_pct': f"{annual_return*100:.2f}%",
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': f"{max_drawdown*100:.2f}%",
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'final_equity': final_equity,
            'initial_capital': initial_capital,
            'trading_days': len(self.equity_curve),
            'start_date': start_date,
            'end_date': end_date
        }
    
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.equity_curve:
            return 0
        
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0
        
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> float:
        """计算夏普比率"""
        if not self.daily_returns or len(self.daily_returns) < 2:
            return 0
        
        returns = pd.Series(self.daily_returns)
        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        
        if returns.std() == 0:
            return 0
        
        sharpe = excess_returns.mean() / returns.std() * np.sqrt(252)  # 年化
        return sharpe
    
    def export_report(self, results: Dict, output_path: str):
        """导出回测报告"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        report = {
            'report_time': datetime.now().isoformat(),
            'summary': results['metrics'],
            'config': results['config'],
            'trade_count': len(results['trades']),
            'recent_trades': results['trades'][-20:]  # 最近 20 笔交易
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 回测报告已保存：{output_path}")
        
        return report


def run_backtest(config, stock_pool, start_date, end_date, strategy='macd', engine_type=None):
    """
    快捷回测函数
    
    Args:
        config: 配置字典
        stock_pool: 股票池
        start_date: 开始日期
        end_date: 结束日期
        strategy: 策略名称
        engine_type: 回测引擎类型 ('traditional' 或 'vectorbt')，默认从 config 读取
    """
    # 确定使用哪个引擎
    if engine_type is None:
        engine_type = config.get('backtest', {}).get('engine', 'traditional')
    
    if engine_type == 'vectorbt':
        # 使用 VectorBT 引擎
        try:
            from .vectorbt_backtest import run_vectorbt_backtest
            print(f"\n🚀 使用 VectorBT 向量化回测引擎")
            results = run_vectorbt_backtest(config, stock_pool, start_date, end_date, strategy)
            results['engine'] = 'vectorbt'
        except ImportError as e:
            print(f"⚠️  VectorBT 未安装，回退到传统引擎：{e}")
            engine_type = 'traditional'
    
    if engine_type == 'traditional':
        # 使用传统引擎
        print(f"\n🚀 使用传统回测引擎")
        engine = BacktestEngine(config)
        results = engine.run(stock_pool, start_date, end_date, strategy)
        results['engine'] = 'traditional'
    
    # 打印回测摘要
    print("\n" + "=" * 60)
    print("📊 回测结果摘要")
    print("=" * 60)
    
    if results.get('engine') == 'vectorbt':
        # VectorBT 结果格式
        print(f"回测引擎：  {results.get('engine', 'N/A')}")
        print(f"策略：      {results.get('strategy', 'N/A')}")
        print(f"股票数量：  {results.get('stock_count', 0)}")
        print(f"平均收益：  {results.get('avg_return', 0)*100:.2f}%")
        print(f"平均夏普：  {results.get('avg_sharpe', 0):.2f}")
    else:
        # 传统结果格式
        metrics = results.get('metrics', {})
        print(f"总收益率：  {metrics.get('total_return_pct', 'N/A')}")
        print(f"年化收益：  {metrics.get('annual_return_pct', 'N/A')}")
        print(f"最大回撤：  {metrics.get('max_drawdown_pct', 'N/A')}")
        print(f"夏普比率：  {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"交易次数：  {metrics.get('total_trades', 0)}")
        print(f"胜率：      {metrics.get('win_rate', 0)*100:.1f}%")
    
    print("=" * 60)
    
    return results
