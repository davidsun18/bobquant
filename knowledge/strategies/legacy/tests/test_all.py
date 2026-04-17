# -*- coding: utf-8 -*-
"""
BobQuant 单元测试
覆盖: 配置 / 指标 / 账户 / T+1 / 执行器 / 策略 / 风控 / 做T / 券商
"""
import sys
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime

# 确保项目根目录在 sys.path
_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

import pandas as pd

# ==================== 测试工具 ====================
_pass = 0
_fail = 0

def assert_eq(actual, expected, msg=''):
    global _pass, _fail
    if actual == expected:
        _pass += 1
    else:
        _fail += 1
        print(f"  ❌ FAIL: {msg} | expected={expected}, got={actual}")

def assert_true(condition, msg=''):
    global _pass, _fail
    if condition:
        _pass += 1
    else:
        _fail += 1
        print(f"  ❌ FAIL: {msg}")

def assert_near(actual, expected, tol=0.01, msg=''):
    global _pass, _fail
    if abs(actual - expected) <= tol:
        _pass += 1
    else:
        _fail += 1
        print(f"  ❌ FAIL: {msg} | expected≈{expected}, got={actual}")

def section(name):
    print(f"\n{'='*50}")
    print(f"📋 {name}")
    print(f"{'='*50}")


# ==================== 1. 配置测试 ====================
section("配置系统")

from bobquant.config import get_settings, to_legacy_config, PROJECT_ROOT, POSITIONS_FILE

s = get_settings()
assert_eq(s.initial_capital, 1000000, "初始资金")
assert_eq(s.commission_rate, 0.0005, "手续费率")
assert_eq(s.check_interval, 10, "检查间隔 (v1.1 优化)")
assert_eq(s.get('strategy.stop_loss_pct'), -0.08, "止损线")
assert_eq(s.get('data.primary'), 'tencent', "主数据源")
assert_eq(s.get('broker.mode'), 'simulator', "券商模式")
assert_eq(len(s.stock_pool), 50, "股票池数量")
assert_true(str(PROJECT_ROOT).endswith('bobquant'), "项目根路径")
print(f"  ✅ 配置测试全部通过")

# 向后兼容
CONFIG, TRADE_CONFIG = to_legacy_config()
assert_eq(len(CONFIG), 11, "CONFIG keys")
assert_eq(len(TRADE_CONFIG), 15, "TRADE_CONFIG keys")
assert_eq(CONFIG['stock_pool'][0][0], 'sh.601398', "股票池格式")
print(f"  ✅ 向后兼容测试通过")


# ==================== 2. 指标测试 ====================
section("技术指标")

from bobquant.indicator.technical import macd, bollinger, rsi, volume_ratio, compute_all

# 构造测试数据
prices = [10+i*0.3+(-1)**i*0.2 for i in range(40)]
volumes = [100000+i*5000 for i in range(40)]
df = pd.DataFrame({'close': prices, 'volume': volumes})

df_m = macd(df)
assert_true('macd' in df_m.columns, "MACD列存在")
assert_true('ma1' in df_m.columns, "MA1兼容列")
assert_true(pd.notna(df_m['macd'].iloc[-1]), "MACD有值")
print(f"  ✅ MACD 计算正常")

df_b = bollinger(df)
assert_true('bb_pos' in df_b.columns, "BB%列存在")
bb_val = df_b['bb_pos'].iloc[-1]
assert_true(0 <= bb_val <= 1.5, f"BB%范围合理: {bb_val:.2f}")
print(f"  ✅ 布林带计算正常")

df_r = rsi(df)
rsi_val = df_r['rsi'].iloc[-1]
assert_true(0 <= rsi_val <= 100, f"RSI范围: {rsi_val:.1f}")
print(f"  ✅ RSI 计算正常")

df_v = volume_ratio(df)
vr = df_v['vol_ratio'].iloc[-1]
assert_true(vr > 0, f"量比>0: {vr:.2f}")
print(f"  ✅ 量比计算正常")

df_all = compute_all(df)
assert_true(all(c in df_all.columns for c in ['macd', 'bb_pos', 'rsi', 'vol_ratio']), "compute_all 全指标")
print(f"  ✅ 全指标一次性计算正常")


# ==================== 3. 账户测试 ====================
section("账户管理")

from bobquant.core.account import Account, get_sellable_shares

# 用临时文件测试
with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
    tmp_file = f.name

acc = Account(tmp_file, 500000).load()
assert_eq(acc.cash, 500000, "初始现金")
assert_eq(len(acc.positions), 0, "初始无持仓")

acc.set_position('sh.600519', {
    'shares': 100, 'avg_price': 1800, 'buy_price': 1800,
    'buy_date': '2026-03-24', 'buy_lots': [{'shares': 100, 'price': 1800, 'date': '2026-03-24'}],
    'add_level': 1, 'profit_taken': 0,
})
assert_true(acc.has_position('sh.600519'), "有持仓")
assert_eq(acc.get_position('sh.600519')['shares'], 100, "持仓股数")

acc.save()
acc2 = Account(tmp_file, 500000).load()
assert_true(acc2.has_position('sh.600519'), "持久化读取")
os.unlink(tmp_file)
print(f"  ✅ 账户管理测试通过")

# T+1 测试
today = datetime.now().strftime('%Y-%m-%d')
pos_old = {'shares': 1600, 'buy_lots': [
    {'shares': 1500, 'price': 37.82, 'date': '2026-03-24'},
    {'shares': 100, 'price': 39.76, 'date': today},
]}
assert_eq(get_sellable_shares(pos_old), 1500, "T+1: 昨天1500可卖")

pos_today = {'shares': 1000, 'buy_lots': [
    {'shares': 1000, 'price': 69.21, 'date': today},
]}
assert_eq(get_sellable_shares(pos_today), 0, "T+1: 今天全买不可卖")

pos_all_old = {'shares': 2000, 'buy_lots': [
    {'shares': 2000, 'price': 10, 'date': '2026-03-20'},
]}
assert_eq(get_sellable_shares(pos_all_old), 2000, "T+1: 旧仓全可卖")

# 兼容无 buy_lots 的旧数据
pos_legacy = {'shares': 500, 'buy_date': '2026-03-20'}
assert_eq(get_sellable_shares(pos_legacy), 500, "T+1: 旧格式兼容")
pos_legacy_today = {'shares': 500, 'buy_date': today}
assert_eq(get_sellable_shares(pos_legacy_today), 0, "T+1: 旧格式今天")
print(f"  ✅ T+1 可卖计算测试通过")

# 数据迁移测试
acc3 = Account(tmp_file, 100000).load()
acc3.set_position('test', {'shares': 100, 'avg_price': 10, 'buy_price': 10, 'buy_date': '2026-03-24'})
acc3.migrate_positions()
p = acc3.get_position('test')
assert_true('buy_lots' in p, "迁移: buy_lots")
assert_eq(p['add_level'], 1, "迁移: add_level")
assert_eq(p['profit_taken'], 0, "迁移: profit_taken")
try:
    os.unlink(tmp_file)
except:
    pass
print(f"  ✅ 数据迁移测试通过")


# ==================== 4. 执行器测试 ====================
section("交易执行器")

from bobquant.core.executor import Executor

with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
    tmp_acc = f.name
with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
    tmp_trade = f.name

acc = Account(tmp_acc, 1000000).load()
logs = []
exe = Executor(acc, 0.0005, tmp_trade, lambda msg: logs.append(msg), lambda t, m: None)

# 买入测试
t1 = exe.buy('sh.600519', '贵州茅台', 100, 1800, '测试买入')
assert_true(t1 is not None, "买入成功")
assert_eq(t1['shares'], 100, "买入股数")
assert_true(acc.cash < 1000000, "现金减少")
assert_true(acc.has_position('sh.600519'), "有持仓")

# 加仓测试
t2 = exe.buy('sh.600519', '贵州茅台', 100, 1750, '测试加仓', is_add=True)
assert_true(t2 is not None, "加仓成功")
pos = acc.get_position('sh.600519')
assert_eq(pos['shares'], 200, "加仓后200股")
assert_near(pos['avg_price'], 1775, 1, "均价1775")

# 把 buy_lots 日期改成昨天（否则 T+1 不可卖）
for lot in pos['buy_lots']:
    lot['date'] = '2026-03-24'

# 部分卖出
t3 = exe.sell('sh.600519', '贵州茅台', 100, 1800, '测试卖出')
assert_true(t3 is not None, "卖出成功")
assert_eq(acc.get_position('sh.600519')['shares'], 100, "剩余100股")
assert_true(t3['profit'] > 0, "有盈利")

# 资金不足
old_cash = acc.cash
t4 = exe.buy('sh.600519', '贵州茅台', 10000, 1800, '资金不足测试')
assert_true(t4 is None, "资金不足返回None")
assert_eq(acc.cash, old_cash, "现金不变")

# 同步交易记录
import tempfile as _tf
with _tf.NamedTemporaryFile(suffix='.json', delete=False) as _ftmp:
    _sync_file = _ftmp.name
    _ftmp.write(b'[]')
exe2 = Executor(acc, 0.0005, _sync_file, lambda msg: None, lambda t, m: None)
exe2.sync_trade_log([t1, t3])
with open(_sync_file) as f:
    saved = json.load(f)
assert_eq(len(saved), 2, "同步2条记录")
os.unlink(_sync_file)

os.unlink(tmp_acc)
os.unlink(tmp_trade)
print(f"  ✅ 执行器测试全部通过")


# ==================== 5. 策略测试 ====================
section("策略引擎")

from bobquant.strategy.engine import get_strategy, GridTStrategy, RiskManager

# MACD 策略
strat = get_strategy('macd')
assert_eq(strat.name, 'macd', "策略名")

# 布林带策略
strat2 = get_strategy('bollinger')
assert_eq(strat2.name, 'bollinger', "策略名")

# 未知策略
try:
    get_strategy('unknown')
    assert_true(False, "应该抛异常")
except ValueError:
    assert_true(True, "未知策略抛异常")
print(f"  ✅ 策略工厂测试通过")

# 风控测试
risk_cfg = {
    'stop_loss_pct': -0.08,
    'trailing_stop_activate': 0.05,
    'trailing_stop_drawdown': 0.02,
    'take_profit': [{'pct': 0.05, 'sell_ratio': 0.33}],
}
rm = RiskManager(risk_cfg)

# 止损触发
pos_loss = {'shares': 1000, 'avg_price': 100, 'profit_taken': 0,
            'buy_lots': [{'shares': 1000, 'date': '2026-03-20', 'price': 100}]}
r = rm.check('test', pos_loss, 91)  # 亏9%
assert_eq(r['action'], 'stop_loss', "止损触发")

# 正常持仓
r2 = rm.check('test2', pos_loss, 99)  # 亏1%
assert_true(r2['action'] is None, "正常不触发")

# 止盈触发
pos_profit = {'shares': 1000, 'avg_price': 100, 'profit_taken': 0,
              'buy_lots': [{'shares': 1000, 'date': '2026-03-20', 'price': 100}]}
r3 = rm.check('test3', pos_profit, 106)  # 盈6%
assert_eq(r3['action'], 'take_profit_L1', "止盈L1触发")
print(f"  ✅ 风控测试通过")

# 做T测试
grid_cfg = {
    't_grid_up': 0.02, 't_grid_step': 0.015, 't_grid_max': 3,
    't_buyback_dip': 0.01, 't_sell_ratio': 0.20,
}
gt = GridTStrategy(grid_cfg)
gt.reset_if_new_day()

# 日内涨2.5%，触发L1
quote = {'current': 10.25, 'open': 10.0}
shares, reason = gt.check_sell('test', quote, 1000)
assert_true(shares > 0, "做T L1 触发")
gt.record_sell('test', shares, 10.25)

# 价格回落触发接回
bb_shares, bb_reason = gt.check_buyback('test', 10.12)  # 回落>1%
assert_true(bb_shares > 0, "做T接回触发")
gt.record_buyback('test')

# 已接回不再触发
bb2, _ = gt.check_buyback('test', 10.0)
assert_eq(bb2, 0, "已接回不重复")
print(f"  ✅ 做T测试通过")


# ==================== 6. 券商接口测试 ====================
section("券商接口")

from bobquant.broker.base import get_broker, SimulatorBroker, EasytraderBroker

acc = Account(tmp_file, 100000).load()
broker = get_broker('simulator', account=acc)
assert_true(isinstance(broker, SimulatorBroker), "模拟券商")

# 买单
order = broker.buy('sh.600519', 1800, 100)
assert_true(order['success'], "模拟买入成功")
assert_true(order['order_id'].startswith('SIM-B'), "订单号格式")

# 卖单
order2 = broker.sell('sh.600519', 1850, 100)
assert_true(order2['success'], "模拟卖出成功")

# 实盘预留
try:
    eb = get_broker('easytrader', client_type='ths')
    eb.buy('sh.600519', 1800, 100)
    assert_true(False, "应该报未实现")
except (NotImplementedError, RuntimeError):
    assert_true(True, "实盘未实现")
print(f"  ✅ 券商接口测试通过")

try:
    os.unlink(tmp_file)
except:
    pass


# ==================== 汇总 ====================
print(f"\n{'='*50}")
print(f"📊 测试汇总: {_pass} 通过, {_fail} 失败")
print(f"{'='*50}")
if _fail == 0:
    print(f"🎉 全部测试通过！")
else:
    print(f"⚠️ 有 {_fail} 个测试失败，请检查")
    sys.exit(1)
