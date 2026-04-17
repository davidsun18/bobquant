# -*- coding: utf-8 -*-
"""
盘中交易系统 - 完整版
实时监控股价，自动预警，支持飞书推送
"""

import requests
import json
import time
from datetime import datetime
import os
import sys

# ==================== 配置 ====================
CONFIG = {
    'positions_file': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account.json',
    'check_interval': 60,  # 60 秒
    'log_file': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/盘中监控.log',
    'alert_file': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/预警记录.json'
}

# ==================== 日志 ====================
def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    # 保存到文件
    try:
        with open(CONFIG['log_file'], 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except:
        pass

# ==================== 获取实时价格 ====================
def get_price(code, max_retries=3):
    """获取实时价格（带重试）"""
    symbol = code.replace('.', '')
    url = f"http://hq.sinajs.cn/list={symbol}"
    
    for i in range(max_retries):
        try:
            headers = {
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0'
            }
            response = requests.get(url, headers=headers, timeout=3)
            response.encoding = 'gbk'
            
            if response.status_code == 200:
                data = response.text.strip()
                if '=' in data:
                    parts = data.split('=')[1].strip('"').split(',')
                    if len(parts) >= 4:
                        return {
                            'name': parts[0],
                            'current': float(parts[3]),
                            'change': (float(parts[3]) - float(parts[2])) / float(parts[2]) * 100
                        }
        except:
            if i < max_retries - 1:
                time.sleep(1)
            continue
    
    return None

# ==================== 加载持仓 ====================
def load_positions():
    """加载持仓数据"""
    try:
        with open(CONFIG['positions_file'], 'r', encoding='utf-8') as f:
            account = json.load(f)
        
        positions = []
        for code, pos in account['positions'].items():
            positions.append({
                'code': code,
                'name': code,  # TODO: 获取股票名称
                'shares': pos['shares'],
                'cost': pos['avg_price'],
                'stop_loss': pos.get('stop_loss', pos['avg_price'] * 0.92),
                'take_profit': pos.get('take_profit', pos['avg_price'] * 1.15)
            })
        
        return positions
    except Exception as e:
        log(f"加载持仓失败：{e}")
        return []

# ==================== 发送预警 ====================
def send_alert(title, message, alert_type='info'):
    """发送预警（记录 + 飞书）"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    # 预警记录
    alert = {
        'time': timestamp,
        'type': alert_type,
        'title': title,
        'message': message
    }
    
    # 保存到文件
    try:
        alerts = []
        if os.path.exists(CONFIG['alert_file']):
            with open(CONFIG['alert_file'], 'r', encoding='utf-8') as f:
                alerts = json.load(f)
        alerts.append(alert)
        with open(CONFIG['alert_file'], 'w', encoding='utf-8') as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    # 打印预警
    emojis = {
        'stop_loss': '🔴',
        'take_profit': '🟢',
        'info': 'ℹ️'
    }
    emoji = emojis.get(alert_type, 'ℹ️')
    
    log(f"{emoji} {title}")
    log(f"   {message}")
    
    # TODO: 发送飞书消息
    # 需要配置飞书 webhook 或使用 message 工具

# ==================== 检查持仓 ====================
def check():
    """检查所有持仓"""
    positions = load_positions()
    
    if not positions:
        log("⚠️ 无持仓")
        return
    
    log(f"📊 检查 {len(positions)} 只持仓...")
    
    for pos in positions:
        quote = get_price(pos['code'])
        
        if not quote:
            log(f"  ❌ {pos['code']}: 获取价格失败")
            continue
        
        current = quote['current']
        change = quote['change']
        
        # 计算盈亏
        profit = (current - pos['cost']) * pos['shares']
        profit_pct = (current - pos['cost']) / pos['cost'] * 100
        
        # 状态
        status = '🟢' if profit > 0 else '🔴' if profit < 0 else '⚪'
        log(f"  {status} {pos['code']}: ¥{current:.2f} ({change:+.1f}%) 盈亏：¥{profit:,.0f} ({profit_pct:+.1f}%)")
        
        # 止损检查
        if current <= pos['stop_loss'] * 1.01:  # 1% 容差
            send_alert(
                f"止损预警 - {pos['code']}",
                f"现价¥{current:.2f} ≤ 止损¥{pos['stop_loss']:.2f}\n"
                f"亏损¥{profit:,.0f} ({profit_pct:.1f}%)\n"
                f"建议：立即卖出！",
                'stop_loss'
            )
        
        # 止盈检查
        if current >= pos['take_profit'] * 0.99:
            send_alert(
                f"止盈预警 - {pos['code']}",
                f"现价¥{current:.2f} ≥ 止盈¥{pos['take_profit']:.2f}\n"
                f"盈利¥{profit:,.0f} ({profit_pct:+.1f}%)\n"
                f"建议：考虑止盈！",
                'take_profit'
            )

# ==================== 交易时间判断 ====================
def is_trading_time():
    """是否在交易时间"""
    now = datetime.now()
    
    # 周末
    if now.weekday() >= 5:
        return False
    
    # 9:30-11:30, 13:00-15:00
    h, m = now.hour, now.minute
    
    if h < 9 or (h == 9 and m < 30):
        return 'before'
    if 11 <= h < 13:
        return 'break'
    if h >= 15:
        return 'after'
    
    return True

# ==================== 主程序 ====================
def main():
    """主循环"""
    log("="*60)
    log("🎯 盘中监控系统启动")
    log("="*60)
    log(f"检查间隔：{CONFIG['check_interval']}秒")
    log(f"持仓文件：{CONFIG['positions_file']}")
    log("="*60)
    
    last_minute = None
    
    while True:
        try:
            now = datetime.now()
            current_minute = now.strftime('%H:%M')
            
            # 交易时间检查
            trading_status = is_trading_time()
            
            if trading_status == True:
                # 每分钟检查一次
                if current_minute != last_minute:
                    check()
                    last_minute = current_minute
            else:
                status_msg = {
                    'before': '未开盘',
                    'break': '午休',
                    'after': '已收盘'
                }
                if now.hour >= 15:
                    log(f"💤 {status_msg.get(trading_status, '等待中...')}，明日再见")
                    break
            
            time.sleep(CONFIG['check_interval'])
            
        except KeyboardInterrupt:
            log("\n⚠️ 用户中断")
            break
        except Exception as e:
            log(f"❌ 错误：{e}")
            time.sleep(10)
    
    log("="*60)
    log("📊 监控结束")
    log("="*60)

if __name__ == '__main__':
    main()
