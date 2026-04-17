# -*- coding: utf-8 -*-
"""
BobQuant 自动调仓策略模块 v1.0

功能:
- 定期调仓（每周/每月）
- 等权重调仓
- 目标仓位调仓
- 调仓阈值（偏离>5% 触发）
- 自动生成调仓订单
- 考虑交易成本和 T+1 限制

集成方式:
1. 在 main.py 中初始化 RebalanceEngine
2. 在策略检查流程中调用 rebalance_engine.check_rebalance()
3. 配置文件中设置调仓参数
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from ..core.account import Account, get_sellable_shares
    from ..core.executor import Executor
    from ..config import ConfigLoader
except ImportError:
    from core.account import Account, get_sellable_shares
    from core.executor import Executor
    from config import ConfigLoader


class RebalanceConfig:
    """调仓配置"""
    
    def __init__(self, config_dict: dict = None):
        cfg = config_dict or {}
        
        # 调仓模式
        self.enabled = cfg.get('enabled', False)
        self.mode = cfg.get('mode', 'equal_weight')  # equal_weight / target_weight
        
        # 调仓频率
        self.frequency = cfg.get('frequency', 'weekly')  # daily / weekly / monthly
        self.rebalance_day = cfg.get('rebalance_day', 0)  # 0=周一，0-31=每月第几天
        
        # 调仓阈值
        self.threshold_pct = cfg.get('threshold_pct', 0.05)  # 偏离 5% 触发
        self.min_trade_value = cfg.get('min_trade_value', 1000)  # 最小交易金额
        
        # 交易成本
        self.commission_rate = cfg.get('commission_rate', 0.0005)  # 万分之五
        self.stamp_duty_rate = cfg.get('stamp_duty_rate', 0.001)  # 千分之一
        self.slippage = cfg.get('slippage', 0.001)  # 滑点 0.1%
        
        # 仓位限制
        self.max_position_pct = cfg.get('max_position_pct', 0.10)  # 单票最大 10%
        self.min_position_pct = cfg.get('min_position_pct', 0.02)  # 单票最小 2%
        self.target_positions = cfg.get('target_positions', {})  # 目标仓位 {code: pct}
        
        # T+1 限制
        self.respect_t1 = cfg.get('respect_t1', True)
        
        # 股票池
        self.stock_pool = cfg.get('stock_pool', [])
        
        # 通知
        self.notify_enabled = cfg.get('notify_enabled', True)


class RebalanceOrder:
    """调仓订单"""
    
    def __init__(self, code: str, name: str, action: str, shares: int, 
                 price: float, reason: str, priority: int = 0):
        self.code = code
        self.name = name
        self.action = action  # buy / sell
        self.shares = shares
        self.price = price
        self.reason = reason
        self.priority = priority  # 优先级，数字越大优先级越高
        self.estimated_value = shares * price
        self.estimated_cost = self._calc_cost()
    
    def _calc_cost(self) -> float:
        """估算交易成本"""
        value = self.estimated_value
        commission = value * 0.0005  # 佣金
        if self.action == 'sell':
            stamp_duty = value * 0.001  # 印花税（仅卖出）
        else:
            stamp_duty = 0
        slippage = value * 0.001  # 滑点
        return commission + stamp_duty + slippage
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'action': self.action,
            'shares': self.shares,
            'price': self.price,
            'reason': self.reason,
            'priority': self.priority,
            'estimated_value': self.estimated_value,
            'estimated_cost': self.estimated_cost,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


class RebalanceEngine:
    """自动调仓引擎"""
    
    def __init__(self, config: RebalanceConfig, log_callback=None, notify_callback=None):
        self.config = config
        self.log = log_callback or (lambda msg: print(msg))
        self.notify = notify_callback or (lambda title, msg: None)
        
        self.last_rebalance_date: Optional[str] = None
        self.rebalance_history: List[dict] = []
        self.pending_orders: List[RebalanceOrder] = []
        
        # 加载上次调仓日期
        self._load_state()
    
    def _load_state(self):
        """加载调仓状态"""
        state_file = Path(__file__).parent.parent / "logs" / "rebalance_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.last_rebalance_date = state.get('last_rebalance_date')
                    self.rebalance_history = state.get('history', [])[-50:]  # 保留最近 50 次
            except Exception as e:
                self.log(f"  ⚠️ 加载调仓状态失败：{e}")
    
    def _save_state(self):
        """保存调仓状态"""
        state_file = Path(__file__).parent.parent / "logs" / "rebalance_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            'last_rebalance_date': self.last_rebalance_date,
            'history': self.rebalance_history,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def should_rebalance(self) -> Tuple[bool, str]:
        """
        判断是否应该执行调仓
        
        Returns:
            (should_rebalance, reason)
        """
        if not self.config.enabled:
            return False, "调仓功能未启用"
        
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        
        # 检查是否已经调过仓
        if self.last_rebalance_date == today_str:
            return False, f"今日 ({today_str}) 已调仓"
        
        # 检查调仓频率
        if self.config.frequency == 'daily':
            return True, f"每日调仓模式"
        
        elif self.config.frequency == 'weekly':
            # 检查是否是调仓日（默认周一）
            if today.weekday() == self.config.rebalance_day:
                return True, f"每周调仓模式 (周{['一', '二', '三', '四', '五', '六', '日'][today.weekday()]})"
            else:
                return False, f"非调仓日 (调仓日：周{['一', '二', '三', '四', '五', '六', '日'][self.config.rebalance_day]})"
        
        elif self.config.frequency == 'monthly':
            # 检查是否是调仓日（每月第几天）
            if today.day == self.config.rebalance_day or \
               (today.day >= 28 and self.config.rebalance_day >= 28):  # 月末处理
                return True, f"每月调仓模式 (每月{self.config.rebalance_day}日)"
            else:
                return False, f"非调仓日 (调仓日：每月{self.config.rebalance_day}日)"
        
        return False, "未知调仓频率"
    
    def check_position_deviation(self, account: Account, current_prices: Dict[str, float]) -> Tuple[bool, float, str]:
        """
        检查当前仓位偏离度
        
        Args:
            account: 账户对象
            current_prices: 当前价格 {code: price}
        
        Returns:
            (needs_rebalance, max_deviation, reason)
        """
        if not self.config.stock_pool:
            return False, 0, "未配置股票池"
        
        # 计算总资产
        total_asset = account.cash
        positions_value = {}
        
        for code, pos in account.positions.items():
            shares = pos.get('shares', 0)
            price = current_prices.get(code, 0)
            value = shares * price
            positions_value[code] = value
            total_asset += value
        
        if total_asset == 0:
            return False, 0, "总资产为 0"
        
        # 计算当前仓位比例和目标仓位比例
        max_deviation = 0
        deviation_details = []
        
        for code in self.config.stock_pool:
            current_pct = positions_value.get(code, 0) / total_asset
            
            # 获取目标仓位
            if self.config.mode == 'equal_weight':
                target_pct = 1.0 / len(self.config.stock_pool)
            else:
                target_pct = self.config.target_positions.get(code, 1.0 / len(self.config.stock_pool))
            
            # 计算偏离度
            deviation = abs(current_pct - target_pct)
            max_deviation = max(max_deviation, deviation)
            
            if deviation > self.config.threshold_pct:
                deviation_details.append(
                    f"{code}: 当前{current_pct*100:.1f}% vs 目标{target_pct*100:.1f}% (偏离{deviation*100:.1f}%)"
                )
        
        needs_rebalance = max_deviation > self.config.threshold_pct
        
        if needs_rebalance:
            reason = f"仓位偏离超过阈值 ({max_deviation*100:.1f}% > {self.config.threshold_pct*100:.1f}%):\n" + \
                     "\n".join(deviation_details[:5])  # 只显示前 5 个
        else:
            reason = f"仓位偏离在阈值内 (最大{max_deviation*100:.1f}% <= {self.config.threshold_pct*100:.1f}%)"
        
        return needs_rebalance, max_deviation, reason
    
    def generate_rebalance_orders(self, account: Account, current_prices: Dict[str, float], 
                                   stock_names: Dict[str, str] = None) -> List[RebalanceOrder]:
        """
        生成调仓订单
        
        Args:
            account: 账户对象
            current_prices: 当前价格 {code: price}
            stock_names: 股票名称 {code: name}
        
        Returns:
            List[RebalanceOrder]: 调仓订单列表
        """
        stock_names = stock_names or {}
        orders = []
        
        if not self.config.stock_pool:
            self.log("  ⚠️ 未配置股票池，无法生成调仓订单")
            return orders
        
        # 计算总资产和目标仓位
        total_asset = account.cash
        positions_value = {}
        
        for code, pos in account.positions.items():
            shares = pos.get('shares', 0)
            price = current_prices.get(code, 0)
            value = shares * price
            positions_value[code] = value
            total_asset += value
        
        if total_asset == 0:
            self.log("  ⚠️ 总资产为 0，无法生成调仓订单")
            return orders
        
        # 计算每个股票的目标价值和当前价值
        target_values = {}
        current_values = {}
        
        for code in self.config.stock_pool:
            if self.config.mode == 'equal_weight':
                target_pct = 1.0 / len(self.config.stock_pool)
            else:
                target_pct = self.config.target_positions.get(code, 1.0 / len(self.config.stock_pool))
            
            target_values[code] = total_asset * target_pct
            current_values[code] = positions_value.get(code, 0)
        
        # 生成交易订单
        sell_orders = []
        buy_orders = []
        
        for code in self.config.stock_pool:
            name = stock_names.get(code, code)
            target_value = target_values[code]
            current_value = current_values[code]
            diff_value = target_value - current_value
            
            # 忽略小额差异
            if abs(diff_value) < self.config.min_trade_value:
                continue
            
            price = current_prices.get(code, 0)
            if price == 0:
                self.log(f"  ⚠️ {code} 无价格数据，跳过")
                continue
            
            # 计算股数（考虑交易规则）
            shares = int(abs(diff_value) / price / 100) * 100  # 100 股的整数倍
            if shares == 0:
                continue
            
            if diff_value > 0:
                # 需要买入
                # 检查现金是否足够
                required_cash = shares * price * (1 + self.config.commission_rate)
                if required_cash > account.cash:
                    # 现金不足，按最大可买数量调整
                    shares = int(account.cash / price / (1 + self.config.commission_rate) / 100) * 100
                    if shares == 0:
                        self.log(f"  ⚠️ {code} 现金不足，跳过买入")
                        continue
                
                orders.append(RebalanceOrder(
                    code=code,
                    name=name,
                    action='buy',
                    shares=shares,
                    price=price,
                    reason=f"调仓买入：目标{target_pct*100:.1f}% (当前{current_value/total_asset*100:.1f}%)",
                    priority=2
                ))
            else:
                # 需要卖出
                # 检查 T+1 限制
                if code in account.positions:
                    pos = account.positions[code]
                    if self.config.respect_t1:
                        sellable = get_sellable_shares(pos)
                        shares = min(shares, sellable)
                        if shares == 0:
                            self.log(f"  ⚠️ {code} 无可用股数 (T+1 限制)，跳过卖出")
                            continue
                    else:
                        shares = min(shares, pos.get('shares', 0))
                
                if shares > 0:
                    orders.append(RebalanceOrder(
                        code=code,
                        name=name,
                        action='sell',
                        shares=shares,
                        price=price,
                        reason=f"调仓卖出：目标{target_pct*100:.1f}% (当前{current_value/total_asset*100:.1f}%)",
                        priority=1  # 卖出优先级更高（释放现金）
                    ))
        
        # 按优先级排序：先卖后买
        orders.sort(key=lambda x: (-x.priority, x.code))
        
        return orders
    
    def execute_rebalance(self, account: Account, executor: Executor, 
                          current_prices: Dict[str, float],
                          stock_names: Dict[str, str] = None) -> dict:
        """
        执行调仓
        
        Args:
            account: 账户对象
            executor: 执行器对象
            current_prices: 当前价格 {code: price}
            stock_names: 股票名称 {code: name}
        
        Returns:
            dict: 调仓结果摘要
        """
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        self.log("=" * 60)
        self.log(f"🔄 开始执行自动调仓 ({today_str})")
        self.log("=" * 60)
        
        # 生成订单
        orders = self.generate_rebalance_orders(account, current_prices, stock_names)
        
        if not orders:
            self.log("  ✅ 无需调仓或无可用订单")
            return {'success': True, 'orders': 0, 'message': '无需调仓'}
        
        self.log(f"  📋 生成 {len(orders)} 个调仓订单:")
        for i, order in enumerate(orders, 1):
            action_icon = "🟢" if order.action == 'buy' else "🔴"
            self.log(f"    {i}. {action_icon} {order.action.upper()} {order.name} ({order.code}) "
                    f"{order.shares}股 @ ¥{order.price:.2f} (≈¥{order.estimated_value:.0f})")
        
        # 执行订单
        executed_count = 0
        failed_count = 0
        total_value = 0
        total_cost = 0
        
        for order in orders:
            try:
                # 模拟执行（实际集成时调用 executor 的方法）
                # 这里返回订单信息，由主引擎决定如何执行
                self.pending_orders.append(order)
                executed_count += 1
                total_value += order.estimated_value
                total_cost += order.estimated_cost
                
                self.log(f"  ✅ {order.action.upper()} {order.name} {order.shares}股 已提交")
                
            except Exception as e:
                failed_count += 1
                self.log(f"  ❌ {order.name} 执行失败：{e}")
        
        # 记录调仓历史
        rebalance_record = {
            'date': today_str,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mode': self.config.mode,
            'orders_count': executed_count,
            'total_value': total_value,
            'total_cost': total_cost,
            'orders': [o.to_dict() for o in self.pending_orders[-len(orders):]]
        }
        self.rebalance_history.append(rebalance_record)
        self.last_rebalance_date = today_str
        self._save_state()
        
        # 发送通知
        if self.config.notify_enabled and self.notify:
            title = f"🔄 调仓执行完成 ({today_str})"
            message = f"执行模式：{self.config.mode}\n" \
                     f"订单数量：{executed_count} 个\n" \
                     f"成交金额：¥{total_value:,.0f}\n" \
                     f"交易成本：¥{total_cost:,.0f}\n" \
                     f"失败订单：{failed_count} 个"
            self.notify(title, message)
        
        self.log("=" * 60)
        self.log(f"✅ 调仓完成：{executed_count} 个订单，成交¥{total_value:,.0f}, 成本¥{total_cost:,.0f}")
        self.log("=" * 60)
        
        return {
            'success': True,
            'orders': executed_count,
            'failed': failed_count,
            'total_value': total_value,
            'total_cost': total_cost,
            'records': rebalance_record
        }
    
    def check_rebalance(self, account: Account, executor: Executor,
                        current_prices: Dict[str, float],
                        stock_names: Dict[str, str] = None) -> dict:
        """
        检查并执行调仓（主接口）
        
        Args:
            account: 账户对象
            executor: 执行器对象
            current_prices: 当前价格 {code: price}
            stock_names: 股票名称 {code: name}
        
        Returns:
            dict: 调仓结果
        """
        # 检查是否应该调仓
        should_reb, reason = self.should_rebalance()
        
        if not should_reb:
            self.log(f"⏭️ 跳过调仓：{reason}")
            return {'success': True, 'skipped': True, 'reason': reason}
        
        self.log(f"✅ 触发调仓：{reason}")
        
        # 检查仓位偏离
        needs_reb, deviation, dev_reason = self.check_position_deviation(account, current_prices)
        
        if not needs_reb:
            self.log(f"⏭️ 仓位正常：{dev_reason}")
            return {'success': True, 'skipped': True, 'reason': dev_reason}
        
        self.log(f"📊 仓位偏离检测：{dev_reason}")
        
        # 执行调仓
        return self.execute_rebalance(account, executor, current_prices, stock_names)
    
    def get_rebalance_summary(self) -> dict:
        """获取调仓摘要"""
        return {
            'enabled': self.config.enabled,
            'mode': self.config.mode,
            'frequency': self.config.frequency,
            'last_rebalance': self.last_rebalance_date,
            'total_rebalances': len(self.rebalance_history),
            'recent_history': self.rebalance_history[-5:]
        }


# ==================== 工厂函数 ====================

def create_rebalance_engine(config_dict: dict = None, log_callback=None, notify_callback=None) -> RebalanceEngine:
    """
    创建调仓引擎
    
    Args:
        config_dict: 配置字典（从 settings.yaml 读取）
        log_callback: 日志回调函数
        notify_callback: 通知回调函数
    
    Returns:
        RebalanceEngine: 调仓引擎实例
    """
    cfg = RebalanceConfig(config_dict)
    return RebalanceEngine(cfg, log_callback, notify_callback)


def get_rebalance_config_from_settings(config_path: str = None) -> dict:
    """从全局配置读取调仓配置"""
    if config_path is None:
        config_path = "bobquant/config/sim_config_v2_2.yaml"
    loader = ConfigLoader(config_path)
    config = loader.load()
    return config.get('rebalance', {})


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试调仓引擎
    print("🧪 测试自动调仓引擎...")
    
    # 模拟配置
    test_config = {
        'enabled': True,
        'mode': 'equal_weight',
        'frequency': 'weekly',
        'rebalance_day': 0,  # 周一
        'threshold_pct': 0.05,
        'stock_pool': ['sh.600000', 'sh.600036', 'sz.000001', 'sz.000002'],
        'max_position_pct': 0.25,
        'notify_enabled': False
    }
    
    # 创建引擎
    engine = create_rebalance_engine(test_config, log_callback=print)
    
    # 模拟账户
    class MockAccount:
        def __init__(self):
            self.cash = 500000
            self.positions = {
                'sh.600000': {'shares': 5000, 'avg_price': 10.0},
                'sh.600036': {'shares': 3000, 'avg_price': 35.0},
            }
    
    # 模拟价格
    test_prices = {
        'sh.600000': 10.5,
        'sh.600036': 36.0,
        'sz.000001': 12.0,
        'sz.000002': 25.0
    }
    
    # 模拟执行器
    class MockExecutor:
        def __init__(self):
            pass
    
    account = MockAccount()
    executor = MockExecutor()
    
    # 测试
    print("\n1️⃣ 检查是否应该调仓:")
    should, reason = engine.should_rebalance()
    print(f"   结果：{should}, 原因：{reason}")
    
    print("\n2️⃣ 检查仓位偏离:")
    needs, dev, dev_reason = engine.check_position_deviation(account, test_prices)
    print(f"   结果：{needs}, 最大偏离：{dev*100:.1f}%")
    print(f"   原因：{dev_reason}")
    
    print("\n3️⃣ 生成调仓订单:")
    orders = engine.generate_rebalance_orders(account, test_prices)
    print(f"   生成订单数：{len(orders)}")
    for order in orders:
        print(f"   - {order.action.upper()} {order.code} {order.shares}股 @ ¥{order.price:.2f}")
    
    print("\n4️⃣ 调仓摘要:")
    summary = engine.get_rebalance_summary()
    for k, v in summary.items():
        print(f"   {k}: {v}")
    
    print("\n✅ 测试完成!")
