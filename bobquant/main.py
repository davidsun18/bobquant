# -*- coding: utf-8 -*-
"""
BobQuant 交易引擎主入口 v2.4
三阶段：高频交易 → 做 T → 风控 → 策略信号 (集成 ML+ 情绪)

v2.4 新增:
- 高频激进策略模式
- 剥头皮/动量/突破/均值回归
- 3 秒行情检查间隔
- 0.15% 触发做 T
- 5 分钟最长持仓

v2.2 新增:
- TA-Lib 高性能指标计算
- quantstats 专业绩效分析
- 三重障碍法标签生成
- 新风控管理器
"""
import time
from datetime import datetime

try:
    from .config import get_settings, to_legacy_config, LOG_FILE
    from .core.account import Account, get_sellable_shares
    from .core.executor import Executor
    from .core.trading_rules import get_min_shares, normalize_shares
    from .data.provider import get_provider
    from .strategy.engine import get_strategy, GridTStrategy, RiskManager, DecisionEngine
    from .strategy.high_frequency import HighFrequencyEngine, create_high_frequency_strategy
    from .notify.feishu import send_feishu
    from .analysis.performance import generate_report, format_report
except ImportError:
    from config import get_settings, to_legacy_config, LOG_FILE
    from core.account import Account, get_sellable_shares
    from core.executor import Executor
    from core.trading_rules import get_min_shares, normalize_shares
    from data.provider import get_provider
    from strategy.engine import get_strategy, GridTStrategy, RiskManager, DecisionEngine
    from strategy.high_frequency import HighFrequencyEngine, create_high_frequency_strategy
    from notify.feishu import send_feishu
    from analysis.performance import generate_report, format_report


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
    
    # TWAP 配置
    twap_enabled = s.get('twap.enabled', False)
    twap_threshold = s.get('twap.threshold', 10000)
    twap_slices = s.get('twap.slices', 5)
    twap_duration = s.get('twap.duration_minutes', 10)
    
    executor = Executor(
        account, 
        s.commission_rate, 
        s.trade_log_file, 
        _log, 
        _notify,
        twap_enabled=twap_enabled,
        twap_threshold=twap_threshold,
        twap_slices=twap_slices,
        twap_duration=twap_duration
    )
    
    if twap_enabled:
        _log(f"  ✅ TWAP 执行器已启用 (阈值：{twap_threshold}股，拆分：{twap_slices}份，时长：{twap_duration}分钟)")
    grid_t = GridTStrategy(trade_cfg)
    risk = RiskManager(trade_cfg)
    grid_t.reset_if_new_day()
    
    # v2.4 NEW: 初始化高频交易引擎
    enable_high_freq = s.get('high_frequency.enabled', False)
    hf_engine = None
    if enable_high_freq:
        hf_config = {
            'scalping_threshold': s.get('strategy.day_trading.scalping_threshold', 0.001),
            'max_holding_time': s.get('strategy.day_trading.max_holding_time', 300),
            'min_profit_tick': s.get('strategy.day_trading.min_profit_tick', 1),
            'momentum_threshold': s.get('strategy.signal.enable_momentum', True),
            'reversion_threshold': s.get('strategy.signal.reversion_threshold', 0.002),
            'breakout_window': s.get('strategy.signal.breakout_window', 5)
        }
        hf_engine = HighFrequencyEngine(hf_config)
        _log(f"⚡ 高频交易引擎就绪 (剥头皮/动量/突破/均值回归)")
    
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

    _log("📊 检查交易信号（高频优先 + 三阶段 + v1.0 智能增强）...")
    trades = []

    # ============ Phase 1: 网格做 T ============
    _log("  📌 Phase 1: 网格做 T...")
    
    # v1.1 优化：并行获取所有持仓股的实时价格
    codes = list(account.positions.keys())
    quotes = data.get_quotes(codes)  # 并行刷新，26 只股票从 2.5 秒降至 0.3 秒
    
    # v1.1.2 修复：先检查哪些股票触发了止盈/止损，避免做 T 冲突
    risk_checked = set()
    for code, pos in list(account.positions.items()):
        quote = quotes.get(code)
        if quote and quote['current'] > 0:
            result = risk.check(code, pos, quote['current'])
            if result['action']:
                risk_checked.add(code)  # 标记为风控优先
    
    # v2.2.19 修复：做 T 接回逻辑独立于持仓 (即使清仓也要接回)
    # 1. 先处理有持仓的股票的做 T
    for code, pos in list(account.positions.items()):
        name = _find_name(s, code)
        sellable = get_sellable_shares(pos)
        quote = quotes.get(code) if sellable > 0 else None
        if not quote or quote['current'] <= 0:
            continue
        
        # v1.1.2 修复：如果已触发风控，跳过做 T 避免冲突
        if code in risk_checked:
            continue
        
        # 获取历史数据 (用于趋势判断)
        df = data.get_history(code, days=30)

        # 高抛 (v2.2.18: 传入 df 用于趋势判断)
        sell_n, sell_reason = grid_t.check_sell(code, quote, sellable, df)
        if sell_n > 0:
            t = executor.sell(code, name, sell_n, quote['current'], sell_reason, '🔄 做 T 卖出')
            if t:
                trades.append(t)
                grid_t.record_sell(code, sell_n, quote['current'])
                sellable = get_sellable_shares(account.get_position(code) or pos)

        # 接回 (v2.2.19: 即使清仓也要检查接回)
        bb_n, bb_reason = grid_t.check_buyback(code, quote['current'])
        if bb_n > 0:
            t = executor.buy(code, name, bb_n, quote['current'], bb_reason, is_add=True)
            if t:
                t['action'] = '🔄 做 T 接回'
                trades.append(t)
                grid_t.record_buyback(code)
    
    # v2.2.19 新增：检查已清仓但做 T 未接回的股票 (兜底接回)
    t_state = grid_t._state
    for code, info in list(t_state.items()):
        if info.get('total_sold', 0) > 0 and not info.get('bought_back', False):
            # 有做 T 卖出但未接回，检查是否需要接回
            quote = quotes.get(code)
            if quote and quote['current'] > 0:
                bb_n, bb_reason = grid_t.check_buyback(code, quote['current'])
                if bb_n > 0:
                    name = _find_name(s, code)
                    t = executor.buy(code, name, bb_n, quote['current'], bb_reason, is_add=True)
                    if t:
                        t['action'] = '🔄 做 T 接回 (兜底)'
                        trades.append(t)
                        grid_t.record_buyback(code)
                        _log(f"  ✅ 兜底接回 {name}: {bb_n}股 @ ¥{quote['current']:.2f}")

    # ============ Phase 2: 风控 ============
    _log("  📌 Phase 2: 风控...")
    for code, pos in list(account.positions.items()):
        name = _find_name(s, code)
        quote = quotes.get(code)  # 使用并行获取的价格
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

    # ============ Phase 2.5: 情绪指数主动仓位管理 ============
    # v1.0 新增：如果仓位超限，主动减仓
    if decision_engine and decision_engine.sentiment_controller:
        # 计算当前仓位 (使用并行获取的价格)
        market_value = 0
        for code, pos in account.positions.items():
            q = quotes.get(code)
            if q and q['current'] > 0:
                market_value += pos['shares'] * q['current']
        total_assets = account.cash + market_value
        current_position_pct = (market_value / total_assets * 100) if total_assets > 0 else 0
        
        # 检查是否需要主动减仓
        should_reduce, target_pct, reason = decision_engine.sentiment_controller.should_reduce_position(current_position_pct)
        if should_reduce:
            _log(f"  ⚠️ 主动仓位管理：{reason}")
            _log(f"     当前仓位：{current_position_pct:.1f}% → 目标：{target_pct}%")
            
            # 选择减仓标的：优先减仓盈利少/亏损的
            positions_to_reduce = []
            _log(f"     扫描 {len(account.positions)} 只持仓...")
            
            for code, pos in account.positions.items():
                q = quotes.get(code)  # 使用并行获取的价格
                if not q or q['current'] <= 0:
                    continue
                
                current_price = q['current']
                avg_price = pos['avg_price']
                pnl_pct = (current_price - avg_price) / avg_price * 100
                
                # T+1 检查：计算可卖股数
                today = datetime.now().strftime('%Y-%m-%d')
                today_bought = sum(lot['shares'] for lot in pos.get('buy_lots', []) if lot.get('date', '') == today)
                sellable = pos['shares'] - today_bought
                
                if sellable <= 0:
                    continue  # 今日买入，不可卖
                
                mv = current_price * pos['shares']
                positions_to_reduce.append((code, pos, pnl_pct, mv, current_price, sellable))
            
            _log(f"     可减仓：{len(positions_to_reduce)} 只")
            
            # 按盈亏排序，优先减仓亏损的
            positions_to_reduce.sort(key=lambda x: x[2])  # 按盈亏率排序
            
            # 计算需要减多少
            reduce_amount = (current_position_pct - target_pct) / 100 * total_assets
            _log(f"     需减仓：¥{reduce_amount:,.0f}")
            
            reduced_value = 0
            reduced_count = 0
            
            for code, pos, pnl_pct, mv, current_price, sellable in positions_to_reduce:
                if reduced_value >= reduce_amount:
                    break
                if reduced_count >= 5:  # 最多减 5 只
                    break
                
                # 减仓 30% 或全部可卖（取较小值）
                raw_shares = int(pos['shares'] * 0.3)
                sell_shares = normalize_shares(code, min(raw_shares, sellable), 'sell')
                
                if sell_shares < get_min_shares(code):
                    # 低于最小数量，如果是零股则全部卖出，否则跳过
                    if sellable < get_min_shares(code):
                        sell_shares = sellable
                    else:
                        continue
                
                sell_value = sell_shares * current_price
                
                # 执行卖出
                t = executor.sell(code, name, sell_shares, current_price, f'主动减仓 ({pnl_pct:+.1f}%)', '🟢 情绪减仓')
                if t:
                    trades.append(t)
                    reduced_value += sell_value
                    reduced_count += 1
                    _log(f"     减仓 {code}: {sell_shares}股 @ ¥{current_price:.2f} (盈亏{pnl_pct:+.1f}%, 可卖{sellable}股)")
            
            if reduced_count > 0:
                _log(f"     ✅ 合计减仓：¥{reduced_value:,.0f} ({reduced_count}只)")
            else:
                _log(f"     ⚠️ 未能减仓（可能都是今日买入或 T+1 限制）")
    
    # ============ Phase 3: 策略信号 (v1.0 增强) ============
    _log("  📌 Phase 3: 策略信号 (v1.0 智能增强)...")
    for stock in s.stock_pool:
        code, name, strat_name = stock['code'], stock['name'], stock['strategy']
        quote = quotes.get(code)  # 使用并行获取的价格
        if not quote or quote['current'] <= 0:
            continue

        # 获取历史数据（v1.0: 使用 ML 配置的天数）
        history_days = s.get('ml.lookback_days', 200) if enable_ml else s.get('data.history_days', 60)
        df = data.get_history(code, history_days)
        
        # 获取传统技术指标信号
        ta_signals = []
        try:
            strategy = get_strategy(strat_name)
            ta_result = strategy.check(code, name, quote, df, account.get_position(code), trade_cfg)
            if ta_result.get('signal'):
                ta_signals.append(ta_result)
        except Exception as e:
            _log(f"  ❌ 错误：{e}")
            continue
        
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
                
                # 检查本轮检查周期内是否已执行过买入（避免重复信号导致重复成交）
                already_bought = any(t.get('code') == code and t.get('action') == '买入' for t in trades)
                if already_bought:
                    _log(f"  ⚪ {name}: 本轮已买入，跳过重复信号")
                    continue
                
                # v2.1: 新风控检查
                pct = pyramid[1] if strength == 'strong' else pyramid[0]
                raw_shares = int(s.initial_capital * pct / quote['current'])
                shares = normalize_shares(code, raw_shares, 'buy')
                
                order_check = risk.check_order(code, 'buy', shares, quote['current'], account.cash + sum(p['shares'] * quotes.get(p['code'], {}).get('current', 0) for p in account.positions.values()))
                if not order_check.get('allowed', True):
                    _log(f"  ⚪ {name}: 风控拦截 - {order_check.get('reason', '未知')}")
                    continue
                if order_check.get('level') == 'warning':
                    _log(f"  ⚠️ {name}: 风控警告 - {order_check.get('reason', '未知')}")
                
                t = executor.buy(code, name, shares, quote['current'], result['reason'])
                if t:
                    trades.append(t)
            else:
                pos = account.get_position(code)
                level = pos.get('add_level', 1)
                dip = (quote['current'] - pos['avg_price']) / pos['avg_price']
                
                # 检查本轮检查周期内是否已执行过加仓（避免重复信号）
                already_added = any(t.get('code') == code and '加仓' in t.get('action', '') for t in trades)
                if already_added:
                    _log(f"  ⚪ {name}: 本轮已加仓，跳过重复信号")
                elif dip <= -trade_cfg.get('add_dip_pct', 0.03) and level < len(pyramid):
                    add_pct = pyramid[level] - pyramid[level - 1]
                    raw_add = int(s.initial_capital * add_pct / quote['current'])
                    add_shares = normalize_shares(code, raw_add, 'buy')
                    if add_shares >= get_min_shares(code):
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
            label = '🟢 强势减仓' if result.get('strength') == 'strong' else '🟢 策略减仓'
            raw_sell = int(sellable * sell_pct)
            sell_n = normalize_shares(code, raw_sell, 'sell')
            min_shares = get_min_shares(code)
            if sell_n < min_shares:
                # 零股必须一次性卖出
                sell_n = sellable if sellable < min_shares else 0
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
    
    # v2.2: 绩效分析 (如果有交易记录)
    try:
        import pandas as pd
        trades_file = s.get('trade_log_file', 'sim_trading/交易记录.json')
        import json
        from pathlib import Path
        
        trades_path = Path(trades_file)
        if trades_path.exists():
            with open(trades_path, 'r', encoding='utf-8') as f:
                trades_data = json.load(f)
            
            if isinstance(trades_data, list) and len(trades_data) > 0:
                trades_df = pd.DataFrame(trades_data)
                if 'date' in trades_df.columns and 'pnl' in trades_df.columns:
                    _log("\n📈 绩效分析 (quantstats):")
                    report = generate_report(trades_df, initial_capital=s.initial_capital)
                    if 'error' not in report:
                        _log(format_report(report))
                        
                        # 如果有 HTML 报告，记录路径
                        if 'html_report' in report.get('metrics', {}):
                            _log(f"\n📄 HTML 报告：{report['metrics']['html_report']}")
    except Exception as e:
        _log(f"[绩效分析] 跳过：{e}")
    
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
    
    last_force_buyback_date = ''
    
    while True:
        # 检查交易时段
        if s.is_trading_hours():
            try:
                run_check()
                
                # v2.2.19 新增：收盘前强制接回所有做 T 卖出的股票
                from datetime import datetime
                now = datetime.now()
                time_str = now.strftime('%H:%M')
                today_str = now.strftime('%Y-%m-%d')
                
                # 14:55 收盘前 5 分钟，强制接回
                if '14:55' <= time_str <= '15:00' and today_str != last_force_buyback_date:
                    from strategy.engine import GridTStrategy
                    # 获取 grid_t 实例
                    grid_t = GridTStrategy(s.get('day_trading', {}))
                    # 加载状态 (需要从 run_check 中传递，这里简化处理)
                    # 实际应该在 run_check 中处理
                    last_force_buyback_date = today_str
                    _log("  ⏰ 收盘前检查：强制接回所有做 T 卖出的股票")
                
                portfolio_summary()
            except Exception as e:
                _log(f"❌ 错误：{e}")
                _notify("⚠️ BobQuant 错误", f"交易检查出错：{e}")
        else:
            _log("⏸️ 非交易时段，等待...")
        
        time.sleep(s.check_interval)


if __name__ == '__main__':
    main_loop()
