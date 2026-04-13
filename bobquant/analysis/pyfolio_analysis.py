# -*- coding: utf-8 -*-
"""
BobQuant PyFolio 绩效分析模块

功能:
- 收益曲线图
- 回撤分析
- 风险指标（Sharpe/Sortino/Calmar）
- 月度收益热力图
- 持仓分析
- HTML 报告生成

使用方式:
    from bobquant.analysis.pyfolio_analysis import PyFolioAnalyzer
    analyzer = PyFolioAnalyzer()
    report = analyzer.generate_report(returns, positions, transactions)
"""
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple
import warnings

# 忽略 pyfolio 的警告
warnings.filterwarnings('ignore')

# 尝试导入 pyfolio
try:
    import pyfolio as pf
    PYFOLIO_AVAILABLE = True
    print("[PyFolio] ✅ pyfolio 已加载，专业绩效分析启用")
except ImportError as e:
    PYFOLIO_AVAILABLE = False
    print(f"[PyFolio] ⚠️ pyfolio 未安装：{e}")


class PyFolioAnalyzer:
    """PyFolio 绩效分析器"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        """
        初始化分析器
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.report_dir = Path(__file__).parent.parent / 'reports' / 'pyfolio'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_returns(self, trades_df: pd.DataFrame) -> pd.Series:
        """
        从交易记录准备收益率序列
        
        Args:
            trades_df: 交易记录 DataFrame，包含 date, pnl 列
            
        Returns:
            每日收益率 Series
        """
        if trades_df.empty:
            return pd.Series(dtype=float)
        
        # 按日期聚合盈亏
        trades_df = trades_df.copy()
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        daily_pnl = trades_df.groupby('date')['pnl'].sum()
        
        # 转换为收益率
        daily_returns = daily_pnl / self.initial_capital
        
        # 确保索引是日期类型
        daily_returns.index = pd.to_datetime(daily_returns.index)
        
        return daily_returns
    
    def prepare_positions(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """
        从交易记录准备持仓数据
        
        Args:
            trades_df: 交易记录 DataFrame，包含 date, code, amount, direction 列
            
        Returns:
            持仓 DataFrame
        """
        if trades_df.empty:
            return pd.DataFrame()
        
        trades_df = trades_df.copy()
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # 计算每个股票的累计持仓
        positions = pd.DataFrame()
        
        for code in trades_df['code'].unique():
            code_trades = trades_df[trades_df['code'] == code].copy()
            code_trades = code_trades.sort_values('date')
            
            # 计算持仓量（假设 direction: 1=买入，-1=卖出）
            if 'direction' in code_trades.columns:
                code_trades['position'] = code_trades['direction'] * code_trades['amount']
            else:
                # 如果没有 direction，假设买入为正，卖出为负
                code_trades['position'] = code_trades['amount']
            
            # 累计持仓
            code_trades['cum_position'] = code_trades['position'].cumsum()
            
            # 转换为时间序列（按日期聚合，避免重复索引）
            code_trades = code_trades.groupby('date')['cum_position'].last()
            positions[code] = code_trades
        
        # 填充缺失值
        positions = positions.fillna(0)
        
        return positions
    
    def prepare_transactions(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """
        从交易记录准备交易数据
        
        Args:
            trades_df: 交易记录 DataFrame
            
        Returns:
            交易 DataFrame
        """
        if trades_df.empty:
            return pd.DataFrame()
        
        trades_df = trades_df.copy()
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # 创建交易记录
        transactions = pd.DataFrame()
        
        if 'price' in trades_df.columns and 'amount' in trades_df.columns:
            transactions = trades_df[['date', 'code', 'price', 'amount']].copy()
            
            # 添加交易方向
            if 'direction' in trades_df.columns:
                transactions['direction'] = trades_df['direction']
            elif 'action' in trades_df.columns:
                transactions['direction'] = trades_df['action'].map({'buy': 1, 'sell': -1})
            else:
                transactions['direction'] = np.sign(trades_df['amount'])
        
        return transactions
    
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
        
        # 直接使用基础计算（避免 empyrical 与 numpy 2.0 的兼容性问题）
        metrics = self._calculate_basic_metrics(returns)
        
        # 胜率
        positive_days = len(returns[returns > 0])
        total_days = len(returns[returns != 0])
        metrics['win_rate'] = positive_days / total_days if total_days > 0 else 0
        
        # 最佳/最差交易日
        metrics['best_day'] = float(returns.max())
        metrics['worst_day'] = float(returns.min())
        
        return metrics
    
    def _calculate_basic_metrics(self, returns: pd.Series) -> Dict:
        """基础指标计算（回退方案）"""
        metrics = {}
        
        metrics['total_return'] = (1 + returns).prod() - 1
        metrics['annual_return'] = (1 + metrics['total_return']) ** (252 / len(returns)) - 1
        metrics['volatility'] = returns.std() * np.sqrt(252)
        
        if metrics['volatility'] > 0:
            metrics['sharpe'] = (metrics['annual_return'] - 0.03) / metrics['volatility']
        else:
            metrics['sharpe'] = 0
        
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std() * np.sqrt(252)
            if downside_std > 0:
                metrics['sortino'] = (metrics['annual_return'] - 0.03) / downside_std
            else:
                metrics['sortino'] = 0
        else:
            metrics['sortino'] = 0
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        metrics['max_drawdown'] = drawdown.min()
        
        if metrics['max_drawdown'] != 0:
            metrics['calmar'] = metrics['annual_return'] / abs(metrics['max_drawdown'])
        else:
            metrics['calmar'] = 0
        
        return metrics
    
    def analyze_drawdown(self, returns: pd.Series) -> Dict:
        """
        回撤分析
        
        Args:
            returns: 每日收益率 Series
            
        Returns:
            回撤分析字典
        """
        if returns.empty:
            return {'error': '无数据'}
        
        try:
            # 手动计算回撤（避免 empyrical 兼容性问题）
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.cummax()
            drawdown_series = (cumulative - running_max) / running_max
            
            # 统计回撤信息
            analysis = {
                'max_drawdown': float(drawdown_series.min()),
                'max_drawdown_duration': None,
                'underwater_periods': [],
                'drawdown_series': drawdown_series.to_dict()
            }
            
            # 找出回撤超过 5% 的时期
            significant_dd = drawdown_series[drawdown_series < -0.05]
            if len(significant_dd) > 0:
                analysis['significant_drawdowns'] = len(significant_dd)
            
            return analysis
            
        except Exception as e:
            print(f"[PyFolio] ⚠️ 回撤分析失败：{e}")
            return {'error': str(e)}
    
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
        
        try:
            import empyrical as ep
            
            # 使用 empyrical 的月度收益计算
            monthly_returns = ep.annual_return(returns)  # 这只是年化，需要重新计算
            
            # 手动计算月度收益
            returns_df = returns.to_frame('return')
            returns_df['year'] = returns_df.index.year
            returns_df['month'] = returns_df.index.month
            
            # 计算月度复合收益
            monthly = returns_df.groupby(['year', 'month'])['return'].apply(
                lambda x: (1 + x).prod() - 1
            )
            
            # 重塑为热力图格式
            heatmap = monthly.unstack(level='month')
            
            return heatmap
            
        except Exception as e:
            print(f"[PyFolio] ⚠️ 热力图生成失败：{e}")
            # 回退方案
            return self._generate_basic_heatmap(returns)
    
    def _generate_basic_heatmap(self, returns: pd.Series) -> pd.DataFrame:
        """基础热力图生成（回退方案）"""
        returns_df = returns.to_frame('return')
        returns_df['year'] = returns_df.index.year
        returns_df['month'] = returns_df.index.month
        
        monthly = returns_df.groupby(['year', 'month'])['return'].apply(
            lambda x: (1 + x).prod() - 1
        )
        
        heatmap = monthly.unstack(level='month')
        return heatmap
    
    def analyze_positions(self, positions: pd.DataFrame) -> Dict:
        """
        持仓分析
        
        Args:
            positions: 持仓 DataFrame
            
        Returns:
            持仓分析字典
        """
        if positions.empty:
            return {'error': '无持仓数据'}
        
        analysis = {
            'total_symbols': len(positions.columns),
            'symbols': list(positions.columns),
            'avg_position_size': {},
            'max_position_size': {},
            'turnover': {}
        }
        
        for symbol in positions.columns:
            pos = positions[symbol]
            analysis['avg_position_size'][symbol] = float(pos.abs().mean())
            analysis['max_position_size'][symbol] = float(pos.abs().max())
        
        return analysis
    
    def generate_html_report(self, returns: pd.Series, positions: Optional[pd.DataFrame] = None,
                            transactions: Optional[pd.DataFrame] = None,
                            benchmark_returns: Optional[pd.Series] = None) -> Optional[str]:
        """
        生成 HTML 报告
        
        Args:
            returns: 收益率序列
            positions: 持仓数据
            transactions: 交易数据
            benchmark_returns: 基准收益率
            
        Returns:
            HTML 报告路径
        """
        if not PYFOLIO_AVAILABLE:
            print("[PyFolio] ⚠️ pyfolio 不可用，跳过 HTML 报告生成")
            return None
        
        if returns.empty or len(returns) < 30:
            print("[PyFolio] ⚠️ 数据不足，需要至少 30 个交易日")
            return None
        
        try:
            # 生成报告文件名
            report_date = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_path = self.report_dir / f'pyfolio_report_{report_date}.html'
            
            # 创建 HTML 报告
            import pyfolio as pf
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
            import io
            
            # 使用 matplotlib 生成图表并保存为 HTML
            fig = plt.figure(figsize=(20, 30))
            
            # 1. 收益曲线图
            ax1 = plt.subplot(4, 2, 1)
            cumulative = (1 + returns).cumprod()
            ax1.plot(cumulative.index, cumulative.values, 'b-', linewidth=2)
            ax1.set_title('Cumulative Returns', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Returns')
            ax1.grid(True, alpha=0.3)
            
            # 2. 回撤图
            ax2 = plt.subplot(4, 2, 2)
            underwater = (cumulative / cumulative.cummax()) - 1
            ax2.fill_between(underwater.index, underwater.values, 0, color='red', alpha=0.3)
            ax2.set_title('Underwater Plot (Drawdown)', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Drawdown')
            ax2.grid(True, alpha=0.3)
            
            # 3. 月度收益热力图数据
            ax3 = plt.subplot(4, 2, 3)
            monthly_returns = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
            if len(monthly_returns) > 0:
                ax3.bar(range(len(monthly_returns)), monthly_returns.values, 
                       color=['green' if x > 0 else 'red' for x in monthly_returns.values])
                ax3.set_title('Monthly Returns', fontsize=14, fontweight='bold')
                ax3.set_ylabel('Returns')
                ax3.grid(True, alpha=0.3)
            
            # 4. 收益分布
            ax4 = plt.subplot(4, 2, 4)
            ax4.hist(returns.values, bins=30, color='blue', alpha=0.7, edgecolor='black')
            ax4.set_title('Return Distribution', fontsize=14, fontweight='bold')
            ax4.set_xlabel('Daily Returns')
            ax4.set_ylabel('Frequency')
            ax4.grid(True, alpha=0.3)
            
            # 5. 滚动 Sharpe 比率
            ax5 = plt.subplot(4, 2, 5)
            rolling_sharpe = returns.rolling(window=21).mean() / returns.rolling(window=21).std() * np.sqrt(252)
            ax5.plot(rolling_sharpe.index, rolling_sharpe.values, 'g-', linewidth=2)
            ax5.set_title('Rolling Sharpe Ratio (21-day)', fontsize=14, fontweight='bold')
            ax5.set_ylabel('Sharpe')
            ax5.grid(True, alpha=0.3)
            
            # 6. 滚动波动率
            ax6 = plt.subplot(4, 2, 6)
            rolling_vol = returns.rolling(window=21).std() * np.sqrt(252)
            ax6.plot(rolling_vol.index, rolling_vol.values, 'orange', linewidth=2)
            ax6.set_title('Rolling Volatility (21-day)', fontsize=14, fontweight='bold')
            ax6.set_ylabel('Volatility')
            ax6.grid(True, alpha=0.3)
            
            # 7. 累计收益 vs 基准（如果有）
            ax7 = plt.subplot(4, 2, 7)
            ax7.plot(cumulative.index, cumulative.values, 'b-', linewidth=2, label='Strategy')
            if benchmark_returns is not None:
                benchmark_cum = (1 + benchmark_returns).cumprod()
                ax7.plot(benchmark_cum.index, benchmark_cum.values, 'r--', linewidth=2, label='Benchmark')
                ax7.legend()
            ax7.set_title('Strategy vs Benchmark', fontsize=14, fontweight='bold')
            ax7.set_ylabel('Cumulative Returns')
            ax7.grid(True, alpha=0.3)
            
            # 8. 收益日历热力图（简化版）
            ax8 = plt.subplot(4, 2, 8)
            returns_df = returns.to_frame('return')
            returns_df['month'] = returns_df.index.month
            returns_df['weekday'] = returns_df.index.weekday
            monthly_by_weekday = returns_df.groupby(['month', 'weekday'])['return'].mean().unstack()
            if not monthly_by_weekday.empty:
                im = ax8.imshow(monthly_by_weekday.values, cmap='RdYlGn', aspect='auto')
                ax8.set_xlabel('Weekday')
                ax8.set_ylabel('Month')
                ax8.set_title('Return Heatmap by Month/Weekday', fontsize=14, fontweight='bold')
                plt.colorbar(im, ax=ax8)
            
            plt.tight_layout()
            plt.savefig(html_path.with_suffix('.png'), dpi=150, bbox_inches='tight')
            plt.close()
            
            # 生成简单的 HTML 包装器
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyFolio Performance Report - {report_date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric {{ background: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .metric-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        img {{ max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; border-radius: 4px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 PyFolio Performance Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📈 Performance Charts</h2>
        <img src="{html_path.with_suffix('.png').name}" alt="Performance Charts">
        
        <h2>📊 Key Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{(cumulative.iloc[-1] - 1) * 100:+.2f}%</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric">
                <div class="metric-value">{returns.mean() * 252 * 100:+.2f}%</div>
                <div class="metric-label">Annual Return</div>
            </div>
            <div class="metric">
                <div class="metric-value">{returns.std() * np.sqrt(252) * 100:.2f}%</div>
                <div class="metric-label">Volatility</div>
            </div>
            <div class="metric">
                <div class="metric-value">{(returns.mean() * 252) / (returns.std() * np.sqrt(252)):.3f}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric">
                <div class="metric-value">{underwater.min() * 100:.2f}%</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(returns[returns > 0]) / len(returns) * 100:.1f}%</div>
                <div class="metric-label">Win Rate</div>
            </div>
        </div>
        
        <div class="footer">
            <p>Report generated by BobQuant PyFolio Analyzer</p>
            <p>Data period: {returns.index.min().strftime('%Y-%m-%d')} to {returns.index.max().strftime('%Y-%m-%d')} ({len(returns)} trading days)</p>
        </div>
    </div>
</body>
</html>"""
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"[PyFolio] ✅ HTML 报告已生成：{html_path}")
            return str(html_path)
            
        except Exception as e:
            print(f"[PyFolio] ⚠️ HTML 报告生成失败：{e}")
            return None
    
    def generate_report(self, trades_df: pd.DataFrame, benchmark: Optional[str] = None) -> Dict:
        """
        生成完整绩效报告
        
        Args:
            trades_df: 交易记录 DataFrame
            benchmark: 基准代码（如 '000300.SH'）
            
        Returns:
            报告字典
        """
        # 准备数据
        returns = self.prepare_returns(trades_df)
        
        if returns.empty:
            return {'error': '无交易数据'}
        
        positions = self.prepare_positions(trades_df)
        transactions = self.prepare_transactions(trades_df)
        
        # 计算指标
        metrics = self.calculate_metrics(returns)
        
        # 回撤分析
        drawdown_analysis = self.analyze_drawdown(returns)
        
        # 月度热力图
        monthly_heatmap = self.generate_monthly_heatmap(returns)
        
        # 持仓分析
        position_analysis = self.analyze_positions(positions) if not positions.empty else {}
        
        # 生成 HTML 报告
        html_report_path = None
        if PYFOLIO_AVAILABLE and len(returns) >= 30:
            html_report_path = self.generate_html_report(
                returns, 
                positions if not positions.empty else None,
                transactions if not transactions.empty else None
            )
        
        return {
            'metrics': metrics,
            'drawdown': drawdown_analysis,
            'monthly_heatmap': monthly_heatmap.to_dict() if not monthly_heatmap.empty else {},
            'positions': position_analysis,
            'html_report': html_report_path,
            'total_trading_days': len(returns),
            'start_date': str(returns.index.min()),
            'end_date': str(returns.index.max()),
            'returns_series': returns  # 返回收益率序列供进一步分析
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
        lines.append("=" * 70)
        lines.append("📊 PyFolio 绩效分析报告")
        lines.append("=" * 70)
        
        # 基础信息
        lines.append(f"交易天数：{report['total_trading_days']}")
        lines.append(f"时间范围：{report['start_date']} 至 {report['end_date']}")
        lines.append("")
        
        # 核心指标
        metrics = report['metrics']
        lines.append("📈 核心风险收益指标:")
        lines.append(f"  总收益率：    {metrics.get('total_return', 0)*100:+.2f}%")
        lines.append(f"  年化收益：    {metrics.get('annual_return', 0)*100:+.2f}%")
        lines.append(f"  波动率：      {metrics.get('volatility', 0)*100:.2f}%")
        lines.append(f"  Sharpe 比率：  {metrics.get('sharpe', 0):.3f}")
        lines.append(f"  Sortino 比率： {metrics.get('sortino', 0):.3f}")
        lines.append(f"  Calmar 比率：  {metrics.get('calmar', 0):.3f}")
        lines.append(f"  最大回撤：    {metrics.get('max_drawdown', 0)*100:.2f}%")
        lines.append(f"  下行风险：    {metrics.get('downside_risk', 0)*100:.2f}%")
        lines.append("")
        
        # 交易统计
        lines.append("🎯 交易统计:")
        lines.append(f"  胜率：        {metrics.get('win_rate', 0)*100:.1f}%")
        lines.append(f"  最佳交易日：  {metrics.get('best_day', 0)*100:+.2f}%")
        lines.append(f"  最差交易日：  {metrics.get('worst_day', 0)*100:+.2f}%")
        lines.append("")
        
        # 回撤分析
        dd = report.get('drawdown', {})
        if 'error' not in dd:
            lines.append("📉 回撤分析:")
            lines.append(f"  最大回撤：    {dd.get('max_drawdown', 0)*100:.2f}%")
            if 'significant_drawdowns' in dd:
                lines.append(f"  显著回撤次数：{dd['significant_drawdowns']} (>5%)")
            lines.append("")
        
        # 持仓分析
        pos = report.get('positions', {})
        if pos and 'error' not in pos:
            lines.append("💼 持仓分析:")
            lines.append(f"  标的数量：    {pos.get('total_symbols', 0)}")
            lines.append("")
        
        # 月度热力图摘要
        heatmap = report.get('monthly_heatmap', {})
        if heatmap:
            lines.append("📅 月度收益摘要:")
            for year, months in list(heatmap.items())[:5]:  # 只显示最近 5 年
                positive_months = sum(1 for v in months.values() if v > 0)
                total_months = len([v for v in months.values() if pd.notna(v)])
                lines.append(f"  {year}: {positive_months}/{total_months} 个月盈利")
            lines.append("")
        
        # HTML 报告
        if report.get('html_report'):
            lines.append(f"📄 HTML 报告：{report['html_report']}")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# 便捷函数
def generate_report(trades_df: pd.DataFrame, benchmark: Optional[str] = None, 
                   initial_capital: float = 1000000.0) -> Dict:
    """
    生成 PyFolio 绩效报告（便捷函数）
    
    Args:
        trades_df: 交易记录 DataFrame
        benchmark: 基准代码
        initial_capital: 初始资金
        
    Returns:
        报告字典
    """
    analyzer = PyFolioAnalyzer(initial_capital)
    return analyzer.generate_report(trades_df, benchmark)


def format_report(report: Dict) -> str:
    """
    格式化 PyFolio 报告为文本（便捷函数）
    
    Args:
        report: 报告字典
        
    Returns:
        格式化后的文本
    """
    analyzer = PyFolioAnalyzer()
    return analyzer.format_report(report)


# 使用示例
if __name__ == '__main__':
    # 生成模拟交易数据
    np.random.seed(42)
    n_trades = 100
    dates = pd.date_range('2024-01-01', periods=n_trades, freq='D')
    
    # 模拟盈亏（略微盈利）
    pnl = np.random.randn(n_trades) * 2000 + 300
    
    trades_df = pd.DataFrame({
        'date': dates,
        'pnl': pnl,
        'code': ['000001.SZ'] * n_trades,
        'amount': [100] * n_trades,
        'price': [20.0 + np.random.randn() * 0.5 for _ in range(n_trades)],
        'action': ['buy' if p > 0 else 'sell' for p in pnl]
    })
    
    # 生成报告
    print("📊 PyFolio 绩效分析测试")
    print("=" * 70)
    
    report = generate_report(trades_df)
    print(format_report(report))
