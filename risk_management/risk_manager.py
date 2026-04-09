#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理器 - QuantConnect/Lean 风控模块实现

功能:
- 实时订单风控检查
- 持仓风险监控
- 回撤控制
- 集中度管理

使用示例:
    python risk_manager.py --demo
"""

import argparse
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from enum import Enum
import json


class RiskCheckResult(Enum):
    PASS = 'pass'
    FAIL = 'fail'
    WARNING = 'warning'


@dataclass
class RiskLimits:
    """风险限制配置"""
    # 持仓限制
    max_position_value: float = 500000.0  # 单只股票最大持仓市值
    max_portfolio_exposure: float = 2000000.0  # 最大总敞口
    concentration_limit: float = 0.30  # 单只股票持仓占比上限
    
    # 亏损限制
    max_drawdown: float = 0.10  # 最大回撤 10%
    max_daily_loss: float = 50000.0  # 单日最大亏损 5 万
    
    # 订单限制
    max_order_value: float = 100000.0  # 单笔订单最大金额 10 万
    max_order_pct_of_position: float = 0.20  # 单笔订单最大占持仓比例
    
    # 交易频率限制
    max_orders_per_minute: int = 10  # 每分钟最大订单数
    max_daily_turnover: float = 1000000.0  # 单日最大成交额


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    def update_price(self, price: float):
        """更新价格并计算盈亏"""
        self.current_price = price
        self.market_value = self.quantity * price
        self.unrealized_pnl = (price - self.avg_cost) * self.quantity
        self.unrealized_pnl_pct = (price - self.avg_cost) / self.avg_cost if self.avg_cost > 0 else 0


@dataclass
class RiskMetrics:
    """风险指标"""
    total_value: float  # 组合总市值
    cash: float  # 可用现金
    exposure: float  # 总敞口
    drawdown: float  # 当前回撤
    daily_pnl: float  # 当日盈亏
    concentration: Dict[str, float]  # 各股票持仓占比
    var_95: Optional[float] = None  # 95% VaR (可选)


class RiskManager:
    """风险管理器"""
    
    def __init__(self, limits: RiskLimits, initial_capital: float = 1000000.0):
        self.limits = limits
        self.initial_capital = initial_capital
        self.cash = initial_capital
        
        self.positions: Dict[str, Position] = {}
        self.prices: Dict[str, float] = {}
        
        # 风控跟踪
        self.peak_value = initial_capital
        self.current_value = initial_capital
        self.daily_pnl = 0.0
        self.daily_turnover = 0.0
        self.order_timestamps: List[datetime] = []
        
        # 风控日志
        self.risk_log: List[Dict] = []
    
    def update_prices(self, prices: Dict[str, float]):
        """
        更新价格
        
        参数:
            prices: {symbol: price} 字典
        """
        self.prices.update(prices)
        
        # 更新持仓价格
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)
        
        # 重新计算组合价值
        self._recalculate_portfolio()
    
    def _recalculate_portfolio(self):
        """重新计算组合价值"""
        position_value = sum(pos.market_value for pos in self.positions.values())
        self.current_value = position_value + self.cash
        
        # 更新峰值
        if self.current_value > self.peak_value:
            self.peak_value = self.current_value
    
    def get_metrics(self) -> RiskMetrics:
        """获取当前风险指标"""
        position_value = sum(pos.market_value for pos in self.positions.values())
        
        # 计算集中度
        concentration = {}
        if position_value > 0:
            for symbol, pos in self.positions.items():
                concentration[symbol] = pos.market_value / position_value
        
        # 计算回撤
        drawdown = (self.peak_value - self.current_value) / self.peak_value if self.peak_value > 0 else 0
        
        return RiskMetrics(
            total_value=self.current_value,
            cash=self.cash,
            exposure=position_value,
            drawdown=drawdown,
            daily_pnl=self.daily_pnl,
            concentration=concentration
        )
    
    def check_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float
    ) -> Tuple[RiskCheckResult, str]:
        """
        检查订单是否符合风控要求
        
        参数:
            symbol: 股票代码
            side: 'buy' 或 'sell'
            quantity: 数量
            price: 价格
        
        返回:
            (检查结果，原因说明)
        """
        order_value = quantity * price
        checks_passed = []
        checks_failed = []
        warnings = []
        
        # ========== 硬性限制检查 ==========
        
        # 1. 单笔订单金额限制
        if order_value > self.limits.max_order_value:
            checks_failed.append(
                f"订单金额 {order_value:,.0f} 超过限制 {self.limits.max_order_value:,.0f}"
            )
        else:
            checks_passed.append("订单金额检查 ✓")
        
        # 2. 计算执行后的持仓
        current_qty = self.positions.get(symbol, Position(symbol, 0, 0)).quantity
        if side == 'buy':
            new_qty = current_qty + quantity
            new_position_value = new_qty * price
        else:
            new_qty = max(0, current_qty - quantity)
            new_position_value = new_qty * price
        
        # 3. 单只股票持仓限制
        if new_position_value > self.limits.max_position_value:
            checks_failed.append(
                f"持仓市值 {new_position_value:,.0f} 超过限制 {self.limits.max_position_value:,.0f}"
            )
        else:
            checks_passed.append("单股持仓限制 ✓")
        
        # 4. 组合总敞口限制
        current_exposure = sum(pos.market_value for pos in self.positions.values())
        if side == 'buy':
            new_exposure = current_exposure + order_value
        else:
            new_exposure = max(0, current_exposure - order_value)
        
        if new_exposure > self.limits.max_portfolio_exposure:
            checks_failed.append(
                f"组合敞口 {new_exposure:,.0f} 超过限制 {self.limits.max_portfolio_exposure:,.0f}"
            )
        else:
            checks_passed.append("组合敞口限制 ✓")
        
        # 5. 集中度限制
        if new_exposure > 0:
            concentration = new_position_value / new_exposure
            if concentration > self.limits.concentration_limit:
                checks_failed.append(
                    f"持仓集中度 {concentration:.1%} 超过限制 {self.limits.concentration_limit:.1%}"
                )
            else:
                checks_passed.append("集中度限制 ✓")
        
        # 6. 回撤检查
        if self.peak_value > 0:
            drawdown = (self.peak_value - self.current_value) / self.peak_value
            if drawdown > self.limits.max_drawdown:
                checks_failed.append(
                    f"当前回撤 {drawdown:.1%} 超过限制 {self.limits.max_drawdown:.1%}"
                )
            else:
                checks_passed.append(f"回撤检查 ✓ (当前：{drawdown:.1%})")
        
        # 7. 单日亏损检查
        if self.daily_pnl < -self.limits.max_daily_loss:
            checks_failed.append(
                f"单日亏损 {abs(self.daily_pnl):,.0f} 超过限制 {self.limits.max_daily_loss:,.0f}"
            )
        else:
            checks_passed.append("单日亏损检查 ✓")
        
        # 8. 可用现金检查（买单）
        if side == 'buy':
            if order_value > self.cash:
                checks_failed.append(
                    f"可用现金不足：需要 {order_value:,.0f}, 可用 {self.cash:,.0f}"
                )
            else:
                checks_passed.append("可用现金检查 ✓")
        
        # 9. 持仓数量检查（卖单）
        if side == 'sell':
            if quantity > current_qty:
                checks_failed.append(
                    f"持仓不足：需要 {quantity}, 可用 {current_qty}"
                )
            else:
                checks_passed.append("持仓数量检查 ✓")
        
        # ========== 警告检查（不阻止交易） ==========
        
        # 10. 订单占持仓比例警告
        if current_qty > 0:
            order_pct = quantity / current_qty
            if order_pct > self.limits.max_order_pct_of_position:
                warnings.append(
                    f"⚠️ 订单占持仓 {order_pct:.1%}, 建议上限 {self.limits.max_order_pct_of_position:.1%}"
                )
        
        # 11. 交易频率警告
        now = datetime.now()
        recent_orders = [t for t in self.order_timestamps if (now - t).total_seconds() < 60]
        if len(recent_orders) >= self.limits.max_orders_per_minute:
            warnings.append(
                f"⚠️ 过去 1 分钟已有 {len(recent_orders)} 笔订单，建议降低频率"
            )
        
        # ========== 汇总结果 ==========
        
        # 记录风控日志
        log_entry = {
            'time': now.isoformat(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'order_value': order_value,
            'checks_passed': len(checks_passed),
            'checks_failed': len(checks_failed),
            'warnings': len(warnings)
        }
        self.risk_log.append(log_entry)
        
        # 返回结果
        if checks_failed:
            return RiskCheckResult.FAIL, "❌ " + "; ".join(checks_failed)
        elif warnings:
            return RiskCheckResult.WARNING, "⚠️ " + "; ".join(warnings)
        else:
            return RiskCheckResult.PASS, "✅ " + "; ".join(checks_passed)
    
    def execute_order(self, symbol: str, side: str, quantity: int, price: float) -> bool:
        """
        执行订单（先检查风控，再更新持仓）
        
        返回：是否成功执行
        """
        # 风控检查
        result, message = self.check_order(symbol, side, quantity, price)
        
        if result == RiskCheckResult.FAIL:
            print(f"🚫 订单被风控拦截：{message}")
            return False
        
        if result == RiskCheckResult.WARNING:
            print(f"⚠️  风控警告：{message}")
        
        # 更新持仓
        order_value = quantity * price
        
        if side == 'buy':
            if symbol in self.positions:
                pos = self.positions[symbol]
                # 更新平均成本
                total_cost = pos.avg_cost * pos.quantity + price * quantity
                pos.quantity += quantity
                pos.avg_cost = total_cost / pos.quantity if pos.quantity > 0 else 0
                pos.update_price(price)
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=price,
                    current_price=price
                )
            
            self.cash -= order_value
            self.daily_turnover += order_value
        
        else:  # sell
            if symbol in self.positions:
                pos = self.positions[symbol]
                realized_pnl = (price - pos.avg_cost) * quantity
                pos.quantity -= quantity
                self.daily_pnl += realized_pnl
                
                if pos.quantity <= 0:
                    del self.positions[symbol]
                else:
                    pos.update_price(price)
            
            self.cash += order_value
            self.daily_turnover += order_value
        
        # 记录订单时间戳
        self.order_timestamps.append(datetime.now())
        
        # 更新组合价值
        self._recalculate_portfolio()
        
        print(f"✓ 订单执行成功：{symbol} {side} {quantity} @ {price:.2f}")
        return True
    
    def get_risk_report(self) -> str:
        """生成风控报告"""
        metrics = self.get_metrics()
        
        report = []
        report.append("=" * 60)
        report.append("📊 风险报告")
        report.append("=" * 60)
        report.append(f"组合总市值：{metrics.total_value:,.0f}")
        report.append(f"可用现金：{metrics.cash:,.0f}")
        report.append(f"股票敞口：{metrics.exposure:,.0f}")
        report.append(f"仓位：{metrics.exposure / metrics.total_value:.1%}" if metrics.total_value > 0 else "仓位：N/A")
        report.append("")
        report.append(f"当前回撤：{metrics.drawdown:.1%}")
        report.append(f"最大允许回撤：{self.limits.max_drawdown:.1%}")
        report.append(f"回撤缓冲：{(self.limits.max_drawdown - metrics.drawdown):.1%}")
        report.append("")
        report.append(f"当日盈亏：{metrics.daily_pnl:+,.0f}")
        report.append(f"单日亏损限制：{self.limits.max_daily_loss:,.0f}")
        report.append(f"亏损缓冲：{self.limits.max_daily_loss + metrics.daily_pnl:,.0f}")
        report.append("")
        
        # 持仓明细
        if self.positions:
            report.append("📦 持仓明细:")
            report.append("-" * 60)
            for symbol, pos in self.positions.items():
                report.append(
                    f"  {symbol}: {pos.quantity}股 @ {pos.current_price:.2f} "
                    f"市值={pos.market_value:,.0f} 盈亏={pos.unrealized_pnl:+,.0f}({pos.unrealized_pnl_pct:+.1%})"
                )
            report.append("")
        
        # 集中度
        if metrics.concentration:
            report.append("🎯 持仓集中度:")
            for symbol, pct in sorted(metrics.concentration.items(), key=lambda x: -x[1]):
                bar = "█" * int(pct * 20)
                report.append(f"  {symbol}: {bar} {pct:.1%}")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def reset_daily(self):
        """重置每日统计（每日开盘前调用）"""
        self.daily_pnl = 0.0
        self.daily_turnover = 0.0
        self.order_timestamps = []
        print("✓ 每日统计已重置")


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("风险管理器演示")
    print("=" * 60)
    
    # 创建风控配置
    limits = RiskLimits(
        max_position_value=500000,
        max_portfolio_exposure=2000000,
        max_drawdown=0.10,
        max_daily_loss=50000,
        max_order_value=100000,
        concentration_limit=0.30
    )
    
    # 创建风控管理器
    risk_mgr = RiskManager(limits, initial_capital=1000000)
    
    # 模拟一些交易
    print("\n📝 模拟交易...")
    
    # 买入平安银行
    risk_mgr.execute_order('000001.SZ', 'buy', 5000, 10.5)
    risk_mgr.execute_order('000001.SZ', 'buy', 5000, 10.6)
    
    # 买入贵州茅台
    risk_mgr.execute_order('600519.SH', 'buy', 100, 1500.0)
    
    # 更新价格
    print("\n📈 更新价格...")
    risk_mgr.update_prices({
        '000001.SZ': 10.8,
        '600519.SH': 1520.0
    })
    
    # 尝试一笔超限订单
    print("\n🧪 测试风控拦截...")
    risk_mgr.check_order('000001.SZ', 'buy', 100000, 10.8)
    
    # 生成风控报告
    print("\n")
    print(risk_mgr.get_risk_report())


def main():
    parser = argparse.ArgumentParser(description='风险管理器')
    parser.add_argument('--demo', action='store_true', help='运行演示')
    parser.add_argument('--config', type=str, help='风控配置文件路径 (JSON)')
    
    args = parser.parse_args()
    
    if args.demo or not args.config:
        run_demo()
    else:
        # 从配置文件加载
        with open(args.config, 'r') as f:
            config = json.load(f)
        
        limits = RiskLimits(**config.get('limits', {}))
        risk_mgr = RiskManager(limits, initial_capital=config.get('initial_capital', 1000000))
        
        print(f"✅ 风控管理器已初始化")
        print(risk_mgr.get_risk_report())


if __name__ == '__main__':
    main()
