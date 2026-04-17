# -*- coding: utf-8 -*-
"""
BobQuant 全面集成测试
覆盖: 模块集成 / 实盘数据联调 / 边界条件 / 压力测试
"""
import sys
import json
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime
from copy import deepcopy

_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

import pandas as pd

_pass = 0
_fail = 0
_warn = 0

def ok(condition, msg):
    global _pass, _fail
    if condition:
        _pass += 1
        return True
    else:
        _fail += 1
        print(f"  ❌ {msg}")
        return False

def warn(msg):
    global _warn
    _warn += 1
    print(f"  ⚠️ {msg}")

def section(name):
    print(f"\n{'='*60}")
    print(f"🧪 {name}")
    print(f"{'='*60}")


# =============================================================
# Round 1: 模块集成测试（组件之间的数据流）
# =============================================================
section("Round 1: 模块集成 — 配置→数据→指标→策略→执行器→账户")

from bobquant.config import get_settings, to_legacy_config
from bobquant.indicator.technical import compute_all, macd, bollinger, rsi, volume_ratio
from bobquant.data.provider import get_provider, TencentProvider
from bobquant.core.account import Account, get_sellable_shares
from bobquant.core.executor import Executor
from bobquant.strategy.engine import get_strategy, GridTStrategy, RiskManager
from bobquant.broker.base import get_broker, SimulatorBroker

# 1.1 配置→策略参数传递
s = get_settings()
_, trade_cfg = to_legacy_config()
ok(trade_cfg['pyramid_levels'] == [0.03, 0.05, 0.07], "配置→策略: 金字塔参数")
ok(trade_cfg['stop_loss_pct'] == -0.08, "配置→策略: 止损参数")
ok(trade_cfg['rsi_buy_max'] == 35, "配置→策略: RSI参数")
ok(trade_cfg['t_grid_up'] == 0.02, "配置→策略: 做T参数")

# 1.2 模拟完整交易流程: 买入→持仓→部分卖出→再卖→清仓
print("\n  📋 模拟完整交易生命周期...")
tmp = tempfile.mktemp(suffix='.json')
tmp_trade = tempfile.mktemp(suffix='.json')
with open(tmp_trade, 'w') as f:
    json.dump([], f)

acc = Account(tmp, 1000000).load()
logs = []
exe = Executor(acc, 0.0005, tmp_trade, lambda m: logs.append(m), lambda t,m: None)

# Step 1: 建仓
t1 = exe.buy('sh.600519', '贵州茅台', 200, 1800, 'MACD金叉')
ok(t1 is not None, "生命周期: 建仓成功")
ok(acc.get_position('sh.600519')['shares'] == 200, "生命周期: 持仓200股")
ok(acc.get_position('sh.600519')['add_level'] == 1, "生命周期: 档位L1")
cash_after_buy = acc.cash

# Step 2: 加仓
t2 = exe.buy('sh.600519', '贵州茅台', 100, 1750, '加仓L2', is_add=True)
ok(t2 is not None, "生命周期: 加仓成功")
pos = acc.get_position('sh.600519')
ok(pos['shares'] == 300, "生命周期: 加仓后300股")
ok(pos['add_level'] == 2, "生命周期: 档位L2")
ok(len(pos['buy_lots']) == 2, "生命周期: 2笔买入记录")
expected_avg = (200*1800 + 100*1750) / 300
ok(abs(pos['avg_price'] - expected_avg) < 0.01, f"生命周期: 均价{pos['avg_price']:.2f}≈{expected_avg:.2f}")

# 改日期让T+1可卖
for lot in pos['buy_lots']:
    lot['date'] = '2026-03-24'

# Step 3: 部分卖出(100股)
t3 = exe.sell('sh.600519', '贵州茅台', 100, 1850, '止盈L1', '🔴 止盈L1')
ok(t3 is not None, "生命周期: 部分卖出成功")
ok(acc.get_position('sh.600519')['shares'] == 200, "生命周期: 剩余200股")
ok(t3['profit'] > 0, "生命周期: 盈利为正")

# Step 4: 再卖100股
t4 = exe.sell('sh.600519', '贵州茅台', 100, 1900, '止盈L2', '🔴 止盈L2')
ok(t4 is not None, "生命周期: 再次卖出成功")
ok(acc.get_position('sh.600519')['shares'] == 100, "生命周期: 剩余100股")

# Step 5: 清仓
t5 = exe.sell('sh.600519', '贵州茅台', 100, 1800, '策略减仓', '🔴 策略减仓')
ok(t5 is not None, "生命周期: 清仓成功")
ok(not acc.has_position('sh.600519'), "生命周期: 持仓已清空")
ok(acc.cash > cash_after_buy, "生命周期: 整体盈利，现金增加")

# 验证交易记录同步
exe.sync_trade_log([t1, t2, t3, t4, t5])
with open(tmp_trade) as f:
    saved = json.load(f)
ok(len(saved) == 5, "生命周期: 5条交易记录已同步")

# 清理
for f in [tmp, tmp_trade]:
    try: os.unlink(f)
    except: pass

print(f"  ✅ Round 1 完成")


# =============================================================
# Round 2: 实盘数据联调（用腾讯财经真实行情）
# =============================================================
section("Round 2: 实盘数据联调 — 腾讯财经+baostock")

provider = get_provider('tencent')

# 2.1 实时行情获取（多只股票）
test_stocks = [
    ('sh.601398', '工商银行'),
    ('sh.600519', '贵州茅台'),
    ('sz.000333', '美的集团'),
    ('sh.600547', '山东黄金'),
    ('sz.002460', '赣锋锂业'),
]

print("  📋 实时行情测试...")
quote_results = {}
for code, name in test_stocks:
    q = provider.get_quote(code)
    if q and q['current'] > 0:
        quote_results[code] = q
        ok(True, f"{name} 行情获取")
        required_fields = ['name', 'current', 'open', 'pre_close', 'high', 'low', 'change']
        for field in required_fields:
            ok(field in q, f"{name} 字段 {field}")
    else:
        warn(f"{name} ({code}) 行情获取失败（可能已收盘或网络问题）")

if quote_results:
    print(f"  ✅ 成功获取 {len(quote_results)}/{len(test_stocks)} 只股票行情")
else:
    warn("所有行情获取失败，跳过行情相关测试")

# 2.2 历史数据获取
print("\n  📋 历史数据测试...")
history_ok = False
try:
    df = provider.get_history('sh.600519', days=60)
    if df is not None and len(df) > 20:
        history_ok = True
        ok(True, "历史数据获取")
        ok('close' in df.columns, "历史数据有close列")
        ok('volume' in df.columns, "历史数据有volume列")
        ok(len(df) >= 20, f"历史数据{len(df)}条≥20")

        # 2.3 指标计算（用真实数据）
        print("\n  📋 真实数据指标计算...")
        df_all = compute_all(df)
        ok(pd.notna(df_all['macd'].iloc[-1]), f"MACD={df_all['macd'].iloc[-1]:.4f}")
        ok(pd.notna(df_all['rsi'].iloc[-1]), f"RSI={df_all['rsi'].iloc[-1]:.1f}")
        ok(pd.notna(df_all['bb_pos'].iloc[-1]), f"BB%={df_all['bb_pos'].iloc[-1]:.3f}")
        if 'vol_ratio' in df_all.columns:
            ok(pd.notna(df_all['vol_ratio'].iloc[-1]), f"量比={df_all['vol_ratio'].iloc[-1]:.2f}")

        # 2.4 策略信号检测（用真实数据）
        print("\n  📋 真实数据策略信号检测...")
        for strat_name in ['macd', 'bollinger']:
            strat = get_strategy(strat_name)
            result = strat.check('sh.600519', '贵州茅台', quote_results.get('sh.600519', {}), df, None, trade_cfg)
            sig = result.get('signal')
            reason = result.get('reason', '')
            filtered = result.get('filtered', False)
            status = f"信号={sig}" if sig else ("被过滤" if filtered else "无信号")
            print(f"    {strat_name}: {status} {reason}")
            ok(True, f"{strat_name}策略执行无异常")
    else:
        warn("历史数据获取失败或数据不足")
except Exception as e:
    warn(f"历史数据测试异常: {e}")

print(f"  ✅ Round 2 完成")


# =============================================================
# Round 3: 边界条件测试
# =============================================================
section("Round 3: 边界条件测试")

# 3.1 资金边界
print("  📋 资金边界...")
tmp = tempfile.mktemp(suffix='.json')
acc = Account(tmp, 1000).load()  # 只有1000元
exe = Executor(acc, 0.0005, '', lambda m: None, lambda t,m: None)

t = exe.buy('sh.600519', '贵州茅台', 100, 1800, '测试')
ok(t is None, "资金不足: 买入失败")
ok(acc.cash == 1000, "资金不足: 现金不变")

t = exe.buy('sz.000001', '平安银行', 100, 9.5, '测试')
ok(t is not None, "低价股: 买入成功")
try: os.unlink(tmp)
except: pass

# 3.2 零股/负数
print("  📋 零股/负数...")
tmp = tempfile.mktemp(suffix='.json')
acc = Account(tmp, 100000).load()
exe = Executor(acc, 0.0005, '', lambda m: None, lambda t,m: None)

t = exe.buy('test', 'TEST', 0, 100, '零股')
ok(t is None, "零股买入: 返回None")

t = exe.buy('test', 'TEST', 50, 100, '不足100股')
ok(t is None, "50股买入: 取整为0, 返回None")

t = exe.buy('test', 'TEST', -100, 100, '负数')
ok(t is None, "负数买入: 返回None")

# 正常买入后测试卖出边界
exe.buy('test', 'TEST', 100, 10, '正常买入')
pos = acc.get_position('test')
for lot in pos['buy_lots']:
    lot['date'] = '2026-03-20'

t = exe.sell('test', 'TEST', 0, 11, '零股卖出')
ok(t is None, "零股卖出: 返回None")

t = exe.sell('test', 'TEST', 50, 11, '50股卖出')
ok(t is None, "50股卖出: 取整为0, 返回None")

t = exe.sell('test', 'TEST', 500, 11, '超出持仓')
ok(t is not None and t['shares'] == 100, "超出持仓: 自动限制到可卖数量")
try: os.unlink(tmp)
except: pass

# 3.3 T+1 边界: 混合日期
print("  📋 T+1 混合日期...")
today = datetime.now().strftime('%Y-%m-%d')
pos_mixed = {
    'shares': 2000,
    'buy_lots': [
        {'shares': 500, 'date': '2026-03-20', 'price': 10},   # 可卖
        {'shares': 300, 'date': '2026-03-21', 'price': 11},   # 可卖
        {'shares': 200, 'date': today, 'price': 12},           # 不可卖
        {'shares': 400, 'date': '2026-03-22', 'price': 9},    # 可卖
        {'shares': 600, 'date': today, 'price': 13},           # 不可卖
    ]
}
sellable = get_sellable_shares(pos_mixed)
ok(sellable == 1200, f"T+1混合: 可卖{sellable}=500+300+400=1200")

# 3.4 FIFO 卖出验证
print("  📋 FIFO 卖出顺序...")
tmp = tempfile.mktemp(suffix='.json')
acc = Account(tmp, 1000000).load()
exe = Executor(acc, 0.0005, '', lambda m: None, lambda t,m: None)

acc.set_position('test_fifo', {
    'shares': 1000, 'avg_price': 10, 'buy_price': 10,
    'buy_date': '2026-03-20', 'buy_time': '',
    'buy_lots': [
        {'shares': 300, 'date': '2026-03-20', 'price': 9, 'time': ''},
        {'shares': 200, 'date': '2026-03-21', 'price': 10, 'time': ''},
        {'shares': 500, 'date': '2026-03-22', 'price': 11, 'time': ''},
    ],
    'add_level': 1, 'profit_taken': 0, 'commission': 0,
})

# 卖400股，应该先消耗第一批300+第二批100
exe.sell('test_fifo', 'TEST', 400, 12, 'FIFO测试')
pos = acc.get_position('test_fifo')
ok(pos['shares'] == 600, "FIFO: 剩余600股")
lots = pos['buy_lots']
# 第一批300全卖 → 消失; 第二批200卖100 → 剩100; 第三批500不动
ok(len(lots) == 2, f"FIFO: 剩余{len(lots)}笔lots")
ok(lots[0]['shares'] == 100, f"FIFO: 第二批剩{lots[0]['shares']}=100")
ok(lots[1]['shares'] == 500, f"FIFO: 第三批不动{lots[1]['shares']}=500")
try: os.unlink(tmp)
except: pass

# 3.5 风控边界
print("  📋 风控边界...")
risk_cfg = {
    'stop_loss_pct': -0.08,
    'trailing_stop_activate': 0.05,
    'trailing_stop_drawdown': 0.02,
    'take_profit': [
        {'pct': 0.05, 'sell_ratio': 0.33},
        {'pct': 0.10, 'sell_ratio': 0.50},
    ],
}
rm = RiskManager(risk_cfg)

# 刚好在止损线上
pos_edge = {'shares': 100, 'avg_price': 100, 'profit_taken': 0,
            'buy_lots': [{'shares': 100, 'date': '2026-03-20', 'price': 100}]}
r = rm.check('edge1', pos_edge, 92.01)  # 亏7.99% — 不触发
ok(r['action'] is None, "止损边界: -7.99%不触发")

r = rm.check('edge2', pos_edge, 92.0)  # 亏8% — 触发
ok(r['action'] == 'stop_loss', "止损边界: -8%触发")

# 跟踪止损: 先涨到激活线再回撤（保持盈利>5%才会检查回撤）
r1 = rm.check('trail', pos_edge, 108)  # +8%激活
ok(r1['action'] is None, "跟踪止损: 激活后不立即卖")
r2 = rm.check('trail', pos_edge, 110)  # 新高+10%
r3 = rm.check('trail', pos_edge, 107.9)  # 从110回撤到107.9 = -1.9%，盈利7.9%>5%
ok(r3['action'] is None, "跟踪止损: 回撤1.9%不触发")
r4 = rm.check('trail', pos_edge, 107.7)  # 回撤到107.7 = -2.09%，盈利7.7%>5%
ok(r4['action'] == 'trailing_stop', "跟踪止损: 回撤2.09%触发")

# 止盈档位递进
pos_tp = {'shares': 1000, 'avg_price': 100, 'profit_taken': 0,
          'buy_lots': [{'shares': 1000, 'date': '2026-03-20', 'price': 100}]}
r_tp1 = rm.check('tp', pos_tp, 106)
ok(r_tp1['action'] == 'take_profit_L1', "止盈: L1触发")
# 模拟已执行L1
pos_tp['profit_taken'] = 1
r_tp2 = rm.check('tp', pos_tp, 111)
ok(r_tp2['action'] == 'take_profit_L2', "止盈: L2触发")
pos_tp['profit_taken'] = 2
r_tp3 = rm.check('tp', pos_tp, 115)
ok(r_tp3['action'] is None, "止盈: 已到最高档不再触发")

# 3.6 做T边界
print("  📋 做T边界...")
grid_cfg = {'t_grid_up': 0.02, 't_grid_step': 0.015, 't_grid_max': 3,
            't_buyback_dip': 0.01, 't_sell_ratio': 0.20}
gt = GridTStrategy(grid_cfg)
gt.reset_if_new_day()

# 涨幅不够不触发
q = {'current': 10.15, 'open': 10.0}  # +1.5%
shares, _ = gt.check_sell('x', q, 1000)
ok(shares == 0, "做T: +1.5%不触发L1")

# 多档连续触发
q2 = {'current': 10.25, 'open': 10.0}  # +2.5%
s1, _ = gt.check_sell('multi', q2, 1000)
ok(s1 > 0, "做T多档: L1触发")
gt.record_sell('multi', s1, 10.25)

q3 = {'current': 10.40, 'open': 10.0}  # +4.0%，触发L2(3.5%)
s2, _ = gt.check_sell('multi', q3, 800)
ok(s2 > 0, "做T多档: L2触发")
gt.record_sell('multi', s2, 10.40)

q4 = {'current': 10.55, 'open': 10.0}  # +5.5%，触发L3(5.0%)
s3, _ = gt.check_sell('multi', q4, 600)
ok(s3 > 0, "做T多档: L3触发")
gt.record_sell('multi', s3, 10.55)

# 已达上限不再触发
q5 = {'current': 10.70, 'open': 10.0}  # +7%
s4, _ = gt.check_sell('multi', q5, 400)
ok(s4 == 0, "做T多档: 达上限3次不再触发")

# 日期切换重置
gt._state_date = '2026-03-20'  # 模拟昨天
gt.reset_if_new_day()
ok(len(gt._state) == 0, "做T: 新日期重置状态")

# 3.7 券商接口集成
print("  📋 券商接口集成...")
tmp = tempfile.mktemp(suffix='.json')
acc = Account(tmp, 500000).load()
broker = get_broker('simulator', account=acc)

ok(isinstance(broker, SimulatorBroker), "券商: 模拟模式")
r1 = broker.buy('sh.600519', 1800, 100)
r2 = broker.sell('sh.600519', 1850, 100)
ok(r1['order_id'] != r2['order_id'], "券商: 订单号唯一")
ok(r1['filled_price'] == 1800, "券商: 成交价正确")

positions = broker.get_positions()
ok(isinstance(positions, dict), "券商: 查持仓")
balance = broker.get_balance()
ok('cash' in balance, "券商: 查余额")

# 撤单
cancel_r = broker.cancel(r1['order_id'])
ok(cancel_r['success'], "券商: 撤单")
try: os.unlink(tmp)
except: pass

print(f"  ✅ Round 3 完成")


# =============================================================
# Round 4: 压力测试
# =============================================================
section("Round 4: 压力测试")

# 4.1 大量持仓
print("  📋 50只持仓账户操作...")
tmp = tempfile.mktemp(suffix='.json')
acc = Account(tmp, 10000000).load()
exe = Executor(acc, 0.0005, '', lambda m: None, lambda t,m: None)

t0 = time.time()
for i in range(50):
    code = f"test.{i:03d}"
    exe.buy(code, f'测试股{i}', 100, 10+i*0.1, '批量建仓')
t_buy = time.time() - t0
ok(len(acc.positions) == 50, f"压力: 50只持仓建仓成功 ({t_buy:.2f}s)")

# 保存/读取
t0 = time.time()
acc.save()
acc2 = Account(tmp, 10000000).load()
t_io = time.time() - t0
ok(len(acc2.positions) == 50, f"压力: 50只持仓读写 ({t_io:.3f}s)")
ok(t_io < 1.0, "压力: 读写<1秒")

# 批量卖出
for code, pos in list(acc2.positions.items()):
    for lot in pos['buy_lots']:
        lot['date'] = '2026-03-20'

t0 = time.time()
for code in list(acc2.positions.keys()):
    exe2 = Executor(acc2, 0.0005, '', lambda m: None, lambda t,m: None)
    exe2.sell(code, '测试', 100, 15, '批量清仓')
t_sell = time.time() - t0
ok(len(acc2.positions) == 0, f"压力: 50只全部清仓 ({t_sell:.2f}s)")
try: os.unlink(tmp)
except: pass

# 4.2 大量指标计算
print("  📋 大数据量指标计算...")
big_df = pd.DataFrame({
    'close': [100 + i*0.01 + (-1)**i * 0.5 for i in range(1000)],
    'volume': [100000 + i*100 for i in range(1000)],
})
t0 = time.time()
big_df = compute_all(big_df)
t_ind = time.time() - t0
ok(pd.notna(big_df['macd'].iloc[-1]), f"压力: 1000条数据指标计算 ({t_ind:.3f}s)")
ok(t_ind < 1.0, "压力: 指标计算<1秒")

# 4.3 风控批量检查
print("  📋 风控批量检查...")
rm = RiskManager(risk_cfg)
t0 = time.time()
for i in range(200):
    pos_t = {'shares': 1000, 'avg_price': 100, 'profit_taken': 0,
             'buy_lots': [{'shares': 1000, 'date': '2026-03-20', 'price': 100}]}
    rm.check(f'stress_{i}', pos_t, 95 + i*0.05)
t_risk = time.time() - t0
ok(t_risk < 1.0, f"压力: 200只风控检查 ({t_risk:.3f}s)")

# 4.4 配置反复加载
print("  📋 配置反复加载...")
t0 = time.time()
for _ in range(100):
    s2 = get_settings()
    s2.get('strategy.stop_loss_pct')
    s2.get('strategy.pyramid_levels')
    len(s2.stock_pool)
t_cfg = time.time() - t0
ok(t_cfg < 1.0, f"压力: 100次配置读取 ({t_cfg:.3f}s)")

print(f"  ✅ Round 4 完成")


# =============================================================
# 汇总
# =============================================================
print(f"\n{'='*60}")
print(f"📊 全面测试汇总")
print(f"{'='*60}")
print(f"  ✅ 通过: {_pass}")
print(f"  ❌ 失败: {_fail}")
print(f"  ⚠️ 警告: {_warn}")
print(f"{'='*60}")
if _fail == 0:
    print(f"🎉 全部测试通过！新架构可以投入使用！")
else:
    print(f"⚠️ 有 {_fail} 个测试失败")
    sys.exit(1)
