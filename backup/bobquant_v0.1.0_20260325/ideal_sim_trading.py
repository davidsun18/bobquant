# -*- coding: utf-8 -*-
"""
理想化模拟盘交易系统
- 假设每笔交易都成交
- 自动执行买卖
- 自动计算手续费（万分之五）
- 实时统计盈亏
"""

import requests
import json
import time
from datetime import datetime
import os

# ==================== 配置 ====================
CONFIG = {
    'initial_capital': 1000000,  # 初始资金 100 万 ⭐
    'commission_rate': 0.0005,  # 手续费万分之五
    'positions_file': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json',
    'log_file': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/模拟盘日志.log',
    'trade_log_file': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json',
    'check_interval': 30,  # 30 秒检查一次 ⭐
    'feishu_push': True,  # 开启飞书推送
    'user_id': 'ou_973651ccbc692b7cd90a7d561f6885b3',  # 飞书用户 ID
    'max_position_percent': 0.05,  # 单只股票最大仓位 5%
    'max_stocks': 20,  # 最大持仓数量
}

# ==================== 交易增强配置 ====================
TRADE_CONFIG = {
    # 金字塔加仓
    'pyramid_levels': [0.03, 0.05, 0.07],  # 仓位递进: 3% → 5% → 7%
    'add_dip_pct': 0.03,                    # 跌3%触发加仓

    # 分批止盈 + 跟踪止损
    'take_profit': [
        {'pct': 0.05, 'sell_ratio': 0.33},  # 涨5%卖1/3
        {'pct': 0.10, 'sell_ratio': 0.50},  # 涨10%卖1/2剩余
        {'pct': 0.15, 'sell_ratio': 1.00},  # 涨15%全卖
    ],
    'stop_loss_pct': -0.08,                 # 亏8%止损
    'trailing_stop_activate': 0.05,         # 盈利5%后激活跟踪止损
    'trailing_stop_drawdown': 0.02,         # 从最高点回撤2%触发卖出

    # 网格做T（替代固定阈值）
    't_grid_up': 0.02,     # 日内涨2%触发第一次高抛
    't_grid_step': 0.015,  # 每涨1.5%再抛一次（多档网格）
    't_grid_max': 3,       # 单日最多3次网格卖出
    't_buyback_dip': 0.01, # 较最后一次卖出价回落1%接回
    't_sell_ratio': 0.20,  # 每次高抛可卖部分的20%

    # 信号增强
    'rsi_buy_max': 35,     # RSI < 35 才允许买入（避免追高）
    'rsi_sell_min': 70,    # RSI > 70 加强卖出信号
    'volume_confirm': True, # 成交量确认开关
    'volume_ratio_buy': 1.5, # 买入需成交量 > 20日均量的1.5倍
}

# 导入股票池和配置
from stock_pool_50 import STOCK_POOL
from itick_config import ITICK_CONFIG
CONFIG['stock_pool'] = STOCK_POOL
CONFIG['itick'] = ITICK_CONFIG

# ==================== 日志 ====================
def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    try:
        with open(CONFIG['log_file'], 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except:
        pass

# ==================== 飞书推送 ====================
def send_feishu(title, message, msg_type='text'):
    """发送飞书消息 - 使用 message 工具"""
    if not CONFIG.get('feishu_push', False):
        return
    
    try:
        import subprocess
        import json
        
        # 构建消息内容
        if msg_type == 'text':
            content = f"{title}\n\n{message}"
        elif msg_type == 'post':
            content = {
                "zh_cn": {
                    "title": title,
                    "content": [[{"tag": "text", "text": message}]]
                }
            }
        
        # 使用 message 工具发送
        cmd = [
            'message', 'send',
            '--target', f"user:{CONFIG['user_id']}",
            '--message', content
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            log(f"  📱 飞书推送成功")
        else:
            # 如果 message 命令失败，记录但不影响交易
            log(f"  ⚠️ 飞书推送失败：{result.stderr}")
    except Exception as e:
        # 异常时记录日志，但不影响交易执行
        log(f"  ⚠️ 飞书推送异常：{e}")

# ==================== 获取实时价格（腾讯财经 - 主力接口）====================
def get_price_tencent(code, max_retries=2):
    """获取实时价格（腾讯财经接口 - 主力使用）"""
    symbol = code.replace('.', '')
    url = f"http://qt.gtimg.cn/q={symbol}"
    
    for i in range(max_retries):
        try:
            headers = {'Referer': 'http://stockapp.finance.qq.com', 'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=3)
            response.encoding = 'gbk'
            
            if response.status_code == 200:
                data = response.text.strip()
                if '=' in data and '"' in data:
                    parts = data.split('=')[1].strip('"').split('~')
                    if len(parts) >= 32:
                        return {
                            'name': parts[1],
                            'current': float(parts[3]),
                            'open': float(parts[5]),
                            'pre_close': float(parts[4]),
                            'high': float(parts[32]) if len(parts) > 32 else float(parts[5]),
                            'low': float(parts[33]) if len(parts) > 33 else float(parts[5]),
                            'change': ((float(parts[3]) - float(parts[4])) / float(parts[4]) * 100) if float(parts[4]) > 0 else 0
                        }
        except:
            if i < max_retries - 1:
                time.sleep(1)
            continue
    
    return None

# ==================== 获取实时价格（iTick - 测试备用）====================
def get_price_itick_batch(codes_batch):
    """
    使用 iTick 批量获取实时价格（后台测试）
    codes_batch: 股票代码列表
    返回：{code: {name, current, ...}}
    """
    try:
        token = CONFIG['itick']['token']
        api_url = CONFIG['itick']['api_url']
        
        params = {'token': token, 'codes': ','.join(codes_batch)}
        headers = {'User-Agent': 'OpenClaw-Quant/1.0', 'Accept': 'application/json'}
        
        response = requests.get(api_url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            results = {}
            
            if data.get('status') == 'ok' and 'data' in data:
                for quote in data['data']:
                    code = quote.get('code', '')
                    results[code] = {
                        'name': quote.get('name', ''),
                        'current': float(quote.get('price', 0)),
                        'open': float(quote.get('open', 0)),
                        'pre_close': float(quote.get('pre_close', 0)),
                        'high': float(quote.get('high', 0)),
                        'low': float(quote.get('low', 0)),
                        'change': float(quote.get('change', 0))
                    }
            
            return results
        else:
            log(f"  ⚠️ iTick API 错误：HTTP {response.status_code}")
            return {}
    
    except Exception as e:
        log(f"  ⚠️ iTick 请求失败：{e}")
        return {}

# 默认使用腾讯财经
get_price = get_price_tencent

# 使用腾讯财经作为主力接口（iTick 备用）
if ITICK_CONFIG.get('enabled', False):
    CONFIG['check_interval'] = ITICK_CONFIG['interval_seconds']
    get_price = get_price_itick_batch  # 使用 iTick
else:
    CONFIG['check_interval'] = 30  # 腾讯财经 30 秒检查一次
    # get_price 已经设置为 get_price_tencent

# ==================== 加载账户 ====================
def load_account():
    """加载账户"""
    if os.path.exists(CONFIG['positions_file']):
        with open(CONFIG['positions_file'], 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            'cash': CONFIG['initial_capital'],
            'initial_capital': CONFIG['initial_capital'],
            'positions': {},
            'trade_history': [],
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# ==================== 保存账户 ====================
def save_account(account):
    """保存账户"""
    account['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(CONFIG['positions_file'], 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)

# ==================== 辅助函数（加仓/减仓/做T） ====================
def get_sellable_shares(pos):
    """计算T+1可卖股数，通过 buy_lots 逐笔判断"""
    today = datetime.now().strftime('%Y-%m-%d')
    lots = pos.get('buy_lots', [])
    if not lots:
        # 兼容旧数据
        if pos.get('buy_date', '') == today:
            return 0
        return pos.get('shares', 0)
    sellable = 0
    for lot in lots:
        if lot['date'] != today:
            sellable += lot['shares']
    return min(sellable, pos.get('shares', 0))  # 不超过总持仓


def migrate_positions(account):
    """给旧持仓添加 buy_lots/add_level/profit_taken"""
    for code, pos in account['positions'].items():
        if 'buy_lots' not in pos:
            pos['buy_lots'] = [{
                'shares': pos['shares'],
                'price': pos.get('buy_price', pos['avg_price']),
                'date': pos.get('buy_date', '2026-03-24'),
                'time': pos.get('buy_time', ''),
            }]
        if 'add_level' not in pos:
            pos['add_level'] = 1
        if 'profit_taken' not in pos:
            pos['profit_taken'] = 0


def get_stock_name_from_pool(code):
    """从股票池查名称"""
    for stock in CONFIG['stock_pool']:
        if stock[0] == code:
            return stock[1]
    return code


def execute_buy(account, code, name, shares, price, reason, is_add=False):
    """
    统一的买入执行函数
    - 计算手续费，扣减现金
    - 新建仓或加仓（更新avg_price, shares, buy_lots, add_level）
    - 返回交易记录dict（用于trades_executed）
    - 资金不足返回None
    """
    # 股数取整到100的整数倍
    shares = int(shares / 100) * 100
    if shares <= 0:
        return None

    cost = shares * price
    commission = cost * CONFIG['commission_rate']
    total_cost = cost + commission

    # 检查资金
    if total_cost > account['cash']:
        log(f"  ⚠️ {name}: 资金不足 (需要¥{total_cost:,.0f}, 可用¥{account['cash']:,.0f})")
        return None

    account['cash'] -= total_cost

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_str = datetime.now().strftime('%Y-%m-%d')

    new_lot = {
        'shares': shares,
        'price': price,
        'date': today_str,
        'time': now_str,
    }

    if code in account['positions'] and account['positions'][code]['shares'] > 0:
        # 加仓：更新均价和股数
        pos = account['positions'][code]
        old_shares = pos['shares']
        old_avg = pos['avg_price']
        new_total_shares = old_shares + shares
        pos['avg_price'] = (old_shares * old_avg + shares * price) / new_total_shares
        pos['shares'] = new_total_shares
        pos['buy_lots'].append(new_lot)
        pos['add_level'] = pos.get('add_level', 1) + 1
        pos['commission'] = pos.get('commission', 0) + commission
        action_label = f"加仓L{pos['add_level']}" if is_add else "买入"
    else:
        # 新建仓
        account['positions'][code] = {
            'shares': shares,
            'avg_price': price,
            'buy_price': price,
            'buy_date': today_str,
            'buy_time': now_str,
            'commission': commission,
            'buy_lots': [new_lot],
            'add_level': 1,
            'profit_taken': 0,
        }
        action_label = "买入"

    emoji = "🟢"
    log(f"  {emoji} {action_label} {name}: {shares}股 @ ¥{price:.2f} (手续费¥{commission:.2f})")
    log(f"     原因：{reason}")

    send_feishu(
        f"{emoji} {action_label} - {name}",
        f"股票：{code} {name}\n"
        f"操作：{action_label}\n"
        f"数量：{shares}股\n"
        f"价格：¥{price:.2f}\n"
        f"金额：¥{cost:,.2f}\n"
        f"手续费：¥{commission:.2f}\n"
        f"原因：{reason}\n"
        f"时间：{datetime.now().strftime('%H:%M:%S')}"
    )

    trade = {
        'time': now_str,
        'code': code,
        'name': name,
        'action': action_label,
        'shares': shares,
        'price': price,
        'amount': cost,
        'commission': commission,
        'reason': reason,
    }
    account['trade_history'].append(trade)
    return trade


def execute_sell(account, code, name, shares, price, reason, action_label='卖出'):
    """
    统一的卖出执行函数
    - 支持部分卖出（不是全清仓）
    - 计算盈亏
    - 更新 buy_lots（FIFO先卖最早的，跳过today的lot）
    - pos['shares'] 减到0时删除持仓
    - 返回交易记录dict
    """
    if code not in account['positions'] or account['positions'][code]['shares'] <= 0:
        return None

    pos = account['positions'][code]

    # 股数取整到100的整数倍
    shares = int(shares / 100) * 100
    if shares <= 0:
        return None

    # 不能超过可卖股数
    sellable = get_sellable_shares(pos)
    shares = min(shares, sellable)
    shares = int(shares / 100) * 100
    if shares <= 0:
        return None

    revenue = shares * price
    commission = revenue * CONFIG['commission_rate']
    net_revenue = revenue - commission

    # 计算盈亏（基于均价）
    cost_basis = shares * pos['avg_price']
    profit = net_revenue - cost_basis
    profit_pct = (profit / cost_basis * 100) if cost_basis > 0 else 0

    account['cash'] += net_revenue

    # FIFO 更新 buy_lots（跳过 today 的 lot）
    today = datetime.now().strftime('%Y-%m-%d')
    remaining_to_sell = shares
    new_lots = []
    for lot in pos.get('buy_lots', []):
        if remaining_to_sell <= 0 or lot['date'] == today:
            new_lots.append(lot)
            continue
        if lot['shares'] <= remaining_to_sell:
            remaining_to_sell -= lot['shares']
            # 这个lot被完全卖掉，不保留
        else:
            lot['shares'] -= remaining_to_sell
            remaining_to_sell = 0
            new_lots.append(lot)
    pos['buy_lots'] = new_lots

    # 更新持仓股数
    pos['shares'] -= shares

    emoji = "🔴" if "做T" not in action_label else "🔄"

    if pos['shares'] <= 0:
        del account['positions'][code]
        log(f"  {emoji} {action_label} {name}: {shares}股 @ ¥{price:.2f} (清仓, 手续费¥{commission:.2f})")
    else:
        log(f"  {emoji} {action_label} {name}: {shares}股 @ ¥{price:.2f} (剩余{pos['shares']}股, 手续费¥{commission:.2f})")

    log(f"     盈亏：¥{profit:,.2f} ({profit_pct:+.1f}%)")
    log(f"     原因：{reason}")

    send_feishu(
        f"{emoji} {action_label} - {name}",
        f"股票：{code} {name}\n"
        f"操作：{action_label}\n"
        f"数量：{shares}股\n"
        f"价格：¥{price:.2f}\n"
        f"金额：¥{revenue:,.2f}\n"
        f"手续费：¥{commission:.2f}\n"
        f"盈亏：¥{profit:,.2f} ({profit_pct:+.1f}%)\n"
        f"原因：{reason}\n"
        f"时间：{datetime.now().strftime('%H:%M:%S')}"
    )

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trade = {
        'time': now_str,
        'code': code,
        'name': name,
        'action': action_label,
        'shares': shares,
        'price': price,
        'amount': revenue,
        'commission': commission,
        'profit': profit,
        'profit_pct': profit_pct,
        'reason': reason,
    }
    account['trade_history'].append(trade)
    return trade


def sync_trade_log(trades):
    """同步交易到交易记录.json"""
    if not trades:
        return
    try:
        trade_log_file = CONFIG['trade_log_file']
        existing_trades = []
        if os.path.exists(trade_log_file):
            with open(trade_log_file, 'r', encoding='utf-8') as f:
                existing_trades = json.load(f)
        existing_trades.extend(trades)
        with open(trade_log_file, 'w', encoding='utf-8') as f:
            json.dump(existing_trades, f, ensure_ascii=False, indent=2)
        log(f"  ✅ 交易记录已同步到 交易记录.json")
    except Exception as e:
        log(f"  ⚠️ 交易记录同步失败: {e}")


# 做T 日内状态（模块级变量）
_t_state = {}       # {code: {'sells': [{'shares':n,'price':p},...], 'total_sold': n, 'count': n, 'bought_back': bool}}
_t_state_date = ''  # 日期切换时重置
# 跟踪止损：记录每只股票的最高盈利价
_trailing_high = {}  # {code: max_price}

# ==================== 计算指标 ====================
def calculate_macd(df, ma1=12, ma2=26):
    """计算 MACD"""
    df['ma1'] = df['close'].rolling(ma1).mean()
    df['ma2'] = df['close'].rolling(ma2).mean()
    df['macd'] = df['ma1'] - df['ma2']
    return df

def calculate_bollinger(df, window=20, std=2):
    """计算布林带"""
    df['bb_mid'] = df['close'].rolling(window).mean()
    df['bb_std'] = df['close'].rolling(window).std()
    df['bb_upper'] = df['bb_mid'] + std * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - std * df['bb_std']
    df['bb_pos'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    return df

def calculate_rsi(df, period=14):
    """计算 RSI 相对强弱指标"""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def calculate_volume_ratio(df, period=20):
    """计算量比（当日成交量 / N日均量）"""
    df['vol_ma'] = df['volume'].rolling(period).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma'].replace(0, 1e-10)
    return df

# ==================== 获取历史数据 ====================
def get_history(code, days=60):
    """获取历史数据（用于计算指标）"""
    try:
        lg = bs.login()
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=start_date, end_date=end_date, frequency="d"
        )
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        
        if len(data) > 0:
            df = pd.DataFrame(data, columns=rs.fields)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
    except:
        pass
    return None

# ==================== 交易逻辑（三阶段：做T → 风控 → 策略信号） ====================
def check_signals():
    """
    三阶段检查交易信号：
    Phase 1 - 做T（日内高抛低吸）
    Phase 2 - 风控（止损止盈）
    Phase 3 - 策略信号（MACD/布林带 建仓/加仓/减仓）
    """
    global _t_state, _t_state_date
    
    account = load_account()
    migrate_positions(account)  # 兼容旧数据
    
    log(f"📊 检查交易信号（三阶段）...")
    
    trades_executed = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 日期切换时重置做T状态
    if _t_state_date != today:
        _t_state = {}
        _t_state_date = today
    
    # ============================================================
    # Phase 1 - 网格做T（多档高抛低吸）
    # ============================================================
    log(f"  📌 Phase 1: 网格做T扫描...")
    for code, pos in list(account['positions'].items()):
        name = get_stock_name_from_pool(code)
        sellable = get_sellable_shares(pos)
        if sellable <= 0:
            continue
        
        quote = get_price(code)
        if not quote or quote['current'] <= 0 or quote['open'] <= 0:
            continue
        
        current_price = quote['current']
        open_price = quote['open']
        intraday_change = (current_price - open_price) / open_price
        
        if code not in _t_state:
            _t_state[code] = {'sells': [], 'total_sold': 0, 'count': 0, 'bought_back': False}
        t_info = _t_state[code]
        
        # 网格高抛：检查是否触发某档网格线
        grid_up = TRADE_CONFIG['t_grid_up']
        grid_step = TRADE_CONFIG['t_grid_step']
        grid_max = TRADE_CONFIG['t_grid_max']
        sell_ratio = TRADE_CONFIG['t_sell_ratio']
        
        if (not t_info['bought_back']
                and t_info['count'] < grid_max
                and sellable > 0):
            # 当前应触发的网格档位
            target_level = t_info['count'] + 1
            trigger_pct = grid_up + (target_level - 1) * grid_step
            
            if intraday_change >= trigger_pct:
                t_sell_shares = int(sellable * sell_ratio / 100) * 100
                if t_sell_shares >= 100:
                    trade = execute_sell(account, code, name, t_sell_shares, current_price,
                                         f'网格做T L{target_level} (日内+{intraday_change*100:.1f}%，触发{trigger_pct*100:.1f}%)',
                                         '🔄 做T卖出')
                    if trade:
                        trades_executed.append(trade)
                        t_info['sells'].append({'shares': t_sell_shares, 'price': current_price})
                        t_info['total_sold'] += t_sell_shares
                        t_info['count'] += 1
                        # 更新可卖股数
                        sellable = get_sellable_shares(account['positions'].get(code, pos))
        
        # 做T接回：之前高抛过，价格较最后一次卖出价回落 >= 1%
        if (t_info['total_sold'] > 0
              and not t_info['bought_back']
              and len(t_info['sells']) > 0):
            last_sell_price = t_info['sells'][-1]['price']
            if current_price <= last_sell_price * (1 - TRADE_CONFIG['t_buyback_dip']):
                buyback_shares = t_info['total_sold']
                trade = execute_buy(account, code, name, buyback_shares, current_price,
                                    f'做T接回 (均卖¥{last_sell_price:.2f}→¥{current_price:.2f}，赚差价)', is_add=True)
                if trade:
                    trade['action'] = '🔄 做T接回'
                    trades_executed.append(trade)
                    t_info['bought_back'] = True
    
    # ============================================================
    # Phase 2 - 风控（止损 + 跟踪止损 + 分批止盈）
    # ============================================================
    log(f"  📌 Phase 2: 风控扫描...")
    for code, pos in list(account['positions'].items()):
        name = get_stock_name_from_pool(code)
        sellable = get_sellable_shares(pos)
        if sellable <= 0:
            continue
        
        quote = get_price(code)
        if not quote or quote['current'] <= 0:
            continue
        
        current_price = quote['current']
        avg_price = pos['avg_price']
        if avg_price <= 0:
            continue
        profit_pct = (current_price - avg_price) / avg_price
        
        # 1) 硬止损：亏 >= 8%
        if profit_pct <= TRADE_CONFIG['stop_loss_pct']:
            trade = execute_sell(account, code, name, sellable, current_price,
                                 f'止损 ({profit_pct*100:+.1f}%)', '🔴 止损卖出')
            if trade:
                trades_executed.append(trade)
            if code in _trailing_high:
                del _trailing_high[code]
            continue
        
        # 2) 跟踪止损：盈利超过激活线后，从最高点回撤超过阈值则卖出
        trailing_activate = TRADE_CONFIG['trailing_stop_activate']
        trailing_drawdown = TRADE_CONFIG['trailing_stop_drawdown']
        
        if profit_pct >= trailing_activate:
            # 更新最高价
            if code not in _trailing_high or current_price > _trailing_high[code]:
                _trailing_high[code] = current_price
            
            high_price = _trailing_high[code]
            drawdown = (high_price - current_price) / high_price
            
            if drawdown >= trailing_drawdown:
                trade = execute_sell(account, code, name, sellable, current_price,
                                     f'跟踪止损 (最高¥{high_price:.2f}→¥{current_price:.2f}，回撤{drawdown*100:.1f}%)',
                                     '🔴 跟踪止损')
                if trade:
                    trades_executed.append(trade)
                if code in _trailing_high:
                    del _trailing_high[code]
                continue
        
        # 3) 分批止盈
        profit_taken = pos.get('profit_taken', 0)
        tp_levels = TRADE_CONFIG['take_profit']
        
        if profit_taken < len(tp_levels):
            tp = tp_levels[profit_taken]
            if profit_pct >= tp['pct']:
                tp_shares = int(sellable * tp['sell_ratio'] / 100) * 100
                if tp_shares >= 100:
                    label = f'止盈L{profit_taken+1}'
                    trade = execute_sell(account, code, name, tp_shares, current_price,
                                         f'{label} (盈{profit_pct*100:+.1f}% 卖{tp["sell_ratio"]*100:.0f}%)',
                                         f'🔴 {label}')
                    if trade:
                        trades_executed.append(trade)
                        if code in account['positions']:
                            account['positions'][code]['profit_taken'] = profit_taken + 1
    
    # ============================================================
    # Phase 3 - 策略信号（RSI+量确认 + MACD/布林带 建仓/加仓/减仓）
    # ============================================================
    log(f"  📌 Phase 3: 策略信号扫描...")
    for stock in CONFIG['stock_pool']:
        code = stock[0]
        name = stock[1]
        strategy = stock[2]
        
        quote = get_price(code)
        if not quote or quote['current'] <= 0:
            continue
        
        current_price = quote['current']
        
        # 获取历史数据计算指标
        df = get_history(code)
        if df is None or len(df) < 30:
            continue
        
        # 计算 RSI 和量比（所有策略通用）
        df = calculate_rsi(df, 14)
        df = calculate_volume_ratio(df, 20)
        latest = df.iloc[-1]
        rsi = latest.get('rsi', 50)
        vol_ratio = latest.get('vol_ratio', 1.0)
        
        signal = None
        reason = ''
        signal_strength = 'normal'  # normal / strong / weak
        
        # === 策略判断 ===
        if strategy == 'macd':
            df = calculate_macd(df, 12, 26)
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            if latest['ma1'] > latest['ma2'] and prev['ma1'] <= prev['ma2']:
                signal = 'buy'
                reason = 'MACD 金叉'
                # 放量金叉 = 强信号
                if vol_ratio >= TRADE_CONFIG['volume_ratio_buy']:
                    signal_strength = 'strong'
                    reason += f' + 放量({vol_ratio:.1f}x)'
            elif latest['ma1'] < latest['ma2'] and prev['ma1'] >= prev['ma2']:
                signal = 'sell'
                reason = 'MACD 死叉'
        
        elif strategy == 'bollinger':
            df = calculate_bollinger(df, 20, 2)
            latest = df.iloc[-1]
            
            if latest['bb_pos'] < 0.1:
                signal = 'buy'
                reason = f'布林带下轨 (%B={latest["bb_pos"]:.2f})'
                if vol_ratio >= TRADE_CONFIG['volume_ratio_buy']:
                    signal_strength = 'strong'
                    reason += f' + 放量({vol_ratio:.1f}x)'
            elif latest['bb_pos'] > 0.9:
                signal = 'sell'
                reason = f'布林带上轨 (%B={latest["bb_pos"]:.2f})'
        
        # === RSI 过滤 ===
        if signal == 'buy':
            if rsi > TRADE_CONFIG['rsi_buy_max']:
                log(f"  ⚪ {name}: {reason} 但 RSI={rsi:.0f}>{TRADE_CONFIG['rsi_buy_max']}，过滤掉")
                continue
            reason += f' RSI={rsi:.0f}'
        
        if signal == 'sell':
            if rsi > TRADE_CONFIG['rsi_sell_min']:
                signal_strength = 'strong'
                reason += f' + RSI超买({rsi:.0f})'
            reason += f' RSI={rsi:.0f}'
        
        # === 成交量确认（可选）===
        if signal == 'buy' and TRADE_CONFIG['volume_confirm'] and signal_strength != 'strong':
            if vol_ratio < 0.8:
                log(f"  ⚪ {name}: {reason} 但缩量({vol_ratio:.1f}x)，信号较弱，跳过")
                continue
        
        # === 买入信号 ===
        if signal == 'buy':
            has_position = code in account['positions'] and account['positions'][code]['shares'] > 0
            
            if not has_position:
                # 新建仓：强信号直接上5%，普通信号3%
                if signal_strength == 'strong':
                    level_pct = TRADE_CONFIG['pyramid_levels'][1]  # 5%
                    reason += ' [强信号→5%仓位]'
                else:
                    level_pct = TRADE_CONFIG['pyramid_levels'][0]  # 3%
                
                target_amount = CONFIG['initial_capital'] * level_pct
                shares = int(target_amount / current_price / 100) * 100
                if shares < 100:
                    shares = 100
                
                trade = execute_buy(account, code, name, shares, current_price, reason)
                if trade:
                    trades_executed.append(trade)
            else:
                # 加仓判断
                pos = account['positions'][code]
                add_level = pos.get('add_level', 1)
                dip_pct = (current_price - pos['avg_price']) / pos['avg_price']
                
                if dip_pct <= -TRADE_CONFIG['add_dip_pct'] and add_level < len(TRADE_CONFIG['pyramid_levels']):
                    next_pct = TRADE_CONFIG['pyramid_levels'][add_level]
                    target_amount = CONFIG['initial_capital'] * (next_pct - TRADE_CONFIG['pyramid_levels'][add_level - 1])
                    add_shares = int(target_amount / current_price / 100) * 100
                    if add_shares >= 100:
                        trade = execute_buy(account, code, name, add_shares, current_price,
                                             f'{reason} + 加仓L{add_level+1} (跌{dip_pct*100:.1f}%)', is_add=True)
                        if trade:
                            trades_executed.append(trade)
                else:
                    log(f"  ⚪ {name}: 已持仓L{add_level}，等待加仓条件")
        
        # === 卖出信号 ===
        elif signal == 'sell':
            if code not in account['positions'] or account['positions'][code]['shares'] <= 0:
                continue
            
            pos = account['positions'][code]
            sellable = get_sellable_shares(pos)
            if sellable <= 0:
                log(f"  ⚪ {name}: T+1 限制，无可卖股数")
                continue
            
            # 强卖出信号（RSI超买）卖70%，普通卖50%
            if signal_strength == 'strong':
                sell_pct = 0.7
                action_label = '🔴 强势减仓'
            else:
                sell_pct = 0.5
                action_label = '🔴 策略减仓'
            
            sell_shares = int(sellable * sell_pct / 100) * 100
            if sell_shares < 100:
                sell_shares = min(100, int(sellable / 100) * 100)
            if sell_shares >= 100:
                trade = execute_sell(account, code, name, sell_shares, current_price,
                                     f'策略减仓 ({reason})', action_label)
                if trade:
                    trades_executed.append(trade)
    
    # ============================================================
    # 保存 + 同步
    # ============================================================
    if len(trades_executed) > 0:
        save_account(account)
        sync_trade_log(trades_executed)
        log(f"  ✅ 执行 {len(trades_executed)} 笔交易，账户已更新")
    else:
        log(f"  ⚪ 无交易信号")
    
    return trades_executed

# ==================== 账户汇总 ====================
def portfolio_summary():
    """显示账户汇总"""
    account = load_account()
    
    # 计算持仓市值
    market_value = 0
    position_details = []
    
    for code, pos in account['positions'].items():
        quote = get_price(code)
        if quote:
            current = quote['current']
            mv = pos['shares'] * current
            cost = pos['shares'] * pos['avg_price']
            profit = mv - cost
            profit_pct = profit / cost * 100
            
            market_value += mv
            position_details.append({
                'code': code,
                'name': pos.get('name', code),
                'shares': pos['shares'],
                'cost': cost,
                'market_value': mv,
                'profit': profit,
                'profit_pct': profit_pct
            })
    
    total_assets = account['cash'] + market_value
    total_profit = total_assets - account['initial_capital']
    total_profit_pct = total_profit / account['initial_capital'] * 100
    
    log(f"💰 账户汇总:")
    log(f"   现金：¥{account['cash']:,.2f}")
    log(f"   持仓市值：¥{market_value:,.2f}")
    log(f"   总资产：¥{total_assets:,.2f}")
    log(f"   总盈亏：¥{total_profit:,.2f} ({total_profit_pct:+.2f}%)")
    
    if len(position_details) > 0:
        log(f"   持仓明细:")
        for pos in position_details:
            emoji = '🟢' if pos['profit'] > 0 else '🔴' if pos['profit'] < 0 else '⚪'
            log(f"     {emoji} {pos['code']}: ¥{pos['profit']:,.0f} ({pos['profit_pct']:+.1f}%)")
    
    return {
        'cash': account['cash'],
        'market_value': market_value,
        'total_assets': total_assets,
        'total_profit': total_profit,
        'total_profit_pct': total_profit_pct,
        'positions': position_details
    }

# ==================== 主循环 ====================
def main_loop():
    """主循环"""
    log("="*70)
    log("🎯 理想化模拟盘启动")
    log("="*70)
    log(f"初始资金：¥{CONFIG['initial_capital']:,.2f}")
    log(f"手续费率：万分之五 ({CONFIG['commission_rate']*10000:.0f}‱)")
    log(f"检查间隔：{CONFIG['check_interval']}秒")
    log(f"监控股票：{len(CONFIG['stock_pool'])} 只")
    log("="*70)
    
    # 首次运行显示账户
    portfolio_summary()
    
    last_check = None
    
    while True:
        try:
            now = datetime.now()
            current_minute = now.strftime('%H:%M')
            
            # 交易时间判断
            if now.weekday() >= 5:  # 周末
                log(f"💤 周末休市，明日再见")
                break
            
            hour, minute = now.hour, now.minute
            if hour < 9 or (hour == 9 and minute < 30):
                log(f"💤 未开盘，等待中...")
                time.sleep(300)
                continue
            elif 11 <= hour < 13:
                log(f"💤 午休时间...")
                time.sleep(300)
                continue
            elif hour >= 15:
                log(f"💤 已收盘，明日再见")
                break
            
            # 每分钟检查一次
            if current_minute != last_check:
                check_signals()
                portfolio_summary()
                last_check = current_minute
            
            time.sleep(CONFIG['check_interval'])
            
        except KeyboardInterrupt:
            log("\n⚠️ 用户中断")
            break
        except Exception as e:
            log(f"❌ 错误：{e}")
            time.sleep(10)
    
    log("="*70)
    log("📊 模拟盘结束")
    log("="*70)

# ==================== 主函数 ====================
if __name__ == '__main__':
    import pandas as pd
    import baostock as bs
    
    main_loop()
