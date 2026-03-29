#!/usr/bin/env python3
"""
执行引擎

功能:
- 信号处理
- 订单执行
- 仓位管理
- 日志记录
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from .signal_generator import Signal, SignalType
from .risk_monitor import RiskMonitor


class ExecutionEngine:
    """执行引擎"""
    
    def __init__(
        self,
        account_file: str,
        trade_log_file: str,
        risk_config: dict = None
    ):
        """
        Args:
            account_file: 账户文件路径
            trade_log_file: 交易日志路径
            risk_config: 风控配置
        """
        self.account_file = Path(account_file)
        self.trade_log_file = Path(trade_log_file)
        
        self.risk_monitor = RiskMonitor(risk_config)
        self._trade_counter = 0
    
    def execute_signal(
        self,
        signal: Signal,
        account: dict,
        dry_run: bool = False
    ) -> dict:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
            account: 账户数据
            dry_run: 模拟执行 (不实际下单)
        
        Returns:
            执行结果
        """
        result = {
            'success': False,
            'action': None,
            'code': signal.code,
            'name': signal.name,
            'reason': '',
            'shares': 0,
            'price': signal.price,
            'amount': 0.0,
            'dry_run': dry_run
        }
        
        # 1. 风控检查
        paused, reason = self.risk_monitor.should_pause_trading(signal.code)
        if paused:
            result['reason'] = f"风控暂停：{reason}"
            return result
        
        # 2. 获取当前持仓
        positions = account.get('positions', {})
        current_pos = positions.get(signal.code, {})
        current_shares = current_pos.get('shares', 0)
        current_price = current_pos.get('avg_price', 0)
        
        # 3. 检查止损止盈 (如果是卖出)
        if signal.signal_type == SignalType.SELL and current_shares > 0:
            triggered, reason = self.risk_monitor.check_stop_loss(
                signal.code,
                current_price,
                signal.price
            )
            if triggered:
                result['reason'] = f"止损止盈：{reason}"
                # 继续执行卖出
        
        # 4. 计算目标仓位
        target_position = signal.target_position
        total_capital = self._calculate_total_capital(account)
        target_value = total_capital * target_position
        target_shares = int(target_value / signal.price / 100) * 100
        
        # 5. 计算交易数量
        if signal.signal_type == SignalType.BUY:
            shares_to_trade = max(0, target_shares - current_shares)
            action = '买入'
        else:
            shares_to_trade = max(0, current_shares - target_shares)
            action = '卖出'
        
        if shares_to_trade < 100:
            result['reason'] = f"交易数量不足 ({shares_to_trade}股)"
            return result
        
        # 6. 仓位限制检查
        new_position = (current_shares + shares_to_trade if signal.signal_type == SignalType.BUY 
                       else current_shares - shares_to_trade)
        new_position_ratio = (new_position * signal.price) / total_capital
        
        allowed, reason = self.risk_monitor.check_position_limit(
            signal.code,
            current_shares * signal.price / total_capital,
            new_position_ratio,
            self._calculate_total_position(account)
        )
        
        if not allowed:
            result['reason'] = f"仓位限制：{reason}"
            return result
        
        # 7. 执行交易
        amount = shares_to_trade * signal.price
        commission = amount * 0.0003  # 0.03% 手续费
        
        if not dry_run:
            if signal.signal_type == SignalType.BUY:
                # 检查资金
                if account.get('cash', 0) < (amount + commission):
                    result['reason'] = "资金不足"
                    return result
                
                # 更新账户
                account['cash'] -= (amount + commission)
                
                # 更新持仓
                if signal.code not in positions:
                    positions[signal.code] = {
                        'shares': 0,
                        'avg_price': 0,
                        'name': signal.name
                    }
                
                pos = positions[signal.code]
                old_value = pos['shares'] * pos['avg_price']
                new_value = amount
                total_shares = pos['shares'] + shares_to_trade
                pos['avg_price'] = (old_value + new_value) / total_shares if total_shares > 0 else 0
                pos['shares'] = total_shares
            
            else:  # SELL
                # 更新账户
                account['cash'] += (amount - commission)
                
                # 更新持仓
                if signal.code in positions:
                    pos = positions[signal.code]
                    profit = (signal.price - pos['avg_price']) * shares_to_trade
                    pos['shares'] -= shares_to_trade
                    
                    if pos['shares'] <= 0:
                        del positions[signal.code]
                    
                    # 记录盈亏
                    self.risk_monitor.record_trade(
                        signal.code,
                        action,
                        signal.price,
                        shares_to_trade,
                        profit
                    )
            
            # 保存账户
            self._save_account(account)
            
            # 记录交易日志
            self._record_trade(
                signal=signal,
                action=action,
                shares=shares_to_trade,
                price=signal.price,
                amount=amount
            )
        
        # 填充结果
        result['success'] = True
        result['action'] = action
        result['shares'] = shares_to_trade
        result['amount'] = amount
        result['reason'] = f"{signal.strategy.value}信号 ({', '.join(signal.reasons)})"
        
        return result
    
    def _calculate_total_capital(self, account: dict) -> float:
        """计算总资金"""
        cash = account.get('cash', 0)
        positions = account.get('positions', {})
        
        position_value = 0
        for code, pos in positions.items():
            # 使用最新价格估算
            current_price = pos.get('current_price', pos.get('avg_price', 0))
            position_value += pos['shares'] * current_price
        
        return cash + position_value
    
    def _calculate_total_position(self, account: dict) -> float:
        """计算总仓位比例"""
        total = self._calculate_total_capital(account)
        if total <= 0:
            return 0.0
        
        cash = account.get('cash', 0)
        return (total - cash) / total
    
    def _record_trade(
        self,
        signal: Signal,
        action: str,
        shares: int,
        price: float,
        amount: float
    ):
        """记录交易日志"""
        trade_log = self._load_trade_log()
        
        trade = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'code': signal.code,
            'name': signal.name,
            'action': action,
            'shares': shares,
            'price': price,
            'amount': amount,
            'strategy': signal.strategy.value,
            'reason': ', '.join(signal.reasons),
            'trade_id': f'MF{len(trade_log)+1:08d}',
            'status': 'completed'
        }
        
        trade_log.append(trade)
        self._save_trade_log(trade_log)
        
        self._trade_counter += 1
    
    def _load_trade_log(self) -> list:
        """加载交易日志"""
        if self.trade_log_file.exists():
            with open(self.trade_log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_trade_log(self, log: list):
        """保存交易日志"""
        with open(self.trade_log_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    
    def _load_account(self) -> dict:
        """加载账户"""
        with open(self.account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_account(self, account: dict):
        """保存账户"""
        with open(self.account_file, 'w', encoding='utf-8') as f:
            json.dump(account, f, ensure_ascii=False, indent=2)
    
    def get_stats(self) -> dict:
        """获取执行统计"""
        risk_stats = self.risk_monitor.get_daily_stats()
        
        return {
            'today_trades': risk_stats['total_trades'],
            'today_profit': risk_stats['total_profit'],
            'trade_counter': self._trade_counter
        }


# ========== 测试 ==========
if __name__ == '__main__':
    print("="*60)
    print("测试执行引擎")
    print("="*60)
    
    from .signal_generator import Signal, SignalType, StrategyType
    
    # 配置
    account_file = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json'
    trade_log_file = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json'
    
    risk_config = {
        'max_position_per_stock': 0.10,
        'stop_loss': -0.03,
        'take_profit': 0.08,
    }
    
    engine = ExecutionEngine(account_file, trade_log_file, risk_config)
    
    # 加载账户
    import json
    with open(account_file, 'r', encoding='utf-8') as f:
        account = json.load(f)
    
    print(f"\n【1】模拟买入信号")
    signal = Signal(
        code='sh.603986',
        name='兆易创新',
        signal_type=SignalType.BUY,
        strategy=StrategyType.SWING,
        price=95.0,
        confidence=0.75,
        reasons=['RSI 超卖', 'MACD 金叉'],
        target_position=0.08
    )
    
    result = engine.execute_signal(signal, account, dry_run=True)
    print(f"  成功：{result['success']}")
    print(f"  动作：{result['action']}")
    print(f"  数量：{result['shares']}股")
    print(f"  金额：¥{result['amount']/10000:.2f}万")
    print(f"  原因：{result['reason']}")
    
    print(f"\n【2】执行统计")
    stats = engine.get_stats()
    print(f"  今日交易：{stats['today_trades']}笔")
    print(f"  今日盈亏：¥{stats['today_profit']:.2f}")
    
    print("\n✅ 测试完成")
