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

# ==================== 交易逻辑 ====================
def check_signals():
    """检查交易信号并执行（腾讯财经 - 主力）"""
    account = load_account()
    
    log(f"📊 检查交易信号...")
    
    trades_executed = []
    
    for stock in CONFIG['stock_pool']:
        # 股票池格式：('code', 'name', 'strategy')
        code = stock[0]
        name = stock[1]
        strategy = stock[2]
        
        # 获取实时价格（腾讯财经）
        quote = get_price(code)
        if not quote:
            log(f"  ⚠️ {name}: 获取价格失败")
            continue
        
        current_price = quote['current']
        
        # 获取历史数据计算指标
        df = get_history(code)
        if df is None or len(df) < 30:
            continue
        
        signal = None
        reason = ''
        
        # === 策略判断 ===
        if strategy == 'macd':
            df = calculate_macd(df, 12, 26)  # MACD 默认参数
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 金叉买入
            if latest['ma1'] > latest['ma2'] and prev['ma1'] <= prev['ma2']:
                signal = 'buy'
                reason = 'MACD 金叉'
            # 死叉卖出
            elif latest['ma1'] < latest['ma2'] and prev['ma1'] >= prev['ma2']:
                signal = 'sell'
                reason = 'MACD 死叉'
        
        elif strategy == 'bollinger':
            df = calculate_bollinger(df, 20, 2)  # 布林带默认参数
            latest = df.iloc[-1]
            
            # 下轨买入
            if latest['bb_pos'] < 0.1:
                signal = 'buy'
                reason = f'布林带下轨 (%B={latest["bb_pos"]:.2f})'
            # 上轨卖出
            elif latest['bb_pos'] > 0.9:
                signal = 'sell'
                reason = f'布林带上轨 (%B={latest["bb_pos"]:.2f})'
        
        # === 执行交易 ===
        if signal == 'buy':
            # 检查是否已持仓
            if code in account['positions'] and account['positions'][code]['shares'] > 0:
                log(f"  ⚪ {name}: 已持仓，跳过买入")
                continue
            
            # 智能仓位管理：根据股价和流动性调整
            # 基础仓位 5%，根据股价灵活调整 3%-8%
            
            base_percent = CONFIG['max_position_percent']  # 5%
            
            # 股价调整因子：
            # - 高价股 (>100 元)：增加仓位到 6-7%（因为股数少，波动大）
            # - 中价股 (30-100 元)：标准仓位 5%
            # - 低价股 (<30 元)：降低仓位到 3-4%（因为股数多，流动性好）
            if current_price > 100:
                price_factor = 1.4  # 高价股 7%
            elif current_price > 50:
                price_factor = 1.2  # 6%
            elif current_price < 30:
                price_factor = 0.7  # 3.5%
            elif current_price < 20:
                price_factor = 0.6  # 3%
            else:
                price_factor = 1.0  # 标准 5%
            
            # 流动性调整因子：成交量大的可增加仓位
            volume_factor = 1.0
            if 'volume' in df.columns and len(df) > 20:
                avg_volume = df['volume'].iloc[-20:].mean()
                if avg_volume > 1000000:  # 日均成交>100 万股
                    volume_factor = 1.2
                elif avg_volume < 100000:  # 日均成交<10 万股
                    volume_factor = 0.8
            
            # 计算最终仓位比例
            final_percent = base_percent * price_factor * volume_factor
            
            # 限制在 3%-8% 之间
            final_percent = max(0.03, min(0.08, final_percent))
            
            target_amount = CONFIG['initial_capital'] * final_percent
            shares = int(target_amount / current_price / 100) * 100
            
            # 确保至少买 100 股
            if shares < 100:
                shares = 100
            
            if shares <= 0:
                continue
            
            cost = shares * current_price
            commission = cost * CONFIG['commission_rate']
            total_cost = cost + commission
            
            # 检查资金
            if total_cost > account['cash']:
                log(f"  ⚠️ {name}: 资金不足 (需要¥{total_cost:,.0f}, 可用¥{account['cash']:,.0f})")
                continue
            
            # 执行买入
            account['cash'] -= total_cost
            account['positions'][code] = {
                'shares': shares,
                'avg_price': current_price,
                'buy_price': current_price,
                'buy_date': datetime.now().strftime('%Y-%m-%d'),  # T+1 关键：记录买入日期
                'buy_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'commission': commission
            }
            
            log(f"  🟢 买入 {name}: {shares}股 @ ¥{current_price:.2f} (手续费¥{commission:.2f})")
            log(f"     原因：{reason}")
            
            # 飞书推送
            send_feishu(
                f"🟢 买入信号 - {name}",
                f"股票：{code} {name}\n"
                f"操作：买入\n"
                f"数量：{shares}股\n"
                f"价格：¥{current_price:.2f}\n"
                f"金额：¥{cost:,.2f}\n"
                f"手续费：¥{commission:.2f}\n"
                f"原因：{reason}\n"
                f"时间：{datetime.now().strftime('%H:%M:%S')}"
            )
            
            trades_executed.append({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'code': code,
                'name': name,
                'action': '买入',
                'shares': shares,
                'price': current_price,
                'amount': cost,
                'commission': commission,
                'reason': reason
            })
        
        elif signal == 'sell':
            # 检查是否持仓
            if code not in account['positions'] or account['positions'][code]['shares'] <= 0:
                continue
            
            pos = account['positions'][code]
            
            # T+1 检查：今天买入的不能卖
            buy_date = pos.get('buy_date', '')
            today = datetime.now().strftime('%Y-%m-%d')
            
            if buy_date == today:
                log(f"  ⚪ {name}: T+1 限制，今日买入不可卖出")
                continue
            
            shares = pos['shares']
            
            # 执行卖出
            revenue = shares * current_price
            commission = revenue * CONFIG['commission_rate']
            net_revenue = revenue - commission
            
            # 计算盈亏
            profit = net_revenue - (shares * pos['avg_price'] + pos.get('commission', 0))
            profit_pct = profit / (shares * pos['avg_price']) * 100
            
            account['cash'] += net_revenue
            
            trade_record = {
                'sell_price': current_price,
                'sell_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'revenue': revenue,
                'commission': commission,
                'profit': profit,
                'profit_pct': profit_pct,
                'reason': reason
            }
            
            # 添加到历史
            account['trade_history'].append({
                **pos,
                **trade_record,
                'code': code,
                'name': name
            })
            
            del account['positions'][code]
            
            log(f"  🔴 卖出 {name}: {shares}股 @ ¥{current_price:.2f} (手续费¥{commission:.2f})")
            log(f"     盈亏：¥{profit:,.2f} ({profit_pct:+.1f}%)")
            log(f"     原因：{reason}")
            
            # 飞书推送
            send_feishu(
                f"🔴 卖出信号 - {name}",
                f"股票：{code} {name}\n"
                f"操作：卖出\n"
                f"数量：{shares}股\n"
                f"价格：¥{current_price:.2f}\n"
                f"金额：¥{revenue:,.2f}\n"
                f"手续费：¥{commission:.2f}\n"
                f"盈亏：¥{profit:,.2f} ({profit_pct:+.1f}%)\n"
                f"原因：{reason}\n"
                f"时间：{datetime.now().strftime('%H:%M:%S')}"
            )
            
            trades_executed.append({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'code': code,
                'name': name,
                'action': '卖出',
                'shares': shares,
                'price': current_price,
                'amount': revenue,
                'commission': commission,
                'profit': profit,
                'profit_pct': profit_pct,
                'reason': reason
            })
    
    # 保存账户
    if len(trades_executed) > 0:
        save_account(account)
        log(f"  ✅ 执行 {len(trades_executed)} 笔交易，账户已更新")
    else:
        log(f"  ⚪ 无交易信号")
    
    # 后台测试 iTick（每 10 次检查测试一次）
    if not hasattr(check_signals, 'test_counter'):
        check_signals.test_counter = 0
    check_signals.test_counter += 1
    
    if check_signals.test_counter % 10 == 0:
        log(f"🔬 后台测试 iTick 接口...")
        test_codes = ['sh.601398', 'sz.000001', 'sh.600519']
        itick_results = get_price_itick_batch(test_codes)
        if itick_results:
            log(f"  ✅ iTick 测试成功，获取到 {len(itick_results)} 只股票数据")
        else:
            log(f"  ⚠️ iTick 测试失败")
    
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
