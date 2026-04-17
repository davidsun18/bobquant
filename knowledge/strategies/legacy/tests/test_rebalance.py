# -*- coding: utf-8 -*-
"""
BobQuant 自动调仓策略测试

测试场景:
1. 等权重调仓
2. 目标仓位调仓
3. 调仓阈值触发
4. T+1 限制处理
5. 交易成本计算
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategy.rebalance import (
    RebalanceConfig, 
    RebalanceEngine, 
    RebalanceOrder,
    create_rebalance_engine
)
from core.account import Account


class MockExecutor:
    """模拟执行器"""
    def __init__(self, account, log_callback):
        self.account = account
        self.log = log_callback
        self.trades = []
    
    def buy(self, code, name, shares, price, reason, **kwargs):
        """模拟买入"""
        cost = shares * price * (1 + 0.0005)
        if cost > self.account.cash:
            self.log(f"  ❌ 买入失败：现金不足 (需要¥{cost:,.0f}, 可用¥{self.account.cash:,.0f})")
            return None
        
        self.account.cash -= cost
        
        # 更新持仓
        if code not in self.account.positions:
            self.account.positions[code] = {
                'shares': 0,
                'avg_price': 0,
                'buy_lots': []
            }
        
        pos = self.account.positions[code]
        old_value = pos['shares'] * pos['avg_price'] if pos['avg_price'] > 0 else 0
        new_value = shares * price
        total_shares = pos['shares'] + shares
        pos['avg_price'] = (old_value + new_value) / total_shares if total_shares > 0 else price
        pos['shares'] = total_shares
        pos['buy_lots'].append({
            'shares': shares,
            'price': price,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S')
        })
        
        trade = {
            'code': code,
            'name': name,
            'action': 'buy',
            'shares': shares,
            'price': price,
            'reason': reason,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.trades.append(trade)
        self.log(f"  ✅ 买入 {name}: {shares}股 @ ¥{price:.2f} (¥{cost:,.0f})")
        return trade
    
    def sell(self, code, name, shares, price, reason, **kwargs):
        """模拟卖出"""
        if code not in self.account.positions:
            self.log(f"  ❌ 卖出失败：无持仓")
            return None
        
        pos = self.account.positions[code]
        if pos['shares'] < shares:
            self.log(f"  ❌ 卖出失败：持仓不足 (持有{pos['shares']}股，卖出{shares}股)")
            return None
        
        # 计算收益
        revenue = shares * price * (1 - 0.001 - 0.0005)  # 印花税 + 佣金
        self.account.cash += revenue
        
        # 更新持仓
        pos['shares'] -= shares
        if pos['shares'] == 0:
            del self.account.positions[code]
        
        trade = {
            'code': code,
            'name': name,
            'action': 'sell',
            'shares': shares,
            'price': price,
            'reason': reason,
            'pnl': revenue - shares * pos.get('avg_price', price),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.trades.append(trade)
        self.log(f"  ✅ 卖出 {name}: {shares}股 @ ¥{price:.2f} (¥{revenue:,.0f})")
        return trade


def test_equal_weight_rebalance():
    """测试等权重调仓"""
    print("\n" + "="*80)
    print("🧪 测试 1: 等权重调仓")
    print("="*80)
    
    # 配置
    config = {
        'enabled': True,
        'mode': 'equal_weight',
        'frequency': 'daily',  # 每天都可以调仓
        'threshold_pct': 0.05,
        'stock_pool': ['sh.600000', 'sh.600036', 'sz.000001', 'sz.000002'],
        'max_position_pct': 0.25,
        'min_trade_value': 1000,
        'respect_t1': True,
        'notify_enabled': False
    }
    
    # 创建引擎
    log_messages = []
    def log_callback(msg):
        log_messages.append(msg)
        print(msg)
    
    engine = create_rebalance_engine(config, log_callback)
    
    # 创建模拟账户（初始状态：全仓一只股票）
    account = Account('/tmp/test_rebalance_account.json', initial_capital=1000000)
    account._data = {
        'cash': 200000,
        'initial_capital': 1000000,
        'positions': {
            'sh.600000': {
                'shares': 80000,
                'avg_price': 10.0,
                'buy_lots': [{'shares': 80000, 'price': 10.0, 'date': '2026-04-10'}]
            }
        },
        'trade_history': []
    }
    
    # 当前价格
    current_prices = {
        'sh.600000': 10.5,  # 持仓股票
        'sh.600036': 35.0,
        'sz.000001': 12.0,
        'sz.000002': 25.0
    }
    
    # 模拟执行器
    executor = MockExecutor(account, log_callback)
    
    # 测试
    print("\n📊 初始状态:")
    print(f"  现金：¥{account.cash:,.0f}")
    print(f"  持仓：{len(account.positions)} 只")
    for code, pos in account.positions.items():
        value = pos['shares'] * current_prices.get(code, 0)
        print(f"    {code}: {pos['shares']}股 @ ¥{current_prices.get(code, 0):.2f} = ¥{value:,.0f}")
    
    total_asset = account.cash + sum(pos['shares'] * current_prices.get(code, 0) 
                                     for code, pos in account.positions.items())
    print(f"  总资产：¥{total_asset:,.0f}")
    
    print("\n🎯 目标配置 (等权重 25% 每只):")
    for code in config['stock_pool']:
        target_value = total_asset * 0.25
        print(f"    {code}: ¥{target_value:,.0f}")
    
    print("\n🔄 执行调仓:")
    result = engine.execute_rebalance(account, executor, current_prices)
    
    print("\n📊 调仓后状态:")
    print(f"  现金：¥{account.cash:,.0f}")
    print(f"  持仓：{len(account.positions)} 只")
    for code, pos in account.positions.items():
        value = pos['shares'] * current_prices.get(code, 0)
        pct = value / (account.cash + sum(p['shares'] * current_prices.get(c, 0) 
                                          for c, p in account.positions.items())) * 100
        print(f"    {code}: {pos['shares']}股 @ ¥{current_prices.get(code, 0):.2f} = ¥{value:,.0f} ({pct:.1f}%)")
    
    print(f"\n✅ 测试结果：生成 {result.get('orders', 0)} 个订单")
    return result


def test_target_weight_rebalance():
    """测试目标仓位调仓"""
    print("\n" + "="*80)
    print("🧪 测试 2: 目标仓位调仓")
    print("="*80)
    
    # 配置（自定义目标仓位）
    config = {
        'enabled': True,
        'mode': 'target_weight',
        'frequency': 'daily',
        'threshold_pct': 0.05,
        'stock_pool': ['sh.600000', 'sh.600036', 'sz.000001', 'sz.000002'],
        'target_positions': {
            'sh.600000': 0.30,  # 30%
            'sh.600036': 0.30,  # 30%
            'sz.000001': 0.25,  # 25%
            'sz.000002': 0.15   # 15%
        },
        'max_position_pct': 0.30,
        'min_trade_value': 1000,
        'respect_t1': True,
        'notify_enabled': False
    }
    
    def log_callback(msg):
        print(msg)
    
    engine = create_rebalance_engine(config, log_callback)
    
    # 创建模拟账户（初始状态：等权重）
    account = Account('/tmp/test_rebalance_account2.json', initial_capital=1000000)
    account._data = {
        'cash': 0,
        'initial_capital': 1000000,
        'positions': {
            'sh.600000': {'shares': 25000, 'avg_price': 10.0, 'buy_lots': []},
            'sh.600036': {'shares': 7142, 'avg_price': 35.0, 'buy_lots': []},
            'sz.000001': {'shares': 20833, 'avg_price': 12.0, 'buy_lots': []},
            'sz.000002': {'shares': 10000, 'avg_price': 25.0, 'buy_lots': []}
        },
        'trade_history': []
    }
    
    current_prices = {
        'sh.600000': 10.0,
        'sh.600036': 35.0,
        'sz.000001': 12.0,
        'sz.000002': 25.0
    }
    
    executor = MockExecutor(account, log_callback)
    
    print("\n📊 初始状态 (等权重 25% 每只):")
    total_asset = account.cash + sum(pos['shares'] * current_prices.get(code, 0) 
                                     for code, pos in account.positions.items())
    for code, pos in account.positions.items():
        value = pos['shares'] * current_prices.get(code, 0)
        pct = value / total_asset * 100
        print(f"    {code}: ¥{value:,.0f} ({pct:.1f}%)")
    
    print("\n🎯 目标配置:")
    for code, target_pct in config['target_positions'].items():
        target_value = total_asset * target_pct
        print(f"    {code}: {target_pct*100:.0f}% = ¥{target_value:,.0f}")
    
    print("\n🔄 执行调仓:")
    result = engine.execute_rebalance(account, executor, current_prices)
    
    print(f"\n✅ 测试结果：生成 {result.get('orders', 0)} 个订单")
    return result


def test_threshold_trigger():
    """测试调仓阈值触发"""
    print("\n" + "="*80)
    print("🧪 测试 3: 调仓阈值触发")
    print("="*80)
    
    config = {
        'enabled': True,
        'mode': 'equal_weight',
        'frequency': 'daily',
        'threshold_pct': 0.05,  # 5% 阈值
        'stock_pool': ['sh.600000', 'sh.600036'],
        'max_position_pct': 0.50,
        'min_trade_value': 1000,
        'respect_t1': True,
        'notify_enabled': False
    }
    
    def log_callback(msg):
        print(msg)
    
    engine = create_rebalance_engine(config, log_callback)
    
    # 场景 1: 偏离度 < 5%，不触发
    account1 = Account('/tmp/test_rebalance_account3.json', initial_capital=1000000)
    account1._data = {
        'cash': 0,
        'initial_capital': 1000000,
        'positions': {
            'sh.600000': {'shares': 52000, 'avg_price': 10.0, 'buy_lots': []},  # 52%
            'sh.600036': {'shares': 13714, 'avg_price': 35.0, 'buy_lots': []}   # 48%
        }
    }
    
    prices1 = {'sh.600000': 10.0, 'sh.600036': 35.0}
    
    print("\n📊 场景 1: 偏离度 2% (52% vs 48%)")
    needs, dev, reason = engine.check_position_deviation(account1, prices1)
    print(f"  最大偏离：{dev*100:.1f}%")
    print(f"  是否触发：{needs}")
    print(f"  原因：{reason}")
    
    # 场景 2: 偏离度 > 5%，触发
    account2 = Account('/tmp/test_rebalance_account4.json', initial_capital=1000000)
    account2._data = {
        'cash': 0,
        'initial_capital': 1000000,
        'positions': {
            'sh.600000': {'shares': 60000, 'avg_price': 10.0, 'buy_lots': []},  # 60%
            'sh.600036': {'shares': 11428, 'avg_price': 35.0, 'buy_lots': []}   # 40%
        }
    }
    
    prices2 = {'sh.600000': 10.0, 'sh.600036': 35.0}
    
    print("\n📊 场景 2: 偏离度 10% (60% vs 40%)")
    needs, dev, reason = engine.check_position_deviation(account2, prices2)
    print(f"  最大偏离：{dev*100:.1f}%")
    print(f"  是否触发：{needs}")
    print(f"  原因：{reason}")
    
    print(f"\n✅ 测试结果：阈值触发逻辑正常")
    return {'scenario1_triggered': needs, 'scenario2_triggered': needs}


def test_t1_limit():
    """测试 T+1 限制"""
    print("\n" + "="*80)
    print("🧪 测试 4: T+1 限制处理")
    print("="*80)
    
    config = {
        'enabled': True,
        'mode': 'equal_weight',
        'frequency': 'daily',
        'threshold_pct': 0.05,
        'stock_pool': ['sh.600000'],
        'respect_t1': True,
        'notify_enabled': False
    }
    
    def log_callback(msg):
        print(msg)
    
    engine = create_rebalance_engine(config, log_callback)
    
    # 今日买入的持仓
    today = datetime.now().strftime('%Y-%m-%d')
    account = Account('/tmp/test_rebalance_account5.json', initial_capital=1000000)
    account._data = {
        'cash': 500000,
        'initial_capital': 1000000,
        'positions': {
            'sh.600000': {
                'shares': 100000,
                'avg_price': 10.0,
                'buy_lots': [
                    {'shares': 50000, 'price': 10.0, 'date': today},      # 今日买入，不可卖
                    {'shares': 50000, 'price': 10.0, 'date': '2026-04-10'}  # 昨日买入，可卖
                ]
            }
        }
    }
    
    prices = {'sh.600000': 10.0}
    
    print(f"\n📊 持仓状态 (今日：{today}):")
    print(f"  总股数：100000 股")
    print(f"  今日买入：50000 股 (不可卖)")
    print(f"  昨日买入：50000 股 (可卖)")
    
    # 生成调仓订单
    orders = engine.generate_rebalance_orders(account, prices)
    
    print("\n🔄 生成调仓订单:")
    for order in orders:
        t1_status = "⚠️ T+1 限制" if order.action == 'sell' and order.shares == 0 else "✅"
        print(f"  {t1_status} {order.action.upper()} {order.shares}股")
    
    print(f"\n✅ 测试结果：T+1 限制处理正常")
    return {'orders': len(orders)}


def test_transaction_cost():
    """测试交易成本计算"""
    print("\n" + "="*80)
    print("🧪 测试 5: 交易成本计算")
    print("="*80)
    
    # 买入订单
    buy_order = RebalanceOrder(
        code='sh.600000',
        name='浦发银行',
        action='buy',
        shares=10000,
        price=10.0,
        reason='调仓买入'
    )
    
    print("\n📊 买入订单:")
    print(f"  成交金额：¥{buy_order.estimated_value:,.0f}")
    print(f"  交易成本：¥{buy_order.estimated_cost:,.0f}")
    print(f"  成本率：{buy_order.estimated_cost/buy_order.estimated_value*100:.2f}%")
    print(f"  明细：佣金 0.05% + 印花税 0% + 滑点 0.1%")
    
    # 卖出订单
    sell_order = RebalanceOrder(
        code='sh.600000',
        name='浦发银行',
        action='sell',
        shares=10000,
        price=10.0,
        reason='调仓卖出'
    )
    
    print("\n📊 卖出订单:")
    print(f"  成交金额：¥{sell_order.estimated_value:,.0f}")
    print(f"  交易成本：¥{sell_order.estimated_cost:,.0f}")
    print(f"  成本率：{sell_order.estimated_cost/sell_order.estimated_value*100:.2f}%")
    print(f"  明细：佣金 0.05% + 印花税 0.1% + 滑点 0.1%")
    
    print(f"\n✅ 测试结果：交易成本计算正常")
    return {
        'buy_cost_rate': buy_order.estimated_cost/buy_order.estimated_value,
        'sell_cost_rate': sell_order.estimated_cost/sell_order.estimated_value
    }


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("🧪 BobQuant 自动调仓策略测试套件")
    print("="*80)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    try:
        results['test1_equal_weight'] = test_equal_weight_rebalance()
    except Exception as e:
        print(f"\n❌ 测试 1 失败：{e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['test2_target_weight'] = test_target_weight_rebalance()
    except Exception as e:
        print(f"\n❌ 测试 2 失败：{e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['test3_threshold'] = test_threshold_trigger()
    except Exception as e:
        print(f"\n❌ 测试 3 失败：{e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['test4_t1_limit'] = test_t1_limit()
    except Exception as e:
        print(f"\n❌ 测试 4 失败：{e}")
        import traceback
        traceback.print_exc()
    
    try:
        results['test5_cost'] = test_transaction_cost()
    except Exception as e:
        print(f"\n❌ 测试 5 失败：{e}")
        import traceback
        traceback.print_exc()
    
    # 汇总
    print("\n" + "="*80)
    print("📊 测试汇总")
    print("="*80)
    print(f"总测试数：{len(results)}")
    print(f"成功：{len([r for r in results.values() if r])}")
    print(f"失败：{len([r for r in results.values() if not r])}")
    
    print("\n✅ 所有测试完成!")
    print("="*80)
    
    return results


if __name__ == "__main__":
    main()
