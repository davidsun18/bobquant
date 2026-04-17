# -*- coding: utf-8 -*-
"""
BobQuant 交易引擎主入口
三阶段: 做T → 风控 → 策略信号
"""
import time
from datetime import datetime

from .config import get_settings, to_legacy_config, LOG_FILE
from .core.account import Account, get_sellable_shares
from .core.executor import Executor
from .data.provider import get_provider
from .strategy.engine import get_strategy, GridTStrategy, RiskManager
from .notify.feishu import send_feishu


# ==================== 日志 ====================
def _log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with open(str(LOG_FILE), 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _notify(title, message):
    uid = get_settings().get('notify.feishu.user_id', '')
    send_feishu(title, message, uid)


def run_check():
    """执行一次三阶段信号检查"""
    s = get_settings()
    _, trade_cfg = to_legacy_config()

    # 初始化组件
    data = get_provider(s.get('data.primary', 'tencent'))
    account = Account(s.positions_file, s.initial_capital).load()
    account.migrate_positions()
    executor = Executor(account, s.commission_rate, s.trade_log_file, _log, _notify)
    grid_t = GridTStrategy(trade_cfg)
    risk = RiskManager(trade_cfg)
    grid_t.reset_if_new_day()

    _log("📊 检查交易信号（三阶段）...")
    trades = []

    # ============ Phase 1: 网格做T ============
    _log("  📌 Phase 1: 网格做T...")
    for code, pos in list(account.positions.items()):
        name = _find_name(s, code)
        sellable = get_sellable_shares(pos)
        quote = data.get_quote(code) if sellable > 0 else None
        if not quote or quote['current'] <= 0:
            continue

        # 高抛
        sell_n, sell_reason = grid_t.check_sell(code, quote, sellable)
        if sell_n > 0:
            t = executor.sell(code, name, sell_n, quote['current'], sell_reason, '🔄 做T卖出')
            if t:
                trades.append(t)
                grid_t.record_sell(code, sell_n, quote['current'])
                sellable = get_sellable_shares(account.get_position(code) or pos)

        # 接回
        bb_n, bb_reason = grid_t.check_buyback(code, quote['current'])
        if bb_n > 0:
            t = executor.buy(code, name, bb_n, quote['current'], bb_reason, is_add=True)
            if t:
                t['action'] = '🔄 做T接回'
                trades.append(t)
                grid_t.record_buyback(code)

    # ============ Phase 2: 风控 ============
    _log("  📌 Phase 2: 风控...")
    for code, pos in list(account.positions.items()):
        name = _find_name(s, code)
        quote = data.get_quote(code)
        if not quote or quote['current'] <= 0:
            continue

        result = risk.check(code, pos, quote['current'])
        if result['action']:
            t = executor.sell(code, name, result['shares'], quote['current'], result['reason'], result['label'])
            if t:
                trades.append(t)
                if 'take_profit' in result['action'] and account.has_position(code):
                    p = account.get_position(code)
                    p['profit_taken'] = p.get('profit_taken', 0) + 1
                if result['action'] in ('stop_loss', 'trailing_stop'):
                    risk.clear_trailing(code)

    # ============ Phase 3: 策略信号 ============
    _log("  📌 Phase 3: 策略信号...")
    for stock in s.stock_pool:
        code, name, strat_name = stock['code'], stock['name'], stock['strategy']
        quote = data.get_quote(code)
        if not quote or quote['current'] <= 0:
            continue

        df = data.get_history(code, s.get('data.history_days', 60))
        strategy = get_strategy(strat_name)
        result = strategy.check(code, name, quote, df, account.get_position(code), trade_cfg)

        if result.get('filtered'):
            _log(f"  ⚪ {name}: {result.get('reason', '信号被过滤')}")
            continue

        sig = result.get('signal')

        if sig == 'buy':
            strength = result.get('strength', 'normal')
            pyramid = trade_cfg.get('pyramid_levels', [0.03, 0.05, 0.07])

            if not account.has_position(code):
                pct = pyramid[1] if strength == 'strong' else pyramid[0]
                shares = int(s.initial_capital * pct / quote['current'] / 100) * 100
                if shares < 100:
                    shares = 100
                t = executor.buy(code, name, shares, quote['current'], result['reason'])
                if t:
                    trades.append(t)
            else:
                pos = account.get_position(code)
                level = pos.get('add_level', 1)
                dip = (quote['current'] - pos['avg_price']) / pos['avg_price']
                if dip <= -trade_cfg.get('add_dip_pct', 0.03) and level < len(pyramid):
                    add_pct = pyramid[level] - pyramid[level - 1]
                    add_shares = int(s.initial_capital * add_pct / quote['current'] / 100) * 100
                    if add_shares >= 100:
                        t = executor.buy(code, name, add_shares, quote['current'],
                                          f'{result["reason"]} + 加仓L{level+1} (跌{dip*100:.1f}%)', is_add=True)
                        if t:
                            trades.append(t)
                else:
                    _log(f"  ⚪ {name}: 已持仓L{level}，等待加仓条件")

        elif sig == 'sell':
            if not account.has_position(code):
                continue
            pos = account.get_position(code)
            sellable = get_sellable_shares(pos)
            if sellable <= 0:
                _log(f"  ⚪ {name}: T+1 限制")
                continue
            sell_pct = 0.7 if result.get('strength') == 'strong' else 0.5
            label = '🔴 强势减仓' if result.get('strength') == 'strong' else '🔴 策略减仓'
            sell_n = int(sellable * sell_pct / 100) * 100
            if sell_n < 100:
                sell_n = min(100, int(sellable / 100) * 100)
            if sell_n >= 100:
                t = executor.sell(code, name, sell_n, quote['current'], f'策略减仓 ({result["reason"]})', label)
                if t:
                    trades.append(t)

    # ============ 保存 ============
    if trades:
        account.save()
        executor.sync_trade_log(trades)
        _log(f"  ✅ 执行 {len(trades)} 笔交易")
    else:
        _log(f"  ⚪ 无交易信号")

    return trades


def portfolio_summary():
    """打印账户汇总"""
    s = get_settings()
    data = get_provider(s.get('data.primary', 'tencent'))
    account = Account(s.positions_file, s.initial_capital).load()

    mv = 0
    for code, pos in account.positions.items():
        q = data.get_quote(code)
        if q:
            mv += pos['shares'] * q['current']

    total = account.cash + mv
    pnl = total - s.initial_capital
    pnl_pct = pnl / s.initial_capital * 100

    _log(f"💰 账户汇总: 现金¥{account.cash:,.0f} + 持仓¥{mv:,.0f} = ¥{total:,.0f} ({pnl_pct:+.2f}%)")


def main_loop():
    """交易主循环"""
    s = get_settings()

    _log("=" * 60)
    _log(f"🎯 BobQuant v{__import__('bobquant').__version__} 启动")
    _log(f"   资金: ¥{s.initial_capital:,} | 股票池: {len(s.stock_pool)}只 | 间隔: {s.check_interval}s")
    _log("=" * 60)

    portfolio_summary()
    last_check = None

    while True:
        try:
            now = datetime.now()
            if now.weekday() >= 5:
                _log("💤 周末"); break

            h, m = now.hour, now.minute
            if h < 9 or (h == 9 and m < 30):
                time.sleep(300); continue
            elif 11 <= h < 13:
                time.sleep(300); continue
            elif h >= 15:
                _log("💤 收盘"); break

            cm = now.strftime('%H:%M')
            if cm != last_check:
                run_check()
                portfolio_summary()
                last_check = cm

            time.sleep(s.check_interval)

        except KeyboardInterrupt:
            _log("⚠️ 用户中断"); break
        except Exception as e:
            _log(f"❌ 错误: {e}")
            time.sleep(10)

    _log("=" * 60)
    _log("📊 BobQuant 结束")
    _log("=" * 60)


def _find_name(settings, code):
    for s in settings.stock_pool:
        if s['code'] == code:
            return s['name']
    return code
