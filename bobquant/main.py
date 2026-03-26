# -*- coding: utf-8 -*-
"""
BobQuant 交易引擎主入口 v1.0
三阶段：做 T → 风控 → 策略信号 (集成 ML+ 情绪)
"""
import time
from datetime import datetime

try:
    from .config import get_settings, to_legacy_config, LOG_FILE
    from .core.account import Account, get_sellable_shares
    from .core.executor import Executor
    from .data.provider import get_provider
    from .strategy.engine import get_strategy, GridTStrategy, RiskManager, DecisionEngine
    from .notify.feishu import send_feishu
except ImportError:
    from config import get_settings, to_legacy_config, LOG_FILE
    from core.account import Account, get_sellable_shares
    from core.executor import Executor
    from data.provider import get_provider
    from strategy.engine import get_strategy, GridTStrategy, RiskManager, DecisionEngine
    from notify.feishu import send_feishu


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
    """执行一次三阶段信号检查（v1.0 集成 ML+ 情绪）"""
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
    
    # v1.0 NEW: 初始化综合决策引擎
    enable_ml = s.get('ml.enabled', True)
    enable_sentiment = s.get('sentiment.enabled', True)
    decision_engine = None
    if enable_ml or enable_sentiment:
        config = {
            'enable_ml': enable_ml,
            'enable_sentiment': enable_sentiment,
            'ml_signal_weight': s.get('ml.signal_weight', 0.4),
            'ta_signal_weight': s.get('sentiment.signal_weight', 0.4),
            'ml_lookback_days': s.get('ml.lookback_days', 200),
            'ml_min_train_samples': s.get('ml.min_train_samples', 60),
            'ml_probability_threshold': s.get('ml.probability_threshold', 0.6),
            'ml_model_dir': s.get('ml.model_dir', 'ml/models'),
            'base_position_pct': s.get('sentiment.position.base', 60),
            'sentiment_high_threshold': s.get('sentiment.high_threshold', 70),
            'sentiment_low_threshold': s.get('sentiment.low_threshold', 30)
        }
        decision_engine = DecisionEngine(config)
        _log(f"🧠 综合决策引擎就绪 (ML={enable_ml}, 情绪={enable_sentiment})")

    _log("📊 检查交易信号（三阶段 + v1.0 智能增强）...")
    trades = []

    # ============ Phase 1: 网格做 T ============
    _log("  📌 Phase 1: 网格做 T...")
    for code, pos in list(account.positions.items()):
        name = _find_name(s, code)
        sellable = get_sellable_shares(pos)
        quote = data.get_quote(code) if sellable > 0 else None
        if not quote or quote['current'] <= 0:
            continue

        # 高抛
        sell_n, sell_reason = grid_t.check_sell(code, quote, sellable)
        if sell_n > 0:
            t = executor.sell(code, name, sell_n, quote['current'], sell_reason, '🔄 做 T 卖出')
            if t:
                trades.append(t)
                grid_t.record_sell(code, sell_n, quote['current'])
                sellable = get_sellable_shares(account.get_position(code) or pos)

        # 接回
        bb_n, bb_reason = grid_t.check_buyback(code, quote['current'])
        if bb_n > 0:
            t = executor.buy(code, name, bb_n, quote['current'], bb_reason, is_add=True)
            if t:
                t['action'] = '🔄 做 T 接回'
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

    # ============ Phase 3: 策略信号 (v1.0 增强) ============
    _log("  📌 Phase 3: 策略信号 (v1.0 智能增强)...")
    for stock in s.stock_pool:
        code, name, strat_name = stock['code'], stock['name'], stock['strategy']
        quote = data.get_quote(code)
        if not quote or quote['current'] <= 0:
            continue

        # 获取历史数据（v1.0: 使用 ML 配置的天数）
        history_days = s.get('ml.lookback_days', 200) if enable_ml else s.get('data.history_days', 60)
        df = data.get_history(code, history_days)
        
        # 获取传统技术指标信号
        ta_signals = []
        strategy = get_strategy(strat_name)
        ta_result = strategy.check(code, name, quote, df, account.get_position(code), trade_cfg)
        if ta_result.get('signal'):
            ta_signals.append(ta_result)
        
        # v1.0: 使用综合决策引擎
        if decision_engine:
            decision = decision_engine.combine_signals(
                code, name, quote, df, 
                account.get_position(code), 
                ta_signals
            )
            
            # 检查是否被情绪过滤
            if decision.get('filtered'):
                _log(f"  ⚪ {name}: {decision.get('reason', '信号被过滤')} [情绪过滤]")
                continue
            
            result = decision
        else:
            result = ta_result if ta_signals else {'signal': None}

        # 执行交易
        sig = result.get('signal')

        if sig == 'buy':
            strength = result.get('strength', 'normal')
            pyramid = trade_cfg.get('pyramid_levels', [0.03, 0.05, 0.07])
            
            # v1.0: 根据情绪调整仓位
            position_adjustment = result.get('position_adjustment', {})
            position_limit = position_adjustment.get('position_limit', s.get('sentiment.position.max', 90))
            
            if not account.has_position(code):
                # 检查仓位上限
                total_position_pct = sum(p.get('position_pct', 0) for p in account.positions.values())
                if total_position_pct >= position_limit:
                    _log(f"  ⚪ {name}: 已达仓位上限 ({position_limit}%)")
                    continue
                
                # v1.0 修复：检查今天是否已经买过这只股票（避免重复交易）
                today = datetime.now().strftime('%Y-%m-%d')
                bought_today = False
                for trade in trades:
                    if trade.get('code') == code and trade.get('action') == '买入' and trade.get('time', '').startswith(today):
                        bought_today = True
                        break
                
                if bought_today:
                    _log(f"  ⚪ {name}: 今日已买入，跳过")
                    continue
                
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
                
                # v1.0 修复：检查今天是否已经加仓过（避免重复）
                today = datetime.now().strftime('%Y-%m-%d')
                added_today = False
                for trade in trades:
                    if trade.get('code') == code and trade.get('action') == '买入' and trade.get('time', '').startswith(today):
                        added_today = True
                        break
                
                if added_today:
                    _log(f"  ⚪ {name}: 今日已加仓，跳过")
                elif dip <= -trade_cfg.get('add_dip_pct', 0.03) and level < len(pyramid):
                    add_pct = pyramid[level] - pyramid[level - 1]
                    add_shares = int(s.initial_capital * add_pct / quote['current'] / 100) * 100
                    if add_shares >= 100:
                        t = executor.buy(code, name, add_shares, quote['current'],
                                          f'{result["reason"]} + 加仓 L{level+1} (跌{dip*100:.1f}%)', is_add=True)
                        if t:
                            trades.append(t)
                else:
                    _log(f"  ⚪ {name}: 已持仓 L{level}，等待加仓条件")

        elif sig == 'sell':
            if not account.has_position(code):
                continue
            pos = account.get_position(code)
            sellable = get_sellable_shares(pos)
            if sellable <= 0:
                _log(f"  ⚪ {name}: T+1 限制")
                continue
            
            # v1.0: 根据信号强度调整卖出比例
            confidence = result.get('confidence', 0.5)
            sell_pct = 0.7 if (result.get('strength') == 'strong' or confidence > 0.8) else 0.5
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
        if q and q['current'] > 0:
            mv += pos['shares'] * q['current']

    cash = account.cash
    total = mv + cash
    pnl = total - s.initial_capital
    pnl_pct = pnl / s.initial_capital * 100

    _log("\n" + "=" * 60)
    _log("📊 账户汇总")
    _log("=" * 60)
    _log(f"总资产：¥{total:,.0f} (现金¥{cash:,.0f} + 持仓¥{mv:,.0f})")
    _log(f"盈亏：¥{pnl:+,.0f} ({pnl_pct:+.2f}%)")
    _log(f"持仓：{len(account.positions)} 只")
    _log("=" * 60)

    return {'total': total, 'cash': cash, 'market_value': mv, 'pnl': pnl, 'pnl_pct': pnl_pct}


# ==================== 辅助函数 ====================
def _find_name(s, code):
    for stock in s.stock_pool:
        if stock['code'] == code:
            return stock['name']
    return ''


# ==================== 主循环 ====================
def main_loop():
    """主循环"""
    _log("🚀 BobQuant v1.0 启动")
    _log("📍 模拟盘模式")
    
    s = get_settings()
    
    # v1.0: 发送启动通知
    enable_ml = s.get('ml.enabled', True)
    enable_sentiment = s.get('sentiment.enabled', True)
    _notify(
        "⚡ BobQuant v1.0 启动",
        f"模拟盘已启动\n"
        f"ML 预测：{'✅' if enable_ml else '❌'}\n"
        f"情绪指数：{'✅' if enable_sentiment else '❌'}\n"
        f"股票池：{len(s.stock_pool)} 只"
    )
    
    while True:
        # 检查交易时段
        if s.is_trading_hours():
            try:
                run_check()
                portfolio_summary()
            except Exception as e:
                _log(f"❌ 错误：{e}")
                _notify("⚠️ BobQuant 错误", f"交易检查出错：{e}")
        else:
            _log("⏸️ 非交易时段，等待...")
        
        time.sleep(s.check_interval)


if __name__ == '__main__':
    main_loop()
