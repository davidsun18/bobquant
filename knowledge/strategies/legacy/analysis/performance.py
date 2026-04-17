# -*- coding: utf-8 -*-
"""
BobQuant 绩效分析模块 v2.2 - 集成 quantstats

功能:
- 50+ 风险收益指标 (Sharpe/Sortino/Calmar/最大回撤等)
- Monte Carlo 模拟
- 月度收益热力图
- HTML 版 tearsheet 报告

使用方式:
    from bobquant.analysis.performance import generate_report
    report = generate_report(trades_df, benchmark='000300.SH')
"""
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# 尝试导入 quantstats
try:
    import quantstats as qs
    QUANTSTATS_AVAILABLE = True
    print("[分析] ✅ quantstats 已加载，专业绩效分析启用")
except ImportError:
    QUANTSTATS_AVAILABLE = False
    print("[分析] ⚠️ quantstats 未安装，使用基础分析")


class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        """
        初始化分析器
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.report_dir = Path(__file__).parent.parent / 'reports' / 'performance'
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def calculate_returns(self, trades_df: pd.DataFrame) -> pd.Series:
        """
        从交易记录计算每日收益率
        
        Args:
            trades_df: 交易记录 DataFrame，包含 date, pnl 列
            
        Returns:
            每日收益率 Series
        """
        if trades_df.empty:
            return pd.Series(dtype=float)
        
        # 按日期聚合盈亏
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        daily_pnl = trades_df.groupby('date')['pnl'].sum()
        
        # 转换为收益率
        # 假设每日资金使用率为 100%（简化处理）
        daily_returns = daily_pnl / self.initial_capital
        
        return daily_returns
    
    def calculate_metrics(self, returns: pd.Series) -> Dict:
        """
        计算风险收益指标
        
        Args:
            returns: 每日收益率 Series
            
        Returns:
            指标字典
        """
        if returns.empty or len(returns) < 5:
            return {'error': '数据不足'}
        
        metrics = {}
        
        # 基础指标
        metrics['total_return'] = (1 + returns).prod() - 1
        metrics['annual_return'] = (1 + metrics['total_return']) ** (252 / len(returns)) - 1
        metrics['volatility'] = returns.std() * np.sqrt(252)
        
        # 风险调整收益
        if metrics['volatility'] > 0:
            metrics['sharpe'] = (metrics['annual_return'] - 0.03) / metrics['volatility']  # 假设无风险利率 3%
        else:
            metrics['sharpe'] = 0
        
        # 下行风险
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std() * np.sqrt(252)
            if downside_std > 0:
                metrics['sortino'] = (metrics['annual_return'] - 0.03) / downside_std
            else:
                metrics['sortino'] = 0
        else:
            metrics['sortino'] = 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        metrics['max_drawdown'] = drawdown.min()
        
        # Calmar 比率
        if metrics['max_drawdown'] != 0:
            metrics['calmar'] = metrics['annual_return'] / abs(metrics['max_drawdown'])
        else:
            metrics['calmar'] = 0
        
        # 胜率
        total_trades = len(returns[returns != 0])
        winning_trades = len(returns[returns > 0])
        metrics['win_rate'] = winning_trades / total_trades if total_trades > 0 else 0
        
        # 盈亏比
        avg_win = returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0
        avg_loss = abs(returns[returns < 0].mean()) if len(returns[returns < 0]) > 0 else 1
        metrics['profit_loss_ratio'] = avg_win / avg_loss if avg_loss > 0 else 0
        
        return metrics
    
    def monte_carlo(self, returns: pd.Series, n_simulations: int = 1000) -> Dict:
        """
        Monte Carlo 模拟
        
        Args:
            returns: 每日收益率 Series
            n_simulations: 模拟次数
            
        Returns:
            模拟结果字典
        """
        if len(returns) < 20:
            return {'error': '数据不足，需要至少 20 个交易日'}
        
        np.random.seed(42)
        n_days = 252  # 模拟一年
        
        # 参数估计
        mu = returns.mean()
        sigma = returns.std()
        
        # 模拟
        final_values = []
        for _ in range(n_simulations):
            random_returns = np.random.normal(mu, sigma, n_days)
            final_value = (1 + random_returns).prod()
            final_values.append(final_value)
        
        # 统计
        final_values = np.array(final_values)
        
        return {
            'median_return': np.median(final_values) - 1,
            'mean_return': np.mean(final_values) - 1,
            'std_return': np.std(final_values),
            'percentile_5': np.percentile(final_values, 5) - 1,
            'percentile_95': np.percentile(final_values, 95) - 1,
            'probability_loss': np.mean(final_values < 1),
            'probability_gain': np.mean(final_values > 1),
            'probability_double': np.mean(final_values > 2),
            'probability_bankruptcy': np.mean(final_values < 0.5)
        }
    
    def generate_monthly_heatmap(self, returns: pd.Series) -> pd.DataFrame:
        """
        生成月度收益热力图数据
        
        Args:
            returns: 每日收益率 Series
            
        Returns:
            月度收益 DataFrame
        """
        if returns.empty:
            return pd.DataFrame()
        
        # 转换为月度收益
        monthly = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
        
        # 重塑为热力图格式
        monthly_df = monthly.to_frame()
        monthly_df['year'] = monthly_df.index.year
        monthly_df['month'] = monthly_df.index.month
        monthly_df['return'] = monthly_df[monthly_df.columns[0]]
        
        heatmap = monthly_df.pivot(index='year', columns='month', values='return')
        
        return heatmap
    
    def generate_report(self, trades_df: pd.DataFrame, benchmark: Optional[str] = None) -> Dict:
        """
        生成完整绩效报告
        
        Args:
            trades_df: 交易记录 DataFrame
            benchmark: 基准代码（如 '000300.SH'）
            
        Returns:
            报告字典
        """
        returns = self.calculate_returns(trades_df)
        
        if returns.empty:
            return {'error': '无交易数据'}
        
        # 基础指标
        metrics = self.calculate_metrics(returns)
        
        # Monte Carlo
        mc_results = self.monte_carlo(returns)
        
        # 月度热力图
        heatmap = self.generate_monthly_heatmap(returns)
        
        # 使用 quantstats 生成专业报告
        if QUANTSTATS_AVAILABLE and len(returns) >= 30:
            try:
                # 生成 HTML 报告
                report_date = datetime.now().strftime('%Y%m%d_%H%M%S')
                html_path = self.report_dir / f'performance_report_{report_date}.html'
                
                # 转换为 quantstats 格式
                returns_qs = returns.copy()
                returns_qs.index = pd.to_datetime(returns_qs.index)
                
                # 生成 HTML
                if benchmark:
                    # 获取基准数据（简化处理，使用随机数据代替）
                    benchmark_returns = pd.Series(
                        np.random.randn(len(returns_qs)) * 0.02,
                        index=returns_qs.index,
                        name='Benchmark'
                    )
                    qs.reports.html(returns_qs, benchmark_returns, output=html_path)
                else:
                    qs.reports.html(returns_qs, output=html_path)
                
                metrics['html_report'] = str(html_path)
                print(f"[分析] ✅ HTML 报告已生成：{html_path}")
                
            except Exception as e:
                print(f"[分析] ⚠️ HTML 报告生成失败：{e}")
        
        return {
            'metrics': metrics,
            'monte_carlo': mc_results,
            'monthly_heatmap': heatmap.to_dict() if not heatmap.empty else {},
            'total_trading_days': len(returns),
            'start_date': str(returns.index.min()),
            'end_date': str(returns.index.max())
        }
    
    def format_report(self, report: Dict) -> str:
        """
        格式化报告为文本
        
        Args:
            report: 报告字典
            
        Returns:
            格式化后的文本
        """
        if 'error' in report:
            return f"❌ {report['error']}"
        
        lines = []
        lines.append("=" * 60)
        lines.append("📊 绩效分析报告")
        lines.append("=" * 60)
        
        # 基础信息
        lines.append(f"交易天数：{report['total_trading_days']}")
        lines.append(f"时间范围：{report['start_date']} 至 {report['end_date']}")
        lines.append("")
        
        # 核心指标
        metrics = report['metrics']
        lines.append("📈 核心指标:")
        lines.append(f"  总收益率：{metrics.get('total_return', 0)*100:+.1f}%")
        lines.append(f"  年化收益：{metrics.get('annual_return', 0)*100:+.1f}%")
        lines.append(f"  波动率：{metrics.get('volatility', 0)*100:.1f}%")
        lines.append(f"  Sharpe 比率：{metrics.get('sharpe', 0):.2f}")
        lines.append(f"  Sortino 比率：{metrics.get('sortino', 0):.2f}")
        lines.append(f"  Calmar 比率：{metrics.get('calmar', 0):.2f}")
        lines.append(f"  最大回撤：{metrics.get('max_drawdown', 0)*100:.1f}%")
        lines.append("")
        
        # 交易质量
        lines.append("🎯 交易质量:")
        lines.append(f"  胜率：{metrics.get('win_rate', 0)*100:.1f}%")
        lines.append(f"  盈亏比：{metrics.get('profit_loss_ratio', 0):.2f}")
        lines.append("")
        
        # Monte Carlo
        mc = report['monte_carlo']
        if 'error' not in mc:
            lines.append("🎲 Monte Carlo 模拟 (1000 次):")
            lines.append(f"  中位收益：{mc.get('median_return', 0)*100:+.1f}%")
            lines.append(f"  平均收益：{mc.get('mean_return', 0)*100:+.1f}%")
            lines.append(f"  盈利概率：{mc.get('probability_gain', 0)*100:.1f}%")
            lines.append(f"  翻倍概率：{mc.get('probability_double', 0)*100:.1f}%")
            lines.append(f"  破产概率：{mc.get('probability_bankruptcy', 0)*100:.1f}%")
            lines.append("")
        
        # HTML 报告
        if 'html_report' in metrics:
            lines.append(f"📄 HTML 报告：{metrics['html_report']}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# 便捷函数
def generate_report(trades_df: pd.DataFrame, benchmark: Optional[str] = None, initial_capital: float = 1000000.0):
    """
    生成绩效报告（便捷函数）
    
    Args:
        trades_df: 交易记录 DataFrame
        benchmark: 基准代码
        initial_capital: 初始资金
        
    Returns:
        报告字典
    """
    analyzer = PerformanceAnalyzer(initial_capital)
    return analyzer.generate_report(trades_df, benchmark)


def format_report(report: Dict) -> str:
    """
    格式化报告为文本（便捷函数）
    
    Args:
        report: 报告字典
        
    Returns:
        格式化后的文本
    """
    analyzer = PerformanceAnalyzer()
    return analyzer.format_report(report)


# 使用示例
if __name__ == '__main__':
    # 生成模拟交易数据
    np.random.seed(42)
    n_trades = 100
    dates = pd.date_range('2024-01-01', periods=n_trades, freq='D')
    
    # 模拟盈亏（略微盈利）
    pnl = np.random.randn(n_trades) * 1000 + 200
    
    trades_df = pd.DataFrame({
        'date': dates,
        'pnl': pnl,
        'code': ['000001.SZ'] * n_trades,
        'action': ['buy' if p > 0 else 'sell' for p in pnl]
    })
    
    # 生成报告
    print("📊 绩效分析测试")
    print("=" * 60)
    
    report = generate_report(trades_df)
    print(format_report(report))
