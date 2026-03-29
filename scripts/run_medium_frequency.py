#!/usr/bin/env python3
"""
中频交易主程序

用法:
python3 scripts/run_medium_frequency.py [--dry-run] [--config CONFIG]
"""

import sys
import time
import yaml
import argparse
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from medium_frequency import (
    MinuteDataFetcher,
    SignalGenerator,
    ExecutionEngine,
)
from medium_frequency.signal_generator import StrategyType


class MediumFrequencyTrader:
    """中频交易器"""
    
    def __init__(self, config_file: str, dry_run: bool = False):
        """
        Args:
            config_file: 配置文件路径
            dry_run: 模拟模式
        """
        # 加载配置
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.dry_run = dry_run
        self.mf_config = self.config.get('medium_frequency', {})
        self.strategy_config = self.config.get('strategies', {})
        self.risk_config = self.config.get('risk_control', {})
        
        # 初始化组件
        cache_duration = self.mf_config.get('cache_duration', 60)
        self.data_fetcher = MinuteDataFetcher(cache_duration=cache_duration)
        
        # 合并策略配置
        grid_config = self.strategy_config.get('grid', {})
        swing_config = self.strategy_config.get('swing', {})
        momentum_config = self.strategy_config.get('momentum', {})
        
        strategy_cfg = {
            **grid_config,
            **swing_config,
            **momentum_config,
        }
        
        self.signal_generator = SignalGenerator(strategy_cfg)
        
        # 执行引擎
        account_file = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json'
        trade_log_file = '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json'
        
        self.execution_engine = ExecutionEngine(
            account_file,
            trade_log_file,
            self.risk_config
        )
        
        # 股票池
        self.stock_pool = self.mf_config.get('stock_pool', [])
        
        # 运行状态
        self.running = False
        self.check_interval = self.mf_config.get('check_interval', 300)
    
    def is_trading_time(self) -> bool:
        """检查是否在交易时间"""
        now = datetime.now()
        
        # 周末休市
        if now.weekday() >= 5:
            return False
        
        # 交易时段
        trading_hours = self.mf_config.get('trading_hours', {})
        morning = trading_hours.get('morning', '09:30-11:30')
        afternoon = trading_hours.get('afternoon', '13:00-15:00')
        
        current_time = now.strftime('%H:%M')
        
        # 检查早盘
        start, end = morning.split('-')
        if start <= current_time <= end:
            return True
        
        # 检查午盘
        start, end = afternoon.split('-')
        if start <= current_time <= end:
            return True
        
        return False
    
    def run_once(self):
        """执行一次交易检查"""
        print(f"\n{'='*60}")
        print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # 加载账户
        import json
        account_file = Path(self.execution_engine.account_file)
        with open(account_file, 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        print(f"账户现金：¥{account.get('cash', 0)/10000:.2f}万")
        
        # 遍历股票池
        signals_generated = 0
        signals_executed = 0
        
        for stock in self.stock_pool[:5]:  # 先测试前 5 只
            code = stock['code']
            name = stock['name']
            
            print(f"\n  [{code}] {name}")
            
            # 1. 获取数据
            df = self.data_fetcher.get_minute_kline(
                code, 
                period=5, 
                limit=50,
                use_cache=True
            )
            
            if df is None or len(df) < 30:
                print(f"    ⚠️ 数据不足")
                continue
            
            current_price = df['close'].iloc[-1]
            print(f"    最新价：¥{current_price:.2f}")
            
            # 2. 生成信号
            # 获取当前持仓
            positions = account.get('positions', {})
            current_pos = positions.get(code, {})
            current_position_ratio = (
                current_pos.get('shares', 0) * current_price / 
                (account.get('cash', 0) + sum(
                    p.get('shares', 0) * p.get('current_price', p.get('avg_price', 0))
                    for p in positions.values()
                ))
            )
            
            # 启用所有策略
            strategies = [
                StrategyType.GRID,
                StrategyType.SWING,
                StrategyType.MOMENTUM
            ]
            
            signals = self.signal_generator.generate_signals(
                df=df,
                code=code,
                name=name,
                current_price=current_price,
                position=current_position_ratio,
                strategies=strategies
            )
            
            if signals:
                signals_generated += len(signals)
                print(f"    生成{len(signals)}个信号:")
                
                for signal in signals:
                    print(f"      {signal}")
                    
                    # 3. 执行信号
                    result = self.execution_engine.execute_signal(
                        signal=signal,
                        account=account,
                        dry_run=self.dry_run
                    )
                    
                    if result['success']:
                        signals_executed += 1
                        mode = "[模拟]" if self.dry_run else "[实盘]"
                        print(f"        {mode} {result['action']} {result['shares']}股 "
                              f"@ ¥{result['price']:.2f} (¥{result['amount']/10000:.2f}万)")
                        print(f"        原因：{result['reason']}")
                    else:
                        print(f"        ❌ 执行失败：{result['reason']}")
            else:
                print(f"    暂无信号")
        
        # 统计
        print(f"\n{'='*60}")
        print(f"本次检查完成:")
        print(f"  生成信号：{signals_generated}个")
        print(f"  执行交易：{signals_executed}笔")
        print(f"  模式：{'模拟' if self.dry_run else '实盘'}")
        print(f"{'='*60}")
    
    def run_loop(self):
        """运行交易循环"""
        print("="*60)
        print("🚀 中频交易启动")
        print("="*60)
        print(f"配置：{self.mf_config.get('check_interval', 300)}秒检查一次")
        print(f"股票池：{len(self.stock_pool)}只")
        print(f"模式：{'模拟' if self.dry_run else '实盘'}")
        print("="*60)
        
        self.running = True
        
        try:
            while self.running:
                if self.is_trading_time():
                    self.run_once()
                else:
                    print(f"\n⏸️ 非交易时间，等待...")
                
                # 等待下次检查
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断，停止交易")
            self.running = False
        
        except Exception as e:
            print(f"\n❌ 异常：{e}")
            import traceback
            traceback.print_exc()
            self.running = False
    
    def stop(self):
        """停止交易"""
        self.running = False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='中频交易系统')
    parser.add_argument(
        '--config', 
        type=str, 
        default='/home/openclaw/.openclaw/workspace/quant_strategies/medium_frequency/config/mf_config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='模拟模式 (不实际下单)'
    )
    parser.add_argument(
        '--once', 
        action='store_true', 
        help='只执行一次 (不循环)'
    )
    
    args = parser.parse_args()
    
    # 创建交易器
    trader = MediumFrequencyTrader(
        config_file=args.config,
        dry_run=args.dry_run
    )
    
    if args.once:
        trader.run_once()
    else:
        trader.run_loop()


if __name__ == '__main__':
    main()
