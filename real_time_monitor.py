# -*- coding: utf-8 -*-
"""
盘中实时监控脚本
每分钟检查价格，触及止损止盈时发送飞书预警
"""

import requests
import json
import time
from datetime import datetime
import os

# ==================== 配置 ====================
CONFIG = {
    'positions': [
        {
            'code': 'sh.601138',
            'name': '工业富联',
            'cost': 47.60,
            'shares': 200,
            'stop_loss': 43.79,
            'take_profit': 54.74
        },
        {
            'code': 'sz.000333',
            'name': '美的集团',
            'cost': 73.37,
            'shares': 100,
            'stop_loss': 67.50,
            'take_profit': 84.38
        },
        {
            'code': 'sh.600887',
            'name': '伊利股份',
            'cost': 25.49,
            'shares': 200,
            'stop_loss': 23.45,
            'take_profit': 29.31
        }
    ],
    'check_interval': 60,  # 60 秒检查一次
    'trading_hours': (9, 15),  # 9:00-15:00
    'output_dir': '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/'
}

# ==================== 获取实时价格 ====================
def get_realtime_price(code):
    """
    从新浪财经获取实时价格
    免费、无需 API Key、实时延迟
    """
    try:
        # sh.601138 → sh601138
        symbol = code.replace('.', '')
        url = f"http://hq.sinajs.cn/list={symbol}"
        
        headers = {
            'Referer': 'http://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'
        
        if response.status_code == 200:
            # 解析返回数据
            # 格式：var hq_str_sh601138="工商银行，4.50,4.49,4.48,4.51,4.47,..."
            data = response.text.strip()
            if '=' in data:
                parts = data.split('=')[1].strip('"').split(',')
                if len(parts) >= 4:
                    name = parts[0]
                    open_price = float(parts[1])
                    pre_close = float(parts[2])
                    current = float(parts[3])
                    high = float(parts[4])
                    low = float(parts[5])
                    
                    return {
                        'name': name,
                        'open': open_price,
                        'pre_close': pre_close,
                        'current': current,
                        'high': high,
                        'low': low,
                        'change': (current - pre_close) / pre_close * 100
                    }
    except Exception as e:
        print(f"获取价格失败：{e}")
    
    return None

# ==================== 发送飞书预警 ====================
def send_feishu_alert(message, alert_type='info'):
    """
    发送飞书消息预警
    需要飞书 webhook 或使用 message 工具
    """
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    # 消息前缀
    emojis = {
        'stop_loss': '🔴 止损预警',
        'take_profit': '🟢 止盈预警',
        'buy_signal': '🟢 买入信号',
        'sell_signal': '🔴 卖出信号',
        'info': 'ℹ️ 系统消息'
    }
    
    emoji = emojis.get(alert_type, 'ℹ️')
    
    alert_msg = f"""
{emoji}
时间：{timestamp}
{message}
    """
    
    print(alert_msg)
    
    # TODO: 如果需要推送到飞书，可以：
    # 1. 使用飞书 webhook
    # 2. 或者调用 message 工具发送
    
    # 保存到预警日志
    log_file = f"{CONFIG['output_dir']}预警日志.txt"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {alert_type}: {message}\n")

# ==================== 检查持仓 ====================
def check_positions():
    """检查所有持仓股票"""
    print(f"\n{'='*60}")
    print(f"📊 盘中检查 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    alerts = []
    
    for pos in CONFIG['positions']:
        # 获取实时价格
        quote = get_realtime_price(pos['code'])
        
        if quote is None:
            print(f"  ❌ {pos['name']}: 获取价格失败")
            continue
        
        current = quote['current']
        change = quote['change']
        
        # 计算盈亏
        profit_loss = (current - pos['cost']) * pos['shares']
        profit_pct = (current - pos['cost']) / pos['cost'] * 100
        
        # 打印状态
        color = '🟢' if profit_loss > 0 else '🔴' if profit_loss < 0 else '⚪'
        print(f"  {color} {pos['name']}: ¥{current:.2f} ({change:+.2f}%) "
              f"盈亏：¥{profit_loss:,.2f} ({profit_pct:+.2f}%)")
        
        # 检查止损
        if current <= pos['stop_loss']:
            msg = f"""
【止损预警】{pos['code']} {pos['name']}
当前价：¥{current:.2f}
止损位：¥{pos['stop_loss']}
成本价：¥{pos['cost']}
持仓：{pos['shares']}股
亏损：¥{profit_loss:,.2f} ({profit_pct:.2f}%)

建议：立即卖出止损！
            """
            alerts.append((msg, 'stop_loss'))
            send_feishu_alert(msg.strip(), 'stop_loss')
        
        # 检查止盈
        elif current >= pos['take_profit']:
            msg = f"""
【止盈预警】{pos['code']} {pos['name']}
当前价：¥{current:.2f}
止盈位：¥{pos['take_profit']}
成本价：¥{pos['cost']}
持仓：{pos['shares']}股
盈利：¥{profit_loss:,.2f} ({profit_pct:.2f}%)

建议：考虑分批止盈！
            """
            alerts.append((msg, 'take_profit'))
            send_feishu_alert(msg.strip(), 'take_profit')
    
    return alerts

# ==================== 判断交易时间 ====================
def is_trading_time():
    """判断是否在交易时间内"""
    now = datetime.now()
    
    # 工作日
    if now.weekday() >= 5:  # 周六日
        return False
    
    # 交易时间 9:30-11:30, 13:00-15:00
    hour = now.hour
    minute = now.minute
    
    if hour < 9 or (hour == 9 and minute < 30):
        return False
    if hour >= 11 and hour < 13:
        return False
    if hour >= 15:
        return False
    
    return True

# ==================== 主循环 ====================
def main_loop():
    """主监控循环"""
    print("="*60)
    print("🎯 盘中实时监控系统启动")
    print("="*60)
    print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"检查间隔：{CONFIG['check_interval']}秒")
    print(f"交易时间：9:30-11:30, 13:00-15:00")
    print(f"监控股票：{len(CONFIG['positions'])} 只")
    print("="*60)
    
    last_check = None
    
    while True:
        try:
            now = datetime.now()
            
            # 检查交易时间
            if is_trading_time():
                # 避免重复检查（每分钟一次）
                current_minute = now.strftime('%H:%M')
                if current_minute != last_check:
                    check_positions()
                    last_check = current_minute
            else:
                # 非交易时间
                if now.hour >= 15:
                    print(f"\n[{now.strftime('%H:%M:%S')}] 收盘了，明日再见！")
                    break
                elif now.hour < 9 or (now.hour == 9 and now.minute < 30):
                    print(f"\n[{now.strftime('%H:%M:%S')}] 还没开盘，等待中...")
            
            # 等待
            time.sleep(CONFIG['check_interval'])
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断，退出监控")
            break
        except Exception as e:
            print(f"\n❌ 错误：{e}")
            time.sleep(10)
    
    print("\n" + "="*60)
    print("📊 监控结束")
    print("="*60)

# ==================== 主函数 ====================
if __name__ == '__main__':
    main_loop()
