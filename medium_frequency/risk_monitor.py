#!/usr/bin/env python3
"""
风险监控器

功能:
- 仓位监控
- 止损止盈
- 交易频率限制
- 异常检测
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class RiskMonitor:
    """风险监控器"""
    
    def __init__(self, config: dict = None):
        """
        Args:
            config: 风控配置
        """
        self.config = config or {}
        
        # 仓位限制
        self.max_position_per_stock = self.config.get('max_position_per_stock', 0.10)
        self.max_total_position = self.config.get('max_total_position', 0.60)
        self.min_cash_reserve = self.config.get('min_cash_reserve', 0.40)
        
        # 交易限制
        self.max_trades_per_day = self.config.get('max_trades_per_day', 5)
        self.min_trade_interval = self.config.get('min_trade_interval', 300)  # 秒
        
        # 止损止盈
        self.stop_loss = self.config.get('stop_loss', -0.03)  # -3%
        self.take_profit = self.config.get('take_profit', 0.08)  # +8%
        self.trailing_stop = self.config.get('trailing_stop', True)
        
        # 异常检测
        self.max_consecutive_losses = self.config.get('max_consecutive_losses', 3)
        self.max_daily_loss = self.config.get('max_daily_loss', -0.05)  # -5%
        
        # 交易日志
        self._today_trades: Dict[str, List[dict]] = {}  # {code: [trades]}
        self._last_trade_time: Dict[str, datetime] = {}
        self._consecutive_losses: Dict[str, int] = {}
    
    def check_position_limit(
        self,
        code: str,
        current_position: float,
        target_position: float,
        total_position: float
    ) -> Tuple[bool, str]:
        """
        检查仓位限制
        
        Returns:
            (是否允许，原因)
        """
        # 单只股票仓位限制
        if target_position > self.max_position_per_stock:
            return False, f"单只股票仓位超标 ({target_position*100:.1f}% > {self.max_position_per_stock*100:.1f}%)"
        
        # 总仓位限制
        if total_position > self.max_total_position:
            return False, f"总仓位超标 ({total_position*100:.1f}% > {self.max_total_position*100:.1f}%)"
        
        # 现金储备限制
        if total_position < (1 - self.min_cash_reserve):
            if target_position > current_position:  # 买入
                return False, f"现金储备不足 (需保留{self.min_cash_reserve*100:.1f}%)"
        
        return True, "仓位检查通过"
    
    def check_trade_frequency(self, code: str) -> Tuple[bool, str]:
        """
        检查交易频率
        
        Returns:
            (是否允许，原因)
        """
        now = datetime.now()
        
        # 今日交易次数
        today_trades = self._today_trades.get(code, [])
        if len(today_trades) >= self.max_trades_per_day:
            return False, f"今日交易次数已达上限 ({len(today_trades)}/{self.max_trades_per_day})"
        
        # 最小交易间隔
        if code in self._last_trade_time:
            last_trade = self._last_trade_time[code]
            elapsed = (now - last_trade).total_seconds()
            
            if elapsed < self.min_trade_interval:
                return False, f"交易间隔过短 ({elapsed:.0f}s < {self.min_trade_interval}s)"
        
        return True, "频率检查通过"
    
    def check_stop_loss(
        self,
        code: str,
        buy_price: float,
        current_price: float,
        highest_price: float = None
    ) -> Tuple[bool, str]:
        """
        检查止损止盈
        
        Returns:
            (是否触发，原因)
        """
        if buy_price <= 0:
            return False, ""
        
        pnl = (current_price - buy_price) / buy_price
        
        # 止损检查
        if pnl <= self.stop_loss:
            return True, f"止损触发 ({pnl*100:.1f}% <= {self.stop_loss*100:.1f}%)"
        
        # 止盈检查
        if pnl >= self.take_profit:
            return True, f"止盈触发 ({pnl*100:.1f}% >= {self.take_profit*100:.1f}%)"
        
        # 移动止盈
        if self.trailing_stop and highest_price and highest_price > buy_price:
            peak_pnl = (highest_price - buy_price) / buy_price
            current_from_peak = (current_price - highest_price) / highest_price
            
            # 从最高点回撤超过 50% 的利润
            if peak_pnl > 0.05 and current_from_peak < -0.50:
                return True, f"移动止盈触发 (回撤{current_from_peak*100:.1f}%)"
        
        return False, ""
    
    def record_trade(
        self,
        code: str,
        action: str,
        price: float,
        shares: int,
        profit: float = 0.0
    ):
        """记录交易"""
        now = datetime.now()
        
        trade = {
            'time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'action': action,
            'price': price,
            'shares': shares,
            'profit': profit
        }
        
        # 更新今日交易
        if code not in self._today_trades:
            self._today_trades[code] = []
        self._today_trades[code].append(trade)
        
        # 更新最后交易时间
        self._last_trade_time[code] = now
        
        # 更新连续亏损
        if profit < 0:
            self._consecutive_losses[code] = self._consecutive_losses.get(code, 0) + 1
        else:
            self._consecutive_losses[code] = 0
    
    def check_consecutive_losses(self, code: str) -> Tuple[bool, str]:
        """检查连续亏损"""
        losses = self._consecutive_losses.get(code, 0)
        
        if losses >= self.max_consecutive_losses:
            return True, f"连续亏损{losses}笔，暂停交易"
        
        return False, ""
    
    def should_pause_trading(self, code: str) -> Tuple[bool, str]:
        """
        综合检查是否应该暂停交易
        
        Returns:
            (是否暂停，原因)
        """
        # 检查连续亏损
        paused, reason = self.check_consecutive_losses(code)
        if paused:
            return True, reason
        
        # 检查交易频率
        paused, reason = self.check_trade_frequency(code)
        if paused:
            return True, reason
        
        return False, ""
    
    def get_daily_stats(self) -> dict:
        """获取今日统计"""
        total_trades = sum(len(trades) for trades in self._today_trades.values())
        total_profit = sum(
            trade['profit'] 
            for trades in self._today_trades.values() 
            for trade in trades
        )
        
        return {
            'total_trades': total_trades,
            'total_profit': total_profit,
            'stocks_traded': len(self._today_trades),
            'consecutive_losses': self._consecutive_losses
        }
    
    def reset_daily(self):
        """重置每日数据"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 保留今日数据，清除历史
        new_trades = {}
        for code, trades in self._today_trades.items():
            today_trades = [
                t for t in trades 
                if t['time'].startswith(today)
            ]
            if today_trades:
                new_trades[code] = today_trades
        
        self._today_trades = new_trades


# ========== 测试 ==========
if __name__ == '__main__':
    print("="*60)
    print("测试风险监控器")
    print("="*60)
    
    config = {
        'max_position_per_stock': 0.10,
        'max_total_position': 0.60,
        'stop_loss': -0.03,
        'take_profit': 0.08,
        'max_trades_per_day': 5,
    }
    
    monitor = RiskMonitor(config)
    
    print("\n【1】测试仓位检查")
    allowed, reason = monitor.check_position_limit(
        code='sh.600519',
        current_position=0.05,
        target_position=0.08,
        total_position=0.35
    )
    print(f"  允许：{allowed}")
    print(f"  原因：{reason}")
    
    print("\n【2】测试止损止盈")
    triggered, reason = monitor.check_stop_loss(
        code='sh.600519',
        buy_price=100.0,
        current_price=96.0  # -4%
    )
    print(f"  触发：{triggered}")
    print(f"  原因：{reason}")
    
    print("\n【3】测试交易记录")
    monitor.record_trade(
        code='sh.600519',
        action='买入',
        price=100.0,
        shares=100,
        profit=0.0
    )
    
    stats = monitor.get_daily_stats()
    print(f"  今日交易：{stats['total_trades']}笔")
    print(f"  总盈亏：{stats['total_profit']:.2f}")
    
    print("\n✅ 测试完成")
